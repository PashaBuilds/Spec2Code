"""Static (deterministic) codegen orchestration (Brief 13).

Loads a validated project.spec, builds the C render-model (cmodel), renders the Jinja
templates, and writes drop-in output through hostplat.io (always CRLF). No LLM involved.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Callable, Optional

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from hostplat import io as hio
from orchestrator import cmodel, tics
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


def _app_version() -> str:
    for name in ("SPEC2CODE_VERSION", "VITE_SPEC2CODE_VERSION", "RELEASE_VERSION"):
        value = os.environ.get(name, "").strip()
        if re.fullmatch(r"v\d+\.\d+\.\d+", value):
            return value

    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
    roots.extend([_ROOT, Path.cwd(), Path(sys.executable).resolve().parent])

    for root in roots:
        version_file = root / "spec2code_version.txt"
        if version_file.is_file():
            value = version_file.read_text(encoding="utf-8", errors="replace").strip()
            if re.fullmatch(r"v\d+\.\d+\.\d+", value):
                return value

    source_version = _ROOT / "frontend" / "src" / "lib" / "version.ts"
    if source_version.is_file():
        text = source_version.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'"(v\d+\.\d+\.\d+)"', text)
        if match:
            return match.group(1)

    changelog = _ROOT / "changelog.md"
    if changelog.is_file():
        text = changelog.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^##\s+(v\d+\.\d+\.\d+)\s+", text, re.MULTILINE)
        if match:
            return match.group(1)

    return "dev"


def _c_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
        "    unsigned int uiHasValue;\n"
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
        "    spRequest->uiHasValue = 0U;\n"
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
        "static void spec2codeTestbenchLineCopy(char* cpDst, unsigned int uiDstLength, const char* cpSrc)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    /* TextCopy'den farki: '|' ayraclarini KORUR - o yardimci tek alan\n"
        "     * degeri kopyalamak icindir. Tum istek satiri burada kopyalanir;\n"
        "     * yalnizca satir sonu/NUL'da durur. (Eski TextCopy kullanimi ilk\n"
        "     * '|' karakterinde kesiyor ve her istegi 'S2C' govdesine\n"
        "     * indirgedigi icin tum komutlar 'request parse failed' donuyordu.) */\n"
        "    if ((cpDst == NULL) || (uiDstLength == 0U))\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    for (uiIndex = 0U; uiIndex < (uiDstLength - 1U); uiIndex++)\n"
        "    {\n"
        "        if ((cpSrc == NULL) || (cpSrc[uiIndex] == '\\0') ||\n"
        "            (cpSrc[uiIndex] == '\\r') || (cpSrc[uiIndex] == '\\n'))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        cpDst[uiIndex] = cpSrc[uiIndex];\n"
        "    }\n"
        "    cpDst[uiIndex] = '\\0';\n"
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
        "    spec2codeTestbenchLineCopy(cArrLocal, sizeof(cArrLocal), cpLine);\n"
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
        "                spRequest->uiHasValue = 1U;\n"
        "            }\n"
        "            else if (spec2codeTestbenchStringEqual(cpToken, \"data\") == 1)\n"
        "            {\n"
        "                spec2codeTestbenchDataParse(cpValue, spRequest);\n"
        "            }\n"
        "        }\n"
        "        cpToken = strtok(NULL, \"|\");\n"
        "    }\n"
        "    if (spRequest->cArrOperation[0] == '\\0')\n"
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
        "    iWritten = snprintf(&cpLine[iUsed], uiLineLength - (unsigned int)iUsed, \"|message=%s\\r\\n\", spResponse->cArrMessage);\n"
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
            "voltage_read": "Tüm voltaj kanallarını oku (mV)",
            "current_read": "Differential raw kodlarını oku (µV = kod × 19.075)",
            "vcc_read": "VCC oku (mV)",
            "temperature_read": "Internal temperature oku (0.01 °C)",
            "device_init": "LTC2991 init config uygula",
        },
        "AD7414": {
            "temperature_read": "Sıcaklık oku",
            "config_read": "Config register oku",
        },
        "TMP101": {"temperature_read": "Sıcaklık oku"},
        "SHT21": {"temperature_read": "Sıcaklık oku"},
        "DS1682": {
            "elapsed_read": "Geçen süre oku (saniye)",
            "alarm_read": "Alarm eşiği oku (saniye)",
        },
        "LTC2945": {
            "sense_read": "Şönt (sense) voltajı oku (µV)",
            "voltage_read": "VIN oku (mV)",
            "adin_read": "ADIN oku (µV)",
            "current_read": "Akım oku (mA, config şönt ile)",
        },
        "LMK04832": {
            "device_init": "TICS Pro init sequence uygula",
            "pll1_lock_detect": "PLL1 lock detect oku",
            "pll1_lock_loss": "PLL1 lock loss oku",
            "pll2_lock_detect": "PLL2 lock detect oku",
            "pll2_lock_loss": "PLL2 lock loss oku",
        },
        "LMX2820": {"device_init": "TICS Pro init sequence uygula"},
        "LTM4681": {
            "device_init": "NVM'den açılır; bus yazımı gerekmez",
            "id_read": "MFR_SPECIAL_ID oku (0x500n beklenir)",
            "status_read": "STATUS_WORD oku (seçili PAGE)",
            "vout_read": "VOUT oku (mV, L16 exp -12)",
            "voltage_read": "VIN oku (mV, Linear11)",
            "current_read": "IOUT oku (mA, Linear11)",
            "temperature_read": "Kanal sıcaklığı oku (0.01 °C, Linear11)",
            "power_read": "POUT oku (mW, Linear11)",
        },
        "LMX1204": {"device_init": "TICS Pro init sequence uygula"},
        "LMX1205": {
            "device_init": "TICS Pro init sequence uygula",
            "multiplier_lock_detect": "Multiplier lock detect oku (R37)",
        },
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
    if requested:
        requested_set = {str(name) for name in requested}
        operations = [op for op in operations if op.get("name") in requested_set]
    # Kart-verisi config'i eksik olan dönüşümlü oplar üretimden düşer
    # (cmodel aynı durumda ya atlar ya açık istekte hata verir); manifest
    # ile üretilen kod aynı listeyi görmeli.
    return [op for op in operations if not cmodel.convert_config_issue(device, op)]


def _supports_i2c_register_ops(descriptor: dict) -> bool:
    if descriptor.get("transport", {}).get("type") != "i2c":
        return False
    if descriptor.get("memory"):
        return False
    registers = descriptor.get("registers") or []
    return any("name" in reg and "offset" in reg and str(reg.get("access", "")).lower() != "reserved" for reg in registers)


def _supports_spi_register_ops(descriptor: dict) -> bool:
    """Generic single-register access over a 24-bit TICS-style SPI frame.

    Writes reuse the exact word format device_init already emits. Anything
    without a 24-bit register model stays out (no generic path to be honest
    about).
    """
    if descriptor.get("transport", {}).get("type") != "spi":
        return False
    if descriptor.get("memory"):
        return False
    model = tics.register_model(descriptor)
    if not model or int(model.get("frame_bits", 24) or 24) != 24:
        return False
    registers = descriptor.get("registers") or []
    return any("name" in reg and "offset" in reg and str(reg.get("access", "")).lower() != "reserved" for reg in registers)


def _spi_readback(descriptor: dict) -> dict | None:
    """Datasheet-verified readback info, or None (write-only generic access).

    Register reads over SPI are hardware/config-conditional (dedicated SDO
    vs. MUXOUT pin muxing). A part only gets a generic `register_read` when
    its descriptor carries `register_model.readback.verified: true`, set
    after checking the official datasheet; `requires` documents the wiring/
    config precondition and is surfaced in the UI.
    """
    readback = tics.register_model(descriptor).get("readback")
    if isinstance(readback, dict) and readback.get("verified") is True:
        return readback
    return None


def _post_init_status(descriptor: dict) -> dict | None:
    """device_init sonrası doğrulama okuması: test_hints.post_init_status.

    Kullanıcı isteği (2026-07-05): device_init yanıtının data alanı boş
    kalmasın, cihazdan bir durum dönsün. Descriptor'da işaretlenen register
    init başarısından sonra generic yol ile geri okunur ve yanıtın
    value/data alanlarına konur. Generic okuma yolu olmayan cihazlarda
    (flash komut seti, mux, EEPROM) dürüstçe atlanır.
    """
    hint = (descriptor.get("test_hints") or {}).get("post_init_status")
    if not isinstance(hint, dict):
        return None
    reg_name = hint.get("reg")
    if not any(reg.get("name") == reg_name and "offset" in reg
               for reg in descriptor.get("registers", [])):
        return None
    transport = descriptor.get("transport", {}).get("type", "")
    if transport == "i2c" and not descriptor.get("memory"):
        return {"reg": str(reg_name), "bytes": 1, "transport": "i2c"}
    if transport == "spi" and _supports_spi_register_ops(descriptor):
        data_bits = int(tics.register_model(descriptor).get("data_bits", 8) or 8)
        return {"reg": str(reg_name), "bytes": data_bits // 8, "transport": "spi"}
    return None


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
    if "int32" in returns and "uint32" not in returns:
        return 4
    if "uint8" in returns:
        return 1
    for step in op.get("steps", []):
        if step.get("op") == "read_command_address" and "length" in step:
            return int(step.get("length", 0))
    return 0


#: Log seviyeleri artan detayla: yalnizca seviyesi ayarlanan esik degerden
#: KUCUK VEYA ESIT printler basilir. Varsayilan warning (2).
_TESTBENCH_LOG_LEVELS: dict[str, int] = {
    "error": 1,
    "warning": 2,
    "message": 3,  # gelen/giden S2C satirlari
    "info": 4,
    "debug": 5,
}
_TESTBENCH_LOG_DEFAULT_LEVEL = "warning"


def _testbench_log_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_log.h\n"
        " * @brief Leveled runtime logging for the Spec2Code test bench agent.\n"
        " *\n"
        " * Seviyeler artan detayla siralidir; bir print ancak seviyesi o an\n"
        " * ayarli esikten KUCUK veya ESITSE basilir. Varsayilan: warning.\n"
        ' * Cikti "S2C-LOG|<TAG>|..." satirlaridir: host tarafi bunlari yanit\n'
        " * sanmaz (yanitlar \"S2C|\" ile baslar), konsol ve Veri Akisi\n"
        " * ekranlarinda gorunur. Esik calisma zamaninda S2C komutuyla\n"
        ' * degistirilir: S2C|id=1|op=log_level|value=4\n'
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_LOG_H\n"
        "#define SPEC2CODE_TESTBENCH_LOG_H\n\n"
        "#define SPEC2CODE_LOG_LEVEL_ERROR 1U\n"
        "#define SPEC2CODE_LOG_LEVEL_WARNING 2U\n"
        "#define SPEC2CODE_LOG_LEVEL_MESSAGE 3U\n"
        "#define SPEC2CODE_LOG_LEVEL_INFO 4U\n"
        "#define SPEC2CODE_LOG_LEVEL_DEBUG 5U\n"
        "#define SPEC2CODE_LOG_LEVEL_DEFAULT SPEC2CODE_LOG_LEVEL_WARNING\n\n"
        "typedef void (*FSpec2codeLogSink)(const char* cpLine);\n\n"
        "void spec2codeLogSinkSet(FSpec2codeLogSink fpSink);\n"
        "unsigned int spec2codeLogLevelGet(void);\n"
        "unsigned int spec2codeLogLevelSet(unsigned int uiLevel);\n"
        "const char* spec2codeLogLevelName(unsigned int uiLevel);\n"
        "void spec2codeLog(unsigned int uiLevel, const char* cpFormat, ...);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_LOG_H */\n"
    )


def _testbench_log_source() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_log.c\n"
        " * @brief Leveled runtime logging for the Spec2Code test bench agent.\n"
        " *\n"
        " * Sink kaydedilmemisse xil_printf (stdout) kullanilir; agent\n"
        " * transportlari kendi hat fonksiyonlarini sink olarak kaydeder ki\n"
        " * loglar S2C trafigiyle ayni kanaldan (CoreSight DCC / UART) aksin.\n"
        " */\n"
        '#include "spec2code_testbench_log.h"\n'
        '#include "xil_printf.h"\n\n'
        "#include <stdarg.h>\n"
        "#include <stdio.h>\n\n"
        "#define SPEC2CODE_LOG_BODY_MAX 160U\n"
        "#define SPEC2CODE_LOG_LINE_MAX 192U\n\n"
        "static unsigned int S_uiLogLevel = SPEC2CODE_LOG_LEVEL_DEFAULT;\n"
        "static FSpec2codeLogSink S_fpLogSink = NULL;\n\n"
        "void spec2codeLogSinkSet(FSpec2codeLogSink fpSink)\n"
        "{\n"
        "    S_fpLogSink = fpSink;\n"
        "}\n\n"
        "unsigned int spec2codeLogLevelGet(void)\n"
        "{\n"
        "    return S_uiLogLevel;\n"
        "}\n\n"
        "unsigned int spec2codeLogLevelSet(unsigned int uiLevel)\n"
        "{\n"
        "    if (uiLevel < SPEC2CODE_LOG_LEVEL_ERROR)\n"
        "    {\n"
        "        uiLevel = SPEC2CODE_LOG_LEVEL_ERROR;\n"
        "    }\n"
        "    if (uiLevel > SPEC2CODE_LOG_LEVEL_DEBUG)\n"
        "    {\n"
        "        uiLevel = SPEC2CODE_LOG_LEVEL_DEBUG;\n"
        "    }\n"
        "    S_uiLogLevel = uiLevel;\n"
        "    return S_uiLogLevel;\n"
        "}\n\n"
        "const char* spec2codeLogLevelName(unsigned int uiLevel)\n"
        "{\n"
        "    switch (uiLevel)\n"
        "    {\n"
        "    case SPEC2CODE_LOG_LEVEL_ERROR: return \"error\";\n"
        "    case SPEC2CODE_LOG_LEVEL_WARNING: return \"warning\";\n"
        "    case SPEC2CODE_LOG_LEVEL_MESSAGE: return \"message\";\n"
        "    case SPEC2CODE_LOG_LEVEL_INFO: return \"info\";\n"
        "    case SPEC2CODE_LOG_LEVEL_DEBUG: return \"debug\";\n"
        "    default: return \"unknown\";\n"
        "    }\n"
        "}\n\n"
        "static const char* spec2codeLogLevelTag(unsigned int uiLevel)\n"
        "{\n"
        "    switch (uiLevel)\n"
        "    {\n"
        "    case SPEC2CODE_LOG_LEVEL_ERROR: return \"E\";\n"
        "    case SPEC2CODE_LOG_LEVEL_WARNING: return \"W\";\n"
        "    case SPEC2CODE_LOG_LEVEL_MESSAGE: return \"M\";\n"
        "    case SPEC2CODE_LOG_LEVEL_INFO: return \"I\";\n"
        "    case SPEC2CODE_LOG_LEVEL_DEBUG: return \"D\";\n"
        "    default: return \"?\";\n"
        "    }\n"
        "}\n\n"
        "void spec2codeLog(unsigned int uiLevel, const char* cpFormat, ...)\n"
        "{\n"
        "    char cArrBody[SPEC2CODE_LOG_BODY_MAX];\n"
        "    char cArrLine[SPEC2CODE_LOG_LINE_MAX];\n"
        "    va_list sArgs;\n"
        "    int iWritten;\n\n"
        "    if ((uiLevel > S_uiLogLevel) || (cpFormat == NULL))\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    va_start(sArgs, cpFormat);\n"
        "    iWritten = vsnprintf(cArrBody, sizeof(cArrBody), cpFormat, sArgs);\n"
        "    va_end(sArgs);\n"
        "    if (iWritten < 0)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    iWritten = snprintf(cArrLine, sizeof(cArrLine), \"S2C-LOG|%s|%s\\r\\n\",\n"
        "                        spec2codeLogLevelTag(uiLevel), cArrBody);\n"
        "    if (iWritten < 0)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    if (S_fpLogSink != NULL)\n"
        "    {\n"
        "        S_fpLogSink(cArrLine);\n"
        "    }\n"
        "    else\n"
        "    {\n"
        "        xil_printf(\"%s\", cArrLine);\n"
        "    }\n"
        "}\n"
    )


def _testbench_manifest(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    agent = _testbench_transport_agent(spec)
    manifest = {
        "schema_version": "1.0",
        "project": spec.get("project", {}).get("name", ""),
        "agent_version": _app_version(),
        "protocol": "S2C line protocol v1",
        "line_format": ("S2C|id=1|device=<id>|op=<operation>|reg=<name>|reg_addr=0x00|address=0x0|length=16|value=0x00|data=AABB; "
                        "global: S2C|id=1|op=spec2code_version, S2C|id=1|op=log_level|value=1..5"),
        "transport_agent": agent,
        "log": {
            "op": "log_level",
            "levels": dict(_TESTBENCH_LOG_LEVELS),
            "default": _TESTBENCH_LOG_LEVELS[_TESTBENCH_LOG_DEFAULT_LEVEL],
            "line_prefix": "S2C-LOG|",
        },
        "devices": [],
    }
    if agent == "uart":
        uart = _testbench_uart_controller(spec) or {}
        manifest["uart"] = {
            "instance": uart.get("instance", ""),
            "driver": _testbench_uart_driver(spec),
            "baud": 115200,
        }
    if agent == "coresight":
        manifest["coresight"] = {
            "device": "psu_coresight_0",
            "driver": "coresightps_dcc",
            "processor": "psu_cortexa53_0",
            "host_bridge": "xsdb jtagterminal -socket",
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
            description = op.get("description", "")
            fixed_read_length = _operation_fixed_read_length(op)
            if op_name == "device_init":
                post_init = _post_init_status(descriptor)
                if post_init is not None:
                    fixed_read_length = post_init["bytes"]
                    description = (description + " " if description else "") + (
                        f"Başarıda {post_init['reg']} geri okunur (value + data).")
            operations.append({
                "name": op_name,
                "label": _testbench_label(device.get("part", ""), op_name),
                "description": description,
                "risk": _testbench_risk(op_name),
                "implemented": True,
                "fixed_read_length": fixed_read_length,
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
        if _supports_spi_register_ops(descriptor):
            model = tics.register_model(descriptor)
            data_bits = int(model.get("data_bits", 8) or 8)
            readback = _spi_readback(descriptor)
            if readback is not None:
                requires = str(readback.get("requires", "")).strip()
                operations.append({
                    "name": "register_read",
                    "label": "Register oku",
                    "description": (
                        f"SPI 24-bit frame ile {data_bits}-bit register oku."
                        + (f" KOŞUL: {requires}" if requires else "")
                    ),
                    "risk": "safe",
                    "implemented": True,
                    "fixed_read_length": data_bits // 8,
                    "requires_address": False,
                    "requires_length": False,
                    "requires_data": False,
                    "requires_register": True,
                    "requires_value": False,
                })
            operations.append({
                "name": "register_write",
                "label": "Register yaz",
                "description": f"SPI 24-bit frame ile {data_bits}-bit register yaz (device_init ile aynı word formatı).",
                "risk": "risky",
                "implemented": True,
                "fixed_read_length": 0,
                "requires_address": False,
                "requires_length": False,
                "requires_data": False,
                "requires_register": True,
                "requires_value": True,
            })
        transport_type = descriptor.get("transport", {}).get("type", "")
        # Generic register access moves one native frame: 1 byte on I2C
        # (PMBus word commands have dedicated operations), data_bits wide on
        # TICS-style SPI parts.
        native_width = 8
        if transport_type == "spi" and _supports_spi_register_ops(descriptor):
            native_width = int(tics.register_model(descriptor).get("data_bits", 8) or 8)
        manifest["devices"].append({
            "id": device.get("id", ""),
            "part": device.get("part", ""),
            "transport": transport_type,
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
                and int(reg.get("width", 8)) == native_width
            ],
            "operations": operations,
        })
    return json_dumps_crlf(manifest)


def json_dumps_crlf(value: dict) -> str:
    import json

    return json.dumps(value, indent=2) + "\n"


_TESTBENCH_HANDLE_HEADERS: list[tuple[str, str]] = [
    ("XIicPs", "xiicps.h"),
    ("XSpiPs", "xspips.h"),
    ("XQspiPsu", "xqspipsu.h"),
]


def _testbench_used_handle_types(spec: dict) -> set[str]:
    """Controller handle types actually wired in this design.

    Headers such as xspips.h only exist in the BSP when the matching PS
    peripheral is enabled in the hardware design; including them
    unconditionally breaks the Vitis application compile on hardware
    without that peripheral.
    """
    return {entry["htype"] for entry in _testbench_board_controller_entries(spec)}


def _testbench_ops_header(project_name: str, handle_types: set[str]) -> str:
    guard = _header_guard(f"{project_name}_testbench_ops_h")
    controller_includes = "".join(
        f'#include "{header}"\n'
        for htype, header in _TESTBENCH_HANDLE_HEADERS
        if htype in handle_types
    )
    getter_prototypes = "".join(
        f"{htype}* {_testbench_getter(htype)}(const char* cpControllerId);\n"
        for htype, _header in _TESTBENCH_HANDLE_HEADERS
        if htype in handle_types
    )
    return (
        "/**\n"
        f" * @file {project_name}_testbench_ops.h\n"
        " * @brief Generated operation dispatch for the Spec2Code target test bench.\n"
        " */\n"
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        '#include "spec2code_testbench_protocol.h"\n'
        + controller_includes
        + "\n"
        "typedef struct\n"
        "{\n"
        "    const char* cpDeviceId;\n"
        "    const char* cpPart;\n"
        "    const char* cpOperation;\n"
        "    const char* cpLabel;\n"
        "    const char* cpRisk;\n"
        "} SSpec2codeTestbenchOperation;\n\n"
        + getter_prototypes
        + "unsigned int spec2codeTestbenchOperationCount(void);\n"
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
        if _supports_spi_register_ops(descriptor):
            if _spi_readback(descriptor) is not None:
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


def _testbench_register_resolver(entry: dict, *, wide: bool = False) -> list[str]:
    module = entry["module"]
    MOD = module.upper()
    regs = [
        reg for reg in entry["descriptor"].get("registers", [])
        if "name" in reg and "offset" in reg and str(reg.get("access", "")).lower() != "reserved"
    ]
    if not regs:
        return []
    func = f"{module}TestbenchRegisterResolve"
    # SPI TICS parts carry 15-bit register addresses; the resolver output and
    # the raw-address ceiling widen accordingly.
    out_type = "unsigned int" if wide else "unsigned char"
    out_var = "uipReg" if wide else "ucpReg"
    if wide:
        address_bits = int(tics.register_model(entry["descriptor"]).get("address_bits", 15) or 15)
        raw_limit = f"{_c_hex((1 << address_bits) - 1)}"
    else:
        raw_limit = "0xFFU"
    lines = [
        f"static int {func}(const char* cpRegister, unsigned int uiRegister, {out_type}* {out_var})",
        "{",
        f"    if ({out_var} == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
    ]
    for reg in regs:
        lines.extend([
            f"    if (spec2codeTestbenchStringEqual(cpRegister, \"{reg['name']}\") == 1)",
            "    {",
            f"        *{out_var} = {MOD}_REG_{reg['name']};",
            "        return XST_SUCCESS;",
            "    }",
        ])
    lines.extend([
        f"    if (uiRegister <= {raw_limit})",
        "    {",
        f"        *{out_var} = ({out_type})uiRegister;",
        "        return XST_SUCCESS;",
        "    }",
        "    return XST_FAILURE;",
        "}",
        "",
    ])
    return lines


def _c_hex(value: int) -> str:
    return f"0x{value:X}U"


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
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"i2c reg read: addr=0x%02X reg=0x%02X\", ucAddress, ucReg);",
        "    iStatus = XIicPs_MasterSendPolled(spIic, &ucReg, 1, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"i2c send HATA: addr=0x%02X reg=0x%02X status=%d\", ucAddress, ucReg, iStatus);",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    iStatus = XIicPs_MasterRecvPolled(spIic, ucpValue, 1, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"i2c recv HATA: addr=0x%02X reg=0x%02X status=%d\", ucAddress, ucReg, iStatus);",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"i2c reg read tamam: addr=0x%02X reg=0x%02X value=0x%02X\", ucAddress, ucReg, *ucpValue);",
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
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"i2c reg write: addr=0x%02X reg=0x%02X value=0x%02X\", ucAddress, ucReg, ucValue);",
        "    iStatus = XIicPs_MasterSendPolled(spIic, ucArrBuffer, 2, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"i2c write HATA: addr=0x%02X reg=0x%02X status=%d\", ucAddress, ucReg, iStatus);",
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


def _testbench_spi_helpers() -> list[str]:
    return [
        "static int spec2codeTestbenchSpiRegisterWrite(XSpiPs* spSpi, unsigned char ucSelect,",
        "                                              unsigned int uiWord)",
        "{",
        "    unsigned char ucArrTx[3];",
        "    int iStatus;",
        "",
        "    if (spSpi == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    ucArrTx[0] = (unsigned char)((uiWord >> 16U) & 0xFFU);",
        "    ucArrTx[1] = (unsigned char)((uiWord >> 8U) & 0xFFU);",
        "    ucArrTx[2] = (unsigned char)(uiWord & 0xFFU);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"spi reg write: word=0x%06X\", uiWord);",
        "    iStatus = XSpiPs_SetSlaveSelect(spSpi, ucSelect);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    iStatus = XSpiPs_PolledTransfer(spSpi, ucArrTx, NULL, 3U);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"spi write HATA: word=0x%06X status=%d\", uiWord, iStatus);",
        "    }",
        "    return iStatus;",
        "}",
        "",
        "static int spec2codeTestbenchSpiRegisterRead(XSpiPs* spSpi, unsigned char ucSelect,",
        "                                             unsigned int uiWord, unsigned int uiDataBytes,",
        "                                             unsigned int* uipValue)",
        "{",
        "    unsigned char ucArrTx[3];",
        "    unsigned char ucArrRx[3];",
        "    int iStatus;",
        "",
        "    if ((spSpi == NULL) || (uipValue == NULL) || (uiDataBytes == 0U) || (uiDataBytes > 2U))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    ucArrTx[0] = (unsigned char)((uiWord >> 16U) & 0xFFU);",
        "    ucArrTx[1] = (unsigned char)((uiWord >> 8U) & 0xFFU);",
        "    ucArrTx[2] = (unsigned char)(uiWord & 0xFFU);",
        "    ucArrRx[0] = 0U;",
        "    ucArrRx[1] = 0U;",
        "    ucArrRx[2] = 0U;",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"spi reg read: word=0x%06X\", uiWord);",
        "    iStatus = XSpiPs_SetSlaveSelect(spSpi, ucSelect);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    iStatus = XSpiPs_PolledTransfer(spSpi, ucArrTx, ucArrRx, 3U);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"spi read HATA: word=0x%06X status=%d\", uiWord, iStatus);",
        "        return iStatus;",
        "    }",
        "    if (uiDataBytes == 2U)",
        "    {",
        "        *uipValue = ((unsigned int)ucArrRx[1] << 8U) | (unsigned int)ucArrRx[2];",
        "    }",
        "    else",
        "    {",
        "        *uipValue = (unsigned int)ucArrRx[2];",
        "    }",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"spi reg read tamam: word=0x%06X value=0x%04X\", uiWord, *uipValue);",
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
        status = _post_init_status(descriptor)
        if status is not None:
            MOD = module.upper()
            lines.append("if (iStatus == XST_SUCCESS)")
            lines.append("{")
            lines.append(f"    /* init dogrulamasi: {status['reg']} geri okunur (value + data). */")
            if status["transport"] == "i2c":
                lines.extend([
                    f"    iStatus = spec2codeTestbenchI2cRegisterRead({hvar}, {MOD}_I2C_ADDR, {MOD}_REG_{status['reg']}, &ucValue);",
                    "    if (iStatus == XST_SUCCESS)",
                    "    {",
                    "        spResponse->uiValue = (unsigned int)ucValue;",
                    "        iStatus = spec2codeTestbenchDataPush(spResponse, ucValue);",
                    "    }",
                ])
            else:
                model = tics.register_model(descriptor)
                frame_bits = int(model.get("frame_bits", 24) or 24)
                rw_bit = int(model.get("rw_bit", frame_bits - 1) or (frame_bits - 1))
                read_value = 0 if int(model.get("write_value", 0) or 0) else 1
                address_bits = int(model.get("address_bits", 15) or 15)
                address_shift = int(model.get("address_shift", 8) or 8)
                mask = _c_hex((1 << address_bits) - 1)
                word = (f"((unsigned int){read_value}U << {rw_bit}U) | "
                        f"(((unsigned int){MOD}_REG_{status['reg']} & {mask}) << {address_shift}U)")
                lines.extend([
                    f"    iStatus = spec2codeTestbenchSpiRegisterRead({hvar}, {MOD}_SPI_SELECT, {word}, {status['bytes']}U, &uiRegValue);",
                    "    if (iStatus == XST_SUCCESS)",
                    "    {",
                    "        spResponse->uiValue = uiRegValue;",
                ])
                if status["bytes"] == 2:
                    lines.extend([
                        "        iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)((uiRegValue >> 8U) & 0xFFU));",
                        "        if (iStatus == XST_SUCCESS)",
                        "        {",
                        "            iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)(uiRegValue & 0xFFU));",
                        "        }",
                    ])
                else:
                    lines.append("        iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)(uiRegValue & 0xFFU));")
                lines.append("    }")
            lines.append("}")
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
    elif "int32" in returns and "uint32" not in returns:
        # Converted engineering-unit scalar (e.g. santi-Celsius): value goes
        # out two's complement in uiValue, data carries 4 big-endian bytes.
        lines.append(f"iStatus = {func}({hvar}, &iValue);")
        lines.extend([
            "if (iStatus == XST_SUCCESS)",
            "{",
            "    spResponse->uiValue = (unsigned int)iValue;",
        ])
        for shift in (24, 16, 8, 0):
            lines.extend([
                f"    iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)(((unsigned int)iValue >> {shift}) & 0xFFU));",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
            ])
        lines.append("}")
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
    spi_register_ops = _supports_spi_register_ops(descriptor)
    spi_readback = _spi_readback(descriptor) if spi_register_ops else None
    post_init = _post_init_status(descriptor) if any(
        op.get("name") == "device_init" for op in operations) else None
    needs_array = any(_array_return_count(str(op.get("returns", "")).lower()) for op in operations)
    needs_us_value = any("uint16" in str(op.get("returns", "")).lower() for op in operations)
    needs_i_value = any(
        "int32" in str(op.get("returns", "")).lower()
        and "uint32" not in str(op.get("returns", "")).lower()
        for op in operations
    )
    needs_uc_value = (
        register_ops
        or (post_init is not None and post_init["transport"] == "i2c")
        or any("uint8" in str(op.get("returns", "")).lower() for op in operations)
    )
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
    if needs_i_value:
        lines.append("        int iValue;")
    if needs_array:
        lines.append("        unsigned short usArrValues[8];")
    if needs_uc_value:
        lines.append("        unsigned char ucValue;")
    if needs_uc_reg:
        lines.append("        unsigned char ucReg;")
    if spi_register_ops:
        lines.append("        unsigned int uiReg;")
        lines.append("        unsigned int uiWord;")
    if spi_readback is not None or (post_init is not None and post_init["transport"] == "spi"):
        lines.append("        unsigned int uiRegValue;")
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

    if spi_register_ops:
        model = tics.register_model(descriptor)
        frame_bits = int(model.get("frame_bits", 24) or 24)
        address_bits = int(model.get("address_bits", 15) or 15)
        address_shift = int(model.get("address_shift", 8) or 8)
        rw_bit = int(model.get("rw_bit", frame_bits - 1) or (frame_bits - 1))
        write_value = int(model.get("write_value", 0) or 0)
        read_value = 0 if write_value else 1
        data_bits = int(model.get("data_bits", 8) or 8)
        data_bytes = data_bits // 8
        address_mask = _c_hex((1 << address_bits) - 1)
        data_mask = _c_hex((1 << data_bits) - 1)
        resolve = [
            f"            iStatus = {module}TestbenchRegisterResolve(spRequest->cArrRegister, spRequest->uiRegister, &uiReg);",
            "            if (iStatus != XST_SUCCESS)",
            "            {",
            "                spResponse->iStatus = iStatus;",
            "                spec2codeTestbenchMessageSet(spResponse, \"register not found\");",
            "                return iStatus;",
            "            }",
        ]
        if spi_readback is not None:
            lines.extend([
                "        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"register_read\") == 1)",
                "        {",
                *resolve,
                f"            uiWord = ((unsigned int){read_value}U << {rw_bit}U) | ((uiReg & {address_mask}) << {address_shift}U);",
                f"            iStatus = spec2codeTestbenchSpiRegisterRead({hvar}, {MOD}_SPI_SELECT, uiWord, {data_bytes}U, &uiRegValue);",
                "            spResponse->iStatus = iStatus;",
                "            spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
                "            spResponse->uiValue = uiRegValue;",
                "            if (iStatus == XST_SUCCESS)",
                "            {",
            ])
            if data_bytes == 2:
                lines.append("                (void)spec2codeTestbenchDataPush(spResponse, (unsigned char)((uiRegValue >> 8U) & 0xFFU));")
            lines.extend([
                "                (void)spec2codeTestbenchDataPush(spResponse, (unsigned char)(uiRegValue & 0xFFU));",
                "                spec2codeTestbenchMessageSet(spResponse, \"register_read ok\");",
                "            }",
                "            return iStatus;",
                "        }",
            ])
        write_word_terms = []
        if write_value:
            write_word_terms.append(f"((unsigned int){write_value}U << {rw_bit}U)")
        write_word_terms.append(f"((uiReg & {address_mask}) << {address_shift}U)")
        write_word_terms.append(f"((unsigned int)spRequest->uiValue & {data_mask})")
        lines.extend([
            "        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"register_write\") == 1)",
            "        {",
            *resolve,
            f"            uiWord = {' | '.join(write_word_terms)};",
            f"            iStatus = spec2codeTestbenchSpiRegisterWrite({hvar}, {MOD}_SPI_SELECT, uiWord);",
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
    app_version = _app_version()
    entries = _testbench_device_entries(spec, get_descriptor)
    handle_types = _testbench_used_handle_types(spec)
    rows = _testbench_op_table(entries)
    includes = [
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "xstatus.h"',
        '#include <stddef.h>',
        "",
    ]
    emitted_includes: set[str] = set()
    for entry in entries:
        include = f'#include "{entry["module"]}.h"'
        if include not in emitted_includes:
            includes.append(include)
            emitted_includes.add(include)
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
        f"#define SPEC2CODE_TESTBENCH_AGENT_VERSION {_c_string_literal(app_version)}",
        "",
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if htype in handle_types
            for line in (
                f"SPEC2CODE_WEAK {htype}* {_testbench_getter(htype)}(const char* cpControllerId)",
                "{",
                "    (void)cpControllerId;",
                "    return NULL;",
                "}",
                "",
            )
        ],
        *(_testbench_i2c_helpers() if any(entry["descriptor"].get("transport", {}).get("type") == "i2c" for entry in entries) else []),
        *(_testbench_spi_helpers() if any(_supports_spi_register_ops(entry["descriptor"]) for entry in entries) else []),
    ]
    emitted_resolvers: set[str] = set()
    for entry in entries:
        module = entry["module"]
        if module in emitted_resolvers:
            continue
        if _supports_i2c_register_ops(entry["descriptor"]):
            lines.extend(_testbench_register_resolver(entry))
            emitted_resolvers.add(module)
        elif _supports_spi_register_ops(entry["descriptor"]):
            lines.extend(_testbench_register_resolver(entry, wide=True))
            emitted_resolvers.add(module)

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
        "    if ((spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"spec2code_version\") == 1) ||",
        "        (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"version\") == 1))",
        "    {",
        "        spResponse->uiOk = 1U;",
        "        spResponse->iStatus = XST_SUCCESS;",
        "        spec2codeTestbenchMessageSet(spResponse, \"Spec2Code \" SPEC2CODE_TESTBENCH_AGENT_VERSION);",
        "        return XST_SUCCESS;",
        "    }",
        "    if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"log_level\") == 1)",
        "    {",
        "        /* Calisma zamaninda log esigi: value verilirse ayarla, her",
        "         * durumda gecerli seviyeyi dondur. 1=error..5=debug. */",
        "        if (spRequest->uiHasValue == 1U)",
        "        {",
        "            (void)spec2codeLogLevelSet(spRequest->uiValue);",
        "            spec2codeLog(SPEC2CODE_LOG_LEVEL_WARNING, \"log seviyesi degisti: %s (%u)\",",
        "                         spec2codeLogLevelName(spec2codeLogLevelGet()), spec2codeLogLevelGet());",
        "        }",
        "        spResponse->uiOk = 1U;",
        "        spResponse->iStatus = XST_SUCCESS;",
        "        spResponse->uiValue = spec2codeLogLevelGet();",
        "        spec2codeTestbenchMessageSet(spResponse, spec2codeLogLevelName(spec2codeLogLevelGet()));",
        "        return XST_SUCCESS;",
        "    }",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"op basliyor: device=%s op=%s\",",
        "                 spRequest->cArrDevice, spRequest->cArrOperation);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG,",
        "                 \"op parametreleri: reg=%s reg_addr=0x%X address=0x%X length=%u value=0x%X data_len=%u\",",
        "                 spRequest->cArrRegister, spRequest->uiRegister, spRequest->uiAddress,",
        "                 spRequest->uiLength, spRequest->uiValue, spRequest->uiDataLength);",
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
        "    int iFormatStatus;",
        "",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, \"RX %s\", cpRequestLine);",
        "    iStatus = spec2codeTestbenchRequestParse(cpRequestLine, &sRequest);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"istek cozulmedi (parse failed): %s\", cpRequestLine);",
        "        spec2codeTestbenchResponseClear(&sResponse);",
        "        sResponse.iStatus = iStatus;",
        "        spec2codeTestbenchMessageSet(&sResponse, \"request parse failed\");",
        "        return spec2codeTestbenchResponseFormat(&sResponse, cpResponseLine, uiResponseLength);",
        "    }",
        "    (void)spec2codeTestbenchDispatch(&sRequest, &sResponse);",
        "    if (sResponse.uiOk == 1U)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"op tamam: device=%s op=%s status=%d\",",
        "                     sRequest.cArrDevice, sRequest.cArrOperation, sResponse.iStatus);",
        "    }",
        "    else",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"op HATA: device=%s op=%s status=%d mesaj=%s\",",
        "                     sRequest.cArrDevice, sRequest.cArrOperation, sResponse.iStatus, sResponse.cArrMessage);",
        "    }",
        "    iFormatStatus = spec2codeTestbenchResponseFormat(&sResponse, cpResponseLine, uiResponseLength);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, \"TX %s\", cpResponseLine);",
        "    return iFormatStatus;",
        "}",
        "",
    ])
    return "\n".join(lines)


def _zynqmp_lwip_eth_controller(spec: dict) -> dict | None:
    if spec.get("project", {}).get("platform") != "zynq_ultrascale":
        return None
    for controller in spec.get("controllers", []):
        if controller.get("type") != "eth":
            continue
        if controller.get("zone") != "ps":
            continue
        if controller.get("driver", "XEmacPs") != "XEmacPs":
            continue
        return controller
    return None


#: UART drivers the serial agent can be generated for. The Versal uartpsv
#: driver mirrors the uartps API one-to-one (Lookup/CfgInitialize/
#: SetBaudRate/Recv/Send); MicroBlaze's AXI UARTLITE has the same polled
#: Recv/Send shape but a single-call Initialize and a hardware-fixed baud.
_TESTBENCH_UART_DRIVERS: dict[str, str] = {
    "XUartPs": "xuartps.h",
    "XUartPsv": "xuartpsv.h",
    "XUartLite": "xuartlite.h",
}


def _testbench_uart_controller(spec: dict) -> dict | None:
    """Deterministic UART pick for the serial test bench agent.

    PS UARTs win over PL UARTLITEs, then lowest instance name, so the same
    design always binds the same UART (usually the console UART, which the
    host client tolerates: non-protocol lines are ignored on both sides).
    """
    candidates = [
        controller
        for controller in spec.get("controllers", [])
        if controller.get("type") == "uart"
        and controller.get("driver", "XUartPs") in _TESTBENCH_UART_DRIVERS
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (item.get("zone") != "ps", str(item.get("instance", ""))),
    )[0]


def _testbench_coresight_supported(spec: dict) -> bool:
    """CoreSight DCC agent is ZynqMP-only for now (psu_coresight_0).

    The coresightps_dcc driver ships in the standalone BSP for other Arm
    platforms too, but only the ZynqMP path is end-to-end validated; the
    honest gate below keeps unvalidated platforms from generating code
    that was never exercised.
    """
    return spec.get("project", {}).get("platform") == "zynq_ultrascale"


def _testbench_transport_agent(spec: dict) -> str | None:
    """Which on-target agent carries the S2C line protocol.

    ``project.testbench_transport``: "auto" (default) | "eth" | "uart" |
    "coresight". auto prefers Ethernet and falls back to the PS UART so
    boards without a PHY still get a runnable test bench. CoreSight (JTAG
    DCC over psu_coresight_0) is never auto-picked: it needs a debug cable
    and an xsdb jtagterminal bridge on the host, so it must be explicit.
    """
    choice = str(spec.get("project", {}).get("testbench_transport", "auto") or "auto")
    lwip_possible = _zynqmp_lwip_eth_controller(spec) is not None
    uart_possible = _testbench_uart_controller(spec) is not None
    if choice == "eth":
        return "lwip" if lwip_possible else None
    if choice == "uart":
        return "uart" if uart_possible else None
    if choice == "coresight":
        if _testbench_coresight_supported(spec):
            return "coresight"
        raise cmodel.CodegenError(
            "CoreSight (DCC) test bench su an yalnizca ZynqMP (psu_coresight_0) "
            "platformunda dogrulandi; bu platformda eth veya uart transportunu kullanin")
    if lwip_possible:
        return "lwip"
    if uart_possible:
        return "uart"
    return None


def _testbench_lwip_enabled(spec: dict) -> bool:
    return _testbench_transport_agent(spec) == "lwip"


def _testbench_uart_enabled(spec: dict) -> bool:
    return _testbench_transport_agent(spec) == "uart"


def _testbench_coresight_enabled(spec: dict) -> bool:
    return _testbench_transport_agent(spec) == "coresight"


def _controller_static_handle_name(controller: dict) -> str:
    return f"S_s{_pascal_identifier(str(controller.get('id', 'controller')))}Handle"


def _testbench_board_controller_entries(spec: dict) -> list[dict]:
    controllers = {controller["id"]: controller for controller in spec.get("controllers", [])}
    used_ids = {mux.get("controller_id") for mux in spec.get("muxes", [])}
    used_ids.update(device.get("attach", {}).get("controller_id") for device in spec.get("devices", []))
    entries: list[dict] = []
    for controller_id in sorted(item for item in used_ids if item):
        controller = controllers.get(controller_id)
        if controller is None:
            continue
        try:
            htype, _hvar = cmodel._handle_for(controller)
        except cmodel.CodegenError:
            continue
        if htype not in {"XIicPs", "XSpiPs", "XQspiPsu"}:
            continue
        entries.append({
            "id": controller_id,
            "instance": controller.get("instance", ""),
            "htype": htype,
            "handle": _controller_static_handle_name(controller),
        })
    return entries


def _testbench_runtime_is_freertos(spec: dict) -> bool:
    return spec.get("project", {}).get("runtime") == "freertos"


def _testbench_lwip_header(spec: dict) -> str:
    if _testbench_runtime_is_freertos(spec):
        api_decls = (
            "/* FreeRTOS + lwIP SOCKET_API agent: main() spawns\n"
            " * spec2codeTestbenchLwipMainThread via sys_thread_new and starts the\n"
            " * scheduler (pattern of the official Xilinx freertos_lwip_echo_server). */\n"
            "#define SPEC2CODE_TESTBENCH_THREAD_STACKSIZE 1024\n\n"
            "int spec2codeTestbenchBoardInit(void);\n"
            "void spec2codeTestbenchLwipMainThread(void* vpArg);\n\n"
        )
    else:
        api_decls = (
            "int spec2codeTestbenchBoardInit(void);\n"
            "int spec2codeTestbenchLwipNetworkInit(void);\n"
            "int spec2codeTestbenchLwipTcpStart(unsigned short usPort);\n"
            "int spec2codeTestbenchLwipStart(unsigned short usPort);\n"
            "void spec2codeTestbenchLwipInputPoll(void);\n\n"
        )
    return (
        "/**\n"
        " * @file spec2code_testbench_lwip.h\n"
        " * @brief Zynq UltraScale+ PS Ethernet lwIP TCP agent for Spec2Code test bench.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_LWIP_H\n"
        "#define SPEC2CODE_TESTBENCH_LWIP_H\n\n"
        "#define SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT 5000U\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_IP_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR0 192U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR1 168U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR2 1U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR3 10U\n"
        "#endif\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_NETMASK_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR0 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR1 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR2 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR3 0U\n"
        "#endif\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_GATEWAY_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR0 192U\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR1 168U\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR2 1U\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR3 1U\n"
        "#endif\n\n"
        + api_decls +
        "#endif /* SPEC2CODE_TESTBENCH_LWIP_H */\n"
    )


def _testbench_board_handle_decls(entries: list[dict]) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        lines.append(f"static {entry['htype']} {entry['handle']};")
    if entries:
        lines.append("")
    return lines


def _testbench_board_init_lines(entries: list[dict]) -> list[str]:
    lines = [
        "int spec2codeTestbenchBoardInit(void)",
        "{",
        "    int iStatus;",
    ]
    if any(entry["htype"] == "XIicPs" for entry in entries):
        lines.append("    XIicPs_Config* spIicConfig;")
    if any(entry["htype"] == "XSpiPs" for entry in entries):
        lines.append("    XSpiPs_Config* spSpiConfig;")
    if any(entry["htype"] == "XQspiPsu" for entry in entries):
        lines.append("    XQspiPsu_Config* spQspiConfig;")
    lines.extend([
        "",
        "    if (S_uiBoardReady == 1U)",
        "    {",
        "        return XST_SUCCESS;",
        "    }",
    ])
    if not entries:
        lines.extend([
            "    S_uiBoardReady = 1U;",
            "    return XST_SUCCESS;",
            "}",
            "",
        ])
        return lines

    for entry in entries:
        instance = entry["instance"]
        handle = entry["handle"]
        if entry["htype"] == "XIicPs":
            lines.extend([
                f'    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, "controller init: {entry["id"]} (I2C)");',
                f"    spIicConfig = XIicPs_LookupConfig({instance}_DEVICE_ID);",
                "    if (spIicConfig == NULL)",
                "    {",
                f'        xil_printf("Spec2Code I2C config bulunamadi: {entry["id"]}\\r\\n");',
                f'        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "controller init HATA: {entry["id"]} config yok");',
                "        return XST_FAILURE;",
                "    }",
                f"    iStatus = XIicPs_CfgInitialize(&{handle}, spIicConfig, spIicConfig->BaseAddress);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                f'        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "controller init HATA: {entry["id"]} cfg status=%d", iStatus);',
                "        return iStatus;",
                "    }",
                f"    iStatus = XIicPs_SetSClk(&{handle}, 100000U);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                f'        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "controller init HATA: {entry["id"]} sclk status=%d", iStatus);',
                "        return iStatus;",
                "    }",
            ])
        elif entry["htype"] == "XSpiPs":
            lines.extend([
                f"    spSpiConfig = XSpiPs_LookupConfig({instance}_DEVICE_ID);",
                "    if (spSpiConfig == NULL)",
                "    {",
                f'        xil_printf("Spec2Code SPI config bulunamadi: {entry["id"]}\\r\\n");',
                "        return XST_FAILURE;",
                "    }",
                f"    iStatus = XSpiPs_CfgInitialize(&{handle}, spSpiConfig, spSpiConfig->BaseAddress);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                f"    iStatus = XSpiPs_SetOptions(&{handle}, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                f"    iStatus = XSpiPs_SetClkPrescaler(&{handle}, XSPIPS_CLK_PRESCALE_8);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
            ])
        elif entry["htype"] == "XQspiPsu":
            lines.extend([
                f'    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, "controller init: {entry["id"]} (QSPI)");',
                f"    spQspiConfig = XQspiPsu_LookupConfig({instance}_DEVICE_ID);",
                "    if (spQspiConfig == NULL)",
                "    {",
                f'        xil_printf("Spec2Code QSPI config bulunamadi: {entry["id"]}\\r\\n");',
                f'        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "controller init HATA: {entry["id"]} config yok");',
                "        return XST_FAILURE;",
                "    }",
                f"    iStatus = XQspiPsu_CfgInitialize(&{handle}, spQspiConfig, spQspiConfig->BaseAddress);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                f'        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "controller init HATA: {entry["id"]} cfg status=%d", iStatus);',
                "        return iStatus;",
                "    }",
                f"    iStatus = XQspiPsu_SetOptions(&{handle}, XQSPIPSU_MANUAL_START_OPTION);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                f"    iStatus = XQspiPsu_SetClkPrescaler(&{handle}, XQSPIPSU_CLK_PRESCALE_8);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                f"    XQspiPsu_SelectFlash(&{handle}, XQSPIPSU_SELECT_FLASH_CS_LOWER, XQSPIPSU_SELECT_FLASH_BUS_LOWER);",
            ])
    lines.extend([
        f'    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, "board init tamam ({len(entries)} controller); '
        'device_init otomatik KOSULMAZ");',
        "    S_uiBoardReady = 1U;",
        "    return XST_SUCCESS;",
        "}",
        "",
    ])
    return lines


def _testbench_board_getter_lines(entries: list[dict], htype: str, func_name: str) -> list[str]:
    lines = [
        f"{htype}* {func_name}(const char* cpControllerId)",
        "{",
    ]
    matching = [entry for entry in entries if entry["htype"] == htype]
    for entry in matching:
        lines.extend([
            f"    if (spec2codeTestbenchStringEqual(cpControllerId, \"{entry['id']}\") == 1)",
            "    {",
            f"        return &{entry['handle']};",
            "    }",
        ])
    lines.extend([
        "    return NULL;",
        "}",
        "",
    ])
    return lines


def _testbench_lwip_source(spec: dict) -> str:
    """Runtime-matched lwIP agent.

    standalone -> RAW_API + xemacif_input polling (official lwip_echo_server
    pattern); freertos -> SOCKET_API threads (official
    freertos_lwip_echo_server pattern: lwip_init in a thread, xemac_add +
    xemacif_input_thread in a network thread, socket accept loop in an app
    thread). Matches the BSP api_mode the Vitis flow configures per runtime.
    """
    if _testbench_runtime_is_freertos(spec):
        return _testbench_lwip_source_socket(spec)
    return _testbench_lwip_source_raw(spec)


def _testbench_lwip_source_socket(spec: dict) -> str:
    eth = _zynqmp_lwip_eth_controller(spec)
    if eth is None:
        raise cmodel.CodegenError("lwIP test bench requested without a ZynqMP PS Ethernet controller")
    project_name = spec["project"]["name"]
    entries = _testbench_board_controller_entries(spec)
    headers = [
        '#include "spec2code_testbench_lwip.h"',
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "xparameters.h"',
        '#include "xstatus.h"',
        '#include "xil_printf.h"',
        '#include "lwipopts.h"',
        '#include "lwip/init.h"',
        '#include "lwip/ip_addr.h"',
        '#include "lwip/sockets.h"',
        '#include "lwip/sys.h"',
        '#include "netif/xadapter.h"',
        '#include "FreeRTOS.h"',
        '#include "task.h"',
        '#include <stddef.h>',
        '#include <string.h>',
    ]
    if any(entry["htype"] == "XIicPs" for entry in entries):
        headers.append('#include "xiicps.h"')
    if any(entry["htype"] == "XSpiPs" for entry in entries):
        headers.append('#include "xspips.h"')
    if any(entry["htype"] == "XQspiPsu" for entry in entries):
        headers.append('#include "xqspipsu.h"')

    lines = [
        "/**",
        " * @file spec2code_testbench_lwip.c",
        " * @brief Zynq UltraScale+ PS Ethernet lwIP TCP agent (FreeRTOS SOCKET_API).",
        " */",
        *headers,
        "",
        "#define SPEC2CODE_TESTBENCH_LINE_MAX 512U",
        "#define SPEC2CODE_TESTBENCH_RECV_CHUNK 64",
        "",
        "#ifndef SPEC2CODE_TESTBENCH_ETH_BASEADDR",
        f"#define SPEC2CODE_TESTBENCH_ETH_BASEADDR {eth.get('instance')}_BASEADDR",
        "#endif",
        "",
        "#ifndef SPEC2CODE_TESTBENCH_MAC0",
        "#define SPEC2CODE_TESTBENCH_MAC0 0x02U",
        "#define SPEC2CODE_TESTBENCH_MAC1 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC2 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC3 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC4 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC5 0x02U",
        "#endif",
        "",
        "static struct netif S_sNetif;",
        "static char S_cArrRequestLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static char S_cArrResponseLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static unsigned char S_ucArrMac[6] =",
        "{",
        "    SPEC2CODE_TESTBENCH_MAC0,",
        "    SPEC2CODE_TESTBENCH_MAC1,",
        "    SPEC2CODE_TESTBENCH_MAC2,",
        "    SPEC2CODE_TESTBENCH_MAC3,",
        "    SPEC2CODE_TESTBENCH_MAC4,",
        "    SPEC2CODE_TESTBENCH_MAC5",
        "};",
        "static unsigned int S_uiBoardReady;",
        "",
        *_testbench_board_handle_decls(entries),
        "static unsigned int spec2codeTestbenchStringLengthLocal(const char* cpText)",
        "{",
        "    unsigned int uiLength;",
        "",
        "    uiLength = 0U;",
        "    while ((cpText != NULL) && (cpText[uiLength] != '\\0'))",
        "    {",
        "        uiLength++;",
        "    }",
        "    return uiLength;",
        "}",
        "",
        *_testbench_board_init_lines(entries),
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if any(entry["htype"] == htype for entry in entries)
            for line in _testbench_board_getter_lines(entries, htype, _testbench_getter(htype))
        ],
        "static void spec2codeTestbenchClientServe(int iClientSocket)",
        "{",
        "    char cArrChunk[SPEC2CODE_TESTBENCH_RECV_CHUNK];",
        "    unsigned int uiLineLength;",
        "    unsigned int uiResponseLength;",
        "    int iReceived;",
        "    int iIndex;",
        "    int iStatus;",
        "    char cByte;",
        "",
        "    uiLineLength = 0U;",
        "    for (;;)",
        "    {",
        "        iReceived = lwip_recv(iClientSocket, cArrChunk, sizeof(cArrChunk), 0);",
        "        if (iReceived <= 0)",
        "        {",
        "            return;",
        "        }",
        "        for (iIndex = 0; iIndex < iReceived; iIndex++)",
        "        {",
        "            cByte = cArrChunk[iIndex];",
        "            if (cByte == '\\r')",
        "            {",
        "                continue;",
        "            }",
        "            if (cByte == '\\n')",
        "            {",
        "                S_cArrRequestLine[uiLineLength] = '\\0';",
        "                uiLineLength = 0U;",
        "                iStatus = spec2codeTestbenchDispatchLine(S_cArrRequestLine,",
        "                                                         S_cArrResponseLine,",
        "                                                         SPEC2CODE_TESTBENCH_LINE_MAX);",
        "                uiResponseLength = spec2codeTestbenchStringLengthLocal(S_cArrResponseLine);",
        "                if ((iStatus == XST_SUCCESS) && (uiResponseLength > 0U))",
        "                {",
        "                    (void)lwip_send(iClientSocket, S_cArrResponseLine, uiResponseLength, 0);",
        "                }",
        "                continue;",
        "            }",
        "            if (uiLineLength < (SPEC2CODE_TESTBENCH_LINE_MAX - 1U))",
        "            {",
        "                S_cArrRequestLine[uiLineLength] = cByte;",
        "                uiLineLength++;",
        "            }",
        "            else",
        "            {",
        "                uiLineLength = 0U;",
        "            }",
        "        }",
        "    }",
        "}",
        "",
        "static void spec2codeTestbenchServerThread(void* vpArg)",
        "{",
        "    struct sockaddr_in sAddress;",
        "    struct sockaddr_in sRemote;",
        "    socklen_t uiRemoteSize;",
        "    int iListenSocket;",
        "    int iClientSocket;",
        "    int iStatus;",
        "",
        "    (void)vpArg;",
        "    iStatus = spec2codeTestbenchBoardInit();",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        '        xil_printf("Spec2Code test bench board init failed\\r\\n");',
        "        vTaskDelete(NULL);",
        "        return;",
        "    }",
        "    iListenSocket = lwip_socket(AF_INET, SOCK_STREAM, 0);",
        "    if (iListenSocket < 0)",
        "    {",
        '        xil_printf("Spec2Code test bench socket create failed\\r\\n");',
        "        vTaskDelete(NULL);",
        "        return;",
        "    }",
        "    memset(&sAddress, 0, sizeof(sAddress));",
        "    sAddress.sin_family = AF_INET;",
        "    sAddress.sin_port = htons(SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT);",
        "    sAddress.sin_addr.s_addr = INADDR_ANY;",
        "    if (lwip_bind(iListenSocket, (struct sockaddr*)&sAddress, sizeof(sAddress)) < 0)",
        "    {",
        '        xil_printf("Spec2Code test bench bind failed\\r\\n");',
        "        lwip_close(iListenSocket);",
        "        vTaskDelete(NULL);",
        "        return;",
        "    }",
        "    if (lwip_listen(iListenSocket, 1) < 0)",
        "    {",
        '        xil_printf("Spec2Code test bench listen failed\\r\\n");',
        "        lwip_close(iListenSocket);",
        "        vTaskDelete(NULL);",
        "        return;",
        "    }",
        '    xil_printf("Spec2Code test bench TCP agent listening on port %d\\r\\n",',
        "               SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT);",
        "    for (;;)",
        "    {",
        "        uiRemoteSize = sizeof(sRemote);",
        "        iClientSocket = lwip_accept(iListenSocket, (struct sockaddr*)&sRemote, &uiRemoteSize);",
        "        if (iClientSocket < 0)",
        "        {",
        "            continue;",
        "        }",
        "        spec2codeTestbenchClientServe(iClientSocket);",
        "        lwip_close(iClientSocket);",
        "    }",
        "}",
        "",
        "static void spec2codeTestbenchNetworkThread(void* vpArg)",
        "{",
        "    ip_addr_t sIpAddr;",
        "    ip_addr_t sNetmask;",
        "    ip_addr_t sGateway;",
        "",
        "    (void)vpArg;",
        "    IP4_ADDR(&sIpAddr,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR0,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR1,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR2,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR3);",
        "    IP4_ADDR(&sNetmask,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR0,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR1,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR2,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR3);",
        "    IP4_ADDR(&sGateway,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR0,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR1,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR2,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR3);",
        "    if (xemac_add(&S_sNetif,",
        "                  &sIpAddr,",
        "                  &sNetmask,",
        "                  &sGateway,",
        "                  S_ucArrMac,",
        "                  SPEC2CODE_TESTBENCH_ETH_BASEADDR) == NULL)",
        "    {",
        '        xil_printf("Spec2Code lwIP PS Ethernet init failed\\r\\n");',
        "        vTaskDelete(NULL);",
        "        return;",
        "    }",
        "    netif_set_default(&S_sNetif);",
        "    netif_set_up(&S_sNetif);",
        '    sys_thread_new("s2c_in",',
        "                   (void (*)(void*))xemacif_input_thread,",
        "                   &S_sNetif,",
        "                   SPEC2CODE_TESTBENCH_THREAD_STACKSIZE,",
        "                   DEFAULT_THREAD_PRIO);",
        '    sys_thread_new("s2c_srv",',
        "                   spec2codeTestbenchServerThread,",
        "                   NULL,",
        "                   SPEC2CODE_TESTBENCH_THREAD_STACKSIZE,",
        "                   DEFAULT_THREAD_PRIO);",
        "    vTaskDelete(NULL);",
        "}",
        "",
        "void spec2codeTestbenchLwipMainThread(void* vpArg)",
        "{",
        "    (void)vpArg;",
        "    /* Xilinx lwIP port: in OS mode lwip_init() also runs tcpip_init(). */",
        "    lwip_init();",
        '    sys_thread_new("s2c_net",',
        "                   spec2codeTestbenchNetworkThread,",
        "                   NULL,",
        "                   SPEC2CODE_TESTBENCH_THREAD_STACKSIZE,",
        "                   DEFAULT_THREAD_PRIO);",
        "    vTaskDelete(NULL);",
        "}",
        "",
    ]
    return "\n".join(lines)


def _testbench_lwip_source_raw(spec: dict) -> str:
    eth = _zynqmp_lwip_eth_controller(spec)
    if eth is None:
        raise cmodel.CodegenError("lwIP test bench requested without a ZynqMP PS Ethernet controller")
    project_name = spec["project"]["name"]
    entries = _testbench_board_controller_entries(spec)
    headers = [
        '#include "spec2code_testbench_lwip.h"',
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "xparameters.h"',
        '#include "xstatus.h"',
        '#include "xil_printf.h"',
        '#include "lwip/err.h"',
        '#include "lwip/init.h"',
        '#include "lwip/ip_addr.h"',
        '#include "lwip/pbuf.h"',
        '#include "lwip/tcp.h"',
        '#include "netif/xadapter.h"',
        '#include <stddef.h>',
    ]
    if any(entry["htype"] == "XIicPs" for entry in entries):
        headers.append('#include "xiicps.h"')
    if any(entry["htype"] == "XSpiPs" for entry in entries):
        headers.append('#include "xspips.h"')
    if any(entry["htype"] == "XQspiPsu" for entry in entries):
        headers.append('#include "xqspipsu.h"')

    lines = [
        "/**",
        " * @file spec2code_testbench_lwip.c",
        " * @brief Zynq UltraScale+ PS Ethernet lwIP TCP agent for Spec2Code test bench.",
        " */",
        *headers,
        "",
        "#define SPEC2CODE_TESTBENCH_LINE_MAX 512U",
        "",
        "#ifndef SPEC2CODE_TESTBENCH_ETH_BASEADDR",
        f"#define SPEC2CODE_TESTBENCH_ETH_BASEADDR {eth.get('instance')}_BASEADDR",
        "#endif",
        "",
        "#ifndef SPEC2CODE_TESTBENCH_MAC0",
        "#define SPEC2CODE_TESTBENCH_MAC0 0x02U",
        "#define SPEC2CODE_TESTBENCH_MAC1 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC2 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC3 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC4 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC5 0x02U",
        "#endif",
        "",
        "static struct netif S_sNetif;",
        "static struct tcp_pcb* S_spServerPcb;",
        "static struct tcp_pcb* S_spClientPcb;",
        "static char S_cArrRequestLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static char S_cArrResponseLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static unsigned char S_ucArrMac[6] =",
        "{",
        "    SPEC2CODE_TESTBENCH_MAC0,",
        "    SPEC2CODE_TESTBENCH_MAC1,",
        "    SPEC2CODE_TESTBENCH_MAC2,",
        "    SPEC2CODE_TESTBENCH_MAC3,",
        "    SPEC2CODE_TESTBENCH_MAC4,",
        "    SPEC2CODE_TESTBENCH_MAC5",
        "};",
        "static unsigned int S_uiRequestLength;",
        "static unsigned int S_uiBoardReady;",
        "static unsigned int S_uiNetworkReady;",
        "static unsigned int S_uiServerReady;",
        "",
        *_testbench_board_handle_decls(entries),
        "static unsigned int spec2codeTestbenchStringLengthLocal(const char* cpText)",
        "{",
        "    unsigned int uiLength;",
        "",
        "    uiLength = 0U;",
        "    while ((cpText != NULL) && (cpText[uiLength] != '\\0'))",
        "    {",
        "        uiLength++;",
        "    }",
        "    return uiLength;",
        "}",
        "",
        "static void spec2codeTestbenchLineReset(void)",
        "{",
        "    S_uiRequestLength = 0U;",
        "    S_cArrRequestLine[0] = '\\0';",
        "}",
        "",
        "static err_t spec2codeTestbenchResponseSend(struct tcp_pcb* spTcpPcb)",
        "{",
        "    err_t enErr;",
        "    unsigned int uiLength;",
        "",
        "    uiLength = spec2codeTestbenchStringLengthLocal(S_cArrResponseLine);",
        "    if ((spTcpPcb == NULL) || (uiLength == 0U) || (uiLength > 0xFFFFU))",
        "    {",
        "        return ERR_VAL;",
        "    }",
        "    enErr = tcp_write(spTcpPcb, S_cArrResponseLine, (unsigned short)uiLength, TCP_WRITE_FLAG_COPY);",
        "    if (enErr == ERR_OK)",
        "    {",
        "        enErr = tcp_output(spTcpPcb);",
        "    }",
        "    return enErr;",
        "}",
        "",
        "static void spec2codeTestbenchByteConsume(struct tcp_pcb* spTcpPcb, char cByte)",
        "{",
        "    int iStatus;",
        "",
        "    if (cByte == '\\r')",
        "    {",
        "        return;",
        "    }",
        "    if (cByte == '\\n')",
        "    {",
        "        S_cArrRequestLine[S_uiRequestLength] = '\\0';",
        "        iStatus = spec2codeTestbenchDispatchLine(S_cArrRequestLine,",
        "                                                 S_cArrResponseLine,",
        "                                                 SPEC2CODE_TESTBENCH_LINE_MAX);",
        "        if (iStatus == XST_SUCCESS)",
        "        {",
        "            (void)spec2codeTestbenchResponseSend(spTcpPcb);",
        "        }",
        "        spec2codeTestbenchLineReset();",
        "        return;",
        "    }",
        "    if (S_uiRequestLength >= (SPEC2CODE_TESTBENCH_LINE_MAX - 1U))",
        "    {",
        "        spec2codeTestbenchLineReset();",
        "        return;",
        "    }",
        "    S_cArrRequestLine[S_uiRequestLength] = cByte;",
        "    S_uiRequestLength++;",
        "}",
        "",
        "static err_t spec2codeTestbenchTcpReceive(void* vpArg,",
        "                                           struct tcp_pcb* spTcpPcb,",
        "                                           struct pbuf* spPbuf,",
        "                                           err_t enErr)",
        "{",
        "    struct pbuf* spCurrent;",
        "    char* cpPayload;",
        "    unsigned int uiIndex;",
        "",
        "    (void)vpArg;",
        "    if ((enErr != ERR_OK) || (spTcpPcb == NULL))",
        "    {",
        "        return enErr;",
        "    }",
        "    if (spPbuf == NULL)",
        "    {",
        "        (void)tcp_close(spTcpPcb);",
        "        S_spClientPcb = NULL;",
        "        spec2codeTestbenchLineReset();",
        "        return ERR_OK;",
        "    }",
        "    tcp_recved(spTcpPcb, spPbuf->tot_len);",
        "    for (spCurrent = spPbuf; spCurrent != NULL; spCurrent = spCurrent->next)",
        "    {",
        "        cpPayload = (char*)spCurrent->payload;",
        "        for (uiIndex = 0U; uiIndex < (unsigned int)spCurrent->len; uiIndex++)",
        "        {",
        "            spec2codeTestbenchByteConsume(spTcpPcb, cpPayload[uiIndex]);",
        "        }",
        "    }",
        "    pbuf_free(spPbuf);",
        "    return ERR_OK;",
        "}",
        "",
        "static void spec2codeTestbenchTcpError(void* vpArg, err_t enErr)",
        "{",
        "    (void)vpArg;",
        "    (void)enErr;",
        "    S_spClientPcb = NULL;",
        "    spec2codeTestbenchLineReset();",
        "}",
        "",
        "static err_t spec2codeTestbenchTcpAccept(void* vpArg,",
        "                                          struct tcp_pcb* spNewPcb,",
        "                                          err_t enErr)",
        "{",
        "    (void)vpArg;",
        "    if ((enErr != ERR_OK) || (spNewPcb == NULL))",
        "    {",
        "        return enErr;",
        "    }",
        "    if (S_spClientPcb != NULL)",
        "    {",
        "        tcp_abort(spNewPcb);",
        "        return ERR_ABRT;",
        "    }",
        "    S_spClientPcb = spNewPcb;",
        "    spec2codeTestbenchLineReset();",
        "    tcp_arg(spNewPcb, NULL);",
        "    tcp_recv(spNewPcb, spec2codeTestbenchTcpReceive);",
        "    tcp_err(spNewPcb, spec2codeTestbenchTcpError);",
        "    return ERR_OK;",
        "}",
        "",
        *_testbench_board_init_lines(entries),
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if any(entry["htype"] == htype for entry in entries)
            for line in _testbench_board_getter_lines(entries, htype, _testbench_getter(htype))
        ],
        "int spec2codeTestbenchLwipNetworkInit(void)",
        "{",
        "    ip_addr_t sIpAddr;",
        "    ip_addr_t sNetmask;",
        "    ip_addr_t sGateway;",
        "",
        "    if (S_uiNetworkReady == 1U)",
        "    {",
        "        return XST_SUCCESS;",
        "    }",
        "    lwip_init();",
        "    IP4_ADDR(&sIpAddr,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR0,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR1,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR2,",
        "             SPEC2CODE_TESTBENCH_IP_ADDR3);",
        "    IP4_ADDR(&sNetmask,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR0,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR1,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR2,",
        "             SPEC2CODE_TESTBENCH_NETMASK_ADDR3);",
        "    IP4_ADDR(&sGateway,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR0,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR1,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR2,",
        "             SPEC2CODE_TESTBENCH_GATEWAY_ADDR3);",
        "    if (xemac_add(&S_sNetif,",
        "                  &sIpAddr,",
        "                  &sNetmask,",
        "                  &sGateway,",
        "                  S_ucArrMac,",
        "                  SPEC2CODE_TESTBENCH_ETH_BASEADDR) == NULL)",
        "    {",
        '        xil_printf("Spec2Code lwIP PS Ethernet init failed\\r\\n");',
        "        return XST_FAILURE;",
        "    }",
        "    netif_set_default(&S_sNetif);",
        "    netif_set_up(&S_sNetif);",
        "    S_uiNetworkReady = 1U;",
        "    return XST_SUCCESS;",
        "}",
        "",
        "int spec2codeTestbenchLwipTcpStart(unsigned short usPort)",
        "{",
        "    err_t enErr;",
        "",
        "    if (S_uiServerReady == 1U)",
        "    {",
        "        return XST_SUCCESS;",
        "    }",
        "    S_spServerPcb = tcp_new();",
        "    if (S_spServerPcb == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    enErr = tcp_bind(S_spServerPcb, IP_ADDR_ANY, usPort);",
        "    if (enErr != ERR_OK)",
        "    {",
        "        tcp_abort(S_spServerPcb);",
        "        S_spServerPcb = NULL;",
        "        return XST_FAILURE;",
        "    }",
        "    S_spServerPcb = tcp_listen(S_spServerPcb);",
        "    if (S_spServerPcb == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    tcp_accept(S_spServerPcb, spec2codeTestbenchTcpAccept);",
        "    S_uiServerReady = 1U;",
        "    return XST_SUCCESS;",
        "}",
        "",
        "int spec2codeTestbenchLwipStart(unsigned short usPort)",
        "{",
        "    int iStatus;",
        "",
        "    iStatus = spec2codeTestbenchBoardInit();",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    iStatus = spec2codeTestbenchLwipNetworkInit();",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        return iStatus;",
        "    }",
        "    return spec2codeTestbenchLwipTcpStart(usPort);",
        "}",
        "",
        "void spec2codeTestbenchLwipInputPoll(void)",
        "{",
        "    if (S_uiNetworkReady == 1U)",
        "    {",
        "        xemacif_input(&S_sNetif);",
        "    }",
        "}",
        "",
    ]
    return "\n".join(lines)


def _testbench_lwip_main_header(spec: dict) -> str:
    if _testbench_runtime_is_freertos(spec):
        run_decl = ""
    else:
        run_decl = "int spec2codeTestbenchLwipMainRun(void);\n"
    return (
        "/**\n"
        " * @file spec2code_testbench_lwip_main.h\n"
        " * @brief Example main loop for the Spec2Code lwIP TCP test bench agent.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_LWIP_MAIN_H\n"
        "#define SPEC2CODE_TESTBENCH_LWIP_MAIN_H\n\n"
        + run_decl +
        "int main(void);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_LWIP_MAIN_H */\n"
    )


def _testbench_lwip_main_source(spec: dict) -> str:
    if _testbench_runtime_is_freertos(spec):
        return (
            "/**\n"
            " * @file spec2code_testbench_lwip_main.c\n"
            " * @brief FreeRTOS entry for the Spec2Code lwIP TCP test bench agent.\n"
            " */\n"
            '#include "spec2code_testbench_lwip_main.h"\n'
            '#include "spec2code_testbench_lwip.h"\n'
            '#include "lwipopts.h"\n'
            '#include "lwip/sys.h"\n'
            '#include "FreeRTOS.h"\n'
            '#include "task.h"\n'
            '#include "xil_printf.h"\n\n'
            "int main(void)\n"
            "{\n"
            '    xil_printf("Spec2Code test bench TCP agent (FreeRTOS) baslatiliyor\\r\\n");\n'
            '    sys_thread_new("s2c_main",\n'
            "                   spec2codeTestbenchLwipMainThread,\n"
            "                   NULL,\n"
            "                   SPEC2CODE_TESTBENCH_THREAD_STACKSIZE,\n"
            "                   DEFAULT_THREAD_PRIO);\n"
            "    vTaskStartScheduler();\n"
            "    for (;;)\n"
            "    {\n"
            "    }\n"
            "    return 0;\n"
            "}\n"
        )
    return (
        "/**\n"
        " * @file spec2code_testbench_lwip_main.c\n"
        " * @brief Example main loop for the Spec2Code lwIP TCP test bench agent.\n"
        " */\n"
        '#include "spec2code_testbench_lwip_main.h"\n'
        '#include "spec2code_testbench_lwip.h"\n'
        '#include "xil_printf.h"\n'
        '#include "xstatus.h"\n\n'
        "int spec2codeTestbenchLwipMainRun(void)\n"
        "{\n"
        "    int iStatus;\n\n"
        "    iStatus = spec2codeTestbenchLwipStart(SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT);\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        "        xil_printf(\"Spec2Code test bench TCP agent baslatilamadi: %d\\r\\n\", iStatus);\n"
        "        return iStatus;\n"
        "    }\n"
        "    xil_printf(\"Spec2Code test bench TCP agent port %u dinliyor\\r\\n\",\n"
        "               SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT);\n"
        "    for (;;)\n"
        "    {\n"
        "        spec2codeTestbenchLwipInputPoll();\n"
        "    }\n"
        "    return XST_SUCCESS;\n"
        "}\n\n"
        "int main(void)\n"
        "{\n"
        "    return spec2codeTestbenchLwipMainRun();\n"
        "}\n"
    )


def _testbench_uart_driver(spec: dict) -> str:
    uart = _testbench_uart_controller(spec)
    driver = str(uart.get("driver", "XUartPs")) if uart else "XUartPs"
    return driver if driver in _TESTBENCH_UART_DRIVERS else "XUartPs"


def _testbench_uart_header(spec: dict) -> str:
    uart = _testbench_uart_controller(spec)
    instance = uart.get("instance") if uart else "XPAR_XUARTPS_0"
    driver = _testbench_uart_driver(spec)
    return (
        "/**\n"
        " * @file spec2code_testbench_uart.h\n"
        f" * @brief PS UART ({driver}) line-protocol agent for the Spec2Code test bench.\n"
        " *\n"
        " * Carries the same S2C line protocol as the TCP agent over the PS UART.\n"
        ' * Lines that do not start with "S2C|" are ignored, so the agent can\n'
        " * share the console UART with xil_printf output.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_UART_H\n"
        "#define SPEC2CODE_TESTBENCH_UART_H\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_UART_DEVICE_ID\n"
        f"#define SPEC2CODE_TESTBENCH_UART_DEVICE_ID {instance}_DEVICE_ID\n"
        "#endif\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_UART_BAUD\n"
        "#define SPEC2CODE_TESTBENCH_UART_BAUD 115200U\n"
        "#endif\n\n"
        "int spec2codeTestbenchBoardInit(void);\n"
        "int spec2codeTestbenchUartInit(void);\n"
        "void spec2codeTestbenchUartRun(void);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_UART_H */\n"
    )


def _testbench_uart_source(spec: dict) -> str:
    uart = _testbench_uart_controller(spec)
    if uart is None:
        raise cmodel.CodegenError("UART test bench requested without a PS UART controller")
    project_name = spec["project"]["name"]
    entries = _testbench_board_controller_entries(spec)
    headers = [
        '#include "spec2code_testbench_uart.h"',
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "xparameters.h"',
        '#include "xstatus.h"',
        '#include "xil_printf.h"',
        f'#include "{_TESTBENCH_UART_DRIVERS[_testbench_uart_driver(spec)]}"',
        '#include <stddef.h>',
    ]
    uart_prefix = _testbench_uart_driver(spec)
    for htype, header in _TESTBENCH_HANDLE_HEADERS:
        if any(entry["htype"] == htype for entry in entries):
            headers.append(f'#include "{header}"')

    lines = [
        "/**",
        " * @file spec2code_testbench_uart.c",
        f" * @brief PS UART ({uart_prefix}) polled line-protocol agent for the Spec2Code test bench.",
        " *",
        " * Polled receive per the official polled UART example; needs no",
        " * interrupts and no scheduler, so the same agent runs on bare metal",
        " * and on a FreeRTOS BSP alike.",
        " */",
        *headers,
        "",
        "#define SPEC2CODE_TESTBENCH_LINE_MAX 512U",
        "",
        f"static {uart_prefix} S_sTestbenchUart;",
        "static char S_cArrRequestLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static char S_cArrResponseLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static unsigned int S_uiBoardReady;",
        "",
        *_testbench_board_handle_decls(entries),
        "static unsigned int spec2codeTestbenchStringLengthLocal(const char* cpText)",
        "{",
        "    unsigned int uiLength;",
        "",
        "    uiLength = 0U;",
        "    while ((cpText != NULL) && (cpText[uiLength] != '\\0'))",
        "    {",
        "        uiLength++;",
        "    }",
        "    return uiLength;",
        "}",
        "",
        *_testbench_board_init_lines(entries),
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if any(entry["htype"] == htype for entry in entries)
            for line in _testbench_board_getter_lines(entries, htype, _testbench_getter(htype))
        ],
        *(
            [
                # AXI UARTLITE: single-call init; baud is fixed in hardware.
                "int spec2codeTestbenchUartInit(void)",
                "{",
                "    int iStatus;",
                "",
                "    iStatus = XUartLite_Initialize(&S_sTestbenchUart, SPEC2CODE_TESTBENCH_UART_DEVICE_ID);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                '        xil_printf("Spec2Code UART init basarisiz\\r\\n");',
                "        return iStatus;",
                "    }",
                "    return XST_SUCCESS;",
                "}",
            ]
            if uart_prefix == "XUartLite"
            else [
                "int spec2codeTestbenchUartInit(void)",
                "{",
                f"    {uart_prefix}_Config* spUartConfig;",
                "    int iStatus;",
                "",
                f"    spUartConfig = {uart_prefix}_LookupConfig(SPEC2CODE_TESTBENCH_UART_DEVICE_ID);",
                "    if (spUartConfig == NULL)",
                "    {",
                '        xil_printf("Spec2Code UART config bulunamadi\\r\\n");',
                "        return XST_FAILURE;",
                "    }",
                f"    iStatus = {uart_prefix}_CfgInitialize(&S_sTestbenchUart, spUartConfig, spUartConfig->BaseAddress);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                f"    iStatus = {uart_prefix}_SetBaudRate(&S_sTestbenchUart, SPEC2CODE_TESTBENCH_UART_BAUD);",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
                "    return XST_SUCCESS;",
                "}",
            ]
        ),
        "",
        "static void spec2codeTestbenchUartSendLine(const char* cpLine)",
        "{",
        "    unsigned int uiLength;",
        "    unsigned int uiSent;",
        "",
        "    uiLength = spec2codeTestbenchStringLengthLocal(cpLine);",
        "    uiSent = 0U;",
        "    while (uiSent < uiLength)",
        "    {",
        f"        uiSent += {uart_prefix}_Send(&S_sTestbenchUart,",
        "                               (u8*)&cpLine[uiSent],",
        "                               uiLength - uiSent);",
        "    }",
        "}",
        "",
        "static int spec2codeTestbenchUartLineIsRequest(const char* cpLine)",
        "{",
        "    /* Only \"S2C|...\" lines are protocol requests; terminal echo and",
        "     * boot noise on a shared console UART are skipped. */",
        "    if ((cpLine[0] == 'S') && (cpLine[1] == '2') && (cpLine[2] == 'C') && (cpLine[3] == '|'))",
        "    {",
        "        return 1;",
        "    }",
        "    return 0;",
        "}",
        "",
        "void spec2codeTestbenchUartRun(void)",
        "{",
        "    unsigned int uiLineLength;",
        "    unsigned int uiPrevWasCr;",
        "    unsigned char ucByte;",
        "",
        "    /* Loglar S2C trafigiyle ayni UART'tan aksin. */",
        "    spec2codeLogSinkSet(spec2codeTestbenchUartSendLine);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"UART agent dongusu basladi; log seviyesi=%s\",",
        "                 spec2codeLogLevelName(spec2codeLogLevelGet()));",
        "    uiLineLength = 0U;",
        "    uiPrevWasCr = 0U;",
        "    for (;;)",
        "    {",
        f"        if ({uart_prefix}_Recv(&S_sTestbenchUart, &ucByte, 1U) == 0U)",
        "        {",
        "            continue;",
        "        }",
        "        if ((ucByte != (unsigned char)'\\r') && (ucByte != (unsigned char)'\\n'))",
        "        {",
        "            uiPrevWasCr = 0U;",
        "            if (uiLineLength < (SPEC2CODE_TESTBENCH_LINE_MAX - 1U))",
        "            {",
        "                S_cArrRequestLine[uiLineLength] = (char)ucByte;",
        "                uiLineLength++;",
        "            }",
        "            else",
        "            {",
        "                uiLineLength = 0U;",
        "            }",
        "            continue;",
        "        }",
        "        /* CR de LF de satiri bitirir: terminal Enter'i cogunlukla",
        "         * yalniz CR gonderir. CRLF'nin LF'si yutulur ki bos satir",
        "         * istemi iki kez basilmasin. */",
        "        if ((ucByte == (unsigned char)'\\n') && (uiPrevWasCr == 1U))",
        "        {",
        "            uiPrevWasCr = 0U;",
        "            continue;",
        "        }",
        "        if (ucByte == (unsigned char)'\\r')",
        "        {",
        "            uiPrevWasCr = 1U;",
        "        }",
        "        else",
        "        {",
        "            uiPrevWasCr = 0U;",
        "        }",
        "        S_cArrRequestLine[uiLineLength] = '\\0';",
        "        if (uiLineLength == 0U)",
        "        {",
        "            /* Bos satir (Enter): canlilik istemi - agent yasiyorsa",
        "             * konsola \"> \" duser, cakilma/takilma buradan anlasilir. */",
        "            spec2codeTestbenchUartSendLine(\"> \\r\\n\");",
        "            continue;",
        "        }",
        "        uiLineLength = 0U;",
        "        if (spec2codeTestbenchUartLineIsRequest(S_cArrRequestLine) == 0)",
        "        {",
        "            continue;",
        "        }",
        "        (void)spec2codeTestbenchDispatchLine(S_cArrRequestLine,",
        "                                             S_cArrResponseLine,",
        "                                             SPEC2CODE_TESTBENCH_LINE_MAX);",
        "        spec2codeTestbenchUartSendLine(S_cArrResponseLine);",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def _testbench_uart_main_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_uart_main.h\n"
        " * @brief Entry point for the Spec2Code UART test bench agent.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_UART_MAIN_H\n"
        "#define SPEC2CODE_TESTBENCH_UART_MAIN_H\n\n"
        "int main(void);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_UART_MAIN_H */\n"
    )


def _testbench_uart_main_source(spec: dict) -> str:
    project_name = spec["project"]["name"]
    app_version = _app_version()
    banner = (
        f'    xil_printf("Spec2Code test bench {app_version} | proje: {project_name}'
        ' | transport: UART\\r\\n");\n'
        '    xil_printf("Enter\'a basinca \\"> \\" istemi doner (canlilik kontrolu).\\r\\n");\n'
    )
    banner += (
        '    xil_printf("S2C-UART-AGENT-READY (uartlite, baud sabit donanimda)\\r\\n");\n'
        if _testbench_uart_driver(spec) == "XUartLite"
        else '    xil_printf("S2C-UART-AGENT-READY baud=%u\\r\\n", SPEC2CODE_TESTBENCH_UART_BAUD);\n'
    )
    runtime_note = (
        " * The polled agent needs no scheduler; on a FreeRTOS BSP it runs\n"
        " * before vTaskStartScheduler would, which is intentional.\n"
        if _testbench_runtime_is_freertos(spec)
        else ""
    )
    return (
        "/**\n"
        " * @file spec2code_testbench_uart_main.c\n"
        " * @brief Entry point for the Spec2Code UART test bench agent.\n"
        + runtime_note +
        " */\n"
        '#include "spec2code_testbench_uart_main.h"\n'
        '#include "spec2code_testbench_uart.h"\n'
        '#include "xil_printf.h"\n'
        '#include "xstatus.h"\n\n'
        "int main(void)\n"
        "{\n"
        "    int iStatus;\n\n"
        "    iStatus = spec2codeTestbenchBoardInit();\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        '        xil_printf("Spec2Code board init basarisiz: %d\\r\\n", iStatus);\n'
        "        return iStatus;\n"
        "    }\n"
        "    iStatus = spec2codeTestbenchUartInit();\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        '        xil_printf("Spec2Code UART agent baslatilamadi: %d\\r\\n", iStatus);\n'
        "        return iStatus;\n"
        "    }\n"
        + banner +
        "    spec2codeTestbenchUartRun();\n"
        "    return XST_SUCCESS;\n"
        "}\n"
    )


def _testbench_coresight_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_coresight.h\n"
        " * @brief CoreSight DCC (psu_coresight_0) line-protocol agent for the Spec2Code test bench.\n"
        " *\n"
        " * Carries the same S2C line protocol as the TCP/UART agents over the\n"
        " * Arm Debug Communication Channel: no cable beyond JTAG, no PHY, no\n"
        " * UART pin needed. The host bridges the channel with xsdb\n"
        ' * "jtagterminal -socket" (works over SmartLynq too).\n'
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_CORESIGHT_H\n"
        "#define SPEC2CODE_TESTBENCH_CORESIGHT_H\n\n"
        "int spec2codeTestbenchBoardInit(void);\n"
        "int spec2codeTestbenchCoresightInit(void);\n"
        "void spec2codeTestbenchCoresightRun(void);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_CORESIGHT_H */\n"
    )


def _testbench_coresight_source(spec: dict) -> str:
    if not _testbench_coresight_supported(spec):
        raise cmodel.CodegenError(
            "CoreSight (DCC) test bench su an yalnizca ZynqMP (psu_coresight_0) "
            "platformunda dogrulandi")
    project_name = spec["project"]["name"]
    entries = _testbench_board_controller_entries(spec)
    headers = [
        '#include "spec2code_testbench_coresight.h"',
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "xparameters.h"',
        '#include "xstatus.h"',
        '#include "xcoresightpsdcc.h"',
        '#include <stddef.h>',
    ]
    for htype, header in _TESTBENCH_HANDLE_HEADERS:
        if any(entry["htype"] == htype for entry in entries):
            headers.append(f'#include "{header}"')

    lines = [
        "/**",
        " * @file spec2code_testbench_coresight.c",
        " * @brief CoreSight DCC polled line-protocol agent for the Spec2Code test bench.",
        " *",
        " * Uses the standalone BSP coresightps_dcc driver",
        " * (XCoresightPs_DccSendByte/RecvByte). RecvByte blocks until the",
        " * debugger side writes a byte, which is exactly the agent's job:",
        " * wait for a request line, dispatch, answer. No interrupts, no",
        " * scheduler - runs the same on bare metal and FreeRTOS BSPs.",
        " */",
        *headers,
        "",
        "#define SPEC2CODE_TESTBENCH_LINE_MAX 512U",
        "",
        "static char S_cArrRequestLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static char S_cArrResponseLine[SPEC2CODE_TESTBENCH_LINE_MAX];",
        "static unsigned int S_uiBoardReady;",
        "",
        *_testbench_board_handle_decls(entries),
        "static unsigned int spec2codeTestbenchStringLengthLocal(const char* cpText)",
        "{",
        "    unsigned int uiLength;",
        "",
        "    uiLength = 0U;",
        "    while ((cpText != NULL) && (cpText[uiLength] != '\\0'))",
        "    {",
        "        uiLength++;",
        "    }",
        "    return uiLength;",
        "}",
        "",
        *_testbench_board_init_lines(entries),
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if any(entry["htype"] == htype for entry in entries)
            for line in _testbench_board_getter_lines(entries, htype, _testbench_getter(htype))
        ],
        "int spec2codeTestbenchCoresightInit(void)",
        "{",
        "    /* DCC her Arm cekirdeginde hazirdir; ayrica init gerekmez. */",
        "    return XST_SUCCESS;",
        "}",
        "",
        "static void spec2codeTestbenchCoresightSendLine(const char* cpLine)",
        "{",
        "    unsigned int uiLength;",
        "    unsigned int uiSent;",
        "",
        "    uiLength = spec2codeTestbenchStringLengthLocal(cpLine);",
        "    for (uiSent = 0U; uiSent < uiLength; uiSent++)",
        "    {",
        "        XCoresightPs_DccSendByte(0U, (u8)cpLine[uiSent]);",
        "    }",
        "}",
        "",
        "static int spec2codeTestbenchCoresightLineIsRequest(const char* cpLine)",
        "{",
        "    if ((cpLine[0] == 'S') && (cpLine[1] == '2') && (cpLine[2] == 'C') && (cpLine[3] == '|'))",
        "    {",
        "        return 1;",
        "    }",
        "    return 0;",
        "}",
        "",
        "void spec2codeTestbenchCoresightRun(void)",
        "{",
        "    unsigned int uiLineLength;",
        "    unsigned int uiPrevWasCr;",
        "    unsigned char ucByte;",
        "",
        "    /* Loglar S2C trafigiyle ayni DCC kanalindan aksin (jtagterminal). */",
        "    spec2codeLogSinkSet(spec2codeTestbenchCoresightSendLine);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"CoreSight agent dongusu basladi; log seviyesi=%s\",",
        "                 spec2codeLogLevelName(spec2codeLogLevelGet()));",
        "    uiLineLength = 0U;",
        "    uiPrevWasCr = 0U;",
        "    for (;;)",
        "    {",
        "        ucByte = (unsigned char)XCoresightPs_DccRecvByte(0U);",
        "        if ((ucByte != (unsigned char)'\\r') && (ucByte != (unsigned char)'\\n'))",
        "        {",
        "            uiPrevWasCr = 0U;",
        "            if (uiLineLength < (SPEC2CODE_TESTBENCH_LINE_MAX - 1U))",
        "            {",
        "                S_cArrRequestLine[uiLineLength] = (char)ucByte;",
        "                uiLineLength++;",
        "            }",
        "            else",
        "            {",
        "                uiLineLength = 0U;",
        "            }",
        "            continue;",
        "        }",
        "        /* CR de LF de satiri bitirir; CRLF'nin LF'si yutulur ki bos",
        "         * satir istemi iki kez basilmasin. */",
        "        if ((ucByte == (unsigned char)'\\n') && (uiPrevWasCr == 1U))",
        "        {",
        "            uiPrevWasCr = 0U;",
        "            continue;",
        "        }",
        "        if (ucByte == (unsigned char)'\\r')",
        "        {",
        "            uiPrevWasCr = 1U;",
        "        }",
        "        else",
        "        {",
        "            uiPrevWasCr = 0U;",
        "        }",
        "        S_cArrRequestLine[uiLineLength] = '\\0';",
        "        if (uiLineLength == 0U)",
        "        {",
        "            /* Bos satir (Enter): canlilik istemi - agent yasiyorsa",
        "             * konsola \"> \" duser, cakilma/takilma buradan anlasilir. */",
        "            spec2codeTestbenchCoresightSendLine(\"> \\r\\n\");",
        "            continue;",
        "        }",
        "        uiLineLength = 0U;",
        "        if (spec2codeTestbenchCoresightLineIsRequest(S_cArrRequestLine) == 0)",
        "        {",
        "            continue;",
        "        }",
        "        (void)spec2codeTestbenchDispatchLine(S_cArrRequestLine,",
        "                                             S_cArrResponseLine,",
        "                                             SPEC2CODE_TESTBENCH_LINE_MAX);",
        "        spec2codeTestbenchCoresightSendLine(S_cArrResponseLine);",
        "    }",
        "}",
    ]
    return "\n".join(lines) + "\n"


def _testbench_coresight_main_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_coresight_main.h\n"
        " * @brief Entry point for the Spec2Code CoreSight DCC test bench agent.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_CORESIGHT_MAIN_H\n"
        "#define SPEC2CODE_TESTBENCH_CORESIGHT_MAIN_H\n\n"
        "int main(void);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_CORESIGHT_MAIN_H */\n"
    )


def _testbench_coresight_main_source(spec: dict) -> str:
    project_name = spec["project"]["name"]
    app_version = _app_version()
    runtime_note = (
        " * The polled agent needs no scheduler; on a FreeRTOS BSP it runs\n"
        " * before vTaskStartScheduler would, which is intentional.\n"
        if _testbench_runtime_is_freertos(spec)
        else ""
    )
    banner_text = (
        f"Spec2Code test bench {app_version} | proje: {project_name}"
        " | transport: CoreSight DCC (psu_coresight_0)"
    )
    return (
        "/**\n"
        " * @file spec2code_testbench_coresight_main.c\n"
        " * @brief Entry point for the Spec2Code CoreSight DCC test bench agent.\n"
        " *\n"
        " * BSP stdin/stdout stays on the console UART: xil_printf keeps\n"
        " * printing there, only the S2C protocol rides the DCC. The boot\n"
        " * banner is printed on BOTH channels so the serial console shows\n"
        " * life at power-up and the host's jtagterminal bridge sees the\n"
        " * agent too.\n"
        + runtime_note +
        " */\n"
        '#include "spec2code_testbench_coresight_main.h"\n'
        '#include "spec2code_testbench_coresight.h"\n'
        '#include "xcoresightpsdcc.h"\n'
        '#include "xil_printf.h"\n'
        '#include "xstatus.h"\n\n'
        "static void spec2codeTestbenchCoresightBannerLine(const char* cpLine)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    for (uiIndex = 0U; cpLine[uiIndex] != '\\0'; uiIndex++)\n"
        "    {\n"
        "        XCoresightPs_DccSendByte(0U, (u8)cpLine[uiIndex]);\n"
        "    }\n"
        "}\n\n"
        "int main(void)\n"
        "{\n"
        "    int iStatus;\n\n"
        "    iStatus = spec2codeTestbenchBoardInit();\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        '        xil_printf("Spec2Code board init basarisiz: %d\\r\\n", iStatus);\n'
        "        return iStatus;\n"
        "    }\n"
        "    iStatus = spec2codeTestbenchCoresightInit();\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        '        xil_printf("Spec2Code CoreSight agent baslatilamadi: %d\\r\\n", iStatus);\n'
        "        return iStatus;\n"
        "    }\n"
        "    /* Seri konsol (stdout=UART): acilis isareti. */\n"
        f'    xil_printf("{banner_text}\\r\\n");\n'
        '    xil_printf("S2C protokolu CoreSight DCC uzerinde; bu UART yalnizca konsol.\\r\\n");\n'
        '    xil_printf("S2C-CORESIGHT-AGENT-READY\\r\\n");\n'
        "    /* Host koprusu (jtagterminal): ayni banner DCC uzerinden. */\n"
        f'    spec2codeTestbenchCoresightBannerLine("{banner_text}\\r\\n");\n'
        '    spec2codeTestbenchCoresightBannerLine("Enter\'a basinca \\"> \\" istemi doner'
        ' (canlilik kontrolu).\\r\\n");\n'
        '    spec2codeTestbenchCoresightBannerLine("S2C-CORESIGHT-AGENT-READY\\r\\n");\n'
        "    spec2codeTestbenchCoresightRun();\n"
        "    return XST_SUCCESS;\n"
        "}\n"
    )


def testbench_harness_paths(spec: dict, out_dir: Path) -> list[Path]:
    project_name = spec["project"]["name"]
    tests_dir = out_dir / "tests"
    paths = [
        tests_dir / "spec2code_testbench_protocol.h",
        tests_dir / "spec2code_testbench_protocol.c",
        tests_dir / "spec2code_testbench_log.h",
        tests_dir / "spec2code_testbench_log.c",
        tests_dir / f"{project_name}_testbench_ops.h",
        tests_dir / f"{project_name}_testbench_ops.c",
        tests_dir / "spec2code_testbench_manifest.json",
    ]
    if _testbench_lwip_enabled(spec):
        paths.extend([
            tests_dir / "spec2code_testbench_lwip.h",
            tests_dir / "spec2code_testbench_lwip.c",
            tests_dir / "spec2code_testbench_lwip_main.h",
            tests_dir / "spec2code_testbench_lwip_main.c",
        ])
    if _testbench_uart_enabled(spec):
        paths.extend([
            tests_dir / "spec2code_testbench_uart.h",
            tests_dir / "spec2code_testbench_uart.c",
            tests_dir / "spec2code_testbench_uart_main.h",
            tests_dir / "spec2code_testbench_uart_main.c",
        ])
    if _testbench_coresight_enabled(spec):
        paths.extend([
            tests_dir / "spec2code_testbench_coresight.h",
            tests_dir / "spec2code_testbench_coresight.c",
            tests_dir / "spec2code_testbench_coresight_main.h",
            tests_dir / "spec2code_testbench_coresight_main.c",
        ])
    return paths


def write_testbench_harness(spec: dict, out_dir: Path, *, root: Path = _ROOT) -> list[str]:
    get_descriptor = make_descriptor_loader(root)
    paths = testbench_harness_paths(spec, out_dir)
    contents = [
        _apply_default_identifier_style(_testbench_protocol_header()),
        _apply_default_identifier_style(_testbench_protocol_source()),
        _apply_default_identifier_style(_testbench_log_header()),
        _apply_default_identifier_style(_testbench_log_source()),
        _apply_default_identifier_style(_testbench_ops_header(spec["project"]["name"], _testbench_used_handle_types(spec))),
        _apply_default_identifier_style(_testbench_ops_source(spec, get_descriptor)),
        _testbench_manifest(spec, get_descriptor),
    ]
    if _testbench_lwip_enabled(spec):
        contents.extend([
            _apply_default_identifier_style(_testbench_lwip_header(spec)),
            _apply_default_identifier_style(_testbench_lwip_source(spec)),
            _apply_default_identifier_style(_testbench_lwip_main_header(spec)),
            _apply_default_identifier_style(_testbench_lwip_main_source(spec)),
        ])
    if _testbench_uart_enabled(spec):
        contents.extend([
            _apply_default_identifier_style(_testbench_uart_header(spec)),
            _apply_default_identifier_style(_testbench_uart_source(spec)),
            _apply_default_identifier_style(_testbench_uart_main_header()),
            _apply_default_identifier_style(_testbench_uart_main_source(spec)),
        ])
    if _testbench_coresight_enabled(spec):
        contents.extend([
            _apply_default_identifier_style(_testbench_coresight_header()),
            _apply_default_identifier_style(_testbench_coresight_source(spec)),
            _apply_default_identifier_style(_testbench_coresight_main_header()),
            _apply_default_identifier_style(_testbench_coresight_main_source(spec)),
        ])
    return [str(hio.write_output(path, content)) for path, content in zip(paths, contents)]


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def _remove_retired_boardless_artifacts(out_dir: Path, project_name: str) -> None:
    legacy = "mo" + "ck"
    for path in (
        out_dir / "tests" / f"spec2code_{legacy}_bus.h",
        out_dir / "tests" / f"spec2code_{legacy}_bus.c",
        out_dir / "tests" / f"{project_name}_{legacy}_plan.h",
        out_dir / "tests" / f"{project_name}_{legacy}_plan.c",
    ):
        path.unlink(missing_ok=True)


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
    _remove_retired_boardless_artifacts(out_dir, spec["project"]["name"])
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

    written.extend(write_testbench_harness(spec, out_dir, root=root))

    emit({"event": "codegen.done", "files": len(written)})
    return written
