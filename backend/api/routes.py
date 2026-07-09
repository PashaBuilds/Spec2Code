"""REST API routes (Brief 18). Thin orchestration over the existing modules."""

from __future__ import annotations

import json
import io
import os
import re
import struct
import zipfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import Literal

import yaml
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field

from backend import s2cmsg
from backend import yatt
from backend.cit import decode_board_cit
from backend.jobs import manager
from backend.parsers.xparameters import parse_xparameters
from backend import register_map as regmap
from backend.parsers.xsa import XsaParseError, parse_xsa, safe_xsa_filename
from backend.rulesets import DEFAULT_RULESET, RULESET_SCHEMA
from backend.testbench import (
    TestbenchCommand,
    TestbenchSessionError,
    list_serial_ports,
    send_command,
    testbench_sessions,
)
from backend.bringup import BringupConfig, bringup_manager, render_certificate_html
from backend.registers import snapshot_registers
from backend.run_on_board import RunOnBoardConfig, normalize_hw_server_url, runboard_manager
from backend.validators.wiring import validate_wiring
from backend.vitis_errors import map_vitis_errors
from backend.vitis_workspace import VitisWorkspaceConfig, default_vitis_processor, vitis_manager, vitis_os
from backend.vivado_design import (
    VivadoDesignConfig,
    VivadoPeripheral,
    list_parts as list_vivado_parts,
    validate_design as validate_vivado_design,
    vivado_manager,
    zynqmp_ddr_parts,
    zynqmp_mio_options,
)
from catalog.matcher import scan_folder
from hostplat import io as hio
from hostplat import tools
from orchestrator.codegen import resolve_descriptor_path, user_descriptors_dir
from orchestrator.descriptor_check import validate_descriptor
from orchestrator.descriptor_example import EXAMPLE_FILE_NAME, EXAMPLE_USER_DESCRIPTOR
from orchestrator.llm.client import LlmClient, LlmConfig, LlmError

_ROOT = Path(__file__).resolve().parent.parent.parent
_PLATFORMS = _ROOT / "platforms"
_DESCRIPTORS = _ROOT / "descriptors"
_CATALOG = _ROOT / "catalog" / "catalog.json"
_IMPORTED = _ROOT / "catalog" / "imported.json"
_SPEC_SCHEMA = json.loads((_ROOT / "schemas" / "project.spec.schema.json").read_text(encoding="utf-8"))

router = APIRouter(prefix="/api")


# --- request models ---------------------------------------------------------------------

class ParseRequest(BaseModel):
    text: str
    platform: str


class ValidateRequest(BaseModel):
    spec: dict


class GenerateRequest(BaseModel):
    spec: dict
    max_rounds: int = 3


class ScanRequest(BaseModel):
    folder: str


class ConfirmRequest(BaseModel):
    stem: str
    part: str
    role: str = "as_is"          # as_is | llm_exemplar | descriptor_source
    files: list[str] = []


class KnowledgeAskRequest(BaseModel):
    part: str
    question: str
    context: str
    llm: dict = Field(default_factory=dict)


class VitisWorkspaceRequest(BaseModel):
    vitis_path: str
    xsa_path: str = ""  # update modunda gerekmez
    workspace_path: str
    temp_path: str
    processor: str = ""
    runtime: str = ""
    platform_name: str = ""
    system_name: str = ""
    app_name: str = ""
    timeout_s: int = 1800
    custom_ip_driver_policy: str = "auto_none"
    mode: str = "full"  # full = platform+BSP+app sıfırdan; update = yalnızca kaynak + app build


class VitisErrorMapRequest(BaseModel):
    log: str


class TestbenchCommandRequest(BaseModel):
    host: str
    port: int
    device: str
    operation: str
    command_id: int = 1
    device_index: int = 0xFFFFFFFF
    session_id: str = ""
    register_name: str = Field("", alias="register")
    register_address: int | None = None
    address: int | None = None
    length: int | None = None
    value: int | None = None
    data_hex: str = ""
    timeout_s: float = 5.0


class TestbenchConnectRequest(BaseModel):
    session_id: str
    transport: str = "tcp"  # "tcp" | "serial" | "coresight"
    host: str = ""
    port: int = 0
    serial_port: str = ""
    baud: int = 115200
    vitis_path: str = ""  # coresight: xsdb bu kurulumdan bulunur
    hw_server_url: str = ""  # coresight: boş = lokal USB JTAG; SmartLynq için <ip>[:port]
    processor: str = "psu_cortexa53_0"  # coresight: DCC'nin bağlandığı çekirdek
    timeout_s: float = 5.0


class TestbenchTrafficRequest(BaseModel):
    session_id: str
    since: int = 0


class TestbenchSessionRequest(BaseModel):
    session_id: str


class TestbenchConsoleReadRequest(BaseModel):
    session_id: str
    since: int = 0


class TestbenchConsoleWriteRequest(BaseModel):
    session_id: str
    text: str


# --- helpers ----------------------------------------------------------------------------

def _platform_model(platform_id: str) -> dict:
    path = _PLATFORMS / f"{platform_id}.yaml"
    if not path.is_file():
        raise HTTPException(404, f"unknown platform '{platform_id}'")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _job_or_404(job_id: str):
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    return job


def _job_with_result(job_id: str):
    job = _job_or_404(job_id)
    if not job.result:
        raise HTTPException(409, "job result is not ready")
    return job


def _posix_path(value: str) -> str:
    return value.replace("\\", "/")


def _archive_name(rel: str, out_dir: str) -> str:
    rel_posix = _posix_path(rel)
    out_posix = _posix_path(out_dir).rstrip("/")
    if out_posix and rel_posix.startswith(f"{out_posix}/"):
        name = rel_posix[len(out_posix) + 1:]
    else:
        name = PurePosixPath(rel_posix).name

    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        return PurePosixPath(rel_posix).name
    return name or PurePosixPath(rel_posix).name


def _safe_download_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return name or "spec2code"


_ANSWER_TOKEN_RE = re.compile(r"\b0x[0-9A-Fa-f]+\b|\b[A-Z][A-Z0-9_#]{2,}\b")
_ANSWER_TOKEN_ALLOWLIST = {
    "ADC",
    "API",
    "CPHA",
    "CPOL",
    "CRC",
    "CS",
    "GPIO",
    "I2C",
    "IRQ",
    "JESD",
    "LLM",
    "LSB",
    "MISO",
    "MOSI",
    "MSB",
    "NULL",
    "POR",
    "QSPI",
    "RO",
    "RW",
    "SCK",
    "SPI",
    "TX",
    "RX",
    "UI",
    "WO",
}


