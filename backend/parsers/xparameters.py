"""xparameters.h parser (Brief §7).

Extracts a controller inventory from a Vivado/Vitis ``xparameters.h``. Recognizes the
two common Xilinx naming conventions:

  * driver-indexed PS drivers:  ``XPAR_XIICPS_0_BASEADDR``           (hardened, PS zone)
  * AXI / soft IP in the PL:     ``XPAR_AXI_IIC_0_BASEADDR``          (soft, PL zone)

Each ``*_BASEADDR`` macro is a controller candidate. A candidate is treated as a real
*peripheral* (vs. a memory region like DDR/OCM, which also has BASEADDR) only if it has a
companion ``*_DEVICE_ID`` macro — the discriminator Xilinx headers give us for free.

The parser is pure (text in, dicts out). Zone assignment is delegated to the platform
topology model (Brief §9.2) so the same parser serves all four platforms.
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


# --- driver classification --------------------------------------------------------------
# Ordered rules: first regex (searched against the captured middle name) wins.
# More specific PS-hardened driver names are listed before the looser PL/AXI tokens so that
# e.g. "XIICPS" matches i2c/PS before the PL "XIIC" rule can fire.
# Each rule -> (type, family, canonical BSP driver).

_RULES: list[tuple[re.Pattern, str, str, str]] = [
    # --- PS hardened drivers (driver-indexed) ---
    (re.compile(r"XQSPIPS"), "qspi", "ps", "XQspiPs"),
    (re.compile(r"XIICPS"), "i2c", "ps", "XIicPs"),
    (re.compile(r"XSPIPS"), "spi", "ps", "XSpiPs"),
    (re.compile(r"XGPIOPS"), "gpio", "ps", "XGpioPs"),
    (re.compile(r"XUARTPS"), "uart", "ps", "XUartPs"),
    (re.compile(r"XCANPS"), "can", "ps", "XCanPs"),
    (re.compile(r"XEMACPS"), "eth", "ps", "XEmacPs"),
    (re.compile(r"XSDPS"), "sdio", "ps", "XSdPs"),
    # --- PS hardened (canonical PS7_/PSU_ instance names) ---
    (re.compile(r"^(PS7|PSU)_.*QSPI"), "qspi", "ps", "XQspiPs"),
    (re.compile(r"^(PS7|PSU)_.*(I2C|IIC)"), "i2c", "ps", "XIicPs"),
    (re.compile(r"^(PS7|PSU)_.*SPI"), "spi", "ps", "XSpiPs"),
    (re.compile(r"^(PS7|PSU)_.*GPIO"), "gpio", "ps", "XGpioPs"),
    (re.compile(r"^(PS7|PSU)_.*UART"), "uart", "ps", "XUartPs"),
    (re.compile(r"^(PS7|PSU)_.*(ENET|ETHERNET|GEM)"), "eth", "ps", "XEmacPs"),
    (re.compile(r"^(PS7|PSU)_.*SD"), "sdio", "ps", "XSdPs"),
    # --- PL / AXI soft IP ---
    (re.compile(r"QUAD_SPI"), "spi", "pl", "XSpi"),
    (re.compile(r"AXI_IIC|^XIIC"), "i2c", "pl", "XIic"),
    (re.compile(r"AXI_SPI|^XSPI"), "spi", "pl", "XSpi"),
    (re.compile(r"AXI_GPIO|^XGPIO"), "gpio", "pl", "XGpio"),
    (re.compile(r"UARTLITE"), "uart", "pl", "XUartLite"),
    (re.compile(r"AXI_DMA|AXIDMA"), "dma", "pl", "XAxiDma"),
]

# Recognized but non-attachable peripherals — skipped silently (kept out of `unmatched`).
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


def parse_xparameters(text: str, platform_model: Optional[dict] = None) -> ParseResult:
    """Parse *text* (xparameters.h contents) into a controller inventory.

    Returns a :class:`ParseResult` with ``controllers`` (project.spec format) and
    ``unmatched`` (controller-like macros whose driver we don't recognize — UI can show).
    """
    defines: dict[str, str] = {m.group("name"): m.group("value") for m in _DEFINE_RE.finditer(text)}
    result = ParseResult()
    seen_ids: set[str] = set()

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

        addr_int = _to_int(raw_value)
        base_address = f"0x{addr_int:08X}" if addr_int is not None else _clean_value(raw_value)
        device_id_val = _to_int(defines.get(f"{base_key}_DEVICE_ID", "")) if has_device_id else None

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

        ctrl_id = f"{zone}_{ctype}_{idx}"
        # Guarantee uniqueness if two drivers collapse to the same id.
        unique_id, bump = ctrl_id, 0
        while unique_id in seen_ids:
            bump += 1
            unique_id = f"{ctrl_id}_{bump}"
        seen_ids.add(unique_id)

        result.controllers.append(
            Controller(
                id=unique_id,
                type=ctype,
                instance=base_key,
                base_address=base_address,
                device_id=device_id_val,
                driver=driver,
                zone=zone,
            ).to_spec()
        )

    # Stable, human-friendly ordering: by zone then type then instance.
    result.controllers.sort(key=lambda c: (c["zone"], c["type"], c["instance"]))
    result.unmatched.sort(key=lambda c: c["instance"])
    return result
