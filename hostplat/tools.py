"""Cross-platform external-tool resolution (Brief §8).

Finds clang-format / clang-tidy / cppcheck executables and the libclang shared library
on both macOS and Windows (and Linux, for good measure). Search order per tool:

  1. env override  SPEC2CODE_<TOOL>_PATH   (e.g. SPEC2CODE_CLANG_FORMAT_PATH)
  2. PATH          (shutil.which)
  3. known install dirs per OS

This is the ONLY module that branches on ``sys.platform``. Callers that need graceful
degradation (the QC loop) pass ``required=False`` and get ``None`` instead of an error.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional


class ToolNotFoundError(RuntimeError):
    """Raised by resolve(..., required=True) when a tool cannot be located."""


_IS_WINDOWS = sys.platform.startswith("win")
_IS_MAC = sys.platform == "darwin"

# Known executable install directories, most-specific first.
_KNOWN_BIN_DIRS_MAC = [
    "/opt/homebrew/opt/llvm/bin",
    "/opt/homebrew/bin",
    "/usr/local/opt/llvm/bin",
    "/usr/local/bin",
    "/Library/Developer/CommandLineTools/usr/bin",
]
_KNOWN_BIN_DIRS_WINDOWS = [
    r"C:\Program Files\LLVM\bin",
    r"C:\Program Files (x86)\LLVM\bin",
    r"C:\Program Files\Cppcheck",
    r"C:\msys64\mingw64\bin",
    r"C:\ProgramData\chocolatey\bin",
]
_KNOWN_BIN_DIRS_LINUX = ["/usr/bin", "/usr/local/bin"]

# Known libclang shared-library locations + filenames.
_LIBCLANG_DIRS_MAC = [
    "/opt/homebrew/opt/llvm/lib",
    "/usr/local/opt/llvm/lib",
    "/Library/Developer/CommandLineTools/usr/lib",
]
_LIBCLANG_DIRS_WINDOWS = [r"C:\Program Files\LLVM\bin", r"C:\Program Files (x86)\LLVM\bin"]
_LIBCLANG_DIRS_LINUX = ["/usr/lib", "/usr/lib/llvm-18/lib", "/usr/lib/x86_64-linux-gnu"]
_LIBCLANG_NAMES_MAC = ["libclang.dylib"]
_LIBCLANG_NAMES_WINDOWS = ["libclang.dll"]
_LIBCLANG_NAMES_LINUX = ["libclang.so", "libclang.so.1", "libclang-18.so.1"]


def _env_key(tool_name: str) -> str:
    """clang-format -> SPEC2CODE_CLANG_FORMAT_PATH; libclang -> SPEC2CODE_LIBCLANG_PATH."""
    slug = tool_name.replace("-", "_").replace(".", "_").upper()
    return f"SPEC2CODE_{slug}_PATH"


def _known_bin_dirs() -> list[str]:
    if _IS_MAC:
        return _KNOWN_BIN_DIRS_MAC
    if _IS_WINDOWS:
        return _KNOWN_BIN_DIRS_WINDOWS
    return _KNOWN_BIN_DIRS_LINUX


def _exe_names(name: str) -> list[str]:
    return [name, name + ".exe"] if _IS_WINDOWS else [name]


def resolve(name: str, *, required: bool = True) -> Optional[Path]:
    """Locate an executable tool (clang-format, clang-tidy, cppcheck).

    Returns a Path, or None when not found and ``required`` is False.
    Raises :class:`ToolNotFoundError` when not found and ``required`` is True.
    """
    # 1) explicit env override
    override = os.environ.get(_env_key(name))
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate

    # 2) PATH
    found = shutil.which(name)
    if found:
        return Path(found)

    # 3) known install dirs
    for directory in _known_bin_dirs():
        for exe in _exe_names(name):
            candidate = Path(directory) / exe
            if candidate.is_file():
                return candidate

    if required:
        raise ToolNotFoundError(
            f"Could not find '{name}'. Install it, add it to PATH, or set "
            f"{_env_key(name)} to its full path. "
            f"(macOS: `brew install llvm cppcheck`; Windows: install LLVM + Cppcheck.)"
        )
    return None


def resolve_libclang(*, required: bool = True) -> Optional[Path]:
    """Locate the libclang shared library used by the naming-linter (Brief §15)."""
    override = os.environ.get(_env_key("libclang"))
    if override:
        candidate = Path(override)
        if candidate.is_file():
            return candidate

    if _IS_MAC:
        dirs, names = _LIBCLANG_DIRS_MAC, _LIBCLANG_NAMES_MAC
    elif _IS_WINDOWS:
        dirs, names = _LIBCLANG_DIRS_WINDOWS, _LIBCLANG_NAMES_WINDOWS
    else:
        dirs, names = _LIBCLANG_DIRS_LINUX, _LIBCLANG_NAMES_LINUX

    for directory in dirs:
        for libname in names:
            candidate = Path(directory) / libname
            if candidate.is_file():
                return candidate

    if required:
        raise ToolNotFoundError(
            "Could not find libclang. Set SPEC2CODE_LIBCLANG_PATH to the full path of "
            "libclang.dylib/.dll/.so, or install LLVM."
        )
    return None


def status() -> dict[str, Optional[str]]:
    """Resolve everything non-fatally; used by the README smoke-test and /api health."""
    out: dict[str, Optional[str]] = {}
    for tool in ("clang-format", "clang-tidy", "cppcheck"):
        path = resolve(tool, required=False)
        out[tool] = str(path) if path else None
    libclang = resolve_libclang(required=False)
    out["libclang"] = str(libclang) if libclang else None
    return out