def _knowledge_answer_unsupported_tokens(answer: str, context: str) -> list[str]:
    """Return code-like tokens in the answer that were not present in the supplied context."""
    context_upper = context.upper()
    unsupported: list[str] = []
    for token in sorted(set(_ANSWER_TOKEN_RE.findall(answer))):
        normalized = token.upper()
        if normalized in _ANSWER_TOKEN_ALLOWLIST:
            continue
        if normalized not in context_upper:
            unsupported.append(token)
    return unsupported


def _resolve_job_file(job, file_path: str) -> tuple[Path, str]:
    requested = _posix_path(file_path).lstrip("/")
    allowed = {_posix_path(rel) for rel in job.result.get("files", [])}
    if requested not in allowed:
        raise HTTPException(404, "generated file not found")

    path = (_ROOT / requested).resolve()
    try:
        path.relative_to(_ROOT.resolve())
    except ValueError as exc:
        raise HTTPException(400, "generated file path escaped repository root") from exc

    if not path.is_file():
        raise HTTPException(404, "generated file not found")
    return path, requested


def _validate_llm_config(spec: dict) -> list[dict[str, str]]:
    llm = spec.get("llm") or {}
    if not llm.get("enabled"):
        return []
    issues: list[dict[str, str]] = []
    base_url = (llm.get("base_url") or os.environ.get("SPEC2CODE_LLM_BASE_URL", "")).strip()
    model = (llm.get("model") or os.environ.get("SPEC2CODE_LLM_MODEL", "")).strip()
    if not base_url:
        issues.append({
            "severity": "error",
            "path": "llm/base_url",
            "message": "LLM is enabled but no OpenAI-compatible base_url is configured",
        })
    if not model:
        issues.append({
            "severity": "error",
            "path": "llm/model",
            "message": "LLM is enabled but no exact model name is configured",
        })
    return issues


def _driver_module(part: str) -> str:
    return re.sub(r"[^a-z0-9]", "", part.lower())


def _pascal_identifier(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _driver_function(module: str, action: str) -> str:
    return f"{module}{_pascal_identifier(action)}"


def _controller_handle_type(controller: dict) -> str | None:
    driver = controller.get("driver")
    if driver:
        return driver
    return {
        "i2c": "XIicPs",
        "spi": "XSpiPs",
        "qspi": "XQspiPsu",
    }.get(controller.get("type", ""))


def _controller_header(handle_type: str) -> str | None:
    return {
        "XIicPs": "xiicps.h",
        "XSpiPs": "xspips.h",
        "XQspiPs": "xqspips.h",
        "XQspiPsu": "xqspipsu.h",
    }.get(handle_type)


def _vitis_readme(job, files: list[str]) -> str:
    project = job.spec.get("project", {}).get("name", job.id)
    runtime = job.spec.get("project", {}).get("runtime", "bare_metal")
    qc = job.result.get("qc", {}) if job.result else {}
    file_list = "\n".join(f"- `{f}`" for f in files)
    return (
        f"# {project} - Vitis entegrasyon paketi\n\n"
        "Bu paket Spec2Code tarafindan uretilen suruculeri Vitis uygulamasina daha kolay "
        "tasimak icin hazirlanmistir.\n\n"
        "## Klasorler\n\n"
        "- `src/drivers/`: uretilen `.c` ve `.h` suruculer.\n"
        "- `src/tests/`: secilen self-test dosyalari.\n"
        "- `src/spec2code_selftest_main.c/.h`: self-testleri topluca cagiran ornek runner.\n"
        "- `meta/project.spec.json`: bu paketi ureten canonical spec.\n"
        "- `meta/qc_report.json`: son QC raporu.\n\n"
        "## Vitis'e aktarma\n\n"
        "1. `src/drivers` altindaki `.c` ve `.h` dosyalarini Vitis application source tree'ye ekle.\n"
        "2. Self-test kullanacaksan `src/tests` ve `src/spec2code_selftest_main.c/.h` dosyalarini da ekle.\n"
        "3. Include path'e `src/drivers` klasorunu ekle.\n"
        "4. BSP tarafinda `xparameters.h` ayni donanim platformundan gelmeli.\n"
        "5. `spec2codeRunSelfTests()` fonksiyonunu kendi `main.c` veya FreeRTOS task akisin icinden cagir.\n\n"
        f"Runtime: `{runtime}`\n\n"
        f"QC: `passed={str(qc.get('passed')).lower()}`\n\n"
        "## Paket dosyalari\n\n"
        f"{file_list}\n"
    )


def _vitis_selftest_main(spec: dict) -> str:
    controllers = {c["id"]: c for c in spec.get("controllers", [])}
    devices = spec.get("devices", [])
    declarations: list[str] = []
    declaration_keys: set[tuple[str, str]] = set()
    calls: list[str] = []
    includes = {
        "spec2code_selftest_main.h",
        "xstatus.h",
        "xil_printf.h",
        "xil_types.h",
    }

    for device in devices:
        if "self_test" not in (device.get("tests_requested") or []):
            continue
        controller = controllers.get(device.get("attach", {}).get("controller_id"))
        if not controller:
            continue
        handle_type = _controller_handle_type(controller)
        if handle_type is None:
            continue
        module = _driver_module(device.get("part", ""))
        handle_base = _pascal_identifier(device.get("id") or module)
        handle_name = f"s{handle_base}Handle"
        header = _controller_header(handle_type)
        if header:
            includes.add(header)
        includes.add(f"{module}.h")
        self_test = _driver_function(module, "self_test")
        declaration_key = (self_test, handle_type)
        if declaration_key not in declaration_keys:
            declaration_keys.add(declaration_key)
            declarations.append(f"int {self_test}({handle_type}* spHandle);")
        calls.extend([
            f"    {handle_type} {handle_name};",
            f"    iStatus = {self_test}(&{handle_name});",
            "    if (iStatus != XST_SUCCESS)",
            "    {",
            f'        xil_printf("{device.get("part", module)} self-test FAILED: %d\\r\\n", iStatus);',
            "        return iStatus;",
            "    }",
            f'    xil_printf("{device.get("part", module)} self-test PASSED\\r\\n");',
            "",
        ])

    include_lines = [f'#include "{name}"' for name in sorted(includes) if name.endswith(".h")]
    declaration_block = "\n".join(declarations) or "/* No self-test functions were selected. */"
    call_block = "\n".join(calls) if calls else "    xil_printf(\"No Spec2Code self-tests selected.\\r\\n\");\n"
    return (
        "/**\n"
        " * @file spec2code_selftest_main.c\n"
        " * @brief Example Vitis runner for Spec2Code generated self-tests.\n"
        " */\n"
        + "\n".join(include_lines)
        + "\n\n"
        + declaration_block
        + "\n\n"
        "int spec2codeRunSelfTests(void)\n"
        "{\n"
        "    int iStatus;\n\n"
        + call_block
        + "    return XST_SUCCESS;\n"
        "}\n"
    )


def _vitis_selftest_header() -> str:
    return (
        "/**\n"
        " * @file spec2code_selftest_main.h\n"
        " * @brief Public Spec2Code Vitis self-test runner API.\n"
        " */\n"
        "#ifndef SPEC2CODE_SELFTEST_MAIN_H\n"
        "#define SPEC2CODE_SELFTEST_MAIN_H\n\n"
        "int spec2codeRunSelfTests(void);\n\n"
        "#endif\n"
    )


# --- endpoints --------------------------------------------------------------------------

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "tools": tools.status()}


