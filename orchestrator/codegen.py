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
from orchestrator import tics
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
        if "w" not in access or "*" in access:
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
            if tics.has_tics_register_model(descriptor):
                model = tics.register_model(descriptor)
                decoded = tics.decode_words(tics.normalize_words(device.get("config")), model)
                for item in decoded:
                    add_transfer("enSpec2codeMockSpiWrite", str(device.get("id")), item.bytes_msb_first)
                rewrite_addr = model.get("rewrite_last_address")
                delay_ms = int(model.get("rewrite_last_address_after_ms", 0) or 0)
                if rewrite_addr is not None and delay_ms > 0:
                    for item in decoded:
                        if item.address == int(rewrite_addr):
                            add_transfer("enSpec2codeMockSpiWrite", str(device.get("id")), item.bytes_msb_first)
                            break
                continue
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


def _testbench_protocol_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_protocol.h\n"
        " * @brief Line protocol for the Spec2Code TCP test bench agent.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_PROTOCOL_H\n"
        "#define SPEC2CODE_TESTBENCH_PROTOCOL_H\n\n"
        "#define SPEC2CODE_TESTBENCH_TEXT_MAX 64U\n"
        "#define SPEC2CODE_TESTBENCH_MESSAGE_MAX 160U\n"
        "#define SPEC2CODE_TESTBENCH_DATA_MAX 256U\n\n"
        "typedef struct\n"
        "{\n"
        "    unsigned int uiId;\n"
        "    char cArrDevice[SPEC2CODE_TESTBENCH_TEXT_MAX];\n"
        "    char cArrOperation[SPEC2CODE_TESTBENCH_TEXT_MAX];\n"
        "    char cArrRegister[SPEC2CODE_TESTBENCH_TEXT_MAX];\n"
        "    unsigned int uiRegister;\n"
        "    unsigned int uiAddress;\n"
        "    unsigned int uiLength;\n"
        "    unsigned int uiValue;\n"
        "    unsigned char ucArrData[SPEC2CODE_TESTBENCH_DATA_MAX];\n"
        "    unsigned int uiDataLength;\n"
        "} SSpec2codeTestbenchRequest;\n\n"
        "typedef struct\n"
        "{\n"
        "    unsigned int uiId;\n"
        "    unsigned int uiOk;\n"
        "    int iStatus;\n"
        "    unsigned int uiValue;\n"
        "    unsigned char ucArrData[SPEC2CODE_TESTBENCH_DATA_MAX];\n"
        "    unsigned int uiDataLength;\n"
        "    char cArrMessage[SPEC2CODE_TESTBENCH_MESSAGE_MAX];\n"
        "} SSpec2codeTestbenchResponse;\n\n"
        "void spec2codeTestbenchRequestClear(SSpec2codeTestbenchRequest* spRequest);\n"
        "void spec2codeTestbenchResponseClear(SSpec2codeTestbenchResponse* spResponse);\n"
        "int spec2codeTestbenchRequestParse(const char* cpLine, SSpec2codeTestbenchRequest* spRequest);\n"
        "int spec2codeTestbenchResponseFormat(const SSpec2codeTestbenchResponse* spResponse,\n"
        "                                      char* cpLine,\n"
        "                                      unsigned int uiLineLength);\n"
        "int spec2codeTestbenchStringEqual(const char* cpLeft, const char* cpRight);\n"
        "void spec2codeTestbenchMessageSet(SSpec2codeTestbenchResponse* spResponse, const char* cpMessage);\n"
        "int spec2codeTestbenchDataPush(SSpec2codeTestbenchResponse* spResponse, unsigned char ucValue);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_PROTOCOL_H */\n"
    )


