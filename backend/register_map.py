"""Register map yeteneği: memory-mapped bir donanım bloğunun register
haritasından typedef struct/union header (.h) + kaynak (.c) üretir.

Amaç (kullanıcı vizyonu): sayısal tasarım ekibinden gelen register haritası
(base adres + her biri 4 bayt register + 32-bit bitfield tanımları + reset
değerleri) elle typedef struct'a çevrilmez; Spec2Code bunu deterministik
üretir. Veri modeli JSON'dur (self-contained HTML editörün gövdesine gömülü
ya da doğrudan); bu modül JSON'u doğrular, C üretir, örnek/boş HTML editörü
üretir ve bir HTML dosyasından gömülü JSON'u geri çıkarır.

TASARIM KARARLARI (kullanıcı, 2026-07-08..09):
  - Register genişliği artık SABİT 4 bayt DEĞİL: offset'lerden çıkarılır.
    Bir register'ın byte genişliği = bir sonraki register'ın offset'ine olan
    fark; SON register'ın genişliği alanlarından çıkarılıp 1/2/4/8'e yuvarlanır
    (alan yoksa 4 bayt). Ham tip genişliğe göre: 1→unsigned char, 2→unsigned
    short, 4→unsigned int, 8→unsigned long long.
  - Skaler mi / bitfield mi ALANLARDAN çıkarılır (ayrı bayrak yok):
      * reserved              → `unsigned char ucReservedN[width]` (opak dolgu)
      * alan yok / tek alan tüm genişliği kaplıyor (ör. 31:0)
                              → düz skaler üye `<önek><Ad>` (ör. uiTemperature)
      * register'ı bölen alanlar → INLINE union `S<Ad>` { <önek>Value; anonim
        bitfield alt-struct } — bitfield'lara doğrudan SCONFIG.MODE, ham
        erişim SCONFIG.usValue. Kullanıcı bitfield riskini bilerek kabul etti.
  - Tek `__attribute__((packed))` union üyesinin (S<Ad>) solunda; iç
    alt-struct anonim + packed'siz; kullanılmayan bitler anonim isimsiz alan.
  - init: alanı SIFIRLAMAZ; her register'ı RESET değerine eşitler (skaler
    doğrudan, bitfield ham <önek>Value üzerinden; reserved atlanır).
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

from backend import xlsx_min

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
            elif offset < 0:
                errors.append(f"{rwhere}.offset: negatif olamaz")
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
                if msb > 63:
                    errors.append(f"{fwhere}.bits: en yüksek bit 63 olabilir (en fazla 8 bayt; şu an: {msb})")
                    continue
                mask = ((1 << (msb - lsb + 1)) - 1) << lsb
                if used_bits & mask:
                    errors.append(f"{fwhere}.bits: {field.get('bits')} başka bir alanla ÇAKIŞIYOR")
                used_bits |= mask

        # Genişlik çıkarımı sonrası kontroller: genişlik = sonraki offset farkı
        # (son register alanlarından yuvarlanır). Alanlar genişliğe sığmalı;
        # bit alanlı (skaler olmayan) register 1/2/4/8 byte olmalı; reset değeri
        # genişliğe sığmalı; offset'ler kesin artan olmalı.
        valid_regs = [r for r in registers
                      if isinstance(r, dict) and _parse_int(r.get("offset")) is not None]
        valid_regs.sort(key=lambda r: _parse_int(r.get("offset")))
        for reg, width in zip(valid_regs, _register_widths(valid_regs)):
            rname = reg.get("name", "?")
            if width < 1:
                errors.append(f"{where}.{rname}: offset'ler kesin artan olmalı (çıkarılan genişlik {width} byte)")
                continue
            if reg.get("reserved"):
                continue
            hb = _highest_bit(reg)
            if hb >= 0 and hb >= width * 8:
                errors.append(f"{where}.{rname}: en yüksek bit {hb}, register genişliği "
                              f"{width} byte ({width * 8} bit) — alan sığmıyor")
            if (reg.get("fields") and not _is_scalar(reg, width)
                    and _raw_type(width) is None):
                errors.append(f"{where}.{rname}: bit alanlı register genişliği 1/2/4/8 byte "
                              f"olmalı (offset aralığı {width} byte)")
            reset = _parse_int(reg.get("reset", 0))
            if reset is not None and 1 <= width <= 8 and reset >= (1 << (width * 8)):
                errors.append(f"{where}.{rname}: reset değeri {hex(reset)} register genişliğine "
                              f"({width} byte) sığmıyor")
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


def _raw_type(width: int):
    """Byte genişliği → (C tam sayı tipi, Hungarian önek). Standart olmayan
    genişlik (1/2/4/8 dışı) → None; çağıran bayt dizisine düşer."""
    return {
        1: ("unsigned char", "uc"),
        2: ("unsigned short", "us"),
        4: ("unsigned int", "ui"),
        8: ("unsigned long long", "ull"),
    }.get(width)


def _highest_bit(reg: dict) -> int:
    """Register alanlarının kullandığı en yüksek bit (0-index); alan yoksa -1."""
    hb = -1
    for field in reg.get("fields") or []:
        span = _bit_span(field.get("bits"))
        if span is not None:
            hb = max(hb, span[0])
    return hb


def _round_up_width(highest_bit: int) -> int:
    """En yüksek bit → 1/2/4/8 byte'a yuvarlanmış genişlik."""
    needed = highest_bit + 1
    for width in (1, 2, 4, 8):
        if needed <= width * 8:
            return width
    return 8


