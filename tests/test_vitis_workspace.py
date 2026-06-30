import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.jobs import Job, _OUTPUTS
from backend.vitis_workspace import (
    VitisWorkspaceConfig,
    VitisWorkspaceJob,
    VitisWorkspaceJobManager,
    default_vitis_processor,
    detect_xsct,
    locate_xsct,
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

    def test_xsct_script_contains_workspace_creation_steps(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="standalone",
        )

        self.assertIn("setws $workspace_path", script)
        self.assertIn('puts "\\[Spec2Code\\] workspace: $workspace_path"', script)
        self.assertNotIn('puts "[Spec2Code]', script)
        self.assertIn("app create -name $app_name -hw $xsa_path -proc $processor -os $os_name", script)
        self.assertIn("importsources -name $app_name -path $source_path", script)
        self.assertIn("app build -name $app_name", script)

    def test_xsct_script_enables_lwip_library_when_requested(self) -> None:
        script = render_xsct_script(
            workspace_path=Path("/tmp/ws"),
            xsa_path=Path("/tmp/board.xsa"),
            source_root=Path("/tmp/src"),
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
            app_name="my_app",
            processor="psu_cortexa53_0",
            os_name="freertos10_xilinx",
            enable_lwip=True,
        )

        self.assertIn("set spec2code_enable_lwip 1", script)
        self.assertIn("set spec2code_lwip_api_mode {SOCKET_API}", script)
        self.assertIn("foreach spec2code_lwip_api_name {api_mode API_MODE}", script)
        self.assertIn("lwIP API mode selected: $spec2code_lwip_api_name=$spec2code_lwip_api_mode", script)

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

                config = VitisWorkspaceConfig(
                    vitis_path=str(tmp_path),
                    xsa_path=str(xsa),
                    workspace_path=str(workspace),
                    processor="psu_cortexa53_0",
                    runtime="standalone",
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
                self.assertTrue((workspace / "_spec2code_staging" / "vitis_unit" / "src" / "drivers").is_dir())
                self.assertTrue(Path(result["script_path"]).is_file())
                self.assertTrue(Path(result["stdout_log"]).read_text(encoding="utf-8").startswith("fake xsct ran"))
                self.assertTrue(result["successful"])
                self.assertEqual(result["xsct_exit_code"], 0)
                self.assertIn("spec2code_selftest_main.h", result["staged_files"])
                self.assertIn("spec2code_selftest_main.c", result["staged_files"])
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

                config = VitisWorkspaceConfig(
                    vitis_path=str(tmp_path),
                    xsa_path=str(xsa),
                    workspace_path=str(workspace),
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
