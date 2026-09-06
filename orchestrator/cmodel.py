"""C render-model builder (Brief 13).

Turns a validated project.spec + device descriptors + ruleset into a structured model of
C functions with fully-rendered, coding-standard-compliant bodies. The Jinja templates
(codegen.py) only assemble the file skeletons around this model.

Design notes:
  * Codegen targets the descriptor's NAMED OPERATIONS, not raw registers (Brief 6.2).
  * Function names are camelCase: ``tca9548aChannelSelect(...)`` rather than
    underscore-separated names.
  * A mux-attached device gets a ``<mux>ChannelSelect(...)`` call injected before every
    device access (Brief 10, 13).
  * SPI flash address width (3 vs 4 bytes) flows from each descriptor command's
    ``address_bytes`` straight into the generated transfers - proving MT25QU02G differs
    from MT25Q128 (acceptance 20.3).

This module returns pure data; only codegen.py writes it out (through hostplat.io, CRLF).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from orchestrator.device_profiles import registry as device_profiles
from orchestrator import boards, tics

_IND = "    "  # 4 spaces


class CodegenError(RuntimeError):
    pass


# --- tiny C emitter: Allman braces + indentation handled for us -------------------------

class Emit:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.level = 1

    def ln(self, text: str = "") -> "Emit":
        self.lines.append((_IND * self.level + text) if text else "")
        return self

    def open(self, header: str) -> "Emit":
        self.ln(header)
        self.ln("{")
        self.level += 1
        return self

    def open_scope(self) -> "Emit":
        """Open a bare nested block (single '{'), e.g. to give a poll its own locals."""
        self.ln("{")
        self.level += 1
        return self

    def close(self, suffix: str = "") -> "Emit":
        self.level -= 1
        self.ln("}" + suffix)
        return self

    def check_status(self) -> "Emit":
        """if (iStatus != XST_SUCCESS) { return iStatus; }"""
        self.open("if (iStatus != XST_SUCCESS)")
        self.ln("return iStatus;")
        self.close()
        return self

    def blank(self) -> "Emit":
        self.lines.append("")
        return self

    def out(self) -> list[str]:
        return self.lines


# --- model dataclasses ------------------------------------------------------------------

@dataclass
class CFunc:
    name: str
    ret: str
    params: list[str]
    body: list[str]
    brief: str = ""
    doxy_params: list[tuple[str, str]] = field(default_factory=list)
    doxy_return: str = ""
    static: bool = False

    @property
    def signature(self) -> str:
        params = ", ".join(self.params) if self.params else "void"
        return f"{'static ' if self.static else ''}{self.ret} {self.name}({params})"


@dataclass
class CTest:
    runtime: str
    module: str
    includes: list[str]
    funcs: list[CFunc]


@dataclass
class CUnit:
    module: str
    part: str
    summary: str
    transport: str
    header_includes: list[str]
    driver_includes: list[str]
    defines: list[tuple[str, str, str]]   # (name, value, trailing comment)
    funcs: list[CFunc]
    public_names: list[str]
    private_decls: list[str] = field(default_factory=list)
    #: Baslikta yayimlanan typedef metinleri (S<Mod>Status, S<Mod>Voltage ...).
    public_types: list[str] = field(default_factory=list)
    #: Fiziksel kart kimligi (spec `boards` tanimsizken herkes ortuk ana kartta).
    board_id: str = boards.MAIN_BOARD_ID
    test: Optional[CTest] = None


# --- helpers ----------------------------------------------------------------------------

def _prune_unused_static_funcs(funcs: list[CFunc]) -> list[CFunc]:
    """Drop static helpers no other emitted function references.

    Low-level helpers are emitted per transport, but the requested operation
    set may never call some of them; unused statics trip -Wunused-function in
    the Vitis application build.
    """
    kept = list(funcs)
    changed = True
    while changed:
        changed = False
        for func in list(kept):
            if not func.static:
                continue
            other_bodies = "\n".join("\n".join(other.body) for other in kept if other is not func)
            if re.search(rf"\b{re.escape(func.name)}\s*\(", other_bodies) is None:
                kept.remove(func)
                changed = True
    return kept


def _module_of(part: str) -> str:
    mod = "".join(ch.lower() for ch in part if ch.isalnum())
    if mod and not mod[0].isalpha():
        mod = f"dev{mod}"
    if not mod or not mod[0].isalpha():
        raise CodegenError(f"cannot derive a valid C module name from part '{part}'")
    return mod


def device_module_map(spec: dict) -> dict[str, str]:
    """Cihaz kimliği -> C modül adı (spec sırasına göre kararlı).

    SAHA BULGUSU (2026-07-05): aynı parçadan birden çok cihaz varken modül
    adı parçadan türediği için her örnek AYNI ltc2991.c'yi (son yazılan
    kazanır) ve içindeki tek LTC2991_I2C_ADDR sabitini paylaşıyordu — tüm
    örnekler tek fiziksel çipten okuyordu. Adres/mux kanalı derleme zamanı
    sabiti olduğundan her örnek kendi modülünü alır: ilki geriye dönük
    uyumlu kalır (ltc2991), sonrakiler harf soneki alır (ltc2991b,
    ltc2991c, ...).

    v0.1.182 (kullanici kurali): I2C cihazlarinda sonek YOK - ayni parcadan N cihaz TEK
    surucu modulu paylasir; bus ornegi, adres ve switch bilgisi `drivers/i2c_cihazlar.*`
    tablosundan (`const SI2cCihaz*` parametresi) gelir. Sonek yalniz SPI/GPIO cihazlarinda
    (chip-select/maske derleme sabiti) kalir.
    """
    counts: dict[str, int] = {}
    mapping: dict[str, str] = {}
    for device in spec.get("devices", []):
        base = _module_of(device.get("part", ""))
        if is_i2c_device(device):
            mapping[device.get("id", "")] = base
            continue
        n = counts.get(base, 0)
        counts[base] = n + 1
        if n == 0:
            mapping[device.get("id", "")] = base
        elif n <= 25:
            mapping[device.get("id", "")] = f"{base}{chr(ord('a') + n)}"
        else:
            mapping[device.get("id", "")] = f"{base}x{n}"
    return mapping


def is_i2c_device(device: dict) -> bool:
    """Spec'te I2C adresiyle bagli cihaz (register cihazi ya da EEPROM)."""
    return (device.get("attach") or {}).get("i2c_address") is not None


# --- I2C cihaz tablosu (drivers/i2c_cihazlar.h/.c) ------------------------------------------
#: Tasinabilir tablo: enum (cihaz id'sinden) + {bus ornegi, adres, switch adresi/kanali}.
#: Surucu, cit/ ve test bench ayni satiri `const SI2cCihaz*` olarak alir; ornek/adres AYRI
#: parametre olarak dolasmaz (kullanici kurali 2026-09-06: "structure array en alt katmana
#: kadar gitsin").
I2C_TABLE_MODULE = "i2c_cihazlar"
I2C_DEVICE_PARAM = "const SI2cCihaz* spCihaz"
I2C_DEVICE_VAR = "spCihaz"


def i2c_enum_name(device_id: str) -> str:
    return "I2C_CIHAZ_" + re.sub(r"[^A-Za-z0-9]+", "_", str(device_id)).strip("_").upper()


def i2c_init_writes_for(device: dict, descriptor: Optional[dict]) -> list[dict]:
    """Cihaza ozel init yazimlari (profil + config.init_sequence): {reg, offset, value, note}."""
    if descriptor is None:
        return []
    regs = {rg["name"]: rg for rg in descriptor.get("registers", [])}
    writes = [*device_profiles.i2c_init_writes(device), *_generic_i2c_init_writes(device, regs)]
    out = []
    for w in writes:
        reg = regs.get(str(w.get("reg")))
        if reg is None:
            raise CodegenError(f"{device.get('id')}: init yazimi bilinmeyen register '{w.get('reg')}'")
        out.append({"reg": str(w["reg"]), "offset": int(reg["offset"]), "value": int(w["value"]) & 0xFF,
                    "note": str(w.get("note") or "")})
    return out


def i2c_device_rows(spec: dict, get_descriptor: Optional[Callable[[str], dict]] = None) -> list[dict]:
    """Tablo satirlari (spec cihaz sirasi): enum, adres, switch adresi/kanali, denetleyici, init dizisi."""
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    rows: list[dict] = []
    for device in spec.get("devices", []):
        if not is_i2c_device(device):
            continue
        attach = device["attach"]
        via = attach.get("via_mux") or {}
        mux = muxes.get(via.get("mux_id")) if isinstance(via, dict) else None
        descriptor = None
        if get_descriptor is not None:
            descriptor = get_descriptor(device.get("descriptor_ref") or device.get("part", ""))
            if descriptor.get("memory"):
                descriptor = None  # EEPROM: init yazimi yok
        rows.append({
            "init": i2c_init_writes_for(device, descriptor),
            "id": str(device.get("id", "")),
            "part": str(device.get("part", "")),
            "enum": i2c_enum_name(str(device.get("id", ""))),
            "address": int(str(attach["i2c_address"]), 0),
            "switch_address": int(str(mux["i2c_address"]), 0) if mux else 0,
            "switch_channel": int(via.get("channel", 0)) if mux else 0,
            "controller_id": str(attach.get("controller_id", "")),
        })
    return rows


def i2c_controllers(spec: dict) -> list[dict]:
    """I2C cihazlarin bagli oldugu denetleyiciler (spec sirasi, tekil)."""
    used = {r["controller_id"] for r in i2c_device_rows(spec)}
    return [c for c in spec.get("controllers", []) if c.get("id") in used]


def i2c_table_htype(spec: dict) -> str:
    """Tablodaki bus ornegi tipi (XIic / XIicPs). Karisik tip desteklenmez (tek struct)."""
    types = {_handle_for(c)[0] for c in i2c_controllers(spec)}
    if not types:
        return "XIic"
    if len(types) > 1:
        raise CodegenError(f"I2C cihaz tablosu tek denetleyici tipi ister, spec'te karisik: {sorted(types)}")
    return next(iter(types))


def i2c_controller_var(controller: dict) -> str:
    return "sp" + _pascal_suffix(str(controller.get("id", "iic")))


def i2c_table_header(spec: dict) -> str:
    rows = i2c_device_rows(spec)
    htype = i2c_table_htype(spec)
    ctrls = i2c_controllers(spec)
    enum_lines = []
    for i, r in enumerate(rows):
        note = f"{r['id']} ({r['part']}) 0x{r['address']:02X}"
        if r["switch_address"]:
            note += f", switch 0x{r['switch_address']:02X} kanal {r['switch_channel']}"
        enum_lines.append(f"    {r['enum']} = {i}, /* {note} */")
    params = ", ".join(f"{htype}* {i2c_controller_var(c)}" for c in ctrls) or "void"
    lines = [
        "/**",
        " * @file i2c_cihazlar.h",
        " * @brief I2C cihaz tablosu: her cihazin bus ornegi, adresi ve (varsa) I2C switch",
        " *        adresi/kanali TEK satirda. Suruculer ve cit/ katmani cihazi bu satirla alir;",
        " *        ayni parcadan N cihaz ayni surucuyu paylasir. Generated by Spec2Code.",
        " */",
        "#ifndef I2C_CIHAZLAR_H",
        "#define I2C_CIHAZLAR_H",
        "",
        f'#include "{_i2c_header_for(htype)}"',
        "",
        "typedef enum",
        "{",
        *enum_lines,
        f"    I2C_CIHAZ_SAYISI = {len(rows)}",
        "} EI2cCihaz;",
        "",
        "/* device_init'te sirayla yazilan register/deger cifti (cihaza ozel config'ten). */",
        "typedef struct",
        "{",
        "    unsigned char ucReg;",
        "    unsigned char ucDeger;",
        "} SI2cInitYazim;",
        "",
        "typedef struct",
        "{",
        f"    {htype}* spIic;              /* denetleyici ornegi (i2cCihazlarInit ile atanir)      */",
        "    unsigned char ucAdres;       /* 7-bit I2C adresi                                    */",
        "    unsigned char ucSwitchAdres; /* I2C switch (TCA9548A) adresi; 0 = switch yok         */",
        "    unsigned char ucSwitchKanal; /* switch kanali 0..7 (ucSwitchAdres != 0 ise gecerli)  */",
        "    const SI2cInitYazim* spInit; /* device_init yazim dizisi (NULL = yok)                */",
        "    unsigned char ucInitSayisi;  /* spInit eleman sayisi                                */",
        "} SI2cCihaz;",
        "",
        "/* Denetleyici ornekleri tabloya baglanir (bir kez, ornekler ilklendirildikten sonra). */",
        f"void i2cCihazlarInit({params});",
        "",
        "/* Cihazin tablo satiri; gecersiz indekste NULL. */",
        "const SI2cCihaz* i2cCihaz(EI2cCihaz eCihaz);",
        "",
        "#endif /* I2C_CIHAZLAR_H */",
        "",
    ]
    return "\n".join(lines)


def i2c_table_source(spec: dict, get_descriptor: Optional[Callable[[str], dict]] = None) -> str:
    rows = i2c_device_rows(spec, get_descriptor)
    htype = i2c_table_htype(spec)
    ctrls = i2c_controllers(spec)
    var_of = {c["id"]: i2c_controller_var(c) for c in ctrls}
    init_blocks: list[str] = []
    table: list[str] = []
    for r in rows:
        if r["init"]:
            name = f"S_sArrInit{_pascal_suffix(r['id'])}"
            init_blocks.append(f"/* {r['id']} ({r['part']}) device_init yazimlari (spec config'ten). */")
            init_blocks.append(f"static const SI2cInitYazim {name}[{len(r['init'])}] = {{")
            for w in r["init"]:
                note = f" /* {w['reg']}: {w['note']} */" if w["note"] else f" /* {w['reg']} */"
                init_blocks.append(f"    {{{_hexu8(w['offset'])}, {_hexu8(w['value'])}}},{note}")
            init_blocks.append("};")
            init_blocks.append("")
            init_ref = f"{name}, {len(r['init'])}U"
        else:
            init_ref = "NULL, 0U"
        table.append(f"    {{NULL, {_hexu8(r['address'])}, {_hexu8(r['switch_address'])}, "
                     f"{_hexu8(r['switch_channel'])}, {init_ref}}}, /* {r['enum']} */")
    if not table:
        table = ["    {NULL, 0x00U, 0x00U, 0x00U, NULL, 0U}"]
    params = ", ".join(f"{htype}* {var_of[c['id']]}" for c in ctrls) or "void"
    assigns = [f"    S_sArrI2cCihaz[{r['enum']}].spIic = {var_of[r['controller_id']]};" for r in rows]
    lines = [
        "/**",
        " * @file i2c_cihazlar.c",
        " * @brief I2C cihaz tablosu gerceklemesi. Generated by Spec2Code.",
        " */",
        '#include "i2c_cihazlar.h"',
        "#include <stddef.h>",
        "",
        *init_blocks,
        f"static SI2cCihaz S_sArrI2cCihaz[{max(1, len(rows))}] = {{",
        *table,
        "};",
        "",
        f"void i2cCihazlarInit({params})",
        "{",
        *assigns,
        "}",
        "",
        "const SI2cCihaz* i2cCihaz(EI2cCihaz eCihaz)",
        "{",
        "    if ((unsigned int)eCihaz >= (unsigned int)I2C_CIHAZ_SAYISI)",
        "    {",
        "        return NULL;",
        "    }",
        "    return &S_sArrI2cCihaz[eCihaz];",
        "}",
        "",
    ]
    return "\n".join(lines)


#: Drivers the deterministic bus-op emitters actually speak. Every bus fragment
#: is routed through a per-driver adapter (``_I2cApi`` for i2c, the
#: ``_is_axi_spi``/``_is_qspipsu`` branches for spi), so only the drivers that
#: have an adapter arm may pass. Letting an unimplemented driver (XQspiPs,
#: XOspiPsv) through would emit code that cannot compile against that BSP -
#: fail loudly instead.
_SUPPORTED_BUS_DRIVERS: dict[str, set[str]] = {
    "i2c": {"XIicPs", "XIic"},
    "spi": {"XSpiPs", "XSpi"},
    "qspi": {"XQspiPsu"},
    # AXI GPIO (soft IP) only. PS GPIO (XGpioPs) has a different API entirely
    # (XGpioPs_ReadPin/WritePin on a flat pin space, no channel/TRI-mask model)
    # and no emitter arm - it must fail loudly rather than emit code that
    # cannot compile.
    "gpio": {"XGpio"},
}

