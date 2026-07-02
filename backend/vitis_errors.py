"""Vitis/XSCT build-log error mapper.

The goal is not to hide the raw log. It is to surface the first useful engineering hint:
missing BSP include, wrong XSA/processor, unresolved driver symbol, and similar bring-up
failures that otherwise get buried in a long Vitis transcript.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VitisIssue:
    severity: str
    category: str
    message: str
    suggestion: str
    file: str = ""
    line: int | None = None
    symbol: str = ""
    raw: str = ""

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "suggestion": self.suggestion,
            "file": self.file,
            "line": self.line,
            "symbol": self.symbol,
            "raw": self.raw,
        }


_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(r"libsrc[/\\](?P<symbol>[^/\\\s]+)[/\\]src[/\\]make\.libs", re.I),
        "custom_ip_bsp_driver",
        "BSP build custom PL IP driver klasorunde patlamis. Bu genelde user-packaged/custom IP'nin gercek driver source'u olmadan BSP'ye driver gibi eklenmesinden olur. Guncel Spec2Code ile `Auto: custom IP - none` secili sekilde temiz/yeni workspace'e yeniden uret; gerekirse BSP Settings > drivers altinda ilgili IP driver'ini `none` yap.",
    ),
    (
        re.compile(r"fatal error:\s+\*\.c:\s+Invalid argument", re.I),
        "custom_ip_bsp_driver",
        "Windows GCC literal `*.c` girdisini derlemeye calismis. Bu genelde source'suz custom PL IP BSP driver makefile'inda gorulur. Guncel Spec2Code ile `Auto: custom IP - none` secili sekilde temiz/yeni workspace'e yeniden uret.",
    ),
    (
        re.compile(r"application project '(?P<symbol>[^']+)' was not created", re.I),
        "workspace_stale",
        "Hedef workspace dizini önceki (başarısız) denemeden kalıntı içeriyor olabilir. Spec2Code her çalıştırmada platform/application'ı sıfırdan oluşturur; boş bir workspace dizini ile tekrar dene.",
    ),
    (
        re.compile(r"The project given does not exist in workspace", re.I),
        "workspace_stale",
        "Application projesi workspace registry'sinde yok. Genelde `app create` önceki denemeden kalan workspace kalıntısı yüzünden sessizce başarısız olmuştur; boş bir workspace dizini ile tekrar dene.",
    ),
    (
        re.compile(r"invalid command name\s+\"(?P<symbol>[^\"]+)\"", re.I),
        "xsct_tcl_command",
        "XSCT Tcl script içinde literal yazı komut gibi yorumlanmış. Script quoting/escaping kontrol edilmeli; generated script güncel sürümle tekrar üretilmeli.",
    ),
    (
        re.compile(r"while executing", re.I),
        "xsct_tcl_stack",
        "XSCT Tcl script çalışırken hata oluştu. Hemen üstteki Tcl hata satırı ve script line bilgisini kontrol et.",
    ),
    (
        re.compile(r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s+fatal error:\s+(?P<header>[^:]+): No such file", re.I),
        "missing_include",
        "Header bulunamadı. BSP include path, generated driver include path veya Vitis domain ayarı eksik olabilir.",
    ),
    (
        re.compile(r"undefined reference to [`'](?P<symbol>[^`']+)", re.I),
        "undefined_reference",
        "Link aşamasında sembol bulunamadı. İlgili `.c` dosyası application source içine eklenmemiş veya function adı değişmiş olabilir.",
    ),
    (
        re.compile(r"multiple definition of [`'](?P<symbol>[^`']+)", re.I),
        "multiple_definition",
        "Aynı sembol birden fazla source dosyasında tanımlanıyor. Aynı driver dosyasının iki kez eklenmediğini kontrol et.",
    ),
    (
        re.compile(r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s+error:\s+[`']?(?P<symbol>XPAR_[A-Za-z0-9_]+)[`']?\s+undeclared", re.I),
        "missing_xparameter",
        "`xparameters.h` içindeki macro generated kodun beklediği macro ile uyuşmuyor. Yanlış XSA/BSP veya farklı processor domain seçilmiş olabilir.",
    ),
    (
        re.compile(r"(?P<file>[^:\n]+):(?P<line>\d+):\d+:\s+error:\s+unknown type name [`']?(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)", re.I),
        "unknown_type",
        "BSP driver header include edilmemiş veya ilgili peripheral driver domain içinde yok.",
    ),
    (
        re.compile(r"implicit declaration of function [`']?(?P<symbol>[A-Za-z_][A-Za-z0-9_]*)", re.I),
        "implicit_declaration",
        "Fonksiyon prototipi görünmüyor. İlgili header include path'e girmemiş veya `.h` dosyası application source tree'ye eklenmemiş olabilir.",
    ),
    (
        re.compile(r"cannot find -l(?P<symbol>[A-Za-z0-9_+-]+)", re.I),
        "missing_library",
        "Linker library bulamadı. BSP/domain generation ve linker settings kontrol edilmeli.",
    ),
    (
        re.compile(r"ERROR:\s+.*processor.*(?P<symbol>ps[a-z0-9_]+|microblaze_[0-9]+)", re.I),
        "wrong_processor",
        "Vitis processor instance adı XSA ile uyuşmuyor olabilir. Workspace panelindeki processor alanını XSA içindeki gerçek instance adıyla düzelt.",
    ),
    (
        re.compile(r"ERROR:\s+.*(?:xsa|hardware|platform).*", re.I),
        "xsa_or_platform",
        "XSA/platform oluşturma aşaması hata verdi. `.xsa` path'ini, export bütünlüğünü ve Vitis sürüm uyumluluğunu kontrol et.",
    ),
    (
        re.compile(r"No rule to make target [`']?(?P<file>[^`'\n]+)", re.I),
        "missing_source",
        "Build system beklediği source/object dosyasını bulamıyor. Workspace staging ve importsources adımını kontrol et.",
    ),
]

_BENIGN_TAIL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:aarch64-none-elf-)?ar(?:\.exe)?:\s+creating\b", re.I),
]


def _looks_like_benign_tail(line: str) -> bool:
    return any(pattern.search(line) for pattern in _BENIGN_TAIL_PATTERNS)


def map_vitis_errors(log_text: str, *, limit: int = 40) -> list[dict]:
    issues: list[VitisIssue] = []
    seen: set[tuple[str, str, str, int | None]] = set()
    for line in log_text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        for pattern, category, suggestion in _PATTERNS:
            match = pattern.search(clean)
            if not match:
                continue
            groups = match.groupdict()
            file_name = groups.get("file") or ""
            raw_line = groups.get("line")
            line_no = int(raw_line) if raw_line and raw_line.isdigit() else None
            symbol = groups.get("symbol") or groups.get("header") or ""
            key = (category, file_name, symbol, line_no)
            if key in seen:
                break
            seen.add(key)
            issues.append(VitisIssue(
                severity="error",
                category=category,
                message=clean,
                suggestion=suggestion,
                file=file_name,
                line=line_no,
                symbol=symbol,
                raw=clean,
            ))
            break
        if len(issues) >= limit:
            break

    if not issues and log_text.strip():
        non_empty_lines = [line.strip() for line in log_text.splitlines() if line.strip()]
        tail = non_empty_lines[-1]
        useful_tail = next(
            (line for line in reversed(non_empty_lines) if not _looks_like_benign_tail(line)),
            "",
        )
        if useful_tail:
            message = useful_tail
            raw = useful_tail
            suggestion = "Raw Vitis/XSCT log içinde ilk ERROR veya compiler error satırını incele. Bu hata sınıfı henüz mapper tarafından tanınmıyor."
        else:
            message = "Vitis/XSCT hata döndürdü ama log sonunda açık compiler/linker hata satırı bulunamadı."
            raw = tail
            suggestion = (
                "Application build loglarını ve ELF artifact listesini kontrol et. "
                "`ar: creating libfreertos.a` gibi BSP archive satırları tek başına root cause değildir."
            )
        issues.append(VitisIssue(
            severity="error",
            category="unclassified",
            message=message,
            suggestion=suggestion,
            raw=raw,
        ))
    return [issue.as_dict() for issue in issues]
