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
        tail = [line.strip() for line in log_text.splitlines() if line.strip()][-1]
        issues.append(VitisIssue(
            severity="error",
            category="unclassified",
            message=tail,
            suggestion="Raw Vitis/XSCT log içinde ilk ERROR veya compiler error satırını incele. Bu hata sınıfı henüz mapper tarafından tanınmıyor.",
            raw=tail,
        ))
    return [issue.as_dict() for issue in issues]
