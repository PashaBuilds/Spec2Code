"""Surucu struct API'si + CIT ust katmani (cit/) + Xilinx-seviyesi simulasyon (tests/sim).

Tasarim: docs/superpowers/specs/2026-09-06-driver-struct-api-design.md

  * drivers/: S<Mod>Status (bit bit) + <mod>StatusRegistersRead, dizi op'lari icin
    S<Mod>Voltage; kullaniciya giden dosyalarda `spec2code` adi YOK (dbg_printf.h).
  * cit/: surucu fonksiyonlarini cagirir, limitle anlamlandirir (S<Mod>CitLimit, OK bitleri).
  * tests/sim/: -include ile Xilinx veri-yolu cagrilarina araya girer; ajan dispatch'i
    GERCEK surucuyu cagirir, sarmalayici yok.
  * Host round-trip: tests/xilinx_stubs + gcc ile drivers+cit+sim gercek derleyicide kosar.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from orchestrator import cit_layer, codegen

ROOT = Path(__file__).resolve().parents[1]
STUBS = ROOT / "tests" / "xilinx_stubs"
ERR_LINE = 'dbg_printf(DEBUG_LEVEL_ERROR, "TRACEERR|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d", '


def _find_cc() -> str | None:
    return shutil.which("gcc") or shutil.which("cc")


def _axi_spec(name: str) -> dict:
    """MicroBlaze: AXI IIC (mux arkasinda LTC2991 + TMP101) + AXI SPI (LMK04832)."""
    base = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    return {
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
                        "internal_temperature": True, "vcc_read": False,
                        "cit": {"measurements": [
                            {"op": "voltage_read", "channel": 0, "name": "VCC_3V3", "min": 3135, "max": 3465,
                             "severity": "critical"}]}},
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


def _generate(spec: dict) -> Path:
    out_dir = Path(tempfile.mkdtemp(prefix="s2c_cit_layer_"))
    codegen.generate(spec, out_dir)
    return out_dir


def _read(out_dir: Path, rel: str) -> str:
    return (out_dir / rel).read_text(encoding="utf-8")


class BitfieldLayoutTests(unittest.TestCase):
    def test_gcc_unit_allocation(self) -> None:
        self.assertEqual(cit_layer.bitfield_bytes([1] * 20), 4)
        self.assertEqual(cit_layer.bitfield_bytes([1] * 33), 8)
        self.assertEqual(cit_layer.bitfield_bytes([8, 8, 8, 8, 1]), 8)
        self.assertEqual(cit_layer.bitfield_bytes([]), 0)


class DriverStructApiTests(unittest.TestCase):
    """drivers/: ham veri surucu struct'larinda; kullaniciya spec2code adi gitmez."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_dir = _generate(_axi_spec("unit_driver_struct_api"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.out_dir, ignore_errors=True)

    def test_status_struct_is_bit_exact_with_raw_bytes(self) -> None:
        header = _read(self.out_dir, "drivers/ltc2991.h")
        self.assertIn("typedef struct", header)
        self.assertIn("unsigned int uiV1Ready : 1; /* STATUS_LOW bit 0 */", header)
        self.assertIn("unsigned int uiBusy : 1; /* STATUS_HIGH bit 2 */", header)
        self.assertIn("unsigned char ucStatusLow; /* ham STATUS_LOW (0x00) */", header)
        self.assertIn("} SLtc2991Status;", header)
        self.assertIn("int ltc2991StatusRegistersRead(const SI2cCihaz* spCihaz, SLtc2991Status* spStatus);", header)
        source = _read(self.out_dir, "drivers/ltc2991.c")
        self.assertIn("spStatus->uiV2Ready = (unsigned int)((spStatus->ucStatusLow >> 1U) & 0x1U);", source)
        # mux arkasindaki cihaz: durum okumasi da kanal secer
        # Switch secimi calisma zamaninda tablo satirindan (ucSwitchAdres != 0).
        self.assertIn("iStatus = tca9548aChannelSelect(spCihaz->spIic, spCihaz->ucSwitchAdres, spCihaz->ucSwitchKanal);", source)

    def test_array_op_fills_driver_struct(self) -> None:
        header = _read(self.out_dir, "drivers/ltc2991.h")
        self.assertIn("unsigned short usArrVoltage[8];", header)
        self.assertIn("} SLtc2991Voltage;", header)
        self.assertIn("int ltc2991VoltageRead(const SI2cCihaz* spCihaz, SLtc2991Voltage* spVoltage);", header)
        source = _read(self.out_dir, "drivers/ltc2991.c")
        # Donusum ayri STATIK yardimcida: op govdesi yalniz okur, helper mask/isaret/olcek/kirpma yapar.
        self.assertIn("static int ltc2991VoltageConvert(unsigned int uiRaw)", source)
        self.assertIn("spVoltage->usArrVoltage[ucIndex] = (unsigned short)ltc2991VoltageConvert(((unsigned int)ucMsb << 8U) | (unsigned int)ucLsb);", source)
        self.assertIn("static int ltc2991TemperatureConvert(unsigned int uiRaw)", source)
        self.assertIn("*ipTemperature = (int)ltc2991TemperatureConvert(", source)
        # skaler op degismez
        self.assertIn("int ltc2991TemperatureRead(const SI2cCihaz* spCihaz, int* ipTemperature);", header)

    def test_spi_tics_device_gets_status_struct(self) -> None:
        header = _read(self.out_dir, "drivers/lmk04832.h")
        self.assertIn("} SLmk04832Status;", header)
        self.assertIn("int lmk04832StatusRegistersRead(XSpi* spSpi, SLmk04832Status* spStatus);", header)

    def test_user_facing_files_have_no_spec2code_names(self) -> None:
        drivers = self.out_dir / "drivers"
        cit = self.out_dir / "cit"
        for path in [*drivers.rglob("*"), *cit.rglob("*")]:
            if path.is_file():
                self.assertNotIn("spec2code", path.name.lower(), path.name)
                self.assertNotIn("spec2code", path.read_text(encoding="utf-8").lower().replace("generated by spec2code", ""),
                                 f"{path.name} icinde spec2code sembolu")
        self.assertTrue((drivers / "dbg_printf.h").is_file())
        dbg = _read(self.out_dir, "drivers/dbg_printf.h")
        self.assertIn("#define DEBUG_LEVEL_ALWAYS 0U", dbg)
        self.assertIn("#define DEBUG_LEVEL_TRACE 5U", dbg)
        self.assertIn("#define DEBUG_LEVEL_DEFAULT DEBUG_LEVEL_ERROR", dbg)
        self.assertIn("void dbg_printf(unsigned int uiLevel, const char* cpFormat, ...);", dbg)
        driver = _read(self.out_dir, "drivers/ltc2991.c")
        self.assertIn("dbgTraceI2c(spCihaz->ucAdres, ucReg, 'r', ucpValue, 1U);", driver)
        self.assertIn(ERR_LINE + "spCihaz->ucAdres, ucReg, 'p', iStatus);", driver)
        self.assertNotIn("bus_trace", driver)

    def test_self_test_uses_struct_api(self) -> None:
        test = _read(self.out_dir, "tests/ltc2991_test.c")
        self.assertIn("SLtc2991Voltage sVoltage;", test)
        self.assertIn("SLtc2991Status sStatusRegs;", test)
        self.assertIn("iStatus = ltc2991StatusRegistersRead(spCihaz, &sStatusRegs);", test)
        self.assertIn("iStatus = ltc2991VoltageRead(spCihaz, &sVoltage);", test)

    def test_testbench_dispatch_uses_struct_api(self) -> None:
        ops = _read(self.out_dir, "tests/unit_driver_struct_api_testbench_ops.c")
        self.assertIn("SLtc2991Voltage sVoltage;", ops)
        self.assertIn("iStatus = ltc2991VoltageRead(spCihaz, &sVoltage);", ops)
        self.assertIn("sVoltage.usArrVoltage[uiIndex]", ops)
        self.assertNotIn("usArrValues", ops)
        self.assertNotIn("spec2codeSanal", ops)


