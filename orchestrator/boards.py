"""Kart (fiziksel PCB) katmani — tek dogruluk kaynagi.

Kart, elektriksel modele DIK bir konum katmanidir: cihazin attach.controller_id /
via_mux alanlari degismez, board_id yalnizca fiziksel yeri soyler. `boards`
tanimli degilse sistem tek ortuk ana karttan ibaret sayilir ve uretilen cikti
bugunku duzeninde kalir (bkz. docs/superpowers/specs/2026-08-04-multi-board-topology-design.md).
"""
from __future__ import annotations

import re

MAIN_BOARD_ID = "main"

#: Turkce harfler ASCII karsiliklarina katlanir (C tanimlayici uretimi icin).
_FOLD = {
    "ı": "i", "İ": "I", "ş": "s", "Ş": "S", "ğ": "g", "Ğ": "G",
    "ü": "u", "Ü": "U", "ö": "o", "Ö": "O", "ç": "c", "Ç": "C",
}


def _fold_ascii(text: str) -> str:
    return "".join(_FOLD.get(ch, ch) for ch in text)


def _words(name: str) -> list[str]:
    folded = _fold_ascii(name or "")
    return [w for w in re.split(r"[^A-Za-z0-9]+", folded) if w]


def board_identifier(name: str) -> str:
    """Kart adindan C camelCase tanimlayici: "RF Kart" -> "rfKart"."""
    words = _words(name)
    if not words:
        return "kart"
    head = words[0].lower()
    tail = "".join(w[:1].upper() + w[1:].lower() for w in words[1:])
    identifier = head + tail
    if not identifier[0].isalpha():
        identifier = "k" + identifier
    return identifier


def board_dirname(name: str) -> str:
    """Kart adindan snake_case klasor adi: "RF Kart" -> "rf_kart"."""
    words = _words(name)
    if not words:
        return "kart"
    dirname = "_".join(w.lower() for w in words)
    if not dirname[0].isalpha():
        dirname = "k_" + dirname
    return dirname


def assert_unique_identifiers(board_list: list[dict]) -> None:
    """Iki kart ayni C tanimlayiciya duserse sessiz cakisma yerine acik hata."""
    seen: dict[str, str] = {}
    for board in board_list:
        identifier = board_identifier(str(board.get("name", "")))
        previous = seen.get(identifier)
        if previous is not None:
            raise ValueError(
                f"kart adlari ayni C tanimlayiciya dusuyor ('{identifier}'): "
                f"'{previous}' ve '{board.get('name')}' — kart adlarini ayirin")
        seen[identifier] = str(board.get("name", ""))


def boards_declared(spec: dict) -> bool:
    """Kullanici kart tanimladi mi? TUM 'kart modu' kararlari buna bakar."""
    return bool(spec.get("boards"))


def normalized_boards(spec: dict) -> list[dict]:
    """Kart listesi; tanimli degilse tek ortuk ana kart dondurur."""
    declared = spec.get("boards") or []
    if declared:
        return [{**board, "implicit": False} for board in declared]
    name = str((spec.get("project") or {}).get("name") or "Ana Kart")
    return [{"id": MAIN_BOARD_ID, "name": name, "role": "main", "implicit": True}]


def board_id_of(entity: dict) -> str:
    """Cihaz/mux'un kart kimligi; verilmemisse ana kart."""
    return str(entity.get("board_id") or MAIN_BOARD_ID)


def main_board_id(spec: dict) -> str:
    for board in normalized_boards(spec):
        if str(board.get("role")) == "main":
            return str(board["id"])
    return MAIN_BOARD_ID
