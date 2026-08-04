# Çok-Kartlı Sistem Topolojisi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kartları (fiziksel PCB'leri) birinci sınıf hale getirmek: şematikte kutu, üretimde klasör + kart fonksiyonları, CİT/Test Bench'te grup, YATT'ta topoloji bölümü.

**Architecture:** Kart, elektriksel modele **dik bir konum katmanıdır** (spec Yaklaşım A). Cihazın `attach.controller_id`/`via_mux` alanları DEĞİŞMEZ; yeni `board_id` alanı fiziksel yeri söyler. Konnektörler hattın kartlar arası geçişini belgeler. Kart tanımlanmadığında üretilen çıktı bugünküyle bayt-bayt aynıdır.

**Tech Stack:** Python 3 (backend/orchestrator), Jinja2 şablonlar, React 18 + React Flow (şematik), zustand, TypeScript, unittest.

**Spec:** `docs/superpowers/specs/2026-08-04-multi-board-topology-design.md`

## Global Constraints

- **Değişmezlik kuralı (en kritik):** `spec["boards"]` yoksa/boşsa üretilen tüm dosyalar bugünküyle **bayt-bayt aynı** olmalı — yol, içerik, manifest. Golden-diff ile kanıtlanacak.
- **CİT bit sırası değişmez:** `SBoardCit` bit sözleşmesi ve `boardCitRun()` adı korunur; kart bilgisi yalnız manifest üzerinden taşınır (`cit.olcumler[i].board_id`).
- Denetleyiciler her zaman ana karttadır; `controllers[]` **board_id ALMAZ**.
- Tam olarak bir `role: "main"` kart olmalı.
- Üretilen C, `docs/kodlama_standardi.md` + `std/default.ruleset.json`'a uyar (Hungarian önekler, Allman, `unsigned int`, stdint yok); naming linter 0 ihlal.
- Testler: `.venv/Scripts/python.exe -m unittest discover -s tests -q` (gcc `C:/msys64/mingw64/bin` PATH'te) — taban **407 geçer**. Frontend: `cd frontend && npm run build` → 0 TS hatası.
- LF satır sonları (Python/TS/test kaynakları); üretilen C çıktısı CRLF (mevcut davranış).
- Türkçe hata mesajları mevcut üslupla.

---

### Task 1: Şema + model + doğrulama (boards / connectors / board_id)

**Files:**
- Modify: `schemas/project.spec.schema.json` (üst seviye `properties`; `devices.items.properties`; `muxes.items.properties`)
- Create: `orchestrator/boards.py` (kart yardımcıları — tek doğruluk kaynağı)
- Modify: `backend/validators/wiring.py:67` (`validate_wiring`)
- Modify: `frontend/src/lib/types.ts` (Board, Connector tipleri + Device/Mux'a `board_id`)
- Test: `tests/test_boards_model.py` (yeni)

**Interfaces:**
- Produces (sonraki görevler bunlara güvenir):
  - `orchestrator/boards.py`:
    - `MAIN_BOARD_ID = "main"`
    - `def normalized_boards(spec: dict) -> list[dict]` — `boards` yoksa `[{"id":"main","name":<proje adı>,"role":"main","implicit":True}]` döner; varsa olduğu gibi (her girdiye `implicit: False`).
    - `def boards_declared(spec: dict) -> bool` — `bool(spec.get("boards"))`. **Tüm "kart modu" kararları buna bakar.**
    - `def board_id_of(entity: dict) -> str` — `entity.get("board_id") or MAIN_BOARD_ID`.
    - `def board_identifier(name: str) -> str` — C camelCase tanımlayıcı ("RF Kart" → `rfKart`).
    - `def board_dirname(name: str) -> str` — snake_case klasör ("RF Kart" → `rf_kart`).
    - `def assert_unique_identifiers(boards: list[dict]) -> None` — çakışmada `ValueError`.

- [ ] **Step 1: Failing test yaz** — `tests/test_boards_model.py`:

```python
import unittest

from orchestrator import boards


class BoardIdentifierTests(unittest.TestCase):
    def test_turkish_names_fold_to_ascii_camel_case(self) -> None:
        self.assertEqual(boards.board_identifier("RF Kart"), "rfKart")
        self.assertEqual(boards.board_identifier("Güç Kartı"), "gucKarti")
        self.assertEqual(boards.board_identifier("IO-Şase 2"), "ioSase2")
        self.assertEqual(boards.board_identifier("ana kart"), "anaKart")

    def test_dirname_is_snake_case_ascii(self) -> None:
        self.assertEqual(boards.board_dirname("RF Kart"), "rf_kart")
        self.assertEqual(boards.board_dirname("Güç Kartı"), "guc_karti")

    def test_duplicate_identifiers_raise(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            boards.assert_unique_identifiers([
                {"id": "a", "name": "RF Kart"},
                {"id": "b", "name": "rf  kart"},
            ])
        self.assertIn("rfKart", str(ctx.exception))


class NormalizedBoardsTests(unittest.TestCase):
    def test_missing_boards_yields_one_implicit_main(self) -> None:
        spec = {"project": {"name": "demo"}}
        got = boards.normalized_boards(spec)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["id"], boards.MAIN_BOARD_ID)
        self.assertEqual(got[0]["name"], "demo")
        self.assertTrue(got[0]["implicit"])
        self.assertFalse(boards.boards_declared(spec))

    def test_declared_boards_are_kept(self) -> None:
        spec = {"project": {"name": "demo"},
                "boards": [{"id": "main", "name": "Ana Kart", "role": "main"},
                           {"id": "rf", "name": "RF Kart", "role": "peripheral"}]}
        got = boards.normalized_boards(spec)
        self.assertEqual([b["id"] for b in got], ["main", "rf"])
        self.assertFalse(got[0]["implicit"])
        self.assertTrue(boards.boards_declared(spec))

    def test_board_id_of_defaults_to_main(self) -> None:
        self.assertEqual(boards.board_id_of({"id": "u1"}), boards.MAIN_BOARD_ID)
        self.assertEqual(boards.board_id_of({"id": "u1", "board_id": "rf"}), "rf")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Testin FAIL ettiğini gör**

Run: `.venv/Scripts/python.exe -m unittest tests.test_boards_model -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orchestrator.boards'`

- [ ] **Step 3: `orchestrator/boards.py` yaz**

```python
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
```

- [ ] **Step 4: Testin GEÇTİĞİNİ gör**

Run: `.venv/Scripts/python.exe -m unittest tests.test_boards_model -v`
Expected: PASS (7 test)

- [ ] **Step 5: Şemayı genişlet**

`schemas/project.spec.schema.json` üst seviye `properties` içine (mevcut `muxes` girdisinin yanına) ekle:

```json
"boards": {
  "type": "array",
  "description": "Fiziksel kartlar. Verilmezse sistem tek ortuk ana karttan ibaret sayilir.",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["id", "name", "role"],
    "properties": {
      "id": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
      "name": { "type": "string", "minLength": 1 },
      "role": { "type": "string", "enum": ["main", "peripheral"] },
      "notes": { "type": "string" }
    }
  }
},
"connectors": {
  "type": "array",
  "description": "Kartlar arasi fiziksel baglanti (belgeleyicidir; elektriksel yolu degistirmez).",
  "items": {
    "type": "object",
    "additionalProperties": false,
    "required": ["id", "name", "from_board", "to_board", "bus"],
    "properties": {
      "id": { "type": "string", "pattern": "^[a-z][a-z0-9_]*$" },
      "name": { "type": "string", "minLength": 1 },
      "from_board": { "type": "string" },
      "to_board": { "type": "string" },
      "bus": {
        "type": "object",
        "additionalProperties": false,
        "required": ["controller_id"],
        "properties": {
          "controller_id": { "type": "string" },
          "via_mux": {
            "type": "object",
            "additionalProperties": false,
            "required": ["mux_id", "channel"],
            "properties": {
              "mux_id": { "type": "string" },
              "channel": { "type": "integer", "minimum": 0 }
            }
          }
        }
      },
      "notes": { "type": "string" }
    }
  }
}
```

`devices.items.properties` ve `muxes.items.properties` içine ekle:

```json
"board_id": { "type": "string", "description": "Cihazin bulundugu kart; verilmezse ana kart." }
```

- [ ] **Step 6: Doğrulama kurallarını ekle**

`backend/validators/wiring.py` — `validate_wiring` içinde, cihaz döngüsünden ÖNCE kart/konnektör bloğu:

```python
    from orchestrator import boards as boards_mod

    board_list = spec.get("boards") or []
    board_ids = {str(b.get("id")) for b in board_list}
    if board_list:
        mains = [b for b in board_list if str(b.get("role")) == "main"]
        if len(mains) != 1:
            add("error", "/boards",
                f"tam olarak bir 'main' kart olmali (bulunan: {len(mains)})")
        try:
            boards_mod.assert_unique_identifiers(board_list)
        except ValueError as exc:
            add("error", "/boards", str(exc))
        seen_ids: set[str] = set()
        for index, board in enumerate(board_list):
            bid = str(board.get("id", ""))
            if bid in seen_ids:
                add("error", f"/boards/{index}/id", f"kart kimligi tekrar ediyor: {bid}")
            seen_ids.add(bid)

    controller_ids = {str(c.get("id")) for c in spec.get("controllers", [])}
    mux_by_id = {str(m.get("id")): m for m in spec.get("muxes", [])}
    for index, connector in enumerate(spec.get("connectors", []) or []):
        path = f"/connectors/{index}"
        for side in ("from_board", "to_board"):
            value = str(connector.get(side, ""))
            if value not in board_ids:
                add("error", f"{path}/{side}", f"tanimsiz kart: {value}")
        if connector.get("from_board") == connector.get("to_board"):
            add("error", f"{path}/to_board", "konnektorun iki ucu ayni kart olamaz")
        bus = connector.get("bus") or {}
        if str(bus.get("controller_id", "")) not in controller_ids:
            add("error", f"{path}/bus/controller_id",
                f"tanimsiz denetleyici: {bus.get('controller_id')}")
        via = bus.get("via_mux")
        if via:
            mux = mux_by_id.get(str(via.get("mux_id", "")))
            if mux is None:
                add("error", f"{path}/bus/via_mux/mux_id",
                    f"tanimsiz switch: {via.get('mux_id')}")
            else:
                channels = _int_value(mux.get("channels")) or 0
                channel = _int_value(via.get("channel"))
                if channel is None or not (0 <= channel < channels):
                    add("error", f"{path}/bus/via_mux/channel",
                        f"kanal 0..{channels - 1} araliginda olmali (verilen: {via.get('channel')})")

    # Cihaz/mux board_id'leri var olan karti gostermeli.
    if board_list:
        for index, device in enumerate(spec.get("devices", [])):
            bid = device.get("board_id")
            if bid is not None and str(bid) not in board_ids:
                add("error", f"/devices/{index}/board_id", f"tanimsiz kart: {bid}")
        for index, mux in enumerate(spec.get("muxes", [])):
            bid = mux.get("board_id")
            if bid is not None and str(bid) not in board_ids:
                add("error", f"/muxes/{index}/board_id", f"tanimsiz kart: {bid}")
        # Ana kart disindaki bir kartta cihaz var ama o hatti belgeleyen
        # konnektor yoksa UYARI (hata degil — model calisir, dokuman eksik).
        documented = {str(c.get("to_board")) for c in (spec.get("connectors") or [])}
        main_id = boards_mod.main_board_id(spec)
        populated = {boards_mod.board_id_of(d) for d in spec.get("devices", [])}
        for bid in sorted(populated - {main_id} - documented):
            add("warning", "/connectors",
                f"'{bid}' kartinda cihaz var ama baglantisini belgeleyen konnektor yok")
```

- [ ] **Step 7: Doğrulama testlerini ekle ve koş**

`tests/test_boards_model.py` içine `WiringValidationTests` sınıfı ekle: (a) iki `main` kart → hata; (b) tanımsız `board_id` → hata; (c) konnektörün iki ucu aynı → hata; (d) geçersiz mux kanalı → hata; (e) belgesiz uzak kart → **warning** (hata değil); (f) `boards` yokken hiçbir yeni hata üretilmez.

Run: `.venv/Scripts/python.exe -m unittest tests.test_boards_model -q`
Expected: PASS

- [ ] **Step 8: Frontend tipleri**

`frontend/src/lib/types.ts` — `Mux` arayüzünün yanına:

```typescript
export interface Board {
  id: string;
  name: string;
  role: "main" | "peripheral";
  notes?: string;
}
export interface ConnectorBus {
  controller_id: string;
  via_mux?: ViaMux | null;
}
export interface Connector {
  id: string;
  name: string;
  from_board: string;
  to_board: string;
  bus: ConnectorBus;
  notes?: string;
}
```
`Device` ve `Mux` arayüzlerine `board_id?: string;` ekle.

- [ ] **Step 9: Tam paket + build**

Run: `.venv/Scripts/python.exe -m unittest discover -s tests -q` (gcc PATH'te)
Expected: OK, regresyon yok (taban 407 + yeni testler)
Run: `cd frontend && npm run build`
Expected: 0 TS hatası

- [ ] **Step 10: Commit**

```bash
git add schemas/project.spec.schema.json orchestrator/boards.py backend/validators/wiring.py frontend/src/lib/types.ts tests/test_boards_model.py
git commit -m "Kart katmani: sema (boards/connectors/board_id) + model yardimcilari + dogrulama"
```

---

### Task 2: Codegen — kart klasörleri + kart modülleri + manifest

**Files:**
- Modify: `orchestrator/cmodel.py:107-118` (`CUnit`'e `board_id`), `orchestrator/cmodel.py:2304` (`build_units` — üniteye kart ata)
- Modify: `orchestrator/codegen.py:6543` (`generate` — yazım yolları), `orchestrator/codegen.py` manifest üreticisi (`_testbench_manifest`)
- Create: `orchestrator/codegen.py` içinde `_board_module_header(...)` / `_board_module_source(...)` üreteçleri
- Test: `tests/test_board_codegen.py` (yeni)

**Interfaces:**
- Consumes: Task 1'in `orchestrator/boards.py` API'si (`boards_declared`, `normalized_boards`, `board_id_of`, `board_identifier`, `board_dirname`, `main_board_id`).
- Produces:
  - `CUnit.board_id: str` (varsayılan `"main"`).
  - Kart tanımlıysa yazım yolu `drivers/<board_dirname>/<module>.{h,c}`; tanımlı değilse `drivers/<module>.{h,c}` (bugünkü).
  - Kart başına modül: `drivers/<board_dirname>/<board_dirname>.{h,c}` → `int <ident>Init(void);`, `void <ident>CitRun(SBoardCit* spCit);`, `int <ident>SelfTest(void);`
  - Manifest: üst seviye `"boards"`, `"connectors"`; `devices[]` girdilerine `"board_id"`; `cit.olcumler[]` girdilerine `"board_id"`.

- [ ] **Step 1: Golden-invariant testini önce yaz** (en kritik koruma)

`tests/test_board_codegen.py`:

```python
"""Kart katmani codegen: kart tanimli DEGILKEN cikti bugunku ile ayni kalmali."""
import filecmp
import shutil
import tempfile
import unittest
from pathlib import Path

from orchestrator import codegen


def _base_spec(name: str) -> dict:
    return {
        "project": {"name": name, "platform": "zynq_ultrascale",
                    "target_core": "psu_cortexa53_0", "runtime": "bare_metal",
                    "testbench_transport": "uart"},
        "zones": [], "cores": [],
        "controllers": [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XIicPs", "driver": "XIicPs",
             "base_address": "0xFF020000", "device_id": 0, "source": "ps", "zone": "ps"},
            {"id": "ps_uart_0", "type": "uart", "instance": "XUartPs", "driver": "XUartPs",
             "base_address": "0xFF000000", "device_id": 0, "source": "ps", "zone": "ps"},
        ],
        "muxes": [{"id": "u10_tca9548a", "part": "TCA9548A", "controller_id": "ps_i2c_0",
                   "i2c_address": "0x70", "channels": 8}],
        "devices": [
            {"id": "u1_ltc2991", "part": "LTC2991",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x48",
                        "via_mux": {"mux_id": "u10_tca9548a", "channel": 0}}},
            {"id": "u2_tmp101", "part": "TMP101",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x49",
                        "via_mux": {"mux_id": "u10_tca9548a", "channel": 3}}},
        ],
    }


class BoardlessOutputIsUnchangedTests(unittest.TestCase):
    def test_spec_without_boards_generates_todays_flat_layout(self) -> None:
        spec = _base_spec("boardless_demo")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "p"
            codegen.generate(spec, out)
            # Duz duzen: drivers/ altinda dogrudan .c/.h, alt klasor YOK.
            self.assertTrue((out / "drivers" / "ltc2991.c").is_file())
            self.assertTrue((out / "drivers" / "tmp101.c").is_file())
            subdirs = [p for p in (out / "drivers").iterdir() if p.is_dir()]
            self.assertEqual(subdirs, [], f"kart tanimsizken alt klasor olmamali: {subdirs}")
            # Kart modulu de uretilmemeli.
            self.assertFalse(list((out / "drivers").glob("*kart*")))

    def test_declaring_boards_is_the_only_trigger(self) -> None:
        """Ayni spec + boards -> kart duzeni; boards yok -> duz duzen."""
        spec = _base_spec("trigger_demo")
        boarded = {**spec,
                   "boards": [{"id": "main", "name": "Ana Kart", "role": "main"},
                              {"id": "rf", "name": "RF Kart", "role": "peripheral"}]}
        boarded["devices"] = [
            {**spec["devices"][0], "board_id": "main"},
            {**spec["devices"][1], "board_id": "rf"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            flat = Path(tmp) / "flat"
            grouped = Path(tmp) / "grouped"
            codegen.generate(spec, flat)
            codegen.generate(boarded, grouped)
            self.assertTrue((flat / "drivers" / "tmp101.c").is_file())
            self.assertTrue((grouped / "drivers" / "rf_kart" / "tmp101.c").is_file())
            self.assertTrue((grouped / "drivers" / "ana_kart" / "ltc2991.c").is_file())
            self.assertTrue((grouped / "drivers" / "rf_kart" / "rf_kart.c").is_file())
            self.assertTrue((grouped / "drivers" / "ana_kart" / "ana_kart.c").is_file())


class BoardModuleTests(unittest.TestCase):
    def _generate_boarded(self, tmp: Path) -> Path:
        spec = _base_spec("board_mod_demo")
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"},
                          {"id": "rf", "name": "RF Kart", "role": "peripheral"}]
        spec["devices"] = [{**spec["devices"][0], "board_id": "main"},
                           {**spec["devices"][1], "board_id": "rf"}]
        out = tmp / "p"
        codegen.generate(spec, out)
        return out

    def test_board_module_exposes_init_cit_selftest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            header = (out / "drivers" / "rf_kart" / "rf_kart.h").read_text(encoding="utf-8")
            self.assertIn("int rfKartInit(void);", header)
            self.assertIn("void rfKartCitRun(SBoardCit* spCit);", header)
            self.assertIn("int rfKartSelfTest(void);", header)
            self.assertNotIn("uint32_t", header)

    def test_board_init_calls_only_its_own_devices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            source = (out / "drivers" / "rf_kart" / "rf_kart.c").read_text(encoding="utf-8")
            self.assertIn("tmp101", source)          # RF kartin cihazi
            self.assertNotIn("ltc2991", source)      # ana kartin cihazi sizmamali

    def test_manifest_carries_boards_and_device_board_ids(self) -> None:
        import json
        with tempfile.TemporaryDirectory() as tmp:
            out = self._generate_boarded(Path(tmp))
            manifest = json.loads(
                (out / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([b["id"] for b in manifest["boards"]], ["main", "rf"])
            by_id = {d["id"]: d for d in manifest["devices"]}
            self.assertEqual(by_id["u2_tmp101"]["board_id"], "rf")
            self.assertEqual(by_id["u1_ltc2991"]["board_id"], "main")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: FAIL doğrula**

Run: `.venv/Scripts/python.exe -m unittest tests.test_board_codegen -v`
Expected: `BoardlessOutputIsUnchangedTests` GEÇER (bugünkü davranış), diğerleri FAIL (kart düzeni yok).

- [ ] **Step 3: `CUnit`'e kart kimliği ekle**

`orchestrator/cmodel.py:107` `CUnit` dataclass'ına (mevcut alanların sonuna, `test` alanından önce):

```python
    board_id: str = "main"
```

`build_units` (satır ~2304) içinde her ünite kurulurken cihazın kartını geçir. Ünite kurucu çağrılarının hepsine `board_id=boards.board_id_of(device)` eklenir; mux üniteleri için `boards.board_id_of(mux)`. Dosyanın başına `from orchestrator import boards`.

- [ ] **Step 4: `generate`'te yazım yolunu karta göre seç**

`orchestrator/codegen.py:6565` civarı — `drivers_dir` sabit yerine ünite başına hedef:

```python
    from orchestrator import boards as boards_mod

    drivers_dir = out_dir / "drivers"
    tests_dir = out_dir / "tests"
    use_boards = boards_mod.boards_declared(spec)
    board_list = boards_mod.normalized_boards(spec)
    if use_boards:
        boards_mod.assert_unique_identifiers(board_list)
    board_by_id = {str(b["id"]): b for b in board_list}

    def _unit_dir(unit_board_id: str) -> Path:
        """Kart tanimliysa kart klasoru, degilse bugunku duz drivers/."""
        if not use_boards:
            return drivers_dir
        board = board_by_id.get(unit_board_id) or board_by_id[boards_mod.main_board_id(spec)]
        return drivers_dir / boards_mod.board_dirname(str(board["name"]))
```

Ünite yazım satırlarında `drivers_dir / f"{unit.module}.h"` → `_unit_dir(unit.board_id) / f"{unit.module}.h"` (aynısı `.c` için).

- [ ] **Step 5: Kart modülü üreteçlerini yaz**

`orchestrator/codegen.py` içine (mevcut üreteçlerin yanına) ekle. Üretilen C kodlama standardına uyar (Allman, `unsigned int`, Doxygen):

```python
def _board_module_header(board: dict, module_headers: list[str], has_cit: bool) -> str:
    """Kart basina toplu API: <ident>Init / <ident>CitRun / <ident>SelfTest."""
    ident = boards.board_identifier(str(board["name"]))
    guard = boards.board_dirname(str(board["name"])).upper() + "_H"
    includes = "".join(f'#include "{name}"\n' for name in module_headers)
    cit_decl = (
        "/**\n"
        f" * @brief Yalniz bu kartin CIT olcumlerini sistem SBoardCit'ine doldurur.\n"
        " * @param spCit Sistem geneli CIT kopyasi (bit sirasi degismez).\n"
        " */\n"
        f"void {ident}CitRun(SBoardCit* spCit);\n\n") if has_cit else ""
    cit_include = '#include "spec2code_cit.h"\n' if has_cit else ""
    return (
        "/**\n"
        f" * @file {boards.board_dirname(str(board['name']))}.h\n"
        f" * @brief '{board['name']}' kartinin toplu API'si (uretildi; elle duzenlemeyin).\n"
        " */\n"
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        f"{cit_include}{includes}\n"
        "/**\n"
        f" * @brief Bu karttaki tum cihazlari sirayla ilklendirir.\n"
        " * @return Ilk hatanin XST_* kodu; hepsi basariliysa XST_SUCCESS.\n"
        " */\n"
        f"int {ident}Init(void);\n\n"
        f"{cit_decl}"
        "/**\n"
        f" * @brief Bu karttaki self-test'i olan cihazlari kosar.\n"
        " * @return Ilk hatanin XST_* kodu; hepsi basariliysa XST_SUCCESS.\n"
        " */\n"
        f"int {ident}SelfTest(void);\n\n"
        f"#endif /* {guard} */\n"
    )
```

`_board_module_source(board, init_calls, cit_calls, selftest_calls)` benzer şekilde gövdeyi üretir: `Init` her cihazın init fonksiyonunu sırayla çağırır, ilk hatayı `iFirst` içinde saklar ama **döngüye devam eder** (kısmi ilklendirme), sonunda `iFirst` döner. `CitRun` yalnız o kartın ölçüm indekslerini doldurur (sistem `boardCitRun` mantığının alt kümesi). `SelfTest` aynı kalıpta.

- [ ] **Step 6: `generate` sonunda kart modüllerini yaz**

Ünite döngüsünden sonra, `use_boards` iken her kart için:

```python
    if use_boards:
        for board in board_list:
            bid = str(board["id"])
            board_units = [u for u in units if u.board_id == bid]
            if not board_units:
                continue
            bdir = drivers_dir / boards_mod.board_dirname(str(board["name"]))
            stem = boards_mod.board_dirname(str(board["name"]))
            header = _board_module_header(board, [f"{u.module}.h" for u in board_units],
                                          has_cit=_board_has_cit(spec, bid))
            written.append(str(hio.write_output(bdir / f"{stem}.h",
                                                _apply_default_identifier_style(header))))
            source = _board_module_source(board, board_units, spec)
            written.append(str(hio.write_output(bdir / f"{stem}.c",
                                                _apply_default_identifier_style(source))))
```

- [ ] **Step 7: Manifest'e kart bilgisi ekle**

`_testbench_manifest` içinde: `manifest["boards"] = [{"id","name","role","notes"} ...]` ve `manifest["connectors"] = spec.get("connectors", [])` **yalnız `boards_declared(spec)` iken** (aksi halde manifest bugünküyle aynı kalmalı). Her `devices[]` girdisine `"board_id"`; CİT bölümü üretilirken her ölçüme `"board_id"`.

- [ ] **Step 8: Testleri koş**

Run: `.venv/Scripts/python.exe -m unittest tests.test_board_codegen -v`
Expected: PASS (hepsi)

- [ ] **Step 9: Golden-diff ile bayt-bayt kanıt**

Kart tanımsız iki PS projesi (biri FreeRTOS+eth, biri bare_metal+uart) HEAD worktree'sinde ve bu dalda üretilip `diff -r` ile karşılaştırılır; çıktı BOŞ olmalı. Komutu ve sonucunu rapora yaz.

- [ ] **Step 10: Derleme + linter + tam paket**

Gerçek BSP'ye karşı derleme (mevcut compile-verify yolunu kullan) + naming linter (kart modülleri dahil 0 ihlal) + tam paket.

- [ ] **Step 11: Commit**

```bash
git add orchestrator/cmodel.py orchestrator/codegen.py tests/test_board_codegen.py
git commit -m "Kart codegen: kart klasorleri + kart modulleri (Init/CitRun/SelfTest) + manifest"
```

---

### Task 3: Şematik — kart kutuları + konnektörler

**Files:**
- Modify: `frontend/src/features/schematic/SchematicCanvas.tsx` (242 satır), `nodes.tsx` (326), `edges.tsx` (50), `SidePanel.tsx` (113)
- Modify: `frontend/src/store/useStore.ts` (boards/connectors state + eylemler)
- Create: `frontend/src/features/schematic/BoardNode.tsx`

**Interfaces:**
- Consumes: Task 1 tipleri (`Board`, `Connector`), Task 2 manifest alanları.
- Produces: store eylemleri `addBoard(name)`, `renameBoard(id, name)`, `deleteBoard(id)` (içindeki cihazlar ana karta taşınır, onay UI'da), `setDeviceBoard(deviceId, boardId)`, `addConnector(c)`, `updateConnector(id, patch)`, `deleteConnector(id)`.

- [ ] **Step 1: Kart düğümü bileşeni** — React Flow group node: yeniden boyutlanabilir kutu, başlıkta kart adı (çift tıkla düzenlenir), ana kartta rozet, sağ üstte cihaz sayısı. Mevcut koyu PCB temasıyla uyumlu (mevcut `nodes.tsx` stillerini örnek al).
- [ ] **Step 2: Cihaz düğümlerini karta çocuk yap** — React Flow `parentNode` + `extent: "parent"`. Sürükleyip bırakınca `setDeviceBoard` çağrılır.
- [ ] **Step 3: Konnektör kenarları** — kartlar arası etiketli kenar: `"J7 → J1 · I2C0 · mux ch3"`. `edges.tsx` içindeki mevcut kanal-şeridi mantığı korunur.
- [ ] **Step 4: SidePanel** — "Kart ekle" düğmesi; kart seçiliyken ad/not düzenleme; konnektör ekle/düzenle formu (ad, kartlar, denetleyici, opsiyonel mux+kanal, not).
- [ ] **Step 5: Boş/tek kart durumu** — kart tanımlanmamışsa kanvas bugünkü gibi görünür (kutu yok); ilk "Kart ekle"de mevcut tüm cihazlar otomatik ana karta atanır.
- [ ] **Step 6: Build + görsel doğrulama** — `npm run build` 0 hata; preview'da kart ekle → cihaz sürükle → konnektör ekle akışı screenshot ile doğrulanır.
- [ ] **Step 7: Commit** — `git commit -m "Sematik: kart kutulari + kartlar arasi isimli konnektorler"`

---

### Task 4: CİT + Test Bench kart bazlı gruplama

**Files:**
- Modify: `frontend/src/features/cit/CitPanel.tsx`, `frontend/src/features/testbench/TestBenchPanel.tsx`, `frontend/src/features/testbench/InitAllCard.tsx`
- Modify: `backend/cit.py` (`decode_board_cit` — ölçüme `board_id` taşı)

**Interfaces:**
- Consumes: Task 2 manifest (`boards`, `cit.olcumler[].board_id`, `devices[].board_id`).
- Produces: `CitDecodeMeasurement`'a `board_id: string`; UI'da kart başlıkları + kart başına OK/NOK sayacı.

- [ ] **Step 1: `decode_board_cit` ölçüme `board_id` ekler** (manifest'ten; yoksa `"main"`), test ile.
- [ ] **Step 2: CitPanel gruplama** — kart başlığı + kart özet rozeti ("RF Kart: 4/4 OK"); sistem toplamları üst şeritte korunur; kart tanımsızken görünüm **bugünküyle aynı** (tek grup, başlık gösterilmez).
- [ ] **Step 3: TestBenchPanel** — entegre listesi kart başlıkları altında; `InitAllCard` özeti kart kart raporlar.
- [ ] **Step 4: Build + preview doğrulaması + tam paket.**
- [ ] **Step 5: Commit** — `git commit -m "CIT/Test Bench: kart bazli gruplama ve ozet"`

---

### Task 5: YATT — sistem topolojisi bölümü

**Files:**
- Modify: `backend/yatt.py` (HTML + Markdown üreticileri), `frontend/src/features/yatt/YattPanel.tsx`
- Test: `tests/test_yatt.py` (mevcut dosyaya ekleme)

- [ ] **Step 1: Failing test** — manifest'li YATT çıktısında kart tablosu (ad/rol/not) ve konnektör tablosu (ad, kartlar, hat, mux kanalı) geçmeli; kartsız manifest'te bu bölüm **hiç görünmemeli** (determinizm + geriye uyum).
- [ ] **Step 2: `_system_topology_rows(manifest)` yardımcısı + HTML/MD bölümü** — mevcut bölüm/çip/rozet stiliyle; sticky TOC'a "Sistem Topolojisi" girdisi.
- [ ] **Step 3: Testler + determinizm kontrolü (iki çağrı aynı string) + `npm run build`.**
- [ ] **Step 4: Commit** — `git commit -m "YATT: sistem topolojisi bolumu (kart + konnektor tablolari)"`

---

### Task 6: Uçtan uca doğrulama + dokümantasyon + kapanış

**Files:**
- Create: `specs/samples/multi_board_demo.spec.json` (2 kartlı örnek: ana kart + RF kart, mux'lu)
- Modify: `userguide.md` (yeni "Çok-kartlı sistemler" bölümü), `README.md` (özellik listesi)
- Modify: `changelog.md`, `frontend/src/lib/version.ts`

- [ ] **Step 1: Örnek spec + headless build** — `python spec2code_cli.py build --spec specs/samples/multi_board_demo.spec.json` → **QC GEÇTİ** (dört araç da mevcut olmalı; yoksa açıkça belirt).
- [ ] **Step 2: Gerçek BSP derlemesi** — üretilen kart klasörlü kaynaklar gerçek BSP include'larıyla derlenir (kart alt dizinleri `staged_header_dirs` ile include yoluna girer — bunu da doğrula).
- [ ] **Step 3: Vitis staging doğrulaması** — `stage_vitis_sources` çıktısında `drivers/ana_kart/...` ve `drivers/rf_kart/...` yolları görünmeli, `staged_header_dirs` her iki klasörü de listelemeli.
- [ ] **Step 4: Tam paket + frontend build + naming linter (0 ihlal).**
- [ ] **Step 5: Doküman + sürüm + changelog.**
- [ ] **Step 6: Commit + push (auto-release).**

---

## Self-Review Notları

- **Spec kapsaması:** §3 veri modeli→T1; §4 kod üretimi (değişmezlik kuralı + kart modülleri + tanımlayıcı türetme)→T2; §5 şematik→T3; §6 CİT/Test Bench→T4; §7 YATT/manifest→T2(manifest)+T5(YATT); §8 doğrulama→T1; §10 karar kaydı→hepsinde global kısıt olarak.
- **Tip tutarlılığı:** `boards.board_identifier/board_dirname/board_id_of/boards_declared/normalized_boards/main_board_id` adları T1'de tanımlanıp T2/T4/T5'te aynen kullanılıyor; `CUnit.board_id` T2'de tanımlı, T2 içinde tüketiliyor; `Board`/`Connector` TS tipleri T1'de tanımlı, T3/T4/T5'te kullanılıyor.
- **Placeholder taraması:** yok — kritik kod (boards.py, şema parçaları, validator bloğu, golden testi, kart modülü başlığı) tam metin olarak verildi; T3-T5 adımları UI/doküman işi olduğu için dosya+davranış düzeyinde bağlanmış, her adımın doğrulaması var.