def _register_widths(regs: list[dict]) -> list[int]:
    """Sıralı register'lar için byte genişlikleri. Genişlik = bir sonraki
    register'ın offset'ine olan fark; SON register'ın genişliği alanlarından
    çıkarılıp 1/2/4/8'e yuvarlanır (alan yoksa 4 byte varsayılır)."""
    widths: list[int] = []
    for i, reg in enumerate(regs):
        offset = _parse_int(reg.get("offset")) or 0
        if i + 1 < len(regs):
            nxt = _parse_int(regs[i + 1].get("offset")) or 0
            widths.append(nxt - offset)
        else:
            hb = _highest_bit(reg)
            widths.append(_round_up_width(hb) if hb >= 0 else 4)
    return widths


def _is_scalar(reg: dict, width: int) -> bool:
    """Register düz tek bir değer mi (union/bitfield yerine skaler üye)?
    reserved değilse ve ya hiç alanı yoksa YA DA tek alanı tüm register
    genişliğini (width*8-1:0) kaplıyorsa skalerdir."""
    if reg.get("reserved"):
        return False
    fields = reg.get("fields") or []
    if not fields:
        return True
    if len(fields) == 1:
        span = _bit_span(fields[0].get("bits"))
        if span is not None and span[1] == 0 and span[0] == width * 8 - 1:
            return True
    return False


def _layout(rmap: dict) -> list[dict]:
    """Her register için yerleşim kaydı: {reg, offset, width, kind, member, raw}.
    kind ∈ {scalar, bitfield, reserved}; member = struct üye adı; raw = bitfield
    union'ının ham üye öneki (yalnız kind=='bitfield'). Header ve source aynı
    üye adlarını buradan alır ki tutarlı kalsın."""
    regs = _sorted_registers(rmap)
    widths = _register_widths(regs)
    out: list[dict] = []
    reserved_idx = 0
    for reg, width in zip(regs, widths):
        offset = _parse_int(reg.get("offset")) or 0
        raw = _raw_type(width)
        if reg.get("reserved"):
            out.append({"reg": reg, "offset": offset, "width": width,
                        "kind": "reserved", "member": f"ucReserved{reserved_idx}", "raw": None})
            reserved_idx += 1
        elif _is_scalar(reg, width):
            prefix = raw[1] if raw else "uc"
            out.append({"reg": reg, "offset": offset, "width": width,
                        "kind": "scalar", "member": f"{prefix}{_pascal(reg['name'])}", "raw": None})
        else:
            out.append({"reg": reg, "offset": offset, "width": width,
                        "kind": "bitfield", "member": f"S{_pascal(reg['name'])}",
                        "raw": (raw[1] if raw else "ui")})
    return out


# --------------------------------------------------------------------------- #
# C üretimi
# --------------------------------------------------------------------------- #

def _guard(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "_", f"{name}_REGS_H".upper())


def _reset_hex(reset: int, width: int) -> str:
    """Reset sabitini register genişliği kadar hex haneyle yaz (2B → 4 hane)."""
    mask = (1 << (width * 8)) - 1
    return f"0x{reset & mask:0{width * 2}X}"


