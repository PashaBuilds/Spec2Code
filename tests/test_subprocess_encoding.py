"""Alt surec ciktisi UTF-8 cozulur; formatlayici hatasinda dosya BOSALTILMAZ.

Sahada bulunan VERI KAYBEDEN hata (Windows + Turkce yerel ayar, cp1254):

1. `hostplat.proc.run` alt sureci `text=True` ile ACIK encoding VERMEDEN
   calistiriyordu. Python o durumda `locale.getpreferredencoding(False)`
   kullanir -> bu makinede **cp1254**. Uretilen kaynaklar ise HER ZAMAN
   UTF-8'dir (`hostplat.io.write_output` utf-8 encode eder).

2. Iki asamali yikim zinciri:
   * **1. gecis** - kaynakta uzun tire `—` (U+2014, utf8 `e2 80 94`) var.
     cp1254'te bu uc bayt TANIMLIDIR ve sessizce `â€”` mojibake'ine doner
     (0x94 -> U+201D). Dosya bozulur ama hala doludur, hata bildirilmez.
   * **2. gecis** - artik dosyada U+201D var; utf8 karsiligi `e2 80 9d` ve
     **0x9D cp1254'te TANIMSIZ**. Cozme hatasi `subprocess`'in _readerthread
     is parcaciginda patlar, disari SIZMAZ; `communicate()` bos tampon doner.
     Sonuc: `returncode=0`, `stdout=""`, `result.ok is True`.

3. `runners.format_file` bu "basarili" sonucu dogrudan geri yazardi:
   `hio.write_output(path, "")` -> **dosya 0 bayta duser**. Kurbanlar:
   `spec2code_cit.h`, `spec2code_cit.c`, `spec2code_testbench_log.c`.

Iki katmanli savunma test edilir: (a) kok neden - cikti makinenin yerel
ayarindan BAGIMSIZ olarak UTF-8 cozulur; (b) yazma kalkani - formatlayici
bos/basarisiz donerse dosyaya DOKUNULMAZ ve hata acikca bildirilir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from hostplat import io as hio
from hostplat import proc
from hostplat import tools
from orchestrator.qc import loop, runners

# cp1254'te TANIMSIZ olan baytlar. UTF-8 devam baytlari 0x80-0xBF oldugu icin
# bu baytlar gunluk Turkce metinde kolayca olusur:
#   Ş U+015E -> c5 9e | Ğ U+011E -> c4 9e | ” U+201D -> e2 80 9d | ‐ U+2010 -> e2 80 90
CP1254_UNDEFINED = {0x81, 0x8D, 0x8E, 0x8F, 0x90, 0x9D, 0x9E}

# Tam kurban kumesi: uzun tire (1. asama tetikleyici) + cp1254'te cozulemeyenler.
TRICKY_TEXT = "olcum — esik ”tamam” ‐ çİŞĞ sonu"


class ProcUtf8DecodingTests(unittest.TestCase):
    """proc.run cikti cozumu makine yerel ayarina BAGLI OLMAMALI."""

    @staticmethod
    def _emit_bytes_cmd(text: str) -> list[str]:
        """stdout'a ham UTF-8 bayt yazan bir yardimci alt surec (komut satiri saf ASCII)."""
        payload = text.encode("utf-8").hex()
        program = (
            "import sys;"
            f"sys.stdout.buffer.write(bytes.fromhex('{payload}'));"
            "sys.stdout.buffer.flush()"
        )
        return [sys.executable, "-c", program]

    def test_non_cp1254_utf8_stdout_is_decoded_not_lost(self) -> None:
        """cp1254'te TANIMSIZ bayt iceren UTF-8 cikti aynen geri gelmeli."""
        result = proc.run(self._emit_bytes_cmd(TRICKY_TEXT), timeout=60)
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.ok)
        self.assertNotEqual(
            result.stdout, "",
            "cikti BOS geldi: cozme hatasi _readerthread icinde yutuldu (kok hata)")
        self.assertEqual(result.stdout, TRICKY_TEXT)

    def test_em_dash_survives_round_trip_without_mojibake(self) -> None:
        """Uzun tire cp1254 mojibake'ine (`â€”`) donmemeli - 1. asama bozulma."""
        result = proc.run(self._emit_bytes_cmd("uzun tire — burada"), timeout=60)
        self.assertIn("—", result.stdout)
        self.assertNotIn("€", result.stdout, "em dash cp1254 mojibake'ine dondu")
        self.assertNotIn("”", result.stdout, "em dash cp1254 mojibake'ine dondu")

    def test_stderr_is_decoded_with_utf8_too(self) -> None:
        payload = TRICKY_TEXT.encode("utf-8").hex()
        program = (
            "import sys;"
            f"sys.stderr.buffer.write(bytes.fromhex('{payload}'));"
            "sys.stderr.buffer.flush()"
        )
        result = proc.run([sys.executable, "-c", program], timeout=60)
        self.assertEqual(result.stderr, TRICKY_TEXT)

    def test_undecodable_bytes_never_raise_and_never_empty_the_stream(self) -> None:
        """Gecersiz UTF-8 dizisi bile istisna atmamali; cikti kaybolmamali."""
        program = (
            "import sys;"
            "sys.stdout.buffer.write(b'bas' + bytes([0xFF, 0xFE]) + b'son');"
            "sys.stdout.buffer.flush()"
        )
        result = proc.run([sys.executable, "-c", program], timeout=60)
        self.assertTrue(result.stdout.startswith("bas"))
        self.assertTrue(result.stdout.endswith("son"))

    def test_stdout_is_always_encodable_back_to_utf8(self) -> None:
        """Cikti hostplat.io.write_output'tan gecebilmeli (surrogate OLMAMALI).

        `errors="surrogateescape"` secilseydi cozme yasal olurdu ama olusan
        yalniz-surrogate'lar `str.encode("utf-8")` sirasinda patlardi; yani
        sessiz bosaltma yerine yazma aninda cokme olurdu. `replace` bunu onler.
        """
        program = (
            "import sys;"
            "sys.stdout.buffer.write(bytes([0x9D, 0x90, 0xFF]));"
            "sys.stdout.buffer.flush()"
        )
        result = proc.run([sys.executable, "-c", program], timeout=60)
        result.stdout.encode("utf-8")  # istisna atmamali


