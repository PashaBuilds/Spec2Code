"""Task 7: CIT codegen — SBoardCit + boardCitRun + CIT_RUN/CIT_READ.

Uretilen spec2code_cit.h/.c dosyalarinin (a) header sekli/bit isimleri/
_Static_assert'leri, (b) sabit limit tablosu degerleri config'ten birebir, ve
(c) host derleme round-trip'i (dispatch stub'u ile boardCitRun + CIT_RUN/CIT_READ
cerceveleri MesajIsle'den gecirilir) dogrulanir.

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


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


def _find_cc() -> str | None:
    return shutil.which("gcc") or shutil.which("cc")


def _cit_spec(project_name: str) -> dict:
    """LTC2991 (I2C, mux arkasinda) + AD7414 (I2C, dogrudan) iceren CIT test speci.

    Olcum sirasi (manifest cit.olcumler ile birebir):
      0: u12_ltc2991 voltage_read     -> VCC_3V3_RF (limit 3135..3465, critical)
      1: u12_ltc2991 temperature_read -> varsayilan isim, limitsiz
      2: u13_ad7414  temperature_read -> varsayilan isim, limit 2000..3000
    """
    spec = load_sample_spec(project_name)
    spec["devices"] = [
        {
            "id": "u12_ltc2991",
            "part": "LTC2991",
            "descriptor_ref": "descriptors/ltc2991.yaml",
            "attach": {
                "controller_id": "ps_i2c_0",
                "i2c_address": "0x48",
                "via_mux": {"mux_id": "u7_tca9548a", "channel": 3},
                "reset_gpio": None,
                "irq_line": None,
            },
            "config": {
                "pairs": {
                    "v1_v2": {"mode": "single_ended_voltage", "shunt_milliohm": None},
                    "v3_v4": {"mode": "single_ended_voltage", "shunt_milliohm": None},
                    "v5_v6": {"mode": "single_ended_voltage", "shunt_milliohm": None},
                    "v7_v8": {"mode": "single_ended_voltage", "shunt_milliohm": None},
                },
                "internal_temperature": True,
                "vcc_read": False,
                "cit": {
                    "measurements": [
                        {
                            "op": "voltage_read",
                            "name": "VCC_3V3_RF",
                            "min": 3135,
                            "max": 3465,
                            "severity": "critical",
                        },
                    ],
                },
            },
            "operations_requested": ["device_init", "voltage_read", "temperature_read"],
            "tests_requested": ["self_test"],
        },
        {
            "id": "u13_ad7414",
            "part": "AD7414",
            "descriptor_ref": "descriptors/ad7414.yaml",
            "attach": {
                "controller_id": "ps_i2c_0",
                "i2c_address": "0x49",
                "via_mux": None,
                "reset_gpio": None,
                "irq_line": None,
            },
            "config": {
                "cit": {
                    "measurements": [
                        {
                            "op": "temperature_read",
                            "name": "AD_TEMP",
                            "min": 2000,
                            "max": 3000,
                            "severity": "warning",
                        },
                    ],
                },
            },
            "operations_requested": ["device_init", "temperature_read", "config_read"],
            "tests_requested": ["self_test"],
        },
    ]
    return spec


def _measureless_spec(project_name: str) -> dict:
    """CIT olcumu uretmeyen spec: yalniz device_init (whitelist disi) istenir."""
    spec = _cit_spec(project_name)
    for device in spec["devices"]:
        device["config"].pop("cit", None)
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

        # Kullanici isimli bit (VCC_3V3_RF -> Vcc3v3Rf).
        self.assertIn("unsigned int uiVcc3v3RfOk : 1;", header)
        # AD_TEMP -> AdTemp.
        self.assertIn("unsigned int uiAdTempOk : 1;", header)
        # Olcum sayisi 3.
        self.assertIn("#define BOARD_CIT_OLCUM_SAYISI 3U", header)
        # Bayrak word sayisi ((3+31)/32)*4 == 4 bayt.
        self.assertIn("_Static_assert(sizeof(SBoardCitBayraklar) == 4U", header)
        self.assertIn("_Static_assert(sizeof(SBoardCit) % 4U == 0U", header)
        # Prototipler.
        self.assertIn("void boardCitRun(SBoardCit* spCit);", header)
        self.assertIn("const SBoardCit* boardCitSon(void);", header)
        # stdint tipi sizmamis olmali.
        self.assertNotIn("uint32_t", header)
        self.assertNotIn("uint8_t", header)

    def test_no_limit_embedded_in_firmware(self) -> None:
        # KOK KARAR: kart LIMIT GOMMEZ — limit/OK-NOK/onem/enabled karari host'ta
        # (CIT ekrani) canli yapilir. Uretilen .c'de limit tablosu ve config'ten
        # gelen limit sayilari BULUNMAMALI; kart yalniz okur (bayrak = okuma basarisi).
        spec = _cit_spec("unit_cit_limits")
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = self._generate(spec, tmp)
            source = (tests_dir / "spec2code_cit.c").read_text(encoding="utf-8")

        # Limit tablosu ve alanlari uretilmemeli.
        self.assertNotIn("S_sArrCitLimit", source)
        self.assertNotIn("uiLimitVar", source)
        self.assertNotIn("uiKritik", source)
        self.assertNotIn("uiEtkin", source)
        # Config'ten gelen limit sayilari koda gomulmemeli.
        for limit in ("3135", "3465", "2000", "3000"):
            self.assertNotIn(limit, source)
        # Bayrak biti = okuma basarisi; enabled-atlama (DESTEKLENMIYOR) yok — kart hepsini okur.
        self.assertIn("OKUMA BASARISI", source)
        self.assertNotIn("SPEC2CODE_MESAJ_DURUM_DESTEKLENMIYOR", source)
        # Dispatch koprusu (cihaz/op tablolari) yerinde.
        self.assertIn("S_cpArrCitCihaz", source)
        self.assertIn("S_cpArrCitOp", source)

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


@unittest.skipUnless(_find_cc(), "host C compiler required")
class CitHostRoundTripTest(unittest.TestCase):
    """Uretilen cit + mesaj katmanini gercek derleyiciyle uctan uca dogrular."""

    def _build_and_run(self, spec: dict, main_c: str, extra_sources: list[str]) -> str:
        compiler = _find_cc()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            work = Path(tmp) / "host"
            work.mkdir()
            for name in ("spec2code_mesaj.c", "spec2code_mesaj.h", "spec2code_cit.c",
                         "spec2code_cit.h", "spec2code_testbench_protocol.c",
                         "spec2code_testbench_protocol.h"):
                shutil.copy2(tests_dir / name, work / name)
            # xstatus.h stub: gercek Vitis xil_types.h NULL'i saglar; host
            # derlemesinde <stddef.h> ile ayni garantiyi veriyoruz.
            (work / "xstatus.h").write_text(
                "#ifndef XSTATUS_H\n#define XSTATUS_H\n#include <stddef.h>\n"
                "#define XST_SUCCESS 0\n#define XST_FAILURE 1\n#endif\n",
                encoding="utf-8")
            (work / "main.c").write_text(main_c, encoding="utf-8")
            binary = work / "cit_roundtrip"
            sources = [str(work / "main.c"), str(work / "spec2code_mesaj.c"),
                       str(work / "spec2code_cit.c"),
                       str(work / "spec2code_testbench_protocol.c")]
            sources.extend(str(work / s) for s in extra_sources)
            compile_run = subprocess.run(
                [compiler, "-Wall", "-Wextra", "-I", str(work), "-o", str(binary)] + sources,
                capture_output=True, text=True)
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            return subprocess.run([str(binary)], capture_output=True, text=True).stdout

    # Dispatch stub: olcum 0 (voltage_read) -> 3300, olcum 1 (temperature_read,
    # LTC2991) -> 5000, olcum 2 (temperature_read, AD7414) -> 9999. Kart LIMIT
    # DEGERLENDIRMEZ: uc okuma da basarili -> uc bayrak biti de 1 (okuma basarisi).
    # Limit gecti/kaldi karari host'ta. Cihaza gore ayrilir cunku iki temperature_read var.
    _STUB = (
        'int spec2codeTestbenchDispatch(const SSpec2codeTestbenchRequest* spRequest,\n'
        '                               SSpec2codeTestbenchResponse* spResponse)\n'
        '{\n'
        '    spec2codeTestbenchResponseClear(spResponse);\n'
        '    spResponse->uiId = spRequest->uiId;\n'
        '    spResponse->uiOk = 1U;\n'
        '    spResponse->iStatus = 0;\n'
        '    if (spec2codeTestbenchStringEqual(spRequest->cArrOperation, "voltage_read") == 1)\n'
        '    {\n'
        '        spResponse->uiValue = 3300U;\n'
        '    }\n'
        '    else if (spec2codeTestbenchStringEqual(spRequest->cArrDevice, "u13_ad7414") == 1)\n'
        '    {\n'
        '        spResponse->uiValue = 9999U;\n'
        '    }\n'
        '    else\n'
        '    {\n'
        '        spResponse->uiValue = 5000U;\n'
        '    }\n'
        '    return XST_SUCCESS;\n'
        '}\n'
    )

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
            olcumler.append({"iDeger": iDeger, "uiHam": uiHam, "uiDurum": uiDurum,
                             "read_ok": bool(flags & (1 << i))})
        return {"istek_sayac": istek_sayac, "durum": durum, "uiSayac": uiSayac,
                "uiZaman": uiZaman, "flags": flags, "olcumler": olcumler}

    def _main_for(self, run_extra: str) -> str:
        return (
            '#include <stdio.h>\n'
            '#include "spec2code_mesaj.h"\n'
            '#include "spec2code_cit.h"\n'
            '#include "spec2code_testbench_protocol.h"\n'
            '#include "xstatus.h"\n'
            + self._STUB +
            'static void emitFrame(const unsigned char* ucpFrame, unsigned int uiLen)\n'
            '{\n'
            '    unsigned int uiIndex;\n'
            '    for (uiIndex = 0U; uiIndex < uiLen; uiIndex++) { printf("%02X", ucpFrame[uiIndex]); }\n'
            '    printf("\\n");\n'
            '}\n'
            'static void feedFrame(const unsigned char* ucpFrame, unsigned int uiLen)\n'
            '{\n'
            '    SMesajParser sParser;\n'
            '    unsigned char ucArrCikti[4200];\n'
            '    unsigned int uiPos = 0U;\n'
            '    spec2codeMesajParserSifirla(&sParser);\n'
            '    while (uiPos < uiLen)\n'
            '    {\n'
            '        unsigned int uiTuketilen = 0U;\n'
            '        int iTam = spec2codeMesajBesle(&sParser, &ucpFrame[uiPos], 1U, &uiTuketilen);\n'
            '        uiPos += uiTuketilen;\n'
            '        if (iTam == 1)\n'
            '        {\n'
            '            unsigned int uiCiktiBoy = spec2codeMesajIsle(&sParser.sBaslik,\n'
            '                sParser.ucArrGovde, ucArrCikti, (unsigned int)sizeof(ucArrCikti));\n'
            '            emitFrame(ucArrCikti, uiCiktiBoy);\n'
            '        }\n'
            '    }\n'
            '}\n'
            'int main(void)\n'
            '{\n'
            + run_extra +
            '    return 0;\n'
            '}\n'
        )

    def test_cit_run_and_read_round_trip(self) -> None:
        spec = _cit_spec("unit_cit_rt")
        # CIT_RUN cercevesi (op'suz, cihazsiz global): pack_named_request.
        run_frame = s2cmsg.pack_named_request("CIT_RUN", 101)
        read_frame = s2cmsg.pack_named_request("CIT_READ", 202)
        run_bytes = ", ".join(f"0x{b:02X}U" for b in run_frame)
        read_bytes = ", ".join(f"0x{b:02X}U" for b in read_frame)
        run_extra = (
            f'    static const unsigned char ucArrRun[] = {{ {run_bytes} }};\n'
            f'    static const unsigned char ucArrRead[] = {{ {read_bytes} }};\n'
            '    feedFrame(ucArrRun, (unsigned int)sizeof(ucArrRun));\n'
            '    feedFrame(ucArrRead, (unsigned int)sizeof(ucArrRead));\n'
        )
        output = self._build_and_run(spec, self._main_for(run_extra), [])
        lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2, output)

        run = self._decode_cit_response(lines[0], 3)
        self.assertEqual(run["istek_sayac"], 101)
        self.assertEqual(run["durum"], 0)  # OK genel kosu
        self.assertEqual(run["uiSayac"], 1)
        # Kart limit degerlendirmez: uc okuma da basarili -> uc bayrak biti de 1.
        self.assertTrue(run["olcumler"][0]["read_ok"])
        self.assertEqual(run["olcumler"][0]["iDeger"], 3300)
        self.assertEqual(run["olcumler"][0]["uiDurum"], 0)
        self.assertTrue(run["olcumler"][1]["read_ok"])
        self.assertEqual(run["olcumler"][1]["iDeger"], 5000)
        # Olcum 2: 9999 (host'ta limit disi olabilir) ama KART icin okuma basarili -> bit 1.
        self.assertTrue(run["olcumler"][2]["read_ok"])
        self.assertEqual(run["olcumler"][2]["iDeger"], 9999)
        self.assertEqual(run["olcumler"][2]["uiDurum"], 0)

        # CIT_READ: yeniden kosmadan ayni kopya (uiSayac degismez).
        read = self._decode_cit_response(lines[1], 3)
        self.assertEqual(read["istek_sayac"], 202)
        self.assertEqual(read["uiSayac"], 1)
        self.assertEqual(read["olcumler"][0]["iDeger"], 3300)
        self.assertEqual(read["olcumler"][2]["iDeger"], 9999)

    def test_disabled_measurement_still_read_by_board(self) -> None:
        # enabled artik HOST tarafinda (CIT ekrani gizler); kart config'teki
        # enabled=false'a bakmadan HER olcumu okur (limit/enabled koda gomulmez).
        spec = _cit_spec("unit_cit_disabled_rt")
        spec["devices"][0]["config"]["cit"] = {
            "measurements": [
                {"op": "voltage_read", "name": "VCC_3V3_RF", "min": 3135, "max": 3465,
                 "severity": "critical"},
                {"op": "temperature_read", "name": "LTC_TEMP", "enabled": False},
            ],
        }
        run_frame = s2cmsg.pack_named_request("CIT_RUN", 55)
        run_bytes = ", ".join(f"0x{b:02X}U" for b in run_frame)
        run_extra = (
            f'    static const unsigned char ucArrRun[] = {{ {run_bytes} }};\n'
            '    feedFrame(ucArrRun, (unsigned int)sizeof(ucArrRun));\n'
        )
        output = self._build_and_run(spec, self._main_for(run_extra), [])
        lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, output)
        run = self._decode_cit_response(lines[0], 3)
        # Olcum 1 config'te disabled ama kart yine de OKUDU (DESTEKLENMIYOR degil).
        self.assertEqual(run["olcumler"][1]["uiDurum"], 0)
        self.assertTrue(run["olcumler"][1]["read_ok"])
        # Digerleri de okundu.
        self.assertTrue(run["olcumler"][0]["read_ok"])
        self.assertTrue(run["olcumler"][2]["read_ok"])

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
            # xstatus.h stub: gercek Vitis xil_types.h NULL'i saglar; host
            # derlemesinde <stddef.h> ile ayni garantiyi veriyoruz.
            (work / "xstatus.h").write_text(
                "#ifndef XSTATUS_H\n#define XSTATUS_H\n#include <stddef.h>\n"
                "#define XST_SUCCESS 0\n#define XST_FAILURE 1\n#endif\n",
                encoding="utf-8")
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
                '    spResponse->uiOk = 1U;\n'
                '    return XST_SUCCESS;\n'
                '}\n'
                f'static const unsigned char S_ucArrRun[] = {{ {run_bytes} }};\n'
                'int main(void)\n'
                '{\n'
                '    SMesajParser sParser;\n'
                '    unsigned char ucArrCikti[4200];\n'
                '    unsigned int uiPos = 0U;\n'
                '    spec2codeMesajParserSifirla(&sParser);\n'
                '    while (uiPos < (unsigned int)sizeof(S_ucArrRun))\n'
                '    {\n'
                '        unsigned int uiTuketilen = 0U;\n'
                '        int iTam = spec2codeMesajBesle(&sParser, &S_ucArrRun[uiPos], 1U, &uiTuketilen);\n'
                '        uiPos += uiTuketilen;\n'
                '        if (iTam == 1)\n'
                '        {\n'
                '            unsigned int uiCiktiBoy = spec2codeMesajIsle(&sParser.sBaslik,\n'
                '                sParser.ucArrGovde, ucArrCikti, (unsigned int)sizeof(ucArrCikti));\n'
                '            unsigned int uiIndex;\n'
                '            for (uiIndex = 0U; uiIndex < uiCiktiBoy; uiIndex++) { printf("%02X", ucArrCikti[uiIndex]); }\n'
                '            printf("\\n");\n'
                '        }\n'
                '    }\n'
                '    return 0;\n'
                '}\n',
                encoding="utf-8")
            binary = work / "cit_none"
            compile_run = subprocess.run(
                [compiler, "-Wall", "-Wextra", "-I", str(work), "-o", str(binary),
                 str(work / "main.c"), str(work / "spec2code_mesaj.c"),
                 str(work / "spec2code_testbench_protocol.c")],
                capture_output=True, text=True)
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            output = subprocess.run([str(binary)], capture_output=True, text=True).stdout

        lines = [l.strip() for l in output.strip().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1, output)
        # Yanit govdesi standart cerceve; durum DESTEKLENMIYOR (7).
        frame = bytes.fromhex(lines[0])
        body = frame[12:]
        _istek, durum = struct.unpack_from("<II", body, 0)
        self.assertEqual(durum, 7)


if __name__ == "__main__":
    unittest.main()
