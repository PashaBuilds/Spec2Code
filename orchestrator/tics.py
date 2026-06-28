"""Helpers for TI TICS Pro register-array exports.

TICS Pro exports device configuration as ordered SPI register words.  For clock
chips this ordered array is the source of truth; codegen validates and emits it
without sorting or trying to re-synthesize PLL settings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TicsRegisterWord:
    word: int
    address: int
    value: int
    rw: int

    @property
    def bytes_msb_first(self) -> list[int]:
        return [
            (self.word >> 16) & 0xFF,
            (self.word >> 8) & 0xFF,
            self.word & 0xFF,
        ]


def has_tics_register_model(descriptor: dict[str, Any]) -> bool:
    model = register_model(descriptor)
    return bool(model.get("ticspro_words"))


def register_model(descriptor: dict[str, Any]) -> dict[str, Any]:
    transport = descriptor.get("transport")
    if not isinstance(transport, dict):
        return {}
    model = transport.get("register_model")
    return model if isinstance(model, dict) else {}


def normalize_words(config: Any) -> list[int]:
    if not isinstance(config, dict):
        return []
    raw = (
        config.get("ticspro_registers")
        if "ticspro_registers" in config
        else config.get("ticspro_array", config.get("register_words"))
    )
    return parse_words(raw)


def parse_words(raw: Any) -> list[int]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return _parse_words_from_text(raw)
    if isinstance(raw, (int, float)):
        return [int(raw)]
    if isinstance(raw, list):
        out: list[int] = []
        for item in raw:
            if isinstance(item, dict):
                item = item.get("word", item.get("value"))
            if isinstance(item, str) and not _is_single_number(item):
                out.extend(_parse_words_from_text(item))
            elif item is not None:
                out.append(_int_value(item))
        return out
    return []


def decode_word(word: int, model: dict[str, Any]) -> TicsRegisterWord:
    address_bits = int(model.get("address_bits", 7))
    address_shift = int(model.get("address_shift", model.get("data_bits", 16)))
    data_bits = int(model.get("data_bits", 16))
    rw_bit = int(model.get("rw_bit", 23))
    address_mask = (1 << address_bits) - 1
    data_mask = (1 << data_bits) - 1
    return TicsRegisterWord(
        word=word,
        address=(word >> address_shift) & address_mask,
        value=word & data_mask,
        rw=(word >> rw_bit) & 0x1,
    )


def decode_words(words: list[int], model: dict[str, Any]) -> list[TicsRegisterWord]:
    return [decode_word(word, model) for word in words]


def word_hex(word: int) -> str:
    return f"0x{word & 0xFFFFFF:06X}"


def c_word(word: int) -> str:
    return f"0x{word & 0xFFFFFF:06X}U"


def validate_words(words: list[int], model: dict[str, Any]) -> list[str]:
    frame_bits = int(model.get("frame_bits", 24))
    max_word = (1 << frame_bits) - 1
    write_value = int(model.get("write_value", 0))
    issues: list[str] = []
    for index, word in enumerate(words):
        if not 0 <= word <= max_word:
            issues.append(f"{index}: word {word_hex(word)} does not fit in {frame_bits} bits")
            continue
        decoded = decode_word(word, model)
        if decoded.rw != write_value:
            issues.append(
                f"{index}: word {word_hex(word)} has R/W={decoded.rw}, expected write value {write_value}"
            )
    return issues


def _parse_words_from_text(raw: str) -> list[int]:
    hex_tokens = re.findall(r"0[xX][0-9A-Fa-f]+", raw)
    if hex_tokens:
        return [_int_value(token) for token in hex_tokens]
    tokens = re.findall(r"(?<![A-Za-z0-9_])-?\d+(?![A-Za-z0-9_])", raw)
    return [_int_value(token) for token in tokens]


def _is_single_number(raw: str) -> bool:
    return bool(re.fullmatch(r"\s*(?:0[xX][0-9A-Fa-f]+|-?\d+)\s*", raw))


def _int_value(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value.strip(), 0)
    return int(value)