#: Handle variable name overrides per driver (none: every driver, AXI IIC dahil, ornek
#: isaretcisi tasir - kural: ornek en alt seviyeye kadar iner).
_HANDLE_VARS: dict[str, str] = {}


def _handle_for(controller: dict) -> tuple[str, str]:
    ctype = controller.get("type")
    var = {"i2c": "spIic", "spi": "spSpi", "qspi": "spQspi", "gpio": "spGpio"}.get(ctype, "spDev")
    driver = controller.get("driver")
    if not driver:
        is_ps = controller.get("zone") == "ps"
        table = {
            ("i2c", True): "XIicPs", ("i2c", False): "XIic",
            ("spi", True): "XSpiPs", ("spi", False): "XSpi",
            ("qspi", True): "XQspiPs", ("qspi", False): "XSpi",
            ("gpio", True): "XGpioPs", ("gpio", False): "XGpio",
        }
        driver = table.get((ctype, is_ps))
        if driver is None:
            raise CodegenError(f"no BSP driver mapping for controller type '{ctype}'")
    supported = _SUPPORTED_BUS_DRIVERS.get(str(ctype))
    if supported is not None and driver not in supported:
        raise CodegenError(
            f"controller '{controller.get('id', '?')}' ({ctype}) uses driver '{driver}', which "
            f"deterministic code generation does not support yet (supported: "
            f"{', '.join(sorted(supported))}). XQspiPs/XOspiPsv paths are not implemented; "
            "attach the device to a supported controller.")
    return driver, _HANDLE_VARS.get(driver, var)




def _handle_param(htype: str, hvar: str) -> str:
    """C parameter declaration for a bus-controller handle: always a driver instance pointer.

    KARAR (v0.1.179, kullanici): AXI IIC de ``XIic*`` ornegi tasir; xiic_l.h polled
    API'sine taban adres ``spIic->BaseAddress`` ile verilir. Ornek en alt seviyeye kadar iner.
    """
    return f"{htype}* {hvar}"


def _spi_header_for(htype: str) -> str:
    return {
        "XQspiPsu": "xqspipsu.h",
        "XQspiPs": "xqspips.h",
        "XSpi": "xspi.h",
    }.get(htype, "xspips.h")


def _i2c_header_for(htype: str) -> str:
    return "xiic.h" if htype == "XIic" else "xiicps.h"


def _gpio_header_for(htype: str) -> str:
    """BSP header for a GPIO controller driver.

    Only the AXI GPIO soft IP (``XGpio``) has an emitter arm; ``_handle_for``
    already rejects everything else, so this stays a single-entry map that
    fails as loudly as its caller if that ever changes.
    """
    if htype != "XGpio":
        raise CodegenError(f"no GPIO header mapping for driver '{htype}' (only XGpio is implemented)")
    return "xgpio.h"


def _is_qspipsu(htype: str) -> bool:
    return htype == "XQspiPsu"


def _is_axi_spi(htype: str) -> bool:
    return htype == "XSpi"