@router.get("/platforms")
def list_platforms() -> dict:
    items = []
    for path in sorted(_PLATFORMS.glob("*.yaml")):
        model = yaml.safe_load(path.read_text(encoding="utf-8"))
        items.append({"id": model["platform"], "display_name": model.get("display_name", ""),
                      "summary": model.get("summary", ""),
                      "cores": model.get("cores", []), "zones": model.get("zones", [])})
    return {"platforms": items}


@router.get("/platforms/{platform_id}")
def get_platform(platform_id: str) -> dict:
    return _platform_model(platform_id)


@router.post("/xparameters/parse")
def parse(req: ParseRequest) -> dict:
    model = _platform_model(req.platform)
    result = parse_xparameters(req.text, model)
    return {
        "platform": req.platform,
        "zones": model.get("zones", []),
        "cores": model.get("cores", []),
        "controllers": result.controllers,
        "unmatched": result.unmatched,
    }


class XsaParseRequest(BaseModel):
    path: str


def _xsa_parse_response(xsa_path: Path) -> dict:
    try:
        detected = parse_xsa(xsa_path)
    except XsaParseError as exc:
        raise HTTPException(422, str(exc)) from exc
    if not detected.platform:
        raise HTTPException(422, "XSA içinden platform algılanamadı (işlemci modülü bulunamadı).")
    model = _platform_model(detected.platform)
    # Re-parse with the platform model so zones resolve exactly as in the
    # xparameters flow.
    detected = parse_xsa(xsa_path, model)
    detected.platform = detected.platform or ""
    return {
        "platform": detected.platform,
        "zones": model.get("zones", []),
        "cores": model.get("cores", []),
        "controllers": detected.controllers,
        "unmatched": detected.unmatched,
        "processors": detected.processors,
        "xsa_path": str(xsa_path),
    }


@router.post("/xsa/parse")
def xsa_parse(req: XsaParseRequest) -> dict:
    xsa_path = Path(os.path.expandvars(req.path.strip().strip('"').strip("'")))
    if not xsa_path.is_file():
        raise HTTPException(404, f"XSA dosyası bulunamadı: {xsa_path}")
    return _xsa_parse_response(xsa_path)


@router.post("/xsa/upload")
async def xsa_upload(file: UploadFile) -> dict:
    uploads_dir = _ROOT / "uploads" / "xsa"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    target = uploads_dir / safe_xsa_filename(file.filename or "design.xsa")
    content = await file.read()
    target.write_bytes(content)
    return _xsa_parse_response(target)


def _user_descriptor_entries() -> list[dict]:
    """user_descriptors/ içeriği; bozuk YAML'lar hata alanıyla listelenir."""
    entries: list[dict] = []
    user_dir = user_descriptors_dir()
    if not user_dir.is_dir():
        return entries
    for path in sorted([*user_dir.glob("*.yaml"), *user_dir.glob("*.yml")]):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            entries.append({"file": path.name, "part": None, "error": f"YAML parse hatası: {exc}"})
            continue
        if not isinstance(doc, dict):
            entries.append({"file": path.name, "part": None, "error": "YAML kökü nesne olmalı"})
            continue
        entries.append({
            "file": path.name,
            "part": doc.get("part"),
            "transport": (doc.get("transport") or {}).get("type"),
            "summary": doc.get("summary", ""),
            "registers": len(doc.get("registers") or []),
            "operations": [op.get("name") for op in doc.get("operations") or [] if isinstance(op, dict)],
        })
    return entries


@router.get("/catalog")
def get_catalog() -> dict:
    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    if _IMPORTED.is_file():
        catalog["imported"] = json.loads(_IMPORTED.read_text(encoding="utf-8"))
    # Kullanıcı descriptor'ları parça seçicide yerleşiklerle yan yana görünür;
    # aynı part hem yerleşik hem kullanıcıda varsa kullanıcı girdisi kazanır
    # (çözümleme önceliğiyle tutarlı).
    users = [e for e in _user_descriptor_entries() if e.get("part") and not e.get("error")]
    if users:
        catalog.setdefault("statuses", {})["user"] = "User descriptor (user_descriptors/); resolved before the built-in library."
        by_part = {d.get("part"): i for i, d in enumerate(catalog.get("devices", []))}
        for entry in users:
            device = {
                "part": entry["part"],
                "transport": entry.get("transport") or "i2c",
                "status": "user",
                "descriptor": f"user_descriptors/{entry['file']}",
                "summary": entry.get("summary", ""),
                "match_tokens": [entry["part"]],
            }
            index = by_part.get(entry["part"])
            if index is None:
                catalog.setdefault("devices", []).append(device)
            else:
                catalog["devices"][index] = device
    return catalog


@router.get("/descriptors")
def list_descriptors() -> dict:
    items = []
    user_parts = set()
    for entry in _user_descriptor_entries():
        if entry.get("error") or not entry.get("part"):
            continue
        user_parts.add(entry["part"])
        items.append({"part": entry["part"], "ref": f"user_descriptors/{entry['file']}",
                      "transport": entry.get("transport"), "summary": entry.get("summary", ""),
                      "operations": entry.get("operations", []), "source": "user"})
    for path in sorted(_DESCRIPTORS.glob("*.yaml")):
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        if d.get("part") in user_parts:
            continue  # kullanıcı dosyası yerleşiği gölgeler
        items.append({"part": d.get("part"), "ref": f"descriptors/{path.name}",
                      "transport": d.get("transport", {}).get("type"),
                      "summary": d.get("summary", ""),
                      "operations": [op["name"] for op in d.get("operations", [])],
                      "source": "builtin"})
    return {"descriptors": items}


@router.get("/descriptors/{part}")
def get_descriptor(part: str) -> dict:
    path = resolve_descriptor_path(part, _ROOT)
    if not path.is_file():
        raise HTTPException(404, f"no descriptor for '{part}'")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class UserDescriptorUpload(BaseModel):
    content: str


