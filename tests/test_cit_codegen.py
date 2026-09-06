"""CIT codegen — SBoardCit + boardCitRun (cit/ katmani uzerinden) + CIT_RUN/CIT_READ.

Uretilen spec2code_cit.h/.c dosyalarinin (a) header sekli/bit isimleri/
_Static_assert'leri, (b) boardCitRun'in cit/ katmanini (sistemCitRead) kosup manifest
sirasiyla SBoardCit'e kopyalamasi, ve (c) host derleme round-trip'i (drivers + cit +
tests/sim sanal cihazlar + xilinx stub'lari; CIT_RUN/CIT_READ cerceveleri MesajIsle'den
gecirilir) dogrulanir.

Bit alani bayt yerlesimi: ilk olcum bit 0 (LSB-first, little-endian unsigned int
container — GCC/ARM EABI). Python tarafinda `flags_word & (1 << i)` ile okunur.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

from backend import s2cmsg
from orchestrator import codegen

ROOT = Path(__file__).resolve().parent.parent
STUBS = ROOT / "tests" / "xilinx_stubs"


def _find_cc() -> str | None:
    return shutil.which("gcc") or shutil.which("cc")


def _cit_spec(project_name: str, *, simulate: bool = False) -> dict:
    """MicroBlaze/AXI: LTC2991 (mux ch3) + TMP101 (mux ch1) + LMK04832 (AXI SPI).

    Olcum sirasi (manifest cit.olcumler ile birebir; voltage_read dizi donuslu
    (voltages[8]) oldugundan KANAL BASINA olcum acilir):
      0..7: u2_ltc2991 voltage_read V1..V8 -> V1 = VCC_3V3 (limit 3135..3465)
      8:    u2_ltc2991 temperature_read
      9:    u3_tmp101  temperature_read
      10:   u4_lmk04832 pll1_lock_detect
      11:   u4_lmk04832 pll2_lock_detect
    """
    base = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    return {
        "schema_version": base.get("schema_version", "1.0"),
        "project": {"name": project_name, "platform": "microblaze_7series", "target_core": "microblaze_0",
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
             "tests_requested": ["self_test"], "simulate": simulate},
            {"id": "u3_tmp101", "part": "TMP101", "descriptor_ref": "descriptors/tmp101.yaml",
             "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x4A",
                        "via_mux": {"mux_id": "u1_tca9548a", "channel": 1}},
             "config": {"cit": {"measurements": [
                 {"op": "temperature_read", "name": "TMP_TEMP", "min": 2000, "max": 3000, "severity": "warning"}]}},
             "operations_requested": ["device_init", "temperature_read", "config_read"],
             "tests_requested": ["self_test"], "simulate": simulate},
            {"id": "u4_lmk04832", "part": "LMK04832", "descriptor_ref": "descriptors/lmk04832.yaml",
             "attach": {"controller_id": "pl_spi_0", "spi_chip_select": 0},
             "config": {"ticspro_registers": ["0x000010", "0x016302", "0x018300", "0x017300"]},
             "operations_requested": ["device_init", "pll1_lock_detect", "pll2_lock_detect"],
             "tests_requested": ["self_test"], "simulate": simulate},
        ],
        "generation_options": {"qc_max_rounds": 1, "include_doxygen": False, "line_ending": "crlf"},
    }


def _measureless_spec(project_name: str) -> dict:
    """CIT olcumu uretmeyen spec: yalniz device_init (whitelist disi) istenir."""
    spec = _cit_spec(project_name)
    for device in spec["devices"]:
        device.get("config", {}).pop("cit", None)
        device["operations_requested"] = ["device_init"]
    return spec


class CitHeaderTest(unittest.TestCase):
    def _generate(self, spec: dict, tmp: str) -> Path:
        out_dir = Path(tmp) / spec["project"]["name"]
        codegen.generate(spec, out_dir)
        return out_dir / "tests"

    def test_header_has_named_bits_and_static_asserts(self) -> None:
        spec = _cit_spec("unit_cit_header")
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            header = (tests_dir / "spec2code_cit.h").read_text(encoding="utf-8")

        # Kullanici isimli bit (VCC_3V3 -> Vcc3v3; TMP_TEMP -> TmpTemp).
        self.assertIn("unsigned int uiVcc3v3Ok : 1;", header)
        self.assertIn("unsigned int uiTmpTempOk : 1;", header)
        # Olcum sayisi 12 (8 voltaj kanali + 2 sicaklik + 2 PLL); kanal isimleri V2..V8.
        self.assertIn("#define BOARD_CIT_OLCUM_SAYISI 12U", header)
        self.assertIn("unsigned int uiU2Ltc2991V2Ok : 1;", header)
        self.assertIn("unsigned int uiU2Ltc2991V8Ok : 1;", header)
        # Bayrak word sayisi ((12+31)/32)*4 == 4 bayt.
        self.assertIn("_Static_assert(sizeof(SBoardCitBayraklar) == 4U", header)
        self.assertIn("_Static_assert(sizeof(SBoardCit) % 4U == 0U", header)
        # Prototipler.
        self.assertIn("void boardCitRun(SBoardCit* spCit);", header)
        self.assertIn("const SBoardCit* boardCitSon(void);", header)
        # stdint tipi sizmamis olmali.
        self.assertNotIn("uint32_t", header)
        self.assertNotIn("uint8_t", header)

    def test_cit_run_uses_cit_layer_not_dispatch(self) -> None:
        # KOK KARAR: boardCitRun cit/ katmanini (sistemCitRead -> <mod>CitRead -> surucu)
        # kosar; dispatch koprusu / cihaz-op string tablolari YOK. Limit/OK-NOK karari
        # host'ta (CIT ekrani) canli yapilir; koda limit sayisi gomulmez.
        spec = _cit_spec("unit_cit_layer_use")
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            source = (tests_dir / "spec2code_cit.c").read_text(encoding="utf-8")

        self.assertIn('#include "sistem_cit.h"', source)
        self.assertIn("static SSistemCitLimit S_sCitLimit = SISTEM_CIT_LIMIT_VARSAYILAN;", source)
        self.assertIn("(void)sistemCitRead(&S_sCitBus, &S_sCitLimit, &S_sSistemCit);", source)
        # Host limitleri CIT_LIMIT_SET ile yazar; olcum indeksi -> cit/ limit alani.
        self.assertIn("void boardCitLimitAyarla(unsigned int uiOlcum, const SCitLimit* spLimit)", source)
        self.assertIn("case 0U: S_sCitLimit.sU2Ltc2991.sV1 = *spLimit; break;", source)
        self.assertIn("case 9U: S_sCitLimit.sU3Tmp101.sTemperature = *spLimit; break;", source)
        # Denetleyici handle'lari ajanin getter'larindan (ilklendirilmis denetleyiciler).
        self.assertIn('S_sCitBus.sPlI2c0 = spec2codeTestbenchIicHandleGet("pl_i2c_0");', source)
        self.assertIn('S_sCitBus.sPlSpi0 = spec2codeTestbenchSpiHandleGet("pl_spi_0");', source)
        self.assertIn("if (spec2codeTestbenchBoardInit() != XST_SUCCESS)", source)
        self.assertNotIn("spec2codeSimHazirla", source)  # sanal cihaz yok -> cagri yok
        # Dispatch koprusu ve string tablolari yok.
        for stale in ("spec2codeTestbenchDispatch", "S_cpArrCitCihaz", "S_cpArrCitOp", "S_uiArrCitKanal",
                      "spec2codeCitMetinKopya"):
            self.assertNotIn(stale, source)
        for limit in ("3135", "3465", "2000", "3000"):
            self.assertNotIn(limit, source)
        self.assertNotIn("SPEC2CODE_MESAJ_DURUM_DESTEKLENMIYOR", source)

    def test_array_op_expands_to_channel_slots_from_driver_struct(self) -> None:
        spec = _cit_spec("unit_cit_channels")
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            source = (tests_dir / "spec2code_cit.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (tests_dir / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        olcumler = manifest["cit"]["olcumler"]
        kanallar = [m for m in olcumler if m["op"] == "voltage_read"]
        self.assertEqual([m["channel"] for m in kanallar], list(range(8)))
        self.assertEqual([m["channel_label"] for m in kanallar], [f"V{i}" for i in range(1, 9)])
        self.assertTrue(all(m["channels"] == 8 for m in kanallar))
        self.assertEqual(kanallar[0]["name"], "VCC_3V3")
        self.assertEqual(kanallar[1]["name"], "U2_LTC2991_V2")  # varsayilan ad cihaz kimliginden
        # Skaler olcumlerde kanal anahtari YOK (eski manifest sekli korunur).
        self.assertNotIn("channel", olcumler[8])
        # Her kanal surucu struct'inin kendi elemanindan; okundu biti op'un okuma biti.
        self.assertIn("spec2codeCitOlcumYaz(spCit, 0U, (int)S_sSistemCit.sU2Ltc2991.sVoltage.usArrVoltage[0U], "
                      "S_sSistemCit.sU2Ltc2991.sBayraklar.uiVoltageReadOkundu);", source)
        self.assertIn("spec2codeCitOlcumYaz(spCit, 7U, (int)S_sSistemCit.sU2Ltc2991.sVoltage.usArrVoltage[7U], "
                      "S_sSistemCit.sU2Ltc2991.sBayraklar.uiVoltageReadOkundu);", source)
        # Bayrak biti = kartin karari (cit/ ok biti), okuma durumu uiDurum'da.
        self.assertIn("spCit->sBayraklar.uiVcc3v3Ok = S_sSistemCit.sU2Ltc2991.sBayraklar.uiV1Ok;", source)
        self.assertIn("spCit->sBayraklar.uiU2Ltc2991V2Ok = S_sSistemCit.sU2Ltc2991.sBayraklar.uiV2Ok;", source)
        self.assertIn("spec2codeCitOlcumYaz(spCit, 9U, (int)S_sSistemCit.sU3Tmp101.iTemperature, "
                      "S_sSistemCit.sU3Tmp101.sBayraklar.uiTemperatureReadOkundu);", source)
        self.assertIn("(int)S_sSistemCit.sU4Lmk04832.ucPll1LockDetect", source)

    def test_channelless_override_applies_limits_to_all_channels(self) -> None:
        spec = _cit_spec("unit_cit_channel_generic")
        spec["devices"][0]["config"]["cit"] = {"measurements": [
            {"op": "voltage_read", "name": "GENEL", "min": 100, "max": 200, "severity": "critical"},
            {"op": "voltage_read", "channel": 2, "name": "VCC_IO", "max": 999},
        ]}
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            manifest = json.loads(
                (tests_dir / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        kanallar = [m for m in manifest["cit"]["olcumler"] if m["op"] == "voltage_read"]
        # Kanalsiz override: isim HARIC her sey butun kanallara (cname benzersiz kalir).
        self.assertEqual([m["name"] for m in kanallar][:2], ["U2_LTC2991_V1", "U2_LTC2991_V2"])
        self.assertTrue(all(m["min"] == 100 and m["severity"] == "critical" for m in kanallar
                            if m["channel"] != 2))
        # Kanal eslesmesi ustune yazar (min genelden kalir, max/isim kanaldan).
        self.assertEqual(kanallar[2]["name"], "VCC_IO")
        self.assertEqual((kanallar[2]["min"], kanallar[2]["max"]), (100, 999))

    def test_measureless_spec_omits_cit_files(self) -> None:
        spec = _measureless_spec("unit_cit_none")
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            self.assertFalse((tests_dir / "spec2code_cit.h").exists())
            self.assertFalse((tests_dir / "spec2code_cit.c").exists())
            mesaj = (tests_dir / "spec2code_mesaj.c").read_text(encoding="utf-8")
            # CIT dallari DESTEKLENMIYOR dondurur, cit.h include EDILMEZ.
            self.assertNotIn('#include "spec2code_cit.h"', mesaj)
            self.assertIn("SPEC2CODE_MESAJ_DURUM_DESTEKLENMIYOR", mesaj)

    def test_self_test_is_reachable_from_agent_and_has_no_wrapper(self) -> None:
        """tests/<mod>_test.c yalniz istenirse uretilir, ajan `self_test` op'uyla kosar;
        TestRun/TestTask sarmalayicisi ve ayri self-test runner YOK (kullanilmayan kod)."""
        spec = _cit_spec("unit_cit_selftest_op")
        spec["devices"][1]["tests_requested"] = []
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            test_h = (tests_dir / "ltc2991_test.h").read_text(encoding="utf-8")
            test_c = (tests_dir / "ltc2991_test.c").read_text(encoding="utf-8")
            ops = (tests_dir / "unit_cit_selftest_op_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (tests_dir / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            self.assertFalse((tests_dir / "tmp101_test.c").exists())
            self.assertFalse((tests_dir / "tmp101_test.h").exists())
        self.assertIn("int ltc2991SelfTest(const SI2cCihaz* spCihaz);", test_h)
        self.assertNotIn("TestRun", test_h)
        self.assertNotIn("TestTask", test_h)
        self.assertNotIn("xil_printf", test_c)
        self.assertIn('dbg_printf(DEBUG_LEVEL_INFO, "LTC2991 status registers read OK");', test_c)
        self.assertIn('#include "ltc2991_test.h"', ops)
        self.assertNotIn('#include "tmp101_test.h"', ops)
        self.assertIn("iStatus = ltc2991SelfTest(spCihaz);", ops)
        self.assertIn("spCihaz = i2cCihaz(I2C_CIHAZ_U2_LTC2991);", ops)
        self.assertNotIn("tmp101SelfTest(", ops)
        ops_by_device = {d["id"]: [op["name"] for op in d["operations"]] for d in manifest["devices"]}
        self.assertIn("self_test", ops_by_device["u2_ltc2991"])
        self.assertNotIn("self_test", ops_by_device["u3_tmp101"])
        # CIT olcumu degil (birimsiz, whitelist disi).
        self.assertFalse(any(m["op"] == "self_test" for m in manifest["cit"]["olcumler"]))


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


@unittest.skipUnless(_find_cc(), "host C compiler required")
class CitHostRoundTripTest(unittest.TestCase):
    """Uretilen mesaj + spec2code_cit + cit/ + drivers + tests/sim katmanini gercek
    derleyiciyle uctan uca dogrular (Xilinx stub'lari + -include araya-girme)."""

    def _build_and_run(self, spec: dict, main_c: str) -> str:
        compiler = _find_cc()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            work = Path(tmp) / "host"
            work.mkdir()
            (work / "xparameters.h").write_text(_HOST_XPARAMETERS, encoding="utf-8")
            (work / "main.c").write_text(main_c, encoding="utf-8")
            binary = work / ("cit_roundtrip.exe" if os.name == "nt" else "cit_roundtrip")
            sources = [str(work / "main.c"),
                       str(tests_dir / "spec2code_mesaj.c"),
                       str(tests_dir / "spec2code_cit.c"),
                       str(tests_dir / "spec2code_testbench_protocol.c"),
                       str(STUBS / "xilinx_stubs.c"),
                       *[str(p) for p in (out_dir / "drivers").glob("*.c")],
                       *[str(p) for p in (out_dir / "cit").glob("*.c")],
                       *[str(p) for p in (tests_dir / "sim").glob("*.c")]]
            cmd = [compiler, "-std=c99", "-Wall", "-Wextra",
                   "-include", "spec2code_sim_xilinx.h",
                   "-I", str(work), "-I", str(STUBS), "-I", str(out_dir / "drivers"),
                   "-I", str(out_dir / "cit"), "-I", str(tests_dir), "-I", str(tests_dir / "sim"),
                   "-o", str(binary), *sources]
            build = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(binary)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            return run.stdout

    def _decode_cit_response(self, hex_line: str, olcum_sayisi: int) -> dict:
        frame = bytes.fromhex(hex_line)
        # Baslik 12B, sonra govde: uiIstekSayac(4) + uiDurum(4) + SBoardCit.
        body = frame[12:]
        istek_sayac, durum = struct.unpack_from("<II", body, 0)
        cit = body[8:]
        # SBoardCit: uiSayac(4) + uiZaman(4) + bayraklar(pad4) + arrOlcum[N]*12.
        flag_words = ((olcum_sayisi + 31) // 32) * 4
        uiSayac, uiZaman = struct.unpack_from("<II", cit, 0)
        flags = int.from_bytes(cit[8:8 + flag_words], "little")
        olcum_off = 8 + flag_words
        olcumler = []
        for i in range(olcum_sayisi):
            iDeger, uiHam, uiDurum = struct.unpack_from("<iII", cit, olcum_off + i * 12)
            # read_ok = KARTIN OK biti (cit/ karari); okuma durumu uiDurum'dadir.
            olcumler.append({"iDeger": iDeger, "uiHam": uiHam, "uiDurum": uiDurum,
                             "read_ok": bool(flags & (1 << i))})
        return {"istek_sayac": istek_sayac, "durum": durum, "uiSayac": uiSayac,
                "uiZaman": uiZaman, "flags": flags, "olcumler": olcumler}

    @staticmethod
    def _frame_c(name: str, sayac: int) -> str:
        return ", ".join(f"0x{b:02X}U" for b in s2cmsg.pack_named_request(name, sayac))

    def _main_for(self, project: str, run_extra: str) -> str:
        return (
            '#include <stdio.h>\n'
            '#include "spec2code_mesaj.h"\n'
            '#include "spec2code_cit.h"\n'
            '#include "spec2code_testbench_protocol.h"\n'
            f'#include "{project}_testbench_ops.h"\n'
            '#include "sistem_cit.h"\n'
            '#include "spec2code_sim.h"\n'
            '#include "ltc2991_sim.h"\n'
            '#include "tmp101_sim.h"\n'
            '#include "lmk04832_sim.h"\n'
            '#include "xstatus.h"\n'
            '#include "xparameters.h"\n'
            '#include "i2c_cihazlar.h"\n'
            '/* Ajan stub\'lari: denetleyiciler hazir, handle getter\'lari sabit; op dispatch\'i\n'
            ' * CIT yolunda KULLANILMAZ (boardCitRun cit/ katmanini kosar). */\n'
            'static XSpi S_sSpi;\n'
            'static XIic S_sIic;\n'
            'static SLtc2991Sim S_sLtc;\n'
            'static STmp101Sim S_sTmp;\n'
            'static SLmk04832Sim S_sLmk;\n'
            'static SSpec2codeI2cSimSwitch S_sSwitch;\n'
            'int spec2codeTestbenchBoardInit(void) { return XST_SUCCESS; }\n'
            'void spec2codeTestbenchI2cCihazlarBagla(void) { i2cCihazlarInit(&S_sIic); }\n'
            'void spec2codeSimHazirla(void) { /* sanal cihazlar main() icinde elle kuruldu */ }\n'
            'XIic* spec2codeTestbenchIicHandleGet(const char* cpControllerId)\n'
            '{ (void)cpControllerId; return &S_sIic; }\n'
            'XSpi* spec2codeTestbenchSpiHandleGet(const char* cpControllerId)\n'
            '{ (void)cpControllerId; return &S_sSpi; }\n'
            'int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,\n'
            '                               SSpec2codeTestbenchResponse* spResponse)\n'
            '{\n'
            '    spec2codeTestbenchResponseClear(spResponse);\n'
            '    spResponse->uiId = spRequest->uiId;\n'
            '    spResponse->iStatus = XST_FAILURE;\n'
            '    return XST_FAILURE;\n'
            '}\n'
            'static void emitFrame(const unsigned char* ucpFrame, unsigned int uiLen)\n'
            '{\n'
            '    unsigned int uiIndex;\n'
            '    for (uiIndex = 0U; uiIndex < uiLen; uiIndex++) { printf("%02X", ucpFrame[uiIndex]); }\n'
            '    printf("\\n");\n'
            '}\n'
            'static void feedFrame(const unsigned char* ucpFrame, unsigned int uiLen)\n'
            '{\n'
            '    SMesajParser sParser;\n'
            '    static unsigned char ucArrCikti[4200];\n'
            '    unsigned int uiPos = 0U;\n'
            '    spec2codeMesajParserSifirla(&sParser);\n'
            '    while (uiPos < uiLen)\n'
            '    {\n'
            '        unsigned int uiTuketilen = 0U;\n'
            '        int iTam = spec2codeMesajBesle(&sParser, &ucpFrame[uiPos], 1U, &uiTuketilen);\n'
            '        uiPos += uiTuketilen;\n'
            '        if (iTam == TRUE)\n'
            '        {\n'
            '            unsigned int uiCiktiBoy = spec2codeMesajIsle(&sParser.sBaslik,\n'
            '                sParser.ucArrGovde, ucArrCikti, (unsigned int)sizeof(ucArrCikti));\n'
            '            emitFrame(ucArrCikti, uiCiktiBoy);\n'
            '        }\n'
            '    }\n'
            '}\n'
            'int main(void)\n'
            '{\n'
            '    SSistemCitBus sBus;\n'
            '    /* Sanal cihazlar (tests/sim): mux arkasinda LTC2991 + TMP101, SPI LMK04832. */\n'
            '    ltc2991SimKur(&S_sLtc, 0x48U);\n'
            '    (void)spec2codeSimI2cEkle(&S_sLtc.sCihaz);\n'
            '    tmp101SimKur(&S_sTmp, 0x4AU);\n'
            '    S_sTmp.ucArrReg[0x00U][0] = 0x19U; /* TMP101 sicaklik registeri: 25.00 C (12 bit, MSB) */\n'
            '    S_sTmp.ucArrReg[0x00U][1] = 0x00U;\n'
            '    (void)spec2codeSimI2cEkle(&S_sTmp.sCihaz);\n'
            '    lmk04832SimKur(&S_sLmk, (unsigned char)LMK04832_SPI_SELECT);\n'
            '    (void)spec2codeSimSpiEkle(&S_sLmk.sCihaz);\n'
            '    spec2codeSimSwitchKur(&S_sSwitch, 0x70U);\n'
            '    (void)spec2codeSimI2cEkle(&S_sSwitch.sCihaz);\n'
            '    ltc2991SimKanalAyarla(&S_sLtc, 0U, 3300);\n'
            '    ltc2991SimKanalAyarla(&S_sLtc, 7U, 1200);\n'
            '    /* Ajanin "init all" adimi yerine: entegre ilklendirmeleri (surucu DeviceInit). */\n'
            '    sBus.sPlI2c0 = spec2codeTestbenchIicHandleGet("pl_i2c_0");\n'
            '    spec2codeTestbenchI2cCihazlarBagla(); /* tablo -> denetleyici ornegi */\n'
            '    sBus.sPlSpi0 = spec2codeTestbenchSpiHandleGet("pl_spi_0");\n'
            '    (void)sistemCitInit(&sBus);\n'
            + run_extra +
            '    return 0;\n'
            '}\n'
        )

    def test_cit_run_and_read_round_trip_over_cit_layer(self) -> None:
        spec = _cit_spec("unit_cit_rt", simulate=True)
        # Canli limit: V1 3300..3400 (3299 disarida -> NOK), digerleri limitsiz, olcum 9 kapali.
        limits = [{"min": None, "max": None, "enabled": True} for _ in range(12)]
        limits[0] = {"min": 3300, "max": 3400, "enabled": True}
        limits[9] = {"min": 0, "max": 0, "enabled": False}
        limit_frame = s2cmsg.pack_named_request("CIT_LIMIT_SET", 404, extra=s2cmsg.pack_cit_limits(limits), length=12)
        limit_bytes = ", ".join(f"0x{b:02X}U" for b in limit_frame)
        bad_frame = s2cmsg.pack_named_request("CIT_LIMIT_SET", 505, extra=s2cmsg.pack_cit_limits(limits[:3]), length=3)
        bad_bytes = ", ".join(f"0x{b:02X}U" for b in bad_frame)
        run_extra = (
            f'    static const unsigned char ucArrRun[] = {{ {self._frame_c("CIT_RUN", 101)} }};\n'
            f'    static const unsigned char ucArrRead[] = {{ {self._frame_c("CIT_READ", 202)} }};\n'
            f'    static const unsigned char ucArrRun2[] = {{ {self._frame_c("CIT_RUN", 303)} }};\n'
            f'    static const unsigned char ucArrLimit[] = {{ {limit_bytes} }};\n'
            f'    static const unsigned char ucArrLimitBad[] = {{ {bad_bytes} }};\n'
            f'    static const unsigned char ucArrRun3[] = {{ {self._frame_c("CIT_RUN", 606)} }};\n'
            '    feedFrame(ucArrRun, (unsigned int)sizeof(ucArrRun));\n'
            '    feedFrame(ucArrRead, (unsigned int)sizeof(ucArrRead));\n'
            '    /* Canli limit karta yazilir (yanit: standart onek), yanlis sayi reddedilir. */\n'
            '    feedFrame(ucArrLimit, (unsigned int)sizeof(ucArrLimit));\n'
            '    feedFrame(ucArrLimitBad, (unsigned int)sizeof(ucArrLimitBad));\n'
            '    feedFrame(ucArrRun3, (unsigned int)sizeof(ucArrRun3));\n'
            '    /* LTC hattan dusmus gibi (NACK): yalniz LTC olcumleri okunamaz. */\n'
            '    ltc2991SimHataAyarla(&S_sLtc, SPEC2CODE_SIM_HATA_NACK);\n'
            '    feedFrame(ucArrRun2, (unsigned int)sizeof(ucArrRun2));\n'
        )
        output = self._build_and_run(spec, self._main_for("unit_cit_rt", run_extra))
        # dbg_printf (ERROR esigi) stub'da satir basabilir; yalniz hex cerceve satirlari.
        lines = [l.strip() for l in output.strip().splitlines() if re.fullmatch(r"[0-9A-F]+", l.strip())]
        self.assertEqual(len(lines), 6, output)

        run = self._decode_cit_response(lines[0], 12)
        self.assertEqual(run["istek_sayac"], 101)
        self.assertEqual(run["durum"], 0)
        self.assertEqual(run["uiSayac"], 1)
        # Spec varsayilan limitleri: V1 3135..3465 (3299 icinde), TMP 2000..3000 -> hepsi OK.
        self.assertTrue(all(m["read_ok"] for m in run["olcumler"]), run["olcumler"])
        self.assertTrue(all(m["uiDurum"] == 0 for m in run["olcumler"]))
        # Surucu struct'indan kanal degerleri (sim 3300 -> LSB donusumu 3299, 1200 -> 1199).
        self.assertEqual(run["olcumler"][0]["iDeger"], 3299)
        self.assertEqual(run["olcumler"][0]["uiHam"], 3299)
        self.assertEqual(run["olcumler"][7]["iDeger"], 1199)
        self.assertEqual(run["olcumler"][8]["iDeger"], 2500)   # LTC2991 ic sicaklik (sim: 25.00 C)
        self.assertEqual(run["olcumler"][10]["iDeger"], 1)     # LMK PLL1 kilitli
        self.assertEqual(run["olcumler"][11]["iDeger"], 1)     # LMK PLL2 kilitli

        # CIT_READ: yeniden kosmadan ayni kopya (uiSayac degismez).
        read = self._decode_cit_response(lines[1], 12)
        self.assertEqual(read["istek_sayac"], 202)
        self.assertEqual(read["uiSayac"], 1)
        self.assertEqual(read["olcumler"][0]["iDeger"], 3299)
        self.assertEqual(read["olcumler"][7]["iDeger"], 1199)

        # Canli limit: kabul (durum 0), yanlis sayi -> GECERSIZ_PARAMETRE (3).
        self.assertEqual(struct.unpack_from("<II", bytes.fromhex(lines[2]), 12)[1], 0)
        self.assertEqual(struct.unpack_from("<II", bytes.fromhex(lines[3]), 12)[1], 3)
        # Yeni limitle kosu: V1 3299 artik 3300..3400 disinda -> KART NOK dedi, okuma yine basarili.
        run3 = self._decode_cit_response(lines[4], 12)
        self.assertEqual(run3["uiSayac"], 2)
        self.assertFalse(run3["olcumler"][0]["read_ok"])
        self.assertEqual(run3["olcumler"][0]["uiDurum"], 0)
        self.assertEqual(run3["olcumler"][0]["iDeger"], 3299)
        self.assertTrue(run3["olcumler"][1]["read_ok"])   # limitsiz kanal OK
        self.assertTrue(run3["olcumler"][9]["read_ok"])   # etkin degil (0..0 limit) -> OK sayilir

        # NACK: LTC olcumleri (0..8) okunamadi -> bit 0, uiDurum BUS_HATASI; digerleri temiz.
        run2 = self._decode_cit_response(lines[5], 12)
        self.assertEqual(run2["uiSayac"], 3)
        for k in range(0, 9):
            self.assertFalse(run2["olcumler"][k]["read_ok"], k)
            self.assertEqual(run2["olcumler"][k]["uiDurum"], 5, k)
        for k in range(9, 12):
            self.assertTrue(run2["olcumler"][k]["read_ok"], k)
            self.assertEqual(run2["olcumler"][k]["uiDurum"], 0, k)

    def test_disabled_measurement_still_read_by_board(self) -> None:
        # enabled artik HOST tarafinda (CIT ekrani gizler); kart config'teki
        # enabled=false'a bakmadan HER olcumu okur (bayrak = okuma basarisi).
        spec = _cit_spec("unit_cit_disabled_rt", simulate=True)
        spec["devices"][0]["config"]["cit"] = {
            "measurements": [
                {"op": "voltage_read", "channel": 0, "name": "VCC_3V3_RF", "min": 3135,
                 "max": 3465, "severity": "critical"},
                {"op": "temperature_read", "name": "LTC_TEMP", "enabled": False},
            ],
        }
        run_extra = (
            f'    static const unsigned char ucArrRun[] = {{ {self._frame_c("CIT_RUN", 55)} }};\n'
            '    feedFrame(ucArrRun, (unsigned int)sizeof(ucArrRun));\n'
        )
        output = self._build_and_run(spec, self._main_for("unit_cit_disabled_rt", run_extra))
        lines = [l.strip() for l in output.strip().splitlines() if re.fullmatch(r"[0-9A-F]+", l.strip())]
        self.assertEqual(len(lines), 1, output)
        run = self._decode_cit_response(lines[0], 12)
        # Olcum 8 (LTC_TEMP) config'te disabled: kart yine de OKUDU (durum 0), etkin degil -> OK biti 1.
        self.assertEqual(run["olcumler"][8]["uiDurum"], 0)
        self.assertTrue(run["olcumler"][8]["read_ok"])
        self.assertEqual(run["olcumler"][8]["iDeger"], 2500)
        self.assertTrue(run["olcumler"][0]["read_ok"])
        self.assertTrue(run["olcumler"][9]["read_ok"])

    def test_measureless_spec_cit_run_returns_desteklenmiyor(self) -> None:
        spec = _measureless_spec("unit_cit_none_rt")
        # cit dosyalari yok; main sadece mesaj + protocol linkler.
        run_frame = s2cmsg.pack_named_request("CIT_RUN", 77)
        run_bytes = ", ".join(f"0x{b:02X}U" for b in run_frame)
        compiler = _find_cc()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            self.assertFalse((tests_dir / "spec2code_cit.c").exists())
            work = Path(tmp) / "host"
            work.mkdir()
            for name in ("spec2code_mesaj.c", "spec2code_mesaj.h",
                         "spec2code_testbench_protocol.c", "spec2code_testbench_protocol.h"):
                shutil.copy2(tests_dir / name, work / name)
            (work / "main.c").write_text(
                '#include <stdio.h>\n'
                '#include "spec2code_mesaj.h"\n'
                '#include "spec2code_testbench_protocol.h"\n'
                '#include "xstatus.h"\n'
                'int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,\n'
                '                               SSpec2codeTestbenchResponse* spResponse)\n'
                '{\n'
                '    spec2codeTestbenchResponseClear(spResponse);\n'
                '    spResponse->uiId = spRequest->uiId;\n'
                '    spResponse->iStatus = XST_FAILURE;\n'
                '    return XST_FAILURE;\n'
                '}\n'
                f'static const unsigned char S_ucArrRun[] = {{ {run_bytes} }};\n'
                'int main(void)\n'
                '{\n'
                '    SMesajParser sParser;\n'
                '    unsigned char ucArrCikti[256];\n'
                '    unsigned int uiPos = 0U;\n'
                '    spec2codeMesajParserSifirla(&sParser);\n'
                '    while (uiPos < (unsigned int)sizeof(S_ucArrRun))\n'
                '    {\n'
                '        unsigned int uiTuketilen = 0U;\n'
                '        int iTam = spec2codeMesajBesle(&sParser, &S_ucArrRun[uiPos], 1U, &uiTuketilen);\n'
                '        uiPos += uiTuketilen;\n'
                '        if (iTam == TRUE)\n'
                '        {\n'
                '            unsigned int uiBoy = spec2codeMesajIsle(&sParser.sBaslik, sParser.ucArrGovde,\n'
                '                ucArrCikti, (unsigned int)sizeof(ucArrCikti));\n'
                '            unsigned int uiI;\n'
                '            for (uiI = 0U; uiI < uiBoy; uiI++) { printf("%02X", ucArrCikti[uiI]); }\n'
                '            printf("\\n");\n'
                '        }\n'
                '    }\n'
                '    return 0;\n'
                '}\n',
                encoding="utf-8")
            binary = work / ("cit_none.exe" if os.name == "nt" else "cit_none")
            sources = [str(work / "main.c"), str(work / "spec2code_mesaj.c"),
                       str(work / "spec2code_testbench_protocol.c")]
            build = subprocess.run(
                [compiler, "-Wall", "-Wextra", "-I", str(work), "-I", str(STUBS), "-o", str(binary)] + sources,
                capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        line = output.strip().splitlines()[0]
        frame = bytes.fromhex(line)
        istek_sayac, durum = struct.unpack_from("<II", frame, 12)
        self.assertEqual(istek_sayac, 77)
        self.assertEqual(durum, 7)  # DESTEKLENMIYOR


if __name__ == "__main__":
    unittest.main()
