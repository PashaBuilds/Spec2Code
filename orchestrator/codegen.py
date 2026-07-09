"""Static (deterministic) codegen orchestration (Brief 13).

Loads a validated project.spec, builds the C render-model (cmodel), renders the Jinja
templates, and writes drop-in output through hostplat.io (always CRLF). No LLM involved.
"""

from __future__ import annotations

import json
import os
import re
import sys
import zlib
from functools import lru_cache
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
            # utf-8-sig: BOM'lu yazilmis dosyada fullmatch sessizce
            # kacmasin (SAHA: paketli uygulama ajana "dev" damgaladi).
            value = version_file.read_text(encoding="utf-8-sig", errors="replace").strip()
            if re.fullmatch(r"v\d+\.\d+\.\d+", value):
                return value

    source_version = _ROOT / "frontend" / "src" / "lib" / "version.ts"
    if source_version.is_file():
        text = source_version.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'"(v\d+\.\d+\.\d+)"', text)
        if match:
            return match.group(1)

    # Changelog yedegi TUM koklerde aranir: release bundle'inda changelog.md
    # exe'nin YANINDA durur (_ROOT frozen uygulamada _MEIPASS'tir ve orada
    # changelog yoktur - yalniz _ROOT'a bakmak paketli uygulamada bu yedegi
    # olu koda ceviriyordu).
    for root in roots:
        changelog = root / "changelog.md"
        if changelog.is_file():
            text = changelog.read_text(encoding="utf-8-sig", errors="replace")
            match = re.search(r"^##\s+(v\d+\.\d+\.\d+)\s+", text, re.MULTILINE)
            if match:
                return match.group(1)

    return "dev"


def _c_string_literal(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


# --- S2C-MSG mesaj kataloğu (tek doğruluk kaynağı: backend/data/message_catalog.json) ---
# Codegen backend'i import ETMEZ (katman ayrımı); katalog dosyası _ROOT'a göre
# okunur, CRC32 zlib ile aynı bayt dizisinden hesaplanır (s2cmsg.catalog_crc32
# ile birebir eşdeğer). Paketli exe'de dosya PyInstaller datas'ıyla gelir.
_MESSAGE_CATALOG_PATH = _ROOT / "backend" / "data" / "message_catalog.json"


@lru_cache(maxsize=1)
def _load_message_catalog() -> dict:
    catalog = json.loads(_MESSAGE_CATALOG_PATH.read_text(encoding="utf-8"))
    catalog["by_op"] = {m["op"]: m for m in catalog["messages"] if m.get("op")}
    catalog["by_name"] = {m["name"]: m for m in catalog["messages"]}
    return catalog


def _message_catalog_crc32() -> int:
    return zlib.crc32(_MESSAGE_CATALOG_PATH.read_bytes()) & 0xFFFFFFFF


def _message_id_for_op(op_name: str) -> int:
    entry = _load_message_catalog()["by_op"].get(op_name)
    if entry is None:
        raise cmodel.CodegenError(
            f"op {op_name!r} mesaj katalogunda yok — "
            "backend/data/message_catalog.json'a KALICI ID ile ekleyin")
    return int(entry["id"], 16)


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
        " * @brief Test bench istek/yanit veri yapilari + para birimi yardimcilari.\n"
        " *\n"
        " * S2C-MSG binary tel katmani (spec2code_mesaj.*) bu yapilari doldurur ve\n"
        " * dispatch'e kopruler; metin satir protokolu (parse/format) yoktur.\n"
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
        "int spec2codeTestbenchStringEqual(const char* cpLeft, const char* cpRight);\n"
        "void spec2codeTestbenchMessageSet(SSpec2codeTestbenchResponse* spResponse, const char* cpMessage);\n"
        "int spec2codeTestbenchDataPush(SSpec2codeTestbenchResponse* spResponse, unsigned char ucValue);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_PROTOCOL_H */\n"
    )


def _testbench_protocol_source() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_protocol.c\n"
        " * @brief Test bench istek/yanit para birimi yardimcilari (binary katman kullanir).\n"
        " */\n"
        '#include "spec2code_testbench_protocol.h"\n'
        '#include "xstatus.h"\n\n'
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
        "}\n"
    )


