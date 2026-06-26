"""Folder-watching wrapper around watchdog (Brief §8).

Hides the backend/OS difference. watchdog is imported lazily so that importing
``hostplat`` does not hard-require it (the deterministic path doesn't need watching).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Union

PathLike = Union[str, Path]


class Watcher:
    """Thin start/stop handle over a watchdog Observer."""

    def __init__(self, observer):
        self._observer = observer

    def start(self) -> "Watcher":
        self._observer.start()
        return self

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join(timeout=5)


def make(path: PathLike, callback: Callable[[str, str], None], *, recursive: bool = True) -> Watcher:
    """Create a Watcher that calls ``callback(event_type, src_path)`` on FS changes.

    Caller is responsible for ``.start()`` and ``.stop()``.
    """
    from watchdog.events import FileSystemEventHandler  # lazy import
    from watchdog.observers import Observer

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            if not event.is_directory:
                callback(event.event_type, event.src_path)

    observer = Observer()
    observer.schedule(_Handler(), str(Path(path)), recursive=recursive)
    return Watcher(observer)
