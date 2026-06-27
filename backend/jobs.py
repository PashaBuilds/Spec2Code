"""Generate-job manager (Brief 18).

A generate job writes the spec, runs deterministic codegen + the QC loop in a worker thread,
and streams structured pipeline events to any number of WebSocket subscribers. Events are
buffered (with sequence numbers) so a late subscriber replays from the start with no gaps and
no duplicates.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from orchestrator import codegen
from orchestrator.qc import loop as qc_loop
from backend.rulesets import DEFAULT_RULESET_REF, resolve_ruleset_ref

_ROOT = Path(__file__).resolve().parent.parent
_OUTPUTS = _ROOT / "outputs"
_SPECS = _ROOT / "specs"
_IMPORTED = _ROOT / "catalog" / "imported.json"


def _load_ruleset(spec: dict) -> dict:
    spec["coding_standard_ref"] = DEFAULT_RULESET_REF
    path = resolve_ruleset_ref(DEFAULT_RULESET_REF)
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_spec(spec: dict) -> dict:
    return {**spec, "coding_standard_ref": DEFAULT_RULESET_REF}


def _relative_to_root(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _reset_output_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    resolved.relative_to(_OUTPUTS.resolve())
    if out_dir.exists():
        shutil.rmtree(out_dir)


def _collect_output_files(out_dir: Path) -> list[Path]:
    return sorted(
        (path for path in out_dir.rglob("*") if path.is_file()),
        key=lambda path: path.relative_to(out_dir).as_posix(),
    )


def _module_of(part: str) -> str:
    return "".join(ch for ch in part.lower() if ch.isalnum()) or "part"


def _copy_imported_sources(spec: dict, out_dir: Path, emit) -> None:
    if not _IMPORTED.is_file():
        return
    try:
        imported = json.loads(_IMPORTED.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        emit({"event": "imported_sources.error", "message": "catalog/imported.json is invalid"})
        return

    used_parts = {item.get("part") for item in [*spec.get("devices", []), *spec.get("muxes", [])]}
    copied = 0
    missing: list[str] = []
    manifest: dict[str, dict] = {}
    for part in sorted(p for p in used_parts if p):
        entry = imported.get(part)
        if not entry:
            continue
        target_dir = out_dir / "reference_sources" / _module_of(part)
        target_dir.mkdir(parents=True, exist_ok=True)
        copied_files: list[str] = []
        for file_name in entry.get("files", []):
            source = Path(file_name)
            if not source.is_file():
                missing.append(file_name)
                continue
            target = target_dir / source.name
            shutil.copy2(source, target)
            copied_files.append(target.relative_to(out_dir).as_posix())
            copied += 1
        manifest[part] = {
            "role": entry.get("role", "as_is"),
            "source_files": entry.get("files", []),
            "copied_files": copied_files,
        }

    if manifest:
        target = out_dir / "reference_sources" / "manifest.json"
        target.write_text(json.dumps({"parts": manifest, "missing": missing}, indent=2), encoding="utf-8")
        emit({"event": "imported_sources.copied", "files": copied, "missing": len(missing)})


@dataclass
class Job:
    id: str
    spec: dict
    status: str = "pending"            # pending | running | done | error
    events: list[dict] = field(default_factory=list)
    subscribers: set = field(default_factory=set)
    result: Optional[dict] = None
    error: Optional[str] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, event: dict) -> None:
        """Thread-safe: append (with seq) and fan out to subscriber queues."""
        event = {**event, "_seq": len(self.events)}
        self.events.append(event)
        loop = self._loop
        if loop is None:
            return
        for q in list(self.subscribers):
            loop.call_soon_threadsafe(q.put_nowait, event)


class JobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._counter = 0

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def start(self, spec: dict, *, max_rounds: int = 3) -> str:
        self._counter += 1
        job_id = f"job_{self._counter:04d}"
        spec = _normalize_spec(spec)
        job = Job(id=job_id, spec=spec, _loop=asyncio.get_running_loop())
        self._jobs[job_id] = job

        # Persist the spec (canonical handoff artifact) before generating.
        name = spec["project"]["name"]
        spec_path = _SPECS / name / "project.spec.json"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")

        asyncio.create_task(self._run(job, max_rounds))
        return job_id

    async def _run(self, job: Job, max_rounds: int) -> None:
        job.status = "running"
        job.emit({"event": "job.start", "project": job.spec["project"]["name"]})
        try:
            await asyncio.to_thread(self._blocking, job, max_rounds)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - surface any failure to the console
            job.status = "error"
            job.error = str(exc)
            job.emit({"event": "error", "message": str(exc),
                      "trace": traceback.format_exc().splitlines()[-3:]})
        finally:
            job.emit({"event": "job.end", "status": job.status})
            # wake subscribers with a sentinel
            loop = job._loop
            if loop is not None:
                for q in list(job.subscribers):
                    loop.call_soon_threadsafe(q.put_nowait, None)

    def _blocking(self, job: Job, max_rounds: int) -> None:
        spec = job.spec
        out_dir = _OUTPUTS / spec["project"]["name"]
        _reset_output_dir(out_dir)
        codegen.generate(spec, out_dir, emit=job.emit)
        _copy_imported_sources(spec, out_dir, job.emit)
        ruleset = _load_ruleset(spec)
        fixer = _maybe_llm_fixer(spec, ruleset, emit=job.emit)
        report = qc_loop.run_qc(out_dir, ruleset, max_rounds=max_rounds, emit=job.emit, fixer=fixer)
        files = _collect_output_files(out_dir)
        job.result = {
            "out_dir": _relative_to_root(out_dir),
            "files": [_relative_to_root(path) for path in files],
            "qc": report,
        }
        job.emit({"event": "result.ready", "files": len(files), "qc_passed": report["passed"]})


def _maybe_llm_fixer(spec: dict, ruleset: dict, emit=None):
    """Return an LLM-backed QC fixer when llm.enabled, else None (deterministic path)."""
    if not spec.get("llm", {}).get("enabled"):
        return None
    try:
        from orchestrator.llm.tasks import make_qc_fixer
        return make_qc_fixer(spec, ruleset, emit=emit)
    except Exception as exc:
        if emit is not None:
            emit({"event": "llm.error", "task": "setup", "message": str(exc)})
        return None


manager = JobManager()