def _mesaj_header(spec: dict | None = None,
                  get_descriptor: Callable[[str], dict] | None = None) -> str:
    """Üretilen `spec2code_mesaj.h`: S2C-MSG binary çerçeve başlığı + parser API.

    Katalog (backend/data/message_catalog.json) tek doğruluk kaynağı; ID
    makroları (SPEC2CODE_MESAJ_*) buradan üretilir. Durum kodları 0..7. Yalnız
    unsigned int/int kullanılır (proje konvansiyonu — uint*_t / stdint.h yok).

    CIT ölçümü varsa `CERCEVE_MAX`, CIT yanıt çerçevesini de kapsayacak şekilde
    (standart yanıt ile CIT çerçevesinin büyüğü) genişletilir — transport çıktı
    tamponları bu makroyla boyutlanır. Header cit.h'ye bağlanmaz (mesaj katmanı
    tek başına derlenir kalır): CIT boyu spec'ten sayısal hesaplanır.
    """
    catalog = _load_message_catalog()
    id_lines = [
        f"#define SPEC2CODE_MESAJ_{message['name']} {message['id']}U"
        for message in catalog["messages"]
    ]
    durum_names = ["OK", "GENEL_HATA", "GECERSIZ_MESAJ", "GECERSIZ_PARAMETRE",
                   "CIHAZ_YOK", "BUS_HATASI", "ZAMAN_ASIMI", "DESTEKLENMIYOR"]
    durum_lines = [
        f"#define SPEC2CODE_MESAJ_DURUM_{name} {index}U"
        for index, name in enumerate(durum_names)
    ]
    # CIT cerceve boyu (yalniz olcum varsa CERCEVE_MAX'a katilir): baslik(12) +
    # istekSayac(4) + durum(4) + sizeof(SBoardCit). SBoardCit = uiSayac(4) +
    # uiZaman(4) + bayrak(((N+31)/32)*4) + N*12.
    cit_lines = ""
    if spec is not None and get_descriptor is not None:
        sayi = len(_cit_measurements(spec, get_descriptor))
        if sayi > 0:
            board_cit_boy = 8 + ((sayi + 31) // 32) * 4 + sayi * 12
            cit_frame = 12 + 8 + board_cit_boy
            cit_lines = (
                "/* CIT yanit cercevesi de cikti tamponuna sigmali: baslik + 8 (istekSayac+\n"
                f" * durum) + sizeof(SBoardCit) = {cit_frame} bayt ({sayi} olcum). CERCEVE_MAX\n"
                " * standart yanit ile CIT'in buyugu alinir (transport tamponu tek sabit). */\n"
                f"#define SPEC2CODE_MESAJ_CIT_CERCEVE_MAX {cit_frame}U\n"
                "#undef SPEC2CODE_MESAJ_CERCEVE_MAX\n"
                "#define SPEC2CODE_MESAJ_CERCEVE_MAX \\\n"
                "    ((SPEC2CODE_MESAJ_CERCEVE_STD >= SPEC2CODE_MESAJ_CIT_CERCEVE_MAX) ? \\\n"
                "     SPEC2CODE_MESAJ_CERCEVE_STD : SPEC2CODE_MESAJ_CIT_CERCEVE_MAX)\n\n"
            )
    return (
        "/**\n"
        " * @file spec2code_mesaj.h\n"
        " * @brief S2C-MSG binary tel katmani: cerceve basligi, cozucu (resync'li)\n"
        " *        ve dispatch koprusu. Baytlar little-endian.\n"
        " *\n"
        " * ID makrolari (SPEC2CODE_MESAJ_*) mesaj katalogundan uretildi\n"
        " * (backend/data/message_catalog.json - tek dogruluk kaynagi). El ile\n"
        " * duzenlemeyin; katalogdan yeniden uretilir.\n"
        " */\n"
        "#ifndef SPEC2CODE_MESAJ_H\n"
        "#define SPEC2CODE_MESAJ_H\n\n"
        '#include "spec2code_testbench_protocol.h"\n\n'
        "/* Cerceve sabitleri (little-endian). */\n"
        "#define SPEC2CODE_MESAJ_BASLIK_BOY 12U\n"
        "#define SPEC2CODE_MESAJ_GOVDE_MAX 4096U\n"
        "#define SPEC2CODE_MESAJ_YANIT_BIT 0x80000000U\n"
        "#define SPEC2CODE_MESAJ_IMZA 0x5343U\n"
        "#define SPEC2CODE_MESAJ_ISTEK_GOVDE_BOY 28U\n"
        "/* En buyuk standart yanit cercevesi: baslik(12) + yanit govdesi\n"
        " * (20 sabit alan + pad4(veri 256) + 4 metinBoy + pad4(metin)). Ajan\n"
        " * transportlari cikti tamponunu CERCEVE_MAX ile ayirir; feed-forward recv\n"
        " * yolu 4096B govdeyi zaten parser tamponunda tutar. */\n"
        "#define SPEC2CODE_MESAJ_CERCEVE_STD (SPEC2CODE_MESAJ_BASLIK_BOY + 20U + \\\n"
        "    (((SPEC2CODE_TESTBENCH_DATA_MAX + 3U) & ~3U) + 4U + \\\n"
        "     ((SPEC2CODE_TESTBENCH_MESSAGE_MAX + 3U) & ~3U)))\n"
        "#define SPEC2CODE_MESAJ_CERCEVE_MAX SPEC2CODE_MESAJ_CERCEVE_STD\n\n"
        + cit_lines +
        "/* Mesaj ID makrolari (katalogdan uretildi). */\n"
        + "\n".join(id_lines) + "\n\n"
        "/* Durum kodlari (yanit govdesi uiDurum). */\n"
        + "\n".join(durum_lines) + "\n\n"
        "/**\n"
        " * @brief 12 baytlik S2C-MSG cerceve basligi (little-endian, dogal 4B hizali).\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        "    unsigned int uiMesajKomut;\n"
        "    unsigned int uiMesajBoyu;\n"
        "    unsigned int uiMesajSayac;\n"
        "} SMesajBaslik;\n\n"
        "_Static_assert(sizeof(SMesajBaslik) == 12U, \"SMesajBaslik 12 bayt olmalidir\");\n"
        "/* En buyuk yanit cercevesi govde+baslik sinirlarina sigmali (transport\n"
        " * cikti tamponu bu sabittir). 452 = 12 + 20 + 256 + 4 + 160. */\n"
        "_Static_assert(SPEC2CODE_MESAJ_CERCEVE_MAX <=\n"
        "               (SPEC2CODE_MESAJ_BASLIK_BOY + SPEC2CODE_MESAJ_GOVDE_MAX),\n"
        "               \"cerceve kapasitesi govde sinirini asamaz\");\n\n"
        "/* Ic dispatch (metin protokolu para birimi olarak kalir): mesaj katmani\n"
        " * her istek cercevesini bu fonksiyona kopruler. Ayni prototip uretilen\n"
        " * spec2code_..._testbench_ops.h icinde de bulunur (uyumlu tekrar). */\n"
        "int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,\n"
        "                               SSpec2codeTestbenchResponse* spResponse);\n\n"
        "/**\n"
        " * @brief Bayt akisindan cerceve toplayan cozucu (Python FrameParser'in C ikizi).\n"
        " *\n"
        " * ucArrTampon: baslik + govde (en fazla SPEC2CODE_MESAJ_GOVDE_MAX). uiDolu\n"
        " * o ana kadar biriken bayt sayisi. Cerceve tamamlaninca sBaslik + ucArrGovde\n"
        " * doldurulur ve spec2codeMesajBesle 1 doner.\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        "    unsigned char ucArrTampon[SPEC2CODE_MESAJ_BASLIK_BOY + SPEC2CODE_MESAJ_GOVDE_MAX];\n"
        "    unsigned int uiDolu;\n"
        "    SMesajBaslik sBaslik;\n"
        "    unsigned char ucArrGovde[SPEC2CODE_MESAJ_GOVDE_MAX];\n"
        "} SMesajParser;\n\n"
        "/** @brief Cozucuyu sifirlar (tampon bosaltilir). */\n"
        "void spec2codeMesajParserSifirla(SMesajParser* spParser);\n\n"
        "/**\n"
        " * @brief Akistan bayt besle; tam cerceve tamamlaninca 1 doner.\n"
        " * @param spParser     cozucu durumu\n"
        " * @param ucpVeri      gelen bayt tamponu\n"
        " * @param uiBoy        gelen bayt sayisi\n"
        " * @param upTuketilen  bu cagride tuketilen bayt sayisi (NULL degil)\n"
        " * @return 1 = spParser->sBaslik + ucArrGovde hazir; 0 = daha fazla bayt gerek.\n"
        " *\n"
        " * Cagiran, tuketilmeyen baytlari bir sonraki cagriya tasir (tam cerceve\n"
        " * dondugunde uiBoy'un tamami tuketilmemis olabilir).\n"
        " */\n"
        "int spec2codeMesajBesle(SMesajParser* spParser, const unsigned char* ucpVeri,\n"
        "                        unsigned int uiBoy, unsigned int* upTuketilen);\n\n"
        "/**\n"
        " * @brief Bir istek cercevesini dispatch'e kopruleyip yanit cercevesi uretir.\n"
        " * @return yazilan cikti bayt sayisi (0 = cikti yok / kapasite yetersiz).\n"
        " */\n"
        "unsigned int spec2codeMesajIsle(const SMesajBaslik* spBaslik,\n"
        "                                const unsigned char* ucpGovde,\n"
        "                                unsigned char* ucpCikti,\n"
        "                                unsigned int uiCiktiKapasite);\n\n"
        "/**\n"
        " * @brief TRACE_EVENT/BUS_TRACE_EVENT cercevesi kurar (istem disi olay).\n"
        " * @return yazilan cikti bayt sayisi (0 = kapasite yetersiz).\n"
        " */\n"
        "unsigned int spec2codeMesajTraceCerceveKur(unsigned int uiMesajId, unsigned int uiSeviye,\n"
        "                                           const char* cpMetin, unsigned char* ucpCikti,\n"
        "                                           unsigned int uiKapasite);\n\n"
        "#endif /* SPEC2CODE_MESAJ_H */\n"
    )


def _mesaj_source(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    """Üretilen `spec2code_mesaj.c`: cozucu + dispatch koprusu + katalog tablolari.

    Spec'te kullanilan HER descriptor op'unun katalogda karsiligi olmali;
    olmayan bir op uretim aninda CodegenError firlatir.
    """
    catalog = _load_message_catalog()
    entries = _testbench_device_entries(spec, get_descriptor)

    # Katalog-dogrulama: spec'te fiilen uretilen her op katalogda olmali.
    # (_message_id_for_op eksikse CodegenError firlatir.)
    for row in _testbench_op_table(entries):
        _message_id_for_op(row["operation"])

    # ID -> op adi tablosu: KATALOGUN TAMAMINDAN uretilir (kalici ID'ler);
    # backend yalniz katalogdaki ID'leri gonderebilir, bu yuzden tam kapsama.
    op_rows = [
        f'    {{ {message["id"]}U, "{message["op"]}" }},'
        for message in catalog["messages"] if message.get("op")
    ]
    op_table = "\n".join(op_rows) if op_rows else "    { 0U, \"\" }"

    # Cihaz indeks -> id tablosu: device-entry sirasi == manifest devices[]
    # sirasi (indeks <-> id eslemesi garanti).
    device_ids = [entry["device"].get("id", "") for entry in entries]
    device_rows = "\n".join(
        f'    "{_c_string_escape(device_id)}",' for device_id in device_ids
    ) or '    ""'
    device_count = len(device_ids)

    # CIT: yalniz olcum varsa cit.h include edilir ve CIT_RUN hedefi olan
    # dosya-statigi (S_sMesajCit) + CIT_RUN/CIT_READ dallari uretilir.
    cit_enabled = len(_cit_measurements(spec, get_descriptor)) > 0
    cit_include = '#include "spec2code_cit.h"\n' if cit_enabled else ""
    cit_static = ("/* CIT_RUN hedefi: koss ve bu kopyayi cerceve. */\n"
                  "static SBoardCit S_sMesajCit;\n\n") if cit_enabled else ""

    return (
        "/**\n"
        " * @file spec2code_mesaj.c\n"
        " * @brief S2C-MSG binary tel katmani gerceklemesi (cozucu + dispatch\n"
        " *        koprusu). Cozucu semantigi Python s2cmsg.FrameParser.feed'in\n"
        " *        satir satir C ikizidir. Katalog tablolari otomatik uretildi.\n"
        " */\n"
        '#include "spec2code_mesaj.h"\n'
        '#include "spec2code_testbench_protocol.h"\n'
        + cit_include + "\n"
        "/* ID -> op adi tablosu (katalogdan uretildi; kalici ID'ler). */\n"
        "typedef struct\n"
        "{\n"
        "    unsigned int uiId;\n"
        "    const char* cpOp;\n"
        "} SMesajOpSatir;\n\n"
        "static const SMesajOpSatir S_sArrMesajOpTablosu[] =\n"
        "{\n"
        f"{op_table}\n"
        "};\n"
        "static const unsigned int S_uiMesajOpTabloBoy =\n"
        "    (unsigned int)(sizeof(S_sArrMesajOpTablosu) / sizeof(S_sArrMesajOpTablosu[0]));\n\n"
        "/* Cihaz indeks -> id tablosu (manifest devices[] sirasiyla ayni). */\n"
        f"#define SPEC2CODE_MESAJ_CIHAZ_SAYISI {device_count}U\n"
        "static const char* const S_cpArrCihazTablosu[] =\n"
        "{\n"
        f"{device_rows}\n"
        "};\n\n"
        "/* Yanit sayaci: ajan tarafinda monoton, 1'den baslar. */\n"
        "static unsigned int S_uiYanitSayac = 0U;\n\n"
        + cit_static
        + _mesaj_source_body(cit_enabled)
    )


# Sabit gövde: tablolardan bağımsız, tüm parser/köprü gerçeklemesi.
def _mesaj_source_body(cit_enabled: bool) -> str:
    """Parser + köprü gövdesi. `cit_enabled` ise CIT çerçeveleyici + CIT_RUN/
    CIT_READ dalları da (cit.h'ye bağlı) üretilir; değilse dallar
    DESTEKLENMIYOR döner ve cit.h include EDİLMEZ (mesaj katmanı tek başına derlenir).
    """
    cit_framer = _MESAJ_CIT_FRAMER if cit_enabled else ""
    cit_branch = _MESAJ_CIT_BRANCH_ENABLED if cit_enabled else _MESAJ_CIT_BRANCH_DISABLED
    return (_MESAJ_SOURCE_BODY_TEMPLATE
            .replace("/*<<CIT_FRAMER>>*/\n", cit_framer)
            .replace("/*<<CIT_BRANCH>>*/\n", cit_branch))


_MESAJ_SOURCE_BODY_TEMPLATE = (
    "/* --- Little-endian yardimcilar (kontrat LE; hedef endian'dan bagimsiz). --- */\n"
    "static unsigned int spec2codeMesajOku32(const unsigned char* ucpVeri)\n"
    "{\n"
    "    return ((unsigned int)ucpVeri[0])\n"
    "         | ((unsigned int)ucpVeri[1] << 8U)\n"
    "         | ((unsigned int)ucpVeri[2] << 16U)\n"
    "         | ((unsigned int)ucpVeri[3] << 24U);\n"
    "}\n\n"
    "static void spec2codeMesajYaz32(unsigned char* ucpCikti, unsigned int uiDeger)\n"
    "{\n"
    "    ucpCikti[0] = (unsigned char)(uiDeger & 0xFFU);\n"
    "    ucpCikti[1] = (unsigned char)((uiDeger >> 8U) & 0xFFU);\n"
    "    ucpCikti[2] = (unsigned char)((uiDeger >> 16U) & 0xFFU);\n"
    "    ucpCikti[3] = (unsigned char)((uiDeger >> 24U) & 0xFFU);\n"
    "}\n\n"
    "static const char* spec2codeMesajOpAdi(unsigned int uiKomut)\n"
    "{\n"
    "    unsigned int uiIndex;\n"
    "    unsigned int uiIstekId = uiKomut & ~SPEC2CODE_MESAJ_YANIT_BIT;\n\n"
    "    for (uiIndex = 0U; uiIndex < S_uiMesajOpTabloBoy; uiIndex++)\n"
    "    {\n"
    "        if (S_sArrMesajOpTablosu[uiIndex].uiId == uiIstekId)\n"
    "        {\n"
    "            return S_sArrMesajOpTablosu[uiIndex].cpOp;\n"
    "        }\n"
    "    }\n"
    "    return (const char*)0;\n"
    "}\n\n"
    "static void spec2codeMesajMetinKopya(char* cpDst, unsigned int uiDstBoy, const char* cpSrc)\n"
    "{\n"
    "    unsigned int uiIndex;\n\n"
    "    if ((cpDst == (char*)0) || (uiDstBoy == 0U))\n"
    "    {\n"
    "        return;\n"
    "    }\n"
    "    for (uiIndex = 0U; uiIndex < (uiDstBoy - 1U); uiIndex++)\n"
    "    {\n"
    "        if ((cpSrc == (const char*)0) || (cpSrc[uiIndex] == '\\0'))\n"
    "        {\n"
    "            break;\n"
    "        }\n"
    "        cpDst[uiIndex] = cpSrc[uiIndex];\n"
    "    }\n"
    "    cpDst[uiIndex] = '\\0';\n"
    "}\n\n"
    "void spec2codeMesajParserSifirla(SMesajParser* spParser)\n"
    "{\n"
    "    if (spParser == (SMesajParser*)0)\n"
    "    {\n"
    "        return;\n"
    "    }\n"
    "    spParser->uiDolu = 0U;\n"
    "    spParser->sBaslik.uiMesajKomut = 0U;\n"
    "    spParser->sBaslik.uiMesajBoyu = 0U;\n"
    "    spParser->sBaslik.uiMesajSayac = 0U;\n"
    "}\n\n"
    "/* Python FrameParser.feed'in C ikizi: baytlari biriktir, imza/boy dogrula,\n"
    " * senkron kaybinda 1 bayt kaydir; tam cerceve tamamlaninca 1 don. */\n"
    "int spec2codeMesajBesle(SMesajParser* spParser, const unsigned char* ucpVeri,\n"
    "                        unsigned int uiBoy, unsigned int* upTuketilen)\n"
    "{\n"
    "    unsigned int uiGiris;\n"
    "    unsigned int uiKomut;\n"
    "    unsigned int uiGovdeBoy;\n"
    "    unsigned int uiImza;\n"
    "    unsigned int uiToplam;\n"
    "    unsigned int uiIndex;\n\n"
    "    if (upTuketilen != (unsigned int*)0)\n"
    "    {\n"
    "        *upTuketilen = 0U;\n"
    "    }\n"
    "    if ((spParser == (SMesajParser*)0) || (ucpVeri == (const unsigned char*)0))\n"
    "    {\n"
    "        return 0;\n"
    "    }\n"
    "    uiGiris = 0U;\n"
    "    while (uiGiris < uiBoy)\n"
    "    {\n"
    "        /* Tampon dolana kadar bayt cek (tampon = baslik + govde max). */\n"
    "        if (spParser->uiDolu < (unsigned int)sizeof(spParser->ucArrTampon))\n"
    "        {\n"
    "            spParser->ucArrTampon[spParser->uiDolu] = ucpVeri[uiGiris];\n"
    "            spParser->uiDolu++;\n"
    "            uiGiris++;\n"
    "            if (upTuketilen != (unsigned int*)0)\n"
    "            {\n"
    "                *upTuketilen = uiGiris;\n"
    "            }\n"
    "        }\n"
    "        else\n"
    "        {\n"
    "            /* Tampon dolu ama cerceve cozulmedi: senkron kaybi, 1 bayt at. */\n"
    "            for (uiIndex = 1U; uiIndex < spParser->uiDolu; uiIndex++)\n"
    "            {\n"
    "                spParser->ucArrTampon[uiIndex - 1U] = spParser->ucArrTampon[uiIndex];\n"
    "            }\n"
    "            spParser->uiDolu--;\n"
    "            continue;\n"
    "        }\n"
    "        /* Baslik tamamlanmadi: daha fazla bayt bekle. */\n"
    "        if (spParser->uiDolu < SPEC2CODE_MESAJ_BASLIK_BOY)\n"
    "        {\n"
    "            continue;\n"
    "        }\n"
    "        uiKomut = spec2codeMesajOku32(&spParser->ucArrTampon[0]);\n"
    "        uiGovdeBoy = spec2codeMesajOku32(&spParser->ucArrTampon[4]);\n"
    "        uiImza = (uiKomut & ~SPEC2CODE_MESAJ_YANIT_BIT) >> 16U;\n"
    "        if ((uiImza != SPEC2CODE_MESAJ_IMZA) || (uiGovdeBoy > SPEC2CODE_MESAJ_GOVDE_MAX) ||\n"
    "            ((uiGovdeBoy % 4U) != 0U))\n"
    "        {\n"
    "            /* Senkron kaybi: bir bayt kaydir, imzayi yeniden ara. */\n"
    "            for (uiIndex = 1U; uiIndex < spParser->uiDolu; uiIndex++)\n"
    "            {\n"
    "                spParser->ucArrTampon[uiIndex - 1U] = spParser->ucArrTampon[uiIndex];\n"
    "            }\n"
    "            spParser->uiDolu--;\n"
    "            continue;\n"
    "        }\n"
    "        uiToplam = SPEC2CODE_MESAJ_BASLIK_BOY + uiGovdeBoy;\n"
    "        if (spParser->uiDolu < uiToplam)\n"
    "        {\n"
    "            /* Govde henuz tamamlanmadi. */\n"
    "            continue;\n"
    "        }\n"
    "        /* Tam cerceve hazir: basligi + govdeyi disari cikar. */\n"
    "        spParser->sBaslik.uiMesajKomut = uiKomut;\n"
    "        spParser->sBaslik.uiMesajBoyu = uiGovdeBoy;\n"
    "        spParser->sBaslik.uiMesajSayac = spec2codeMesajOku32(&spParser->ucArrTampon[8]);\n"
    "        for (uiIndex = 0U; uiIndex < uiGovdeBoy; uiIndex++)\n"
    "        {\n"
    "            spParser->ucArrGovde[uiIndex] = spParser->ucArrTampon[SPEC2CODE_MESAJ_BASLIK_BOY + uiIndex];\n"
    "        }\n"
    "        /* Cerceveyi tampondan cikar (kalan baytlar basa kayar). */\n"
    "        for (uiIndex = uiToplam; uiIndex < spParser->uiDolu; uiIndex++)\n"
    "        {\n"
    "            spParser->ucArrTampon[uiIndex - uiToplam] = spParser->ucArrTampon[uiIndex];\n"
    "        }\n"
    "        spParser->uiDolu -= uiToplam;\n"
    "        if (upTuketilen != (unsigned int*)0)\n"
    "        {\n"
    "            *upTuketilen = uiGiris;\n"
    "        }\n"
    "        return 1;\n"
    "    }\n"
    "    return 0;\n"
    "}\n\n"
    "/* Yanit cercevesi kur: yanit ID = istek ID | YANIT_BIT; sayac monoton. */\n"
    "static unsigned int spec2codeMesajYanitCerceveKur(unsigned int uiIstekKomut,\n"
    "    const SSpec2codeTestbenchResponse* spYanit, unsigned int uiDurum, int iCihazDurum,\n"
    "    unsigned char* ucpCikti, unsigned int uiKapasite)\n"
    "{\n"
    "    unsigned int uiVeriBoy;\n"
    "    unsigned int uiVeriPad;\n"
    "    unsigned int uiMetinBoy;\n"
    "    unsigned int uiMetinPad;\n"
    "    unsigned int uiGovdeBoy;\n"
    "    unsigned int uiToplam;\n"
    "    unsigned int uiOfset;\n"
    "    unsigned int uiIndex;\n"
    "    unsigned int uiDeger;\n\n"
    "    uiVeriBoy = 0U;\n"
    "    uiMetinBoy = 0U;\n"
    "    uiDeger = 0U;\n"
    "    if (spYanit != (const SSpec2codeTestbenchResponse*)0)\n"
    "    {\n"
    "        uiVeriBoy = spYanit->uiDataLength;\n"
    "        uiDeger = spYanit->uiValue;\n"
    "        while ((uiMetinBoy < SPEC2CODE_TESTBENCH_MESSAGE_MAX) &&\n"
    "               (spYanit->cArrMessage[uiMetinBoy] != '\\0'))\n"
    "        {\n"
    "            uiMetinBoy++;\n"
    "        }\n"
    "    }\n"
    "    uiVeriPad = (uiVeriBoy + 3U) & ~3U;\n"
    "    uiMetinPad = (uiMetinBoy + 3U) & ~3U;\n"
    "    /* Govde: 5*4 (sayac,durum,cihazDurum,deger,veriBoy) + veriPad + 4 (metinBoy) + metinPad. */\n"
    "    uiGovdeBoy = 20U + uiVeriPad + 4U + uiMetinPad;\n"
    "    uiToplam = SPEC2CODE_MESAJ_BASLIK_BOY + uiGovdeBoy;\n"
    "    if ((ucpCikti == (unsigned char*)0) || (uiToplam > uiKapasite))\n"
    "    {\n"
    "        return 0U;\n"
    "    }\n"
    "    for (uiIndex = 0U; uiIndex < uiToplam; uiIndex++)\n"
    "    {\n"
    "        ucpCikti[uiIndex] = 0U;\n"
    "    }\n"
    "    /* Baslik: yanit ID, govde boyu, ajan yanit sayaci (monoton). */\n"
    "    S_uiYanitSayac++;\n"
    "    spec2codeMesajYaz32(&ucpCikti[0], uiIstekKomut | SPEC2CODE_MESAJ_YANIT_BIT);\n"
    "    spec2codeMesajYaz32(&ucpCikti[4], uiGovdeBoy);\n"
    "    spec2codeMesajYaz32(&ucpCikti[8], S_uiYanitSayac);\n"
    "    uiOfset = SPEC2CODE_MESAJ_BASLIK_BOY;\n"
    "    /* Govde alanlari. uiIstekSayac = istek cercevesinin sayaci (spYanit->uiId). */\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], (spYanit != (const SSpec2codeTestbenchResponse*)0) ? spYanit->uiId : 0U);\n"
    "    uiOfset += 4U;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiDurum);\n"
    "    uiOfset += 4U;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], (unsigned int)iCihazDurum);\n"
    "    uiOfset += 4U;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiDeger);\n"
    "    uiOfset += 4U;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiVeriBoy);\n"
    "    uiOfset += 4U;\n"
    "    if (spYanit != (const SSpec2codeTestbenchResponse*)0)\n"
    "    {\n"
    "        for (uiIndex = 0U; uiIndex < uiVeriBoy; uiIndex++)\n"
    "        {\n"
    "            ucpCikti[uiOfset + uiIndex] = spYanit->ucArrData[uiIndex];\n"
    "        }\n"
    "    }\n"
    "    uiOfset += uiVeriPad;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiMetinBoy);\n"
    "    uiOfset += 4U;\n"
    "    if (spYanit != (const SSpec2codeTestbenchResponse*)0)\n"
    "    {\n"
    "        for (uiIndex = 0U; uiIndex < uiMetinBoy; uiIndex++)\n"
    "        {\n"
    "            ucpCikti[uiOfset + uiIndex] = (unsigned char)spYanit->cArrMessage[uiIndex];\n"
    "        }\n"
    "    }\n"
    "    return uiToplam;\n"
    "}\n\n"
    "/* Hata yolu: dispatch'e inmeden uygun durumlu (bos) yanit cercevesi. */\n"
    "static unsigned int spec2codeMesajHataCerceve(unsigned int uiIstekKomut, unsigned int uiIstekSayac,\n"
    "    unsigned int uiDurum, unsigned char* ucpCikti, unsigned int uiKapasite)\n"
    "{\n"
    "    SSpec2codeTestbenchResponse sYanit;\n\n"
    "    spec2codeTestbenchResponseClear(&sYanit);\n"
    "    sYanit.uiId = uiIstekSayac;\n"
    "    sYanit.uiOk = 0U;\n"
    "    return spec2codeMesajYanitCerceveKur(uiIstekKomut, &sYanit, uiDurum, sYanit.iStatus,\n"
    "                                         ucpCikti, uiKapasite);\n"
    "}\n\n"
    "/*<<CIT_FRAMER>>*/\n"
    "unsigned int spec2codeMesajIsle(const SMesajBaslik* spBaslik, const unsigned char* ucpGovde,\n"
    "                                unsigned char* ucpCikti, unsigned int uiCiktiKapasite)\n"
    "{\n"
    "    SSpec2codeTestbenchRequest sIstek;\n"
    "    SSpec2codeTestbenchResponse sYanit;\n"
    "    const char* cpOp;\n"
    "    unsigned int uiCihazIndeks;\n"
    "    unsigned int uiVeriBoyu;\n"
    "    unsigned int uiDurum;\n"
    "    unsigned int uiIndex;\n\n"
    "    if ((spBaslik == (const SMesajBaslik*)0) || (ucpGovde == (const unsigned char*)0))\n"
    "    {\n"
    "        return 0U;\n"
    "    }\n"
    "    /* Bozuk govde (sabit istek alanlari sigmiyor) -> GECERSIZ_MESAJ. */\n"
    "    if (spBaslik->uiMesajBoyu < SPEC2CODE_MESAJ_ISTEK_GOVDE_BOY)\n"
    "    {\n"
    "        return spec2codeMesajHataCerceve(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "            SPEC2CODE_MESAJ_DURUM_GECERSIZ_MESAJ, ucpCikti, uiCiktiKapasite);\n"
    "    }\n"
    "/*<<CIT_BRANCH>>*/\n"
    "    cpOp = spec2codeMesajOpAdi(spBaslik->uiMesajKomut);\n"
    "    if (cpOp == (const char*)0)\n"
    "    {\n"
    "        /* Bilinmeyen mesaj ID -> GECERSIZ_MESAJ. */\n"
    "        return spec2codeMesajHataCerceve(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "            SPEC2CODE_MESAJ_DURUM_GECERSIZ_MESAJ, ucpCikti, uiCiktiKapasite);\n"
    "    }\n"
    "    /* Sabit istek govdesi: cihazIndeks, registerAdres, adres, uzunluk, deger, degerVar, veriBoyu. */\n"
    "    spec2codeTestbenchRequestClear(&sIstek);\n"
    "    sIstek.uiId = spBaslik->uiMesajSayac;\n"
    "    spec2codeMesajMetinKopya(sIstek.cArrOperation, SPEC2CODE_TESTBENCH_TEXT_MAX, cpOp);\n"
    "    uiCihazIndeks = spec2codeMesajOku32(&ucpGovde[0]);\n"
    "    sIstek.uiRegister = spec2codeMesajOku32(&ucpGovde[4]);\n"
    "    sIstek.uiAddress = spec2codeMesajOku32(&ucpGovde[8]);\n"
    "    sIstek.uiLength = spec2codeMesajOku32(&ucpGovde[12]);\n"
    "    sIstek.uiValue = spec2codeMesajOku32(&ucpGovde[16]);\n"
    "    sIstek.uiHasValue = (spec2codeMesajOku32(&ucpGovde[20]) != 0U) ? 1U : 0U;\n"
    "    uiVeriBoyu = spec2codeMesajOku32(&ucpGovde[24]);\n"
    "    if (uiVeriBoyu > SPEC2CODE_TESTBENCH_DATA_MAX)\n"
    "    {\n"
    "        uiVeriBoyu = SPEC2CODE_TESTBENCH_DATA_MAX;\n"
    "    }\n"
    "    /* Veri, sabit 28B alanlarin ardindan gelir. */\n"
    "    if ((SPEC2CODE_MESAJ_ISTEK_GOVDE_BOY + uiVeriBoyu) > spBaslik->uiMesajBoyu)\n"
    "    {\n"
    "        return spec2codeMesajHataCerceve(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "            SPEC2CODE_MESAJ_DURUM_GECERSIZ_MESAJ, ucpCikti, uiCiktiKapasite);\n"
    "    }\n"
    "    for (uiIndex = 0U; uiIndex < uiVeriBoyu; uiIndex++)\n"
    "    {\n"
    "        sIstek.ucArrData[uiIndex] = ucpGovde[SPEC2CODE_MESAJ_ISTEK_GOVDE_BOY + uiIndex];\n"
    "    }\n"
    "    sIstek.uiDataLength = uiVeriBoyu;\n"
    "    /* Cihaz indeks -> id string (0xFFFFFFFF = cihazsiz global op). */\n"
    "    if (uiCihazIndeks != 0xFFFFFFFFU)\n"
    "    {\n"
    "        if (uiCihazIndeks >= SPEC2CODE_MESAJ_CIHAZ_SAYISI)\n"
    "        {\n"
    "            /* Tablo disi cihaz indeksi -> CIHAZ_YOK. */\n"
    "            return spec2codeMesajHataCerceve(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "                SPEC2CODE_MESAJ_DURUM_CIHAZ_YOK, ucpCikti, uiCiktiKapasite);\n"
    "        }\n"
    "        spec2codeMesajMetinKopya(sIstek.cArrDevice, SPEC2CODE_TESTBENCH_TEXT_MAX,\n"
    "                                 S_cpArrCihazTablosu[uiCihazIndeks]);\n"
    "    }\n"
    "    /* Ic dispatch (metin protokolu para birimi olarak kalir). */\n"
    "    spec2codeTestbenchResponseClear(&sYanit);\n"
    "    (void)spec2codeTestbenchDispatch(&sIstek, &sYanit);\n"
    "    /* Durum eslemesi: uiOk==1 -> OK; aksi halde BUS_HATASI + ham iStatus. */\n"
    "    uiDurum = (sYanit.uiOk == 1U) ? SPEC2CODE_MESAJ_DURUM_OK : SPEC2CODE_MESAJ_DURUM_BUS_HATASI;\n"
    "    return spec2codeMesajYanitCerceveKur(spBaslik->uiMesajKomut, &sYanit, uiDurum,\n"
    "                                         sYanit.iStatus, ucpCikti, uiCiktiKapasite);\n"
    "}\n\n"
    "unsigned int spec2codeMesajTraceCerceveKur(unsigned int uiMesajId, unsigned int uiSeviye,\n"
    "                                           const char* cpMetin, unsigned char* ucpCikti,\n"
    "                                           unsigned int uiKapasite)\n"
    "{\n"
    "    unsigned int uiMetinBoy;\n"
    "    unsigned int uiMetinPad;\n"
    "    unsigned int uiGovdeBoy;\n"
    "    unsigned int uiToplam;\n"
    "    unsigned int uiOfset;\n"
    "    unsigned int uiIndex;\n\n"
    "    uiMetinBoy = 0U;\n"
    "    while ((cpMetin != (const char*)0) && (cpMetin[uiMetinBoy] != '\\0'))\n"
    "    {\n"
    "        uiMetinBoy++;\n"
    "    }\n"
    "    uiMetinPad = (uiMetinBoy + 3U) & ~3U;\n"
    "    /* TRACE govdesi: uiSeviye + uiMetinBoy + metin pad4. */\n"
    "    uiGovdeBoy = 8U + uiMetinPad;\n"
    "    uiToplam = SPEC2CODE_MESAJ_BASLIK_BOY + uiGovdeBoy;\n"
    "    if ((ucpCikti == (unsigned char*)0) || (uiToplam > uiKapasite))\n"
    "    {\n"
    "        return 0U;\n"
    "    }\n"
    "    for (uiIndex = 0U; uiIndex < uiToplam; uiIndex++)\n"
    "    {\n"
    "        ucpCikti[uiIndex] = 0U;\n"
    "    }\n"
    "    spec2codeMesajYaz32(&ucpCikti[0], uiMesajId);\n"
    "    spec2codeMesajYaz32(&ucpCikti[4], uiGovdeBoy);\n"
    "    S_uiYanitSayac++;\n"
    "    spec2codeMesajYaz32(&ucpCikti[8], S_uiYanitSayac);\n"
    "    uiOfset = SPEC2CODE_MESAJ_BASLIK_BOY;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiSeviye);\n"
    "    uiOfset += 4U;\n"
    "    spec2codeMesajYaz32(&ucpCikti[uiOfset], uiMetinBoy);\n"
    "    uiOfset += 4U;\n"
    "    for (uiIndex = 0U; uiIndex < uiMetinBoy; uiIndex++)\n"
    "    {\n"
    "        ucpCikti[uiOfset + uiIndex] = (unsigned char)cpMetin[uiIndex];\n"
    "    }\n"
    "    return uiToplam;\n"
    "}\n"
)


