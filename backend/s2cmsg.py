"""S2C-MSG binary mesaj katmani (tek dogruluk kaynagi: message_catalog.json).

12B baslik (uiMesajKomut, uiMesajBoyu, uiMesajSayac) + 4B hizali govde, LE.
Yanit ID = istek ID | RESPONSE_BIT. Resync: bayt akisinda ID'nin ust iki
byte'inin (0x5343 / 0xD343) LE yazimdaki `.. .. 43 53` / `.. .. 43 D3`
imzasi aranir; uiMesajBoyu > MAX_BODY veya 4'e bolunmezse senkron kaybi
sayilir ve 1 bayt kaydirilarak devam edilir.
"""
from __future__ import annotations

import json
import struct
import zlib
from functools import lru_cache
from pathlib import Path

RESPONSE_BIT = 0x80000000
HEADER_SIZE = 12
MAX_BODY = 4096
FIXED_REQUEST_SIZE = 28  # cihazIndeks..uiVeriBoyu sabit alanlari
NO_DEVICE = 0xFFFFFFFF

STATUS_LABELS = {0: "OK", 1: "GENEL_HATA", 2: "GECERSIZ_MESAJ",
                 3: "GECERSIZ_PARAMETRE", 4: "CIHAZ_YOK", 5: "BUS_HATASI",
                 6: "ZAMAN_ASIMI", 7: "DESTEKLENMIYOR"}

_CATALOG_PATH = Path(__file__).resolve().parent / "data" / "message_catalog.json"