def _union_lines(item: dict) -> list[str]:
    """Bitfield register → struct içine INLINE union üyesi. Ham üye tipi
    genişliğe göre (uiValue/usValue/ucValue/ullValue); bit alanları AYNI tam
    sayı tipiyle ANONİM alt-struct içinde ki union boyutu genişlikle birebir
    kalsın ve bitfield'lara doğrudan `SCONFIG.MODE` diye erişilsin. Tek
    `__attribute__((packed))` üyenin (S<Ad>) solunda; iç alt-struct'ta packed
    yok; kullanılmayan bit aralıkları anonim isimsiz alanlarla kapatılır."""
    reg = item["reg"]
    width = item["width"]
    offset = item["offset"]
    member = item["member"]
    ctype, prefix = _raw_type(width) or ("unsigned int", "ui")
    out: list[str] = []
    out.append("    union")
    out.append("    {")
    out.append(f"        {ctype} {prefix}Value;")
    out.append("        struct")
    out.append("        {")
    covered = 0
    fields = sorted(reg["fields"], key=lambda f: _bit_span(f["bits"])[1])
    for field in fields:
        msb, lsb = _bit_span(field["bits"])
        if lsb > covered:
            out.append(f"            {ctype} : {lsb - covered};")
            covered = lsb
        bits = msb - lsb + 1
        comment = f"  /* {field['description']} */" if field.get("description") else ""
        out.append(f"            {ctype} {field['name']} : {bits};{comment}")
        covered = msb + 1
    total = width * 8
    if covered < total:
        out.append(f"            {ctype} : {total - covered};")
    out.append("        };")
    out.append(f"    }} __attribute__((packed)) {member};  /* 0x{offset:03X} ({width}B) */")
    return out


def generate_header(rmap: dict) -> str:
    """Bir register map için .h içeriği. Register genişlikleri offset'lerden
    çıkarılır (son register alanlarından 1/2/4/8'e yuvarlanır). Skaler register
    düz üye (uiTemperature); bitfield register struct içine INLINE union
    (S<Ad>); reserved bayt dizisi. `__attribute__((packed))` her yapının
    solunda; sayısal sabitlerde `U` soneki yok; static_assert offset mühürleri
    struct'ı register haritasına kilitler."""
    map_name = rmap["name"]
    MOD = re.sub(r"[^A-Z0-9]", "_", map_name.upper())
    struct_t = _struct_type_name(map_name)
    guard = _guard(map_name)
    base = _parse_int(rmap.get("base_address")) or 0
    layout = _layout(rmap)

    lines: list[str] = []
    lines.append(f"#ifndef {guard}")
    lines.append(f"#define {guard}")
    lines.append("")
    lines.append("/* Spec2Code register map ureticisi tarafindan uretildi.")
    if rmap.get("description"):
        lines.append(f" * {rmap['description']}")
    lines.append(" * Register genislikleri offset'lerden cikarilir; bit alanlari LSB-first.")
    lines.append(" * static_assert offset muhurleri register haritasiyla struct'i kilitler. */")
    lines.append("")
    lines.append("#include <stddef.h>")
    lines.append("#include <assert.h>")
    lines.append("")
    lines.append(f"#define {MOD}_BASE_ADDRESS 0x{base:08X}")
    lines.append("")

    # Reset sabitleri (reserved haric; genislik kadar hex hane).
    for item in layout:
        if item["reg"].get("reserved"):
            continue
        reset = _parse_int(item["reg"].get("reset", 0)) or 0
        lines.append(f"#define {MOD}_{item['reg']['name'].upper()}_RESET "
                     f"{_reset_hex(reset, item['width'])}")
    lines.append("")

    # Map struct'i: her register offset'ine gore skaler / bitfield union /
    # reserved bayt dizisi olarak yerlesir. Genislik = sonraki offset farki.
    lines.append("typedef struct")
    lines.append("{")
    for item in layout:
        reg = item["reg"]
        offset = item["offset"]
        width = item["width"]
        member = item["member"]
        desc = reg.get("description")
        if item["kind"] == "reserved":
            lines.append(f"    unsigned char {member}[{width}];"
                         f"  /* 0x{offset:03X} reserved ({width}B) */")
        elif item["kind"] == "scalar":
            raw = _raw_type(width)
            tail = f"  /* 0x{offset:03X}" + (f" - {desc}" if desc else "") + f" ({width}B) */"
            if raw:
                lines.append(f"    {raw[0]} {member};{tail}")
            else:
                lines.append(f"    unsigned char {member}[{width}];{tail}")
        else:
            lines.extend(_union_lines(item))
    lines.append(f"}} __attribute__((packed)) {struct_t};")
    lines.append("")

    # Offset muhurleri.
    lines.append("/* Offset muhurleri: struct register haritasindan kayarsa derleme durur. */")
    for item in layout:
        lines.append(
            f"_Static_assert(offsetof({struct_t}, {item['member']}) == 0x{item['offset']:X}, "
            f"\"{item['reg']['name']} offset kaymis\");")
    lines.append("")

    # init + dump prototipleri.
    lines.append(f"void {map_name}Init(void);")
    lines.append(f"void {map_name}Dump(void);")
    lines.append("")
    lines.append(f"#endif /* {guard} */")
    lines.append("")
    return "\n".join(lines)


