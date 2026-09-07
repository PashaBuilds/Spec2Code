"""Saha makinesi uyumu (2026-09-07, sirket bilgisayari, paketli uygulama).

1. Eski clang-format (<10) `.clang-format` icindeki `AllowShortBlocksOnASingleLine:
   Never` enum'unu ve `UseCRLF`/`DeriveLineEnding` anahtarlarini reddediyordu:
   her dosyada `qc.format_failed` -> 63 error -> QC KALDI. Config artik boolean
   yazilir, yerel aracla dogrulanir ve reddedilirse legacy config'e duser.
2. PyInstaller --onefile paketinde `Path(__file__)` tabanli kokler gecici
   `_MEIxxxx` klasorunu gosteriyordu; outputs/specs/uploads uygulama kapaninca
   siliniyordu. Yazilabilir kok artik `hostplat.paths.data_root()`.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hostplat import paths, tools
from orchestrator.qc import runners

RULESET = {"formatting": {"brace_style": "allman", "indent": "spaces_4",
                          "max_line_length": 100, "line_ending": "crlf"}}


class ClangFormatConfigCompatTests(unittest.TestCase):
    def test_short_blocks_option_is_boolean_not_enum(self) -> None:
        for legacy in (False, True):
            text = runners.clang_format_config(RULESET, legacy=legacy)
            self.assertIn("AllowShortBlocksOnASingleLine: false\n", text)
            self.assertNotIn("Never\n", text.replace("UseTab: Never\n", ""))

    def test_legacy_config_drops_line_ending_keys(self) -> None:
        full = runners.clang_format_config(RULESET)
        legacy = runners.clang_format_config(RULESET, legacy=True)
        self.assertIn("UseCRLF: true\n", full)
        self.assertIn("DeriveLineEnding: false\n", full)
        self.assertNotIn("UseCRLF", legacy)
        self.assertNotIn("DeriveLineEnding", legacy)
        self.assertIn("BreakBeforeBraces: Allman\n", legacy)

    def test_rejected_config_falls_back_to_legacy(self) -> None:
        """Arac ilk config'i 'invalid boolean' ile reddederse legacy yazilir ve None doner."""
        calls: list[str] = []

        def _fake_run(cmd, **kwargs):
            content = (Path(kwargs["cwd"]) / ".clang-format").read_text(encoding="utf-8")
            calls.append(content)
            if "UseCRLF" in content:
                return mock.Mock(ok=False, stdout="", returncode=1,
                                 stderr="YAML:14:32: error: invalid boolean\nError reading .clang-format: Invalid argument")
            return mock.Mock(ok=True, stdout="---\n", stderr="", returncode=0)

        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(tools, "resolve", return_value=Path("clang-format.exe")), \
             mock.patch.object(runners.proc, "run", side_effect=_fake_run):
            error = runners.write_clang_format_config(Path(tmp), RULESET)
            final = (Path(tmp) / ".clang-format").read_text(encoding="utf-8")
        self.assertIsNone(error)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("UseCRLF", final)
        self.assertIn("AllowShortBlocksOnASingleLine: false", final)

    def test_unfixable_rejection_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(tools, "resolve", return_value=Path("clang-format.exe")), \
             mock.patch.object(runners.proc, "run",
                               return_value=mock.Mock(ok=False, stdout="", stderr="YAML:2:1: error: unknown key", returncode=1)):
            error = runners.write_clang_format_config(Path(tmp), RULESET)
        self.assertIn("unknown key", error or "")

    def test_without_tool_config_is_still_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(tools, "resolve", return_value=None):
            self.assertIsNone(runners.write_clang_format_config(Path(tmp), RULESET))
            self.assertTrue((Path(tmp) / ".clang-format").is_file())


class DataRootTests(unittest.TestCase):
    def test_source_run_uses_repo_root(self) -> None:
        with mock.patch.dict(os.environ, {"SPEC2CODE_DATA_DIR": ""}):
            self.assertEqual(paths.data_root(), Path(__file__).resolve().parent.parent)

    def test_env_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.dict(os.environ, {"SPEC2CODE_DATA_DIR": tmp}):
            self.assertEqual(paths.data_root(), Path(tmp).resolve())

    def test_frozen_app_writes_next_to_executable_not_meipass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.dict(os.environ, {"SPEC2CODE_DATA_DIR": ""}), \
             mock.patch.object(sys, "frozen", True, create=True), \
             mock.patch.object(sys, "_MEIPASS", str(Path(tmp) / "_MEI123"), create=True), \
             mock.patch.object(sys, "executable", str(Path(tmp) / "app" / "Spec2Code.exe")):
            root = paths.data_root()
        self.assertEqual(root, (Path(tmp) / "app").resolve())
        self.assertNotIn("_MEI", str(root))


if __name__ == "__main__":
    unittest.main()
