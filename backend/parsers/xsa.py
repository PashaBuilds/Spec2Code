"""Parse controllers straight from a Vivado .xsa - the single-file entry flow.

The XSA already contains everything the xparameters.h step provides (and
more): the .hwh hardware description lists every PS/PL peripheral with its
memory ranges, and the processors tell us the platform. Instance names map
1:1 onto the canonical `XPAR_<NAME>` macro prefixes that classic BSPs emit,
so the generated code keeps using `{instance}_DEVICE_ID` exactly as in the
xparameters flow.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from backend.parsers.xparameters import _classify, _zone_for

_MODULE_KINDS = {
    "PERIPHERAL", "PROCESSOR", "BUS", "MEMORY", "MEMORY_CNTLR",
    "INTERRUPT_CNTLR", "DEBUG", "CLOCK", "RESET",
}

#: Processor MODTYPE prefixes -> Spec2Code platform id.
_PROCESSOR_PLATFORMS = [
    ("psv_cortex", "versal"),
    ("psu_cortex", "zynq_ultrascale"),
    ("ps7_cortex", "zynq_7000"),
    ("microblaze", "microblaze_7series"),
]

#: Monolithic PS blocks: board-level hwh files describe the whole PS as one
#: MODULE whose peripherals live in enable PARAMETERs, not as sub-modules.
#: (Versal CIPS enumerates psv_* modules in its own pspmc hwh, so it only
#: needs platform detection here.) PS peripheral base addresses are fixed by
#: the architecture; instance names match the canonical XPAR_* macros the
#: classic BSP emits.
_ZYNQMP_PS_PERIPHERALS = [
    ("PSU__I2C0__PERIPHERAL__ENABLE", "psu_i2c_0", 0xFF020000),
    ("PSU__I2C1__PERIPHERAL__ENABLE", "psu_i2c_1", 0xFF030000),
    ("PSU__UART0__PERIPHERAL__ENABLE", "psu_uart_0", 0xFF000000),
    ("PSU__UART1__PERIPHERAL__ENABLE", "psu_uart_1", 0xFF010000),
    ("PSU__SPI0__PERIPHERAL__ENABLE", "psu_spi_0", 0xFF040000),
    ("PSU__SPI1__PERIPHERAL__ENABLE", "psu_spi_1", 0xFF050000),
    ("PSU__QSPI__PERIPHERAL__ENABLE", "psu_qspi_0", 0xFF0F0000),
    ("PSU__ENET0__PERIPHERAL__ENABLE", "psu_ethernet_0", 0xFF0B0000),
    ("PSU__ENET1__PERIPHERAL__ENABLE", "psu_ethernet_1", 0xFF0C0000),
    ("PSU__ENET2__PERIPHERAL__ENABLE", "psu_ethernet_2", 0xFF0D0000),
    ("PSU__ENET3__PERIPHERAL__ENABLE", "psu_ethernet_3", 0xFF0E0000),
    ("PSU__CAN0__PERIPHERAL__ENABLE", "psu_can_0", 0xFF060000),
    ("PSU__CAN1__PERIPHERAL__ENABLE", "psu_can_1", 0xFF070000),
    ("PSU__SD0__PERIPHERAL__ENABLE", "psu_sd_0", 0xFF160000),
    ("PSU__SD1__PERIPHERAL__ENABLE", "psu_sd_1", 0xFF170000),
]
_ZYNQ7_PS_PERIPHERALS = [
    ("PCW_I2C0_PERIPHERAL_ENABLE", "ps7_i2c_0", 0xE0004000),
    ("PCW_I2C1_PERIPHERAL_ENABLE", "ps7_i2c_1", 0xE0005000),
    ("PCW_UART0_PERIPHERAL_ENABLE", "ps7_uart_0", 0xE0000000),
    ("PCW_UART1_PERIPHERAL_ENABLE", "ps7_uart_1", 0xE0001000),
    ("PCW_SPI0_PERIPHERAL_ENABLE", "ps7_spi_0", 0xE0006000),
    ("PCW_SPI1_PERIPHERAL_ENABLE", "ps7_spi_1", 0xE0007000),
    ("PCW_QSPI_PERIPHERAL_ENABLE", "ps7_qspi_0", 0xE000D000),
    ("PCW_ENET0_PERIPHERAL_ENABLE", "ps7_ethernet_0", 0xE000B000),
    ("PCW_ENET1_PERIPHERAL_ENABLE", "ps7_ethernet_1", 0xE000C000),
    ("PCW_CAN0_PERIPHERAL_ENABLE", "ps7_can_0", 0xE0008000),
    ("PCW_CAN1_PERIPHERAL_ENABLE", "ps7_can_1", 0xE0009000),
    ("PCW_SD0_PERIPHERAL_ENABLE", "ps7_sd_0", 0xE0100000),
    ("PCW_SD1_PERIPHERAL_ENABLE", "ps7_sd_1", 0xE0101000),
]
_PS_BLOCKS: dict[str, tuple[str, list[tuple[str, str, int]]]] = {
    "zynq_ultra_ps_e": ("zynq_ultrascale", _ZYNQMP_PS_PERIPHERALS),
    "processing_system7": ("zynq_7000", _ZYNQ7_PS_PERIPHERALS),
    "versal_cips": ("versal", []),
}


class XsaParseError(RuntimeError):
    """Raised when the file is not a readable XSA with a hardware handoff."""


@dataclass
class XsaParseResult:
    platform: str = ""
    controllers: list[dict] = field(default_factory=list)
    unmatched: list[dict] = field(default_factory=list)
    processors: list[str] = field(default_factory=list)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attr(element: ET.Element, *names: str) -> str:
    for name in names:
        for key, value in element.attrib.items():
            if key.upper() == name.upper() and value:
                return value
    return ""


def _hwh_documents(xsa_path: Path) -> list[tuple[str, bytes]]:
    try:
        with zipfile.ZipFile(xsa_path) as archive:
            return [
                (name, archive.read(name))
                for name in archive.namelist()
                if name.lower().endswith(".hwh")
            ]
    except (OSError, zipfile.BadZipFile) as exc:
        raise XsaParseError(f"XSA okunamadı (zip değil ya da erişilemiyor): {xsa_path}") from exc


def _module_kind(element: ET.Element) -> str:
    for kind_attr in ("IPTYPE", "MODCLASS"):
        value = _attr(element, kind_attr).upper()
        if value:
            return value
    modtype = _attr(element, "MODTYPE").upper()
    return modtype if modtype in _MODULE_KINDS else ""


def _instance_of(element: ET.Element) -> str:
    instance = _attr(element, "INSTANCE", "NAME")
    if instance:
        return instance
    fullname = _attr(element, "FULLNAME")
    return fullname.rsplit("/", 1)[-1] if fullname else ""


def _base_address_of(element: ET.Element) -> int | None:
    """Lowest MEMRANGE base, else a *BASEADDR parameter."""
    bases: list[int] = []
    for child in element.iter():
        if _local_name(child.tag).upper() == "MEMRANGE":
            raw = _attr(child, "BASEVALUE")
            try:
                bases.append(int(raw, 0))
            except (TypeError, ValueError):
                continue
    if bases:
        return min(bases)
    for child in element.iter():
        if _local_name(child.tag).upper() != "PARAMETER":
            continue
        name = _attr(child, "NAME").upper()
        if name.endswith("BASEADDR"):
            try:
                return int(_attr(child, "VALUE"), 0)
            except (TypeError, ValueError):
                continue
    return None


def _module_parameters(element: ET.Element) -> dict[str, str]:
    params: dict[str, str] = {}
    for child in element.iter():
        if _local_name(child.tag).upper() != "PARAMETER":
            continue
        name = _attr(child, "NAME")
        if name:
            params[name.upper()] = _attr(child, "VALUE")
    return params


def parse_xsa(xsa_path: Path, platform_model: dict | None = None) -> XsaParseResult:
    documents = _hwh_documents(xsa_path)
    if not documents:
        raise XsaParseError(f"XSA içinde .hwh hardware handoff dosyası yok: {xsa_path}")

    result = XsaParseResult()
    seen_instances: set[str] = set()
    raw_controllers: list[dict] = []

    def add_raw(instance: str, base: int) -> bool:
        middle = instance.upper()
        classified = _classify(middle)
        if classified is None:
            return False
        ctype, family, driver = classified
        raw_controllers.append({
            "type": ctype,
            "family": family,
            "driver": driver,
            "instance": f"XPAR_{middle}",
            "base": base,
        })
        return True

    for _name, content in documents:
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            continue
        for element in root.iter():
            if _local_name(element.tag).upper() != "MODULE":
                continue
            kind = _module_kind(element)
            instance = _instance_of(element)
            modtype = _attr(element, "MODTYPE")
            if not instance or instance in seen_instances:
                continue

            if kind == "PROCESSOR":
                seen_instances.add(instance)
                result.processors.append(instance)
                lowered = modtype.lower() or instance.lower()
                for prefix, platform in _PROCESSOR_PLATFORMS:
                    if lowered.startswith(prefix) and not result.platform:
                        result.platform = platform
                continue

            # Board-level hwh files describe the whole PS/CIPS as a single
            # block; expand its enabled peripherals from the parameters.
            ps_block = _PS_BLOCKS.get(modtype.lower())
            if ps_block is not None:
                seen_instances.add(instance)
                platform, peripherals = ps_block
                if not result.platform:
                    result.platform = platform
                if peripherals:
                    params = _module_parameters(element)
                    for enable_key, ps_instance, base in peripherals:
                        if params.get(enable_key.upper(), "0").strip() == "1":
                            if ps_instance not in seen_instances:
                                seen_instances.add(ps_instance)
                                add_raw(ps_instance, base)
                continue
            if kind and kind != "PERIPHERAL":
                continue

            base = _base_address_of(element)
            if base is None:
                # Clock/reset helpers and interconnect internals: silent noise.
                continue
            seen_instances.add(instance)
            if not add_raw(instance, base) and kind == "PERIPHERAL":
                # Memory-mapped unknowns are worth reporting (custom PL IP).
                result.unmatched.append({
                    "instance": f"XPAR_{instance.upper()}",
                    "base_address": f"0x{base:08X}",
                    "reason": f"tanınmayan IP '{modtype or instance}' (custom PL IP olabilir)",
                })

    if not result.platform and any(
        item["instance"].startswith("XPAR_PSV_") for item in raw_controllers
    ):
        result.platform = "versal"

    # Deterministic ids mirroring the xparameters flow: <zone>_<type>_<n>.
    raw_controllers.sort(key=lambda item: (item["family"], item["type"], item["base"]))
    counters: dict[tuple[str, str], int] = {}
    for item in raw_controllers:
        zone = _zone_for(item["family"], platform_model)
        index = counters.get((zone, item["type"]), 0)
        counters[(zone, item["type"])] = index + 1
        result.controllers.append({
            "id": f"{zone}_{item['type']}_{index}",
            "type": item["type"],
            "instance": item["instance"],
            "base_address": f"0x{item['base']:08X}",
            "driver": item["driver"],
            "source": "xparameters",
            "zone": zone,
        })
    return result


def detect_platform(xsa_path: Path) -> str:
    return parse_xsa(xsa_path).platform


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_xsa_filename(name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("_", Path(name).name).strip("._") or "design.xsa"
    return cleaned if cleaned.lower().endswith(".xsa") else f"{cleaned}.xsa"