def _spi_select(e: "Emit", htype: str, hvar: str, sel_def: str) -> "Emit":
    """Chip-select call for the single-transfer SPI drivers (XSpiPs / AXI XSpi).

    ``XSpiPs_SetSlaveSelect`` takes a slave INDEX, while AXI ``XSpi`` takes a
    ONE-HOT, ACTIVE-HIGH MASK - xspi.c documents it as "a 32-bit mask with a 1
    in the bit position of the slave being selected", and the official
    ``xspi_stm_flash_example.c`` / ``xspi_eeprom_example.c`` pass ``0x01`` for
    CS0. The generated ``*_SPI_SELECT`` define stays the CS index either way;
    only the shift is driver-specific.
    """
    if _is_axi_spi(htype):
        e.ln(f"iStatus = XSpi_SetSlaveSelect({hvar}, (1U << {sel_def}));").check_status()
    else:
        e.ln(f"iStatus = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
    return e


def _spi_transfer(e: "Emit", htype: str, hvar: str, tx: str, rx: str, count: str) -> "Emit":
    """Blocking full-duplex transfer for XSpiPs / AXI XSpi (identical argument order)."""
    func = "XSpi_Transfer" if _is_axi_spi(htype) else "XSpiPs_PolledTransfer"
    e.ln(f"iStatus = {func}({hvar}, {tx}, {rx}, {count});").check_status()
    return e


def _spi_emit_init(e: "Emit", htype: str, hvar: str, instance: str) -> "Emit":
    """Guarded SPI controller bring-up for all three SPI-ish drivers.

    The AXI arm follows the official polled flow verbatim
    (``spi_v4_11/examples/xspi_polled_example.c`` plus the flash/EEPROM
    examples): LookupConfig -> CfgInitialize -> SetOptions(MASTER | MANUAL_SS)
    -> Start -> IntrGlobalDisable. Interrupts must be masked because every
    generated transfer is polled.
    """
    # Testbench'in başlattığı paylaşılan denetleyiciyi yeniden CfgInitialize
    # etme: XQspiPsu XST_DEVICE_IS_STARTED döndürür (sahada mt25qu02g
    # device_init status=5 olarak görüldü).
    e.open(f"if ({hvar}->IsReady != XIL_COMPONENT_IS_READY)")
    if _is_qspipsu(htype):
        e.ln(f"spConfig = XQspiPsu_LookupConfig({instance}_DEVICE_ID);")
    elif _is_axi_spi(htype):
        e.ln(f"spConfig = XSpi_LookupConfig({instance}_DEVICE_ID);")
    else:
        e.ln(f"spConfig = XSpiPs_LookupConfig({instance}_DEVICE_ID);")
    e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
    if _is_qspipsu(htype):
        e.ln(f"iStatus = XQspiPsu_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
        e.ln(f"iStatus = XQspiPsu_SetOptions({hvar}, XQSPIPSU_MANUAL_START_OPTION);").check_status()
        e.ln(f"iStatus = XQspiPsu_SetClkPrescaler({hvar}, XQSPIPSU_CLK_PRESCALE_8);").check_status()
        e.ln(f"XQspiPsu_SelectFlash({hvar}, XQSPIPSU_SELECT_FLASH_CS_LOWER, XQSPIPSU_SELECT_FLASH_BUS_LOWER);")
    elif _is_axi_spi(htype):
        e.ln(f"iStatus = XSpi_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
        e.ln(f"iStatus = XSpi_SetOptions({hvar}, XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION);").check_status()
        e.ln(f"iStatus = XSpi_Start({hvar});").check_status()
        e.ln("/* Uretilen her transfer polled: kesmeler maskeli kalmali. */")
        e.ln(f"XSpi_IntrGlobalDisable({hvar});")
    else:
        e.ln(f"iStatus = XSpiPs_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
        e.ln(f"iStatus = XSpiPs_SetOptions({hvar}, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);").check_status()
        e.ln(f"iStatus = XSpiPs_SetClkPrescaler({hvar}, XSPIPS_CLK_PRESCALE_8);").check_status()
    e.close()
    return e


class _I2cApi:
    """Driver-polymorphic I2C fragments: PS ``XIicPs`` vs AXI soft-IP ``XIic``.

    Every I2C emitter asks this adapter for its bus fragments instead of
    hard-coding ``XIicPs_*`` literals, so the same operation logic serves a
    ZynqMP PS controller and a MicroBlaze AXI IIC core.

    The two drivers differ in three ways that matter here:

    * **Handle** - XIicPs is instance based, XIic's polled API is base-address
      based (see ``_handle_param``).
    * **Return value** - ``XIicPs_MasterSendPolled`` returns ``XST_*``, while
      ``XIic_DynSend``/``XIic_DynRecv`` return the NUMBER OF BYTES TRANSFERRED (0
      when the bus is busy). DYNAMIC mode is used on purpose: the standard-mode
      ``XIic_Send`` clears MSMS before the last byte of a STOP transfer, so a
      single-byte write (register pointer, TCA9548A control byte) generates STOP
      right after the address and the byte never leaves the FIFO (FIELD: Nexys A7
      ADT7420 always answered from register 0). ``XIic_DynInit`` runs in init. AXI units therefore get two small static wrappers
      (``<module>BusSend`` / ``<module>BusRecv``) that compare the count against
      the request and translate to ``XST_SUCCESS``/``XST_FAILURE``; every call
      site keeps the familiar ``iStatus = ...; if (iStatus != XST_SUCCESS)``
      shape.
    * **Bus-idle wait** - XIicPs needs an explicit ``XIicPs_BusIsBusy`` spin
      after each transfer; ``XIic_Send``/``XIic_Recv`` already block until the
      transfer finished and wait for bus-free themselves, so nothing is emitted.

    STOP vs REPEATED_START: the PS path writes the register pointer with a
    STOP and then reads (``XIicPs_MasterSendPolled`` always emits a STOP; field
    proven on ZynqMP). On AXI IIC in dynamic mode that sequence HANGS inside
    ``XIic_DynRecv`` (FIELD, Nexys A7 + ADT7420, six-variant probe: after a
    STOP transfer the next dynamic read START is never issued), so AXI register
    reads send the pointer with ``XIIC_REPEATED_START`` (``hold_bus=True``) and
    let ``XIic_DynRecv`` finish with the STOP. Writes stay STOP (1..N bytes are
    delivered; verified through the ADT7420 software-reset register).
    """

    def __init__(self, module: str, htype: str, hvar: str) -> None:
        self.module = module
        self.htype = htype
        self.hvar = hvar
        self.param_override: str = ""
        self.bus: str = hvar  # Xilinx cagrilarindaki handle ifadesi

    @property
    def is_axi(self) -> bool:
        return self.htype == "XIic"

    @property
    def param(self) -> str:
        if self.param_override:
            return self.param_override
        return _handle_param(self.htype, self.hvar)

    @property
    def header(self) -> str:
        return _i2c_header_for(self.htype)

    def _count(self, count: int | str) -> str:
        """Byte count rendered for the target API's parameter type."""
        if isinstance(count, int):
            return f"{count}U" if self.is_axi else str(count)
        return count if self.is_axi else f"(int){count}"

    def send(self, e: Emit, buffer: str, count: int | str, addr_def: str, *,
             hold_bus: bool = False, status: str = "iStatus") -> Emit:
        if self.is_axi:
            option = "XIIC_REPEATED_START" if hold_bus else "XIIC_STOP"
            e.ln(f"{status} = {_func_name(self.module, 'bus_send')}({self.bus}, {addr_def}, "
                 f"{buffer}, {self._count(count)}, {option});")
        else:
            e.ln(f"{status} = XIicPs_MasterSendPolled({self.bus}, {buffer}, "
                 f"{self._count(count)}, {addr_def});")
        return e

    def recv(self, e: Emit, buffer: str, count: int | str, addr_def: str, *,
             status: str = "iStatus") -> Emit:
        if self.is_axi:
            e.ln(f"{status} = {_func_name(self.module, 'bus_recv')}({self.bus}, {addr_def}, "
                 f"{buffer}, {self._count(count)});")
        else:
            e.ln(f"{status} = XIicPs_MasterRecvPolled({self.bus}, {buffer}, "
                 f"{self._count(count)}, {addr_def});")
        return e

    def wait_idle(self, e: Emit, comment: str = "/* wait */") -> Emit:
        if not self.is_axi:
            e.open(f"while (XIicPs_BusIsBusy({self.bus}) == TRUE)").ln(comment).close()
        return e

    def config_decl(self) -> Optional[str]:
        return f"{self.htype}_Config* spConfig;"

    def emit_init(self, e: Emit, instance: str, sclk_def: str) -> Emit:
        """Controller bring-up, guarded against re-initializing a live handle."""
        if self.is_axi:
            e.ln("/* AXI IIC ornegi (xiic.h) ilk kullanimda kurulur; veri-yolu cagrilari polled")
            e.ln(" * API'ye (xiic_l.h) taban adresle gider: spIic->BaseAddress. SCL hizi IP'de")
            e.ln(" * sabittir. Cekirdek DINAMIK moda alinir (XIic_DynInit): standart-mod")
            e.ln(" * XIic_Send tek baytlik STOP yaziminda bayti dusuruyor (SAHA: Nexys A7")
            e.ln(" * ADT7420). Ardindan hat gercekten bosta mi diye bakilir. */")
            e.open(f"if ({self.bus}->IsReady != XIL_COMPONENT_IS_READY)")
            e.ln(f"spConfig = XIic_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
            e.ln(f"iStatus = XIic_CfgInitialize({self.bus}, spConfig, spConfig->BaseAddress);").check_status()
            e.close()
            e.ln(f"iStatus = XIic_DynInit({self.bus}->BaseAddress);").check_status()
            e.ln(f"iStatus = (int)XIic_WaitBusFree({self.bus}->BaseAddress);").check_status()
        else:
            # Shared, already-running controllers (test bench boot) must not
            # be re-initialized: CfgInitialize returns XST_DEVICE_IS_STARTED
            # on some drivers and resets live bus settings on others.
            e.open(f"if ({self.bus}->IsReady != XIL_COMPONENT_IS_READY)")
            e.ln(f"spConfig = XIicPs_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
            e.ln(f"iStatus = XIicPs_CfgInitialize({self.bus}, spConfig, spConfig->BaseAddress);").check_status()
            e.ln(f"iStatus = XIicPs_SetSClk({self.bus}, {sclk_def});").check_status()
            e.close()
        return e

    def wrapper_funcs(self) -> list[CFunc]:
        """Byte-count -> XST_* adapters for the AXI IIC low-level API (AXI only).

        ``XIic_Send``/``XIic_Recv`` report BYTES TRANSFERRED, so a short count
        (NACK, arbitration loss, busy bus -> 0) is the only failure signal there
        is; these wrappers turn that into the XST_* contract the rest of the
        generated code speaks.
        """
        if not self.is_axi:
            return []
        base_param = _handle_param(self.htype, "spIic")

        snd = Emit()
        snd.ln("unsigned int uiSent;").blank()
        snd.ln("uiSent = (unsigned int)XIic_DynSend(spIic->BaseAddress, (unsigned short)ucAddress, ucpBuffer,")
        snd.ln("                                     (unsigned char)uiLength, ucOption);")
        snd.open("if (uiSent != uiLength)")
        snd.ln("return XST_FAILURE;")
        snd.close()
        snd.ln("return XST_SUCCESS;")
        send = CFunc(
            _func_name(self.module, "bus_send"), "int",
            [base_param, "unsigned char ucAddress", "unsigned char* ucpBuffer",
             "unsigned int uiLength", "unsigned char ucOption"],
            snd.out(), static=True)

        rcv = Emit()
        rcv.ln("unsigned int uiGot;").blank()
        rcv.ln("uiGot = (unsigned int)XIic_DynRecv(spIic->BaseAddress, ucAddress, ucpBuffer, (unsigned char)uiLength);")
        rcv.open("if (uiGot != uiLength)")
        rcv.ln("return XST_FAILURE;")
        rcv.close()
        rcv.ln("return XST_SUCCESS;")
        recv = CFunc(
            _func_name(self.module, "bus_recv"), "int",
            [base_param, "unsigned char ucAddress", "unsigned char* ucpBuffer",
             "unsigned int uiLength"],
            rcv.out(), static=True)
        return [send, recv]


def _i2c_api(module: str, controller: dict) -> _I2cApi:
    htype, hvar = _handle_for(controller)
    return _I2cApi(module, htype, hvar)


def _i2c_device_api(module: str, controller: dict) -> _I2cApi:
    """Cihaz surucusu: handle TABLO SATIRINDAN (spCihaz->spIic), adres spCihaz->ucAdres."""
    htype, _hvar = _handle_for(controller)
    api = _I2cApi(module, htype, I2C_DEVICE_VAR)
    api.bus = f"{I2C_DEVICE_VAR}->spIic"
    api.param_override = I2C_DEVICE_PARAM
    return api


def _hexu8(value: int) -> str:
    return f"0x{value & 0xFF:02X}U"


def _hexu32(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:X}U"


def _first_bit(bits: str) -> int:
    bits = str(bits)
    return int(bits.split(":")[-1]) if ":" in bits else int(bits)


def _pascal_suffix(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("_") if part)


def _func_name(module: str, action: str) -> str:
    return f"{module}{_pascal_suffix(action)}"


def _struct_type(module: str, suffix: str) -> str:
    return f"S{_pascal_suffix(module)}{suffix}"


def _static_array_name(module: str, suffix: str) -> str:
    return f"S_sArr{_pascal_suffix(module)}{suffix}"


def _static_uint_array_name(module: str, suffix: str) -> str:
    return f"S_uiArr{_pascal_suffix(module)}{suffix}"


def _static_uchar_array_name(module: str, suffix: str) -> str:
    return f"S_ucArr{_pascal_suffix(module)}{suffix}"


def _is_lmk_byte_register_model(model: dict) -> bool:
    """LMK04832-style TICS Pro register model: 15-bit address + 8-bit data.

    Scope for the "3 bytes per message" unsigned char array format (saha
    isteği). LMX-style parts (7-bit address, 16-bit data) keep the existing
    unsigned int word array untouched.
    """
    return int(model.get("address_bits", 0) or 0) == 15 and int(model.get("data_bits", 0) or 0) == 8


def _handle_var(module: str, htype: str = "") -> str:
    del htype  # her surucu ornek isaretcisi tasir: tek adlandirma
    return f"s{_pascal_suffix(module)}Handle"


def _return_param(op_name: str, returns: str) -> tuple[str, str]:
    obj = op_name.split("_")[0]
    ret = returns.lower()
    if "uint8" in ret:
        return "unsigned char", f"ucp{_pascal_suffix(obj)}"
    if "uint32" in ret:
        return "unsigned int", f"uip{_pascal_suffix(obj)}"
    if "int32" in ret:
        return "int", f"ip{_pascal_suffix(obj)}"
    return "unsigned short", f"usp{_pascal_suffix(obj)}"


def _array_return_info(module: str, returns: str) -> Optional[dict]:
    """Dizi donuslu op (``voltages[8]``) icin surucu struct'i.

    'voltages[8]' -> {ctype: 'SLtc2991Voltage', param: 'spVoltage', field: 'usArrVoltage',
    count: 8, noun: 'Voltage'} (isim = returns adinin tekili). Skaler donus -> None.
    """
    m = re.match(r"^\s*([A-Za-z_]+)\s*\[(\d+)\]\s*$", str(returns))
    if not m:
        return None
    noun = m.group(1).lower()
    if noun.endswith("s") and len(noun) > 1:
        noun = noun[:-1]
    pas = _pascal_suffix(noun)
    return {
        "ctype": f"S{_pascal_suffix(module)}{pas}",
        "param": f"sp{pas}",
        "field": f"usArr{pas}",
        "count": int(m.group(2)),
        "noun": pas,
    }


def _array_struct_typedef(part: str, op_name: str, info: dict, unit: str) -> str:
    unit_note = f", birim {unit}" if unit else ""
    return (
        "/**\n"
        f" * @brief {part} {op_name} sonucu: {info['count']} kanal{unit_note}.\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        f"    unsigned short {info['field']}[{info['count']}];\n"
        "}" + f" {info['ctype']};"
    )


def _bits_range(bits) -> Optional[tuple[int, int]]:
    """'7:4' -> (7, 4); '0' -> (0, 0); cozulemeyen -> None."""
    text = str(bits).strip()
    m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", text)
    if m:
        hi, lo = int(m.group(1)), int(m.group(2))
        return (max(hi, lo), min(hi, lo))
    if re.fullmatch(r"\d+", text):
        return (int(text), int(text))
    return None


@dataclass
class StatusRegPlan:
    """Surucu S<Mod>Status yapisina giren bir durum registeri."""
    name: str
    offset: int
    width: int                              # 8 / 16
    raw_field: str                          # ucStatusLow / usStatusWord
    fields: list[tuple[str, int, int, str]]  # (cname, lo, width, comment)


def status_register_plans(descriptor: dict) -> list[StatusRegPlan]:
    """Durum registerleri: fields tanimli, width<=16, `access: ro` VEYA post_init_status.reg.

    Bit alanlari descriptor bit tanimlariyla birebir; ad cakismasinda register adi one eklenir.
    """
    hint = (descriptor.get("test_hints") or {}).get("post_init_status") or {}
    post = str(hint.get("reg", "") or "")
    used: set[str] = set()
    plans: list[StatusRegPlan] = []
    for rg in descriptor.get("registers", []):
        name = str(rg.get("name", ""))
        width = int(rg.get("width", 8) or 8)
        access = str(rg.get("access", "")).lower()
        if not name or width > 16 or not rg.get("fields"):
            continue
        if not (access == "ro" or name == post):
            continue
        fields: list[tuple[str, int, int, str]] = []
        for f in rg["fields"]:
            rng = _bits_range(f.get("bits"))
            fname = str(f.get("name", ""))
            if rng is None or not fname or rng[0] >= width:
                continue
            cname = "ui" + _pascal_suffix(fname.lower())
            if cname in used:
                cname = "ui" + _pascal_suffix(name.lower()) + _pascal_suffix(fname.lower())
            used.add(cname)
            fields.append((cname, rng[1], rng[0] - rng[1] + 1, f"{name} bit {f.get('bits')}"))
        if not fields:
            continue
        prefix = "uc" if width <= 8 else "us"
        plans.append(StatusRegPlan(
            name=name, offset=int(rg.get("offset", 0)), width=width,
            raw_field=f"{prefix}{_pascal_suffix(name.lower())}", fields=fields))
    return plans


def _status_struct_typedef(module: str, part: str, regs: list[StatusRegPlan]) -> str:
    lines = [
        "/**",
        f" * @brief {part} durum registerleri BIT BIT (descriptor bit tanimlariyla birebir) + ham deger.",
        f" *        {module}StatusRegistersRead() doldurur.",
        " */",
        "typedef struct",
        "{",
    ]
    for reg in regs:
        for cname, _lo, width, comment in reg.fields:
            lines.append(f"    unsigned int {cname} : {width}; /* {comment} */")
    for reg in regs:
        ctype = "unsigned char" if reg.width <= 8 else "unsigned short"
        lines.append(f"    {ctype} {reg.raw_field}; /* ham {reg.name} (0x{reg.offset:02X}) */")
    lines.append("}" + f" S{_pascal_suffix(module)}Status;")
    return "\n".join(lines)


def _status_read_func(module: str, part: str, regs: list[StatusRegPlan], handle_param: str,
                      hvar: str, read_line: Callable[[StatusRegPlan, str], str],
                      wide_line: Optional[Callable[[StatusRegPlan], str]],
                      byte_order: str, inject_mux: Callable[["Emit"], None]) -> CFunc:
    """``<mod>StatusRegistersRead(handle, S<Mod>Status*)``: ham registerler + bit alanlari."""
    e = Emit()
    e.ln("int iStatus;")
    if any(r.width > 8 for r in regs):
        e.ln("unsigned char ucArrBytes[2];")
    e.blank()
    e.open("if (spStatus == NULL)").ln("return XST_FAILURE;").close()
    inject_mux(e)
    for reg in regs:
        if reg.width <= 8:
            e.ln(read_line(reg, f"&spStatus->{reg.raw_field}")).check_status()
        else:
            assert wide_line is not None
            e.ln(wide_line(reg)).check_status()
            hi, lo = ("0", "1") if byte_order == "big" else ("1", "0")
            e.ln(f"spStatus->{reg.raw_field} = (unsigned short)(((unsigned short)ucArrBytes[{hi}U] << 8) | "
                 f"(unsigned short)ucArrBytes[{lo}U]);")
    for reg in regs:
        for cname, lo, width, _comment in reg.fields:
            mask = (1 << width) - 1
            shift = f" >> {lo}U" if lo else ""
            e.ln(f"spStatus->{cname} = (unsigned int)((spStatus->{reg.raw_field}{shift}) & 0x{mask:X}U);")
    e.ln("return XST_SUCCESS;")
    return CFunc(
        name=_func_name(module, "status_registers_read"), ret="int",
        params=[handle_param, f"S{_pascal_suffix(module)}Status* spStatus"], body=e.out(),
        brief=f"Read the {part} status registers into a bit-field struct (raw bytes kept alongside).",
        doxy_params=[(hvar, "Initialized controller handle."), ("spStatus", "Out: status bits + raw registers.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")


def _convert_func(module: str, op_name: str, convert: dict, noun: str) -> tuple[CFunc, str]:
    """Ham kodu muhendislik birimine ceviren STATIK yardimci: ``<mod><Noun>Convert(uiRaw)``.

    Op govdesi yalniz okuma yapar; donusum (mask, isaret genisletme, olcek, ofset, kirpma)
    tek bir fonksiyonda toplanir (kullanici istegi 2026-09-06: LTC2991 voltaj donusumu ayri
    static fonksiyonda). Donus tipi convert.unsigned'a gore unsigned int / int.
    """
    is_unsigned = bool(convert.get("unsigned", False))
    ret = "unsigned int" if is_unsigned else "int"
    cvar = "uiCode" if is_unsigned else "iCode"
    e = Emit()
    e.ln(f"{ret} {cvar};")
    if convert.get("format") == "pmbus_l11":
        e.ln("int iExp;")
        e.ln("long long llValue;")
    e.blank()
    _emit_convert_lines(e, convert, "uiRaw")
    e.ln(f"return {cvar};")
    name = _func_name(module, f"{noun}_convert")
    unit = str(convert.get("unit", "") or "")
    return CFunc(name, ret, ["unsigned int uiRaw"], e.out(), static=True,
                 brief=f"{op_name}: raw code -> {unit or 'engineering unit'}"), name


def _emit_convert_lines(e: "Emit", convert: dict, raw_expr: str) -> None:
    """Fixed-point engineering-unit conversion into the local `iCode`.

    value = sign_extend(raw & mask, signed_bits) * scale_num / scale_den
            + offset, optionally clamped at clamp_min. Integer-only math;
    division truncates toward zero (<=1 output-unit error, documented in the
    descriptor description).

    format: pmbus_l11 decodes PMBus Linear11 instead (5-bit two's complement
    exponent in [15:11], 11-bit two's complement mantissa in [10:0]);
    value = mantissa * scale_num * 2^exponent, computed in 64 bit so large
    positive exponents cannot overflow.
    """
    if convert.get("format") == "pmbus_l11":
        scale_num = int(convert.get("scale_num", 1))
        e.ln(f"iCode = (int)(({raw_expr}) & 0x7FFU);")
        e.open("if (iCode >= 1024)")
        e.ln("iCode -= 2048;  /* mantissa: two's complement, 11 bit */")
        e.close()
        e.ln(f"iExp = (int)((({raw_expr}) >> 11) & 0x1FU);")
        e.open("if (iExp >= 16)")
        e.ln("iExp -= 32;  /* exponent: two's complement, 5 bit */")
        e.close()
        e.ln(f"llValue = (long long)iCode * {scale_num};")
        e.open("if (iExp >= 0)")
        e.ln("llValue = llValue << iExp;")
        e.close()
        e.open("else")
        e.ln("llValue = llValue / (1LL << (-iExp));  /* truncates toward zero */")
        e.close()
        e.ln("iCode = (int)llValue;")
        return
    mask = int(convert.get("mask", 0xFFFF))
    rshift = int(convert.get("rshift", 0))
    signed_bits = int(convert.get("signed_bits", 0))
    scale_num = int(convert.get("scale_num", 1))
    scale_den = int(convert.get("scale_den", 1))
    offset = int(convert.get("offset", 0))
    is_unsigned = bool(convert.get("unsigned", False))
    var = "uiCode" if is_unsigned else "iCode"
    ctype = "unsigned int" if is_unsigned else "int"
    shifted = f"({raw_expr}) >> {rshift}" if rshift else raw_expr
    e.ln(f"{var} = ({ctype})(({shifted}) & {_hexu32(mask)});")
    if signed_bits and not is_unsigned:
        e.open(f"if ({var} >= {1 << (signed_bits - 1)})")
        e.ln(f"{var} -= {1 << signed_bits};  /* two's complement, {signed_bits} bit */")
        e.close()
    if scale_num != 1 or scale_den != 1:
        suffix = "U" if is_unsigned else ""
        e.ln(f"{var} = ({var} * {scale_num}{suffix}) / {scale_den}{suffix};")
    if offset:
        suffix = "U" if is_unsigned else ""
        if offset < 0:
            e.ln(f"{var} -= {-offset}{suffix};")
        else:
            e.ln(f"{var} += {offset}{suffix};")
    if "clamp_min" in convert:
        clamp = int(convert["clamp_min"])
        e.open(f"if ({var} < {clamp})")
        e.ln(f"{var} = {clamp};")
        e.close()


def _scalar_assign_expr(byte_count: int, c_type: str, byte_order: str,
                        pieces: list[dict[str, int]]) -> str:
    cast = "unsigned int" if c_type == "unsigned int" or byte_count > 2 else c_type
    explicit = any(("mask" in p) or ("shift" in p) for p in pieces)
    terms: list[str] = []

    if explicit:
        for p in pieces:
            idx = p["index"]
            mask = p.get("mask", 0xFF)
            right_shift = p.get("right_shift", 0)
            shift = p.get("shift", 0)
            term = f"(({cast})ucArrBytes[{idx}U] & {_hexu32(mask)})"
            if right_shift:
                term = f"({term} >> {right_shift}U)"
            if shift:
                term = f"({term} << {shift}U)"
            terms.append(term)
    else:
        for idx in range(byte_count):
            shift = (8 * idx) if byte_order == "little" else (8 * (byte_count - 1 - idx))
            term = f"({cast})ucArrBytes[{idx}U]"
            if shift:
                term = f"({term} << {shift}U)"
            terms.append(term)

    return " | ".join(terms) if terms else "0U"


def _private_spi_register_init_sequence(module: str, mod: str, words: list[tics.TicsRegisterWord],
                                        model: dict | None = None) -> list[str]:
    if not words:
        return []

    if _is_lmk_byte_register_model(model or {}):
        return _private_spi_byte_init_sequence(module, mod, words)

    seq_name = _static_uint_array_name(module, "InitSequence")
    count_name = f"{mod}_INIT_SEQUENCE_COUNT"
    lines = [
        f"#define {count_name} {len(words)}U",
        "",
        f"static const unsigned int {seq_name}[{count_name}] =",
        "{",
    ]
    for item in words:
        lines.append(
            f"    {tics.c_word(item.word)},  /* address 0x{item.address:X}, value 0x{item.value:X} */"
        )
    lines.extend([
        "};",
        "",
    ])
    return lines


def _private_spi_byte_init_sequence(module: str, mod: str, words: list[tics.TicsRegisterWord]) -> list[str]:
    """TICS Pro export as 3-byte-per-message unsigned char array (saha isteği).

    Each 24-bit register word is split MSB-first into the same 3 bytes the
    SPI write already sends (`ucArrTx[0..2]` in `_spi_register_write_func`);
    only the C source representation changes, not the bytes on the wire.
    """
    seq_name = _static_uchar_array_name(module, "ConfigFile")
    byte_count_name = f"{mod}_CONFIG_FILE_BYTE_COUNT"
    lines = [
        f"#define {byte_count_name} {len(words) * 3}U",
        "",
        "/*",
        " * Format: 3 bytes per message.",
        " *    Byte 0: Address High (bit 7 = R/W, 0 = write)",
        " *    Byte 1: Address Low",
        " *    Byte 2: Data",
        " */",
        f"static const unsigned char {seq_name}[{byte_count_name}] =",
        "{",
    ]
    for item in words:
        byte0, byte1, byte2 = item.bytes_msb_first
        lines.append(
            f"    0x{byte0:02X}, 0x{byte1:02X}, 0x{byte2:02X},"
        )
    lines.extend([
        "};",
        "",
    ])
    return lines


def _int_value(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _generic_i2c_init_writes(device: dict, regs: dict[str, dict]) -> list[dict]:
    config = device.get("config")
    if not isinstance(config, dict):
        return []
    sequence = config.get("init_sequence")
    if not isinstance(sequence, list):
        return []

    writes: list[dict] = []
    for item in sequence:
        if not isinstance(item, dict):
            continue
        reg = item.get("reg")
        if not isinstance(reg, str) or reg not in regs:
            continue
        access = str(regs[reg].get("access", "rw")).lower()
        if "w" not in access:
            continue
        value = _int_value(item.get("value", 0)) & 0xFF
        note = str(item.get("note") or "manual init builder write")
        writes.append({"reg": reg, "value": value, "note": note})
    return writes


# --- mux unit (TCA9548A) ----------------------------------------------------------------

def _mux_unit(mux: dict, controller: dict, descriptor: dict) -> CUnit:
    module = _module_of(mux["part"])
    api = _i2c_api(module, controller)
    hvar = api.hvar
    # Switch adresi PARAMETREDIR (ucSwitchAdres): ayni parcadan N switch tek modul.
    addr_def = "ucSwitchAdres"

    sel = Emit()
    sel.ln("unsigned char ucMask;").ln("int iStatus;").blank()
    sel.ln("ucMask = (unsigned char)(1U << ucChannel);")
    api.send(sel, "&ucMask", 1, addr_def)
    sel.open("if (iStatus != XST_SUCCESS)")
    sel.ln("/* Sessiz hizli fail birakma: hangi switch/kanal dustu logda gorunsun. */")
    sel.ln(f"dbg_printf(DEBUG_LEVEL_ERROR, \"TRACEERR|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d\", {addr_def}, ucChannel, 'm', iStatus);")
    sel.ln("return iStatus;")
    sel.close()
    api.wait_idle(sel, "/* wait for the transfer to complete */")
    sel.ln("return XST_SUCCESS;")
    select = CFunc(
        name=_func_name(module, "channel_select"), ret="int",
        params=[api.param, "unsigned char ucSwitchAdres", "unsigned char ucChannel"], body=sel.out(),
        brief="Enable exactly one downstream channel on the I2C switch.",
        doxy_params=[(hvar, "Initialized I2C controller handle the mux sits on."),
                     ("ucSwitchAdres", "7-bit I2C address of the switch."),
                     ("ucChannel", "Channel index 0..7 to enable.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")

    dis = Emit()
    dis.ln("unsigned char ucMask;").ln("int iStatus;").blank()
    dis.ln("ucMask = 0x00U;")
    api.send(dis, "&ucMask", 1, addr_def)
    dis.open("if (iStatus != XST_SUCCESS)")
    dis.ln(f"dbg_printf(DEBUG_LEVEL_ERROR, \"TRACEERR|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d\", {addr_def}, 0xFFU, 'm', iStatus);")
    dis.ln("return iStatus;")
    dis.close()
    api.wait_idle(dis, "/* wait for the transfer to complete */")
    dis.ln("return XST_SUCCESS;")
    disable = CFunc(
        name=_func_name(module, "channel_disable"), ret="int", params=[api.param, "unsigned char ucSwitchAdres"],
        body=dis.out(), brief="Disable all downstream channels on the I2C switch.",
        doxy_params=[(hvar, "Initialized I2C controller handle the mux sits on."),
                     ("ucSwitchAdres", "7-bit I2C address of the switch.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")

    return CUnit(
        module=module, part=mux["part"], summary=descriptor.get("summary", ""), transport="i2c_mux",
        header_includes=["xil_types.h", api.header],
        driver_includes=[f"{module}.h", "dbg_printf.h", "xparameters.h", "xstatus.h"],
        defines=[],
        funcs=_prune_unused_static_funcs([*api.wrapper_funcs(), select, disable]),
        public_names=[select.name, disable.name])


# --- I2C device unit --------------------------------------------------------------------

def _inject_switch_select(e: "Emit", mux_module: Optional[str]) -> None:
    """Tablo satirinda switch varsa (ucSwitchAdres != 0) kanali sec; yoksa dogrudan gecer."""
    if mux_module is None:
        return
    e.open(f"if ({I2C_DEVICE_VAR}->ucSwitchAdres != 0U)")
    e.ln(f"iStatus = {_func_name(mux_module, 'channel_select')}({I2C_DEVICE_VAR}->spIic, "
         f"{I2C_DEVICE_VAR}->ucSwitchAdres, {I2C_DEVICE_VAR}->ucSwitchKanal);").check_status()
    e.close()


def _i2c_low_level(module: str, api: "_I2cApi", addr_def: str) -> list[CFunc]:
    hvar = api.hvar
    # Basarisizlik noktalari SESSIZ kalmaz (SAHA: DS1682 hizli fail tek
    # "failed" satiriyla dondu, iz/asama yoktu): her NACK/timeout hata
    # kancasina adres+register+asama ile raporlanir.
    def check_traced(e: Emit, reg_expr: str, stage: str) -> None:
        e.open("if (iStatus != XST_SUCCESS)")
        e.ln(f"dbg_printf(DEBUG_LEVEL_ERROR, \"TRACEERR|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d\", {addr_def}, {reg_expr}, '{stage}', iStatus);")
        e.ln("return iStatus;")
        e.close()

    w = Emit()
    w.ln("unsigned char ucArrBuffer[2];").ln("int iStatus;").blank()
    w.ln("ucArrBuffer[0] = ucReg;").ln("ucArrBuffer[1] = ucValue;")
    api.send(w, "ucArrBuffer", 2, addr_def)
    check_traced(w, "ucReg", "w")
    api.wait_idle(w)
    w.ln(f"dbgTraceI2c({addr_def}, ucReg, 'w', &ucValue, 1U);")
    w.ln("return XST_SUCCESS;")
    write = CFunc(_func_name(module, "register_write"), "int",
                  [api.param, "unsigned char ucReg", "unsigned char ucValue"], w.out(), static=True)

    r = Emit()
    r.ln("int iStatus;").blank()
    # AXI IIC (dinamik mod): STOP'lu pointer yazimi + DynRecv IP'de takilir (SAHA:
    # Nexys A7); pointer REPEATED_START ile gonderilir, DynRecv okumayi STOP'la bitirir.
    # PS XIicPs'te STOP'lu akis sahada kanitli - degismez.
    api.send(r, "&ucReg", 1, addr_def, hold_bus=api.is_axi)
    check_traced(r, "ucReg", "p")
    api.wait_idle(r)
    api.recv(r, "ucpValue", 1, addr_def)
    check_traced(r, "ucReg", "r")
    api.wait_idle(r)
    r.ln(f"dbgTraceI2c({addr_def}, ucReg, 'r', ucpValue, 1U);")
    r.ln("return XST_SUCCESS;")
    read = CFunc(_func_name(module, "register_read"), "int",
                 [api.param, "unsigned char ucReg", "unsigned char* ucpValue"], r.out(), static=True)

    # SAHA BULGUSU (2026-07-05): DS1682'de tek pointer + COK BAYTLI recv
    # (blok okuma) aninda dusuyordu; ayni karttaki register snapshot ise
    # register basina TEK baytlik okumayla 21/21 basariliydi. read_registers
    # ardisik REGISTER adresleridir (her baytin kendi adresi var) - blok
    # yerine kanitli tek-bayt okumalarla toplanir.
    once = Emit()
    once.ln("unsigned int uiIndex;")
    once.ln("int iStatus;").blank()
    once.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)")
    once.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, (unsigned char)(ucReg + uiIndex), &ucpBuffer[uiIndex]);")
    once.open("if (iStatus != XST_SUCCESS)").ln("return iStatus;").close()
    once.close()
    once.ln("return XST_SUCCESS;")
    read_once = CFunc(_func_name(module, "registers_read_once"), "int",
                      [api.param, "unsigned char ucReg",
                       "unsigned char* ucpBuffer", "unsigned int uiLength"],
                      once.out(), static=True)

    # GENIS (16-bit+) TEK register: baytlar AYNI adresin icindedir (AD7414/
    # TMP101 TEMPERATURE) - pointer bir kez yazilir, N bayt TEK islemde
    # okunur (sahada kanitli calisan yol). Ardisik-adres tek-bayt yontemi
    # burada YANLIS olur: ikinci bayt bir SONRAKI register'dan gelirdi.
    wide = Emit()
    wide.ln("int iStatus;").blank()
    wide.open("if ((ucpBuffer == NULL) || (uiLength == 0U))")
    wide.ln("return XST_FAILURE;")
    wide.close()
    api.send(wide, "&ucReg", 1, addr_def, hold_bus=api.is_axi)
    check_traced(wide, "ucReg", "p")
    api.wait_idle(wide)
    api.recv(wide, "ucpBuffer", "uiLength", addr_def)
    check_traced(wide, "ucReg", "r")
    api.wait_idle(wide)
    wide.ln(f"dbgTraceI2c({addr_def}, ucReg, 'r', ucpBuffer, uiLength);")
    wide.ln("return XST_SUCCESS;")
    read_wide = CFunc(_func_name(module, "register_read_wide"), "int",
                      [api.param, "unsigned char ucReg",
                       "unsigned char* ucpBuffer", "unsigned int uiLength"],
                      wide.out(), static=True)

    rb = Emit()
    rb.ln("unsigned char ucArrCheck[8];")
    rb.ln("unsigned int uiIndex;")
    rb.ln("unsigned int uiSame;")
    rb.ln("int iStatus;").blank()
    rb.open("if ((ucpBuffer == NULL) || (uiLength == 0U) || (uiLength > 8U))")
    rb.ln("return XST_FAILURE;")
    rb.close()
    rb.ln("/* Sayac kosarken tutarlilik (DS1682 ETC 0.25 s'de bir artar):")
    rb.ln(" * iki gecis karsilastirilir, uyusmazsa ucuncu gecis gecerlidir. */")
    rb.ln(f"iStatus = {_func_name(module, 'registers_read_once')}({hvar}, ucReg, ucpBuffer, uiLength);").check_status()
    rb.ln(f"iStatus = {_func_name(module, 'registers_read_once')}({hvar}, ucReg, ucArrCheck, uiLength);").check_status()
    rb.ln("uiSame = 1U;")
    rb.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)")
    rb.open("if (ucpBuffer[uiIndex] != ucArrCheck[uiIndex])").ln("uiSame = 0U;").close()
    rb.close()
    rb.open("if (uiSame == 0U)")
    rb.ln(f"iStatus = {_func_name(module, 'registers_read_once')}({hvar}, ucReg, ucpBuffer, uiLength);").check_status()
    rb.close()
    rb.ln("return XST_SUCCESS;")
    read_block = CFunc(_func_name(module, "registers_read"), "int",
                       [api.param, "unsigned char ucReg",
                        "unsigned char* ucpBuffer", "unsigned int uiLength"],
                       rb.out(), static=True)
    return [*api.wrapper_funcs(), write, read, read_wide, read_once, read_block]


def convert_config_issue(device: dict, op: dict) -> str | None:
    """`convert.scale_den_config` isteyen op için eksik/geçersiz config anahtarı.

    Kart verisi gerektiren dönüşümler (ör. LTC2945 akımı için şönt direnci)
    payda değerini device.config'ten alır. Anahtar yoksa/pozitif tamsayı
    değilse anahtar adı döner; op açıkça istenmişse çağıran hata verir,
    varsayılan tüm-op listesinde ise sessizce atlanır (dürüst kapı).
    """
    convert = op.get("convert") or {}
    key = convert.get("scale_den_config")
    if not key:
        return None
    raw = (device.get("config") or {}).get(key)
    try:
        value = int(str(raw), 0) if raw is not None else 0
    except (TypeError, ValueError):
        value = 0
    return str(key) if value <= 0 else None


def resolve_convert(device: dict, op: dict) -> dict | None:
    """convert bloğunu device.config referansları çözülmüş kopya olarak döndür."""
    convert = op.get("convert")
    if not convert:
        return None
    key = convert.get("scale_den_config")
    if not key:
        return convert
    resolved = dict(convert)
    resolved["scale_den"] = int(str((device.get("config") or {}).get(key)), 0)
    resolved.pop("scale_den_config", None)
    return resolved


def _check_convert_config(device: dict, op_name: str, op: dict) -> bool:
    """True = op üretilebilir; eksik config'te açık istekse hata, değilse atla."""
    issue = convert_config_issue(device, op)
    if not issue:
        return True
    if device.get("operations_requested"):
        raise CodegenError(
            f"{device.get('id', '?')} {op_name}: device.config.{issue} gerekli "
            f"(örn. LTC2945 akımı için sense_resistor_mohms = şönt direnci, miliohm)")
    return False


def _i2c_device_unit(device: dict, controller: dict, descriptor: dict,
                     mux_module: Optional[str], mux_channel: Optional[int],
                     module: Optional[str] = None) -> CUnit:
    module = module or _module_of(device["part"])
    api = _i2c_device_api(module, controller)
    hvar = api.hvar
    MOD = module.upper()
    addr_def, sclk_def, to_def = f"{I2C_DEVICE_VAR}->ucAdres", f"{MOD}_I2C_SCLK_HZ", f"{MOD}_POLL_TIMEOUT"
    regs = {rg["name"]: rg for rg in descriptor.get("registers", [])}
    instance = controller["instance"]
    byte_order = descriptor.get("transport", {}).get("byte_order", "big")
    # Cihaza ozel init yazimlari TABLODADIR (spCihaz->spInit): surucu config'ten bagimsiz.
    # Profil/config yazimi olan parcada descriptor device_init adimlari yerine tablo kosar.
    profile_writes = [
        *device_profiles.i2c_init_writes(device),
        *_generic_i2c_init_writes(device, regs),
    ]

    defines = [
        (sclk_def, "100000U", "I2C SCL frequency (Hz)"),
        # Her poll denemesi tam bir I2C register okumasıdır (~0.5 ms @100
        # kHz): 1000 deneme ~0.5 s tavan demektir. Onceki 100000U butcesi
        # sahada op basina ~46 s surdu (UI 5 s timeout'unu asar).
        (to_def, "1000U", "poll attempts; each is one I2C register read (~0.5 s cap)"),
    ]
    defines += [(f"{MOD}_REG_{n}", _hexu8(rg["offset"]), "") for n, rg in regs.items()]
    private_decls: list[str] = []

    funcs = _i2c_low_level(module, api, addr_def)
    public: list[str] = []
    public_types: list[str] = []
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    requested = device.get("operations_requested") or list(ops_by_name)

    def inject_mux(e: Emit) -> None:
        _inject_switch_select(e, mux_module)

    # Durum registerleri: S<Mod>Status + <mod>StatusRegistersRead (op'lardan bagimsiz; cit/
    # katmani ve kullanici bunu dogrudan kullanir).
    status_regs = status_register_plans(descriptor)
    if status_regs:
        public_types.append(_status_struct_typedef(module, device["part"], status_regs))
        funcs.append(_status_read_func(
            module, device["part"], status_regs, api.param, hvar,
            lambda reg, target: f"iStatus = {_func_name(module, 'register_read')}({hvar}, {MOD}_REG_{reg.name}, {target});",
            lambda reg: f"iStatus = {_func_name(module, 'register_read_wide')}({hvar}, {MOD}_REG_{reg.name}, ucArrBytes, 2U);",
            byte_order, inject_mux))
        public.append(_func_name(module, "status_registers_read"))

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        if not _check_convert_config(device, op_name, op):
            continue
        returns = op.get("returns", "")
        is_init = op_name == "device_init"
        params = [api.param]
        out_c_type = ""
        out_param = None
        array_info = _array_return_info(module, returns) if returns else None
        if array_info:
            # Dizi donus: surucu KENDI struct'ini doldurur (SLtc2991Voltage.usArrVoltage[8]).
            out_c_type, out_param = array_info["ctype"], array_info["param"]
            params.append(f"{out_c_type}* {out_param}")
            public_types.append(_array_struct_typedef(
                device["part"], op_name, array_info, str((op.get("convert") or {}).get("unit", ""))))
        elif returns:
            out_c_type, out_param = _return_param(op_name, returns)
            params.append(f"{out_c_type}* {out_param}")
        array_target = f"{out_param}->{array_info['field']}" if array_info else out_param

        has_channels = any(s["op"] == "read_channels" for s in op["steps"])
        convert = resolve_convert(device, op)
        scalar_combine = bool(returns) and "[" not in returns
        scalar_read_bytes = 0
        if scalar_combine:
            for step in op["steps"]:
                if step["op"] == "read_register":
                    scalar_read_bytes += 1
                elif step["op"] == "read_registers":
                    scalar_read_bytes += int(step.get("length", 1))
            if scalar_read_bytes > 4:
                raise CodegenError(f"{device['id']} {op_name}: scalar reads are limited to 4 bytes")
        e = Emit()
        # declarations (top of block, embedded C style)
        e.ln("int iStatus;")
        if is_init:
            config_decl = api.config_decl()
            if config_decl:
                e.ln(config_decl)
            e.ln("unsigned int uiIndex;")
        if has_channels:
            e.ln("unsigned char ucIndex;")
        if has_channels:
            e.ln("unsigned char ucMsb;").ln("unsigned char ucLsb;")
        if scalar_read_bytes:
            e.ln("unsigned char ucArrBytes[4];")
        e.blank()
        convert_call = ""
        if convert:
            noun = array_info["noun"].lower() if array_info else (
                op_name[:-5] if op_name.endswith("_read") else op_name)
            convert_fn, convert_call = _convert_func(module, op_name, convert, noun)
            funcs.append(convert_fn)

        if is_init:
            api.emit_init(e, instance, sclk_def)

        inject_mux(e)

        read_seen = 0
        scalar_pieces: list[dict[str, int]] = []
        if is_init:
            e.ln("/* Cihaza ozel init yazimlari tablodan (spec config: profil + init_sequence). */")
            e.open(f"for (uiIndex = 0U; uiIndex < (unsigned int){hvar}->ucInitSayisi; uiIndex++)")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {hvar}->spInit[uiIndex].ucReg, "
                 f"{hvar}->spInit[uiIndex].ucDeger);")
            e.check_status()
            e.close()
        if is_init and profile_writes:
            pass  # descriptor device_init adimlari yerine tablo dizisi (yukarida) kosar
        else:
            for step in op["steps"]:
                sop = step["op"]
                if sop == "comment":
                    e.ln(f"/* {step.get('note', '')} */")
                elif sop == "write_register":
                    e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {MOD}_REG_{step['reg']}, "
                         f"{_hexu8(step.get('value', 0))});").check_status()
                elif sop == "poll":
                    rg = regs.get(step["reg"], {})
                    bit = next((_first_bit(f["bits"]) for f in rg.get("fields", [])
                                if f["name"] == step.get("field")), 0)
                    mask_expr = "(ucPoll & 0x1U)" if bit == 0 else f"((ucPoll >> {bit}) & 0x1U)"
                    e.open_scope()
                    e.ln("unsigned char ucPoll;")
                    e.ln(f"unsigned int uiTimeout = {to_def};  /* deneme sayisi; her deneme bir I2C okumasi */")
                    e.open("do")
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, {MOD}_REG_{step['reg']}, &ucPoll);").check_status()
                    e.open("if (uiTimeout == 0U)").ln("return XST_FAILURE;").close()
                    e.ln("uiTimeout--;")
                    e.close(f" while ({mask_expr} != {step.get('until', 0)}U);")
                    e.close()
                elif sop == "read_register":
                    if scalar_combine:
                        target = f"ucArrBytes[{read_seen}U]"
                        piece = {"index": read_seen}
                        if "mask" in step:
                            piece["mask"] = int(step["mask"])
                        if "shift" in step:
                            piece["shift"] = int(step["shift"])
                        scalar_pieces.append(piece)
                    else:
                        target = "ucMsb" if read_seen == 0 else "ucLsb"
                    read_seen += 1
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, {MOD}_REG_{step['reg']}, &{target});").check_status()
                elif sop == "read_registers":
                    length = int(step.get("length", 1))
                    if not scalar_combine:
                        raise CodegenError(f"{device['id']} {op_name}: read_registers needs a scalar return")
                    # Yol ayrimi hedef registerin GENISLIGIYLE yapilir:
                    # width==8 -> ardisik ayri adresler (DS1682 ETC, LTC2945),
                    #   tek-bayt okumalarla toplanir (blok recv bu kartta dusuyor);
                    # width>8 -> TEK genis register (AD7414/TMP101 TEMPERATURE),
                    #   baytlar ayni adresin icinde: pointer + N bayt TEK islem.
                    step_reg_width = int(regs.get(step["reg"], {}).get("width", 8))
                    read_func = "register_read_wide" if step_reg_width > 8 else "registers_read"
                    e.ln(f"iStatus = {_func_name(module, read_func)}({hvar}, {MOD}_REG_{step['reg']}, "
                         f"&ucArrBytes[{read_seen}U], {length}U);").check_status()
                    read_seen += length
                elif sop == "read_channels":
                    base, count = f"{MOD}_REG_{step['reg']}", step.get("count", 8)
                    e.open(f"for (ucIndex = 0U; ucIndex < {count}U; ucIndex++)")
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, (unsigned char)({base} + (ucIndex * 2U)), &ucMsb);").check_status()
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, (unsigned char)({base} + (ucIndex * 2U) + 1U), &ucLsb);").check_status()
                    if convert:
                        e.ln(f"{array_target}[ucIndex] = (unsigned short){convert_call}("
                             "((unsigned int)ucMsb << 8U) | (unsigned int)ucLsb);")
                    else:
                        e.ln(f"{array_target}[ucIndex] = (unsigned short)(((unsigned short)ucMsb << 8) | (unsigned short)ucLsb);")
                    e.close()

        if scalar_combine and out_param:
            expr = _scalar_assign_expr(read_seen, out_c_type, byte_order, scalar_pieces)
            if convert:
                e.ln(f"*{out_param} = ({out_c_type}){convert_call}((unsigned int)({expr}));")
            else:
                e.ln(f"*{out_param} = ({out_c_type})({expr});")
        e.ln("return XST_SUCCESS;")

        doxy_params = [(I2C_DEVICE_VAR, "I2C cihaz tablosu satiri (bus ornegi, adres, switch).")]
        if out_param:
            doxy_params.append((out_param, f"Out parameter: {returns}."))
        funcs.append(CFunc(
            name=_func_name(module, op_name), ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params, doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(_func_name(module, op_name))

    includes_c = [f"{module}.h", "dbg_printf.h", "xparameters.h", "xstatus.h"]
    if mux_module:
        includes_c.insert(1, f"{mux_module}.h")
    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="i2c",
        header_includes=["xil_types.h", api.header, f"{I2C_TABLE_MODULE}.h"], driver_includes=includes_c,
        defines=defines, funcs=_prune_unused_static_funcs(funcs), public_names=public,
        private_decls=private_decls, public_types=public_types)


def _i2c_eeprom_unit(device: dict, controller: dict, descriptor: dict,
                     mux_module: Optional[str], mux_channel: Optional[int],
                     module: Optional[str] = None) -> CUnit:
    module = module or _module_of(device["part"])
    api = _i2c_device_api(module, controller)
    hvar = api.hvar
    MOD = module.upper()
    instance = controller["instance"]
    addr_def = f"{I2C_DEVICE_VAR}->ucAdres"
    sclk_def = f"{MOD}_I2C_SCLK_HZ"
    to_def = f"{MOD}_POLL_TIMEOUT"
    size_def = f"{MOD}_MEMORY_SIZE_BYTES"
    page_def = f"{MOD}_PAGE_SIZE_BYTES"
    memory = descriptor.get("memory", {})
    size_bytes = int(memory.get("size_bytes", 4096))
    page_size = int(memory.get("page_size", 32))

    defines = [
        (sclk_def, "100000U", "I2C SCL frequency (Hz)"),
        # ACK poll denemesi kisa bir adres yazimidir (~0.2 ms); EEPROM write
        # cycle max ~5 ms oldugundan 1000 deneme (>=100 ms) bol tavandir.
        (to_def, "1000U", "ACK poll attempts; each is one short I2C write"),
        (size_def, f"{size_bytes}U", "EEPROM memory size"),
        (page_def, f"{page_size}U", "EEPROM physical page size"),
    ]

    def inject_mux(e: Emit) -> None:
        _inject_switch_select(e, mux_module)

    funcs: list[CFunc] = [*api.wrapper_funcs()]
    public: list[str] = []

    init = Emit()
    init.ln("int iStatus;")
    config_decl = api.config_decl()
    if config_decl:
        init.ln(config_decl)
    init.blank()
    # Paylaşılan/başlatılmış denetleyicide yeniden init yok (test bench).
    api.emit_init(init, instance, sclk_def)
    init.ln("return XST_SUCCESS;")
    funcs.append(CFunc(
        name=_func_name(module, "device_init"), ret="int", params=[api.param], body=init.out(),
        brief="Initialize the I2C controller for EEPROM access.",
        doxy_params=[("spCihaz", "I2C cihaz tablosu satiri.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code."))
    public.append(_func_name(module, "device_init"))

    ack = Emit()
    ack.ln("unsigned char ucArrAddress[2];")
    ack.ln("unsigned int uiTimeout;")
    ack.ln("int iStatus;")
    ack.blank()
    ack.ln("ucArrAddress[0] = (unsigned char)((uiAddress >> 8U) & 0x0FU);")
    ack.ln("ucArrAddress[1] = (unsigned char)(uiAddress & 0xFFU);")
    ack.ln(f"uiTimeout = {to_def};")
    ack.open("do")
    api.send(ack, "ucArrAddress", 2, addr_def)
    ack.open("if (iStatus == XST_SUCCESS)")
    api.wait_idle(ack)
    ack.ln("return XST_SUCCESS;")
    ack.close()
    ack.open("if (uiTimeout == 0U)").ln("return XST_FAILURE;").close()
    ack.ln("uiTimeout--;")
    ack.close(" while (iStatus != XST_SUCCESS);")
    ack.ln("return XST_FAILURE;")
    funcs.append(CFunc(
        name=_func_name(module, "ack_poll"), ret="int",
        params=[api.param, "unsigned int uiAddress"], body=ack.out(),
        brief="Poll until the EEPROM internal write cycle accepts I2C traffic again.",
        doxy_params=[("spCihaz", "I2C cihaz tablosu satiri."), ("uiAddress", "Word address used for the harmless pointer write.")],
        doxy_return="XST_SUCCESS when the EEPROM acknowledges, else XST_FAILURE.", static=True))

    read = Emit()
    read.ln("unsigned char ucArrAddress[2];")
    read.ln("int iStatus;")
    read.blank()
    read.open(f"if ((ucpBuffer == NULL) || (uiLength == 0U) || (uiAddress >= {size_def}) || ((uiAddress + uiLength) > {size_def}))")
    read.ln("return XST_FAILURE;")
    read.close()
    inject_mux(read)
    read.ln("ucArrAddress[0] = (unsigned char)((uiAddress >> 8U) & 0x0FU);")
    read.ln("ucArrAddress[1] = (unsigned char)(uiAddress & 0xFFU);")
    api.send(read, "ucArrAddress", 2, addr_def, hold_bus=api.is_axi).check_status()
    api.wait_idle(read)
    api.recv(read, "ucpBuffer", "uiLength", addr_def).check_status()
    api.wait_idle(read)
    read.ln("return XST_SUCCESS;")
    funcs.append(CFunc(
        name=_func_name(module, "data_read"), ret="int",
        params=[api.param, "unsigned int uiAddress", "unsigned char* ucpBuffer", "unsigned int uiLength"],
        body=read.out(),
        brief="Read bytes from the EEPROM using random-read addressing followed by sequential read.",
        doxy_params=[("spCihaz", "I2C cihaz tablosu satiri."), ("uiAddress", "12-bit EEPROM word address."),
                     ("ucpBuffer", "Output buffer."), ("uiLength", "Number of bytes to read.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code."))
    public.append(_func_name(module, "data_read"))

    byte = Emit()
    byte.ln("unsigned char ucArrBuffer[3];")
    byte.ln("int iStatus;")
    byte.blank()
    byte.open(f"if (uiAddress >= {size_def})").ln("return XST_FAILURE;").close()
    inject_mux(byte)
    byte.ln("ucArrBuffer[0] = (unsigned char)((uiAddress >> 8U) & 0x0FU);")
    byte.ln("ucArrBuffer[1] = (unsigned char)(uiAddress & 0xFFU);")
    byte.ln("ucArrBuffer[2] = ucValue;")
    api.send(byte, "ucArrBuffer", 3, addr_def).check_status()
    api.wait_idle(byte)
    byte.ln(f"iStatus = {_func_name(module, 'ack_poll')}({hvar}, uiAddress);").check_status()
    byte.ln("return XST_SUCCESS;")
    funcs.append(CFunc(
        name=_func_name(module, "byte_write"), ret="int",
        params=[api.param, "unsigned int uiAddress", "unsigned char ucValue"],
        body=byte.out(),
        brief="Write one EEPROM byte and poll until the internal write cycle finishes.",
        doxy_params=[("spCihaz", "I2C cihaz tablosu satiri."), ("uiAddress", "12-bit EEPROM word address."),
                     ("ucValue", "Byte value to program.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code."))
    public.append(_func_name(module, "byte_write"))

    page = Emit()
    page.ln("unsigned char ucArrBuffer[34];")
    page.ln("unsigned int uiIndex;")
    page.ln("int iStatus;")
    page.blank()
    page.open(f"if ((ucpBuffer == NULL) || (uiLength == 0U) || (uiLength > {page_def}) || (uiAddress >= {size_def}) || ((uiAddress + uiLength) > {size_def}))")
    page.ln("return XST_FAILURE;")
    page.close()
    page.open(f"if (((uiAddress % {page_def}) + uiLength) > {page_def})")
    page.ln("return XST_FAILURE;")
    page.close()
    inject_mux(page)
    page.ln("ucArrBuffer[0] = (unsigned char)((uiAddress >> 8U) & 0x0FU);")
    page.ln("ucArrBuffer[1] = (unsigned char)(uiAddress & 0xFFU);")
    page.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)")
    page.ln("ucArrBuffer[uiIndex + 2U] = ucpBuffer[uiIndex];")
    page.close()
    api.send(page, "ucArrBuffer", "(uiLength + 2U)", addr_def).check_status()
    api.wait_idle(page)
    page.ln(f"iStatus = {_func_name(module, 'ack_poll')}({hvar}, uiAddress);").check_status()
    page.ln("return XST_SUCCESS;")
    funcs.append(CFunc(
        name=_func_name(module, "page_write"), ret="int",
        params=[api.param, "unsigned int uiAddress", "const unsigned char* ucpBuffer", "unsigned int uiLength"],
        body=page.out(),
        brief="Write up to one EEPROM page without crossing a physical page boundary.",
        doxy_params=[("spCihaz", "I2C cihaz tablosu satiri."), ("uiAddress", "12-bit EEPROM word address."),
                     ("ucpBuffer", "Input buffer."), ("uiLength", "Number of bytes to write, maximum one page.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code."))
    public.append(_func_name(module, "page_write"))

    includes_c = [f"{module}.h", "xparameters.h", "xstatus.h"]
    if mux_module:
        includes_c.insert(1, f"{mux_module}.h")
    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="i2c_eeprom",
        header_includes=["xil_types.h", api.header, f"{I2C_TABLE_MODULE}.h"], driver_includes=includes_c,
        defines=defines, funcs=_prune_unused_static_funcs(funcs), public_names=public)


# --- SPI device unit (NOR flash) --------------------------------------------------------

def _spi_low_level(module: str, htype: str, hvar: str, sel_def: str, max_def: str) -> list[CFunc]:
    send = Emit()
    send.ln("unsigned char ucArrTx[1];")
    if _is_qspipsu(htype):
        send.ln("XQspiPsu_Msg sArrMessage[1];")
    send.ln("int iStatus;")
    send.blank()
    send.ln("ucArrTx[0] = ucOpcode;")
    if _is_qspipsu(htype):
        send.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        send.ln("sArrMessage[0].RxBfrPtr = NULL;")
        send.ln("sArrMessage[0].ByteCount = 1U;")
        send.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        send.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        send.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);").check_status()
    else:
        _spi_select(send, htype, hvar, sel_def)
        _spi_transfer(send, htype, hvar, "ucArrTx", "NULL", "1")
    send.ln("dbgTraceSpi(0U, ucArrTx, NULL, 1U);")
    send.ln("return XST_SUCCESS;")
    f_send = CFunc(_func_name(module, "command_send"), "int",
                   [f"{htype}* {hvar}", "unsigned char ucOpcode"], send.out(), static=True)

    rd = Emit()
    rd.ln("unsigned char ucArrTx[" + max_def + "];")
    if _is_qspipsu(htype):
        # RX DMA hedefi: driver Xil_DCacheInvalidateRange uygular; tampon
        # cache-line (64B) hizali olmazsa komsu stack verisi bozulabilir
        # (resmi flash orneklerindeki aligned(64) kaligi).
        rd.ln("unsigned char ucArrRx[" + max_def + "] __attribute__((aligned(64)));")
        rd.ln("XQspiPsu_Msg sArrMessage[2];")
    else:
        rd.ln("unsigned char ucArrRx[" + max_def + "];")
    rd.ln("unsigned int uiIndex;").ln("unsigned int uiHeader;").ln("int iStatus;").blank()
    rd.ln("uiHeader = 1U + (unsigned int)ucAddrBytes;")
    rd.open(f"if ((uiHeader + uiLength) > (unsigned int){max_def})").ln("return XST_FAILURE;").close()
    rd.ln("ucArrTx[0] = ucOpcode;")
    rd.open("for (uiIndex = 0U; uiIndex < (unsigned int)ucAddrBytes; uiIndex++)")
    rd.ln("ucArrTx[1U + uiIndex] = (unsigned char)((uiAddress >> (8U * ((unsigned int)ucAddrBytes - 1U - uiIndex))) & 0xFFU);")
    rd.close()
    if _is_qspipsu(htype):
        # SAHA BULGUSU (2026-07-05): TEK mesajda TX|RX kombine + DMA yolu
        # (toplam >= 8 bayt) KILITLENIR: XQspiPsu_SetupRxDma 4'e
        # bolunmeyen uzunlukta Msg->ByteCount'u kirpar (or. 9->8) ama TX
        # kurulumu 9 bayti yukledi - tek ortak ByteCount iki yonu birden
        # temsil edemez (id_read'in calismasi <8 baytin IO moduna
        # dusmesindendir). Resmi surucu akisi: cmd+addr TX-only mesaj,
        # veri RX-only mesaj; CS iki giris boyunca asserted kalir.
        rd.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        rd.ln("sArrMessage[0].RxBfrPtr = NULL;")
        rd.ln("sArrMessage[0].ByteCount = uiHeader;")
        rd.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        rd.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        rd.ln("sArrMessage[1].TxBfrPtr = NULL;")
        rd.ln("sArrMessage[1].RxBfrPtr = ucArrRx;")
        rd.ln("sArrMessage[1].ByteCount = uiLength;")
        rd.ln("sArrMessage[1].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        rd.ln("sArrMessage[1].Flags = XQSPIPSU_MSG_FLAG_RX;")
        # Dual-parallel (iki flash) modunda VERI fazi iki yongaya seritlenir:
        # STRIPE yalniz veri RX mesajina, yalniz ConnectionMode PARALLEL iken
        # eklenir - komut/adres/dummy'ye eklenmez (resmi Xilinx qspipsu flash
        # ornegi FlashRead ile birebir; SAHA 2026-07-08: stripe'siz okumada
        # dual-parallel byte'lari yanlis birlesiyordu). Single flash'ta kosul
        # false, davranis degismez.
        rd.open(f"if ({hvar}->Config.ConnectionMode == XQSPIPSU_CONNECTION_MODE_PARALLEL)")
        rd.ln("sArrMessage[1].Flags |= XQSPIPSU_MSG_FLAG_STRIPE;")
        rd.close()
        rd.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, 2U);").check_status()
        rd.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucpBuffer[uiIndex] = ucArrRx[uiIndex];").close()
        rd.ln("dbgTraceSpi(0U, ucArrTx, NULL, uiHeader);")
        rd.ln("dbgTraceSpi(0U, NULL, ucArrRx, uiLength);")
    else:
        rd.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucArrTx[uiHeader + uiIndex] = 0x00U;").close()
        _spi_select(rd, htype, hvar, sel_def)
        _spi_transfer(rd, htype, hvar, "ucArrTx", "ucArrRx", "uiHeader + uiLength")
        rd.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucpBuffer[uiIndex] = ucArrRx[uiHeader + uiIndex];").close()
        rd.ln("dbgTraceSpi(0U, ucArrTx, ucArrRx, uiHeader + uiLength);")
    rd.ln("return XST_SUCCESS;")
    f_read = CFunc(_func_name(module, "command_read"), "int",
                   [f"{htype}* {hvar}", "unsigned char ucOpcode", "unsigned int uiAddress",
                    "unsigned char ucAddrBytes", "unsigned char* ucpBuffer", "unsigned int uiLength"],
                   rd.out(), static=True)

    wr = Emit()
    wr.ln("unsigned char ucArrTx[" + max_def + "];")
    if _is_qspipsu(htype):
        wr.ln("XQspiPsu_Msg sArrMessage[2];")
        wr.ln("unsigned int uiMsgCount;")
    wr.ln("unsigned int uiIndex;").ln("unsigned int uiHeader;")
    wr.ln("int iStatus;")
    wr.blank()
    wr.ln("uiHeader = 1U + (unsigned int)ucAddrBytes;")
    wr.open(f"if ((uiHeader + uiLength) > (unsigned int){max_def})").ln("return XST_FAILURE;").close()
    wr.ln("ucArrTx[0] = ucOpcode;")
    wr.open("for (uiIndex = 0U; uiIndex < (unsigned int)ucAddrBytes; uiIndex++)")
    wr.ln("ucArrTx[1U + uiIndex] = (unsigned char)((uiAddress >> (8U * ((unsigned int)ucAddrBytes - 1U - uiIndex))) & 0xFFU);")
    wr.close()
    wr.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucArrTx[uiHeader + uiIndex] = ucpData[uiIndex];").close()
    if _is_qspipsu(htype):
        # Resmi flash write akisi: komut+adres AYRI TX mesaj, veri payload'i
        # AYRI TX mesaj. Dual-parallel'de STRIPE yalniz veri mesajina ve
        # yalniz ConnectionMode PARALLEL iken eklenir (komut/adres seritlenmez
        # - resmi qspipsu FlashWrite ile birebir). Verisiz (uiLength==0)
        # cagrilarda tek mesaj gonderilir.
        wr.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        wr.ln("sArrMessage[0].RxBfrPtr = NULL;")
        wr.ln("sArrMessage[0].ByteCount = uiHeader;")
        wr.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        wr.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        wr.ln("uiMsgCount = 1U;")
        wr.open("if (uiLength > 0U)")
        wr.ln("sArrMessage[1].TxBfrPtr = &ucArrTx[uiHeader];")
        wr.ln("sArrMessage[1].RxBfrPtr = NULL;")
        wr.ln("sArrMessage[1].ByteCount = uiLength;")
        wr.ln("sArrMessage[1].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        wr.ln("sArrMessage[1].Flags = XQSPIPSU_MSG_FLAG_TX;")
        wr.open(f"if ({hvar}->Config.ConnectionMode == XQSPIPSU_CONNECTION_MODE_PARALLEL)")
        wr.ln("sArrMessage[1].Flags |= XQSPIPSU_MSG_FLAG_STRIPE;")
        wr.close()
        wr.ln("uiMsgCount = 2U;")
        wr.close()
        wr.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, uiMsgCount);").check_status()
    else:
        _spi_select(wr, htype, hvar, sel_def)
        _spi_transfer(wr, htype, hvar, "ucArrTx", "NULL", "uiHeader + uiLength")
    wr.ln("dbgTraceSpi(0U, ucArrTx, NULL, uiHeader + uiLength);")
    wr.ln("return XST_SUCCESS;")
    f_write = CFunc(_func_name(module, "command_write"), "int",
                    [f"{htype}* {hvar}", "unsigned char ucOpcode", "unsigned int uiAddress",
                     "unsigned char ucAddrBytes", "const unsigned char* ucpData", "unsigned int uiLength"],
                    wr.out(), static=True)
    return [f_send, f_read, f_write]


def _spi_register_write_func(module: str, htype: str, hvar: str, sel_def: str, frame_def: str) -> CFunc:
    wr = Emit()
    wr.ln(f"unsigned char ucArrTx[{frame_def}];")
    if _is_qspipsu(htype):
        wr.ln("XQspiPsu_Msg sArrMessage[1];")
    wr.ln("int iStatus;")
    wr.blank()
    wr.ln("ucArrTx[0] = (unsigned char)((uiWord >> 16U) & 0xFFU);")
    wr.ln("ucArrTx[1] = (unsigned char)((uiWord >> 8U) & 0xFFU);")
    wr.ln("ucArrTx[2] = (unsigned char)(uiWord & 0xFFU);")
    if _is_qspipsu(htype):
        wr.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        wr.ln("sArrMessage[0].RxBfrPtr = NULL;")
        wr.ln(f"sArrMessage[0].ByteCount = {frame_def};")
        wr.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        wr.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        wr.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);").check_status()
    else:
        _spi_select(wr, htype, hvar, sel_def)
        _spi_transfer(wr, htype, hvar, "ucArrTx", "NULL", frame_def)
    wr.ln(f"dbgTraceSpi({sel_def}, ucArrTx, NULL, {frame_def});")
    wr.ln("return XST_SUCCESS;")
    return CFunc(
        _func_name(module, "register_write"),
        "int",
        [f"{htype}* {hvar}", "unsigned int uiWord"],
        wr.out(),
        static=True,
    )


def _spi_register_read_func(module: str, htype: str, hvar: str, sel_def: str,
                            frame_def: str, model: dict) -> CFunc:
    frame_bits = int(model.get("frame_bits", 24) or 24)
    address_bits = int(model.get("address_bits", 15) or 15)
    address_shift = int(model.get("address_shift", 8) or 8)
    rw_bit = int(model.get("rw_bit", frame_bits - 1) or (frame_bits - 1))
    write_value = int(model.get("write_value", 0) or 0)
    read_value = 0 if write_value else 1
    address_mask = (1 << address_bits) - 1

    rd = Emit()
    rd.ln(f"unsigned char ucArrTx[{frame_def}];")
    rd.ln(f"unsigned char ucArrRx[{frame_def}];")
    rd.ln("unsigned int uiWord;")
    rd.ln("int iStatus;")
    if _is_qspipsu(htype):
        rd.ln("XQspiPsu_Msg sArrMessage[1];")
    rd.blank()
    rd.open("if (ucpValue == NULL)").ln("return XST_FAILURE;").close()
    rd.ln(
        f"uiWord = ((unsigned int){read_value}U << {rw_bit}U) | "
        f"(((unsigned int)uiReg & {_hexu32(address_mask)}) << {address_shift}U);"
    )
    rd.ln("ucArrTx[0] = (unsigned char)((uiWord >> 16U) & 0xFFU);")
    rd.ln("ucArrTx[1] = (unsigned char)((uiWord >> 8U) & 0xFFU);")
    rd.ln("ucArrTx[2] = (unsigned char)(uiWord & 0xFFU);")
    rd.ln("ucArrRx[0] = 0U;")
    rd.ln("ucArrRx[1] = 0U;")
    rd.ln("ucArrRx[2] = 0U;")
    if _is_qspipsu(htype):
        rd.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        rd.ln("sArrMessage[0].RxBfrPtr = ucArrRx;")
        rd.ln(f"sArrMessage[0].ByteCount = {frame_def};")
        rd.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        rd.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX | XQSPIPSU_MSG_FLAG_RX;")
        rd.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);").check_status()
    else:
        _spi_select(rd, htype, hvar, sel_def)
        _spi_transfer(rd, htype, hvar, "ucArrTx", "ucArrRx", frame_def)
    rd.ln(f"dbgTraceSpi({sel_def}, ucArrTx, ucArrRx, {frame_def});")
    rd.ln("*ucpValue = ucArrRx[2];")
    rd.ln("return XST_SUCCESS;")
    return CFunc(
        _func_name(module, "register_read"),
        "int",
        [f"{htype}* {hvar}", "unsigned int uiReg", "unsigned char* ucpValue"],
        rd.out(),
        static=True,
    )


def _delay_func(module: str) -> CFunc:
    body = Emit()
    body.ln("unsigned int uiIndex;")
    body.ln("volatile unsigned int uiDelay;")
    body.blank()
    body.open("for (uiIndex = 0U; uiIndex < uiMs; uiIndex++)")
    body.open("for (uiDelay = 0U; uiDelay < 100000U; uiDelay++)")
    body.close()
    body.close()
    return CFunc(
        _func_name(module, "delay_ms"),
        "void",
        ["unsigned int uiMs"],
        body.out(),
        static=True,
    )


def _spi_register_device_unit(device: dict, controller: dict, descriptor: dict,
                              module: Optional[str] = None) -> CUnit:
    module = module or _module_of(device["part"])
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    attach = device["attach"]
    sel_def = f"{MOD}_SPI_SELECT"
    frame_def = f"{MOD}_SPI_FRAME_BYTES"
    sck_def = f"{MOD}_SPI_MAX_SCK_HZ"
    instance = controller["instance"]
    model = tics.register_model(descriptor)
    words = tics.decode_words(tics.normalize_words(device.get("config")), model)
    byte_config = _is_lmk_byte_register_model(model)
    seq_name = (
        _static_uchar_array_name(module, "ConfigFile") if byte_config
        else _static_uint_array_name(module, "InitSequence")
    )
    count_def = f"{MOD}_CONFIG_FILE_BYTE_COUNT" if byte_config else f"{MOD}_INIT_SEQUENCE_COUNT"
    rewrite_delay_ms = int(model.get("rewrite_last_address_after_ms", 0) or 0)
    rewrite_addr = model.get("rewrite_last_address")
    rewrite_word = None
    if rewrite_delay_ms > 0 and rewrite_addr is not None:
        for item in words:
            if item.address == int(rewrite_addr):
                rewrite_word = item

    defines = [
        (sel_def, f"{int(attach.get('spi_chip_select', 0))}U", "SPI slave select"),
        (frame_def, "3U", "SPI register frame length"),
        (sck_def, f"{int(model.get('max_sck_hz', 0) or 0)}U", "datasheet maximum SPI clock"),
    ]
    defines += [
        (f"{MOD}_REG_{rg['name']}", _hexu32(int(rg["offset"])), rg.get("description", "register offset"))
        for rg in descriptor.get("registers", [])
        if "name" in rg and "offset" in rg
    ]
    if rewrite_word is not None:
        defines.append((f"{MOD}_POST_INIT_DELAY_MS", f"{rewrite_delay_ms}U", "delay before post-init calibration write"))

    private_decls = _private_spi_register_init_sequence(module, MOD, words, model)
    requested = device.get("operations_requested") or [op["name"] for op in descriptor["operations"]]
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    needs_register_read = any(
        any(step.get("op") == "read_register" for step in ops_by_name.get(op_name, {}).get("steps", []))
        for op_name in requested
    )

    status_regs = [r for r in status_register_plans(descriptor) if r.width <= 8]
    funcs = [_spi_register_write_func(module, htype, hvar, sel_def, frame_def)]
    if needs_register_read or status_regs:
        funcs.append(_spi_register_read_func(module, htype, hvar, sel_def, frame_def, model))
    if rewrite_word is not None:
        funcs.append(_delay_func(module))

    public: list[str] = []
    public_types: list[str] = []
    if status_regs:
        public_types.append(_status_struct_typedef(module, device["part"], status_regs))
        funcs.append(_status_read_func(
            module, device["part"], status_regs, f"{htype}* {hvar}", hvar,
            lambda reg, target: f"iStatus = {_func_name(module, 'register_read')}({hvar}, {MOD}_REG_{reg.name}, {target});",
            None, "big", lambda e: None))
        public.append(_func_name(module, "status_registers_read"))

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        returns = op.get("returns", "")
        is_init = op_name == "device_init"

        e = Emit()
        e.ln("int iStatus;")
        out_c_type = ""
        out_param = None
        scalar_combine = bool(returns) and "[" not in returns
        read_seen = 0
        scalar_pieces: list[dict[str, int]] = []
        if returns:
            out_c_type, out_param = _return_param(op_name, returns)
        if is_init:
            e.ln(f"{htype}_Config* spConfig;")
        if is_init and words:
            e.ln("unsigned int uiIndex;")
        if scalar_combine:
            e.ln("unsigned char ucArrBytes[4];")
        e.blank()

        if out_param:
            e.open(f"if ({out_param} == NULL)").ln("return XST_FAILURE;").close()

        if is_init:
            _spi_emit_init(e, htype, hvar, instance)

        if is_init and words and byte_config:
            e.open(f"for (uiIndex = 0U; uiIndex < {count_def}; uiIndex += 3U)")
            e.ln(
                f"iStatus = {_func_name(module, 'register_write')}({hvar}, "
                f"((unsigned int){seq_name}[uiIndex] << 16U) | "
                f"((unsigned int){seq_name}[uiIndex + 1U] << 8U) | "
                f"(unsigned int){seq_name}[uiIndex + 2U]);"
            ).check_status()
            e.close()
        elif is_init and words:
            e.open(f"for (uiIndex = 0U; uiIndex < {count_def}; uiIndex++)")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {seq_name}[uiIndex]);").check_status()
            e.close()
        if is_init and rewrite_word is not None:
            e.ln(f"{_func_name(module, 'delay_ms')}({MOD}_POST_INIT_DELAY_MS);")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {tics.c_word(rewrite_word.word)});").check_status()
        if not is_init:
            if not scalar_combine:
                continue
            for step in op["steps"]:
                sop = step.get("op")
                if sop == "comment":
                    e.ln(f"/* {step.get('note', '')} */")
                elif sop == "read_register":
                    piece = {"index": read_seen}
                    if "mask" in step:
                        piece["mask"] = int(step["mask"])
                    if "right_shift" in step:
                        piece["right_shift"] = int(step["right_shift"])
                    if "shift" in step:
                        piece["shift"] = int(step["shift"])
                    scalar_pieces.append(piece)
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, {MOD}_REG_{step['reg']}, &ucArrBytes[{read_seen}U]);").check_status()
                    read_seen += 1
            if out_param:
                expr = _scalar_assign_expr(
                    read_seen,
                    out_c_type,
                    descriptor.get("transport", {}).get("byte_order", "big"),
                    scalar_pieces,
                )
                e.ln(f"*{out_param} = ({out_c_type})({expr});")

        e.ln("return XST_SUCCESS;")
        params = [f"{htype}* {hvar}"]
        if out_param:
            params.append(f"{out_c_type}* {out_param}")
        doxy_params = [(
            hvar,
            "Initialized SPI controller handle."
            if not is_init
            else "Uninitialized SPI controller handle; this routine initializes it.",
        )]
        if out_param:
            doxy_params.append((out_param, f"Out parameter: {returns}."))

        funcs.append(CFunc(
            name=_func_name(module, op_name),
            ret="int",
            params=params,
            body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params,
            doxy_return="XST_SUCCESS on success, else an XST_* error code.",
        ))
        public.append(_func_name(module, op_name))

    return CUnit(
        module=module,
        part=device["part"],
        summary=descriptor.get("summary", ""),
        transport="spi",
        header_includes=["xil_types.h", _spi_header_for(htype)],
        driver_includes=[f"{module}.h", "dbg_printf.h", "xparameters.h", "xstatus.h"],
        defines=defines,
        funcs=_prune_unused_static_funcs(funcs),
        public_names=public,
        private_decls=private_decls,
        public_types=public_types,
    )


def _spi_device_unit(device: dict, controller: dict, descriptor: dict,
                     module: Optional[str] = None) -> CUnit:
    module = module or _module_of(device["part"])
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    attach = device["attach"]
    sel_def, max_def = f"{MOD}_SPI_SELECT", f"{MOD}_SPI_MAX_TRANSFER"
    instance = controller["instance"]
    cmds = {c["name"]: c for c in descriptor.get("commands", [])}

    defines = [
        (sel_def, f"{int(attach.get('spi_chip_select', 0))}U", "SPI slave select"),
        (max_def, "264U", "max single transfer (opcode + 4 addr + 256 data)"),
    ]
    defines += [(f"{MOD}_CMD_{n}", _hexu8(c["opcode"]), c.get("description", ""))
                for n, c in cmds.items()]

    funcs = _spi_low_level(module, htype, hvar, sel_def, max_def)
    public: list[str] = []
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    requested = device.get("operations_requested") or list(ops_by_name)

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        is_init = op_name == "device_init"
        # Find the primary command-address step (if any) to derive parameters.
        rca = next((s for s in op["steps"] if s["op"] == "read_command_address"), None)
        wca = next((s for s in op["steps"] if s["op"] == "write_command_address"), None)
        params = [f"{htype}* {hvar}"]
        out_obj = op_name.split("_")[0]
        addr_param = data_param = len_param = buf_param = None

        if rca is not None:
            cmd = cmds[rca["cmd"]]
            if cmd["address_bytes"] > 0:
                addr_param = "uiAddress"
                params.append("unsigned int uiAddress")
            if "length" in rca:                       # fixed-length read (e.g. RDID)
                buf_param = f"ucp{_pascal_suffix(out_obj)}"
                params.append(f"unsigned char* {buf_param}")
            else:
                buf_param, len_param = "ucpBuffer", "uiLength"
                params += ["unsigned char* ucpBuffer", "unsigned int uiLength"]
        elif wca is not None:
            cmd = cmds[wca["cmd"]]
            addr_param = "uiAddress"
            params.append("unsigned int uiAddress")
            if wca.get("length") == 0:                # no data payload (erase)
                pass
            else:
                data_param, len_param = "ucpData", "uiLength"
                params += ["const unsigned char* ucpData", "unsigned int uiLength"]

        e = Emit()
        e.ln("int iStatus;")
        if is_init:
            e.ln(f"{htype}_Config* spConfig;")
        e.blank()

        if is_init:
            _spi_emit_init(e, htype, hvar, instance)

        for step in op["steps"]:
            sop = step["op"]
            if sop == "comment":
                e.ln(f"/* {step.get('note', '')} */")
            elif sop == "send_command":
                e.ln(f"iStatus = {_func_name(module, 'command_send')}({hvar}, {MOD}_CMD_{step['cmd']});").check_status()
            elif sop == "read_command_address":
                cmd = cmds[step["cmd"]]
                addr_expr = addr_param if addr_param else "0U"
                length_expr = f"{step['length']}U" if "length" in step else len_param
                e.ln(f"iStatus = {_func_name(module, 'command_read')}({hvar}, {MOD}_CMD_{step['cmd']}, "
                     f"{addr_expr}, {cmd['address_bytes']}U, {buf_param}, {length_expr});").check_status()
            elif sop == "write_command_address":
                cmd = cmds[step["cmd"]]
                if step.get("length") == 0:
                    data_expr, length_expr = "NULL", "0U"
                else:
                    data_expr, length_expr = data_param, len_param
                e.ln(f"iStatus = {_func_name(module, 'command_write')}({hvar}, {MOD}_CMD_{step['cmd']}, "
                     f"{addr_param}, {cmd['address_bytes']}U, {data_expr}, {length_expr});").check_status()

        e.ln("return XST_SUCCESS;")

        _desc = {
            "uiAddress": "Byte address within the flash.",
            "ucpBuffer": "Out: receive buffer (uiLength bytes).",
            "uiLength": "Number of data bytes to transfer.",
            "ucpData": "Source data buffer to program.",
            buf_param or "": f"Out: {out_obj} bytes.",
        }
        doxy_params = [(hvar, "Initialized SPI controller handle.")]
        for p in (addr_param, buf_param, data_param, len_param):
            if p:
                doxy_params.append((p, _desc.get(p, "")))
        funcs.append(CFunc(
            name=_func_name(module, op_name), ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params, doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(_func_name(module, op_name))

    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="spi",
        header_includes=["xil_types.h", _spi_header_for(htype)],
        driver_includes=[f"{module}.h", "dbg_printf.h", "xparameters.h", "xstatus.h"],
        defines=defines, funcs=_prune_unused_static_funcs(funcs), public_names=public)


# --- GPIO device unit (AXI GPIO / XGpio) ------------------------------------------------

#: Descriptor step ops the GPIO emitter can express. Anything else must fail
#: loudly - a silently skipped step would produce a driver that compiles and
#: does nothing.
_GPIO_STEP_OPS: frozenset[str] = frozenset({"comment", "pin_write", "pin_read"})


def _gpio_channel_of(attach: dict) -> int:
    channel = attach.get("gpio_channel", 1)
    channel = _int_value(channel) if channel is not None else 1
    if channel not in (1, 2):
        raise CodegenError(f"gpio_channel must be 1 or 2 (AXI GPIO has two channels), got {channel!r}")
    return channel


def _gpio_pin_mask(step: dict, mask_def: str, where: str) -> str:
    """C expression for a step's ``pin_mask``.

    A step without ``pin_mask`` means "all the lines this device owns", which is
    exactly the ``<MOD>_GPIO_MASK`` define - emit the define, not a copy of its
    value, so the board wiring stays a single named constant.
    """
    raw = step.get("pin_mask")
    if raw is None:
        return mask_def
    mask = _int_value(raw)
    if not 0 < mask <= 0xFFFFFFFF:
        raise CodegenError(f"{where}: pin_mask 0x{mask:X} is outside a 32-bit non-zero range")
    return _hexu32(mask)


def _gpio_low_level(module: str, channel_def: str) -> list[CFunc]:
    """Masked read / read-modify-write helpers over the XGpio discrete API.

    Direction semantics come straight from the driver: in ``XGpio_SetDataDirection``
    a mask bit set to **1 is an INPUT** and a bit set to **0 is an OUTPUT**
    (``gpio_v4_10/src/xgpio.c`` doxygen). Each channel has its own TRI register
    (``(Channel-1) * XGPIO_CHAN_OFFSET + XGPIO_TRI_OFFSET``), so touching one
    channel can never disturb the other; within a channel only the masked bits
    are moved, the rest of the direction word is preserved.
    """
    wr = Emit()
    wr.ln("unsigned int uiDirection;")
    wr.ln("unsigned int uiCurrent;")
    wr.blank()
    wr.ln("/* Yon maskesinde bit=1 GIRIS, bit=0 CIKIS. Yalniz maskelenen")
    wr.ln(" * pinler cikisa alinir; ayni kanaldaki digerlerinin yonu korunur,")
    wr.ln(" * diger kanalin TRI yazmacina hic dokunulmaz. */")
    wr.ln(f"uiDirection = (unsigned int)XGpio_GetDataDirection(spGpio, {channel_def});")
    wr.ln(f"XGpio_SetDataDirection(spGpio, {channel_def}, uiDirection & ~uiMask);")
    wr.ln("/* \"All Inputs\" konfigurasyonunda TRI SALT-OKUNURDUR ve yazma")
    wr.ln(" * sessizce yutulur: geri okunup pinlerin gercekten cikis oldugu")
    wr.ln(" * dogrulanmazsa yazma hicbir sey yapmadan basarili gorunurdu. */")
    wr.ln(f"uiDirection = (unsigned int)XGpio_GetDataDirection(spGpio, {channel_def});")
    wr.open("if ((uiDirection & uiMask) != 0U)")
    wr.ln("return XST_FAILURE;")
    wr.close()
    wr.ln(f"uiCurrent = (unsigned int)XGpio_DiscreteRead(spGpio, {channel_def});")
    wr.ln(f"XGpio_DiscreteWrite(spGpio, {channel_def},")
    wr.ln("                    (uiCurrent & ~uiMask) | (uiValue & uiMask));")
    wr.ln("return XST_SUCCESS;")
    write = CFunc(
        name=_func_name(module, "pins_write"), ret="int",
        params=["XGpio* spGpio", "unsigned int uiMask", "unsigned int uiValue"],
        body=wr.out(), static=True)

    # Okuma hicbir sekilde basarisiz olamaz (tek bir AXI yazmac okumasi, yon
    # degistirilmez) - int dondurup her cagri noktasina asla girilmeyen bir
    # hata dali koymak yerine void.
    rd = Emit()
    rd.ln(f"*uipValue = ((unsigned int)XGpio_DiscreteRead(spGpio, {channel_def})) & uiMask;")
    read = CFunc(
        name=_func_name(module, "pins_read"), ret="void",
        params=["XGpio* spGpio", "unsigned int uiMask", "unsigned int* uipValue"],
        body=rd.out(), static=True)
    return [write, read]


def _gpio_device_unit(device: dict, controller: dict, descriptor: dict,
                      module: Optional[str] = None) -> CUnit:
    """Driver unit for a device wired to discrete AXI GPIO lines (XGpio)."""
    module = module or _module_of(device["part"])
    htype, hvar = _handle_for(controller)
    if htype != "XGpio":
        raise CodegenError(
            f"device {device.get('id', '?')}: gpio transport needs an AXI GPIO (XGpio) controller, "
            f"got driver '{htype}'")
    MOD = module.upper()
    attach = device.get("attach", {})
    instance = controller["instance"]
    channel = _gpio_channel_of(attach)
    channel_def, mask_def = f"{MOD}_GPIO_CHANNEL", f"{MOD}_GPIO_MASK"
    device_mask = _int_value(attach.get("gpio_pin_mask", 0xFFFFFFFF))
    if not 0 < device_mask <= 0xFFFFFFFF:
        raise CodegenError(
            f"device {device.get('id', '?')}: gpio_pin_mask 0x{device_mask:X} is outside a "
            "32-bit non-zero range")

    defines = [
        (channel_def, f"{channel}U", "AXI GPIO channel (1 or 2)"),
        (mask_def, _hexu32(device_mask), "board lines this device owns on that channel"),
    ]

    funcs = _gpio_low_level(module, channel_def)
    public: list[str] = []
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    requested = device.get("operations_requested") or list(ops_by_name)

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        where = f"device {device.get('id', '?')} op '{op_name}'"
        steps = op.get("steps", [])
        for step in steps:
            if step.get("op") not in _GPIO_STEP_OPS:
                raise CodegenError(
                    f"{where}: gpio transport cannot express step '{step.get('op')}' "
                    f"(supported: {', '.join(sorted(_GPIO_STEP_OPS))})")
            if step.get("op") == "pin_write" and step.get("pin_value") is None:
                raise CodegenError(
                    f"{where}: pin_write needs an explicit 'pin_value'; a runtime-valued line "
                    "write is not generated - use the controller-level gpio_write op for that")

        reads = [s for s in steps if s.get("op") == "pin_read"]
        if len(reads) > 1:
            raise CodegenError(f"{where}: gpio transport supports at most one pin_read per operation")
        params = [f"XGpio* {hvar}"]
        out_param = None
        if reads:
            returns = str(op.get("returns", "")).lower()
            if "uint32" not in returns:
                raise CodegenError(
                    f"{where}: a pin_read operation must declare 'returns: uint32' "
                    f"(got {op.get('returns')!r})")
            _out_type, out_param = _return_param(op_name, returns)
            params.append(f"unsigned int* {out_param}")

        # `iStatus` yalniz gercekten atanacaksa bildirilir: yalniz `comment`
        # adimi olan bir op'ta bildirmek -Wunused-variable uretirdi.
        uses_status = op_name == "device_init" or any(
            step["op"] == "pin_write" for step in steps)
        e = Emit()
        if uses_status:
            e.ln("int iStatus;")
            e.blank()
        if op_name == "device_init":
            e.ln(f"iStatus = XGpio_Initialize({hvar}, {instance}_DEVICE_ID);").check_status()
            if channel == 2:
                e.ln("/* Kanal 2 yalniz cift kanalli IP'de vardir; tek kanalli")
                e.ln(" * cekirdekte 0x8/0xC yazmaclari yoktur (surucu Xil_Assert")
                e.ln(" * eder, release derlemesinde bu sessizce kaybolur). */")
                e.open(f"if ({hvar}->IsDual == 0)")
                e.ln("return XST_FAILURE;")
                e.close()

        for step in steps:
            sop = step["op"]
            if sop == "comment":
                e.ln(f"/* {step.get('note', '')} */")
            elif sop == "pin_write":
                mask = _gpio_pin_mask(step, mask_def, where)
                value = _int_value(step["pin_value"])
                e.ln(f"iStatus = {_func_name(module, 'pins_write')}({hvar}, {mask}, "
                     f"{_hexu32(value)});").check_status()
            elif sop == "pin_read":
                mask = _gpio_pin_mask(step, mask_def, where)
                e.ln(f"{_func_name(module, 'pins_read')}({hvar}, {mask}, {out_param});")
        e.ln("return XST_SUCCESS;")

        doxy_params = [(hvar, "AXI GPIO controller instance (initialized by device_init).")]
        if out_param:
            doxy_params.append((out_param, "Out: masked 32-bit channel value."))
        funcs.append(CFunc(
            name=_func_name(module, op_name), ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params,
            doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(_func_name(module, op_name))

    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="gpio",
        header_includes=["xil_types.h", _gpio_header_for(htype)],
        driver_includes=[f"{module}.h", "xparameters.h", "xstatus.h"],
        defines=defines, funcs=_prune_unused_static_funcs(funcs), public_names=public)


# --- test unit --------------------------------------------------------------------------

def _test_unit(unit: CUnit, device: dict, controller: dict, runtime: str) -> CTest:
    module = unit.module
    htype, hvar = _handle_for(controller)
    if unit.transport in {"i2c", "i2c_eeprom"}:
        hvar = I2C_DEVICE_VAR  # tablo satiri: <mod>Op(spCihaz, ...)
    MOD = module.upper()
    part = unit.part
    # Non-destructive ops only: device init + *Read functions.
    read_ops = [n for n in unit.public_names if n.endswith("Read")]
    funcs_by_name = {func.name: func for func in unit.funcs}

    def is_array_read(name: str) -> bool:
        return any("[ucIndex]" in line for line in funcs_by_name.get(name, CFunc("", "", [], [])).body)

    def array_struct(name: str) -> tuple[str, str, str]:
        """(tip, degisken, alan): 'SLtc2991Voltage', 'sVoltage', 'usArrVoltage'."""
        params = funcs_by_name.get(name, CFunc("", "", [], [])).params
        ctype = params[1].split("*")[0].strip() if len(params) > 1 else "unsigned short"
        noun = ctype[len("S" + _pascal_suffix(module)):] if ctype.startswith("S" + _pascal_suffix(module)) else "Value"
        return ctype, f"s{noun}", f"usArr{noun}"

    status_regs_func = _func_name(module, "status_registers_read")
    has_status_regs = status_regs_func in read_ops
    read_ops = [n for n in read_ops if n != status_regs_func]

    def has_uint_out(name: str) -> bool:
        return any("unsigned int*" in param for param in funcs_by_name.get(name, CFunc("", "", [], [])).params)

    def has_int_out(name: str) -> bool:
        # Converted (engineering-unit) reads use a signed int out parameter.
        return any(
            param.strip().startswith("int*")
            for param in funcs_by_name.get(name, CFunc("", "", [], [])).params
        )

    def has_ushort_out(name: str) -> bool:
        # Word-size scalar reads (e.g. PMBus STATUS_WORD / MFR_SPECIAL_ID).
        return any(
            param.strip().startswith("unsigned short*")
            for param in funcs_by_name.get(name, CFunc("", "", [], [])).params
        )

    def has_uchar_id_out(name: str) -> bool:
        # TEK BAYTLIK id_read (I2C `returns: uint8`, or. ADT7420 ID registeri): out
        # parametresi `unsigned char* ucpId`. SPI flash'in 3 baytlik JEDEC id_read'i
        # ise `ucpBuffer` alir - ikisi ayni "IdRead" sonekini tasir (SAHA 2026-09-05:
        # ADT7420 self-test'i tanimsiz `ucArrId` ile derlenmiyordu).
        # Flash id_read de `ucpId` adini tasir ama 3 baytlik tampondur: ayrim TRANSPORT'la.
        return unit.transport in {"i2c", "i2c_eeprom"} and any(
            param.strip().startswith("unsigned char*") and param.strip().endswith("ucpId")
            for param in funcs_by_name.get(name, CFunc("", "", [], [])).params
        )

    st = Emit()
    st.ln("int iStatus;")
    if has_status_regs:
        # Durum yapisi her transportta (I2C register cihazi, SPI TICS cihazi) olabilir.
        st.ln(f"S{_pascal_suffix(module)}Status sStatusRegs;")
    if unit.transport in {"i2c", "i2c_eeprom"}:
        if any(n.endswith("ConfigRead") for n in read_ops):
            st.ln("unsigned char ucConfig;")
        if any(n.endswith("StatusRead") and not has_ushort_out(n) for n in read_ops):
            st.ln("unsigned char ucStatus;")
        if any(n.endswith("StatusRead") and has_ushort_out(n) for n in read_ops):
            st.ln("unsigned short usStatusWord;")
        if any(n.endswith("IdRead") and has_ushort_out(n) for n in read_ops):
            st.ln("unsigned short usId;")
        if any(n.endswith("IdRead") and has_uchar_id_out(n) for n in read_ops):
            st.ln("unsigned char ucId;")
        for n in read_ops:
            if is_array_read(n):
                ctype, var, _fld = array_struct(n)
                st.ln(f"{ctype} {var};")
        if any(n.endswith("VoltageRead") and not is_array_read(n) and has_int_out(n) for n in read_ops):
            st.ln("int iVoltage;")
        if any(n.endswith("VoltageRead") and not is_array_read(n) and not has_int_out(n) for n in read_ops):
            st.ln("unsigned short usVoltage;")
        if any(n.endswith("CurrentRead") and not is_array_read(n) and has_int_out(n) for n in read_ops):
            st.ln("int iCurrent;")
        if any(n.endswith("CurrentRead") and not is_array_read(n) and not has_int_out(n) for n in read_ops):
            st.ln("unsigned short usCurrent;")
        if any(n.endswith("TemperatureRead") and has_uint_out(n) for n in read_ops):
            st.ln("unsigned int uiTemperature;")
        if any(n.endswith("TemperatureRead") and has_int_out(n) for n in read_ops):
            st.ln("int iTemperature;")
        if any(n.endswith("TemperatureRead") and not has_uint_out(n) and not has_int_out(n) for n in read_ops):
            st.ln("unsigned short usTemperature;")
        if any(n.endswith("HumidityRead") and has_int_out(n) for n in read_ops):
            st.ln("int iHumidity;")
        if any(n.endswith("HumidityRead") and not has_int_out(n) for n in read_ops):
            st.ln("unsigned int uiHumidity;")
        if any(n.endswith("UserRegisterRead") for n in read_ops):
            st.ln("unsigned char ucUser;")
        if any(n.endswith("PowerRead") and has_int_out(n) for n in read_ops):
            st.ln("int iPower;")
        if any(n.endswith("PowerRead") and not has_int_out(n) for n in read_ops):
            st.ln("unsigned int uiPower;")
        if any(n.endswith("SenseRead") and has_int_out(n) for n in read_ops):
            st.ln("int iSense;")
        if any(n.endswith("SenseRead") and not has_int_out(n) for n in read_ops):
            st.ln("unsigned short usSense;")
        if any(n.endswith("AdinRead") and has_int_out(n) for n in read_ops):
            st.ln("int iAdin;")
        if any(n.endswith("AdinRead") and not has_int_out(n) for n in read_ops):
            st.ln("unsigned short usAdin;")
        if any(n.endswith("ElapsedRead") for n in read_ops):
            st.ln("unsigned int uiElapsed;")
        if any(n.endswith("AlarmRead") for n in read_ops):
            st.ln("unsigned int uiAlarm;")
        if any(n.endswith("EventRead") for n in read_ops):
            st.ln("unsigned int uiEvent;")
        if any(n.endswith("DataRead") for n in read_ops):
            st.ln("unsigned char ucArrBuffer[16];")
    elif unit.transport == "gpio":
        if any(n.endswith("LineRead") for n in read_ops):
            st.ln("unsigned int uiLines;")
    else:
        if any(n.endswith("IdRead") for n in read_ops):
            st.ln("unsigned char ucArrId[3];")
        # Flash status_read (RDSR, 1 bayt): SPI komut cihazinda da `ucpStatus` alir.
        if any(n.endswith("StatusRead") and not has_ushort_out(n) for n in read_ops):
            st.ln("unsigned char ucStatus;")
        if any(n.endswith("DataRead") for n in read_ops):
            st.ln("unsigned char ucArrBuffer[16];")
    st.blank()
    # Only call device_init when it was actually generated: the user may
    # request read-only operations, and an unconditional init call would be
    # an undefined reference at link time.
    if _func_name(module, "device_init") in unit.public_names:
        st.ln(f"iStatus = {_func_name(module, 'device_init')}({hvar});").check_status()
    if has_status_regs:
        st.ln(f"iStatus = {status_regs_func}({hvar}, &sStatusRegs);").check_status()
        st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' status registers read OK");')
    for name in read_ops:
        if is_array_read(name):
            ctype, var, fld = array_struct(name)
            st.ln(f"iStatus = {name}({hvar}, &{var});").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + f' {fld}[0] = %u", (unsigned int){var}.{fld}[0]);')
        elif name.endswith("ConfigRead"):
            st.ln(f"iStatus = {name}({hvar}, &ucConfig);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' config = %02X", ucConfig);')
        elif name.endswith("StatusRead"):
            if has_ushort_out(name):
                st.ln(f"iStatus = {name}({hvar}, &usStatusWord);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' status word = %04X", (unsigned int)usStatusWord);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &ucStatus);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' status = %02X", ucStatus);')
        elif name.endswith("VoltageRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iVoltage);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' voltage = %d", iVoltage);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usVoltage);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' voltage raw = %u", (unsigned int)usVoltage);')
        elif name.endswith("CurrentRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iCurrent);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' current = %d", iCurrent);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usCurrent);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' current raw = %u", (unsigned int)usCurrent);')
        elif name.endswith("TemperatureRead"):
            if has_uint_out(name):
                st.ln(f"iStatus = {name}({hvar}, &uiTemperature);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' temperature raw = %lu", (unsigned long)uiTemperature);')
            elif has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iTemperature);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' temperature = %d santi-C (0.01 C)", iTemperature);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usTemperature);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' Tint raw = %u", (unsigned int)usTemperature);')
        elif name.endswith("HumidityRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iHumidity);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' humidity = %d santi-RH", iHumidity);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &uiHumidity);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' humidity raw = %lu", (unsigned long)uiHumidity);')
        elif name.endswith("UserRegisterRead"):
            st.ln(f"iStatus = {name}({hvar}, &ucUser);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' user register = %02X", ucUser);')
        elif name.endswith("PowerRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iPower);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' power = %d mW", iPower);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &uiPower);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' power raw = %lu", (unsigned long)uiPower);')
        elif name.endswith("SenseRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iSense);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' sense = %d uV", iSense);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usSense);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' sense raw = %u", (unsigned int)usSense);')
        elif name.endswith("AdinRead"):
            if has_int_out(name):
                st.ln(f"iStatus = {name}({hvar}, &iAdin);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' ADIN = %d uV", iAdin);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usAdin);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' ADIN raw = %u", (unsigned int)usAdin);')
        elif name.endswith("ElapsedRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiElapsed);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' elapsed = %lu s", (unsigned long)uiElapsed);')
        elif name.endswith("AlarmRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiAlarm);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' alarm ticks = %lu", (unsigned long)uiAlarm);')
        elif name.endswith("EventRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiEvent);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' events = %lu", (unsigned long)uiEvent);')
        elif name.endswith("IdRead"):
            if has_ushort_out(name):
                st.ln(f"iStatus = {name}({hvar}, &usId);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' id = %04X", (unsigned int)usId);')
            elif has_uchar_id_out(name):
                st.ln(f"iStatus = {name}({hvar}, &ucId);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' id = %02X", ucId);')
            else:
                st.ln(f"iStatus = {name}({hvar}, ucArrId);").check_status()
                st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' JEDEC id = %02X %02X %02X", ucArrId[0], ucArrId[1], ucArrId[2]);')
        elif unit.transport == "gpio" and name.endswith("LineRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiLines);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' lines = 0x%X", uiLines);')
        elif name.endswith("DataRead"):
            st.ln(f"iStatus = {name}({hvar}, 0x0U, ucArrBuffer, 16U);").check_status()
            st.ln('dbg_printf(DEBUG_LEVEL_INFO, "' + part + ' data[0] = %02X", ucArrBuffer[0]);')
    st.ln("return XST_SUCCESS;")
    self_test = CFunc(
        name=_func_name(module, "self_test"), ret="int",
        params=[I2C_DEVICE_PARAM if unit.transport in {"i2c", "i2c_eeprom"} else _handle_param(htype, hvar)],
        body=st.out(),
        brief=f"Non-destructive self-test for the {part}: init + reads.",
        doxy_params=[(hvar, "Uninitialized controller handle; this routine initializes it.")],
        doxy_return="XST_SUCCESS if all checks pass, else an XST_* error code.")

    # Self-test ajandan (Test Bench `self_test` op'u) kosulur; ayri harness/gorev sarmalayicisi
    # YOK (kullanilmayan kod uretilmez). Log: dbg_printf INFO (varsayilan esikte sessiz).
    includes = ["dbg_printf.h", "xstatus.h", f"{module}.h"]
    return CTest(runtime=runtime, module=module, includes=includes, funcs=[self_test])