class FormatFileNeverTruncatesTests(unittest.TestCase):
    """format_file basarisizken hedef dosyayi ASLA bosaltmamali."""

    ORIGINAL = "#include <stdint.h>\r\nint spec2code_cit_run(void)\r\n{\r\n    return 0;\r\n}\r\n"

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out_dir = Path(self._tmp.name)
        self.target = self.out_dir / "spec2code_cit.c"
        hio.write_output(self.target, self.ORIGINAL)
        self.before = self.target.read_bytes()
        self.assertGreater(len(self.before), 0)

    def _run_with_fake_tool(self, result: proc.ProcResult):
        with mock.patch.object(tools, "resolve", return_value="fake-clang-format"), \
                mock.patch.object(proc, "run", return_value=result):
            return runners.format_file(self.target, self.out_dir)

    def test_empty_stdout_with_success_returncode_leaves_file_intact(self) -> None:
        """KOK VAKA: rc=0 ama stdout bos -> dosya KORUNMALI, hata bildirilmeli."""
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=0, stdout="", stderr="", cmd=["fake"]))
        self.assertEqual(self.target.read_bytes(), self.before,
                         "dosya BOSALTILDI/degistirildi - veri kaybi")
        self.assertGreater(self.target.stat().st_size, 0)
        self.assertTrue(available)
        self.assertFalse(changed)
        self.assertIsNotNone(reason, "sessizce basarili gorundu; hata bildirilmedi")

    def test_whitespace_only_stdout_leaves_file_intact(self) -> None:
        """Sadece bosluk donen formatlayici da kaynagi silmis sayilir."""
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=0, stdout="   \r\n\t \r\n", stderr="", cmd=["fake"]))
        self.assertEqual(self.target.read_bytes(), self.before)
        self.assertIsNotNone(reason)

    def test_nonzero_returncode_leaves_file_intact(self) -> None:
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=1, stdout="", stderr="parse error", cmd=["fake"]))
        self.assertEqual(self.target.read_bytes(), self.before)
        self.assertTrue(available)
        self.assertFalse(changed)
        self.assertIn("parse error", reason or "")

    def test_timeout_leaves_file_intact(self) -> None:
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=124, stdout="", stderr="timeout after 60s",
                            cmd=["fake"], timed_out=True))
        self.assertEqual(self.target.read_bytes(), self.before)
        self.assertIsNotNone(reason)

    def test_successful_format_still_replaces_content(self) -> None:
        """Kalkan normal yolu BOZMAMALI: gercek cikti eskisi gibi yazilir."""
        formatted = "#include <stdint.h>\nint spec2code_cit_run(void)\n{\n    return 1;\n}\n"
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=0, stdout=formatted, stderr="", cmd=["fake"]))
        self.assertTrue(available)
        self.assertTrue(changed)
        self.assertIsNone(reason)
        # Bayt karsilastir: read_text evrensel satir sonu cevirisi yapip CRLF'i gizler.
        self.assertEqual(self.target.read_bytes(),
                         hio.normalize_crlf(formatted).encode("utf-8"))

    def test_unchanged_content_reports_not_changed(self) -> None:
        available, changed, reason = self._run_with_fake_tool(
            proc.ProcResult(returncode=0, stdout=self.ORIGINAL, stderr="", cmd=["fake"]))
        self.assertTrue(available)
        self.assertFalse(changed)
        self.assertIsNone(reason)

    def test_empty_input_file_is_allowed_to_stay_empty(self) -> None:
        """Zaten bos bir dosya icin bos cikti mesrudur - yanlis alarm olmamali."""
        empty = self.out_dir / "bos.c"
        empty.write_bytes(b"")
        with mock.patch.object(tools, "resolve", return_value="fake-clang-format"), \
                mock.patch.object(proc, "run",
                                  return_value=proc.ProcResult(0, "", "", ["fake"])):
            available, changed, reason = runners.format_file(empty, self.out_dir)
        self.assertTrue(available)
        self.assertIsNone(reason)