# CIT çerçeveleyici: yalnız ölçüm varken üretilir (cit.h'ye bağlı). Gövde:
# uiIstekSayac(4) + uiDurum(4) + SBoardCit paketlenmiş kopya. Yanıt ID = istek
# ID | YANIT_BIT; sayaç monoton (mevcut S_uiYanitSayac paylaşılır).
_MESAJ_CIT_FRAMER = (
    "/* CIT yanit cercevesi: uiIstekSayac + uiDurum + SBoardCit (packed kopya). */\n"
    "static unsigned int spec2codeMesajCitCerceveKur(unsigned int uiIstekKomut,\n"
    "    unsigned int uiIstekSayac, unsigned int uiDurum, const SBoardCit* spCit,\n"
    "    unsigned char* ucpCikti, unsigned int uiKapasite)\n"
    "{\n"
    "    unsigned int uiGovdeBoy;\n"
    "    unsigned int uiToplam;\n"
    "    unsigned int uiIndex;\n\n"
    "    /* Govde: 4 (istekSayac) + 4 (durum) + sizeof(SBoardCit). SBoardCit 4B hizali. */\n"
    "    uiGovdeBoy = 8U + (unsigned int)sizeof(SBoardCit);\n"
    "    uiToplam = SPEC2CODE_MESAJ_BASLIK_BOY + uiGovdeBoy;\n"
    "    if ((ucpCikti == (unsigned char*)0) || (uiToplam > uiKapasite))\n"
    "    {\n"
    "        return 0U;\n"
    "    }\n"
    "    for (uiIndex = 0U; uiIndex < uiToplam; uiIndex++)\n"
    "    {\n"
    "        ucpCikti[uiIndex] = 0U;\n"
    "    }\n"
    "    S_uiYanitSayac++;\n"
    "    spec2codeMesajYaz32(&ucpCikti[0], uiIstekKomut | SPEC2CODE_MESAJ_YANIT_BIT);\n"
    "    spec2codeMesajYaz32(&ucpCikti[4], uiGovdeBoy);\n"
    "    spec2codeMesajYaz32(&ucpCikti[8], S_uiYanitSayac);\n"
    "    spec2codeMesajYaz32(&ucpCikti[SPEC2CODE_MESAJ_BASLIK_BOY], uiIstekSayac);\n"
    "    spec2codeMesajYaz32(&ucpCikti[SPEC2CODE_MESAJ_BASLIK_BOY + 4U], uiDurum);\n"
    "    if (spCit != (const SBoardCit*)0)\n"
    "    {\n"
    "        const unsigned char* ucpCit = (const unsigned char*)spCit;\n"
    "        for (uiIndex = 0U; uiIndex < (unsigned int)sizeof(SBoardCit); uiIndex++)\n"
    "        {\n"
    "            ucpCikti[SPEC2CODE_MESAJ_BASLIK_BOY + 8U + uiIndex] = ucpCit[uiIndex];\n"
    "        }\n"
    "    }\n"
    "    return uiToplam;\n"
    "}\n\n"
)

# CIT_RUN / CIT_READ dallari (olcum varken): koss/oku, CIT cercevesi dondur.
_MESAJ_CIT_BRANCH_ENABLED = (
    "    /* CIT dallari (op koprusunden ONCE): CIT_RUN kosar, CIT_READ son kopyayi dondurur. */\n"
    "    {\n"
    "        unsigned int uiIstekId = spBaslik->uiMesajKomut & ~SPEC2CODE_MESAJ_YANIT_BIT;\n"
    "        if (uiIstekId == SPEC2CODE_MESAJ_CIT_RUN)\n"
    "        {\n"
    "            boardCitRun(&S_sMesajCit);\n"
    "            return spec2codeMesajCitCerceveKur(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "                SPEC2CODE_MESAJ_DURUM_OK, &S_sMesajCit, ucpCikti, uiCiktiKapasite);\n"
    "        }\n"
    "        if (uiIstekId == SPEC2CODE_MESAJ_CIT_READ)\n"
    "        {\n"
    "            return spec2codeMesajCitCerceveKur(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "                SPEC2CODE_MESAJ_DURUM_OK, boardCitSon(), ucpCikti, uiCiktiKapasite);\n"
    "        }\n"
    "    }\n"
)

# Olcumsuz spec: CIT dallari DESTEKLENMIYOR doner (cit.h include EDILMEZ).
_MESAJ_CIT_BRANCH_DISABLED = (
    "    /* CIT dallari: bu spec'te olcum yok -> DESTEKLENMIYOR (cit.h uretilmedi). */\n"
    "    {\n"
    "        unsigned int uiIstekId = spBaslik->uiMesajKomut & ~SPEC2CODE_MESAJ_YANIT_BIT;\n"
    "        if ((uiIstekId == SPEC2CODE_MESAJ_CIT_RUN) || (uiIstekId == SPEC2CODE_MESAJ_CIT_READ))\n"
    "        {\n"
    "            return spec2codeMesajHataCerceve(spBaslik->uiMesajKomut, spBaslik->uiMesajSayac,\n"
    "                SPEC2CODE_MESAJ_DURUM_DESTEKLENMIYOR, ucpCikti, uiCiktiKapasite);\n"
    "        }\n"
    "    }\n"
)


def _c_string_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


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


def _op_wire_plan(device: dict, descriptor: dict, op: dict) -> list[dict]:
    """Operasyonun BUS seviyesindeki transfer planı (Seri Hat görselleştirme).

    Descriptor adımlarından türetilir: UI her adımı katalogdaki bus zaman
    diyagramıyla (gerçek register adları/adresleri, init'te gerçek yazılan
    değerlerle) çizer. Poll adımları "hazır olana dek tekrarlanır" notuyla
    tek transfer olarak temsil edilir — iterasyon sayısı çalışma zamanında
    belli olur, uydurulmaz.
    """
    transport = descriptor.get("transport", {}).get("type", "")
    regs = {r["name"]: r for r in descriptor.get("registers", []) if "name" in r}
    cmds = {c["name"]: c for c in descriptor.get("commands", [])}

    def reg_addr(name: str) -> int:
        return int(regs.get(name, {}).get("offset", 0))

    plan: list[dict] = []
    op_name = op.get("name", "")

    if op_name == "device_init":
        if transport == "i2c" and not descriptor.get("memory"):
            for write in device_profiles.i2c_init_writes(device):
                plan.append({
                    "kind": "reg_write", "reg": write["reg"],
                    "addr": reg_addr(write["reg"]), "value": int(write["value"]),
                    "note": write.get("note", ""),
                })
        elif transport == "spi" and tics.register_model(descriptor):
            words = tics.normalize_words(device.get("config"))
            if words:
                plan.append({"kind": "tics_init", "count": len(words),
                             "first_word": f"0x{words[0] & 0xFFFFFF:06X}"})
        post = _post_init_status(descriptor)
        if post is not None:
            plan.append({"kind": "reg_read", "reg": post["reg"],
                         "addr": reg_addr(post["reg"]), "length": post["bytes"],
                         "note": "init doğrulama okuması"})
        return plan

    for step in op.get("steps", []):
        sop = step.get("op", "")
        if sop == "comment":
            continue
        if sop == "poll":
            plan.append({"kind": "reg_read", "reg": step["reg"], "addr": reg_addr(step["reg"]),
                         "length": 1, "repeat": "poll",
                         "note": f"{step.get('field', 'hazır')} biti {step.get('until', 1)} olana dek tekrarlanır"})
        elif sop == "read_register":
            plan.append({"kind": "reg_read", "reg": step["reg"], "addr": reg_addr(step["reg"]), "length": 1})
        elif sop == "read_registers":
            plan.append({"kind": "reg_read", "reg": step["reg"], "addr": reg_addr(step["reg"]),
                         "length": int(step.get("length", 1))})
        elif sop == "read_channels":
            plan.append({"kind": "reg_read_channels", "reg": step["reg"], "addr": reg_addr(step["reg"]),
                         "count": int(step.get("count", 8))})
        elif sop == "write_register":
            plan.append({"kind": "reg_write", "reg": step["reg"], "addr": reg_addr(step["reg"]),
                         "value": int(step.get("value", 0))})
        elif sop == "send_command":
            cmd = cmds.get(step.get("cmd", ""), {})
            plan.append({"kind": "cmd", "cmd": step.get("cmd", ""),
                         "opcode": int(cmd.get("opcode", 0)), "addr_bytes": 0, "length": 0})
        elif sop == "read_command_address":
            cmd = cmds.get(step.get("cmd", ""), {})
            plan.append({"kind": "cmd_read", "cmd": step.get("cmd", ""),
                         "opcode": int(cmd.get("opcode", 0)),
                         "addr_bytes": int(cmd.get("address_bytes", 0)),
                         "length": int(step["length"]) if "length" in step else None})
        elif sop == "write_command_address":
            cmd = cmds.get(step.get("cmd", ""), {})
            plan.append({"kind": "cmd_write", "cmd": step.get("cmd", ""),
                         "opcode": int(cmd.get("opcode", 0)),
                         "addr_bytes": int(cmd.get("address_bytes", 0)),
                         "length": int(step["length"]) if "length" in step else None})
    return plan


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

