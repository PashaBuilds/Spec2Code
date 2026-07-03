import os
import tempfile
import unittest
from pathlib import Path

from backend.run_on_board import (
    RunOnBoardConfig,
    RunOnBoardJob,
    RunOnBoardJobManager,
    locate_xsdb,
    normalize_hw_server_url,
    render_run_on_board_script,
)
from tests.test_vitis_workspace import _write_fake_xsct


_RUN_OK_BODY = '''\
print("S2C-RUN: connected")
print("S2C-RUN: psu_init done")
print("S2C-RUN: elf downloaded")
print("S2C-RUN: running")
sys.exit(0)
'''

_RUN_FAIL_BODY = '''\
print("no targets found with jtag")
sys.exit(1)
'''


def _make_workspace(root: Path, *, with_bit: bool = True) -> Path:
    ws = root / "ws"
    (ws / "myapp" / "Debug").mkdir(parents=True)
    (ws / "myapp" / "Debug" / "myapp.elf").write_text("elf")
    (ws / "myplat" / "hw").mkdir(parents=True)
    (ws / "myplat" / "hw" / "psu_init.tcl").write_text("proc psu_init {} {}")
    if with_bit:
        (ws / "myplat" / "hw" / "design.bit").write_text("bit")
    return ws


class NormalizeHwServerUrlTests(unittest.TestCase):
    def test_empty_means_local_usb_jtag(self) -> None:
        self.assertEqual(normalize_hw_server_url(""), "")
        self.assertEqual(normalize_hw_server_url("   "), "")

    def test_bare_ip_gets_default_smartlynq_port(self) -> None:
        self.assertEqual(normalize_hw_server_url("192.168.0.10"), "TCP:192.168.0.10:3121")

    def test_host_with_port_is_kept(self) -> None:
        self.assertEqual(normalize_hw_server_url("smartlynq-lab1:3122"), "TCP:smartlynq-lab1:3122")

    def test_tcp_prefixes_are_normalized(self) -> None:
        self.assertEqual(normalize_hw_server_url("TCP:192.168.0.10:3121"), "TCP:192.168.0.10:3121")
        self.assertEqual(normalize_hw_server_url("tcp://192.168.0.10"), "TCP:192.168.0.10:3121")

    def test_invalid_addresses_raise(self) -> None:
        for bad in (":3121", "192.168.0.10:abc", "tcp:"):
            with self.assertRaises(ValueError):
                normalize_hw_server_url(bad)


