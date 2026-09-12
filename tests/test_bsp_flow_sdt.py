"""Vitis Unified / SDT BSP akisi: bsp_flow modulu, xparameters SDT ayristirma, SDT kod uretimi,
Unified workspace betigi (kurulum oncesi hazirlik; gercek Vitis 2025.2 dogrulamasi ayri)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.parsers.xparameters import parse_xparameters  # noqa: E402
from backend.vitis_unified import (  # noqa: E402
    MICROBLAZE_LWIP_PARAMS, bsp_flow_preflight_issue, locate_vitis_cli, render_unified_workspace_script)
from orchestrator import codegen  # noqa: E402
from orchestrator.bsp_flow import (  # noqa: E402
    bsp_flow, expected_bsp_flow_for_vitis, is_sdt, is_unified_vitis, lookup_arg, lookup_suffix)
from tests.test_testbench import add_microblaze_ethernetlite, add_zynqmp_ps_uart, load_sample_spec  # noqa: E402

SDT_XPARAMETERS = """
/* Vitis Unified (SDT/Lopper) xparameters.h - DEVICE_ID yok */
#define XPAR_XIIC_0_BASEADDR 0x40800000
#define XPAR_XIIC_0_HIGHADDR 0x4080FFFF
#define XPAR_AXI_IIC_0_BASEADDR 0x40800000
#define XPAR_XSPI_0_BASEADDR 0x44A00000
#define XPAR_XUARTLITE_0_BASEADDR 0x40600000
#define XPAR_AXI_UARTLITE_0_BASEADDR 0x40600000
#define XPAR_MICROBLAZE_0_LOCAL_MEMORY_BASEADDR 0x00000000
#define XPAR_MIG_7SERIES_0_BASEADDR 0x80000000
#define XPAR_XINTC_0_BASEADDR 0x41200000
"""

CLASSIC_XPARAMETERS = """
#define XPAR_AXI_IIC_0_DEVICE_ID 0
#define XPAR_AXI_IIC_0_BASEADDR 0x40800000
#define XPAR_MIG_7SERIES_0_BASEADDR 0x80000000
"""


class BspFlowModuleTests(unittest.TestCase):
    def test_default_flow_is_classic_and_sdt_is_recognized(self) -> None:
        self.assertEqual(bsp_flow({"project": {}}), "classic")
        self.assertEqual(bsp_flow({"project": {"bsp_flow": "SDT"}}), "sdt")
        self.assertEqual(bsp_flow({"project": {"bsp_flow": "bogus"}}), "classic")
        self.assertTrue(is_sdt({"project": {"bsp_flow": "sdt"}}))

    def test_lookup_arg_by_flow(self) -> None:
        self.assertEqual(lookup_arg("XPAR_AXI_IIC_0", False), "XPAR_AXI_IIC_0_DEVICE_ID")
        self.assertEqual(lookup_arg("XPAR_AXI_IIC_0", True), "XPAR_AXI_IIC_0_BASEADDR")
        self.assertEqual(lookup_suffix(True), "BASEADDR")

    def test_unified_version_threshold(self) -> None:
        self.assertFalse(is_unified_vitis("2023.2"))
        self.assertFalse(is_unified_vitis("2022.2"))
        self.assertTrue(is_unified_vitis("2024.1"))
        self.assertTrue(is_unified_vitis("2025.2.1"))
        self.assertFalse(is_unified_vitis("unknown"))
        self.assertEqual(expected_bsp_flow_for_vitis("2025.2"), "sdt")
        self.assertEqual(expected_bsp_flow_for_vitis("2023.2"), "classic")


class XparametersSdtTests(unittest.TestCase):
    def test_sdt_header_without_device_id_yields_peripherals(self) -> None:
        result = parse_xparameters(SDT_XPARAMETERS)
        self.assertTrue(result.sdt)
        by_type = {c["type"]: c for c in result.controllers}
        self.assertIn("i2c", by_type)
        self.assertIn("spi", by_type)
        self.assertIn("uart", by_type)
        self.assertEqual(by_type["i2c"]["base_address"], "0x40800000")
        # Bellek bolgeleri (LMB, MIG) surucu kuralina uymaz -> denetleyici degil.
        instances = {c["instance"] for c in result.controllers}
        self.assertNotIn("XPAR_MIG_7SERIES_0", instances)
        self.assertNotIn("XPAR_MICROBLAZE_0_LOCAL_MEMORY", instances)
        # Ayni adresteki kanonik/etiket cifti tek denetleyiciye iner.
        self.assertEqual(len([c for c in result.controllers if c["type"] == "i2c"]), 1)

    def test_classic_header_is_not_flagged_sdt(self) -> None:
        result = parse_xparameters(CLASSIC_XPARAMETERS)
        self.assertFalse(result.sdt)
        self.assertEqual(len(result.controllers), 1)


class SdtCodegenTests(unittest.TestCase):
    def _generate(self, spec: dict) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            codegen.generate(spec, out)
            return {str(p.relative_to(out)).replace("\\", "/"): p.read_text(encoding="utf-8", errors="replace")
                    for p in out.rglob("*") if p.suffix in (".c", ".h")}

    def test_sdt_spec_uses_baseaddr_lookup_everywhere(self) -> None:
        spec = load_sample_spec("sdt_probe")
        spec["project"]["bsp_flow"] = "sdt"
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        files = self._generate(spec)
        joined = "\n".join(files.values())
        self.assertIn("_LookupConfig(XPAR_", joined)
        self.assertNotIn("_DEVICE_ID)", joined, "SDT uretiminde LookupConfig DEVICE_ID ile cagrilmamali")
        self.assertRegex(joined, r"_LookupConfig\(XPAR_[A-Z0-9_]+_BASEADDR\)")
        uart_h = files["tests/spec2code_testbench_uart.h"]
        self.assertIn("SPEC2CODE_TESTBENCH_UART_BASEADDR", uart_h)
        self.assertNotIn("SPEC2CODE_TESTBENCH_UART_DEVICE_ID", uart_h)

    def test_classic_spec_keeps_device_id_lookup(self) -> None:
        spec = load_sample_spec("classic_probe")
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        joined = "\n".join(self._generate(spec).values())
        self.assertRegex(joined, r"_LookupConfig\(XPAR_[A-Z0-9_]+_DEVICE_ID\)")
        self.assertNotRegex(joined, r"_LookupConfig\(XPAR_[A-Z0-9_]+_BASEADDR\)")

    def test_microblaze_lwip_agent_in_sdt_uses_xiltimer_platform(self) -> None:
        spec = load_sample_spec("sdt_mb_eth")
        spec["project"].update({"platform": "microblaze_7series", "target_core": "microblaze_0",
                                "runtime": "bare_metal", "testbench_transport": "eth", "bsp_flow": "sdt"})
        add_microblaze_ethernetlite(spec)
        files = self._generate(spec)
        lwip_c = files["tests/spec2code_testbench_lwip.c"]
        self.assertIn('#include "xiltimer.h"', lwip_c)
        self.assertIn("XTimer_SetInterval(50UL);", lwip_c)
        self.assertIn("XTimer_SetHandler(spec2codeTestbenchTimerHandler, NULL, XINTERRUPT_DEFAULT_PRIORITY);", lwip_c)
        self.assertIn("spec2codeTestbenchPlatformTimerSetup();", lwip_c)
        # Klasik INTC/Timer kalibi SDT'de yok: vektor makrosu, XIntc, microblaze_enable_interrupts.
        for token in ("XPAR_INTC_0_TMRCTR_0_VEC_ID", "XIntc_Initialize", "microblaze_enable_interrupts",
                      "spec2codeTestbenchPlatformInterruptsEnable", '#include "xintc.h"'):
            self.assertNotIn(token, lwip_c)
        self.assertNotIn("_DEVICE_ID)", "\n".join(files.values()))

    def test_microblaze_lwip_agent_in_classic_keeps_intc_platform(self) -> None:
        spec = load_sample_spec("classic_mb_eth")
        spec["project"].update({"platform": "microblaze_7series", "target_core": "microblaze_0",
                                "runtime": "bare_metal", "testbench_transport": "eth"})
        add_microblaze_ethernetlite(spec)
        lwip_c = self._generate(spec)["tests/spec2code_testbench_lwip.c"]
        self.assertIn("XIntc_Initialize(&S_sIntc, XPAR_INTC_0_DEVICE_ID);", lwip_c)
        self.assertNotIn("xiltimer", lwip_c)


class UnifiedWorkspaceTests(unittest.TestCase):
    def test_locate_vitis_cli_finds_bin_vitis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Vitis" / "2025.2"
            (root / "bin").mkdir(parents=True)
            (root / "bin" / "vitis.bat").write_text("@echo off\n", encoding="utf-8")
            self.assertEqual(locate_vitis_cli(str(root)), root / "bin" / "vitis.bat")
            self.assertEqual(locate_vitis_cli(str(root.parent)), root / "bin" / "vitis.bat")
            with self.assertRaises(FileNotFoundError):
                locate_vitis_cli(str(Path(tmp) / "nowhere"))

    def test_bsp_flow_preflight_mismatch(self) -> None:
        self.assertIsNone(bsp_flow_preflight_issue({"project": {"bsp_flow": "sdt"}}, "2025.2"))
        self.assertIsNone(bsp_flow_preflight_issue({"project": {}}, "2023.2"))
        issue = bsp_flow_preflight_issue({"project": {}}, "2025.2")
        self.assertIsNotNone(issue)
        self.assertEqual(issue["category"], "bsp_flow_mismatch")
        self.assertEqual(issue["expected_bsp_flow"], "sdt")
        issue = bsp_flow_preflight_issue({"project": {"bsp_flow": "sdt"}}, "2023.2")
        self.assertEqual(issue["expected_bsp_flow"], "classic")

    def test_render_full_script_is_valid_python_with_platform_and_lwip(self) -> None:
        script = render_unified_workspace_script(
            mode="full", workspace_path=Path("D:/ws"), xsa_path=Path("D:/hw/design.xsa"), source_root=Path("D:/stage/src"),
            source_files=["main.c", "drivers/x/x.c", "tests/spec2code_testbench_lwip.c"], platform_name="p_platform",
            domain_name="p_domain", app_name="p_app", processor="microblaze_0", os_name="standalone",
            enable_lwip=True, lwip_sys_timers=True, lwip_api_mode="RAW_API", lwip_params=MICROBLAZE_LWIP_PARAMS,
            source_include_dirs=["drivers/x", "tests"], shell_app_name="p_app_shell",
            shell_source_root=Path("D:/stage/src_shell"), shell_source_files=["main.c"], shell_include_dirs=["drivers/x"])
        compile(script, "unified.py", "exec")
        self.assertIn("import vitis", script)
        self.assertIn("create_platform_component(name=PLATFORM, hw_design=XSA, os=OS, cpu=CPU", script)
        self.assertIn('template="empty_application"', script)
        self.assertIn("set_lib(lib_name=LWIP_LIB)", script)
        self.assertIn("LWIP_LIB = 'lwip220'", script)
        self.assertIn("'memp_n_tcp_seg': 64", script)
        self.assertIn('set_lib_param(domain, LWIP_LIB, "no_sys_no_timers", "false")', script)
        self.assertIn("LWIP_SYS_TIMERS = True", script)
        self.assertIn('set_app_config(key="USER_INCLUDE_DIRECTORIES"', script)
        self.assertIn("find_platform_in_repos(PLATFORM)", script)
        self.assertIn("patch_lwip_sources", script)
        self.assertIn("emaclite_status_declared_twice", script)
        self.assertNotIn('set_lib(lib_name="xiltimer")', script)
        self.assertIn("vitis.dispose()", script)
        self.assertIn("MICROBLAZE = True", script)
        self.assertIn("XSA = 'D:/hw/design.xsa'", script)

    def test_render_update_script_skips_platform(self) -> None:
        script = render_unified_workspace_script(
            mode="update", workspace_path=Path("D:/ws"), xsa_path=None, source_root=Path("D:/stage/src"),
            source_files=["main.c"], platform_name="p", domain_name="d", app_name="a", processor="psu_cortexa53_0",
            os_name="freertos")
        compile(script, "unified_update.py", "exec")
        self.assertIn("MODE = 'update'", script)
        self.assertIn("client.get_component(name=name)", script)
        self.assertIn("MICROBLAZE = False", script)
        with self.assertRaises(ValueError):
            render_unified_workspace_script(
                mode="full", workspace_path=Path("D:/ws"), xsa_path=None, source_root=Path("D:/s"), source_files=[],
                platform_name="p", domain_name="d", app_name="a", processor="microblaze_0", os_name="standalone")


if __name__ == "__main__":
    unittest.main()
