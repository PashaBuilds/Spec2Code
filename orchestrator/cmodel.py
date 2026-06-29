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

from dataclasses import dataclass, field
from typing import Callable, Optional

from orchestrator.device_profiles import registry as device_profiles
from orchestrator import tics

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
    test: Optional[CTest] = None


# --- helpers ----------------------------------------------------------------------------

def _module_of(part: str) -> str:
    mod = "".join(ch.lower() for ch in part if ch.isalnum())
    if not mod or not mod[0].isalpha():
        raise CodegenError(f"cannot derive a valid C module name from part '{part}'")
    return mod


def _handle_for(controller: dict) -> tuple[str, str]:
    ctype = controller.get("type")
    var = {"i2c": "spIic", "spi": "spSpi", "qspi": "spQspi", "gpio": "spGpio"}.get(ctype, "spDev")
    driver = controller.get("driver")
    if driver:
        return driver, var
    is_ps = controller.get("zone") == "ps"
    table = {
        ("i2c", True): "XIicPs", ("i2c", False): "XIic",
        ("spi", True): "XSpiPs", ("spi", False): "XSpi",
        ("qspi", True): "XQspiPs", ("qspi", False): "XSpi",
    }
    htype = table.get((ctype, is_ps))
    if htype is None:
        raise CodegenError(f"no BSP driver mapping for controller type '{ctype}'")
    return htype, var


def _spi_header_for(htype: str) -> str:
    return {
        "XQspiPsu": "xqspipsu.h",
        "XQspiPs": "xqspips.h",
    }.get(htype, "xspips.h")


def _is_qspipsu(htype: str) -> bool:
    return htype == "XQspiPsu"


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


def _handle_var(module: str) -> str:
    return f"s{_pascal_suffix(module)}Handle"


def _return_param(op_name: str, returns: str) -> tuple[str, str]:
    obj = op_name.split("_")[0]
    ret = returns.lower()
    if "uint8" in ret:
        return "unsigned char", f"ucp{_pascal_suffix(obj)}"
    if "uint32" in ret:
        return "unsigned int", f"uip{_pascal_suffix(obj)}"
    return "unsigned short", f"usp{_pascal_suffix(obj)}"


def _scalar_assign_expr(byte_count: int, c_type: str, byte_order: str,
                        pieces: list[dict[str, int]]) -> str:
    cast = "unsigned int" if c_type == "unsigned int" or byte_count > 2 else c_type
    explicit = any(("mask" in p) or ("shift" in p) for p in pieces)
    terms: list[str] = []

    if explicit:
        for p in pieces:
            idx = p["index"]
            mask = p.get("mask", 0xFF)
            shift = p.get("shift", 0)
            term = f"(({cast})ucArrBytes[{idx}U] & {_hexu32(mask)})"
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


def _private_i2c_init_sequence(module: str, mod: str, writes: list[dict]) -> list[str]:
    if not writes:
        return []

    type_name = _struct_type(module, "InitWrite")
    seq_name = _static_array_name(module, "InitSequence")
    count_name = f"{mod}_INIT_SEQUENCE_COUNT"
    lines = [
        "typedef struct",
        "{",
        "    unsigned char ucReg;",
        "    unsigned char ucValue;",
        f"}} {type_name};",
        "",
        f"#define {count_name} {len(writes)}U",
        "",
        f"static const {type_name} {seq_name}[{count_name}] =",
        "{",
    ]
    for write in writes:
        note = str(write.get("note", "")).strip()
        comment = f"  /* {note} */" if note else ""
        lines.append(f"    {{ {mod}_REG_{write['reg']}, {_hexu8(int(write['value']))} }},{comment}")
    lines.extend([
        "};",
        "",
    ])
    return lines


def _private_spi_register_init_sequence(module: str, mod: str, words: list[tics.TicsRegisterWord]) -> list[str]:
    if not words:
        return []

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


def _doxy(func: CFunc) -> CFunc:
    return func


# --- mux unit (TCA9548A) ----------------------------------------------------------------

