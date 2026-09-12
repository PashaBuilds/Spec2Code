"""Vitis Unified (>= 2024.1) workspace akisi: `vitis -s <python>` + SDT BSP.

Klasik akis (`backend/vitis_workspace.py`, xsct Tcl: platform create / bsp config /
app create) 2024.1'den itibaren yerini Python API'li Unified IDE'ye birakir:

* ``vitis.create_client()`` -> ``client.set_workspace()`` -> ``create_platform_component``
  (XSA, os, cpu) -> ``platform.build()`` -> ``create_app_component`` (xpfm, domain,
  ``empty_application``) -> ``import_files`` -> ``app.build()``.
* BSP System Device Tree (Lopper) ile uretilir: ``xparameters.h``'ta ``DEVICE_ID`` yok,
  surucular ``-DSDT`` ile derlenir; uretilen kod ``project.bsp_flow = sdt`` olmali
  (``orchestrator/bsp_flow.py``).
* lwIP kutuphanesi ``lwip220``; MicroBlaze bellek parametreleri klasik akistaki
  degerlerle ayni (``lwip220_<param>``).
* Uygulama include yollari ``UserConfig.cmake`` (``USER_INCLUDE_DIRECTORIES``) ile verilir;
  Unified app CDT degil CMake ile derlenir.

Python API cagrilari Vitis 2025.2 kurulumundaki ``cli/vitis/*.py`` imzalari ve
``cli/examples/embedded/*.py`` ornekleriyle dogrulandi: ``create_platform_component(name,
hw_design, os, cpu, domain_name)``, ``platform.get_domain(name)``, ``domain.set_lib(lib_name)``,
``domain.set_config(option, param, value, lib_name)``, ``client.find_platform_in_repos``,
``create_app_component(name, platform, domain, template)``, ``app.import_files(from_loc, files,
dest_dir_in_cmp)``, ``app.set_app_config/append_app_config(USER_INCLUDE_DIRECTORIES)``,
``app.get_ld_script().set_stack_size/set_heap_size``, ``vitis.dispose()``. lwip220 (v1_0..v1_3)
lwip213'teki iki hatayi (xadapter.c cift `status`, xemacliteif.c IEEE 802.3 secicisi) hala
tasir; betik platform derlemesinden sonra libsrc'yi yamalayip yeniden derler.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

from orchestrator.bsp_flow import BSP_FLOW_CLASSIC, BSP_FLOW_SDT, bsp_flow, expected_bsp_flow_for_vitis, is_unified_vitis

if TYPE_CHECKING:  # pragma: no cover
    from backend.vitis_workspace import VitisWorkspaceJob, XsctInfo

#: Vitis Unified lwIP kutuphanesi (klasik lwip213'un yerine).
UNIFIED_LWIP_LIB = "lwip220"
#: MicroBlaze LMB icin lwIP bellek parametreleri (klasik akisla ayni degerler).
MICROBLAZE_LWIP_PARAMS: dict[str, int] = {
    "mem_size": 32768,
    "memp_n_pbuf": 8,
    "pbuf_pool_size": 16,
    "tcp_wnd": 4096,
    "tcp_snd_buf": 4096,
    "memp_n_tcp_pcb": 4,
    "memp_n_tcp_seg": 64,
}
_VITIS_CLI_NAMES = ("vitis.bat", "vitis.cmd", "vitis")


def locate_vitis_cli(vitis_path: str) -> Path:
    """Unified ``vitis`` komut satirini (``<Vitis>/bin/vitis[.bat]``) bulur."""
    root = Path(str(vitis_path or "").strip().strip('"')).expanduser()
    if root.is_file() and root.name.lower() in _VITIS_CLI_NAMES:
        return root
    searched: list[Path] = []
    roots = [root, root / "bin"]
    if root.is_dir():
        roots += sorted((child / "bin" for child in root.iterdir() if child.is_dir()), reverse=True)
    for base in roots:
        for name in _VITIS_CLI_NAMES:
            candidate = base / name
            searched.append(candidate)
            if candidate.is_file():
                return candidate
    listing = "\n".join(str(path) for path in searched[:12])
    raise FileNotFoundError(f"vitis executable not found under '{root}'. Searched:\n{listing}")


def bsp_flow_preflight_issue(spec: dict, vitis_version: str) -> dict | None:
    """Spec'in ``bsp_flow``u Vitis surumuyle uyusmuyorsa issue dondurur (kod derlenmez)."""
    expected = expected_bsp_flow_for_vitis(vitis_version)
    actual = bsp_flow(spec)
    if expected == actual:
        return None
    if expected == BSP_FLOW_SDT:
        message = (
            f"Vitis {vitis_version} Unified/SDT akisidir ama spec project.bsp_flow = '{actual}': uretilen kod "
            "XPAR_*_DEVICE_ID ile LookupConfig cagirir, SDT BSP'de bu makrolar yoktur. Proje Kurulumu'nda BSP "
            "akisini 'sdt' yapip kodu yeniden uretin (ya da Vitis <= 2023.2 kullanin)."
        )
    else:
        message = (
            f"Vitis {vitis_version} klasik (xsct) akisidir ama spec project.bsp_flow = '{actual}': uretilen kod "
            "XPAR_*_BASEADDR ile LookupConfig cagirir, klasik BSP DEVICE_ID bekler. BSP akisini 'classic' "
            "yapip kodu yeniden uretin (ya da Vitis >= 2024.1 kullanin)."
        )
    return {
        "file": "project.spec.json", "line": 0, "column": 0,
        "rule": "spec2code-vitis-bsp-flow", "severity": "error",
        "category": "bsp_flow_mismatch", "source": "Spec2Code",
        "message": message,
        "expected_bsp_flow": expected, "actual_bsp_flow": actual,
    }


