"""Build & Run on Board: program the target over JTAG with xsdb and start the app.

Standard ZynqMP JTAG bring-up (Vitis "Run on hardware" order, UG1400):
system reset -> psu_init (from the platform's psu_init.tcl) -> optional PL
bitstream -> download ELF to the APU core -> continue. The board must be in
JTAG boot mode and hw_server reachable: with no hw_server URL xsdb `connect`
starts a local one (USB JTAG cable); with a URL it connects to a remote
hw_server such as the one built into a SmartLynq/SmartLynq+ data cable
(`connect -url TCP:<ip>:3121`).
"""

from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from backend.vitis_workspace import (
    _clean_user_path,
    _run_xsct_streaming,
    _version_key,
)

RUN_STALL_TIMEOUT_S = 120
RUN_STALL_GRACE_S = 60

DEFAULT_HW_SERVER_PORT = 3121


def normalize_hw_server_url(value: str) -> str:
    """Canonicalize a remote hw_server address to xsdb's ``TCP:<host>:<port>`` form.

    Accepts what users typically paste for a SmartLynq / remote hw_server:
    ``192.168.0.10``, ``192.168.0.10:3121``, ``TCP:192.168.0.10:3121`` or
    ``tcp://smartlynq-hostname``. An empty value means local USB JTAG and
    returns ''. The port defaults to 3121 (hw_server / SmartLynq default).
    """
    text = (value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    for prefix in ("tcp://", "tcp:"):
        if lowered.startswith(prefix):
            text = text[len(prefix):]
            break
    if ":" in text:
        host, _, port = text.rpartition(":")
    else:
        host, port = text, str(DEFAULT_HW_SERVER_PORT)
    host = host.strip()
    port = port.strip() or str(DEFAULT_HW_SERVER_PORT)
    if not host or not port.isdigit():
        raise ValueError(
            f"geçersiz hw_server adresi: '{value}'. Beklenen biçim: <ip|host>[:port], "
            f"örn. SmartLynq için 192.168.0.10 veya TCP:192.168.0.10:3121")
    return f"TCP:{host}:{port}"


@dataclass
class RunOnBoardConfig:
    vitis_path: str
    workspace_path: str
    platform_name: str
    app_name: str
    processor: str = "psu_cortexa53_0"
    platform: str = "zynq_ultrascale"  # zynq_ultrascale | zynq_7000 | versal
    program_fpga: str = "auto"  # auto | yes | no (versal: PL is inside the PDI)
    hw_server_url: str = ""  # boş = lokal USB JTAG; SmartLynq/uzak hw_server için <ip>[:port]
    timeout_s: int = 300


@dataclass
class RunOnBoardJob:
    id: str
    config: RunOnBoardConfig
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


def _candidate_xsdb_paths(root: Path) -> list[Path]:
    executable_names = ("xsdb.bat", "xsdb.cmd", "xsdb.exe", "xsdb")
    if root.is_file():
        return [root]
    candidates: list[Path] = []
    for name in executable_names:
        candidates.append(root / "bin" / name)
        candidates.append(root / name)
    for base in (root / "Vitis", root):
        if base.is_dir():
            for child in sorted(base.iterdir(), key=_version_key, reverse=True):
                if child.is_dir():
                    for name in executable_names:
                        candidates.append(child / "bin" / name)
    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def locate_xsdb(vitis_path: str) -> Path:
    root = _clean_user_path(vitis_path)
    for candidate in _candidate_xsdb_paths(root):
        if candidate.is_file():
            return candidate
    searched = "\n".join(str(path) for path in _candidate_xsdb_paths(root)[:12])
    raise FileNotFoundError(f"xsdb executable not found under '{root}'. Searched:\n{searched}")


def find_application_elf(workspace: Path, app_name: str) -> Path:
    for candidate in (
        workspace / app_name / "Debug" / f"{app_name}.elf",
        workspace / app_name / "Release" / f"{app_name}.elf",
    ):
        if candidate.is_file():
            return candidate
    matches = sorted((workspace / app_name).glob(f"**/{app_name}.elf")) if (workspace / app_name).is_dir() else []
    if matches:
        return matches[0]
    raise FileNotFoundError(
        f"application ELF not found: {workspace / app_name / 'Debug' / (app_name + '.elf')}")


def _find_init_tcl(workspace: Path, platform_name: str, init_name: str) -> Path:
    platform_dir = workspace / platform_name
    for candidate in (
        platform_dir / "hw" / init_name,
        platform_dir / "export" / platform_name / "hw" / init_name,
    ):
        if candidate.is_file():
            return candidate
    matches = sorted(platform_dir.glob(f"**/{init_name}")) if platform_dir.is_dir() else []
    if matches:
        return matches[0]
    raise FileNotFoundError(f"{init_name} not found under platform '{platform_dir}'")


def find_psu_init(workspace: Path, platform_name: str) -> Path:
    return _find_init_tcl(workspace, platform_name, "psu_init.tcl")


def find_ps7_init(workspace: Path, platform_name: str) -> Path:
    return _find_init_tcl(workspace, platform_name, "ps7_init.tcl")


def find_bitstream(workspace: Path, platform_name: str) -> Path | None:
    platform_dir = workspace / platform_name
    if not platform_dir.is_dir():
        return None
    for candidate in sorted(platform_dir.glob("hw/*.bit")) + sorted(platform_dir.glob("**/*.bit")):
        return candidate
    return None


def find_pdi(workspace: Path, platform_name: str) -> Path:
    """Versal boot image: PLM + PL + NoC config in one PDI inside the platform."""
    platform_dir = workspace / platform_name
    if platform_dir.is_dir():
        for candidate in sorted(platform_dir.glob("hw/*.pdi")) + sorted(platform_dir.glob("**/*.pdi")):
            return candidate
    raise FileNotFoundError(f"boot .pdi not found under platform '{platform_dir}'")


def _tcl_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _core_filter(processor: str) -> str:
    lowered = processor.lower()
    if "a72" in lowered:
        return '"*A72*#0"'
    if "a53" in lowered:
        return '"*A53*#0"'
    if "a9" in lowered:
        return '"*A9*#0"'
    if "r5" in lowered:
        return '"*R5*#0"'
    return '"*#0"'


def render_run_on_board_script(
    *,
    elf_path: Path,
    processor: str,
    platform: str = "zynq_ultrascale",
    psu_init_path: Path | None = None,
    ps7_init_path: Path | None = None,
    bitstream_path: Path | None = None,
    pdi_path: Path | None = None,
    hw_server_url: str = "",
) -> str:
    """xsdb Tcl for the classic JTAG run flow, per platform.

    zynq_ultrascale: rst -system -> psu_init -> [fpga .bit] -> A53/R5 -> dow -> con
    zynq_7000:       rst -system -> ps7_init -> [fpga .bit] -> A9 -> dow -> ps7_post_config -> con
    versal:          device program <pdi> (PLM+PL) -> A72 -> dow -> con

    hw_server_url (canonical ``TCP:<host>:<port>``) switches the connect from
    the local hw_server to a remote one, e.g. a SmartLynq cable's built-in
    hw_server over Ethernet.

    The S2C-RUN marker lines let the backend verdict on progress even when
    xsdb noise varies between installs.
    """
    core_filter = _core_filter(processor)
    connect_cmd = f"connect -url {hw_server_url}" if hw_server_url else "connect"
    lines = [
        "catch {fconfigure stdout -buffering line}",
        connect_cmd,
        'puts "S2C-RUN: connected"',
    ]
    if platform == "versal":
        if pdi_path is None:
            raise ValueError("versal run-on-board requires a boot PDI")
        lines.extend([
            'targets -set -nocase -filter {name =~ "*Versal*"}',
            f"device program {{{_tcl_path(pdi_path)}}}",
            'puts "S2C-RUN: pdi programmed"',
        ])
    elif platform == "zynq_7000":
        if ps7_init_path is None:
            raise ValueError("zynq_7000 run-on-board requires ps7_init.tcl")
        lines.extend([
            'targets -set -nocase -filter {name =~ "*APU*"}',
            "rst -system",
            "after 3000",
            f"source {{{_tcl_path(ps7_init_path)}}}",
            "ps7_init",
            "after 1000",
            'puts "S2C-RUN: ps7_init done"',
        ])
        if bitstream_path is not None:
            lines.extend([
                f"fpga {{{_tcl_path(bitstream_path)}}}",
                'puts "S2C-RUN: fpga programmed"',
            ])
    else:
        if psu_init_path is None:
            raise ValueError("zynq_ultrascale run-on-board requires psu_init.tcl")
        lines.extend([
            'targets -set -nocase -filter {name =~ "*PSU*"}',
            "rst -system",
            "after 3000",
            f"source {{{_tcl_path(psu_init_path)}}}",
            "psu_init",
            "after 1000",
            'puts "S2C-RUN: psu_init done"',
        ])
        if bitstream_path is not None:
            lines.extend([
                f"fpga {{{_tcl_path(bitstream_path)}}}",
                'puts "S2C-RUN: fpga programmed"',
            ])
    lines.extend([
        f"targets -set -nocase -filter {{name =~ {core_filter}}}",
        "rst -processor -clear-registers",
        f"dow {{{_tcl_path(elf_path)}}}",
        'puts "S2C-RUN: elf downloaded"',
    ])
    if platform == "zynq_7000":
        lines.append("ps7_post_config")
    lines.extend([
        "con",
        'puts "S2C-RUN: running"',
        "disconnect",
        "exit",
    ])
    return "\n".join(lines) + "\n"


def _hint_for_failure(output: str, hw_server_url: str = "") -> str:
    text = output.lower()
    if "no targets" in text or "no target" in text:
        if hw_server_url:
            return ("JTAG üzerinde hedef görünmüyor: kartın açık olduğundan, SmartLynq/uzak JTAG "
                    "kablosunun kartın JTAG konnektörüne takılı olduğundan ve boot modunun JTAG "
                    "olduğundan emin olun.")
        return ("JTAG üzerinde hedef görünmüyor: kartın açık olduğundan, JTAG USB kablosunun takılı "
                "olduğundan ve boot modunun JTAG olduğundan emin olun.")
    if "connection refused" in text or "connection timed out" in text or "hw_server" in text:
        if hw_server_url:
            return (f"{hw_server_url} adresindeki hw_server'a bağlanılamadı: SmartLynq/uzak hw_server "
                    "cihazının ağa bağlı olduğunu, IP adresini ve portu (varsayılan 3121) kontrol edin.")
        return "hw_server'a bağlanılamadı: Vitis hw_server servisinin çalıştığını kontrol edin."
    if "memory write error" in text or "dow" in text and "error" in text:
        return "ELF indirme hatası: psu_init'in doğru XSA'dan geldiğini ve DDR'ın ayakta olduğunu kontrol edin."
    return ""


class RunOnBoardJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, RunOnBoardJob] = {}
        self._counter = 0

    def get(self, job_id: str) -> Optional[RunOnBoardJob]:
        return self._jobs.get(job_id)

    async def start(self, config: RunOnBoardConfig) -> str:
        self._counter += 1
        job_id = f"runboard_{self._counter:04d}"
        job = RunOnBoardJob(id=job_id, config=config, _loop=asyncio.get_running_loop())
        self._jobs[job_id] = job
        asyncio.create_task(self._run(job))
        return job_id

    async def _run(self, job: RunOnBoardJob) -> None:
        job.status = "running"
        job.emit({"event": "runboard.start", "stage": "start", "progress": 5,
                  "message": "Board'a yükleme akışı başlatıldı (JTAG/xsdb)."})
        try:
            await asyncio.to_thread(self._blocking, job)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - surface board/tool failures directly
            job.status = "error"
            job.error = str(exc)
            job.emit({"event": "runboard.error", "stage": "error", "progress": 100,
                      "message": str(exc),
                      "trace": traceback.format_exc().splitlines()[-5:]})
        finally:
            final_stage = "done" if job.status == "done" else "error"
            job.emit({"event": "runboard.end", "stage": final_stage, "progress": 100,
                      "status": job.status})
            loop = job._loop
            if loop is not None:
                for queue in list(job.subscribers):
                    loop.call_soon_threadsafe(queue.put_nowait, None)

    def _blocking(self, job: RunOnBoardJob) -> None:
        config = job.config
        workspace = _clean_user_path(config.workspace_path)
        hw_server_url = normalize_hw_server_url(config.hw_server_url)
        connection_note = (f"SmartLynq/uzak hw_server: {hw_server_url}" if hw_server_url
                           else "lokal USB JTAG")
        job.emit({"event": "runboard.stage", "stage": "locate", "progress": 10,
                  "message": f"Bağlantı: {connection_note}"})

        job.emit({"event": "runboard.stage", "stage": "locate", "progress": 15,
                  "message": "xsdb aranıyor..."})
        xsdb = locate_xsdb(config.vitis_path)
        job.emit({"event": "runboard.stage", "stage": "locate", "progress": 20,
                  "message": f"xsdb: {xsdb}"})

        elf = find_application_elf(workspace, config.app_name)
        psu_init: Path | None = None
        ps7_init: Path | None = None
        pdi: Path | None = None
        bitstream: Path | None = None
        if config.platform == "versal":
            pdi = find_pdi(workspace, config.platform_name)
            boot_note = f"pdi: {pdi.name}"
        elif config.platform == "zynq_7000":
            ps7_init = find_ps7_init(workspace, config.platform_name)
            boot_note = f"ps7_init: {ps7_init.name}"
        else:
            psu_init = find_psu_init(workspace, config.platform_name)
            boot_note = f"psu_init: {psu_init.name}"
        if config.platform != "versal" and config.program_fpga in ("auto", "yes"):
            bitstream = find_bitstream(workspace, config.platform_name)
            if bitstream is None and config.program_fpga == "yes":
                raise FileNotFoundError("bitstream requested but no .bit found under the platform")
        job.emit({"event": "runboard.stage", "stage": "script", "progress": 35,
                  "message": f"ELF: {elf.name}; {boot_note}; "
                             f"bit: {bitstream.name if bitstream else 'yok'}"})

        script = render_run_on_board_script(
            elf_path=elf, processor=config.processor, platform=config.platform,
            psu_init_path=psu_init, ps7_init_path=ps7_init,
            bitstream_path=bitstream, pdi_path=pdi,
            hw_server_url=hw_server_url)
        run_dir = workspace / ".spec2code_runboard"
        run_dir.mkdir(parents=True, exist_ok=True)
        script_path = run_dir / f"run_{int(time.time())}.tcl"
        script_path.write_text(script, encoding="utf-8")

        boot_step = {"versal": "PDI programla", "zynq_7000": "ps7_init"}.get(config.platform, "psu_init")
        job.emit({"event": "runboard.stage", "stage": "run", "progress": 45,
                  "message": f"xsdb çalışıyor: reset -> {boot_step} -> ELF indir -> başlat..."})
        stdout_path = run_dir / "xsdb_stdout.log"
        stderr_path = run_dir / "xsdb_stderr.log"
        outcome = _run_xsct_streaming(
            [str(xsdb), str(script_path)],
            cwd=workspace,
            timeout_s=config.timeout_s,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            emit=lambda event: job.emit({**event, "stage": "run"}),
            stall_timeout_s=RUN_STALL_TIMEOUT_S,
            stall_grace_s=RUN_STALL_GRACE_S,
        )

        markers = [line for line in outcome.stdout.splitlines() if line.startswith("S2C-RUN:")]
        ran = any("S2C-RUN: running" in line for line in markers)
        if outcome.timed_out:
            raise RuntimeError(f"xsdb {config.timeout_s}s içinde bitmedi (stall={outcome.stalled})")
        if outcome.returncode != 0 or not ran:
            tail = "\n".join((outcome.stdout + "\n" + outcome.stderr).strip().splitlines()[-15:])
            hint = _hint_for_failure(outcome.stdout + outcome.stderr, hw_server_url)
            raise RuntimeError(
                "board'a yükleme başarısız oldu"
                + (f" — {hint}" if hint else "")
                + f"\nxsdb çıktısının sonu:\n{tail}")

        job.result = {
            "elf": str(elf),
            "platform": config.platform,
            "hw_server_url": hw_server_url or None,
            "psu_init": str(psu_init) if psu_init else None,
            "ps7_init": str(ps7_init) if ps7_init else None,
            "pdi": str(pdi) if pdi else None,
            "bitstream": str(bitstream) if bitstream else None,
            "markers": markers,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
        }
        job.emit({"event": "runboard.stage", "stage": "done", "progress": 95,
                  "message": "Uygulama board üzerinde çalışıyor. UART konsolundan çıktıyı izleyebilirsiniz."})


runboard_manager = RunOnBoardJobManager()
