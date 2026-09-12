"""SDT'de PS denetleyici ornek adlari kanonik (XPAR_XIICPS_0) olur; PL etiketleri korunur; telnet net IP makrolari."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import codegen  # noqa: E402
from orchestrator.bsp_flow import sdt_controller_instances, with_sdt_instances  # noqa: E402
from tests.test_testbench import add_zynqmp_ps_ethernet, add_zynqmp_ps_uart, load_sample_spec  # noqa: E402


def _controllers() -> list[dict]:
    return [
        {"id": "ps_i2c_1", "type": "i2c", "instance": "XPAR_PSU_I2C_1", "base_address": "0xFF030000", "driver": "XIicPs", "zone": "ps", "source": "xsa"},
        {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_PSU_I2C_0", "base_address": "0xFF020000", "driver": "XIicPs", "zone": "ps", "source": "xsa"},
        {"id": "ps_eth_0", "type": "eth", "instance": "XPAR_PSU_ETHERNET_3", "base_address": "0xFF0E0000", "driver": "XEmacPs", "zone": "ps", "source": "xsa"},
        {"id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0", "base_address": "0xA0000000", "driver": "XIic", "zone": "pl", "source": "xsa"},
    ]


class SdtInstanceTests(unittest.TestCase):
    def test_classic_keeps_label_names(self) -> None:
        names = sdt_controller_instances({"project": {}, "controllers": _controllers()})
        self.assertEqual(names["ps_i2c_0"], "XPAR_PSU_I2C_0")
        self.assertEqual(names["ps_eth_0"], "XPAR_PSU_ETHERNET_3")

    def test_sdt_uses_canonical_driver_ordinals(self) -> None:
        spec = {"project": {"bsp_flow": "sdt"}, "controllers": _controllers()}
        names = sdt_controller_instances(spec)
        self.assertEqual(names["ps_i2c_0"], "XPAR_XIICPS_0")   # taban adres sirasi: 0xFF020000 once
        self.assertEqual(names["ps_i2c_1"], "XPAR_XIICPS_1")
        self.assertEqual(names["ps_eth_0"], "XPAR_XEMACPS_0")  # tek GEM etkin -> indeks 0 (psu_ethernet_3 olsa da)
        self.assertEqual(names["pl_i2c_0"], "XPAR_AXI_IIC_0")  # PL etiketi SDT'de de var
        rewritten = with_sdt_instances(spec)
        self.assertEqual([c["instance"] for c in rewritten["controllers"]],
                         ["XPAR_XIICPS_1", "XPAR_XIICPS_0", "XPAR_XEMACPS_0", "XPAR_AXI_IIC_0"])
        self.assertEqual(spec["controllers"][0]["instance"], "XPAR_PSU_I2C_1")  # orijinal degismez


class SdtZynqmpCodegenTests(unittest.TestCase):
    def _generate(self, spec: dict) -> dict[str, str]:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            codegen.generate(spec, out)
            return {str(p.relative_to(out)).replace("\\", "/"): p.read_text(encoding="utf-8", errors="replace")
                    for p in out.rglob("*") if p.suffix in (".c", ".h")}

    def test_sdt_zynqmp_uart_agent_with_ps_eth_telnet(self) -> None:
        spec = load_sample_spec("sdt_zu")
        spec["project"]["bsp_flow"] = "sdt"
        spec["project"]["runtime"] = "bare_metal"  # RAW mod: sys_now() uretilmeli
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        add_zynqmp_ps_ethernet(spec)
        files = self._generate(spec)
        joined = "\n".join(files.values())
        self.assertNotIn("XPAR_PSU_", joined, "SDT'de PS etiket adlari (XPAR_PSU_*) kullanilmamali")
        self.assertRegex(joined, r"XPAR_XIICPS_\d_BASEADDR")
        net_c = files.get("tests/spec2code_testbench_lwip_net.c", "")
        self.assertIn("XPAR_XEMACPS_0_BASEADDR", net_c)
        self.assertIn("#define SPEC2CODE_TESTBENCH_IP_ADDR0 18U", net_c)
        self.assertIn("#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR3 1U", net_c)
        # Telnet (sys_timeout) RAW modda sys_now() ister: uretilen zaman kaynagi dosyasi.
        time_c = files.get("tests/spec2code_lwip_time.c", "")
        self.assertIn("u32_t sys_now(void)", time_c)
        self.assertIn("XTime_GetTime((XTime*)&ullNow);", time_c)
        self.assertIn('#include "xiltimer.h"', time_c)   # SDT: xtime_l.h yok
        self.assertNotIn("xtime_l.h", time_c)

    def test_freertos_socket_mode_does_not_emit_sys_now(self) -> None:
        spec = load_sample_spec("rtos_zu")
        spec["project"]["runtime"] = "freertos"
        spec["project"]["testbench_transport"] = "eth"
        add_zynqmp_ps_ethernet(spec)
        files = self._generate(spec)
        self.assertNotIn("tests/spec2code_lwip_time.c", files)  # sys_arch.c sys_now'i verir

    def test_classic_zynqmp_telnet_net_has_ip_defines(self) -> None:
        spec = load_sample_spec("classic_zu")
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        add_zynqmp_ps_ethernet(spec)
        files = self._generate(spec)
        net_c = files.get("tests/spec2code_testbench_lwip_net.c", "")
        self.assertIn("#define SPEC2CODE_TESTBENCH_IP_ADDR0 18U", net_c)
        self.assertIn("#define SPEC2CODE_TESTBENCH_ETH_BASEADDR XPAR_XEMACPS_0_BASEADDR", net_c)
        if "tests/spec2code_lwip_time.c" in files:   # bare-metal: klasik BSP xtime_l.h
            self.assertIn('#include "xtime_l.h"', files["tests/spec2code_lwip_time.c"])


if __name__ == "__main__":
    unittest.main()
