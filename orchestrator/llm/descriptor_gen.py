"""Referans metninden (datasheet register tablosu, surucu basligi) descriptor YAML uretimi - LLM + dogrulayici dongusu.

Akis: sema + iki ornek descriptor + S2C katalog op adlari + referans metni -> model YAML uretir ->
`descriptor_check.validate_descriptor` -> hata varsa hatalar ve onceki YAML modele geri verilir (en fazla
`rounds` tur). Kabul edilen aday KAYDEDILMEZ; kullanici onizler, dogrular ve user_descriptors'a kaydeder.
Deterministik uretim zinciri (codegen + QC) degismez: LLM yalniz descriptor'in ilk taslagini yazar.

Saha kaydi (2026-09-19, ADXL362 / Nexys A7 acl tasarimi, deepseek-flash): 1 turda dogrulayicidan gecen
descriptor, uretilen surucu kartta id 0xAD1DF2, x/y/z ve sicaklik okudu.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import yaml

from backend import s2cmsg
from orchestrator import descriptor_check
from orchestrator.llm.client import LlmClient, LlmConfig

_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA = _ROOT / "descriptors" / "_schema" / "descriptor.schema.json"
_EXAMPLE_SPI = _ROOT / "descriptors" / "adar1000.yaml"
_EXAMPLE_I2C = _ROOT / "descriptors" / "adt7420.yaml"
_FENCE_RE = re.compile(r"```(?:yaml|yml)?\s*(.*?)```", re.DOTALL)
MAX_ROUNDS = 5
MAX_REFERENCE_CHARS = 60_000


def catalog_operation_names() -> list[str]:
    """S2C-MSG katalogundaki cihaz op adlari: descriptor operations[].name bunlardan biri olmali (op id'ler kalici)."""
    catalog = s2cmsg.load_catalog()
    return sorted(op for op in catalog["by_op"] if op)


def _strip_fences(text: str) -> str:
    match = _FENCE_RE.search(text)
    return (match.group(1) if match else text).strip() + "\n"


def _example_head(path: Path, keep_lines: int) -> str:
    text = path.read_text(encoding="utf-8")
    head = "\n".join(text.splitlines()[:keep_lines])
    ops = text[text.index("operations:"):] if "operations:" in text else ""
    return head + "\n  # ... (diger registerlar)\n" + ops


def system_prompt(op_names: list[str]) -> str:
    return (
        "You write Spec2Code device descriptors (YAML). Output ONLY a YAML document, no prose, no code fences.\n"
        "Hard rules (violations are rejected by a validator and sent back to you):\n"
        "- Top-level keys exactly: descriptor_version \"1.0\", part, manufacturer, summary, transport, "
        "access_primitives, registers, operations, test_hints.\n"
        "- I2C register devices: transport {type: i2c, default_address: 0x.., byte_order: big|little}; "
        "access_primitives { write_register: {pattern: i2c_write_reg8}, read_register: {pattern: i2c_read_reg8} }.\n"
        "- SPI register devices: transport {type: spi, byte_order: little|big, register_model: {frame_bits (16|24|32), "
        "address_bits, address_shift, data_bits, rw_bit, write_value (0|1), fixed_bits (integer OR-ed into every frame, "
        "e.g. a constant command byte), spi_mode, max_sck_hz, default_order: exported}}; "
        "access_primitives { write_register_word: {pattern: spi_24bit_rw_addr_data} }. The generated read frame is "
        "(read_value << rw_bit) | (address << address_shift) | fixed_bits with read_value = 1 - write_value; "
        "the data byte is the last byte of the frame.\n"
        "- registers: list of {name, offset (hex), width (8|16), access (ro|rw|wo), reset (hex)}; names UPPER_SNAKE; "
        "optional fields: [{name, bits: \"7:4\" or \"0\"}].\n"
        "- operations: device_init with a single comment step (initial configuration words are supplied by the "
        "project, not the descriptor); read operations use ONLY read_register steps with fields reg (register name), "
        "optional mask, right_shift, shift. Multi-byte results: one read_register step per byte with shift (0, 8) "
        "combined per transport.byte_order; returns one of uint8|uint16|int16|uint32. No write steps in operations.\n"
        "- test_hints: { self_test: { description: \"...\" } } and optionally post_init_status: { reg: NAME }.\n"
        "- Operation names must come from the fixed S2C message catalog (op ids are permanent): "
        + ", ".join(op_names) + ". Do not invent other operation names.\n"
        "- Use the reference text values verbatim (addresses, resets, bit layout). Never invent registers. "
        "If the reference lacks a value, omit that register instead of guessing."
    )


def user_prompt(part: str, reference: str, hints: str, errors: list[str] | None, previous: str | None) -> str:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    parts = [
        "JSON schema of a descriptor:\n" + json.dumps(schema)[:12000],
        "Example descriptor 1 (SPI register model, 24-bit frame):\n" + _example_head(_EXAMPLE_SPI, 45),
        "Example descriptor 2 (I2C register device):\n" + _EXAMPLE_I2C.read_text(encoding="utf-8"),
        f"Reference text for the target part ({part}):\n" + reference[:MAX_REFERENCE_CHARS],
        f"Task: write the descriptor for {part}." + (f" Additional instructions from the engineer: {hints}" if hints.strip() else ""),
    ]
    if errors:
        parts.append(
            "Your previous YAML was rejected by the validator with these errors; fix ALL of them and return the "
            "full YAML again:\n- " + "\n- ".join(errors)
        )
        parts.append("Previous YAML:\n" + (previous or ""))
    return "\n\n".join(parts)


def validate_yaml_text(text: str) -> tuple[list[str], dict | None]:
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [f"YAML parse hatasi: {exc}"], None
    if not isinstance(doc, dict):
        return ["YAML kok nesnesi map degil"], None
    return descriptor_check.validate_descriptor(doc), doc


def generate_descriptor(llm: dict, part: str, reference: str, *, hints: str = "", rounds: int = 3,
                        client: LlmClient | None = None, emit=None) -> dict:
    """Dogrulayici donguseyle descriptor adayi uretir. Donus: {accepted, yaml, part, rounds: [{round, seconds, errors}]}.

    `client` testlerde sahte istemci vermek icindir; uretimde `LlmConfig.resolve(llm)` ile kurulur.
    """
    part = part.strip()
    if not part:
        raise ValueError("parca adi bos")
    if not reference.strip():
        raise ValueError("referans metni bos: datasheet register tablosunu ya da surucu basligini yapistir")
    rounds = max(1, min(int(rounds), MAX_ROUNDS))
    client = client or LlmClient(LlmConfig.resolve(llm))
    system = system_prompt(catalog_operation_names())
    log: list[dict] = []
    errors: list[str] | None = None
    previous: str | None = None
    text = ""
    for rnd in range(1, rounds + 1):
        t0 = time.time()
        messages = [{"role": "system", "content": system},
                    {"role": "user", "content": user_prompt(part, reference, hints, errors, previous)}]
        text = _strip_fences(client.chat(messages, temperature=0.1))
        errs, doc = validate_yaml_text(text)
        if not errs and doc is not None and str(doc.get("part", "")).strip().upper() != part.upper():
            errs = [f"part alani '{doc.get('part')}' istenen parca ile uyusmuyor: {part}"]
        entry = {"round": rnd, "seconds": round(time.time() - t0, 1), "errors": errs}
        log.append(entry)
        if emit is not None:
            emit({"event": "llm.descriptor.round", **entry})
        if not errs:
            return {"accepted": True, "yaml": text, "part": part, "rounds": log}
        errors, previous = errs, text
    return {"accepted": False, "yaml": text, "part": part, "rounds": log}
