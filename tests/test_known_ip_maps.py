"""Register haritasi bilinen IP'ler (JESD204C v4.x): dokuman, XSA tanima, kod uretimi, shell tablosu."""

from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import ip_register_maps, register_map  # noqa: E402
from backend.parsers.xsa import parse_xsa  # noqa: E402
from orchestrator import codegen  # noqa: E402
from tests.test_testbench import add_zynqmp_ps_uart, load_sample_spec  # noqa: E402

_HWH = """<?xml version="1.0" encoding="UTF-8"?>
<EDKSYSTEM EDWVERSION="1.2">
  <MODULES>
    <MODULE FULLNAME="/psu_cortexa53_0" INSTANCE="psu_cortexa53_0" MODTYPE="psu_cortexa53" IPTYPE="PROCESSOR"/>
    <MODULE FULLNAME="/psu_i2c_0" INSTANCE="psu_i2c_0" MODTYPE="psu_i2c" IPTYPE="PERIPHERAL">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xFF020000" HIGHVALUE="0xFF02FFFF"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/jesd204c_rx" INSTANCE="jesd204c_rx" MODTYPE="jesd204c" IPTYPE="PERIPHERAL" VLNV="xilinx.com:ip:jesd204c:4.2">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xA0000000" HIGHVALUE="0xA000FFFF" MEMTYPE="REGISTER" SLAVEBUSINTERFACE="S_AXI"/></MEMORYMAP>
      <PARAMETERS><PARAMETER NAME="C_LANES" VALUE="2"/><PARAMETER NAME="C_NODE_IS_TRANSMIT" VALUE="0"/><PARAMETER NAME="C_SUBCLASS" VALUE="1"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/jesd204c_tx" INSTANCE="jesd204c_tx" MODTYPE="jesd204c" IPTYPE="PERIPHERAL" VLNV="xilinx.com:ip:jesd204c:4.2">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xA0010000" HIGHVALUE="0xA001FFFF" MEMTYPE="REGISTER" SLAVEBUSINTERFACE="S_AXI"/></MEMORYMAP>
      <PARAMETERS><PARAMETER NAME="C_LANES" VALUE="4"/><PARAMETER NAME="C_NODE_IS_TRANSMIT" VALUE="1"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/axi_timer_0" INSTANCE="axi_timer_0" MODTYPE="axi_timer" IPTYPE="PERIPHERAL" VLNV="xilinx.com:ip:axi_timer:2.0">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xA0020000" HIGHVALUE="0xA002FFFF" MEMTYPE="REGISTER"/></MEMORYMAP>
    </MODULE>
  </MODULES>
</EDKSYSTEM>
"""
PLATFORM = {"family_zone": {"ps": "ps", "pl": "pl"}, "default_zone": "ps"}


class KnownIpDocumentTests(unittest.TestCase):
    def test_defaults_and_parameter_normalization(self) -> None:
        self.assertEqual(ip_register_maps.normalize_jesd204c_parameters(None),
                         {"lanes": 4, "direction": "rx", "link_layer": "64b66b", "subclass": 1})
        params = ip_register_maps.normalize_jesd204c_parameters(
            {"C_LANES": "2", "C_NODE_IS_TRANSMIT": "1", "C_SUBCLASS": "2", "C_LINK_LAYER": "8B10B"})
        self.assertEqual(params, {"lanes": 2, "direction": "tx", "link_layer": "8b10b", "subclass": 2})
        # gecersiz degerler varsayilani bozmaz
        params = ip_register_maps.normalize_jesd204c_parameters({"lanes": "99", "direction": "sideways", "subclass": "7"})
        self.assertEqual(params["lanes"], 4)
        self.assertEqual(params["direction"], "rx")
        self.assertEqual(params["subclass"], 1)

    def test_rx_document_is_valid_contiguous_and_has_lane_blocks(self) -> None:
        doc = ip_register_maps.jesd204c_document(name="jesd204c_rx", base_address="0xA0000000",
                                                 parameters={"lanes": 2, "direction": "rx"})
        self.assertEqual(register_map.validate_register_document(doc), [])
        regs = doc["maps"][0]["registers"]
        names = [r["name"] for r in regs]
        for expected in ("IP_VERSION", "IP_CONFIG", "RESET", "STAT_STATUS", "CTRL_IRQ", "CTRL_RX_BUF_ADV",
                         "STAT_LOCK_DEBUG", "L0_STAT_RX_BUF_LVL", "L1_STAT_RX_ERROR_CNT0", "L1_RX_ILA_CFG3", "L1_CTRL_RX_GT"):
            self.assertIn(expected, names)
        self.assertNotIn("L2_STAT_RX_BUF_LVL", names)          # yalniz 2 lane
        self.assertNotIn("CTRL_TX_ILA_CFG0", names)            # TX'e ozgu yok
        self.assertNotIn("STAT_RX_ERR", names)                 # 8B/10B'ye ozgu yok
        # her gercek register 4 bayt: bosluklar reserved dolgu ile kapali
        widths = register_map._register_widths(register_map._sorted_registers(doc["maps"][0]))
        for reg, width in zip(register_map._sorted_registers(doc["maps"][0]), widths):
            if not reg.get("reserved"):
                self.assertEqual(width, 4, reg["name"])
        by_name = {r["name"]: r for r in regs}
        self.assertEqual(by_name["L1_CTRL_RX_GT"]["offset"], "0x4E4")
        self.assertEqual([f["bits"] for f in by_name["STAT_STATUS"]["fields"]][:3], ["15", "14", "13"])

    def test_tx_document_has_tx_registers(self) -> None:
        doc = ip_register_maps.jesd204c_document(name="jesd204c_tx", base_address="0xA0010000",
                                                 parameters={"lanes": 4, "direction": "tx"})
        self.assertEqual(register_map.validate_register_document(doc), [])
        names = [r["name"] for r in doc["maps"][0]["registers"]]
        for expected in ("CTRL_ENABLE", "CTRL_TX_ILA_CFG0", "CTRL_TX_ILA_CFG4", "L3_CTRL_TX_ILA_LID", "L3_CTRL_TX_GT"):
            self.assertIn(expected, names)
        self.assertNotIn("L0_STAT_RX_BUF_LVL", names)
        files = register_map.generate_files(doc)
        self.assertIn("jesd204c_tx_regs.h", files)
        self.assertIn("JESD204C_TX_BASE_ADDRESS", files["jesd204c_tx_regs.h"])
        self.assertIn("shellUserJesd204cTx", files["jesd204c_tx_shell.c"])

    def test_known_ip_key_matching(self) -> None:
        self.assertEqual(ip_register_maps.known_ip_key("xilinx.com:ip:jesd204c:4.2", "jesd204c"), "jesd204c")
        self.assertEqual(ip_register_maps.known_ip_key("", "jesd204c_1"), "jesd204c")
        self.assertIsNone(ip_register_maps.known_ip_key("xilinx.com:ip:axi_timer:2.0", "axi_timer"))
        self.assertIsNone(ip_register_maps.known_ip_key("user.org:user:jesd_like_thing:1.0", "jesd_like_thing"))