def _dump_function_lines(map_name: str, MOD: str, ptr_name: str, layout: list[dict]) -> list[str]:
    """Register değerlerini isimleriyle DÜZGÜN bir tablo halinde yazan
    `<map>Dump(void)`. Bitfield register'da ham değer + her bit alanı adıyla;
    skaler register doğrudan; reserved atlanır. Çıktı fonksiyonu REGMAP_PRINTF
    makrosuyla soyutlanır (varsayılan printf; Vitis'te -DREGMAP_PRINTF=xil_printf
    ile hafif çıktı). -DREGMAP_NO_DUMP tümünü derleme dışı bırakır."""
    out: list[str] = []
    out.append("")
    out.append("#ifndef REGMAP_NO_DUMP")
    out.append("/* Register haritasini duzgun bir tablo halinde yazar. Vitis'te hafif")
    out.append(" * cikti icin -DREGMAP_PRINTF=xil_printf; istemezseniz -DREGMAP_NO_DUMP. */")
    out.append("#include <stdio.h>")
    out.append("#ifndef REGMAP_PRINTF")
    out.append("#define REGMAP_PRINTF printf")
    out.append("#endif")
    out.append("")
    out.append(f"void {map_name}Dump(void)")
    out.append("{")
    out.append(f'    REGMAP_PRINTF("=== {map_name} @ 0x%08X ===\\r\\n", (unsigned int)({MOD}_BASE_ADDRESS));')
    out.append('    REGMAP_PRINTF("%-26s %-8s   %s\\r\\n", "NAME", "OFFS/BIT", "VALUE");')
    for item in layout:
        reg = item["reg"]
        if reg.get("reserved"):
            continue
        width = item["width"]
        member = item["member"]
        name = reg["name"]
        offs = f"0x{item['offset']:03X}"
        if width <= 4:
            cast, rawfmt, fieldfmt = "unsigned int", f"0x%0{width * 2}X", "0x%X"
        elif width == 8:
            cast, rawfmt, fieldfmt = "unsigned long long", "0x%016llX", "0x%llX"
        else:
            # Standart olmayan genişlik: skaler bayt dizisi — tek değer basılamaz.
            out.append(f'    REGMAP_PRINTF("%-26s %-8s   ({width}B dizi)\\r\\n", "{name}", "{offs}");')
            continue
        if item["kind"] == "scalar":
            out.append(f'    REGMAP_PRINTF("%-26s %-8s = {rawfmt}\\r\\n", "{name}", "{offs}", '
                       f'({cast})({ptr_name}->{member}));')
        else:
            out.append(f'    REGMAP_PRINTF("%-26s %-8s = {rawfmt}\\r\\n", "{name}", "{offs}", '
                       f'({cast})({ptr_name}->{member}.{item["raw"]}Value));')
            for field in sorted(reg["fields"], key=lambda f: _bit_span(f["bits"])[1]):
                msb, lsb = _bit_span(field["bits"])
                bits = f"[{msb}:{lsb}]" if msb != lsb else f"[{msb}]"
                out.append(f'    REGMAP_PRINTF("  %-24s %-8s = {fieldfmt}\\r\\n", "{field["name"]}", '
                           f'"{bits}", ({cast})({ptr_name}->{member}.{field["name"]}));')
    out.append("}")
    out.append("#endif /* REGMAP_NO_DUMP */")
    return out


def generate_source(rmap: dict) -> str:
    """Bir register map için .c içeriği: base'e map'li static struct pointer +
    init (her register'i reset degerine esitler; skaler dogrudan, bitfield ham
    <onek>Value uzerinden; reserved atlanir) + Dump (degerleri tablo halinde
    yazar)."""
    map_name = rmap["name"]
    MOD = re.sub(r"[^A-Z0-9]", "_", map_name.upper())
    struct_t = _struct_type_name(map_name)
    ptr_name = f"S_sp{_pascal(map_name)}"
    layout = _layout(rmap)

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
    for item in layout:
        reg = item["reg"]
        if reg.get("reserved"):
            continue
        rhs = f"{MOD}_{reg['name'].upper()}_RESET"
        if item["kind"] == "scalar":
            if _raw_type(item["width"]):
                lines.append(f"    {ptr_name}->{item['member']} = {rhs};")
            else:
                lines.append(f"    /* {item['member']}: {item['width']}B dizi — "
                             f"reset elle yazilmali ({rhs}) */")
        else:  # bitfield
            lines.append(f"    {ptr_name}->{item['member']}.{item['raw']}Value = {rhs};")
    lines.append("}")
    lines.extend(_dump_function_lines(map_name, MOD, ptr_name, layout))
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
# Excel (XLSX) — KATI şablon: içe/dışa aktar (openpyxl'siz, bkz. xlsx_min)
# --------------------------------------------------------------------------- #

