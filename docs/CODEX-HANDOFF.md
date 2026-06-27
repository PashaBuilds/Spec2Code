# Spec2Code — Handoff Prompt (paste into Codex / a fresh agent)

You are taking over **Spec2Code**, a working PoC. Read this whole file first, then run the
2-minute verification below before changing anything.

## 0. Mission & working directory

- **Working directory:** `/Users/mpcukur/Projects/Spec2Code` (git repo, no commits yet).
- **What it does:** loads a Xilinx `xparameters.h` + lets the user add external devices on a
  Vivado-like interactive schematic, then generates **drop-in** C driver + test code (`.c/.h`)
  for the Vitis application layer — deterministically, with an optional LLM pass on top.
- **Build host:** macOS (Mac Mini). **Final target:** air-gapped **Windows 10**. Therefore: all
  code is portable, every platform-specific touch is isolated in `hostplat/`, and **all generated
  output is CRLF**.
- **Authoritative spec:** the original Build Brief (Turkish), `~/Downloads/spec2code-claude-code-prompt.md`.
  Build-phasing + every flagged decision is in **`docs/EXECUTION-PLAN.md`**. Setup/run is in **`README.md`**.
- The user works in **Turkish**; the brief is the contract — stay faithful to it, and when it
  leaves a decision open, pick a sensible default, flag it in a comment + EXECUTION-PLAN, proceed.

## 1. Current state — DONE and verified

Full PoC is built end-to-end and was confirmed working on the Mac Mini. Verified:

- **Parser** (`backend/parsers/xparameters.py`): 4 platforms, PS/PL zoning, memory regions
  filtered (no DEVICE_ID), TTC/GIC ignored, driver detection (XIicPs vs XIic, XAxiDma, …).
- **Deterministic codegen** (`orchestrator/codegen.py` + `cmodel.py` + `templates/*.j2`): produces
  `ltc2991.c/.h` with **mux channel-select injected**, `mt25qu02g.c/.h` with **4-byte addressing
  (`ENTER_4BYTE 0xB7` + `4U` address bytes)** vs `mt25q128` (3-byte) — proving descriptor-driven
  divergence. Generated C **compiles clean under `clang -fsyntax-only -Wall -Wextra`** against the
  BSP stubs in `orchestrator/qc/bsp_stubs/`.
- **QC loop** (`orchestrator/qc/loop.py`): clang-format + naming-linter(libclang) + clang-tidy +
  cppcheck → **0 violations**; writes `qc_report.json`; graceful-degrades if a tool is missing.
- **LLM smoke (2026-06-26)**: local Ollama OpenAI-compatible endpoint
  (`http://127.0.0.1:11434/v1`, `gemma3:12b`) verified `make_qc_fixer` live. A temp C file with
  a gate-failing bare `\n` print was fixed to `\r\n`, then QC re-ran clean in round 2. Direct
  `optimize_code()` also returned non-empty C output. The LLM client now requires the exact model id
  from the user and reports timeout, HTTP, truncated, empty, and overlong responses as structured
  `llm.error` events without rewriting files. Model answers are staged as temporary candidates and
  must pass shape guards plus the available deterministic tools (clang-format, naming-linter,
  clang-tidy, cppcheck) before replacing the real file; rejected candidates emit `llm.rejected`.
- **Backend** (FastAPI + WS): `generate` → live event stream → result, verified on real uvicorn.
- **Frontend** (React + Vite + Tailwind + React Flow): full flow verified visually — setup →
  upload xparameters → schematic with zones → add TCA9548A mux + LTC2991 device → set via-mux
  channel 3 → generate → live console + CodeMirror code view with QC pass.
- **Coding Standard Studio**: Setup-integrated ruleset builder. Backend endpoints
  `/api/rulesets/default|extract|validate|save` normalize LLM candidates against
  `schemas/ruleset.schema.json`, show diff/checks/issues, and persist approved refs as
  `std/user/<name>.ruleset.json`.
- **Device profiles**: `devices[].config` is the board-specific layer above descriptor
  behavior. `orchestrator/device_profiles/` currently implements LTC2991 pair-mode config,
  backend preflight validation, and profile-generated init write arrays.
- **Portability static audit**: no platform-specific code, no `shell=True`, no manual path joins,
  no non-CRLF output outside `hostplat/`.

## 2. Orientation map

```
hostplat/        ONLY platform module: io.write_output()=CRLF, tools.resolve(), proc.run(), watch
backend/         main.py · jobs.py (JobManager + WS event buffering) · api/routes.py · ws/jobs.py
                 parsers/xparameters.py
orchestrator/    codegen.py · cmodel.py (C render-model: Emit class + i2c/spi/mux/test builders)
                 templates/*.j2 · device_profiles/ · qc/{loop,runners,naming_linter}.py + bsp_stubs/ · llm/{client,tasks}.py
                 selftest.py
descriptors/     ltc2991/tca9548a/mt25q128/mt25qu02g/ad7414/ds1682/ltc2945 .yaml + _schema/descriptor.schema.json
platforms/       4 topology models (zones/cores)
catalog/         catalog.json + matcher.py (content-aware .c/.h matching, verified 100%)
std/             default.ruleset.json + extract_ruleset.py (Word→ruleset)
schemas/         project.spec.schema.json (canonical handoff artifact)
specs/samples/   xparameters_*.h (4) + radar_io_board.spec.json
frontend/src/    lib/{types,api,utils} · store/useStore.ts · components/ui.tsx · theme/tokens.css
                 features/{schematic,catalog,device-params,generate-console,code-view,driver-import,setup}
rag/             ingest.py + retriever.py — STUBS (deferred)
docs/            EXECUTION-PLAN.md (phasing + flagged decisions)
```