class RenderRunScriptTests(unittest.TestCase):
    def test_script_follows_standard_zynqmp_jtag_flow(self) -> None:
        # Vitis "Run on hardware" order: system reset -> psu_init -> FPGA ->
        # processor reset -> ELF download -> continue.
        script = render_run_on_board_script(
            elf_path=Path("C:/ws/app/Debug/app.elf"),
            psu_init_path=Path("C:/ws/plat/hw/psu_init.tcl"),
            bitstream_path=Path("C:/ws/plat/hw/top.bit"),
            processor="psu_cortexa53_0",
        )
        markers = ["\nconnect\n", "rst -system", "psu_init", "fpga {",
                   "rst -processor", "\ndow {", "\ncon\n", "disconnect"]
        positions = [script.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('name =~ "*A53*#0"', script)
        # Tcl paths must use forward slashes even on Windows.
        self.assertIn("C:/ws/app/Debug/app.elf", script)

    def test_script_connects_to_smartlynq_hw_server_when_url_given(self) -> None:
        script = render_run_on_board_script(
            elf_path=Path("a.elf"),
            psu_init_path=Path("p.tcl"),
            processor="psu_cortexa53_0",
            hw_server_url="TCP:192.168.0.10:3121",
        )
        self.assertIn("connect -url TCP:192.168.0.10:3121\n", script)
        self.assertNotIn("\nconnect\n", script)

    def test_script_without_bitstream_targets_r5(self) -> None:
        script = render_run_on_board_script(
            elf_path=Path("a.elf"),
            psu_init_path=Path("p.tcl"),
            bitstream_path=None,
            processor="psu_cortexr5_0",
        )
        self.assertNotIn("fpga", script)
        self.assertIn('"*R5*#0"', script)

    def test_versal_script_programs_pdi_then_downloads_to_a72(self) -> None:
        # Versal JTAG boot: the PDI carries PLM + PL + NoC config; there is
        # no psu_init/ps7_init and no separate bitstream step.
        script = render_run_on_board_script(
            elf_path=Path("C:/ws/app/Debug/app.elf"),
            processor="psv_cortexa72_0",
            platform="versal",
            pdi_path=Path("C:/ws/plat/hw/vck190.pdi"),
        )
        markers = ["\nconnect\n", "device program {C:/ws/plat/hw/vck190.pdi}",
                   "rst -processor", "\ndow {", "\ncon\n"]
        positions = [script.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('"*A72*#0"', script)
        self.assertNotIn("psu_init", script)
        self.assertNotIn("fpga {", script)

    def test_versal_script_requires_pdi(self) -> None:
        with self.assertRaises(ValueError):
            render_run_on_board_script(
                elf_path=Path("a.elf"), processor="psv_cortexa72_0",
                platform="versal", pdi_path=None)

    def test_zynq7000_script_uses_ps7_init_and_post_config(self) -> None:
        script = render_run_on_board_script(
            elf_path=Path("C:/ws/app/Debug/app.elf"),
            processor="ps7_cortexa9_0",
            platform="zynq_7000",
            ps7_init_path=Path("C:/ws/plat/hw/ps7_init.tcl"),
            bitstream_path=Path("C:/ws/plat/hw/top.bit"),
        )
        markers = ["rst -system", "ps7_init\n", "fpga {", "\ndow {",
                   "ps7_post_config", "\ncon\n"]
        positions = [script.index(marker) for marker in markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('"*A9*#0"', script)
        self.assertNotIn("psu_init", script)


class LocateXsdbTests(unittest.TestCase):
    def test_locates_versioned_vitis_layout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            name = "xsdb.bat" if os.name == "nt" else "xsdb"
            target = root / "Vitis" / "2023.2" / "bin" / name
            _write_fake_xsct(target, "sys.exit(0)\n", "2023.2")
            self.assertEqual(locate_xsdb(str(root)), target)

    def test_missing_xsdb_reports_searched_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError) as ctx:
                locate_xsdb(tmp)
            self.assertIn("xsdb executable not found", str(ctx.exception))


class RunOnBoardBlockingTests(unittest.TestCase):
    def _run(self, body: str, root: Path, *, program_fpga: str = "auto",
             hw_server_url: str = "") -> RunOnBoardJob:
        name = "xsdb.bat" if os.name == "nt" else "xsdb"
        xsdb = root / "tools" / name
        _write_fake_xsct(xsdb, body, "2023.2")
        config = RunOnBoardConfig(
            vitis_path=str(xsdb),
            workspace_path=str(root / "ws"),
            platform_name="myplat",
            app_name="myapp",
            program_fpga=program_fpga,
            hw_server_url=hw_server_url,
            timeout_s=60,
        )
        job = RunOnBoardJob(id="runboard_test", config=config)
        RunOnBoardJobManager()._blocking(job)
        return job

    def test_success_flow_collects_run_markers_and_bitstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            job = self._run(_RUN_OK_BODY, root)
        self.assertIn("S2C-RUN: running", job.result["markers"])
        self.assertTrue(job.result["bitstream"].endswith("design.bit"))
        self.assertTrue(job.result["elf"].endswith("myapp.elf"))

    def test_smartlynq_url_reaches_script_and_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root)
            job = self._run(_RUN_OK_BODY, root, hw_server_url="192.168.0.10")
            scripts = sorted((root / "ws" / ".spec2code_runboard").glob("run_*.tcl"))
            script = scripts[-1].read_text(encoding="utf-8")
        self.assertEqual(job.result["hw_server_url"], "TCP:192.168.0.10:3121")
        self.assertIn("connect -url TCP:192.168.0.10:3121\n", script)

    def test_smartlynq_connection_failure_hints_at_address(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root, with_bit=False)
            with self.assertRaises(RuntimeError) as ctx:
                self._run('print("Connection refused")\nsys.exit(1)\n', root,
                          hw_server_url="TCP:10.0.0.5:3121")
            self.assertIn("TCP:10.0.0.5:3121", str(ctx.exception))
            self.assertIn("SmartLynq", str(ctx.exception))

    def test_failure_raises_with_jtag_hint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root, with_bit=False)
            with self.assertRaises(RuntimeError) as ctx:
                self._run(_RUN_FAIL_BODY, root)
            self.assertIn("JTAG", str(ctx.exception))

    def test_program_fpga_yes_requires_bitstream(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _make_workspace(root, with_bit=False)
            with self.assertRaises(FileNotFoundError):
                self._run(_RUN_OK_BODY, root, program_fpga="yes")

    def test_versal_blocking_flow_finds_pdi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = _make_workspace(root, with_bit=False)
            (ws / "myplat" / "hw" / "boot.pdi").write_text("pdi")
            name = "xsdb.bat" if os.name == "nt" else "xsdb"
            xsdb = root / "tools" / name
            _write_fake_xsct(xsdb, _RUN_OK_BODY, "2023.2")
            config = RunOnBoardConfig(
                vitis_path=str(xsdb),
                workspace_path=str(root / "ws"),
                platform_name="myplat",
                app_name="myapp",
                processor="psv_cortexa72_0",
                platform="versal",
                timeout_s=60,
            )
            job = RunOnBoardJob(id="runboard_versal", config=config)
            RunOnBoardJobManager()._blocking(job)
        self.assertIn("S2C-RUN: running", job.result["markers"])
        self.assertIsNone(job.result["bitstream"])


if __name__ == "__main__":
    unittest.main()
