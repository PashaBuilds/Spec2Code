import tempfile
import unittest
import zipfile
from pathlib import Path

from backend.parsers.xsa import XsaParseError, parse_xsa, safe_xsa_filename

VITIS_FIXED = Path(r"C:\Xilinx_2023_2\Vitis\2023.2\data\embeddedsw\lib\fixed_hwplatforms")
PLATFORM = {"family_zone": {"ps": "ps", "pl": "pl"}, "default_zone": "ps"}

_SYNTH_HWH = """<?xml version="1.0" encoding="UTF-8"?>
<EDKSYSTEM EDWVERSION="1.2">
  <MODULES>
    <MODULE FULLNAME="/psu_cortexa53_0" INSTANCE="psu_cortexa53_0" MODTYPE="psu_cortexa53" IPTYPE="PROCESSOR"/>
    <MODULE FULLNAME="/psu_i2c_0" INSTANCE="psu_i2c_0" MODTYPE="psu_i2c" IPTYPE="PERIPHERAL">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xFF020000" HIGHVALUE="0xFF02FFFF"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/psu_uart_1" INSTANCE="psu_uart_1" MODTYPE="psu_uart" IPTYPE="PERIPHERAL">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xFF010000" HIGHVALUE="0xFF01FFFF"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/psu_qspi_0" INSTANCE="psu_qspi_0" MODTYPE="psu_qspi" IPTYPE="PERIPHERAL">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xFF0F0000" HIGHVALUE="0xFF0FFFFF"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/mem_pcie_intr_0" INSTANCE="mem_pcie_intr_0" MODTYPE="mem_pcie_intr" IPTYPE="PERIPHERAL" VLNV="user.org:user:mem_pcie_intr:1.0">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xA0000000" HIGHVALUE="0xA000FFFF" MEMTYPE="REGISTER" SLAVEBUSINTERFACE="S00_AXI"/></MEMORYMAP>
      <PARAMETERS><PARAMETER NAME="C_S00_AXI_ADDR_WIDTH" VALUE="4"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/pl_blob_0" INSTANCE="pl_blob_0" MODTYPE="pl_blob" IPTYPE="PERIPHERAL" VLNV="user.org:user:pl_blob:1.0">
      <MEMORYMAP><MEMRANGE BASEVALUE="0xA0010000" HIGHVALUE="0xA00100FF" MEMTYPE="REGISTER"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/lmb_bram_0" INSTANCE="lmb_bram_0" MODTYPE="lmb_bram_if_cntlr" IPTYPE="PERIPHERAL">
      <MEMORYMAP><MEMRANGE BASEVALUE="0x00000000" HIGHVALUE="0x0003FFFF" MEMTYPE="MEMORY"/></MEMORYMAP>
    </MODULE>
    <MODULE FULLNAME="/real_ip_0" INSTANCE="real_ip_0" MODTYPE="real_ip" IPTYPE="PERIPHERAL" VLNV="user.org:user:real_ip:1.0">
      <ADDRESSBLOCKS><ADDRESSBLOCK INTERFACE="S00_AXI" NAME="S00_AXI_reg" RANGE="4096" USAGE="register"/></ADDRESSBLOCKS>
      <PARAMETERS><PARAMETER NAME="C_S00_AXI_ADDR_WIDTH" VALUE="6"/><PARAMETER NAME="C_S00_AXI_BASEADDR" VALUE="0xA0020000"/><PARAMETER NAME="C_S00_AXI_HIGHADDR" VALUE="0xA002FFFF"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/lmb_bram_2" INSTANCE="lmb_bram_2" MODTYPE="lmb_bram_if_cntlr" IPTYPE="PERIPHERAL" MODCLASS="MEMORY_CNTLR">
      <PARAMETERS><PARAMETER NAME="C_BASEADDR" VALUE="0x00000000"/><PARAMETER NAME="C_HIGHADDR" VALUE="0x0003FFFF"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/axi_timer_0" INSTANCE="axi_timer_0" MODTYPE="axi_timer" IPTYPE="PERIPHERAL" VLNV="xilinx.com:ip:axi_timer:2.0">
      <ADDRESSBLOCKS><ADDRESSBLOCK INTERFACE="S_AXI" NAME="Reg" RANGE="65536" USAGE="register"/></ADDRESSBLOCKS>
      <PARAMETERS><PARAMETER NAME="C_BASEADDR" VALUE="0x41C00000"/><PARAMETER NAME="C_HIGHADDR" VALUE="0x41C0FFFF"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/lmb_bram_1" INSTANCE="lmb_bram_1" MODTYPE="lmb_bram_if_cntlr" IPTYPE="PERIPHERAL">
      <ADDRESSBLOCKS><ADDRESSBLOCK INTERFACE="SLMB" NAME="Mem" RANGE="8192" USAGE="memory"/></ADDRESSBLOCKS>
      <PARAMETERS><PARAMETER NAME="C_BASEADDR" VALUE="0x00000000"/><PARAMETER NAME="C_HIGHADDR" VALUE="0x0003FFFF"/></PARAMETERS>
    </MODULE>
    <MODULE FULLNAME="/proc_sys_reset_0" INSTANCE="proc_sys_reset_0" MODTYPE="proc_sys_reset" IPTYPE="RESET"/>
  </MODULES>
</EDKSYSTEM>
"""


