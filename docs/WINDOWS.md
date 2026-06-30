# Running Spec2Code on Windows 10

Spec2Code is developed on macOS, but the target operating environment is Windows 10. The
application is designed to run portably: generated `.c`, `.h`, and `.md` files are always
written with CRLF line endings, and all host-specific behavior is isolated in `hostplat/`.

There are two supported Windows paths:

1. Use the `Spec2Code.exe` bundle from GitHub Releases.
2. Run from source with Python and Node installed.

The executable is easiest for users. Source mode is best for development or debugging.

## EXE, source, and the web UI

Spec2Code is a local web application. The UI you open in the browser is not hosted by an
external cloud service. It is a React single-page app served by a local FastAPI process.

- `Spec2Code.exe` is a packaged runtime: it starts the local server and serves the built web UI.
- `spec2code-vX.Y.Z-source.zip` is the full tracked source tree: use this when you want to keep
  developing on Windows.
- In source mode, the same UI is available through either the single-server built app
  (`run_spec2code.py`) or the Vite dev server (`npm run dev`) with hot reload.

For an air-gapped Windows development machine, copy the source zip plus an offline dependency
cache prepared on a connected Windows machine.

## Option A: Run the release executable

Download the Windows asset from GitHub Releases:

```text
spec2code-vX.Y.Z-windows-x64.zip
```

Unzip it, then run:

```powershell
.\Spec2Code.exe
```

The executable zip is intentionally minimal:

```text
Spec2Code.exe
changelog.md
userguide.md
```

`changelog.md` contains the full release history. `userguide.md` contains the user-level
operating guide for setup, schematic, generate, Vitis workspace, LLM, and troubleshooting.

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

## Tek Tuş Vitis Workspace Üretimi

Generate tamamlandıktan sonra Code ekranındaki **Vitis workspace** panelini kullanabilirsin.
Bu akış Windows makinede lokal çalışan FastAPI backend üzerinden gerçek dosya path'lerine
erişir; browser file picker yerine path'leri text olarak girmen bu yüzden yeterlidir.

Gereken bilgiler:

- Vitis dizini: `C:\Xilinx\Vitis\2024.2` veya `C:\Xilinx`
- XSA dosyası: Vivado/Vitis hardware export çıktısının doğrudan `.xsa` dosya yolu,
  örnek `D:\Board\export\system.xsa`
- Workspace dizini: örnek `D:\VitisWorkspaces\spec2code`
- Temp/Staging dizini: örnek `D:\VitisTemp\spec2code`
- Platform proje adı: örnek `my_io_board_platform`
- System proje adı: örnek `my_io_board_system`
- Application proje adı: örnek `my_io_board_app`
- Processor: çoğu durumda otomatik gelir; gerekirse Vitis'teki gerçek instance adıyla
  değiştir, örnek `psu_cortexa53_0`

Backend şu arama sırasıyla `xsct` bulmaya çalışır:

```text
<Vitis>\bin\xsct.bat
<Vitis>\xsct.bat
<Vitis>\Vitis\<version>\bin\xsct.bat
<Vitis>\<version>\bin\xsct.bat
```

Linux/macOS geliştirme ortamında aynı mantık `xsct` dosyasını arar. Windows'ta `.bat`
bulunursa komut `cmd.exe /c xsct.bat <script>` şeklinde çalıştırılır.

Akış aşamaları UI'da progress bar ile görünür:

1. XSCT path'i bulunur.
2. `xsct -version` ile Vitis/XSCT sürümü algılanır.
3. `.xsa` dosyası, generated `drivers/`, `tests/`, referans kaynaklar ve
   `spec2code_selftest_main.c/.h` kullanıcının verdiği temp/staging dizinine
   kopyalanır.
4. XSA içindeki non-Xilinx/AMD custom PL IP adayları `.hwh` üzerinden algılanır.
   `xilinx.com:ip:<custom_ad>` şeklinde görünen ama standart Xilinx IP ailesine
   benzemeyen PL peripheral'lar da custom-like aday sayılır; standart Xilinx IP
   aileleri korunur.
5. Varsayılan custom PL IP policy `auto_none` olduğu için bu aday IP'lerin BSP
   driver'ı `none` yapılmaya çalışılır. Vitis yine de source'suz custom IP BSP
   driver'ını build etmeye çalışırsa ilgili `make.libs`, `bsp regenerate` ve
   `app build` öncesinde no-op hale getirilir. Staged `.xsa` içindeki source'suz
   custom driver makefile'ları da Vitis görmeden önce patchlenir. XSCT sırasında
   host watcher application, FSBL ve PMU/PMUFW BSP `libsrc` klasörlerini de izler;
   gerçek şirket driver'ı kullanılacaksa Vitis panelinde `BSP default'u koru`
   seçilmelidir.
6. lwIP test bench gerekiyorsa BSP library seçimi yapılır; standalone için
   `RAW_API`, FreeRTOS için `SOCKET_API` mode denenir.
7. `spec2code_create_workspace.tcl` yazılır.
8. XSCT headless çalıştırılır; önce adlandırılmış platform/system/application
   akışı denenir, uyumsuz Vitis varyantında legacy `app create -hw` akışına dönülür.
9. `app build` başarılıysa workspace hazır olarak işaretlenir.

Temp/Staging dizini altında oluşturulan yardımcı dosyalar:

```text
<temp-staging-dizini>\<vitis_job>\
  hw\
  src\
  spec2code_create_workspace.tcl
  spec2code_vitis_manifest.json
  logs\xsct_stdout.log
  logs\xsct_stderr.log