class EmDashGeneratedProjectRegressionTests(unittest.TestCase):
    """Uzun tire iceren uretilmis proje QC format gecisinden SAG cikmali."""

    SOURCE = (
        "#include <stdint.h>\n"
        "/* Bayrak biti = OKUMA BASARISI (limit DEGERLENDIRMESI YOK — o host'ta). */\n"
        "int spec2code_cit_run(void)\n"
        "{\n"
        "    int deger = 0;\n"
        "    return deger;\n"
        "}\n"
    )

    def setUp(self) -> None:
        if tools.resolve("clang-format", required=False) is None:
            self.skipTest("clang-format bulunamadi")
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out_dir = Path(self._tmp.name)
        self.tests_dir = self.out_dir / "tests"
        (self.out_dir / "drivers").mkdir(parents=True, exist_ok=True)
        self.cit = self.tests_dir / "spec2code_cit.c"
        hio.write_output(self.cit, self.SOURCE)
        hio.write_output(self.out_dir / ".clang-format", runners.clang_format_config({}))

    def test_repeated_format_passes_keep_file_non_empty(self) -> None:
        """Iki asamali zincir: 1. gecis mojibake, 2. gecis BOSALTMA. Ikisi de olmamali."""
        for pass_no in (1, 2, 3):
            runners.format_file(self.cit, self.out_dir)
            size = self.cit.stat().st_size
            self.assertGreater(
                size, 0, f"{pass_no}. format gecisinde spec2code_cit.c BOSALDI")
            text = self.cit.read_text(encoding="utf-8")
            self.assertIn("spec2code_cit_run", text)
            self.assertIn("—", text, f"{pass_no}. gecis uzun tireyi bozdu")
            self.assertNotIn("€", text, f"{pass_no}. gecis mojibake uretti")

    def test_run_qc_leaves_cit_file_non_empty(self) -> None:
        """Tam QC gecisi (loop.run_qc) sonrasi CIT dosyasi dolu kalmali."""
        loop.run_qc(self.out_dir, {}, max_rounds=1)
        self.assertGreater(self.cit.stat().st_size, 0,
                           "QC gecisinden sonra spec2code_cit.c BOSALDI")
        self.assertIn("spec2code_cit_run", self.cit.read_text(encoding="utf-8"))


class QcLoopSurfacesFormatFailureTests(unittest.TestCase):
    """format_file bir hata bildirdiginde QC kapisi bunu YUTMAMALI."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out_dir = Path(self._tmp.name)
        (self.out_dir / "drivers").mkdir(parents=True, exist_ok=True)
        self.cit = self.out_dir / "tests" / "spec2code_cit.c"
        hio.write_output(self.cit, "int spec2code_cit_run(void)\n{\n    return 0;\n}\n")

    def test_format_failure_becomes_gate_error(self) -> None:
        with mock.patch.object(runners, "format_file",
                               return_value=(True, False, "clang-format bos cikti dondu")):
            report = loop.run_qc(self.out_dir, {}, max_rounds=1)
        self.assertFalse(report.get("passed"), "bicimlendirme hatasina ragmen QC GECTI")
        blob = str(report)
        self.assertIn("clang-format bos cikti dondu", blob,
                      "hata sebebi rapora hic yansimadi")


if __name__ == "__main__":
    unittest.main()
