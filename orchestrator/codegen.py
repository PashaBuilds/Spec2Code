"""Static (deterministic) codegen orchestration (Brief 13).

Loads a validated project.spec, builds the C render-model (cmodel), renders the Jinja
templates, and writes drop-in output through hostplat.io (always CRLF). No LLM involved.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from hostplat import io as hio
from orchestrator import cmodel
from orchestrator.device_profiles import registry as device_profiles

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parent
_TEMPLATES = _HERE / "templates"
_DEFAULT_RULESET_REF = "std/default.ruleset.json"

_IDENTIFIER_REPLACEMENTS = {
    "i_status": "iStatus",
    "sp_iic": "spIic",
    "sp_spi": "spSpi",
    "sp_qspi": "spQspi",
    "sp_gpio": "spGpio",
    "sp_dev": "spDev",
    "sp_config": "spConfig",
    "s_message": "sArrMessage",
    "uc_addr_bytes": "ucAddrBytes",
    "uc_buffer": "ucArrBuffer",
    "uc_bytes": "ucArrBytes",
    "uc_channel": "ucChannel",
    "uc_config": "ucConfig",
    "uc_id": "ucArrId",
    "uc_index": "ucIndex",
    "uc_lsb": "ucLsb",
    "uc_mask": "ucMask",
    "uc_msb": "ucMsb",
    "uc_opcode": "ucOpcode",
    "uc_poll": "ucPoll",
    "uc_reg": "ucReg",
    "uc_rx": "ucArrRx",
    "uc_tx": "ucArrTx",
    "uc_value": "ucValue",
    "ui_address": "uiAddress",
    "ui_delay": "uiDelay",
    "ui_header": "uiHeader",
    "ui_index": "uiIndex",
    "ui_iter": "uiIter",
    "ui_length": "uiLength",
    "ui_timeout": "uiTimeout",
    "ui_power": "uiPower",
    "ui_elapsed": "uiElapsed",
    "ui_alarm": "uiAlarm",
    "ui_event": "uiEvent",
    "us_adin": "usAdin",
    "us_sense": "usSense",
    "us_temperature": "usTemperature",
    "us_voltage": "usVoltage",
    "us_voltages": "usArrVoltages",
    "pv_parameters": "vpParameters",
}

_TYPE_REPLACEMENTS = {
    "uint8_t": "unsigned char",
    "int8_t": "char",
    "uint16_t": "unsigned short",
    "int16_t": "short",
    "uint32_t": "unsigned int",
    "int32_t": "int",
    "uint64_t": "unsigned long long",
    "int64_t": "long long",
}


def _pascal_identifier(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _header_guard(value: str) -> str:
    guard = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
    return guard if guard else "SPEC2CODE_GENERATED_H"


def _apply_default_identifier_style(text: str) -> str:
    """Apply the fixed camelCase + Hungarian identifier surface to generated C files."""
    for old, new in _TYPE_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    for old, new in _IDENTIFIER_REPLACEMENTS.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    text = re.sub(
        r"\b([a-z][a-z0-9]*)_init_write_t\b",
        lambda m: f"S{_pascal_identifier(m.group(1))}InitWrite",
        text,
    )
    text = re.sub(
        r"\bS_([a-z][a-z0-9]*)_init_sequence\b",
        lambda m: f"S_sArr{_pascal_identifier(m.group(1))}InitSequence",
        text,
    )
    text = re.sub(
        r"\b([a-z][a-z0-9]*)_handle\b",
        lambda m: f"s{_pascal_identifier(m.group(1))}Handle",
        text,
    )
    return text


def _int_value(value) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    return int(value)


def _hex_byte(value: int) -> str:
    return f"0x{value & 0xFF:02X}U"


def _mock_byte_array(values: list[int]) -> str:
    return ", ".join(_hex_byte(value) for value in values)


def _generic_i2c_init_writes(device: dict, descriptor: dict) -> list[dict]:
    config = device.get("config")
    if not isinstance(config, dict):
        return []
    sequence = config.get("init_sequence")
    if not isinstance(sequence, list):
        return []
    registers = {r.get("name"): r for r in descriptor.get("registers", [])}
    writes: list[dict] = []
    for item in sequence:
        if not isinstance(item, dict):
            continue
        reg = item.get("reg")
        if not isinstance(reg, str) or reg not in registers:
            continue
        access = str(registers[reg].get("access", "rw")).lower()
        if "w" not in access:
            continue
        writes.append({
            "reg": reg,
            "value": _int_value(item.get("value", 0)) & 0xFF,
            "note": str(item.get("note") or "manual init builder write"),
        })
    return writes


def _mock_bus_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_mock_bus.h\n"
        " * @brief Lightweight transfer recorder for boardless Spec2Code tests.\n"
        " */\n"
        "#ifndef SPEC2CODE_MOCK_BUS_H\n"
        "#define SPEC2CODE_MOCK_BUS_H\n\n"
        "#define SPEC2CODE_MOCK_MAX_TRANSFERS 128U\n"
        "#define SPEC2CODE_MOCK_MAX_BYTES 32U\n\n"
        "typedef enum\n"
        "{\n"
        "    enSpec2codeMockI2cWrite = 0,\n"
        "    enSpec2codeMockI2cRead = 1,\n"
        "    enSpec2codeMockSpiWrite = 2,\n"
        "    enSpec2codeMockSpiRead = 3\n"
        "} ESpec2codeMockTransferType;\n\n"
        "typedef struct\n"
        "{\n"
        "    ESpec2codeMockTransferType enType;\n"
        "    char cArrDevice[32];\n"
        "    unsigned char ucArrTx[SPEC2CODE_MOCK_MAX_BYTES];\n"
        "    unsigned char ucArrRx[SPEC2CODE_MOCK_MAX_BYTES];\n"
        "    unsigned int uiTxLength;\n"
        "    unsigned int uiRxLength;\n"
        "} SSpec2codeMockTransfer;\n\n"
        "void spec2codeMockBusReset(void);\n"
        "int spec2codeMockBusPush(ESpec2codeMockTransferType enType,\n"
        "                         const char* cpDevice,\n"
        "                         const unsigned char* ucpTx,\n"
        "                         unsigned int uiTxLength,\n"
        "                         const unsigned char* ucpRx,\n"
        "                         unsigned int uiRxLength);\n"
        "unsigned int spec2codeMockBusCount(void);\n"
        "const SSpec2codeMockTransfer* spec2codeMockBusTransferGet(unsigned int uiIndex);\n\n"
        "#endif /* SPEC2CODE_MOCK_BUS_H */\n"
    )


def _mock_bus_source() -> str:
    return (
        "/**\n"
        " * @file spec2code_mock_bus.c\n"
        " * @brief Lightweight transfer recorder for boardless Spec2Code tests.\n"
        " */\n"
        '#include "spec2code_mock_bus.h"\n'
        '#include "xstatus.h"\n\n'
        "#include <stddef.h>\n\n"
        "static SSpec2codeMockTransfer S_sArrTransfers[SPEC2CODE_MOCK_MAX_TRANSFERS];\n"
        "static unsigned int S_uiTransferCount;\n\n"
        "void spec2codeMockBusReset(void)\n"
        "{\n"
        "    unsigned int uiIndex;\n"
        "    unsigned int uiByte;\n\n"
        "    S_uiTransferCount = 0U;\n"
        "    for (uiIndex = 0U; uiIndex < SPEC2CODE_MOCK_MAX_TRANSFERS; uiIndex++)\n"
        "    {\n"
        "        S_sArrTransfers[uiIndex].enType = enSpec2codeMockI2cWrite;\n"
        "        S_sArrTransfers[uiIndex].uiTxLength = 0U;\n"
        "        S_sArrTransfers[uiIndex].uiRxLength = 0U;\n"
        "        for (uiByte = 0U; uiByte < SPEC2CODE_MOCK_MAX_BYTES; uiByte++)\n"
        "        {\n"
        "            S_sArrTransfers[uiIndex].ucArrTx[uiByte] = 0U;\n"
        "            S_sArrTransfers[uiIndex].ucArrRx[uiByte] = 0U;\n"
        "        }\n"
        "    }\n"
        "}\n\n"
        "int spec2codeMockBusPush(ESpec2codeMockTransferType enType,\n"
        "                         const char* cpDevice,\n"
        "                         const unsigned char* ucpTx,\n"
        "                         unsigned int uiTxLength,\n"
        "                         const unsigned char* ucpRx,\n"
        "                         unsigned int uiRxLength)\n"
        "{\n"
        "    SSpec2codeMockTransfer* spTransfer;\n"
        "    unsigned int uiIndex;\n\n"
        "    if ((uiTxLength > SPEC2CODE_MOCK_MAX_BYTES) || (uiRxLength > SPEC2CODE_MOCK_MAX_BYTES))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    if (S_uiTransferCount >= SPEC2CODE_MOCK_MAX_TRANSFERS)\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n\n"
        "    spTransfer = &S_sArrTransfers[S_uiTransferCount];\n"
        "    spTransfer->enType = enType;\n"
        "    spTransfer->uiTxLength = uiTxLength;\n"
        "    spTransfer->uiRxLength = uiRxLength;\n"
        "    for (uiIndex = 0U; uiIndex < 31U; uiIndex++)\n"
        "    {\n"
        "        if ((cpDevice == NULL) || (cpDevice[uiIndex] == '\\0'))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        spTransfer->cArrDevice[uiIndex] = cpDevice[uiIndex];\n"
        "    }\n"
        "    spTransfer->cArrDevice[uiIndex] = '\\0';\n"
        "    for (uiIndex = 0U; uiIndex < uiTxLength; uiIndex++)\n"
        "    {\n"
        "        if (ucpTx != NULL)\n"
        "        {\n"
        "            spTransfer->ucArrTx[uiIndex] = ucpTx[uiIndex];\n"
        "        }\n"
        "    }\n"
        "    for (uiIndex = 0U; uiIndex < uiRxLength; uiIndex++)\n"
        "    {\n"
        "        if (ucpRx != NULL)\n"
        "        {\n"
        "            spTransfer->ucArrRx[uiIndex] = ucpRx[uiIndex];\n"
        "        }\n"
        "    }\n\n"
        "    S_uiTransferCount++;\n"
        "    return XST_SUCCESS;\n"
        "}\n\n"
        "unsigned int spec2codeMockBusCount(void)\n"
        "{\n"
        "    return S_uiTransferCount;\n"
        "}\n\n"
        "const SSpec2codeMockTransfer* spec2codeMockBusTransferGet(unsigned int uiIndex)\n"
        "{\n"
        "    if (uiIndex >= S_uiTransferCount)\n"
        "    {\n"
        "        return NULL;\n"
        "    }\n"
        "    return &S_sArrTransfers[uiIndex];\n"
        "}\n"
    )


def _mock_plan_header(spec: dict) -> str:
    project_name = spec["project"]["name"]
    guard = _header_guard(f"{project_name}_mock_plan_h")
    return (
        "/**\n"
        f" * @file {project_name}_mock_plan.h\n"
        " * @brief Public API for loading the expected boardless transfer plan.\n"
        " */\n"
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        '#include "spec2code_mock_bus.h"\n'
        '#include "xstatus.h"\n\n'
        "int spec2codeMockPlanLoad(void);\n\n"
        f"#endif /* {guard} */\n"
    )


def _mock_plan_source(spec: dict, get_descriptor) -> str:
    controllers = {c["id"]: c for c in spec.get("controllers", [])}
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    transfers: list[dict] = []

    def add_transfer(kind: str, device: str, tx: list[int], rx_len: int = 0) -> None:
        transfers.append({"kind": kind, "device": device, "tx": tx, "rx_len": rx_len})

    for device in spec.get("devices", []):
        controller = controllers.get(device.get("attach", {}).get("controller_id"))
        if controller is None:
            continue
        descriptor = get_descriptor(device.get("descriptor_ref") or device.get("part", ""))
        transport = descriptor.get("transport", {}).get("type")
        requested = set(device.get("operations_requested") or [])
        if requested and "device_init" not in requested:
            continue
        if transport == "i2c":
            via = device.get("attach", {}).get("via_mux")
            if via:
                mux = muxes.get(via.get("mux_id"))
                if mux is not None:
                    add_transfer("enSpec2codeMockI2cWrite", str(mux.get("id")), [1 << int(via.get("channel", 0))])
            registers = {r.get("name"): r for r in descriptor.get("registers", [])}
            writes = [
                *device_profiles.i2c_init_writes(device),
                *_generic_i2c_init_writes(device, descriptor),
            ]
            for write in writes:
                reg = registers.get(write.get("reg"))
                if reg is None:
                    continue
                add_transfer(
                    "enSpec2codeMockI2cWrite",
                    str(device.get("id")),
                    [int(reg.get("offset", 0)), int(write.get("value", 0))],
                )
        elif transport == "spi":
            commands = {c.get("name"): c for c in descriptor.get("commands", [])}
            ops = {op.get("name"): op for op in descriptor.get("operations", [])}
            init = ops.get("device_init")
            if not init:
                continue
            for step in init.get("steps", []):
                if step.get("op") != "send_command":
                    continue
                cmd = commands.get(step.get("cmd"))
                if cmd is not None:
                    add_transfer("enSpec2codeMockSpiWrite", str(device.get("id")), [int(cmd.get("opcode", 0))])

    lines = [
        "/**",
        f" * @file {spec['project']['name']}_mock_plan.c",
        " * @brief Expected init-transfer plan for boardless review.",
        " */",
        f'#include "{spec["project"]["name"]}_mock_plan.h"',
        "",
        "#include <stddef.h>",
        "",
    ]
    for index, transfer in enumerate(transfers):
        lines.append(
            f"static const unsigned char S_ucArrTransfer{index}Tx[] = "
            f"{{ {_mock_byte_array(transfer['tx'])} }};"
        )
    if transfers:
        lines.append("")
    lines.extend([
        "int spec2codeMockPlanLoad(void)",
        "{",
        "    int iStatus;",
        "",
        "    spec2codeMockBusReset();",
    ])
    for index, transfer in enumerate(transfers):
        lines.extend([
            f"    iStatus = spec2codeMockBusPush({transfer['kind']},",
            f"                                     \"{transfer['device']}\",",
            f"                                     S_ucArrTransfer{index}Tx,",
            f"                                     {len(transfer['tx'])}U,",
            "                                     NULL,",
            f"                                     {transfer['rx_len']}U);",
            "    if (iStatus != XST_SUCCESS)",
            "    {",
            "        return iStatus;",
            "    }",
        ])
    lines.extend([
        "    return XST_SUCCESS;",
        "}",
        "",
    ])
    return "\n".join(lines)


def mock_harness_paths(spec: dict, out_dir: Path) -> list[Path]:
    project_name = spec["project"]["name"]
    tests_dir = out_dir / "tests"
    return [
        tests_dir / "spec2code_mock_bus.h",
        tests_dir / "spec2code_mock_bus.c",
        tests_dir / f"{project_name}_mock_plan.h",
        tests_dir / f"{project_name}_mock_plan.c",
    ]


def write_mock_harness(spec: dict, out_dir: Path, *, root: Path = _ROOT) -> list[str]:
    """Write the boardless mock harness files and return their resolved paths."""
    get_descriptor = make_descriptor_loader(root)
    paths = mock_harness_paths(spec, out_dir)
    contents = [
        _apply_default_identifier_style(_mock_bus_header()),
        _apply_default_identifier_style(_mock_bus_source()),
        _apply_default_identifier_style(_mock_plan_header(spec)),
        _apply_default_identifier_style(_mock_plan_source(spec, get_descriptor)),
    ]
    return [str(hio.write_output(path, content)) for path, content in zip(paths, contents)]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def make_descriptor_loader(root: Path = _ROOT) -> Callable[[str], dict]:
    """Resolve a descriptor by ref path (descriptors/x.yaml) or by part name (TCA9548A)."""
    cache: dict[str, dict] = {}

    def get(ref_or_part: str) -> dict:
        if ref_or_part.endswith((".yaml", ".yml")) or "/" in ref_or_part:
            path = root / ref_or_part
        else:
            path = root / "descriptors" / f"{cmodel._module_of(ref_or_part)}.yaml"
        key = str(path)
        if key not in cache:
            if not path.is_file():
                raise cmodel.CodegenError(f"descriptor not found: {path}")
            cache[key] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return cache[key]

    return get


def generate(
    spec: dict,
    out_dir: Path,
    *,
    emit: Optional[Callable[[dict], None]] = None,
    root: Path = _ROOT,
) -> list[str]:
    """Generate drop-in drivers + tests + README into *out_dir*. Returns written paths.

    ``emit`` (optional) receives structured progress events for WebSocket streaming.
    """
    emit = emit or (lambda _e: None)
    spec = {**spec, "coding_standard_ref": _DEFAULT_RULESET_REF}
    env = _env()
    get_descriptor = make_descriptor_loader(root)
    units = cmodel.build_units(spec, get_descriptor)

    gen_opts = spec.get("generation_options", {})
    include_doxygen = gen_opts.get("include_doxygen", True)
    ruleset_ref = _DEFAULT_RULESET_REF

    drivers_dir = out_dir / "drivers"
    tests_dir = out_dir / "tests"
    header_t = env.get_template("header.h.j2")
    driver_t = env.get_template("driver.c.j2")
    test_header_t = env.get_template("test.h.j2")
    test_t = env.get_template("test.c.j2")
    readme_t = env.get_template("readme.md.j2")

    written: list[str] = []
    for unit in units:
        emit({"event": "codegen.unit", "module": unit.module, "part": unit.part,
              "transport": unit.transport})
        public_funcs = [f for f in unit.funcs if not f.static]

        header = header_t.render(
            module=unit.module, part=unit.part, summary=unit.summary,
            guard=f"{unit.module.upper()}_H", header_includes=unit.header_includes,
            defines=unit.defines, public_funcs=public_funcs,
            include_doxygen=include_doxygen, ruleset_ref=ruleset_ref)
        header = _apply_default_identifier_style(header)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.h", header)))

        driver = driver_t.render(
            module=unit.module, part=unit.part, summary=unit.summary,
            driver_includes=unit.driver_includes, private_decls=unit.private_decls,
            funcs=unit.funcs,
            include_doxygen=include_doxygen)
        driver = _apply_default_identifier_style(driver)
        written.append(str(hio.write_output(drivers_dir / f"{unit.module}.c", driver)))

        if unit.test:
            test_header = test_header_t.render(
                module=unit.module, part=unit.part, runtime=unit.test.runtime,
                guard=_header_guard(f"{unit.module}_test_h"),
                test_includes=unit.test.includes, test_funcs=unit.test.funcs,
                include_doxygen=include_doxygen)
            test_header = _apply_default_identifier_style(test_header)
            written.append(str(hio.write_output(tests_dir / f"{unit.module}_test.h", test_header)))

            test = test_t.render(
                module=unit.module, part=unit.part, runtime=unit.test.runtime,
                test_includes=unit.test.includes, test_funcs=unit.test.funcs,
                include_doxygen=include_doxygen)
            test = _apply_default_identifier_style(test)
            written.append(str(hio.write_output(tests_dir / f"{unit.module}_test.c", test)))

    readme = readme_t.render(spec=spec, units=units)
    written.append(str(hio.write_output(out_dir / "README.md", readme)))

    written.extend(write_mock_harness(spec, out_dir, root=root))

    emit({"event": "codegen.done", "files": len(written)})
    return written
