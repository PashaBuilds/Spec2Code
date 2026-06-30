import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.jobs import Job, _OUTPUTS
from backend.vitis_workspace import (
    VitisWorkspaceConfig,
    VitisWorkspaceJob,
    VitisWorkspaceJobManager,
    default_vitis_processor,
    detect_xsct,
    discover_custom_pl_ips,
    locate_xsct,
    normalize_custom_ip_driver_policy,
    patch_custom_ip_make_libs,
    patch_xsa_custom_ip_make_libs,
    render_xsct_recovery_script,
    render_xsct_script,
    vitis_lwip_api_mode,
    vitis_os,
)
from orchestrator import codegen


ROOT = Path(__file__).resolve().parent.parent


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


def write_fake_xsct(path: Path, version: str = "2024.2") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-version\" ]; then\n"
        f"  echo \"xsct version {version}\"\n"
        "  exit 0\n"
        "fi\n"
        "echo \"fake xsct ran $@\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def write_failing_xsct(path: Path, version: str = "2024.2") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-version\" ]; then\n"
        f"  echo \"xsct version {version}\"\n"
        "  exit 0\n"
        "fi\n"
        "echo 'invalid command name \"Spec2Code\"' >&2\n"
        "echo '    while executing' >&2\n"
        "echo '\"Spec2Code\"' >&2\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def write_self_healing_xsct(path: Path, version: str = "2024.2") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"-version\" ]; then\n"
        f"  echo \"xsct version {version}\"\n"
        "  exit 0\n"
        "fi\n"
        "count_file=\"$PWD/spec2code_xsct_count\"\n"
        "count=0\n"
        "if [ -f \"$count_file\" ]; then count=$(cat \"$count_file\"); fi\n"
        "next=$((count + 1))\n"
        "echo \"$next\" > \"$count_file\"\n"
        "if [ \"$count\" = \"0\" ]; then\n"
        "  src=\"$PWD/platform/export/platform/sw/platform/unit_platform/unit_application_domain/bsp/psu_cortexa53_0/libsrc/mem_pcie_intr_v1_0/src\"\n"
        "  mkdir -p \"$src\"\n"
        "  printf 'LIBSOURCES = *.c\\nlibs:\\n\\t$(CC) *.c\\n' > \"$src/make.libs\"\n"
        "  echo 'cc1.exe: fatal error: *.c: Invalid argument' >&2\n"
        "  echo 'make[1]: *** [Makefile:46: psu_cortexa53_0/libsrc/mem_pcie_intr_v1_0/src/make.libs] Error 2' >&2\n"
        "  exit 2\n"
        "fi\n"
        "echo 'self-heal recovery build ok'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


