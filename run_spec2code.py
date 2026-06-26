"""Run Spec2Code as a single local web application.

This entrypoint is intentionally tiny so it works both from source and from a
PyInstaller executable built by the release workflow.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import webbrowser

import uvicorn

from backend.main import app


def _open_browser_later(url: str) -> None:
    def worker() -> None:
        time.sleep(1.0)
        webbrowser.open(url)

    threading.Thread(target=worker, daemon=True).start()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Spec2Code locally")
    parser.add_argument("--host", default=os.environ.get("SPEC2CODE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SPEC2CODE_PORT", "8077")))
    parser.add_argument("--no-browser", action="store_true", help="do not open the web UI automatically")
    args = parser.parse_args(argv)

    url = f"http://{args.host}:{args.port}"
    print(f"Spec2Code is starting on {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        _open_browser_later(url)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
