"""REST API routes (Brief §18). Thin orchestration over the existing modules."""

from __future__ import annotations

import json
import io
import re
import zipfile
from pathlib import Path
from pathlib import PurePosixPath

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response
from jsonschema import Draft7Validator
from pydantic import BaseModel

from backend.jobs import manager
from backend.parsers.xparameters import parse_xparameters
from catalog.matcher import scan_folder
from hostplat import io as hio
from hostplat import tools

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


@router.post("/spec/validate")
def validate_spec(req: ValidateRequest) -> dict:
    errors = sorted(Draft7Validator(_SPEC_SCHEMA).iter_errors(req.spec), key=lambda e: list(e.path))
    return {
        "valid": not errors,
        "errors": [{"path": "/".join(map(str, e.path)), "message": e.message} for e in errors],
    }


@router.post("/generate")
async def generate(req: GenerateRequest) -> dict:
    errors = list(Draft7Validator(_SPEC_SCHEMA).iter_errors(req.spec))
    if errors:
        raise HTTPException(400, {"message": "spec invalid",
                                  "errors": [e.message for e in errors[:5]]})
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
