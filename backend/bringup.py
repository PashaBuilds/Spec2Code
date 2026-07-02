"""Bring-up wizard: dependency-ordered device checks over a live test bench session.

The plan is derived from the generated test bench manifest: power monitors
first (rails must be sane), then sensors, clock tree, memories and RF.
Every step sends one S2C command through the existing TCP/serial session
and records the parsed verdict. Failures do not abort the run - a board
birth certificate needs the full picture, not the first bad news.
"""

from __future__ import annotations

import asyncio
import html
import time
import traceback
from dataclasses import dataclass, field
from typing import Optional

from backend.testbench import TestbenchCommand, TestbenchSessionError, testbench_sessions

CATEGORY_ORDER = ["power", "sensor", "clock", "memory", "rf", "other"]
CATEGORY_LABELS = {
    "power": "Güç / izleme",
    "sensor": "Sensörler",
    "clock": "Saat ağacı",
    "memory": "Bellekler",
    "rf": "RF / beamformer",
    "other": "Diğer",
}
_PART_CATEGORY = {
    "LTC2945": "power",
    "LTC2991": "power",
    "AD7414": "sensor",
    "TMP101": "sensor",
    "SHT21": "sensor",
    "LMK04832": "clock",
    "LMX2820": "clock",
    "MT25Q128": "memory",
    "MT25QU02G": "memory",
    "24LC32A": "memory",
    "DS1682": "memory",
    "ADAR1000": "rf",
}


def part_category(part: str) -> str:
    return _PART_CATEGORY.get(part.upper(), "other")


@dataclass
class BringupStep:
    device_id: str
    part: str
    operation: str
    label: str
    category: str
    risk: str


@dataclass
class BringupConfig:
    session_id: str
    manifest: dict
    include_init: bool = True
    timeout_s: float = 5.0


@dataclass
class BringupJob:
    id: str
    config: BringupConfig
    status: str = "pending"            # pending | running | done | error
    events: list[dict] = field(default_factory=list)
    subscribers: set = field(default_factory=set)
    result: Optional[dict] = None
    error: Optional[str] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, event: dict) -> None:
        event = {**event, "_seq": len(self.events)}
        self.events.append(event)
        loop = self._loop
        if loop is None:
            return
        for queue in list(self.subscribers):
            loop.call_soon_threadsafe(queue.put_nowait, event)


def _step_sort_key(op_name: str) -> tuple[int, str]:
    lowered = op_name.lower()
    if "id" in lowered:
        return (0, lowered)
    if "status" in lowered or "lock" in lowered:
        return (1, lowered)
    return (2, lowered)


def build_plan(manifest: dict, *, include_init: bool = True) -> list[BringupStep]:
    steps: list[BringupStep] = []
    for device in manifest.get("devices", []):
        operations = device.get("operations", [])
        chosen: list[dict] = []
        if include_init:
            chosen.extend(op for op in operations if op.get("name") == "device_init")
        safe = [op for op in operations if op.get("risk") == "safe"]
        safe.sort(key=lambda op: _step_sort_key(str(op.get("name", ""))))
        chosen.extend(safe)
        for op in chosen:
            # Ops that need a manual address/data payload cannot run unattended.
            if op.get("requires_address") or op.get("requires_data") or op.get("requires_value"):
                continue
            steps.append(BringupStep(
                device_id=str(device.get("id", "")),
                part=str(device.get("part", "")),
                operation=str(op.get("name", "")),
                label=str(op.get("label", "")),
                category=part_category(str(device.get("part", ""))),
                risk=str(op.get("risk", "safe")),
            ))
    steps.sort(key=lambda step: CATEGORY_ORDER.index(step.category))  # stable within category
    return steps


class BringupJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, BringupJob] = {}
        self._counter = 0

    def get(self, job_id: str) -> Optional[BringupJob]:
        return self._jobs.get(job_id)

    async def start(self, config: BringupConfig) -> str:
        self._counter += 1
        job_id = f"bringup_{self._counter:04d}"
        job = BringupJob(id=job_id, config=config, _loop=asyncio.get_running_loop())
        self._jobs[job_id] = job
        asyncio.create_task(self._run(job))
        return job_id

    async def _run(self, job: BringupJob) -> None:
        job.status = "running"
        job.emit({"event": "bringup.start", "stage": "start", "progress": 2,
                  "message": "Bring-up sırası çalışıyor..."})
        try:
            await asyncio.to_thread(self._blocking, job)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - surface session failures directly
            job.status = "error"
            job.error = str(exc)
            job.emit({"event": "bringup.error", "stage": "error", "progress": 100,
                      "message": str(exc),
                      "trace": traceback.format_exc().splitlines()[-5:]})
        finally:
            final_stage = "done" if job.status == "done" else "error"
            job.emit({"event": "bringup.end", "stage": final_stage, "progress": 100,
                      "status": job.status})
            loop = job._loop
            if loop is not None:
                for queue in list(job.subscribers):
                    loop.call_soon_threadsafe(queue.put_nowait, None)

    def _blocking(self, job: BringupJob) -> None:
        config = job.config
        manifest = config.manifest
        plan = build_plan(manifest, include_init=config.include_init)
        if not plan:
            raise ValueError("bring-up planı boş: manifest'te çalıştırılabilir operasyon yok")

        started_at = time.time()
        results: list[dict] = []
        total = len(plan)
        job.emit({"event": "bringup.plan", "stage": "plan", "progress": 4,
                  "total": total,
                  "steps": [{
                      "index": index,
                      "device_id": step.device_id,
                      "part": step.part,
                      "operation": step.operation,
                      "label": step.label,
                      "category": step.category,
                      "risk": step.risk,
                  } for index, step in enumerate(plan)],
                  "message": f"{total} adımlık plan hazırlandı."})

        for index, step in enumerate(plan):
            progress = 5 + int(90 * index / total)
            job.emit({"event": "bringup.step_start", "stage": "run", "progress": progress,
                      "index": index, "device_id": step.device_id, "part": step.part,
                      "operation": step.operation, "category": step.category,
                      "message": f"{step.part} • {step.operation}"})
            step_started = time.time()
            entry = {
                "index": index,
                "device_id": step.device_id,
                "part": step.part,
                "operation": step.operation,
                "label": step.label,
                "category": step.category,
                "risk": step.risk,
                "ok": False,
                "status": None,
                "value": "",
                "data": "",
                "response_message": "",
                "error": "",
                "duration_ms": 0,
            }
            try:
                result = testbench_sessions.send(config.session_id, TestbenchCommand(
                    host="", port=0,
                    device=step.device_id,
                    operation=step.operation,
                    command_id=index + 1,
                    timeout_s=config.timeout_s,
                ))
                parsed = result.parsed
                entry["ok"] = parsed.get("ok") == "1"
                entry["status"] = parsed.get("status")
                entry["value"] = parsed.get("value", "")
                entry["data"] = parsed.get("data", "")
                entry["response_message"] = parsed.get("message", "")
            except (TestbenchSessionError, OSError) as exc:
                entry["error"] = str(exc)
            entry["duration_ms"] = int((time.time() - step_started) * 1000)
            results.append(entry)
            job.emit({"event": "bringup.step_done", "stage": "run",
                      "progress": 5 + int(90 * (index + 1) / total),
                      "index": index, "ok": entry["ok"],
                      "value": entry["value"], "data": entry["data"],
                      "status": entry["status"], "error": entry["error"],
                      "duration_ms": entry["duration_ms"],
                      "message": f"{step.part} • {step.operation}: "
                                 + ("OK" if entry["ok"] else (entry["error"] or "FAIL"))})
            # A dead session fails everything downstream identically; stop early.
            if entry["error"] and "not connected" in entry["error"]:
                for later_index, later in enumerate(plan[index + 1:], start=index + 1):
                    results.append({
                        "index": later_index, "device_id": later.device_id, "part": later.part,
                        "operation": later.operation, "label": later.label,
                        "category": later.category, "risk": later.risk,
                        "ok": False, "status": None, "value": "", "data": "",
                        "response_message": "", "error": "atlandı: bağlantı koptu",
                        "duration_ms": 0,
                    })
                break

        passed = sum(1 for item in results if item["ok"])
        job.result = {
            "project": manifest.get("project", ""),
            "agent_version": manifest.get("agent_version", ""),
            "transport_agent": manifest.get("transport_agent"),
            "include_init": config.include_init,
            "started_at": started_at,
            "finished_at": time.time(),
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "steps": results,
        }
        job.emit({"event": "bringup.summary", "stage": "run", "progress": 97,
                  "passed": passed, "failed": len(results) - passed,
                  "message": f"Bring-up bitti: {passed}/{len(results)} adım geçti."})


