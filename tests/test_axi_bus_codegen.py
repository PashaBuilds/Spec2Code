"""AXI soft-IP bus codegen (MicroBlaze): XIic / XSpi device drivers.

The deterministic emitters used to speak XIicPs_*/XSpiPs_* literals only, so a
MicroBlaze design - which has no PS at all - could not get an I2C or SPI device
driver. These tests lock the driver-polymorphic behaviour:

  * AXI IIC uses the BASE-ADDRESS polled API from xiic_l.h and checks the BYTE
    COUNT it returns (XIic_Send/XIic_Recv do not return XST_*).
  * AXI SPI follows the official polled flow from
    ``spi_v4_11/examples/xspi_polled_example.c`` and masks interrupts.
  * The PS output is byte-for-byte what it was before the refactor - that path
    is field verified on real ZynqMP hardware and must not move.
  * Drivers with no adapter arm (XQspiPs, XOspiPsv) still fail loudly.
"""

import json
import tempfile
import unittest
from pathlib import Path

from orchestrator import cmodel, codegen


ROOT = Path(__file__).resolve().parent.parent

#: Instances/base addresses match the REAL MicroBlaze BSP fixture in
#: test/0_workspace_mb/.../bsp/microblaze_0/include/xparameters.h.
AXI_I2C_CONTROLLER = {
    "id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0",
    "base_address": "0x40800000", "device_id": 0, "driver": "XIic",
    "source": "xparameters", "zone": "pl",
}
AXI_SPI_CONTROLLER = {
    "id": "pl_spi_0", "type": "spi", "instance": "XPAR_AXI_QUAD_SPI_0",
    "base_address": "0x44A00000", "device_id": 0, "driver": "XSpi",
    "source": "xparameters", "zone": "pl",
}
PS_I2C_CONTROLLER = {
    "id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
    "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
    "source": "xparameters", "zone": "ps",
}
PS_SPI_CONTROLLER = {
    "id": "ps_spi_0", "type": "spi", "instance": "XPAR_XSPIPS_0",
    "base_address": "0xFF040000", "device_id": 0, "driver": "XSpiPs",
    "source": "xparameters", "zone": "ps",
}


def _base_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


def _microblaze_spec(project_name: str) -> dict:
    spec = _base_spec(project_name)
    spec["project"].update({
        "platform": "microblaze_7series", "target_core": "microblaze_0",
        "runtime": "bare_metal", "testbench_transport": "uart",
    })
    spec["controllers"] = [
        {"id": "pl_uart_0", "type": "uart", "instance": "XPAR_AXI_UARTLITE_0",
         "base_address": "0x40600000", "device_id": 0, "driver": "XUartLite",
         "source": "xparameters", "zone": "pl"},
        dict(AXI_I2C_CONTROLLER),
        dict(AXI_SPI_CONTROLLER),
    ]
    spec["muxes"] = []
    spec["devices"] = []
    return spec


def _tmp101(controller_id: str, via_mux: dict | None = None) -> dict:
    return {
        "id": "u3_tmp101", "part": "TMP101", "descriptor_ref": "descriptors/tmp101.yaml",
        "attach": {"controller_id": controller_id, "i2c_address": "0x4A",
                   "via_mux": via_mux, "reset_gpio": None, "irq_line": None},
        "tests_requested": [],
    }


def _lmk04832(controller_id: str) -> dict:
    """A TICS register device - the only shape that pulls in the SPI register helpers."""
    return {
        "id": "u30_lmk04832", "part": "LMK04832",
        "descriptor_ref": "descriptors/lmk04832.yaml",
        "attach": {"controller_id": controller_id, "spi_chip_select": 0, "reset_gpio": None},
        "tests_requested": [],
    }


def _mt25q128(controller_id: str) -> dict:
    return {
        "id": "u21_mt25q128", "part": "MT25Q128",
        "descriptor_ref": "descriptors/mt25q128.yaml",
        "attach": {"controller_id": controller_id, "spi_chip_select": 0,
                   "address_width": 24, "reset_gpio": None},
        "tests_requested": [],
    }


def _generate(spec: dict) -> dict[str, str]:
    """Generate into a temp dir and return {relative posix path: text}."""
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / spec["project"]["name"]
        codegen.generate(spec, out_dir)
        return {
            path.relative_to(out_dir).as_posix(): path.read_text(encoding="utf-8")
            for path in sorted(out_dir.rglob("*")) if path.is_file()
        }


