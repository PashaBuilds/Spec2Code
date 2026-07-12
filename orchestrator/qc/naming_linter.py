"""Naming / convention linter via libclang AST (Brief 15, 16).

Enforces the *meaning* that clang-format can't: function naming pattern, Hungarian variable
prefixes, and print line terminators. Spec2Code uses the fixed default ruleset, and this linter
reads the rule values from that ruleset while keeping the supported C type surface explicit.

Severity policy:
  * function-name pattern mismatch  -> error   (gate-failing)
  * print line-terminator mismatch  -> error   (gate-failing)
  * Hungarian / camelCase mismatch  -> error   (gate-failing)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from hostplat import tools
from orchestrator.qc.runners import BSP_STUBS, Violation

_LIB_READY = False
_SCALAR_KEYS = (
    "unsigned char",
    "char",
    "unsigned short",
    "short",
    "unsigned int",
    "int",
    "unsigned long",
    "unsigned long long",
)

_POINTER_STAR_RE = re.compile(
    r"\b(?:const\s+|volatile\s+|static\s+)*"
    r"(?:(?:unsigned\s+)?(?:char|short|int|long(?:\s+long)?)|"
    r"[A-Z][A-Za-z0-9_]*|struct\s+[A-Za-z_][A-Za-z0-9_]*)"
    r"\s+\*\s*[A-Za-z_]"
)


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


def _base_type(written_type: str) -> str:
    t = re.sub(r"\b(static|const|volatile)\b", "", written_type).strip()
    return re.sub(r"\s+", " ", t.replace("*", " ").strip())


def _is_structish_type(base: str) -> bool:
    return base.startswith("S") or base.startswith("X") or base.startswith("struct ")


def _source_line_checks(path: Path, src: str, ruleset: dict) -> list[Violation]:
    violations: list[Violation] = []
    disallowed = ruleset.get("naming", {}).get("disallowed_types", [])
    disallowed_re = re.compile(r"\b(" + "|".join(re.escape(t) for t in disallowed) + r")\b") if disallowed else None

    for i, line in enumerate(src.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#")):
            continue

        if disallowed_re:
            m = disallowed_re.search(line)
            if m:
                violations.append(Violation(
                    file=str(path), line=i, column=m.start(1) + 1, rule="naming.disallowed_type",
                    severity="error",
                    message=f"type '{m.group(1)}' is not allowed; use primitive C types instead",
                    source="naming-linter"))

        m = _POINTER_STAR_RE.search(line)
        if m:
            violations.append(Violation(
                file=str(path), line=i, column=line.find("*") + 1, rule="naming.pointer_star",
                severity="error",
                message="pointer '*' must attach to the type, for example 'XIicPs* spIic'",
                source="naming-linter"))

    return violations


# Hungarian prefix expected for a (pointer?, array?, base-type) pair, derived from the ruleset.
def _expected_prefix(written_type: str, prefixes: dict, *, is_array: bool = False) -> Optional[str]:
    """Expected Hungarian prefix for a *written* (source-token) type, or None to skip.

    Uses the type as the programmer wrote it (immune to libclang header-resolution gaps).
    """
    t = re.sub(r"\b(static|const|volatile)\b", "", written_type).strip()
    is_ptr = "*" in t
    base = _base_type(written_type)
    if base == "void":
        return None  # void* names (e.g. FreeRTOS pv_parameters) aren't covered by the map
    scalar = {k: v for k, v in prefixes.items() if k in _SCALAR_KEYS}
    if is_array:
        suffix = prefixes.get("array_suffix", "Arr")
        if is_ptr:
            # pointer-element arrays keep the pointer marker: const char* const [] -> cpArr
            if base in scalar:
                ptr = prefixes.get("pointer_suffix", prefixes.get("pointer", "p"))
                return scalar[base] + ptr + suffix
            if _is_structish_type(base):
                return prefixes.get("struct_pointer", "sp") + suffix
            return None
        if base in scalar:
            return scalar[base] + suffix
        if _is_structish_type(base):
            return prefixes.get("struct", "s") + suffix
        return None
    if is_ptr:
        if base in scalar:
            suffix = prefixes.get("pointer_suffix", prefixes.get("pointer", "p"))
            return scalar[base] + suffix
        return prefixes.get("struct_pointer", "sp")             # struct*    -> sp
    if _is_structish_type(base):
        return prefixes.get("struct", "s")
    return scalar.get(base)


def _name_parts_for_storage(name: str, storage_prefix: str) -> tuple[str, str]:
    if storage_prefix and name.startswith(storage_prefix):
        return storage_prefix, name[len(storage_prefix):]
    return "", name


def _is_camel_case_name(name: str) -> bool:
    return "_" not in name and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", name))


def lint_file(path: Path, ruleset: dict, include_dirs: Optional[list[Path]] = None) -> list[Violation]:
    violations: list[Violation] = []
    naming = ruleset.get("naming", {})
    func_regex = naming.get("function_regex")
    prefixes = naming.get("hungarian_prefixes", {})
    identifier_case = naming.get("identifier_case")
    term = ruleset.get("print_conventions", {}).get("line_terminator_in_prints", "\\r\\n")

    # --- print line-terminator check (source scan, no AST needed) ---
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    violations.extend(_source_line_checks(path, src, ruleset))
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
            name_idx = toks.index(name) if name in toks else -1
            # declarator brackets only: stop at '=' so initializer indexing
            # (e.g. sizeof(x)/sizeof(x[0])) is not mistaken for an array decl
            decl_toks = toks[name_idx + 1:] if name_idx >= 0 else []
            if "=" in decl_toks:
                decl_toks = decl_toks[:decl_toks.index("=")]
            is_array = "[" in decl_toks
            storage_prefix = ""
            try:
                if cursor.storage_class == cindex.StorageClass.STATIC:
                    storage_prefix = prefixes.get("static_prefix", "S_")
            except Exception:
                storage_prefix = ""
            if storage_prefix == "" and cursor.semantic_parent.kind == cindex.CursorKind.TRANSLATION_UNIT:
                storage_prefix = prefixes.get("global_prefix", "G_")
            actual_storage, local_name = _name_parts_for_storage(name, storage_prefix)
            expected = _expected_prefix(written_type, prefixes, is_array=is_array)
            if expected and storage_prefix and actual_storage != storage_prefix:
                violations.append(Violation(
                    file=str(path), line=loc.line, column=loc.column, rule="naming.storage_prefix",
                    severity="error",
                    message=f"'{name}' ({cursor.type.spelling}) should start with storage prefix '{storage_prefix}'",
                    source="naming-linter"))
            elif expected and not local_name.startswith(expected):
                expected_name = f"{storage_prefix}{expected}" if storage_prefix else expected
                violations.append(Violation(
                    file=str(path), line=loc.line, column=loc.column, rule="naming.hungarian_prefix",
                    severity="error",
                    message=f"'{name}' ({cursor.type.spelling}) should start with '{expected_name}'",
                    source="naming-linter"))
            elif identifier_case == "camelCase" and local_name and not _is_camel_case_name(local_name):
                violations.append(Violation(
                    file=str(path), line=loc.line, column=loc.column, rule="naming.identifier_case",
                    severity="error",
                    message=f"'{name}' should use camelCase after its Hungarian/storage prefix",
                    source="naming-linter"))
    return violations