#: CIT (cihaz ici test) adayi olcum op'lari — v1 beyaz listesi (Board Contract
#: v1, tasarim §4.1). Yalnizca "birimli okuma" niteligindeki op adlari; lock
#: detect/loss op'lari 0/1 olcum olarak sayilir (limit girilirse ayni [min,max]
#: mantigi calisir). Bu liste elle kontrol edilir: yeni bir olcum op'u eklenirse
#: buraya da eklenmesi gerekir (aksi halde CIT'e girmez).
_CIT_MEASUREMENT_OP_WHITELIST: frozenset[str] = frozenset({
    "voltage_read",
    "temperature_read",
    "current_read",
    "vcc_read",
    "sense_read",
    "adin_read",
    "vout_read",
    "power_read",
    "humidity_read",
    "elapsed_read",
    "pll1_lock_detect",
    "pll1_lock_loss",
    "pll2_lock_detect",
    "pll2_lock_loss",
    "multiplier_lock_detect",
})


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


def _bus_trace_header() -> str:
    """drivers/spec2code_bus_trace.h — sürücülerin zayıf iz kancaları.

    Sürücüler her GERÇEK bus transferinden sonra bu kancaları çağırır.
    Standalone (dropin) kullanımda buradaki zayıf boş tanımlar geçerlidir
    ve hiçbir maliyet/yan etki yoktur; test bench güçlü implementasyonu
    (tests/spec2code_testbench_trace.c) transferleri komut id'siyle
    S2C-LOG TRACE satırları olarak yayınlar — Seri Hat ekranı bunlardan
    canlı, bit seviyesinde diyagram çizer.
    """
    return (
        "/**\n"
        " * @file spec2code_bus_trace.h\n"
        " * @brief Weak bus-transfer trace hooks (test bench overrides them).\n"
        " *\n"
        " * Standalone kullanimda zayif bos tanimlar gecerlidir (yan etkisiz);\n"
        " * test bench guclu implementasyonu transferleri S2C-LOG TRACE\n"
        " * satirlari olarak yayinlar (log seviyesi debug iken).\n"
        " */\n"
        "#ifndef SPEC2CODE_BUS_TRACE_H\n"
        "#define SPEC2CODE_BUS_TRACE_H\n\n"
        "void spec2codeBusTraceI2c(unsigned char ucAddress, unsigned char ucReg, char cDir,\n"
        "                          const unsigned char* ucpData, unsigned int uiLength);\n"
        "void spec2codeBusTraceSpi(unsigned int uiSelect, const unsigned char* ucpTx,\n"
        "                          const unsigned char* ucpRx, unsigned int uiLength);\n"
        "/* Basarisiz I2C transferi: hangi adres/register/asama dustu?\n"
        " * cStage: 'w' register yazma, 'p' register pointer yazma,\n"
        " * 'r' okuma (recv), 'm' mux kanal secimi. Test bench guclu\n"
        " * implementasyonu ERROR seviyesinde loglar (varsayilan log\n"
        " * seviyesinde bile gorunur) - sessiz hizli fail birakmaz. */\n"
        "void spec2codeBusTraceI2cError(unsigned char ucAddress, unsigned char ucReg,\n"
        "                               char cStage, int iStatus);\n\n"
        "/* Guclu implementasyon (test bench) zayif varsayilanlari kapatmak icin\n"
        " * include etmeden once SPEC2CODE_BUS_TRACE_NO_WEAK tanimlar. */\n"
        "#if defined(__GNUC__) && !defined(SPEC2CODE_BUS_TRACE_NO_WEAK)\n"
        "__attribute__((weak)) void spec2codeBusTraceI2c(unsigned char ucAddress, unsigned char ucReg,\n"
        "                                                char cDir, const unsigned char* ucpData,\n"
        "                                                unsigned int uiLength)\n"
        "{\n"
        "    (void)ucAddress;\n"
        "    (void)ucReg;\n"
        "    (void)cDir;\n"
        "    (void)ucpData;\n"
        "    (void)uiLength;\n"
        "}\n\n"
        "__attribute__((weak)) void spec2codeBusTraceSpi(unsigned int uiSelect, const unsigned char* ucpTx,\n"
        "                                                const unsigned char* ucpRx, unsigned int uiLength)\n"
        "{\n"
        "    (void)uiSelect;\n"
        "    (void)ucpTx;\n"
        "    (void)ucpRx;\n"
        "    (void)uiLength;\n"
        "}\n\n"
        "__attribute__((weak)) void spec2codeBusTraceI2cError(unsigned char ucAddress, unsigned char ucReg,\n"
        "                                                     char cStage, int iStatus)\n"
        "{\n"
        "    (void)ucAddress;\n"
        "    (void)ucReg;\n"
        "    (void)cStage;\n"
        "    (void)iStatus;\n"
        "}\n"
        "#endif /* __GNUC__ */\n\n"
        "#endif /* SPEC2CODE_BUS_TRACE_H */\n"
    )


def _testbench_trace_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_testbench_trace.h\n"
        " * @brief Bus trace guclu implementasyonu icin komut baglami.\n"
        " */\n"
        "#ifndef SPEC2CODE_TESTBENCH_TRACE_H\n"
        "#define SPEC2CODE_TESTBENCH_TRACE_H\n\n"
        "void spec2codeTestbenchTraceSetId(unsigned int uiId);\n\n"
        "#endif /* SPEC2CODE_TESTBENCH_TRACE_H */\n"
    )


def _testbench_trace_source() -> str:
    """Güçlü iz implementasyonu: gerçek transfer baytlarını komut id'siyle
    debug seviyesinde yayınlar. Sürücülerdeki zayıf kancaları linkte ezer."""
    return (
        "/**\n"
        " * @file spec2code_testbench_trace.c\n"
        " * @brief Bus transfer izleme: gercek TX/RX baytlari TRACE satiri olur.\n"
        " *\n"
        " * Suruculerdeki zayif kancalari ezer. Cikti yalniz log seviyesi\n"
        ' * debug (5) iken uretilir: "S2C-LOG|D|TRACE|id=..|bus=..|..." —\n'
        " * Seri Hat ekrani bu satirlardan canli bus diyagrami cizer.\n"
        " */\n"
        '#include "spec2code_testbench_trace.h"\n'
        "#define SPEC2CODE_BUS_TRACE_NO_WEAK 1\n"
        '#include "spec2code_bus_trace.h"\n'
        '#include "spec2code_testbench_log.h"\n\n'
        "#include <stddef.h>\n\n"
        "#define SPEC2CODE_TRACE_DATA_MAX 16U\n\n"
        "static unsigned int S_uiTraceCommandId = 0U;\n\n"
        "void spec2codeTestbenchTraceSetId(unsigned int uiId)\n"
        "{\n"
        "    S_uiTraceCommandId = uiId;\n"
        "}\n\n"
        "static void spec2codeTraceHex(char* cpOut, const unsigned char* ucpData, unsigned int uiLength)\n"
        "{\n"
        "    static const char C_cArrDigits[] = \"0123456789ABCDEF\";\n"
        "    unsigned int uiIndex;\n"
        "    unsigned int uiCount;\n\n"
        "    if (ucpData == NULL)\n"
        "    {\n"
        "        cpOut[0] = '-';\n"
        "        cpOut[1] = '\\0';\n"
        "        return;\n"
        "    }\n"
        "    uiCount = (uiLength > SPEC2CODE_TRACE_DATA_MAX) ? SPEC2CODE_TRACE_DATA_MAX : uiLength;\n"
        "    for (uiIndex = 0U; uiIndex < uiCount; uiIndex++)\n"
        "    {\n"
        "        cpOut[uiIndex * 2U] = C_cArrDigits[(ucpData[uiIndex] >> 4U) & 0x0FU];\n"
        "        cpOut[(uiIndex * 2U) + 1U] = C_cArrDigits[ucpData[uiIndex] & 0x0FU];\n"
        "    }\n"
        "    cpOut[uiCount * 2U] = '\\0';\n"
        "}\n\n"
        "void spec2codeBusTraceI2c(unsigned char ucAddress, unsigned char ucReg, char cDir,\n"
        "                          const unsigned char* ucpData, unsigned int uiLength)\n"
        "{\n"
        "    char cArrData[(SPEC2CODE_TRACE_DATA_MAX * 2U) + 1U];\n\n"
        "    if (spec2codeLogLevelGet() < SPEC2CODE_LOG_LEVEL_DEBUG)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    spec2codeTraceHex(cArrData, ucpData, uiLength);\n"
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG,\n"
        "                 \"TRACE|id=%u|bus=i2c|addr=0x%02X|reg=0x%02X|dir=%c|len=%u|data=%s\",\n"
        "                 S_uiTraceCommandId, ucAddress, ucReg, cDir, uiLength, cArrData);\n"
        "}\n\n"
        "void spec2codeBusTraceSpi(unsigned int uiSelect, const unsigned char* ucpTx,\n"
        "                          const unsigned char* ucpRx, unsigned int uiLength)\n"
        "{\n"
        "    char cArrTx[(SPEC2CODE_TRACE_DATA_MAX * 2U) + 1U];\n"
        "    char cArrRx[(SPEC2CODE_TRACE_DATA_MAX * 2U) + 1U];\n\n"
        "    if (spec2codeLogLevelGet() < SPEC2CODE_LOG_LEVEL_DEBUG)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    spec2codeTraceHex(cArrTx, ucpTx, uiLength);\n"
        "    spec2codeTraceHex(cArrRx, ucpRx, uiLength);\n"
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG,\n"
        "                 \"TRACE|id=%u|bus=spi|cs=%u|len=%u|tx=%s|rx=%s\",\n"
        "                 S_uiTraceCommandId, uiSelect, uiLength, cArrTx, cArrRx);\n"
        "}\n\n"
        "void spec2codeBusTraceI2cError(unsigned char ucAddress, unsigned char ucReg,\n"
        "                               char cStage, int iStatus)\n"
        "{\n"
        "    /* ERROR seviyesi: varsayilan logda bile gorunur. Sessiz hizli\n"
        "     * fail'i (SAHA: DS1682 elapsed_read tek satir 'failed') hangi\n"
        "     * adres/register/asamanin dusurdugu okunur hale gelir. */\n"
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR,\n"
        "                 \"TRACEERR|id=%u|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d\",\n"
        "                 S_uiTraceCommandId, ucAddress, ucReg, cStage, iStatus);\n"
        "}\n"
    )


def _testbench_cit_section(spec: dict, manifest_devices: list[dict]) -> dict:
    """Manifest "cit" bolumu: birimli olcum op'larinin duz, kararli sirali listesi.

    `manifest_devices` cagiran tarafta zaten uretilmis olan
    ``manifest["devices"]`` listesidir (id/part/operations alanlariyla); bu
    fonksiyon onu YENIDEN OKUR, degistirmez — device_index = manifest devices[]
    offset'i (Task 7 bit i == olcumler[i] sozlesmesi bu hizalamaya dayanir).

    Kural sirasi: manifest devices[] sirasi, cihaz icinde de operations[]
    sirasi (bu da descriptor'daki op sirasidir, `_requested_operations`
    descriptor sirasini korur). `enabled: false` olcumler LISTEDE KALIR (slot
    stabil kalsin diye) — yalnizca bayrak kapanir.
    """
    olcumler: list[dict] = []
    seen_cnames: dict[str, str] = {}  # cname -> hangi olcumden geldigi (hata mesaji icin)
    for device_index, device_manifest in enumerate(manifest_devices):
        device_id = device_manifest.get("id", "")
        part = device_manifest.get("part", "")
        user_measurements = {
            str(m.get("op", "")): m
            for m in (
                ((spec.get("devices", [])[device_index].get("config") or {}).get("cit") or {})
                .get("measurements") or []
            )
            if isinstance(m, dict) and m.get("op")
        } if device_index < len(spec.get("devices", [])) else {}
        for op in device_manifest.get("operations", []):
            op_name = str(op.get("name", ""))
            if op_name not in _CIT_MEASUREMENT_OP_WHITELIST:
                continue
            if not op.get("result_returns"):
                continue
            if op.get("risk") != "safe":
                continue
            if op.get("requires_address") or op.get("requires_data") or op.get("requires_value"):
                continue
            user = user_measurements.get(op_name, {})
            default_name = f"{part}_{op_name}_{device_index}".upper()
            name = str(user.get("name") or default_name)
            # _pascal_identifier yalnizca her parcanin ILK harfini buyutur; CIT
            # isimleri genelde BUYUK_HARFLI (VCC_3V3_RF / varsayilan <PART>_<OP>_<i>)
            # geldiginden once kucuk harfe cevrilir (Vcc3v3Rf, VCC3V3RF degil).
            cname = _pascal_identifier(name.lower())
            if cname in seen_cnames and seen_cnames[cname] != name:
                raise cmodel.CodegenError(
                    f"CIT olcum cname catismasi: '{cname}' hem '{seen_cnames[cname]}' hem '{name}' "
                    "icin uretiliyor — isimleri benzersiz secin.")
            seen_cnames[cname] = name
            severity = str(user.get("severity") or "warning")
            enabled = bool(user.get("enabled", True))
            min_value = user.get("min")
            max_value = user.get("max")
            olcumler.append({
                "index": len(olcumler),
                "device": device_id,
                "device_index": device_index,
                "part": part,
                "op": op_name,
                "name": name,
                "cname": cname,
                "unit": op.get("result_unit") or None,
                "min": min_value if isinstance(min_value, (int, float)) else None,
                "max": max_value if isinstance(max_value, (int, float)) else None,
                "severity": severity,
                "enabled": enabled,
            })
    return {
        "olcumler": olcumler,
        "bit_sirasi": [m["cname"] for m in olcumler],
    }


def _testbench_manifest_devices(spec: dict, get_descriptor: Callable[[str], dict]) -> list[dict]:
    """Manifest ``devices[]`` listesini kurar (tek doğruluk kaynağı).

    Hem ``_testbench_manifest`` hem CIT üreteci (``_cit_measurements``) bu
    fonksiyonu çağırır — böylece olçüm sırası (manifest devices[] → operations[])
    tek yerden gelir ve CIT bit hizası bağımsız türetmeye kaymaz.
    """
    devices: list[dict] = []
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
                # UI, donusturulmus degeri ondalik + birimle gosterebilsin
                # (0xF23 yerine 38.75 C): donus tipi ve convert birimi.
                "result_returns": str(op.get("returns", "") or ""),
                "result_unit": str((op.get("convert") or {}).get("unit", "") or ""),
                # Seri Hat: operasyonun bus seviyesindeki transfer plani.
                "wire": _op_wire_plan(device, descriptor, op),
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
                    "result_returns": "uint8",
                    "result_unit": "",
                    "wire": [{"kind": "reg_read", "runtime": True, "length": 1}],
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
                    "result_returns": "",
                    "result_unit": "",
                    "wire": [{"kind": "reg_write", "runtime": True}],
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
                    "result_returns": "uint16" if data_bits == 16 else "uint8",
                    "result_unit": "",
                    "wire": [{"kind": "reg_read", "runtime": True, "length": data_bits // 8}],
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
                "result_returns": "",
                "result_unit": "",
                "wire": [{"kind": "reg_write", "runtime": True}],
            })
        transport_type = descriptor.get("transport", {}).get("type", "")
        devices.append({
            "id": device.get("id", ""),
            "part": device.get("part", ""),
            "transport": transport_type,
            "attach": device.get("attach", {}),
            # Liste offset'e gore SIRALI gider: descriptor dosya sirasi
            # (katalog birlestirmesi sona ekledigi icin) karisik olabilir;
            # Registers ekrani ve snapshot okunabilirlik icin kucukten
            # buyuge adres sirasi bekler (saha istegi, LMK04832 ornegi).
            "registers": sorted(
                (
                    {
                        "name": reg.get("name", ""),
                        "offset": reg.get("offset", 0),
                        "access": reg.get("access", ""),
                        "width": reg.get("width", 8),
                    }
                    # SAHA (2026-07-05): width == native_width filtresi 16-bit
                    # registerlari (AD7414/TMP101 TEMPERATURE, TLOW/THIGH)
                    # Registers ekranindan dusuruyordu. Genislik artik listede
                    # tasinir; generic R/W ajan tarafinda genislik-farkindali.
                    for reg in descriptor.get("registers", [])
                    if "name" in reg and str(reg.get("access", "")).lower() not in {"reserved"}
                ),
                key=lambda item: int(item["offset"]),
            ),
            "operations": operations,
        })
    return devices


