"""QC tool runners (Brief §15, §16): clang-format, clang-tidy, cppcheck.

Each runner resolves its tool through hostplat.tools (cross-platform) and shells out through
hostplat.proc. When a tool is missing, the runner returns a structured "skipped" marker
instead of raising — the QC loop degrades gracefully (Brief decision #3). clang-format output
is captured and re-written through hostplat.io so the CRLF guarantee stays centralized.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from hostplat import io as hio
from hostplat import proc
from hostplat import tools

# Directory of minimal BSP stub headers so clang-tidy/cppcheck can parse generated code.
BSP_STUBS = Path(__file__).resolve().parent / "bsp_stubs"


@dataclass
class Violation:
    file: str
    line: int
    column: int
    rule: str
    severity: str       # error | warning | style | info
    message: str
    source: str         # clang-format | clang-tidy | cppcheck | naming-linter

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunnerResult:
    tool: str
    available: bool
    violations: list[Violation]
    skipped_reason: Optional[str] = None


# --- clang-format -----------------------------------------------------------------------

def clang_format_config(ruleset: dict) -> str:
    fmt = ruleset.get("formatting", {})
    brace = {"allman": "Allman", "attach": "Attach", "k&r": "Linux"}.get(
        fmt.get("brace_style", "allman"), "Allman")
    indent = 4 if fmt.get("indent", "spaces_4") == "spaces_4" else 4
    column = fmt.get("max_line_length", 100)
    use_crlf = "true" if fmt.get("line_ending") == "crlf" else "false"
    return (
        "---\n"
        "Language: Cpp\n"
        "BasedOnStyle: LLVM\n"
        f"BreakBeforeBraces: {brace}\n"
        f"IndentWidth: {indent}\n"
        "UseTab: Never\n"
        f"ColumnLimit: {column}\n"
        f"UseCRLF: {use_crlf}\n"
        "DeriveLineEnding: false\n"
        "AllowShortFunctionsOnASingleLine: None\n"
        "AllowShortIfStatementsOnASingleLine: false\n"
        "AllowShortLoopsOnASingleLine: false\n"
        "AllowShortBlocksOnASingleLine: Never\n"
        "SortIncludes: false\n"
    )


def format_file(path: Path, config_dir: Path) -> tuple[bool, bool, Optional[str]]:
    """Format *path* in place (via stdout capture + hostplat.io write).

    Returns (available, changed, skipped_reason).
    """
    tool = tools.resolve("clang-format", required=False)
    if tool is None:
        return False, False, "clang-format not found"
    before = Path(path).read_bytes()
    result = proc.run([tool, "-style=file", str(path)], cwd=config_dir, timeout=60)
    if not result.ok:
        return True, False, result.stderr.strip() or "clang-format failed"
    hio.write_output(path, result.stdout)
    after = Path(path).read_bytes()
    return True, (before != after), None


# --- clang-tidy -------------------------------------------------------------------------

_TIDY_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<sev>warning|error):\s+(?P<msg>.*?)\s*(?:\[(?P<rule>[^\]]+)\])?$"
)


def run_clang_tidy(path: Path, include_dirs: list[Path]) -> RunnerResult:
    tool = tools.resolve("clang-tidy", required=False)
    if tool is None:
        return RunnerResult("clang-tidy", False, [], "clang-tidy not found")
    includes = []
    for d in [BSP_STUBS, *include_dirs]:
        includes += ["-I", str(d)]
    cmd = [tool, str(path), "--quiet",
           # bugprone-easily-swappable-parameters conflicts with hardware register/value APIs.
           "--checks=clang-analyzer-*,bugprone-*,-bugprone-easily-swappable-parameters,"
           "readability-braces-around-statements",
           "--", "-std=c11", *includes]
    result = proc.run(cmd, timeout=120)
    violations: list[Violation] = []
    target = str(Path(path).resolve())
    for line in result.stdout.splitlines():
        m = _TIDY_RE.match(line.strip())
        if not m:
            continue
        if str(Path(m.group("file")).resolve()) != target:
            continue  # only our file, not stub-header noise
        violations.append(Violation(
            file=str(path), line=int(m.group("line")), column=int(m.group("col")),
            rule=m.group("rule") or "clang-tidy", severity=m.group("sev"),
            message=m.group("msg"), source="clang-tidy"))
    return RunnerResult("clang-tidy", True, violations)


# --- cppcheck ---------------------------------------------------------------------------

_CPPCHECK_TEMPLATE = "{file}:{line}:{column}: {severity}: {message} [{id}]"
_CPPCHECK_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<sev>\w+):\s+(?P<msg>.*?)\s*\[(?P<rule>[^\]]+)\]$"
)
# Non-violations: stub/include limitations, not problems with the generated code.
_CPPCHECK_IGNORE = {"missingInclude", "missingIncludeSystem", "unmatchedSuppression",
                    "toomanyconfigs", "normalCheckLevelMaxBranches", "checkersReport",
                    # variableScope conflicts with the embedded "declare at block top" convention.
                    "variableScope"}


def run_cppcheck(path: Path, include_dirs: list[Path]) -> RunnerResult:
    tool = tools.resolve("cppcheck", required=False)
    if tool is None:
        return RunnerResult("cppcheck", False, [], "cppcheck not found")
    includes = [f"-I{BSP_STUBS}"] + [f"-I{d}" for d in include_dirs]
    cmd = [tool, "--enable=warning,style,performance,portability", "--quiet",
           "--inline-suppr", f"--template={_CPPCHECK_TEMPLATE}", "--language=c",
           "--std=c11", *includes, str(path)]
    result = proc.run(cmd, timeout=120)
    violations: list[Violation] = []
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        m = _CPPCHECK_RE.match(line.strip())
        if not m or m.group("rule") in _CPPCHECK_IGNORE:
            continue
        violations.append(Violation(
            file=str(path), line=int(m.group("line")), column=int(m.group("col")),
            rule=m.group("rule"), severity=m.group("sev"),
            message=m.group("msg"), source="cppcheck"))
    return RunnerResult("cppcheck", True, violations)
