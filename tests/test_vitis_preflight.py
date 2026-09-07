"""Spec/XSA on kontrolu (SAHA 2026-09-07): ZynqMP + FreeRTOS spec'ine MicroBlaze XSA verildi.

XSCT BSP DRC'si `CPU has no connection to Interrupt controller` ile dustu ve Doctor
bunu yaniltici `workspace_stale` diye raporladi. Artik XSCT'den ONCE iki kontrol
vardir (platform uyumu, MicroBlaze+FreeRTOS icin AXI INTC/Timer) ve DRC metni de
kendi kategorisiyle eslesir.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.vitis_errors import map_vitis_errors
from backend.vitis_workspace import spec_xsa_preflight, workspace_lock_issue, workspace_locked_by_ide, xsa_module_types

ROOT = Path(__file__).resolve().parent.parent
MB_XSA = ROOT / "test" / "0_dosyalar" / "microblaze_nexys_a7.xsa"
ZCU_XSA = ROOT / "test" / "0_dosyalar" / "zcu102.xsa"


def _spec(platform: str, runtime: str) -> dict:
    return {"project": {"name": "p", "platform": platform, "runtime": runtime}}


@unittest.skipUnless(MB_XSA.is_file() and ZCU_XSA.is_file(), "yerel test XSA'lari yok")
class SpecXsaPreflightTests(unittest.TestCase):
    def test_module_types_are_read_from_hwh(self) -> None:
        self.assertIn("microblaze", xsa_module_types(MB_XSA))
        self.assertNotIn("axi_intc", xsa_module_types(MB_XSA))
        self.assertIn("zynq_ultra_ps_e", xsa_module_types(ZCU_XSA))

    def test_zynqmp_freertos_spec_with_microblaze_xsa_is_rejected_before_xsct(self) -> None:
        issues = spec_xsa_preflight(_spec("zynq_ultrascale", "freertos"), MB_XSA, "freertos10_xilinx")
        categories = [i["category"] for i in issues]
        self.assertIn("platform_mismatch", categories)
        self.assertIn("freertos_mb_no_intc", categories)
        self.assertTrue(all(i["severity"] == "error" for i in issues))
        self.assertIn("axi_intc, axi_timer", next(i["message"] for i in issues if i["category"] == "freertos_mb_no_intc"))

    def test_microblaze_bare_metal_spec_with_microblaze_xsa_passes(self) -> None:
        self.assertEqual(spec_xsa_preflight(_spec("microblaze_7series", "bare_metal"), MB_XSA, "standalone"), [])

    def test_microblaze_freertos_without_intc_is_flagged_even_when_platform_matches(self) -> None:
        issues = spec_xsa_preflight(_spec("microblaze_7series", "freertos"), MB_XSA, "freertos10_xilinx")
        self.assertEqual([i["category"] for i in issues], ["freertos_mb_no_intc"])

    def test_zynqmp_spec_with_zynqmp_xsa_passes(self) -> None:
        self.assertEqual(spec_xsa_preflight(_spec("zynq_ultrascale", "freertos"), ZCU_XSA, "freertos10_xilinx"), [])

    def test_missing_xsa_is_not_a_preflight_failure(self) -> None:
        self.assertEqual(spec_xsa_preflight(_spec("zynq_ultrascale", "freertos"), Path("yok.xsa"), "freertos10_xilinx"), [])


class WorkspaceLockTests(unittest.TestCase):
    """Vitis IDE workspace'i acikken XSCT 'Invalid Workspace' verir; kilit XSCT'den once gorulmeli."""

    def test_no_metadata_means_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(workspace_locked_by_ide(Path(tmp)))
            self.assertIsNone(workspace_lock_issue(Path(tmp)))

    def test_unlocked_lock_file_means_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / ".metadata" / ".lock"
            lock.parent.mkdir()
            lock.write_bytes(b"")
            self.assertIsNone(workspace_locked_by_ide(Path(tmp)))

    def test_os_locked_lock_file_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / ".metadata" / ".lock"
            lock.parent.mkdir()
            lock.write_bytes(b"\0")
            fd = os.open(str(lock), os.O_RDWR)
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                self.assertEqual(workspace_locked_by_ide(Path(tmp)), lock)
                issue = workspace_lock_issue(Path(tmp))
                self.assertEqual(issue["category"], "workspace_locked")
                self.assertIn("Invalid Workspace", issue["message"])
            finally:
                if os.name == "nt":
                    import msvcrt
                    try:
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
                os.close(fd)

    def test_invalid_workspace_log_line_maps_to_lock_category(self) -> None:
        issues = map_vitis_errors("Invalid Workspace\n    while executing\n")
        self.assertEqual(issues[0]["category"], "workspace_locked")


class FreertosDrcErrorMappingTests(unittest.TestCase):
    def test_intc_drc_line_maps_to_its_own_category(self) -> None:
        log = ("ERROR: [Hsi 55-1545] Problem running tcl command ::sw_freertos10_xilinx_v1_14::FreeRTOS_drc : "
               "CPU has no connection to Interrupt controller.\n")
        issues = map_vitis_errors(log)
        self.assertTrue(issues)
        self.assertEqual(issues[0]["category"], "freertos_mb_no_intc")
        self.assertIn("axi_intc", issues[0]["suggestion"])


if __name__ == "__main__":
    unittest.main()
