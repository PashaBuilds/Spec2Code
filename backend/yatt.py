"""YATT (Yazilim Arayuzu Tanimlama/Tarifi) uretici.

S2C-MSG binary protokolunun tek dogruluk kaynagi backend/data/message_catalog.json
(kodek: backend/s2cmsg.py). Bu modul o katalogdan self-contained bir HTML/MD
sayfasi uretir: baslik formati, sayac/yanit-biti/resync kurallari, hata
kodlari, mesaj tablosu ve her govde sablonunun alan tablosu. Icerik KATALOGDAN
turetilir — yeni bir mesaj eklenince (message_catalog.json'a) YATT elle
dokunulmadan buyur; sabit mesaj listesi/alan tablosu Python kodunda YOK.

Govde sablon alan tanimlari (offset/tip/boy/aciklama) tek sozluk sabitinde
yasar: ``_BODY_LAYOUTS``. Bu yerlesimler
docs/superpowers/plans/2026-07-09-s2cmsg-cit-yatt.md "Mesaj govde
yerlesimleri" bolumunden AYNEN alinmistir; backend/cit.py decode_board_cit
ile CIT yerlesimi tutarlidir (bkz. _cit_layout_rows).

Manifest verilirse (opsiyonel zenginlestirme): cihaz tablosu (devices[]) ve
CIT olcum tablosu + SBoardCit yerlesimi N'e gore hesaplanmis offset'lerle.

Determinizm: uretim tarihi/timestamp YOK — testler sabit cikti bekler; surum
bilgisi olarak katalog CRC32 yeterli.
"""
from __future__ import annotations

import html as html_mod
import json

from backend.s2cmsg import HEADER_SIZE, MAX_BODY, RESPONSE_BIT, STATUS_LABELS, catalog_crc32

# --- Govde sablonlari: TEK sozluk sabiti (yeni sablon eklenince burasi buyur) --- #

_BODY_LAYOUTS: dict[str, list[dict]] = {
    "request_std": [
        {"offset": 0, "size": 4, "name": "uiCihazIndeks", "type": "u32",
         "note": "manifest devices[] sirasi; cihazsiz mesajda 0xFFFFFFFF (NO_DEVICE)"},
        {"offset": 4, "size": 4, "name": "uiRegisterAdres", "type": "u32", "note": "reg_addr; yoksa 0"},
        {"offset": 8, "size": 4, "name": "uiAdres", "type": "u32", "note": "address; yoksa 0"},
        {"offset": 12, "size": 4, "name": "uiUzunluk", "type": "u32", "note": "length; yoksa 0"},
        {"offset": 16, "size": 4, "name": "uiDeger", "type": "u32", "note": "value"},
        {"offset": 20, "size": 4, "name": "uiDegerVar", "type": "u32", "note": "0/1 — uiDeger gecerli mi"},
        {"offset": 24, "size": 4, "name": "uiVeriBoyu", "type": "u32", "note": "N (<=256)"},
        {"offset": 28, "size": None, "name": "veri", "type": "u8[N]+pad4", "note": "N bayt veri, 4'e tamamlanir"},
    ],
    "response_std": [
        {"offset": 0, "size": 4, "name": "uiIstekSayac", "type": "u32", "note": "istegin uiMesajSayac'i"},
        {"offset": 4, "size": 4, "name": "uiDurum", "type": "u32", "note": "0 OK / hata tablosu (asagida)"},
        {"offset": 8, "size": 4, "name": "iCihazDurum", "type": "i32", "note": "ajan iStatus ham (imzali)"},
        {"offset": 12, "size": 4, "name": "uiDeger", "type": "u32", "note": "islenmis/birimli deger"},
        {"offset": 16, "size": 4, "name": "uiVeriBoyu", "type": "u32", "note": "N — veri alaninin boyu"},
        {"offset": 20, "size": None, "name": "veri", "type": "u8[N]+pad4", "note": "N bayt veri, 4'e tamamlanir"},
        {"offset": None, "size": 4, "name": "uiMetinBoyu", "type": "u32",
         "note": "M — 20+pad4(N) offsetinde (degiskene bagli)"},
        {"offset": None, "size": None, "name": "metin", "type": "utf8[M]+pad4",
         "note": "tani metni (cArrMessage), 4'e tamamlanir"},
    ],
    "trace": [
        {"offset": 0, "size": 4, "name": "uiSeviye", "type": "u32", "note": "trace seviyesi"},
        {"offset": 4, "size": 4, "name": "uiMetinBoyu", "type": "u32", "note": "M"},
        {"offset": 8, "size": None, "name": "metin", "type": "utf8[M]+pad4", "note": "log satiri, 4'e tamamlanir"},
    ],
    "cit": [
        {"offset": 0, "size": 4, "name": "uiIstekSayac", "type": "u32", "note": "istegin uiMesajSayac'i"},
        {"offset": 4, "size": 4, "name": "uiDurum", "type": "u32", "note": "0 OK / hata tablosu (asagida)"},
        {"offset": 8, "size": 4, "name": "uiSayac", "type": "u32", "note": "SBoardCit.uiSayac — kosu sayaci"},
        {"offset": 12, "size": 4, "name": "uiZaman", "type": "u32",
         "note": "SBoardCit.uiZaman — v1'de 0 (ms-tick kaynagi yok)"},
        {"offset": 16, "size": None, "name": "bayrak_words", "type": "u32[ceil(N/32)]",
         "note": "OKUMA-BASARILI bit alani (limit DEGIL); bit i = olcum i (LSB-first); ((N+31)/32)*4 bayt"},
        {"offset": None, "size": None, "name": "arrOlcum[N]", "type": "SBoardCitOlcum[N]",
         "note": "her biri {iDeger i32, uiHam u32, uiDurum u32} = 12 bayt/olcum"},
    ],
}

