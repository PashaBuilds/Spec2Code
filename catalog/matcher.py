"""Content-aware driver-source matcher (Brief §12, step 1).

Scans a folder of .c/.h driver sources and, for each .c/.h pair (grouped by file stem),
proposes which catalog part it implements — by CONTENT, not just filename. Signals:
  * part-number / token hits from the catalog's ``match_tokens`` (in comments, #defines, code)
  * function-prefix pattern (e.g. ``ltc2991_*``)
Each proposal carries a 0..1 confidence so the UI can show "X → PART (94%)" for the user to
confirm or correct (step 2). Pure read-only; no persistence here.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from hostplat import io as hio

_ROOT = Path(__file__).resolve().parent.parent
_CATALOG = _ROOT / "catalog" / "catalog.json"


@dataclass
class FileMatch:
    stem: str
    files: list[str]
    part: Optional[str]
    confidence: float
    signals: list[str] = field(default_factory=list)


def _load_catalog() -> dict:
    return json.loads(_CATALOG.read_text())


def _score_text(text: str, part: str, tokens: list[str]) -> tuple[float, list[str]]:
    upper = text.upper()
    lower = text.lower()
    signals: list[str] = []
    score = 0.0
    # strong: exact part number present
    if part.upper() in upper:
        score += 0.6
        signals.append(f"part '{part}' present")
    # function prefix like ltc2991_
    prefix = part.lower() + "_"
    if re.search(rf"\b{re.escape(prefix)}[a-z0-9_]+\s*\(", lower):
        score += 0.3
        signals.append(f"function prefix '{prefix}'")
    # characteristic tokens (registers/commands)
    hits = [t for t in tokens if t.upper() in upper and t.upper() != part.upper()]
    if hits:
        score += min(0.3, 0.1 * len(hits))
        signals.append("tokens: " + ", ".join(hits[:4]))
    return min(score, 1.0), signals


def scan_folder(folder: str | Path) -> list[FileMatch]:
    folder = Path(folder)
    if not folder.is_dir():
        raise NotADirectoryError(f"not a folder: {folder}")
    catalog = _load_catalog()["devices"]

    # group .c/.h by stem
    groups: dict[str, list[Path]] = {}
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() in (".c", ".h"):
            groups.setdefault(path.stem.lower(), []).append(path)

    results: list[FileMatch] = []
    for stem, files in groups.items():
        text = "\n".join(hio.read_text(f) for f in files)
        best_part, best_conf, best_signals = None, 0.0, []
        for dev in catalog:
            conf, signals = _score_text(text, dev["part"], dev.get("match_tokens", []))
            if conf > best_conf:
                best_part, best_conf, best_signals = dev["part"], conf, signals
        results.append(FileMatch(
            stem=stem, files=[str(f) for f in files],
            part=best_part if best_conf >= 0.5 else None,
            confidence=round(best_conf, 2), signals=best_signals))
    results.sort(key=lambda r: r.confidence, reverse=True)
    return results
