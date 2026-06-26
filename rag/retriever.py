"""RAG retrieval (Brief §17) — DEFERRED to a later phase.

Queries:
  - descriptor extraction:  part + "register map" + operation names  (datasheet index)
  - test generation:        device type + transport + operations      (example-code index)

The deterministic path runs without this. See rag/ingest.py for the planned pipeline.
"""

from __future__ import annotations


def retrieve_datasheet(query: str, k: int = 6) -> list[str]:
    raise NotImplementedError("RAG retrieval is deferred (Brief §17). Use hand-authored descriptors.")


def retrieve_examples(query: str, k: int = 4) -> list[str]:
    raise NotImplementedError("RAG retrieval is deferred (Brief §17).")
