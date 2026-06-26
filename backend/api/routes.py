"""REST API routes (Brief §18). Thin orchestration over the existing modules."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from jsonschema import Draft7Validator
from pydantic import BaseModel

from backend.jobs import manager
from backend.parsers.xparameters import parse_xparameters
from catalog.matcher import scan_folder
from hostplat import tools

_ROOT = Path(__file__).resolve().parent.parent.parent
_PLATFORMS = _ROOT / "platforms"
_DESCRIPTORS = _ROOT / "descriptors"
_CATALOG = _ROOT / "catalog" / "catalog.json"
_IMPORTED = _ROOT / "catalog" / "imported.json"
_SPEC_SCHEMA = json.loads((_ROOT / "schemas" / "project.spec.schema.json").read_text())

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
    return yaml.safe_load(path.read_text())


# --- endpoints --------------------------------------------------------------------------

@router.get("/health")
def health() -> dict:
    return {"status": "ok", "tools": tools.status()}


@router.get("/platforms")
def list_platforms() -> dict:
    items = []
    for path in sorted(_PLATFORMS.glob("*.yaml")):
        model = yaml.safe_load(path.read_text())
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
    catalog = json.loads(_CATALOG.read_text())
    if _IMPORTED.is_file():
        catalog["imported"] = json.loads(_IMPORTED.read_text())
    return catalog


@router.get("/descriptors")
def list_descriptors() -> dict:
    items = []
    for path in sorted(_DESCRIPTORS.glob("*.yaml")):
        d = yaml.safe_load(path.read_text())
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
    return yaml.safe_load(path.read_text())


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
    job = manager.get(job_id)
    if job is None:
        raise HTTPException(404, "unknown job")
    files = []
    if job.result:
        for rel in job.result["files"]:
            p = _ROOT / rel
            files.append({"path": rel, "name": Path(rel).name,
                          "content": p.read_text() if p.is_file() else ""})
    return {"job_id": job_id, "status": job.status, "error": job.error,
            "result": job.result, "files": files}


@router.post("/drivers/scan")
def drivers_scan(req: ScanRequest) -> dict:
    try:
        matches = scan_folder(req.folder)
    except (NotADirectoryError, FileNotFoundError) as exc:
        raise HTTPException(400, str(exc))
    return {"matches": [m.__dict__ for m in matches]}


@router.post("/drivers/confirm")
def drivers_confirm(req: ConfirmRequest) -> dict:
    imported = json.loads(_IMPORTED.read_text()) if _IMPORTED.is_file() else {}
    imported[req.part] = {"stem": req.stem, "role": req.role, "files": req.files}
    _IMPORTED.write_text(json.dumps(imported, indent=2))
    return {"ok": True, "imported": imported[req.part]}
