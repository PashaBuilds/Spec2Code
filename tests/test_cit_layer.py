"""CIT entegre katmani (cit/): HAL + entegre CIT + sistem toplayici.

Uc sey kilitlenir:
  * Uretim sekli: dosya agaci, struct/bit alani isimleri, _Static_assert boyutlari,
    konfig varsayilanlari spec'ten birebir; PS ve AXI port makrolari.
  * Degismezlik: drivers/ ve tests/ ciktilari cit/ katmani eklendi diye
    DEGISMEZ (README'ye yalniz bolum eklenir).
  * Host round-trip: kullanici portu arka ucuyla (SPEC2CODE_CIT_PORT_KULLANICI)
    sahte LTC2991/TMP101/LMK04832 register modeli uzerinden sistemCitRead
    kosturulur; bitler ve degerler beklenen sekilde dolar. gcc yoksa atlanir.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator import cit_layer, codegen

ROOT = Path(__file__).resolve().parent.parent
MB_SPEC = ROOT / "test/0_temp_mb_e2e/mb_e2e.spec.json"


def _find_cc() -> str | None:
    return shutil.which("gcc") or shutil.which("cc")


def _mb_spec(name: str) -> dict:
    if MB_SPEC.is_file():
        spec = json.loads(MB_SPEC.read_text(encoding="utf-8"))
    else:
        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": name}
    return spec


def _axi_spec(name: str) -> dict:
    """MicroBlaze: AXI IIC (mux arkasinda LTC2991 + TMP101) + AXI SPI (LMK04832)."""
    base = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec = {
        "schema_version": base.get("schema_version", "1.0"),
        "project": {"name": name, "platform": "microblaze_7series", "target_core": "microblaze_0",
                    "runtime": "bare_metal", "output_mode": "dropin", "testbench_transport": "uart"},
        "coding_standard_ref": "std/default.ruleset.json",
        "llm": {"enabled": False},
        "controllers": [
            {"id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0", "base_address": "0x40800000",
             "device_id": 0, "driver": "XIic", "source": "xparameters", "zone": "pl"},
            {"id": "pl_spi_0", "type": "spi", "instance": "XPAR_AXI_QUAD_SPI_0",
             "base_address": "0x44A00000", "device_id": 0, "driver": "XSpi", "source": "xparameters",
             "zone": "pl"},
            {"id": "pl_uart_0", "type": "uart", "instance": "XPAR_AXI_UARTLITE_0",
             "base_address": "0x40600000", "device_id": 0, "driver": "XUartLite",
             "source": "xparameters", "zone": "pl"},
        ],
        "muxes": [{"id": "u1_tca9548a", "part": "TCA9548A", "controller_id": "pl_i2c_0",
                   "i2c_address": "0x70", "channels": 8}],
        "devices": [
            {"id": "u2_ltc2991", "part": "LTC2991", "descriptor_ref": "descriptors/ltc2991.yaml",
             "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x48",
                        "via_mux": {"mux_id": "u1_tca9548a", "channel": 3}},
             "config": {"pairs": {k: {"mode": "single_ended_voltage", "shunt_milliohm": None}
                                  for k in ("v1_v2", "v3_v4", "v5_v6", "v7_v8")},
                        "internal_temperature": True, "vcc_read": False},
             "operations_requested": ["device_init", "voltage_read", "temperature_read"],
             "tests_requested": ["self_test"]},
            {"id": "u3_tmp101", "part": "TMP101", "descriptor_ref": "descriptors/tmp101.yaml",
             "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x4A",
                        "via_mux": {"mux_id": "u1_tca9548a", "channel": 1}},
             "operations_requested": ["device_init", "temperature_read", "config_read"],
             "tests_requested": ["self_test"]},
            {"id": "u4_lmk04832", "part": "LMK04832", "descriptor_ref": "descriptors/lmk04832.yaml",
             "attach": {"controller_id": "pl_spi_0", "spi_chip_select": 0},
             "config": {"ticspro_registers": ["0x000010", "0x016302", "0x018300", "0x017300"]},
             "operations_requested": ["device_init", "pll1_lock_detect", "pll2_lock_detect"],
             "tests_requested": ["self_test"]},
        ],
        "generation_options": {"qc_max_rounds": 1, "include_doxygen": True, "line_ending": "crlf"},
    }
    return spec


def _generate(spec: dict) -> Path:
    out_dir = Path(tempfile.mkdtemp(prefix="s2c_cit_layer_"))
    codegen.generate(spec, out_dir)
    return out_dir


class BitfieldLayoutTests(unittest.TestCase):
    def test_gcc_unit_allocation(self) -> None:
        self.assertEqual(cit_layer.bitfield_bytes([1] * 20), 4)
        self.assertEqual(cit_layer.bitfield_bytes([1] * 32), 4)
        self.assertEqual(cit_layer.bitfield_bytes([1] * 33), 8)
        # 30 + 4: 4 bitlik alan kalan 2 bite sigmaz -> ikinci birim
        self.assertEqual(cit_layer.bitfield_bytes([30, 4]), 8)
        self.assertEqual(cit_layer.bitfield_bytes([2, 8, 3]), 4)


class CitLayerGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.out_dir = _generate(_axi_spec("unit_cit_layer_axi"))
        cls.cit = cls.out_dir / "cit"

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.out_dir, ignore_errors=True)

    def _read(self, rel: str) -> str:
        return (self.cit / rel).read_text(encoding="utf-8")

    def test_tree_has_hal_chip_and_system_layers(self) -> None:
        for rel in ("hal/spec2code_cit_port.h", "hal/spec2code_i2c_bus.h", "hal/spec2code_i2c_bus.c",
                    "hal/spec2code_spi_bus.h", "hal/spec2code_spi_bus.c",
                    "ltc2991_cit.h", "ltc2991_cit.c", "tmp101_cit.h", "tmp101_cit.c",
                    "lmk04832_cit.h", "lmk04832_cit.c",
                    "spec2code_cit_sistem.h", "spec2code_cit_sistem.c"):
            self.assertTrue((self.cit / rel).is_file(), rel)
        # CRLF (hedef Vitis/Windows) - write_output yolu
        self.assertIn(b"\r\n", (self.cit / "ltc2991_cit.h").read_bytes())

    def test_port_header_selects_axi_backends_from_controllers(self) -> None:
        port = self._read("hal/spec2code_cit_port.h")
        self.assertIn("#define SPEC2CODE_CIT_PORT_XIIC 1", port)
        self.assertIn("#define SPEC2CODE_CIT_PORT_XSPI 1", port)
        self.assertIn("#define SPEC2CODE_CIT_PORT_XIICPS 0", port)
        self.assertIn("#define SPEC2CODE_CIT_PORT_XSPIPS 0", port)
        # -D ile ezilebilir olmali
        self.assertIn("#ifndef SPEC2CODE_CIT_PORT_XIIC\n", port.replace("\r\n", "\n"))

    def test_ltc2991_struct_has_status_bits_and_measurements(self) -> None:
        header = self._read("ltc2991_cit.h")
        for bit in ("uiStatusLowOk : 1", "uiStatusHighOk : 1", "uiVoltageReadOk : 1",
                    "uiTemperatureReadOk : 1", "uiV1Ready : 1", "uiV8Ready : 1", "uiBusy : 1",
                    "uiTInternalReady : 1", "uiV7V8Enable : 1"):
            self.assertIn(bit, header)
        self.assertIn("unsigned short usArrVoltageRead[8];", header)
        self.assertIn("int iTemperatureRead;", header)
        self.assertIn("unsigned char ucStatusLow;", header)
        self.assertIn("_Static_assert(sizeof(SLtc2991CitBayraklar) == 4U", header)
        # spec'ten varsayilan: adres 0x48, mux 0x70 kanal 3
        self.assertIn("#define LTC2991_CIT_I2C_ADDR 0x48U", header)
        self.assertIn("#define LTC2991_CIT_MUX_ADDR 0x70U", header)
        self.assertIn("#define LTC2991_CIT_MUX_KANAL 3U", header)
        self.assertIn("int ltc2991CitInit(SSpec2codeI2cBus* spBus, const SLtc2991CitConfig* spConfig);", header)
        self.assertIn("int ltc2991CitRead(SSpec2codeI2cBus* spBus, const SLtc2991CitConfig* spConfig,", header)

    def test_chip_sources_only_talk_to_the_hal(self) -> None:
        for rel in ("ltc2991_cit.c", "tmp101_cit.c", "lmk04832_cit.c", "spec2code_cit_sistem.c"):
            src = self._read(rel)
            for forbidden in ("XIic_", "XIicPs_", "XSpi_", "XSpiPs_", "xiic_l.h", "xspi.h", "xstatus.h"):
                self.assertNotIn(forbidden, src, f"{rel} icinde {forbidden}")
        ltc = self._read("ltc2991_cit.c")
        self.assertIn("spec2codeI2cMuxSelect(spBus, spConfig->ucMuxAdres, spConfig->ucMuxKanal)", ltc)
        self.assertIn("spec2codeI2cRegisterRead(spBus, spConfig->ucI2cAdres", ltc)
        # profil init yazimlari HAL uzerinden (4 yazim: CONTROL_V1V4, CONTROL_V5V8, PWM, STATUS_HIGH)
        self.assertIn("#define LTC2991_CIT_INIT_SEQUENCE_COUNT 4U", ltc)
        self.assertIn("spec2codeI2cRegisterWrite(spBus, spConfig->ucI2cAdres,", ltc)

    def test_lmk04832_spi_uses_tics_frame_and_status_bits(self) -> None:
        header = self._read("lmk04832_cit.h")
        src = self._read("lmk04832_cit.c")
        for bit in ("uiRbPllStatusOk : 1", "uiPll1LockDetectOk : 1", "uiRbPll1Dld : 1", "uiRbPll2DldLost : 1"):
            self.assertIn(bit, header)
        self.assertIn("unsigned char ucPll1LockDetect;", header)
        self.assertIn("#define LMK04832_CIT_REG_RB_PLL_STATUS 0x0183U", header)
        # okuma cercevesi: R/W biti 23 = 1, adres << 8 (descriptor register_model)
        self.assertIn("uiWord = ((unsigned int)1U << 23U) | ((uiReg & 0x7FFFU) << 8U);", src)
        self.assertIn("#define LMK04832_CIT_INIT_SEQUENCE_COUNT 4U", src)
        self.assertIn("0x016302U", src)
        self.assertIn("spec2codeSpiTransfer(spBus, spConfig->ucSpiSelect,", src)

    def test_system_aggregate_lists_every_chip_and_bus(self) -> None:
        header = self._read("spec2code_cit_sistem.h")
        src = self._read("spec2code_cit_sistem.c")
        self.assertIn("SSpec2codeI2cBus sPlI2c0;", header)
        self.assertIn("SSpec2codeSpiBus sPlSpi0;", header)
        self.assertIn("SLtc2991Cit sU2Ltc2991;", header)
        self.assertIn("STmp101Cit sU3Tmp101;", header)
        self.assertIn("SLmk04832Cit sU4Lmk04832;", header)
        self.assertIn("#define SISTEM_CIT_CIHAZ_SAYISI 3U", header)
        self.assertIn("XPAR_AXI_IIC_0_BASEADDR", src)
        self.assertIn("XPAR_AXI_QUAD_SPI_0_DEVICE_ID", src)
        self.assertIn("SPEC2CODE_I2C_SURUCU_KULLANICI", src)

    def test_readme_documents_the_layer(self) -> None:
        readme = (self.out_dir / "README.md").read_text(encoding="utf-8")
        self.assertIn("## CIT entegre katmani (`cit/`)", readme)
        self.assertIn("`cit/ltc2991_cit.h/.c`", readme)
        self.assertIn("`sistemCitRead()`", readme)


class CitLayerInvarianceTests(unittest.TestCase):
    def test_existing_driver_and_test_outputs_are_untouched(self) -> None:
        """cit/ eklendi diye drivers/ ve tests/ bayt-bayt degismemeli."""
        spec = _axi_spec("unit_cit_layer_invariance")
        out_dir = _generate(spec)
        try:
            for rel in ("drivers/ltc2991.c", "tests/spec2code_cit.h", "tests/spec2code_cit.c"):
                text = (out_dir / rel).read_text(encoding="utf-8")
                self.assertNotIn("spec2code_i2c_bus", text)
                self.assertNotIn("SSpec2codeI2cBus", text)
            # mevcut SBoardCit sozlesmesi yerinde
            self.assertIn("void boardCitRun(SBoardCit* spCit);", (out_dir / "tests/spec2code_cit.h").read_text(encoding="utf-8"))
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_ps_spec_selects_ps_backends(self) -> None:
        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
        spec["project"] = {**spec["project"], "name": "unit_cit_layer_ps"}
        out_dir = _generate(spec)
        try:
            port = (out_dir / "cit/hal/spec2code_cit_port.h").read_text(encoding="utf-8")
            self.assertIn("#define SPEC2CODE_CIT_PORT_XIICPS 1", port)
            self.assertIn("#define SPEC2CODE_CIT_PORT_XIIC 0", port)
            src = (out_dir / "cit/spec2code_cit_sistem.c").read_text(encoding="utf-8")
            self.assertIn("SPEC2CODE_I2C_SURUCU_XIICPS", src)
            self.assertIn("_DEVICE_ID;", src)
            # komut tabanli flash CIT'e girmez, README'de acikca yazar
            readme = (out_dir / "README.md").read_text(encoding="utf-8")
            self.assertIn("komut tabanli SPI flash", readme)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


_HOST_MAIN = r"""
#include <stdio.h>
#include <string.h>
#include "spec2code_cit_sistem.h"

