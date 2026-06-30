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
_XSCT_FATAL_RE = re.compile(
    r"(invalid command name|while executing|^ERROR:|traceback|exception)",
    re.IGNORECASE | re.MULTILINE,
)
_KNOWN_AMD_XILINX_VENDORS = {"xilinx.com", "amd.com"}
_CUSTOM_IP_DRIVER_POLICIES = {"auto_none", "keep"}


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


def discover_custom_pl_ips(xsa_path: Path) -> list[CustomPlIpCandidate]:
    candidates: dict[str, CustomPlIpCandidate] = {}
    for hwh_name, content in _hwh_documents_from_xsa(xsa_path):
        try:
            root = ET.fromstring(content)
        except ET.ParseError:
            continue
        for element in root.iter():
            if _xml_local_name(element.tag).upper() != "MODULE":
                continue
            modtype = _xml_attr(element, "MODTYPE").upper()
            if modtype and modtype != "PERIPHERAL":
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
            if vendor in _KNOWN_AMD_XILINX_VENDORS and library != "user":
                continue
            ip_name = _xml_attr(element, "IP_NAME") or (vlnv_parts[2] if len(vlnv_parts) >= 3 else "")
            reason = f"{hwh_name}: non-Xilinx/AMD peripheral VLNV"
            if vendor in _KNOWN_AMD_XILINX_VENDORS and library == "user":
                reason = f"{hwh_name}: user-packaged PL peripheral VLNV"
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


def vitis_selftest_source(spec: dict) -> str:
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

    for name, content in {
        "spec2code_selftest_main.h": vitis_selftest_header(),
        "spec2code_selftest_main.c": vitis_selftest_source(job.spec),
    }.items():
        target = source_root / name
        target.write_text(hio.normalize_crlf(content), encoding="utf-8", newline="")
        staged.append(name)

    return sorted(staged)


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


def _xsct_log_has_fatal_error(stdout: str, stderr: str) -> bool:
    log = f"{stdout}\n{stderr}"
    return bool(_XSCT_FATAL_RE.search(log))


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
) -> str:
    lwip_flag = "1" if enable_lwip else "0"
    lwip_api_mode = vitis_lwip_api_mode(os_name) if enable_lwip else ""
    custom_ip_driver_policy = normalize_custom_ip_driver_policy(custom_ip_driver_policy)
    custom_ip_instances = custom_ip_instances or []
    custom_ip_list = _tcl_list(custom_ip_instances)
    bsp_config_script = (
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
        "            if {[catch {bsp regenerate} spec2code_custom_ip_regen_err]} {\n"
        f"                {_tcl_put('WARNING: BSP regenerate failed after custom IP driver policy: $spec2code_custom_ip_regen_err')}"
        "            }\n"
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
        "            if {[catch {bsp regenerate} spec2code_lwip_regen_err]} {\n"
        f"                {_tcl_put('WARNING: BSP regenerate failed after lwIP selection: $spec2code_lwip_regen_err')}"
        "            }\n"
        "        } else {\n"
        f"            {_tcl_put('WARNING: lwIP BSP library could not be enabled automatically; enable it manually if build reports missing lwIP headers.')}"
        "        }\n"
        "    }\n"
        "}\n\n"
    )
    return (
        "# Spec2Code generated Vitis workspace script.\n"
        "# This script is intentionally plain XSCT so it works in air-gapped Windows hosts.\n"
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
        "    spec2codeConfigureBsp\n"
        "} spec2code_create_err]} {\n"
        f"    {_tcl_put('named platform/system flow failed: $spec2code_create_err')}"
        f"    {_tcl_put('retrying with legacy app create flow')}"
        "    if {[catch {app create -name $app_name -hw $xsa_path -proc $processor -os $os_name -lang C -template {Empty Application(C)}} app_err]} {\n"
        f"        {_tcl_put('Empty Application(C) template failed: $app_err')}"
        f"        {_tcl_put('retrying with Empty Application template')}"
        "        app create -name $app_name -hw $xsa_path -proc $processor -os $os_name -lang C -template {Empty Application}\n"
        "    }\n"
        "    spec2codeConfigureBsp\n"
        "}\n\n"
        f"{_tcl_put('importing generated sources')}"
        "importsources -name $app_name -path $source_path\n\n"
        f"{_tcl_put('building application')}"
        "app build -name $app_name\n"
        f"{_tcl_put('done')}"
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
        source_root = staging_root / "src"
        hw_root = staging_root / "hw"
        log_dir = staging_root / "logs"
        hw_root.mkdir(parents=True, exist_ok=True)
        log_dir.mkdir(parents=True, exist_ok=True)
        staged_xsa_path = hw_root / input_xsa_path.name
        shutil.copy2(input_xsa_path, staged_xsa_path)

        custom_ip_driver_policy = normalize_custom_ip_driver_policy(config.custom_ip_driver_policy)
        custom_pl_ips = discover_custom_pl_ips(staged_xsa_path) if custom_ip_driver_policy == "auto_none" else []
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

        job.emit({
            "event": "vitis.stage_sources",
            "stage": "stage_sources",
            "progress": 40,
            "message": "XSA kopyası ve generated C/H kaynakları Vitis staging klasörüne hazırlanıyor.",
        })
        staged_files = stage_vitis_sources(job.generate_job, source_root)
        requires_lwip = any(path.startswith("tests/spec2code_testbench_lwip") for path in staged_files)
        lwip_api_mode = vitis_lwip_api_mode(os_name) if requires_lwip else None

        script_path = staging_root / "spec2code_create_workspace.tcl"
        stdout_log = log_dir / "xsct_stdout.log"
        stderr_log = log_dir / "xsct_stderr.log"
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
            ),
            encoding="utf-8",
        )

        job.result = {
            **manifest,
            "script_path": str(script_path),
            "manifest_path": str(manifest_path),
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
        }

        job.emit({
            "event": "vitis.run",
            "stage": "run",
            "progress": 72,
            "message": "XSCT çalışıyor; platform/application oluşturulup build alınıyor.",
            "script_path": str(script_path),
        })
        completed = subprocess.run(
            _command_for(xsct.path, str(script_path)),
            cwd=workspace_path,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(60, int(config.timeout_s or 1800)),
        )
        stdout_log.write_text(completed.stdout, encoding="utf-8")
        stderr_log.write_text(completed.stderr, encoding="utf-8")
        log_has_fatal_error = _xsct_log_has_fatal_error(completed.stdout, completed.stderr)
        if job.result is not None:
            job.result["xsct_exit_code"] = completed.returncode
            job.result["xsct_stdout_tail"] = _log_tail(completed.stdout)
            job.result["xsct_stderr_tail"] = _log_tail(completed.stderr)
            job.result["successful"] = completed.returncode == 0 and not log_has_fatal_error
        if completed.returncode != 0 or log_has_fatal_error:
            issues = map_vitis_errors(f"{completed.stdout}\n{completed.stderr}")
            if job.result is not None:
                job.result["compile_issues"] = issues
                job.result["successful"] = False
            job.emit({
                "event": "vitis.compile_errors",
                "stage": "run",
                "progress": 92,
                "message": f"Vitis build log {len(issues)} issue ile eşleştirildi.",
                "issues": issues,
            })
            reason = f"exit={completed.returncode}" if completed.returncode != 0 else "XSCT log hata içeriyor"
            raise RuntimeError(
                "XSCT workspace üretimi hata ile bitti "
                f"({reason}). Log: {stderr_log}"
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