def _py(value) -> str:
    """Python kaynak sabiti (yollar ham string olarak, ters bolu kacisi yok)."""
    if isinstance(value, Path):
        return repr(str(value.resolve()).replace("\\", "/"))
    return repr(value)


def render_unified_workspace_script(
    *,
    mode: str,
    workspace_path: Path,
    xsa_path: Path | None,
    source_root: Path,
    source_files: list[str],
    platform_name: str,
    domain_name: str,
    app_name: str,
    processor: str,
    os_name: str,
    enable_lwip: bool = False,
    lwip_api_mode: str = "RAW_API",
    lwip_params: dict[str, int] | None = None,
    source_include_dirs: list[str] | None = None,
    shell_app_name: str = "",
    shell_source_root: Path | None = None,
    shell_source_files: list[str] | None = None,
    shell_include_dirs: list[str] | None = None,
) -> str:
    """`vitis -s` ile kosan Python betigi (full: platform+app; update: yalniz kaynak+build)."""
    if mode not in ("full", "update"):
        raise ValueError(f"unknown unified workspace mode: {mode}")
    if mode == "full" and xsa_path is None:
        raise ValueError("full mode requires an XSA path")
    microblaze = processor.lower().startswith("microblaze")
    header = (
        "# Spec2Code generated Vitis Unified workspace script (Vitis >= 2024.1).\n"
        "# Kullanim: vitis -s <bu dosya>   (Unified Python API; klasik xsct Tcl akisi degildir)\n"
        "import os\n"
        "import re\n"
        "import shutil\n"
        "import sys\n"
        "\n"
        "import vitis\n"
        "\n"
        f"MODE = {_py(mode)}\n"
        f"WORKSPACE = {_py(workspace_path)}\n"
        f"XSA = {_py(xsa_path) if xsa_path is not None else 'None'}\n"
        f"SOURCE_ROOT = {_py(source_root)}\n"
        f"SOURCE_FILES = {_py(list(source_files))}\n"
        f"SOURCE_INCLUDE_DIRS = {_py(list(source_include_dirs or []))}\n"
        f"PLATFORM = {_py(platform_name)}\n"
        f"DOMAIN = {_py(domain_name)}\n"
        f"APP = {_py(app_name)}\n"
        f"CPU = {_py(processor)}\n"
        f"OS = {_py(os_name)}\n"
        f"MICROBLAZE = {_py(microblaze)}\n"
        f"ENABLE_LWIP = {_py(bool(enable_lwip))}\n"
        f"LWIP_LIB = {_py(UNIFIED_LWIP_LIB)}\n"
        f"LWIP_API_MODE = {_py(lwip_api_mode)}\n"
        f"LWIP_PARAMS = {_py(dict(lwip_params or {}))}\n"
        f"SHELL_APP = {_py(shell_app_name)}\n"
        f"SHELL_SOURCE_ROOT = {_py(shell_source_root) if shell_source_root is not None else 'None'}\n"
        f"SHELL_SOURCE_FILES = {_py(list(shell_source_files or []))}\n"
        f"SHELL_INCLUDE_DIRS = {_py(list(shell_include_dirs or []))}\n"
        "\n"
    )
    body = r'''
def log(message):
    print("[Spec2Code] " + str(message), flush=True)


def norm(path):
    return str(path).replace("\\", "/")


def find_files(root, name):
    hits = []
    for dirpath, _dirs, files in os.walk(root):
        if name in files:
            hits.append(os.path.join(dirpath, name))
    return hits


def emaclite_status_declared_twice(text):
    # lwip213: emaclite_link_status icinde `status` iki kez bildirilir (derleme hatasi); lwip220 v1_x'te
    # tek bildirim vardir ve KALDIRILMAMALIDIR (SAHA 2026-09-12: yanlis yama 'status undeclared' verdi).
    match = re.search(r"void emaclite_link_status\([^)]*\)\s*\{(.*?)\n\}", text, re.S)
    if not match:
        return False
    body = match.group(1)
    return len(re.findall(r"^\s*u32_t\s+[^;]*\bstatus\b[^;]*;", body, re.M)) >= 2


def patch_lwip_sources(root):
    # Xilinx lwIP portu (SAHA 2026-09-11/12):
    #  1) lwip213 xadapter.c emaclite_link_status: `status` ayni kapsamda iki kez bildirilir -> derleme hatasi
    #     (yalniz gercekten cift bildirim varsa dokunulur; lwip220'de tek bildirim var).
    #  2) xemacliteif.c ADVERTISE_*: IEEE 802.3 secici biti (0x0001) yok -> LAN8720A autoneg hic bitmez
    #     (lwip220 v1_3'te de var).
    patched = []
    for path in find_files(root, "xadapter.c"):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        fixed = text
        if emaclite_status_declared_twice(text):
            fixed = text.replace("u32_t phy_link_status, status, phy_autoneg_status;",
                                 "u32_t phy_link_status, phy_autoneg_status; /* Spec2Code: duplicate status fixed */")
        if fixed != text:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(fixed)
            patched.append(path)
    for path in find_files(root, "xemacliteif.c"):
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        fixed = text
        for macro in ("ADVERTISE_100_AND_10", "ADVERTISE_100", "ADVERTISE_10"):
            fixed = re.sub(r"(#define %s\s*\()(?!0x0001)" % macro,
                           r"\g<1>0x0001 /* Spec2Code: IEEE 802.3 selector */ | ", fixed, count=1)
        if fixed != text:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(fixed)
            patched.append(path)
    for path in patched:
        log("lwIP kaynagi yamalandi: " + norm(path))
    return patched


def set_include_dirs(app, component_dir, include_dirs):
    absolute = [norm(os.path.join(component_dir, "src", d)) for d in include_dirs]
    if not absolute:
        return
    # USER_INCLUDE_DIRECTORIES: UserConfig.cmake'e Vitis API'siyle yazilir (CDT yok, CMake var).
    app.set_app_config(key="USER_INCLUDE_DIRECTORIES", values=absolute[0])
    for extra in absolute[1:]:
        app.append_app_config(key="USER_INCLUDE_DIRECTORIES", values=extra)
    log("include yollari: " + ", ".join(absolute))


def set_stack_heap(app):
    # MicroBlaze: Vitis varsayilan 1 KB yigin / 2 KB heap yetmez -> 16 KB / 8 KB (klasik akisla ayni).
    try:
        ld = app.get_ld_script()
        if int(str(ld.get_stack_size()), 0) < 0x4000:
            ld.set_stack_size("0x4000")
        if int(str(ld.get_heap_size()), 0) < 0x2000:
            ld.set_heap_size("0x2000")
        log("lscript yigin/heap: %s / %s" % (ld.get_stack_size(), ld.get_heap_size()))
    except Exception as exc:
        log("lscript yigin/heap ayarlanamadi: " + str(exc))


def import_sources(app, source_root, rel_files):
    # Kok dosyalar (main.c/main.h) ve alt klasorler (drivers/ tests/ cit/ shell/) src/ altina; klasor yapisi korunur.
    top_level = sorted({rel.split("/", 1)[0] for rel in rel_files})
    app.import_files(from_loc=norm(source_root), files=top_level, dest_dir_in_cmp="src")
    log("import edildi: " + ", ".join(top_level))


def set_lib_param(domain, lib, param, value):
    # lwip220 parametre adlari: <lib>_<param> (klasik `bsp config <param>` karsiligi). Ad tutmazsa
    # tek basina <param> denenir; ikisi de tutmazsa list_params ciktisi loga dusulur.
    for name in (lib + "_" + param, param):
        try:
            domain.set_config(option="lib", param=name, value=str(value), lib_name=lib)
            log("%s.%s = %s" % (lib, name, value))
            return True
        except Exception as exc:
            last = exc
    log("UYARI: %s parametresi ayarlanamadi (%s): %s" % (param, lib, last))
    try:
        domain.list_params("lib", lib)
    except Exception:
        pass
    return False


def create_platform(client):
    platform = client.create_platform_component(name=PLATFORM, hw_design=XSA, os=OS, cpu=CPU, domain_name=DOMAIN)
    domain = platform.get_domain(name=DOMAIN)
    if ENABLE_LWIP:
        log("lwIP kutuphanesi ekleniyor: " + LWIP_LIB + " (" + LWIP_API_MODE + ")")
        domain.set_lib(lib_name=LWIP_LIB)
        set_lib_param(domain, LWIP_LIB, "api_mode", LWIP_API_MODE)
        for key, value in LWIP_PARAMS.items():
            set_lib_param(domain, LWIP_LIB, key, value)
    # xiltimer (SDT MicroBlaze lwIP platformunun 50 ms tick'i) standalone BSP'de zaten vardir
    # (-lxiltimer; set_lib INTERNAL hatasi verir), eklenmez.
    platform_dir = os.path.join(WORKSPACE, PLATFORM)
    log("platform build: " + PLATFORM)
    try:
        platform.build()
        build_ok = True
    except Exception as exc:
        build_ok = False
        log("platform build ilk deneme basarisiz: " + str(exc))
    if ENABLE_LWIP and patch_lwip_sources(platform_dir):
        log("lwIP yamalari uygulandi; platform yeniden derleniyor")
        platform.build()
    elif not build_ok:
        raise RuntimeError("platform build failed")
    return platform


def create_or_get_app(client, name):
    if MODE == "update":
        return client.get_component(name=name)
    xpfm = client.find_platform_in_repos(PLATFORM)
    log("platform xpfm: " + str(xpfm))
    return client.create_app_component(name=name, platform=xpfm, domain=DOMAIN, template="empty_application")


def build_app(client, name, source_root, rel_files, include_dirs):
    app = create_or_get_app(client, name)
    component_dir = os.path.join(WORKSPACE, name)
    import_sources(app, source_root, rel_files)
    set_include_dirs(app, component_dir, include_dirs)
    if MICROBLAZE and MODE == "full":
        set_stack_heap(app)
    log("application build: " + name)
    app.build()
    elf = os.path.join(component_dir, "build", name + ".elf")
    if os.path.isfile(elf):
        log("application ELF present: " + norm(elf))
    else:
        log("application ELF missing after build: " + norm(elf))
    return os.path.isfile(elf)


client = vitis.create_client()
client.set_workspace(path=WORKSPACE)
if MODE == "full":
    create_platform(client)
ok = build_app(client, APP, SOURCE_ROOT, SOURCE_FILES, SOURCE_INCLUDE_DIRS)
if SHELL_APP and SHELL_SOURCE_ROOT:
    try:
        build_app(client, SHELL_APP, SHELL_SOURCE_ROOT, SHELL_SOURCE_FILES, SHELL_INCLUDE_DIRS)
    except Exception as exc:  # shell ikincil cikti: ajan akisini dusurmez
        log("shell application build failed: " + str(exc))
vitis.dispose()
if not ok:
    log("ERROR: application ELF missing: " + APP)
    sys.exit(1)
log("done")
'''
    return header + body


