"""QC tool runners (Brief 15, 16): clang-format, clang-tidy, cppcheck.

Each runner resolves its tool through hostplat.tools (cross-platform) and shells out through
hostplat.proc. When a tool is missing, the runner returns a structured "skipped" marker
instead of raising - the QC loop degrades gracefully (Brief decision #3). clang-format output
is captured and re-written through hostplat.io so the CRLF guarantee stays centralized.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from hostplat import io as hio
from hostplat import proc
from hostplat import tools

# Directory of minimal BSP stub headers so clang-tidy/cppcheck can parse generated code.
BSP_STUBS = Path(__file__).resolve().parent / "bsp_stubs"


@dataclass
class Violation:
    file: str
    line: int
    column: int
    rule: str
    severity: str       # error | warning | style | info
    message: str
    source: str         # clang-format | clang-tidy | cppcheck | naming-linter

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RunnerResult:
    tool: str
    available: bool
    violations: list[Violation]
    skipped_reason: Optional[str] = None


# --- kaynak agaci ------------------------------------------------------------------------

def driver_include_dirs(drivers_dir: Path) -> list[Path]:
    """`drivers/` + basligi olan her ALT klasoru (kart klasorleri).

    Kart tanimliyken suruculer `drivers/<kart>/` altina yazilir; nitelenmemis
    ``#include "tmp101.h"`` cozulsun diye her kart klasoru include yoluna girer.
    Kart tanimsiz projelerde alt klasor yoktur -> sonuc bugunku ``[drivers]``.
    """
    drivers_dir = Path(drivers_dir)
    dirs = [drivers_dir]
    if drivers_dir.is_dir():
        dirs.extend(sorted({
            header.parent for header in drivers_dir.rglob("*.h")
            if header.parent != drivers_dir
        }))
    return dirs


# --- clang-format -----------------------------------------------------------------------

def clang_format_config(ruleset: dict, *, legacy: bool = False) -> str:
    """`.clang-format` icerigi.

    SAHA (2026-09-07, sirket makinesi): eski bir clang-format (<10) config'i
    `YAML:14:32: error: invalid boolean` ile reddetti -> HER dosya
    `qc.format_failed` -> 63 error, QC KALDI. `AllowShortBlocksOnASingleLine`
    10 oncesinde boolean'dir; `false` her surumde gecerlidir (>=10 bunu `Never`
    olarak okur), o yuzden enum degil boolean yazilir. `UseCRLF`/`DeriveLineEnding`
    de 10'da geldi ve eski surum bilinmeyen anahtari HATA sayar: ``legacy=True``
    bu iki anahtari birakir (CRLF'i zaten `hostplat.io.write_output` basar).
    """
    fmt = ruleset.get("formatting", {})
    brace = {"allman": "Allman", "attach": "Attach", "k&r": "Linux"}.get(
        fmt.get("brace_style", "allman"), "Allman")
    indent = 4 if fmt.get("indent", "spaces_4") == "spaces_4" else 4
    column = fmt.get("max_line_length", 100)
    use_crlf = "true" if fmt.get("line_ending") == "crlf" else "false"
    line_ending_keys = "" if legacy else (
        f"UseCRLF: {use_crlf}\n"
        "DeriveLineEnding: false\n"
    )
    return (
        "---\n"
        "Language: Cpp\n"
        "BasedOnStyle: LLVM\n"
        f"BreakBeforeBraces: {brace}\n"
        f"IndentWidth: {indent}\n"
        "UseTab: Never\n"
        f"ColumnLimit: {column}\n"
        f"{line_ending_keys}"
        "PointerAlignment: Left\n"
        "AllowShortFunctionsOnASingleLine: None\n"
        "AllowShortIfStatementsOnASingleLine: false\n"
        "AllowShortLoopsOnASingleLine: false\n"
        "AllowShortBlocksOnASingleLine: false\n"
        "SortIncludes: false\n"
    )


def write_clang_format_config(out_dir: Path, ruleset: dict) -> Optional[str]:
    """`.clang-format`'i yazar ve YEREL clang-format'in onu okuyabildigini dogrular.

    Arac config'i reddederse (eski surum, bilinmeyen anahtar) legacy config'e
    duser ve yeniden dogrular. Donus: None (tamam / arac yok) ya da aracin
    verdigi hata metni (legacy bile okunamadi - format adimi bunu raporlar).
    """
    out_dir = Path(out_dir)
    tool = tools.resolve("clang-format", required=False)
    for legacy in (False, True):
        hio.write_output(out_dir / ".clang-format", clang_format_config(ruleset, legacy=legacy))
        if tool is None:
            return None
        probe = proc.run([tool, "-style=file", "--dump-config"], cwd=out_dir, timeout=60)
        if probe.ok and "error" not in probe.stderr.lower():
            return None
        last_error = probe.stderr.strip() or "clang-format config reddedildi"
    return last_error


def format_file(path: Path, config_dir: Path) -> tuple[bool, bool, Optional[str]]:
    """Format *path* in place (via stdout capture + hostplat.io write).

    Returns (available, changed, skipped_reason).

    **Yazma kalkani (derinlemesine savunma).** Bu fonksiyon bir aracin stdout'unu
    KAYNAK DOSYANIN uzerine yazar; yani arac ne donerse dosyanin yeni icerigi odur.
    Sahada gorulen veri kaybinda `proc.run` yerel ayar yuzunden cozemedigi ciktiyi
    `returncode=0` + `stdout=""` olarak dondurmus, burasi da o bosu geri yazip
    `spec2code_cit.c` / `spec2code_cit.h` / `spec2code_testbench_log.c`
    dosyalarini 0 bayta dusurmustu - ustelik "basarili" raporlayarak.

    Kok neden `hostplat.proc` tarafinda giderildi. Buradaki kalkan ondan BAGIMSIZDIR:
    dolu bir girdi bos/yalniz-bosluk bir ciktiya format'lanamaz, dolayisiyla bu
    durum HER ZAMAN arac hatasidir. Boyle bir durumda dosyaya DOKUNULMAZ ve sebep
    acikca dondurulur; gelecekte baska bir arac arizasi da dosyayi bosaltamaz.
    """
    tool = tools.resolve("clang-format", required=False)
    if tool is None:
        return False, False, "clang-format not found"
    target = Path(path)
    before = target.read_bytes()
    result = proc.run([tool, "-style=file", str(target)], cwd=config_dir, timeout=60)
    if not result.ok:
        return True, False, result.stderr.strip() or "clang-format failed"
    # Dolu girdi -> bos cikti: imkansiz. Yaz-ma, bildir. (Bos girdi icin mesru.)
    if before.strip() and not result.stdout.strip():
        detail = result.stderr.strip()
        return True, False, (
            "clang-format bos cikti dondu (girdi {n} bayt) - dosya KORUNDU, "
            "yazilmadi{extra}".format(
                n=len(before), extra=f": {detail}" if detail else "")
        )
    hio.write_output(target, result.stdout)
    after = target.read_bytes()
    return True, (before != after), None


# --- proje ozel xparameters eki ------------------------------------------------------------

_XPAR_TOKEN_RE = re.compile(r"\bXPAR_[A-Z0-9_]+?_(?:DEVICE_ID|BASEADDR|HIGHADDR)\b")
PROJECT_XPARAMETERS_STUB = "spec2code_qc_xparameters.h"


def collect_xpar_tokens(files: list[Path]) -> list[str]:
    """Uretilen kodda gecen `XPAR_*_{DEVICE_ID,BASEADDR,HIGHADDR}` adlari (sirali, tekil)."""
    tokens: set[str] = set()
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        tokens.update(_XPAR_TOKEN_RE.findall(text))
    return sorted(tokens)


def project_xparameters_stub(files: list[Path]) -> str:
    """Generic stub'in tanimadigi XPAR adlari icin tip-denetimi degerleri.

    SAHA (2026-09-07): XSA'dan cikarilan spec'te denetleyici ornekleri `XPAR_PSU_I2C_0`,
    `XPAR_PSU_QSPI_0`, `XPAR_PSU_ETHERNET_3` gibi cevre-birimi adlaridir; generic stub
    yalniz kanonik `XPAR_XIICPS_0` ailesini tasiyordu -> clang-tidy "undeclared
    identifier" ERROR -> XSA yuklenen HER projede QC KALDI. Degerlerin anlami yoktur
    (yalniz cozumleme); gercek BSP xparameters.h'i Vitis'te kullanilir.
    """
    generic = (BSP_STUBS / "xparameters.h").read_text(encoding="utf-8")
    lines = ["/* Spec2Code QC: proje ozel XPAR ekleri (otomatik, tip denetimi icin). */",
             "#ifndef SPEC2CODE_QC_XPARAMETERS_H", "#define SPEC2CODE_QC_XPARAMETERS_H"]
    device_ids = 0
    base_addrs = 0
    for token in collect_xpar_tokens(files):
        if re.search(rf"#define {re.escape(token)}\b", generic):
            continue
        if token.endswith("_DEVICE_ID"):
            value = str(device_ids)
            device_ids += 1
        elif token.endswith("_BASEADDR"):
            value = f"0x{0x40000000 + base_addrs * 0x10000:08X}U"
            base_addrs += 1
        else:
            value = f"0x{0x4000FFFF + base_addrs * 0x10000:08X}U"
        lines.append(f"#ifndef {token}")
        lines.append(f"#define {token} {value}")
        lines.append("#endif")
    lines.append("#endif /* SPEC2CODE_QC_XPARAMETERS_H */")
    return "\n".join(lines) + "\n"


def write_project_xparameters_stub(include_dir: Path, files: list[Path]) -> Path:
    target = Path(include_dir) / PROJECT_XPARAMETERS_STUB
    hio.write_output(target, project_xparameters_stub(files))
    return target


# --- clang-tidy -------------------------------------------------------------------------

# `(?:[A-Za-z]:)?` is load-bearing on Windows: clang-tidy/cppcheck echo the
# absolute path they were given (`C:\...\tmp101.c:12:5: warning: ...`), and a
# plain `[^:]+` file group stops at the drive-letter colon so the whole line
# fails to match. Without it every finding was silently dropped on Windows and
# the QC gate reported "tool available, 0 violations" — a false pass.
_PATH_PREFIX = r"(?:[A-Za-z]:)?"
_TIDY_RE = re.compile(
    rf"^(?P<file>{_PATH_PREFIX}[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<sev>warning|error):\s+(?P<msg>.*?)\s*(?:\[(?P<rule>[^\]]+)\])?$"
)


def run_clang_tidy(path: Path, include_dirs: list[Path]) -> RunnerResult:
    tool = tools.resolve("clang-tidy", required=False)
    if tool is None:
        return RunnerResult("clang-tidy", False, [], "clang-tidy not found")
    includes = []
    for d in [BSP_STUBS, *include_dirs]:
        includes += ["-I", str(d)]
    cmd = [tool, str(path), "--quiet",
           # bugprone-easily-swappable-parameters conflicts with hardware register/value APIs.
           # security.insecureAPI.DeprecatedOrUnsafeBufferHandling asks for the C11 Annex K
           # `_s` functions (memset_s/snprintf_s). Annex K is OPTIONAL and the Xilinx bare-metal
           # newlib (mb-gcc, aarch64-none-elf-gcc) does not implement it, so following the advice
           # would not even link on the target - it is a false positive for this codebase.
           "--checks=clang-analyzer-*,bugprone-*,-bugprone-easily-swappable-parameters,"
           "-clang-analyzer-security.insecureAPI.DeprecatedOrUnsafeBufferHandling,"
           "readability-braces-around-statements",
           # Windows'ta VS-LLVM clang-tidy MSVC CRT basliklarini gorur; CRT'nin
           # `strncpy` -> `strncpy_s` "deprecated" uyarisi HOST gurultusudur
           # (hedef newlib'de yoktur), kapatilir.
           "--", "-std=c11", "-D_CRT_SECURE_NO_WARNINGS", *includes]
    result = proc.run(cmd, timeout=120)
    violations: list[Violation] = []
    target = str(Path(path).resolve())
    for line in result.stdout.splitlines():
        m = _TIDY_RE.match(line.strip())
        if not m:
            continue
        if str(Path(m.group("file")).resolve()) != target and "file not found" not in m.group("msg"):
            # only our file, not stub-header noise. ISTISNA: bir include'un bulunamamasi
            # (or. surucu basliginin icindeki `xiic.h`) baska dosyada raporlanir ama TU'yu
            # oldurur; sessiz gecilirse dosya hic denetlenmemis olur (SAHA 2026-09-07:
            # MicroBlaze ciktilari aylarca bu yuzden "temiz" gorundu).
            continue
        violations.append(Violation(
            file=str(path), line=int(m.group("line")), column=int(m.group("col")),
            rule=m.group("rule") or "clang-tidy", severity=m.group("sev"),
            message=m.group("msg"), source="clang-tidy"))
    return RunnerResult("clang-tidy", True, violations)


# --- cppcheck ---------------------------------------------------------------------------

_CPPCHECK_TEMPLATE = "{file}:{line}:{column}: {severity}: {message} [{id}]"
_CPPCHECK_RE = re.compile(
    rf"^(?P<file>{_PATH_PREFIX}[^:]+):(?P<line>\d+):(?P<col>\d+):\s+(?P<sev>\w+):\s+(?P<msg>.*?)\s*\[(?P<rule>[^\]]+)\]$"
)
# Non-violations: stub/include limitations, not problems with the generated code.
_CPPCHECK_IGNORE = {"missingInclude", "missingIncludeSystem", "unmatchedSuppression",
                    "toomanyconfigs", "normalCheckLevelMaxBranches", "checkersReport",
                    # variableScope conflicts with the embedded "declare at block top" convention.
                    "variableScope"}


def run_cppcheck(path: Path, include_dirs: list[Path]) -> RunnerResult:
    tool = tools.resolve("cppcheck", required=False)
    if tool is None:
        return RunnerResult("cppcheck", False, [], "cppcheck not found")
    includes = [f"-I{BSP_STUBS}"] + [f"-I{d}" for d in include_dirs]
    cmd = [tool, "--enable=warning,style,performance,portability", "--quiet",
           "--inline-suppr", f"--template={_CPPCHECK_TEMPLATE}", "--language=c",
           "--std=c11", *includes, str(path)]
    result = proc.run(cmd, timeout=120)
    violations: list[Violation] = []
    for line in (result.stdout + "\n" + result.stderr).splitlines():
        m = _CPPCHECK_RE.match(line.strip())
        if not m or m.group("rule") in _CPPCHECK_IGNORE:
            continue
        violations.append(Violation(
            file=str(path), line=int(m.group("line")), column=int(m.group("col")),
            rule=m.group("rule"), severity=m.group("sev"),
            message=m.group("msg"), source="cppcheck"))
    return RunnerResult("cppcheck", True, violations)