class CitLayerGenerationTests(unittest.TestCase):
    """cit/: surucu uzerinde ust seviye anlamlandirma."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.out_dir = _generate(_axi_spec("unit_cit_layer_gen"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.out_dir, ignore_errors=True)

    def test_tree(self) -> None:
        for rel in ("cit/cit_ortak.h", "cit/cit_ortak.c", "cit/ltc2991_cit.h", "cit/ltc2991_cit.c",
                    "cit/tmp101_cit.h", "cit/lmk04832_cit.h", "cit/sistem_cit.h", "cit/sistem_cit.c"):
            self.assertTrue((self.out_dir / rel).is_file(), rel)
        self.assertFalse((self.out_dir / "cit" / "hal").exists())
        self.assertFalse((self.out_dir / "cit" / "sim").exists())
        self.assertIn(b"\r\n", (self.out_dir / "cit/ltc2991_cit.h").read_bytes())

    def test_ltc2991_cit_limits_flags_and_driver_calls(self) -> None:
        header = _read(self.out_dir, "cit/ltc2991_cit.h")
        self.assertIn('#include "ltc2991.h"', header)
        self.assertIn("SCitLimit sV1; /* VCC_3V3 (voltage_read, mV) */", header)
        self.assertIn("SCitLimit sTemperature;", header)
        # spec limiti varsayilana gomulur: {min, max, limitVar, etkin}
        self.assertIn("{3135, 3465, 1U, 1U},", header)
        self.assertIn("unsigned int uiVoltageReadOkundu : 1;", header)
        self.assertIn("unsigned int uiV1Ok : 1; /* VCC_3V3: okundu VE limit icinde", header)
        self.assertIn("SLtc2991Status sDurum;", header)
        self.assertIn("SLtc2991Voltage sVoltage;", header)
        self.assertIn("int iTemperature;", header)
        self.assertIn("int ltc2991CitRead(const SI2cCihaz* spCihaz, const SLtc2991CitLimit* spLimit, SLtc2991Cit* spCit);", header)
        source = _read(self.out_dir, "cit/ltc2991_cit.c")
        self.assertIn("iStatus = ltc2991StatusRegistersRead(spCihaz, &spCit->sDurum);", source)
        self.assertIn("iStatus = ltc2991VoltageRead(spCihaz, &spCit->sVoltage);", source)
        self.assertIn("spCit->sBayraklar.uiV1Ok = citLimitDegerlendir(&spLimit->sV1, (int)spCit->sVoltage.usArrVoltage[0U]);", source)
        self.assertIn("return (ltc2991DeviceInit(spCihaz) == XST_SUCCESS) ? CIT_OK : CIT_HATA;", source)
        # cit dogrudan Xilinx veri-yolu cagirmaz: surucu uzerinden gider
        self.assertNotIn("XIic_", source)

    def test_lmk04832_cit_on_spi_driver(self) -> None:
        header = _read(self.out_dir, "cit/lmk04832_cit.h")
        self.assertIn("SCitLimit sPll1LockDetect;", header)
        self.assertIn("unsigned int uiPll1LockDetectOkundu : 1;", header)
        self.assertIn("unsigned int uiPll1LockDetectOk : 1;", header)
        self.assertIn("unsigned char ucPll1LockDetect;", header)
        self.assertIn("int lmk04832CitRead(XSpi* spSpi, const SLmk04832CitLimit* spLimit, SLmk04832Cit* spCit);", header)

    def test_system_aggregate(self) -> None:
        header = _read(self.out_dir, "cit/sistem_cit.h")
        self.assertIn("XIic* sPlI2c0; /* pl_i2c_0 (XPAR_AXI_IIC_0) */", header)
        self.assertIn("XSpi* sPlSpi0; /* pl_spi_0 (XPAR_AXI_QUAD_SPI_0) */", header)
        self.assertIn("SLtc2991CitLimit sU2Ltc2991;", header)
        self.assertIn("SLtc2991Cit sU2Ltc2991;", header)
        self.assertIn("#define SISTEM_CIT_LIMIT_VARSAYILAN", header)
        self.assertIn("int sistemCitRead(SSistemCitBus* spBus, const SSistemCitLimit* spLimit, SSistemCit* spCit);", header)
        source = _read(self.out_dir, "cit/sistem_cit.c")
        self.assertIn("static XIic S_sPlI2c0Instance;", source)
        self.assertIn("spBus->sPlI2c0 = &S_sPlI2c0Instance;", source)
        self.assertIn("static XSpi S_sPlSpi0Instance;", source)
        self.assertIn("iStatus = ltc2991CitRead(i2cCihaz(I2C_CIHAZ_U2_LTC2991), &spLimit->sU2Ltc2991, &spCit->sU2Ltc2991);", source)
        self.assertIn("i2cCihazlarInit(spBus->sPlI2c0);", source)
        self.assertNotIn("uiHataSayac", source)

    def test_readme_documents_the_layer(self) -> None:
        readme = _read(self.out_dir, "README.md")
        self.assertIn("## CIT ust katmani (`cit/`)", readme)
        self.assertIn("`cit/ltc2991_cit.h/.c`", readme)
        self.assertNotIn("cit/hal/", readme)


class SimulatedDeviceAgentTests(unittest.TestCase):
    """`devices[].simulate`: tests/sim + ajan kaydi; surucu ve dispatch degismez."""

    def test_simulated_devices_register_simulators_and_no_shims(self) -> None:
        spec = _axi_spec("unit_sim_agent")
        for device in spec["devices"]:
            if device["id"] in ("u2_ltc2991", "u3_tmp101", "u4_lmk04832"):
                device["simulate"] = True
        out_dir = _generate(spec)
        try:
            for rel in ("tests/sim/spec2code_sim.h", "tests/sim/spec2code_sim.c", "tests/sim/spec2code_sim_xilinx.h",
                        "tests/sim/ltc2991_sim.h", "tests/sim/ltc2991_sim.c", "tests/sim/lmk04832_sim.c"):
                self.assertTrue((out_dir / rel).is_file(), rel)
            interpose = _read(out_dir, "tests/sim/spec2code_sim_xilinx.h")
            self.assertIn("#define XIic_DynSend spec2codeSimXIicDynSend", interpose)
            self.assertIn("#define XSpi_Transfer spec2codeSimXSpiTransfer", interpose)
            ops = _read(out_dir, "tests/unit_sim_agent_testbench_ops.c")
            self.assertIn("static SLtc2991Sim S_sSimU2Ltc2991;", ops)
            self.assertIn("ltc2991SimKur(&S_sSimU2Ltc2991, 0x48U);", ops)
            self.assertIn("(void)spec2codeSimI2cEkle(&S_sSimU2Ltc2991.sCihaz);", ops)
            self.assertIn("lmk04832SimKur(&S_sSimU4Lmk04832, (unsigned char)LMK04832_SPI_SELECT);", ops)
            # mux arkasindaki HER cihaz sanal -> sanal switch de kaydedilir
            self.assertIn("spec2codeSimSwitchKur(&S_sSimSwitchU1Tca9548a, 0x70U);", ops)
            self.assertIn("    spec2codeSimHazirla();", ops)
            # dispatch GERCEK surucuyu cagirir; sarmalayici yok
            self.assertIn("iStatus = ltc2991VoltageRead(spCihaz, &sVoltage);", ops)
            self.assertNotIn("spec2codeSanal", ops)
            manifest = json.loads(_read(out_dir, "tests/spec2code_testbench_manifest.json"))
            self.assertTrue(all(d.get("simulated") for d in manifest["devices"]))
            # suruculer sim'i bilmez
            self.assertNotIn("spec2code_sim", _read(out_dir, "drivers/ltc2991.c"))
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_partial_simulation_keeps_real_mux(self) -> None:
        spec = _axi_spec("unit_sim_partial")
        spec["devices"][0]["simulate"] = True  # yalniz LTC2991; TMP101 ayni mux'ta gercek
        out_dir = _generate(spec)
        try:
            ops = _read(out_dir, "tests/unit_sim_partial_testbench_ops.c")
            self.assertIn("static SLtc2991Sim S_sSimU2Ltc2991;", ops)
            self.assertNotIn("S_sSimSwitch", ops)
            self.assertFalse((out_dir / "tests/sim/tmp101_sim.c").exists())
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)

    def test_unmarked_project_has_no_sim_dir(self) -> None:
        out_dir = _generate(_axi_spec("unit_sim_none"))
        try:
            self.assertFalse((out_dir / "tests" / "sim").exists())
            ops = _read(out_dir, "tests/unit_sim_none_testbench_ops.c")
            self.assertNotIn("spec2codeSimHazirla", ops)
            self.assertNotIn("simulated", _read(out_dir, "tests/spec2code_testbench_manifest.json"))
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


_HOST_XPARAMETERS = """#ifndef XPARAMETERS_H
#define XPARAMETERS_H
#define XPAR_XIIC_NUM_INSTANCES 1
#define XPAR_XSPI_NUM_INSTANCES 1
#define XPAR_XIICPS_NUM_INSTANCES 0
#define XPAR_XSPIPS_NUM_INSTANCES 0
#define XPAR_AXI_IIC_0_BASEADDR 0x40800000UL
#define XPAR_AXI_IIC_0_DEVICE_ID 0U
#define XPAR_AXI_QUAD_SPI_0_DEVICE_ID 0U
#endif
"""

_HOST_MAIN = r"""
#include <stdio.h>
#include "sistem_cit.h"
#include "spec2code_sim.h"
#include "ltc2991_sim.h"
#include "tmp101_sim.h"
#include "lmk04832_sim.h"

