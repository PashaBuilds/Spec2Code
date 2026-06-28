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
            self.assertIn("tests/unit_mock_codegen_mock_plan.c", written)

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
            self.assertIn(f"outputs/{project_name}/tests/{project_name}_mock_plan.c", files)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
