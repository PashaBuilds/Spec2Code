"""Fixed coding-standard ruleset used by Spec2Code.

The product no longer imports or persists user-provided coding standards. Codegen,
LLM prompts, and QC always use ``std/default.ruleset.json`` so Windows/macOS runs
stay deterministic and reviewable.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULESET_REF = "std/default.ruleset.json"
DEFAULT_RULESET_PATH = ROOT / DEFAULT_RULESET_REF
RULESET_SCHEMA_PATH = ROOT / "schemas" / "ruleset.schema.json"

DEFAULT_RULESET = json.loads(DEFAULT_RULESET_PATH.read_text(encoding="utf-8"))
RULESET_SCHEMA = json.loads(RULESET_SCHEMA_PATH.read_text(encoding="utf-8"))


def resolve_ruleset_ref(ref: str = DEFAULT_RULESET_REF) -> Path:
    """Return the fixed default ruleset path.

    ``ref`` is accepted for compatibility with older project specs, but custom
    refs are intentionally ignored.
    """
    return DEFAULT_RULESET_PATH