class VitisWorkspaceTests(unittest.TestCase):
    def test_locates_xsct_under_versioned_vitis_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            older = root / "Vitis" / "2023.2" / "bin" / "xsct"
            newer = root / "Vitis" / "2024.2" / "bin" / "xsct"
            write_fake_xsct(older, "2023.2")
            write_fake_xsct(newer, "2024.2")

            self.assertEqual(locate_xsct(str(root)), newer)
            info = detect_xsct(str(root))
            self.assertEqual(info.version, "2024.2")
            self.assertEqual(info.version_source, "xsct -version")

    def test_default_processor_and_runtime_mapping(self) -> None:
        self.assertEqual(default_vitis_processor("zynq_ultrascale", "a53_0"), "psu_cortexa53_0")
        self.assertEqual(default_vitis_processor("zynq_ultrascale", "r5_1"), "psu_cortexr5_1")
        self.assertEqual(default_vitis_processor("versal", "a72_0"), "psv_cortexa72_0")
        self.assertEqual(default_vitis_processor("zynq_7000", "ps7_cortexa9_0"), "ps7_cortexa9_0")
        self.assertEqual(vitis_os("freertos"), "freertos10_xilinx")
        self.assertEqual(vitis_os("bare_metal"), "standalone")
        self.assertEqual(vitis_lwip_api_mode("freertos10_xilinx"), "SOCKET_API")
        self.assertEqual(vitis_lwip_api_mode("standalone"), "RAW_API")
        self.assertEqual(normalize_custom_ip_driver_policy("keep"), "keep")
        self.assertEqual(normalize_custom_ip_driver_policy("unexpected"), "auto_none")

    def test_xsct_script_contains_workspace_creation_steps(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="standalone",
        )

        self.assertIn("setws $workspace_path", script)
        self.assertIn('puts "\\[Spec2Code\\] workspace: $workspace_path"', script)
        self.assertNotIn('puts "[Spec2Code]', script)
        self.assertIn("set platform_name {my_platform}", script)
        self.assertIn("set system_name {my_system}", script)
        self.assertIn("platform create -name $platform_name -hw $xsa_path", script)
        self.assertIn("domain create -name $domain_name -proc $processor -os $os_name", script)
        self.assertIn("app create -name $app_name -platform $platform_name -domain $domain_name -sysproj $system_name", script)
        self.assertIn("retrying with legacy app create flow", script)
        self.assertIn("importsources -name $app_name -path $source_path", script)
        self.assertIn("app build -name $app_name", script)

    def test_xsct_script_enables_lwip_library_when_requested(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="standalone",
            enable_lwip=True,
        )

        self.assertIn("set spec2code_enable_lwip 1", script)
        self.assertIn("set spec2code_lwip_api_mode {RAW_API}", script)
        self.assertIn("foreach spec2code_lwip_lib {lwip220 lwip213 lwip211 lwip202}", script)
        self.assertIn("bsp setlib -name $spec2code_lwip_lib", script)
        self.assertIn("bsp config $spec2code_lwip_api_name $spec2code_lwip_api_mode", script)
        self.assertIn("bsp regenerate", script)

    def test_xsct_script_selects_socket_api_for_freertos_lwip(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="freertos10_xilinx",
            enable_lwip=True,
        )

        self.assertIn("set spec2code_enable_lwip 1", script)
        self.assertIn("set spec2code_lwip_api_mode {SOCKET_API}", script)
        self.assertIn("foreach spec2code_lwip_api_name {api_mode API_MODE}", script)
        self.assertIn("lwIP API mode selected: $spec2code_lwip_api_name=$spec2code_lwip_api_mode", script)

    def test_xsa_custom_pl_ip_discovery_uses_non_xilinx_vlnv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xsa = Path(tmp) / "board.xsa"
            hwh = """<?xml version="1.0"?>
<SYSTEM>
  <MODULE INSTANCE="axi_gpio_0" MODTYPE="PERIPHERAL" VLNV="xilinx.com:ip:axi_gpio:2.0" IP_NAME="axi_gpio"/>
  <MODULE INSTANCE="mem_pcie_intr_0" MODTYPE="PERIPHERAL" VLNV="xilinx.com:ip:mem_pcie_intr:1.0" IP_NAME="mem_pcie_intr"/>
  <MODULE INSTANCE="clk_wiz_0" MODTYPE="PERIPHERAL" VLNV="xilinx.com:ip:clk_wiz:6.0" IP_NAME="clk_wiz"/>
  <MODULE INSTANCE="mem_pcie_intr_0" MODTYPE="PERIPHERAL" VLNV="xilinx.com:user:mem_pcie_intr:1.0" IP_NAME="mem_pcie_intr"/>
  <MODULE INSTANCE="company_filter_0" MODTYPE="PERIPHERAL" VLNV="company.local:user:company_filter:1.0" IP_NAME="company_filter"/>
  <MODULE INSTANCE="custom_dma_0" MODTYPE="PERIPHERAL" VLNV="acme.com:user:custom_dma:1.0"/>
  <MODULE INSTANCE="psu_cortexa53_0" MODTYPE="PROCESSOR" VLNV="xilinx.com:ip:psu_cortexa53:1.0"/>
</SYSTEM>
"""
            with zipfile.ZipFile(xsa, "w") as archive:
                archive.writestr("hw/system.hwh", hwh)

            candidates = discover_custom_pl_ips(xsa)

        self.assertEqual([item.instance for item in candidates], ["company_filter_0", "custom_dma_0", "mem_pcie_intr_0"])
        self.assertEqual(candidates[0].ip_name, "company_filter")
        self.assertEqual(candidates[1].ip_name, "custom_dma")
        self.assertEqual(candidates[2].ip_name, "mem_pcie_intr")
        self.assertNotIn("axi_gpio_0", [item.instance for item in candidates])
        self.assertNotIn("clk_wiz_0", [item.instance for item in candidates])
        self.assertIn("custom-like", candidates[2].reason)

    def test_xsct_script_sets_custom_pl_ip_driver_none_when_auto_policy_is_used(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="standalone",
            custom_ip_driver_policy="auto_none",
            custom_ip_instances=["company_filter_0"],
        )

        self.assertIn("set spec2code_custom_ip_driver_policy {auto_none}", script)
        self.assertIn("set spec2code_custom_ip_instances [list {company_filter_0}]", script)
        self.assertIn("bsp setdriver -ip $spec2code_custom_ip -driver $spec2code_none_driver", script)
        self.assertIn("foreach spec2code_none_driver {none None NONE}", script)
        self.assertIn("proc spec2codeDisableCustomIpBspLibsrc", script)
        self.assertIn("spec2codeWriteNoopMakeLibs $make_libs", script)
        self.assertIn(".PHONY: all libs include install clean", script)
        self.assertIn("${make_libs}.spec2code_backup", script)
        self.assertIn("string match \"${alias}_v*\" $libsrc_name", script)
        self.assertIn("proc spec2codeMakeLibsLooksSourceLess", script)
        self.assertIn("string first \"*.c\" $content", script)
        self.assertIn("[spec2codeIsCustomIpMakeLibs $make_libs] || [spec2codeMakeLibsLooksSourceLess $make_libs]", script)
        self.assertNotIn("[llength $spec2code_custom_ip_instances] == 0", script)

    def test_xsct_script_applies_custom_ip_policy_before_lwip_regenerate(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="freertos10_xilinx",
            enable_lwip=True,
            custom_ip_driver_policy="auto_none",
            custom_ip_instances=["mem_pcie_intr_0"],
        )

        self.assertLess(
            script.index("custom PL IP candidates detected"),
            script.index("lwIP target test bench detected"),
        )
        self.assertLess(
            script.index("bsp setdriver -ip $spec2code_custom_ip -driver $spec2code_none_driver"),
            script.index("bsp setlib -name $spec2code_lwip_lib"),
        )
        self.assertLess(
            script.index("spec2codeDisableCustomIpBspLibsrc"),
            script.index("app build -name $app_name"),
        )
        self.assertLess(
            script.index("spec2codeDisableCustomIpBspLibsrc\n            if {[catch {bsp regenerate} spec2code_custom_ip_regen_err]}"),
            script.index("bsp setlib -name $spec2code_lwip_lib"),
        )
        self.assertLess(
            script.index("spec2codeDisableCustomIpBspLibsrc\n            if {[catch {bsp regenerate} spec2code_lwip_regen_err]}"),
            script.index("importsources -name $app_name -path $source_path"),
        )

    def test_xsct_script_retries_build_after_custom_ip_bsp_bypass(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="freertos10_xilinx",
            enable_lwip=True,
            custom_ip_driver_policy="auto_none",
            custom_ip_instances=["mem_pcie_intr_0"],
        )

        self.assertIn("if {[catch {app build -name $app_name} spec2code_build_err]}", script)
        self.assertIn("retrying once", script)
        self.assertGreater(script.count("spec2codeDisableCustomIpBspLibsrc"), 2)

    def test_xsct_recovery_script_reuses_existing_workspace(self) -> None:
        script = render_xsct_recovery_script(
            workspace_path=Path("/tmp/ws"),
            platform_name="unit_platform",
            domain_name="unit_domain",
            app_name="unit_app",
            custom_ip_driver_policy="auto_none",
            custom_ip_instances=["mem_pcie_intr_0"],
        )

        self.assertIn("Spec2Code generated Vitis self-heal script", script)
        self.assertIn("setws $workspace_path", script)
        self.assertIn("catch {platform active $platform_name}", script)
        self.assertIn("catch {domain active $domain_name}", script)
        self.assertIn("bsp setdriver -ip $spec2code_custom_ip -driver $spec2code_none_driver", script)
        self.assertIn("app build -name $app_name", script)
        self.assertNotIn("platform create", script)

    def test_host_make_libs_patcher_covers_application_pmu_and_fsbl_bsp_domains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            domain_roots = [
                workspace / "platform" / "export" / "platform" / "sw" / "platform" / "spec2code_test_sw_domain" / "bsp" / "psu_cortexa53_0",
                workspace / "platform" / "export" / "platform" / "sw" / "platform" / "zynqmp_fsbl" / "bsp" / "psu_cortexa53_0",
                workspace / "platform" / "export" / "platform" / "sw" / "platform" / "zynqmp_pmufw" / "bsp" / "psu_pmu_0",
            ]
            for root in domain_roots:
                src = root / "libsrc" / "mem_pcie_intr_v1_0" / "src"
                src.mkdir(parents=True)
                (src / "make.libs").write_text("LIBSOURCES = *.c\nlibs:\n\t$(CC) *.c\n", encoding="utf-8")

            patched = patch_custom_ip_make_libs(workspace, ["mem_pcie_intr_0"], "auto_none")

            self.assertEqual(len(patched), 3)
            for root in domain_roots:
                make_libs = root / "libsrc" / "mem_pcie_intr_v1_0" / "src" / "make.libs"
                self.assertIn("Spec2Code: source-less custom PL IP BSP driver disabled", make_libs.read_text(encoding="utf-8"))
                self.assertTrue((make_libs.parent / "make.libs.spec2code_backup").is_file())

    def test_host_make_libs_patcher_uses_sourceless_wildcard_heuristic_without_hwh_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            src = workspace / "platform" / "export" / "platform" / "sw" / "platform" / "zynqmp_pmufw" / "bsp" / "psu_pmu_0" / "libsrc" / "company_irq_v1_0" / "src"
            src.mkdir(parents=True)
            (src / "make.libs").write_text("LIBSOURCES = *.c\nlibs:\n\t$(CC) *.c\n", encoding="utf-8")

            patched = patch_custom_ip_make_libs(workspace, [], "auto_none")

            self.assertEqual(len(patched), 1)
            self.assertIn("Spec2Code: source-less custom PL IP BSP driver disabled", (src / "make.libs").read_text(encoding="utf-8"))

    def test_host_make_libs_patcher_keeps_real_driver_sources_and_known_xilinx_libs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            real_src = workspace / "platform" / "export" / "platform" / "sw" / "platform" / "domain" / "bsp" / "psu_cortexa53_0" / "libsrc" / "company_irq_v1_0" / "src"
            real_src.mkdir(parents=True)
            (real_src / "company_irq.c").write_text("int companyIrqInit(void) { return 0; }\n", encoding="utf-8")
            (real_src / "make.libs").write_text("LIBSOURCES = *.c\n", encoding="utf-8")
            xil_src = workspace / "platform" / "export" / "platform" / "sw" / "platform" / "domain" / "bsp" / "psu_cortexa53_0" / "libsrc" / "xilflash_v1_0" / "src"
            xil_src.mkdir(parents=True)
            (xil_src / "make.libs").write_text("LIBSOURCES = *.c\n", encoding="utf-8")

            patched = patch_custom_ip_make_libs(workspace, [], "auto_none")

            self.assertEqual(patched, [])
            self.assertNotIn("Spec2Code", (real_src / "make.libs").read_text(encoding="utf-8"))
            self.assertNotIn("Spec2Code", (xil_src / "make.libs").read_text(encoding="utf-8"))

    def test_xsa_make_libs_patcher_rewrites_sourceless_custom_driver_before_vitis_sees_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xsa = Path(tmp) / "board.xsa"
            with zipfile.ZipFile(xsa, "w") as archive:
                archive.writestr("hw/system.hwh", "<SYSTEM />")
                archive.writestr("ip_repo/drivers/mem_pcie_intr_v1_0/src/make.libs", "LIBSOURCES = *.c\nlibs:\n\t$(CC) *.c\n")
                archive.writestr("ip_repo/drivers/real_driver_v1_0/src/make.libs", "LIBSOURCES = *.c\n")
                archive.writestr("ip_repo/drivers/real_driver_v1_0/src/real_driver.c", "int realDriverInit(void) { return 0; }\n")

            patched = patch_xsa_custom_ip_make_libs(xsa, ["mem_pcie_intr_0"], "auto_none")

            self.assertEqual(patched, ["ip_repo/drivers/mem_pcie_intr_v1_0/src/make.libs"])
            with zipfile.ZipFile(xsa, "r") as archive:
                patched_text = archive.read("ip_repo/drivers/mem_pcie_intr_v1_0/src/make.libs").decode("utf-8")
                real_text = archive.read("ip_repo/drivers/real_driver_v1_0/src/make.libs").decode("utf-8")
            self.assertIn("Spec2Code: source-less custom PL IP BSP driver disabled in staged XSA", patched_text)
            self.assertNotIn("Spec2Code", real_text)

    def test_xsa_make_libs_patcher_uses_sourceless_heuristic_without_custom_ip_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xsa = Path(tmp) / "board.xsa"
            with zipfile.ZipFile(xsa, "w") as archive:
                archive.writestr("ip_repo/drivers/company_irq_v1_0/src/make.libs", "LIBSOURCES = *.c\nlibs:\n\t$(CC) *.c\n")

            patched = patch_xsa_custom_ip_make_libs(xsa, [], "auto_none")

            self.assertEqual(patched, ["ip_repo/drivers/company_irq_v1_0/src/make.libs"])
            with zipfile.ZipFile(xsa, "r") as archive:
                patched_text = archive.read("ip_repo/drivers/company_irq_v1_0/src/make.libs").decode("utf-8")
            self.assertIn("Spec2Code: source-less custom PL IP BSP driver disabled in staged XSA", patched_text)

    def test_xsct_script_can_keep_custom_pl_ip_bsp_defaults(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            platform_name="my_platform",
            system_name="my_system",
            domain_name="my_app_domain",
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="standalone",
            custom_ip_driver_policy="keep",
            custom_ip_instances=["company_filter_0"],
        )

        self.assertIn("set spec2code_custom_ip_driver_policy {keep}", script)
        self.assertIn("custom PL IP driver policy keeps BSP defaults", script)

    def test_workspace_job_stages_sources_and_runs_xsct(self) -> None:
        project_name = "unit_vitis_workspace"
        spec = load_sample_spec(project_name)
        out_dir = _OUTPUTS / project_name
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            codegen.generate(spec, out_dir)
            files = sorted(path.relative_to(ROOT).as_posix() for path in out_dir.rglob("*") if path.is_file())
            generate_job = Job(
                id="job_unit_vitis",
                spec=spec,
                status="done",
                result={"out_dir": f"outputs/{project_name}", "files": files, "qc": {"passed": True}},
            )

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                fake_xsct = tmp_path / "Vitis" / "2024.2" / "bin" / "xsct"
                write_fake_xsct(fake_xsct)
                xsa = tmp_path / "board.xsa"
                xsa.write_bytes(b"fake xsa")
                workspace = tmp_path / "workspace"
                temp_root = tmp_path / "temp"

                config = VitisWorkspaceConfig(
                    vitis_path=str(tmp_path),
                    xsa_path=str(xsa),
                    workspace_path=str(workspace),
                    temp_path=str(temp_root),
                    processor="psu_cortexa53_0",
                    runtime="standalone",
                    platform_name="unit_platform",
                    system_name="unit_system",
                    app_name="unit_application",
                    timeout_s=10,
                )
                manager = VitisWorkspaceJobManager()
                job = VitisWorkspaceJob(
                    id="vitis_unit",
                    source_job_id=generate_job.id,
                    source_project=project_name,
                    config=config,
                    generate_job=generate_job,
                )

                manager._blocking(job)

                self.assertIsNotNone(job.result)
                result = job.result or {}
                self.assertEqual(result["vitis_version"], "2024.2")
                self.assertTrue((temp_root / "vitis_unit" / "src" / "drivers").is_dir())
                self.assertEqual(result["source_xsa_path"], str(xsa))
                self.assertEqual(result["xsa_path"], str(temp_root / "vitis_unit" / "hw" / "board.xsa"))
                self.assertEqual(result["temp_path"], str(temp_root))
                self.assertEqual(result["staging_path"], str(temp_root / "vitis_unit"))
                self.assertTrue(Path(result["xsa_path"]).is_file())
                self.assertEqual(result["platform_name"], "unit_platform")
                self.assertEqual(result["system_name"], "unit_system")
                self.assertEqual(result["app_name"], "unit_application")
                self.assertTrue(Path(result["script_path"]).is_file())
                self.assertTrue(Path(result["stdout_log"]).read_text(encoding="utf-8").startswith("fake xsct ran"))
                self.assertTrue(result["successful"])
                self.assertEqual(result["xsct_exit_code"], 0)
                self.assertIn("spec2code_selftest_main.h", result["staged_files"])
                self.assertIn("spec2code_selftest_main.c", result["staged_files"])
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_workspace_job_self_heals_custom_ip_make_libs_failure(self) -> None:
        project_name = "unit_vitis_workspace_self_heal"
        spec = load_sample_spec(project_name)
        out_dir = _OUTPUTS / project_name
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            codegen.generate(spec, out_dir)
            files = sorted(path.relative_to(ROOT).as_posix() for path in out_dir.rglob("*") if path.is_file())
            generate_job = Job(
                id="job_unit_vitis_self_heal",
                spec=spec,
                status="done",
                result={"out_dir": f"outputs/{project_name}", "files": files, "qc": {"passed": True}},
            )

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                fake_xsct = tmp_path / "Vitis" / "2024.2" / "bin" / "xsct"
                write_self_healing_xsct(fake_xsct)
                xsa = tmp_path / "board.xsa"
                hwh = """<?xml version="1.0"?>
<SYSTEM>
  <MODULE INSTANCE="mem_pcie_intr_0" MODTYPE="PERIPHERAL" VLNV="xilinx.com:ip:mem_pcie_intr:1.0" IP_NAME="mem_pcie_intr"/>
</SYSTEM>
"""
                with zipfile.ZipFile(xsa, "w") as archive:
                    archive.writestr("hw/system.hwh", hwh)
                workspace = tmp_path / "workspace"
                temp_root = tmp_path / "temp"

                config = VitisWorkspaceConfig(
                    vitis_path=str(tmp_path),
                    xsa_path=str(xsa),
                    workspace_path=str(workspace),
                    temp_path=str(temp_root),
                    processor="psu_cortexa53_0",
                    runtime="standalone",
                    platform_name="unit_platform",
                    system_name="unit_system",
                    app_name="unit_application",
                    timeout_s=10,
                )
                manager = VitisWorkspaceJobManager()
                job = VitisWorkspaceJob(
                    id="vitis_self_heal",
                    source_job_id=generate_job.id,
                    source_project=project_name,
                    config=config,
                    generate_job=generate_job,
                )

                manager._blocking(job)

                self.assertIsNotNone(job.result)
                result = job.result or {}
                self.assertTrue(result["successful"])
                self.assertEqual(result["xsct_initial_exit_code"], 2)
                self.assertEqual(result["xsct_exit_code"], 0)
                self.assertTrue(result["self_heal"]["attempted"])
                self.assertTrue(result["self_heal"]["successful"])
                self.assertIn("S2C-VITIS-CUSTOM-IP-MAKELIBS-001", result["vitis_doctor"]["error_codes"])
                self.assertGreater(result["custom_ip_make_libs_patched_count"], 0)
                make_libs = workspace / "platform" / "export" / "platform" / "sw" / "platform" / "unit_platform" / "unit_application_domain" / "bsp" / "psu_cortexa53_0" / "libsrc" / "mem_pcie_intr_v1_0" / "src" / "make.libs"
                self.assertIn("Spec2Code: source-less custom PL IP BSP driver disabled", make_libs.read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_workspace_job_treats_xsct_stderr_tcl_error_as_failure(self) -> None:
        project_name = "unit_vitis_workspace_tcl_error"
        spec = load_sample_spec(project_name)
        out_dir = _OUTPUTS / project_name
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            codegen.generate(spec, out_dir)
            files = sorted(path.relative_to(ROOT).as_posix() for path in out_dir.rglob("*") if path.is_file())
            generate_job = Job(
                id="job_unit_vitis_tcl_error",
                spec=spec,
                status="done",
                result={"out_dir": f"outputs/{project_name}", "files": files, "qc": {"passed": True}},
            )

            with tempfile.TemporaryDirectory() as tmp:
                tmp_path = Path(tmp)
                fake_xsct = tmp_path / "Vitis" / "2024.2" / "bin" / "xsct"
                write_failing_xsct(fake_xsct)
                xsa = tmp_path / "board.xsa"
                xsa.write_bytes(b"fake xsa")
                workspace = tmp_path / "workspace"
                temp_root = tmp_path / "temp"

                config = VitisWorkspaceConfig(
                    vitis_path=str(tmp_path),
                    xsa_path=str(xsa),
                    workspace_path=str(workspace),
                    temp_path=str(temp_root),
                    processor="psu_cortexa53_0",
                    runtime="standalone",
                    timeout_s=10,
                )
                manager = VitisWorkspaceJobManager()
                job = VitisWorkspaceJob(
                    id="vitis_tcl_error",
                    source_job_id=generate_job.id,
                    source_project=project_name,
                    config=config,
                    generate_job=generate_job,
                )

                with self.assertRaisesRegex(RuntimeError, "XSCT log hata"):
                    manager._blocking(job)

                self.assertIsNotNone(job.result)
                result = job.result or {}
                self.assertFalse(result["successful"])
                self.assertEqual(result["xsct_exit_code"], 0)
                self.assertIn("invalid command name", result["xsct_stderr_tail"])
                categories = {issue["category"] for issue in result["compile_issues"]}
                self.assertIn("xsct_tcl_command", categories)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