def _testbench_protocol_source() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_protocol.c\n"
        " * @brief Line protocol parser/formatter for the Spec2Code TCP test bench agent.\n"
        " */\n"
        '#include "spec2code_testbench_protocol.h"\n'
        '#include "xstatus.h"\n\n'
        "#include <stdio.h>\n"
        "#include <string.h>\n\n"
        "static unsigned int spec2codeTestbenchTextCopy(char* cpDst, unsigned int uiDstLength, const char* cpSrc)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    if ((cpDst == NULL) || (uiDstLength == 0U))\n"
        "    {\n"
        "        return 0U;\n"
        "    }\n"
        "    for (uiIndex = 0U; uiIndex < (uiDstLength - 1U); uiIndex++)\n"
        "    {\n"
        "        if ((cpSrc == NULL) || (cpSrc[uiIndex] == '\\0') || (cpSrc[uiIndex] == '|') ||\n"
        "            (cpSrc[uiIndex] == '\\r') || (cpSrc[uiIndex] == '\\n'))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        cpDst[uiIndex] = cpSrc[uiIndex];\n"
        "    }\n"
        "    cpDst[uiIndex] = '\\0';\n"
        "    return uiIndex;\n"
        "}\n\n"
        "static int spec2codeTestbenchHexNibble(char cValue)\n"
        "{\n"
        "    if ((cValue >= '0') && (cValue <= '9'))\n"
        "    {\n"
        "        return (int)(cValue - '0');\n"
        "    }\n"
        "    if ((cValue >= 'A') && (cValue <= 'F'))\n"
        "    {\n"
        "        return (int)(cValue - 'A') + 10;\n"
        "    }\n"
        "    if ((cValue >= 'a') && (cValue <= 'f'))\n"
        "    {\n"
        "        return (int)(cValue - 'a') + 10;\n"
        "    }\n"
        "    return -1;\n"
        "}\n\n"
        "static unsigned int spec2codeTestbenchNumberParse(const char* cpText)\n"
        "{\n"
        "    unsigned int uiValue;\n"
        "    unsigned int uiIndex;\n"
        "    unsigned int uiBase;\n"
        "    int iDigit;\n\n"
        "    uiValue = 0U;\n"
        "    uiIndex = 0U;\n"
        "    uiBase = 10U;\n"
        "    if ((cpText != NULL) && (cpText[0] == '0') && ((cpText[1] == 'x') || (cpText[1] == 'X')))\n"
        "    {\n"
        "        uiBase = 16U;\n"
        "        uiIndex = 2U;\n"
        "    }\n"
        "    while ((cpText != NULL) && (cpText[uiIndex] != '\\0') && (cpText[uiIndex] != '|'))\n"
        "    {\n"
        "        iDigit = (uiBase == 16U) ? spec2codeTestbenchHexNibble(cpText[uiIndex]) : (int)(cpText[uiIndex] - '0');\n"
        "        if ((iDigit < 0) || ((unsigned int)iDigit >= uiBase))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        uiValue = (uiValue * uiBase) + (unsigned int)iDigit;\n"
        "        uiIndex++;\n"
        "    }\n"
        "    return uiValue;\n"
        "}\n\n"
        "static void spec2codeTestbenchDataParse(const char* cpText, SSpec2codeTestbenchRequest* spRequest)\n"
        "{\n"
        "    unsigned int uiIndex;\n"
        "    int iHigh;\n"
        "    int iLow;\n\n"
        "    uiIndex = 0U;\n"
        "    spRequest->uiDataLength = 0U;\n"
        "    while ((cpText != NULL) && (cpText[uiIndex] != '\\0') && (cpText[uiIndex + 1U] != '\\0') &&\n"
        "           (spRequest->uiDataLength < SPEC2CODE_TESTBENCH_DATA_MAX))\n"
        "    {\n"
        "        iHigh = spec2codeTestbenchHexNibble(cpText[uiIndex]);\n"
        "        iLow = spec2codeTestbenchHexNibble(cpText[uiIndex + 1U]);\n"
        "        if ((iHigh < 0) || (iLow < 0))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        spRequest->ucArrData[spRequest->uiDataLength] = (unsigned char)(((unsigned int)iHigh << 4U) | (unsigned int)iLow);\n"
        "        spRequest->uiDataLength++;\n"
        "        uiIndex += 2U;\n"
        "    }\n"
        "}\n\n"
        "int spec2codeTestbenchStringEqual(const char* cpLeft, const char* cpRight)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    if ((cpLeft == NULL) || (cpRight == NULL))\n"
        "    {\n"
        "        return 0;\n"
        "    }\n"
        "    for (uiIndex = 0U; ; uiIndex++)\n"
        "    {\n"
        "        if (cpLeft[uiIndex] != cpRight[uiIndex])\n"
        "        {\n"
        "            return 0;\n"
        "        }\n"
        "        if (cpLeft[uiIndex] == '\\0')\n"
        "        {\n"
        "            return 1;\n"
        "        }\n"
        "    }\n"
        "}\n\n"
        "void spec2codeTestbenchRequestClear(SSpec2codeTestbenchRequest* spRequest)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    if (spRequest == NULL)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    spRequest->uiId = 0U;\n"
        "    spRequest->uiRegister = 0U;\n"
        "    spRequest->uiAddress = 0U;\n"
        "    spRequest->uiLength = 0U;\n"
        "    spRequest->uiValue = 0U;\n"
        "    spRequest->uiDataLength = 0U;\n"
        "    spRequest->cArrDevice[0] = '\\0';\n"
        "    spRequest->cArrOperation[0] = '\\0';\n"
        "    spRequest->cArrRegister[0] = '\\0';\n"
        "    for (uiIndex = 0U; uiIndex < SPEC2CODE_TESTBENCH_DATA_MAX; uiIndex++)\n"
        "    {\n"
        "        spRequest->ucArrData[uiIndex] = 0U;\n"
        "    }\n"
        "}\n\n"
        "void spec2codeTestbenchResponseClear(SSpec2codeTestbenchResponse* spResponse)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    if (spResponse == NULL)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    spResponse->uiId = 0U;\n"
        "    spResponse->uiOk = 0U;\n"
        "    spResponse->iStatus = XST_FAILURE;\n"
        "    spResponse->uiValue = 0U;\n"
        "    spResponse->uiDataLength = 0U;\n"
        "    spResponse->cArrMessage[0] = '\\0';\n"
        "    for (uiIndex = 0U; uiIndex < SPEC2CODE_TESTBENCH_DATA_MAX; uiIndex++)\n"
        "    {\n"
        "        spResponse->ucArrData[uiIndex] = 0U;\n"
        "    }\n"
        "}\n\n"
        "void spec2codeTestbenchMessageSet(SSpec2codeTestbenchResponse* spResponse, const char* cpMessage)\n"
        "{\n"
        "    if (spResponse != NULL)\n"
        "    {\n"
        "        (void)spec2codeTestbenchTextCopy(spResponse->cArrMessage, SPEC2CODE_TESTBENCH_MESSAGE_MAX, cpMessage);\n"
        "    }\n"
        "}\n\n"
        "int spec2codeTestbenchDataPush(SSpec2codeTestbenchResponse* spResponse, unsigned char ucValue)\n"
        "{\n"
        "    if ((spResponse == NULL) || (spResponse->uiDataLength >= SPEC2CODE_TESTBENCH_DATA_MAX))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    spResponse->ucArrData[spResponse->uiDataLength] = ucValue;\n"
        "    spResponse->uiDataLength++;\n"
        "    return XST_SUCCESS;\n"
        "}\n\n"
        "int spec2codeTestbenchRequestParse(const char* cpLine, SSpec2codeTestbenchRequest* spRequest)\n"
        "{\n"
        "    char cArrLocal[512];\n"
        "    char* cpToken;\n"
        "    char* cpValue;\n\n"
        "    if ((cpLine == NULL) || (spRequest == NULL))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    spec2codeTestbenchRequestClear(spRequest);\n"
        "    (void)spec2codeTestbenchTextCopy(cArrLocal, sizeof(cArrLocal), cpLine);\n"
        "    cpToken = strtok(cArrLocal, \"|\");\n"
        "    while (cpToken != NULL)\n"
        "    {\n"
        "        cpValue = strchr(cpToken, '=');\n"
        "        if (cpValue != NULL)\n"
        "        {\n"
        "            *cpValue = '\\0';\n"
        "            cpValue++;\n"
        "            if (spec2codeTestbenchStringEqual(cpToken, \"id\") == 1)\n"
        "            {\n"
        "                spRequest->uiId = spec2codeTestbenchNumberParse(cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"device\") == 1)\n"
        "            {\n"
        "                (void)spec2codeTestbenchTextCopy(spRequest->cArrDevice, SPEC2CODE_TESTBENCH_TEXT_MAX, cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"op\") == 1)\n"
        "            {\n"
        "                (void)spec2codeTestbenchTextCopy(spRequest->cArrOperation, SPEC2CODE_TESTBENCH_TEXT_MAX, cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"reg\") == 1)\n"
        "            {\n"
        "                (void)spec2codeTestbenchTextCopy(spRequest->cArrRegister, SPEC2CODE_TESTBENCH_TEXT_MAX, cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"reg_addr\") == 1)\n"
        "            {\n"
        "                spRequest->uiRegister = spec2codeTestbenchNumberParse(cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"address\") == 1)\n"
        "            {\n"
        "                spRequest->uiAddress = spec2codeTestbenchNumberParse(cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"length\") == 1)\n"
        "            {\n"
        "                spRequest->uiLength = spec2codeTestbenchNumberParse(cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"value\") == 1)\n"
        "            {\n"
        "                spRequest->uiValue = spec2codeTestbenchNumberParse(cpValue);\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"data\") == 1)\n"
        "            {\n"
        "                spec2codeTestbenchDataParse(cpValue, spRequest);\n"
        "            }\n"
        "        }\n"
        "        cpToken = strtok(NULL, \"|\");\n"
        "    }\n"
        "    if ((spRequest->cArrDevice[0] == '\\0') || (spRequest->cArrOperation[0] == '\\0'))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    return XST_SUCCESS;\n"
        "}\n\n"
        "int spec2codeTestbenchResponseFormat(const SSpec2codeTestbenchResponse* spResponse,\n"
        "                                      char* cpLine,\n"
        "                                      unsigned int uiLineLength)\n"
        "{\n"
        "    unsigned int uiIndex;\n"
        "    int iWritten;\n"
        "    int iUsed;\n\n"
        "    if ((spResponse == NULL) || (cpLine == NULL) || (uiLineLength == 0U))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    iUsed = snprintf(cpLine, uiLineLength, \"S2C|id=%u|ok=%u|status=%d|value=0x%X|data=\",\n"
        "                     spResponse->uiId, spResponse->uiOk, spResponse->iStatus, spResponse->uiValue);\n"
        "    if ((iUsed < 0) || ((unsigned int)iUsed >= uiLineLength))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    for (uiIndex = 0U; uiIndex < spResponse->uiDataLength; uiIndex++)\n"
        "    {\n"
        "        iWritten = snprintf(&cpLine[iUsed], uiLineLength - (unsigned int)iUsed, \"%02X\", spResponse->ucArrData[uiIndex]);\n"
        "        if ((iWritten < 0) || ((unsigned int)(iUsed + iWritten) >= uiLineLength))\n"
        "        {\n"
        "            return XST_FAILURE;\n"
        "        }\n"
        "        iUsed += iWritten;\n"
        "    }\n"
        "    iWritten = snprintf(&cpLine[iUsed], uiLineLength - (unsigned int)iUsed, \"|message=%s\\n\", spResponse->cArrMessage);\n"
        "    if ((iWritten < 0) || ((unsigned int)(iUsed + iWritten) >= uiLineLength))\n"
        "    {\n"
        "        return XST_FAILURE;\n"
        "    }\n"
        "    return XST_SUCCESS;\n"
        "}\n"
    )