@router.get("/user-descriptors")
def list_user_descriptors() -> dict:
    return {"dir": str(user_descriptors_dir()), "descriptors": _user_descriptor_entries()}


@router.post("/user-descriptors/validate")
def validate_user_descriptor(req: UserDescriptorUpload) -> dict:
    """Kaydetmeden doğrula (Descriptor Sihirbazı canlı kontrolü)."""
    try:
        doc = yaml.safe_load(req.content)
    except yaml.YAMLError as exc:
        return {"valid": False, "errors": [f"YAML parse hatası: {exc}"]}
    errors = validate_descriptor(doc)
    return {"valid": not errors, "errors": errors,
            "part": doc.get("part") if isinstance(doc, dict) else None}


@router.get("/user-descriptors/example")
def user_descriptor_example() -> dict:
    """Bilinen-iyi örnek şablon: testler aynı içeriği doğrulayıcıdan ve
    tam üretimden geçirir — indirilen şablon her zaman çalışır durumdadır."""
    return {"file": EXAMPLE_FILE_NAME, "content": EXAMPLE_USER_DESCRIPTOR}


@router.post("/user-descriptors")
def upload_user_descriptor(req: UserDescriptorUpload) -> dict:
    try:
        doc = yaml.safe_load(req.content)
    except yaml.YAMLError as exc:
        raise HTTPException(400, {"message": "YAML parse hatası", "errors": [str(exc)]})
    errors = validate_descriptor(doc)
    if errors:
        raise HTTPException(400, {"message": "descriptor doğrulaması başarısız", "errors": errors})
    part = str(doc["part"]).strip()
    stem = "".join(ch.lower() for ch in part if ch.isalnum()) or "part"
    user_dir = user_descriptors_dir()
    user_dir.mkdir(parents=True, exist_ok=True)
    target = user_dir / f"{stem}.yaml"
    target.write_text(req.content, encoding="utf-8")
    return {"saved": target.name, "part": part, "dir": str(user_dir),
            "overrides_builtin": (_DESCRIPTORS / f"{stem}.yaml").is_file()}


@router.delete("/user-descriptors/{file_name}")
def delete_user_descriptor(file_name: str) -> dict:
    user_dir = user_descriptors_dir()
    target = (user_dir / Path(file_name).name).resolve()
    # Yol kacisi olmasin: yalniz user_descriptors icindeki .yaml/.yml silinir.
    if target.parent != user_dir.resolve() or target.suffix not in {".yaml", ".yml"}:
        raise HTTPException(400, "geçersiz dosya adı")
    if not target.is_file():
        raise HTTPException(404, f"dosya yok: {target.name}")
    target.unlink()
    return {"deleted": target.name}


@router.get("/rulesets/default")
def ruleset_default() -> dict:
    return {"ruleset": DEFAULT_RULESET, "schema": RULESET_SCHEMA}


@router.post("/knowledge/ask")
def knowledge_ask(req: KnowledgeAskRequest) -> dict:
    question = req.question.strip()
    context = req.context.strip()
    if not question:
        raise HTTPException(400, "question is empty")
    if not context:
        raise HTTPException(400, "knowledge context is empty")
    if not req.llm.get("enabled"):
        raise HTTPException(400, {
            "message": "llm disabled",
            "errors": [{
                "severity": "error",
                "path": "llm/enabled",
                "message": "LLM assist kapali. Knowledge sorulari icin OpenAI uyumlu lokal model endpointini etkinlestir.",
            }],
        })

    llm_errors = _validate_llm_config({"llm": req.llm})
    if llm_errors:
        raise HTTPException(400, {"message": "llm invalid", "errors": llm_errors[:10]})

    config = LlmConfig.resolve(req.llm)
    max_context_chars = 220_000
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n[context burada kesildi]"

    messages = [
        {
            "role": "system",
            "content": (
                "Sen Spec2Code icindeki statik datasheet knowledge paketini cevaplayan bir gomulu yazilim "
                "yardimcisisin. Sadece verilen KNOWLEDGE CONTEXT icindeki bilgilere dayan. Contextte olmayan "
                "bir bilgiyi tahmin etme; bunun yerine 'Bu bilgi verilen knowledge icinde yok' de. "
                "Contextte bulunmayan register, bit field, opcode, fonksiyon veya entegre adi uydurma. "
                "Cevaplari Turkce cumlelerle ver; register, bit field, driver, readback, opcode gibi teknik "
                "terimleri gerektiğinde Ingilizce kullan. Register adresi, bit field adi, read/write akisi, "
                "TX/RX byte boyutu ve driver fonksiyon adi contextte varsa mutlaka belirt. "
                "Cevabi okunabilir ve kisa bolumler halinde ver: once 'Kisa cevap', sonra gerekiyorsa "
                "'Register detayi', 'Bit field', 'Islem sirasi' ve 'Driver view'. Gereksiz markdown kalabaligi "
                "uretme; madde isaretlerini ve numarali adimlari sadece okunurluk icin kullan."
            ),
        },
        {
            "role": "user",
            "content": (
                f"PART: {req.part}\n\n"
                f"KNOWLEDGE CONTEXT:\n{context}\n\n"
                f"QUESTION:\n{question}"
            ),
        },
    ]

    try:
        answer = LlmClient(config).chat(messages, temperature=0.0, max_tokens=min(config.max_tokens, 2048)).strip()
    except LlmError as exc:
        raise HTTPException(502, {"message": "llm failed", "error": str(exc)}) from exc
    if not answer:
        raise HTTPException(502, {"message": "llm empty", "error": "LLM bos cevap dondurdu."})

    unsupported_tokens = _knowledge_answer_unsupported_tokens(answer, context)
    if unsupported_tokens:
        raise HTTPException(502, {
            "message": "llm ungrounded",
            "error": "LLM cevabi verilen knowledge context disinda register/opcode/bitfield tokenlari iceriyor.",
            "unsupported_tokens": unsupported_tokens[:20],
        })

    return {
        "part": req.part,
        "model": config.model,
        "answer": answer,
        "context_chars": len(context),
        "grounded": True,
    }


@router.post("/spec/validate")
def validate_spec(req: ValidateRequest) -> dict:
    schema_errors = sorted(Draft7Validator(_SPEC_SCHEMA).iter_errors(req.spec), key=lambda e: list(e.path))
    schema_result = [{"path": "/".join(map(str, e.path)), "message": e.message} for e in schema_errors]
    wiring = {"valid": False, "errors": [], "warnings": []}
    llm_errors: list[dict[str, str]] = []
    if not schema_errors:
        wiring = validate_wiring(req.spec)
        llm_errors = _validate_llm_config(req.spec)
    return {
        "valid": not schema_errors and wiring["valid"] and not llm_errors,
        "errors": [*schema_result, *wiring["errors"], *llm_errors],
        "schema_errors": schema_result,
        "wiring": wiring,
        "llm_errors": llm_errors,
    }


