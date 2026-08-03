"""QC arac zinciri regresyonlari (MicroBlaze Faz 5 E2E kosusunda bulundu).

Iki gercek "sessiz gecis" hatasi:

1. **Windows mutlak yolu clang-tidy/cppcheck ciktisinda ayristirilamiyordu.**
   Her iki runner arac cagrisina MUTLAK yolu verir; Windows'ta arac o yolu
   `C:\\...\\tmp101.c:12:5: warning: ...` seklinde geri yazar. Ayristirici
   `[^:]+` dosya grubuyla surucu harfi iki nokta ustustesinde durdugu icin
   satir HIC eslesmiyordu -> bulgular sessizce dusuyor, QC "arac var, 0 ihlal"
   diyordu. Yani Windows'ta clang-tidy/cppcheck hic bir sey yakalayamazdi.

2. **Visual Studio ile gelen LLVM bulunamiyordu.** VS "Desktop development with
   C++" -> "C++ Clang tools for Windows" clang-format/clang-tidy'yi VS agacina
   kurar ve PATH'e KOYMAZ. Bilinen dizin listesinde olmadigi icin QC bu cok
   yaygin makinelerde sessizce dejenere oluyordu.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from hostplat import tools
from orchestrator.qc import runners


class WindowsAbsolutePathDiagnosticsTests(unittest.TestCase):
    """Surucu harfli mutlak yollar ayristirilabilmeli (yoksa sessiz gecis)."""

    TIDY_LINE = (
        r"C:\Users\dev\out\drivers\tmp101.c:12:5: warning: "
        r"Undefined or garbage value returned to caller "
        r"[clang-analyzer-core.uninitialized.UndefReturn]"
    )
    CPPCHECK_LINE = (
        r"D:\proj\out\drivers\ltc2991.c:44:9: style: "
        r"Variable is assigned a value that is never used. [unreadVariable]"
    )

    def test_clang_tidy_line_with_drive_letter_is_parsed(self) -> None:
        match = runners._TIDY_RE.match(self.TIDY_LINE.strip())
        self.assertIsNotNone(match, "surucu harfli clang-tidy satiri ayristirilamadi")
        assert match is not None
        self.assertEqual(match.group("file"), r"C:\Users\dev\out\drivers\tmp101.c")
        self.assertEqual(match.group("line"), "12")
        self.assertEqual(match.group("col"), "5")
        self.assertEqual(match.group("sev"), "warning")
        self.assertEqual(match.group("rule"), "clang-analyzer-core.uninitialized.UndefReturn")

    def test_cppcheck_line_with_drive_letter_is_parsed(self) -> None:
        match = runners._CPPCHECK_RE.match(self.CPPCHECK_LINE.strip())
        self.assertIsNotNone(match, "surucu harfli cppcheck satiri ayristirilamadi")
        assert match is not None
        self.assertEqual(match.group("file"), r"D:\proj\out\drivers\ltc2991.c")
        self.assertEqual(match.group("rule"), "unreadVariable")
        self.assertEqual(match.group("sev"), "style")

    def test_posix_absolute_and_relative_paths_still_parse(self) -> None:
        """Surucu harfi ONEKI opsiyoneldir: macOS/Linux davranisi degismedi."""
        posix = "/home/dev/out/drivers/tmp101.c:7:1: error: bad thing [some-check]"
        relative = "drivers/tmp101.c:7:1: error: bad thing [some-check]"
        for line in (posix, relative):
            with self.subTest(line=line):
                match = runners._TIDY_RE.match(line)
                self.assertIsNotNone(match)
                assert match is not None
                self.assertEqual(match.group("line"), "7")

    def test_clang_tidy_findings_reach_the_violation_list(self) -> None:
        """Uctan uca: sahte clang-tidy ciktisi -> Violation nesnesi."""
        target = Path(r"C:\Users\dev\out\drivers\tmp101.c")
        fake_stdout = "2120 warnings generated.\n" + self.TIDY_LINE + "\n"
        with mock.patch.object(tools, "resolve", return_value=Path("clang-tidy.exe")), \
             mock.patch.object(runners.proc, "run",
                               return_value=mock.Mock(stdout=fake_stdout, stderr="", returncode=0)), \
             mock.patch.object(Path, "resolve", lambda self: self):
            result = runners.run_clang_tidy(target, [])
        self.assertTrue(result.available)
        self.assertEqual(len(result.violations), 1, "Windows yolunda bulgu dusuruldu")
        self.assertEqual(result.violations[0].rule,
                         "clang-analyzer-core.uninitialized.UndefReturn")
        self.assertEqual(result.violations[0].source, "clang-tidy")


class ClangTidyCheckSelectionTests(unittest.TestCase):
    def test_annex_k_buffer_handling_check_is_disabled(self) -> None:
        """C11 Annex K (`memset_s`) Xilinx bare-metal newlib'de YOKTUR.

        Kontrolu acik birakmak, uyulmasi imkansiz (linklenmez) bir tavsiyeyle
        her uretilen projeye kalici uyari basardi.
        """
        captured: dict = {}

        def _capture(cmd, **kwargs):
            captured["cmd"] = cmd
            return mock.Mock(stdout="", stderr="", returncode=0)

        with mock.patch.object(tools, "resolve", return_value=Path("clang-tidy.exe")), \
             mock.patch.object(runners.proc, "run", side_effect=_capture):
            runners.run_clang_tidy(Path("x.c"), [])
        checks = next(arg for arg in captured["cmd"] if str(arg).startswith("--checks="))
        self.assertIn("-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling",
                      checks)
        self.assertIn("clang-analyzer-*", checks)


class VisualStudioBundledLlvmTests(unittest.TestCase):
    VS_BIN = (r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools"
              r"\VC\Tools\Llvm\x64\bin")

    def test_visual_studio_llvm_dirs_are_searched_on_windows(self) -> None:
        with mock.patch.object(tools, "_IS_WINDOWS", True), \
             mock.patch.object(tools, "_IS_MAC", False), \
             mock.patch.object(tools, "_visual_studio_llvm_dirs", return_value=[self.VS_BIN]):
            self.assertIn(self.VS_BIN, tools._known_bin_dirs())

    def test_visual_studio_llvm_dirs_are_not_searched_off_windows(self) -> None:
        with mock.patch.object(tools, "_IS_WINDOWS", False), \
             mock.patch.object(tools, "_IS_MAC", False), \
             mock.patch.object(tools, "_visual_studio_llvm_dirs", return_value=[self.VS_BIN]):
            self.assertNotIn(self.VS_BIN, tools._known_bin_dirs())

    def test_newest_visual_studio_install_wins(self) -> None:
        """Birden fazla VS kurulumunda siralama deterministik ve yeniden eskiye."""
        found = [
            r"C:\Program Files\Microsoft Visual Studio\2019\Community\VC\Tools\Llvm\bin",
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\x64\bin",
            r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\Llvm\bin",
        ]
        with mock.patch("glob.glob", side_effect=lambda pattern: list(found)):
            dirs = tools._visual_studio_llvm_dirs()
        self.assertEqual(dirs[0], found[1], "2022/x64 kurulumu once gelmeli")
        self.assertEqual(len(dirs), len(set(dirs)), "tekrar eden dizin dondu")

    def test_resolve_finds_clang_tidy_in_visual_studio_tree(self) -> None:
        expected = Path(self.VS_BIN) / "clang-tidy.exe"
        with mock.patch.dict("os.environ", {}, clear=False) as env:
            env.pop("SPEC2CODE_CLANG_TIDY_PATH", None)
            with mock.patch.object(tools, "_IS_WINDOWS", True), \
                 mock.patch.object(tools, "_IS_MAC", False), \
                 mock.patch.object(tools, "_KNOWN_BIN_DIRS_WINDOWS", []), \
                 mock.patch.object(tools, "_visual_studio_llvm_dirs", return_value=[self.VS_BIN]), \
                 mock.patch("shutil.which", return_value=None), \
                 mock.patch.object(Path, "is_file", lambda self: self == expected):
                self.assertEqual(tools.resolve("clang-tidy", required=False), expected)


if __name__ == "__main__":
    unittest.main()