/* --- sahte LTC2991 (0x48, mux 0x70 kanal 3) + TMP101 (0x4A, kanal 1) --- */
static unsigned char S_ucMuxKanal = 0xFFU;
static unsigned char S_ucArrLtc[0x20];
static unsigned char S_ucArrTmp[4][2];
static unsigned char S_ucPointer = 0U;
static unsigned char S_ucSonAdres = 0U;
static unsigned int S_uiLtcYazim = 0U;

int spec2codeI2cPortWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                          const unsigned char* ucpVeri, unsigned int uiBoy)
{
    (void)spBus;
    if (ucAdres == 0x70U)
    {
        S_ucMuxKanal = ucpVeri[0];
        return 0;
    }
    S_ucSonAdres = ucAdres;
    S_ucPointer = ucpVeri[0];
    if ((ucAdres == 0x48U) && (uiBoy == 2U))
    {
        /* STATUS_LOW/STATUS_HIGH'in hazir bitleri salt okunur: yazimlar sayilir, ham
         * hazir bitleri ezilmez (gercek cipte de READY bitleri yazimla degismez). */
        if (S_ucPointer > 0x01U)
        {
            S_ucArrLtc[S_ucPointer] = ucpVeri[1];
        }
        S_uiLtcYazim++;
    }
    return 0;
}

