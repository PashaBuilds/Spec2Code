# Spec2Code

Spec2Code is a local-first hardware-to-driver generator for Xilinx embedded projects. It
turns a platform `xparameters.h` plus user-defined external devices into drop-in Vitis
application-layer C drivers, tests, and a QC report.

Turn a Xilinx embedded project's hardware spec (`xparameters.h` + attached external devices)
into **drop-in** C driver + test code (`.c`/`.h`) for the Vitis application layer.

Load an `xparameters.h` and Spec2Code draws a clean, Vivado-like **interactive schematic** for
the selected platform. Controllers come from `xparameters` automatically (read-only); you add
external devices on the schematic (protocol-aware: I²C address + switch/mux + channel, SPI
chip-select + address width, …). Then it generates deterministic, coding-standard-compliant,
**CRLF** drivers — with an optional LLM pass on top.

> Build host: macOS. Final target: air-gapped Windows 10. All code is portable; every
> platform-specific touch lives in `hostplat/`, and all generated output is CRLF from day one.

## What it gives you

- **Vivado-like schematic UI:** upload `xparameters.h`, inspect PS/PL zones and controllers,
  then add external devices visually.
- **Descriptor-driven codegen:** device YAML descriptors drive transport, operations, address
  width, mux channel selection, and generated tests.
- **Deterministic QC loop:** generated C is formatted and checked with clang-format,
  naming-linter/libclang, clang-tidy, and cppcheck.
- **Optional LLM pass:** an OpenAI-compatible endpoint can optimize or repair output, but every
  LLM result is re-gated by the deterministic QC loop.
- **Windows-ready output:** generated `.c`, `.h`, and `.md` files are written through
  `hostplat.io.write_output()` with CRLF line endings.

## Current PoC status

The current PoC covers the end-to-end path:

```text
xparameters.h -> schematic -> external devices -> project.spec.json -> codegen -> QC -> files
```

Verified examples include:

- TCA9548A mux + LTC2991 over I2C, including channel-select injection.
- MT25Q128 3-byte SPI flash vs MT25QU02G 4-byte SPI flash descriptor divergence.
- FastAPI + WebSocket generation stream.
- React/Vite frontend with React Flow schematic and CodeMirror output viewer.

## Architecture

```
Frontend (React + Vite + Tailwind + React Flow)  ──REST + WS──►  Backend (FastAPI)
  schematic · catalog · device params · console · code view          parse · validate · jobs
                                                                          │
                                              Orchestrator: Jinja2 codegen + QC loop
                                              (clang-format · naming-linter · clang-tidy · cppcheck)
                                                       ↕ optional OpenAI-compatible LLM (Kimi K2.6)
```

- **Deterministic first.** Driver code is generated from descriptors + templates. The LLM is a
  default-OFF toggle that produces an optimized variant on top; the system is fully usable without it.
- **`hostplat/`** is the only platform-dependent module (CRLF I/O, tool resolution, subprocess, watch).

## GitHub Releases

Releases are created from `v*` tags. The workflow builds and uploads:

| Asset | Contents | Build host |
| --- | --- | --- |
| `spec2code-vX.Y.Z-source.zip` | Full tracked source archive for development | Linux runner |
| `spec2code-vX.Y.Z-source.tar.gz` | Same full tracked source archive | Linux runner |
| `spec2code-vX.Y.Z-macos-*.zip` | macOS `Spec2Code` executable + docs | macOS runner |
| `spec2code-vX.Y.Z-windows-*.zip` | Windows `Spec2Code.exe` executable + docs | Windows runner |

To publish a release after pushing the repository to GitHub:

```bash
git tag -a v0.1.0 -m "Spec2Code v0.1.0"
git push origin main --tags
```

GitHub Actions will attach the source archives and platform executables to the Release.

You can also create the source archives locally:

```bash
python3 scripts/package_release.py --version v0.1.0
```

Platform executables must be built on their own OS. See
[`docs/WINDOWS.md`](docs/WINDOWS.md) for the Windows path and
`scripts/build_executable.py` for the executable packaging entrypoint.

The executable bundles are runtime packages. Use the source archive when you want to continue
development on Windows. The source archive includes Windows helper scripts under
`scripts/windows/` for online setup, air-gapped setup from an offline dependency cache, single-server
runtime, and frontend HMR development.

## Prerequisites

- **Python 3.11+** (tested on 3.14), **Node 18+** (tested on 22).
- **LLVM tools + cppcheck** for the QC loop (the deterministic codegen runs without them; QC
  degrades gracefully and the naming-linter uses libclang).

## macOS dev setup

