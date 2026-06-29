"""Project-spec wiring validation before code generation.

The JSON schema checks object shape. This module checks relationships between controllers,
muxes, devices, addresses, descriptors, and transport types.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from orchestrator.device_profiles import registry as device_profiles
from orchestrator import tics

_ROOT = Path(__file__).resolve().parent.parent.parent
_DESCRIPTORS = _ROOT / "descriptors"


def _issue(severity: str, path: str, message: str) -> dict[str, str]:
    return {"severity": severity, "path": path, "message": message}


def _module_of(part: str) -> str:
    return re.sub(r"[^a-z0-9]", "", part.lower())


def _descriptor_path(ref_or_part: str) -> Path:
    if ref_or_part.endswith((".yaml", ".yml")) or "/" in ref_or_part or "\\" in ref_or_part:
        return _ROOT / ref_or_part
    return _DESCRIPTORS / f"{_module_of(ref_or_part)}.yaml"


def _load_descriptor(ref_or_part: str) -> dict[str, Any] | None:
    path = _descriptor_path(ref_or_part)
    if not path.is_file():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _hex_int(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    try:
        return int(value, 16)
    except ValueError:
        return None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value, 0)
        except ValueError:
            return None
    return None


def validate_wiring(spec: dict) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    controllers = {c.get("id"): c for c in spec.get("controllers", [])}
    muxes = {m.get("id"): m for m in spec.get("muxes", [])}
    seen_i2c: dict[tuple[tuple[str, str], int], str] = {}
    seen_spi: dict[tuple[str, int], str] = {}

    def add(severity: str, path: str, message: str) -> None:
        target = errors if severity == "error" else warnings
        target.append(_issue(severity, path, message))

    def i2c_addr(path: str, owner: str, value: Any) -> int | None:
        addr = _hex_int(value)
        if addr is None:
            add("error", path, f"{owner}: I2C address must be a hex string such as 0x48")
            return None
        if not 0 <= addr <= 0x7F:
            add("error", path, f"{owner}: I2C address 0x{addr:X} is outside 7-bit range")
            return None
        return addr

    def record_i2c(bus: tuple[str, str], addr: int, owner: str, path: str) -> None:
        key = (bus, addr)
        previous = seen_i2c.get(key)
        if previous:
            bus_label = f"{bus[0]}:{bus[1]}"
            add("error", path, f"{owner}: I2C address 0x{addr:02X} conflicts with {previous} on {bus_label}")
            return
        seen_i2c[key] = owner

    for idx, mux in enumerate(spec.get("muxes", [])):
        owner = f"mux {mux.get('id') or idx}"
        path = f"muxes/{idx}"
        controller = controllers.get(mux.get("controller_id"))
        if controller is None:
            add("error", f"{path}/controller_id", f"{owner}: referenced controller does not exist")
            continue
        if controller.get("type") != "i2c":
            add("error", f"{path}/controller_id", f"{owner}: muxes must be attached to an I2C controller")
        channels = mux.get("channels")
        if not isinstance(channels, int) or not 1 <= channels <= 8:
            add("error", f"{path}/channels", f"{owner}: channels must be between 1 and 8")
        desc = _load_descriptor(mux.get("part", ""))
        if desc is None:
            add("error", f"{path}/part", f"{owner}: descriptor was not found")
        elif desc.get("transport", {}).get("type") != "i2c_mux":
            add("error", f"{path}/part", f"{owner}: descriptor transport is not i2c_mux")
        addr = i2c_addr(f"{path}/i2c_address", owner, mux.get("i2c_address"))
        if addr is not None:
            record_i2c(("controller", mux["controller_id"]), addr, owner, f"{path}/i2c_address")

    for idx, device in enumerate(spec.get("devices", [])):
        owner = f"device {device.get('id') or idx}"
        path = f"devices/{idx}"
        attach = device.get("attach", {})
        controller = controllers.get(attach.get("controller_id"))
        if controller is None:
            add("error", f"{path}/attach/controller_id", f"{owner}: referenced controller does not exist")
            continue

        desc_ref = device.get("descriptor_ref") or device.get("part", "")
        desc = _load_descriptor(desc_ref)
        if desc is None:
            add("error", f"{path}/part", f"{owner}: descriptor was not found")
            continue
        transport = desc.get("transport", {}).get("type")
        controller_type = controller.get("type")

        if transport == "i2c":
            if controller_type != "i2c":
                add("error", f"{path}/attach/controller_id", f"{owner}: I2C descriptor is attached to {controller_type}")
            addr = i2c_addr(f"{path}/attach/i2c_address", owner, attach.get("i2c_address"))
            via = attach.get("via_mux")
            if via:
                mux = muxes.get(via.get("mux_id"))
                if mux is None:
                    add("error", f"{path}/attach/via_mux/mux_id", f"{owner}: mux does not exist")
                elif mux.get("controller_id") != attach.get("controller_id"):
                    add("error", f"{path}/attach/via_mux/mux_id", f"{owner}: mux is on another controller")
                else:
                    channel = via.get("channel")
                    channels = mux.get("channels", 0)
                    if not isinstance(channel, int) or not 0 <= channel < channels:
                        add("error", f"{path}/attach/via_mux/channel", f"{owner}: mux channel is out of range")
                    elif addr is not None:
                        record_i2c(("mux", mux["id"], str(channel)), addr, owner, f"{path}/attach/i2c_address")
            elif addr is not None:
                record_i2c(("controller", attach["controller_id"]), addr, owner, f"{path}/attach/i2c_address")
            _validate_i2c_init_sequence(
                device=device,
                descriptor=desc,
                path=path,
                owner=owner,
                add=add,
            )
        elif transport == "spi":
            if controller_type not in {"spi", "qspi"}:
                add("error", f"{path}/attach/controller_id", f"{owner}: SPI descriptor is attached to {controller_type}")
            chip_select = attach.get("spi_chip_select")
            if not isinstance(chip_select, int) or chip_select < 0:
                add("error", f"{path}/attach/spi_chip_select", f"{owner}: SPI chip select must be a non-negative integer")
            else:
                key = (attach["controller_id"], chip_select)
                previous = seen_spi.get(key)
                if previous:
                    add("error", f"{path}/attach/spi_chip_select", f"{owner}: SPI CS{chip_select} conflicts with {previous}")
                seen_spi[key] = owner
            expected_width = desc.get("transport", {}).get("address_width")
            actual_width = attach.get("address_width")
            is_flash = str(device.get("part", "")).upper().startswith("MT25Q")
            if expected_width is not None and actual_width not in {None, expected_width}:
                severity = "error" if is_flash else "warning"
                add(severity, f"{path}/attach/address_width",
                    f"{owner}: address width {actual_width} differs from descriptor value {expected_width}")
            elif expected_width is not None and actual_width is None:
                add("warning", f"{path}/attach/address_width",
                    f"{owner}: address width is not set; descriptor value is {expected_width}")
            if tics.has_tics_register_model(desc):
                _validate_ticspro_registers(
                    device=device,
                    descriptor=desc,
                    path=path,
                    owner=owner,
                    add=add,
                )
            elif _has_manual_init_sequence(device):
                add("warning", f"{path}/config/init_sequence",
                    f"{owner}: manual register init sequence is only applied to I2C register devices")
        elif transport == "i2c_mux":
            add("error", f"{path}/part", f"{owner}: I2C mux parts must be added as muxes, not devices")
        else:
            add("error", f"{path}/part", f"{owner}: descriptor transport '{transport}' is not supported")

        declared_ops = {op.get("name") for op in desc.get("operations", [])}
        requested_ops = set(device.get("operations_requested") or [])
        unknown_ops = sorted(op for op in requested_ops if op not in declared_ops)
        if unknown_ops:
            add("warning", f"{path}/operations_requested",
                f"{owner}: requested operations are not in descriptor: {', '.join(unknown_ops)}")

        for issue in device_profiles.validate_config(device):
            severity = issue.get("severity", "error")
            rel = issue.get("path", "config")
            add(severity, f"{path}/{rel}", f"{owner}: {issue.get('message', 'invalid device config')}")

    return {"valid": not errors, "errors": errors, "warnings": warnings}


def _has_manual_init_sequence(device: dict[str, Any]) -> bool:
    config = device.get("config")
    return isinstance(config, dict) and bool(config.get("init_sequence"))


def _validate_i2c_init_sequence(
    *,
    device: dict[str, Any],
    descriptor: dict[str, Any],
    path: str,
    owner: str,
    add,
) -> None:
    config = device.get("config")
    if not isinstance(config, dict) or "init_sequence" not in config:
        return

    sequence = config.get("init_sequence")
    seq_path = f"{path}/config/init_sequence"
    if sequence in (None, []):
        return
    if not isinstance(sequence, list):
        add("error", seq_path, f"{owner}: init_sequence must be a list of register writes")
        return

    requested_ops = set(device.get("operations_requested") or [])
    if requested_ops and "device_init" not in requested_ops:
        add("warning", seq_path, f"{owner}: init_sequence is ignored unless device_init is selected")

    registers = {r.get("name"): r for r in descriptor.get("registers", [])}
    seen: set[str] = set()
    profile_regs = {w.get("reg") for w in device_profiles.i2c_init_writes(device)}
    for idx, item in enumerate(sequence):
        item_path = f"{seq_path}/{idx}"
        if not isinstance(item, dict):
            add("error", item_path, f"{owner}: init write must be an object")
            continue
        reg_name = item.get("reg")
        if not isinstance(reg_name, str):
            add("error", f"{item_path}/reg", f"{owner}: init write reg must be a register name")
            continue
        reg = registers.get(reg_name)
        if reg is None:
            add("error", f"{item_path}/reg", f"{owner}: unknown register '{reg_name}'")
            continue
        access = str(reg.get("access", "rw")).lower()
        if "w" not in access or "*" in access:
            add("error", f"{item_path}/reg", f"{owner}: register '{reg_name}' is not writable")
        if reg_name in seen:
            add("warning", f"{item_path}/reg", f"{owner}: register '{reg_name}' is written more than once")
        if reg_name in profile_regs:
            add("warning", f"{item_path}/reg",
                f"{owner}: register '{reg_name}' is also written by the device profile; later writes override earlier ones")
        seen.add(reg_name)

        value = _int_value(item.get("value"))
        width = int(reg.get("width", 8) or 8)
        if value is None:
            add("error", f"{item_path}/value", f"{owner}: init write value must be an integer or hex string")
        elif width <= 0 or width > 8:
            add("error", f"{item_path}/value", f"{owner}: init builder currently supports 8-bit registers only")
        elif not 0 <= value <= ((1 << width) - 1):
            add("error", f"{item_path}/value",
                f"{owner}: value 0x{value:X} does not fit in {width}-bit register '{reg_name}'")


def _validate_ticspro_registers(
    *,
    device: dict[str, Any],
    descriptor: dict[str, Any],
    path: str,
    owner: str,
    add,
) -> None:
    config = device.get("config")
    seq_key = "register_words" if isinstance(config, dict) and "register_words" in config else "ticspro_registers"
    seq_path = f"{path}/config/{seq_key}"
    words = tics.normalize_words(config)
    requested_ops = set(device.get("operations_requested") or [])
    if requested_ops and "device_init" not in requested_ops and words:
        add("warning", seq_path, f"{owner}: SPI register array is ignored unless device_init is selected")
    if not words:
        add("warning", seq_path, f"{owner}: no SPI register array is configured; generated init will only initialize SPI")
        return

    model = tics.register_model(descriptor)
    for issue in tics.validate_words(words, model):
        index, _, message = issue.partition(": ")
        add("error", f"{seq_path}/{index}", f"{owner}: {message}")

    rewrite_addr = model.get("rewrite_last_address")
    delay_ms = int(model.get("rewrite_last_address_after_ms", 0) or 0)
    if rewrite_addr is not None and delay_ms > 0:
        decoded = tics.decode_words(words, model)
        if not any(item.address == int(rewrite_addr) for item in decoded):
            add("warning", seq_path,
                f"{owner}: post-init rewrite after {delay_ms} ms is configured, but address 0x{int(rewrite_addr):X} is not present")
