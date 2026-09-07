"""QC stub baslik kapsami: ZynqMP FreeRTOS + PS Ethernet (lwIP SOCKET) + QSPI PSU.

SAHA (2026-09-07): custom PL IP'li ZynqMP tasariminda Generate'in QC kapisi
dusuyordu. Kok neden uretilen kodda degil, QC'nin stub BSP basliklarindaydi:
`orchestrator/qc/bsp_stubs/` yalnizca bare-metal RAW lwIP (tcp.h/pbuf.h) ve
eski XQspiPsu API'sini tasiyordu. FreeRTOS SOCKET ajani (`lwipopts.h`,
`lwip/sys.h`, `lwip/sockets.h`, `lwip/tcpip.h`, `lwip/timeouts.h`, `task.h`
vTaskDelete/vTaskStartScheduler, SYS_ARCH_* kilitleri), dual-parallel stripe
(`Config.ConnectionMode`, `XQSPIPSU_MSG_FLAG_STRIPE`) ve GEM3 (`XPAR_XEMACPS_3_*`)
stub'da yoktu -> clang-tidy "file not found / undeclared" ERROR -> QC KALDI.

Bu test uretilen ZynqMP ciktisini GERCEK clang-tidy ile stub'lara karsi cozer;
tek bir error-seviyesi bulgu kapiyi dusurur. clang-tidy yoksa atlanir (stub
kapsamini tek basina dogrulamak icin `StubHeaderContentTests` her yerde kosar).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hostplat import tools
from orchestrator import codegen
from orchestrator.qc import runners

ROOT = Path(__file__).resolve().parent.parent
STUBS = ROOT / "orchestrator" / "qc" / "bsp_stubs"


def zynqmp_freertos_lwip_qspi_spec() -> dict:
    """radar_io_board ornegi + GEM3 PS Ethernet + XQspiPsu flash (my_io_board sahasi)."""
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": "unit_qc_stub_zynqmp", "runtime": "freertos"}
    spec["controllers"].append({
        "id": "ps_gem_3", "type": "eth", "instance": "XPAR_XEMACPS_3",
        "base_address": "0xFF0E0000", "device_id": 3, "driver": "XEmacPs",
        "source": "xparameters", "zone": "ps",
    })
    spec["controllers"].append({
        "id": "ps_qspi_0", "type": "qspi", "instance": "XPAR_XQSPIPSU_0",
        "base_address": "0xFF0F0000", "device_id": 0, "driver": "XQspiPsu",
        "source": "xparameters", "zone": "ps",
    })
    for device in spec["devices"]:
        if device.get("part") == "MT25QU02G":
            device["attach"] = {"controller_id": "ps_qspi_0", "spi_chip_select": 0}
    return spec


class StubHeaderContentTests(unittest.TestCase):
    """Arac olmadan da kosar: stub basliklari FreeRTOS/lwIP/QSPI PSU sembollerini tasimali."""

    def test_lwip_socket_flavor_headers_exist(self) -> None:
        for rel in ("lwipopts.h", "lwip/sys.h", "lwip/sockets.h", "lwip/tcpip.h",
                    "lwip/timeouts.h", "task.h", "netif/xadapter.h"):
            self.assertTrue((STUBS / rel).is_file(), rel)

    def test_stub_symbols_used_by_generated_zynqmp_code(self) -> None:
        expectations = {
            "xqspipsu.h": ("ConnectionMode", "XQSPIPSU_CONNECTION_MODE_PARALLEL", "XQSPIPSU_MSG_FLAG_STRIPE"),
            "lwip/sys.h": ("sys_thread_new", "SYS_ARCH_DECL_PROTECT", "SYS_ARCH_PROTECT", "SYS_ARCH_UNPROTECT"),
            "lwip/sockets.h": ("lwip_socket", "lwip_accept", "lwip_recv", "lwip_send", "struct sockaddr_in", "socklen_t"),
            "lwip/tcpip.h": ("tcpip_callback",),
            "lwip/timeouts.h": ("sys_timeout",),
            "lwip/tcp.h": ("tcp_sndbuf",),
            "lwipopts.h": ("DEFAULT_THREAD_PRIO",),
            "task.h": ("vTaskDelete", "vTaskStartScheduler"),
            "netif/xadapter.h": ("xemacif_input_thread",),
            "xparameters.h": ("XPAR_XEMACPS_3_BASEADDR",),
        }
        for rel, symbols in expectations.items():
            text = (STUBS / rel).read_text(encoding="utf-8")
            for symbol in symbols:
                self.assertIn(symbol, text, f"{rel}: {symbol}")


def xsa_named_spec() -> dict:
    """XSA'dan cikarilan spec: denetleyici ornekleri cevre-birimi adli (XPAR_PSU_I2C_0 ...)."""
    spec = zynqmp_freertos_lwip_qspi_spec()
    spec["project"]["name"] = "unit_qc_stub_xsa_named"
    rename = {"XPAR_XIICPS_0": "XPAR_PSU_I2C_0", "XPAR_XQSPIPSU_0": "XPAR_PSU_QSPI_0",
              "XPAR_XEMACPS_3": "XPAR_PSU_ETHERNET_3", "XPAR_XUARTPS_0": "XPAR_PSU_UART_0"}
    for controller in spec["controllers"]:
        controller["instance"] = rename.get(controller["instance"], controller["instance"])
    return spec