def body_layouts_json() -> dict[str, list[dict]]:
    """``_BODY_LAYOUTS``in JSON-dostu genel kopyasi (routes.py buradan okur).

    Frontend'in govde sablon alan tablolarini backend'den tek kaynaktan
    almasi icin: routes.py ozel `_BODY_LAYOUTS` adini degil bu fonksiyonu
    kullanir. Sozluk/liste zaten JSON-serilestirilebilir (str/int/None) —
    burada sadece sig (shallow) kopyalanir ki caginin _BODY_LAYOUTS'u yerinde
    mutasyona ugratmasi bu modulun ic durumunu bozmasin.
    """
    return {name: [dict(field) for field in fields] for name, fields in _BODY_LAYOUTS.items()}


#: SBoardCitOlcum tek elemaninin alt-alanlari (CIT olcum tablosu yerlesim
#: satirlari icin; backend/cit.py _OLCUM_SIZE=12 ile birebir).
_CIT_OLCUM_FIELDS = [
    {"name": "iDeger", "type": "i32", "size": 4, "note": "islenmis/birimli deger (int32)"},
    {"name": "uiHam", "type": "u32", "size": 4, "note": "ham okuma (yanit data ilk 4B / uiValue)"},
    {"name": "uiDurum", "type": "u32", "size": 4, "note": "0 OK / hata tablosu (asagida)"},
]

_HEADER_FIELD_NOTES = {
    "uiMesajKomut": "yanit biti bit31 (RESPONSE_BIT=0x80000000); ust 2 bayt imza 0x5343 (istek) / 0xD343 (LE yazimda .. .. 43 53 / .. .. 43 D3)",
    "uiMesajBoyu": f"govde boyu, bayt; <= {MAX_BODY} ve 4'un kati; asilirsa/bolunmezse senkron kaybi -> resync",
    "uiMesajSayac": "yon basina 1'den monoton (istek sayaci ayri, yanit sayaci ayri sayilir)",
}

_DIR_LABELS = {"req": "istek/yanıt", "unsolicited": "kendiliğinden (yanıt öneki yok)"}

_NOTES_MD = """## Notlar / Kısıtlar (v1)

- **Endian:** little-endian (tüm alanlar LE).
- **Bit-alanı yerleşimi:** GCC/ARM-EABI varsayımı (LSB-first) — CIT bayrak
  kelimelerinde bit *i* = ölçüm *i* (`word[i//32] & (1<<(i%32))`).
- **`uiZaman` (CIT):** v1'de her zaman 0 — kartta ms-tick kaynağı yok.
- **`BUS_HATASI` (uiDurum=5):** ham cihaz `iStatus` CIT ölçümünde TAŞINMAZ;
  yalnızca standart yanıtın `iCihazDurum` alanında görülür.
- **Limit / OK-NOK HOST'ta:** kart CIT'te limit GÖMMEZ — her ölçümü okur, `iDeger`
  + `uiHam` + `uiDurum` (okuma başarısı) döner; bayrak biti = okuma başarısı. Min/max
  limitini, önem ve aç/kapa kararını CIT ekranı canlı uygular; limit değiştirmek için
  kod üretmek/yeniden yüklemek GEREKMEZ.
- **CRC/magic:** v1'de mesaj çerçevesinde CRC ya da magic YOK; dayanıklılık
  resync deseniyle sağlanır (imza + boy doğrulaması, 1 bayt kaydırmalı arama).
"""


def _format_field_offset(field: dict) -> str:
    return str(field["offset"]) if field["offset"] is not None else "değişken"


def _format_field_size(field: dict) -> str:
    return str(field["size"]) if field["size"] is not None else "değişken (N/M'e bağlı)"


def _response_body_name(body: str) -> str:
    """Bir mesajin YANIT govde sablonu adi (katalogdaki `body` istek sablonudur)."""
    if body == "trace":
        return "trace"  # kendiliginden; ayri yanit yok
    if body == "cit":
        return "cit"
    return "response_std"


