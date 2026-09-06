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


def part_slug(part: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(part).lower()) or "cihaz"


def normalize_device_ids(spec: dict) -> dict:
    """Cihaz/mux kimliklerini `<kart>_<parca>[_<n>]` kuralina ceker (frontend
    lib/boards.ts::normalizeDeviceIds ile AYNI kural); yeni spec kopyasi dondurur.

    Kart oneki kart adinin snake_case'i (kart tanimsizsa "kart"); ayni kartta ayni parcadan
    birden fazla cihaz varsa ekleme sirasiyla _1, _2 ... (tek ise sonek yok).
    """
    board_list = normalized_boards(spec)
    declared = bool(spec.get("boards"))
    by_id = {str(b["id"]): b for b in board_list}
    main_id = main_board_id(spec)

    def prefix_of(item: dict) -> str:
        if not declared:
            return "kart"
        bid = str(item.get("board_id") or main_id)
        board = by_id.get(bid) or by_id.get(main_id) or board_list[0]
        return board_dirname(str(board["name"]))

    def assign(items: list[dict]) -> dict[str, str]:
        counts: dict[str, int] = {}
        for item in items:
            key = f"{prefix_of(item)}_{part_slug(item.get('part', ''))}"
            counts[key] = counts.get(key, 0) + 1
        seen: dict[str, int] = {}
        mapping: dict[str, str] = {}
        for item in items:
            key = f"{prefix_of(item)}_{part_slug(item.get('part', ''))}"
            seen[key] = seen.get(key, 0) + 1
            mapping[str(item.get("id"))] = f"{key}_{seen[key]}" if counts[key] > 1 else key
        return mapping

    devices = [dict(d) for d in spec.get("devices", [])]
    muxes = [dict(m) for m in spec.get("muxes", [])]
    dev_map, mux_map = assign(devices), assign(muxes)
    for d in devices:
        d["id"] = dev_map.get(str(d.get("id")), d.get("id"))
        via = (d.get("attach") or {}).get("via_mux")
        if isinstance(via, dict) and via.get("mux_id") in mux_map:
            d["attach"] = {**d["attach"], "via_mux": {**via, "mux_id": mux_map[via["mux_id"]]}}
    for m in muxes:
        m["id"] = mux_map.get(str(m.get("id")), m.get("id"))
    return {**spec, "devices": devices, "muxes": muxes}
