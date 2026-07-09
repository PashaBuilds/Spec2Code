# S2C-MSG Binary ICD + CİT + YATT v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Metin-satırı ajan protokolünü 12-byte başlıklı binary S2C-MSG çerçevesiyle TAMAMEN değiştirmek; tüm entegrelerden ham+OK/NOK toplayan CİT altyapısı ve sayfası eklemek; mesaj kataloğundan YATT v1 üretip export etmek.

**Architecture:** Ajan İÇİNDEKİ `spec2codeTestbenchDispatch(SSpec2codeTestbenchRequest*, SSpec2codeTestbenchResponse*)` katmanı (tüm saha-doğrulanmış op dalları) AYNEN KALIR; yalnız tel katmanı değişir: mesaj ID→op-adı ve cihaz-indeks→cihaz-id köprü tabloları üretilir, binary çerçeve ↔ mevcut request/response struct'ları arasında çevrim yapılır. Backend'de `TestbenchCommand` API para birimi kalır; `format_command`/`parse_response` yerine katalog-tabanlı pack/unpack gelir. CİT, dispatch'i içeriden çağıran üretilmiş bir ölçüm döngüsüdür (yeni bus kodu yok). Tek doğruluk kaynağı: `backend/data/message_catalog.json`.

**Tech Stack:** Python 3 (backend `struct`, FastAPI), üretilmiş C (Xilinx BSP, -Werror), React/TS frontend, unittest.

**Spec:** `docs/superpowers/specs/2026-07-09-s2cmsg-cit-yatt-design.md`

## Global Constraints