## 3. 2-minute verification (run before editing)

```bash
cd /Users/mpcukur/Projects/Spec2Code
.venv/bin/python -m orchestrator.selftest            # expect: qc.passed: True, 9 files
# backend + SPA on one port:
cd frontend && npm run build && cd ..
.venv/bin/python -m uvicorn backend.main:app --port 8077   # open http://127.0.0.1:8077
# frontend dev (HMR), proxies /api+/ws to :8077:
cd frontend && npm run dev                           # http://localhost:5181
```

Tools (already installed on the Mac Mini via `brew install llvm cppcheck`): clang-format,
clang-tidy, cppcheck, libclang. Python deps in `.venv` (Python 3.14). Frontend deps installed.

## 4. Critical invariants — DO NOT break

1. **Never rename `hostplat/` back to `platform/`** — it would shadow Python's stdlib `platform`.
2. **All generated `.c/.h/.md` output goes through `hostplat.io.write_output()`** (CRLF, binary mode).
   clang-format output is captured via stdout and re-written through it — keep that pattern.
3. **No platform-specific code outside `hostplat/`**; no `subprocess` outside `hostplat.proc`.
4. **Function names are strict `module_object_action` (3 tokens)** — the ruleset regex is
   authoritative; the brief's 4-token `ltc2991_voltage_read_all` example is intentionally NOT followed.
5. **`cmodel.py` `Emit` class manages Allman braces + indentation** — don't hand-write `{`/`}`.
6. **`naming_linter.py` reads rules from the ruleset** — never hardcode them.
7. Frontend: the **zustand store (`useStore.ts`) is the contract** between features; React Flow
   node positions must be finite numbers (see decision #5), fitView runs on a timeout.

## 5. Flagged decisions (don't "fix" these — they're deliberate)

- `platform/` → `hostplat/` (stdlib collision).
- **dagre → manual layered layout** (`frontend/src/features/schematic/layout.ts`): dagre's browser
  bundle returned NaN positions via CJS/ESM interop; manual layout is portable & deterministic.
  `@dagrejs/dagre` is still in package.json but unused — fine to remove later.
- **BSP stub headers** (`orchestrator/qc/bsp_stubs/`): minimal Xilinx headers so clang-tidy/cppcheck/
  clang can syntax/type-check generated code. This is a QC gate, NOT real BSP compile (Brief §21).
- Flash demo is attached to **SPI (`XSpiPs`)**, not QSPI, for clean generic codegen.
- Ports: backend **8077**, frontend dev **5181** (5173 is taken by the user's other project).
- LLM **default OFF**; config via `SPEC2CODE_LLM_BASE_URL/MODEL/API_KEY` plus timeout/length
  env vars. The user supplies the exact OpenAI-compatible model id; no Kimi/Qwen default is guessed.

## 6. Next-up backlog (prioritized)

1. **LLM production/UI acceptance (acceptance #5)** — local plumbing is smoke-tested with Ollama
   (see current-state note above). Still needs the intended production OpenAI-compatible endpoint:
   toggle on in UI, set env/spec config, verify optimize pass + QC re-gating from the full app flow.
2. **Windows smoke-test (Brief §22)** — checklist in README; run on real air-gapped Win10. Code is
   portable-by-design and statically audited but NOT yet executed on Windows.
3. **RAG (Brief §17)** — implement `rag/ingest.py` + `retriever.py` (Docling → structural chunk →
   BGE-M3 → FAISS, two indices) and wire `orchestrator/llm/tasks.extract_descriptor`. Install
   `requirements-rag.txt` under Python 3.11–3.12 (torch/faiss may lack 3.14 wheels).
4. **More codegen transports** — `cmodel.py` covers i2c (+mux) and spi; add gpio / native qspi.
5. **`extract_ruleset.py`** — point it at the real coding-standard Word doc when provided (Brief §16).
6. **Schematic polish** — optional: per-channel mux handles (currently single handle + channel edge label).
7. Deferred per Brief §21: real compile-in-the-loop, git integration, multi-core, full Vitis scaffold.

## 7. How the pieces talk (data flow)

`xparameters.h` → `parse_xparameters` → controllers (project.spec format) → UI builds
`project.spec.json` (validated by `schemas/project.spec.schema.json`) → `POST /api/generate` →
`JobManager` runs `codegen.generate` (Jinja over `cmodel.build_units`) then `qc.run_qc`, streaming
events over `/ws/jobs/{id}` → result = generated files + `qc_report.json`. Descriptors drive the
named operations; a mux-attached device gets `<mux>_channel_select(...)` injected before each access.
```