def _testbench_risk(op_name: str) -> str:
    lowered = op_name.lower()
    if any(token in lowered for token in ("erase", "program", "write", "init", "config", "reset")):
        return "risky"
    return "safe"


def _testbench_label(part: str, op_name: str) -> str:
    labels = {
        "LTC2991": {
            "voltage_read": "Tüm voltaj kanallarını oku",
            "current_read": "Akım/differential raw kodlarını oku",
            "vcc_read": "VCC oku",
            "temperature_read": "Internal temperature oku",
            "device_init": "LTC2991 init config uygula",
        },
        "AD7414": {
            "temperature_read": "Sıcaklık oku",
            "config_read": "Config register oku",
        },
        "TMP101": {"temperature_read": "Sıcaklık oku"},
        "SHT21": {"temperature_read": "Sıcaklık oku"},
        "LMK04832": {"device_init": "TICS Pro init sequence uygula"},
        "LMX2820": {"device_init": "TICS Pro init sequence uygula"},
        "LMX1204": {"device_init": "TICS Pro init sequence uygula"},
    }
    generic = {
        "status_read": "Status oku",
        "config_read": "Config oku",
        "power_read": "Power raw oku",
        "sense_read": "Sense/current raw oku",
        "voltage_read": "Voltaj raw oku",
        "current_read": "Akım raw oku",
        "adin_read": "ADIN raw oku",
        "elapsed_read": "Elapsed counter oku",
        "alarm_read": "Alarm counter oku",
        "event_read": "Event counter oku",
        "humidity_read": "Humidity oku",
        "user_register_read": "User register oku",
        "id_read": "JEDEC ID oku",
        "data_read": "Data oku",
        "byte_write": "Byte yaz",
        "page_write": "Page yaz",
        "page_program": "Page programla",
        "sector_erase": "Sector erase",
        "device_init": "Init uygula",
    }
    return labels.get(part, {}).get(op_name, generic.get(op_name, op_name.replace("_", " ")))