- Little-endian tel düzeni; başlık 12B: `uiMesajKomut`, `uiMesajBoyu` (gövde, 4'ün katı), `uiMesajSayac` (yön başına 1'den başlar).
- Yanıt ID = istek ID `| 0x80000000`. Komut ID üst 2 byte'ı SABİT `0x5343`; bayt akışında imza `... b0 b1 0x43 0x53` (istek) / `0x43 0xD3` (yanıt).
- `uiMesajBoyu` üst sınırı 4096; aşımı = senkron kaybı → resync.
- Hata kodları: 0 OK, 1 GENEL_HATA, 2 GECERSIZ_MESAJ, 3 GECERSIZ_PARAMETRE, 4 CIHAZ_YOK, 5 BUS_HATASI, 6 ZAMAN_ASIMI, 7 DESTEKLENMIYOR.
- Atanmış mesaj ID'si ASLA değişmez (snapshot testi korur); yeni op grubun sonuna eklenir.
- C kod standardı: `unsigned int`/`int` (uint*_t yok), SPascalStruct, spPointer, uiCamelCase, Allman, 4 boşluk, CRLF üretim çıktısı; packed struct + `_Static_assert` mühürleri.
- Python testler `.venv/Scripts/python.exe -m unittest` ile koşar (sistem python'da jsonschema yok).
- Release YOK — yalnız lokal commit'ler (kullanıcı isterse release).
- Metin protokolü tamamen kalkar: `S2C|id=..` üreten/çözen hiçbir kod kalmaz (git geçmişi yeter).

## Mesaj gövde yerleşimleri (tüm görevlerin ortak sözlüğü)

**İstek gövdesi** (sistem/generic/cihaz-op mesajlarının tümü; `SSpec2codeTestbenchRequest`'in binary karşılığı):

| offset | boy | alan | not |
|-------:|----:|------|-----|
| 0 | 4 | uiCihazIndeks | manifest `devices[]` sırası; cihazsız mesajda 0xFFFFFFFF |
| 4 | 4 | uiRegisterAdres | reg_addr; yoksa 0 |
| 8 | 4 | uiAdres | address; yoksa 0 |
| 12 | 4 | uiUzunluk | length; yoksa 0 |
| 16 | 4 | uiDeger | value |
| 20 | 4 | uiDegerVar | 0/1 |
| 24 | 4 | uiVeriBoyu | N (≤256) |
| 28 | N+pad4 | veri | |

**Yanıt gövdesi** (CIT_RUN/CIT_READ hariç tüm yanıtlar):

| offset | boy | alan |
|-------:|----:|------|
| 0 | 4 | uiIstekSayac |
| 4 | 4 | uiDurum (0 OK / hata tablosu) |
| 8 | 4 | iCihazDurum (ajan iStatus ham, int32) |
| 12 | 4 | uiDeger |
| 16 | 4 | uiVeriBoyu (N) |
| 20 | N+pad4 | veri |
| 20+pad4(N) | 4 | uiMetinBoyu (M) |
| +4 | M+pad4 | metin (tanı; cArrMessage) |

**TRACE_EVENT / BUS_TRACE_EVENT gövdesi** (kendiliğinden; yanıt öneki YOK):
`uiSeviye(4) + uiMetinBoyu(4) + metin(pad4)`.

**CIT_RUN / CIT_READ yanıt gövdesi:** `uiIstekSayac(4) + uiDurum(4) + SBoardCit (packed)`.

**Mesaj ID tablosu (kalıcı — v1'in tamamı):**

| ID | ad | yön |
|----|----|-----|
| 0x53430101 | PING | istek/yanıt |
| 0x53430102 | VERSION | istek/yanıt |
| 0x53430103 | TRACE_LEVEL_SET | istek/yanıt (uiDeger=seviye) |
| 0x53430181 | TRACE_EVENT | kart→üst, kendiliğinden |
| 0x53430182 | BUS_TRACE_EVENT | kart→üst, kendiliğinden |
| 0x53430201 | REGISTER_READ | istek/yanıt |
| 0x53430202 | REGISTER_WRITE | istek/yanıt |
| 0x53430203 | REGISTERS_READ | istek/yanıt (geniş/çoklu) |
| 0x53430204 | MEM_READ | istek/yanıt |
| 0x53430205 | MEM_WRITE | istek/yanıt |
| 0x53430206 | I2C_SCAN | istek/yanıt |
| 0x53430301 | CIT_RUN | istek/yanıt |
| 0x53430302 | CIT_READ | istek/yanıt |
| 0x53430401 | DEVICE_INIT | istek/yanıt |
| 0x53430402 | VOLTAGE_READ | istek/yanıt |
| 0x53430403 | TEMPERATURE_READ | istek/yanıt |
| 0x53430404 | CURRENT_READ | istek/yanıt |
| 0x53430405 | VCC_READ | istek/yanıt |
| 0x53430406 | STATUS_READ | istek/yanıt |
| 0x53430407 | CONFIG_READ | istek/yanıt |
| 0x53430408 | ELAPSED_READ | istek/yanıt |
| 0x53430409 | ALARM_READ | istek/yanıt |
| 0x5343040A | EVENT_READ | istek/yanıt |
| 0x5343040B | SENSE_READ | istek/yanıt |
| 0x5343040C | ADIN_READ | istek/yanıt |
| 0x5343040D | VOUT_READ | istek/yanıt |
| 0x5343040E | POWER_READ | istek/yanıt |
| 0x5343040F | HUMIDITY_READ | istek/yanıt |
| 0x53430410 | USER_REGISTER_READ | istek/yanıt |
| 0x53430411 | ID_READ | istek/yanıt |
| 0x53430412 | DATA_READ | istek/yanıt |
| 0x53430413 | BYTE_WRITE | istek/yanıt |
| 0x53430414 | PAGE_WRITE | istek/yanıt |
| 0x53430415 | PAGE_PROGRAM | istek/yanıt |
| 0x53430416 | SECTOR_ERASE | istek/yanıt |
| 0x53430417 | PLL1_LOCK_DETECT | istek/yanıt |
| 0x53430418 | PLL1_LOCK_LOSS | istek/yanıt |
| 0x53430419 | PLL2_LOCK_DETECT | istek/yanıt |
| 0x5343041A | PLL2_LOCK_LOSS | istek/yanıt |
| 0x5343041B | MULTIPLIER_LOCK_DETECT | istek/yanıt |

Op-adı ↔ mesaj-adı eşlemesi: op adı küçük-harf snake (`voltage_read`) → mesaj adı BÜYÜK snake (`VOLTAGE_READ`). Katalogda olmayan bir descriptor op'u codegen'de HATA üretir ("mesaj kataloğuna ekleyin") — sessiz atlama yok.

**Akış notu (spec §2.4):** flash indirme bugün de üst katmanın 256B'lık DATA_READ istekleriyle parçalanıyor (saha-doğrulanmış); v1 bu davranışı korur — tek istek→tek yanıt. `uiParcaNo` şeması katalogda gelecekteki büyük transferler için rezervedir, v1'de üretilmez.

---

### Task 1: message_catalog.json + backend kodek (`s2cmsg.py`)

**Files:**
- Create: `backend/data/message_catalog.json`
- Create: `backend/s2cmsg.py`
- Test: `tests/test_s2cmsg.py`

**Interfaces:**
- Produces (sonraki görevler bunlara güvenir):
  - `s2cmsg.RESPONSE_BIT = 0x80000000`, `s2cmsg.HEADER_SIZE = 12`, `s2cmsg.MAX_BODY = 4096`
  - `s2cmsg.STATUS_LABELS: dict[int, str]` (0..7 → "OK".."DESTEKLENMIYOR")
  - `s2cmsg.load_catalog() -> dict` (id→tanım ve ad→tanım indeksli)
  - `s2cmsg.message_id_for_op(op_name: str) -> int` (bilinmeyen op → `KeyError`)
  - `s2cmsg.pack_request(op_name: str, counter: int, *, device_index: int = 0xFFFFFFFF, register_address: int = 0, address: int = 0, length: int = 0, value: int | None = None, data: bytes = b"") -> bytes`
  - `s2cmsg.FrameParser` — `feed(chunk: bytes) -> list[Frame]`; `Frame = (command_id: int, counter: int, body: bytes)`; senkron kaybında bayt atlayıp toparlar
  - `s2cmsg.unpack_response(frame) -> dict` — anahtarlar mevcut `parse_response` sözlüğüyle uyumlu: `{"id": str(uiIstekSayac), "ok": "1"/"0", "status": str(iCihazDurum), "value": "0x..", "data": hex, "message": str, "durum": int}`
  - `s2cmsg.unpack_trace(frame) -> dict` — `{"level": int, "text": str}`
  - `s2cmsg.decode_frame_summary(frame) -> str` — traffic log için "VOLTAGE_READ idx=0 sayac=12" gibi tek satır özet
  - `s2cmsg.catalog_crc32() -> int` — kontrat hash'i

**Step 1: Kataloğu yaz** — `backend/data/message_catalog.json`, yukarıdaki ID tablosunun TAMAMI şu şemayla (ilk üç girdi örneği; kalan girdiler ID tablosundaki tüm satırlar için aynı kalıpta, `body` alanı üç sabitten biri: `"request_std"`, `"response_std"`, `"trace"`, `"cit"`):

```json
{
  "version": 1,
  "endian": "little",
  "header": [
    {"name": "uiMesajKomut", "type": "u32"},
    {"name": "uiMesajBoyu",  "type": "u32"},
    {"name": "uiMesajSayac", "type": "u32"}
  ],
  "status_codes": {"0": "OK", "1": "GENEL_HATA", "2": "GECERSIZ_MESAJ",
    "3": "GECERSIZ_PARAMETRE", "4": "CIHAZ_YOK", "5": "BUS_HATASI",
    "6": "ZAMAN_ASIMI", "7": "DESTEKLENMIYOR"},
  "messages": [
    {"id": "0x53430101", "name": "PING", "op": null, "dir": "req",
     "body": "request_std", "aciklama": "Yasam isareti; yanit govdesi standart."},
    {"id": "0x53430181", "name": "TRACE_EVENT", "op": null, "dir": "unsolicited",
     "body": "trace", "aciklama": "Ajan trace/log satiri."},
    {"id": "0x53430402", "name": "VOLTAGE_READ", "op": "voltage_read", "dir": "req",
     "body": "request_std", "aciklama": "Birimli voltaj okumasi (mV)."}
  ]
}
```

- [ ] **Step 2: Failing test yaz** — `tests/test_s2cmsg.py`:

```python
import unittest
from backend import s2cmsg


class CatalogTests(unittest.TestCase):
    def test_catalog_ids_are_stable_snapshot(self) -> None:
        # KALICILIK KURALI: atanan ID asla degismez. Bu tablo bilerek
        # elle yazilmistir; katalogda ID degisirse bu test KIRILMALIDIR.
        expected = {
            "PING": 0x53430101, "VERSION": 0x53430102, "TRACE_LEVEL_SET": 0x53430103,
            "TRACE_EVENT": 0x53430181, "BUS_TRACE_EVENT": 0x53430182,
            "REGISTER_READ": 0x53430201, "REGISTER_WRITE": 0x53430202,
            "REGISTERS_READ": 0x53430203, "MEM_READ": 0x53430204,
            "MEM_WRITE": 0x53430205, "I2C_SCAN": 0x53430206,
            "CIT_RUN": 0x53430301, "CIT_READ": 0x53430302,
            "DEVICE_INIT": 0x53430401, "VOLTAGE_READ": 0x53430402,
            "TEMPERATURE_READ": 0x53430403, "CURRENT_READ": 0x53430404,
            "VCC_READ": 0x53430405, "STATUS_READ": 0x53430406,
            "CONFIG_READ": 0x53430407, "ELAPSED_READ": 0x53430408,
            "ALARM_READ": 0x53430409, "EVENT_READ": 0x5343040A,
            "SENSE_READ": 0x5343040B, "ADIN_READ": 0x5343040C,
            "VOUT_READ": 0x5343040D, "POWER_READ": 0x5343040E,
            "HUMIDITY_READ": 0x5343040F, "USER_REGISTER_READ": 0x53430410,
            "ID_READ": 0x53430411, "DATA_READ": 0x53430412,
            "BYTE_WRITE": 0x53430413, "PAGE_WRITE": 0x53430414,
            "PAGE_PROGRAM": 0x53430415, "SECTOR_ERASE": 0x53430416,
            "PLL1_LOCK_DETECT": 0x53430417, "PLL1_LOCK_LOSS": 0x53430418,
            "PLL2_LOCK_DETECT": 0x53430419, "PLL2_LOCK_LOSS": 0x5343041A,
            "MULTIPLIER_LOCK_DETECT": 0x5343041B,
        }
        catalog = s2cmsg.load_catalog()
        actual = {m["name"]: int(m["id"], 16) for m in catalog["messages"]}
        for name, mid in expected.items():
            self.assertEqual(actual.get(name), mid, f"{name} ID degisti/yok!")
        # Tum ID'ler 0x5343 imzasini tasimali (resync varsayimi).
        for name, mid in actual.items():
            self.assertEqual(mid >> 16, 0x5343, name)

    def test_every_id_is_unique(self) -> None:
        catalog = s2cmsg.load_catalog()
        ids = [m["id"] for m in catalog["messages"]]
        self.assertEqual(len(ids), len(set(ids)))


class PackUnpackTests(unittest.TestCase):
    def test_request_roundtrip_header_and_alignment(self) -> None:
        frame = s2cmsg.pack_request("voltage_read", 7, device_index=2,
                                    register_address=0x0A, value=0x55, data=b"\x01\x02\x03")
        # 12B baslik + 28B sabit alanlar + 3B veri pad->4B = 44B govde
        self.assertEqual(len(frame), 12 + 28 + 4)
        parser = s2cmsg.FrameParser()
        frames = parser.feed(frame)
        self.assertEqual(len(frames), 1)
        cmd, counter, body = frames[0]
        self.assertEqual(cmd, 0x53430402)
        self.assertEqual(counter, 7)
        self.assertEqual(len(body) % 4, 0)

    def test_parser_resyncs_after_garbage(self) -> None:
        good = s2cmsg.pack_request("ping", 1)
        noisy = b"\xde\xad\xbe\xef\r\nboot log\n" + good + b"\x00" + good
        parser = s2cmsg.FrameParser()
        frames = parser.feed(noisy)
        self.assertEqual(len(frames), 2)
        self.assertTrue(all(f[0] == 0x53430101 for f in frames))

    def test_parser_survives_split_delivery(self) -> None:
        good = s2cmsg.pack_request("mem_read", 3, address=0xA0000000, length=4)
        parser = s2cmsg.FrameParser()
        out = []
        for i in range(len(good)):
            out += parser.feed(good[i:i + 1])
        self.assertEqual(len(out), 1)

    def test_unpack_response_maps_status_and_text(self) -> None:
        # Elle kurulmus yanit govdesi: sayac=7, durum=5 (BUS_HATASI),
        # iCihazDurum=-2, deger=0xCAFE, veri=2B, metin="I2C NACK"
        import struct
        body = struct.pack("<IIiII", 7, 5, -2, 0xCAFE, 2) + b"\xAB\xCD\x00\x00"
        text = b"I2C NACK"
        body += struct.pack("<I", len(text)) + text  # 8B, zaten 4 kati
        header = struct.pack("<III", 0x53430402 | s2cmsg.RESPONSE_BIT, len(body), 42)
        frames = s2cmsg.FrameParser().feed(header + body)
        parsed = s2cmsg.unpack_response(frames[0])
        self.assertEqual(parsed["id"], "7")
        self.assertEqual(parsed["ok"], "0")
        self.assertEqual(parsed["durum"], 5)
        self.assertEqual(parsed["status"], "-2")
        self.assertEqual(parsed["value"], "0xCAFE")
        self.assertEqual(parsed["data"], "ABCD")
        self.assertEqual(parsed["message"], "I2C NACK")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Testin FAIL ettiğini gör** — `cd D:/Projects/claude/Spec2Code && .venv/Scripts/python.exe -m unittest tests.test_s2cmsg -v` → beklenen: `ModuleNotFoundError`/`ImportError` (s2cmsg yok).

- [ ] **Step 4: `backend/s2cmsg.py`'yi yaz** — tam içerik:

```python
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
```

- [ ] **Step 5: Testleri koş** — `.venv/Scripts/python.exe -m unittest tests.test_s2cmsg -v` → beklenen: hepsi PASS. (`pack_request("ping", ...)` çağrısı için katalogda PING'e `"op": "ping"` verilmeli — kataloğu buna göre yaz: sistem mesajlarında da op alanı dolu: `ping`, `version`, `trace_level_set`.)

- [ ] **Step 6: Commit** — `git add backend/data/message_catalog.json backend/s2cmsg.py tests/test_s2cmsg.py && git commit -m "S2C-MSG: mesaj katalogu + backend binary kodek (ID snapshot testli)"`

---

### Task 2: Backend transport katmanının binary'ye tam geçişi

**Files:**
- Modify: `backend/testbench.py` (format_command:78, parse_response:101, `_read_response_line`:111, `_TestbenchTcpSession.send`:257, `_TestbenchSerialSession._reader_loop`:439 ve `send`:490, `_TrafficRing._traffic_push`:153)
- Modify: `backend/api/routes.py:1192` (`testbench_command` — `device_index` alanı)
- Test: `tests/test_testbench.py` (FakeSerial:107, OneShot/Persistent handler:82/90, CoresightEchoHandler:168 ve ilgili testler)

**Interfaces:**
- Consumes: Task 1'in tamamı.
- Produces:
  - `TestbenchCommand` dataclass'ına `device_index: int = 0xFFFFFFFF` alanı eklenir; `operation` op adı olarak kalır.
  - `format_command`/`parse_response` SİLİNİR; yerine `s2cmsg.pack_request` / `s2cmsg.unpack_response` kullanılır.
  - Oturum sınıflarında satır okuma yerine `s2cmsg.FrameParser`; yanıt eşleme `uiIstekSayac == gönderilen sayaç` ile (bugünkü id eşlemesinin birebir karşılığı — `_TestbenchTcpSession.send` içindeki "geç yanıt" mantığı korunur, satır yerine frame).
  - Seri oturumda frame parser'dan artan (imza tutmayan) baytlar mevcut console satır tamponuna akmaya devam eder (boot logları görünür kalır).
  - `_traffic_push(direction, entry)` artık `{"dir","hex","ozet"}` yazar: `hex` = çerçevenin hex dökümü (ilk 64B), `ozet` = `s2cmsg.decode_frame_summary(...)`.
  - Kendiliğinden TRACE_EVENT/BUS_TRACE_EVENT çerçeveleri console/trace akışına `unpack_trace` metniyle düşer.
- Testler: `FakeSerial`/`OneShotHandler`/`PersistentHandler`/`StaleThenAnswerHandler`/`CoresightEchoHandler` binary konuşur: istek çerçevesini `FrameParser` ile çözüp `pack_frame(cmd|RESPONSE_BIT, ..., yanıt_gövdesi)` döner. `test_command_formatter_and_response_parser` yeni pack/unpack'i doğrular. `test_serial_send_matches_response_by_command_id` sayaç eşlemesiyle güncellenir.

- [ ] Step 1: `tests/test_testbench.py` içinde önce yardımcı ekle (fake'lerin ortak yanıt kurucusu) + `test_command_formatter_and_response_parser`'ı binary bekleyecek şekilde YENİDEN yaz; koş → FAIL.
- [ ] Step 2: `backend/testbench.py` geçişini yaz (yukarıdaki Produces sözleşmesi birebir). Metin protokolüne dair TÜM kod silinir (`_clean_token`/`_hex_data` yalnız hâlâ kullanan varsa kalır; kullanılmıyorsa silinir).
- [ ] Step 3: Fake'leri binary'ye çevir; TÜM testbench oturum testlerini koş → PASS: `.venv/Scripts/python.exe -m unittest tests.test_testbench -v` (codegen testleri Task 4'e kadar metin dispatch'i test etmeye devam eder — onlara DOKUNMA; yalnız oturum/format testleri değişir).
- [ ] Step 4: `routes.py` `TestbenchCommandRequest`'e `device_index: int = 0xFFFFFFFF` ekle ve `TestbenchCommand`'a geçir.
- [ ] Step 5: Commit — `"S2C-MSG: backend transport katmani binary'ye gecti (metin protokolu kalkti)"`

---

### Task 3: Frontend — device_index + trafik görünümü

**Files:**
- Modify: `frontend/src/lib/api.ts` (testbenchCommand)
- Modify: `frontend/src/lib/types.ts` (TestbenchCommand tipi)
- Modify: `frontend/src/features/serial-line/SerialLinePanel.tsx` ve Akış trafik render'ı (traffic girdileri `{dir,hex,ozet}`)

**Interfaces:**
- Consumes: Task 2 (`device_index` request alanı; traffic yeni biçimi).
- Produces: `api.testbenchCommand` çağrıları store'daki manifest `devices[]` sırasından `device_index`'i MERKEZİ olarak çözer (tek yerde: api.ts içinde `resolveDeviceIndex(deviceId)`; manifest store'da yoksa 0xFFFFFFFF). Trafik bileşeni hex + özet satırı gösterir.

- [ ] Step 1: `api.ts`'te `resolveDeviceIndex` + testbenchCommand gövdesine `device_index` ekle.
- [ ] Step 2: Trafik render'ını `{dir,hex,ozet}`'e uyarlaya; `npm run build` (frontend/) → PASS.
- [ ] Step 3: Commit — `"S2C-MSG: UI device_index cozumu + binary trafik gorunumu"`

---

### Task 4: Codegen — üretilen ajan tel katmanı (`spec2code_mesaj.h/.c`)

**Files:**
- Modify: `orchestrator/codegen.py` — yeni üreteçler: `_mesaj_header()`, `_mesaj_source(spec, get_descriptor)`; `_testbench_protocol_header/source`'a DOKUNULMAZ (iç dispatch para birimi olarak kalır) ama `RequestParse`/`ResponseFormat` satır fonksiyonları ve onları çağıran yerler kaldırılır; `testbench_harness_paths`/`write_testbench_harness`'e yeni dosyalar eklenir; `_testbench_manifest`'e `"message_catalog_crc32"` alanı eklenir.
- Modify: `orchestrator/codegen.py` katalog okuma: `backend/data/message_catalog.json` repo-göreli yüklenir (`_ROOT` üzerinden); paketli exe'de data dosyası PyInstaller datas'ına eklidir (mevcut descriptors kalıbıyla aynı — `spec2code.spec` dosyasına `backend/data` zaten gidiyor mu KONTROL ET, gitmiyorsa ekle).
- Test: `tests/test_testbench.py::test_generated_request_parser_round_trips_on_host_compiler` (1688) kalıbı örnek alınarak YENİ test: `test_generated_mesaj_layer_round_trips_on_host_compiler` + `test_mesaj_id_tablosu_kataloga_esit`.

**Interfaces:**
- Consumes: Task 1 kataloğu.
- Produces (üretilen C):
  - `spec2code_mesaj.h`: `SMesajBaslik` (12B, packed+static_assert), `SPEC2CODE_MESAJ_*` ID makroları (katalogdan), `SPEC2CODE_MESAJ_DURUM_*` (0..7), API:
    - `void spec2codeMesajParserSifirla(SMesajParser* spParser);`
    - `int spec2codeMesajBesle(SMesajParser* spParser, const unsigned char* ucpVeri, unsigned int uiBoy);` → tam çerçeve hazırsa 1 döner, `spParser->sBaslik` + `spParser->ucArrGovde` doldurulur (resync mantığı Task 1 Python parser'ının C ikizi)
    - `int spec2codeMesajIsle(const SMesajBaslik* spBaslik, const unsigned char* ucpGovde, unsigned char* ucpCikti, unsigned int uiCiktiKapasite, unsigned int* upCiktiBoy);` → gövdeyi `SSpec2codeTestbenchRequest`'e açar (ID→op adı tablosu + indeks→cihaz-id tablosu), MEVCUT `spec2codeTestbenchDispatch`'i çağırır, yanıtı binary çerçeveye paketler (yanıt sayacı ajan tarafı monoton `S_uiYanitSayac`)
    - `unsigned int spec2codeMesajTraceCerceveKur(unsigned int uiSeviye, const char* cpMetin, unsigned char* ucpCikti, unsigned int uiKapasite);`
  - ID→op tablosu üretimde katalogdan gelir; spec'te olup katalogda olmayan op = üretim HATASI.
- Test C round-trip (host derleyici): istek çerçevesi kur → `spec2codeMesajBesle` → `spec2codeMesajIsle` (dispatch stub'lu) → dönen çerçeveyi Python `s2cmsg.FrameParser`+`unpack_response` ile çöz → alanlar eşit. Araya çöp bayt sokarak resync da aynı testte doğrulanır.

- [ ] Step 1: `test_mesaj_id_tablosu_kataloga_esit` + host round-trip testini yaz; koş → FAIL.
- [ ] Step 2: `_mesaj_header/_mesaj_source` üreteçlerini yaz (C içerik yukarıdaki API'ye birebir; parser C kodu Task 1'deki Python `FrameParser.feed` mantığının satır satır karşılığı — imza `0x5343`, boy sınırı 4096, 1-bayt kaydırmalı resync).
- [ ] Step 3: Harness path listesine ekle; testler PASS olana kadar düzelt.
- [ ] Step 4: Commit — `"S2C-MSG codegen: uretilen mesaj katmani (parser+dispatch koprusu, host round-trip testli)"`

---

### Task 5: Codegen — üç transportun binary çerçeveye bağlanması + trace çerçeveleme

**Files:**
- Modify: `orchestrator/codegen.py`:
  - `_testbench_lwip_source_socket` (2918) / `_testbench_lwip_source_raw` (3186): satır tamponu (`S_cArrRequestLine`) yerine `SMesajParser` + `spec2codeMesajBesle`/`spec2codeMesajIsle`; TCP'de kısmi gönderim döngüsü aynı kalır.
  - `_testbench_uart_source` (3614): karakter alımı frame parser'a akar; eski satır sonu (`\n`) tetikleyicisi kalkar; banner/enter-prompt metin karşılama kaldırılır (binary kanalda banner YOK — testler güncellenir).
  - `_testbench_coresight_source` (3902): DCC byte köprüsü aynı; satır yerine frame parser.
  - `_testbench_trace_source` (982) / `_testbench_log_source` (805): transport'a satır yazan emit yolu `spec2codeMesajTraceCerceveKur` ile TRACE_EVENT/BUS_TRACE_EVENT çerçevesi yazar.
- Test: `tests/test_testbench.py` içindeki üretilen-kaynak metin beklentileri güncellenir: `test_uart_agent_banner_and_enter_prompt` → `test_uart_agent_feeds_bytes_into_mesaj_parser` (banner yok, `spec2codeMesajBesle` çağrısı var); lwIP/DCC testlerinde `DispatchLine` beklentileri `MesajIsle`'ye döner; `test_agent_line_buffer_fits_full_data_payload_and_guards_overflow` → çerçeve kapasite testi (`SPEC2CODE_TESTBENCH_DATA_MAX` 256 + metin 160 + sabitler ≤ çıktı tamponu; static_assert üret).

- [ ] Step 1: Test beklentilerini yeni sözleşmeye çevir; koş → FAIL.
- [ ] Step 2: Dört üreteç fonksiyonunu geçir; `spec2codeTestbenchDispatchLine` ve onu çağıran her şey SİLİNİR (grep ile sıfır referans doğrulanır: `grep -rn "DispatchLine" orchestrator/ backend/` boş).
- [ ] Step 3: Tüm suite koş: `.venv/Scripts/python.exe -m unittest discover -s tests -q` → PASS.
- [ ] Step 4: Commit — `"S2C-MSG codegen: UART/TCP/DCC binary cerceveye gecti; trace TRACE_EVENT oldu; metin dispatch silindi"`

---

### Task 6: CİT modeli — şematik config + manifest bölümü

**Files:**
- Modify: `frontend/src/lib/types.ts` — `Device.config.cit?: { measurements: Array<{ op: string; name: string; min?: number; max?: number; severity: "critical" | "warning"; enabled: boolean }> }`
- Modify: `orchestrator/codegen.py` `_testbench_manifest` (1065) — manifest'e `"cit"` bölümü: her cihazın birimli read op'ları (spec §4.1: `_op_wire_plan`'ı olan, `returns` içeren op'lar) + kullanıcı config'inden isim/limit/önem; isim verilmemişse `<PART>_<OP>_<CihazIndeks>`; C tanımlayıcı türetimi `_pascal_identifier` ile.
- Test: `tests/test_testbench.py::test_manifest_cit_section_lists_unit_measurements_with_limits` (yeni)

**Interfaces:**
- Produces: manifest `"cit"`: `{"olcumler": [{"index": 0, "device": "u12", "device_index": 0, "part": "LTC2991", "op": "voltage_read", "name": "VCC_3V3_RF", "cname": "Vcc3v3Rf", "unit": "mV", "min": 3135, "max": 3465, "severity": "critical", "enabled": true}, ...], "bit_sirasi": ["Vcc3v3Rf", ...]}` — Task 7 codegen'i ve Task 8 decode bu sırayı kullanır (bit i = olcumler[i]).

- [ ] Step 1: Manifest testini yaz (LTC2991+AD7414'lü spec, config.cit'li) → FAIL.
- [ ] Step 2: `_testbench_manifest`'e cit bölümünü ekle → PASS.
- [ ] Step 3: Commit — `"CIT modeli: sematik config.cit + manifest cit bolumu (bit sirasi sozlesmesi)"`

---

### Task 7: CİT codegen — `SBoardCit` + `boardCitRun` + CIT_RUN/CIT_READ

**Files:**
- Modify: `orchestrator/codegen.py` — yeni üreteç `_cit_header(spec,...)` / `_cit_source(spec,...)` → `spec2code_cit.h/.c`; `spec2codeMesajIsle` içine CIT_RUN/CIT_READ dalları; harness path listesine ekleme.
- Test: `tests/test_cit_codegen.py` (yeni dosya): (a) üretilen header'da kullanıcı isimli bitler + `_Static_assert` var; (b) host derleme round-trip: dispatch stub'u sabit değerler döner → `boardCitRun` → bitler/limitler doğru; limit dışı değer → OK=0; bus hatası (stub iStatus<0) → uiDurum=5, koşu devam.

**Interfaces:**
- Consumes: Task 6 manifest `cit.olcumler` sırası; Task 4 `spec2codeTestbenchDispatch` köprüsü.
- Produces (üretilen C, spec §4.2 birebir):

```c
typedef struct { unsigned int uiVcc3v3RfOk : 1; /* olcum sirasiyla */ } SBoardCitBayraklar;
typedef struct { int iDeger; unsigned int uiHam; unsigned int uiDurum; } SBoardCitOlcum;
typedef struct { unsigned int uiSayac; unsigned int uiZaman;
                 SBoardCitBayraklar sBayraklar;
                 SBoardCitOlcum arrOlcum[BOARD_CIT_OLCUM_SAYISI]; } SBoardCit;
void boardCitRun(SBoardCit* spCit);      /* dispatch'i iceriden cagirir */
const SBoardCit* boardCitSon(void);      /* CIT_READ icin son kosu     */
```

  - Limit tablosu üretilen sabit dizi: `{iMin, iMax, uiLimitVar, uiKritik}`.
  - `uiHam` = yanıt `data`'nın ilk 4B'ı (varsa) yoksa `uiDeger`; `iDeger` = `(int)uiDeger` (işlenmiş birimli değer — mevcut decoded-value davranışı).
  - CIT_RUN yanıt gövdesi: `uiIstekSayac + uiDurum + SBoardCit` (packed kopya; `_Static_assert(sizeof(SBoardCit) % 4 == 0)`).

- [ ] Step 1: `tests/test_cit_codegen.py` yaz → FAIL.
- [ ] Step 2: Üreteçleri yaz; MesajIsle'ye CIT dallarını ekle → PASS (host derleme dahil).
- [ ] Step 3: Commit — `"CIT codegen: SBoardCit + boardCitRun + CIT_RUN/CIT_READ (host derleme testli)"`

---

### Task 8: CİT sayfası (UI) + decode endpoint

**Files:**
- Create: `frontend/src/features/cit/CitPanel.tsx`
- Modify: `frontend/src/App.tsx` (nav "CİT" + palette + keepAlive — RegisterMapPanel kaydıyla aynı kalıp)
- Modify: `backend/api/routes.py` — `POST /testbench/cit/run` ve `POST /testbench/cit/read`: `{session_id, manifest}` alır; CIT_RUN/CIT_READ çerçevesini yollar, `SBoardCit`'i manifest `cit.olcumler` sırasıyla çözer → `{"sayac": n, "zaman": t, "olcumler": [{"name","part","device","raw","value","unit","ok","durum","min","max","severity"}]}`
- Modify: `backend/testbench.py` — `TestbenchSessionManager.send_named(session_id, name, timeout_s)` (op'suz katalog mesajı gönderimi; `pack_named_request` kullanır, ham yanıt gövdesini de döner)
- Test: `tests/test_cit_api.py` (yeni): sahte oturum + elle kurulmuş SBoardCit çerçevesi → decode endpoint JSON'u doğru.

**UI davranışı (spec §4.4):** üst şerit (kritik NOK, uyarı NOK, son koşu, sayaç) + tablo (ad/cihaz/ham/işlenmiş+birim/min-max/önem/OK-NOK rozeti) + "CİT koştur" + periyodik yenile (5 sn toggle) + satır içi isim/min/max/önem düzenleme → `useStore` device.config.cit'e persist + "kontrat değişti — kodu yeniden üret" rozeti (manifest'teki limitlerle store'daki farklıysa).

- [ ] Step 1: `tests/test_cit_api.py` yaz → FAIL; endpoint + `send_named`'i yaz → PASS.
- [ ] Step 2: CitPanel + App kaydı; `npm run build` → PASS.
- [ ] Step 3: Preview doğrulaması (demo/sahte veriyle tablo render) + Commit — `"CIT sayfasi + decode endpointleri"`

---

### Task 9: Arayüz/YATT sayfası + export

**Files:**
- Create: `backend/yatt.py` — `build_yatt_html(catalog: dict, manifest: dict | None) -> str` (self-contained; `backend/register_map.py:781 build_html` kalıbı) ve `build_yatt_markdown(...) -> str`. İçerik: başlık formatı (12B tablo), sayaç/yanıt-biti/resync kuralları, hata kodları, mesaj tablosu (ID/ad/yön/gövde), gövde alan tabloları (bu planın "Mesaj gövde yerleşimleri" bölümü verinin kaynağı: katalogdaki `body` şablon adı → alan listesi), cihaz tablosu + CİT structure yerleşimi (manifest verilmişse).
- Modify: `backend/api/routes.py` — `GET /yatt/catalog` (JSON), `GET /yatt/export?fmt=html|md` (+ opsiyonel manifest POST varyantı `POST /yatt/export`).
- Create: `frontend/src/features/yatt/YattPanel.tsx` — mesaj tablosu, satır genişlet→alan tablosu, "YATT dışa aktar (HTML)/(MD)" indirme; App.tsx kaydı ("Arayüz/YATT").
- Test: `tests/test_yatt.py`: HTML çıktısında tüm mesaj ID'leri + başlık alan adları + hata kodu etiketleri geçiyor; MD çıktısı boş değil ve ID tablosu satır sayısı katalogla eşit.

- [ ] Step 1: `tests/test_yatt.py` yaz → FAIL; `backend/yatt.py` + endpointler → PASS.
- [ ] Step 2: YattPanel + App kaydı; `npm run build` → PASS; preview'da sayfa render + export indirme doğrula.
- [ ] Step 3: Commit — `"YATT v1: Arayuz sayfasi + self-contained HTML/MD export"`

---

### Task 10: Uçtan uca kapanış — parite listesi, sürüm, changelog

**Files:**
- Create: `docs/s2cmsg_parite_listesi.md` — kullanıcının gerçek kartta koşacağı kontrol listesi (üç transport × {register R/W, birimli okumalar, device_init, flash 256B indir/yükle döngüsü, i2c tarama, trace seviyeleri, CIT_RUN}) + beklenen sonuçlar.
- Modify: `frontend/src/lib/version.ts` (bump), `changelog.md` (S2C-MSG tam geçiş + CİT + YATT girdisi; "gerçek kart doğrulaması bekliyor" notu).
- Test: tam suite + frontend build.

- [ ] Step 1: Tam koşu: `.venv/Scripts/python.exe -m unittest discover -s tests -q` → OK; `cd frontend && npm run build` → PASS.
- [ ] Step 2: Parite listesi + changelog + sürüm.
- [ ] Step 3: Commit — `"S2C-MSG + CIT + YATT v1 kapanis: parite listesi, changelog, surum"` (push/release YOK).

---

## Self-Review Notları (plan yazarı kontrolü)

- **Spec kapsaması:** §2 çerçeve→Task 1/2/4/5; §3 katalog/ID→Task 1 (+Task 4 üretim hatası kuralı); §3.3 VERSION kontrat hash→Task 1 `catalog_crc32` + Task 4 manifest alanı (VERSION yanıt gövdesine hash yazımı Task 4 MesajIsle'de); §4 CİT→Task 6/7/8; §5 YATT→Task 9; §6 geçiş etkisi/testler→Task 2/3/5/10. Akış parçalama (§2.4) v1'de üst-katman parçalama olarak korunuyor — planın "Akış notu"nda gerekçeli.
- **Tip tutarlılığı:** `Frame = (command_id, counter, body)` tuple'ı Task 1'de tanımlı, Task 2/8 aynı imzayı kullanıyor; `SMesajParser`/`spec2codeMesajBesle/Isle` adları Task 4-5-7 arasında birebir aynı; manifest `cit.olcumler` sırası Task 6→7→8 sözleşmesi.
- **Placeholder taraması:** "benzer şekilde/TBD" yok; katalog JSON'unda kalan girdiler için kalıp + TAM ID/ad tablosu bu dosyada mevcut (veri, kod değil).