class AxiI2cCodegenTests(unittest.TestCase):
    def test_axi_iic_device_uses_base_address_low_level_api(self) -> None:
        spec = _microblaze_spec("unit_axi_iic_device")
        spec["devices"] = [_tmp101("pl_i2c_0")]

        files = _generate(spec)
        source = files["drivers/tmp101.c"]
        header = files["drivers/tmp101.h"]

        # xiic_l.h - the POLLED AXI IIC API - not xiicps.h, and no PS literals.
        self.assertIn('#include "xiic_l.h"', header)
        self.assertNotIn("xiicps.h", header)
        self.assertNotIn("XIicPs_", source)

        # The handle is the controller BASE ADDRESS (unsigned long / 'ul'
        # prefix), because xiic_l.h has no driver instance at all.
        self.assertIn("int tmp101TemperatureRead(unsigned long ulIicBase, int* ipTemperature)", source)
        self.assertNotIn("XIic*", source)

    def test_axi_iic_checks_returned_byte_count_and_uses_stop(self) -> None:
        spec = _microblaze_spec("unit_axi_iic_bytecount")
        spec["devices"] = [_tmp101("pl_i2c_0")]

        source = _generate(spec)["drivers/tmp101.c"]

        # XIic_Send/XIic_Recv return BYTES TRANSFERRED (0 on a busy bus), never
        # XST_*: a short count is the only failure signal there is.
        self.assertIn(
            "uiSent = (unsigned int)XIic_DynSend(ulBase, (unsigned short)ucAddress, ucpBuffer,",
            source)
        self.assertIn(
            "uiGot = (unsigned int)XIic_DynRecv(ulBase, ucAddress, ucpBuffer, (unsigned char)uiLength);",
            source)
        for guard in ("if (uiSent != uiLength)", "if (uiGot != uiLength)"):
            self.assertIn(guard, source)
        self.assertIn("return XST_FAILURE;", source)

        # Yazimlar STOP ile biter; register-pointer yazimi ise REPEATED_START ile
        # (SAHA Nexys A7: dinamik modda STOP'lu pointer + DynRecv IP'de takilir).
        # (Bu spec'te yazim yok: STOP'lu yazim mux testinde dogrulanir.)
        # Register okumalarinda pointer REPEATED_START ile gider (SAHA: Nexys A7).
        self.assertIn("tmp101BusSend(ulIicBase, TMP101_I2C_ADDR, &ucReg, 1U, XIIC_REPEATED_START);", source)

    def test_axi_iic_device_init_probes_the_bus_instead_of_faking_a_controller_init(self) -> None:
        spec = _microblaze_spec("unit_axi_iic_init")
        spec["devices"] = [_tmp101("pl_i2c_0")]

        source = _generate(spec)["drivers/tmp101.c"]

        # No instance -> no LookupConfig/CfgInitialize. device_init must still
        # do something honest: confirm the AXI IIC core answers and SDA/SCL are
        # not stuck, so a dead bus fails loudly at init.
        self.assertIn("int tmp101DeviceInit(unsigned long ulIicBase)", source)
        self.assertIn("iStatus = XIic_DynInit(ulIicBase);", source)
        self.assertIn("iStatus = (int)XIic_WaitBusFree(ulIicBase);", source)
        self.assertNotIn("XIic_LookupConfig", source)
        self.assertNotIn("XIic_CfgInitialize", source)

    def test_axi_iic_mux_unit_generates_over_the_low_level_api(self) -> None:
        # The user's boards put devices behind a TCA9548A; the mux emitter must
        # be driver-polymorphic too, or every muxed AXI board stays unbuildable.
        spec = _microblaze_spec("unit_axi_iic_mux")
        spec["muxes"] = [{"id": "u7_tca9548a", "part": "TCA9548A",
                          "controller_id": "pl_i2c_0", "i2c_address": "0x70", "channels": 8}]
        spec["devices"] = [_tmp101("pl_i2c_0", {"mux_id": "u7_tca9548a", "channel": 3})]

        files = _generate(spec)
        mux_source = files["drivers/tca9548a.c"]
        device_source = files["drivers/tmp101.c"]

        self.assertIn("int tca9548aChannelSelect(unsigned long ulIicBase, unsigned char ucChannel)",
                      mux_source)
        self.assertIn("XIic_DynSend(ulBase, (unsigned short)ucAddress, ucpBuffer,", mux_source)
        self.assertNotIn("XIicPs_", mux_source)
        # The mux select is still injected before every device access, with the
        # base address handed straight through.
        self.assertIn("iStatus = tca9548aChannelSelect(ulIicBase, 3U);", device_source)

    def test_axi_iic_testbench_wires_base_address_handles_and_scan(self) -> None:
        spec = _microblaze_spec("unit_axi_iic_testbench")
        spec["devices"] = [_tmp101("pl_i2c_0")]

        ops = _generate(spec)["tests/unit_axi_iic_testbench_testbench_ops.c"]

        # Board-handle hook: base address by value, 0 == "unknown controller".
        self.assertIn(
            "SPEC2CODE_WEAK unsigned long spec2codeTestbenchIicHandleGet(const char* cpControllerId)",
            ops)
        self.assertIn('ulIicBase = spec2codeTestbenchIicHandleGet("pl_i2c_0");', ops)
        self.assertIn("if (ulIicBase == 0U)", ops)
        # Generic register helpers and the muxed-line bus scan both run on the
        # AXI API; no PS driver may leak into a MicroBlaze application.
        self.assertIn("spec2codeTestbenchI2cRegisterReadAxi", ops)
        self.assertIn("XIic_DynSend(ulScanIic, (unsigned short)uiScanAddr, &ucProbe, 1U, XIIC_STOP)", ops)
        self.assertNotIn("XIicPs_", ops)

    def test_axi_iic_controllers_are_published_for_scanning_in_the_manifest(self) -> None:
        # Faz 2 boslugu: manifest `i2c_scan` bolumu `"XIicPs" in handle_types`
        # ile kapiliydi. Tarama op'lari (i2c_scan/i2c_mux_set) AXI XIic icin de
        # URETILIYORDU, ama manifest bunu bildirmedigi icin UI'nin tarama karti
        # (`I2cScanCard`, `scanInfo.controllers` bos oldugunda hic render
        # edilmez) MicroBlaze kartlarinda gorunmuyordu.
        spec = _microblaze_spec("unit_axi_iic_scan_manifest")
        spec["muxes"] = [{"id": "u10_tca9548a", "part": "TCA9548A",
                          "controller_id": "pl_i2c_0", "i2c_address": "0x70", "channels": 8}]
        spec["devices"] = [_tmp101("pl_i2c_0")]

        files = _generate(spec)
        manifest = json.loads(files["tests/spec2code_testbench_manifest.json"])
        ops = files["tests/unit_axi_iic_scan_manifest_testbench_ops.c"]
        mesaj = files["tests/spec2code_mesaj.c"]

        scan = manifest["i2c_scan"]
        self.assertEqual(scan["controllers"], [{"id": "pl_i2c_0", "instance": "XPAR_AXI_IIC_0"}])
        self.assertEqual(scan["op"], "i2c_scan")
        self.assertEqual(scan["mux_op"], "i2c_mux_set")
        # Mux topolojisi de bildirilir: kanal kanal harita UI'dan surulebilir.
        self.assertEqual([m["id"] for m in scan["muxes"]], ["u10_tca9548a"])
        self.assertEqual(scan["muxes"][0]["address"], 0x70)
        # Ajan op'u gercekten var (manifest bos vaat etmiyor).
        self.assertIn('spRequest->cArrOperation, "i2c_scan"', ops)
        self.assertIn('spRequest->cArrOperation, "i2c_mux_set"', ops)
        # DENETLEYICI-INDEKS KONTRATI: backend/i2c_scan.py tel'e manifest
        # `i2c_scan.controllers` sirasindaki indeksi koyar; uretilen kopru
        # cArrRegister'i AYNI siradaki tablodan cozer. PS'te oldugu gibi.
        table = mesaj.split("S_cpArrDenetleyiciTablosu[] =", 1)[1].split("};", 1)[0]
        wire_ids = [line.strip().strip(',').strip('"') for line in table.splitlines()
                    if line.strip().startswith('"')]
        self.assertEqual(wire_ids[:len(scan["controllers"])],
                         [c["id"] for c in scan["controllers"]])

    def test_axi_spi_testbench_register_helpers_use_the_axi_api(self) -> None:
        spec = _microblaze_spec("unit_axi_spi_testbench")
        spec["devices"] = [_lmk04832("pl_spi_0")]

        ops = _generate(spec)["tests/unit_axi_spi_testbench_testbench_ops.c"]

        self.assertIn("static int spec2codeTestbenchSpiRegisterWriteAxi(XSpi* spSpi, unsigned char ucSelect,",
                      ops)
        self.assertIn("iStatus = XSpi_SetSlaveSelect(spSpi, (1U << ucSelect));", ops)
        self.assertIn("iStatus = XSpi_Transfer(spSpi, ucArrTx, ucArrRx, 3U);", ops)
        self.assertNotIn("XSpiPs_", ops)


