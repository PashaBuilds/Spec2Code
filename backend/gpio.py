"""AXI GPIO denetleyici op'lari (gpio_read / gpio_write) orkestrasyonu.

Ajan iki DENETLEYICI-adresli op sunar: hedef bir cihaz degil, bir AXI GPIO
cekirdeginin kendisidir (LED/reset bankasi gibi bir "parca" karsiligi olmayan
hatlar). Bu yuzden S2C-MSG tel cercevesindeki ``uiCihazIndeks`` bir DENETLEYICI
indeksidir — manifest ``gpio.controllers[].index`` degeri — ve uretilen kopru
``cArrRegister``'i denetleyici tablosundan cozer (bkz. ``backend/i2c_scan.py``,
ayni kontrat).

Govde eslemesi (tek kaynak: backend/data/message_catalog.json, YATT'ta gorunur):
  * ``uiAdres``   = kanal (1 veya 2)
  * ``uiUzunluk`` = pin maskesi (0 = tum 32 pin)
  * ``uiDeger``   = yazilacak deger (yalniz gpio_write)
  * yanit ``uiDeger`` = op SONRASI maskelenmis kanal degeri; veri alani ayni
    degerin 4 baytidir (MSB once).

Yon (TRI) davranisi bilincli olarak asimetriktir: ``gpio_write`` maskelenen
pinleri CIKIS yapar (aksi halde tri-state bir pine yazmak hicbir sey yapmaz),
``gpio_read`` yonu HIC DEGISTIRMEZ — surulen bir hatti (tutulan reset, enable)
giris yapmak yikicidir.
"""

from __future__ import annotations

import time

from backend.testbench import TestbenchCommand, testbench_sessions

#: GPIO komutlari UI komut sayaclariyla ve tarama bandiyla cakismasin diye
#: ayri bant (bkz. i2c_scan._SCAN_COMMAND_ID_BASE = 7000).
_GPIO_COMMAND_ID_BASE = 7500

#: "Denetleyici yok" (0xFFFFFFFF): denetleyici indeksi cozulemediginde tel bu
#: degeri tasir (bkz. s2cmsg.NO_DEVICE).
_NO_CONTROLLER = 0xFFFFFFFF

_U32_MAX = 0xFFFFFFFF

#: Kart uzerinde gecerli AXI GPIO kanallari (IP'nin en fazla iki kanali vardir).
_CHANNELS = (1, 2)


class GpioError(RuntimeError):
    """Ajan gpio op'unu reddetti (mesaj ajandan gelir)."""


_command_id = _GPIO_COMMAND_ID_BASE


def _next_command_id() -> int:
    global _command_id
    _command_id += 1
    return _command_id


def _check(channel: int, mask: int, value: int | None) -> None:
    if channel not in _CHANNELS:
        raise GpioError(f"kanal 1 veya 2 olmali (verilen: {channel})")
    if not 0 <= mask <= _U32_MAX:
        raise GpioError(f"pin maskesi 32 bite sigmali (verilen: 0x{mask:X})")
    if value is not None and not 0 <= value <= _U32_MAX:
        raise GpioError(f"deger 32 bite sigmali (verilen: 0x{value:X})")


def _run(session_id: str, operation: str, controller_id: str, controller_index: int,
         *, channel: int, mask: int, value: int | None, timeout_s: float) -> dict:
    started_at = time.time()
    result = testbench_sessions.send(session_id, TestbenchCommand(
        host="", port=0,
        device="spec2code",
        operation=operation,
        command_id=_next_command_id(),
        device_index=controller_index,
        # controller_id (string) tel'e ULASMAZ; kopru cArrRegister'i denetleyici
        # tablosundan uiCihazIndeks ile cozer. Burada yalniz trafik/gunluk
        # okunurlugu icin tasinir.
        register=controller_id,
        address=channel,
        length=mask,
        value=value,
        timeout_s=timeout_s,
    ))
    parsed = result.parsed
    if parsed.get("ok") != "1":
        raise GpioError(f"{operation}: {parsed.get('message', 'yanit yok')}")
    return {
        "controller_id": controller_id,
        "op": operation,
        "channel": channel,
        "mask": mask if mask else _U32_MAX,
        "value": int(str(parsed.get("value", "0x0")), 16),
        "data": parsed.get("data", ""),
        "message": parsed.get("message", ""),
        "taken_at": started_at,
        "duration_ms": int((time.time() - started_at) * 1000),
    }


def read_channel(session_id: str, controller_id: str, *,
                 controller_index: int = _NO_CONTROLLER,
                 channel: int = 1, mask: int = 0, timeout_s: float = 5.0) -> dict:
    """Kanalin maskelenmis 32-bit degerini oku (yon DEGISTIRILMEZ)."""
    _check(channel, mask, None)
    return _run(session_id, "gpio_read", controller_id, controller_index,
                channel=channel, mask=mask, value=None, timeout_s=timeout_s)


def write_channel(session_id: str, controller_id: str, *,
                  controller_index: int = _NO_CONTROLLER,
                  channel: int = 1, value: int = 0, mask: int = 0,
                  timeout_s: float = 5.0) -> dict:
    """Maskelenen pinleri CIKIS yapip degeri oku-degistir-yaz ile sur."""
    _check(channel, mask, value)
    return _run(session_id, "gpio_write", controller_id, controller_index,
                channel=channel, mask=mask, value=value, timeout_s=timeout_s)
