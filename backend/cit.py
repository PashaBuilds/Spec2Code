"""CIT (cihaz ici test) yanit govdesi cozumu (Task 8).

Kart SBoardCit'i tek atimda doldurur (bkz. orchestrator/codegen.py
_testbench_cit_section + docs/superpowers/specs/2026-07-09-s2cmsg-cit-yatt-design.md
bolum 4). Bu modul CIT_RUN/CIT_READ yanit govdesini (SYanitOnek onegi
COKTAN ATILMIS, yani uiIstekSayac(4)+uiDurum(4)+SBoardCit) manifest
``cit.olcumler`` sirasiyla Python sozlugune cevirir.

SBoardCit bayt yerlesimi (little-endian, packed):
    uiSayac(4) + uiZaman(4) + bayrak_words + arrOlcum[N] * SBoardCitOlcum{iDeger(4) uiHam(4) uiDurum(4)}
bayrak_words = ((N+31)//32)*4 bayt; bit i = olcum i (LSB-first, manifest
cit.olcumler[i] ile birebir — Task 7 kararina sadakat).
"""
from __future__ import annotations

import struct

_PREFIX_SIZE = 8  # uiIstekSayac(4) + uiDurum(4)
_CIT_HEADER_SIZE = 8  # uiSayac(4) + uiZaman(4)
_OLCUM_SIZE = 12  # iDeger(4) + uiHam(4) + uiDurum(4)


def _flag_words_size(n: int) -> int:
    return ((n + 31) // 32) * 4


def decode_board_cit(body: bytes, manifest: dict) -> dict:
    """CIT_RUN/CIT_READ yanit govdesini manifest cit.olcumler sirasiyla coz.

    ``body`` = uiIstekSayac(4) + uiDurum(4) + SBoardCit (SYanitOnek disinda
    kalan gercek CIT govdesi — TestbenchSessionManager.send_named() bu
    govdeyi ham dondurur).

    Uzunluk manifest'teki olcum sayisiyla uyusmuyorsa (kart farkli bir
    kontrat/uretimden calisiyor) ValueError ile net Turkce hata verir —
    sessiz yanlis-hizalanmis veri okumasi yerine.
    """
    cit_section = manifest.get("cit") if isinstance(manifest, dict) else None
    if not cit_section or not isinstance(cit_section, dict):
        raise ValueError("manifest'te cit bolumu yok — bu uretimde CIT olcumu yok")
    olcumler_manifest = cit_section.get("olcumler") or []
    n = len(olcumler_manifest)
    flag_words = _flag_words_size(n)
    expected_size = _PREFIX_SIZE + _CIT_HEADER_SIZE + flag_words + n * _OLCUM_SIZE

    if len(body) < _PREFIX_SIZE:
        raise ValueError(
            "CIT yanit govdesi cok kisa (SYanitOnek okunamadi) — "
            "kart CIT yerlesimi manifest ile uyusmuyor: kodu yeniden uretin/yukleyin"
        )

    istek_sayac, durum = struct.unpack_from("<II", body, 0)

    if len(body) != expected_size:
        raise ValueError(
            f"CIT yanit govdesi boyu uyusmuyor (beklenen {expected_size}B, gelen {len(body)}B, "
            f"olcum sayisi={n}) — kart CIT yerlesimi manifest ile uyusmuyor — "
            "kodu yeniden uretin/yukleyin"
        )

    cit = body[_PREFIX_SIZE:]
    uiSayac, uiZaman = struct.unpack_from("<II", cit, 0)
    flags = int.from_bytes(cit[_CIT_HEADER_SIZE:_CIT_HEADER_SIZE + flag_words], "little")
    olcum_off = _CIT_HEADER_SIZE + flag_words

    olcumler: list[dict] = []
    for i, meta in enumerate(olcumler_manifest):
        iDeger, uiHam, uiOlcumDurum = struct.unpack_from("<iII", cit, olcum_off + i * _OLCUM_SIZE)
        # Kart bayragi = OKUMA BASARISI (limit degil). OK/NOK karari HOST'ta canli
        # limitle yapilir; min/max/severity/enabled burada yalniz VARSAYILAN (manifest)
        # olarak tasinir, CIT ekrani store override'ini uygular (koda gomulmez).
        read_ok = bool(flags & (1 << i))
        olcumler.append({
            "index": meta.get("index", i),
            "name": meta.get("name", ""),
            "cname": meta.get("cname", ""),
            "part": meta.get("part", ""),
            "device": meta.get("device", ""),
            "op": meta.get("op", ""),
            "unit": meta.get("unit"),
            "raw": uiHam,
            "value": iDeger,
            "read_ok": read_ok,
            "durum": uiOlcumDurum,
            "min": meta.get("min"),
            "max": meta.get("max"),
            "severity": meta.get("severity", "warning"),
            "enabled": bool(meta.get("enabled", True)),
        })

    return {
        "durum": durum,
        "sayac": uiSayac,
        "zaman": uiZaman,
        "istek_sayac": istek_sayac,
        "olcumler": olcumler,
    }
