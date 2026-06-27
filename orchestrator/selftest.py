"""End-to-end deterministic self-test (no UI, no LLM).

    python -m orchestrator.selftest [spec.json]

Generates drivers + runs the QC loop for a spec (default: the radar_io_board sample) and prints
a pass/fail summary. Exit code 0 on QC pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from orchestrator import codegen
from orchestrator.qc import loop

_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_RULESET_REF = "std/default.ruleset.json"


def main(argv: list[str]) -> int:
    spec_path = Path(argv[1]) if len(argv) > 1 else _ROOT / "specs/samples/radar_io_board.spec.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec = {**spec, "coding_standard_ref": _DEFAULT_RULESET_REF}
    ruleset = json.loads((_ROOT / _DEFAULT_RULESET_REF).read_text(encoding="utf-8"))
    out_dir = _ROOT / "outputs" / spec["project"]["name"]

    files = codegen.generate(spec, out_dir, emit=lambda e: print("  ", e))
    report = loop.run_qc(out_dir, ruleset, max_rounds=spec.get("generation_options", {}).get("qc_max_rounds", 3))
    print(f"\nfiles: {len(files)} | qc.passed: {report['passed']} | "
          f"violations: {len(report['final_violations'])}")
    if report["warning"]:
        print("warning:", report["warning"])
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