@router.post("/generate")
async def generate(req: GenerateRequest) -> dict:
    errors = list(Draft7Validator(_SPEC_SCHEMA).iter_errors(req.spec))
    if errors:
        raise HTTPException(400, {"message": "spec invalid",
                                  "errors": [e.message for e in errors[:5]]})
    wiring = validate_wiring(req.spec)
    if wiring["errors"]:
        raise HTTPException(400, {"message": "wiring invalid", "errors": wiring["errors"][:10]})
    llm_errors = _validate_llm_config(req.spec)
    if llm_errors:
        raise HTTPException(400, {"message": "llm invalid", "errors": llm_errors[:10]})
    job_id = await manager.start(req.spec, max_rounds=req.max_rounds)
    return {"job_id": job_id}


@router.get("/jobs/{job_id}/result")
def job_result(job_id: str) -> dict:
    job = _job_or_404(job_id)
    files = []
    if job.result:
        out_dir = job.result.get("out_dir", "")
        for rel in job.result["files"]:
            p = _ROOT / rel
            files.append({
                "path": rel,
                "relative_path": _archive_name(rel, out_dir),
                "name": Path(rel).name,
                "content": hio.read_text(p) if p.is_file() else "",
            })
    return {"job_id": job_id, "status": job.status, "error": job.error,
            "result": job.result, "files": files}


@router.get("/jobs/{job_id}/download")
def download_job(job_id: str) -> Response:
    job = _job_with_result(job_id)
    out_dir = job.result.get("out_dir", "")
    buffer = io.BytesIO()
    written = 0
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in job.result.get("files", []):
            path, normalized = _resolve_job_file(job, rel)
            archive.write(path, _archive_name(normalized, out_dir))
            written += 1

    if written == 0:
        raise HTTPException(404, "no generated files")

    project = job.spec.get("project", {}).get("name", job_id)
    filename = f"{_safe_download_name(project)}-generated.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/jobs/{job_id}/vitis")
def download_vitis_job(job_id: str) -> Response:
    job = _job_with_result(job_id)
    out_dir = job.result.get("out_dir", "")
    buffer = io.BytesIO()
    archived: list[str] = []

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for rel in job.result.get("files", []):
            path, normalized = _resolve_job_file(job, rel)
            name = _archive_name(normalized, out_dir)
            if name.startswith("drivers/"):
                arcname = f"src/{name}"
            elif name.startswith("tests/"):
                arcname = f"src/{name}"
            elif name.startswith("reference_sources/"):
                arcname = name
            elif name == "qc_report.json":
                arcname = "meta/qc_report.json"
            elif name == "README.md":
                arcname = "meta/generated_README.md"
            elif name == ".clang-format":
                arcname = "meta/.clang-format"
            else:
                arcname = f"meta/{name}"
            archive.write(path, arcname)
            archived.append(arcname)

        archive.writestr(
            "src/spec2code_selftest_main.h",
            hio.normalize_crlf(_vitis_selftest_header()).encode("utf-8"),
        )
        archived.append("src/spec2code_selftest_main.h")
        archive.writestr(
            "src/spec2code_selftest_main.c",
            hio.normalize_crlf(_vitis_selftest_main(job.spec)).encode("utf-8"),
        )
        archived.append("src/spec2code_selftest_main.c")
        archive.writestr(
            "meta/project.spec.json",
            (json.dumps(job.spec, indent=2) + "\n").encode("utf-8"),
        )
        archived.append("meta/project.spec.json")
        archive.writestr(
            "README_TR.md",
            hio.normalize_crlf(_vitis_readme(job, sorted(archived))).encode("utf-8"),
        )

    project = job.spec.get("project", {}).get("name", job_id)
    filename = f"{_safe_download_name(project)}-vitis.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/jobs/{job_id}/vitis/workspace")
