"""Subprocess wrapper (Brief §8): shell=False, list args, timeout, captured output.

Cross-platform. No other module calls subprocess directly.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, Union

PathLike = Union[str, Path]


@dataclass
class ProcResult:
    returncode: int
    stdout: str
    stderr: str
    cmd: list[str]
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


class ProcError(RuntimeError):
    def __init__(self, result: "ProcResult"):
        self.result = result
        super().__init__(
            f"command failed ({result.returncode}): {' '.join(result.cmd)}\n{result.stderr}"
        )


def run(
    cmd: Sequence[PathLike],
    *,
    cwd: Optional[PathLike] = None,
    timeout: float = 60.0,
    input_text: Optional[str] = None,
    check: bool = False,
) -> ProcResult:
    """Run *cmd* (a list, never a shell string). Captures stdout/stderr as text.

    On timeout returns a ProcResult with ``timed_out=True`` and returncode 124.
    Raises :class:`ProcError` when ``check`` and the command fails.
    """
    argv = [str(part) for part in cmd]
    workdir = str(cwd) if cwd is not None else None
    try:
        completed = subprocess.run(
            argv,
            cwd=workdir,
            input=input_text,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,  # never invoke a shell — portable + safe
        )
    except subprocess.TimeoutExpired as exc:
        result = ProcResult(
            returncode=124,
            stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
            stderr=f"timeout after {timeout}s",
            cmd=argv,
            timed_out=True,
        )
        if check:
            raise ProcError(result) from exc
        return result
    except FileNotFoundError as exc:
        result = ProcResult(returncode=127, stdout="", stderr=str(exc), cmd=argv)
        if check:
            raise ProcError(result) from exc
        return result

    result = ProcResult(
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        cmd=argv,
    )
    if check and not result.ok:
        raise ProcError(result)
    return result
