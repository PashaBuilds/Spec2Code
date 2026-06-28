"""REST API routes (Brief 18). Thin orchestration over the existing modules."""

from __future__ import annotations

import json
import io
import os
import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from jsonschema import Draft7Validator
from pydantic import BaseModel, Field

from backend.jobs import manager
from backend.parsers.xparameters import parse_xparameters
from backend.rulesets import DEFAULT_RULESET, RULESET_SCHEMA
from backend.validators.wiring import validate_wiring
from catalog.matcher import scan_folder
from hostplat import io as hio
from hostplat import tools
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
        "- `src/spec2code_selftest_main.c`: self-testleri topluca cagiran ornek runner.\n"
        "- `meta/project.spec.json`: bu paketi ureten canonical spec.\n"
        "- `meta/qc_report.json`: son QC raporu.\n\n"
        "## Vitis'e aktarma\n\n"
        "1. `src/drivers` altindaki `.c` ve `.h` dosyalarini Vitis application source tree'ye ekle.\n"
        "2. Self-test kullanacaksan `src/tests` ve `src/spec2code_selftest_main.c` dosyalarini da ekle.\n"
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


@router.get("/catalog")
def get_catalog() -> dict:
    catalog = json.loads(_CATALOG.read_text(encoding="utf-8"))
    if _IMPORTED.is_file():
        catalog["imported"] = json.loads(_IMPORTED.read_text(encoding="utf-8"))
    return catalog


@router.get("/descriptors")
def list_descriptors() -> dict:
    items = []
    for path in sorted(_DESCRIPTORS.glob("*.yaml")):
        d = yaml.safe_load(path.read_text(encoding="utf-8"))
        items.append({"part": d.get("part"), "ref": f"descriptors/{path.name}",
                      "transport": d.get("transport", {}).get("type"),
                      "summary": d.get("summary", ""),
                      "operations": [op["name"] for op in d.get("operations", [])]})
    return {"descriptors": items}


@router.get("/descriptors/{part}")
def get_descriptor(part: str) -> dict:
    path = _DESCRIPTORS / f"{part.lower()}.yaml"
    if not path.is_file():
        raise HTTPException(404, f"no descriptor for '{part}'")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


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
    max_context_chars = 90_000
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n[context burada kesildi]"

    messages = [
        {
            "role": "system",
            "content": (
                "Sen Spec2Code icindeki statik datasheet knowledge paketini cevaplayan bir gomulu yazilim "
                "yardimcisisin. Sadece verilen KNOWLEDGE CONTEXT icindeki bilgilere dayan. Contextte olmayan "
                "bir bilgiyi tahmin etme; bunun yerine 'Bu bilgi verilen knowledge icinde yok' de. "
                "Cevaplari Turkce cumlelerle ver; register, bit field, driver, readback, opcode gibi teknik "
                "terimleri gerektiğinde Ingilizce kullan. Register adresi, bit field adi, read/write akisi, "
                "TX/RX byte boyutu ve driver fonksiyon adi contextte varsa mutlaka belirt."
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
        answer = LlmClient(config).chat(messages, temperature=0.0, max_tokens=min(config.max_tokens, 2048))
    except LlmError as exc:
        raise HTTPException(502, {"message": "llm failed", "error": str(exc)}) from exc

    return {
        "part": req.part,
        "model": config.model,
        "answer": answer,
        "context_chars": len(context),
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