def run_unified_job(manager, job: "VitisWorkspaceJob", xsct: "XsctInfo") -> None:
    """Unified akisi (full/update) - VitisWorkspaceManager._blocking bunu cagirir."""
    from backend import vitis_workspace as vw
    from backend.vitis_errors import map_vitis_errors

    config = job.config
    mode = str(getattr(config, "mode", "full") or "full")
    spec = job.generate_job.spec
    project = spec.get("project", {})
    processor = config.processor or vw.default_vitis_processor(str(project.get("platform", "")), str(project.get("target_core", "")))
    os_name = vw.vitis_os(config.runtime or str(project.get("runtime", "")))
    name_base = vw._safe_identifier(job.source_project, "spec2code")
    platform_name = vw._safe_identifier(config.platform_name or f"{name_base}_platform", f"spec2code_platform_{job.id}")
    app_name = vw._safe_identifier(config.app_name or f"{name_base}_app", f"spec2code_app_{job.id}")
    domain_name = vw._safe_identifier(f"{app_name}_domain", f"spec2code_domain_{job.id}")

    vitis_cli = locate_vitis_cli(config.vitis_path)
    job.emit({
        "event": "vitis.version", "stage": "version", "progress": 22,
        "message": f"Vitis Unified algılandı: {xsct.version} (SDT BSP, `vitis -s` Python akışı"
                   + (", kaynak güncelleme modu)" if mode == "update" else ")"),
        "xsct_path": str(xsct.path), "vitis_cli_path": str(vitis_cli),
        "vitis_version": xsct.version, "version_source": xsct.version_source, "vitis_flow": "unified",
    })
    flow_issue = bsp_flow_preflight_issue(spec, xsct.version)
    if flow_issue is not None:
        job.emit({
            "event": "vitis.compile_errors", "stage": "stage_sources", "progress": 30,
            "message": "Spec BSP akışı Vitis sürümüyle uyuşmuyor; vitis başlatılmadı.",
            "issues": [flow_issue], "error_codes": vw._issue_error_codes([flow_issue]),
        })
        raise RuntimeError(flow_issue["message"])

    workspace_path = vw._clean_user_path(config.workspace_path)
    app_dir = workspace_path / app_name
    if mode == "update":
        if not workspace_path.is_dir() or not app_dir.is_dir():
            raise FileNotFoundError(
                f"Kaynak güncellemesi mevcut bir workspace gerektirir: '{app_dir}' bulunamadı. "
                "Önce 'Sıfırdan kur' ile workspace oluşturun.")
    else:
        workspace_path.mkdir(parents=True, exist_ok=True)
    lock_issue = vw.workspace_lock_issue(workspace_path)
    if lock_issue is not None:
        job.emit({
            "event": "vitis.compile_errors", "stage": "stage_sources", "progress": 30,
            "message": "Workspace kilitli; vitis baslatilmadi.",
            "issues": [lock_issue], "error_codes": vw._issue_error_codes([lock_issue]),
        })
        raise RuntimeError(lock_issue["message"])

    temp_path = vw._clean_user_path(config.temp_path)
    temp_path.mkdir(parents=True, exist_ok=True)
    staging_root = temp_path / job.id
    suffix = 1
    while staging_root.exists():
        suffix += 1
        staging_root = temp_path / f"{job.id}_{suffix}"
    source_root = staging_root / "src"
    log_dir = staging_root / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    staged_xsa_path: Path | None = None
    if mode == "full":
        input_xsa_path = vw._clean_user_path(config.xsa_path)
        if not input_xsa_path.is_file() or input_xsa_path.suffix.lower() != ".xsa":
            raise FileNotFoundError(f"XSA file not found or invalid: {input_xsa_path}")
        hw_root = staging_root / "hw"
        hw_root.mkdir(parents=True, exist_ok=True)
        staged_xsa_path = hw_root / input_xsa_path.name
        shutil.copy2(input_xsa_path, staged_xsa_path)
        preflight_issues = vw.spec_xsa_preflight(spec, staged_xsa_path, os_name)
        if preflight_issues:
            job.emit({
                "event": "vitis.compile_errors", "stage": "stage_sources", "progress": 30,
                "message": f"Spec/XSA on kontrolu {len(preflight_issues)} sorun buldu; vitis baslatilmadi.",
                "issues": preflight_issues, "error_codes": vw._issue_error_codes(preflight_issues),
            })
            raise RuntimeError("Spec/XSA uyumsuz: " + " | ".join(i["message"] for i in preflight_issues))
        if vw.normalize_custom_ip_driver_policy(config.custom_ip_driver_policy) != "keep":
            job.emit({
                "event": "vitis.custom_ip_policy", "stage": "stage_sources", "progress": 34,
                "message": "Unified/SDT akisinda custom PL IP surucu politikasi uygulanmaz: BSP suruculeri SDT "
                           "uyumluluk dizgisiyle eslesir, eslesmeyen IP icin surucu uretilmez (make.libs yamasi yok).",
            })

    job.emit({
        "event": "vitis.stage_sources", "stage": "stage_sources", "progress": 40,
        "message": "Generated C/H kaynakları Vitis staging klasörüne hazırlanıyor.",
    })
    staged_files = vw.stage_vitis_sources(job.generate_job, source_root)
    shell_app_name = vw.shell_app_name_for(app_name)
    shell_source_root = staging_root / "src_shell"
    shell_staged_files = vw.stage_shell_sources(job.generate_job, shell_source_root)
    if not shell_staged_files:
        shell_app_name = ""
    if mode == "update":
        removed = vw.clear_staged_app_sources(workspace_path, app_name)
        if shell_app_name and (workspace_path / shell_app_name / "src").is_dir():
            removed += vw.clear_staged_app_sources(workspace_path, shell_app_name)
        if removed:
            job.emit({
                "event": "vitis.stale_sources_removed", "stage": "stage_sources", "progress": 45,
                "message": f"{len(removed)} eski staged kaynak workspace'ten silindi.", "removed": removed,
            })
    requires_lwip = any(path.startswith("tests/spec2code_testbench_lwip") for path in staged_files)
    lwip_api_mode = vw.vitis_lwip_api_mode(os_name) if requires_lwip else None

    script_path = staging_root / "spec2code_unified_workspace.py"
    stdout_log = log_dir / "vitis_stdout.log"
    stderr_log = log_dir / "vitis_stderr.log"
    manifest_path = staging_root / "spec2code_vitis_manifest.json"
    manifest = {
        "job_id": job.id, "source_job_id": job.source_job_id, "mode": mode, "vitis_flow": "unified",
        "vitis_version": xsct.version, "vitis_cli_path": str(vitis_cli),
        "workspace_path": str(workspace_path), "xsa_path": str(staged_xsa_path) if staged_xsa_path else "",
        "platform_name": platform_name, "domain_name": domain_name, "app_name": app_name,
        "shell_app_name": shell_app_name, "processor": processor, "os": os_name,
        "requires_lwip": requires_lwip, "lwip_api_mode": lwip_api_mode, "lwip_lib": UNIFIED_LWIP_LIB,
        "staged_files": staged_files, "shell_staged_files": shell_staged_files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    job.emit({
        "event": "vitis.script", "stage": "script", "progress": 55,
        "message": "Vitis Unified Python betiği yazılıyor.", "staged_files": len(staged_files),
    })
    script_path.write_text(
        render_unified_workspace_script(
            mode=mode, workspace_path=workspace_path, xsa_path=staged_xsa_path, source_root=source_root,
            source_files=staged_files, platform_name=platform_name, domain_name=domain_name, app_name=app_name,
            processor=processor, os_name=os_name, enable_lwip=requires_lwip,
            lwip_api_mode=lwip_api_mode or "RAW_API",
            lwip_params=MICROBLAZE_LWIP_PARAMS if (requires_lwip and processor.lower().startswith("microblaze")) else None,
            source_include_dirs=vw.staged_header_dirs(staged_files),
            shell_app_name=shell_app_name, shell_source_root=shell_source_root if shell_app_name else None,
            shell_source_files=shell_staged_files, shell_include_dirs=vw.staged_header_dirs(shell_staged_files),
        ),
        encoding="utf-8",
    )
    job.result = {
        **manifest, "script_path": str(script_path), "manifest_path": str(manifest_path),
        "stdout_log": str(stdout_log), "stderr_log": str(stderr_log),
    }
    job.emit({
        "event": "vitis.run", "stage": "run", "progress": 70,
        "message": "vitis -s çalışıyor: " + ("kaynaklar import edilip application build alınıyor."
                                            if mode == "update" else "platform + BSP + application üretiliyor."),
        "script_path": str(script_path),
    })

    def _emit_watchdog(events: list[str]) -> None:
        job.emit({"event": "vitis.watchdog", "stage": "run", "progress": 75, "message": " | ".join(events)})

    build_started_at = time.time()
    completed = vw._run_xsct_streaming(
        vw._command_for(vitis_cli, "-s", str(script_path)),
        cwd=workspace_path, timeout_s=int(config.timeout_s or 1800),
        stdout_path=stdout_log, stderr_path=stderr_log, emit=_emit_watchdog,
    )
    stdout_log.write_text(completed.stdout, encoding="utf-8")
    stderr_log.write_text(completed.stderr, encoding="utf-8")
    log_text = f"{completed.stdout}\n{completed.stderr}"
    build_failed = (
        completed.returncode != 0
        or bool(getattr(completed, "timed_out", False))
        or bool(getattr(completed, "stalled", False))
        or bool(vw._VITIS_BUILD_FATAL_RE.search(log_text))
    )
    issues = map_vitis_errors(log_text) if build_failed else []
    if completed.timed_out or completed.stalled:
        issues.insert(0, vw._xsct_hang_issue(completed, script_path))
    elf_artifacts = vw.inspect_vitis_elf_artifacts([workspace_path / app_name, staging_root], app_name)
    artifact_issues: list[dict] = []
    if int(elf_artifacts.get("application", 0)) == 0:
        artifact_issues.append({
            "file": str(workspace_path), "line": 0, "column": 0,
            "rule": "spec2code-vitis-artifact", "severity": "error", "category": "missing_elf", "source": "Spec2Code",
            "message": ("Vitis build hata verdi ve application ELF bulunamadı. " if build_failed
                        else "Vitis build hata vermedi ama application ELF bulunamadı. ")
                       + f"Beklenen application adı: {app_name} (Unified: <workspace>/{app_name}/build/{app_name}.elf)",
        })
    elif not build_failed:
        stale = vw.stale_application_elf(elf_artifacts, build_started_at)
        if stale is not None:
            artifact_issues.append(stale)
    vitis_doctor = vw.build_vitis_doctor(
        custom_ip_driver_policy="keep", custom_pl_ips=[], xsa_make_libs={}, elf_artifacts=elf_artifacts,
        requires_lwip=requires_lwip, lwip_api_mode=lwip_api_mode, issues=issues + artifact_issues,
    )
    job.result.update({
        "xsct_initial_exit_code": completed.returncode, "xsct_exit_code": completed.returncode,
        "xsct_stdout_tail": vw._log_tail(completed.stdout), "xsct_stderr_tail": vw._log_tail(completed.stderr),
        "successful": not build_failed and not artifact_issues, "vitis_elf_artifacts": elf_artifacts,
        "vitis_doctor": vitis_doctor, "xsct_recovered_log_issues": [],
    })
    shell_issues = manager._shell_app_issues(job, workspace_path, shell_app_name)
    if build_failed or artifact_issues:
        all_issues = (issues or map_vitis_errors(log_text)) + artifact_issues + shell_issues
        job.result["compile_issues"] = all_issues
        job.result["successful"] = False
        job.emit({
            "event": "vitis.compile_errors", "stage": "run", "progress": 98,
            "message": f"Vitis build log {len(all_issues)} issue ile eşleştirildi.",
            "issues": all_issues, "error_codes": vw._issue_error_codes(all_issues),
        })
        reason = f"exit={completed.returncode}" if completed.returncode != 0 else "application ELF yok"
        raise RuntimeError(f"Vitis Unified workspace üretimi hata ile bitti ({reason}). Log: {stderr_log}")
    job.result["compile_issues"] = shell_issues
    job.result["successful"] = True
    job.emit({
        "event": "vitis.done", "stage": "done", "progress": 100,
        "message": ("Kaynaklar güncellendi, application build hazır (Vitis Unified)." if mode == "update"
                    else f"Vitis Unified workspace hazır: {workspace_path} (ELF: {app_name}/build/{app_name}.elf)"),
        "workspace_path": str(workspace_path), "platform_name": platform_name, "system_name": "",
        "app_name": app_name,
    })