# --- entry point ------------------------------------------------------------------------

def build_units(spec: dict, get_descriptor: Callable[[str], dict]) -> list[CUnit]:
    """Build all driver units (muxes first, then devices) for a validated spec."""
    controllers = {c["id"]: c for c in spec["controllers"]}
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    runtime = spec["project"].get("runtime", "bare_metal")
    modules = device_module_map(spec)
    units: list[CUnit] = []

    built_mux: set[str] = set()
    for mux in spec.get("muxes", []):
        controller = controllers.get(mux["controller_id"])
        if controller is None:
            raise CodegenError(f"mux {mux['id']} references unknown controller {mux['controller_id']}")
        mux_unit = _mux_unit(mux, controller, get_descriptor(mux["part"]))
        if mux_unit.module in built_mux:
            continue  # ayni parcadan N switch: tek modul (adres parametre)
        built_mux.add(mux_unit.module)
        mux_unit.board_id = boards.board_id_of(mux)
        units.append(mux_unit)
    # Switch secimi calisma zamaninda tablo satirindan yapilir; hangi switch surucusu?
    # Spec'teki switch parcalari tek modulde bulusur (hepsi 1<<kanal kontrol bayti).
    switch_modules = sorted({_module_of(m["part"]) for m in spec.get("muxes", [])})
    if len(switch_modules) > 1:
        raise CodegenError(f"I2C switch parcalari tek tip olmali (spec'te: {switch_modules})")
    spec_switch_module = switch_modules[0] if switch_modules else None
    built_i2c: dict[str, dict] = {}

    for device in spec.get("devices", []):
        attach = device["attach"]
        controller = controllers.get(attach["controller_id"])
        if controller is None:
            raise CodegenError(f"device {device['id']} references unknown controller {attach['controller_id']}")
        descriptor = get_descriptor(device.get("descriptor_ref") or device["part"])
        transport = descriptor.get("transport", {}).get("type")

        if transport == "i2c":
            mux_module, mux_channel = spec_switch_module, None
            via = attach.get("via_mux")
            if via and muxes.get(via["mux_id"]) is None:
                raise CodegenError(f"device {device['id']} via unknown mux {via['mux_id']}")
            mod_name = modules.get(device["id"], _module_of(device["part"]))
            prior = built_i2c.get(mod_name)
            if prior is not None:
                # Ayni parcadan ikinci cihaz: TEK surucu (op birlesimi ilk cihazda uretildi);
                # ayrim tablo satirindan. Yalniz donusum sabitine giren config esit olmali.
                _assert_same_convert_config(prior, device, descriptor)
                if "self_test" in (device.get("tests_requested") or []):
                    for u in units:
                        if u.module == mod_name and u.test is None:
                            u.test = _test_unit(u, device, controller, runtime)
                continue
            built_i2c[mod_name] = device
            siblings = [d for d in spec.get("devices", [])
                        if is_i2c_device(d) and modules.get(d["id"], _module_of(d["part"])) == mod_name]
            if len(siblings) > 1:
                device = _i2c_union_device(device, siblings, descriptor)
            if descriptor.get("memory"):
                unit = _i2c_eeprom_unit(device, controller, descriptor, mux_module, mux_channel,
                                        module=modules.get(device["id"]))
            else:
                unit = _i2c_device_unit(device, controller, descriptor, mux_module, mux_channel,
                                        module=modules.get(device["id"]))
        elif transport == "spi":
            if tics.has_tics_register_model(descriptor):
                unit = _spi_register_device_unit(device, controller, descriptor,
                                                 module=modules.get(device["id"]))
            else:
                unit = _spi_device_unit(device, controller, descriptor,
                                        module=modules.get(device["id"]))
        elif transport == "gpio":
            unit = _gpio_device_unit(device, controller, descriptor,
                                     module=modules.get(device["id"]))
        else:
            raise CodegenError(
                f"device {device['id']}: transport '{transport}' not supported by codegen yet "
                f"(supported: i2c, spi, gpio). Extend cmodel.py to add it.")

        unit.board_id = boards.board_id_of(device)
        # tests/<mod>_test.* yalniz istenirse (tests_requested self_test); ajan `self_test` op'u da ayni kosula bagli.
        if "self_test" in (device.get("tests_requested") or []):
            unit.test = _test_unit(unit, device, controller, runtime)
        units.append(unit)

    return units