```

Hata alırsan önce UI'daki son progress mesajına, sonra `xsct_stderr.log` dosyasına bak.
Bu dosyalar özellikle Vitis sürüm farkı, yanlış processor instance adı, bozuk `.xsa` veya
eksik BSP/toolchain durumlarını ayırmak için bırakılır.

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

.\scripts\windows\setup-source.ps1
.\scripts\windows\verify-source.ps1
.\scripts\windows\run-source.ps1
```

Open:

```text
http://127.0.0.1:8077
```

For frontend development with HMR:

```powershell
.\scripts\windows\run-dev.ps1
```

Then open:

```text
http://localhost:5181
```

The helper scripts are thin wrappers around the normal commands. You can still run the commands
manually if you prefer.

## Source development on an air-gapped Windows host

On a connected Windows machine, use the same source tree to prepare dependency caches:

```powershell
.\scripts\windows\prepare-offline-deps.ps1 -OfflineRoot offline
```

Copy these into the air-gapped machine:

- `spec2code-vX.Y.Z-source.zip`
- the generated `offline\` folder, copied into the extracted source root or referenced by full path
- LLVM installer
- Cppcheck installer
- Node.js installer
- Python installer
- optional local or internal OpenAI-compatible LLM runtime

On the air-gapped machine:

```powershell
Expand-Archive .\spec2code-vX.Y.Z-source.zip -DestinationPath C:\Work
cd C:\Work\spec2code-vX.Y.Z
Copy-Item C:\Transfer\offline .\offline -Recurse

.\scripts\windows\setup-source.ps1 -OfflineRoot offline
.\scripts\windows\verify-source.ps1
.\scripts\windows\run-source.ps1
```

For active frontend work:

```powershell
.\scripts\windows\run-dev.ps1
```

## Air-gapped transfer checklist

Before moving to the final Windows 10 machine, prepare these on a connected machine:

- The Windows release zip, or the source zip from GitHub Releases.
- The optional `offline\` dependency cache if you will develop from source without internet.
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

LLM is default off. This is intentional: deterministic descriptor/template codegen and QC work
without any model.

If you run a local or internal OpenAI-compatible endpoint, point Spec2Code at it:

```powershell
$env:SPEC2CODE_LLM_BASE_URL = "http://127.0.0.1:11434/v1"
$env:SPEC2CODE_LLM_MODEL = "endpointte_gorunen_tam_model_adi"
$env:SPEC2CODE_LLM_API_KEY = ""
$env:SPEC2CODE_LLM_TIMEOUT_S = "120"
$env:SPEC2CODE_LLM_MAX_TOKENS = "4096"
$env:SPEC2CODE_LLM_MAX_RESPONSE_CHARS = "120000"
$env:SPEC2CODE_LLM_RETRIES = "0"
```

You can use Kimi, Qwen, or a weaker local model for iteration as long as the server exposes the
OpenAI-compatible `/v1/chat/completions` API. Enter the exact model id shown by that server. Treat
local-model output as an assistive pass, not the source of truth. Timeout, truncated, empty, or
overlong responses are reported explicitly in the generate console. LLM output is staged as a
candidate first, rejected if it removes existing C functions or fails the available deterministic
checks, and only then written to the real file. Every accepted LLM-produced file is re-run through
the deterministic QC loop before delivery.

## Coding Standard on Windows

Spec2Code uses the fixed default coding standard in `std/default.ruleset.json`.
The Windows `.exe` does not import Word, Markdown, text, or custom JSON coding-standard files.
Older project specs that contain another `coding_standard_ref` are normalized back to:

```text
std/default.ruleset.json
```

The Setup screen shows the active standard as information only: camelCase identifiers and
function names such as `tca9548aChannelSelect`, Hungarian prefixes, Allman braces, CRLF line
endings, `SOrnekStruct`-style struct typedefs, `sMyStruct`-style struct variables,
`spMyStruct`-style structure pointers, `EOrnekEnum`-style enum typedefs, type-prefix + `p`
pointers, type-prefix + `Arr` arrays, `G_` globals, and `S_` static variables. Pointer stars
attach to the type (`XIicPs* spIic`), and generated code uses primitive C types such as
`unsigned char`/`unsigned int` instead of `uint8_t`/`uint32_t`.

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