def render_certificate_html(result: dict) -> str:
    """Standalone 'board birth certificate' HTML (printable, air-gap safe)."""
    project = html.escape(str(result.get("project", "")))
    agent = html.escape(str(result.get("agent_version", "")))
    transport = html.escape(str(result.get("transport_agent") or "-"))
    finished = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(result.get("finished_at", time.time())))
    total = int(result.get("total", 0))
    passed = int(result.get("passed", 0))
    failed = int(result.get("failed", 0))
    verdict_ok = failed == 0 and total > 0
    verdict = "GEÇTİ" if verdict_ok else "KOŞULLU / HATALI"
    verdict_color = "#1d8348" if verdict_ok else "#b03a2e"

    rows: list[str] = []
    current_category = None
    for step in result.get("steps", []):
        category = str(step.get("category", "other"))
        if category != current_category:
            current_category = category
            label = html.escape(CATEGORY_LABELS.get(category, category))
            rows.append(f'<tr class="cat"><td colspan="6">{label}</td></tr>')
        ok = bool(step.get("ok"))
        state = "OK" if ok else ("HATA" if not step.get("error") else "HATA*")
        detail = step.get("value") or step.get("data") or step.get("response_message") or step.get("error") or ""
        rows.append(
            "<tr>"
            f'<td class="mono">{html.escape(str(step.get("part", "")))}</td>'
            f'<td class="mono">{html.escape(str(step.get("device_id", "")))}</td>'
            f'<td>{html.escape(str(step.get("label") or step.get("operation", "")))}</td>'
            f'<td class="mono">{html.escape(str(step.get("operation", "")))}</td>'
            f'<td class="{"ok" if ok else "fail"}">{state}</td>'
            f'<td class="mono detail">{html.escape(str(detail))[:96]}</td>'
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Board Birth Certificate — {project}</title>
<style>
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 40px auto; max-width: 900px; color: #1c2833; }}
  h1 {{ font-size: 22px; margin-bottom: 2px; }}
  .sub {{ color: #566573; font-size: 13px; margin-bottom: 24px; }}
  .verdict {{ display: inline-block; padding: 6px 16px; border-radius: 6px; color: white; font-weight: 700;
             background: {verdict_color}; letter-spacing: 0.06em; }}
  .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 26px; }}
  .meta div {{ border: 1px solid #d5dbdb; border-radius: 8px; padding: 10px 12px; }}
  .meta b {{ display: block; font-size: 11px; color: #7b8a8b; text-transform: uppercase; letter-spacing: 0.08em; }}
  .meta span {{ font-size: 15px; font-family: Consolas, monospace; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ border-bottom: 1px solid #e5e8e8; padding: 7px 8px; text-align: left; }}
  th {{ background: #f4f6f6; font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: #566573; }}
  tr.cat td {{ background: #eaf2f8; font-weight: 700; font-size: 12px; letter-spacing: 0.05em; }}
  td.ok {{ color: #1d8348; font-weight: 700; }}
  td.fail {{ color: #b03a2e; font-weight: 700; }}
  .mono {{ font-family: Consolas, monospace; }}
  .detail {{ font-size: 11px; color: #566573; }}
  footer {{ margin-top: 28px; font-size: 11px; color: #7b8a8b; border-top: 1px solid #e5e8e8; padding-top: 10px; }}
  @media print {{ body {{ margin: 10mm; }} }}
</style>
</head>
<body>
  <h1>Board Birth Certificate</h1>
  <div class="sub">Spec2Code bring-up raporu — kartın ilk nefesinin kaydı.</div>
  <span class="verdict">{verdict}</span>
  <div class="meta">
    <div><b>Proje</b><span>{project}</span></div>
    <div><b>Tarih</b><span>{finished}</span></div>
    <div><b>Sonuç</b><span>{passed}/{total} geçti</span></div>
    <div><b>Agent</b><span>{agent} ({transport})</span></div>
  </div>
  <table>
    <thead>
      <tr><th>Entegre</th><th>Cihaz</th><th>Adım</th><th>Operasyon</th><th>Durum</th><th>Değer / mesaj</th></tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <footer>Spec2Code {agent} tarafından üretildi • adım cevapları S2C satır protokolünden ayrıştırıldı • HATA* = haberleşme hatası</footer>
</body>
</html>
"""


bringup_manager = BringupJobManager()