def _write_synthetic_xsa(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("design_1.hwh", _SYNTH_HWH)
        archive.writestr("sysdef.xml", "<xml/>")


class SyntheticXsaTests(unittest.TestCase):
    def test_parses_controllers_platform_and_custom_ip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xsa = Path(tmp) / "synth.xsa"
            _write_synthetic_xsa(xsa)
            result = parse_xsa(xsa, PLATFORM)

        self.assertEqual(result.platform, "zynq_ultrascale")
        self.assertEqual(result.processors, ["psu_cortexa53_0"])

        by_type = {item["type"]: item for item in result.controllers}
        self.assertEqual(set(by_type), {"i2c", "uart", "qspi"})
        self.assertEqual(by_type["i2c"]["driver"], "XIicPs")
        self.assertEqual(by_type["i2c"]["instance"], "XPAR_PSU_I2C_0")
        self.assertEqual(by_type["i2c"]["base_address"], "0xFF020000")
        self.assertEqual(by_type["i2c"]["id"], "ps_i2c_0")
        self.assertEqual(by_type["uart"]["driver"], "XUartPs")
        self.assertEqual(by_type["qspi"]["driver"], "XQspiPsu")
        # The custom AXI IP surfaces as unmatched, not silently dropped.
        self.assertEqual(len(result.unmatched), 7)
        self.assertIn("mem_pcie_intr", result.unmatched[0]["reason"])
        self.assertEqual(result.unmatched[0]["base_address"], "0xA0000000")
        # REGISTER tipli custom IP'ler custom_ips'e girer (MEMORY tipli LMB BRAM girmez);
        # register_count ADDR_WIDTH'ten (4 bit -> 16 B -> 4 reg), yoksa HIGH-BASE+1 / 4 (256 B -> 64).
        # Gercek hwh'de MEMRANGE islemci altindadir: modul parametreleri (C_<IF>_BASEADDR/HIGHADDR)
        # + ADDRESSBLOCK USAGE ile cozulur (real_ip_0: 6 bit -> 16 reg); USAGE=memory (lmb_bram_1) ve
        # MODCLASS=MEMORY_CNTLR (lmb_bram_2, ADDRESSBLOCK'suz ILMB) ve standart Xilinx IP
        # (axi_timer_0, VLNV xilinx.com:ip) girmez - surucusu BSP'dedir, shell komutu uretilmez.
        self.assertEqual([ip["id"] for ip in result.custom_ips], ["mem_pcie_intr_0", "pl_blob_0", "real_ip_0"])
        self.assertEqual((result.custom_ips[2]["base_address"], result.custom_ips[2]["register_count"]), ("0xA0020000", 16))
        pcie = result.custom_ips[0]
        self.assertEqual((pcie["instance"], pcie["ip_name"]), ("XPAR_MEM_PCIE_INTR_0", "mem_pcie_intr"))
        self.assertEqual((pcie["base_address"], pcie["high_address"], pcie["register_count"]), ("0xA0000000", "0xA000FFFF", 4))
        self.assertEqual(result.custom_ips[1]["register_count"], 64)

    def test_hdf_parses_like_xsa(self) -> None:
        # Eski SDK handoff'u (.hdf) ayni kap bicimidir: zip icinde .hwh.
        # Setup artik .xsa yaninda .hdf de kabul eder; parser ayni yoldan
        # okur (Vitis workspace adimi ise .xsa'ya kapilidir).
        with tempfile.TemporaryDirectory() as tmp:
            hdf = Path(tmp) / "legacy_export.hdf"
            _write_synthetic_xsa(hdf)
            result = parse_xsa(hdf, PLATFORM)

        self.assertEqual(result.platform, "zynq_ultrascale")
        self.assertEqual({item["type"] for item in result.controllers}, {"i2c", "uart", "qspi"})

    def test_rejects_non_zip_and_hwhless_archives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            not_zip = Path(tmp) / "bad.xsa"
            not_zip.write_text("this is not a zip")
            with self.assertRaises(XsaParseError):
                parse_xsa(not_zip)

            empty = Path(tmp) / "empty.xsa"
            with zipfile.ZipFile(empty, "w") as archive:
                archive.writestr("readme.txt", "no hwh here")
            with self.assertRaises(XsaParseError):
                parse_xsa(empty)

    def test_safe_xsa_filename(self) -> None:
        self.assertEqual(safe_xsa_filename("my board (rev2).xsa"), "my_board_rev2_.xsa")
        self.assertEqual(safe_xsa_filename("../../etc/passwd"), "passwd.xsa")
        self.assertEqual(safe_xsa_filename(""), "design.xsa")
        # .hdf yuklemesi uzantisini korur (design.hdf.xsa'ya donusmez).
        self.assertEqual(safe_xsa_filename("board export.hdf"), "board_export.hdf")


@unittest.skipUnless(VITIS_FIXED.is_dir(), "Vitis fixed platforms not installed")
class RealXsaTests(unittest.TestCase):
    def test_vck190_detects_versal_with_psv_drivers(self) -> None:
        result = parse_xsa(VITIS_FIXED / "vck190.xsa", PLATFORM)
        self.assertEqual(result.platform, "versal")
        drivers = {item["type"]: item["driver"] for item in result.controllers}
        self.assertEqual(drivers.get("uart"), "XUartPsv")
        self.assertEqual(drivers.get("i2c"), "XIicPs")
        self.assertEqual(drivers.get("qspi"), "XQspiPsu")

    def test_zc702_detects_zynq7000(self) -> None:
        result = parse_xsa(VITIS_FIXED / "zc702.xsa", PLATFORM)
        self.assertEqual(result.platform, "zynq_7000")
        drivers = {item["type"]: item["driver"] for item in result.controllers}
        self.assertEqual(drivers.get("uart"), "XUartPs")
        self.assertEqual(drivers.get("i2c"), "XIicPs")

    def test_zcu102_detects_zynqmp_with_ethernet(self) -> None:
        result = parse_xsa(VITIS_FIXED / "zcu102.xsa", PLATFORM)
        self.assertEqual(result.platform, "zynq_ultrascale")
        types = {item["type"] for item in result.controllers}
        self.assertIn("eth", types)
        self.assertIn("i2c", types)


if __name__ == "__main__":
    unittest.main()
