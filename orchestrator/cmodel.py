"""C render-model builder (Brief §13).

Turns a validated project.spec + device descriptors + ruleset into a structured model of
C functions with fully-rendered, coding-standard-compliant bodies. The Jinja templates
(codegen.py) only assemble the file skeletons around this model.

Design notes:
  * Codegen targets the descriptor's NAMED OPERATIONS, not raw registers (Brief §6.2).
  * Function names are strict ``module_object_action`` (3 tokens) per the ruleset regex.
    The brief's illustrative ``ltc2991_voltage_read_all`` (4 tokens) would fail that regex;
    we honor the machine-checkable ruleset and emit 3-token names (EXECUTION-PLAN note).
  * A mux-attached device gets a ``<mux>_channel_select(...)`` call injected before every
    device access (Brief §10, §13).
  * SPI flash address width (3 vs 4 bytes) flows from each descriptor command's
    ``address_bytes`` straight into the generated transfers — proving MT25QU02G differs
    from MT25Q128 (acceptance §20.3).

This module returns pure data; only codegen.py writes it out (through hostplat.io, CRLF).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from orchestrator.device_profiles import registry as device_profiles

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
        """if (i_status != XST_SUCCESS) { return i_status; }"""
        self.open("if (i_status != XST_SUCCESS)")
        self.ln("return i_status;")
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
    var = {"i2c": "sp_iic", "spi": "sp_spi", "qspi": "sp_qspi", "gpio": "sp_gpio"}.get(ctype, "sp_dev")
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


def _hexu8(value: int) -> str:
    return f"0x{value & 0xFF:02X}U"


def _hexu32(value: int) -> str:
    return f"0x{value & 0xFFFFFFFF:X}U"


def _first_bit(bits: str) -> int:
    bits = str(bits)
    return int(bits.split(":")[-1]) if ":" in bits else int(bits)


def _return_param(op_name: str, returns: str) -> tuple[str, str]:
    obj = op_name.split("_")[0]
    ret = returns.lower()
    if "uint8" in ret:
        return "uint8_t", f"puc_{obj}"
    if "uint32" in ret:
        return "uint32_t", f"pui_{obj}"
    return "uint16_t", f"pus_{obj}"


def _scalar_assign_expr(byte_count: int, c_type: str, byte_order: str,
                        pieces: list[dict[str, int]]) -> str:
    cast = "uint32_t" if c_type == "uint32_t" or byte_count > 2 else c_type
    explicit = any(("mask" in p) or ("shift" in p) for p in pieces)
    terms: list[str] = []

    if explicit:
        for p in pieces:
            idx = p["index"]
            mask = p.get("mask", 0xFF)
            shift = p.get("shift", 0)
            term = f"(({cast})uc_bytes[{idx}U] & {_hexu32(mask)})"
            if shift:
                term = f"({term} << {shift}U)"
            terms.append(term)
    else:
        for idx in range(byte_count):
            shift = (8 * idx) if byte_order == "little" else (8 * (byte_count - 1 - idx))
            term = f"({cast})uc_bytes[{idx}U]"
            if shift:
                term = f"({term} << {shift}U)"
            terms.append(term)

    return " | ".join(terms) if terms else "0U"


def _private_i2c_init_sequence(module: str, mod: str, writes: list[dict]) -> list[str]:
    if not writes:
        return []

    type_name = f"{module}_init_write_t"
    seq_name = f"S_{module}_init_sequence"
    count_name = f"{mod}_INIT_SEQUENCE_COUNT"
    lines = [
        "typedef struct",
        "{",
        "    uint8_t uc_reg;",
        "    uint8_t uc_value;",
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
    sel.ln("uint8_t uc_mask;").ln("int i_status;").blank()
    sel.ln("uc_mask = (uint8_t)(1U << uc_channel);")
    sel.ln(f"i_status = XIicPs_MasterSendPolled({hvar}, &uc_mask, 1, {addr_def});").check_status()
    sel.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait for the transfer to complete */").close()
    sel.ln("return XST_SUCCESS;")
    select = CFunc(
        name=f"{module}_channel_select", ret="int",
        params=[f"{htype} *{hvar}", "uint8_t uc_channel"], body=sel.out(),
        brief="Enable exactly one downstream channel on the I2C switch.",
        doxy_params=[(hvar, "Initialized I2C controller handle the mux sits on."),
                     ("uc_channel", "Channel index 0..7 to enable.")],
        doxy_return="XST_SUCCESS on success, else an XST_* error code.")

    dis = Emit()
    dis.ln("uint8_t uc_mask;").ln("int i_status;").blank()
    dis.ln("uc_mask = 0x00U;")
    dis.ln(f"i_status = XIicPs_MasterSendPolled({hvar}, &uc_mask, 1, {addr_def});").check_status()
    dis.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait for the transfer to complete */").close()
    dis.ln("return XST_SUCCESS;")
    disable = CFunc(
        name=f"{module}_channel_disable", ret="int", params=[f"{htype} *{hvar}"], body=dis.out(),
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
    w.ln("uint8_t uc_buffer[2];").ln("int i_status;").blank()
    w.ln("uc_buffer[0] = uc_reg;").ln("uc_buffer[1] = uc_value;")
    w.ln(f"i_status = XIicPs_MasterSendPolled({hvar}, uc_buffer, 2, {addr_def});").check_status()
    w.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    w.ln("return XST_SUCCESS;")
    write = CFunc(f"{module}_register_write", "int",
                  [f"{htype} *{hvar}", "uint8_t uc_reg", "uint8_t uc_value"], w.out(), static=True)

    r = Emit()
    r.ln("int i_status;").blank()
    r.ln(f"i_status = XIicPs_MasterSendPolled({hvar}, &uc_reg, 1, {addr_def});").check_status()
    r.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    r.ln(f"i_status = XIicPs_MasterRecvPolled({hvar}, puc_value, 1, {addr_def});").check_status()
    r.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    r.ln("return XST_SUCCESS;")
    read = CFunc(f"{module}_register_read", "int",
                 [f"{htype} *{hvar}", "uint8_t uc_reg", "uint8_t *puc_value"], r.out(), static=True)

    rb = Emit()
    rb.ln("int i_status;").blank()
    rb.open("if ((puc_buffer == NULL) || (ui_length == 0U))")
    rb.ln("return XST_FAILURE;")
    rb.close()
    rb.ln(f"i_status = XIicPs_MasterSendPolled({hvar}, &uc_reg, 1, {addr_def});").check_status()
    rb.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    rb.ln(f"i_status = XIicPs_MasterRecvPolled({hvar}, puc_buffer, (int)ui_length, {addr_def});").check_status()
    rb.open(f"while (XIicPs_BusIsBusy({hvar}) == TRUE)").ln("/* wait */").close()
    rb.ln("return XST_SUCCESS;")
    read_block = CFunc(f"{module}_registers_read", "int",
                       [f"{htype} *{hvar}", "uint8_t uc_reg",
                        "uint8_t *puc_buffer", "uint32_t ui_length"],
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
    profile_writes = device_profiles.i2c_init_writes(device)

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
            e.ln(f"i_status = {mux_module}_channel_select({hvar}, {mux_channel}U);").check_status()

    for op_name in requested:
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        returns = op.get("returns", "")
        is_init = op_name == "device_init"
        params = [f"{htype} *{hvar}"]
        out_c_type = ""
        out_param = None
        if returns:
            out_c_type, out_param = _return_param(op_name, returns)
            params.append(f"{out_c_type} *{out_param}")

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
        e.ln("int i_status;")
        if is_init:
            e.ln(f"{htype}_Config *sp_config;")
            if profile_writes:
                e.ln("uint32_t ui_index;")
        if has_channels:
            e.ln("uint8_t uc_index;")
        if has_channels:
            e.ln("uint8_t uc_msb;").ln("uint8_t uc_lsb;")
        if scalar_read_bytes:
            e.ln("uint8_t uc_bytes[4];")
        e.blank()

        if is_init:
            e.ln(f"sp_config = XIicPs_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (sp_config == NULL)").ln("return XST_FAILURE;").close()
            e.ln(f"i_status = XIicPs_CfgInitialize({hvar}, sp_config, sp_config->BaseAddress);").check_status()
            e.ln(f"i_status = XIicPs_SetSClk({hvar}, {sclk_def});").check_status()

        inject_mux(e)

        read_seen = 0
        scalar_pieces: list[dict[str, int]] = []
        if is_init and profile_writes:
            e.open(f"for (ui_index = 0U; ui_index < {MOD}_INIT_SEQUENCE_COUNT; ui_index++)")
            e.ln(f"i_status = {module}_register_write({hvar}, S_{module}_init_sequence[ui_index].uc_reg,")
            e.ln(f"                                  S_{module}_init_sequence[ui_index].uc_value);")
            e.check_status()
            e.close()
        else:
            for step in op["steps"]:
                sop = step["op"]
                if sop == "comment":
                    e.ln(f"/* {step.get('note', '')} */")
                elif sop == "write_register":
                    e.ln(f"i_status = {module}_register_write({hvar}, {MOD}_REG_{step['reg']}, "
                         f"{_hexu8(step.get('value', 0))});").check_status()
                elif sop == "poll":
                    rg = regs.get(step["reg"], {})
                    bit = next((_first_bit(f["bits"]) for f in rg.get("fields", [])
                                if f["name"] == step.get("field")), 0)
                    mask_expr = "(uc_poll & 0x1U)" if bit == 0 else f"((uc_poll >> {bit}) & 0x1U)"
                    e.open_scope()
                    e.ln("uint8_t uc_poll;")
                    e.ln(f"uint32_t ui_timeout = {to_def};  /* ~{step.get('timeout_ms', 0)} ms budget */")
                    e.open("do")
                    e.ln(f"i_status = {module}_register_read({hvar}, {MOD}_REG_{step['reg']}, &uc_poll);").check_status()
                    e.open("if (ui_timeout == 0U)").ln("return XST_FAILURE;").close()
                    e.ln("ui_timeout--;")
                    e.close(f" while ({mask_expr} != {step.get('until', 0)}U);")
                    e.close()
                elif sop == "read_register":
                    if scalar_combine:
                        target = f"uc_bytes[{read_seen}U]"
                        piece = {"index": read_seen}
                        if "mask" in step:
                            piece["mask"] = int(step["mask"])
                        if "shift" in step:
                            piece["shift"] = int(step["shift"])
                        scalar_pieces.append(piece)
                    else:
                        target = "uc_msb" if read_seen == 0 else "uc_lsb"
                    read_seen += 1
                    e.ln(f"i_status = {module}_register_read({hvar}, {MOD}_REG_{step['reg']}, &{target});").check_status()
                elif sop == "read_registers":
                    length = int(step.get("length", 1))
                    if not scalar_combine:
                        raise CodegenError(f"{device['id']} {op_name}: read_registers needs a scalar return")
                    e.ln(f"i_status = {module}_registers_read({hvar}, {MOD}_REG_{step['reg']}, "
                         f"&uc_bytes[{read_seen}U], {length}U);").check_status()
                    read_seen += length
                elif sop == "read_channels":
                    base, count = f"{MOD}_REG_{step['reg']}", step.get("count", 8)
                    e.open(f"for (uc_index = 0U; uc_index < {count}U; uc_index++)")
                    e.ln(f"i_status = {module}_register_read({hvar}, (uint8_t)({base} + (uc_index * 2U)), &uc_msb);").check_status()
                    e.ln(f"i_status = {module}_register_read({hvar}, (uint8_t)({base} + (uc_index * 2U) + 1U), &uc_lsb);").check_status()
                    e.ln(f"{out_param}[uc_index] = (uint16_t)(((uint16_t)uc_msb << 8) | (uint16_t)uc_lsb);")
                    e.close()

        if scalar_combine and out_param:
            expr = _scalar_assign_expr(read_seen, out_c_type, byte_order, scalar_pieces)
            e.ln(f"*{out_param} = ({out_c_type})({expr});")
        e.ln("return XST_SUCCESS;")

        doxy_params = [(hvar, "Initialized I2C controller handle.")]
        if out_param:
            doxy_params.append((out_param, f"Out parameter: {returns}."))
        funcs.append(CFunc(
            name=f"{module}_{op_name}", ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params, doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(f"{module}_{op_name}")

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
    send.ln("uint8_t uc_tx[1];").ln("int i_status;").blank()
    send.ln("uc_tx[0] = uc_opcode;")
    send.ln(f"i_status = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
    send.ln(f"return XSpiPs_PolledTransfer({hvar}, uc_tx, NULL, 1);")
    f_send = CFunc(f"{module}_command_send", "int",
                   [f"{htype} *{hvar}", "uint8_t uc_opcode"], send.out(), static=True)

    rd = Emit()
    rd.ln("uint8_t uc_tx[" + max_def + "];").ln("uint8_t uc_rx[" + max_def + "];")
    rd.ln("uint32_t ui_index;").ln("uint32_t ui_header;").ln("int i_status;").blank()
    rd.ln("ui_header = 1U + (uint32_t)uc_addr_bytes;")
    rd.open(f"if ((ui_header + ui_length) > (uint32_t){max_def})").ln("return XST_FAILURE;").close()
    rd.ln("uc_tx[0] = uc_opcode;")
    rd.open("for (ui_index = 0U; ui_index < (uint32_t)uc_addr_bytes; ui_index++)")
    rd.ln("uc_tx[1U + ui_index] = (uint8_t)((ui_address >> (8U * ((uint32_t)uc_addr_bytes - 1U - ui_index))) & 0xFFU);")
    rd.close()
    rd.open("for (ui_index = 0U; ui_index < ui_length; ui_index++)").ln("uc_tx[ui_header + ui_index] = 0x00U;").close()
    rd.ln(f"i_status = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
    rd.ln(f"i_status = XSpiPs_PolledTransfer({hvar}, uc_tx, uc_rx, ui_header + ui_length);").check_status()
    rd.open("for (ui_index = 0U; ui_index < ui_length; ui_index++)").ln("puc_buffer[ui_index] = uc_rx[ui_header + ui_index];").close()
    rd.ln("return XST_SUCCESS;")
    f_read = CFunc(f"{module}_command_read", "int",
                   [f"{htype} *{hvar}", "uint8_t uc_opcode", "uint32_t ui_address",
                    "uint8_t uc_addr_bytes", "uint8_t *puc_buffer", "uint32_t ui_length"],
                   rd.out(), static=True)

    wr = Emit()
    wr.ln("uint8_t uc_tx[" + max_def + "];")
    wr.ln("uint32_t ui_index;").ln("uint32_t ui_header;").ln("int i_status;").blank()
    wr.ln("ui_header = 1U + (uint32_t)uc_addr_bytes;")
    wr.open(f"if ((ui_header + ui_length) > (uint32_t){max_def})").ln("return XST_FAILURE;").close()
    wr.ln("uc_tx[0] = uc_opcode;")
    wr.open("for (ui_index = 0U; ui_index < (uint32_t)uc_addr_bytes; ui_index++)")
    wr.ln("uc_tx[1U + ui_index] = (uint8_t)((ui_address >> (8U * ((uint32_t)uc_addr_bytes - 1U - ui_index))) & 0xFFU);")
    wr.close()
    wr.open("for (ui_index = 0U; ui_index < ui_length; ui_index++)").ln("uc_tx[ui_header + ui_index] = puc_data[ui_index];").close()
    wr.ln(f"i_status = XSpiPs_SetSlaveSelect({hvar}, {sel_def});").check_status()
    wr.ln(f"return XSpiPs_PolledTransfer({hvar}, uc_tx, NULL, ui_header + ui_length);")
    f_write = CFunc(f"{module}_command_write", "int",
                    [f"{htype} *{hvar}", "uint8_t uc_opcode", "uint32_t ui_address",
                     "uint8_t uc_addr_bytes", "const uint8_t *puc_data", "uint32_t ui_length"],
                    wr.out(), static=True)
    return [f_send, f_read, f_write]


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
        params = [f"{htype} *{hvar}"]
        out_obj = op_name.split("_")[0]
        addr_param = data_param = len_param = buf_param = None

        if rca is not None:
            cmd = cmds[rca["cmd"]]
            if cmd["address_bytes"] > 0:
                addr_param = "ui_address"
                params.append("uint32_t ui_address")
            if "length" in rca:                       # fixed-length read (e.g. RDID)
                buf_param = f"puc_{out_obj}"
                params.append(f"uint8_t *{buf_param}")
            else:
                buf_param, len_param = "puc_buffer", "ui_length"
                params += ["uint8_t *puc_buffer", "uint32_t ui_length"]
        elif wca is not None:
            cmd = cmds[wca["cmd"]]
            addr_param = "ui_address"
            params.append("uint32_t ui_address")
            if wca.get("length") == 0:                # no data payload (erase)
                pass
            else:
                data_param, len_param = "puc_data", "ui_length"
                params += ["const uint8_t *puc_data", "uint32_t ui_length"]

        e = Emit()
        e.ln("int i_status;")
        if is_init:
            e.ln(f"{htype}_Config *sp_config;")
        e.blank()

        if is_init:
            e.ln(f"sp_config = XSpiPs_LookupConfig({instance}_DEVICE_ID);")
            e.open("if (sp_config == NULL)").ln("return XST_FAILURE;").close()
            e.ln(f"i_status = XSpiPs_CfgInitialize({hvar}, sp_config, sp_config->BaseAddress);").check_status()
            e.ln(f"i_status = XSpiPs_SetOptions({hvar}, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);").check_status()
            e.ln(f"i_status = XSpiPs_SetClkPrescaler({hvar}, XSPIPS_CLK_PRESCALE_8);").check_status()

        for step in op["steps"]:
            sop = step["op"]
            if sop == "comment":
                e.ln(f"/* {step.get('note', '')} */")
            elif sop == "send_command":
                e.ln(f"i_status = {module}_command_send({hvar}, {MOD}_CMD_{step['cmd']});").check_status()
            elif sop == "read_command_address":
                cmd = cmds[step["cmd"]]
                addr_expr = addr_param if addr_param else "0U"
                length_expr = f"{step['length']}U" if "length" in step else len_param
                e.ln(f"i_status = {module}_command_read({hvar}, {MOD}_CMD_{step['cmd']}, "
                     f"{addr_expr}, {cmd['address_bytes']}U, {buf_param}, {length_expr});").check_status()
            elif sop == "write_command_address":
                cmd = cmds[step["cmd"]]
                if step.get("length") == 0:
                    data_expr, length_expr = "NULL", "0U"
                else:
                    data_expr, length_expr = data_param, len_param
                e.ln(f"i_status = {module}_command_write({hvar}, {MOD}_CMD_{step['cmd']}, "
                     f"{addr_param}, {cmd['address_bytes']}U, {data_expr}, {length_expr});").check_status()

        e.ln("return XST_SUCCESS;")

        _desc = {
            "ui_address": "Byte address within the flash.",
            "puc_buffer": "Out: receive buffer (ui_length bytes).",
            "ui_length": "Number of data bytes to transfer.",
            "puc_data": "Source data buffer to program.",
            buf_param or "": f"Out: {out_obj} bytes.",
        }
        doxy_params = [(hvar, "Initialized SPI controller handle.")]
        for p in (addr_param, buf_param, data_param, len_param):
            if p:
                doxy_params.append((p, _desc.get(p, "")))
        funcs.append(CFunc(
            name=f"{module}_{op_name}", ret="int", params=params, body=e.out(),
            brief=op.get("description", op_name.replace("_", " ")),
            doxy_params=doxy_params, doxy_return="XST_SUCCESS on success, else an XST_* error code."))
        public.append(f"{module}_{op_name}")

    return CUnit(
        module=module, part=device["part"], summary=descriptor.get("summary", ""), transport="spi",
        header_includes=["xil_types.h", "xspips.h"],
        driver_includes=[f"{module}.h", "xparameters.h", "xstatus.h"],
        defines=defines, funcs=funcs, public_names=public)


# --- test unit --------------------------------------------------------------------------

def _test_unit(unit: CUnit, device: dict, controller: dict, runtime: str) -> CTest:
    module = unit.module
    htype, hvar = _handle_for(controller)
    MOD = module.upper()
    part = unit.part
    # Non-destructive ops only: device_init + *_read.
    read_ops = [n for n in unit.public_names if n.endswith("_read")]
    funcs_by_name = {func.name: func for func in unit.funcs}

    def is_array_read(name: str) -> bool:
        return any("[uc_index]" in line for line in funcs_by_name.get(name, CFunc("", "", [], [])).body)

    st = Emit()
    st.ln("int i_status;")
    if unit.transport == "i2c":
        if any(n.endswith("config_read") for n in read_ops):
            st.ln("uint8_t uc_config;")
        if any(n.endswith("status_read") for n in read_ops):
            st.ln("uint8_t uc_status;")
        if any(n.endswith("voltage_read") and is_array_read(n) for n in read_ops):
            st.ln("uint16_t us_voltages[8];")
        if any(n.endswith("voltage_read") and not is_array_read(n) for n in read_ops):
            st.ln("uint16_t us_voltage;")
        if any(n.endswith("temperature_read") for n in read_ops):
            st.ln("uint16_t us_temperature;")
        if any(n.endswith("power_read") for n in read_ops):
            st.ln("uint32_t ui_power;")
        if any(n.endswith("sense_read") for n in read_ops):
            st.ln("uint16_t us_sense;")
        if any(n.endswith("adin_read") for n in read_ops):
            st.ln("uint16_t us_adin;")
        if any(n.endswith("elapsed_read") for n in read_ops):
            st.ln("uint32_t ui_elapsed;")
        if any(n.endswith("alarm_read") for n in read_ops):
            st.ln("uint32_t ui_alarm;")
        if any(n.endswith("event_read") for n in read_ops):
            st.ln("uint32_t ui_event;")
    else:
        if any(n.endswith("id_read") for n in read_ops):
            st.ln("uint8_t uc_id[3];")
        if any(n.endswith("data_read") for n in read_ops):
            st.ln("uint8_t uc_buffer[16];")
    st.blank()
    st.ln(f"i_status = {module}_device_init({hvar});").check_status()
    for name in read_ops:
        if name.endswith("config_read"):
            st.ln(f"i_status = {name}({hvar}, &uc_config);").check_status()
            st.ln('xil_printf("' + part + ' config = %02X\\r\\n", uc_config);')
        elif name.endswith("status_read"):
            st.ln(f"i_status = {name}({hvar}, &uc_status);").check_status()
            st.ln('xil_printf("' + part + ' status = %02X\\r\\n", uc_status);')
        elif name.endswith("voltage_read"):
            if is_array_read(name):
                st.ln(f"i_status = {name}({hvar}, us_voltages);").check_status()
                st.ln('xil_printf("' + part + ' V1 raw = %u\\r\\n", (unsigned int)us_voltages[0]);')
            else:
                st.ln(f"i_status = {name}({hvar}, &us_voltage);").check_status()
                st.ln('xil_printf("' + part + ' voltage raw = %u\\r\\n", (unsigned int)us_voltage);')
        elif name.endswith("temperature_read"):
            st.ln(f"i_status = {name}({hvar}, &us_temperature);").check_status()
            st.ln('xil_printf("' + part + ' Tint raw = %u\\r\\n", (unsigned int)us_temperature);')
        elif name.endswith("power_read"):
            st.ln(f"i_status = {name}({hvar}, &ui_power);").check_status()
            st.ln('xil_printf("' + part + ' power raw = %lu\\r\\n", (unsigned long)ui_power);')
        elif name.endswith("sense_read"):
            st.ln(f"i_status = {name}({hvar}, &us_sense);").check_status()
            st.ln('xil_printf("' + part + ' sense raw = %u\\r\\n", (unsigned int)us_sense);')
        elif name.endswith("adin_read"):
            st.ln(f"i_status = {name}({hvar}, &us_adin);").check_status()
            st.ln('xil_printf("' + part + ' ADIN raw = %u\\r\\n", (unsigned int)us_adin);')
        elif name.endswith("elapsed_read"):
            st.ln(f"i_status = {name}({hvar}, &ui_elapsed);").check_status()
            st.ln('xil_printf("' + part + ' elapsed ticks = %lu\\r\\n", (unsigned long)ui_elapsed);')
        elif name.endswith("alarm_read"):
            st.ln(f"i_status = {name}({hvar}, &ui_alarm);").check_status()
            st.ln('xil_printf("' + part + ' alarm ticks = %lu\\r\\n", (unsigned long)ui_alarm);')
        elif name.endswith("event_read"):
            st.ln(f"i_status = {name}({hvar}, &ui_event);").check_status()
            st.ln('xil_printf("' + part + ' events = %lu\\r\\n", (unsigned long)ui_event);')
        elif name.endswith("id_read"):
            st.ln(f"i_status = {name}({hvar}, uc_id);").check_status()
            st.ln('xil_printf("' + part + ' JEDEC id = %02X %02X %02X\\r\\n", uc_id[0], uc_id[1], uc_id[2]);')
        elif name.endswith("data_read"):
            st.ln(f"i_status = {name}({hvar}, 0x0U, uc_buffer, 16U);").check_status()
            st.ln('xil_printf("' + part + ' data[0] = %02X\\r\\n", uc_buffer[0]);')
    st.ln("return XST_SUCCESS;")
    self_test = CFunc(
        name=f"{module}_self_test", ret="int", params=[f"{htype} *{hvar}"], body=st.out(),
        brief=f"Non-destructive self-test for the {part}: init + reads.",
        doxy_params=[(hvar, "Uninitialized controller handle; this routine initializes it.")],
        doxy_return="XST_SUCCESS if all checks pass, else an XST_* error code.")

    wr = Emit()
    if runtime == "freertos":
        wr.ln(f"{htype} {module}_handle;").ln("int i_status;").blank()
        wr.ln("(void) pv_parameters;")
        wr.open("for (;;)")
        wr.ln(f"i_status = {module}_self_test(&{module}_handle);")
        wr.open("if (i_status != XST_SUCCESS)")
        wr.ln('xil_printf("' + part + ' self-test FAILED: %d\\r\\n", i_status);')
        wr.close()
        wr.open("else")
        wr.ln('xil_printf("' + part + ' self-test PASSED\\r\\n");')
        wr.close()
        wr.ln("vTaskDelay(pdMS_TO_TICKS(1000));")
        wr.close()
        wrapper = CFunc(
            name=f"{module}_test_task", ret="void", params=["void *pv_parameters"], body=wr.out(),
            brief=f"FreeRTOS task: repeatedly run the {part} self-test.",
            doxy_params=[("pv_parameters", "Unused FreeRTOS task parameter.")], doxy_return="")
        includes = ["FreeRTOS.h", "task.h", "xil_printf.h", "xil_types.h", "xstatus.h", f"{module}.h"]
    else:
        wr.ln(f"{htype} {module}_handle;").ln("int i_status;").ln("uint32_t ui_iter;").ln("volatile uint32_t ui_delay;").blank()
        wr.open("for (ui_iter = 0U; ui_iter < 3U; ui_iter++)")
        wr.ln(f"i_status = {module}_self_test(&{module}_handle);")
        wr.open("if (i_status != XST_SUCCESS)")
        wr.ln('xil_printf("' + part + ' self-test FAILED: %d\\r\\n", i_status);')
        wr.close()
        wr.open("else")
        wr.ln('xil_printf("' + part + ' self-test PASSED\\r\\n");')
        wr.close()
        wr.ln("/* busy-wait between iterations */")
        wr.open("for (ui_delay = 0U; ui_delay < 1000000U; ui_delay++)").close()
        wr.close()
        wr.ln("return i_status;")
        wrapper = CFunc(
            name=f"{module}_test_run", ret="int", params=[], body=wr.out(),
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
            unit = _spi_device_unit(device, controller, descriptor)
        else:
            raise CodegenError(
                f"device {device['id']}: transport '{transport}' not supported by codegen yet "
                f"(supported: i2c, spi). Extend cmodel.py to add it.")

        unit.test = _test_unit(unit, device, controller, runtime)
        units.append(unit)

    return units
