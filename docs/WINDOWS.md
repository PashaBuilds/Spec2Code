# Running Spec2Code on Windows 10

Spec2Code is developed on macOS, but the target operating environment is Windows 10. The
application is designed to run portably: generated `.c`, `.h`, and `.md` files are always
written with CRLF line endings, and all host-specific behavior is isolated in `hostplat/`.

There are two supported Windows paths:

1. Use the `Spec2Code.exe` bundle from GitHub Releases.
2. Run from source with Python and Node installed.

The executable is easiest for users. Source mode is best for development or debugging.

## Option A: Run the release executable

Download the Windows asset from GitHub Releases:

```text
spec2code-vX.Y.Z-windows-amd64.zip
```

Unzip it, then run:

```powershell
.\Spec2Code.exe
```

By default it starts a local web server on:

```text
http://127.0.0.1:8077
```

You can override the host and port:

```powershell
.\Spec2Code.exe --host 127.0.0.1 --port 8077
```

To start without opening the browser automatically:

```powershell
.\Spec2Code.exe --no-browser
```

## Required QC tools

The app can start without the QC tools, but full deterministic validation expects:

- LLVM for `clang-format`, `clang-tidy`, and `libclang.dll`
- Cppcheck

Install them before serious use:

```powershell
winget install LLVM.LLVM
winget install Cppcheck.Cppcheck
```

If `winget` is not available in the target environment, install the same tools on a connected
Windows machine and copy their installers into the air-gapped network using the local IT process.

Spec2Code searches these common paths automatically:

```text
C:\Program Files\LLVM\bin
C:\Program Files (x86)\LLVM\bin
C:\Program Files\Cppcheck
C:\ProgramData\chocolatey\bin
```

If the tools are installed elsewhere, set explicit paths:

```powershell
$env:SPEC2CODE_CLANG_FORMAT_PATH = "D:\Tools\LLVM\bin\clang-format.exe"
$env:SPEC2CODE_CLANG_TIDY_PATH = "D:\Tools\LLVM\bin\clang-tidy.exe"
$env:SPEC2CODE_CPPCHECK_PATH = "D:\Tools\Cppcheck\cppcheck.exe"
$env:SPEC2CODE_LIBCLANG_PATH = "D:\Tools\LLVM\bin\libclang.dll"
```

Open this URL after starting Spec2Code to check tool resolution:

```text
http://127.0.0.1:8077/api/health
```

Expected shape:

```json
{
  "status": "ok",
  "tools": {
    "clang-format": "C:\\Program Files\\LLVM\\bin\\clang-format.exe",
    "clang-tidy": "C:\\Program Files\\LLVM\\bin\\clang-tidy.exe",
    "cppcheck": "C:\\Program Files\\Cppcheck\\cppcheck.exe",
    "libclang": "C:\\Program Files\\LLVM\\bin\\libclang.dll"
  }
}
```

## Option B: Run from source

Use this when you need to inspect or modify the project.

Prerequisites:

- Python 3.11 or 3.12
- Node.js 22 LTS
- LLVM
- Cppcheck

From PowerShell:

```powershell
cd C:\Work\Spec2Code

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..

.\.venv\Scripts\python.exe -m orchestrator.selftest
.\.venv\Scripts\python.exe run_spec2code.py
```

Open:

```text
http://127.0.0.1:8077
```

For frontend development with HMR:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8077

cd frontend
npm run dev
```

Then open:

```text
http://localhost:5181
```

## Air-gapped transfer checklist

Before moving to the final Windows 10 machine, prepare these on a connected machine:

- The Windows release zip, or the source zip from GitHub Releases.
- Python installer, if using source mode.
- Node.js installer, if using source mode.
- LLVM installer.
- Cppcheck installer.
- Optional local OpenAI-compatible LLM runtime, if the LLM pass will be enabled.

After copying into the air-gapped machine:

1. Install LLVM and Cppcheck.
2. Start Spec2Code.
3. Open `/api/health` and confirm tool paths are found.
4. Upload a sample `xparameters.h`.
5. Generate the sample project.
6. Confirm `outputs/<project>/qc_report.json` reports `passed: true`.
7. Confirm generated `.c` and `.h` files use CRLF line endings.

## Optional LLM on Windows

LLM is default off. If you run a local or internal OpenAI-compatible endpoint:

```powershell
$env:SPEC2CODE_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:SPEC2CODE_LLM_MODEL = "gemma3:12b"
$env:SPEC2CODE_LLM_API_KEY = ""
```

Every LLM-produced file is re-run through the deterministic QC loop before delivery.

## Creating a Windows executable manually

Normally GitHub Actions builds the Windows `.exe` when a `v*` tag is pushed. To build it
manually on Windows:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller

cd frontend
npm ci
npm run build
cd ..

.\.venv\Scripts\python.exe scripts\build_executable.py --version vX.Y.Z
```

The zip is written to:

```text
release-assets\
```