class AxiSpiCodegenTests(unittest.TestCase):
    def test_axi_spi_device_follows_the_official_polled_flow(self) -> None:
        spec = _microblaze_spec("unit_axi_spi_device")
        spec["devices"] = [_mt25q128("pl_spi_0")]

        files = _generate(spec)
        source = files["drivers/mt25q128.c"]
        header = files["drivers/mt25q128.h"]

        self.assertIn('#include "xspi.h"', header)
        self.assertNotIn("XSpiPs_", source)

        # xspi_polled_example.c order: LookupConfig -> CfgInitialize ->
        # SetOptions -> Start -> IntrGlobalDisable.
        init = source[source.index("int mt25q128DeviceInit"):]
        for call in ("XSpi_LookupConfig(XPAR_AXI_QUAD_SPI_0_DEVICE_ID)",
                     "XSpi_CfgInitialize(spSpi, spConfig, spConfig->BaseAddress)",
                     "XSpi_SetOptions(spSpi, XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)",
                     "XSpi_Start(spSpi)",
                     "XSpi_IntrGlobalDisable(spSpi)"):
            self.assertIn(call, init)
        self.assertLess(init.index("XSpi_Start(spSpi)"), init.index("XSpi_IntrGlobalDisable(spSpi)"),
                        "interrupts must be masked AFTER the core is started")

    def test_axi_spi_slave_select_is_a_one_hot_mask(self) -> None:
        # XSpiPs takes a slave INDEX; AXI XSpi takes a one-hot ACTIVE-HIGH mask
        # (xspi.c: "a 32-bit mask with a 1 in the bit position of the slave
        # being selected"; the official flash examples pass 0x01 for CS0).
        spec = _microblaze_spec("unit_axi_spi_select")
        spec["devices"] = [_mt25q128("pl_spi_0")]

        source = _generate(spec)["drivers/mt25q128.c"]

        self.assertIn("XSpi_SetSlaveSelect(spSpi, (1U << MT25Q128_SPI_SELECT));", source)
        self.assertIn("XSpi_Transfer(spSpi,", source)
        self.assertNotIn("XSpiPs_PolledTransfer", source)