int spec2codeI2cPortRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char* ucpVeri,
                         unsigned int uiBoy)
{
    unsigned int uiIndex;

    (void)spBus;
    if ((ucAdres == 0x48U) && (S_ucMuxKanal == (1U << 3)))
    {
        for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
        {
            ucpVeri[uiIndex] = S_ucArrLtc[S_ucPointer + uiIndex];
        }
        return 0;
    }
    if ((ucAdres == 0x4AU) && (S_ucMuxKanal == (1U << 1)))
    {
        for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
        {
            ucpVeri[uiIndex] = S_ucArrTmp[S_ucPointer][uiIndex];
        }
        return 0;
    }
    return 1; /* NACK: yanlis kanal ya da bilinmeyen adres */
}

/* --- sahte LMK04832: RB_PLL_STATUS (0x183) = 0x05 (PLL1 DLD + PLL2 DLD) --- */
static unsigned int S_uiLmkYazim = 0U;

int spec2codeSpiPortTransfer(SSpec2codeSpiBus* spBus, unsigned char ucSelect,
                             const unsigned char* ucpTx, unsigned char* ucpRx, unsigned int uiBoy)
{
    unsigned int uiAdres;

    (void)spBus;
    if ((ucSelect != 0U) || (uiBoy != 3U))
    {
        return 1;
    }
    uiAdres = (((unsigned int)ucpTx[0] & 0x7FU) << 8U) | (unsigned int)ucpTx[1];
    if ((ucpTx[0] & 0x80U) == 0U)
    {
        S_uiLmkYazim++;
        return 0;
    }
    if (ucpRx != (unsigned char*)0)
    {
        ucpRx[0] = 0U;
        ucpRx[1] = 0U;
        ucpRx[2] = (uiAdres == 0x183U) ? 0x05U : 0x00U;
    }
    return 0;
}