#: Şablonun ZORUNLU başlık satırı (birebir, bu sıra). Her satır bir bit alanı;
#: alanı olmayan (skaler/reserved) register için tek satır (field/bits boş).
XLSX_HEADERS = [
    "map", "base_address", "register", "offset", "reset", "reserved",
    "reg_description", "field", "bits", "field_description",
]

_XLSX_TRUE = {"x", "1", "true", "evet", "yes", "reserved", "rsvd", "e"}


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in _XLSX_TRUE


def document_to_rows(doc: dict) -> list[list[str]]:
    """Doküman → katı şablon satırları (başlık + register/alan satırları)."""
    rows: list[list[str]] = [list(XLSX_HEADERS)]
    for rmap in doc.get("maps", []):
        mname = rmap.get("name", "")
        base = rmap.get("base_address", "")
        for reg in rmap.get("registers", []):
            rname = reg.get("name", "")
            off = reg.get("offset", "")
            reset = reg.get("reset", "")
            resv = "x" if reg.get("reserved") else ""
            rdesc = reg.get("description", "") or ""
            fields = reg.get("fields") or []
            if reg.get("reserved") or not fields:
                rows.append([mname, base, rname, off, reset, resv, rdesc, "", "", ""])
            else:
                for field in fields:
                    rows.append([mname, base, rname, off, reset, resv, rdesc,
                                 field.get("name", ""), field.get("bits", ""),
                                 field.get("description", "") or ""])
    return rows


def rows_to_document(rows: list[list]) -> dict:
    """Katı şablon satırları → doküman. Başlık birebir eşleşmezse ValueError."""
    if not rows:
        raise ValueError("XLSX boş: en az başlık satırı olmalı.")
    header = [str(c).strip().lower() for c in rows[0]][:len(XLSX_HEADERS)]
    if header != XLSX_HEADERS:
        raise ValueError(
            "XLSX şablonu beklenen sütunlarla eşleşmiyor. İlk satır birebir şu "
            "olmalı: " + " | ".join(XLSX_HEADERS))
    idx = {h: i for i, h in enumerate(XLSX_HEADERS)}

    def cell(row: list, key: str) -> str:
        i = idx[key]
        return str(row[i]).strip() if i < len(row) and row[i] is not None else ""

    maps: dict[str, dict] = {}
    reg_by_key: dict[tuple, dict] = {}
    order: list[str] = []
    for row in rows[1:]:
        if not any(str(c).strip() for c in row):
            continue
        mname = cell(row, "map")
        if not mname:
            continue
        if mname not in maps:
            maps[mname] = {"name": mname, "base_address": cell(row, "base_address"),
                           "description": "", "registers": []}
            order.append(mname)
        rmap = maps[mname]
        if not rmap["base_address"]:
            rmap["base_address"] = cell(row, "base_address")
        rname = cell(row, "register")
        if not rname:
            continue
        key = (mname, rname)
        if key not in reg_by_key:
            reg = {"name": rname, "offset": cell(row, "offset"),
                   "reset": cell(row, "reset") or "0x0",
                   "reserved": _truthy(cell(row, "reserved")),
                   "description": cell(row, "reg_description"), "fields": []}
            reg_by_key[key] = reg
            rmap["registers"].append(reg)
        reg = reg_by_key[key]
        fname = cell(row, "field")
        if fname:
            reg["fields"].append({"name": fname, "bits": cell(row, "bits"),
                                  "description": cell(row, "field_description")})
    return {"version": 1, "maps": [maps[name] for name in order]}


def build_xlsx(doc: dict) -> bytes:
    """Doküman → katı şablon .xlsx (byte)."""
    return xlsx_min.write_sheet(document_to_rows(doc))


def parse_xlsx(data: bytes) -> dict:
    """Katı şablon .xlsx (byte) → doküman."""
    return rows_to_document(xlsx_min.read_first_sheet(data))


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