def _mux_unit(mux: dict, controller: dict, descriptor: dict) -> CUnit:
    module = _module_of(mux["part"])
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    addr_def = f"{MOD}_I2C_ADDR"
    addr = int(str(mux["i2c_address"]), 0)

    sel = Emit()
    sel.ln("unsigned char ucMask;").ln("int iStatus;").blank()
    sel.ln("ucMask = (unsigned char)(1U << ucChannel);")
    sel.ln(f"iStatus = XIicPs_MasterSendPolled({hvar}, &ucMask, 1, {addr_def});").check_status()
    sel.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait for the transfer to complete */").close()
    sel.ln("return XST_SUCCESS;")
    select = CFunc(
        name=_func_name(module, "channel_select"), ret="int",
        params=[f"{htype}* {hvar}", "unsigned char ucChannel"], body=sel.out(),
        brief="Enable exactly one downstream channel on the I2C switch.",
        doxy_params=[(hvar, "Initialized I2C controller handle the mux sits on."),
                     ("ucChannel", "Channel index 0..7 to enable.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")

    dis = Emit()
    dis.ln("unsigned char ucMask;").ln("int iStatus;").blank()
    dis.ln("ucMask = 0x00U;")
    dis.ln(f"iStatus = XIicPs_MasterSendPolled({hvar}, &ucMask, 1, {addr_def});").check_status()
    dis.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait for the transfer to complete */").close()
    dis.ln("return XST_SUCCESS;")
    disable = CFunc(
        name=_func_name(module, "channel_disable"), ret="int", params=[f"{htype}* {hvar}"], body=dis.out(),
        brief="Disable all downstream channels on the I2C switch.",
        doxy_params=[(hvar, "Initialized I2C controller handle the mux sits on.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")

    return CUnit(
        module=module, part=mux["part"], summary=descriptor.get("summary", ""), transport="i2c_mux",
        header_includes=["xil_types.h", "xiicps.h"],
        driver_includes=[f"{module}.h", "xparameters.h", "xstatus.h"],
        defines=[(addr_def, _hexu8(addr), f"{mux['part']} I2C address")],
        funcs=[select, disable], public_names=[select.name, disable.name])


# --- I2C device unit --------------------------------------------------------------------

def _i2c_low_level(module: str, htype: str, hvar: str, addr_def: str) -> list[CFunc]:
    w = Emit()
    w.ln("unsigned char ucArrBuffer[2];").ln("int iStatus;").blank()
    w.ln("ucArrBuffer[0] = ucReg;").ln("ucArrBuffer[1] = ucValue;")
    w.ln(f"iStatus = XIicPs_MasterSendPolled({hvar}, ucArrBuffer, 2, {addr_def});").check_status()
    w.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    w.ln("return XST_SUCCESS;")
    write = CFunc(_func_name(module, "register_write"), "int",
                  [f"{htype}* {hvar}", "unsigned char ucReg", "unsigned char ucValue"], w.out(), static=True)

    r = Emit()
    r.ln("int iStatus;").blank()
    r.ln(f"iStatus = XIicPs_MasterSendPolled({hvar}, &ucReg, 1, {addr_def});").check_status()
    r.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    r.ln(f"iStatus = XIicPs_MasterRecvPolled({hvar}, ucpValue, 1, {addr_def});").check_status()
    r.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    r.ln("return XST_SUCCESS;")
    read = CFunc(_func_name(module, "register_read"), "int",
                 [f"{htype}* {hvar}", "unsigned char ucReg", "unsigned char* ucpValue"], r.out(), static=True)

    rb = Emit()
    rb.ln("int iStatus;").blank()
    rb.open("if ((ucpBuffer == NULL) || (uiLength == 0U))")
    rb.ln("return XST_FAILURE;")
    rb.close()
    rb.ln(f"iStatus = XIicPs_MasterSendPolled({hvar}, &ucReg, 1, {addr_def});").check_status()
    rb.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    rb.ln(f"iStatus = XIicPs_MasterRecvPolled({hvar}, ucpBuffer, (int)uiLength, {addr_def});").check_status()
    rb.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    rb.ln("return XST_SUCCESS;")
    read_block = CFunc(_func_name(module, "registers_read"), "int",
                       [f"{htype}* {hvar}", "unsigned char ucReg",
                        "unsigned char* ucpBuffer", "unsigned int uiLength"],
                       rb.out(), static=True)
    return [write, read, read_block]


def _i2c_device_unit(device: dict, controller: dict, descriptor: dict,
                     mux_module: Optional[str], mux_channel: Optional[int]) -> CUnit:
    module = _module_of(device["part"])
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    attach = device["attach"]
    addr_def, sclk_def, to_def = f"{MOD}_I2C_ADDR", f"{MOD}_I2C_SCLK_HZ", f"{MOD}_POLL_TIMEOUT"
    regs = {rg["name"]: rg for rg in descriptor.get("registers", [])}
    instance = controller["instance"]
    byte_order = descriptor.get("transport", {}).get("byte_order", "big")
    profile_writes = [
        *device_profiles.i2c_init_writes(device),
        *_generic_i2c_init_writes(device, regs),
    ]

    defines = [
        (addr_def, _hexu8(int(str(attach["i2c_address"]), 0)), f"{device['part']} I2C address"),
        (sclk_def, "100000U", "I2C SCL frequency (Hz)"),
        (to_def, "100000U", "polling loop budget"),
    ]
    defines += [(f"{MOD}_REG_{n}", _hexu8(rg["offset"]), "") for n, rg in regs.items()]
    private_decls = _private_i2c_init_sequence(module, MOD, profile_writes)

    funcs = _i2c_low_level(module, htype, hvar, addr_def)
    public: list[str] = []
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    requested = device.get("operations_requested") or list(ops_by_name)

    def inject_mux(e: Emit) -> None:
        if mux_module is not None:
            e.ln(f"iStatus = {_func_name(mux_module, 'channel_select')}({hvar}, {mux_channel}U);").check_status()

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        returns = op.get("returns", "")
        is_init = op_name == "device_init"
        params = [f"{htype}* {hvar}"]
        out_c_type = ""
        out_param = None
        if returns:
            out_c_type, out_param = _return_param(op_name, returns)
            params.append(f"{out_c_type}* {out_param}")

        has_channels = any(s["op"] == "read_channels" for s in op["steps"])
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
            e.ln(f"{htype}_Config* spConfig;")
            if profile_writes:
                e.ln("unsigned int uiIndex;")
        if has_channels:
            e.ln("unsigned char ucIndex;")
        if has_channels:
            e.ln("unsigned char ucMsb;").ln("unsigned char ucLsb;")
        if scalar_read_bytes:
            e.ln("unsigned char ucArrBytes[4];")
        e.blank()

        if is_init:
            e.ln(f"spConfig = XIicPs_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
            e.ln(f"iStatus = XIicPs_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
            e.ln(f"iStatus = XIicPs_SetSClk({hvar}, {sclk_def});").check_status()

        inject_mux(e)

        read_seen = 0
        scalar_pieces: list[dict[str, int]] = []
        if is_init and profile_writes:
            seq_name = _static_array_name(module, "InitSequence")
            e.open(f"for (uiIndex = 0U; uiIndex < {MOD}_INIT_SEQUENCE_COUNT; uiIndex++)")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {seq_name}[uiIndex].ucReg,")
            e.ln(f"                                {seq_name}[uiIndex].ucValue);")
            e.check_status()
            e.close()
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
                    e.ln(f"unsigned int uiTimeout = {to_def};  /* ~{step.get('timeout_ms', 0)} ms budget */")
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
                    e.ln(f"iStatus = {_func_name(module, 'registers_read')}({hvar}, {MOD}_REG_{step['reg']}, "
                         f"&ucArrBytes[{read_seen}U], {length}U);").check_status()
                    read_seen += length
                elif sop == "read_channels":
                    base, count = f"{MOD}_REG_{step['reg']}", step.get("count", 8)
                    e.open(f"for (ucIndex = 0U; ucIndex < {count}U; ucIndex++)")
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, (unsigned char)({base} + (ucIndex * 2U)), &ucMsb);").check_status()
                    e.ln(f"iStatus = {_func_name(module, 'register_read')}({hvar}, (unsigned char)({base} + (ucIndex * 2U) + 1U), &ucLsb);").check_status()
                    e.ln(f"{out_param}[ucIndex] = (unsigned short)(((unsigned short)ucMsb << 8) | (unsigned short)ucLsb);")
                    e.close()

        if scalar_combine and out_param:
            expr = _scalar_assign_expr(read_seen, out_c_type, byte_order, scalar_pieces)
            e.ln(f"*{out_param} = ({out_c_type})({expr});")
        e.ln("return XST_SUCCESS;")

        doxy_params = [(hvar, "Initialized I2C controller handle.")]
        if out_param:
            doxy_params.append((out_param, f"Out parameter: {returns}."))
        funcs.append(CFunc(
            name=_func_name(module, op_name), ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params, doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(_func_name(module, op_name))

    includes_c = [f"{module}.h", "xparameters.h", "xstatus.h"]
    if mux_module:
        includes_c.insert(1, f"{mux_module}.h")
    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="i2c",
        header_includes=["xil_types.h", "xiicps.h"], driver_includes=includes_c,
        defines=defines, funcs=funcs, public_names=public, private_decls=private_decls)


# --- SPI device unit (NOR flash) --------------------------------------------------------

def _spi_low_level(module: str, htype: str, hvar: str, sel_def: str, max_def: str) -> list[CFunc]:
    send = Emit()
    send.ln("unsigned char ucArrTx[1];")
    if _is_qspipsu(htype):
        send.ln("XQspiPsu_Msg sArrMessage[1];")
    else:
        send.ln("int iStatus;")
    send.blank()
    send.ln("ucArrTx[0] = ucOpcode;")
    if _is_qspipsu(htype):
        send.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        send.ln("sArrMessage[0].RxBfrPtr = NULL;")
        send.ln("sArrMessage[0].ByteCount = 1U;")
        send.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        send.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        send.ln(f"return XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);")
    else:
        send.ln(f"iStatus = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
        send.ln(f"return XSpiPs_PolledTransfer({hvar}, ucArrTx, NULL, 1);")
    f_send = CFunc(_func_name(module, "command_send"), "int",
                   [f"{htype}* {hvar}", "unsigned char ucOpcode"], send.out(), static=True)

    rd = Emit()
    rd.ln("unsigned char ucArrTx[" + max_def + "];").ln("unsigned char ucArrRx[" + max_def + "];")
    if _is_qspipsu(htype):
        rd.ln("XQspiPsu_Msg sArrMessage[1];")
    rd.ln("unsigned int uiIndex;").ln("unsigned int uiHeader;").ln("int iStatus;").blank()
    rd.ln("uiHeader = 1U + (unsigned int)ucAddrBytes;")
    rd.open(f"if ((uiHeader + uiLength) > (unsigned int){max_def})").ln("return XST_FAILURE;").close()
    rd.ln("ucArrTx[0] = ucOpcode;")
    rd.open("for (uiIndex = 0U; uiIndex < (unsigned int)ucAddrBytes; uiIndex++)")
    rd.ln("ucArrTx[1U + uiIndex] = (unsigned char)((uiAddress >> (8U * ((unsigned int)ucAddrBytes - 1U - uiIndex))) & 0xFFU);")
    rd.close()
    rd.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucArrTx[uiHeader + uiIndex] = 0x00U;").close()
    if _is_qspipsu(htype):
        rd.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        rd.ln("sArrMessage[0].RxBfrPtr = ucArrRx;")
        rd.ln("sArrMessage[0].ByteCount = uiHeader + uiLength;")
        rd.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        rd.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX | XQSPIPSU_MSG_FLAG_RX;")
        rd.ln(f"iStatus = XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);").check_status()
    else:
        rd.ln(f"iStatus = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
        rd.ln(f"iStatus = XSpiPs_PolledTransfer({hvar}, ucArrTx, ucArrRx, uiHeader + uiLength);").check_status()
    rd.open("for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)").ln("ucpBuffer[uiIndex] = ucArrRx[uiHeader + uiIndex];").close()
    rd.ln("return XST_SUCCESS;")
    f_read = CFunc(_func_name(module, "command_read"), "int",
                   [f"{htype}* {hvar}", "unsigned char ucOpcode", "unsigned int uiAddress",
                    "unsigned char ucAddrBytes", "unsigned char* ucpBuffer", "unsigned int uiLength"],
                   rd.out(), static=True)

    wr = Emit()
    wr.ln("unsigned char ucArrTx[" + max_def + "];")
    if _is_qspipsu(htype):
        wr.ln("XQspiPsu_Msg sArrMessage[1];")
    wr.ln("unsigned int uiIndex;").ln("unsigned int uiHeader;")
    if not _is_qspipsu(htype):
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
        wr.ln("sArrMessage[0].TxBfrPtr = ucArrTx;")
        wr.ln("sArrMessage[0].RxBfrPtr = NULL;")
        wr.ln("sArrMessage[0].ByteCount = uiHeader + uiLength;")
        wr.ln("sArrMessage[0].BusWidth = XQSPIPSU_SELECT_MODE_SPI;")
        wr.ln("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;")
        wr.ln(f"return XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);")
    else:
        wr.ln(f"iStatus = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
        wr.ln(f"return XSpiPs_PolledTransfer({hvar}, ucArrTx, NULL, uiHeader + uiLength);")
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
    else:
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
        wr.ln(f"return XQspiPsu_PolledTransfer({hvar}, sArrMessage, 1U);")
    else:
        wr.ln(f"iStatus = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
        wr.ln(f"return XSpiPs_PolledTransfer({hvar}, ucArrTx, NULL, {frame_def});")
    return CFunc(
        _func_name(module, "register_write"),
        "int",
        [f"{htype}* {hvar}", "unsigned int uiWord"],
        wr.out(),
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


def _spi_register_device_unit(device: dict, controller: dict, descriptor: dict) -> CUnit:
    module = _module_of(device["part"])
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    attach = device["attach"]
    sel_def = f"{MOD}_SPI_SELECT"
    frame_def = f"{MOD}_SPI_FRAME_BYTES"
    sck_def = f"{MOD}_SPI_MAX_SCK_HZ"
    instance = controller["instance"]
    model = tics.register_model(descriptor)
    words = tics.decode_words(tics.normalize_words(device.get("config")), model)
    seq_name = _static_uint_array_name(module, "InitSequence")
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

    private_decls = _private_spi_register_init_sequence(module, MOD, words)
    funcs = [_spi_register_write_func(module, htype, hvar, sel_def, frame_def)]
    if rewrite_word is not None:
        funcs.append(_delay_func(module))

    public: list[str] = []
    ops_by_name = {op["name"]: op for op in descriptor["operations"]}
    requested = device.get("operations_requested") or list(ops_by_name)

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        if op_name != "device_init":
            continue

        e = Emit()
        e.ln("int iStatus;")
        e.ln(f"{htype}_Config* spConfig;")
        if words:
            e.ln("unsigned int uiIndex;")
        e.blank()

        if _is_qspipsu(htype):
            e.ln(f"spConfig = XQspiPsu_LookupConfig((UINTPTR){instance}_BASEADDR);")
        else:
            e.ln(f"spConfig = XSpiPs_LookupConfig({instance}_DEVICE_ID);")
        e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
        if _is_qspipsu(htype):
            e.ln(f"iStatus = XQspiPsu_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
            e.ln(f"iStatus = XQspiPsu_SetOptions({hvar}, XQSPIPSU_MANUAL_START_OPTION);").check_status()
            e.ln(f"iStatus = XQspiPsu_SetClkPrescaler({hvar}, XQSPIPSU_CLK_PRESCALE_8);").check_status()
            e.ln(f"XQspiPsu_SelectFlash({hvar}, XQSPIPSU_SELECT_FLASH_CS_LOWER, XQSPIPSU_SELECT_FLASH_BUS_LOWER);")
        else:
            e.ln(f"iStatus = XSpiPs_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
            e.ln(f"iStatus = XSpiPs_SetOptions({hvar}, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);").check_status()
            e.ln(f"iStatus = XSpiPs_SetClkPrescaler({hvar}, XSPIPS_CLK_PRESCALE_8);").check_status()

        if words:
            e.open(f"for (uiIndex = 0U; uiIndex < {MOD}_INIT_SEQUENCE_COUNT; uiIndex++)")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {seq_name}[uiIndex]);").check_status()
            e.close()
        if rewrite_word is not None:
            e.ln(f"{_func_name(module, 'delay_ms')}({MOD}_POST_INIT_DELAY_MS);")
            e.ln(f"iStatus = {_func_name(module, 'register_write')}({hvar}, {tics.c_word(rewrite_word.word)});").check_status()

        e.ln("return XST_SUCCESS;")

        funcs.append(CFunc(
            name=_func_name(module, op_name),
            ret="int",
            params=[f"{htype}* {hvar}"],
            body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=[(hvar, "Uninitialized SPI controller handle; this routine initializes it.")],
            doxy_return="XST_SUCCESS on success, else an XST_* error code.",
        ))
        public.append(_func_name(module, op_name))

    return CUnit(
        module=module,
        part=device["part"],
        summary=descriptor.get("summary", ""),
        transport="spi",
        header_includes=["xil_types.h", _spi_header_for(htype)],
        driver_includes=[f"{module}.h", "xparameters.h", "xstatus.h"],
        defines=defines,
        funcs=funcs,
        public_names=public,
        private_decls=private_decls,
    )


def _spi_device_unit(device: dict, controller: dict, descriptor: dict) -> CUnit:
    module = _module_of(device["part"])
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
            if _is_qspipsu(htype):
                e.ln(f"spConfig = XQspiPsu_LookupConfig((UINTPTR){instance}_BASEADDR);")
            else:
                e.ln(f"spConfig = XSpiPs_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (spConfig == NULL)").ln("return XST_FAILURE;").close()
            if _is_qspipsu(htype):
                e.ln(f"iStatus = XQspiPsu_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
                e.ln(f"iStatus = XQspiPsu_SetOptions({hvar}, XQSPIPSU_MANUAL_START_OPTION);").check_status()
                e.ln(f"iStatus = XQspiPsu_SetClkPrescaler({hvar}, XQSPIPSU_CLK_PRESCALE_8);").check_status()
                e.ln(f"XQspiPsu_SelectFlash({hvar}, XQSPIPSU_SELECT_FLASH_CS_LOWER, XQSPIPSU_SELECT_FLASH_BUS_LOWER);")
            else:
                e.ln(f"iStatus = XSpiPs_CfgInitialize({hvar}, spConfig, spConfig->BaseAddress);").check_status()
                e.ln(f"iStatus = XSpiPs_SetOptions({hvar}, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);").check_status()
                e.ln(f"iStatus = XSpiPs_SetClkPrescaler({hvar}, XSPIPS_CLK_PRESCALE_8);").check_status()

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
        driver_includes=[f"{module}.h", "xparameters.h", "xstatus.h"],
        defines=defines, funcs=funcs, public_names=public)


# --- test unit --------------------------------------------------------------------------

def _test_unit(unit: CUnit, device: dict, controller: dict, runtime: str) -> CTest:
    module = unit.module
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    part = unit.part
    # Non-destructive ops only: device init + *Read functions.
    read_ops = [n for n in unit.public_names if n.endswith("Read")]
    funcs_by_name = {func.name: func for func in unit.funcs}

    def is_array_read(name: str) -> bool:
        return any("[ucIndex]" in line for line in funcs_by_name.get(name, CFunc("", "", [], [])).body)

    st = Emit()
    st.ln("int iStatus;")
    if unit.transport == "i2c":
        if any(n.endswith("ConfigRead") for n in read_ops):
            st.ln("unsigned char ucConfig;")
        if any(n.endswith("StatusRead") for n in read_ops):
            st.ln("unsigned char ucStatus;")
        if any(n.endswith("VoltageRead") and is_array_read(n) for n in read_ops):
            st.ln("unsigned short usArrVoltages[8];")
        if any(n.endswith("VoltageRead") and not is_array_read(n) for n in read_ops):
            st.ln("unsigned short usVoltage;")
        if any(n.endswith("TemperatureRead") for n in read_ops):
            st.ln("unsigned short usTemperature;")
        if any(n.endswith("PowerRead") for n in read_ops):
            st.ln("unsigned int uiPower;")
        if any(n.endswith("SenseRead") for n in read_ops):
            st.ln("unsigned short usSense;")
        if any(n.endswith("AdinRead") for n in read_ops):
            st.ln("unsigned short usAdin;")
        if any(n.endswith("ElapsedRead") for n in read_ops):
            st.ln("unsigned int uiElapsed;")
        if any(n.endswith("AlarmRead") for n in read_ops):
            st.ln("unsigned int uiAlarm;")
        if any(n.endswith("EventRead") for n in read_ops):
            st.ln("unsigned int uiEvent;")
    else:
        if any(n.endswith("IdRead") for n in read_ops):
            st.ln("unsigned char ucArrId[3];")
        if any(n.endswith("DataRead") for n in read_ops):
            st.ln("unsigned char ucArrBuffer[16];")
    st.blank()
    st.ln(f"iStatus = {_func_name(module, 'device_init')}({hvar});").check_status()
    for name in read_ops:
        if name.endswith("ConfigRead"):
            st.ln(f"iStatus = {name}({hvar}, &ucConfig);").check_status()
            st.ln('xil_printf("' + part + ' config = %02X\\r\\n", ucConfig);')
        elif name.endswith("StatusRead"):
            st.ln(f"iStatus = {name}({hvar}, &ucStatus);").check_status()
            st.ln('xil_printf("' + part + ' status = %02X\\r\\n", ucStatus);')
        elif name.endswith("VoltageRead"):
            if is_array_read(name):
                st.ln(f"iStatus = {name}({hvar}, usArrVoltages);").check_status()
                st.ln('xil_printf("' + part + ' V1 raw = %u\\r\\n", (unsigned int)usArrVoltages[0]);')
            else:
                st.ln(f"iStatus = {name}({hvar}, &usVoltage);").check_status()
                st.ln('xil_printf("' + part + ' voltage raw = %u\\r\\n", (unsigned int)usVoltage);')
        elif name.endswith("TemperatureRead"):
            st.ln(f"iStatus = {name}({hvar}, &usTemperature);").check_status()
            st.ln('xil_printf("' + part + ' Tint raw = %u\\r\\n", (unsigned int)usTemperature);')
        elif name.endswith("PowerRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiPower);").check_status()
            st.ln('xil_printf("' + part + ' power raw = %lu\\r\\n", (unsigned long)uiPower);')
        elif name.endswith("SenseRead"):
            st.ln(f"iStatus = {name}({hvar}, &usSense);").check_status()
            st.ln('xil_printf("' + part + ' sense raw = %u\\r\\n", (unsigned int)usSense);')
        elif name.endswith("AdinRead"):
            st.ln(f"iStatus = {name}({hvar}, &usAdin);").check_status()
            st.ln('xil_printf("' + part + ' ADIN raw = %u\\r\\n", (unsigned int)usAdin);')
        elif name.endswith("ElapsedRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiElapsed);").check_status()
            st.ln('xil_printf("' + part + ' elapsed ticks = %lu\\r\\n", (unsigned long)uiElapsed);')
        elif name.endswith("AlarmRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiAlarm);").check_status()
            st.ln('xil_printf("' + part + ' alarm ticks = %lu\\r\\n", (unsigned long)uiAlarm);')
        elif name.endswith("EventRead"):
            st.ln(f"iStatus = {name}({hvar}, &uiEvent);").check_status()
            st.ln('xil_printf("' + part + ' events = %lu\\r\\n", (unsigned long)uiEvent);')
        elif name.endswith("IdRead"):
            st.ln(f"iStatus = {name}({hvar}, ucArrId);").check_status()
            st.ln('xil_printf("' + part + ' JEDEC id = %02X %02X %02X\\r\\n", ucArrId[0], ucArrId[1], ucArrId[2]);')
        elif name.endswith("DataRead"):
            st.ln(f"iStatus = {name}({hvar}, 0x0U, ucArrBuffer, 16U);").check_status()
            st.ln('xil_printf("' + part + ' data[0] = %02X\\r\\n", ucArrBuffer[0]);')
    st.ln("return XST_SUCCESS;")
    self_test = CFunc(
        name=_func_name(module, "self_test"), ret="int", params=[f"{htype}* {hvar}"], body=st.out(),
        brief=f"Non-destructive self-test for the {part}: init + reads.",
        doxy_params=[(hvar, "Uninitialized controller handle; this routine initializes it.")],
        doxy_return="XST_SUCCESS if all checks pass, else an XST_* error code.")

    wr = Emit()
    if runtime == "freertos":
        handle_name = _handle_var(module)
        wr.ln(f"{htype} {handle_name};").ln("int iStatus;").blank()
        wr.ln("(void) vpParameters;")
        wr.open("for (;;)")
        wr.ln(f"iStatus = {_func_name(module, 'self_test')}(&{handle_name});")
        wr.open("if (iStatus != XST_SUCCESS)")
        wr.ln('xil_printf("' + part + ' self-test FAILED: %d\\r\\n", iStatus);')
        wr.close()
        wr.open("else")
        wr.ln('xil_printf("' + part + ' self-test PASSED\\r\\n");')
        wr.close()
        wr.ln("vTaskDelay(pdMS_TO_TICKS(1000));")
        wr.close()
        wrapper = CFunc(
            name=_func_name(module, "test_task"), ret="void", params=["void* vpParameters"], body=wr.out(),
            brief=f"FreeRTOS task: repeatedly run the {part} self-test.",
            doxy_params=[("vpParameters", "Unused FreeRTOS task parameter.")], doxy_return="")
        includes = ["FreeRTOS.h", "task.h", "xil_printf.h", "xil_types.h", "xstatus.h", f"{module}.h"]
    else:
        handle_name = _handle_var(module)
        wr.ln(f"{htype} {handle_name};").ln("int iStatus;").ln("unsigned int uiIter;").ln("volatile unsigned int uiDelay;").blank()
        wr.open("for (uiIter = 0U; uiIter < 3U; uiIter++)")
        wr.ln(f"iStatus = {_func_name(module, 'self_test')}(&{handle_name});")
        wr.open("if (iStatus != XST_SUCCESS)")
        wr.ln('xil_printf("' + part + ' self-test FAILED: %d\\r\\n", iStatus);')
        wr.close()
        wr.open("else")
        wr.ln('xil_printf("' + part + ' self-test PASSED\\r\\n");')
        wr.close()
        wr.ln("/* busy-wait between iterations */")
        wr.open("for (uiDelay = 0U; uiDelay < 1000000U; uiDelay++)").close()
        wr.close()
        wr.ln("return iStatus;")
        wrapper = CFunc(
            name=_func_name(module, "test_run"), ret="int", params=[], body=wr.out(),
            brief=f"Bare-metal harness: run the {part} self-test a few times with busy-wait.",
            doxy_params=[], doxy_return="XST_SUCCESS if the last run passed, else an XST_* error code.")
        includes = ["xil_printf.h", "xil_types.h", "xstatus.h", f"{module}.h"]

    return CTest(runtime=runtime, module=module, includes=includes, funcs=[self_test, wrapper])


# --- entry point ------------------------------------------------------------------------

def build_units(spec: dict, get_descriptor: Callable[[str], dict]) -> list[CUnit]:
    """Build all driver units (muxes first, then devices) for a validated spec."""
    controllers = {c["id"]: c for c in spec["controllers"]}
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    runtime = spec["project"].get("runtime", "bare_metal")
    units: list[CUnit] = []

    for mux in spec.get("muxes", []):
        controller = controllers.get(mux["controller_id"])
        if controller is None:
            raise CodegenError(f"mux {mux['id']} references unknown controller {mux['controller_id']}")
        units.append(_mux_unit(mux, controller, get_descriptor(mux["part"])))

    for device in spec.get("devices", []):
        attach = device["attach"]
        controller = controllers.get(attach["controller_id"])
        if controller is None:
            raise CodegenError(f"device {device['id']} references unknown controller {attach['controller_id']}")
        descriptor = get_descriptor(device.get("descriptor_ref") or device["part"])
        transport = descriptor.get("transport", {}).get("type")

        if transport == "i2c":
            mux_module = mux_channel = None
            via = attach.get("via_mux")
            if via:
                mux = muxes.get(via["mux_id"])
                if mux is None:
                    raise CodegenError(f"device {device['id']} via unknown mux {via['mux_id']}")
                mux_module, mux_channel = _module_of(mux["part"]), via["channel"]
            unit = _i2c_device_unit(device, controller, descriptor, mux_module, mux_channel)
        elif transport == "spi":
            if tics.has_tics_register_model(descriptor):
                unit = _spi_register_device_unit(device, controller, descriptor)
            else:
                unit = _spi_device_unit(device, controller, descriptor)
        else:
            raise CodegenError(
                f"device {device['id']}: transport '{transport}' not supported by codegen yet "
                f"(supported: i2c, spi). Extend cmodel.py to add it.")

        unit.test = _test_unit(unit, device, controller, runtime)
        units.append(unit)

    return units