def _i2c_union_device(first: dict, siblings: list[dict], descriptor: dict) -> dict:
    """Ayni parcadan N cihaz: surucu HEPSININ istedigi op'lari icerir (descriptor sirasiyla)."""
    wanted: set[str] = set()
    explicit = False
    for d in siblings:
        req = d.get("operations_requested")
        if req:
            explicit = True
            wanted.update(str(x) for x in req)
    if not explicit:
        return first
    order = [op["name"] for op in descriptor.get("operations", [])]
    union = [name for name in order if name in wanted] + sorted(wanted - set(order))
    return {**first, "operations_requested": union}


def _assert_same_convert_config(first: dict, other: dict, descriptor: dict) -> None:
    """Donusum sabitine giren config (or. sont direnci) ayni surucude tek deger olabilir."""
    keys = {str((op.get("convert") or {}).get("scale_den_config"))
            for op in descriptor.get("operations", []) if (op.get("convert") or {}).get("scale_den_config")}
    for key in sorted(keys):
        a = (first.get("config") or {}).get(key)
        b = (other.get("config") or {}).get(key)
        if a != b:
            raise CodegenError(
                f"{other.get('id')} ile {first.get('id')} ayni parca ({first.get('part')}) ama config.{key} farkli "
                f"({a!r} / {b!r}): bu deger surucuye derleme sabiti olarak girer; ayni parcadan cihazlarda esit olmali")
