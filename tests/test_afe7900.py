"""AFE7900 (TI AFE79xx C API) surucu uretimi + JESD204C baglanti modulu (orchestrator/afe79.py)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from orchestrator import afe79, cmodel, codegen, descriptor_check  # noqa: E402
import yaml  # noqa: E402

WORDS = "\n".join(f"0x{0x11223344 + i:08X}," for i in range(12))


def _spec(*, jesd: str | None = "64b66b", words: str = WORDS, driver: str = "XSpiPs") -> dict:
    controller = {"id": "spi0", "type": "spi", "driver": driver, "zone": "ps" if driver == "XSpiPs" else "pl",
                  "instance": "XPAR_PSU_SPI_1" if driver == "XSpiPs" else "XPAR_AXI_QUAD_SPI_0",
                  "base_address": "0xFF050000", "source": "xparameters"}
    spec = {
        "project": {"name": "unit_afe", "platform": "zynq_ultrascale", "target_core": "a53_0",
                    "runtime": "bare_metal", "output_mode": "dropin", "testbench_transport": "uart",
                    "bsp_flow": "classic"},
        "controllers": [controller],
        "devices": [{"id": "afe0", "part": "AFE7900", "descriptor_ref": "descriptors/afe7900.yaml",
                     "attach": {"controller_id": "spi0", "spi_chip_select": 2},
                     "config": {"afe_config_words": words, "log_level": 1, "tdd_override": False},
                     "tests_requested": ["self_test"]}],
        "custom_ips": [],
    }
    if jesd:
        for direction, base in (("rx", "0xA0000000"), ("tx", "0xA0010000")):
            spec["custom_ips"].append({
                "id": f"jesd204c_{direction}", "instance": f"XPAR_JESD204C_{direction.upper()}",
                "ip_name": "jesd204c", "base_address": base, "register_count": 16384,
                "register_map": "jesd204c",
                "ip_parameters": {"lanes": 4, "direction": direction, "link_layer": jesd, "subclass": 1}})
    return spec


class Afe7900GenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="afe7900_"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _generate(self, spec: dict) -> dict[str, str]:
        written = codegen.generate(spec, self.tmp)
        return {Path(p).relative_to(self.tmp).as_posix(): Path(p).read_text(encoding="utf-8", errors="replace")
                for p in written}

    def test_parse_config_words_one_word_per_line_no_byte_grouping(self) -> None:
        self.assertEqual(afe79.parse_config_words("0x11223344,\n0x55667788,\n0x99AABBCC,"),
                         [0x11223344, 0x55667788, 0x99AABBCC])
        self.assertEqual(afe79.parse_config_words(["0x1", 2]), [1, 2])
        self.assertEqual(afe79.parse_config_words(""), [])

    def test_descriptor_is_valid_and_vendor_steps_accepted(self) -> None:
        doc = yaml.safe_load((ROOT / "descriptors" / "afe7900.yaml").read_text(encoding="utf-8"))
        self.assertEqual(descriptor_check.validate_descriptor(doc), [])
        bad = {**doc, "vendor_api": "other"}
        self.assertTrue(any("vendor_api" in e for e in descriptor_check.validate_descriptor(bad)))

    def test_generates_driver_vendor_copy_config_and_jesdlink_64b66b(self) -> None:
        files = self._generate(_spec())
        self.assertIn("drivers/afe7900.c", files)
        self.assertIn("drivers/afe7900.h", files)
        self.assertIn("drivers/afe7900_config.c", files)
        self.assertIn("drivers/vendor/afe79xx/Src/tiAfe79_baseFunc.c", files)
        self.assertIn("drivers/vendor/afe79xx/Include/tiAfe79_allInclude.h", files)
        self.assertIn("drivers/vendor/afe79xx/Src/tiAfe79_init.c", files)
        self.assertIn("drivers/ip/jesdlink.c", files)
        driver = files["drivers/afe7900.c"]
        self.assertIn("AFE79FNP(afeDeviceBringupFromMem)(spDevice, 0U, 0U)", driver)
        self.assertIn("int afe7900JesdLinkBringup(XSpiPs* spSpi, unsigned short* uspStatus)", driver)
        # bring-up sirasi: reset ver -> AFE init -> reset kaldir -> AFE JESD reset/senkron -> FPGA RX bekle
        order = [driver.index("jesdLinkCoreReset(JESDLINK_TX_BASE, 1U)"), driver.index("afe7900DeviceInit(spSpi);\n"),
                 driver.index("jesdLinkCoreReset(JESDLINK_TX_BASE, 0U)"), driver.index("afe7900JesdResetToggle(spSpi)"),
                 driver.index("jesdLinkLinkReset(JESDLINK_RX_BASE)"),
                 driver.index("jesdLinkRxLinkWait(JESDLINK_LINK_TIMEOUT_MS)")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("sdtm", driver.lower())
        self.assertNotIn("uint8_t", driver)
        # wrapper fonksiyon tablolarini tanimlayan sablon baslik yalniz TI init.c'de dahil edilebilir
        self.assertNotIn("tiAfe79_allInclude.h", driver)
        self.assertIn('#include "tiAfe79_jesd.h"', driver)
        header = files["drivers/afe7900.h"]
        self.assertIn("#define AFE7900_SPI_SELECT 2U", header)
        self.assertIn("#define AFE7900_LOG_LEVEL 1U", header)
        self.assertIn("#define AFE7900_TDD_OVERRIDE FALSE", header)
        config = files["drivers/afe7900_config.c"]
        self.assertIn("0x11223344U, 0x11223345U", config)
        self.assertIn("#define AFE7900_CONFIG_WORD_COUNT 12U", files["drivers/afe7900_config.h"])
        bridge = files["drivers/vendor/afe79xx/Src/tiAfe79_baseFunc.c"]
        self.assertIn("afe7900HalSpiWrite(afeInst->halConfig, addr, data)", bridge)
        self.assertIn("*numWordsActuallyRead = 0xffffffff", bridge)
        link = files["drivers/ip/jesdlink.c"]
        self.assertIn("JESDLINK_STAT_SH_LOCK | JESDLINK_STAT_MB_LOCK", link)
        self.assertNotIn("JESDLINK_STAT_CGS", link)
        self.assertNotIn("#ifdef", link)
        link_h = files["drivers/ip/jesdlink.h"]
        self.assertIn("#define JESDLINK_RX_BASE 0xA0000000U", link_h)
        self.assertIn("#define JESDLINK_TX_BASE 0xA0010000U", link_h)
        self.assertIn("#define JESDLINK_ENCODING_64B66B TRUE", link_h)
        # reset kaldirma: reset/GT mesgul bitleri timeout ile beklenir
        self.assertIn("JESDLINK_RESET_BIT | JESDLINK_RESET_CORE_STATE | JESDLINK_RESET_GT_BUSY", link)
        self.assertIn("JESDLINK_RESET_TIMEOUT_MS", link)
        # SAHA KV260: RESET[0] seviye biti -> kaldirma 0 yazar; veri/komut yolu acilir
        self.assertIn("jesdLinkWrite(uiBase, JESDLINK_REG_CTRL_ENABLE, JESDLINK_CTRL_ENABLE_CMD_DATA);", link)
        self.assertIn("jesdLinkWrite(uiBase, JESDLINK_REG_RESET, jesdLinkRead(uiBase, JESDLINK_REG_RESET) & JESDLINK_RESET_TYPE_LINK);", link)
        # link reset: RESET_TYPE=1 ile GT korunur, cikis kriteri tam resetle ayni
        self.assertIn("JESDLINK_RESET_TYPE_LINK | JESDLINK_RESET_BIT", link)
        # self-test HAL fonksiyonlarini cagirmaz
        test = files["tests/afe7900_test.c"]
        self.assertIn("afe7900TemperatureRead(spSpi, &iValue)", test)
        self.assertNotIn("afe7900HalSpiRead", test)
        manifest = json.loads(files["tests/spec2code_testbench_manifest.json"])
        ops = [op["name"] for op in manifest["devices"][0]["operations"]]
        self.assertIn("jesd_link_bringup", ops)
        self.assertIn("pll_lock_read", ops)

    def test_8b10b_uses_cgs_and_rx_err_register(self) -> None:
        files = self._generate(_spec(jesd="8b10b"))
        link = files["drivers/ip/jesdlink.c"]
        self.assertIn("JESDLINK_STAT_SYNC | JESDLINK_STAT_CGS | JESDLINK_STAT_RX_STARTED", link)
        self.assertIn("JESDLINK_STAT_ALIGN_ERROR", link)
        self.assertIn("JESDLINK_REG_STAT_RX_ERR", link)
        self.assertNotIn("JESDLINK_STAT_SH_LOCK", link)
        self.assertIn("#define JESDLINK_ENCODING_64B66B FALSE", files["drivers/ip/jesdlink.h"])

    def test_without_jesd_ip_no_link_ops_and_no_jesdlink(self) -> None:
        files = self._generate(_spec(jesd=None))
        self.assertNotIn("drivers/ip/jesdlink.c", files)
        self.assertNotIn("jesdLinkBringup", files["drivers/afe7900.c"])
        self.assertNotIn('#include "jesdlink.h"', files["drivers/afe7900.c"])
        manifest = json.loads(files["tests/spec2code_testbench_manifest.json"])
        ops = [op["name"] for op in manifest["devices"][0]["operations"]]
        self.assertNotIn("jesd_link_bringup", ops)
        self.assertNotIn("jesd_link_status_read", ops)
        self.assertIn("jesd_rx_link_status_read", ops)

    def test_axi_quad_spi_controller_uses_xspi(self) -> None:
        files = self._generate(_spec(jesd=None, driver="XSpi"))
        driver = files["drivers/afe7900.c"]
        self.assertIn("XSpi_SetSlaveSelect(spHal->spSpi, (1U << AFE7900_SPI_SELECT))", driver)
        self.assertIn("int afe7900DeviceInit(XSpi* spSpi)", driver)

    def test_missing_config_words_is_a_codegen_error(self) -> None:
        with self.assertRaises(cmodel.CodegenError) as ctx:
            self._generate(_spec(jesd=None, words=""))
        self.assertIn("S2C-CODEGEN-AFE-001", str(ctx.exception))

    def test_two_afes_not_supported_yet(self) -> None:
        spec = _spec(jesd=None)
        spec["devices"].append({**spec["devices"][0], "id": "afe1", "attach": {"controller_id": "spi0", "spi_chip_select": 1}})
        with self.assertRaises(cmodel.CodegenError) as ctx:
            self._generate(spec)
        self.assertIn("S2C-CODEGEN-AFE-002", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
