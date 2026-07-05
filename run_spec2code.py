"""Run Spec2Code as a single local web application.

This entrypoint is intentionally tiny so it works both from source and from a
PyInstaller executable built by the release workflow.
"""

from __future__ import annotations

import argparse
import os
import socket
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


def pick_listen_port(host: str, preferred: int, *, attempts: int = 30) -> int:
    """Return `preferred` when it is free, otherwise the next free port.

    A stale Spec2Code (or anything else) already listening on 8077 used to
    kill the new instance with a raw `[WinError 10048]` bind error; scanning
    forward keeps the app usable and the chosen port is printed clearly.
    """
    for offset in range(max(1, attempts)):
        candidate = preferred + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.bind((host, candidate))
        except OSError:
            continue
        return candidate
    return preferred


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Spec2Code locally")
    parser.add_argument("--host", default=os.environ.get("SPEC2CODE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("SPEC2CODE_PORT", "8077")))
    parser.add_argument("--no-browser", action="store_true", help="do not open the web UI automatically")
    args = parser.parse_args(argv)

    port = pick_listen_port(args.host, args.port)
    if port != args.port:
        print(
            f"Port {args.port} zaten kullanımda (muhtemelen eski bir Spec2Code hâlâ açık); "
            f"{port} portuna geçildi."
        )
        print(
            f"Eski instance'ı kapatmak için: netstat -ano | findstr :{args.port} "
            "ile PID'i bulup taskkill /PID <pid> /F çalıştırabilirsin."
        )

    url = f"http://{args.host}:{port}"
    # Backend'in cozdugu surum ajan koduna damgalanir (SPEC2CODE_TESTBENCH_
    # AGENT_VERSION): "dev" gorunuyorsa paketteki surum metadatasi
    # okunamiyor demektir - sahada aninda teshis icin aciliste basilir.
    from orchestrator.codegen import _app_version

    print(f"Spec2Code backend version: {_app_version()}")
    print(f"Spec2Code is starting on {url}")
    print("Press Ctrl+C to stop.")
    if not args.no_browser:
        _open_browser_later(url)

    uvicorn.run(app, host=args.host, port=port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
