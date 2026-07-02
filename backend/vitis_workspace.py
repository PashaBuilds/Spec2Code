"""Headless Vitis workspace creation jobs.

The generated C/H files are deterministic; this module only stages those files and asks the
installed Vitis XSCT runtime to create/build a workspace from a user-provided XSA.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import threading
import traceback
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from backend.jobs import Job
from backend.vitis_errors import map_vitis_errors
from hostplat import io as hio

_ROOT = Path(__file__).resolve().parent.parent
_OUTPUTS = _ROOT / "outputs"
_VERSION_RE = re.compile(r"(20\d{2}\.\d+(?:\.\d+)?)")
# Case-sensitive on purpose: Xilinx fatal lines are uppercase `ERROR: [...]`,
# while benign output contains `Error: Library "lwip220", not available` (the
# expected lwIP fallback probe) and BSP object listings such as
# `xil_exception.o` that a case-insensitive `exception` substring would match.
_XSCT_FATAL_RE = re.compile(
    r"(invalid command name"
    r"|while executing"
    r"|^ERROR:"
    r"|^Traceback \(most recent call last\)"
    r"|^Exception in thread"
    r")",
    re.MULTILINE,
)
_VITIS_BUILD_FATAL_RE = re.compile(
    r"("
    r"\bcc1(?:plus)?(?:\.exe)?:\s+fatal error:"
    r"|\b(?:make|gmake)(?:\[\d+\])?:\s+\*\*\*"
    r"|Failed to build\b"
    r"|\bcompilation terminated\b"
    r"|\bcollect2(?:\.exe)?:\s+error:"
    r")",
    re.IGNORECASE | re.MULTILINE,
)
_MAKE_LIBS_TARGET_RE = re.compile(
    r"(?P<processor>[^/\\\s:\]]+)[/\\]libsrc[/\\](?P<driver>[^/\\\s:\]]+)[/\\]src[/\\]make\.libs",
    re.IGNORECASE,
)
_KNOWN_AMD_XILINX_VENDORS = {"xilinx.com", "amd.com"}
_HWH_MODULE_KINDS = {
    "PERIPHERAL",
    "PROCESSOR",
    "BUS",
    "MEMORY",
    "MEMORY_CNTLR",
    "INTERRUPT_CNTLR",
    "DEBUG",
    "CLOCK",
    "RESET",
}
_CUSTOM_IP_DRIVER_POLICIES = {"auto_none", "keep"}
_VITIS_ERROR_CODES = {
    "custom_ip_bsp_driver": "S2C-VITIS-CUSTOM-IP-MAKELIBS-001",
    "missing_include": "S2C-VITIS-MISSING-INCLUDE-002",
    "missing_xparameter": "S2C-VITIS-XPARAMETER-003",
    "wrong_processor": "S2C-VITIS-PROCESSOR-004",
    "xsa_or_platform": "S2C-VITIS-XSA-PLATFORM-005",
    "xsct_tcl_command": "S2C-VITIS-XSCT-TCL-006",
    "undefined_reference": "S2C-VITIS-LINK-007",
    "missing_library": "S2C-VITIS-LIBRARY-008",
    "missing_elf": "S2C-VITIS-ELF-009",
    "xsct_hang": "S2C-VITIS-HANG-010",
    "workspace_stale": "S2C-VITIS-WORKSPACE-011",
    "unclassified": "S2C-VITIS-UNCLASSIFIED-099",
}
_KNOWN_XILINX_PL_IP_PREFIXES = (
    "axi_",
    "axis_",
    "aurora_",
    "blk_mem_",
    "c_accum",
    "c_addsub",
    "c_compare",
    "c_counter",
    "c_gate",
    "c_mux",
    "c_reg",
    "c_selectio",
    "c_shift",
    "clk_",
    "cordic",
    "dds_",
    "div_",
    "fifo_",
    "fir_",
    "floating_",
    "gt_",
    "ila",
    "interconnect",
    "jtag_",
    "lmb_",
    "mdm",
    "microblaze",
    "mig_",
    "mult_",
    "proc_",
    "processing_",
    "ps7_",
    "psu_",
    "psv_",
    "rst_",
    "smartconnect",
    "system_",
    "util_",
    "vio",
    "xl",
    "xpm_",
    "xps_",
    "xxv_",
    "zynq",
)
_KNOWN_XILINX_PL_IP_NAMES = {
    "axi_noc",
    "axis_data_fifo",
    "clk_wiz",
    "proc_sys_reset",
    "xlconcat",
    "xlconstant",
    "xlslice",
}


@dataclass(frozen=True)
class VitisWorkspaceConfig:
    vitis_path: str
    xsa_path: str
    workspace_path: str
    temp_path: str
    processor: str = ""
    runtime: str = "standalone"
    platform_name: str = ""
    system_name: str = ""
    app_name: str = ""
    timeout_s: int = 1800
    custom_ip_driver_policy: str = "auto_none"


@dataclass(frozen=True)
class CustomPlIpCandidate:
    instance: str
    vlnv: str
    ip_name: str
    reason: str


@dataclass(frozen=True)
class XsctInfo:
    path: Path
    version: str
    version_source: str


@dataclass
class VitisWorkspaceJob:
    id: str
    source_job_id: str
    source_project: str
    config: VitisWorkspaceConfig
    generate_job: Job
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


def _clean_user_path(value: str) -> Path:
    text = value.strip().strip('"').strip("'")
    if not text:
        raise ValueError("path is empty")
    return Path(os.path.expandvars(os.path.expanduser(text)))


def _version_key(path: Path) -> tuple[int, ...]:
    match = None
    for part in reversed(path.parts):
        match = _VERSION_RE.search(part)
        if match:
            break
    if not match:
        return (0,)
    return tuple(int(piece) for piece in match.group(1).split("."))


def _candidate_xsct_paths(root: Path) -> list[Path]:
    executable_names = ("xsct.bat", "xsct.cmd", "xsct.exe", "xsct")
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


def locate_xsct(vitis_path: str) -> Path:
    root = _clean_user_path(vitis_path)
    for candidate in _candidate_xsct_paths(root):
        if candidate.is_file():
            return candidate
    searched = "\n".join(str(path) for path in _candidate_xsct_paths(root)[:12])
    raise FileNotFoundError(f"xsct executable not found under '{root}'. Searched:\n{searched}")


def _command_for(xsct_path: Path, *args: str) -> list[str]:
    if os.name == "nt" and xsct_path.suffix.lower() in {".bat", ".cmd"}:
        return ["cmd.exe", "/c", str(xsct_path), *args]
    return [str(xsct_path), *args]


# XSCT can go silent forever on Windows: Vitis 2023.2 SDSCorePlugin.start()
# runs `which sdscc` during `app create` and blocks on readLine(); on some
# hosts that console child deadlocks before main() and the whole flow hangs
# with zero output. The streaming runner below writes logs incrementally and
# a watchdog first tries to unstick known probe children, then kills the
# process tree so the job fails with logs instead of hanging silently.
XSCT_STALL_TIMEOUT_S = 480
XSCT_STALL_GRACE_S = 180
_STUCK_PROBE_IMAGE_NAMES = {"which.exe"}


@dataclass
class XsctRunOutcome:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    stalled: bool = False
    watchdog_events: list[str] = field(default_factory=list)


def _windows_process_table() -> list[tuple[int, int, str]]:
    """Return (pid, parent_pid, exe_name) rows via Toolhelp32; empty off-Windows."""
    if os.name != "nt":
        return []
    import ctypes
    import ctypes.wintypes as wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        return []
    rows: list[tuple[int, int, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                rows.append((int(entry.th32ProcessID), int(entry.th32ParentProcessID), entry.szExeFile))
                if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)
    return rows


def _descendant_pids(root_pid: int, rows: list[tuple[int, int, str]]) -> list[tuple[int, str]]:
    children: dict[int, list[tuple[int, str]]] = {}
    for pid, ppid, name in rows:
        children.setdefault(ppid, []).append((pid, name))
    found: list[tuple[int, str]] = []
    queue = [root_pid]
    seen = {root_pid}
    while queue:
        current = queue.pop()
        for pid, name in children.get(current, []):
            if pid in seen:
                continue
            seen.add(pid)
            found.append((pid, name))
            queue.append(pid)
    return found


def _force_kill_pid(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _kill_process_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.kill(pid, 9)
        except OSError:
            pass


def _unstick_known_probe_children(root_pid: int) -> list[str]:
    """Kill known stuck toolchain probe children (Vitis `which sdscc`) under root_pid.

    Their conhost children are killed first: a console child deadlocked in
    console initialisation sometimes only dies once its conhost is gone.
    """
    rows = _windows_process_table()
    if not rows:
        return []
    descendants = _descendant_pids(root_pid, rows)
    events: list[str] = []
    for pid, name in descendants:
        if name.lower() not in _STUCK_PROBE_IMAGE_NAMES:
            continue
        for child_pid, child_name in _descendant_pids(pid, rows):
            if child_name.lower() == "conhost.exe":
                _force_kill_pid(child_pid)
                events.append(f"conhost.exe (pid={child_pid}) of stuck {name} killed")
        _force_kill_pid(pid)
        events.append(f"stuck toolchain probe {name} (pid={pid}) kill attempted")
    return events


def _run_xsct_streaming(
    cmd: list[str],
    *,
    cwd: Path,
    timeout_s: int,
    stdout_path: Path,
    stderr_path: Path,
    emit=None,
    stall_timeout_s: int = XSCT_STALL_TIMEOUT_S,
    stall_grace_s: int = XSCT_STALL_GRACE_S,
) -> XsctRunOutcome:
    """Run XSCT streaming stdout/stderr to log files with hang protection.

    Logs are written incrementally so they survive timeouts and kills. If no
    output arrives for ``stall_timeout_s`` the watchdog tries to unstick known
    probe children once; if the silence continues for ``stall_grace_s`` more,
    or the overall ``timeout_s`` deadline passes, the whole tree is killed.
    """
    import time as _time

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    last_activity = _time.monotonic()
    activity_lock = threading.Lock()
    buffers: dict[str, list[str]] = {"stdout": [], "stderr": []}

    def _pump(stream, key: str, path: Path) -> None:
        nonlocal last_activity
        with open(path, "w", encoding="utf-8", errors="replace", newline="") as handle:
            for line in iter(stream.readline, ""):
                buffers[key].append(line)
                handle.write(line)
                handle.flush()
                with activity_lock:
                    last_activity = _time.monotonic()
        stream.close()

    readers = [
        threading.Thread(target=_pump, args=(proc.stdout, "stdout", stdout_path), daemon=True),
        threading.Thread(target=_pump, args=(proc.stderr, "stderr", stderr_path), daemon=True),
    ]
    for reader in readers:
        reader.start()

    deadline = _time.monotonic() + max(60, int(timeout_s or 1800))
    outcome = XsctRunOutcome(returncode=0, stdout="", stderr="")
    unstick_attempted = False
    stall_kill_at: float | None = None
    while proc.poll() is None:
        _time.sleep(1.0)
        now = _time.monotonic()
        if now >= deadline:
            outcome.timed_out = True
            outcome.watchdog_events.append(
                f"XSCT {int(timeout_s)}s timeout aşıldı; process tree kill ediliyor."
            )
            _kill_process_tree(proc.pid)
            break
        with activity_lock:
            silent_for = now - last_activity
        if silent_for < stall_timeout_s:
            unstick_attempted = False
            stall_kill_at = None
            continue
        if not unstick_attempted:
            unstick_attempted = True
            stall_kill_at = now + max(1, int(stall_grace_s))
            events = _unstick_known_probe_children(proc.pid)
            if not events:
                events = [
                    f"XSCT {int(silent_for)}s boyunca çıktı üretmedi; bilinen stuck probe child bulunamadı."
                ]
            outcome.watchdog_events.extend(events)
            if emit is not None:
                emit(events)
        elif stall_kill_at is not None and now >= stall_kill_at:
            outcome.stalled = True
            outcome.watchdog_events.append(
                f"XSCT {int(silent_for)}s sessiz kaldı; hang kabul edilip process tree kill ediliyor."
            )
            _kill_process_tree(proc.pid)
            break

    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc.pid)
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            pass
    for reader in readers:
        reader.join(timeout=10)
    outcome.returncode = proc.returncode if proc.returncode is not None else 1
    outcome.stdout = "".join(buffers["stdout"])
    outcome.stderr = "".join(buffers["stderr"])
    return outcome


def _xsct_hang_issue(outcome: XsctRunOutcome, script_path: Path) -> dict:
    reason = "timeout" if outcome.timed_out else "output stall"
    detail = " | ".join(outcome.watchdog_events) or "watchdog detayı yok"
    return {
        "severity": "error",
        "category": "xsct_hang",
        "message": (
            f"XSCT ilerleme üretmeden durdu ({reason}); process tree Spec2Code watchdog "
            f"tarafından sonlandırıldı. {detail}"
        ),
        "suggestion": (
            "Vitis 2023.2 `app create` sırasında `which sdscc` probe'u bazı Windows "
            "makinelerde konsol başlatmasında donar ve XSCT sonsuza dek bekler. "
            "Log'daki son [Spec2Code] satırına bak: akış `creating named platform/system/application` "
            "üzerinde durduysa Task Manager'da `which.exe` (parent: eclipse.exe) var mı kontrol et. "
            "Varsa antivirüs/console host müdahalesini incele; makinede takılıyorsa Vitis "
            "`gnuwin/bin/which.exe` dosyasını yedekleyip konsol açmayan bir stub ile değiştirmek "
            "bilinen bir workaround'dur."
        ),
        "file": str(script_path),
        "line": None,
        "symbol": "which sdscc" if outcome.stalled else "",
        "raw": detail,
    }


def _parse_version(text: str) -> str | None:
    match = _VERSION_RE.search(text)
    return match.group(1) if match else None


def _version_from_path(path: Path) -> str | None:
    for part in reversed(path.parts):
        version = _parse_version(part)
        if version:
            return version
    return None


def detect_xsct(vitis_path: str, *, timeout_s: int = 20) -> XsctInfo:
    xsct_path = locate_xsct(vitis_path)
    try:
        completed = subprocess.run(
            _command_for(xsct_path, "-version"),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
        version = _parse_version(f"{completed.stdout}\n{completed.stderr}")
        if version:
            return XsctInfo(path=xsct_path, version=version, version_source="xsct -version")
    except (OSError, subprocess.TimeoutExpired):
        pass

    return XsctInfo(path=xsct_path, version=_version_from_path(xsct_path) or "unknown", version_source="path")


def default_vitis_processor(platform: str, target_core: str) -> str:
    if platform == "zynq_ultrascale":
        match = re.fullmatch(r"a53_(\d)", target_core)
        if match:
            return f"psu_cortexa53_{match.group(1)}"
        match = re.fullmatch(r"r5_(\d)", target_core)
        if match:
            return f"psu_cortexr5_{match.group(1)}"
    if platform == "versal":
        match = re.fullmatch(r"a72_(\d)", target_core)
        if match:
            return f"psv_cortexa72_{match.group(1)}"
        match = re.fullmatch(r"r5_(\d)", target_core)
        if match:
            return f"psv_cortexr5_{match.group(1)}"
    return target_core


def vitis_os(runtime: str) -> str:
    normalized = runtime.strip().lower()
    if normalized in {"freertos", "freertos10_xilinx"}:
        return "freertos10_xilinx"
    return "standalone"


def vitis_lwip_api_mode(os_name: str) -> str:
    if vitis_os(os_name) == "freertos10_xilinx":
        return "SOCKET_API"
    return "RAW_API"


def normalize_custom_ip_driver_policy(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in _CUSTOM_IP_DRIVER_POLICIES:
        return normalized
    return "auto_none"


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml_attr(element: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for key, value in element.attrib.items():
        if _xml_local_name(key).lower() in wanted:
            return value.strip()
    return ""


def _is_standard_xilinx_pl_ip(ip_name: str, instance: str) -> bool:
    normalized = _normalize_custom_ip_token(ip_name or instance)
    if not normalized:
        return True
    if normalized in _KNOWN_XILINX_PL_IP_NAMES:
        return True
    return normalized.startswith(_KNOWN_XILINX_PL_IP_PREFIXES)


def _hwh_documents_from_xsa(xsa_path: Path) -> list[tuple[str, bytes]]:
    try:
        with zipfile.ZipFile(xsa_path) as archive:
            docs: list[tuple[str, bytes]] = []
            for name in archive.namelist():
                if name.lower().endswith(".hwh"):
                    docs.append((name, archive.read(name)))
            return docs
    except (OSError, zipfile.BadZipFile):
        return []


def _driver_dir_base_name(dirname: str) -> str:
    """`axi_mem_space_v1_0` -> `axi_mem_space`."""
    token = _normalize_custom_ip_token(dirname)
    return re.sub(r"_v\d+(?:_\d+)?$", "", token)


def embedded_driver_base_names(xsa_path: Path) -> set[str]:
    """Base names of non-Xilinx driver folders embedded in the XSA.

    Standard Xilinx drivers ship with the Vitis install; a `drivers/<name>/`
    folder inside an exported XSA is a user-packaged IP driver by
    construction. This is a stronger custom-IP signal than VLNV heuristics:
    a company IP named e.g. `axi_mem_space` packaged under a Xilinx vendor
    VLNV would otherwise be mistaken for a standard `axi_*` family IP.
    """
    try:
        if not xsa_path.is_file() or not zipfile.is_zipfile(xsa_path):
            return set()
    except OSError:
        return set()
    names: set[str] = set()
    try:
        with zipfile.ZipFile(xsa_path) as archive:
            for entry in archive.namelist():
                parts = entry.replace("\\", "/").split("/")
                for index, part in enumerate(parts[:-1]):
                    if part != "drivers" or index + 1 >= len(parts):
                        continue
                    base = _driver_dir_base_name(parts[index + 1])
                    if base and not _is_known_xilinx_libsrc(base):
                        names.add(base)
    except (OSError, zipfile.BadZipFile):
        return set()
    return names


def discover_custom_pl_ips(xsa_path: Path) -> list[CustomPlIpCandidate]:
    candidates: dict[str, CustomPlIpCandidate] = {}
    embedded_drivers = embedded_driver_base_names(xsa_path)
    for hwh_name, content in _hwh_documents_from_xsa(xsa_path):
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            continue
        for element in root.iter():
            if _xml_local_name(element.tag).upper() != "MODULE":
                continue
            # Real Vivado .hwh files carry the module kind in IPTYPE/MODCLASS
            # (PERIPHERAL, PROCESSOR, BUS, ...) while MODTYPE holds the IP
            # name (e.g. "mem_pcie_intr"). Legacy/synthetic documents put the
            # kind directly in MODTYPE. Accept both encodings.
            ip_kind = ""
            for kind_attr in ("IPTYPE", "MODCLASS"):
                value = _xml_attr(element, kind_attr).upper()
                if value:
                    ip_kind = value
                    break
            modtype = _xml_attr(element, "MODTYPE")
            if not ip_kind and modtype.upper() in _HWH_MODULE_KINDS:
                ip_kind = modtype.upper()
            if ip_kind and ip_kind != "PERIPHERAL":
                continue
            instance = _xml_attr(element, "INSTANCE", "NAME")
            if not instance:
                fullname = _xml_attr(element, "FULLNAME")
                instance = fullname.rsplit("/", 1)[-1] if fullname else ""
            vlnv = _xml_attr(element, "VLNV")
            if not instance or not vlnv:
                continue
            vlnv_parts = vlnv.split(":")
            vendor = vlnv_parts[0].lower() if vlnv_parts else ""
            library = vlnv_parts[1].lower() if len(vlnv_parts) >= 2 else ""
            ip_name = _xml_attr(element, "IP_NAME")
            if not ip_name and modtype and modtype.upper() not in _HWH_MODULE_KINDS:
                ip_name = modtype
            if not ip_name and len(vlnv_parts) >= 3:
                ip_name = vlnv_parts[2]
            has_embedded_driver = _normalize_custom_ip_token(ip_name) in embedded_drivers
            if has_embedded_driver:
                reason = f"{hwh_name}: XSA embeds a non-Xilinx driver for this IP"
            elif vendor in _KNOWN_AMD_XILINX_VENDORS and library == "user":
                reason = f"{hwh_name}: user-packaged PL peripheral VLNV"
            elif vendor in _KNOWN_AMD_XILINX_VENDORS:
                if _is_standard_xilinx_pl_ip(ip_name, instance):
                    continue
                reason = f"{hwh_name}: Xilinx-vendor custom-like PL peripheral"
            else:
                reason = f"{hwh_name}: non-Xilinx/AMD peripheral VLNV"
            candidates.setdefault(
                instance,
                CustomPlIpCandidate(
                    instance=instance,
                    vlnv=vlnv,
                    ip_name=ip_name,
                    reason=reason,
                ),
            )
    return [candidates[key] for key in sorted(candidates)]


def _safe_identifier(value: str, fallback: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return safe or fallback


def _posix_path(value: str) -> str:
    return value.replace("\\", "/")


def _relative_output_name(rel: str, out_dir: str) -> str:
    rel_posix = _posix_path(rel)
    out_posix = _posix_path(out_dir).rstrip("/")
    if out_posix and rel_posix.startswith(f"{out_posix}/"):
        return rel_posix[len(out_posix) + 1:]
    return Path(rel_posix).name


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


def _driver_module(part: str) -> str:
    return re.sub(r"[^a-z0-9]", "", part.lower())


def _pascal_identifier(value: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _driver_function(module: str, action: str) -> str:
    return f"{module}{_pascal_identifier(action)}"


def vitis_selftest_header() -> str:
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


def vitis_selftest_source(spec: dict, *, emit_main: bool = True) -> str:
    controllers = {controller["id"]: controller for controller in spec.get("controllers", [])}
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
    main_block = (
        "\n"
        "int main(void)\n"
        "{\n"
        "    return spec2codeRunSelfTests();\n"
        "}\n"
        if emit_main
        else ""
    )
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
        + main_block
    )


def stage_vitis_sources(job: Job, source_root: Path) -> list[str]:
    if not job.result:
        raise ValueError("generate job result is not ready")

    out_dir = job.result.get("out_dir", "")
    if source_root.exists():
        shutil.rmtree(source_root)
    source_root.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []

    for rel in job.result.get("files", []):
        rel_posix = _posix_path(rel).lstrip("/")
        source = (_ROOT / rel_posix).resolve()
        try:
            source.relative_to(_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"generated file escaped repository root: {rel}") from exc
        if not source.is_file():
            continue

        display = _relative_output_name(rel_posix, out_dir)
        if display.startswith(("drivers/", "tests/", "reference_sources/")):
            target = source_root / display
        else:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        staged.append(target.relative_to(source_root).as_posix())

    emit_selftest_main = "tests/spec2code_testbench_lwip_main.c" not in staged
    for name, content in {
        "spec2code_selftest_main.h": vitis_selftest_header(),
        "spec2code_selftest_main.c": vitis_selftest_source(job.spec, emit_main=emit_selftest_main),
    }.items():
        target = source_root / name
        target.write_text(hio.normalize_crlf(content), encoding="utf-8", newline="")
        staged.append(name)

    return sorted(staged)


def staged_header_dirs(staged_files: list[str]) -> list[str]:
    """Subdirectories (relative to src/) that carry staged headers.

    The CDT application build only inherits the BSP include path, so every
    staged folder with a header must be added to the app include paths or
    cross-folder quote-includes (tests/ including drivers/ headers) fail.
    """
    dirs = {
        _posix_path(str(Path(rel).parent))
        for rel in staged_files
        if rel.lower().endswith(".h") and "/" in _posix_path(rel)
    }
    return sorted(dirs)


def _tcl_path(path: Path) -> str:
    text = str(path.resolve()).replace("\\", "/").replace("}", "\\}")
    return "{" + text + "}"


def _tcl_list(values: list[str]) -> str:
    return " ".join("{" + value.replace("\\", "\\\\").replace("}", "\\}") + "}" for value in values)


def _tcl_put(message: str) -> str:
    return f'puts "\\[Spec2Code\\] {message}"\n'


def _log_tail(text: str, *, limit: int = 4000) -> str:
    clean = text.strip()
    return clean[-limit:] if len(clean) > limit else clean


def _path_tail(value: Path | str, *, parts: int = 6) -> str:
    path_parts = Path(str(value).replace("\\", "/")).parts
    return "/".join(path_parts[-parts:]) if path_parts else str(value)


def _normalize_custom_ip_token(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", value.lower()).strip("_")


def _custom_ip_aliases(value: str) -> set[str]:
    normalized = _normalize_custom_ip_token(value)
    aliases = {normalized} if normalized else set()
    match = re.fullmatch(r"(.+)_([0-9]+)", normalized)
    if match:
        aliases.add(match.group(1))
    return aliases


def _is_known_xilinx_libsrc(libsrc_name: str) -> bool:
    if libsrc_name.startswith(("xil", "lwip", "freertos", "standalone")):
        return True
    return libsrc_name in {
        "common",
        "cpu_cortexa53",
        "cpu_cortexr5",
        "cpu_psu_cortexa53",
        "cpu_psu_cortexr5",
    }


def make_libs_targets_from_log(log_text: str) -> list[dict]:
    targets: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for match in _MAKE_LIBS_TARGET_RE.finditer(log_text):
        processor = match.group("processor")
        driver = match.group("driver")
        key = (processor.lower(), driver.lower())
        if key in seen:
            continue
        seen.add(key)
        targets.append({
            "processor": processor,
            "driver": driver,
            "path_tail": f"{processor}/libsrc/{driver}/src/make.libs",
        })
    return targets


def _make_libs_matches_custom_ip(make_libs: Path, custom_ip_instances: list[str]) -> bool:
    libsrc_name = _normalize_custom_ip_token(make_libs.parent.parent.name)
    for custom_ip in custom_ip_instances:
        for alias in _custom_ip_aliases(custom_ip):
            if libsrc_name == alias or libsrc_name.startswith(f"{alias}_"):
                return True
    return False


def _make_libs_looks_sourceless(make_libs: Path) -> bool:
    libsrc_name = _normalize_custom_ip_token(make_libs.parent.parent.name)
    if not libsrc_name or _is_known_xilinx_libsrc(libsrc_name):
        return False
    if any(make_libs.parent.glob("*.c")):
        return False
    try:
        content = make_libs.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "*.c" in content


def _write_noop_make_libs(make_libs: Path) -> bool:
    try:
        existing = make_libs.read_text(encoding="utf-8", errors="replace") if make_libs.is_file() else ""
    except OSError:
        existing = ""
    if "Spec2Code: source-less custom PL IP BSP driver disabled." in existing:
        return False

    backup = make_libs.with_name(f"{make_libs.name}.spec2code_backup")
    try:
        if make_libs.is_file() and not backup.exists():
            shutil.copy2(make_libs, backup)
        make_libs.write_text(
            "# Spec2Code: source-less custom PL IP BSP driver disabled.\n"
            ".PHONY: all libs include install clean\n"
            "all: libs\n"
            "libs:\n"
            "include:\n"
            "install: libs\n"
            "clean:\n",
            encoding="utf-8",
            newline="",
        )
    except OSError:
        return False
    return True


def patch_custom_ip_make_libs(workspace_path: Path, custom_ip_instances: list[str], policy: str) -> list[str]:
    if normalize_custom_ip_driver_policy(policy) != "auto_none" or not workspace_path.exists():
        return []
    patched: list[str] = []
    for make_libs in workspace_path.rglob("make.libs"):
        if not make_libs.is_file():
            continue
        if _make_libs_matches_custom_ip(make_libs, custom_ip_instances) or _make_libs_looks_sourceless(make_libs):
            if _write_noop_make_libs(make_libs):
                patched.append(str(make_libs))
    return patched


def patch_custom_ip_make_libs_many(root_paths: list[Path], custom_ip_instances: list[str], policy: str) -> list[str]:
    patched: list[str] = []
    for root_path in root_paths:
        patched.extend(patch_custom_ip_make_libs(root_path, custom_ip_instances, policy))
    return sorted(set(patched))


def synthesize_make_libs_from_log_targets(root_paths: list[Path], log_text: str, policy: str) -> list[str]:
    if normalize_custom_ip_driver_policy(policy) != "auto_none":
        return []
    created: list[str] = []
    targets = make_libs_targets_from_log(log_text)
    if not targets:
        return []

    root_resolved: list[Path] = []
    for root_path in root_paths:
        if root_path.exists():
            try:
                root_resolved.append(root_path.resolve())
            except OSError:
                continue

    for target in targets:
        driver = _normalize_custom_ip_token(str(target["driver"]))
        if not driver or _is_known_xilinx_libsrc(driver):
            continue
        processor = str(target["processor"])
        path_tail = str(target["path_tail"])
        processor_dirs: list[Path] = []
        for root_path in root_paths:
            if not root_path.exists():
                continue
            for candidate in root_path.rglob(processor):
                if candidate.is_dir() and candidate.name == processor:
                    processor_dirs.append(candidate)
            for makefile in root_path.rglob("Makefile"):
                if not makefile.is_file():
                    continue
                try:
                    text = makefile.read_text(encoding="utf-8", errors="replace").replace("\\", "/")
                except OSError:
                    continue
                if path_tail in text:
                    processor_dirs.append(makefile.parent / processor)
        for processor_dir in sorted(set(processor_dirs)):
            make_libs = processor_dir / "libsrc" / str(target["driver"]) / "src" / "make.libs"
            try:
                resolved = make_libs.resolve()
                if not any(resolved.is_relative_to(root) for root in root_resolved):
                    continue
            except OSError:
                continue
            make_libs.parent.mkdir(parents=True, exist_ok=True)
            if _write_noop_make_libs(make_libs):
                created.append(str(make_libs))
    return sorted(set(created))


def inspect_filesystem_make_libs(root_paths: list[Path], custom_ip_instances: list[str], policy: str) -> dict:
    summary = {
        "scope": "workspace",
        "total": 0,
        "custom_match": 0,
        "sourceless": 0,
        "risky": 0,
        "samples": [],
    }
    if normalize_custom_ip_driver_policy(policy) != "auto_none":
        return summary
    samples: list[dict] = []
    seen: set[str] = set()
    for root_path in root_paths:
        if not root_path.exists():
            continue
        for make_libs in root_path.rglob("make.libs"):
            if not make_libs.is_file():
                continue
            resolved = str(make_libs)
            if resolved in seen:
                continue
            seen.add(resolved)
            summary["total"] += 1
            matches_custom = _make_libs_matches_custom_ip(make_libs, custom_ip_instances)
            sourceless = _make_libs_looks_sourceless(make_libs)
            if matches_custom:
                summary["custom_match"] += 1
            if sourceless:
                summary["sourceless"] += 1
            if matches_custom or sourceless:
                summary["risky"] += 1
                if len(samples) < 12:
                    samples.append({
                        "driver": make_libs.parent.parent.name,
                        "path_tail": _path_tail(make_libs),
                        "custom_match": matches_custom,
                        "sourceless": sourceless,
                        "patched": (make_libs.parent / "make.libs.spec2code_backup").exists(),
                    })
    summary["samples"] = samples
    return summary


def inspect_vitis_elf_artifacts(root_paths: list[Path], app_name: str) -> dict:
    app_name_lower = app_name.lower()
    expected_name = f"{app_name_lower}.elf" if app_name_lower else ""
    summary = {
        "total": 0,
        "application": 0,
        "expected_names": [expected_name] if expected_name else [],
        "samples": [],
        "application_samples": [],
    }
    samples: list[dict] = []
    application_samples: list[dict] = []
    seen: set[str] = set()
    for root_path in root_paths:
        if not root_path.exists():
            continue
        for elf_path in root_path.rglob("*.elf"):
            if not elf_path.is_file():
                continue
            resolved = str(elf_path)
            if resolved in seen:
                continue
            seen.add(resolved)
            parts_lower = [part.lower() for part in elf_path.parts]
            name_lower = elf_path.name.lower()
            is_application = bool(app_name_lower) and (
                name_lower == expected_name
                or app_name_lower in parts_lower
            )
            item = {
                "name": elf_path.name,
                "path_tail": _path_tail(elf_path, parts=10),
                "application_match": is_application,
            }
            summary["total"] += 1
            if len(samples) < 16:
                samples.append(item)
            if is_application:
                summary["application"] += 1
                if len(application_samples) < 8:
                    application_samples.append(item)
    summary["samples"] = samples
    summary["application_samples"] = application_samples
    return summary


def _zip_libsrc_name(make_libs_name: str) -> str:
    parts = make_libs_name.replace("\\", "/").split("/")
    if len(parts) >= 3 and parts[-1] == "make.libs" and parts[-2] == "src":
        return _normalize_custom_ip_token(parts[-3])
    return ""


def _zip_make_libs_matches_custom_ip(make_libs_name: str, custom_ip_instances: list[str]) -> bool:
    libsrc_name = _zip_libsrc_name(make_libs_name)
    for custom_ip in custom_ip_instances:
        for alias in _custom_ip_aliases(custom_ip):
            if libsrc_name == alias or libsrc_name.startswith(f"{alias}_"):
                return True
    return False


def _zip_make_libs_looks_sourceless(make_libs_name: str, content: str, names: set[str]) -> bool:
    normalized_name = make_libs_name.replace("\\", "/")
    libsrc_name = _zip_libsrc_name(normalized_name)
    if not libsrc_name or _is_known_xilinx_libsrc(libsrc_name) or "*.c" not in content:
        return False
    src_dir = normalized_name.rsplit("/", 1)[0] + "/"
    return not any(name.startswith(src_dir) and name.lower().endswith(".c") for name in names)


def inspect_xsa_make_libs(xsa_path: Path, custom_ip_instances: list[str], policy: str) -> dict:
    summary = {
        "scope": "xsa",
        "is_zip": False,
        "hwh_count": 0,
        "total": 0,
        "custom_match": 0,
        "sourceless": 0,
        "risky": 0,
        "samples": [],
    }
    if not xsa_path.is_file():
        return summary
    try:
        summary["is_zip"] = zipfile.is_zipfile(xsa_path)
    except OSError:
        return summary
    if not summary["is_zip"]:
        return summary

    samples: list[dict] = []
    try:
        with zipfile.ZipFile(xsa_path, "r") as archive:
            infos = archive.infolist()
            names = {info.filename.replace("\\", "/") for info in infos}
            summary["hwh_count"] = sum(1 for name in names if name.lower().endswith(".hwh"))
            for info in infos:
                normalized_name = info.filename.replace("\\", "/")
                if not normalized_name.endswith("/src/make.libs"):
                    continue
                summary["total"] += 1
                raw = archive.read(info.filename)
                text = raw.decode("utf-8", errors="replace")
                matches_custom = _zip_make_libs_matches_custom_ip(normalized_name, custom_ip_instances)
                sourceless = _zip_make_libs_looks_sourceless(normalized_name, text, names)
                if matches_custom:
                    summary["custom_match"] += 1
                if sourceless:
                    summary["sourceless"] += 1
                if matches_custom or sourceless:
                    summary["risky"] += 1
                    if len(samples) < 12:
                        samples.append({
                            "driver": _zip_libsrc_name(normalized_name),
                            "path_tail": _path_tail(normalized_name),
                            "custom_match": matches_custom,
                            "sourceless": sourceless,
                        })
    except (OSError, zipfile.BadZipFile):
        return summary
    summary["samples"] = samples
    return summary


def patch_xsa_custom_ip_make_libs(xsa_path: Path, custom_ip_instances: list[str], policy: str) -> list[str]:
    if normalize_custom_ip_driver_policy(policy) != "auto_none" or not xsa_path.is_file():
        return []
    try:
        is_zip = zipfile.is_zipfile(xsa_path)
    except OSError:
        return []
    if not is_zip:
        return []

    patched: list[str] = []
    temp_path = xsa_path.with_name(f"{xsa_path.name}.spec2code_patched")
    try:
        with zipfile.ZipFile(xsa_path, "r") as source_zip:
            infos = source_zip.infolist()
            names = {info.filename.replace("\\", "/") for info in infos}
            replacements: dict[str, bytes] = {}
            for info in infos:
                normalized_name = info.filename.replace("\\", "/")
                if not normalized_name.endswith("/src/make.libs"):
                    continue
                raw = source_zip.read(info.filename)
                text = raw.decode("utf-8", errors="replace")
                if (
                    _zip_make_libs_matches_custom_ip(normalized_name, custom_ip_instances)
                    or _zip_make_libs_looks_sourceless(normalized_name, text, names)
                ):
                    replacements[info.filename] = (
                        "# Spec2Code: source-less custom PL IP BSP driver disabled in staged XSA.\n"
                        ".PHONY: all libs include install clean\n"
                        "all: libs\n"
                        "libs:\n"
                        "include:\n"
                        "install: libs\n"
                        "clean:\n"
                    ).encode("utf-8")
                    patched.append(info.filename)
            if not replacements:
                return []
            with zipfile.ZipFile(temp_path, "w") as target_zip:
                for info in infos:
                    data = replacements.get(info.filename)
                    if data is None:
                        data = source_zip.read(info.filename)
                    target_zip.writestr(info, data)
        shutil.move(str(temp_path), str(xsa_path))
    except (OSError, zipfile.BadZipFile):
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return []
    return patched


_NOOP_DRIVER_MAKEFILE = (
    "# Spec2Code: source-less custom PL IP BSP driver disabled in staged XSA.\n"
    ".PHONY: all libs include install clean\n"
    "all: libs\n"
    "libs:\n"
    "include:\n"
    "install: libs\n"
    "clean:\n"
)


def neutralize_custom_ip_drivers_in_xsa(xsa_path: Path, custom_ip_instances: list[str], policy: str) -> list[str]:
    """Replace embedded custom PL IP driver build recipes with no-ops.

    `bsp setdriver none` only covers the application domain BSP; the FSBL and
    PMUFW BSPs are generated separately and rebuild the embedded driver every
    time, so a source-less custom driver deterministically breaks them
    (`cc1.exe: fatal error: *.c: Invalid argument` in the driver's `libs`
    target, followed by `cannot find -lxilffs`/`-lxilfpga`). Patching the
    generated workspace copies is a race against the build, and deleting the
    whole driver folder breaks hsi (`Repository Directory ... doesn't exist`).
    Overwriting the driver's `src/Makefile` (and any `src/make.libs`) inside
    the staged XSA with a no-op keeps the repository intact while every BSP
    copy of the driver builds as a no-op. The user's original XSA is
    untouched.
    """
    if normalize_custom_ip_driver_policy(policy) != "auto_none" or not xsa_path.is_file():
        return []
    try:
        if not zipfile.is_zipfile(xsa_path):
            return []
    except OSError:
        return []

    aliases: set[str] = set()
    for instance in custom_ip_instances:
        aliases |= _custom_ip_aliases(instance)

    def _matched_driver_dir(name: str) -> str | None:
        parts = name.replace("\\", "/").split("/")
        for index, part in enumerate(parts[:-1]):
            if part != "drivers" or index + 1 >= len(parts):
                continue
            dirname = parts[index + 1]
            # Any non-Xilinx driver embedded in an XSA is a packaged custom
            # IP driver by construction, independent of VLNV heuristics.
            if not _is_known_xilinx_libsrc(_driver_dir_base_name(dirname)):
                return "/".join(parts[: index + 2])
            driver_dir = _normalize_custom_ip_token(dirname)
            for alias in aliases:
                if driver_dir == alias or driver_dir.startswith(f"{alias}_v") or driver_dir.startswith(f"{alias}_"):
                    return "/".join(parts[: index + 2])
        return None

    temp_path = xsa_path.with_name(f"{xsa_path.name}.spec2code_neutralized")
    neutralized_dirs: set[str] = set()
    try:
        with zipfile.ZipFile(xsa_path, "r") as source_zip:
            infos = source_zip.infolist()
            existing_names = {info.filename.replace("\\", "/") for info in infos}
            noop = _NOOP_DRIVER_MAKEFILE.encode("utf-8")
            replacements: dict[str, bytes] = {}
            for info in infos:
                normalized = info.filename.replace("\\", "/")
                driver_dir = _matched_driver_dir(normalized)
                if not driver_dir:
                    continue
                neutralized_dirs.add(driver_dir)
                if normalized.endswith(("/src/Makefile", "/src/makefile", "/src/make.libs")):
                    replacements[info.filename] = noop
            # Company drivers are sometimes packaged without a src/ folder at
            # all; hsi then fails with `[Hsi 55-1562] Source directory ...
            # does not exist` and the generated BSP compiles a literal `*.c`.
            # Adding no-op build files keeps hsi happy and the build inert.
            additions: dict[str, bytes] = {}
            for driver_dir in neutralized_dirs:
                for missing in (f"{driver_dir}/src/Makefile", f"{driver_dir}/src/make.libs"):
                    if missing not in existing_names:
                        additions[missing] = noop
            if not replacements and not additions:
                return []
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target_zip:
                for info in infos:
                    data = replacements.get(info.filename)
                    if data is None:
                        data = source_zip.read(info.filename)
                    target_zip.writestr(info, data)
                for name, data in sorted(additions.items()):
                    target_zip.writestr(name, data)
        shutil.move(str(temp_path), str(xsa_path))
    except (OSError, zipfile.BadZipFile):
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return []
    return sorted(neutralized_dirs)


class CustomIpMakeLibsWatcher:
    def __init__(self, root_paths: Path | list[Path], custom_ip_instances: list[str], policy: str, *, interval_s: float = 0.005) -> None:
        self.root_paths = root_paths if isinstance(root_paths, list) else [root_paths]
        self.custom_ip_instances = custom_ip_instances
        self.policy = policy
        self.interval_s = interval_s
        self.patched_paths: list[str] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="spec2code-custom-ip-bsp-patcher", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> list[str]:
        self._stop.set()
        self._thread.join(timeout=2.0)
        self._patch_once()
        return sorted(set(self.patched_paths))

    def _patch_once(self) -> None:
        for root_path in self.root_paths:
            for path in patch_custom_ip_make_libs(root_path, self.custom_ip_instances, self.policy):
                self.patched_paths.append(path)

    def _run(self) -> None:
        while not self._stop.is_set():
            self._patch_once()
            self._stop.wait(self.interval_s)


def _xsct_log_has_fatal_error(stdout: str, stderr: str) -> bool:
    log = f"{stdout}\n{stderr}"
    return bool(_XSCT_FATAL_RE.search(log) or _VITIS_BUILD_FATAL_RE.search(log))


def _issue_error_codes(issues: list[dict]) -> list[str]:
    codes: list[str] = []
    for issue in issues:
        code = _VITIS_ERROR_CODES.get(str(issue.get("category", "")))
        if code and code not in codes:
            codes.append(code)
    return codes


def _should_retry_custom_ip_self_heal(issues: list[dict], policy: str) -> bool:
    if normalize_custom_ip_driver_policy(policy) != "auto_none":
        return False
    return any(issue.get("category") == "custom_ip_bsp_driver" for issue in issues)


def build_vitis_doctor(
    *,
    custom_ip_driver_policy: str,
    custom_pl_ips: list[CustomPlIpCandidate],
    xsa_make_libs: dict,
    workspace_make_libs: dict | None = None,
    log_make_libs_targets: list[dict] | None = None,
    elf_artifacts: dict | None = None,
    xsa_patched_count: int = 0,
    host_patched_count: int = 0,
    requires_lwip: bool = False,
    lwip_api_mode: str | None = None,
    issues: list[dict] | None = None,
    recovered_issues: list[dict] | None = None,
    self_heal: dict | None = None,
) -> dict:
    issues = issues or []
    recovered_issues = recovered_issues or []
    log_make_libs_targets = log_make_libs_targets or []
    error_codes = _issue_error_codes(issues)
    recovered_error_codes = _issue_error_codes(recovered_issues)
    checks: list[dict] = []
    hints: list[str] = []

    if custom_ip_driver_policy == "keep":
        checks.append({
            "id": "custom_ip_policy",
            "label": "Custom IP policy",
            "status": "warn",
            "detail": "BSP default'u korunuyor; source'suz custom IP varsa Vitis build hata verebilir.",
        })
    else:
        checks.append({
            "id": "custom_ip_policy",
            "label": "Custom IP policy",
            "status": "ok",
            "detail": "`Auto: custom IP - none` aktif.",
        })

    if custom_pl_ips:
        checks.append({
            "id": "custom_ip_candidates",
            "label": "Custom IP adayları",
            "status": "warn",
            "detail": f"{len(custom_pl_ips)} aday bulundu; BSP driver none denenir.",
        })
    else:
        checks.append({
            "id": "custom_ip_candidates",
            "label": "Custom IP adayları",
            "status": "neutral",
            "detail": "HWH içinde custom-like PL IP adayı bulunmadı.",
        })

    if xsa_make_libs.get("is_zip"):
        status = "warn" if xsa_make_libs.get("risky", 0) else "ok"
        checks.append({
            "id": "xsa_make_libs",
            "label": "XSA driver make.libs",
            "status": status,
            "detail": f"{xsa_make_libs.get('total', 0)} make.libs, {xsa_make_libs.get('risky', 0)} riskli.",
        })
    else:
        checks.append({
            "id": "xsa_make_libs",
            "label": "XSA driver make.libs",
            "status": "neutral",
            "detail": "XSA zip içeriği okunamadı veya make.libs içermiyor.",
        })

    if workspace_make_libs is not None:
        status = "warn" if workspace_make_libs.get("risky", 0) else "ok"
        checks.append({
            "id": "workspace_make_libs",
            "label": "Workspace BSP make.libs",
            "status": status,
            "detail": f"{workspace_make_libs.get('total', 0)} make.libs, {workspace_make_libs.get('risky', 0)} riskli.",
        })

    if log_make_libs_targets:
        labels = ", ".join(str(item.get("driver", "")) for item in log_make_libs_targets[:4])
        checks.append({
            "id": "log_make_libs_targets",
            "label": "Log make.libs hedefleri",
            "status": "warn",
            "detail": f"Build log {len(log_make_libs_targets)} make.libs hedefi gösteriyor: {labels}.",
        })

    if elf_artifacts is not None:
        application_count = int(elf_artifacts.get("application", 0))
        total_count = int(elf_artifacts.get("total", 0))
        if application_count:
            status = "ok"
            detail = f"{application_count} application ELF bulundu."
        elif total_count:
            status = "warn"
            detail = f"{total_count} ELF bulundu ama application adıyla eşleşen ELF bulunamadı."
        else:
            status = "error"
            detail = "Application ELF bulunamadı; Vitis build çıktı üretmemiş olabilir."
        checks.append({
            "id": "elf_artifacts",
            "label": "Application ELF",
            "status": status,
            "detail": detail,
        })

    if requires_lwip:
        checks.append({
            "id": "lwip",
            "label": "lwIP",
            "status": "warn",
            "detail": f"Test Bench TCP agent için lwIP gerekli; hedef API mode: {lwip_api_mode or 'bilinmiyor'}.",
        })

    if xsa_patched_count or host_patched_count:
        checks.append({
            "id": "patch",
            "label": "BSP patch",
            "status": "ok",
            "detail": f"XSA patch {xsa_patched_count}, workspace patch {host_patched_count}.",
        })
    elif custom_ip_driver_policy == "auto_none":
        checks.append({
            "id": "patch",
            "label": "BSP patch",
            "status": "neutral",
            "detail": "Patch uygulanmadı; driver none başarılı olmuş olabilir veya patchlenecek make.libs henüz oluşmamış olabilir.",
        })

    self_heal_success = bool(self_heal and self_heal.get("successful"))
    if error_codes:
        checks.append({
            "id": "error_codes",
            "label": "Hata kodları",
            "status": "error",
            "detail": ", ".join(error_codes),
        })

    if recovered_error_codes:
        checks.append({
            "id": "recovered_error_codes",
            "label": "Self-heal ile kapanan hata kodları",
            "status": "ok" if self_heal_success else "warn",
            "detail": ", ".join(recovered_error_codes),
        })

    if self_heal:
        checks.append({
            "id": "self_heal",
            "label": "Self-heal",
            "status": "ok" if self_heal.get("successful") else "warn" if self_heal.get("attempted") else "neutral",
            "detail": self_heal.get("message") or "Self-heal gerekli olmadı.",
        })

    if any(issue.get("category") == "custom_ip_bsp_driver" for issue in issues):
        hints.append("Custom IP BSP driver source'suz görünüyor; `Auto: custom IP - none` ve temiz workspace/temp ile tekrar dene.")
    if log_make_libs_targets and workspace_make_libs and workspace_make_libs.get("total", 0) == 0:
        hints.append("Build log make.libs hedefi gösteriyor ama dosya taramada yok; self-heal sentetik no-op make.libs üretmeyi dener.")
    if not custom_pl_ips and custom_ip_driver_policy == "auto_none":
        hints.append("Custom IP listesi 0 ise HWH custom IP'yi standart IP gibi gösteriyor olabilir; Doctor panelindeki XSA make.libs risk sayısını kontrol et.")
    if requires_lwip and lwip_api_mode:
        hints.append(f"lwIP gerekiyorsa Vitis BSP içinde API mode değerinin {lwip_api_mode} olduğundan emin ol.")
    if elf_artifacts is not None and int(elf_artifacts.get("application", 0)) == 0:
        hints.append("Application ELF bulunamazsa workspace tamam sayılmamalıdır; app build logunu ve application proje adını kontrol et.")

    severity_order = {"error": 3, "warn": 2, "neutral": 1, "ok": 0}
    severity = max((severity_order.get(check["status"], 0) for check in checks), default=0)
    status = "error" if severity >= 3 else "warn" if severity == 2 else "ok"
    return {
        "status": status,
        "privacy": "Tanı bilgisi lokal UI içindir; otomatik dışarı aktarım yapılmaz.",
        "error_codes": error_codes,
        "recovered_error_codes": recovered_error_codes,
        "checks": checks,
        "hints": hints[:6],
        "custom_ip_candidates": [
            {
                "instance": item.instance,
                "ip_name": item.ip_name,
                "reason": item.reason,
            }
            for item in custom_pl_ips[:24]
        ],
        "xsa_make_libs": xsa_make_libs,
        "workspace_make_libs": workspace_make_libs,
        "log_make_libs_targets": log_make_libs_targets,
        "elf_artifacts": elf_artifacts,
    }


def render_xsct_script(
    *,
    workspace_path: Path,
    xsa_path: Path,
    source_root: Path,
    platform_name: str,
    system_name: str,
    domain_name: str,
    app_name: str,
    processor: str,
    os_name: str,
    enable_lwip: bool = False,
    custom_ip_driver_policy: str = "auto_none",
    custom_ip_instances: list[str] | None = None,
    source_include_dirs: list[str] | None = None,
) -> str:
    lwip_flag = "1" if enable_lwip else "0"
    lwip_api_mode = vitis_lwip_api_mode(os_name) if enable_lwip else ""
    custom_ip_driver_policy = normalize_custom_ip_driver_policy(custom_ip_driver_policy)
    custom_ip_instances = custom_ip_instances or []
    source_include_dirs = source_include_dirs or []
    include_dir_list = _tcl_list(source_include_dirs)
    custom_ip_list = _tcl_list(custom_ip_instances)
    bsp_config_script = (
        "proc spec2codeNormalizeCustomIpToken {value} {\n"
        "    set lowered [string tolower $value]\n"
        "    regsub -all {[^a-z0-9_]+} $lowered {_} normalized\n"
        "    return [string trim $normalized {_}]\n"
        "}\n\n"
        "proc spec2codeCustomIpAliases {custom_ip} {\n"
        "    set normalized [spec2codeNormalizeCustomIpToken $custom_ip]\n"
        "    set aliases [list $normalized]\n"
        "    if {[regexp {^(.+)_([0-9]+)$} $normalized -> base index]} {\n"
        "        lappend aliases $base\n"
        "    }\n"
        "    return [lsort -unique $aliases]\n"
        "}\n\n"
        "proc spec2codeCollectMakeLibs {root result_var} {\n"
        "    upvar 1 $result_var result\n"
        "    foreach child [glob -nocomplain -directory $root *] {\n"
        "        if {[file isdirectory $child]} {\n"
        "            if {[file tail $child] eq \"src\"} {\n"
        "                set make_libs [file join $child make.libs]\n"
        "                if {[file exists $make_libs]} {\n"
        "                    lappend result $make_libs\n"
        "                }\n"
        "            }\n"
        "            spec2codeCollectMakeLibs $child result\n"
        "        }\n"
        "    }\n"
        "}\n\n"
        "proc spec2codeIsCustomIpMakeLibs {make_libs} {\n"
        "    global spec2code_custom_ip_instances\n"
        "    set libsrc_dir [file dirname [file dirname $make_libs]]\n"
        "    set libsrc_name [spec2codeNormalizeCustomIpToken [file tail $libsrc_dir]]\n"
        "    foreach custom_ip $spec2code_custom_ip_instances {\n"
        "        foreach alias [spec2codeCustomIpAliases $custom_ip] {\n"
        "            if {$libsrc_name eq $alias || [string match \"${alias}_v*\" $libsrc_name] || [string first \"${alias}_\" $libsrc_name] == 0} {\n"
        "                return 1\n"
        "            }\n"
        "        }\n"
        "    }\n"
        "    return 0\n"
        "}\n\n"
        "proc spec2codeMakeLibsLooksSourceLess {make_libs} {\n"
        "    set src_dir [file dirname $make_libs]\n"
        "    set libsrc_dir [file dirname $src_dir]\n"
        "    set libsrc_name [spec2codeNormalizeCustomIpToken [file tail $libsrc_dir]]\n"
        "    foreach protected_prefix {xil x} {\n"
        "        if {[string first $protected_prefix $libsrc_name] == 0} {\n"
        "            return 0\n"
        "        }\n"
        "    }\n"
        "    set c_files [glob -nocomplain -directory $src_dir *.c]\n"
        "    if {[llength $c_files] > 0} {\n"
        "        return 0\n"
        "    }\n"
        "    if {[catch {set fd [open $make_libs r]} open_err]} {\n"
        "        return 0\n"
        "    }\n"
        "    set content [read $fd]\n"
        "    close $fd\n"
        "    return [expr {[string first \"*.c\" $content] >= 0}]\n"
        "}\n\n"
        "proc spec2codeWriteNoopMakeLibs {make_libs} {\n"
        "    set backup \"${make_libs}.spec2code_backup\"\n"
        "    if {![file exists $backup] && [file exists $make_libs]} {\n"
        "        catch {file copy -force $make_libs $backup}\n"
        "    }\n"
        "    set fd [open $make_libs w]\n"
        "    puts $fd \"# Spec2Code: source-less custom PL IP BSP driver disabled.\"\n"
        "    puts $fd \".PHONY: all libs include install clean\"\n"
        "    puts $fd \"all: libs\"\n"
        "    puts $fd \"libs:\"\n"
        "    puts $fd \"include:\"\n"
        "    puts $fd \"install: libs\"\n"
        "    puts $fd \"clean:\"\n"
        "    close $fd\n"
        "}\n\n"
        "proc spec2codeDisableCustomIpBspLibsrc {} {\n"
        "    global workspace_path spec2code_custom_ip_driver_policy spec2code_custom_ip_instances\n"
        "    if {$spec2code_custom_ip_driver_policy ne \"auto_none\"} {\n"
        "        return 0\n"
        "    }\n"
        "    set make_libs_files [list]\n"
        "    spec2codeCollectMakeLibs $workspace_path make_libs_files\n"
        "    set patched 0\n"
        "    foreach make_libs $make_libs_files {\n"
        "        if {[spec2codeIsCustomIpMakeLibs $make_libs] || [spec2codeMakeLibsLooksSourceLess $make_libs]} {\n"
        "            if {[catch {spec2codeWriteNoopMakeLibs $make_libs} patch_err]} {\n"
        f"                {_tcl_put('WARNING: custom IP BSP make.libs patch failed for $make_libs: $patch_err')}"
        "            } else {\n"
        "                incr patched\n"
        f"                {_tcl_put('custom IP BSP make.libs disabled: $make_libs')}"
        "            }\n"
        "        }\n"
        "    }\n"
        "    if {$patched == 0} {\n"
        f"        {_tcl_put('custom IP BSP make.libs bypass found no matching libsrc folders yet')}"
        "    }\n"
        "    return $patched\n"
        "}\n\n"
        "proc spec2codeConfigureBsp {} {\n"
        "    global spec2code_enable_lwip spec2code_lwip_api_mode spec2code_custom_ip_driver_policy spec2code_custom_ip_instances\n"
        "    if {$spec2code_custom_ip_driver_policy eq \"auto_none\" && [llength $spec2code_custom_ip_instances] > 0} {\n"
        f"        {_tcl_put('custom PL IP candidates detected; setting BSP drivers to none where possible')}"
        "        set spec2code_custom_ip_driver_changed 0\n"
        "        foreach spec2code_custom_ip $spec2code_custom_ip_instances {\n"
        "            set spec2code_custom_ip_ok 0\n"
        "            foreach spec2code_none_driver {none None NONE} {\n"
        "                if {$spec2code_custom_ip_ok == 0} {\n"
        "                    if {[catch {bsp setdriver -ip $spec2code_custom_ip -driver $spec2code_none_driver} spec2code_custom_ip_err]} {\n"
        f"                        {_tcl_put('custom IP $spec2code_custom_ip driver=$spec2code_none_driver not selected: $spec2code_custom_ip_err')}"
        "                    } else {\n"
        "                        set spec2code_custom_ip_ok 1\n"
        "                        set spec2code_custom_ip_driver_changed 1\n"
        f"                        {_tcl_put('custom IP $spec2code_custom_ip driver set to $spec2code_none_driver')}"
        "                    }\n"
        "                }\n"
        "            }\n"
        "            if {$spec2code_custom_ip_ok == 0} {\n"
        f"                {_tcl_put('WARNING: custom IP $spec2code_custom_ip driver could not be set to none automatically; check BSP settings if build fails inside this IP driver.')}"
        "            }\n"
        "        }\n"
        "        if {$spec2code_custom_ip_driver_changed == 1} {\n"
        "            spec2codeDisableCustomIpBspLibsrc\n"
        "            if {[catch {bsp regenerate} spec2code_custom_ip_regen_err]} {\n"
        f"                {_tcl_put('WARNING: BSP regenerate failed after custom IP driver policy: $spec2code_custom_ip_regen_err')}"
        "            }\n"
        "            spec2codeDisableCustomIpBspLibsrc\n"
        "        }\n"
        "    } elseif {$spec2code_custom_ip_driver_policy eq \"keep\"} {\n"
        f"        {_tcl_put('custom PL IP driver policy keeps BSP defaults')}"
        "    }\n\n"
        "    if {$spec2code_enable_lwip == 1} {\n"
        f"        {_tcl_put('lwIP target test bench detected; enabling BSP lwIP library')}"
        "        set spec2code_lwip_ok 0\n"
        "        foreach spec2code_lwip_lib {lwip220 lwip213 lwip211 lwip202} {\n"
        "            if {$spec2code_lwip_ok == 0} {\n"
        "                if {[catch {bsp setlib -name $spec2code_lwip_lib} spec2code_lwip_err]} {\n"
        f"                    {_tcl_put('lwIP library $spec2code_lwip_lib not selected: $spec2code_lwip_err')}"
        "                } else {\n"
        "                    set spec2code_lwip_ok 1\n"
        f"                    {_tcl_put('lwIP library selected: $spec2code_lwip_lib')}"
        "                }\n"
        "            }\n"
        "        }\n"
        "        if {$spec2code_lwip_ok == 1} {\n"
        f"            {_tcl_put('configuring lwIP API mode: $spec2code_lwip_api_mode')}"
        "            set spec2code_lwip_api_mode_ok 0\n"
        "            foreach spec2code_lwip_api_name {api_mode API_MODE} {\n"
        "                if {$spec2code_lwip_api_mode_ok == 0} {\n"
        "                    if {[catch {bsp config $spec2code_lwip_api_name $spec2code_lwip_api_mode} spec2code_lwip_api_err]} {\n"
        f"                        {_tcl_put('lwIP API mode $spec2code_lwip_api_name=$spec2code_lwip_api_mode not selected: $spec2code_lwip_api_err')}"
        "                    } else {\n"
        "                        set spec2code_lwip_api_mode_ok 1\n"
        f"                        {_tcl_put('lwIP API mode selected: $spec2code_lwip_api_name=$spec2code_lwip_api_mode')}"
        "                    }\n"
        "                }\n"
        "            }\n"
        "            if {$spec2code_lwip_api_mode_ok == 0} {\n"
        f"                {_tcl_put('WARNING: lwIP API mode could not be set automatically; check BSP api_mode manually before relying on this workspace.')}"
        "            }\n"
        "            spec2codeDisableCustomIpBspLibsrc\n"
        "            if {[catch {bsp regenerate} spec2code_lwip_regen_err]} {\n"
        f"                {_tcl_put('WARNING: BSP regenerate failed after lwIP selection: $spec2code_lwip_regen_err')}"
        "            }\n"
        "            spec2codeDisableCustomIpBspLibsrc\n"
        "        } else {\n"
        f"            {_tcl_put('WARNING: lwIP BSP library could not be enabled automatically; enable it manually if build reports missing lwIP headers.')}"
        "        }\n"
        "    }\n"
        "}\n\n"
        "proc spec2codeSynchronizeBeforeAppBuild {} {\n"
        "    global platform_name domain_name\n"
        f"    {_tcl_put('synchronizing platform/domain before application build')}"
        "    catch {platform active $platform_name} spec2code_platform_active_err\n"
        "    catch {domain active $domain_name} spec2code_domain_active_err\n"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    if {[catch {bsp regenerate} spec2code_bsp_regen_before_app_err]} {\n"
        f"        {_tcl_put('WARNING: BSP regenerate before app build failed or was unsupported: $spec2code_bsp_regen_before_app_err')}"
        "    } else {\n"
        f"        {_tcl_put('BSP regenerate before app build completed')}"
        "    }\n"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    if {[catch {platform generate} spec2code_platform_generate_before_app_err]} {\n"
        f"        {_tcl_put('platform generate unsupported or failed, trying platform build: $spec2code_platform_generate_before_app_err')}"
        "        if {[catch {platform build} spec2code_platform_build_before_app_err]} {\n"
        f"            {_tcl_put('WARNING: platform build before app build failed or was unsupported: $spec2code_platform_build_before_app_err')}"
        "        } else {\n"
        f"            {_tcl_put('platform build before app build completed')}"
        "        }\n"
        "    } else {\n"
        f"        {_tcl_put('platform generate before app build completed')}"
        "    }\n"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    after 1000\n"
        "}\n\n"
        "proc spec2codeEnsureApplicationElf {} {\n"
        "    global workspace_path app_name\n"
        "    set spec2code_expected_elf [file join $workspace_path $app_name Debug ${app_name}.elf]\n"
        "    if {[file exists $spec2code_expected_elf]} {\n"
        f"        {_tcl_put('application ELF present: $spec2code_expected_elf')}"
        "        return\n"
        "    }\n"
        f"    {_tcl_put('app build produced no application ELF; running make directly in Debug as fallback')}"
        "    set spec2code_app_debug_dir [file join $workspace_path $app_name Debug]\n"
        "    if {![file isdirectory $spec2code_app_debug_dir]} {\n"
        "        error \"Spec2Code: application Debug directory missing after app build; app project makefiles were not generated: $spec2code_app_debug_dir\"\n"
        "    }\n"
        "    set spec2code_prev_dir [pwd]\n"
        "    cd $spec2code_app_debug_dir\n"
        "    set spec2code_make_status [catch {exec make all >&@ stdout} spec2code_make_err]\n"
        "    cd $spec2code_prev_dir\n"
        "    if {$spec2code_make_status != 0 && ![file exists $spec2code_expected_elf]} {\n"
        "        error \"Spec2Code: direct make fallback failed: $spec2code_make_err\"\n"
        "    }\n"
        "    if {![file exists $spec2code_expected_elf]} {\n"
        "        error \"Spec2Code: application ELF still missing after direct make fallback: $spec2code_expected_elf\"\n"
        "    }\n"
        f"    {_tcl_put('application ELF present after make fallback: $spec2code_expected_elf')}"
        "}\n\n"
    )
    return (
        "# Spec2Code generated Vitis workspace script.\n"
        "# This script is intentionally plain XSCT so it works in air-gapped Windows hosts.\n"
        "catch {fconfigure stdout -buffering line}\n"
        f"set workspace_path {_tcl_path(workspace_path)}\n"
        f"set xsa_path {_tcl_path(xsa_path)}\n"
        f"set source_path {_tcl_path(source_root)}\n"
        f"set platform_name {{{platform_name}}}\n"
        f"set system_name {{{system_name}}}\n"
        f"set domain_name {{{domain_name}}}\n"
        f"set app_name {{{app_name}}}\n"
        f"set processor {{{processor}}}\n"
        f"set os_name {{{os_name}}}\n\n"
        f"set spec2code_enable_lwip {lwip_flag}\n\n"
        f"set spec2code_lwip_api_mode {{{lwip_api_mode}}}\n\n"
        f"set spec2code_custom_ip_driver_policy {{{custom_ip_driver_policy}}}\n"
        f"set spec2code_custom_ip_instances [list {custom_ip_list}]\n\n"
        f"{bsp_config_script}"
        f"{_tcl_put('workspace: $workspace_path')}"
        f"{_tcl_put('xsa: $xsa_path')}"
        f"{_tcl_put('source: $source_path')}"
        f"{_tcl_put('platform: $platform_name')}"
        f"{_tcl_put('system: $system_name')}"
        f"{_tcl_put('application: $app_name')}"
        "setws $workspace_path\n\n"
        f"{_tcl_put('creating named platform/system/application from XSA')}"
        "if {[catch {\n"
        "    platform create -name $platform_name -hw $xsa_path\n"
        "    platform active $platform_name\n"
        "    domain create -name $domain_name -proc $processor -os $os_name\n"
        "    domain active $domain_name\n"
        "    if {[catch {app create -name $app_name -platform $platform_name -domain $domain_name -sysproj $system_name -lang C -template {Empty Application(C)}} app_err]} {\n"
        f"        {_tcl_put('Empty Application(C) template failed: $app_err')}"
        f"        {_tcl_put('retrying with Empty Application template')}"
        "        app create -name $app_name -platform $platform_name -domain $domain_name -sysproj $system_name -lang C -template {Empty Application}\n"
        "    }\n"
        "    domain active $domain_name\n"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    spec2codeConfigureBsp\n"
        "} spec2code_create_err]} {\n"
        f"    {_tcl_put('named platform/system flow failed: $spec2code_create_err')}"
        f"    {_tcl_put('retrying with legacy app create flow')}"
        "    if {[catch {app create -name $app_name -hw $xsa_path -proc $processor -os $os_name -lang C -template {Empty Application(C)}} app_err]} {\n"
        f"        {_tcl_put('Empty Application(C) template failed: $app_err')}"
        f"        {_tcl_put('retrying with Empty Application template')}"
        "        app create -name $app_name -hw $xsa_path -proc $processor -os $os_name -lang C -template {Empty Application}\n"
        "    }\n"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    spec2codeConfigureBsp\n"
        "}\n\n"
        "set spec2code_app_listing {}\n"
        "catch {set spec2code_app_listing [app list]}\n"
        "if {[string first $app_name $spec2code_app_listing] < 0} {\n"
        f"    {_tcl_put('FATAL: application project was not created; app list does not contain $app_name')}"
        "    error \"Spec2Code: application project '$app_name' was not created in the workspace. Workspace may contain stale state from a previous run; use an empty workspace directory.\"\n"
        "}\n\n"
        f"{_tcl_put('importing generated sources')}"
        "importsources -name $app_name -path $source_path\n\n"
        "# Generated sources live in subfolders (drivers/, tests/); the CDT app\n"
        "# build only gets the BSP include path by default, so cross-folder\n"
        "# quote-includes fail without explicit include paths.\n"
        f"set spec2code_source_include_dirs [list {include_dir_list}]\n"
        "foreach spec2code_inc_dir $spec2code_source_include_dirs {\n"
        "    set spec2code_inc_path [file join $workspace_path $app_name src $spec2code_inc_dir]\n"
        "    if {![file isdirectory $spec2code_inc_path]} { continue }\n"
        "    if {[catch {app config -name $app_name -add include-path $spec2code_inc_path} spec2code_inc_err]} {\n"
        f"        {_tcl_put('WARNING: include path not added ($spec2code_inc_path): $spec2code_inc_err')}"
        "    } else {\n"
        f"        {_tcl_put('application include path added: $spec2code_inc_path')}"
        "    }\n"
        "}\n\n"
        "spec2codeSynchronizeBeforeAppBuild\n"
        f"{_tcl_put('building application')}"
        "spec2codeDisableCustomIpBspLibsrc\n"
        "if {[catch {app build -name $app_name} spec2code_build_err]} {\n"
        f"    {_tcl_put('app build failed; refreshing custom IP BSP make.libs bypass and retrying once: $spec2code_build_err')}"
        "    spec2codeDisableCustomIpBspLibsrc\n"
        "    spec2codeSynchronizeBeforeAppBuild\n"
        "    app build -name $app_name\n"
        "}\n"
        "spec2codeEnsureApplicationElf\n"
        f"{_tcl_put('done')}"
        "exit\n"
    )


def render_xsct_recovery_script(
    *,
    workspace_path: Path,
    platform_name: str,
    domain_name: str,
    app_name: str,
    custom_ip_driver_policy: str = "auto_none",
    custom_ip_instances: list[str] | None = None,
) -> str:
    custom_ip_driver_policy = normalize_custom_ip_driver_policy(custom_ip_driver_policy)
    custom_ip_instances = custom_ip_instances or []
    custom_ip_list = _tcl_list(custom_ip_instances)
    return (
        "# Spec2Code generated Vitis self-heal script.\n"
        "# Existing workspace is reused; no data is exported outside the selected temp/workspace folders.\n"
        "catch {fconfigure stdout -buffering line}\n"
        f"set workspace_path {_tcl_path(workspace_path)}\n"
        f"set platform_name {{{platform_name}}}\n"
        f"set domain_name {{{domain_name}}}\n"
        f"set app_name {{{app_name}}}\n"
        f"set spec2code_custom_ip_driver_policy {{{custom_ip_driver_policy}}}\n"
        f"set spec2code_custom_ip_instances [list {custom_ip_list}]\n\n"
        "proc spec2codeNormalizeCustomIpToken {value} {\n"
        "    set lowered [string tolower $value]\n"
        "    regsub -all {[^a-z0-9_]+} $lowered {_} normalized\n"
        "    return [string trim $normalized {_}]\n"
        "}\n\n"
        "proc spec2codeCustomIpAliases {custom_ip} {\n"
        "    set normalized [spec2codeNormalizeCustomIpToken $custom_ip]\n"
        "    set aliases [list $normalized]\n"
        "    if {[regexp {^(.+)_([0-9]+)$} $normalized -> base index]} {\n"
        "        lappend aliases $base\n"
        "    }\n"
        "    return [lsort -unique $aliases]\n"
        "}\n\n"
        "proc spec2codeCollectMakeLibs {root result_var} {\n"
        "    upvar 1 $result_var result\n"
        "    foreach child [glob -nocomplain -directory $root *] {\n"
        "        if {[file isdirectory $child]} {\n"
        "            if {[file tail $child] eq \"src\"} {\n"
        "                set make_libs [file join $child make.libs]\n"
        "                if {[file exists $make_libs]} { lappend result $make_libs }\n"
        "            }\n"
        "            spec2codeCollectMakeLibs $child result\n"
        "        }\n"
        "    }\n"
        "}\n\n"
        "proc spec2codeIsCustomIpMakeLibs {make_libs} {\n"
        "    global spec2code_custom_ip_instances\n"
        "    set libsrc_name [spec2codeNormalizeCustomIpToken [file tail [file dirname [file dirname $make_libs]]]]\n"
        "    foreach custom_ip $spec2code_custom_ip_instances {\n"
        "        foreach alias [spec2codeCustomIpAliases $custom_ip] {\n"
        "            if {$libsrc_name eq $alias || [string match \"${alias}_v*\" $libsrc_name] || [string first \"${alias}_\" $libsrc_name] == 0} { return 1 }\n"
        "        }\n"
        "    }\n"
        "    return 0\n"
        "}\n\n"
        "proc spec2codeMakeLibsLooksSourceLess {make_libs} {\n"
        "    set src_dir [file dirname $make_libs]\n"
        "    set libsrc_name [spec2codeNormalizeCustomIpToken [file tail [file dirname $src_dir]]]\n"
        "    foreach protected_prefix {xil x lwip freertos standalone} {\n"
        "        if {[string first $protected_prefix $libsrc_name] == 0} { return 0 }\n"
        "    }\n"
        "    if {[llength [glob -nocomplain -directory $src_dir *.c]] > 0} { return 0 }\n"
        "    if {[catch {set fd [open $make_libs r]}]} { return 0 }\n"
        "    set content [read $fd]\n"
        "    close $fd\n"
        "    return [expr {[string first \"*.c\" $content] >= 0}]\n"
        "}\n\n"
        "proc spec2codeWriteNoopMakeLibs {make_libs} {\n"
        "    set backup \"${make_libs}.spec2code_backup\"\n"
        "    if {![file exists $backup] && [file exists $make_libs]} { catch {file copy -force $make_libs $backup} }\n"
        "    set fd [open $make_libs w]\n"
        "    puts $fd \"# Spec2Code: source-less custom PL IP BSP driver disabled by self-heal.\"\n"
        "    puts $fd \".PHONY: all libs include install clean\"\n"
        "    puts $fd \"all: libs\"\n"
        "    puts $fd \"libs:\"\n"
        "    puts $fd \"include:\"\n"
        "    puts $fd \"install: libs\"\n"
        "    puts $fd \"clean:\"\n"
        "    close $fd\n"
        "}\n\n"
        "proc spec2codeDisableCustomIpBspLibsrc {} {\n"
        "    global workspace_path spec2code_custom_ip_driver_policy\n"
        "    if {$spec2code_custom_ip_driver_policy ne \"auto_none\"} { return 0 }\n"
        "    set make_libs_files [list]\n"
        "    spec2codeCollectMakeLibs $workspace_path make_libs_files\n"
        "    set patched 0\n"
        "    foreach make_libs $make_libs_files {\n"
        "        if {[spec2codeIsCustomIpMakeLibs $make_libs] || [spec2codeMakeLibsLooksSourceLess $make_libs]} {\n"
        "            spec2codeWriteNoopMakeLibs $make_libs\n"
        "            incr patched\n"
        f"            {_tcl_put('self-heal custom IP BSP make.libs disabled: $make_libs')}"
        "        }\n"
        "    }\n"
        "    return $patched\n"
        "}\n\n"
        f"{_tcl_put('self-heal workspace: $workspace_path')}"
        "setws $workspace_path\n"
        "catch {platform active $platform_name} spec2code_platform_err\n"
        "catch {domain active $domain_name} spec2code_domain_err\n"
        "if {$spec2code_custom_ip_driver_policy eq \"auto_none\"} {\n"
        "    foreach spec2code_custom_ip $spec2code_custom_ip_instances {\n"
        "        foreach spec2code_none_driver {none None NONE} {\n"
        "            catch {bsp setdriver -ip $spec2code_custom_ip -driver $spec2code_none_driver}\n"
        "        }\n"
        "    }\n"
        "}\n"
        "spec2codeDisableCustomIpBspLibsrc\n"
        "catch {bsp regenerate} spec2code_regen_err\n"
        "spec2codeDisableCustomIpBspLibsrc\n"
        f"{_tcl_put('self-heal rebuilding application')}"
        "app build -name $app_name\n"
        "set spec2code_expected_elf [file join $workspace_path $app_name Debug ${app_name}.elf]\n"
        "if {![file exists $spec2code_expected_elf]} {\n"
        f"    {_tcl_put('self-heal app build produced no application ELF; running make directly in Debug as fallback')}"
        "    set spec2code_app_debug_dir [file join $workspace_path $app_name Debug]\n"
        "    if {![file isdirectory $spec2code_app_debug_dir]} {\n"
        "        error \"Spec2Code: application Debug directory missing after app build; app project makefiles were not generated: $spec2code_app_debug_dir\"\n"
        "    }\n"
        "    cd $spec2code_app_debug_dir\n"
        "    set spec2code_make_status [catch {exec make all >&@ stdout} spec2code_make_err]\n"
        "    if {$spec2code_make_status != 0 && ![file exists $spec2code_expected_elf]} {\n"
        "        error \"Spec2Code: direct make fallback failed: $spec2code_make_err\"\n"
        "    }\n"
        "    if {![file exists $spec2code_expected_elf]} {\n"
        "        error \"Spec2Code: application ELF still missing after direct make fallback: $spec2code_expected_elf\"\n"
        "    }\n"
        "}\n"
        f"{_tcl_put('self-heal done')}"
        "exit\n"
    )


class VitisWorkspaceJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, VitisWorkspaceJob] = {}
        self._counter = 0

    def get(self, job_id: str) -> Optional[VitisWorkspaceJob]:
        return self._jobs.get(job_id)

    async def start(self, generate_job: Job, config: VitisWorkspaceConfig) -> str:
        if not generate_job.result:
            raise ValueError("generate job result is not ready")
        self._counter += 1
        job_id = f"vitis_{self._counter:04d}"
        project = generate_job.spec.get("project", {}).get("name", generate_job.id)
        job = VitisWorkspaceJob(
            id=job_id,
            source_job_id=generate_job.id,
            source_project=project,
            config=config,
            generate_job=generate_job,
            _loop=asyncio.get_running_loop(),
        )
        self._jobs[job_id] = job
        asyncio.create_task(self._run(job))
        return job_id

    async def _run(self, job: VitisWorkspaceJob) -> None:
        job.status = "running"
        job.emit({
            "event": "vitis.start",
            "stage": "start",
            "progress": 5,
            "message": "Vitis workspace akışı başlatıldı.",
        })
        try:
            await asyncio.to_thread(self._blocking, job)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - report Vitis/host failures directly
            job.status = "error"
            job.error = str(exc)
            job.emit({
                "event": "vitis.error",
                "stage": "error",
                "progress": 100,
                "message": str(exc),
                "trace": traceback.format_exc().splitlines()[-5:],
            })
        finally:
            final_stage = "done" if job.status == "done" else "error"
            job.emit({"event": "vitis.end", "stage": final_stage, "progress": 100, "status": job.status})
            loop = job._loop
            if loop is not None:
                for queue in list(job.subscribers):
                    loop.call_soon_threadsafe(queue.put_nowait, None)

    def _blocking(self, job: VitisWorkspaceJob) -> None:
        config = job.config
        project = job.generate_job.spec.get("project", {})
        processor = config.processor.strip() or default_vitis_processor(
            str(project.get("platform", "")),
            str(project.get("target_core", "")),
        )
        os_name = vitis_os(config.runtime or str(project.get("runtime", "")))
        name_base = _safe_identifier(job.source_project, "spec2code")
        platform_name = _safe_identifier(config.platform_name or f"{name_base}_platform", f"spec2code_platform_{job.id}")
        system_name = _safe_identifier(config.system_name or f"{name_base}_system", f"spec2code_system_{job.id}")
        app_name = _safe_identifier(config.app_name or f"{name_base}_app", f"spec2code_app_{job.id}")
        domain_name = _safe_identifier(f"{app_name}_domain", f"spec2code_domain_{job.id}")

        job.emit({"event": "vitis.locate", "stage": "locate", "progress": 14, "message": "XSCT aranıyor."})
        xsct = detect_xsct(config.vitis_path)
        job.emit({
            "event": "vitis.version",
            "stage": "version",
            "progress": 25,
            "message": f"Vitis/XSCT algılandı: {xsct.version}",
            "xsct_path": str(xsct.path),
            "vitis_version": xsct.version,
            "version_source": xsct.version_source,
        })

        input_xsa_path = _clean_user_path(config.xsa_path)
        if not input_xsa_path.is_file() or input_xsa_path.suffix.lower() != ".xsa":
            raise FileNotFoundError(f"XSA file not found or invalid: {input_xsa_path}")

        workspace_path = _clean_user_path(config.workspace_path)
        workspace_path.mkdir(parents=True, exist_ok=True)
        temp_path = _clean_user_path(config.temp_path)
        temp_path.mkdir(parents=True, exist_ok=True)
        staging_root = temp_path / job.id
        # Job ids restart with the backend process; never clobber a previous
        # run's staging (its logs are the user's debug evidence).
        suffix = 1
        while staging_root.exists():
            suffix += 1
            staging_root = temp_path / f"{job.id}_{suffix}"
        source_root = staging_root / "src"
        hw_root = staging_root / "hw"
        log_dir = staging_root / "logs"
        hw_root.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        staged_xsa_path = hw_root / input_xsa_path.name
        shutil.copy2(input_xsa_path, staged_xsa_path)

        custom_ip_driver_policy = normalize_custom_ip_driver_policy(config.custom_ip_driver_policy)
        custom_pl_ips = discover_custom_pl_ips(staged_xsa_path) if custom_ip_driver_policy == "auto_none" else []
        custom_ip_instances = [item.instance for item in custom_pl_ips]
        xsa_make_libs_preflight = inspect_xsa_make_libs(
            staged_xsa_path,
            custom_ip_instances,
            custom_ip_driver_policy,
        )
        xsa_patched_make_libs = patch_xsa_custom_ip_make_libs(
            staged_xsa_path,
            custom_ip_instances,
            custom_ip_driver_policy,
        )
        xsa_neutralized_driver_dirs = neutralize_custom_ip_drivers_in_xsa(
            staged_xsa_path,
            custom_ip_instances,
            custom_ip_driver_policy,
        )
        if xsa_neutralized_driver_dirs:
            job.emit({
                "event": "vitis.custom_ip_driver_neutralize",
                "stage": "stage_sources",
                "progress": 33,
                "message": (
                    "Staged XSA içindeki custom PL IP driver build reçeteleri no-op yapıldı; "
                    "tüm BSP'lerde (FSBL/PMUFW dahil) bu driver derlenmeyecek: "
                    + ", ".join(xsa_neutralized_driver_dirs)
                ),
                "neutralized_driver_dirs": xsa_neutralized_driver_dirs,
            })
        if custom_ip_driver_policy == "auto_none" and custom_pl_ips:
            job.emit({
                "event": "vitis.custom_ip_policy",
                "stage": "stage_sources",
                "progress": 34,
                "message": f"{len(custom_pl_ips)} custom PL IP adayı bulundu; BSP driver none denenebilir.",
                "custom_pl_ip_instances": [item.instance for item in custom_pl_ips],
            })
        elif custom_ip_driver_policy == "keep":
            job.emit({
                "event": "vitis.custom_ip_policy",
                "stage": "stage_sources",
                "progress": 34,
                "message": "Custom PL IP driver policy BSP default değerlerini koruyacak.",
            })
        if xsa_patched_make_libs:
            job.emit({
                "event": "vitis.custom_ip_xsa_patch",
                "stage": "stage_sources",
                "progress": 36,
                "message": f"{len(xsa_patched_make_libs)} custom IP driver make.libs staged XSA icinde patchlendi.",
                "patched_make_libs": xsa_patched_make_libs,
            })

        job.emit({
            "event": "vitis.stage_sources",
            "stage": "stage_sources",
            "progress": 40,
            "message": "XSA kopyası ve generated C/H kaynakları Vitis staging klasörüne hazırlanıyor.",
        })
        staged_files = stage_vitis_sources(job.generate_job, source_root)
        requires_lwip = any(path.startswith("tests/spec2code_testbench_lwip") for path in staged_files)
        lwip_api_mode = vitis_lwip_api_mode(os_name) if requires_lwip else None
        vitis_doctor = build_vitis_doctor(
            custom_ip_driver_policy=custom_ip_driver_policy,
            custom_pl_ips=custom_pl_ips,
            xsa_make_libs=xsa_make_libs_preflight,
            xsa_patched_count=len(xsa_patched_make_libs),
            requires_lwip=requires_lwip,
            lwip_api_mode=lwip_api_mode,
        )

        script_path = staging_root / "spec2code_create_workspace.tcl"
        recovery_script_path = staging_root / "spec2code_self_heal_workspace.tcl"
        stdout_log = log_dir / "xsct_stdout.log"
        stderr_log = log_dir / "xsct_stderr.log"
        recovery_stdout_log = log_dir / "xsct_self_heal_stdout.log"
        recovery_stderr_log = log_dir / "xsct_self_heal_stderr.log"
        manifest_path = staging_root / "spec2code_vitis_manifest.json"
        manifest = {
            "vitis_job_id": job.id,
            "source_job_id": job.source_job_id,
            "project": job.source_project,
            "xsct_path": str(xsct.path),
            "vitis_version": xsct.version,
            "vitis_version_source": xsct.version_source,
            "xsa_path": str(staged_xsa_path),
            "source_xsa_path": str(input_xsa_path),
            "workspace_path": str(workspace_path),
            "temp_path": str(temp_path),
            "staging_path": str(staging_root),
            "source_path": str(source_root),
            "platform_name": platform_name,
            "system_name": system_name,
            "domain_name": domain_name,
            "app_name": app_name,
            "processor": processor,
            "os": os_name,
            "requires_lwip": requires_lwip,
            "lwip_api_mode": lwip_api_mode,
            "custom_ip_driver_policy": custom_ip_driver_policy,
            "custom_pl_ip_candidates": [asdict(item) for item in custom_pl_ips],
            "xsa_make_libs_preflight": xsa_make_libs_preflight,
            "custom_ip_xsa_make_libs_patched": xsa_patched_make_libs,
            "custom_ip_xsa_make_libs_patched_count": len(xsa_patched_make_libs),
            "custom_ip_xsa_driver_dirs_neutralized": xsa_neutralized_driver_dirs,
            "custom_ip_xsa_driver_dirs_neutralized_count": len(xsa_neutralized_driver_dirs),
            "vitis_doctor": vitis_doctor,
            "staged_files": staged_files,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        job.emit({
            "event": "vitis.script",
            "stage": "script",
            "progress": 55,
            "message": "XSCT Tcl script'i yazılıyor.",
            "staged_files": len(staged_files),
        })
        script_path.write_text(
            render_xsct_script(
                workspace_path=workspace_path,
                xsa_path=staged_xsa_path,
                source_root=source_root,
                platform_name=platform_name,
                system_name=system_name,
                domain_name=domain_name,
                app_name=app_name,
                processor=processor,
                os_name=os_name,
                enable_lwip=requires_lwip,
                custom_ip_driver_policy=custom_ip_driver_policy,
                custom_ip_instances=[item.instance for item in custom_pl_ips],
                source_include_dirs=staged_header_dirs(staged_files),
            ),
            encoding="utf-8",
        )
        recovery_script_path.write_text(
            render_xsct_recovery_script(
                workspace_path=workspace_path,
                platform_name=platform_name,
                domain_name=domain_name,
                app_name=app_name,
                custom_ip_driver_policy=custom_ip_driver_policy,
                custom_ip_instances=custom_ip_instances,
            ),
            encoding="utf-8",
        )

        job.result = {
            **manifest,
            "script_path": str(script_path),
            "recovery_script_path": str(recovery_script_path),
            "manifest_path": str(manifest_path),
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "recovery_stdout_log": str(recovery_stdout_log),
            "recovery_stderr_log": str(recovery_stderr_log),
        }

        job.emit({
            "event": "vitis.run",
            "stage": "run",
            "progress": 72,
            "message": "XSCT çalışıyor; platform/application oluşturulup build alınıyor. Custom IP BSP watcher aktif.",
            "script_path": str(script_path),
        })
        patch_roots = [workspace_path, staging_root, temp_path]
        watcher = CustomIpMakeLibsWatcher(
            patch_roots,
            custom_ip_instances,
            custom_ip_driver_policy,
        )
        watcher.start()

        def _emit_watchdog(events: list[str]) -> None:
            job.emit({
                "event": "vitis.watchdog",
                "stage": "run",
                "progress": 75,
                "message": " | ".join(events),
            })

        try:
            completed = _run_xsct_streaming(
                _command_for(xsct.path, str(script_path)),
                cwd=workspace_path,
                timeout_s=int(config.timeout_s or 1800),
                stdout_path=stdout_log,
                stderr_path=stderr_log,
                emit=_emit_watchdog,
            )
        finally:
            host_patched_make_libs = watcher.stop()
        stdout_log.write_text(completed.stdout, encoding="utf-8")
        stderr_log.write_text(completed.stderr, encoding="utf-8")
        initial_log_text = f"{completed.stdout}\n{completed.stderr}"
        log_make_libs_targets = make_libs_targets_from_log(initial_log_text)
        log_has_fatal_error = _xsct_log_has_fatal_error(completed.stdout, completed.stderr)
        initial_issues = map_vitis_errors(initial_log_text) if (completed.returncode != 0 or log_has_fatal_error) else []
        if completed.timed_out or completed.stalled:
            initial_issues.insert(0, _xsct_hang_issue(completed, script_path))
        self_heal = {
            "attempted": False,
            "successful": False,
            "reason": "",
            "message": "Self-heal gerekli olmadı.",
            "patched_make_libs": [],
            "synthesized_make_libs": [],
            "recovery_script_path": str(recovery_script_path),
            "stdout_log": str(recovery_stdout_log),
            "stderr_log": str(recovery_stderr_log),
        }
        final_completed = completed
        final_stdout = completed.stdout
        final_stderr = completed.stderr
        final_stderr_log_path = stderr_log
        final_issues = initial_issues
        recovery_patched_make_libs: list[str] = []
        synthesized_make_libs: list[str] = []

        if initial_issues and _should_retry_custom_ip_self_heal(initial_issues, custom_ip_driver_policy):
            self_heal["attempted"] = True
            self_heal["reason"] = "custom_ip_bsp_driver"
            job.emit({
                "event": "vitis.self_heal",
                "stage": "run",
                "progress": 94,
                "message": "Custom IP BSP hatası görüldü; workspace lokal olarak patchlenip recovery build deneniyor.",
            })
            recovery_patched_make_libs = patch_custom_ip_make_libs_many(
                patch_roots,
                custom_ip_instances,
                custom_ip_driver_policy,
            )
            synthesized_make_libs = synthesize_make_libs_from_log_targets(
                patch_roots,
                initial_log_text,
                custom_ip_driver_policy,
            )
            all_self_heal_paths = sorted(set(host_patched_make_libs + recovery_patched_make_libs + synthesized_make_libs))
            self_heal["patched_make_libs"] = [_path_tail(path) for path in all_self_heal_paths]
            self_heal["synthesized_make_libs"] = [_path_tail(path) for path in synthesized_make_libs]
            if all_self_heal_paths:
                recovery_completed = _run_xsct_streaming(
                    _command_for(xsct.path, str(recovery_script_path)),
                    cwd=workspace_path,
                    timeout_s=int(config.timeout_s or 1800),
                    stdout_path=recovery_stdout_log,
                    stderr_path=recovery_stderr_log,
                    emit=_emit_watchdog,
                )
                recovery_stdout_log.write_text(recovery_completed.stdout, encoding="utf-8")
                recovery_stderr_log.write_text(recovery_completed.stderr, encoding="utf-8")
                recovery_fatal = _xsct_log_has_fatal_error(recovery_completed.stdout, recovery_completed.stderr)
                if recovery_completed.timed_out or recovery_completed.stalled:
                    recovery_fatal = True
                final_completed = recovery_completed
                final_stdout = f"{completed.stdout}\n\n[Spec2Code self-heal stdout]\n{recovery_completed.stdout}"
                final_stderr = f"{completed.stderr}\n\n[Spec2Code self-heal stderr]\n{recovery_completed.stderr}"
                final_stderr_log_path = recovery_stderr_log
                final_issues = map_vitis_errors(f"{recovery_completed.stdout}\n{recovery_completed.stderr}") if (recovery_completed.returncode != 0 or recovery_fatal) else []
                self_heal["successful"] = recovery_completed.returncode == 0 and not recovery_fatal
                self_heal["message"] = "Recovery build geçti." if self_heal["successful"] else "Recovery build de hata verdi."
            else:
                self_heal["message"] = "Recovery denenmedi; patchlenecek make.libs bulunamadı."

        host_patched_make_libs = sorted(set(host_patched_make_libs + recovery_patched_make_libs + synthesized_make_libs))
        workspace_make_libs = inspect_filesystem_make_libs(patch_roots, custom_ip_instances, custom_ip_driver_policy)
        elf_artifacts = inspect_vitis_elf_artifacts([workspace_path, staging_root], app_name)
        final_has_fatal_error = _xsct_log_has_fatal_error(final_completed.stdout, final_completed.stderr)
        build_failed = (
            final_completed.returncode != 0
            or final_has_fatal_error
            or bool(getattr(final_completed, "timed_out", False))
            or bool(getattr(final_completed, "stalled", False))
        )
        artifact_issues: list[dict] = []
        if int(elf_artifacts.get("application", 0)) == 0:
            if build_failed:
                missing_elf_message = (
                    f"Vitis build hata verdi ve application ELF bulunamadı. "
                    f"Beklenen application adı: {app_name}"
                )
            else:
                missing_elf_message = (
                    f"Vitis build hata vermedi ama application ELF bulunamadı. "
                    f"Beklenen application adı: {app_name}"
                )
            artifact_issues.append({
                "file": str(workspace_path),
                "line": 0,
                "column": 0,
                "rule": "spec2code-vitis-artifact",
                "severity": "error",
                "category": "missing_elf",
                "message": missing_elf_message,
                "source": "Spec2Code",
            })
        recovered_issues = initial_issues if self_heal.get("successful") else []
        doctor_issues = final_issues + artifact_issues
        vitis_doctor = build_vitis_doctor(
            custom_ip_driver_policy=custom_ip_driver_policy,
            custom_pl_ips=custom_pl_ips,
            xsa_make_libs=xsa_make_libs_preflight,
            workspace_make_libs=workspace_make_libs,
            log_make_libs_targets=log_make_libs_targets,
            elf_artifacts=elf_artifacts,
            xsa_patched_count=len(xsa_patched_make_libs),
            host_patched_count=len(host_patched_make_libs),
            requires_lwip=requires_lwip,
            lwip_api_mode=lwip_api_mode,
            issues=doctor_issues,
            recovered_issues=recovered_issues,
            self_heal=self_heal,
        )
        if job.result is not None:
            job.result["xsct_initial_exit_code"] = completed.returncode
            job.result["xsct_exit_code"] = final_completed.returncode
            job.result["xsct_stdout_tail"] = _log_tail(final_stdout)
            job.result["xsct_stderr_tail"] = _log_tail(final_stderr)
            job.result["successful"] = not build_failed and not artifact_issues
            job.result["custom_ip_make_libs_patched"] = host_patched_make_libs
            job.result["custom_ip_make_libs_patched_count"] = len(host_patched_make_libs)
            job.result["custom_ip_bsp_patch_total_count"] = len(host_patched_make_libs) + len(xsa_patched_make_libs)
            job.result["workspace_make_libs_diagnostic"] = workspace_make_libs
            job.result["log_make_libs_targets"] = log_make_libs_targets
            job.result["vitis_elf_artifacts"] = elf_artifacts
            job.result["self_heal"] = self_heal
            job.result["vitis_doctor"] = vitis_doctor
        if build_failed:
            mapped_issues = final_issues or initial_issues or map_vitis_errors(f"{final_stdout}\n{final_stderr}")
            issues = mapped_issues + artifact_issues
            if job.result is not None:
                job.result["compile_issues"] = issues
                job.result["successful"] = False
            job.emit({
                "event": "vitis.compile_errors",
                "stage": "run",
                "progress": 98,
                "message": f"Vitis build log {len(issues)} issue ile eşleştirildi.",
                "issues": issues,
                "error_codes": _issue_error_codes(issues),
            })
            reason = f"exit={final_completed.returncode}" if final_completed.returncode != 0 else "XSCT log hata içeriyor"
            raise RuntimeError(
                "XSCT workspace üretimi hata ile bitti "
                f"({reason}). Log: {final_stderr_log_path}"
            )
        if artifact_issues:
            if job.result is not None:
                job.result["compile_issues"] = artifact_issues
                job.result["successful"] = False
            job.emit({
                "event": "vitis.compile_errors",
                "stage": "run",
                "progress": 98,
                "message": "Vitis build geçti ama application ELF doğrulanamadı.",
                "issues": artifact_issues,
                "error_codes": _issue_error_codes(artifact_issues),
            })
            raise RuntimeError(
                "Vitis build geçti ama application ELF bulunamadı. "
                f"Workspace: {workspace_path}"
            )

        if job.result is not None:
            job.result["compile_issues"] = []
            job.result["successful"] = True
        job.emit({
            "event": "vitis.done",
            "stage": "done",
            "progress": 100,
            "message": "Vitis workspace hazır.",
            "workspace_path": str(workspace_path),
            "platform_name": platform_name,
            "system_name": system_name,
            "app_name": app_name,
        })


vitis_manager = VitisWorkspaceJobManager()