async def create_vitis_workspace(job_id: str, req: VitisWorkspaceRequest) -> dict:
    # .hdf yalniz sematik/kod uretimi icin kabul edilir: XSCT `platform
    # create -hw` XSA icin belgelidir, eski SDK handoff'u bu akista
    # calistirilmaz - sessiz XSCT hatasi yerine burada net Turkce hata.
    if req.mode != "update" and req.xsa_path.strip().lower().endswith(".hdf"):
        raise HTTPException(
            422,
            "Vitis workspace kurulumu .xsa gerektirir (XSCT platform create). "
            ".hdf yalnız şematik ve kod üretimi için desteklenir; Vivado 2019.2+ "
            "'File > Export > Export Hardware' ile .xsa üretin.",
        )
    job = _job_with_result(job_id)
    project = job.spec.get("project", {})
    runtime = req.runtime.strip() or project.get("runtime", "bare_metal")
    processor = req.processor.strip() or default_vitis_processor(
        str(project.get("platform", "")),
        str(project.get("target_core", "")),
    )
    try:
        vitis_job_id = await vitis_manager.start(
            job,
            VitisWorkspaceConfig(
                vitis_path=req.vitis_path,
                xsa_path=req.xsa_path,
                workspace_path=req.workspace_path,
                temp_path=req.temp_path,
                processor=processor,
                runtime=vitis_os(runtime),
                platform_name=req.platform_name,
                system_name=req.system_name,
                app_name=req.app_name,
                timeout_s=req.timeout_s,
                custom_ip_driver_policy=req.custom_ip_driver_policy,
                mode=req.mode if req.mode in ("full", "update") else "full",
            ),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return {"vitis_job_id": vitis_job_id}


@router.get("/vitis/jobs/{vitis_job_id}/result")
def vitis_workspace_result(vitis_job_id: str) -> dict:
    job = vitis_manager.get(vitis_job_id)
    if job is None:
        raise HTTPException(404, "unknown Vitis job")
    return {
        "vitis_job_id": vitis_job_id,
        "source_job_id": job.source_job_id,
        "status": job.status,
        "error": job.error,
        "result": job.result,
    }


class VivadoPeripheralRequest(BaseModel):
    kind: str
    mio: str = ""
    qspi_mode: str = ""
    qspi_data_mode: str = ""
    qspi_fbclk: bool = False


class VivadoDesignRequest(BaseModel):
    vivado_path: str
    platform: str
    part: str
    temp_path: str
    design_name: str = "spec2code_hw"
    peripherals: list[VivadoPeripheralRequest] = []
    ref_clk_mhz: str = ""
    ddr_mode: str = "none"
    ddr_params: dict[str, str] = {}
    ddr_model: str = ""
    ddr_bus_width: str = ""
    ddr_speed_bin: str = ""
    add_regmap_test_ip: bool = False
    make_bitstream: bool = False
    timeout_s: int = 3600


def _vivado_config(req: VivadoDesignRequest) -> VivadoDesignConfig:
    return VivadoDesignConfig(
        vivado_path=req.vivado_path,
        platform=req.platform,
        part=req.part,
        temp_path=req.temp_path,
        design_name=re.sub(r"[^A-Za-z0-9_]+", "_", req.design_name).strip("_") or "spec2code_hw",
        peripherals=[
            VivadoPeripheral(kind=p.kind, mio=p.mio, qspi_mode=p.qspi_mode,
                             qspi_data_mode=p.qspi_data_mode, qspi_fbclk=p.qspi_fbclk)
            for p in req.peripherals
        ],
        ref_clk_mhz=req.ref_clk_mhz,
        ddr_mode=req.ddr_mode,
        ddr_params=req.ddr_params,
        ddr_model=req.ddr_model,
        ddr_bus_width=req.ddr_bus_width,
        ddr_speed_bin=req.ddr_speed_bin,
        add_regmap_test_ip=req.add_regmap_test_ip,
        make_bitstream=req.make_bitstream,
        timeout_s=max(300, min(req.timeout_s, 4 * 3600)),
    )


class VivadoPartsRequest(BaseModel):
    vivado_path: str
    refresh: bool = False
    cached_only: bool = False


@router.post("/vivado/parts")
def vivado_parts(req: VivadoPartsRequest) -> dict:
    """Kurulu Vivado'nun tam parça listesi (get_parts) — platform -> cihaz ->
    parça olarak gruplanmış. İlk üretim ~1 dk sürer ve önbelleğe yazılır;
    cached_only=true yalnız önbelleğe bakar (Vivado açılmaz)."""
    try:
        return list_vivado_parts(
            req.vivado_path,
            _ROOT / "uploads" / "vivado_parts",
            refresh=req.refresh,
            cached_only=req.cached_only,
        )
    except FileNotFoundError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - Vivado hatası kullanıcıya aynen gider
        raise HTTPException(502, str(exc)) from exc


class RegisterMapRequest(BaseModel):
    document: dict


class RegisterMapHtmlRequest(BaseModel):
    html: str


@router.post("/register-map/validate")
def register_map_validate(req: RegisterMapRequest) -> dict:
    errors = regmap.validate_register_document(req.document)
    return {"valid": not errors, "errors": errors}


@router.post("/register-map/generate")
def register_map_generate(req: RegisterMapRequest) -> dict:
    """Register map dokümanı → { '<map>_regs.h': ..., '<map>.c': ... }."""
    errors = regmap.validate_register_document(req.document)
    if errors:
        raise HTTPException(422, "; ".join(errors))
    return {"files": regmap.generate_files(req.document)}


@router.post("/register-map/export-html")
def register_map_export_html(req: RegisterMapRequest) -> dict:
    """Dokümanı self-contained HTML editöre gömer (sayısal ekiple paylaşım)."""
    errors = regmap.validate_register_document(req.document)
    if errors:
        raise HTTPException(422, "; ".join(errors))
    return {"html": regmap.build_html(req.document)}


@router.post("/register-map/import-html")
def register_map_import_html(req: RegisterMapHtmlRequest) -> dict:
    """Self-contained HTML'den gömülü register map dokümanını çıkarır."""
    try:
        document = regmap.extract_document_from_html(req.html)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    errors = regmap.validate_register_document(document)
    return {"document": document, "valid": not errors, "errors": errors}


class RegisterMapXlsxRequest(BaseModel):
    xlsx_base64: str


@router.post("/register-map/export-xlsx")
def register_map_export_xlsx(req: RegisterMapRequest) -> dict:
    """Dokümanı KATI şablon .xlsx'e (base64) çevirir (Excel ile paylaşım)."""
    import base64

    errors = regmap.validate_register_document(req.document)
    if errors:
        raise HTTPException(422, "; ".join(errors))
    data = regmap.build_xlsx(req.document)
    return {"xlsx_base64": base64.b64encode(data).decode("ascii")}


@router.post("/register-map/import-xlsx")
def register_map_import_xlsx(req: RegisterMapXlsxRequest) -> dict:
    """KATI şablon .xlsx'ten (base64) register map dokümanını çıkarır."""
    import base64

    try:
        data = base64.b64decode(req.xlsx_base64)
        document = regmap.parse_xlsx(data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - okuma hatası kullanıcıya aynen gider
        raise HTTPException(422, f"XLSX okunamadı: {exc}") from exc
    errors = regmap.validate_register_document(document)
    return {"document": document, "valid": not errors, "errors": errors}


@router.get("/register-map/test-ip")
def register_map_test_ip(base_address: str = regmap.REGMAP_TEST_IP_DEFAULT_BASE) -> dict:
    """Vivado "Register Map Test IP"nin haritası (RTL ile birebir). Vivado
    tasarımında IP eklenip üretildiğinde atanan taban adresle Register Map'e
    otomatik getirilir; base_address verilmezse ZynqMP HPM0 varsayılanı."""
    doc = regmap.regmap_test_ip_document(base_address or regmap.REGMAP_TEST_IP_DEFAULT_BASE)
    return {"document": doc, "valid": not regmap.validate_register_document(doc)}


@router.get("/register-map/example")
def register_map_example() -> dict:
    """Boş/örnek register map + gömülü hâli (self-contained HTML editör)."""
    doc = regmap.blank_document()
    return {"document": doc, "html": regmap.build_html(doc)}


@router.get("/vivado/ddr-parts")
def vivado_ddr_parts() -> dict:
    """DDR model havuzu (ZynqMP): geometri Xilinx memparts.csv'den,
    zamanlamalar üretim anında PCW tarafından hesaplanır."""
    return {"zynq_ultrascale": zynqmp_ddr_parts()}


@router.get("/vivado/mio-options")
def vivado_mio_options() -> dict:
    """ZynqMP PS çevre birimleri için geçerli MIO konumları (Vivado
    kabul-testi taramasından; part-bağımsız). UI dropdown'u bundan beslenir."""
    return {"zynq_ultrascale": zynqmp_mio_options()}


@router.post("/vivado/design/validate")
def vivado_design_validate(req: VivadoDesignRequest) -> dict:
    errors = validate_vivado_design(_vivado_config(req))
    return {"valid": not errors, "errors": errors}


@router.post("/vivado/design")
async def vivado_design_start(req: VivadoDesignRequest) -> dict:
    try:
        vivado_job_id = await vivado_manager.start(_vivado_config(req))
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"vivado_job_id": vivado_job_id}


@router.get("/vivado/jobs/{vivado_job_id}/result")
def vivado_design_result(vivado_job_id: str) -> dict:
    job = vivado_manager.get(vivado_job_id)
    if job is None:
        raise HTTPException(404, "unknown Vivado job")
    return {
        "vivado_job_id": vivado_job_id,
        "status": job.status,
        "error": job.error,
        "result": job.result,
    }


@router.post("/vitis/compile-errors/map")
def vitis_compile_errors_map(req: VitisErrorMapRequest) -> dict:
    return {"issues": map_vitis_errors(req.log)}


class RunOnBoardRequest(BaseModel):
    vitis_path: str
    workspace_path: str
    platform_name: str
    app_name: str
    processor: str = "psu_cortexa53_0"
    platform: str = "zynq_ultrascale"  # zynq_ultrascale | zynq_7000 | versal
    program_fpga: str = "auto"  # auto | yes | no
    hw_server_url: str = ""  # boş = lokal USB JTAG; SmartLynq için <ip>[:port]
    bitstream_path: str = ""  # boş = platformdan otomatik; XSA bit içermiyorsa elle .bit yolu
    timeout_s: int = 300


@router.post("/vitis/run-on-board")
async def vitis_run_on_board(req: RunOnBoardRequest) -> dict:
    try:
        hw_server_url = normalize_hw_server_url(req.hw_server_url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    job_id = await runboard_manager.start(RunOnBoardConfig(
        vitis_path=req.vitis_path,
        workspace_path=req.workspace_path,
        platform_name=req.platform_name,
        app_name=req.app_name,
        processor=req.processor,
        platform=req.platform,
        program_fpga=req.program_fpga,
        hw_server_url=hw_server_url,
        bitstream_path=req.bitstream_path,
        timeout_s=req.timeout_s,
    ))
    return {"runboard_job_id": job_id}


@router.get("/vitis/run-on-board/{job_id}/result")
def vitis_run_on_board_result(job_id: str) -> dict:
    job = runboard_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown run-on-board job")
    return {
        "runboard_job_id": job_id,
        "status": job.status,
        "error": job.error,
        "result": job.result,
    }


@router.post("/testbench/command")
def testbench_command(req: TestbenchCommandRequest) -> dict:
    try:
        command = TestbenchCommand(
            host=req.host,
            port=req.port,
            device=req.device,
            operation=req.operation,
            command_id=req.command_id,
            device_index=req.device_index,
            register=req.register_name,
            register_address=req.register_address,
            address=req.address,
            length=req.length,
            value=req.value,
            data_hex=req.data_hex,
            timeout_s=req.timeout_s,
        )
        result = testbench_sessions.send(req.session_id, command) if req.session_id else send_command(command)
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "testbench tcp session is not connected", "error": str(exc)}) from exc
    except OSError as exc:
        raise HTTPException(502, {"message": "testbench tcp failed", "error": str(exc)}) from exc
    return {
        "request_line": result.request_line,
        "response_line": result.response_line,
        "parsed": result.parsed,
    }


