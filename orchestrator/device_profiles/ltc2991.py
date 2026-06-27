"""LTC2991 board-aware configuration profile."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

PAIR_KEYS = ("v1_v2", "v3_v4", "v5_v6", "v7_v8")
PAIR_LABELS = {
    "v1_v2": "V1/V2",
    "v3_v4": "V3/V4",
    "v5_v6": "V5/V6",
    "v7_v8": "V7/V8",
}
PAIR_ENABLE_BITS = {
    "v1_v2": 4,
    "v3_v4": 5,
    "v5_v6": 6,
    "v7_v8": 7,
}
PAIR_CONTROL_REGS = {
    "v1_v2": ("CONTROL_V1V4", 0),
    "v3_v4": ("CONTROL_V1V4", 4),
    "v5_v6": ("CONTROL_V5V8", 0),
    "v7_v8": ("CONTROL_V5V8", 4),
}
MODE_CONTROL_BITS = {
    "disabled": 0x0,
    "single_ended_voltage": 0x0,
    "differential_voltage": 0x1,
    "current_shunt": 0x1,
    "remote_temperature": 0x2,
}
MODE_LABELS = {
    "disabled": "disabled",
    "single_ended_voltage": "single-ended voltage",
    "differential_voltage": "differential voltage",
    "current_shunt": "current via shunt",
    "remote_temperature": "remote temperature",
}


def default_config() -> dict[str, Any]:
    return {
        "pairs": {
            key: {"mode": "single_ended_voltage", "shunt_milliohm": None}
            for key in PAIR_KEYS
        },
        "internal_temperature": True,
        "vcc_read": False,
    }


def normalize_config(raw: Any) -> dict[str, Any]:
    config = default_config()
    if not isinstance(raw, dict):
        return config

    pairs = raw.get("pairs")
    if isinstance(pairs, dict):
        for key in PAIR_KEYS:
            item = pairs.get(key)
            if not isinstance(item, dict):
                continue
            mode = str(item.get("mode", config["pairs"][key]["mode"]))
            if mode in MODE_CONTROL_BITS:
                config["pairs"][key]["mode"] = mode
            if "shunt_milliohm" in item:
                config["pairs"][key]["shunt_milliohm"] = _number_or_none(item.get("shunt_milliohm"))

    if "internal_temperature" in raw:
        config["internal_temperature"] = bool(raw.get("internal_temperature"))
    if "vcc_read" in raw:
        config["vcc_read"] = bool(raw.get("vcc_read"))
    return config


def validate_config(raw: Any) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if raw is None:
        return issues
    if not isinstance(raw, dict):
        return [_issue("error", "config", "LTC2991 config must be an object")]

    pairs = raw.get("pairs")
    if pairs is not None and not isinstance(pairs, dict):
        issues.append(_issue("error", "config/pairs", "LTC2991 pairs must be an object"))
        return issues

    for key, item in (pairs or {}).items():
        pair_path = f"config/pairs/{key}"
        if key not in PAIR_KEYS:
            issues.append(_issue("warning", pair_path, f"unknown LTC2991 input pair '{key}'"))
            continue
        if not isinstance(item, dict):
            issues.append(_issue("error", pair_path, "pair config must be an object"))
            continue
        mode = item.get("mode")
        if mode not in MODE_CONTROL_BITS:
            issues.append(_issue("error", f"{pair_path}/mode", f"unsupported LTC2991 mode '{mode}'"))
            continue
        shunt = _number_or_none(item.get("shunt_milliohm"))
        if mode == "current_shunt" and (shunt is None or shunt <= 0):
            issues.append(_issue("error", f"{pair_path}/shunt_milliohm",
                                 "current measurement requires a positive shunt_milliohm value"))
        elif mode != "current_shunt" and shunt not in (None, 0):
            issues.append(_issue("warning", f"{pair_path}/shunt_milliohm",
                                 "shunt_milliohm is only used when mode is current_shunt"))

    config = normalize_config(raw)
    enabled_pairs = [
        key for key in PAIR_KEYS
        if config["pairs"][key]["mode"] != "disabled"
    ]
    if not enabled_pairs and not config["internal_temperature"] and not config["vcc_read"]:
        issues.append(_issue(
            "warning",
            "config",
            "all LTC2991 measurements are disabled; device_init will only write disabled controls",
        ))

    return issues


def i2c_init_writes(raw: Any) -> list[dict[str, Any]]:
    config = normalize_config(raw)
    enable = 0
    controls = {
        "CONTROL_V1V4": 0,
        "CONTROL_V5V8": 0,
    }
    notes = {
        "CONTROL_V1V4": [],
        "CONTROL_V5V8": [],
    }

    if config["internal_temperature"] or config["vcc_read"]:
        enable |= 0x08

    for key in PAIR_KEYS:
        pair = config["pairs"][key]
        mode = pair["mode"]
        if mode != "disabled":
            enable |= 1 << PAIR_ENABLE_BITS[key]
        reg, shift = PAIR_CONTROL_REGS[key]
        controls[reg] |= MODE_CONTROL_BITS[mode] << shift
        notes[reg].append(f"{PAIR_LABELS[key]} {MODE_LABELS[mode]}")

    writes = [
        {
            "reg": "STATUS_HIGH",
            "value": enable,
            "note": "channel enable bits",
        },
        {
            "reg": "CONTROL_V1V4",
            "value": controls["CONTROL_V1V4"],
            "note": "; ".join(notes["CONTROL_V1V4"]),
        },
        {
            "reg": "CONTROL_V5V8",
            "value": controls["CONTROL_V5V8"],
            "note": "; ".join(notes["CONTROL_V5V8"]),
        },
    ]
    return deepcopy(writes)


def _issue(severity: str, path: str, message: str) -> dict[str, str]:
    return {"severity": severity, "path": path, "message": message}


def _number_or_none(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
