"""Kart katmani codegen: kart tanimli DEGILKEN cikti bugunku ile ayni kalmali."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.jobs import Job
from backend.vitis_workspace import stage_vitis_sources, staged_header_dirs
from orchestrator import codegen

ROOT = Path(__file__).resolve().parent.parent


def _base_spec(name: str) -> dict:
    return {
        "project": {"name": name, "platform": "zynq_ultrascale",
                    "target_core": "psu_cortexa53_0", "runtime": "bare_metal",
                    "testbench_transport": "uart"},
        "zones": [], "cores": [],
        "controllers": [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XIicPs", "driver": "XIicPs",
             "base_address": "0xFF020000", "device_id": 0, "source": "ps", "zone": "ps"},
            {"id": "ps_uart_0", "type": "uart", "instance": "XUartPs", "driver": "XUartPs",
             "base_address": "0xFF000000", "device_id": 0, "source": "ps", "zone": "ps"},
        ],
        "muxes": [{"id": "u10_tca9548a", "part": "TCA9548A", "controller_id": "ps_i2c_0",
                   "i2c_address": "0x70", "channels": 8}],
        "devices": [
            {"id": "u1_ltc2991", "part": "LTC2991",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x48",
                        "via_mux": {"mux_id": "u10_tca9548a", "channel": 0}}},
            {"id": "u2_tmp101", "part": "TMP101",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x49",
                        "via_mux": {"mux_id": "u10_tca9548a", "channel": 3}}},
        ],
    }


class BoardlessOutputIsUnchangedTests(unittest.TestCase):
    def test_spec_without_boards_generates_todays_flat_layout(self) -> None:
        spec = _base_spec("boardless_demo")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            # Duz duzen: drivers/ altinda dogrudan .c/.h, alt klasor YOK.
            self.assertTrue((out / "drivers" / "ltc2991.c").is_file())
            self.assertTrue((out / "drivers" / "tmp101.c").is_file())
            subdirs = [p for p in (out / "drivers").iterdir() if p.is_dir()]
            self.assertEqual(subdirs, [], f"kart tanimsizken alt klasor olmamali: {subdirs}")
            # Kart modulu de uretilmemeli.
            self.assertFalse(list((out / "drivers").glob("*kart*")))

    def test_declaring_boards_is_the_only_trigger(self) -> None:
        """Ayni spec + boards -> kart duzeni; boards yok -> duz duzen."""
        spec = _base_spec("trigger_demo")
        boarded = {**spec,
                   "boards": [{"id": "main", "name": "Ana Kart", "role": "main"},
                              {"id": "rf", "name": "RF Kart", "role": "peripheral"}]}
        boarded["devices"] = [
            {**spec["devices"][0], "board_id": "main"},
            {**spec["devices"][1], "board_id": "rf"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            flat = Path(tmp) / "flat"
            grouped = Path(tmp) / "grouped"
            codegen.generate(spec, flat)
            codegen.generate(boarded, grouped)
            self.assertTrue((flat / "drivers" / "tmp101.c").is_file())
            self.assertTrue((grouped / "drivers" / "rf_kart" / "tmp101.c").is_file())
            self.assertTrue((grouped / "drivers" / "ana_kart" / "ltc2991.c").is_file())
            self.assertTrue((grouped / "tests" / "rf_kart.c").is_file())
            self.assertTrue((grouped / "tests" / "ana_kart.c").is_file())


class BoardModuleTests(unittest.TestCase):
    def _generate_boarded(self, tmp: Path) -> Path:
        spec = _base_spec("board_mod_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        out = tmp / "p"
        codegen.generate(spec, out)
        return out

    def test_board_module_exposes_init_cit_selftest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            header = (out / "tests" / "rf_kart.h").read_text(encoding="utf-8")
            self.assertIn("int rfKartInit(void);", header)
            self.assertIn("void rfKartCitRun(SBoardCit* spCit);", header)
            self.assertIn("int rfKartSelfTest(void);", header)
            self.assertNotIn("uint32_t", header)

    def test_board_init_calls_only_its_own_devices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            source = (out / "tests" / "rf_kart.c").read_text(encoding="utf-8")
            self.assertIn("tmp101", source)          # RF kartin cihazi
            self.assertNotIn("ltc2991", source)      # ana kartin cihazi sizmamali

    def test_manifest_carries_boards_and_device_board_ids(self) -> None:
        import json
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            manifest = json.loads(
                (out / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([b["id"] for b in manifest["boards"]], ["main", "rf"])
            by_id = {d["id"]: d for d in manifest["devices"]}
            self.assertEqual(by_id["u2_tmp101"]["board_id"], "rf")
            self.assertEqual(by_id["u1_ltc2991"]["board_id"], "main")

    def test_manifest_carries_connectors_and_generated_names(self) -> None:
        spec = _base_spec("connector_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        spec["connectors"] = [{"id": "j1", "from_board": "main", "to_board": "rf",
                               "kind": "i2c"}]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            manifest = json.loads(
                (out / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([c["id"] for c in manifest["connectors"]], ["j1"])
        by_id = {b["id"]: b for b in manifest["boards"]}
        # UI/derleme betikleri klasor ve C onekini yeniden turetmesin.
        self.assertEqual(by_id["rf"]["dirname"], "rf_kart")
        self.assertEqual(by_id["rf"]["identifier"], "rfKart")

    def test_boardless_manifest_has_no_board_keys(self) -> None:
        """Kart tanimsizken manifest'e 'boards'/'connectors'/'board_id' SIZMAZ."""
        spec = _base_spec("boardless_manifest")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            text = (out / "tests" / "spec2code_testbench_manifest.json").read_text(
                encoding="utf-8")
            manifest = json.loads(text)
        self.assertNotIn("boards", manifest)
        self.assertNotIn("connectors", manifest)
        self.assertNotIn("board_id", text)


