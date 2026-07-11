"""Helpers for TI TICS Pro register-array exports.

TICS Pro exports device configuration as ordered SPI register words.  For clock
chips this ordered array is the source of truth; codegen validates and emits it
without sorting or trying to re-synthesize PLL settings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


# Below this many tokens, "every value happens to be <=0xFF" is plausibly a
# short, legitimate native word list (address 0, small value - occurs in
# real descriptors/fixtures) rather than a broken byte-triplet dump. Above
# it, a broken paste (saha hatasi: one lone byte token per message instead
# of one 24-bit word) is the far more likely explanation - real TICS Pro
# configs in this codebase top out at a handful of words, while a broken
# paste balloons to 3x the true message count (e.g. 378 vs 126).
_BYTE_DUMP_MIN_LEN = 12


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
        # Tolerance for configs already saved in the broken "one byte token
        # per array entry" shape (378 lone bytes instead of 126 24-bit
        # words) - saha hatasi: eski parser her bayt tokenini ayri bir word
        # olarak kaydetmisti. Each list item is normally one already-
        # canonical word (storage contract), so - unlike a free-text blob -
        # value range alone can't distinguish a short valid word list from
        # a broken byte dump here; require the same volume signal.
        #
        # Residual risk (accepted, code-reviewed): a list of >=12 entries,
        # count a multiple of 3, where every entry is a genuine native word
        # that all happen to be <=0xFF (register address 0x0000 for every
        # single entry, given address_bits=15/address_shift=8 on the LMK-
        # style model) would still be misread as a byte dump. This is not
        # a realistic TICS Pro export - a real init sequence does not
        # target the same zero address a dozen-plus times - and no purely
        # value-based heuristic can fully rule it out; volume remains the
        # best available signal for already-broken stored configs.
        if (
            len(raw) >= _BYTE_DUMP_MIN_LEN
            and len(raw) % 3 == 0
            and all(isinstance(item, str) and _is_single_number(item) for item in raw)
        ):
            values = [_int_value(item) for item in raw]
            if all(value <= 0xFF for value in values):
                return _group_bytes_into_words(values)

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
        values = [_int_value(token) for token in hex_tokens]
        # A lone token is always a single native word, whatever its size -
        # there is nothing to group it with.
        if len(values) == 1:
            return values
        byte_like = [value <= 0xFF for value in values]
        if all(byte_like) and len(values) >= _BYTE_DUMP_MIN_LEN:
            # Every token is <=0xFF AND there are enough of them that this
            # is implausible as a short native word list (a real config
            # with 12+ entries essentially never has ALL its words this
            # small - would need every register's address and upper value
            # bits to be zero). Below the threshold, "all small" is not a
            # reliable signal by itself (e.g. a genuine 3-word native list
            # can coincidentally have every value <=0xFF - see the repo's
            # own ?demo seed, frontend/src/lib/demoSeed.ts), so it must not
            # be regrouped there. At/above threshold, group sequentially in
            # 3s rather than storing each byte token as its own bogus
            # 24-bit register word (saha hatasi: company LMK config pasted
            # as-is, one "0xAA, 0xBB, 0xCC," line per message).
            return _group_bytes_into_words(values)
        if any(byte_like) and len(values) >= _BYTE_DUMP_MIN_LEN:
            # Some tokens look like lone bytes (<=0xFF) and some look like
            # full 24-bit words, AND there are enough tokens that this is
            # plausibly a byte-triplet dump rather than a short native word
            # list with an incidentally small value. Can't safely tell
            # which interpretation is right - refuse rather than guessing.
            raise ValueError(
                "TICS Pro girisi belirsiz: bazi satirlar tek bayt (<=0xFF), "
                "bazilari 24-bit word gibi gorunuyor. 3-bayt/mesaj format "
                "icin butun tokenlar 0x00-0xFF araliginda olmali."
            )
        return values
    tokens = re.findall(r"(?<![A-Za-z0-9_])-?\d+(?![A-Za-z0-9_])", raw)
    return [_int_value(token) for token in tokens]


def _group_bytes_into_words(values: list[int]) -> list[int]:
    if len(values) % 3 != 0:
        raise ValueError(
            f"3-bayt/mesaj formatinda satir sayisi 3'un kati olmali "
            f"(bulunan bayt tokeni sayisi: {len(values)})"
        )
    return [
        (values[i] << 16) | (values[i + 1] << 8) | values[i + 2]
        for i in range(0, len(values), 3)
    ]


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