@router.post("/testbench/session/connect")
def testbench_session_connect(req: TestbenchConnectRequest) -> dict:
    try:
        if req.transport == "serial":
            if not req.serial_port.strip():
                raise HTTPException(400, {"message": "serial_port is required for the serial transport"})
            return testbench_sessions.connect_serial(
                req.session_id, req.serial_port, req.baud, req.timeout_s).__dict__
        if req.transport == "coresight":
            if not req.vitis_path.strip():
                raise HTTPException(400, {"message": "vitis_path is required for the coresight transport"})
            return testbench_sessions.connect_coresight(
                req.session_id, req.vitis_path, req.hw_server_url,
                req.processor, req.timeout_s).__dict__
        return testbench_sessions.connect(req.session_id, req.host, req.port, req.timeout_s).__dict__
    except TestbenchSessionError as exc:
        raise HTTPException(400, {"message": "testbench session is invalid", "error": str(exc)}) from exc
    except ImportError as exc:
        raise HTTPException(501, {"message": "pyserial is not installed on the backend", "error": str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(400, {"message": "testbench connect failed", "error": str(exc)}) from exc
    except (OSError, FileNotFoundError) as exc:
        raise HTTPException(502, {"message": "testbench connect failed", "error": str(exc)}) from exc


@router.get("/testbench/serial/ports")
def testbench_serial_ports() -> dict:
    return {"ports": list_serial_ports()}


@router.post("/testbench/console/read")
def testbench_console_read(req: TestbenchConsoleReadRequest) -> dict:
    try:
        seq, entries = testbench_sessions.console(req.session_id, req.since)
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "serial console is not connected", "error": str(exc)}) from exc
    return {"seq": seq, "entries": entries}


@router.post("/testbench/console/write")
def testbench_console_write(req: TestbenchConsoleWriteRequest) -> dict:
    try:
        testbench_sessions.write_raw(req.session_id, req.text)
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "serial console is not connected", "error": str(exc)}) from exc
    except OSError as exc:
        raise HTTPException(502, {"message": "serial write failed", "error": str(exc)}) from exc
    return {"ok": True}


@router.post("/testbench/traffic")
def testbench_traffic(req: TestbenchTrafficRequest) -> dict:
    try:
        seq, entries = testbench_sessions.traffic(req.session_id, req.since)
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "testbench session not found", "error": str(exc)}) from exc
    return {"seq": seq, "entries": entries}


@router.get("/testbench/sessions")
def testbench_session_list() -> dict:
    return {"sessions": [status.__dict__ for status in testbench_sessions.list_sessions()]}


@router.post("/testbench/session/disconnect")
def testbench_session_disconnect(req: TestbenchSessionRequest) -> dict:
    try:
        return testbench_sessions.disconnect(req.session_id).__dict__
    except TestbenchSessionError as exc:
        raise HTTPException(400, {"message": "testbench tcp session is invalid", "error": str(exc)}) from exc


class I2cScanRequest(BaseModel):
    session_id: str
    controller_id: str
    muxes: list[dict] = []
    timeout_s: float = 10.0


@router.post("/testbench/i2c-scan")
def testbench_i2c_scan(req: I2cScanRequest) -> dict:
    from backend.i2c_scan import I2cScanError, scan_bus

    try:
        return scan_bus(req.session_id, req.controller_id, req.muxes, timeout_s=req.timeout_s)
    except I2cScanError as exc:
        raise HTTPException(502, {"message": "i2c taramasi basarisiz", "error": str(exc)}) from exc
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "testbench session is not usable", "error": str(exc)}) from exc
    except OSError as exc:
        raise HTTPException(502, {"message": "i2c taramasi transport hatasi", "error": str(exc)}) from exc


