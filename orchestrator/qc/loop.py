"""QC loop (Brief 15).

generate -> clang-format -> naming-linter -> clang-tidy + cppcheck -> collect structured
violations -> (if a fixer is wired and round < N) feed back -> repeat. N default 3.

Gate policy: a run PASSES when there are no `error`-severity violations. Warnings/style/info
are reported but advisory. If N rounds can't clear the errors, the loop stops, keeps the best
attempt, and emits a clear warning (Brief 15). Every round is streamed via `emit`; a full
dump is written to qc_report.json.

The optional `fixer(file_path, violations)` callback is how the LLM plugs in later (Brief 14);
with no fixer the loop is fully deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Optional

from hostplat import io as hio
from orchestrator.qc import naming_linter, runners

Emit = Callable[[dict], None]
Fixer = Callable[[Path, list[runners.Violation]], None]


def _counts(violations: list[runners.Violation]) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in violations:
        out[v.severity] = out.get(v.severity, 0) + 1
    return out


def _gate_errors(violations: list[runners.Violation]) -> list[runners.Violation]:
    return [v for v in violations if v.severity == "error"]


def run_qc(
    out_dir: Path,
    ruleset: dict,
    *,
    max_rounds: int = 3,
    emit: Optional[Emit] = None,
    fixer: Optional[Fixer] = None,
) -> dict:
    emit = emit or (lambda _e: None)
    out_dir = Path(out_dir)
    drivers_dir = out_dir / "drivers"
    tests_dir = out_dir / "tests"
    include_dirs = [drivers_dir]

    # Write the clang-format config derived from the ruleset, so `-style=file` finds it.
    hio.write_output(out_dir / ".clang-format", runners.clang_format_config(ruleset))

    c_files = sorted([*drivers_dir.glob("*.c"), *tests_dir.glob("*.c")])
    fmt_files = sorted([
        *drivers_dir.glob("*.c"),
        *drivers_dir.glob("*.h"),
        *tests_dir.glob("*.c"),
        *tests_dir.glob("*.h"),
    ])

    tool_status = {"clang-format": None, "clang-tidy": None, "cppcheck": None, "libclang": None}
    rounds: list[dict] = []
    best: tuple[int, list[dict]] = (10**9, [])  # (error_count, violations) of best round

    for rnd in range(1, max_rounds + 1):
        # 1) format (also our CRLF re-write path)
        fmt_available = True
        for f in fmt_files:
            available, _changed, reason = runners.format_file(f, out_dir)
            fmt_available = fmt_available and available
            if not available:
                emit({"event": "qc.tool_missing", "tool": "clang-format", "reason": reason})
                break
        tool_status["clang-format"] = fmt_available

        # 2) checks
        violations: list[runners.Violation] = []
        for f in c_files:
            nl = naming_linter.lint_file(f, ruleset, include_dirs)
            violations += nl
            tidy = runners.run_clang_tidy(f, include_dirs)
            cpp = runners.run_cppcheck(f, include_dirs)
            tool_status["clang-tidy"] = tidy.available
            tool_status["cppcheck"] = cpp.available
            violations += tidy.violations + cpp.violations
        tool_status["libclang"] = not any(
            v.rule == "naming.libclang_missing" for v in violations)

        errors = _gate_errors(violations)
        counts = _counts(violations)
        round_record = {
            "round": rnd,
            "counts": counts,
            "errors": len(errors),
            "violations": [v.to_dict() for v in violations],
        }
        rounds.append(round_record)
        emit({"event": "qc.round", "round": rnd, "errors": len(errors),
              "warnings": counts.get("warning", 0), "total": len(violations)})

        if len(errors) < best[0]:
            best = (len(errors), [v.to_dict() for v in violations])

        if not errors:
            break
        if fixer is None or rnd == max_rounds:
            break
        # feed violations back to the fixer (LLM) and try again
        emit({"event": "qc.fix", "round": rnd, "errors": len(errors)})
        by_file: dict[str, list[runners.Violation]] = {}
        for v in errors:
            by_file.setdefault(v.file, []).append(v)
        for file_str, vs in by_file.items():
            fixer(Path(file_str), vs)

    passed = best[0] == 0
    warning = None
    if not passed:
        warning = (f"QC did not fully clean in {max_rounds} round(s): "
                   f"{best[0]} error-level violation(s) remain. Output delivered anyway - "
                   f"review qc_report.json and fix by hand.")

    report = {
        "passed": passed,
        "max_rounds": max_rounds,
        "rounds_run": len(rounds),
        "tools": tool_status,
        "final_violations": best[1],
        "warning": warning,
    }
    hio.write_output(out_dir / "qc_report.json", json.dumps(report, indent=2))
    emit({"event": "qc.done", "passed": passed, "errors": best[0], "warning": warning})
    return report