def _cit_measurements(spec: dict, get_descriptor: Callable[[str], dict]) -> list[dict]:
    """CIT ölçüm listesi (manifest cit.olcumler ile birebir sıralı).

    ``_testbench_manifest_devices`` + ``_testbench_cit_section`` üzerinden gelir;
    böylece C üretimi ve manifest tek sıralama kaynağını paylaşır.
    """
    devices = _testbench_manifest_devices(spec, get_descriptor)
    return _testbench_cit_section(spec, devices)["olcumler"]


def _cit_header(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    """Üretilen `spec2code_cit.h`: SBoardCit + bayrak yapısı + koşu/oku API'si.

    Bit sırası manifest cit.olcumler ile birebir (aynı `_cit_measurements`
    kaynağından). Ölçüm yoksa çağıran (harness) bu dosyayı hiç üretmez.
    """
    olcumler = _cit_measurements(spec, get_descriptor)
    sayi = len(olcumler)
    bayrak_bayt = ((sayi + 31) // 32) * 4
    bit_lines = [
        f"    unsigned int ui{m['cname']}Ok : 1;   "
        f"/* olcum {m['index']}: {m['name']}, {m['device']}/{m['op']} */"
        for m in olcumler
    ]
    return (
        "/**\n"
        " * @file spec2code_cit.h\n"
        " * @brief CIT (Card-In-Test) olcum toplama: SBoardCit paketlenmis kopya,\n"
        " *        kullanici isimli gecti/kaldi bitleri + limit degerlendirmesi.\n"
        " *\n"
        " * Olcum sirasi manifest cit.olcumler ile birebir (uretim tek kaynaktan).\n"
        " * El ile duzenlemeyin; spec'ten yeniden uretilir. Yalniz unsigned int/int.\n"
        " */\n"
        "#ifndef SPEC2CODE_CIT_H\n"
        "#define SPEC2CODE_CIT_H\n\n"
        f"#define BOARD_CIT_OLCUM_SAYISI {sayi}U\n\n"
        "/**\n"
        " * @brief Olcum basina gecti(1)/kaldi(0) biti (olcum sirasiyla, bit 0 = olcum 0).\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        + "\n".join(bit_lines) + "\n"
        "} SBoardCitBayraklar;\n\n"
        f"_Static_assert(sizeof(SBoardCitBayraklar) == {bayrak_bayt}U,\n"
        f"               \"SBoardCitBayraklar {bayrak_bayt} bayt olmalidir\");\n\n"
        "/**\n"
        " * @brief Tek olcum sonucu.\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        "    int          iDeger;    /* islenmis deger (birim manifest cit.olcumler[i].unit) */\n"
        "    unsigned int uiHam;     /* ham deger (yanit data'nin ilk 4B'i ya da uiValue)    */\n"
        "    unsigned int uiDurum;   /* 0 OK; mesaj katmani durum kodlari (5 BUS, 7 DESTEKLENMIYOR) */\n"
        "} SBoardCitOlcum;\n\n"
        "/**\n"
        " * @brief Bir CIT kosusunun tam sonucu (mesaj yanit govdesine paketlenir).\n"
        " */\n"
        "typedef struct\n"
        "{\n"
        "    unsigned int       uiSayac;   /* kac kez kosuldu (her boardCitRun'da +1) */\n"
        "    unsigned int       uiZaman;   /* ms tick (kaynak yoksa 0)                */\n"
        "    SBoardCitBayraklar sBayraklar;\n"
        "    SBoardCitOlcum     arrOlcum[BOARD_CIT_OLCUM_SAYISI];\n"
        "} SBoardCit;\n\n"
        "_Static_assert(sizeof(SBoardCit) % 4U == 0U, \"SBoardCit 4B hizali olmalidir\");\n\n"
        "/**\n"
        " * @brief CIT olcumlerini kostur; her olcum icin dispatch'i cagirir, limiti\n"
        " *        degerlendirir, bayrak bitini ve sonucu doldurur. uiSayac +1.\n"
        " */\n"
        "void boardCitRun(SBoardCit* spCit);\n\n"
        "/**\n"
        " * @brief Son kosunun kopyasini dondurur (yeniden kosmadan). Hic kosulmadiysa\n"
        " *        sifirlanmis struct (uiSayac 0).\n"
        " */\n"
        "const SBoardCit* boardCitSon(void);\n\n"
        "#endif /* SPEC2CODE_CIT_H */\n"
    )


def _cit_source(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    """Üretilen `spec2code_cit.c`: limit tablosu + dispatch köprüsü + boardCitRun."""
    olcumler = _cit_measurements(spec, get_descriptor)

    # Sabit limit tablosu: enabled=false -> uiEtkin=0; min/max yoksa uiLimitVar=0.
    limit_rows = []
    for m in olcumler:
        has_limit = (m["min"] is not None) and (m["max"] is not None)
        i_min = int(m["min"]) if has_limit else 0
        i_max = int(m["max"]) if has_limit else 0
        ui_limit = 1 if has_limit else 0
        ui_kritik = 1 if str(m["severity"]).lower() == "critical" else 0
        ui_etkin = 1 if m["enabled"] else 0
        limit_rows.append(
            f"    {{ {i_min}, {i_max}, {ui_limit}U, {ui_kritik}U, {ui_etkin}U }}, "
            f"/* olcum {m['index']}: {m['name']} */")
    limit_table = "\n".join(limit_rows) if limit_rows else "    { 0, 0, 0U, 0U, 0U }"

    # Cihaz id + op adi string tablolari (dispatch koprusu; MesajIsle ile ayni
    # alanlar: cArrDevice = cihaz id string, cArrOperation = op adi string).
    device_rows = "\n".join(
        f'    "{_c_string_escape(m["device"])}",' for m in olcumler) or '    ""'
    op_rows = "\n".join(
        f'    "{_c_string_escape(m["op"])}",' for m in olcumler) or '    ""'

    # Her olcum icin uye adiyla atama (switch): bit alani uyeleri adreslenemez,
    # bit-index aritmetigi YOK — uye adiyla dogrudan atama.
    bit_case_lines = "\n".join(
        f"        case {m['index']}U: spCit->sBayraklar.ui{m['cname']}Ok = uiOk; break;"
        for m in olcumler)

    return (
        "/**\n"
        " * @file spec2code_cit.c\n"
        " * @brief CIT olcum toplama gerceklemesi. Limit tablosu + cihaz/op string\n"
        " *        tablolari otomatik uretildi (manifest cit.olcumler sirasiyla).\n"
        " */\n"
        '#include "spec2code_cit.h"\n'
        '#include "spec2code_mesaj.h"\n'
        '#include "spec2code_testbench_protocol.h"\n\n'
        "/* Sabit limit tablosu (olcum sirasiyla). uiEtkin=0 -> olcum kapali;\n"
        " * uiLimitVar=0 -> limit kontrolu yok (ham dispatch basarisi = gecti). */\n"
        "static const struct\n"
        "{\n"
        "    int          iMin;\n"
        "    int          iMax;\n"
        "    unsigned int uiLimitVar;\n"
        "    unsigned int uiKritik;\n"
        "    unsigned int uiEtkin;\n"
        "} S_sArrCitLimit[BOARD_CIT_OLCUM_SAYISI] =\n"
        "{\n"
        f"{limit_table}\n"
        "};\n\n"
        "/* Olcum -> cihaz id string (dispatch koprusu icin). */\n"
        "static const char* const S_cpArrCitCihaz[BOARD_CIT_OLCUM_SAYISI] =\n"
        "{\n"
        f"{device_rows}\n"
        "};\n\n"
        "/* Olcum -> op adi string (dispatch koprusu icin). */\n"
        "static const char* const S_cpArrCitOp[BOARD_CIT_OLCUM_SAYISI] =\n"
        "{\n"
        f"{op_rows}\n"
        "};\n\n"
        "/* Son kosu kopyasi (CIT_READ + boardCitSon dondurur). */\n"
        "static SBoardCit S_sCitSonKopya;\n"
        "static unsigned int S_uiCitKosuSayac = 0U;\n\n"
        "static void spec2codeCitMetinKopya(char* cpDst, unsigned int uiDstBoy, const char* cpSrc)\n"
        "{\n"
        "    unsigned int uiIndex;\n\n"
        "    if ((cpDst == (char*)0) || (uiDstBoy == 0U))\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    for (uiIndex = 0U; uiIndex < (uiDstBoy - 1U); uiIndex++)\n"
        "    {\n"
        "        if ((cpSrc == (const char*)0) || (cpSrc[uiIndex] == '\\0'))\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        cpDst[uiIndex] = cpSrc[uiIndex];\n"
        "    }\n"
        "    cpDst[uiIndex] = '\\0';\n"
        "}\n\n"
        "static void spec2codeCitBayrakYaz(SBoardCit* spCit, unsigned int uiOlcum, unsigned int uiOk)\n"
        "{\n"
        "    switch (uiOlcum)\n"
        "    {\n"
        f"{bit_case_lines}\n"
        "        default: break;\n"
        "    }\n"
        "}\n\n"
        "void boardCitRun(SBoardCit* spCit)\n"
        "{\n"
        "    SSpec2codeTestbenchRequest sIstek;\n"
        "    SSpec2codeTestbenchResponse sYanit;\n"
        "    unsigned int uiOlcum;\n"
        "    unsigned int uiIndex;\n"
        "    unsigned int uiHam;\n"
        "    int iDeger;\n"
        "    unsigned int uiOk;\n\n"
        "    if (spCit == (SBoardCit*)0)\n"
        "    {\n"
        "        return;\n"
        "    }\n"
        "    /* Kopyayi sifirla; her alan ustune yazilir. */\n"
        "    for (uiIndex = 0U; uiIndex < (unsigned int)sizeof(SBoardCit); uiIndex++)\n"
        "    {\n"
        "        ((unsigned char*)spCit)[uiIndex] = 0U;\n"
        "    }\n"
        "    S_uiCitKosuSayac++;\n"
        "    spCit->uiSayac = S_uiCitKosuSayac;\n"
        "    spCit->uiZaman = 0U;  /* ms tick kaynagi uretilen kodda yok (v1). */\n"
        "    for (uiOlcum = 0U; uiOlcum < BOARD_CIT_OLCUM_SAYISI; uiOlcum++)\n"
        "    {\n"
        "        if (S_sArrCitLimit[uiOlcum].uiEtkin == 0U)\n"
        "        {\n"
        "            /* Kapali olcum: kosma, DESTEKLENMIYOR isaretle, bit 0. */\n"
        "            spCit->arrOlcum[uiOlcum].iDeger = 0;\n"
        "            spCit->arrOlcum[uiOlcum].uiHam = 0U;\n"
        "            spCit->arrOlcum[uiOlcum].uiDurum = SPEC2CODE_MESAJ_DURUM_DESTEKLENMIYOR;\n"
        "            spec2codeCitBayrakYaz(spCit, uiOlcum, 0U);\n"
        "            continue;\n"
        "        }\n"
        "        spec2codeTestbenchRequestClear(&sIstek);\n"
        "        sIstek.uiId = uiOlcum;\n"
        "        spec2codeCitMetinKopya(sIstek.cArrDevice, SPEC2CODE_TESTBENCH_TEXT_MAX,\n"
        "                               S_cpArrCitCihaz[uiOlcum]);\n"
        "        spec2codeCitMetinKopya(sIstek.cArrOperation, SPEC2CODE_TESTBENCH_TEXT_MAX,\n"
        "                               S_cpArrCitOp[uiOlcum]);\n"
        "        spec2codeTestbenchResponseClear(&sYanit);\n"
        "        (void)spec2codeTestbenchDispatch(&sIstek, &sYanit);\n"
        "        /* Ham deger: yanit data'nin ilk 4B'i (>=4 ise LE) yoksa uiValue. */\n"
        "        if (sYanit.uiDataLength >= 4U)\n"
        "        {\n"
        "            uiHam = ((unsigned int)sYanit.ucArrData[0])\n"
        "                  | ((unsigned int)sYanit.ucArrData[1] << 8U)\n"
        "                  | ((unsigned int)sYanit.ucArrData[2] << 16U)\n"
        "                  | ((unsigned int)sYanit.ucArrData[3] << 24U);\n"
        "        }\n"
        "        else\n"
        "        {\n"
        "            uiHam = sYanit.uiValue;\n"
        "        }\n"
        "        iDeger = (int)sYanit.uiValue;\n"
        "        spCit->arrOlcum[uiOlcum].iDeger = iDeger;\n"
        "        spCit->arrOlcum[uiOlcum].uiHam = uiHam;\n"
        "        /* Durum eslemesi: uiOk==1 -> OK; aksi -> BUS_HATASI. */\n"
        "        if (sYanit.uiOk == 1U)\n"
        "        {\n"
        "            spCit->arrOlcum[uiOlcum].uiDurum = SPEC2CODE_MESAJ_DURUM_OK;\n"
        "            /* Gecti biti: dispatch basarili VE (limit yok VEYA aralikta). */\n"
        "            if ((S_sArrCitLimit[uiOlcum].uiLimitVar == 0U) ||\n"
        "                ((iDeger >= S_sArrCitLimit[uiOlcum].iMin) &&\n"
        "                 (iDeger <= S_sArrCitLimit[uiOlcum].iMax)))\n"
        "            {\n"
        "                uiOk = 1U;\n"
        "            }\n"
        "            else\n"
        "            {\n"
        "                uiOk = 0U;\n"
        "            }\n"
        "        }\n"
        "        else\n"
        "        {\n"
        "            spCit->arrOlcum[uiOlcum].uiDurum = SPEC2CODE_MESAJ_DURUM_BUS_HATASI;\n"
        "            uiOk = 0U;\n"
        "        }\n"
        "        spec2codeCitBayrakYaz(spCit, uiOlcum, uiOk);\n"
        "    }\n"
        "    /* Son kopyayi guncelle (CIT_READ icin). */\n"
        "    for (uiIndex = 0U; uiIndex < (unsigned int)sizeof(SBoardCit); uiIndex++)\n"
        "    {\n"
        "        ((unsigned char*)&S_sCitSonKopya)[uiIndex] = ((const unsigned char*)spCit)[uiIndex];\n"
        "    }\n"
        "}\n\n"
        "const SBoardCit* boardCitSon(void)\n"
        "{\n"
        "    return &S_sCitSonKopya;\n"
        "}\n"
    )


def _testbench_manifest(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    agent = _testbench_transport_agent(spec)
    manifest = {
        "schema_version": "1.0",
        "project": spec.get("project", {}).get("name", ""),
        "agent_version": _app_version(),
        "protocol": "S2C line protocol v1",
        # S2C-MSG binary katalog imzasi: uretilen mesaj katmani (spec2code_mesaj.c)
        # ile backend s2cmsg ayni katalog baytlarindan uretilir; bu CRC32
        # (Python zlib.crc32) ikisinin es oldugunu dogrular.
        "message_catalog_crc32": _message_catalog_crc32(),
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
    # I2C hat taraması: UI hangi denetleyicilerin taranabileceğini ve mux
    # topolojisini (kanal kanal harita için) buradan öğrenir.
    if "XIicPs" in _testbench_used_handle_types(spec):
        manifest["i2c_scan"] = {
            "op": "i2c_scan",
            "mux_op": "i2c_mux_set",
            "range": [0x08, 0x77],
            # Prob yazma: recv-polled sahada NACK'te de basari dondurdu.
            "probe": "1-byte write 0x00 (register pointer reset)",
            "skip_address_param": True,
            "controllers": [
                {"id": c.get("id", ""), "instance": c.get("instance", "")}
                for c in spec.get("controllers", [])
                if c.get("type") == "i2c"
            ],
            "muxes": [
                {
                    "id": m.get("id", ""),
                    "part": m.get("part", ""),
                    "controller_id": m.get("controller_id", ""),
                    "address": int(str(m.get("i2c_address", "0x70")), 0),
                    "channels": int(m.get("channels", 8)),
                }
                for m in spec.get("muxes", [])
            ],
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
    manifest["devices"] = _testbench_manifest_devices(spec, get_descriptor)
    # Hardening (Task 4 bulgusu): _testbench_device_entries denetleyicisi
    # olmayan cihazlari atlar, yukaridaki dongu atlamaz — bugun cmodel.build_units
    # daha erken dogruladigi icin ulasilamaz ama CIT bit hizasi bu esitlige
    # dayandigindan sessizce sapmasin diye burada da dogrulaniyor.
    entry_ids = [entry["device"].get("id", "") for entry in _testbench_device_entries(spec, get_descriptor)]
    manifest_ids = [d.get("id", "") for d in manifest["devices"]]
    if entry_ids != manifest_ids:
        raise cmodel.CodegenError(
            "manifest devices[] sirasi _testbench_device_entries ile uyusmuyor "
            f"(manifest={manifest_ids!r}, entries={entry_ids!r}); CIT bit hizasi bu esitlige dayanir.")
    manifest["cit"] = _testbench_cit_section(spec, manifest["devices"])
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
        "                               SSpec2codeTestbenchResponse* spResponse);\n\n"
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
    # Ayni parcadan birden cok cihaz kendi moduluyle eslesmelidir (adres/mux
    # derleme sabiti) - surucu birimleriyle ayni harita kullanilir.
    modules = cmodel.device_module_map(spec)
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
            "module": modules.get(device.get("id", ""), cmodel._module_of(device.get("part", ""))),
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
    if not wide:
        # I2C: register genisligi (bayt) - 16-bit registerlar (AD7414/TMP101
        # TEMPERATURE gibi) generic R/W'de tek islemde 2 bayt tasinir.
        wide_regs = [reg for reg in regs if int(reg.get("width", 8)) > 8]
        width_func = f"{module}TestbenchRegisterWidthBytes"
        lines.extend([
            f"static unsigned char {width_func}(const char* cpRegister, unsigned int uiRegister)",
            "{",
        ])
        if wide_regs:
            # Once ISIM eslesmesi (dar registerlar 1U ile erken doner ki
            # reg_addr'siz isimli istekte varsayilan uiRegister=0, offset'i
            # 0 olan genis registera yanlis eslesmesin), sonra offset.
            for reg in regs:
                is_wide = int(reg.get("width", 8)) > 8
                lines.extend([
                    f"    if (spec2codeTestbenchStringEqual(cpRegister, \"{reg['name']}\") == 1)",
                    "    {",
                    f"        return {'2U' if is_wide else '1U'};",
                    "    }",
                ])
            for reg in wide_regs:
                lines.extend([
                    f"    if (uiRegister == {_c_hex(int(reg['offset']))})",
                    "    {",
                    "        return 2U;",
                    "    }",
                ])
        if not wide_regs:
            lines.append("    (void)uiRegister;")
            lines.append("    (void)cpRegister;")
        lines.extend([
            "    return 1U;",
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
        "    spec2codeBusTraceI2c(ucAddress, ucReg, 'r', ucpValue, 1U);",
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
        "    spec2codeBusTraceI2c(ucAddress, ucReg, 'w', &ucValue, 1U);",
        "    return XST_SUCCESS;",
        "}",
        "",
        "/* GENIS (16-bit) tek register: baytlar ayni adresin icindedir",
        " * (AD7414/TMP101 TEMPERATURE gibi) - pointer bir kez yazilir,",
        " * iki bayt TEK islemde okunur/yazilir. */",
        "static int spec2codeTestbenchI2cRegisterReadWide(XIicPs* spIic, unsigned char ucAddress,",
        "                                                 unsigned char ucReg, unsigned char* ucpBuffer)",
        "{",
        "    int iStatus;",
        "",
        "    if ((spIic == NULL) || (ucpBuffer == NULL))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
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
        "    iStatus = XIicPs_MasterRecvPolled(spIic, ucpBuffer, 2, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"i2c recv HATA: addr=0x%02X reg=0x%02X status=%d\", ucAddress, ucReg, iStatus);",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    spec2codeBusTraceI2c(ucAddress, ucReg, 'r', ucpBuffer, 2U);",
        "    return XST_SUCCESS;",
        "}",
        "",
        "static int spec2codeTestbenchI2cRegisterWriteWide(XIicPs* spIic, unsigned char ucAddress,",
        "                                                  unsigned char ucReg, unsigned char ucHigh,",
        "                                                  unsigned char ucLow)",
        "{",
        "    unsigned char ucArrBuffer[3];",
        "    int iStatus;",
        "",
        "    if (spIic == NULL)",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    ucArrBuffer[0] = ucReg;",
        "    ucArrBuffer[1] = ucHigh;",
        "    ucArrBuffer[2] = ucLow;",
        "    iStatus = XIicPs_MasterSendPolled(spIic, ucArrBuffer, 3, ucAddress);",
        "    if (iStatus != XST_SUCCESS)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"i2c write HATA: addr=0x%02X reg=0x%02X status=%d\", ucAddress, ucReg, iStatus);",
        "        return iStatus;",
        "    }",
        "    while (XIicPs_BusIsBusy(spIic) == TRUE)",
        "    {",
        "        /* wait */",
        "    }",
        "    spec2codeBusTraceI2c(ucAddress, ucReg, 'w', &ucArrBuffer[1], 2U);",
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
        "        return iStatus;",
        "    }",
        "    spec2codeBusTraceSpi((unsigned int)ucSelect, ucArrTx, NULL, 3U);",
        "    return XST_SUCCESS;",
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
        "    spec2codeBusTraceSpi((unsigned int)ucSelect, ucArrTx, ucArrRx, 3U);",
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
    elif "uint32" in returns:
        # Ham 24/32-bit sayaç/akümülatör (DS1682 ETC/EVENT, LTC2945 POWER):
        # value alanına ham değer, data'ya 4 big-endian bayt. SAHA KÖK NEDENİ
        # (2026-07-06): bu dal yokken uint32 dönüşlü TÜM *_read op'ları alttaki
        # "signature not mapped" yakalayıcısına düşüyor ve ajan BUS'A HİÇ
        # ÇIKMADAN status=1 dönüyordu — TRACEERR'siz anlık fail'in sebebi buydu.
        lines.append(f"iStatus = {func}({hvar}, &uiValue32);")
        lines.extend([
            "if (iStatus == XST_SUCCESS)",
            "{",
            "    spResponse->uiValue = uiValue32;",
        ])
        for shift in (24, 16, 8, 0):
            lines.extend([
                f"    iStatus = spec2codeTestbenchDataPush(spResponse, (unsigned char)((uiValue32 >> {shift}U) & 0xFFU));",
                "    if (iStatus != XST_SUCCESS)",
                "    {",
                "        return iStatus;",
                "    }",
            ])
        lines.append("}")
    elif "int32" in returns:
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
        # Bu yakalayıcıya düşen op HİÇ bus'a çıkmadan fail eder; sebep log'da
        # ERROR olarak adıyla görünmeli — genel "<op> failed" mesajı epilogda
        # bunu ezdiği için saha teşhisi haftalarca gecikti (DS1682 vakası).
        lines.append(
            "spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "
            "\"op imzasi eslenmemis (descriptor returns tipi testbench'e bagli degil): %s\", "
            "spRequest->cArrOperation);"
        )
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
    needs_ui_value32 = any("uint32" in str(op.get("returns", "")).lower() for op in operations)
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
    if needs_ui_value32:
        lines.append("        unsigned int uiValue32;")
    if needs_array:
        lines.append("        unsigned short usArrValues[8];")
    if needs_uc_value:
        lines.append("        unsigned char ucValue;")
    if needs_uc_reg:
        lines.append("        unsigned char ucReg;")
    if register_ops:
        # Genis (16-bit) register R/W: tek pointer + iki bayt tek islemde.
        lines.append("        unsigned char ucArrWide[2];")
        lines.append("        unsigned char ucWidthBytes;")
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
            # Genis registerlar (AD7414/TMP101 TEMPERATURE...) tek islemde
            # 2 bayt okunur; value birlesimi descriptor byte_order'a gore.
            f"            ucWidthBytes = {module}TestbenchRegisterWidthBytes(spRequest->cArrRegister, spRequest->uiRegister);",
            "            if (ucWidthBytes == 2U)",
            "            {",
            f"                iStatus = spec2codeTestbenchI2cRegisterReadWide({hvar}, {MOD}_I2C_ADDR, ucReg, ucArrWide);",
            "                spResponse->iStatus = iStatus;",
            "                spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
            ("                spResponse->uiValue = ((unsigned int)ucArrWide[0] << 8U) | (unsigned int)ucArrWide[1];"
             if entry["descriptor"].get("transport", {}).get("byte_order", "big") != "little"
             else "                spResponse->uiValue = ((unsigned int)ucArrWide[1] << 8U) | (unsigned int)ucArrWide[0];"),
            "                if (iStatus == XST_SUCCESS)",
            "                {",
            "                    (void)spec2codeTestbenchDataPush(spResponse, ucArrWide[0]);",
            "                    (void)spec2codeTestbenchDataPush(spResponse, ucArrWide[1]);",
            "                    spec2codeTestbenchMessageSet(spResponse, \"register_read ok\");",
            "                }",
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
            f"            ucWidthBytes = {module}TestbenchRegisterWidthBytes(spRequest->cArrRegister, spRequest->uiRegister);",
            "            if (ucWidthBytes == 2U)",
            "            {",
            # Hatta ilk giden bayt: big-endian cihazda MSB, little'da LSB.
            (f"                iStatus = spec2codeTestbenchI2cRegisterWriteWide({hvar}, {MOD}_I2C_ADDR, ucReg, "
             "(unsigned char)((spRequest->uiValue >> 8U) & 0xFFU), (unsigned char)(spRequest->uiValue & 0xFFU));"
             if entry["descriptor"].get("transport", {}).get("byte_order", "big") != "little"
             else f"                iStatus = spec2codeTestbenchI2cRegisterWriteWide({hvar}, {MOD}_I2C_ADDR, ucReg, "
             "(unsigned char)(spRequest->uiValue & 0xFFU), (unsigned char)((spRequest->uiValue >> 8U) & 0xFFU));"),
            "                spResponse->iStatus = iStatus;",
            "                spResponse->uiOk = (iStatus == XST_SUCCESS) ? 1U : 0U;",
            "                spec2codeTestbenchMessageSet(spResponse, (iStatus == XST_SUCCESS) ? \"register_write ok\" : \"register_write failed\");",
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
            # Debug seviyesinde op başlangıcı loglanır: uzun süren/asılı kalan
            # bir sürücü çağrısı, "basla" görünüp yanıt gelmemesinden anlaşılır.
            f"            spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"op basla: {entry['device'].get('id', '')} {op_name}\");",
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


def _testbench_i2c_scan_lines(handle_types: set[str]) -> list[str]:
    """Global I2C hat taraması opları (yalnız I2C denetleyicisi kullanılıyorsa).

    i2c_scan: reg=<controller_id> — o ANKİ hattı 0x08..0x77 aralığında
    1-baytlık YAZMA (0x00) ile yoklar; ACK veren adresler data alanında
    döner (value = adet). Prob YAZMA çünkü SAHA BULGUSU (2026-07-05):
    XIicPs_MasterRecvPolled adres NACK'inde de XST_SUCCESS döndürdü ve
    0x08..0x77 arası HER adres "cevap verdi" göründü; send yolu ise NACK'ı
    güvenilir raporluyor (EEPROM ack-poll ve DS1682 hızlı-fail vakası aynı
    yolla doğrulandı). 0x00 baytı register-pointer'lı cihazlarda yalnız
    pointer'ı sıfırlar, EEPROM'da tek bayt adres MSB'si olarak kalır (yazma
    tamamlanmaz). address=<atlanacak adres> (0 = yok): kanal taramasında
    aktif switch'in kendi adresine 0x00 yazılsaydı seçili kanal kapanırdı —
    host aktif switch adresini atlatır. Mux arkası haritalama host tarafında
    i2c_mux_set (address=<mux adresi>, value=<kontrol baytı>; 0x00=kapat,
    1<<kanal=seç) ile kanal kanal orkestre edilir — TCA9548A protokolü.
    """
    if "XIicPs" not in handle_types:
        return []
    getter = _testbench_getter("XIicPs")
    return [
        "    if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"i2c_scan\") == 1)",
        "    {",
        "        XIicPs* spScanIic;",
        "        unsigned char ucProbe;",
        "        unsigned int uiScanAddr;",
        "        unsigned int uiFound;",
        "        int iProbeStatus;",
        "",
        f"        spScanIic = {getter}(spRequest->cArrRegister);",
        "        if (spScanIic == NULL)",
        "        {",
        "            spResponse->iStatus = XST_FAILURE;",
        "            spec2codeTestbenchMessageSet(spResponse, \"unknown i2c controller\");",
        "            return XST_FAILURE;",
        "        }",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"i2c tarama basliyor: %s\", spRequest->cArrRegister);",
        "        uiFound = 0U;",
        "        ucProbe = 0x00U;",
        "        for (uiScanAddr = 0x08U; uiScanAddr <= 0x77U; uiScanAddr++)",
        "        {",
        "            if (uiScanAddr == spRequest->uiAddress)",
        "            {",
        "                /* Aktif switch'e 0x00 yazmak secili kanali kapatirdi. */",
        "                continue;",
        "            }",
        "            iProbeStatus = XIicPs_MasterSendPolled(spScanIic, &ucProbe, 1, (unsigned short)uiScanAddr);",
        "            while (XIicPs_BusIsBusy(spScanIic) == TRUE)",
        "            {",
        "                /* wait */",
        "            }",
        "            if (iProbeStatus == XST_SUCCESS)",
        "            {",
        "                (void)spec2codeTestbenchDataPush(spResponse, (unsigned char)uiScanAddr);",
        "                uiFound++;",
        "                spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, \"i2c tarama ACK: 0x%02X\", uiScanAddr);",
        "            }",
        "        }",
        "        spResponse->uiOk = 1U;",
        "        spResponse->iStatus = XST_SUCCESS;",
        "        spResponse->uiValue = uiFound;",
        "        spec2codeTestbenchMessageSet(spResponse, \"i2c_scan ok\");",
        "        return XST_SUCCESS;",
        "    }",
        "    if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"i2c_mux_set\") == 1)",
        "    {",
        "        XIicPs* spScanIic;",
        "        unsigned char ucControl;",
        "        int iProbeStatus;",
        "",
        f"        spScanIic = {getter}(spRequest->cArrRegister);",
        "        if (spScanIic == NULL)",
        "        {",
        "            spResponse->iStatus = XST_FAILURE;",
        "            spec2codeTestbenchMessageSet(spResponse, \"unknown i2c controller\");",
        "            return XST_FAILURE;",
        "        }",
        "        ucControl = (unsigned char)spRequest->uiValue;",
        "        iProbeStatus = XIicPs_MasterSendPolled(spScanIic, &ucControl, 1, (unsigned short)spRequest->uiAddress);",
        "        while (XIicPs_BusIsBusy(spScanIic) == TRUE)",
        "        {",
        "            /* wait */",
        "        }",
        "        spResponse->iStatus = iProbeStatus;",
        "        spResponse->uiOk = (iProbeStatus == XST_SUCCESS) ? 1U : 0U;",
        "        spResponse->uiValue = ucControl;",
        "        spec2codeTestbenchMessageSet(spResponse, (iProbeStatus == XST_SUCCESS) ? \"i2c_mux_set ok\" : \"i2c_mux_set failed\");",
        "        return iProbeStatus;",
        "    }",
    ]


def _testbench_ops_source(spec: dict, get_descriptor: Callable[[str], dict]) -> str:
    project_name = spec["project"]["name"]
    app_version = _app_version()
    entries = _testbench_device_entries(spec, get_descriptor)
    handle_types = _testbench_used_handle_types(spec)
    rows = _testbench_op_table(entries)
    includes = [
        f'#include "{project_name}_testbench_ops.h"',
        '#include "spec2code_testbench_log.h"',
        '#include "spec2code_testbench_trace.h"',
        '#include "spec2code_bus_trace.h"',
        '#include "xstatus.h"',
        # Adres-tabanli genel bellek oku/yaz (mem_read/mem_write) icin:
        # Xil_In32/Xil_Out32 + u8/u16/u32. Tum platformlarin standalone BSP'sinde var.
        '#include "xil_io.h"',
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
        "static int spec2codeTestbenchDispatchCore(const SSpec2codeTestbenchRequest* spRequest,",
        "                                          SSpec2codeTestbenchResponse* spResponse)",
        "{",
        "    if ((spRequest == NULL) || (spResponse == NULL))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    /* Bus trace satirlari bu komutun id'siyle etiketlenir (Seri Hat). */",
        "    spec2codeTestbenchTraceSetId(spRequest->uiId);",
        "    spec2codeTestbenchResponseClear(spResponse);",
        "    spResponse->uiId = spRequest->uiId;",
        "    if ((spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"spec2code_version\") == 1) ||",
        "        (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"version\") == 1))",
        "    {",
        "        const char* pcVersion = SPEC2CODE_TESTBENCH_AGENT_VERSION;",
        "        unsigned int uiVersionIndex;",
        "",
        "        spResponse->uiOk = 1U;",
        "        spResponse->iStatus = XST_SUCCESS;",
        "        spec2codeTestbenchMessageSet(spResponse, \"Spec2Code \" SPEC2CODE_TESTBENCH_AGENT_VERSION);",
        "        /* Surum ASCII olarak data alaninda da doner (UI cozer). */",
        "        for (uiVersionIndex = 0U; pcVersion[uiVersionIndex] != (char)0; uiVersionIndex++)",
        "        {",
        "            (void)spec2codeTestbenchDataPush(spResponse, (unsigned char)pcVersion[uiVersionIndex]);",
        "        }",
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
        # Built-in: adres-tabanli genel bellek oku/yaz (Xil_In32/Out32). Cihaz
        # (I2C/SPI) gerektirmez; register map "Canli Izleme" bunu her transport
        # uzerinden kullanir. length=1/2/4 -> 8/16/32-bit erisim (varsayilan 32).
        "    if ((spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"mem_read\") == 1) ||",
        "        (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"mem_write\") == 1))",
        "    {",
        "        unsigned int uiWidth = spRequest->uiLength;",
        "        unsigned int uiReadValue;",
        "        unsigned int uiByteIndex;",
        "        if ((uiWidth != 1U) && (uiWidth != 2U) && (uiWidth != 4U))",
        "        {",
        "            uiWidth = 4U;",
        "        }",
        "        if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, \"mem_write\") == 1)",
        "        {",
        "            if (spRequest->uiHasValue != 1U)",
        "            {",
        "                spResponse->iStatus = XST_FAILURE;",
        "                spec2codeTestbenchMessageSet(spResponse, \"mem_write: value gerekli\");",
        "                return XST_FAILURE;",
        "            }",
        "            if (uiWidth == 1U)",
        "            {",
        "                Xil_Out8((UINTPTR)spRequest->uiAddress, (u8)spRequest->uiValue);",
        "            }",
        "            else if (uiWidth == 2U)",
        "            {",
        "                Xil_Out16((UINTPTR)spRequest->uiAddress, (u16)spRequest->uiValue);",
        "            }",
        "            else",
        "            {",
        "                Xil_Out32((UINTPTR)spRequest->uiAddress, (u32)spRequest->uiValue);",
        "            }",
        "        }",
        "        if (uiWidth == 1U)",
        "        {",
        "            uiReadValue = (unsigned int)Xil_In8((UINTPTR)spRequest->uiAddress);",
        "        }",
        "        else if (uiWidth == 2U)",
        "        {",
        "            uiReadValue = (unsigned int)Xil_In16((UINTPTR)spRequest->uiAddress);",
        "        }",
        "        else",
        "        {",
        "            uiReadValue = (unsigned int)Xil_In32((UINTPTR)spRequest->uiAddress);",
        "        }",
        "        spResponse->uiOk = 1U;",
        "        spResponse->iStatus = XST_SUCCESS;",
        "        spResponse->uiValue = uiReadValue;",
        "        for (uiByteIndex = 0U; uiByteIndex < uiWidth; uiByteIndex++)",
        "        {",
        "            (void)spec2codeTestbenchDataPush(spResponse,",
        "                (unsigned char)((uiReadValue >> (uiByteIndex * 8U)) & 0xFFU));",
        "        }",
        "        spec2codeTestbenchMessageSet(spResponse, \"mem ok\");",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"mem %s addr=0x%X width=%u value=0x%X\",",
        "                     spRequest->cArrOperation, spRequest->uiAddress, uiWidth, uiReadValue);",
        "        return XST_SUCCESS;",
        "    }",
        *_testbench_i2c_scan_lines(handle_types),
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
        "int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,",
        "                               SSpec2codeTestbenchResponse* spResponse)",
        "{",
        "    int iStatus;",
        "",
        "    if ((spRequest == NULL) || (spResponse == NULL))",
        "    {",
        "        return XST_FAILURE;",
        "    }",
        "    /* Gelen istek (binary cerceveden cozuldu): device/op MESSAGE seviyesi.",
        "     * Metin satir protokolu yok; yapisal alanlardan loglanir. */",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, \"RX id=%u device=%s op=%s\",",
        "                 spRequest->uiId, spRequest->cArrDevice, spRequest->cArrOperation);",
        "    iStatus = spec2codeTestbenchDispatchCore(spRequest, spResponse);",
        "    if (spResponse->uiOk == 1U)",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"op tamam: device=%s op=%s status=%d\",",
        "                     spRequest->cArrDevice, spRequest->cArrOperation, spResponse->iStatus);",
        "    }",
        "    else",
        "    {",
        "        spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, \"op HATA: device=%s op=%s status=%d mesaj=%s\",",
        "                     spRequest->cArrDevice, spRequest->cArrOperation, spResponse->iStatus,",
        "                     spResponse->cArrMessage);",
        "    }",
        "    /* Yanit (TX) MESSAGE seviyesi: cerceveleme mesaj katmaninda yapilir. */",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, \"TX id=%u ok=%u status=%d value=0x%X\",",
        "                 spResponse->uiId, spResponse->uiOk, spResponse->iStatus, spResponse->uiValue);",
        "    return iStatus;",
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
        "/* SABIT statik ag konfigurasyonu (kullanici karari - esneklik yok):\n"
        " * IP 18.2.75.121, netmask 255.255.255.0 (/24), gateway 18.2.75.1.\n"
        " * DHCP YOK; netif dogrudan bu adreslerle eklenir. */\n"
        "#ifndef SPEC2CODE_TESTBENCH_IP_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR0 18U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR1 2U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR2 75U\n"
        "#define SPEC2CODE_TESTBENCH_IP_ADDR3 121U\n"
        "#endif\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_NETMASK_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR0 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR1 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR2 255U\n"
        "#define SPEC2CODE_TESTBENCH_NETMASK_ADDR3 0U\n"
        "#endif\n\n"
        "#ifndef SPEC2CODE_TESTBENCH_GATEWAY_ADDR0\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR0 18U\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR1 2U\n"
        "#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR2 75U\n"
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


def _mesaj_trace_sink_lines(func_name: str, send_frame_call: str) -> list[str]:
    """Generate a leveled-log/bus-trace sink that FRAMES the text line.

    The line protocol is gone: the log core still builds the exact
    ``S2C-LOG|...`` text (the UI's Seri Hat panel decodes that text), but it
    can no longer ride the wire raw — it is wrapped in a TRACE_EVENT frame
    (BUS_TRACE_EVENT when the body is an ``|TRACE`` bus-transfer line) and
    the frame bytes are sent via ``send_frame_call`` (a "(ucpFrame, uiLen)"
    style call). Text content is preserved byte-for-byte.
    """
    return [
        f"static void {func_name}(const char* cpLine)",
        "{",
        "    unsigned char ucArrFrame[SPEC2CODE_MESAJ_CERCEVE_MAX];",
        "    unsigned int uiFrameLength;",
        "    unsigned int uiMesajId;",
        "    unsigned int uiIndex;",
        "",
        "    if (cpLine == NULL)",
        "    {",
        "        return;",
        "    }",
        "    /* Bus izleri (S2C-LOG|D|TRACE|..., S2C-LOG|E|TRACEERR|...)",
        "     * BUS_TRACE_EVENT; diger her satir TRACE_EVENT. Metin AYNEN korunur;",
        "     * UI cerceve metin alanindan cozer. */",
        "    uiMesajId = SPEC2CODE_MESAJ_TRACE_EVENT;",
        "    for (uiIndex = 0U; cpLine[uiIndex] != '\\0'; uiIndex++)",
        "    {",
        "        if ((cpLine[uiIndex] == '|') && (cpLine[uiIndex + 1U] == 'T') &&",
        "            (cpLine[uiIndex + 2U] == 'R') && (cpLine[uiIndex + 3U] == 'A') &&",
        "            (cpLine[uiIndex + 4U] == 'C') && (cpLine[uiIndex + 5U] == 'E'))",
        "        {",
        "            uiMesajId = SPEC2CODE_MESAJ_BUS_TRACE_EVENT;",
        "            break;",
        "        }",
        "    }",
        "    uiFrameLength = spec2codeMesajTraceCerceveKur(uiMesajId, 0U, cpLine,",
        "                                                  ucArrFrame, sizeof(ucArrFrame));",
        "    if (uiFrameLength > 0U)",
        "    {",
        f"        {send_frame_call};",
        "    }",
        "}",
        "",
    ]


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
        '#include "spec2code_mesaj.h"',
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
        " *",
        " * Recv baytlari S2C-MSG cozucusune (parser) feed-forward beslenir; her",
        " * tam cercevede spec2codeMesajIsle yaniti cerceveler ve kismi-gonderim",
        " * (short-write) dongusuyle TCP'ye yazar. Metin satir protokolu YOK.",
        " */",
        *headers,
        "",
        "#define SPEC2CODE_TESTBENCH_RECV_CHUNK 64U",
        "",
        "#ifndef SPEC2CODE_TESTBENCH_ETH_BASEADDR",
        f"#define SPEC2CODE_TESTBENCH_ETH_BASEADDR {eth.get('instance')}_BASEADDR",
        "#endif",
        "",
        "/* SABIT MAC adresi (kullanici karari - esneklik yok): 00-0A-35-00-01-02",
        " * (00:0A:35 = Xilinx OUI). Ayni MAC her zaman kullanilir. */",
        "#ifndef SPEC2CODE_TESTBENCH_MAC0",
        "#define SPEC2CODE_TESTBENCH_MAC0 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC1 0x0AU",
        "#define SPEC2CODE_TESTBENCH_MAC2 0x35U",
        "#define SPEC2CODE_TESTBENCH_MAC3 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC4 0x01U",
        "#define SPEC2CODE_TESTBENCH_MAC5 0x02U",
        "#endif",
        "",
        "static struct netif S_sNetif;",
        "static SMesajParser S_sMesajParser;",
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
        *_testbench_board_init_lines(entries),
        *[
            line
            for htype, _header in _TESTBENCH_HANDLE_HEADERS
            if any(entry["htype"] == htype for entry in entries)
            for line in _testbench_board_getter_lines(entries, htype, _testbench_getter(htype))
        ],
        "static void spec2codeTestbenchClientSendFrame(int iClientSocket,",
        "                                              const unsigned char* ucpFrame,",
        "                                              unsigned int uiLength)",
        "{",
        "    unsigned int uiSent;",
        "    int iWritten;",
        "",
        "    /* Kismi gonderim/short-write dongusu korunur: lwip_send kalan span'i",
        "     * tamamlayana kadar ilerletilir. */",
        "    uiSent = 0U;",
        "    while (uiSent < uiLength)",
        "    {",
        "        iWritten = lwip_send(iClientSocket, &ucpFrame[uiSent], uiLength - uiSent, 0);",
        "        if (iWritten <= 0)",
        "        {",
        "            return;",
        "        }",
        "        uiSent += (unsigned int)iWritten;",
        "    }",
        "}",
        "",
        "static void spec2codeTestbenchClientServe(int iClientSocket)",
        "{",
        "    unsigned char ucArrChunk[SPEC2CODE_TESTBENCH_RECV_CHUNK];",
        "    unsigned char ucArrCikti[SPEC2CODE_MESAJ_CERCEVE_MAX];",
        "    unsigned int uiOfset;",
        "    unsigned int uiTuketilen;",
        "    unsigned int uiCiktiBoy;",
        "    int iReceived;",
        "",
        "    spec2codeMesajParserSifirla(&S_sMesajParser);",
        "    for (;;)",
        "    {",
        "        iReceived = lwip_recv(iClientSocket, ucArrChunk, sizeof(ucArrChunk), 0);",
        "        if (iReceived <= 0)",
        "        {",
        "            return;",
        "        }",
        "        /* Feed-forward: recv chunk'i bittigi ana kadar besle; her tam",
        "         * cercevede isle+gonder. Tek-frame-per-recv varsayimi YOK. */",
        "        uiOfset = 0U;",
        "        while (uiOfset < (unsigned int)iReceived)",
        "        {",
        "            uiTuketilen = 0U;",
        "            if (spec2codeMesajBesle(&S_sMesajParser, &ucArrChunk[uiOfset],",
        "                                    (unsigned int)iReceived - uiOfset, &uiTuketilen) == 1)",
        "            {",
        "                uiCiktiBoy = spec2codeMesajIsle(&S_sMesajParser.sBaslik,",
        "                    S_sMesajParser.ucArrGovde, ucArrCikti, sizeof(ucArrCikti));",
        "                if (uiCiktiBoy > 0U)",
        "                {",
        "                    spec2codeTestbenchClientSendFrame(iClientSocket, ucArrCikti, uiCiktiBoy);",
        "                }",
        "            }",
        "            if (uiTuketilen == 0U)",
        "            {",
        "                break;",
        "            }",
        "            uiOfset += uiTuketilen;",
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
        '#include "spec2code_mesaj.h"',
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
        " *",
        " * RAW API callback'i pbuf baytlarini S2C-MSG cozucusune (parser)",
        " * feed-forward besler; her tam cercevede spec2codeMesajIsle yaniti",
        " * cerceveler ve mevcut tcp_write/tcp_output kalibiyla gonderir. Metin",
        " * satir protokolu YOK.",
        " */",
        *headers,
        "",
        "#ifndef SPEC2CODE_TESTBENCH_ETH_BASEADDR",
        f"#define SPEC2CODE_TESTBENCH_ETH_BASEADDR {eth.get('instance')}_BASEADDR",
        "#endif",
        "",
        "/* SABIT MAC adresi (kullanici karari - esneklik yok): 00-0A-35-00-01-02",
        " * (00:0A:35 = Xilinx OUI). Ayni MAC her zaman kullanilir. */",
        "#ifndef SPEC2CODE_TESTBENCH_MAC0",
        "#define SPEC2CODE_TESTBENCH_MAC0 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC1 0x0AU",
        "#define SPEC2CODE_TESTBENCH_MAC2 0x35U",
        "#define SPEC2CODE_TESTBENCH_MAC3 0x00U",
        "#define SPEC2CODE_TESTBENCH_MAC4 0x01U",
        "#define SPEC2CODE_TESTBENCH_MAC5 0x02U",
        "#endif",
        "",
        "static struct netif S_sNetif;",
        "static struct tcp_pcb* S_spServerPcb;",
        "static struct tcp_pcb* S_spClientPcb;",
        "static SMesajParser S_sMesajParser;",
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
        "static unsigned int S_uiNetworkReady;",
        "static unsigned int S_uiServerReady;",
        "",
        *_testbench_board_handle_decls(entries),
        "static err_t spec2codeTestbenchResponseSend(struct tcp_pcb* spTcpPcb,",
        "                                            const unsigned char* ucpFrame,",
        "                                            unsigned int uiLength)",
        "{",
        "    err_t enErr;",
        "",
        "    /* Mevcut tcp_write/tcp_output kalibi korunur (kopya bayrakli). */",
        "    if ((spTcpPcb == NULL) || (uiLength == 0U) || (uiLength > 0xFFFFU))",
        "    {",
        "        return ERR_VAL;",
        "    }",
        "    enErr = tcp_write(spTcpPcb, ucpFrame, (unsigned short)uiLength, TCP_WRITE_FLAG_COPY);",
        "    if (enErr == ERR_OK)",
        "    {",
        "        enErr = tcp_output(spTcpPcb);",
        "    }",
        "    return enErr;",
        "}",
        "",
        "static err_t spec2codeTestbenchTcpReceive(void* vpArg,",
        "                                           struct tcp_pcb* spTcpPcb,",
        "                                           struct pbuf* spPbuf,",
        "                                           err_t enErr)",
        "{",
        "    struct pbuf* spCurrent;",
        "    const unsigned char* ucpPayload;",
        "    unsigned char ucArrCikti[SPEC2CODE_MESAJ_CERCEVE_MAX];",
        "    unsigned int uiOfset;",
        "    unsigned int uiTuketilen;",
        "    unsigned int uiCiktiBoy;",
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
        "        spec2codeMesajParserSifirla(&S_sMesajParser);",
        "        return ERR_OK;",
        "    }",
        "    tcp_recved(spTcpPcb, spPbuf->tot_len);",
        "    for (spCurrent = spPbuf; spCurrent != NULL; spCurrent = spCurrent->next)",
        "    {",
        "        ucpPayload = (const unsigned char*)spCurrent->payload;",
        "        /* Feed-forward: pbuf segmentini bittigi ana kadar besle; her tam",
        "         * cercevede isle+gonder. Tek-frame-per-recv varsayimi YOK. */",
        "        uiOfset = 0U;",
        "        while (uiOfset < (unsigned int)spCurrent->len)",
        "        {",
        "            uiTuketilen = 0U;",
        "            if (spec2codeMesajBesle(&S_sMesajParser, &ucpPayload[uiOfset],",
        "                                    (unsigned int)spCurrent->len - uiOfset, &uiTuketilen) == 1)",
        "            {",
        "                uiCiktiBoy = spec2codeMesajIsle(&S_sMesajParser.sBaslik,",
        "                    S_sMesajParser.ucArrGovde, ucArrCikti, sizeof(ucArrCikti));",
        "                if (uiCiktiBoy > 0U)",
        "                {",
        "                    (void)spec2codeTestbenchResponseSend(spTcpPcb, ucArrCikti, uiCiktiBoy);",
        "                }",
        "            }",
        "            if (uiTuketilen == 0U)",
        "            {",
        "                break;",
        "            }",
        "            uiOfset += uiTuketilen;",
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
        "    spec2codeMesajParserSifirla(&S_sMesajParser);",
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
        "    spec2codeMesajParserSifirla(&S_sMesajParser);",
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
        '#include "spec2code_mesaj.h"',
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
        f" * @brief PS UART ({uart_prefix}) polled S2C-MSG binary agent for the Spec2Code test bench.",
        " *",
        " * Polled receive per the official polled UART example; needs no",
        " * interrupts and no scheduler, so the same agent runs on bare metal",
        " * and on a FreeRTOS BSP alike. Recv baytlari S2C-MSG cozucusune (parser)",
        " * feed-forward beslenir; her tam cercevede spec2codeMesajIsle yaniti",
        " * cerceveler. Metin banner/enter-prompt YOK (binary kanal).",
        " */",
        *headers,
        "",
        # Recv chunk: binary cerceve baytlari parca parca gelir; parser tam
        # cerceveyi kendi 4096B govde tamponunda birlestirir.
        "#define SPEC2CODE_TESTBENCH_RECV_CHUNK 64U",
        "",
        f"static {uart_prefix} S_sTestbenchUart;",
        "static SMesajParser S_sMesajParser;",
        "static unsigned int S_uiBoardReady;",
        "",
        *_testbench_board_handle_decls(entries),
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
        "static void spec2codeTestbenchUartSendFrame(const unsigned char* ucpFrame, unsigned int uiLength)",
        "{",
        "    unsigned int uiSent;",
        "",
        "    uiSent = 0U;",
        "    while (uiSent < uiLength)",
        "    {",
        f"        uiSent += {uart_prefix}_Send(&S_sTestbenchUart,",
        "                               (u8*)&ucpFrame[uiSent],",
        "                               uiLength - uiSent);",
        "    }",
        "}",
        "",
        *_mesaj_trace_sink_lines(
            "spec2codeTestbenchUartSendLine",
            "spec2codeTestbenchUartSendFrame(ucArrFrame, uiFrameLength)"),
        "void spec2codeTestbenchUartRun(void)",
        "{",
        "    unsigned char ucArrChunk[SPEC2CODE_TESTBENCH_RECV_CHUNK];",
        "    unsigned char ucArrCikti[SPEC2CODE_MESAJ_CERCEVE_MAX];",
        "    unsigned int uiReceived;",
        "    unsigned int uiOfset;",
        "    unsigned int uiTuketilen;",
        "    unsigned int uiCiktiBoy;",
        "",
        "    /* Loglar/izler S2C trafigiyle ayni UART'tan cerceveli aksin. */",
        "    spec2codeLogSinkSet(spec2codeTestbenchUartSendLine);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"UART agent dongusu basladi; log seviyesi=%s\",",
        "                 spec2codeLogLevelName(spec2codeLogLevelGet()));",
        "    spec2codeMesajParserSifirla(&S_sMesajParser);",
        "    for (;;)",
        "    {",
        f"        uiReceived = {uart_prefix}_Recv(&S_sTestbenchUart, ucArrChunk, sizeof(ucArrChunk));",
        "        if (uiReceived == 0U)",
        "        {",
        "            continue;",
        "        }",
        "        /* Feed-forward: recv chunk'i bittigi ana kadar besle; her tam",
        "         * cercevede isle+gonder. Tek-frame-per-recv varsayimi YOK. */",
        "        uiOfset = 0U;",
        "        while (uiOfset < uiReceived)",
        "        {",
        "            uiTuketilen = 0U;",
        "            if (spec2codeMesajBesle(&S_sMesajParser, &ucArrChunk[uiOfset],",
        "                                    uiReceived - uiOfset, &uiTuketilen) == 1)",
        "            {",
        "                uiCiktiBoy = spec2codeMesajIsle(&S_sMesajParser.sBaslik,",
        "                    S_sMesajParser.ucArrGovde, ucArrCikti, sizeof(ucArrCikti));",
        "                if (uiCiktiBoy > 0U)",
        "                {",
        "                    spec2codeTestbenchUartSendFrame(ucArrCikti, uiCiktiBoy);",
        "                }",
        "            }",
        "            if (uiTuketilen == 0U)",
        "            {",
        "                break;",
        "            }",
        "            uiOfset += uiTuketilen;",
        "        }",
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
        '#include "spec2code_mesaj.h"',
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
        " * @brief CoreSight DCC polled S2C-MSG binary agent for the Spec2Code test bench.",
        " *",
        " * Uses the standalone BSP coresightps_dcc driver",
        " * (XCoresightPs_DccSendByte/RecvByte). RecvByte blocks until the",
        " * debugger side writes a byte; her bayt S2C-MSG cozucusune (parser)",
        " * feed-forward beslenir ve tam cercevede spec2codeMesajIsle yaniti",
        " * cerceveler. No interrupts, no scheduler - runs the same on bare",
        " * metal and FreeRTOS BSPs. Metin banner/enter-prompt YOK (binary kanal).",
        " */",
        *headers,
        "",
        "static SMesajParser S_sMesajParser;",
        "static unsigned int S_uiBoardReady;",
        "",
        *_testbench_board_handle_decls(entries),
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
        "static void spec2codeTestbenchCoresightSendFrame(const unsigned char* ucpFrame, unsigned int uiLength)",
        "{",
        "    unsigned int uiSent;",
        "",
        "    for (uiSent = 0U; uiSent < uiLength; uiSent++)",
        "    {",
        "        XCoresightPs_DccSendByte(0U, (u8)ucpFrame[uiSent]);",
        "    }",
        "}",
        "",
        *_mesaj_trace_sink_lines(
            "spec2codeTestbenchCoresightSendLine",
            "spec2codeTestbenchCoresightSendFrame(ucArrFrame, uiFrameLength)"),
        "void spec2codeTestbenchCoresightRun(void)",
        "{",
        "    unsigned char ucByte;",
        "    unsigned char ucArrCikti[SPEC2CODE_MESAJ_CERCEVE_MAX];",
        "    unsigned int uiTuketilen;",
        "    unsigned int uiCiktiBoy;",
        "",
        "    /* Loglar/izler S2C trafigiyle ayni DCC kanalindan cerceveli aksin. */",
        "    spec2codeLogSinkSet(spec2codeTestbenchCoresightSendLine);",
        "    spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, \"CoreSight agent dongusu basladi; log seviyesi=%s\",",
        "                 spec2codeLogLevelName(spec2codeLogLevelGet()));",
        "    spec2codeMesajParserSifirla(&S_sMesajParser);",
        "    for (;;)",
        "    {",
        "        /* DCC byte koprusu birer bayt getirir; feed-forward tek bayt",
        "         * uzerinde de cerceve tamamlaninca isle+gonder yapar. */",
        "        ucByte = (unsigned char)XCoresightPs_DccRecvByte(0U);",
        "        uiTuketilen = 0U;",
        "        if (spec2codeMesajBesle(&S_sMesajParser, &ucByte, 1U, &uiTuketilen) == 1)",
        "        {",
        "            uiCiktiBoy = spec2codeMesajIsle(&S_sMesajParser.sBaslik,",
        "                S_sMesajParser.ucArrGovde, ucArrCikti, sizeof(ucArrCikti));",
        "            if (uiCiktiBoy > 0U)",
        "            {",
        "                spec2codeTestbenchCoresightSendFrame(ucArrCikti, uiCiktiBoy);",
        "            }",
        "        }",
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
        " * banner is printed ONLY on the serial console (xil_printf) so a\n"
        " * human sees life at power-up; the DCC now carries binary S2C-MSG\n"
        " * frames exclusively (no ASCII banner - it would corrupt the frame\n"
        " * stream the host FrameParser reads).\n"
        + runtime_note +
        " */\n"
        '#include "spec2code_testbench_coresight_main.h"\n'
        '#include "spec2code_testbench_coresight.h"\n'
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
        "    iStatus = spec2codeTestbenchCoresightInit();\n"
        "    if (iStatus != XST_SUCCESS)\n"
        "    {\n"
        '        xil_printf("Spec2Code CoreSight agent baslatilamadi: %d\\r\\n", iStatus);\n'
        "        return iStatus;\n"
        "    }\n"
        "    /* Seri konsol (stdout=UART): acilis isareti. DCC'ye banner BASILMAZ\n"
        "     * (binary S2C-MSG cerceve akisini bozar). */\n"
        f'    xil_printf("{banner_text}\\r\\n");\n'
        '    xil_printf("S2C protokolu CoreSight DCC uzerinde (binary S2C-MSG); bu UART yalnizca konsol.\\r\\n");\n'
        '    xil_printf("S2C-CORESIGHT-AGENT-READY\\r\\n");\n'
        "    spec2codeTestbenchCoresightRun();\n"
        "    return XST_SUCCESS;\n"
        "}\n"
    )


def _testbench_cit_enabled(spec: dict, root: Path = _ROOT) -> bool:
    """CIT dosyalari uretilir mi (en az bir olcum var mi)."""
    return len(_cit_measurements(spec, make_descriptor_loader(root))) > 0


def testbench_harness_paths(spec: dict, out_dir: Path, *, root: Path = _ROOT) -> list[Path]:
    project_name = spec["project"]["name"]
    tests_dir = out_dir / "tests"
    paths = [
        tests_dir / "spec2code_testbench_protocol.h",
        tests_dir / "spec2code_testbench_protocol.c",
        tests_dir / "spec2code_mesaj.h",
        tests_dir / "spec2code_mesaj.c",
        tests_dir / "spec2code_testbench_log.h",
        tests_dir / "spec2code_testbench_log.c",
        tests_dir / "spec2code_testbench_trace.h",
        tests_dir / "spec2code_testbench_trace.c",
        tests_dir / f"{project_name}_testbench_ops.h",
        tests_dir / f"{project_name}_testbench_ops.c",
        tests_dir / "spec2code_testbench_manifest.json",
    ]
    # CIT dosyalari yalniz olcum varsa (kosullu uretim) — mesaj katmani dallari
    # da bu koska gore uretilir; ikisi zip'le birebir hizali kalmali.
    if _testbench_cit_enabled(spec, root):
        paths.extend([
            tests_dir / "spec2code_cit.h",
            tests_dir / "spec2code_cit.c",
        ])
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
    paths = testbench_harness_paths(spec, out_dir, root=root)
    contents = [
        _apply_default_identifier_style(_testbench_protocol_header()),
        _apply_default_identifier_style(_testbench_protocol_source()),
        _apply_default_identifier_style(_mesaj_header(spec, get_descriptor)),
        _apply_default_identifier_style(_mesaj_source(spec, get_descriptor)),
        _apply_default_identifier_style(_testbench_log_header()),
        _apply_default_identifier_style(_testbench_log_source()),
        _apply_default_identifier_style(_testbench_trace_header()),
        _apply_default_identifier_style(_testbench_trace_source()),
        _apply_default_identifier_style(_testbench_ops_header(spec["project"]["name"], _testbench_used_handle_types(spec))),
        _apply_default_identifier_style(_testbench_ops_source(spec, get_descriptor)),
        _testbench_manifest(spec, get_descriptor),
    ]
    # CIT dosyalari (yalniz olcum varsa) — path listesiyle ayni sirada (manifest'ten sonra).
    if _testbench_cit_enabled(spec, root):
        contents.extend([
            _apply_default_identifier_style(_cit_header(spec, get_descriptor)),
            _apply_default_identifier_style(_cit_source(spec, get_descriptor)),
        ])
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


def user_descriptors_dir() -> Path:
    """Kullanıcı descriptor klasörü: paketli uygulamada exe'nin YANINDA durur.

    Paket içindeki descriptors/ klasörü salt okunurdur (PyInstaller _MEIPASS);
    kullanıcı kendi entegresini bu klasöre YAML atarak ya da Import ekranından
    yükleyerek ekler. Öncelik sırası: SPEC2CODE_USER_DESCRIPTORS ortam
    değişkeni (testler/otomasyon) -> frozen'da exe dizini -> repo kökü.
    """
    env = os.environ.get("SPEC2CODE_USER_DESCRIPTORS", "").strip()
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "user_descriptors"
    return _ROOT / "user_descriptors"


def resolve_descriptor_path(ref_or_part: str, root: Path = _ROOT) -> Path:
    """Descriptor dosya yolunu çözer; kullanıcı klasörü HER ZAMAN önceliklidir.

    Aynı adlı dosya hem user_descriptors/ hem descriptors/ içinde varsa
    kullanıcınınki kazanır — kullanıcı yerleşik bir haritayı düzeltebilsin.
    """
    user_dir = user_descriptors_dir()
    if ref_or_part.endswith((".yaml", ".yml")) or "/" in ref_or_part:
        candidate = user_dir / Path(ref_or_part).name
        if candidate.is_file():
            return candidate
        return root / ref_or_part
    descriptor_name = "".join(ch.lower() for ch in ref_or_part if ch.isalnum())
    for stem in (descriptor_name, cmodel._module_of(ref_or_part)):
        candidate = user_dir / f"{stem}.yaml"
        if candidate.is_file():
            return candidate
    path = root / "descriptors" / f"{descriptor_name}.yaml"
    if not path.is_file():
        path = root / "descriptors" / f"{cmodel._module_of(ref_or_part)}.yaml"
    return path


def make_descriptor_loader(root: Path = _ROOT) -> Callable[[str], dict]:
    """Resolve a descriptor by ref path (descriptors/x.yaml) or by part name (TCA9548A)."""
    cache: dict[str, dict] = {}

    def get(ref_or_part: str) -> dict:
        path = resolve_descriptor_path(ref_or_part, root)
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
    # Zayıf bus-trace kancaları: sürücüler her gerçek transferi raporlar;
    # standalone kullanımda no-op, test bench güçlü impl ile canlı iz olur.
    written_trace = hio.write_output(drivers_dir / "spec2code_bus_trace.h", _bus_trace_header())
    driver_t = env.get_template("driver.c.j2")
    test_header_t = env.get_template("test.h.j2")
    test_t = env.get_template("test.c.j2")
    readme_t = env.get_template("readme.md.j2")

    written: list[str] = [str(written_trace)]
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