class KnownIpXsaTests(unittest.TestCase):
    def test_xsa_recognizes_jesd204c_with_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "jesd.xsa"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("design_1.hwh", _HWH)
                archive.writestr("sysdef.xml", "<xml/>")
            result = parse_xsa(path, PLATFORM)
        ips = {ip["id"]: ip for ip in result.custom_ips}
        self.assertEqual(sorted(ips), ["jesd204c_rx", "jesd204c_tx"])  # axi_timer (standart) girmez
        self.assertEqual(ips["jesd204c_rx"]["register_map"], "jesd204c")
        self.assertEqual(ips["jesd204c_rx"]["ip_parameters"], {"lanes": 2, "direction": "rx", "link_layer": "64b66b", "subclass": 1})
        self.assertEqual(ips["jesd204c_tx"]["ip_parameters"]["direction"], "tx")
        self.assertEqual(ips["jesd204c_tx"]["base_address"], "0xA0010000")


class KnownIpCodegenTests(unittest.TestCase):
    def test_generate_writes_ip_drivers_and_shell_rows(self) -> None:
        spec = load_sample_spec("jesd_gen")
        spec["project"]["testbench_transport"] = "uart"
        add_zynqmp_ps_uart(spec)
        spec["custom_ips"] = [
            {"id": "jesd204c_rx", "instance": "XPAR_JESD204C_RX", "ip_name": "jesd204c", "base_address": "0xA0000000",
             "high_address": "0xA000FFFF", "register_count": 16384, "register_map": "jesd204c",
             "ip_parameters": {"lanes": 4, "direction": "rx", "link_layer": "64b66b", "subclass": 1}},
            {"id": "pl_blob_0", "base_address": "0xA0100000", "register_count": 8},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            codegen.generate(spec, out)
            ip_dir = out / "drivers" / "ip"
            self.assertTrue((ip_dir / "jesd204c_rx_regs.h").is_file())
            self.assertTrue((ip_dir / "jesd204c_rx.c").is_file())
            self.assertTrue((ip_dir / "jesd204c_rx_shell.c").is_file())
            self.assertFalse((ip_dir / "pl_blob_0_regs.h").exists())
            header = (ip_dir / "jesd204c_rx_regs.h").read_text(encoding="utf-8")
            self.assertIn("JESD204C_RX_BASE_ADDRESS", header)
            self.assertIn("0xA0000000", header)
            self.assertIn("L3_", header)
            shell = (out / "shell" / "shell_user_commands.c").read_text(encoding="utf-8")
            self.assertIn('#include "jesd204c_rx_shell.h"', shell)
            self.assertIn('{"ip_jesd204c_rx", shellUserJesd204cRx,', shell)
            self.assertIn('{"pl_blob_0", shellUserPlBlob0,', shell)   # generic dump/read/write kalir
            # bilinen IP icin generic `<id> dump|read|write` uretilmez (isleyici adi haritayla cakisirdi)
            self.assertNotIn('{"jesd204c_rx",', shell)
            self.assertEqual(shell.count("shellUserJesd204cRx("), 0)  # tanimi drivers/ip'te, burada yalniz tablo satiri
            readme = (out / "README.md").read_text(encoding="utf-8")
            self.assertIn("ip_jesd204c_rx", readme)


if __name__ == "__main__":
    unittest.main()