def _pad4(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    catalog = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog["by_name"] = {m["name"]: m for m in catalog["messages"]}
    catalog["by_id"] = {int(m["id"], 16): m for m in catalog["messages"]}
    catalog["by_op"] = {m["op"]: m for m in catalog["messages"] if m.get("op")}
    return catalog


def catalog_crc32() -> int:
    raw = _CATALOG_PATH.read_bytes()
    return zlib.crc32(raw) & 0xFFFFFFFF


def message_id_for_op(op_name: str) -> int:
    entry = load_catalog()["by_op"].get(op_name)
    if entry is None:
        raise KeyError(f"mesaj katalogunda op yok: {op_name!r} — "
                       "backend/data/message_catalog.json'a KALICI ID ile ekleyin")
    return int(entry["id"], 16)


def message_id_for_name(name: str) -> int:
    entry = load_catalog()["by_name"].get(name)
    if entry is None:
        raise KeyError(f"mesaj katalogunda ad yok: {name!r}")
    return int(entry["id"], 16)


def pack_frame(command_id: int, counter: int, body: bytes) -> bytes:
    body = _pad4(body)
    if len(body) > MAX_BODY:
        raise ValueError(f"govde {len(body)}B > MAX_BODY {MAX_BODY}")
    return struct.pack("<III", command_id, len(body), counter) + body


def pack_request(op_name: str, counter: int, *, device_index: int = NO_DEVICE,
                 register_address: int = 0, address: int = 0, length: int = 0,
                 value: int | None = None, data: bytes = b"") -> bytes:
    body = struct.pack(
        "<IIIIIII",
        device_index & 0xFFFFFFFF,
        register_address & 0xFFFFFFFF,
        address & 0xFFFFFFFF,
        max(0, int(length)) & 0xFFFFFFFF,
        (value or 0) & 0xFFFFFFFF,
        0 if value is None else 1,
        len(data),
    ) + _pad4(bytes(data))
    return pack_frame(message_id_for_op(op_name), counter, body)


def pack_named_request(name: str, counter: int, **kwargs) -> bytes:
    """PING/VERSION/CIT_RUN gibi op'suz mesajlar icin ada gore paketle."""
    entry = load_catalog()["by_name"][name]
    body = struct.pack(
        "<IIIIIII",
        kwargs.get("device_index", NO_DEVICE) & 0xFFFFFFFF,
        kwargs.get("register_address", 0) & 0xFFFFFFFF,
        kwargs.get("address", 0) & 0xFFFFFFFF,
        kwargs.get("length", 0) & 0xFFFFFFFF,
        kwargs.get("value", 0) & 0xFFFFFFFF,
        1 if "value" in kwargs else 0,
        0,
    )
    return pack_frame(int(entry["id"], 16), counter, body)


class FrameParser:
    """Bayt akisindan cerceve ayristirici (resync'li)."""

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> list[tuple[int, int, bytes]]:
        self._buffer.extend(chunk)
        frames: list[tuple[int, int, bytes]] = []
        while True:
            if len(self._buffer) < HEADER_SIZE:
                break
            command_id, body_size, counter = struct.unpack_from("<III", self._buffer, 0)
            signature = (command_id & ~RESPONSE_BIT) >> 16
            if signature != 0x5343 or body_size > MAX_BODY or body_size % 4 != 0:
                # senkron kaybi: 1 bayt at, imzayi yeniden ara
                del self._buffer[0]
                continue
            if len(self._buffer) < HEADER_SIZE + body_size:
                break  # govde henuz tamamlanmadi
            body = bytes(self._buffer[HEADER_SIZE:HEADER_SIZE + body_size])
            del self._buffer[:HEADER_SIZE + body_size]
            frames.append((command_id, counter, body))
        return frames


class ConsoleFrameSplitter:
    """Seri/DCC bayt akisini console metni ile S2C-MSG cerceveleri olarak ayirir.

    FrameParser'dan farki: cerceve OLMAYAN baytlari yutmaz, console olarak
    geri verir. Tek tampon uzerinde calisir; chunk sinirlarinda bolunmus
    imza/baslik/govde dogal olarak birikir (Task 2 review bulgusunun kok
    cozumu — chunk-bazli sezgisel bolme yerine durum makinesi).
    """

    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> tuple[bytes, list[tuple[int, int, bytes]]]:
        """(console_baytlari, cerceveler) dondurur; kararsiz kuyruk tamponda kalir."""
        self._buffer.extend(chunk)
        console = bytearray()
        frames: list[tuple[int, int, bytes]] = []
        while True:
            start = self._find_header_start()
            if start is None:
                # Imza yok: son 3 bayt bir sonraki chunk'ta imza baslangici
                # olabilir — onlari beklet, gerisini console'a ver. Tampon
                # sinirsiz buyumesin: 3 bayt disindaki her sey akitilir.
                keep = min(3, len(self._buffer))
                console.extend(self._buffer[:len(self._buffer) - keep])
                del self._buffer[:len(self._buffer) - keep]
                break
            console.extend(self._buffer[:start])
            del self._buffer[:start]
            if len(self._buffer) < HEADER_SIZE:
                break  # baslik tamamlanana kadar bekle
            command_id, body_size, _counter = struct.unpack_from("<III", self._buffer, 0)
            if body_size > MAX_BODY or body_size % 4 != 0:
                # sahte imza: ilk bayti console'a ver, taramaya devam et
                console.append(self._buffer[0])
                del self._buffer[0]
                continue
            if len(self._buffer) < HEADER_SIZE + body_size:
                break  # govde tamamlanana kadar bekle
            body = bytes(self._buffer[HEADER_SIZE:HEADER_SIZE + body_size])
            counter = struct.unpack_from("<III", self._buffer, 0)[2]
            del self._buffer[:HEADER_SIZE + body_size]
            frames.append((command_id, counter, body))
        return bytes(console), frames

    def _find_header_start(self) -> int | None:
        # Imza baslik offset 2-3'te: 0x43 0x53 (istek) / 0x43 0xD3 (yanit).
        for index in range(len(self._buffer) - 3):
            if self._buffer[index + 2] == 0x43 and self._buffer[index + 3] in (0x53, 0xD3):
                return index
        return None

    def flush(self) -> bytes:
        """Baglanti kapanirken bekletilen kuyrugu console olarak bosalt."""
        leftover = bytes(self._buffer)
        self._buffer.clear()
        return leftover


def unpack_response(frame: tuple[int, int, bytes]) -> dict:
    _command_id, _counter, body = frame
    if len(body) < 20:
        return {"id": "0", "ok": "0", "durum": 2, "status": "0",
                "value": "0x0", "data": "", "message": "kisa yanit govdesi"}
    istek_sayac, durum, cihaz_durum, deger, veri_boyu = struct.unpack_from("<IIiII", body, 0)
    offset = 20
    veri = bytes(body[offset:offset + veri_boyu])
    offset += len(_pad4(veri)) if veri_boyu else 0
    metin = ""
    if len(body) >= offset + 4:
        (metin_boyu,) = struct.unpack_from("<I", body, offset)
        offset += 4
        metin = body[offset:offset + metin_boyu].decode("utf-8", errors="replace")
    return {
        "id": str(istek_sayac),
        "ok": "1" if durum == 0 else "0",
        "durum": durum,
        "status": str(cihaz_durum),
        "value": f"0x{deger:X}",
        "data": veri.hex().upper(),
        "message": metin,
    }


def unpack_trace(frame: tuple[int, int, bytes]) -> dict:
    _command_id, _counter, body = frame
    if len(body) < 8:
        return {"level": 0, "text": ""}
    level, text_size = struct.unpack_from("<II", body, 0)
    text = body[8:8 + text_size].decode("utf-8", errors="replace")
    return {"level": level, "text": text}


def is_response(command_id: int) -> bool:
    return bool(command_id & RESPONSE_BIT)


def is_unsolicited(command_id: int) -> bool:
    entry = load_catalog()["by_id"].get(command_id & ~RESPONSE_BIT)
    return bool(entry and entry.get("dir") == "unsolicited")


def decode_frame_summary(frame: tuple[int, int, bytes]) -> str:
    command_id, counter, body = frame
    entry = load_catalog()["by_id"].get(command_id & ~RESPONSE_BIT)
    name = entry["name"] if entry else f"0x{command_id:08X}"
    suffix = "yanit" if is_response(command_id) else "istek"
    return f"{name} ({suffix}) sayac={counter} govde={len(body)}B"
