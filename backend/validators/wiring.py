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
    # Kullanıcı descriptor'ları (user_descriptors/) yerleşiklerden önceliklidir
    # — codegen çözümlemesiyle aynı kural (tek doğruluk kaynağı codegen'de).
    from orchestrator.codegen import resolve_descriptor_path

    return resolve_descriptor_path(ref_or_part, _ROOT)


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
    #: (controller_id, gpio channel) -> [(pin mask, owner)] - overlapping masks
    #: on one channel mean two devices drive the same physical line.
    seen_gpio: dict[tuple[str, int], list[tuple[int, str]]] = {}

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

    from orchestrator import boards as boards_mod

    board_list = spec.get("boards") or []
    board_ids = {str(b.get("id")) for b in board_list}
    if board_list:
        mains = [b for b in board_list if str(b.get("role")) == "main"]
        if len(mains) != 1:
            add("error", "/boards",
                f"tam olarak bir 'main' kart olmali (bulunan: {len(mains)})")
        try:
            boards_mod.assert_unique_identifiers(board_list)
        except ValueError as exc:
            add("error", "/boards", str(exc))
        seen_ids: set[str] = set()
        for index, board in enumerate(board_list):
            bid = str(board.get("id", ""))
            if bid in seen_ids:
                add("error", f"/boards/{index}/id", f"kart kimligi tekrar ediyor: {bid}")
            seen_ids.add(bid)

    controller_ids = {str(c.get("id")) for c in spec.get("controllers", [])}
    mux_by_id = {str(m.get("id")): m for m in spec.get("muxes", [])}
    for index, connector in enumerate(spec.get("connectors", []) or []):
        path = f"/connectors/{index}"
        for side in ("from_board", "to_board"):
            value = str(connector.get(side, ""))
            if value not in board_ids:
                add("error", f"{path}/{side}", f"tanimsiz kart: {value}")
        if connector.get("from_board") == connector.get("to_board"):
            add("error", f"{path}/to_board", "konnektorun iki ucu ayni kart olamaz")
        bus = connector.get("bus") or {}
        if str(bus.get("controller_id", "")) not in controller_ids:
            add("error", f"{path}/bus/controller_id",
                f"tanimsiz denetleyici: {bus.get('controller_id')}")
        via = bus.get("via_mux")
        if via:
            mux = mux_by_id.get(str(via.get("mux_id", "")))
            if mux is None:
                add("error", f"{path}/bus/via_mux/mux_id",
                    f"tanimsiz switch: {via.get('mux_id')}")
            else:
                channels = _int_value(mux.get("channels")) or 0
                channel = _int_value(via.get("channel"))
                if channel is None or not (0 <= channel < channels):
                    add("error", f"{path}/bus/via_mux/channel",
                        f"kanal 0..{channels - 1} araliginda olmali (verilen: {via.get('channel')})")

    # Sanal cihaz yalniz simulatoru olan transportlarda: I2C register cihazi ve SPI
    # TICS-register cihazi. GPIO hat, komut tabanli flash ve EEPROM icin simulator yok.
    for index, device in enumerate(spec.get("devices", [])):
        if not device.get("simulate"):
            continue
        try:
            from orchestrator import codegen as _codegen, tics as _tics
            descriptor = _codegen.make_descriptor_loader()(device.get("descriptor_ref") or device.get("part", ""))
        except Exception:  # noqa: BLE001 - descriptor cozulemezse baska kural hata verir
            continue
        transport = str((descriptor.get("transport") or {}).get("type", ""))
        supported = (transport == "i2c" and not descriptor.get("memory")) or (
            transport == "spi" and _tics.has_tics_register_model(descriptor))
        if not supported:
            add("error", f"/devices/{index}/simulate",
                f"{device.get('part')} icin simulator yok (yalniz I2C register ve SPI TICS-register "
                "cihazlari sanal olabilir); isareti kaldirin")

    # Cihaz/mux board_id'leri var olan karti gostermeli.
    if board_list:
        for index, device in enumerate(spec.get("devices", [])):
            bid = device.get("board_id")
            if bid is not None and str(bid) not in board_ids:
                add("error", f"/devices/{index}/board_id", f"tanimsiz kart: {bid}")
        for index, mux in enumerate(spec.get("muxes", [])):
            bid = mux.get("board_id")
            if bid is not None and str(bid) not in board_ids:
                add("error", f"/muxes/{index}/board_id", f"tanimsiz kart: {bid}")
        # Ana kart disindaki bir kartta cihaz var ama o hatti belgeleyen
        # konnektor yoksa UYARI (hata degil — model calisir, dokuman eksik).
        documented = {str(c.get("to_board")) for c in (spec.get("connectors") or [])}
        main_id = boards_mod.main_board_id(spec)
        populated = {boards_mod.board_id_of(d) for d in spec.get("devices", [])}
        for bid in sorted(populated - {main_id} - documented):
            add("warning", "/connectors",
                f"'{bid}' kartinda cihaz var ama baglantisini belgeleyen konnektor yok")

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
        elif transport == "gpio":
            if controller_type != "gpio":
                add("error", f"{path}/attach/controller_id", f"{owner}: GPIO descriptor is attached to {controller_type}")
            channel = _int_value(attach.get("gpio_channel", 1))
            if channel not in (1, 2):
                add("error", f"{path}/attach/gpio_channel",
                    f"{owner}: gpio_channel must be 1 or 2 (AXI GPIO has two channels)")
                channel = None
            mask = _int_value(attach.get("gpio_pin_mask", 0xFFFFFFFF))
            if mask is None or not 0 < mask <= 0xFFFFFFFF:
                add("error", f"{path}/attach/gpio_pin_mask",
                    f"{owner}: gpio_pin_mask must be a non-zero 32-bit mask")
            elif channel is not None:
                # Ayni cekirdegin ayni kanalinda iki cihaz AYNI pini surerse
                # biri digerini ezer - I2C adres / SPI CS catismasinin ikizi.
                key = (attach["controller_id"], channel)
                for previous_mask, previous_owner in seen_gpio.get(key, []):
                    overlap = previous_mask & mask
                    if overlap:
                        add("error", f"{path}/attach/gpio_pin_mask",
                            f"{owner}: GPIO pins 0x{overlap:X} on channel {channel} conflict with {previous_owner}")
                seen_gpio.setdefault(key, []).append((mask, owner))
            if _has_manual_init_sequence(device):
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
    try:
        words = tics.normalize_words(config)
    except ValueError as exc:
        add("error", seq_path, f"{owner}: {exc}")
        return
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
