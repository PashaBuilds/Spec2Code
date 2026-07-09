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
         "note": "OK/NOK bit alani; bit i = olcum i (LSB-first); ((N+31)/32)*4 bayt"},
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
    {"name": "uiHam", "type": "u32", "size": 4, "note": "ham okuma; devre disi olcumde 0"},
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
- **Devre dışı (disabled) ölçüm:** `uiHam=0` — CIT bayrak biti de kapalı kalır.
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


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{_esc(h)}</th>" for h in headers)
    body_rows = "\n".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f'<table>\n<thead><tr>{head}</tr></thead>\n<tbody>\n{body_rows}\n</tbody>\n</table>'


def _body_layout_table_html(body_name: str, layout: list[dict]) -> str:
    rows = [
        [_esc(_format_field_offset(f)), f'<span class="mono">{_esc(f["name"])}</span>',
         _esc(f["type"]), _esc(_format_field_size(f)), _esc(f.get("note", ""))]
        for f in layout
    ]
    table = _html_table(["offset", "alan", "tip", "boy", "açıklama"], rows)
    return f'<div class="body-layout" id="govde-{_esc(body_name)}">\n<h4 class="mono">{_esc(body_name)}</h4>\n{table}\n</div>'


def build_yatt_html(catalog: dict, manifest: dict | None) -> str:
    """Katalogdan self-contained (inline CSS, harici kaynak yok) HTML YATT sayfasi uretir."""
    messages = sorted(catalog["messages"], key=lambda m: int(m["id"], 16))
    header_fields = catalog["header"]
    status_codes = catalog.get("status_codes") or {str(k): v for k, v in STATUS_LABELS.items()}
    crc = catalog_crc32()

    # Baslik formati tablosu
    header_rows = [
        [f'<span class="mono">{_esc(f["name"])}</span>', _esc(f["type"]),
         _esc(_HEADER_FIELD_NOTES.get(f["name"], ""))]
        for f in header_fields
    ]
    header_table = _html_table(["alan", "tip", "not"], header_rows)

    # Hata kodu tablosu
    status_rows = [
        [f'<span class="mono">{_esc(code)}</span>', _esc(label)]
        for code, label in sorted(status_codes.items(), key=lambda kv: int(kv[0]))
    ]
    status_table = _html_table(["kod", "etiket"], status_rows)

    # Mesaj tablosu
    message_rows = []
    for m in messages:
        dir_label = _DIR_LABELS.get(m.get("dir", ""), _esc(m.get("dir", "")))
        response_body = _response_body_name(m["body"])
        body_desc = m["body"] if m["body"] == response_body else f'{m["body"]} → {response_body}'
        message_rows.append([
            f'<span class="mono">{_esc(m["id"])}</span>',
            f'<span class="mono">{_esc(m["name"])}</span>',
            _esc(dir_label),
            f'<a class="mono" href="#govde-{_esc(m["body"])}">{_esc(body_desc)}</a>',
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
            manifest_html += f'<section>\n<h3>Cihaz tablosu (manifest devices[])</h3>\n{device_table}\n</section>\n'

        cit_section = manifest.get("cit") or {}
        olcumler = cit_section.get("olcumler") or []
        if olcumler:
            cit_rows = [
                [_esc(o.get("index", i)), f'<span class="mono">{_esc(o.get("cname", ""))}</span>',
                 _esc(o.get("name", "")), _esc(o.get("unit") or "-"),
                 _esc(o.get("min") if o.get("min") is not None else "-"),
                 _esc(o.get("max") if o.get("max") is not None else "-"),
                 _esc(o.get("severity", ""))]
                for i, o in enumerate(olcumler)
            ]
            cit_table = _html_table(["bit i", "cname", "ad", "birim", "min", "max", "önem"], cit_rows)

            n = len(olcumler)
            layout_rows = [
                [_esc(_format_field_offset(f)), f'<span class="mono">{_esc(f["name"])}</span>',
                 _esc(f["type"]), _esc(_format_field_size(f)), _esc(f.get("note", ""))]
                for f in _cit_layout_rows(n)
            ]
            layout_table = _html_table(["offset", "alan", "tip", "boy", "açıklama"], layout_rows)

            manifest_html += (
                f'<section>\n<h3>CİT ölçüm tablosu (N={_esc(n)})</h3>\n{cit_table}\n'
                f'<h4>SBoardCit yerleşimi (hesaplanmış offset)</h4>\n{layout_table}\n</section>\n'
            )

        manifest_crc = manifest.get("message_catalog_crc32")
        if manifest_crc is not None:
            manifest_hex = manifest_crc if isinstance(manifest_crc, str) else f"0x{int(manifest_crc):08X}"
            manifest_html += (
                f'<p class="mono">manifest message_catalog_crc32: {_esc(manifest_hex)}</p>\n'
            )

    contract_crc_hex = f"0x{crc:08X}"

    # Basit ve deterministik MD->HTML: not listesini elle kur (dis kutuphane yok).
    notes_items = "\n".join(
        f"<li>{_esc(line.lstrip('- ').strip())}</li>"
        for line in _NOTES_MD.splitlines()
        if line.startswith("- ")
    )
    notes_html = f'<h3>Notlar / Kısıtlar (v1)</h3>\n<ul>\n{notes_items}\n</ul>'

    return f"""<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>YATT — S2C-MSG Yazılım Arayüzü Tanımlama Tablosu</title>
<style>
  :root {{ color-scheme: dark; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; margin: 0 auto; max-width: 1100px; padding: 32px 24px 64px;
          background: #0f1216; color: #d6dde3; line-height: 1.5; }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  h2 {{ font-size: 16px; margin-top: 40px; border-bottom: 1px solid #2a323b; padding-bottom: 6px; }}
  h3 {{ font-size: 14px; margin-top: 24px; color: #9fb3c8; }}
  h4 {{ font-size: 12px; margin-top: 18px; color: #8494a3; text-transform: uppercase; letter-spacing: 0.04em; }}
  .sub {{ color: #8494a3; font-size: 13px; margin-bottom: 20px; }}
  .badge {{ display: inline-block; padding: 3px 10px; border-radius: 999px; background: #16211a; color: #6fd88a;
            font-family: Consolas, monospace; font-size: 12px; border: 1px solid #234032; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin: 10px 0 4px; }}
  th, td {{ border-bottom: 1px solid #232a31; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #171c22; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: #8494a3; }}
  .mono {{ font-family: Consolas, monospace; }}
  a {{ color: #6fb0e0; }}
  a.mono {{ color: #d6dde3; text-decoration: none; border-bottom: 1px dotted #445; }}
  a.mono:hover {{ color: #6fb0e0; }}
  .body-layout {{ margin: 18px 0 30px; padding: 10px 14px; border: 1px solid #232a31; border-radius: 8px; background: #12161b; }}
  ul {{ font-size: 13px; }}
  section {{ margin-top: 18px; }}
  footer {{ margin-top: 40px; font-size: 11px; color: #62707d; border-top: 1px solid #232a31; padding-top: 12px; }}
  @media print {{ body {{ background: white; color: black; }} }}
</style>
</head>
<body>
<h1>YATT — S2C-MSG Yazılım Arayüzü Tanımlama Tablosu</h1>
<div class="sub">Spec2Code binary mesaj protokolü (S2C-MSG) — kataloğun {_esc(len(messages))} mesajından üretildi.</div>
<span class="badge">kontrat CRC32: {_esc(contract_crc_hex)}</span>

<h2>1. Başlık formatı (12 bayt, little-endian)</h2>
{header_table}
<p>Yanıt ID = istek ID | 0x80000000 (RESPONSE_BIT, bit31). Resync: bayt akışında imza aranır
(<span class="mono">.. .. 43 53</span> istek / <span class="mono">.. .. 43 D3</span> yanıt, LE yazımda üst 2 bayt = 0x5343);
<span class="mono">uiMesajBoyu</span> &gt; {_esc(MAX_BODY)} ya da 4'e bölünmezse senkron kaybı sayılır, 1 bayt kaydırılıp arama sürer.</p>

<h2>2. Hata kodları</h2>
{status_table}

<h2>3. Mesaj tablosu ({_esc(len(messages))} mesaj, ID'ye göre sıralı)</h2>
{message_table}

<h2>4. Gövde şablonları</h2>
{body_layout_sections}

{f'<h2>5. Manifest zenginleştirmesi</h2>{manifest_html}' if manifest_html else ''}

<h2>{'6' if manifest_html else '5'}. Notlar / Kısıtlar</h2>
{notes_html}

<footer>Spec2Code YATT v1 — backend/data/message_catalog.json kaynağından deterministik üretildi (üretim tarihi yok; sürüm = kontrat CRC32).</footer>
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