class RegisterSnapshotRequest(BaseModel):
    session_id: str
    device_id: str
    registers: list[dict]
    timeout_s: float = 5.0


@router.post("/registers/snapshot")
def registers_snapshot(req: RegisterSnapshotRequest) -> dict:
    if not req.registers:
        raise HTTPException(400, "registers list is empty")
    return snapshot_registers(
        req.session_id, req.device_id, req.registers, timeout_s=req.timeout_s)


_DURUM_DESTEKLENMIYOR = 7  # bkz. backend/s2cmsg.py STATUS_LABELS


class CitRequest(BaseModel):
    session_id: str
    manifest: dict
    timeout_s: float = 10.0


def _cit_run_or_read(name: str, req: CitRequest) -> dict:
    if not (req.manifest or {}).get("cit"):
        raise HTTPException(400, "bu uretimde CIT olcumu yok")
    try:
        prefix, raw_body = testbench_sessions.send_named(req.session_id, name, timeout_s=req.timeout_s)
    except TestbenchSessionError as exc:
        raise HTTPException(409, {"message": "testbench session is not usable", "error": str(exc)}) from exc
    except OSError as exc:
        raise HTTPException(502, {"message": "CIT transport hatasi", "error": str(exc)}) from exc
    if prefix.get("durum") == _DURUM_DESTEKLENMIYOR:
        return {"durum": prefix["durum"], "sayac": 0, "zaman": 0, "olcumler": [], "desteklenmiyor": True}
    body = struct.pack("<II", prefix["istek_sayac"], prefix["durum"]) + raw_body
    try:
        return decode_board_cit(body, req.manifest)
    except ValueError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.post("/testbench/cit/run")
def testbench_cit_run(req: CitRequest) -> dict:
    return _cit_run_or_read("CIT_RUN", req)


@router.post("/testbench/cit/read")
def testbench_cit_read(req: CitRequest) -> dict:
    return _cit_run_or_read("CIT_READ", req)


@router.get("/yatt/catalog")
def yatt_catalog_route() -> dict:
    """S2C-MSG mesaj kataloğu (frontend YattPanel tablosu için)."""
    catalog = s2cmsg.load_catalog()
    return {
        "messages": catalog["messages"],
        "header": catalog["header"],
        "crc32": f"0x{s2cmsg.catalog_crc32():08X}",
        "status_codes": catalog.get("status_codes") or {str(k): v for k, v in s2cmsg.STATUS_LABELS.items()},
    }


class YattExportRequest(BaseModel):
    fmt: Literal["html", "md"]
    manifest: dict | None = None


@router.post("/yatt/export")
def yatt_export_route(req: YattExportRequest) -> Response:
    """YATT sayfasini self-contained HTML/MD olarak indirir (manifest verilirse cihaz/CIT tablolari dahil)."""
    catalog = s2cmsg.load_catalog()
    if req.fmt == "html":
        content = yatt.build_yatt_html(catalog, req.manifest)
        media_type, ext = "text/html", "html"
    else:
        content = yatt.build_yatt_markdown(catalog, req.manifest)
        media_type, ext = "text/markdown", "md"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="yatt.{ext}"'},
    )


class BringupStartRequest(BaseModel):
    session_id: str
    manifest: dict
    include_init: bool = True
    timeout_s: float = 5.0


@router.post("/bringup/start")
async def bringup_start(req: BringupStartRequest) -> dict:
    job_id = await bringup_manager.start(BringupConfig(
        session_id=req.session_id,
        manifest=req.manifest,
        include_init=req.include_init,
        timeout_s=req.timeout_s,
    ))
    return {"bringup_job_id": job_id}


@router.get("/bringup/{job_id}/result")
def bringup_result(job_id: str) -> dict:
    job = bringup_manager.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown bring-up job")
    return {
        "bringup_job_id": job_id,
        "status": job.status,
        "error": job.error,
        "result": job.result,
    }


@router.get("/bringup/{job_id}/certificate")
def bringup_certificate(job_id: str) -> HTMLResponse:
    job = bringup_manager.get(job_id)
    if job is None or not job.result:
        raise HTTPException(404, "bring-up result is not ready")
    return HTMLResponse(
        content=render_certificate_html(job.result),
        headers={"Content-Disposition": f'attachment; filename="board_birth_certificate_{job_id}.html"'},
    )


@router.get("/testbench/session/{session_id}")
def testbench_session_status(session_id: str) -> dict:
    try:
        return testbench_sessions.status(session_id).__dict__
    except TestbenchSessionError as exc:
        raise HTTPException(400, {"message": "testbench tcp session is invalid", "error": str(exc)}) from exc


@router.get("/jobs/{job_id}/files/{file_path:path}")
def download_job_file(job_id: str, file_path: str) -> FileResponse:
    job = _job_with_result(job_id)
    path, normalized = _resolve_job_file(job, file_path)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=Path(normalized).name,
    )


@router.post("/drivers/scan")
def drivers_scan(req: ScanRequest) -> dict:
    try:
        matches = scan_folder(req.folder)
    except (NotADirectoryError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc))
    return {"matches": [m.__dict__ for m in matches]}


@router.post("/drivers/confirm")
def drivers_confirm(req: ConfirmRequest) -> dict:
    imported = json.loads(_IMPORTED.read_text(encoding="utf-8")) if _IMPORTED.is_file() else {}
    imported[req.part] = {"stem": req.stem, "role": req.role, "files": req.files}
    _IMPORTED.write_text(json.dumps(imported, indent=2), encoding="utf-8")
    return {"ok": True, "imported": imported[req.part]}


# BU ROTA DOSYANIN SONUNDA KALMALI (Starlette kayıt sırasına göre eşler;
# üstteki gerçek uçlar önce yakalar). Bilinmeyen /api yolları eskiden SPA
# statik sunucusuna düşüp POST'ta şaşırtıcı bir "405 Method Not Allowed"
# üretiyordu (saha bulgusu: eski backend süreci yeni ucu tanımayınca) —
# şimdi her metotta dürüst 404 + yönlendirme döner.
@router.api_route("/{unknown_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"], include_in_schema=False)
def unknown_api_path(unknown_path: str) -> dict:
    raise HTTPException(
        404,
        f"Bilinmeyen API ucu: /api/{unknown_path}. Çalışan backend bu ucu "
        "tanımıyor — uygulama sürümünüz eski olabilir: uygulamayı kapatıp "
        "yeniden başlatın ya da güncel release'i kullanın.",
    )
