"""/api/outputs/<proje>/result: son uretim diskten yeniden kurulur (sayfa yenileme sonrasi)."""

from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.main import app  # noqa: E402


class OutputsResultApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        self.out = ROOT / "outputs" / "unit_outputs_result"
        (self.out / "drivers").mkdir(parents=True, exist_ok=True)
        (self.out / "drivers" / "a.c").write_text("int a;\n", encoding="utf-8")
        (self.out / "qc_report.json").write_text(json.dumps({"passed": True, "max_rounds": 1, "rounds_run": 1,
                                                             "tools": {}, "final_violations": [], "warning": None}),
                                                 encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.out, ignore_errors=True)

    def test_rebuilds_files_and_qc_from_disk(self) -> None:
        r = self.client.get("/api/outputs/unit_outputs_result/result")
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        names = {f["relative_path"] for f in body["files"]}
        self.assertIn("drivers/a.c", names)
        self.assertEqual([f["content"] for f in body["files"] if f["name"] == "a.c"], ["int a;\n"])
        self.assertTrue(body["qc"]["passed"])

    def test_unknown_project_is_404_and_bad_name_is_400(self) -> None:
        self.assertEqual(self.client.get("/api/outputs/nope_nope_nope/result").status_code, 404)
        self.assertEqual(self.client.get("/api/outputs/bad%20name%21/result").status_code, 400)


if __name__ == "__main__":
    unittest.main()
