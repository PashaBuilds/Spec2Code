"""Descriptor YAML yapısal doğrulayıcısı.

Kullanıcı descriptor'ları (user_descriptors/) içe aktarılırken ve testlerde
kullanılır. Amaç: codegen'e ulaşmadan, alan alan Türkçe hata mesajlarıyla
sorunu göstermek — codegen hataları kullanıcıya kriptik gelir. Kurallar
cmodel/codegen'in gerçekte okuduğu şemadan türetilmiştir; burada geçen bir
descriptor üretimde de geçer diye bir garanti yoktur ama bilinen tüm yapısal
tuzaklar yakalanır.
"""
from __future__ import annotations

import re

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BITS = re.compile(r"^\d+(:\d+)?$")
_RETURNS = re.compile(r"^(u?int(8|16|32))(\[\d+\])?$")
_ACCESS = {"ro", "rw", "wo", "reserved"}
_I2C_STEPS = {"comment", "write_register", "read_register", "read_registers",
              "read_channels", "poll"}
_FLASH_STEPS = {"comment", "send_command", "read_command_address", "write_command_address"}
_CONVERT_KEYS = {"mask", "rshift", "signed_bits", "scale_num", "scale_den",
                 "scale_den_config", "offset", "clamp_min", "unsigned", "unit", "format"}


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_descriptor(doc) -> list[str]:
    """Yapısal hatalların listesi; boş liste = geçerli."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["descriptor bir YAML nesnesi (mapping) olmalı"]

    part = doc.get("part")
    if not isinstance(part, str) or not part.strip():
        errors.append("part: zorunlu ve boş olmayan bir metin olmalı (şematikteki parça adıyla birebir)")
    transport = doc.get("transport")
    ttype = ""
    if not isinstance(transport, dict):
        errors.append("transport: zorunlu blok (type/address_width/byte_order)")
    else:
        ttype = str(transport.get("type", ""))
        if ttype not in {"i2c", "spi"}:
            errors.append(f"transport.type: 'i2c' veya 'spi' olmalı (şu an: {ttype!r})")
        if transport.get("byte_order") not in (None, "big", "little"):
            errors.append("transport.byte_order: 'big' veya 'little' olmalı")

    registers = doc.get("registers", [])
    reg_fields: dict[str, set[str]] = {}
    reg_widths: dict[str, int] = {}
    if registers and not isinstance(registers, list):
        errors.append("registers: liste olmalı")
        registers = []
    seen_names: set[str] = set()
    seen_offsets: set[int] = set()
    for i, reg in enumerate(registers):
        where = f"registers[{i}]"
        if not isinstance(reg, dict):
            errors.append(f"{where}: nesne olmalı")
            continue
        name = reg.get("name")
        if not isinstance(name, str) or not _IDENT.match(name):
            errors.append(f"{where}.name: C makrosuna dönüşür — harf/rakam/alt çizgi olmalı (şu an: {name!r})")
            name = None
        elif name in seen_names:
            errors.append(f"{where}.name: '{name}' tekrar ediyor — register adları benzersiz olmalı")
        else:
            seen_names.add(name)
        offset = reg.get("offset")
        if not _is_int(offset) or offset < 0:
            errors.append(f"{where}.offset: 0 veya pozitif tam sayı olmalı (hex için 0x.. yazılabilir)")
        elif offset in seen_offsets:
            errors.append(f"{where}.offset: {offset:#x} tekrar ediyor — offsetler benzersiz olmalı")
        else:
            seen_offsets.add(offset)
        width = reg.get("width", 8)
        if not _is_int(width) or width <= 0:
            errors.append(f"{where}.width: pozitif tam sayı olmalı (bit cinsinden; 8/16/24)")
            width = 8
        access = reg.get("access", "rw")
        if access not in _ACCESS:
            errors.append(f"{where}.access: ro/rw/wo/reserved olmalı (şu an: {access!r})")
        field_names: set[str] = set()
        for j, field in enumerate(reg.get("fields") or []):
            fwhere = f"{where}.fields[{j}]"
            if not isinstance(field, dict):
                errors.append(f"{fwhere}: nesne olmalı")
                continue
            fname = field.get("name")
            if not isinstance(fname, str) or not fname:
                errors.append(f"{fwhere}.name: zorunlu")
            else:
                field_names.add(fname)
            bits = str(field.get("bits", ""))
            if not _BITS.match(bits):
                errors.append(f"{fwhere}.bits: '7' veya '6:5' biçiminde olmalı (şu an: {bits!r})")
        if name:
            reg_fields[name] = field_names
            reg_widths[name] = width

    commands = {c.get("name") for c in doc.get("commands") or [] if isinstance(c, dict)}
    for i, cmd in enumerate(doc.get("commands") or []):
        if not isinstance(cmd, dict) or not cmd.get("name") or not _is_int(cmd.get("opcode")):
            errors.append(f"commands[{i}]: name ve tam sayı opcode zorunlu")
        elif not _is_int(cmd.get("address_bytes")):
            errors.append(f"commands[{i}].address_bytes: tam sayı zorunlu (adres yoksa 0)")

    is_flash = bool(commands)
    is_memory = isinstance(doc.get("memory"), dict)
    step_ops = _FLASH_STEPS if is_flash else _I2C_STEPS

    operations = doc.get("operations", [])
    if not isinstance(operations, list):
        errors.append("operations: liste olmalı")
        operations = []
    op_names: set[str] = set()
    for i, op in enumerate(operations):
        where = f"operations[{i}]"
        if not isinstance(op, dict):
            errors.append(f"{where}: nesne olmalı")
            continue
        name = op.get("name")
        if not isinstance(name, str) or not _IDENT.match(name):
            errors.append(f"{where}.name: C fonksiyon adına dönüşür — harf/rakam/alt çizgi olmalı")
        elif name in op_names:
            errors.append(f"{where}.name: '{name}' tekrar ediyor")
        else:
            op_names.add(name)
        returns = op.get("returns")
        if returns is not None and not _RETURNS.match(str(returns)):
            errors.append(f"{where}.returns: uint8/uint16/uint32/int32 veya 'uint16[8]' biçiminde olmalı (şu an: {returns!r})")
        convert = op.get("convert")
        if convert is not None:
            if not isinstance(convert, dict):
                errors.append(f"{where}.convert: nesne olmalı")
            else:
                unknown = set(convert) - _CONVERT_KEYS
                if unknown:
                    errors.append(f"{where}.convert: bilinmeyen anahtar(lar): {sorted(unknown)}")
                if convert.get("format") not in (None, "pmbus_l11"):
                    errors.append(f"{where}.convert.format: yalnız 'pmbus_l11' desteklenir")
        steps = op.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{where}.steps: en az bir adımlı liste olmalı")
            continue
        scalar_bytes = 0
        for j, step in enumerate(steps):
            swhere = f"{where}.steps[{j}]"
            if not isinstance(step, dict) or "op" not in step:
                errors.append(f"{swhere}: 'op' alanlı nesne olmalı")
                continue
            sop = step["op"]
            if sop not in step_ops:
                errors.append(f"{swhere}.op: {sop!r} desteklenmiyor — bu transport için: {sorted(step_ops)}")
                continue
            if sop in {"write_register", "read_register", "read_registers", "read_channels", "poll"}:
                reg = step.get("reg")
                if reg not in reg_fields:
                    errors.append(f"{swhere}.reg: {reg!r} registers listesinde yok")
                    continue
            if sop == "poll":
                field = step.get("field")
                if field not in reg_fields.get(step.get("reg"), set()):
                    errors.append(f"{swhere}.field: {field!r} '{step.get('reg')}' registerının fields listesinde yok "
                                  f"(poll alan adıyla çalışır)")
                if step.get("until") not in (0, 1):
                    errors.append(f"{swhere}.until: 0 veya 1 olmalı")
            if sop == "read_register":
                scalar_bytes += 1
            if sop == "read_registers":
                length = step.get("length", 1)
                if not _is_int(length) or length <= 0:
                    errors.append(f"{swhere}.length: pozitif tam sayı olmalı")
                else:
                    scalar_bytes += length
                if returns is None or "[" in str(returns):
                    errors.append(f"{swhere}: read_registers skaler bir returns ister (uint32 gibi)")
            if sop == "read_channels" and (returns is None or "[" not in str(returns)):
                errors.append(f"{swhere}: read_channels dizi returns ister ('uint16[8]' gibi)")
            if sop in {"read_command_address", "write_command_address", "send_command"}:
                if step.get("cmd") not in commands:
                    errors.append(f"{swhere}.cmd: {step.get('cmd')!r} commands listesinde yok")
        if returns is not None and "[" not in str(returns) and scalar_bytes > 4 and not is_flash and not is_memory:
            errors.append(f"{where}: skaler dönüş için okunan toplam bayt 4'ü aşamaz (şu an {scalar_bytes})")

    if ttype == "spi" and not is_flash and not isinstance((transport or {}).get("register_model"), dict):
        errors.append("spi transport: TICS tarzı parçalar için transport.register_model bloğu ya da "
                      "flash için commands listesi zorunlu")
    return errors
