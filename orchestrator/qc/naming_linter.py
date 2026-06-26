"""Naming / convention linter via libclang AST (Brief §15, §16).

Enforces the *meaning* that clang-format can't: function naming pattern, Hungarian variable
prefixes, and print line terminators. All rules are READ FROM THE RULESET — never hardcoded —
so changing the standard does not require editing this linter (Brief §16).

Severity policy:
  * function-name pattern mismatch  -> error   (gate-failing)
  * print line-terminator mismatch  -> error   (gate-failing)
  * Hungarian prefix mismatch       -> warning  (advisory, best-effort)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from hostplat import tools
from orchestrator.qc.runners import BSP_STUBS, Violation

_LIB_READY = False


def _ensure_libclang() -> bool:
    global _LIB_READY
    if _LIB_READY:
        return True
    lib = tools.resolve_libclang(required=False)
    if lib is None:
        return False
    from clang import cindex
    try:
        cindex.Config.set_library_file(str(lib))
    except Exception:
        pass  # already configured in this process
    _LIB_READY = True
    return True


# Hungarian prefix expected for a (pointer?, base-type) pair, derived from the ruleset map.
def _expected_prefix(written_type: str, prefixes: dict) -> Optional[str]:
    """Expected Hungarian prefix for a *written* (source-token) type, or None to skip.

    Uses the type as the programmer wrote it (immune to libclang header-resolution gaps).
    """
    t = written_type.replace("const", "").replace("volatile", "").strip()
    is_ptr = "*" in t
    base = t.replace("*", "").strip()
    if base == "void":
        return None  # void* names (e.g. FreeRTOS pv_parameters) aren't covered by the map
    scalar = {k: v for k, v in prefixes.items()
              if k in ("uint8_t", "uint16_t", "uint32_t", "uint64_t", "int32_t")}
    if is_ptr:
        if base in scalar:
            return prefixes.get("pointer", "p") + scalar[base]  # e.g. uint8_t* -> puc
        return prefixes.get("struct_pointer", "sp")             # struct*    -> sp
    return scalar.get(base)


def lint_file(path: Path, ruleset: dict, include_dirs: Optional[list[Path]] = None) -> list[Violation]:
    violations: list[Violation] = []
    naming = ruleset.get("naming", {})
    func_regex = naming.get("function_regex")
    prefixes = naming.get("hungarian_prefixes", {})
    term = ruleset.get("print_conventions", {}).get("line_terminator_in_prints", "\\r\\n")

    # --- print line-terminator check (source scan, no AST needed) ---
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(src.splitlines(), start=1):
        if "printf" not in line:
            continue
        # bare \n (backslash-n) not part of \r\n inside this line
        if re.search(r"(?<!\\r)\\n", line):
            violations.append(Violation(
                file=str(path), line=i, column=1, rule="print.line_terminator",
                severity="error",
                message=f"print uses bare \\n; standard requires '{term}'", source="naming-linter"))

    # --- AST checks (function names + Hungarian prefixes) ---
    if not _ensure_libclang():
        violations.append(Violation(
            file=str(path), line=0, column=0, rule="naming.libclang_missing",
            severity="warning", message="libclang not found; AST naming checks skipped",
            source="naming-linter"))
        return violations

    from clang import cindex
    args = ["-std=c11", "-I", str(BSP_STUBS)]
    for d in include_dirs or []:
        args += ["-I", str(d)]
    index = cindex.Index.create()
    tu = index.parse(str(path), args=args, options=0)  # default: parse bodies (needed for var decls)
    target = str(Path(path).resolve())
    func_re = re.compile(func_regex) if func_regex else None

    for cursor in tu.cursor.walk_preorder():
        loc = cursor.location
        if loc.file is None or str(Path(loc.file.name).resolve()) != target:
            continue
        if cursor.kind == cindex.CursorKind.FUNCTION_DECL and cursor.is_definition():
            name = cursor.spelling
            if func_re and not func_re.match(name):
                violations.append(Violation(
                    file=str(path), line=loc.line, column=loc.column, rule="naming.function_pattern",
                    severity="error",
                    message=f"function '{name}' does not match {func_regex}", source="naming-linter"))
        elif cursor.kind in (cindex.CursorKind.PARM_DECL, cindex.CursorKind.VAR_DECL):
            name = cursor.spelling
            if not name:
                continue
            # Read the WRITTEN type from source tokens (robust to header-resolution gaps).
            toks = [t.spelling for t in cursor.get_tokens()]
            written_type = " ".join(toks[:toks.index(name)]) if name in toks else cursor.type.spelling
            expected = _expected_prefix(written_type, prefixes)
            if expected and not name.startswith(expected):
                violations.append(Violation(
                    file=str(path), line=loc.line, column=loc.column, rule="naming.hungarian_prefix",
                    severity="warning",
                    message=f"'{name}' ({cursor.type.spelling}) should start with '{expected}'",
                    source="naming-linter"))
    return violations