class ProjectXparametersStubTests(unittest.TestCase):
    def test_collects_only_unknown_xpar_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "a.c"
            src.write_text("XPAR_PSU_I2C_0_DEVICE_ID XPAR_XIICPS_0_DEVICE_ID XPAR_AXI_IIC_0_BASEADDR "
                           "XPAR_MDM_0_HIGHADDR XPAR_PSU_I2C_0_DEVICE_ID", encoding="utf-8")
            text = runners.project_xparameters_stub([src])
        self.assertIn("#define XPAR_PSU_I2C_0_DEVICE_ID 0", text)
        self.assertIn("#define XPAR_AXI_IIC_0_BASEADDR 0x40000000U", text)
        self.assertIn("XPAR_MDM_0_HIGHADDR", text)
        # generic stub zaten tanimliyor: yeniden tanimlanmaz
        self.assertNotIn("#define XPAR_XIICPS_0_DEVICE_ID", text)
        self.assertEqual(text.count("XPAR_PSU_I2C_0_DEVICE_ID"), 2)  # ifndef + define

    def test_generic_stub_pulls_project_stub(self) -> None:
        text = (STUBS / "xparameters.h").read_text(encoding="utf-8")
        self.assertIn('__has_include("spec2code_qc_xparameters.h")', text)


@unittest.skipUnless(tools.resolve("clang-tidy", required=False), "clang-tidy yok")
class GeneratedZynqmpOutputResolvesAgainstStubsTests(unittest.TestCase):
    def test_no_error_level_clang_tidy_findings(self) -> None:
        self._assert_clean(zynqmp_freertos_lwip_qspi_spec())

    def test_xsa_named_controllers_resolve_via_project_stub(self) -> None:
        self._assert_clean(xsa_named_spec())

    def _assert_clean(self, spec: dict) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            qc_include_dir = Path(tmp) / "qc_include"
            runners.write_project_xparameters_stub(
                qc_include_dir, [*out_dir.rglob("*.c"), *out_dir.rglob("*.h")])
            include_dirs = [*runners.driver_include_dirs(out_dir / "drivers"), out_dir / "tests",
                            *runners.driver_include_dirs(out_dir / "cit"), qc_include_dir]
            targets = [
                out_dir / "tests" / "spec2code_telnet_log.c",
                out_dir / "tests" / "spec2code_testbench_lwip.c",
                out_dir / "tests" / "spec2code_testbench_lwip_main.c",
                out_dir / "tests" / f"{spec['project']['name']}_testbench_ops.c",
                *sorted((out_dir / "drivers").rglob("mt25qu02g.c")),
                *sorted((out_dir / "drivers").rglob("ltc2991.c")),
            ]
            for target in targets:
                self.assertTrue(target.is_file(), target.name)
            errors = []
            for target in targets:
                result = runners.run_clang_tidy(target, include_dirs)
                self.assertTrue(result.available)
                errors += [f"{target.name}:{v.line}: {v.message}" for v in result.violations
                           if v.severity == "error"]
                # MSVC CRT `strncpy` deprecation'i host gurultusudur, ciktida olmamali.
                self.assertFalse([v for v in result.violations if "strncpy_s" in v.message],
                                 f"{target.name}: CRT deprecation uyarisi sizdi")
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
