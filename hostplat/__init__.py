"""hostplat — the ONLY platform-dependent module in Spec2Code.

The Build Brief calls this the ``platform/`` isolation module (§8). It is named
``hostplat`` here to avoid shadowing Python's stdlib ``platform`` module, which would
be a guaranteed import collision (uvicorn / httpx / asyncio all ``import platform``).
See docs/EXECUTION-PLAN.md decision #1.

Everything that touches the host OS lives here and nowhere else:
  - io      : write_output() -> always CRLF, binary mode
  - tools   : resolve clang-format / clang-tidy / cppcheck / libclang cross-platform
  - proc    : subprocess wrapper (shell=False, list args, timeout, capture)
  - watch   : watchdog folder-watch wrapper

No other module imports ``os``/``sys.platform``/``subprocess`` or deals with line
endings or tool paths directly.
"""

from . import io, proc, tools  # noqa: F401  (watch is imported lazily to avoid hard watchdog dep)

__all__ = ["io", "proc", "tools", "watch"]