extern unsigned int g_uiStubGercekI2c;
extern unsigned int g_uiStubGercekSpi;

static SLtc2991Sim S_sLtc;
static STmp101Sim S_sTmp;
static SLmk04832Sim S_sLmk;
static SSpec2codeI2cSimSwitch S_sSwitch;
static SSistemCitBus S_sBus;
static SSistemCit S_sCit;

int main(void)
{
    SSistemCitLimit sLimit = SISTEM_CIT_LIMIT_VARSAYILAN;
    int iInit;
    int iRead;

    ltc2991SimKur(&S_sLtc, 0x48U);
    (void)spec2codeSimI2cEkle(&S_sLtc.sCihaz);
    tmp101SimKur(&S_sTmp, 0x4AU);
    (void)spec2codeSimI2cEkle(&S_sTmp.sCihaz);
    lmk04832SimKur(&S_sLmk, (unsigned char)LMK04832_SPI_SELECT);
    (void)spec2codeSimSpiEkle(&S_sLmk.sCihaz);
    spec2codeSimSwitchKur(&S_sSwitch, 0x70U);
    (void)spec2codeSimI2cEkle(&S_sSwitch.sCihaz);
    ltc2991SimKanalAyarla(&S_sLtc, 0U, 3300);
    ltc2991SimKanalAyarla(&S_sLtc, 7U, 1200);

    sistemCitBusVarsayilan(&S_sBus);
    iInit = sistemCitInit(&S_sBus);
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("A init=%d read=%d gercek=%u/%u switch=%u\n", iInit, iRead, g_uiStubGercekI2c, g_uiStubGercekSpi,
           S_sSwitch.uiSecimSayac);
    printf("B ltc statusOk=%u voltOk=%u v1ok=%u v1=%u v8=%u busy=%u v1v2en=%u temp=%d\n",
           S_sCit.sU2Ltc2991.sBayraklar.uiStatusRegistersOkundu, S_sCit.sU2Ltc2991.sBayraklar.uiVoltageReadOkundu,
           S_sCit.sU2Ltc2991.sBayraklar.uiV1Ok, S_sCit.sU2Ltc2991.sVoltage.usArrVoltage[0],
           S_sCit.sU2Ltc2991.sVoltage.usArrVoltage[7], S_sCit.sU2Ltc2991.sDurum.uiBusy,
           S_sCit.sU2Ltc2991.sDurum.uiV1V2Enable, S_sCit.sU2Ltc2991.iTemperature);
    printf("C tmp tempOk=%u temp=%d lmk pll1=%u pll1ok=%u\n", S_sCit.sU3Tmp101.sBayraklar.uiTemperatureOk,
           S_sCit.sU3Tmp101.iTemperature, S_sCit.sU4Lmk04832.ucPll1LockDetect,
           S_sCit.sU4Lmk04832.sBayraklar.uiPll1LockDetectOk);
    /* V1 spec limiti 3135..3465: 3300 OK; 2000'e cekince NOK */
    ltc2991SimKanalAyarla(&S_sLtc, 0U, 2000);
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("D read=%d v1ok=%u v1=%u\n", iRead, S_sCit.sU2Ltc2991.sBayraklar.uiV1Ok,
           S_sCit.sU2Ltc2991.sVoltage.usArrVoltage[0]);
    /* Kapali aralik, min == max: LMK pll1 tam 1 -> OK; 0..0 -> NOK */
    sLimit.sU4Lmk04832.sPll1LockDetect.iMin = 1;
    sLimit.sU4Lmk04832.sPll1LockDetect.iMax = 1;
    sLimit.sU4Lmk04832.sPll1LockDetect.uiLimitVar = 1U;
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("H esit1 pll1ok=%u", S_sCit.sU4Lmk04832.sBayraklar.uiPll1LockDetectOk);
    sLimit.sU4Lmk04832.sPll1LockDetect.iMin = 0;
    sLimit.sU4Lmk04832.sPll1LockDetect.iMax = 0;
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf(" esit0 pll1ok=%u\n", S_sCit.sU4Lmk04832.sBayraklar.uiPll1LockDetectOk);
    sLimit.sU4Lmk04832.sPll1LockDetect.uiLimitVar = 0U;
    /* etkin=0 -> degerlendirilmez */
    sLimit.sU2Ltc2991.sV1.uiEtkin = 0U;
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("E read=%d v1ok=%u\n", iRead, S_sCit.sU2Ltc2991.sBayraklar.uiV1Ok);
    /* NACK: LTC hattan dusmus gibi; TMP/LMK etkilenmez */
    ltc2991SimHataAyarla(&S_sLtc, SPEC2CODE_SIM_HATA_NACK);
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("F read=%d ltcVoltOkundu=%u statusOk=%u tmpOkundu=%u lmkOkundu=%u\n", iRead,
           S_sCit.sU2Ltc2991.sBayraklar.uiVoltageReadOkundu, S_sCit.sU2Ltc2991.sBayraklar.uiStatusRegistersOkundu,
           S_sCit.sU3Tmp101.sBayraklar.uiTemperatureReadOkundu, S_sCit.sU4Lmk04832.sBayraklar.uiPll1LockDetectOkundu);
    /* sanal cihaz kaldirilinca gercek hat (stub: basarisiz) kullanilir */
    (void)spec2codeSimI2cKaldir(&S_sTmp.sCihaz);
    iRead = sistemCitRead(&S_sBus, &sLimit, &S_sCit);
    printf("G tmpOkundu=%u gercek=%u\n", S_sCit.sU3Tmp101.sBayraklar.uiTemperatureReadOkundu, g_uiStubGercekI2c);
    return 0;
}
"""


@unittest.skipUnless(_find_cc(), "host C compiler required")
class CitLayerHostRoundTripTests(unittest.TestCase):
    """drivers + cit + tests/sim gercek derleyicide: Xilinx stub'lari + -include araya-girme."""

    def test_system_read_over_virtual_devices(self) -> None:
        spec = _axi_spec("unit_cit_host_rt")
        for device in spec["devices"]:
            device["simulate"] = True
        out_dir = _generate(spec)
        try:
            work = out_dir / "host"
            work.mkdir()
            (work / "xparameters.h").write_text(_HOST_XPARAMETERS, encoding="utf-8")
            (work / "main.c").write_text(_HOST_MAIN, encoding="utf-8")
            binary = work / ("cit_host.exe" if os.name == "nt" else "cit_host")
            sources = [str(work / "main.c"), str(STUBS / "xilinx_stubs.c"),
                       *[str(p) for p in (out_dir / "drivers").glob("*.c")],
                       *[str(p) for p in (out_dir / "cit").glob("*.c")],
                       *[str(p) for p in (out_dir / "tests" / "sim").glob("*.c")]]
            cmd = [_find_cc(), "-std=c99", "-Wall", "-Wextra", "-Werror",
                   "-include", "spec2code_sim_xilinx.h",
                   "-I", str(work), "-I", str(STUBS), "-I", str(out_dir / "drivers"),
                   "-I", str(out_dir / "cit"), "-I", str(out_dir / "tests" / "sim"),
                   "-o", str(binary), *sources]
            build = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            # dbg_printf (varsayilan ERROR esigi) stub hattaki TRACEERR satirlarini da basar; yalniz A..G.
            lines = {line.split()[0]: line for line in run.stdout.strip().splitlines()
                     if len(line.split()) > 1 and line.split()[0] in "ABCDEFGH"}
            # A: hepsi sanal -> gercek hatta HIC transfer yok; mux switch kanal secti
            self.assertIn("init=0 read=0 gercek=0/0", lines["A"])
            self.assertNotIn("switch=0", lines["A"])
            # B: LTC2991 durum bitleri + kanal degerleri + sicaklik (davranis blogu)
            self.assertIn("statusOk=1 voltOk=1 v1ok=1 v1=3299 v8=1199 busy=0 v1v2en=1 temp=2500", lines["B"])
            # C: TMP101 sicaklik okundu ve OK, LMK PLL1 kilitli
            self.assertIn("tempOk=1", lines["C"])
            self.assertIn("pll1=1 pll1ok=1", lines["C"])
            # D: V1 limit disi -> NOK
            self.assertIn("read=1 v1ok=0 v1=1999", lines["D"])
            # H: kapali aralik, min == max (1..1 OK, 0..0 NOK)
            self.assertIn("esit1 pll1ok=1 esit0 pll1ok=0", lines["H"])
            # E: etkin degil -> OK sayilir
            self.assertIn("read=0 v1ok=1", lines["E"])
            # F: NACK -> LTC'nin 3 surucu cagrisi duser, digerleri temiz
            self.assertIn("read=2 ltcVoltOkundu=0 statusOk=0 tmpOkundu=1 lmkOkundu=1", lines["F"])
            # G: kaydi kaldirilan TMP101 gercek (stub) hatta gider ve duser
            self.assertIn("tmpOkundu=0", lines["G"])
            self.assertNotIn("gercek=0", lines["G"])
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
