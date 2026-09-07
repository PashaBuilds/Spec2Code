"""Yazilabilir veri koku (outputs/, specs/, uploads/, catalog/imported.json).

Kaynaktan calisirken repo kokudur. PyInstaller --onefile paketinde ise modul
dosyalari gecici `_MEIxxxx` klasorune acilir ve `Path(__file__)` tabanli kokler
ORAYI gosterir: uretilen kod, kaydedilen spec'ler ve yuklenen XSA'lar uygulama
kapaninca Windows tarafindan SILINEN bir klasore yaziliyordu (SAHA 2026-09-07:
`C:\\Users\\<u>\\AppData\\Local\\Temp\\1\\_MEI178802\\outputs\\edv4_db`).
Paketli uygulamada veri koku exe'nin YANIDIR; `SPEC2CODE_DATA_DIR` ortam
degiskeni her iki modda da onceliklidir (tasinabilir kurulum / otomasyon).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def data_root() -> Path:
    env = os.environ.get("SPEC2CODE_DATA_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _REPO_ROOT


def bundle_root() -> Path:
    """Salt-okunur paket icerigi (descriptors/, platforms/, schemas/, frontend/dist)."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else _REPO_ROOT
