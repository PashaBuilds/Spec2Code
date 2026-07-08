"""Register map yeteneği: memory-mapped bir donanım bloğunun register
haritasından typedef struct/union header (.h) + kaynak (.c) üretir.

Amaç (kullanıcı vizyonu): sayısal tasarım ekibinden gelen register haritası
(base adres + her biri 4 bayt register + 32-bit bitfield tanımları + reset
değerleri) elle typedef struct'a çevrilmez; Spec2Code bunu deterministik
üretir. Veri modeli JSON'dur (self-contained HTML editörün gövdesine gömülü
ya da doğrudan); bu modül JSON'u doğrular, C üretir, örnek/boş HTML editörü
üretir ve bir HTML dosyasından gömülü JSON'u geri çıkarır.

TASARIM KARARLARI (kullanıcı, 2026-07-08):
  - Her register TAM 4 bayt (32-bit). Reserved register'lar bile 4 bayt yer
    tutar; hiçbir offset atlanmaz. Ardışık olmayan offset'lerde otomatik
    reserved dolgu (padding) eklenir.
  - Her register bir UNION: `unsigned int uiValue` (ham/reset erişimi) +
    LSB-first packed bitfield struct `sBits` (okunur erişim). Kullanıcı
    bitfield riskini bilerek kabul etti; union, reset-değeri yazımını (ham)
    ve bitfield okunabilirliğini birlikte verir.
  - `__attribute__((packed))` her struct/union'da.
  - init: alanı SIFIRLAMAZ; her register'ı RESET değerine eşitler.
  - static_assert(offsetof(...)) ile struct offset'leri register offset'lerine
    mühürlenir; sayısal ekibin haritasıyla kod asla kayamaz.
  - Kodlama standardı: SPascalStruct, spPointer, camelCase, unsigned int,
    Allman, 4 boşluk, CRLF (üretimde _apply_default_identifier_style zaten
    CRLF verir; burada satırlar \n, çağıran normalize eder).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
#: "7" (tek bit) veya "15:8" (aralık, msb:lsb). Bit alanı gösterimi.
_BITS = re.compile(r"^\d+(:\d+)?$")
_HEX_OR_DEC = re.compile(r"^(0[xX][0-9a-fA-F]+|\d+)$")


# --------------------------------------------------------------------------- #
# Doğrulama
# --------------------------------------------------------------------------- #

def _parse_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and _HEX_OR_DEC.match(value.strip()):
        return int(value.strip(), 0)
    return None


def _bit_span(bits: str) -> tuple[int, int] | None:
    """"msb:lsb" ya da "n" → (msb, lsb). Geçersizse None."""
    if not isinstance(bits, str) or not _BITS.match(bits.strip()):
        return None
    parts = bits.strip().split(":")
    if len(parts) == 1:
        b = int(parts[0])
        return (b, b)
    msb, lsb = int(parts[0]), int(parts[1])
    if msb < lsb:
        return None
    return (msb, lsb)


def validate_register_document(doc) -> list[str]:
    """Register map dokümanının yapısal hataları (boş liste = geçerli).

    Şema:
      { "maps": [ {
          "name": "<C tanımlayıcı gövdesi>",
          "base_address": "0x...",
          "description": "...",
          "registers": [ {
             "name": "<C tanımlayıcı>", "offset": "0x..", "reset": "0x..",
             "reserved": bool, "description": "...",
             "fields": [ { "name": "...", "bits": "15:8", "description": "..." } ]
          } ]
      } ] }
    """
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["register map dokümanı bir JSON nesnesi olmalı"]
    maps = doc.get("maps")
    if not isinstance(maps, list) or not maps:
        return ["maps: en az bir register map içeren bir dizi olmalı"]

    seen_map_names: set[str] = set()
    for mi, rmap in enumerate(maps):
        where = f"maps[{mi}]"
        if not isinstance(rmap, dict):
            errors.append(f"{where}: her map bir nesne olmalı")
            continue
        name = rmap.get("name")
        if not isinstance(name, str) or not _IDENT.match(name or ""):
            errors.append(f"{where}.name: C tanımlayıcısı olmalı (harf/rakam/_ , rakamla başlamaz)")
        else:
            key = name.lower()
            if key in seen_map_names:
                errors.append(f"{where}.name: '{name}' birden fazla map'te — adlar benzersiz olmalı")
            seen_map_names.add(key)
        if _parse_int(rmap.get("base_address")) is None:
            errors.append(f"{where}.base_address: 0x'li ya da ondalık bir adres olmalı (şu an: {rmap.get('base_address')!r})")

        registers = rmap.get("registers")
        if not isinstance(registers, list) or not registers:
            errors.append(f"{where}.registers: en az bir register içeren bir dizi olmalı")
            continue

        seen_reg_names: set[str] = set()
        seen_offsets: dict[int, str] = {}
        for ri, reg in enumerate(registers):
            rwhere = f"{where}.registers[{ri}]"
            if not isinstance(reg, dict):
                errors.append(f"{rwhere}: her register bir nesne olmalı")
                continue
            rname = reg.get("name")
            if not isinstance(rname, str) or not _IDENT.match(rname or ""):
                errors.append(f"{rwhere}.name: C tanımlayıcısı olmalı")
            else:
                rkey = rname.lower()
                if rkey in seen_reg_names:
                    errors.append(f"{rwhere}.name: '{rname}' bu map'te tekrarlıyor")
                seen_reg_names.add(rkey)
            offset = _parse_int(reg.get("offset"))
            if offset is None:
                errors.append(f"{rwhere}.offset: 0x'li ya da ondalık olmalı")
            elif offset % 4 != 0:
                errors.append(f"{rwhere}.offset: 4'ün katı olmalı (her register 4 bayttır; şu an: {reg.get('offset')!r})")
            elif offset in seen_offsets:
                errors.append(f"{rwhere}.offset: {hex(offset)} zaten '{seen_offsets[offset]}' tarafından kullanılıyor")
            elif isinstance(rname, str):
                seen_offsets[offset] = rname
            if _parse_int(reg.get("reset", 0)) is None:
                errors.append(f"{rwhere}.reset: 0x'li ya da ondalık bir 32-bit değer olmalı (şu an: {reg.get('reset')!r})")

            fields = reg.get("fields", [])
            if reg.get("reserved"):
                # Reserved register: bit alanı beklenmez (tümü ham).
                continue
            if not isinstance(fields, list):
                errors.append(f"{rwhere}.fields: bir dizi olmalı")
                continue
            used_bits = 0
            for fj, field in enumerate(fields):
                fwhere = f"{rwhere}.fields[{fj}]"
                if not isinstance(field, dict):
                    errors.append(f"{fwhere}: her bit alanı bir nesne olmalı")
                    continue
                fname = field.get("name")
                if not isinstance(fname, str) or not _IDENT.match(fname or ""):
                    errors.append(f"{fwhere}.name: C tanımlayıcısı olmalı")
                span = _bit_span(field.get("bits"))
                if span is None:
                    errors.append(f"{fwhere}.bits: 'msb:lsb' ya da 'n' biçiminde olmalı (şu an: {field.get('bits')!r})")
                    continue
                msb, lsb = span
                if msb > 31:
                    errors.append(f"{fwhere}.bits: 32-bit register — en yüksek bit 31 (şu an: {msb})")
                    continue
                mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                if used_bits & mask:
                    errors.append(f"{fwhere}.bits: {field.get('bits')} başka bir alanla ÇAKIŞIYOR")
                used_bits |= mask
    return errors


# --------------------------------------------------------------------------- #
# Yardımcılar
# --------------------------------------------------------------------------- #

def _pascal(identifier: str) -> str:
    """foo_bar / fooBar → FooBar (tip/isim gövdesi için)."""
    parts = re.split(r"[_\s]+", identifier.strip())
    out = []
    for part in parts:
        if not part:
            continue
        out.append(part[0].upper() + part[1:])
    return "".join(out) or "Map"


def _sorted_registers(rmap: dict) -> list[dict]:
    return sorted(rmap["registers"], key=lambda r: _parse_int(r.get("offset")) or 0)


def _struct_type_name(map_name: str) -> str:
    return f"S{_pascal(map_name)}Regs"


def _member_name(reg_name: str) -> str:
    """Register üye adı = 'S' + register adı (kullanıcı standardı: birleşim/
    struct üyesi 'S' öneki taşır). Ör. CONTROL → SCONTROL; erişim
    SCONTROL.uiValue (ham) ve SCONTROL.MODE (anonim bitfield alt-struct'ı
    sayesinde doğrudan)."""
    return "S" + reg_name


# --------------------------------------------------------------------------- #
# C üretimi
# --------------------------------------------------------------------------- #

def _guard(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", f"{name}_REGS_H".upper())


def _register_member_lines(reg: dict) -> list[str]:
    """Struct içindeki INLINE union register üyesi (ayrı bir typedef üretilmez).

    Ham erişim için `unsigned int uiValue` + LSB-first bit alanları ANONİM bir
    alt-struct içinde (adı yok) ki bitfield'lara doğrudan `SCONTROL.MODE` diye
    erişilebilsin. Tek bir `__attribute__((packed))` yeterlidir; o da union
    üyesinin (SCONTROL) SOLUNDA yazılır — iç alt-struct'ta AYRICA packed
    yazılmaz. Üye adı 'S' + register adı; bit alanı adları verbatim (ui öneki
    yok, ör. IRQ_EN); kullanılmayan bit aralıkları anonim isimsiz alanlarla
    (`unsigned int : N;`) kapatılır ki bit konumları birebir kalsın.
    """
    name = _member_name(reg["name"])
    offset = _parse_int(reg.get("offset")) or 0
    out: list[str] = []
    out.append("    union")
    out.append("    {")
    out.append("        unsigned int uiValue;")
    if not reg.get("reserved") and reg.get("fields"):
        out.append("        struct")
        out.append("        {")
        covered = 0
        # LSB-first: alanları lsb'ye göre sırala, aradaki boşluklara anonim
        # reserved bit alanları koy ki bit konumları birebir doğru olsun.
        fields = sorted(reg["fields"], key=lambda f: _bit_span(f["bits"])[1])
        for field in fields:
            msb, lsb = _bit_span(field["bits"])
            if lsb > covered:
                out.append(f"            unsigned int : {lsb - covered};")
                covered = lsb
            width = msb - lsb + 1
            comment = f"  /* {field['description']} */" if field.get("description") else ""
            out.append(f"            unsigned int {field['name']} : {width};{comment}")
            covered = msb + 1
        if covered < 32:
            out.append(f"            unsigned int : {32 - covered};")
        # Anonim alt-struct: adsiz + packed'siz; bitfield'lara SCONTROL.MODE.
        out.append("        };")
    out.append(f"    }} __attribute__((packed)) {name};  /* 0x{offset:03X} */")
    return out


def generate_header(rmap: dict) -> str:
    """Bir register map için .h içeriği: her register struct içine INLINE bir
    union üye (uiValue + LSB-first packed sBits) olarak yazılır; reset sabitleri
    + static_assert offset mühürleri. `__attribute__((packed))` her yapının
    kapanış ayracından sonra; sayısal sabitlerde `U` soneki kullanılmaz."""
    map_name = rmap["name"]
    MOD = re.sub(r"[^A-Z0-9]", "_", map_name.upper())
    struct_t = _struct_type_name(map_name)
    guard = _guard(map_name)
    base = _parse_int(rmap.get("base_address")) or 0
    regs = _sorted_registers(rmap)

    lines: list[str] = []
    lines.append(f"#ifndef {guard}")
    lines.append(f"#define {guard}")
    lines.append("")
    lines.append("/* Spec2Code register map ureticisi tarafindan uretildi.")
    if rmap.get("description"):
        lines.append(f" * {rmap['description']}")
    lines.append(" * Her register 4 bayttir; bit alanlari LSB-first siralanir.")
    lines.append(" * static_assert offset muhurleri register haritasiyla struct'i kilitler. */")
    lines.append("")
    lines.append("#include <stddef.h>")
    lines.append("#include <assert.h>")
    lines.append("")
    lines.append(f"#define {MOD}_BASE_ADDRESS 0x{base:08X}")
    lines.append("")

    # Reset sabitleri.
    for reg in regs:
        reset = _parse_int(reg.get("reset", 0)) or 0
        lines.append(f"#define {MOD}_{reg['name'].upper()}_RESET 0x{reset & 0xFFFFFFFF:08X}")
    lines.append("")

    # Map struct'i: her register INLINE union üye; ardışık olmayan offset'lere
    # reserved dolgu (padding) eklenir ki struct offset'leri register
    # offset'lerine uysun. Ayrı bir per-register typedef ÜRETİLMEZ.
    lines.append("typedef struct")
    lines.append("{")
    expected = 0
    pad_idx = 0
    for reg in regs:
        offset = _parse_int(reg.get("offset")) or 0
        if offset > expected:
            gap_words = (offset - expected) // 4
            lines.append(f"    unsigned int uiReserved{pad_idx}[{gap_words}];"
                         f"  /* 0x{expected:03X}..0x{offset - 4:03X} dolgu */")
            pad_idx += 1
            expected = offset
        lines.extend(_register_member_lines(reg))
        expected = offset + 4
    lines.append(f"}} __attribute__((packed)) {struct_t};")
    lines.append("")

    # Offset muhurleri.
    lines.append("/* Offset muhurleri: struct register haritasindan kayarsa derleme durur. */")
    for reg in regs:
        offset = _parse_int(reg.get("offset")) or 0
        lines.append(
            f"_Static_assert(offsetof({struct_t}, {_member_name(reg['name'])}) == 0x{offset:X}, "
            f"\"{reg['name']} offset kaymis\");")
    lines.append("")

    # init prototipi.
    lines.append(f"void {map_name}Init(void);")
    lines.append("")
    lines.append(f"#endif /* {guard} */")
    lines.append("")
    return "\n".join(lines)


def generate_source(rmap: dict) -> str:
    """Bir register map için .c içeriği: base'e map'li static struct pointer +
    init (her register'i reset degerine esitler)."""
    map_name = rmap["name"]
    MOD = re.sub(r"[^A-Z0-9]", "_", map_name.upper())
    struct_t = _struct_type_name(map_name)
    ptr_name = f"S_sp{_pascal(map_name)}"
    regs = _sorted_registers(rmap)

    lines: list[str] = []
    lines.append("/* Spec2Code register map ureticisi tarafindan uretildi. */")
    lines.append(f"#include \"{map_name}_regs.h\"")
    lines.append("")
    lines.append("/* Base adrese map'li static register blok isaretcisi. */")
    lines.append(f"static {struct_t}* const {ptr_name} = "
                 f"({struct_t}*)({MOD}_BASE_ADDRESS);")
    lines.append("")
    lines.append(f"void {map_name}Init(void)")
    lines.append("{")
    lines.append("    /* Her register RESET degerine esitlenir (alan sifirlanmaz). */")
    for reg in regs:
        if reg.get("reserved"):
            continue
        lines.append(f"    {ptr_name}->{_member_name(reg['name'])}.uiValue = "
                     f"{MOD}_{reg['name'].upper()}_RESET;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def generate_files(doc: dict) -> dict[str, str]:
    """Doğrulanmış doküman → { '<map>_regs.h': ..., '<map>.c': ... }."""
    out: dict[str, str] = {}
    for rmap in doc["maps"]:
        out[f"{rmap['name']}_regs.h"] = generate_header(rmap)
        out[f"{rmap['name']}.c"] = generate_source(rmap)
    return out


# --------------------------------------------------------------------------- #
# HTML gövdesine gömülü JSON: çıkar / göm
# --------------------------------------------------------------------------- #

# Gerçek veri adası hem id hem `type="application/json"` taşır. Şablonun en
# üstündeki HTML yorumu da <script id="spec2code-registermap-data"> etiketini
# METİN olarak anıyor; type niteliği olmadığından iki lookahead onu eler.
# Lookahead'ler sırasız olduğundan tarayıcı yeniden-serileştirmede nitelik
# sırası değişse bile eşleşir.
_JSON_BLOCK_RE = re.compile(
    r'<script\b'
    r'(?=[^>]*\bid=["\']spec2code-registermap-data["\'])'
    r'(?=[^>]*\btype=["\']application/json["\'])'
    r'[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def extract_document_from_html(html: str) -> dict:
    """Self-contained HTML editörün gövdesindeki JSON veri bloğunu çıkarır."""
    match = _JSON_BLOCK_RE.search(html)
    if not match:
        raise ValueError("HTML içinde register map veri bloğu (spec2code-registermap-data) bulunamadı.")
    raw = match.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gömülü JSON çözümlenemedi: {exc}") from exc


def _editor_template() -> str:
    return (Path(__file__).with_name("data") / "register_map_editor.html").read_text(encoding="utf-8")


def build_html(doc: dict) -> str:
    """Verilen dokümanı self-contained HTML editörün gövdesine gömer.

    JSON içeriği </script> içeremez; `<` kaçışıyla güvenli hale getirilir
    (JSON'da string olarak kalır, editör okurken geri çevirir)."""
    payload = json.dumps(doc, ensure_ascii=False, indent=1).replace("</", "<\\/")
    template = _editor_template()
    return template.replace("/*__SPEC2CODE_REGISTERMAP_DATA__*/", payload)


def blank_document() -> dict:
    """İndirilebilir boş/örnek register map (bir map, iki register)."""
    return {
        "version": 1,
        "maps": [
            {
                "name": "ornek_blok",
                "base_address": "0xA0000000",
                "description": "Ornek PL register blogu - sayisal ekip doldurur.",
                "registers": [
                    {
                        "name": "CONTROL", "offset": "0x00", "reset": "0x00000000",
                        "reserved": False, "description": "Kontrol register'i",
                        "fields": [
                            {"name": "ENABLE", "bits": "0", "description": "Blok etkin"},
                            {"name": "MODE", "bits": "2:1", "description": "Calisma modu"},
                            {"name": "IRQ_EN", "bits": "3", "description": "Kesme etkin"},
                        ],
                    },
                    {
                        "name": "STATUS", "offset": "0x04", "reset": "0x00000000",
                        "reserved": False, "description": "Durum register'i",
                        "fields": [
                            {"name": "BUSY", "bits": "0", "description": "Islem suruyor"},
                            {"name": "ERROR_CODE", "bits": "11:8", "description": "Hata kodu"},
                        ],
                    },
                ],
            }
        ],
    }
