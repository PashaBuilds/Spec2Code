"""Datasheet PDF'inden referans metni cikarma (yapay zeka modu, descriptor uretimi girdisi).

Datasheet'ler yuzlerce sayfadir; modele yalniz register haritasi/arayuz sayfalari verilir. Kullanici sayfa
araligi secer ("12-20,35"); secmezse tum sayfalar (karakter sinirina kadar). Sayfa secimine yardim icin
register/reset/address gecen sayfalar puanlanip onerilir. Metin cikarimi pypdf ile yereldir; PDF disari
gonderilmez, yalniz cikan metin (kullanici gorup onayladiktan sonra) LLM endpoint'ine gider.
"""
from __future__ import annotations

import io
import re

from pypdf import PdfReader

MAX_CHARS = 60_000
_KEYWORDS = re.compile(r"\b(register|reg\.|reset value|address|bit ?field|bits?|offset|read/write|r/w)\b", re.IGNORECASE)
_RANGE_RE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$")


def parse_page_spec(spec: str, total: int) -> list[int]:
    """"12-20,35" -> [12..20, 35] (1 tabanli, sirali, tekrarsiz). Bos -> tum sayfalar. Aralik disi -> ValueError."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(1, total + 1))
    pages: list[int] = []
    for chunk in spec.split(","):
        match = _RANGE_RE.match(chunk)
        if not match:
            raise ValueError(f"sayfa ifadesi anlasilamadi: '{chunk.strip()}' (ornek: 12-20,35)")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end > total or start > end:
            raise ValueError(f"sayfa araligi {start}-{end} PDF'in disinda (toplam {total} sayfa)")
        pages.extend(range(start, end + 1))
    return sorted(set(pages))


def _clean(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def extract_reference(pdf_bytes: bytes, page_spec: str = "", *, max_chars: int = MAX_CHARS) -> dict:
    """Secili sayfalarin metni. Donus: text, pages_total, pages_used, chars, truncated, suggested_pages
    (register anahtar kelimesi yogun ilk 12 sayfa; sayfa secmeyen kullaniciya ipucu)."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        total = len(reader.pages)
    except Exception as exc:  # noqa: BLE001 - pypdf farkli hata tipleri atar
        raise ValueError(f"PDF okunamadi: {exc}") from exc
    if total == 0:
        raise ValueError("PDF bos (0 sayfa)")
    pages = parse_page_spec(page_spec, total)
    texts: dict[int, str] = {}
    for number in range(1, total + 1):
        try:
            texts[number] = _clean(reader.pages[number - 1].extract_text() or "")
        except Exception:  # noqa: BLE001 - tek bozuk sayfa tum cikarimi dusurmesin
            texts[number] = ""
    scored = sorted(((len(_KEYWORDS.findall(texts[n])), n) for n in texts), key=lambda item: (-item[0], item[1]))
    suggested = [n for score, n in scored[:12] if score > 0]
    parts: list[str] = []
    used: list[int] = []
    chars = 0
    truncated = False
    for number in pages:
        block = f"--- sayfa {number} ---\n{texts[number]}\n"
        if chars + len(block) > max_chars:
            truncated = True
            break
        parts.append(block)
        used.append(number)
        chars += len(block)
    text = "".join(parts)
    if not text.strip():
        raise ValueError("secili sayfalardan metin cikmadi (taranmis/goruntu PDF olabilir; OCR gerekir)")
    return {"text": text, "pages_total": total, "pages_used": used, "chars": len(text),
            "truncated": truncated, "suggested_pages": sorted(suggested)}