class BoardCitSlotTests(unittest.TestCase):
    """Kart CitRun'i SISTEM bit sirasini degistirmez, yalniz kendi slotlarini doldurur."""

    def _spec(self) -> dict:
        spec = _base_spec("cit_slot_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        return spec

    def test_board_cit_slots_match_system_measurement_indices(self) -> None:
        spec = self._spec()
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            manifest = json.loads(
                (out / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            rf_source = (out / "tests" / "rf_kart.c").read_text(encoding="utf-8")
            ana_source = (out / "tests" / "ana_kart.c").read_text(encoding="utf-8")
            system_cit = (out / "tests" / "spec2code_cit.c").read_text(encoding="utf-8")

        olcumler = manifest["cit"]["olcumler"]
        self.assertTrue(olcumler, "test speci CIT olcumu uretmeli")
        # Her olcum kendi kartini tasir ve indeksler sistem sirasindan gelir.
        rf_slots = [m["index"] for m in olcumler if m["board_id"] == "rf"]
        ana_slots = [m["index"] for m in olcumler if m["board_id"] == "main"]
        self.assertTrue(rf_slots and ana_slots)
        self.assertEqual(sorted(rf_slots + ana_slots),
                         list(range(len(olcumler))))
        for slot in rf_slots:
            self.assertIn(f"    {slot}U,", rf_source)
            self.assertNotIn(f"    {slot}U,", ana_source)
        # Sistem boardCitRun ve bit sirasi DEGISMEZ: hala tum olcumleri gezer.
        self.assertIn("for (uiOlcum = 0U; uiOlcum < BOARD_CIT_OLCUM_SAYISI; uiOlcum++)",
                      system_cit)
        self.assertIn("void boardCitRun(SBoardCit* spCit)", system_cit)
        # Kart CitRun sistemin sayacina/son-kopyasina DOKUNMAZ.
        self.assertNotIn("memset", rf_source)
        self.assertNotIn("S_sCitSonKopya", rf_source)

    def test_board_without_measurements_gets_no_cit_api(self) -> None:
        spec = self._spec()
        # RF kartin cihazi yalniz device_init ister -> CIT olcumu uretmez.
        spec["devices"][1] = {**spec["devices"][1], "operations_requested": ["device_init"]}
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            rf_header = (out / "tests" / "rf_kart.h").read_text(encoding="utf-8")
            ana_header = (out / "tests" / "ana_kart.h").read_text(encoding="utf-8")
        self.assertNotIn("CitRun", rf_header)
        self.assertNotIn("spec2code_cit.h", rf_header)
        self.assertIn("void anaKartCitRun(SBoardCit* spCit);", ana_header)


class BoardNameRobustnessTests(unittest.TestCase):
    def test_long_turkish_board_name_stays_within_line_limit(self) -> None:
        """Kart adi serbest metin: uretilen satirlar 100 sutun kuralini asmamali."""
        spec = _base_spec("uzun_ad_demo")
        spec["boards"] = [
            {"id": "main", "name": "Yuksek Frekans Genisletme Karti", "role": "main"},
            {"id": "rf", "name": "RF Kart", "role": "peripheral"},
        ]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            board_dir = out / "tests"
            source = (board_dir / "yuksek_frekans_genisletme_karti.c").read_text(
                encoding="utf-8")
            header = (board_dir / "yuksek_frekans_genisletme_karti.h").read_text(
                encoding="utf-8")
        self.assertIn("void yuksekFrekansGenisletmeKartiCitRun(SBoardCit* spCit)", source)
        self.assertIn("int yuksekFrekansGenisletmeKartiInit(void);", header)
        too_long = [line for line in (source + header).splitlines() if len(line) > 100]
        self.assertEqual(too_long, [], f"100 sutunu asan satir: {too_long}")

    def test_device_with_undeclared_board_id_lands_on_the_main_board(self) -> None:
        """Dogrulayici bunu zaten hata sayar; codegen'de cihaz SESSIZCE KAYBOLMAZ.

        Surucu dosyasi ana kart klasorune duserse kart modulu de onu ilklendirmeli
        (klasor ile modul sahipligi ayrisamaz).
        """
        spec = _base_spec("yetim_kart_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "yok_boyle_kart"}]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            self.assertTrue((out / "drivers" / "ana_kart" / "tmp101.c").is_file())
            ana_source = (out / "tests" / "ana_kart.c").read_text(
                encoding="utf-8")
        self.assertIn("tmp101DeviceInit", ana_source)

    def test_two_boards_folding_to_one_identifier_fail_loudly(self) -> None:
        spec = _base_spec("cakisan_ad_demo")
        spec["boards"] = [{"id": "a", "name": "RF Kart", "role": "main"},
                          {"id": "b", "name": "rf kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "a"},
                           {**spec["devices"][1], "board_id": "b"}]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                codegen.generate(spec, Path(tmp) / "p")


class BoardQcCoverageTests(unittest.TestCase):
    """QC kapisi kart klasorlerini GORMELI (duz glob onlari sessizce atlardi)."""

    def test_driver_include_dirs_lists_every_board_folder(self) -> None:
        from orchestrator.qc import runners

        with tempfile.TemporaryDirectory() as tmp:
            spec = _base_spec("qc_kapsam_demo")
            spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                              {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
            spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                               {**spec["devices"][1], "board_id": "rf"}]
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            dirs = [p.name for p in runners.driver_include_dirs(out / "drivers")]
            # QC dongusunun denetleyecegi .c dosyalari (rglob, duz glob DEGIL).
            c_files = sorted(p.name for p in (out / "drivers").rglob("*.c"))
            test_files = sorted(p.name for p in (out / "tests").glob("*.c"))
        self.assertEqual(dirs, ["drivers", "ana_kart", "rf_kart"])
        self.assertIn("ana_kart.c", test_files)  # kart modulu test bench artefakti: tests/
        self.assertNotIn("ana_kart.c", c_files)
        self.assertIn("tmp101.c", c_files)

    def test_drivers_and_cit_never_include_test_bench_headers(self) -> None:
        """Tasinabilirlik: drivers/ ve cit/ yalniz kendi basliklari + Xilinx BSP + libc; test
        bench (spec2code_*, <mod>_test.h, tests/) basliklari OLMAZ - kart tanimliyken de."""
        spec = _base_spec("tasinabilirlik_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            offenders: list[str] = []
            for path in [*(out / "drivers").rglob("*.[ch]"), *(out / "cit").rglob("*.[ch]")]:
                text = path.read_text(encoding="utf-8")
                for inc in re.findall(r'#include\s+"([^"]+)"', text):
                    if inc.startswith("spec2code") or inc.endswith("_test.h") or "/" in inc:
                        offenders.append(f"{path.name}: {inc}")
                if re.search(r"\bspec2code(?!\.)\w*\s*\(", text):
                    offenders.append(f"{path.name}: spec2code* cagrisi")
        self.assertEqual(offenders, [])

    def test_driver_include_dirs_unchanged_without_boards(self) -> None:
        from orchestrator.qc import runners

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(_base_spec("qc_kapsam_duz"), out)
            dirs = runners.driver_include_dirs(out / "drivers")
        self.assertEqual(dirs, [out / "drivers"])


class BoardStagingTests(unittest.TestCase):
    """Vitis staging kart alt klasorlerini korur ve include yoluna ekler."""

    def test_staged_header_dirs_covers_every_board_folder(self) -> None:
        self.assertEqual(
            staged_header_dirs([
                "drivers/dbg_printf.h",
                "drivers/dbg_printf.c",
                "drivers/ana_kart/ltc2991.h", "drivers/ana_kart/ltc2991.c",
                "drivers/rf_kart/tmp101.c", "drivers/rf_kart/tmp101.h",
                "tests/ana_kart.h", "tests/rf_kart.h", "tests/tmp101_test.h", "spec2code_selftest_main.h",
            ]),
            ["drivers", "drivers/ana_kart", "drivers/rf_kart", "tests"],
        )

    def test_stage_vitis_sources_keeps_board_subdirectories(self) -> None:
        # stage_vitis_sources depo kokunun ALTINDAKI dosyalari kopyalar; uretim
        # bu yuzden repo icindeki gecici bir klasore yapilir.
        work = Path(tempfile.mkdtemp(prefix="board_stage_", dir=str(ROOT)))
        try:
            spec = _base_spec("stage_demo")
            spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                              {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
            spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                               {**spec["devices"][1], "board_id": "rf"}]
            out_dir = work / "gen"
            written = codegen.generate(spec, out_dir)
            job = Job(id="stage_test", spec=spec)
            job.result = {
                "out_dir": Path(out_dir).relative_to(ROOT).as_posix(),
                "files": [Path(p).relative_to(ROOT).as_posix() for p in written],
            }
            staged = stage_vitis_sources(job, work / "src")
        finally:
            shutil.rmtree(work, ignore_errors=True)

        self.assertIn("tests/rf_kart.h", staged)
        self.assertIn("drivers/rf_kart/tmp101.c", staged)
        self.assertIn("tests/ana_kart.c", staged)
        # Ilgisiz kart baslikleri de dahil her klasor app include yoluna girer;
        # nitelenmemis #include "tmp101.h" bu sayede calismaya devam eder.
        self.assertEqual(
            [d for d in staged_header_dirs(staged) if d.startswith("drivers")],
            ["drivers", "drivers/ana_kart", "drivers/rf_kart"],
        )


if __name__ == "__main__":
    unittest.main()