class UnsupportedBusDriverGateTests(unittest.TestCase):
    def test_axi_soft_ip_drivers_are_now_supported(self) -> None:
        self.assertIn("XIic", cmodel._SUPPORTED_BUS_DRIVERS["i2c"])
        self.assertIn("XSpi", cmodel._SUPPORTED_BUS_DRIVERS["spi"])

    def test_unimplemented_drivers_still_fail_loudly(self) -> None:
        # XQspiPs (Zynq-7000) and XOspiPsv (Versal) have no emitter arm; letting
        # them through would emit code that cannot compile against that BSP.
        for driver, ctype in (("XQspiPs", "qspi"), ("XOspiPsv", "qspi")):
            with self.subTest(driver=driver):
                with self.assertRaises(cmodel.CodegenError) as ctx:
                    cmodel._handle_for({"id": "c0", "type": ctype, "driver": driver,
                                        "instance": "XPAR_X_0", "zone": "ps"})
                message = str(ctx.exception)
                self.assertIn(driver, message)
                self.assertIn("does not support", message)
                self.assertIn("XQspiPsu", message)  # names what IS supported


class PsOutputUnchangedTests(unittest.TestCase):
    """HARD INVARIANT: the field-verified ZynqMP PS output must not move."""

    def _ps_spec(self, project_name: str) -> dict:
        spec = _base_spec(project_name)
        spec["controllers"] = [dict(PS_I2C_CONTROLLER), dict(PS_SPI_CONTROLLER)]
        spec["muxes"] = [{"id": "u7_tca9548a", "part": "TCA9548A",
                          "controller_id": "ps_i2c_0", "i2c_address": "0x70", "channels": 8}]
        spec["devices"] = [_tmp101("ps_i2c_0", {"mux_id": "u7_tca9548a", "channel": 3}),
                           _lmk04832("ps_spi_0"), _mt25q128("ps_spi_0")]
        return spec

    def test_ps_i2c_path_still_emits_the_instance_api_verbatim(self) -> None:
        files = _generate(self._ps_spec("unit_ps_i2c_unchanged"))
        source = files["drivers/tmp101.c"]
        mux_source = files["drivers/tca9548a.c"]

        self.assertIn('#include "xiicps.h"', files["drivers/tmp101.h"])
        self.assertIn("iStatus = XIicPs_MasterSendPolled(spIic, &ucReg, 1, TMP101_I2C_ADDR);", source)
        self.assertIn("iStatus = XIicPs_MasterRecvPolled(spIic, ucpBuffer, (int)uiLength, TMP101_I2C_ADDR);",
                      source)
        self.assertIn("while (XIicPs_BusIsBusy(spIic) == TRUE)", source)
        self.assertIn("spConfig = XIicPs_LookupConfig(XPAR_XIICPS_0_DEVICE_ID);", source)
        self.assertIn("iStatus = XIicPs_SetSClk(spIic, TMP101_I2C_SCLK_HZ);", source)
        self.assertIn("int tca9548aChannelSelect(XIicPs* spIic, unsigned char ucChannel)", mux_source)
        # No AXI machinery may bleed into a PS project.
        for token in ("XIic_", "XIIC_STOP", "tmp101BusSend", "tca9548aBusSend", "unsigned long ulIicBase"):
            self.assertNotIn(token, source + mux_source)

    def test_ps_spi_path_still_emits_the_instance_api_verbatim(self) -> None:
        files = _generate(self._ps_spec("unit_ps_spi_unchanged"))
        source = files["drivers/mt25q128.c"]

        self.assertIn('#include "xspips.h"', files["drivers/mt25q128.h"])
        self.assertIn("iStatus = XSpiPs_SetSlaveSelect(spSpi, MT25Q128_SPI_SELECT);", source)
        self.assertIn("iStatus = XSpiPs_PolledTransfer(spSpi, ucArrTx, NULL, 1);", source)
        self.assertIn("iStatus = XSpiPs_SetOptions(spSpi, XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);",
                      source)
        self.assertIn("iStatus = XSpiPs_SetClkPrescaler(spSpi, XSPIPS_CLK_PRESCALE_8);", source)
        for token in ("XSpi_Transfer", "XSpi_IntrGlobalDisable", "XSP_MASTER_OPTION", "(1U << MT25Q128_SPI_SELECT)"):
            self.assertNotIn(token, source)

    def test_ps_testbench_helper_names_and_handles_are_unchanged(self) -> None:
        ops = _generate(self._ps_spec("unit_ps_testbench_unchanged"))[
            "tests/unit_ps_testbench_unchanged_testbench_ops.c"]

        # Historic (unsuffixed) helper names stay; the AXI twins are suffixed so
        # both can coexist without renaming the proven PS side.
        self.assertIn("static int spec2codeTestbenchI2cRegisterRead(XIicPs* spIic, unsigned char ucAddress,", ops)
        self.assertIn("static int spec2codeTestbenchSpiRegisterWrite(XSpiPs* spSpi, unsigned char ucSelect,", ops)
        self.assertIn("SPEC2CODE_WEAK XIicPs* spec2codeTestbenchIicPsHandleGet(const char* cpControllerId)", ops)
        self.assertIn("iProbeStatus = XIicPs_MasterSendPolled(spScanIic, &ucProbe, 1, (unsigned short)uiScanAddr);",
                      ops)
        for token in ("Axi(", "XIic_", "XSpi_Transfer", "unsigned long ulScanIic"):
            self.assertNotIn(token, ops)


if __name__ == "__main__":
    unittest.main()
