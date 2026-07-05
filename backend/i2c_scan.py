"""I2C hat taraması orkestrasyonu.

Ajan iki basit global op sunar: `i2c_scan` (o anki hattı 0x08..0x77
yoklar, ACK veren adresleri data alanında döndürür) ve `i2c_mux_set`
(TCA9548A tarzı switch kontrol baytı: 0x00 = kapat, 1<<kanal = seç).
Bu modül tam haritayı çıkarır: önce TÜM switch'ler kapatılıp doğrudan
hat taranır (switch arkası cihazlar doğrudan hatta görünmesin), sonra
her switch'in her kanalı sırayla seçilip taranır ve switch kapatılır.
Sonuç pozisyon pozisyon (doğrudan / switch+kanal) adres listeleridir —
cihaz kimliği ÇIKARILMAZ, yalnız "bu adreste cevap veren var" bilgisi.
"""

from __future__ import annotations

import time

from backend.testbench import TestbenchCommand, testbench_sessions

#: Tarama komutları UI komut sayaçlarıyla çakışmasın diye ayrı bant.
_SCAN_COMMAND_ID_BASE = 7000


class I2cScanError(RuntimeError):
    """Tarama sırasında ajan hatası (hangi adımda olduğu mesajdadır)."""


def _send(session_id: str, operation: str, controller_id: str, *, command_id: int,
          address: int | None = None, value: int | None = None,
          timeout_s: float) -> dict:
    result = testbench_sessions.send(session_id, TestbenchCommand(
        host="", port=0,
        device="spec2code",
        operation=operation,
        command_id=command_id,
        register=controller_id,
        address=address,
        value=value,
        timeout_s=timeout_s,
    ))
    return result.parsed


def _addresses_from_data(data_hex: str) -> list[int]:
    clean = "".join(ch for ch in (data_hex or "") if ch in "0123456789abcdefABCDEF")
    return [int(clean[i:i + 2], 16) for i in range(0, len(clean) - 1, 2)]


def scan_bus(session_id: str, controller_id: str, muxes: list[dict], *,
             timeout_s: float = 10.0) -> dict:
    started_at = time.time()
    command_id = _SCAN_COMMAND_ID_BASE

    def next_id() -> int:
        nonlocal command_id
        command_id += 1
        return command_id

    def mux_set(mux: dict, control: int, step: str) -> None:
        parsed = _send(session_id, "i2c_mux_set", controller_id,
                       command_id=next_id(), address=int(mux["address"]),
                       value=control, timeout_s=timeout_s)
        if parsed.get("ok") != "1":
            raise I2cScanError(
                f"{step}: switch {mux.get('id', hex(int(mux['address'])))} kontrol baytı yazılamadı "
                f"({parsed.get('message', 'yanıt yok')})")

    def scan_once(step: str) -> list[int]:
        parsed = _send(session_id, "i2c_scan", controller_id,
                       command_id=next_id(), timeout_s=timeout_s)
        if parsed.get("ok") != "1":
            raise I2cScanError(f"{step}: tarama başarısız ({parsed.get('message', 'yanıt yok')})")
        return _addresses_from_data(parsed.get("data", ""))

    mux_addresses = {int(m["address"]) for m in muxes}

    # 1) Switch arkası adresler doğrudan hatta sızmasın: hepsini kapat.
    for mux in muxes:
        mux_set(mux, 0x00, "hazırlık")

    direct = scan_once("doğrudan hat")

    direct_set = set(direct)

    mux_results: list[dict] = []
    for mux in muxes:
        channels: list[dict] = []
        for channel in range(int(mux.get("channels", 8))):
            mux_set(mux, 1 << channel, f"kanal {channel} seçimi")
            found = scan_once(f"{mux.get('id', '')} kanal {channel}")
            channels.append({
                "channel": channel,
                # Kanal açıkken doğrudan hattaki cihazlar ve switch'in kendisi
                # de ACK'lar; kanal içeriği = fark kümesidir. (Doğrudan hatta
                # da bulunan bir adresin arkasındaki kopya ayırt edilemez —
                # fiziksel olarak aynı anda görünürler.)
                "addresses": sorted(set(found) - direct_set - mux_addresses),
            })
        mux_set(mux, 0x00, "kapatma")
        mux_results.append({
            "id": mux.get("id", ""),
            "part": mux.get("part", ""),
            "address": int(mux["address"]),
            "channels": channels,
        })

    return {
        "controller_id": controller_id,
        "taken_at": started_at,
        "duration_ms": int((time.time() - started_at) * 1000),
        "range": [0x08, 0x77],
        "direct_addresses": sorted(a for a in set(direct) if a not in mux_addresses),
        "switch_addresses": sorted(a for a in set(direct) if a in mux_addresses),
        "muxes": mux_results,
    }