int main(void)
{
    static SSistemCitBus S_sBus;
    static SSistemCit S_sCit;
    int iStatus;
    unsigned int uiIndex;

    /* LTC2991: STATUS_LOW=0xFF (hepsi hazir), STATUS_HIGH=0x0A (T ready + T/VCC enable),
     * V1..V8 = 3300 mV kodu (3300 / 0.30518 = 10813 = 0x2A3D), T = 25.0 C -> 400 * 0.0625 -> 0x190 */
    S_ucArrLtc[0x00] = 0xFFU;
    S_ucArrLtc[0x01] = 0x0AU;
    for (uiIndex = 0U; uiIndex < 8U; uiIndex++)
    {
        S_ucArrLtc[0x0A + 2U * uiIndex] = 0x2AU;
        S_ucArrLtc[0x0B + 2U * uiIndex] = 0x3DU;
    }
    S_ucArrLtc[0x1A] = 0x01U;
    S_ucArrLtc[0x1B] = 0x90U;
    /* TMP101: TEMPERATURE = 0x1900 -> 25.0 C (12 bit, LSB 0.0625); CONFIGURATION = 0x60 */
    S_ucArrTmp[0][0] = 0x19U;
    S_ucArrTmp[0][1] = 0x00U;
    S_ucArrTmp[1][0] = 0x60U;

    sistemCitBusVarsayilan(&S_sBus);
    printf("surucu i2c=%d spi=%d\n", (int)S_sBus.sPlI2c0.eSurucu, (int)S_sBus.sPlSpi0.eSurucu);
    iStatus = sistemCitInit(&S_sBus);
    printf("init=%d ltcyazim=%u lmkyazim=%u\n", iStatus, S_uiLtcYazim, S_uiLmkYazim);
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    printf("read=%d sayac=%u hata=%u\n", iStatus, S_sCit.uiSayac, S_sCit.uiHataSayac);
    printf("ltc ok=%u%u%u%u v1ready=%u v8ready=%u busy=%u tready=%u statuslow=0x%02X\n",
           S_sCit.sU2Ltc2991.sBayraklar.uiStatusLowOk, S_sCit.sU2Ltc2991.sBayraklar.uiStatusHighOk,
           S_sCit.sU2Ltc2991.sBayraklar.uiVoltageReadOk, S_sCit.sU2Ltc2991.sBayraklar.uiTemperatureReadOk,
           S_sCit.sU2Ltc2991.sBayraklar.uiV1Ready, S_sCit.sU2Ltc2991.sBayraklar.uiV8Ready,
           S_sCit.sU2Ltc2991.sBayraklar.uiBusy, S_sCit.sU2Ltc2991.sBayraklar.uiTInternalReady,
           S_sCit.sU2Ltc2991.ucStatusLow);
    printf("ltc v1=%u v8=%u t=%d\n", S_sCit.sU2Ltc2991.usArrVoltageRead[0],
           S_sCit.sU2Ltc2991.usArrVoltageRead[7], S_sCit.sU2Ltc2991.iTemperatureRead);
    printf("tmp t=%d cfgok=%u\n", S_sCit.sU3Tmp101.iTemperatureRead,
           S_sCit.sU3Tmp101.sBayraklar.uiConfigurationOk);
    printf("lmk ok=%u pll1=%u pll2=%u dld1=%u dld2=%u lost1=%u raw=0x%02X\n",
           S_sCit.sU4Lmk04832.sBayraklar.uiRbPllStatusOk, S_sCit.sU4Lmk04832.ucPll1LockDetect,
           S_sCit.sU4Lmk04832.ucPll2LockDetect, S_sCit.sU4Lmk04832.sBayraklar.uiRbPll1Dld,
           S_sCit.sU4Lmk04832.sBayraklar.uiRbPll2Dld, S_sCit.sU4Lmk04832.sBayraklar.uiRbPll1DldLost,
           S_sCit.sU4Lmk04832.ucRbPllStatus);
    /* Hata yolu: mux'i bozalim -> LTC okumalari duser, TMP101 ve LMK etkilenmez. */
    S_ucArrLtc[0x00] = 0x00U; /* V1_READY hic gelmez -> poll zaman asimi */
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    printf("read2=%d hata=%u ltchata=%u vok=%u statuslowok=%u lmkok=%u\n", iStatus, S_sCit.uiHataSayac,
           S_sCit.sU2Ltc2991.uiHataSayac, S_sCit.sU2Ltc2991.sBayraklar.uiVoltageReadOk,
           S_sCit.sU2Ltc2991.sBayraklar.uiStatusLowOk, S_sCit.sU4Lmk04832.sBayraklar.uiRbPllStatusOk);
    return 0;
}
"""


class CitLayerHostRoundTripTests(unittest.TestCase):
    """Kullanici portu arka ucuyla host'ta derle + kostur (gcc varsa)."""

    def test_system_read_fills_bits_and_values_over_user_port(self) -> None:
        compiler = _find_cc()
        if compiler is None:
            self.skipTest("gcc/cc bulunamadi")
        out_dir = _generate(_axi_spec("unit_cit_layer_host"))
        try:
            cit = out_dir / "cit"
            (cit / "main.c").write_text(_HOST_MAIN, encoding="utf-8")
            binary = cit / "cit_host"
            sources = [str(p) for p in [*(cit / "hal").glob("*.c"), *cit.glob("*.c"),
                                        *(cit / "sim").glob("*.c")]]
            cmd = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-DSPEC2CODE_CIT_PORT_XIIC=0", "-DSPEC2CODE_CIT_PORT_XSPI=0",
                   "-DSPEC2CODE_CIT_PORT_KULLANICI=1",
                   "-I", str(cit / "hal"), "-I", str(cit), "-I", str(cit / "sim"),
                   "-o", str(binary)] + sources
            compile_run = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "surucu i2c=3 spi=3", output)          # KULLANICI arka ucu
        self.assertEqual(lines[1], "init=0 ltcyazim=4 lmkyazim=4", output)  # 4 I2C + 4 SPI init yazimi
        self.assertEqual(lines[2], "read=0 sayac=1 hata=0", output)
        self.assertEqual(lines[3], "ltc ok=1111 v1ready=1 v8ready=1 busy=0 tready=1 statuslow=0xFF", output)
        self.assertEqual(lines[4], "ltc v1=3299 v8=3299 t=2500", output)   # 0x2A3D*0.30518=3299.9 -> 3299 mV
        self.assertEqual(lines[5], "tmp t=2500 cfgok=1", output)
        self.assertEqual(lines[6], "lmk ok=1 pll1=1 pll2=1 dld1=1 dld2=1 lost1=0 raw=0x05", output)
        # hata yolu: LTC voltage_read zaman asimi + temperature ok; TMP/LMK etkilenmez
        self.assertEqual(lines[7], "read2=1 hata=1 ltchata=1 vok=0 statuslowok=1 lmkok=1", output)


