"""RAG ingestion (Brief §17) — DEFERRED to a later phase.

Planned pipeline: Docling (PDF -> markdown, tables preserved) -> structural chunking (keep
register tables whole) -> sentence-transformers (BGE-M3) embeddings -> two FAISS indices
(datasheet corpus + example-code corpus).

The deterministic path does NOT depend on this. Until the RAG corpus is built, fall back to
hand-authored descriptors and the .c/.h import flow (Brief §12). Implemented last because the
embeddings (torch/faiss) need internet on macOS and may lack Python 3.14 wheels.
"""

from __future__ import annotations

from pathlib import Path


def ingest_datasheets(pdf_dir: Path, index_dir: Path) -> None:
    raise NotImplementedError(
        "RAG ingestion is deferred (Brief §17). Install rag deps (requirements-rag.txt) under "
        "Python 3.11–3.12 and implement Docling -> chunk -> BGE-M3 -> FAISS here."
    )


def ingest_example_code(code_dir: Path, index_dir: Path) -> None:
    raise NotImplementedError("Example-code corpus ingestion is deferred (Brief §17).")