def _cit_layout_rows(n: int) -> list[dict]:
    """N olcume gore SBoardCit yerlesimini offset'leri hesaplanmis satirlara cevirir.

    backend/cit.py decode_board_cit ile birebir: _PREFIX_SIZE(8) +
    _CIT_HEADER_SIZE(8) + flag_words + n*_OLCUM_SIZE(12).
    """
    flag_words = ((n + 31) // 32) * 4
    rows = [
        {"offset": 0, "size": 4, "name": "uiIstekSayac", "type": "u32", "note": "SYanitOnek"},
        {"offset": 4, "size": 4, "name": "uiDurum", "type": "u32", "note": "SYanitOnek"},
        {"offset": 8, "size": 4, "name": "uiSayac", "type": "u32", "note": "SBoardCit"},
        {"offset": 12, "size": 4, "name": "uiZaman", "type": "u32", "note": "SBoardCit — v1'de 0"},
        {"offset": 16, "size": flag_words, "name": "bayrak_words",
         "type": f"u32[{(n + 31) // 32}]", "note": f"((N+31)/32)*4 = {flag_words} bayt (N={n})"},
    ]
    olcum_off = 16 + flag_words
    for i in range(n):
        rows.append({
            "offset": olcum_off + i * 12, "size": 12, "name": f"arrOlcum[{i}]",
            "type": "SBoardCitOlcum", "note": "iDeger(i32)+uiHam(u32)+uiDurum(u32)",
        })
    return rows


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #

def _esc(value) -> str:
    return html_mod.escape(str(value))


def _status_chip_class(code) -> str:
    """Hata kodu cipi ton sinifi: 0 -> ok (yesil), 5/6 -> hata (kirmizi), digeri notr."""
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "chip-notr"
    if c == 0:
        return "chip-ok"
    if c in (5, 6):
        return "chip-hata"
    return "chip-notr"


def _dir_badge_html(direction: str) -> str:
    """Mesaj yonu rozeti: istek/yanit (amber) veya kendiliginden (teal)."""
    if direction == "unsolicited":
        return '<span class="dir-badge dir-unsolicited">kendiliğinden</span>'
    if direction == "req":
        return '<span class="dir-badge dir-req">istek/yanıt</span>'
    return f'<span class="dir-badge">{_esc(direction)}</span>'


def _severity_badge_html(severity: str) -> str:
    """CIT onem rozeti: critical (kirmizi-ton), warning (amber), digeri notr."""
    sev = (severity or "").lower()
    if sev == "critical":
        return '<span class="sev-badge sev-critical">critical</span>'
    if sev == "warning":
        return '<span class="sev-badge sev-warning">warning</span>'
    if severity:
        return f'<span class="sev-badge">{_esc(severity)}</span>'
    return '<span class="sev-badge sev-yok">—</span>'


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body_rows = "\n".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n{body_rows}\n</tbody>\n</table>'


#: Bayt-serit segmentleri icin donen renk sirasi (bakir / teal / arduvaz).
_SERIT_TONLARI = ["ton-bakir", "ton-teal", "ton-arduvaz"]


def _bayt_serit_html(fields: list[dict]) -> str:
    """Datasheet tarzi yatay bayt-yerlesim diyagrami (saf HTML/CSS, deterministik).

    Her alan bir renkli segment: sabit-boy alanlar bayt sayisina orantili
    flex-grow ile; degisken alanlar (size=None) sabit-esli hatch'li 'N bayt'
    segmenti. Segment ustunde baslangic offset'i, icinde alan adi + boyu.
    Ofset None (degiskene bagli) ise '·' gosterilir. Tablonun gorsel ozeti;
    print'te de calisir (flex).
    """
    segs: list[str] = []
    for i, f in enumerate(fields):
        ton = _SERIT_TONLARI[i % len(_SERIT_TONLARI)]
        size = f.get("size")
        degisken = size is None
        # flex-grow: sabit alanlar bayt oranli; degisken alan sabit genis pay.
        grow = size if (size is not None and size > 0) else 4
        off = f.get("offset")
        off_txt = str(off) if off is not None else "·"
        if degisken:
            boy_txt = "N bayt · pad4"
            ekstra = " serit-degisken"
        else:
            boy_txt = f"{size} B"
            ekstra = ""
        segs.append(
            f'<div class="serit-seg {ton}{ekstra}" style="flex-grow:{grow}">'
            f'<span class="serit-off">{_esc(off_txt)}</span>'
            f'<span class="serit-ad mono">{_esc(f["name"])}</span>'
            f'<span class="serit-boy">{_esc(boy_txt)}</span>'
            f'</div>'
        )
    return f'<div class="yatt-bayt-serit">\n' + "\n".join(segs) + '\n</div>'


def _body_layout_table_html(body_name: str, layout: list[dict]) -> str:
    rows = [
        [_esc(_format_field_offset(f)), f'<span class="mono">{_esc(f["name"])}</span>',
         _esc(f["type"]), _esc(_format_field_size(f)), _esc(f.get("note", ""))]
        for f in layout
    ]
    table = _html_table(["offset", "alan", "tip", "boy", "açıklama"], rows)
    serit = _bayt_serit_html(layout)
    return (
        f'<div class="body-layout" id="govde-{_esc(body_name)}">\n'
        f'<h4 class="mono">{_esc(body_name)}</h4>\n{serit}\n<div class="tablo-sar">{table}</div>\n</div>'
    )


def build_yatt_html(catalog: dict, manifest: dict | None) -> str:
    """Katalogdan self-contained (inline CSS, harici kaynak yok) HTML YATT sayfasi uretir."""
    messages = sorted(catalog["messages"], key=lambda m: int(m["id"], 16))
    header_fields = catalog["header"]
    status_codes = catalog.get("status_codes") or {str(k): v for k, v in STATUS_LABELS.items()}
    crc = catalog_crc32()

    # Baslik formati: bayt-serit diyagrami + tablo
    header_serit = _bayt_serit_html(
        [{"offset": i * 4, "size": 4, "name": f["name"]} for i, f in enumerate(header_fields)]
    )
    header_rows = [
        [f'<span class="mono">{_esc(f["name"])}</span>', _esc(f["type"]),
         _esc(_HEADER_FIELD_NOTES.get(f["name"], ""))]
        for f in header_fields
    ]
    header_table = _html_table(["alan", "tip", "not"], header_rows)

    # Hata kodu cip izgarasi (kod + etiket; 0 yesil-ton, 5/6 kirmizi-ton)
    status_chips = "\n".join(
        f'<div class="status-chip {_status_chip_class(code)}">'
        f'<span class="mono status-kod">{_esc(code)}</span>'
        f'<span class="status-ad">{_esc(label)}</span></div>'
        for code, label in sorted(status_codes.items(), key=lambda kv: int(kv[0]))
    )
    status_html = f'<div class="chip-izgara">\n{status_chips}\n</div>'

    # Mesaj tablosu
    message_rows = []
    for m in messages:
        direction = m.get("dir", "")
        response_body = _response_body_name(m["body"])
        body_desc = m["body"] if m["body"] == response_body else f'{m["body"]} → {response_body}'
        message_rows.append([
            f'<span class="mono id-cip">{_esc(m["id"])}</span>',
            f'<span class="mono">{_esc(m["name"])}</span>',
            _dir_badge_html(direction),
            f'<a class="mono govde-link" href="#govde-{_esc(m["body"])}">{_esc(body_desc)}</a>',
            _esc(m.get("aciklama", "")),
        ])
    message_table = _html_table(["ID", "ad", "yön", "gövde şablonu", "açıklama"], message_rows)

    # Govde sablon alan tablolari (kullanilan tum sablonlar, katalog sirasindan bagimsiz sabit sira)
    used_bodies: list[str] = []
    for name in list(_BODY_LAYOUTS.keys()):
        if name in {m["body"] for m in messages} or name in {_response_body_name(m["body"]) for m in messages}:
            used_bodies.append(name)
    body_layout_sections = "\n".join(_body_layout_table_html(name, _BODY_LAYOUTS[name]) for name in used_bodies)

    # Manifest zenginlestirme: cihaz tablosu + CIT
    manifest_html = ""
    if manifest:
        devices = manifest.get("devices") or []
        if devices:
            device_rows = [
                [_esc(i), f'<span class="mono">{_esc(d.get("id", ""))}</span>', _esc(d.get("part", ""))]
                for i, d in enumerate(devices)
            ]
            device_table = _html_table(["indeks", "id", "part"], device_rows)
            manifest_html += f'<section id="cihaz-tablosu">\n<h3>Cihaz tablosu (manifest devices[])</h3>\n<div class="tablo-sar">{device_table}</div>\n</section>\n'

        cit_section = manifest.get("cit") or {}
        olcumler = cit_section.get("olcumler") or []
        if olcumler:
            def _limit_cell(v) -> str:
                return f'<span class="mono">{_esc(v)}</span>' if v is not None else '<span class="limitsiz">—</span>'
            cit_rows = [
                [f'<span class="mono bit-cip">{_esc(o.get("index", i))}</span>',
                 f'<span class="mono">{_esc(o.get("cname", ""))}</span>',
                 _esc(o.get("name", "")),
                 _esc(o.get("unit") or "—"),
                 _limit_cell(o.get("min")),
                 _limit_cell(o.get("max")),
                 _severity_badge_html(o.get("severity", ""))]
                for i, o in enumerate(olcumler)
            ]
            cit_table = _html_table(["bit i", "cname", "ad", "birim", "min", "max", "önem"], cit_rows)

            n = len(olcumler)
            layout_fields = _cit_layout_rows(n)
            cit_serit = _bayt_serit_html(layout_fields)
            layout_rows = [
                [_esc(_format_field_offset(f)), f'<span class="mono">{_esc(f["name"])}</span>',
                 _esc(f["type"]), _esc(_format_field_size(f)), _esc(f.get("note", ""))]
                for f in layout_fields
            ]
            layout_table = _html_table(["offset", "alan", "tip", "boy", "açıklama"], layout_rows)

            manifest_html += (
                f'<section id="cihazlar-cit">\n<h3>CİT ölçüm tablosu (N={_esc(n)})</h3>\n<div class="tablo-sar">{cit_table}</div>\n'
                f'<h4>SBoardCit yerleşimi (hesaplanmış offset)</h4>\n'
                f'<div class="body-layout">\n{cit_serit}\n<div class="tablo-sar">{layout_table}</div>\n</div>\n</section>\n'
            )

        manifest_crc = manifest.get("message_catalog_crc32")
        if manifest_crc is not None:
            manifest_hex = manifest_crc if isinstance(manifest_crc, str) else f"0x{int(manifest_crc):08X}"
            manifest_html += (
                f'<p class="mono">manifest message_catalog_crc32: {_esc(manifest_hex)}</p>\n'
            )

    contract_crc_hex = f"0x{crc:08X}"

    # Proje adi (manifest'ten, varsa) — hero altbasligi.
    project_name = ""
    if manifest:
        project_name = (
            manifest.get("project_name") or manifest.get("proje_adi")
            or manifest.get("name") or manifest.get("project") or ""
        )

    # Notlar: her maddeyi inceltilmis bakir sol-cizgili callout kart yap.
    # **kalin** vurgular <strong>'a cevrilir (deterministik, dis kutuphane yok).
    def _md_inline(text: str) -> str:
        parts = text.split("**")
        out = []
        for i, p in enumerate(parts):
            out.append(f"<strong>{_esc(p)}</strong>" if i % 2 == 1 else _esc(p))
        return "".join(out)

    note_cards = "\n".join(
        f'<div class="callout">{_md_inline(line.lstrip("- ").strip())}</div>'
        for line in _NOTES_MD.splitlines()
        if line.startswith("- ")
    )
    notes_html = f'<div class="callout-list">\n{note_cards}\n</div>'

    # Sol TOC (Bolumler). Manifest yoksa Cihazlar/CIT baglantisi gizlenir.
    notes_no = "6" if manifest_html else "5"
    toc_items = [
        ("#genel-kurallar", "1", "Genel Kurallar"),
        ("#baslik", "2", "Başlık formatı"),
        ("#hata-kodlari", "3", "Hata kodları"),
        ("#mesaj-katalogu", "4", "Mesaj kataloğu"),
        ("#govde-yerlesimleri", "4·b", "Gövde yerleşimleri"),
    ]
    if manifest_html:
        toc_items.append(("#cihazlar-cit-kok", "5", "Cihazlar / CİT"))
    toc_items.append(("#notlar", notes_no, "Notlar / Kısıtlar"))
    toc_html = "\n".join(
        f'<a class="toc-link" href="{href}"><span class="toc-no mono">{_esc(no)}</span>{_esc(label)}</a>'
        for href, no, label in toc_items
    )

    project_badge = (
        f'<span class="hero-badge badge-proje">{_esc(project_name)}</span>' if project_name else ""
    )

    manifest_section = (
        f'<section id="cihazlar-cit-kok"><h2>5. Manifest zenginleştirmesi</h2>{manifest_html}</section>'
        if manifest_html else ''
    )

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>YATT — S2C-MSG Yazılım Arayüzü Tanımlama Tablosu</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #0b1216; --bg-2: #0e161b; --panel: #101a20; --panel-2: #0d151a;
    --hair: #1c2a31; --hair-2: #24343c;
    --ink: #cdd8de; --ink-dim: #7f929e; --ink-faint: #5d6f7a;
    --copper: #d08c3c; --copper-dim: #a97431; --copper-bg: #251a0e; --copper-line: #4a3316;
    --teal: #3fb4a8; --teal-bg: #0e2320; --teal-line: #1c453f;
    --slate: #5a7686; --slate-bg: #131e25;
    --ok: #5cc98a; --ok-bg: #0f231a; --ok-line: #1f4531;
    --err: #e0736a; --err-bg: #2a1413; --err-line: #4d201d;
    --amber: #e0a24a; --amber-bg: #271c0c; --amber-line: #4a3517;
    --mono: 'Cascadia Mono', 'Consolas', ui-monospace, 'SFMono-Regular', monospace;
    --sans: 'Segoe UI', 'Inter', system-ui, -apple-system, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  html {{ scroll-behavior: smooth; }}
  body {{ font-family: var(--sans); margin: 0; background: var(--bg); color: var(--ink);
          line-height: 1.55; font-size: 14px;
          background-image: radial-gradient(1100px 500px at 80% -10%, #0f1c22 0%, transparent 60%); }}
  .shell {{ display: grid; grid-template-columns: 232px minmax(0, 1fr); gap: 40px;
            max-width: 1180px; margin: 0 auto; padding: 0 28px 96px; align-items: start; }}
  main {{ min-width: 0; max-width: 1100px; padding-top: 34px; }}

  /* --- Sol TOC --- */
  nav.toc {{ position: sticky; top: 0; align-self: start; height: 100vh; overflow-y: auto;
             padding: 34px 0 24px; }}
  .toc-baslik {{ font-size: 10.5px; letter-spacing: 0.14em; text-transform: uppercase;
                 color: var(--copper-dim); font-weight: 600; padding: 0 10px 10px;
                 border-bottom: 1px solid var(--hair); margin-bottom: 8px; }}
  .toc-link {{ display: flex; align-items: baseline; gap: 9px; padding: 7px 10px; border-radius: 7px;
              color: var(--ink-dim); text-decoration: none; font-size: 13px; border-left: 2px solid transparent; }}
  .toc-link:hover {{ background: var(--panel); color: var(--ink); border-left-color: var(--copper); }}
  .toc-no {{ font-size: 10.5px; color: var(--copper-dim); min-width: 26px; }}

  /* --- Hero --- */
  .hero {{ border: 1px solid var(--hair-2); border-radius: 14px; padding: 26px 28px;
           background: linear-gradient(150deg, #101c22 0%, #0c151a 60%);
           position: relative; overflow: hidden; }}
  .hero::before {{ content: ""; position: absolute; inset: 0;
                   background-image:
                     linear-gradient(var(--hair) 1px, transparent 1px),
                     linear-gradient(90deg, var(--hair) 1px, transparent 1px);
                   background-size: 26px 26px; opacity: 0.28;
                   -webkit-mask-image: radial-gradient(420px 200px at 88% 12%, #000 0%, transparent 72%);
                           mask-image: radial-gradient(420px 200px at 88% 12%, #000 0%, transparent 72%); }}
  .hero > * {{ position: relative; }}
  .hero .kicker {{ font-family: var(--mono); font-size: 11px; letter-spacing: 0.16em;
                   text-transform: uppercase; color: var(--copper); margin-bottom: 8px; }}
  h1 {{ font-size: 26px; margin: 0 0 6px; letter-spacing: -0.01em; font-weight: 650; color: #eaf1f5; }}
  h1 .h1-mono {{ font-family: var(--mono); color: var(--copper); font-weight: 600; }}
  .hero .sub {{ color: var(--ink-dim); font-size: 13.5px; margin: 0 0 16px; max-width: 62ch; }}
  .hero-badges {{ display: flex; flex-wrap: wrap; gap: 9px; }}
  .hero-badge {{ display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px; border-radius: 8px;
                 font-family: var(--mono); font-size: 12px; border: 1px solid var(--hair-2); background: var(--panel-2); color: var(--ink-dim); }}
  .badge-crc {{ border-color: var(--copper-line); background: var(--copper-bg); color: #e8b878; }}
  .badge-crc::before {{ content: "▮"; color: var(--copper); font-size: 10px; }}
  .badge-say {{ border-color: var(--teal-line); background: var(--teal-bg); color: #8fd8ce; }}
  .badge-proje {{ border-color: var(--hair-2); color: var(--ink); }}

  /* --- Basliklar --- */
  h2 {{ font-size: 17px; margin: 46px 0 4px; padding-bottom: 8px; font-weight: 620; color: #e6eef2;
        border-bottom: 1px solid var(--hair); position: relative; }}
  h2::before {{ content: ""; position: absolute; left: 0; bottom: -1px; width: 46px; height: 2px; background: var(--copper); }}
  h3 {{ font-size: 14px; margin: 26px 0 6px; color: #a9bccb; font-weight: 600; }}
  h4 {{ font-size: 11px; margin: 20px 0 8px; color: var(--ink-dim); text-transform: uppercase;
        letter-spacing: 0.07em; font-weight: 600; }}
  p {{ font-size: 13.5px; color: #b7c4cd; }}

  .mono {{ font-family: var(--mono); }}
  a {{ color: var(--teal); }}

  /* --- Tablolar --- */
  .tablo-sar {{ overflow-x: auto; border: 1px solid var(--hair); border-radius: 10px; margin: 12px 0 6px; background: var(--panel-2); }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12.5px; }}
  thead th {{ position: sticky; top: 0; background: #0f1a20; z-index: 1; }}
  th, td {{ border-bottom: 1px solid var(--hair); padding: 8px 12px; text-align: left; vertical-align: top; }}
  th {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-dim);
        font-weight: 600; border-bottom: 1px solid var(--hair-2); }}
  tbody tr:last-child td {{ border-bottom: none; }}
  tbody tr:nth-child(even) {{ background: rgba(255,255,255,0.014); }}
  tbody tr:hover {{ background: rgba(208,140,60,0.06); }}

  .id-cip {{ display: inline-block; padding: 2px 7px; border-radius: 5px; background: #0c1519;
             border: 1px solid var(--hair-2); color: #e8b878; font-size: 12px; }}
  .bit-cip {{ display: inline-block; min-width: 22px; text-align: center; padding: 1px 6px; border-radius: 5px;
              background: #0c1519; border: 1px solid var(--hair-2); color: var(--teal); }}
  a.govde-link {{ color: var(--ink); text-decoration: none; border-bottom: 1px dotted var(--slate); }}
  a.govde-link:hover {{ color: var(--teal); border-bottom-color: var(--teal); }}
  .limitsiz {{ color: var(--ink-faint); }}

  /* --- Yon / onem rozetleri --- */
  .dir-badge, .sev-badge {{ display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px;
                            font-weight: 600; border: 1px solid var(--hair-2); white-space: nowrap; }}
  .dir-req {{ color: #e8b878; background: var(--copper-bg); border-color: var(--copper-line); }}
  .dir-unsolicited {{ color: #8fd8ce; background: var(--teal-bg); border-color: var(--teal-line); }}
  .sev-critical {{ color: #eea099; background: var(--err-bg); border-color: var(--err-line); }}
  .sev-warning {{ color: #e6b877; background: var(--amber-bg); border-color: var(--amber-line); }}
  .sev-yok {{ color: var(--ink-faint); border-color: var(--hair); background: transparent; }}

  /* --- Hata kodu cip izgarasi --- */
  .chip-izgara {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin: 14px 0 6px; }}
  .status-chip {{ display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 9px;
                  border: 1px solid var(--hair-2); background: var(--panel-2); }}
  .status-kod {{ min-width: 20px; text-align: center; font-weight: 700; font-size: 13px; }}
  .status-ad {{ font-size: 12.5px; color: var(--ink); }}
  .chip-ok {{ border-color: var(--ok-line); background: var(--ok-bg); }}
  .chip-ok .status-kod {{ color: var(--ok); }}
  .chip-hata {{ border-color: var(--err-line); background: var(--err-bg); }}
  .chip-hata .status-kod {{ color: var(--err); }}
  .chip-notr .status-kod {{ color: var(--copper); }}

  /* --- Bayt-yerlesim seridi (datasheet ruler) --- */
  .body-layout {{ margin: 16px 0 34px; padding: 16px 18px; border: 1px solid var(--hair-2);
                  border-radius: 12px; background: var(--panel); }}
  .body-layout > h4 {{ margin-top: 0; color: #e8b878; letter-spacing: 0.02em; text-transform: none; font-size: 12.5px; }}
  .yatt-bayt-serit {{ display: flex; align-items: stretch; gap: 3px; margin: 6px 0 16px;
                      padding: 22px 0 4px; min-height: 76px; }}
  .serit-seg {{ position: relative; flex-basis: 0; min-width: 62px; border-radius: 6px; padding: 8px 8px 7px;
                display: flex; flex-direction: column; justify-content: center; gap: 3px;
                border: 1px solid var(--hair-2); overflow: hidden; }}
  .serit-off {{ position: absolute; top: -18px; left: 0; font-family: var(--mono); font-size: 10px; color: var(--ink-faint); }}
  .serit-ad {{ font-size: 11.5px; color: var(--ink); word-break: break-word; line-height: 1.25; }}
  .serit-boy {{ font-size: 9.5px; color: var(--ink-dim); font-family: var(--mono); letter-spacing: 0.02em; }}
  .ton-bakir {{ background: linear-gradient(180deg, #2a1d0d, #1c1409); border-color: var(--copper-line); }}
  .ton-bakir .serit-ad {{ color: #f0c384; }}
  .ton-teal {{ background: linear-gradient(180deg, #10241f, #0c1a17); border-color: var(--teal-line); }}
  .ton-teal .serit-ad {{ color: #9adcd1; }}
  .ton-arduvaz {{ background: linear-gradient(180deg, #15222a, #0f1a20); border-color: var(--hair-2); }}
  .ton-arduvaz .serit-ad {{ color: #bcccd6; }}
  .serit-degisken {{ flex-grow: 4; min-width: 96px;
    background-image: repeating-linear-gradient(45deg, rgba(208,140,60,0.16) 0 7px, rgba(0,0,0,0) 7px 14px);
    border-style: dashed; }}

  /* --- Callout notlar --- */
  .callout-list {{ display: flex; flex-direction: column; gap: 10px; margin: 14px 0 6px; }}
  .callout {{ padding: 11px 15px; border-left: 3px solid var(--copper); border-radius: 0 8px 8px 0;
              background: var(--panel-2); font-size: 13px; color: #bcc8d0; }}
  .callout strong {{ color: #e8b878; font-weight: 650; }}

  footer {{ margin-top: 52px; font-size: 11.5px; color: var(--ink-faint); border-top: 1px solid var(--hair);
            padding-top: 16px; }}
  footer .mono {{ color: var(--ink-dim); }}

  @media (max-width: 860px) {{
    .shell {{ grid-template-columns: 1fr; gap: 0; padding: 0 18px 64px; }}
    nav.toc {{ position: static; height: auto; padding: 20px 0 4px; }}
  }}

  /* --- Print: acik tema, formal PDF --- */
  @media print {{
    body {{ background: #fff; color: #16202a; background-image: none; }}
    .shell {{ display: block; max-width: none; padding: 0; }}
    nav.toc {{ display: none; }}
    main {{ max-width: none; padding-top: 0; }}
    .hero {{ background: #fff; border-color: #c9d3da; }}
    .hero::before {{ display: none; }}
    .hero .kicker, h2::before {{ color: #9a6a24; }}
    h1, h2, h3, h4 {{ color: #10202c; }}
    h1 .h1-mono {{ color: #9a6a24; }}
    .sub, p, .serit-boy, .toc-no {{ color: #4a5560; }}
    .tablo-sar, .body-layout, .status-chip, .hero-badge {{ background: #fff; border-color: #c9d3da; }}
    th, td {{ border-color: #d6dee4; color: #1a2732; }}
    th {{ color: #55636e; }}
    tbody tr:hover, tbody tr:nth-child(even) {{ background: #f4f6f8; }}
    .id-cip, .bit-cip {{ background: #f2f5f7; border-color: #cdd7dd; color: #7a4f16; }}
    .serit-ad, .ton-bakir .serit-ad, .ton-teal .serit-ad, .ton-arduvaz .serit-ad {{ color: #16202a; }}
    .ton-bakir {{ background: #f7edda; }} .ton-teal {{ background: #e2f2ef; }} .ton-arduvaz {{ background: #eef2f5; }}
    .callout {{ background: #faf7f1; color: #2a3641; border-left-color: #b8842f; }}
    .callout strong {{ color: #8a5a1c; }}
    .body-layout, .tablo-sar, .yatt-bayt-serit, .chip-izgara, section {{ page-break-inside: avoid; break-inside: avoid; }}
    h2, h3, h4 {{ page-break-after: avoid; }}
  }}
</style>
</head>
<body>
<div class="shell">
<nav class="toc" aria-label="Bölümler">
<div class="toc-baslik">Bölümler</div>
{toc_html}
</nav>
<main>
<header class="hero">
  <div class="kicker">Yazılım Arayüz Tasarım Tanımı · S2C-MSG</div>
  <h1>YATT — <span class="h1-mono">S2C-MSG</span> Arayüzü</h1>
  <p class="sub">Spec2Code binary mesaj protokolü — kataloğun {_esc(len(messages))} mesajından deterministik üretildi. Bu doküman air-gapped, kendi kendine yeterlidir (harici kaynak yok).</p>
  <div class="hero-badges">
    {project_badge}
    <span class="hero-badge badge-crc">kontrat CRC32 · {_esc(contract_crc_hex)}</span>
    <span class="hero-badge badge-say">{_esc(len(messages))} mesaj</span>
  </div>
</header>

<section id="genel-kurallar">
<h2>1. Genel kurallar (çerçeveleme)</h2>
<p>Tüm alanlar <strong>little-endian</strong>. Yanıt ID = istek ID | 0x80000000 (RESPONSE_BIT, bit31). Resync: bayt akışında imza aranır
(<span class="mono">.. .. 43 53</span> istek / <span class="mono">.. .. 43 D3</span> yanıt, LE yazımda üst 2 bayt = 0x5343);
<span class="mono">uiMesajBoyu</span> &gt; {_esc(MAX_BODY)} ya da 4'e bölünmezse senkron kaybı sayılır, 1 bayt kaydırılıp arama sürer.</p>
</section>

<section id="baslik">
<h2>2. Başlık formatı (12 bayt, little-endian)</h2>
{header_serit}
<div class="tablo-sar">{header_table}</div>
</section>

<section id="hata-kodlari">
<h2>3. Hata kodları</h2>
{status_html}
</section>

<section id="mesaj-katalogu">
<h2>4. Mesaj kataloğu ({_esc(len(messages))} mesaj, ID'ye göre sıralı)</h2>
<div class="tablo-sar">{message_table}</div>
</section>

<section id="govde-yerlesimleri">
<h2>4·b. Gövde yerleşimleri</h2>
{body_layout_sections}
</section>

{manifest_section}

<section id="notlar">
<h2>{'6' if manifest_html else '5'}. Notlar / Kısıtlar (v1)</h2>
{notes_html}
</section>

<footer>Bu doküman <span class="mono">message_catalog.json</span> + manifest'ten otomatik üretilmiştir — elle düzenlemeyin. Sürüm = kontrat CRC32 <span class="mono">{_esc(contract_crc_hex)}</span> (üretim tarihi yok, deterministik).</footer>
</main>
</div>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #

def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_yatt_markdown(catalog: dict, manifest: dict | None) -> str:
    """Katalogdan Markdown YATT sayfasi uretir (build_yatt_html ile ayni icerik)."""
    messages = sorted(catalog["messages"], key=lambda m: int(m["id"], 16))
    header_fields = catalog["header"]
    status_codes = catalog.get("status_codes") or {str(k): v for k, v in STATUS_LABELS.items()}
    crc = catalog_crc32()
    contract_crc_hex = f"0x{crc:08X}"

    lines: list[str] = []
    lines.append("# YATT — S2C-MSG Yazılım Arayüzü Tanımlama Tablosu")
    lines.append("")
    lines.append(f"Spec2Code binary mesaj protokolü (S2C-MSG) — kataloğun {len(messages)} mesajından üretildi.")
    lines.append("")
    lines.append(f"**Kontrat CRC32:** `{contract_crc_hex}`")
    lines.append("")
    lines.append("## 1. Başlık formatı (12 bayt, little-endian)")
    lines.append("")
    lines.append(_md_table(
        ["alan", "tip", "not"],
        [[f["name"], f["type"], _HEADER_FIELD_NOTES.get(f["name"], "")] for f in header_fields],
    ))
    lines.append("")
    lines.append(
        "Yanıt ID = istek ID | 0x80000000 (RESPONSE_BIT, bit31). Resync: bayt akışında imza aranır "
        "(`.. .. 43 53` istek / `.. .. 43 D3` yanıt, LE yazımda üst 2 bayt = 0x5343); "
        f"`uiMesajBoyu` > {MAX_BODY} ya da 4'e bölünmezse senkron kaybı sayılır, 1 bayt kaydırılıp arama sürer."
    )
    lines.append("")
    lines.append("## 2. Hata kodları")
    lines.append("")
    lines.append(_md_table(
        ["kod", "etiket"],
        [[code, label] for code, label in sorted(status_codes.items(), key=lambda kv: int(kv[0]))],
    ))
    lines.append("")
    lines.append(f"## 3. Mesaj tablosu ({len(messages)} mesaj, ID'ye göre sıralı)")
    lines.append("")
    message_rows = []
    for m in messages:
        dir_label = _DIR_LABELS.get(m.get("dir", ""), m.get("dir", ""))
        response_body = _response_body_name(m["body"])
        body_desc = m["body"] if m["body"] == response_body else f'{m["body"]} → {response_body}'
        message_rows.append([m["id"], m["name"], dir_label, body_desc, m.get("aciklama", "")])
    lines.append(_md_table(["ID", "ad", "yön", "gövde şablonu", "açıklama"], message_rows))
    lines.append("")
    lines.append("## 4. Gövde şablonları")
    lines.append("")
    used_bodies: list[str] = []
    for name in list(_BODY_LAYOUTS.keys()):
        if name in {m["body"] for m in messages} or name in {_response_body_name(m["body"]) for m in messages}:
            used_bodies.append(name)
    for body_name in used_bodies:
        layout = _BODY_LAYOUTS[body_name]
        lines.append(f"### `{body_name}`")
        lines.append("")
        lines.append(_md_table(
            ["offset", "alan", "tip", "boy", "açıklama"],
            [[_format_field_offset(f), f["name"], f["type"], _format_field_size(f), f.get("note", "")] for f in layout],
        ))
        lines.append("")

    section_no = 5
    if manifest:
        devices = manifest.get("devices") or []
        cit_section = manifest.get("cit") or {}
        olcumler = cit_section.get("olcumler") or []
        if devices or olcumler:
            lines.append(f"## {section_no}. Manifest zenginleştirmesi")
            lines.append("")
            section_no += 1
        if devices:
            lines.append("### Cihaz tablosu (manifest devices[])")
            lines.append("")
            lines.append(_md_table(
                ["indeks", "id", "part"],
                [[str(i), d.get("id", ""), d.get("part", "")] for i, d in enumerate(devices)],
            ))
            lines.append("")
        if olcumler:
            n = len(olcumler)
            lines.append(f"### CİT ölçüm tablosu (N={n})")
            lines.append("")
            lines.append(_md_table(
                ["bit i", "cname", "ad", "birim", "min", "max", "önem"],
                [[str(o.get("index", i)), o.get("cname", ""), o.get("name", ""),
                  str(o.get("unit") or "-"), str(o.get("min") if o.get("min") is not None else "-"),
                  str(o.get("max") if o.get("max") is not None else "-"), o.get("severity", "")]
                 for i, o in enumerate(olcumler)],
            ))
            lines.append("")
            lines.append("### SBoardCit yerleşimi (hesaplanmış offset)")
            lines.append("")
            lines.append(_md_table(
                ["offset", "alan", "tip", "boy", "açıklama"],
                [[_format_field_offset(f), f["name"], f["type"], _format_field_size(f), f.get("note", "")]
                 for f in _cit_layout_rows(n)],
            ))
            lines.append("")
        manifest_crc = manifest.get("message_catalog_crc32")
        if manifest_crc is not None:
            manifest_hex = manifest_crc if isinstance(manifest_crc, str) else f"0x{int(manifest_crc):08X}"
            lines.append(f"**Manifest `message_catalog_crc32`:** `{manifest_hex}`")
            lines.append("")

    lines.append(f"## {section_no}. Notlar / Kısıtlar")
    lines.append("")
    lines.append(_NOTES_MD.split("\n\n", 1)[1] if "\n\n" in _NOTES_MD else _NOTES_MD)
    lines.append("")
    lines.append("---")
    lines.append(
        "Spec2Code YATT v1 — `backend/data/message_catalog.json` kaynağından deterministik üretildi "
        "(üretim tarihi yok; sürüm = kontrat CRC32)."
    )
    lines.append("")

    return "\n".join(lines)
