"""Bağımlılıksız minimal XLSX oku/yaz — katı, tek sayfalı bir tablo için.

openpyxl/pandas YOK: ortam air-gapped ve paketli (PyInstaller) exe'ye ek
bağımlılık istemiyoruz. XLSX aslında XML parçalarından oluşan bir ZIP arşividir;
Python stdlib'inin `zipfile` + `xml` modülleriyle tek sayfalık bir tabloyu
güvenle yazar/okuruz.

Yazarken TÜM hücreler METİN (numFmt "@") biçiminde tutulur: Excel "2:1" gibi bir
bit aralığını saat değerine, "0x00"ı sayıya çevirmesin diye. Okurken hem
inline string (bizim ürettiğimiz) hem shared string (Excel düzenleyip
kaydedince) hem düz sayı hücreleri desteklenir.
"""

from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
    "</Relationships>"
)

_WORKBOOK_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    "</Relationships>"
)

# Tüm hücreler metin (numFmtId 49 = "@"); başlık için ayrıca kalın font.
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
    '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="2"><fill><patternFill patternType="none"/></fill>'
    '<fill><patternFill patternType="gray125"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
    '<cellXfs count="2">'
    '<xf numFmtId="49" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'
    '<xf numFmtId="49" fontId="1" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1"/>'
    "</cellXfs></styleSheet>"
)


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="' + escape(sheet_name) + '" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )


def _col_letter(idx: int) -> str:
    """0-tabanlı sütun indeksi → A, B, ..., Z, AA, ..."""
    idx += 1
    out = ""
    while idx:
        idx, rem = divmod(idx - 1, 26)
        out = chr(65 + rem) + out
    return out


def _col_index(ref: str) -> int:
    """Hücre referansındaki sütun harflerini (ör. 'B3') 0-tabanlı indekse çevirir."""
    m = re.match(r"([A-Za-z]+)", ref or "")
    if not m:
        return 0
    n = 0
    for ch in m.group(1).upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _sheet_xml(rows: list[list]) -> str:
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>',
    ]
    for r, row in enumerate(rows, start=1):
        out.append('<row r="%d">' % r)
        style = 1 if r == 1 else 0
        for c, val in enumerate(row):
            ref = _col_letter(c) + str(r)
            text = escape("" if val is None else str(val))
            out.append(
                '<c r="%s" s="%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                % (ref, style, text)
            )
        out.append("</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def write_sheet(rows: list[list], sheet_name: str = "RegisterMap") -> bytes:
    """Satır listesini (her satır hücre listesi) tek sayfalık bir .xlsx'e yazar."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _ROOT_RELS)
        z.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        z.writestr("xl/styles.xml", _STYLES)
        z.writestr("xl/worksheets/sheet1.xml", _sheet_xml(rows))
    return buf.getvalue()


def _parse_shared_strings(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    out: list[str] = []
    for si in root.findall(_NS + "si"):
        out.append("".join(t.text or "" for t in si.iter(_NS + "t")))
    return out


def _first_worksheet_path(names: list[str]) -> str:
    if "xl/worksheets/sheet1.xml" in names:
        return "xl/worksheets/sheet1.xml"
    sheets = sorted(n for n in names if re.match(r"xl/worksheets/[^/]+\.xml$", n))
    if not sheets:
        raise ValueError("XLSX içinde çalışma sayfası bulunamadı.")
    return sheets[0]


def _parse_sheet(xml_bytes: bytes, shared: list[str]) -> list[list[str]]:
    root = ET.fromstring(xml_bytes)
    data = root.find(_NS + "sheetData")
    rows: list[list[str]] = []
    if data is None:
        return rows
    for row_el in data.findall(_NS + "row"):
        cells: dict[int, str] = {}
        max_c = -1
        for c in row_el.findall(_NS + "c"):
            ci = _col_index(c.get("r", ""))
            ctype = c.get("t")
            val = ""
            if ctype == "inlineStr":
                is_el = c.find(_NS + "is")
                if is_el is not None:
                    val = "".join(t.text or "" for t in is_el.iter(_NS + "t"))
            else:
                v = c.find(_NS + "v")
                raw = v.text if v is not None else None
                if ctype == "s" and raw is not None and raw.strip().isdigit():
                    idx = int(raw.strip())
                    val = shared[idx] if 0 <= idx < len(shared) else ""
                else:
                    val = raw or ""
            cells[ci] = val
            max_c = max(max_c, ci)
        rows.append([cells.get(i, "") for i in range(max_c + 1)])
    return rows


def read_first_sheet(data: bytes) -> list[list[str]]:
    """Bir .xlsx byte'larından ilk sayfanın satırlarını (hücre metinleri) okur."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                shared = _parse_shared_strings(z.read("xl/sharedStrings.xml"))
            return _parse_sheet(z.read(_first_worksheet_path(names)), shared)
    except zipfile.BadZipFile as exc:
        raise ValueError("Geçerli bir .xlsx dosyası değil (ZIP açılamadı).") from exc