def _requested_operations(device: dict, descriptor: dict) -> list[dict]:
    operations = descriptor.get("operations", [])
    requested = device.get("operations_requested")
    if not requested:
        return operations
    requested_set = {str(name) for name in requested}
    return [op for op in operations if op.get("name") in requested_set]


def _supports_i2c_register_ops(descriptor: dict) -> bool:
    if descriptor.get("transport", {}).get("type") != "i2c":
        return False
    if descriptor.get("memory"):
        return False
    registers = descriptor.get("registers") or []
    return any("name" in reg and "offset" in reg and str(reg.get("access", "")).lower() != "reserved" for reg in registers)


def _array_return_count(returns: str) -> int:
    match = re.search(r"\[(\d+)\]", returns)
    return int(match.group(1)) if match else 0


def _operation_fixed_read_length(op: dict) -> int:
    returns = str(op.get("returns", "")).lower()
    array_count = _array_return_count(returns)
    if array_count:
        return array_count * 2
    if "uint16" in returns:
        return 2
    if "uint8" in returns:
        return 1
    for step in op.get("steps", []):
        if step.get("op") == "read_command_address" and "length" in step:
            return int(step.get("length", 0))
    return 0


def _testbench_manifest(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    manifest = {
        "schema_version": "1.0",
        "project": spec.get("project", {}).get("name", ""),
        "protocol": "S2C line protocol v1",
        "line_format": "S2C|id=1|device=<id>|op=<operation>|reg=<name>|reg_addr=0x00|address=0x0|length=16|value=0x00|data=AABB",
        "devices": [],
    }
    for device in spec.get("devices", []):
        descriptor = get_descriptor(device.get("descriptor_ref") or device.get("part", ""))
        operations = []
        for op in _requested_operations(device, descriptor):
            op_name = op.get("name", "")
            needs_address = any(step.get("op") in {"read_command_address", "write_command_address"} and
                                step.get("length") is None for step in op.get("steps", []))
            needs_length = any(step.get("op") == "read_command_address" and "length" not in step
                               for step in op.get("steps", []))
            needs_data = any(step.get("op") == "write_command_address" and step.get("length") != 0
                             for step in op.get("steps", []))
            if descriptor.get("memory") and op_name in {"data_read", "byte_write", "page_write"}:
                needs_address = True
                needs_length = op_name == "data_read"
                needs_data = op_name == "page_write"
            operations.append({
                "name": op_name,
                "label": _testbench_label(device.get("part", ""), op_name),
                "description": op.get("description", ""),
                "risk": _testbench_risk(op_name),
                "implemented": True,
                "fixed_read_length": _operation_fixed_read_length(op),
                "requires_address": needs_address or any(step.get("op") == "write_command_address" for step in op.get("steps", [])),
                "requires_length": needs_length,
                "requires_data": needs_data,
                "requires_register": False,
                "requires_value": False,
            })
        if _supports_i2c_register_ops(descriptor):
            operations.extend([
                {
                    "name": "register_read",
                    "label": "Register oku",
                    "description": "I2C 8-bit register address ile tek byte oku.",
                    "risk": "safe",
                    "implemented": True,
                    "fixed_read_length": 1,
                    "requires_address": False,
                    "requires_length": False,
                    "requires_data": False,
                    "requires_register": True,
                    "requires_value": False,
                },
                {
                    "name": "register_write",
                    "label": "Register yaz",
                    "description": "I2C 8-bit register address ile tek byte yaz.",
                    "risk": "risky",
                    "implemented": True,
                    "fixed_read_length": 0,
                    "requires_address": False,
                    "requires_length": False,
                    "requires_data": False,
                    "requires_register": True,
                    "requires_value": True,
                },
            ])
        manifest["devices"].append({
            "id": device.get("id", ""),
            "part": device.get("part", ""),
            "transport": descriptor.get("transport", {}).get("type", ""),
            "attach": device.get("attach", {}),
            "registers": [
                {
                    "name": reg.get("name", ""),
                    "offset": reg.get("offset", 0),
                    "access": reg.get("access", ""),
                    "width": reg.get("width", 8),
                }
                for reg in descriptor.get("registers", [])
                if "name" in reg and str(reg.get("access", "")).lower() not in {"reserved"}
            ],
            "operations": operations,
        })
    return json_dumps_crlf(manifest)


def json_dumps_crlf(value: dict) -> str:
    import json

    return json.dumps(value, indent=2) + "\n"


def _testbench_ops_header(project_name: str) -> str:
    guard = _header_guard(f"{project_name}_testbench_ops_h")
    return (
        "/**\n"
        f" * @file {project_name}_testbench_ops.h\n"
        " * @brief Generated operation dispatch for the Spec2Code target test bench.\n"
        " */\n"
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        '#include "spec2code_testbench_protocol.h"\n'
        '#include "xiicps.h"\n'
        '#include "xspips.h"\n'
        '#include "xqspipsu.h"\n\n'
        "typedef struct\n"
        "{\n"
        "    const char* cpDeviceId;\n"
        "    const char* cpPart;\n"
        "    const char* cpOperation;\n"
        "    const char* cpLabel;\n"
        "    const char* cpRisk;\n"
        "} SSpec2codeTestbenchOperation;\n\n"
        "XIicPs* spec2codeTestbenchIicPsHandleGet(const char* cpControllerId);\n"
        "XSpiPs* spec2codeTestbenchSpiPsHandleGet(const char* cpControllerId);\n"
        "XQspiPsu* spec2codeTestbenchQspiPsuHandleGet(const char* cpControllerId);\n"
        "unsigned int spec2codeTestbenchOperationCount(void);\n"
        "const SSpec2codeTestbenchOperation* spec2codeTestbenchOperationGet(unsigned int uiIndex);\n"
        "int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,\n"
        "                               SSpec2codeTestbenchResponse* spResponse);\n"
        "int spec2codeTestbenchDispatchLine(const char* cpRequestLine,\n"
        "                                   char* cpResponseLine,\n"
        "                                   unsigned int uiResponseLength);\n\n"
        f"#endif /* {guard} */\n"
    )


def _testbench_getter(htype: str) -> str | None:
    return {
        "XIicPs": "spec2codeTestbenchIicPsHandleGet",
        "XSpiPs": "spec2codeTestbenchSpiPsHandleGet",
        "XQspiPsu": "spec2codeTestbenchQspiPsuHandleGet",
    }.get(htype)


def _testbench_device_entries(spec: dict, get_descriptor: Callable[[str], dict]) -> list[dict]:
    controllers = {controller["id"]: controller for controller in spec.get("controllers", [])}
    muxes = {mux["id"]: mux for mux in spec.get("muxes", [])}
    entries: list[dict] = []
    for device in spec.get("devices", []):
        descriptor = get_descriptor(device.get("descriptor_ref") or device.get("part", ""))
        attach = device.get("attach", {})
        controller = controllers.get(attach.get("controller_id"))
        if controller is None:
            continue
        htype, hvar = cmodel._handle_for(controller)
        via_mux = attach.get("via_mux") or {}
        mux = muxes.get(via_mux.get("mux_id")) if isinstance(via_mux, dict) else None
        entries.append({
            "device": device,
            "descriptor": descriptor,
            "controller": controller,
            "module": cmodel._module_of(device.get("part", "")),
            "htype": htype,
            "hvar": hvar,
            "getter": _testbench_getter(htype),
            "mux": mux,
            "mux_module": cmodel._module_of(mux["part"]) if mux else None,
            "mux_channel": via_mux.get("channel") if isinstance(via_mux, dict) else None,
        })
    return entries


def _testbench_op_table(entries: list[dict]) -> list[dict]:
    rows: list[dict] = []
    for entry in entries:
        device = entry["device"]
        descriptor = entry["descriptor"]
        for op in _requested_operations(device, descriptor):
            op_name = op.get("name", "")
            rows.append({
                "device": device.get("id", ""),
                "part": device.get("part", ""),
                "operation": op_name,
                "label": _testbench_label(device.get("part", ""), op_name),
                "risk": _testbench_risk(op_name),
            })
        if _supports_i2c_register_ops(descriptor):
            rows.append({
                "device": device.get("id", ""),
                "part": device.get("part", ""),
                "operation": "register_read",
                "label": "Register oku",
                "risk": "safe",
            })
            rows.append({
                "device": device.get("id", ""),
                "part": device.get("part", ""),
                "operation": "register_write",
                "label": "Register yaz",
                "risk": "risky",
            })
    return rows


def _testbench_register_resolver(entry: dict) -> list[str]:
    module = entry["module"]
    MOD = module.upper()
    regs = [
        reg for reg in entry["descriptor"].get("registers", [])
        if "name" in reg and "offset" in reg and str(reg.get("access", "")).lower() != "reserved"
    ]
    if not regs:
        return []
    func = f"{module}TestbenchRegisterResolve"
    lines = [
        f"static int {func}(const char* cpRegister, unsigned int uiRegister, unsigned char* ucpReg)",
        "{",
        "    if (ucpReg == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
    ]
    for reg in regs:
        lines.extend([
            f"    if (spec2codeTestbenchStringEqual(cpRegister, \"{reg['name']}\") == 1)",
            "    {",
            f"        *ucpReg = {MOD}_REG_{reg['name']};",
            "        return XST_SUCCESS;",
            "    }",
        ])
    lines.extend([
        "    if (uiRegister <= 0xFFU)",
        "    {",
        "        *ucpReg = (unsigned char)uiRegister;",
        "        return XST_SUCCESS;",
        "    }",
        "    return XST_FAILURE;",
        "}",
        "",
    ])
    return lines


def _testbench_i2c_helpers() -> list[str]:
    return [
        "static int spec2codeTestbenchI2cRegisterRead(XIicPs* spIic, unsigned char ucAddress,",
        "                                             unsigned char ucReg, unsigned char* ucpValue)",
        "{",
        "    int iStatus;",
        "",
        "    if ((spIic == NULL) || (ucpValue == NULL))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    iStatus = XIicPs_MasterSendPolled(spIic, &ucReg, 1, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    iStatus = XIicPs_MasterRecvPolled(spIic, ucpValue, 1, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    return XST_SUCCESS;",
        "}",
        "",
        "static int spec2codeTestbenchI2cRegisterWrite(XIicPs* spIic, unsigned char ucAddress,",
        "                                              unsigned char ucReg, unsigned char ucValue)",
        "{",
        "    unsigned char ucArrBuffer[2];",
        "    int iStatus;",
        "",
        "    if (spIic == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    ucArrBuffer[0] = ucReg;",
        "    ucArrBuffer[1] = ucValue;",
        "    iStatus = XIicPs_MasterSendPolled(spIic, ucArrBuffer, 2, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    return XST_SUCCESS;",
        "}",
        "",
    ]


def _testbench_push_u16_lines(var_name: str) -> list[str]:
    return [
        f"iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)(({var_name} >> 8U) & 0xFFU));",
        "if (iStatus != XST_SUCCESS)",
        "{",
        "    return iStatus;",
        "}",
        f"iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)({var_name} & 0xFFU));",
        "if (iStatus != XST_SUCCESS)",
        "{",
        "    return iStatus;",
        "}",
    ]


def _testbench_call_lines(entry: dict, op: dict) -> list[str]:
    module = entry["module"]
    hvar = entry["hvar"]
    descriptor = entry["descriptor"]
    op_name = op.get("name", "")
    func = f"{module}{_pascal_identifier(op_name)}"
    returns = str(op.get("returns", "")).lower()
    fixed_len = _operation_fixed_read_length(op)
    lines: list[str] = []

    array_count = _array_return_count(returns)

    if op_name == "device_init":
        lines.append(f"iStatus = {func}({hvar});")
    elif descriptor.get("memory") and op_name == "data_read":
        lines.extend([
            "uiLength = spRequest->uiLength;",
            "if ((uiLength == 0U) || (uiLength > SPEC2CODE_TESTBENCH_DATA_MAX))",
            "{",
            "    uiLength = 16U;",
            "}",
            f"iStatus = {func}({hvar}, spRequest->uiAddress, ucArrData, uiLength);",
            "if (iStatus == XST_SUCCESS)",
            "{",
            "    for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)",
            "    {",
            "        iStatus = spec2codeTestbenchDataPush(spResponse, ucArrData[uiIndex]);",
            "        if (iStatus != XST_SUCCESS)",
            "        {",
            "            return iStatus;",
            "        }",
            "    }",
            "}",
        ])
    elif descriptor.get("memory") and op_name == "byte_write":
        lines.append(f"iStatus = {func}({hvar}, spRequest->uiAddress, (unsigned char)spRequest->uiValue);")
    elif descriptor.get("memory") and op_name == "page_write":
        lines.append(f"iStatus = {func}({hvar}, spRequest->uiAddress, spRequest->ucArrData, spRequest->uiDataLength);")
    elif array_count:
        lines.append(f"iStatus = {func}({hvar}, usArrValues);")
        lines.extend([
            "if (iStatus == XST_SUCCESS)",
            "{",
            f"    for (uiIndex = 0U; uiIndex < {array_count}U; uiIndex++)",
            "    {",
        ])
        lines.extend([f"        {line}" for line in _testbench_push_u16_lines("usArrValues[uiIndex]")])
        lines.extend([
            "    }",
            "}",
        ])
    elif "uint16" in returns:
        out_name = op_name.split("_")[0]
        lines.append(f"iStatus = {func}({hvar}, &usValue);")
        lines.extend([
            "if (iStatus == XST_SUCCESS)",
            "{",
            "    spResponse->uiValue = (unsigned int)usValue;",
        ])
        lines.extend([f"    {line}" for line in _testbench_push_u16_lines("usValue")])
        lines.append("}")
        void = out_name
        del void
    elif "uint8" in returns:
        lines.append(f"iStatus = {func}({hvar}, &ucValue);")
        lines.extend([
            "if (iStatus == XST_SUCCESS)",
            "{",
            "    spResponse->uiValue = (unsigned int)ucValue;",
            "    iStatus = spec2codeTestbenchDataPush(spResponse, ucValue);",
            "}",
        ])
    elif any(step.get("op") == "read_command_address" for step in op.get("steps", [])):
        if fixed_len:
            lines.append(f"iStatus = {func}({hvar}, ucArrData);")
            lines.extend([
                "if (iStatus == XST_SUCCESS)",
                "{",
                f"    for (uiIndex = 0U; uiIndex < {fixed_len}U; uiIndex++)",
                "    {",
                "        iStatus = spec2codeTestbenchDataPush(spResponse, ucArrData[uiIndex]);",
                "        if (iStatus != XST_SUCCESS)",
                "        {",
                "            return iStatus;",
                "        }",
                "    }",
                "}",
            ])
        else:
            lines.extend([
                "uiLength = spRequest->uiLength;",
                "if ((uiLength == 0U) || (uiLength > SPEC2CODE_TESTBENCH_DATA_MAX))",
                "{",
                "    uiLength = 16U;",
                "}",
                f"iStatus = {func}({hvar}, spRequest->uiAddress, ucArrData, uiLength);",
                "if (iStatus == XST_SUCCESS)",
                "{",
                "    for (uiIndex = 0U; uiIndex < uiLength; uiIndex++)",
                "    {",
                "        iStatus = spec2codeTestbenchDataPush(spResponse, ucArrData[uiIndex]);",
                "        if (iStatus != XST_SUCCESS)",
                "        {",
                "            return iStatus;",
                "        }",
                "    }",
                "}",
            ])
    elif any(step.get("op") == "write_command_address" for step in op.get("steps", [])):
        if any(step.get("op") == "write_command_address" and step.get("length") == 0 for step in op.get("steps", [])):
            lines.append(f"iStatus = {func}({hvar}, spRequest->uiAddress);")
        else:
            lines.append(f"iStatus = {func}({hvar}, spRequest->uiAddress, spRequest->ucArrData, spRequest->uiDataLength);")
    elif op_name.endswith("_read"):
        lines.append("iStatus = XST_FAILURE;")
        lines.append("spec2codeTestbenchMessageSet(spResponse, \"operation signature not mapped\");")
    else:
        lines.append(f"iStatus = {func}({hvar});")
    return lines


def _testbench_device_branch(entry: dict) -> list[str]:
    device = entry["device"]
    descriptor = entry["descriptor"]
    module = entry["module"]
    MOD = module.upper()
    htype = entry["htype"]
    hvar = entry["hvar"]
    getter = entry["getter"]
    operations = _requested_operations(device, descriptor)
    register_ops = _supports_i2c_register_ops(descriptor)
    needs_array = any(_array_return_count(str(op.get("returns", "")).lower()) for op in operations)
    needs_us_value = any("uint16" in str(op.get("returns", "")).lower() for op in operations)
    needs_uc_value = register_ops or any("uint8" in str(op.get("returns", "")).lower() for op in operations)
    needs_uc_reg = register_ops
    needs_data = any(
        descriptor.get("memory") and op.get("name") == "data_read" or
        any(step.get("op") == "read_command_address" for step in op.get("steps", []))
        for op in operations
    )
    needs_ui_length = any(
        descriptor.get("memory") and op.get("name") == "data_read" or
        any(step.get("op") == "read_command_address" and "length" not in step for step in op.get("steps", []))
        for op in operations
    )
    needs_ui_index = needs_array or any(
        descriptor.get("memory") and op.get("name") == "data_read" or
        any(step.get("op") == "read_command_address" for step in op.get("steps", []))
        for op in operations
    )
    lines = [
        f"    if (spec2codeTestbenchStringEqual(spRequest->cArrDevice, \"{device.get('id', '')}\") == 1)",
        "    {",
        f"        {htype}* {hvar};",
    ]
    if needs_us_value:
        lines.append("        unsigned short usValue;")
    if needs_array:
        lines.append("        unsigned short usArrValues[8];")
    if needs_uc_value:
        lines.append("        unsigned char ucValue;")
    if needs_uc_reg:
        lines.append("        unsigned char ucReg;")
    if needs_data:
        lines.append("        unsigned char ucArrData[SPEC2CODE_TESTBENCH_DATA_MAX];")
    if needs_ui_index:
        lines.append("        unsigned int uiIndex;")
    if needs_ui_length:
        lines.append("        unsigned int uiLength;")
    lines.extend([
        "        int iStatus;",
        "",
    ])
    if getter is None:
        lines.extend([
            "        spResponse->iStatus = XST_FAILURE;",
            "        spec2codeTestbenchMessageSet(spResponse, \"unsupported controller handle type\");",
            "        return XST_FAILURE;",
            "    }",
        ])
        return lines

    lines.extend([
        f"        {hvar} = {getter}(\"{entry['controller'].get('id', '')}\");",
        f"        if ({hvar} == NULL)",
        "        {",
        "            spResponse->iStatus = XST_FAILURE;",
        "            spec2codeTestbenchMessageSet(spResponse, \"board handle hook returned NULL\");",
        "            return XST_FAILURE;",
        "        }",
    ])
    if entry["mux_module"] is not None:
        lines.extend([
            f"        iStatus = {cmodel._func_name(entry['mux_module'], 'channel_select')}({hvar}, {int(entry['mux_channel'])}U);",
            "        if (iStatus != XST_SUCCESS)",
            "        {",
            "            spResponse->iStatus = iStatus;",
            "            spec2codeTestbenchMessageSet(spResponse, \"mux channel select failed\");",
            "            return iStatus;",
            "        }",
        ])

    if register_ops:
        lines.extend([
            "        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"register_read\") == 1)",
            "        {",
            f"            iStatus = {module}TestbenchRegisterResolve(spRequest->cArrRegister, spRequest->uiRegister, &ucReg);",
            "            if (iStatus != XST_SUCCESS)",
            "            {",
            "                spResponse->iStatus = iStatus;",
            "                spec2codeTestbenchMessageSet(spResponse, \"register not found\");",
            "                return iStatus;",
            "            }",
            f"            iStatus = spec2codeTestbenchI2cRegisterRead({hvar}, {MOD}_I2C_ADDR, ucReg, &ucValue);",
            "            spResponse->iStatus = iStatus;",
            "            spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
            "            spResponse->uiValue = (unsigned int)ucValue;",
            "            if (iStatus == XST_SUCCESS)",
            "            {",
            "                (void)spec2codeTestbenchDataPush(spResponse, ucValue);",
            "                spec2codeTestbenchMessageSet(spResponse, \"register_read ok\");",
            "            }",
            "            return iStatus;",
            "        }",
            "        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"register_write\") == 1)",
            "        {",
            f"            iStatus = {module}TestbenchRegisterResolve(spRequest->cArrRegister, spRequest->uiRegister, &ucReg);",
            "            if (iStatus != XST_SUCCESS)",
            "            {",
            "                spResponse->iStatus = iStatus;",
            "                spec2codeTestbenchMessageSet(spResponse, \"register not found\");",
            "                return iStatus;",
            "            }",
            f"            iStatus = spec2codeTestbenchI2cRegisterWrite({hvar}, {MOD}_I2C_ADDR, ucReg, (unsigned char)spRequest->uiValue);",
            "            spResponse->iStatus = iStatus;",
            "            spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
            "            spec2codeTestbenchMessageSet(spResponse, (iStatus == XST_SUCCESS) ? \"register_write ok\" : \"register_write failed\");",
            "            return iStatus;",
            "        }",
        ])

    for op in operations:
        op_name = op.get("name", "")
        lines.extend([
            f"        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"{op_name}\") == 1)",
            "        {",
        ])
        for call_line in _testbench_call_lines(entry, op):
            lines.append(f"            {call_line}" if call_line else "")
        lines.extend([
            "            spResponse->iStatus = iStatus;",
            "            spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
            f"            spec2codeTestbenchMessageSet(spResponse, (iStatus == XST_SUCCESS) ? \"{op_name} ok\" : \"{op_name} failed\");",
            "            return iStatus;",
            "        }",
        ])
    lines.extend([
        "        spResponse->iStatus = XST_FAILURE;",
        "        spec2codeTestbenchMessageSet(spResponse, \"operation not found for device\");",
        "        return XST_FAILURE;",
        "    }",
    ])
    return lines


def _testbench_ops_source(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    project_name = spec["project"]["name"]
    entries = _testbench_device_entries(spec, get_descriptor)
    rows = _testbench_op_table(entries)
    includes = [
        f'#include "{project_name}_testbench_ops.h"',
        '#include "xstatus.h"',
        '#include <stddef.h>',
        "",
    ]
    for entry in entries:
        includes.append(f'#include "{entry["module"]}.h"')
    mux_modules = sorted({entry["mux_module"] for entry in entries if entry["mux_module"] is not None})
    for mux_module in mux_modules:
        includes.append(f'#include "{mux_module}.h"')
    includes.append("")

    lines = [
        "/**",
        f" * @file {project_name}_testbench_ops.c",
        " * @brief Generated operation dispatch for the Spec2Code target test bench.",
        " */",
        *includes,
        "#if defined(__GNUC__)",
        "#define SPEC2CODE_WEAK __attribute__((weak))",
        "#else",
        "#define SPEC2CODE_WEAK",
        "#endif",
        "",
        "SPEC2CODE_WEAK XIicPs* spec2codeTestbenchIicPsHandleGet(const char* cpControllerId)",
        "{",
        "    (void)cpControllerId;",
        "    return NULL;",
        "}",
        "",
        "SPEC2CODE_WEAK XSpiPs* spec2codeTestbenchSpiPsHandleGet(const char* cpControllerId)",
        "{",
        "    (void)cpControllerId;",
        "    return NULL;",
        "}",
        "",
        "SPEC2CODE_WEAK XQspiPsu* spec2codeTestbenchQspiPsuHandleGet(const char* cpControllerId)",
        "{",
        "    (void)cpControllerId;",
        "    return NULL;",
        "}",
        "",
        *(_testbench_i2c_helpers() if any(entry["descriptor"].get("transport", {}).get("type") == "i2c" for entry in entries) else []),
    ]
    for entry in entries:
        if _supports_i2c_register_ops(entry["descriptor"]):
            lines.extend(_testbench_register_resolver(entry))

    lines.extend([
        f"#define SPEC2CODE_TESTBENCH_OPERATION_COUNT {len(rows)}U",
        "",
        "static const SSpec2codeTestbenchOperation S_sArrSpec2codeTestbenchOperations[SPEC2CODE_TESTBENCH_OPERATION_COUNT] =",
        "{",
    ])
    for row in rows:
        lines.append(
            f"    {{ \"{row['device']}\", \"{row['part']}\", \"{row['operation']}\", "
            f"\"{row['label']}\", \"{row['risk']}\" }},"
        )
    lines.extend([
        "};",
        "",
        "unsigned int spec2codeTestbenchOperationCount(void)",
        "{",
        "    return SPEC2CODE_TESTBENCH_OPERATION_COUNT;",
        "}",
        "",
        "const SSpec2codeTestbenchOperation* spec2codeTestbenchOperationGet(unsigned int uiIndex)",
        "{",
        "    if (uiIndex >= SPEC2CODE_TESTBENCH_OPERATION_COUNT)",
        "    {",
        "        return NULL;",
        "    }",
        "    return &S_sArrSpec2codeTestbenchOperations[uiIndex];",
        "}",
        "",
        "int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,",
        "                               SSpec2codeTestbenchResponse* spResponse)",
        "{",
        "    if ((spRequest == NULL) || (spResponse == NULL))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    spec2codeTestbenchResponseClear(spResponse);",
        "    spResponse->uiId = spRequest->uiId;",
    ])
    for entry in entries:
        lines.extend(_testbench_device_branch(entry))
    lines.extend([
        "    spResponse->iStatus = XST_FAILURE;",
        "    spec2codeTestbenchMessageSet(spResponse, \"device not found\");",
        "    return XST_FAILURE;",
        "}",
        "",
        "int spec2codeTestbenchDispatchLine(const char* cpRequestLine,",
        "                                   char* cpResponseLine,",
        "                                   unsigned int uiResponseLength)",
        "{",
        "    SSpec2codeTestbenchRequest sRequest;",
        "    SSpec2codeTestbenchResponse sResponse;",
        "    int iStatus;",
        "",
        "    iStatus = spec2codeTestbenchRequestParse(cpRequestLine, &sRequest);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeTestbenchResponseClear(&sResponse);",
        "        sResponse.iStatus = iStatus;",
        "        spec2codeTestbenchMessageSet(&sResponse, \"request parse failed\");",
        "        return spec2codeTestbenchResponseFormat(&sResponse, cpResponseLine, uiResponseLength);",
        "    }",
        "    (void)spec2codeTestbenchDispatch(&sRequest, &sResponse);",
        "    return spec2codeTestbenchResponseFormat(&sResponse, cpResponseLine, uiResponseLength);",
        "}",
        "",
    ])
    return "\n".join(lines)


def testbench_harness_paths(spec: dict, out_dir: Path) -> list[Path]:
    project_name = spec["project"]["name"]
    tests_dir = out_dir / "tests"
    return [
        tests_dir / "spec2code_testbench_protocol.h",
        tests_dir / "spec2code_testbench_protocol.c",
        tests_dir / f"{project_name}_testbench_ops.h",
        tests_dir / f"{project_name}_testbench_ops.c",
        tests_dir / "spec2code_testbench_manifest.json",
    ]


def write_testbench_harness(spec: dict, out_dir: Path, *, root: Path = _ROOT) -> list[str]:
    get_descriptor = make_descriptor_loader(root)
    paths = testbench_harness_paths(spec, out_dir)
    contents = [
        _apply_default_identifier_style(_testbench_protocol_header()),
        _apply_default_identifier_style(_testbench_protocol_source()),
        _apply_default_identifier_style(_testbench_ops_header(spec["project"]["name"])),
        _apply_default_identifier_style(_testbench_ops_source(spec, get_descriptor)),
        _testbench_manifest(spec, get_descriptor),
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
            descriptor_name = "".join(ch.lower() for ch in ref_or_part if ch.isalnum())
            path = root / "descriptors" / f"{descriptor_name}.yaml"
            if not path.is_file():
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
    written.extend(write_testbench_harness(spec, out_dir, root=root))

    emit({"event": "codegen.done", "files": len(written)})
    return written
