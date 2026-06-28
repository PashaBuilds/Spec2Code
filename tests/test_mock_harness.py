import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.jobs import Job, JobManager, _OUTPUTS
from orchestrator import codegen


ROOT = Path(__file__).resolve().parent.parent


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


class MockHarnessTests(unittest.TestCase):
    def test_codegen_writes_mock_harness_files(self) -> None:
        spec = load_sample_spec("unit_mock_codegen")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]

            written = {Path(path).relative_to(out_dir).as_posix() for path in codegen.generate(spec, out_dir)}

            self.assertIn("tests/spec2code_mock_bus.h", written)
            self.assertIn("tests/spec2code_mock_bus.c", written)
            self.assertIn("tests/unit_mock_codegen_mock_plan.h", written)
            self.assertIn("tests/unit_mock_codegen_mock_plan.c", written)

    def test_every_generated_c_file_has_matching_header(self) -> None:
        spec = load_sample_spec("unit_c_header_pairing")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]

            codegen.generate(spec, out_dir)

            c_files = sorted(out_dir.glob("**/*.c"))
            self.assertGreater(len(c_files), 0)
            for c_file in c_files:
                header = c_file.with_suffix(".h")
                self.assertTrue(
                    header.is_file(),
                    f"missing matching header for {c_file.relative_to(out_dir).as_posix()}",
                )

            ltc_test_header = (out_dir / "tests" / "ltc2991_test.h").read_text(encoding="utf-8")
            self.assertIn("int ltc2991SelfTest(XIicPs* spIic);", ltc_test_header)
            self.assertIn("void ltc2991TestTask(void* vpParameters);", ltc_test_header)

            mock_plan_header = (out_dir / "tests" / "unit_c_header_pairing_mock_plan.h").read_text(
                encoding="utf-8",
            )
            self.assertIn("int spec2codeMockPlanLoad(void);", mock_plan_header)

    def test_backend_result_includes_mock_harness_files(self) -> None:
        project_name = "unit_mock_backend_result"
        spec = load_sample_spec(project_name)
        out_dir = _OUTPUTS / project_name
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            job = Job(id="unit_mock_backend", spec=spec)

            JobManager()._blocking(job, max_rounds=1)

            self.assertIsNotNone(job.result)
            files = set(job.result["files"])
            self.assertIn(f"outputs/{project_name}/tests/spec2code_mock_bus.h", files)
            self.assertIn(f"outputs/{project_name}/tests/spec2code_mock_bus.c", files)
            self.assertIn(f"outputs/{project_name}/tests/{project_name}_mock_plan.h", files)
            self.assertIn(f"outputs/{project_name}/tests/{project_name}_mock_plan.c", files)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
