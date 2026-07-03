"""xparameters.h parser (Brief 7).

Extracts a controller inventory from a Vivado/Vitis ``xparameters.h``. Recognizes the
two common Xilinx naming conventions:

  * driver-indexed PS drivers:  ``XPAR_XIICPS_0_BASEADDR``           (hardened, PS zone)
  * AXI / soft IP in the PL:     ``XPAR_AXI_IIC_0_BASEADDR``          (soft, PL zone)

Each ``*_BASEADDR`` macro is a controller candidate. A candidate is treated as a real
*peripheral* (vs. a memory region like DDR/OCM, which also has BASEADDR) only if it has a
companion ``*_DEVICE_ID`` macro - the discriminator Xilinx headers give us for free.

The parser is pure (text in, dicts out). Zone assignment is delegated to the platform
topology model (Brief 9.2) so the same parser serves all four platforms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# --- macro scanning ---------------------------------------------------------------------

# `#define  NAME  VALUE   [/* comment */]`
_DEFINE_RE = re.compile(r"^\s*#\s*define\s+(?P<name>[A-Za-z_]\w*)\s+(?P<value>.+?)\s*$", re.MULTILINE)
# split `XPAR_<middle>_<idx>` out of a base key like `XPAR_XIICPS_0`
_KEY_RE = re.compile(r"^XPAR_(?P<mid>.+)_(?P<idx>\d+)$")
_BASEADDR_SUFFIX = "_BASEADDR"


def _clean_value(raw: str) -> str:
    """Strip trailing comments and integer suffixes (U/L/UL...) from a macro value."""
    raw = re.split(r"/\*|//", raw, maxsplit=1)[0].strip()
    return re.sub(r"[uUlL]+$", "", raw)


def _to_int(raw: str) -> Optional[int]:
    try:
        return int(_clean_value(raw), 0)
    except (ValueError, TypeError):
        return None


def _resolve_int(raw: str | None, defines: dict[str, str], depth: int = 0) -> Optional[int]:
    """Resolve numeric macro values, including one macro aliasing another."""
    if raw is None or depth > 8:
        return None
    value = _to_int(raw)
    if value is not None:
        return value
    key = _clean_value(raw)
    if key == raw and key not in defines:
        return None
    return _resolve_int(defines.get(key), defines, depth + 1)


# --- driver classification --------------------------------------------------------------
# Ordered rules: first regex (searched against the captured middle name) wins.
# More specific PS-hardened driver names are listed before the looser PL/AXI tokens so that
# e.g. "XIICPS" matches i2c/PS before the PL "XIIC" rule can fire.
# Each rule -> (type, family, canonical BSP driver).

_RULES: list[tuple[re.Pattern, str, str, str]] = [
    # --- PS hardened drivers (driver-indexed) ---
    # Versal XUARTPSV must precede XUARTPS: the looser pattern would
    # otherwise claim it and assign the wrong (XUartPs) driver.
    (re.compile(r"XUARTPSV"), "uart", "ps", "XUartPsv"),
    (re.compile(r"XQSPIPSU"), "qspi", "ps", "XQspiPsu"),
    (re.compile(r"XQSPIPS"), "qspi", "ps", "XQspiPs"),
    (re.compile(r"XOSPIPSV"), "qspi", "ps", "XOspiPsv"),
    (re.compile(r"XIICPS"), "i2c", "ps", "XIicPs"),
    (re.compile(r"XSPIPS"), "spi", "ps", "XSpiPs"),
    (re.compile(r"XGPIOPS"), "gpio", "ps", "XGpioPs"),
    (re.compile(r"XUARTPS"), "uart", "ps", "XUartPs"),
    (re.compile(r"XCANFD"), "can", "ps", "XCanFd"),
    (re.compile(r"XCANPS"), "can", "ps", "XCanPs"),
    (re.compile(r"XEMACPS"), "eth", "ps", "XEmacPs"),
    (re.compile(r"XSDPS"), "sdio", "ps", "XSdPs"),
    # --- PS hardened (canonical PS7_/PSU_/PSV_ instance names) ---
    (re.compile(r"^PSU_.*QSPI"), "qspi", "ps", "XQspiPsu"),
    (re.compile(r"^PS7_.*QSPI"), "qspi", "ps", "XQspiPs"),
    (re.compile(r"^PSV_.*OSPI"), "qspi", "ps", "XOspiPsv"),
    (re.compile(r"^PSV_.*QSPI"), "qspi", "ps", "XQspiPsu"),
    (re.compile(r"^(PS7|PSU|PSV)_.*(I2C|IIC)"), "i2c", "ps", "XIicPs"),
    (re.compile(r"^(PS7|PSU)_.*SPI"), "spi", "ps", "XSpiPs"),
    (re.compile(r"^(PS7|PSU|PSV)_.*GPIO"), "gpio", "ps", "XGpioPs"),
    (re.compile(r"^PSV_.*UART"), "uart", "ps", "XUartPsv"),
    (re.compile(r"^(PS7|PSU)_.*UART"), "uart", "ps", "XUartPs"),
    (re.compile(r"^PSV_.*CANFD"), "can", "ps", "XCanFd"),
    (re.compile(r"^(PS7|PSU)_.*CAN"), "can", "ps", "XCanPs"),
    (re.compile(r"^(PS7|PSU|PSV)_.*(ENET|ETHERNET|GEM)"), "eth", "ps", "XEmacPs"),
    (re.compile(r"^(PS7|PSU|PSV)_.*SD"), "sdio", "ps", "XSdPs"),
    # --- PL / AXI soft IP ---
    (re.compile(r"QUAD_SPI"), "spi", "pl", "XSpi"),
    (re.compile(r"AXI_IIC|^XIIC"), "i2c", "pl", "XIic"),
    (re.compile(r"AXI_SPI|^XSPI"), "spi", "pl", "XSpi"),
    (re.compile(r"AXI_GPIO|^XGPIO"), "gpio", "pl", "XGpio"),
    (re.compile(r"UARTLITE"), "uart", "pl", "XUartLite"),
    (re.compile(r"AXI_DMA|AXIDMA"), "dma", "pl", "XAxiDma"),
]

# Recognized but non-attachable peripherals - skipped silently (kept out of `unmatched`).
_IGNORE_RE = re.compile(
    r"TTC|SCUGIC|SCUTIMER|SCUWDT|^WDT|DEVCFG|XADC|SYSMON|IPI|CSUDMA|RTC|DDRC|DEVC"
)


@dataclass
class Controller:
    id: str
    type: str
    instance: str
    base_address: str
    device_id: Optional[object]
    driver: str
    zone: str
    source: str = "xparameters"

    def to_spec(self) -> dict:
        out = {
            "id": self.id,
            "type": self.type,
            "instance": self.instance,
            "base_address": self.base_address,
            "driver": self.driver,
            "source": self.source,
            "zone": self.zone,
        }
        if self.device_id is not None:
            out["device_id"] = self.device_id
        return out


@dataclass
class ParseResult:
    controllers: list[dict] = field(default_factory=list)
    unmatched: list[dict] = field(default_factory=list)


@dataclass
class _Candidate:
    middle: str
    idx: str
    type: str
    driver: str
    zone: str
    base_address: str
    base_addr_int: Optional[int]
    instance: str
    device_id: Optional[object]


_DRIVER_ALIAS_RE = re.compile(
    r"^(XQSPIPSU|XQSPIPS|XOSPIPSV|XIICPS|XSPIPS|XGPIOPS|XUARTPSV|XUARTPS|XCANFD|XCANPS|XEMACPS|XSDPS|XIIC|XSPI|XGPIO)(?:_|$)"
)


def _classify(middle: str) -> Optional[tuple[str, str, str]]:
    for pattern, ctype, family, driver in _RULES:
        if pattern.search(middle):
            return ctype, family, driver
    return None


def _zone_for(family: str, platform_model: Optional[dict]) -> str:
    if platform_model:
        mapping = platform_model.get("family_zone") or {}
        return mapping.get(family, platform_model.get("default_zone", family))
    # Sensible default when no platform model: ps-family -> ps, pl-family -> pl.
    return family


def _candidate_preference(candidate: _Candidate) -> tuple[int, int, str]:
    """Prefer BSP driver aliases over peripheral aliases for generated C compatibility."""
    driver_alias_rank = 0 if _DRIVER_ALIAS_RE.search(candidate.middle) else 1
    unresolved_device_id_rank = 1 if candidate.device_id is None else 0
    return driver_alias_rank, unresolved_device_id_rank, candidate.instance


def parse_xparameters(text: str, platform_model: Optional[dict] = None) -> ParseResult:
    """Parse *text* (xparameters.h contents) into a controller inventory.

    Returns a :class:`ParseResult` with ``controllers`` (project.spec format) and
    ``unmatched`` (controller-like macros whose driver we don't recognize - UI can show).
    """
    defines: dict[str, str] = {m.group("name"): m.group("value") for m in _DEFINE_RE.finditer(text)}
    result = ParseResult()
    candidates: list[_Candidate] = []

    for name, raw_value in defines.items():
        if not name.endswith(_BASEADDR_SUFFIX):
            continue
        base_key = name[: -len(_BASEADDR_SUFFIX)]  # e.g. XPAR_XIICPS_0
        key_match = _KEY_RE.match(base_key)
        if not key_match:
            continue
        middle, idx = key_match.group("mid"), key_match.group("idx")

        has_device_id = f"{base_key}_DEVICE_ID" in defines
        # Memory regions (DDR/OCM/RAM) have BASEADDR but no DEVICE_ID -> not a peripheral.
        if not has_device_id:
            continue

        addr_int = _resolve_int(raw_value, defines)
        base_address = f"0x{addr_int:08X}" if addr_int is not None else _clean_value(raw_value)
        device_id_raw = defines.get(f"{base_key}_DEVICE_ID") if has_device_id else None
        device_id_val: Optional[object] = _resolve_int(device_id_raw, defines)
        if device_id_val is None and device_id_raw is not None:
            device_id_val = _clean_value(device_id_raw)

        if _IGNORE_RE.search(middle):
            continue

        classified = _classify(middle)
        if classified is None:
            result.unmatched.append(
                {"instance": base_key, "base_address": base_address, "reason": "unknown_driver"}
            )
            continue

        ctype, family, driver = classified
        zone = _zone_for(family, platform_model)
        candidates.append(
            _Candidate(
                middle=middle,
                idx=idx,
                type=ctype,
                driver=driver,
                zone=zone,
                base_address=base_address,
                base_addr_int=addr_int,
                instance=base_key,
                device_id=device_id_val,
            )
        )

    # Vitis often emits both physical peripheral names and BSP-driver aliases for the
    # same controller, e.g. XPAR_PSU_I2C_0 and XPAR_XIICPS_0 at the same BASEADDR.
    # Keep one logical controller per address/type/driver and prefer the BSP alias,
    # because generated C uses <instance>_DEVICE_ID in LookupConfig calls.
    deduped: dict[tuple[str, str, str, str], _Candidate] = {}
    for candidate in candidates:
        addr_key = (
            f"0x{candidate.base_addr_int:X}"
            if candidate.base_addr_int is not None
            else candidate.base_address.upper()
        )
        key = (candidate.zone, candidate.type, candidate.driver, addr_key)
        previous = deduped.get(key)
        if previous is None or _candidate_preference(candidate) < _candidate_preference(previous):
            deduped[key] = candidate

    seen_ids: set[str] = set()
    for candidate in sorted(deduped.values(), key=lambda c: (c.zone, c.type, c.instance)):
        ctrl_id = f"{candidate.zone}_{candidate.type}_{candidate.idx}"
        # Guarantee uniqueness for real same-type controllers whose macro indexes collide.
        unique_id, bump = ctrl_id, 0
        while unique_id in seen_ids:
            bump += 1
            unique_id = f"{ctrl_id}_{bump}"
        seen_ids.add(unique_id)

        result.controllers.append(
            Controller(
                id=unique_id,
                type=candidate.type,
                instance=candidate.instance,
                base_address=candidate.base_address,
                device_id=candidate.device_id,
                driver=candidate.driver,
                zone=candidate.zone,
            ).to_spec()
        )

    # Stable, human-friendly ordering: by zone then type then instance.
    result.controllers.sort(key=lambda c: (c["zone"], c["type"], c["instance"]))
    result.unmatched.sort(key=lambda c: c["instance"])
    return result
