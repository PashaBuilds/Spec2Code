"""LLM tasks (Brief §14): test generation, optimize pass, descriptor extraction, QC fixer.

All of these run ONLY when the LLM is enabled and an endpoint is configured. Every LLM output
is re-checked by the QC loop (Brief §15), so a bad generation can't bypass the quality gate.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Optional

from hostplat import io as hio
from orchestrator.llm.client import LlmClient, LlmConfig, LlmError

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z]*\s*\n(.*?)\n```\s*$", re.DOTALL)


def _strip_fences(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text


def system_prompt(ruleset: dict) -> str:
    """Deterministic context: the coding standard the model must obey (Brief §16)."""
    fmt = ruleset.get("formatting", {})
    naming = ruleset.get("naming", {})
    return (
        "You are an embedded C driver engineer generating Xilinx Vitis (bare-metal/FreeRTOS) "
        "drop-in code. Obey this coding standard exactly:\n"
        f"- Brace style: {fmt.get('brace_style', 'allman')}; indent {fmt.get('indent', 'spaces_4')}; "
        f"max line {fmt.get('max_line_length', 100)}; line endings CRLF.\n"
        f"- Function names MUST match: {naming.get('function_regex')} (module_object_action).\n"
        f"- Hungarian prefixes: {naming.get('hungarian_prefixes')}.\n"
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
        except LlmError as exc:
            disabled_reason = str(exc)
            emit({
                "event": "llm.error",
                "task": "qc_fix",
                "model": client.config.model,
                "message": disabled_reason,
            })
            return
        if fixed.strip():
            hio.write_output(path, fixed)
            emit({
                "event": "llm.done",
                "task": "qc_fix",
                "model": client.config.model,
                "chars": len(fixed),
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
