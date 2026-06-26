"""Output I/O — every generated file goes through here, always CRLF (Brief §1.2, §8).

Rationale: the final target is a Windows coding standard that mandates ``\\r\\n`` line
endings. Getting this right from day one (not at port time) means ALL generated ``.c/.h/.md``
content is written exclusively through :func:`write_output`, in binary mode, with line
endings normalized to CRLF regardless of host OS.
"""

from __future__ import annotations

from pathlib import Path
from typing import Union

CRLF = "\r\n"
PathLike = Union[str, Path]


def normalize_crlf(text: str) -> str:
    """Collapse any mix of CRLF/CR/LF to a single LF, then expand every LF to CRLF.

    Idempotent: running it twice yields the same result.
    """
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    return unified.replace("\n", CRLF)


def write_output(path: PathLike, text: str, *, ensure_trailing_newline: bool = True) -> Path:
    """Write *text* to *path* with CRLF line endings, in binary mode.

    Creates parent directories as needed. This is the ONLY sanctioned way to emit
    generated source/output in Spec2Code. Returns the resolved Path.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    normalized = normalize_crlf(text)
    if ensure_trailing_newline and normalized and not normalized.endswith(CRLF):
        normalized += CRLF
    # Binary mode so the host OS never re-translates the line endings we just set.
    with open(target, "wb") as handle:
        handle.write(normalized.encode("utf-8"))
    return target


def read_text(path: PathLike) -> str:
    """Read a (possibly CRLF) text file and return it with LF endings for parsing.

    Use this for *inputs* (xparameters.h, descriptors, exemplars). Decoded as UTF-8
    with a permissive fallback so odd vendor headers don't blow up the parser.
    """
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def detect_line_ending(path: PathLike) -> str:
    """Return 'crlf', 'lf', 'cr', or 'none' for *path* — used by the CRLF smoke-test."""
    raw = Path(path).read_bytes()
    if b"\r\n" in raw:
        return "crlf"
    if b"\n" in raw:
        return "lf"
    if b"\r" in raw:
        return "cr"
    return "none"
