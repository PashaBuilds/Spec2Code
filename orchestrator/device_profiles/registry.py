"""Device profile dispatch.

The orchestrator stays generic: it asks this registry whether a part has extra
board-aware behavior. Unsupported parts fall back to descriptor-only generation.
"""

from __future__ import annotations

from typing import Any

from orchestrator.device_profiles import ltc2991


_PROFILES = {
    "LTC2991": ltc2991,
}


def _profile(device_or_part: dict[str, Any] | str):
    part = device_or_part if isinstance(device_or_part, str) else device_or_part.get("part", "")
    return _PROFILES.get(str(part).upper())


def default_config(part: str) -> dict[str, Any] | None:
    profile = _profile(part)
    if profile is None:
        return None
    return profile.default_config()


def normalize_config(device: dict[str, Any]) -> dict[str, Any] | None:
    profile = _profile(device)
    if profile is None:
        return None
    return profile.normalize_config(device.get("config"))


def validate_config(device: dict[str, Any]) -> list[dict[str, str]]:
    profile = _profile(device)
    if profile is None:
        return []
    return profile.validate_config(device.get("config"))


def i2c_init_writes(device: dict[str, Any]) -> list[dict[str, Any]]:
    profile = _profile(device)
    if profile is None:
        return []
    return profile.i2c_init_writes(device.get("config"))

