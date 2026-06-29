import json
import shutil
import tempfile
import unittest
from pathlib import Path

from backend.jobs import Job, JobManager, _OUTPUTS
from orchestrator import codegen


ROOT = Path(__file__).resolve().parent.parent
RETIRED_BOARDLESS_FRAGMENTS = ("spec2code_" + "mo" + "ck", "_" + "mo" + "ck" + "_plan")


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


def has_retired_boardless_path(paths: set[str]) -> bool:
    return any(any(fragment in path.lower() for fragment in RETIRED_BOARDLESS_FRAGMENTS) for path in paths)


class GeneratedOutputTests(unittest.TestCase):
    def test_codegen_does_not_write_retired_boardless_files(self) -> None:
        spec = load_sample_spec("unit_generated_outputs")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]

            written = {Path(path).relative_to(out_dir).as_posix() for path in codegen.generate(spec, out_dir)}

            self.assertFalse(has_retired_boardless_path(written))
            self.assertIn("tests/spec2code_testbench_protocol.h", written)
            self.assertIn("tests/spec2code_testbench_protocol.c", written)
            self.assertIn("tests/unit_generated_outputs_testbench_ops.h", written)
            self.assertIn("tests/unit_generated_outputs_testbench_ops.c", written)

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

    def test_backend_result_does_not_include_retired_boardless_files(self) -> None:
        project_name = "unit_generated_backend_result"
        spec = load_sample_spec(project_name)
        out_dir = _OUTPUTS / project_name
        shutil.rmtree(out_dir, ignore_errors=True)
        try:
            job = Job(id="unit_generated_backend", spec=spec)

            JobManager()._blocking(job, max_rounds=1)

            self.assertIsNotNone(job.result)
            files = set(job.result["files"])
            self.assertFalse(has_retired_boardless_path(files))
            self.assertIn(f"outputs/{project_name}/tests/spec2code_testbench_protocol.h", files)
            self.assertIn(f"outputs/{project_name}/tests/{project_name}_testbench_ops.c", files)
        finally:
            shutil.rmtree(out_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