_SIM_MAIN = r"""
#include <stdio.h>
#include "spec2code_cit_sistem.h"

/* Kullanici portu = "gercek donanim" yerine gecer: switch 0x70 ve TMP101 0x4A takili,
 * LTC2991 (0x48) KARTTA YOK -> port NACK doner. Karisik modda 0x48 sanal cevap verir. */
static unsigned char S_ucMuxKanal = 0xFFU;
static unsigned char S_ucArrTmp[4][2];
static unsigned char S_ucPointer = 0U;
static unsigned int S_uiPort48 = 0U; /* porta ulasan 0x48 transferi (karisik modda 0 beklenir) */

int spec2codeI2cPortWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                          const unsigned char* ucpVeri, unsigned int uiBoy)
{
    (void)spBus;
    (void)uiBoy;
    if (ucAdres == 0x70U)
    {
        S_ucMuxKanal = ucpVeri[0];
        return 0;
    }
    if (ucAdres == 0x4AU)
    {
        S_ucPointer = ucpVeri[0];
        return 0;
    }
    if (ucAdres == 0x48U)
    {
        S_uiPort48++;
    }
    return 1;
}

int spec2codeI2cPortRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char* ucpVeri,
                         unsigned int uiBoy)
{
    unsigned int uiIndex;

    (void)spBus;
    if ((ucAdres == 0x4AU) && (S_ucMuxKanal == (1U << 1)))
    {
        for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
        {
            ucpVeri[uiIndex] = S_ucArrTmp[S_ucPointer][uiIndex];
        }
        return 0;
    }
    if (ucAdres == 0x48U)
    {
        S_uiPort48++;
    }
    return 1;
}

int spec2codeSpiPortTransfer(SSpec2codeSpiBus* spBus, unsigned char ucSelect,
                             const unsigned char* ucpTx, unsigned char* ucpRx, unsigned int uiBoy)
{
    (void)spBus;
    (void)ucSelect;
    (void)ucpTx;
    (void)uiBoy;
    if (ucpRx != (unsigned char*)0)
    {
        ucpRx[0] = 0U;
        ucpRx[1] = 0U;
        ucpRx[2] = 0x05U;
    }
    return 0;
}

static void yazdir(const char* cpEtiket, int iStatus, const SSistemCit* spCit,
                   const SSistemCitBus* spBus)
{
    printf("%s read=%d hata=%u ltc[ok=%u%u%u%u hata=%u v1=%u v8=%u t=%d] tmp[t=%d ok=%u] "
           "lmk[pll1=%u] sim=%u port48=%u\n",
           cpEtiket, iStatus, spCit->uiHataSayac,
           spCit->sU2Ltc2991.sBayraklar.uiStatusLowOk, spCit->sU2Ltc2991.sBayraklar.uiStatusHighOk,
           spCit->sU2Ltc2991.sBayraklar.uiVoltageReadOk,
           spCit->sU2Ltc2991.sBayraklar.uiTemperatureReadOk, spCit->sU2Ltc2991.uiHataSayac,
           spCit->sU2Ltc2991.usArrVoltageRead[0], spCit->sU2Ltc2991.usArrVoltageRead[7],
           spCit->sU2Ltc2991.iTemperatureRead, spCit->sU3Tmp101.iTemperatureRead,
           spCit->sU3Tmp101.sBayraklar.uiTemperatureReadOk, spCit->sU4Lmk04832.ucPll1LockDetect,
           spBus->sPlI2c0.uiSimSayac, S_uiPort48);
}

int main(void)
{
    static SSistemCitBus S_sBus;
    static SSistemCitBus S_sSanalBus;
    static SSistemCitSim S_sSim;
    static SSistemCit S_sCit;
    int iStatus;

    S_ucArrTmp[0][0] = 0x19U; /* 25.0 C */
    S_ucArrTmp[0][1] = 0x00U;

    /* --- Karisik mod: switch + TMP101 "gercek" (port), LTC2991 sanal --- */
    sistemCitBusVarsayilan(&S_sBus);
    sistemCitSimKur(&S_sSim);
    ltc2991SimKanalAyarla(&S_sSim.sU2Ltc2991, 0U, 1200);
    ltc2991SimSicaklikAyarla(&S_sSim.sU2Ltc2991, -1050);
    (void)spec2codeI2cSimEkle(&S_sBus.sPlI2c0, &S_sSim.sU2Ltc2991.sCihaz);
    iStatus = sistemCitInit(&S_sBus);
    printf("init=%d ltcyazim=%u\n", iStatus, S_sSim.sU2Ltc2991.uiYazmaSayac);
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    yazdir("karisik", iStatus, &S_sCit, &S_sBus);

    /* --- Hata enjeksiyonu: hazir biti hic gelmez -> olcumler zaman asimi --- */
    ltc2991SimHataAyarla(&S_sSim.sU2Ltc2991, SPEC2CODE_SIM_HATA_HAZIR_YOK);
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    yazdir("hazir-yok", iStatus, &S_sCit, &S_sBus);

    /* --- NACK: cihaz hatta yok gibi -> LTC'nin 4 erisimi de duser --- */
    ltc2991SimHataAyarla(&S_sSim.sU2Ltc2991, SPEC2CODE_SIM_HATA_NACK);
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    yazdir("nack", iStatus, &S_sCit, &S_sBus);

    /* --- Sanal cihazi cikar: 0x48 artik porta (gercek) gider ve NACK alir --- */
    (void)spec2codeI2cSimKaldir(&S_sBus.sPlI2c0, &S_sSim.sU2Ltc2991.sCihaz);
    iStatus = sistemCitRead(&S_sBus, &S_sCit);
    yazdir("kaldir", iStatus, &S_sCit, &S_sBus);

    /* --- Tam sanal: donanim yok, switch + iki entegre sanal --- */
    sistemCitBusVarsayilan(&S_sSanalBus);
    S_sSanalBus.sPlI2c0.eSurucu = SPEC2CODE_I2C_SURUCU_SIM;
    sistemCitSimKur(&S_sSim);
    (void)sistemCitSimSwitchEkle(&S_sSanalBus, &S_sSim);
    (void)sistemCitSimEkle(&S_sSanalBus, &S_sSim);
    iStatus = sistemCitInit(&S_sSanalBus);
    printf("sanal init=%d kanal=0x%02X\n", iStatus, S_sSim.sU1Tca9548a.ucKontrol);
    iStatus = sistemCitRead(&S_sSanalBus, &S_sCit);
    yazdir("sanal", iStatus, &S_sCit, &S_sSanalBus);
    return 0;
}
"""


