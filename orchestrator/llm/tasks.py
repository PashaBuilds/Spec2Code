"""LLM tasks (Brief §14): test generation, optimize pass, descriptor extraction, QC fixer.

All of these run ONLY when the LLM is enabled and an endpoint is configured. Every LLM output
is re-checked by the QC loop (Brief §15), so a bad generation can't bypass the quality gate.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Callable, Optional

from hostplat import io as hio
from orchestrator.llm.client import LlmClient, LlmConfig, LlmError
from orchestrator.qc import naming_linter, runners

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)
_FUNC_DEF_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_ \t\r\n\*]*?\b([A-Za-z_][A-Za-z0-9_]*)\s*\([^;{}]*\)\s*\{",
    re.MULTILINE,
)


class LlmCandidateError(LlmError):
    """Raised when the model answered, but the candidate failed deterministic gates."""


@dataclass
class CandidateCheck:
    text: str
    warnings: int
    tools: dict[str, bool | None]


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def _function_names(source: str) -> set[str]:
    return {match.group(1) for match in _FUNC_DEF_RE.finditer(source)}


def _out_dir_for(path: Path) -> Path:
    path = Path(path)
    if path.parent.name in {"drivers", "tests"}:
        return path.parent.parent
    return path.parent


def _candidate_path_for(path: Path) -> Path:
    candidate = path.with_name(f".{path.stem}.llm_candidate{path.suffix}")
    if not candidate.exists():
        return candidate
    for idx in range(1, 100):
        candidate = path.with_name(f".{path.stem}.llm_candidate_{idx}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise LlmCandidateError(f"could not allocate temporary candidate path near {path}")


def _gate_errors(violations: list[runners.Violation]) -> list[runners.Violation]:
    return [v for v in violations if v.severity == "error"]


def _violation_summary(v: runners.Violation) -> str:
    return f"{v.source}:{v.rule} line {v.line}: {v.message}"


def _preflight_candidate_text(path: Path, original: str, candidate: str) -> str:
    suffix = path.suffix.lower()
    text = _strip_fences(candidate).strip()
    if suffix not in {".c", ".h"}:
        raise LlmCandidateError(f"unsupported LLM target file type: {path.suffix}")
    if not text:
        raise LlmCandidateError("LLM candidate is empty")
    if "```" in text:
        raise LlmCandidateError("LLM candidate still contains markdown fences")
    bad_controls = [ch for ch in text if ord(ch) < 32 and ch not in "\r\n\t"]
    if bad_controls:
        raise LlmCandidateError("LLM candidate contains unsupported control characters")
    if suffix == ".c":
        original_functions = _function_names(original)
        candidate_functions = _function_names(text)
        missing = sorted(original_functions - candidate_functions)
        if original_functions and missing:
            raise LlmCandidateError(
                "LLM candidate removed existing function definition(s): " + ", ".join(missing[:5])
            )
        if not candidate_functions:
            raise LlmCandidateError("LLM candidate does not contain any C function definitions")
    if len(original) > 400 and len(text) < int(len(original) * 0.35):
        raise LlmCandidateError(
            f"LLM candidate is suspiciously short ({len(text)} chars vs original {len(original)} chars)"
        )
    return text + "\n"


def _check_candidate(path: Path, original: str, candidate: str, ruleset: dict) -> CandidateCheck:
    path = Path(path)
    text = _preflight_candidate_text(path, original, candidate)
    out_dir = _out_dir_for(path)
    drivers_dir = out_dir / "drivers"
    include_dirs = [drivers_dir]
    temp_path = _candidate_path_for(path)
    tools: dict[str, bool | None] = {"clang-format": None, "clang-tidy": None, "cppcheck": None, "libclang": None}
    try:
        hio.write_output(out_dir / ".clang-format", runners.clang_format_config(ruleset))
        hio.write_output(temp_path, text)

        fmt_available, _changed, fmt_reason = runners.format_file(temp_path, out_dir)
        tools["clang-format"] = fmt_available
        if fmt_available and fmt_reason:
            raise LlmCandidateError(f"clang-format rejected LLM candidate: {fmt_reason}")

        formatted = temp_path.read_text(encoding="utf-8", errors="replace")
        violations: list[runners.Violation] = []
        if path.suffix.lower() == ".c":
            violations += naming_linter.lint_file(temp_path, ruleset, include_dirs)
            tidy = runners.run_clang_tidy(temp_path, include_dirs)
            cpp = runners.run_cppcheck(temp_path, include_dirs)
            tools["clang-tidy"] = tidy.available
            tools["cppcheck"] = cpp.available
            violations += tidy.violations + cpp.violations
            tools["libclang"] = not any(v.rule == "naming.libclang_missing" for v in violations)

        errors = _gate_errors(violations)
        if errors:
            first = _violation_summary(errors[0])
            raise LlmCandidateError(
                f"LLM candidate failed deterministic QC gate: {len(errors)} error(s); first: {first}"
            )
        warnings = sum(1 for v in violations if v.severity == "warning")
        return CandidateCheck(text=formatted, warnings=warnings, tools=tools)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def system_prompt(ruleset: dict) -> str:
    """Deterministic context: the coding standard the model must obey (Brief §16)."""
    fmt = ruleset.get("formatting", {})
    naming = ruleset.get("naming", {})
    prefixes = naming.get("hungarian_prefixes", {})
    declarations = ruleset.get("declarations", {})
    return (
        "You are an embedded C driver engineer generating Xilinx Vitis (bare-metal/FreeRTOS) "
        "drop-in code. Obey this coding standard exactly:\n"
        f"- Brace style: {fmt.get('brace_style', 'allman')}; indent {fmt.get('indent', 'spaces_4')}; "
        f"max line {fmt.get('max_line_length', 100)}; line endings CRLF.\n"
        "- Put one space after if/for/while and place braces on the following line.\n"
        f"- Function names MUST match: {naming.get('function_regex')} (module_object_action).\n"
        f"- Identifiers use {naming.get('identifier_case', 'camelCase')} with Hungarian prefixes: {prefixes}.\n"
        "- Struct/union typedef names use the capital S prefix (example: SOrnekStruct), "
        "but struct variables use the lowercase s Hungarian prefix "
        "(example: SOrnekStruct sMyStruct; sMyStruct.uiVal = 0;). "
        "Pointers use the type prefix plus the pointer suffix; struct pointers use sp. "
        "Arrays use the type prefix plus Arr. Globals use G_ plus the type prefix; static variables "
        "use S_ plus the type prefix.\n"
        f"- Typedef prefixes: struct {declarations.get('struct_typedef_prefix', 'S')}, "
        f"union {declarations.get('union_typedef_prefix', 'S')}, "
        f"enum {declarations.get('enum_typedef_prefix', 'E')}; bitfield members have no prefix.\n"
        "- All printed strings end with \\r\\n. Public functions get Doxygen comments.\n"
        "- Return ONLY the C source, with no markdown fences or commentary."
    )


def make_qc_fixer(
    spec: dict,
    ruleset: dict,
    *,
    emit: Optional[Callable[[dict], None]] = None,
) -> Callable[[Path, list], None]:
    """Return a fixer(path, violations) that asks the LLM to repair QC violations in a file.

    Wired into the QC loop (Brief §15). The loop re-runs QC on the rewritten file.
    """
    emit = emit or (lambda _event: None)
    client = LlmClient(LlmConfig.resolve(spec.get("llm")))
    disabled_reason: str | None = None

    def fixer(path: Path, violations: list) -> None:
        nonlocal disabled_reason
        if not client.available:
            emit({"event": "llm.skipped", "task": "qc_fix", "reason": "no base_url"})
            return
        if disabled_reason is not None:
            emit({"event": "llm.skipped", "task": "qc_fix", "reason": disabled_reason})
            return
        code = Path(path).read_text(encoding="utf-8", errors="replace")
        viol_text = "\n".join(
            f"- line {getattr(v, 'line', '?')} [{getattr(v, 'rule', '?')}] "
            f"({getattr(v, 'source', '?')}) {getattr(v, 'message', '')}"
            for v in violations
        )
        messages = [
            {"role": "system", "content": system_prompt(ruleset)},
            {"role": "user", "content": (
                f"Fix these QC violations in {Path(path).name} without changing behavior:\n\n"
                f"{viol_text}\n\n--- FILE ---\n{code}"
            )},
        ]
        emit({
            "event": "llm.request",
            "task": "qc_fix",
            "model": client.config.model,
            "timeout_s": client.config.timeout_s,
            "max_tokens": client.config.max_tokens,
        })
        try:
            fixed = _strip_fences(client.chat(messages, temperature=0.0))
            emit({
                "event": "llm.check",
                "task": "qc_fix",
                "file": str(path),
                "model": client.config.model,
            })
            check = _check_candidate(Path(path), code, fixed, ruleset)
        except LlmCandidateError as exc:
            disabled_reason = f"candidate rejected: {exc}"
            emit({
                "event": "llm.rejected",
                "task": "qc_fix",
                "model": client.config.model,
                "file": str(path),
                "message": str(exc),
            })
            return
        except LlmError as exc:
            disabled_reason = str(exc)
            emit({
                "event": "llm.error",
                "task": "qc_fix",
                "model": client.config.model,
                "message": disabled_reason,
            })
            return
        if check.text.strip():
            hio.write_output(path, check.text)
            emit({
                "event": "llm.accepted",
                "task": "qc_fix",
                "model": client.config.model,
                "file": str(path),
                "warnings": check.warnings,
            })
            emit({
                "event": "llm.done",
                "task": "qc_fix",
                "model": client.config.model,
                "chars": len(check.text),
            })

    return fixer


def generate_tests(spec: dict, ruleset: dict, descriptor: dict, runtime: str) -> str:
    """Richer, edge-case test scenarios beyond the deterministic skeleton (Brief §14.1)."""
    client = LlmClient(LlmConfig.resolve(spec.get("llm")))
    messages = [
        {"role": "system", "content": system_prompt(ruleset)},
        {"role": "user", "content": (
            f"Write a {runtime} test for the {descriptor.get('part')} driver covering meaningful "
            f"edge cases and validation. Operations: "
            f"{[op['name'] for op in descriptor.get('operations', [])]}."
        )},
    ]
    return _strip_fences(client.chat(messages, temperature=0.3))


def optimize_code(spec: dict, ruleset: dict, code: str, exemplar: str = "") -> str:
    """Produce a more optimal variant of deterministic code, on top of it (Brief §14.3)."""
    client = LlmClient(LlmConfig.resolve(spec.get("llm")))
    user = "Improve this driver (clarity, robustness, error handling) while keeping the API and " \
           "the coding standard. Return only the C source.\n\n--- CODE ---\n" + code
    if exemplar:
        user += "\n\n--- STYLE EXEMPLAR ---\n" + exemplar
    return _strip_fences(client.chat([
        {"role": "system", "content": system_prompt(ruleset)},
        {"role": "user", "content": user},
    ], temperature=0.2))


def extract_descriptor(spec: dict, ruleset: dict, part: str, datasheet_chunks: list[str]) -> dict:
    """Build a descriptor from datasheet RAG chunks (Brief §14.2 + §17). RAG is deferred."""
    raise NotImplementedError(
        "Descriptor extraction depends on the RAG corpus (Brief §17), deferred this phase. "
        "Use a hand-authored descriptor or the .c/.h import flow (Brief §12) instead."
    )
