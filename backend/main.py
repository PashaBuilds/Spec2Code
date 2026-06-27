"""Spec2Code backend entrypoint (Brief 18).

Thin orchestration shell. Serves the REST API + WebSocket and, when the frontend has been
built, the static SPA. Run: ``uvicorn backend.main:app --reload`` from the repo root.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router
from backend.ws.jobs import ws_router

app = FastAPI(title="Spec2Code", version="1.0")

# Dev convenience: the Vite dev server runs on a different port.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(ws_router)

# Serve the built SPA when present (production / packaged mode).
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")


@app.get("/api")
def api_root() -> dict:
    return {"name": "Spec2Code", "version": "1.0", "docs": "/docs"}
