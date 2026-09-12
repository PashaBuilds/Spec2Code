"""project.testbench_network: lwIP ajaninin statik ag ayarlari (header makrolari, manifest, dogrulama)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import cmodel, codegen  # noqa: E402
from tests.test_testbench import add_microblaze_ethernetlite, load_sample_spec  # noqa: E402


def _eth_spec(name: str, network: dict | None) -> dict:
    spec = load_sample_spec(name)
    spec["project"].update({"platform": "microblaze_7series", "target_core": "microblaze_0",
                            "runtime": "bare_metal", "testbench_transport": "eth"})
    if network is not None:
        spec["project"]["testbench_network"] = network
    add_microblaze_ethernetlite(spec)
    return spec


def _generate(spec: dict) -> tuple[str, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        codegen.generate(spec, out)
        header = (out / "tests" / "spec2code_testbench_lwip.h").read_text(encoding="utf-8")
        manifest = json.loads((out / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
    return header, manifest


class TestbenchNetworkTests(unittest.TestCase):
    def test_defaults_when_field_absent(self) -> None:
        header, manifest = _generate(_eth_spec("net_default", None))
        self.assertIn("#define SPEC2CODE_TESTBENCH_IP_ADDR0 18U", header)
        self.assertIn("#define SPEC2CODE_TESTBENCH_IP_ADDR3 121U", header)
        self.assertIn("#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR3 1U", header)
        self.assertIn("#define SPEC2CODE_TESTBENCH_MAC1 0x0AU", header)
        self.assertIn("#define SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT 5000U", header)
        self.assertEqual(manifest["network"], {"ip": "18.2.75.121", "netmask": "255.255.255.0",
                                               "gateway": "18.2.75.1", "mac": "00:0A:35:00:01:02", "port": 5000})

    def test_custom_network_reaches_header_and_manifest(self) -> None:
        network = {"ip": "169.254.112.1", "netmask": "255.255.0.0", "gateway": "169.254.112.159",
                   "mac": "02-11-22-33-44-55", "port": 6001}
        header, manifest = _generate(_eth_spec("net_custom", network))
        for macro, value in (("IP_ADDR0", "169U"), ("IP_ADDR1", "254U"), ("IP_ADDR2", "112U"), ("IP_ADDR3", "1U"),
                             ("NETMASK_ADDR2", "0U"), ("GATEWAY_ADDR3", "159U"), ("MAC0", "0x02U"), ("MAC5", "0x55U"),
                             ("TCP_DEFAULT_PORT", "6001U")):
            self.assertIn(f"#define SPEC2CODE_TESTBENCH_{macro} {value}", header)
        self.assertEqual(manifest["network"]["ip"], "169.254.112.1")
        self.assertEqual(manifest["network"]["mac"], "02:11:22:33:44:55")
        self.assertEqual(manifest["network"]["port"], 6001)

    def test_partial_network_keeps_defaults_for_missing_fields(self) -> None:
        header, manifest = _generate(_eth_spec("net_partial", {"ip": "10.0.0.7", "port": ""}))
        self.assertIn("#define SPEC2CODE_TESTBENCH_IP_ADDR0 10U", header)
        self.assertIn("#define SPEC2CODE_TESTBENCH_GATEWAY_ADDR0 18U", header)
        self.assertEqual(manifest["network"]["port"], 5000)

    def test_invalid_values_raise_codegen_error(self) -> None:
        for network, code in (({"ip": "300.1.1.1"}, "NET-001"), ({"mac": "00:0A:35"}, "NET-002"),
                              ({"mac": "01:00:5E:00:00:01"}, "NET-003"), ({"port": 70000}, "NET-004")):
            with self.subTest(network=network):
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(cmodel.CodegenError) as ctx:
                        codegen.generate(_eth_spec("net_bad", network), Path(tmp))
                self.assertIn(code, str(ctx.exception))

    def test_uart_agent_manifest_has_no_network_block(self) -> None:
        spec = load_sample_spec("net_uart")
        from tests.test_testbench import add_zynqmp_ps_uart
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        with tempfile.TemporaryDirectory() as tmp:
            codegen.generate(spec, Path(tmp))
            manifest = json.loads((Path(tmp) / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("network", manifest)


if __name__ == "__main__":
    unittest.main()