```bash
# 1) QC toolchain
brew install llvm cppcheck            # clang-format, clang-tidy, libclang, cppcheck

# 2) backend / orchestrator
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 3) frontend
cd frontend && npm install && cd ..

# 4) run backend (serves the built SPA if present)
.venv/bin/python -m uvicorn backend.main:app --port 8077

# 5) run frontend dev server (proxies /api + /ws to :8077)
cd frontend && npm run dev            # http://localhost:5181
```

Quick deterministic self-test (no UI, no LLM):

```bash
.venv/bin/python - <<'PY'
import json; from pathlib import Path
from orchestrator import codegen
from orchestrator.qc import loop
spec = json.loads(Path("specs/samples/radar_io_board.spec.json").read_text())
ruleset = json.loads(Path("std/default.ruleset.json").read_text())
out = Path("outputs")/spec["project"]["name"]
codegen.generate(spec, out)
print(loop.run_qc(out, ruleset)["passed"])   # -> True
PY
```

Tool paths can be overridden with `SPEC2CODE_CLANG_FORMAT_PATH`, `SPEC2CODE_CLANG_TIDY_PATH`,
`SPEC2CODE_CPPCHECK_PATH`, `SPEC2CODE_LIBCLANG_PATH`.

## Optional LLM

Default OFF. Toggle it in the UI (or set `llm.enabled` in the spec) and configure an
OpenAI-compatible endpoint:

```bash
export SPEC2CODE_LLM_BASE_URL="http://localhost:1234/v1"   # any OpenAI-compatible server
export SPEC2CODE_LLM_MODEL="kimi-k2.6"                      # prod default
export SPEC2CODE_LLM_API_KEY="..."                          # optional
```

Every LLM output is re-checked by the QC loop before delivery.

## Production build (single server)

```bash
cd frontend && npm run build && cd ..        # emits frontend/dist
.venv/bin/python run_spec2code.py
# open http://127.0.0.1:8077  (backend serves the built SPA + API + WS)
```

Direct uvicorn remains supported:

```bash
.venv/bin/python -m uvicorn backend.main:app --port 8077
```

## Windows 10 / air-gapped target

For a released Windows build, download the Windows zip from GitHub Releases and run:

```powershell
.\Spec2Code.exe
```

Open:

```text
http://127.0.0.1:8077
```

For full QC on Windows, install LLVM and Cppcheck, then confirm:

- [ ] Python installs; `pip install -r requirements.txt` succeeds (watch `libclang`).
- [ ] `clang-format`, `clang-tidy`, `cppcheck` are found via `hostplat.tools.resolve()`
      (PATH, `C:\Program Files\LLVM\bin`, `C:\Program Files\Cppcheck`, or
      `SPEC2CODE_<TOOL>_PATH`).
- [ ] A subprocess call works:
      `python -c "from hostplat import tools; print(tools.status())"`
- [ ] A file written via `hostplat.io.write_output()` is **CRLF**:
      ```python
      from hostplat import io
      p = io.write_output("outputs/_crlf_probe.txt", "a\nb\n")
      print(io.detect_line_ending(p))   # -> crlf
      ```
- [ ] Frontend deps install from your npm mirror (React Flow included); `npm run build` succeeds.

Full Windows instructions are in [`docs/WINDOWS.md`](docs/WINDOWS.md), including `.exe` usage,
source-mode setup, offline dependency cache preparation, local LLM configuration, and manual
Windows executable builds.

RAG (`requirements-rag.txt`: torch/faiss/sentence-transformers/docling) is **deferred**; install
under Python 3.11–3.12 when you implement it (Brief §17).

## Repository layout

```
hostplat/        the ONLY platform-dependent module (CRLF io, tool resolve, proc, watch)
backend/         FastAPI: api/, ws/, parsers/xparameters.py, jobs.py, main.py
orchestrator/    codegen.py, cmodel.py, templates/*.j2, qc/ (loop, runners, naming_linter), llm/
descriptors/     device descriptors (LTC2991, MT25Q128, TCA9548A, MT25QU02G) + JSON schema
platforms/       platform topology models (zones/cores) for the 4 supported families
catalog/         catalog.json + content-aware .c/.h matcher
std/             default.ruleset.json + Word→ruleset extractor
schemas/         project.spec JSON schema (the canonical handoff artifact)
specs/samples/   sample xparameters.h (4 platforms) + radar_io_board.spec.json
frontend/        React + Vite + Tailwind + React Flow SPA
docs/            EXECUTION-PLAN.md (build phasing + flagged decisions)
```

See `docs/EXECUTION-PLAN.md` for the build phasing and every place a spec decision was made.
