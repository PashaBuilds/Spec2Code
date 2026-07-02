"""Bulk register snapshot over a live test bench session.

One HTTP call reads a device's whole register map through the existing
TCP/serial session (one S2C `register_read` per register, sequential on
the session lock). The frontend diffs snapshots against descriptor reset
values or earlier snapshots.
"""

from __future__ import annotations

import time

from backend.testbench import TestbenchCommand, TestbenchSessionError, testbench_sessions


def snapshot_registers(
    session_id: str,
    device_id: str,
    registers: list[dict],
    *,
    timeout_s: float = 5.0,
) -> dict:
    started_at = time.time()
    entries: list[dict] = []
    for index, register in enumerate(registers):
        name = str(register.get("name", ""))
        offset = register.get("offset")
        entry = {
            "name": name,
            "offset": offset,
            "ok": False,
            "value": "",
            "error": "",
        }
        try:
            result = testbench_sessions.send(session_id, TestbenchCommand(
                host="", port=0,
                device=device_id,
                operation="register_read",
                command_id=index + 1,
                register=name,
                register_address=int(offset) if offset is not None else None,
                timeout_s=timeout_s,
            ))
            parsed = result.parsed
            entry["ok"] = parsed.get("ok") == "1"
            entry["value"] = parsed.get("value", "")
            if not entry["ok"]:
                entry["error"] = parsed.get("message", "") or "cihaz hata döndürdü"
        except (TestbenchSessionError, OSError) as exc:
            entry["error"] = str(exc)
            entries.append(entry)
            # A dead session fails all remaining reads the same way.
            for later in registers[index + 1:]:
                entries.append({
                    "name": str(later.get("name", "")),
                    "offset": later.get("offset"),
                    "ok": False, "value": "",
                    "error": "atlandı: bağlantı koptu",
                })
            break
        entries.append(entry)

    read_ok = sum(1 for item in entries if item["ok"])
    return {
        "device_id": device_id,
        "taken_at": started_at,
        "duration_ms": int((time.time() - started_at) * 1000),
        "total": len(entries),
        "read_ok": read_ok,
        "registers": entries,
    }