class CitLayerSimulationTests(unittest.TestCase):
    """Sanal cihaz zinciri: karisik mod, hata enjeksiyonu, cikarma, tam sanal kosum."""

    def test_generated_simulator_files_and_api(self) -> None:
        out_dir = _generate(_axi_spec("unit_cit_layer_simgen"))
        try:
            cit = out_dir / "cit"
            for rel in ("hal/spec2code_i2c_sim.h", "hal/spec2code_i2c_sim.c",
                        "sim/ltc2991_sim.h", "sim/ltc2991_sim.c", "sim/tmp101_sim.h", "sim/tmp101_sim.c"):
                self.assertTrue((cit / rel).is_file(), rel)
            self.assertFalse((cit / "sim/lmk04832_sim.h").exists())  # SPI simulasyonu sonraki faz
            bus = (cit / "hal/spec2code_i2c_bus.h").read_text(encoding="utf-8")
            self.assertIn("SPEC2CODE_I2C_SURUCU_SIM = 4", bus)
            self.assertIn("int spec2codeI2cSimEkle(SSpec2codeI2cBus* spBus, SSpec2codeI2cSimCihaz* spCihaz);", bus)
            ltc = (cit / "sim/ltc2991_sim.h").read_text(encoding="utf-8")
            for api in ("void ltc2991SimKur(SLtc2991Sim* spSim, unsigned char ucAdres);",
                        "void ltc2991SimKanalAyarla(SLtc2991Sim* spSim, unsigned char ucKanal, int iMv);",
                        "void ltc2991SimHataAyarla(SLtc2991Sim* spSim, unsigned int uiHataModu);"):
                self.assertIn(api, ltc)
            sistem = (cit / "spec2code_cit_sistem.h").read_text(encoding="utf-8")
            self.assertIn("SSpec2codeI2cSimSwitch sU1Tca9548a;", sistem)
            self.assertIn("SLtc2991Sim sU2Ltc2991;", sistem)
            self.assertIn("int sistemCitSimEkle(SSistemCitBus* spBus, SSistemCitSim* spSim);", sistem)
            self.assertIn("int sistemCitSimSwitchEkle(SSistemCitBus* spBus, SSistemCitSim* spSim);", sistem)
            tmp = (cit / "sim/tmp101_sim.c").read_text(encoding="utf-8")
            self.assertIn("S_ucArrTmp101SimReset", tmp)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_mixed_mode_and_fault_injection_round_trip(self) -> None:
        compiler = _find_cc()
        if compiler is None:
            self.skipTest("gcc/cc bulunamadi")
        out_dir = _generate(_axi_spec("unit_cit_layer_sim"))
        try:
            cit = out_dir / "cit"
            (cit / "main.c").write_text(_SIM_MAIN, encoding="utf-8")
            binary = cit / "cit_sim_host"
            sources = [str(p) for p in [*(cit / "hal").glob("*.c"), *cit.glob("*.c"),
                                        *(cit / "sim").glob("*.c")]]
            cmd = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-DSPEC2CODE_CIT_PORT_XIIC=0", "-DSPEC2CODE_CIT_PORT_XSPI=0",
                   "-DSPEC2CODE_CIT_PORT_KULLANICI=1",
                   "-I", str(cit / "hal"), "-I", str(cit), "-I", str(cit / "sim"),
                   "-o", str(binary)] + sources
            compile_run = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)
        lines = output.strip().splitlines()
        # init: LTC'nin 4 profil yazimi sanal cihaza gitti
        self.assertEqual(lines[0], "init=0 ltcyazim=4", output)
        # karisik: LTC sanal (1200 mV -> 1199, -10.50 C), TMP101 "gercek" port; porta 0x48 hic gitmedi
        self.assertTrue(lines[1].startswith(
            "karisik read=0 hata=0 ltc[ok=1111 hata=0 v1=1199 v8=3299 t=-1050] tmp[t=2500 ok=1] "
            "lmk[pll1=1] sim="), output)
        self.assertTrue(lines[1].endswith(" port48=0"), output)
        # hazir-yok: durum registerleri okunur (2 ok), iki olcum zaman asimi
        self.assertIn("hazir-yok read=1 hata=2 ltc[ok=1100 hata=2", lines[2])
        self.assertIn("tmp[t=2500 ok=1]", lines[2])
        # nack: LTC'nin 4 erisimi de duser, TMP101 etkilenmez
        self.assertIn("nack read=1 hata=4 ltc[ok=0000 hata=4", lines[3])
        self.assertIn("tmp[t=2500 ok=1]", lines[3])
        # kaldir: adres gercek porta gider (port48 > 0) ve NACK alir
        self.assertIn("kaldir read=1 hata=4 ltc[ok=0000 hata=4", lines[4])
        self.assertNotIn("port48=0", lines[4])
        # tam sanal: switch son secilen kanali tasir (TMP101 kanal 1 -> 0x02), her sey okunur
        self.assertEqual(lines[5], "sanal init=0 kanal=0x02", output)
        self.assertIn("sanal read=0 hata=0 ltc[ok=1111 hata=0 v1=3299 v8=3299 t=2500] tmp[t=0 ok=1]",
                      lines[6])


if __name__ == "__main__":
    unittest.main()
