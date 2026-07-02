import json
import shutil
import tempfile
import unittest
from pathlib import Path

import spec2code_cli

ROOT = Path(__file__).resolve().parent.parent


class CliBuildTests(unittest.TestCase):
    def test_build_generates_and_passes_qc(self) -> None:
        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
        spec["project"]["name"] = "cli_unit_build"
        out_dir = ROOT / "outputs" / "cli_unit_build"
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            try:
                code = spec2code_cli.main(["build", "--spec", str(spec_path)])
                self.assertEqual(code, 0)
                self.assertTrue((out_dir / "drivers").is_dir())
                self.assertTrue(any((out_dir / "tests").glob("*_testbench_ops.c")))
            finally:
                shutil.rmtree(out_dir, ignore_errors=True)

    def test_build_rejects_invalid_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "bad.json"
            spec_path.write_text(json.dumps({"schema_version": "1.0"}), encoding="utf-8")
            code = spec2code_cli.main(["build", "--spec", str(spec_path)])
        self.assertEqual(code, 2)

    def test_build_requires_complete_vitis_arguments(self) -> None:
        spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
        spec["project"]["name"] = "cli_unit_vitis_args"
        with tempfile.TemporaryDirectory() as tmp:
            spec_path = Path(tmp) / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            code = spec2code_cli.main([
                "build", "--spec", str(spec_path), "--vitis", "C:/Xilinx/Vitis/2023.2",
            ])
        self.assertEqual(code, 2)

    def test_build_reports_missing_spec_file(self) -> None:
        code = spec2code_cli.main(["build", "--spec", "does_not_exist.json"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
