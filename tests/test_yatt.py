"""Task 9: YATT (Yazilim Arayuzu Tanimlama/Tarifi) sayfasi + export testleri.

build_yatt_html/build_yatt_markdown KATALOG-TABANLI ureteclerdir: yeni bir
mesaj backend/data/message_catalog.json'a eklenince YATT elle dokunulmadan
buyumeli. Bu yuzden testler sabit metin yerine katalogdan TUReTiLEN beklenti
listeleriyle karsilastirir (bkz. brief self-review sorusu 1).
"""
from __future__ import annotations

import re
import unittest

from fastapi.testclient import TestClient

from backend import cit, s2cmsg
from backend.s2cmsg import load_catalog, catalog_crc32, STATUS_LABELS
from backend.yatt import build_yatt_html, build_yatt_markdown, _BODY_LAYOUTS, _cit_layout_rows, body_layouts_json


def _fake_manifest(n: int = 2) -> dict:
    return {
        "message_catalog_crc32": catalog_crc32(),
        "devices": [
            {"id": "u1_ltc2991", "part": "LTC2991"},
            {"id": "u2_ad7414", "part": "AD7414"},
        ],
        "cit": {
            "olcumler": [
                {
                    "index": 0, "device": "u1_ltc2991", "device_index": 0, "part": "LTC2991",
                    "op": "voltage_read", "name": "VCC_3V3_RF", "cname": "Vcc3v3Rf",
                    "unit": "mV", "min": 3135, "max": 3465, "severity": "critical", "enabled": True,
                },
                {
                    "index": 1, "device": "u2_ad7414", "device_index": 1, "part": "AD7414",
                    "op": "temperature_read", "name": "AD_TEMP", "cname": "AdTemp",
                    "unit": "C", "min": 2000, "max": 3000, "severity": "warning", "enabled": True,
                },
            ][:n],
            "bit_sirasi": ["Vcc3v3Rf", "AdTemp"][:n],
        },
    }


def _fake_boarded_manifest(n: int = 2) -> dict:
    """_fake_manifest() + kart topolojisi — gercek codegen ciktisiyla BIREBIR sekil
    (orchestrator/codegen.py _testbench_manifest'ten gercek 2-kartli bir proje
    uretilip tests/spec2code_testbench_manifest.json okunarak dogrulandi; ayrica
    bkz. tests/test_board_codegen.py test_manifest_carries_connectors_and_generated_names).
    boards[]: id/name/role/notes/dirname/identifier. connectors[] spec.connectors'i
    HAM tasir: id/name/from_board/to_board/bus{controller_id,via_mux{mux_id,channel}}/notes.
    """
    manifest = _fake_manifest(n)
    manifest["boards"] = [
        {"id": "main", "name": "Ana Kart", "role": "main", "notes": "FPGA + PS",
         "dirname": "ana_kart", "identifier": "anaKart"},
        {"id": "rf", "name": "RF Kart", "role": "peripheral", "notes": None,
         "dirname": "rf_kart", "identifier": "rfKart"},
    ]
    manifest["connectors"] = [
        {"id": "j7_j1", "name": "J7 → J1", "from_board": "main", "to_board": "rf",
         "bus": {"controller_id": "ps_i2c_0",
                 "via_mux": {"mux_id": "u10_tca9548a", "channel": 3}},
         "notes": "10-pin FFC"},
    ]
    for i, device in enumerate(manifest["devices"]):
        device["board_id"] = "main" if i == 0 else "rf"
    return manifest


class YattContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.catalog = load_catalog()
        self.html = build_yatt_html(self.catalog, None)
        self.md = build_yatt_markdown(self.catalog, None)

    def test_html_contains_all_catalog_message_ids(self) -> None:
        for message in self.catalog["messages"]:
            with self.subTest(message["id"]):
                self.assertIn(message["id"], self.html)

    def test_html_contains_all_catalog_message_names(self) -> None:
        for message in self.catalog["messages"]:
            with self.subTest(message["name"]):
                self.assertIn(message["name"], self.html)

    def test_html_contains_header_field_names(self) -> None:
        for field in self.catalog["header"]:
            self.assertIn(field["name"], self.html)

    def test_html_contains_all_status_labels(self) -> None:
        for label in STATUS_LABELS.values():
            with self.subTest(label):
                self.assertIn(label, self.html)

    def test_html_contains_all_body_layout_field_names(self) -> None:
        # Kullanilan tum govde sablonlarinin alan adlari tabloda gecmeli.
        used_bodies = {m["body"] for m in self.catalog["messages"]}
        for body_name in used_bodies:
            for field in _BODY_LAYOUTS[body_name]:
                with self.subTest(body=body_name, field=field["name"]):
                    self.assertIn(field["name"], self.html)

    def test_html_is_self_contained_no_external_resources(self) -> None:
        self.assertNotIn("http://", self.html)
        self.assertNotIn("https://", self.html)

    def test_html_is_deterministic(self) -> None:
        again = build_yatt_html(self.catalog, None)
        self.assertEqual(self.html, again)

    def test_md_message_row_count_matches_catalog(self) -> None:
        # Mesaj tablosu satirlarini say: "| 0x" ile baslayan satirlar ID hex.
        rows = [line for line in self.md.splitlines() if line.startswith("| 0x")]
        self.assertEqual(len(rows), len(self.catalog["messages"]))

    def test_md_is_not_empty_and_deterministic(self) -> None:
        self.assertTrue(self.md.strip())
        again = build_yatt_markdown(self.catalog, None)
        self.assertEqual(self.md, again)

    def test_md_contains_all_catalog_message_ids(self) -> None:
        for message in self.catalog["messages"]:
            with self.subTest(message["id"]):
                self.assertIn(message["id"], self.md)

    def test_html_message_table_sorted_by_id(self) -> None:
        ids_in_catalog_order = sorted(m["id"] for m in self.catalog["messages"])
        found = re.findall(r"0x[0-9A-Fa-f]{8}", self.html)
        found_ids = [f for f in found if f.upper() in {i.upper() for i in ids_in_catalog_order}]
        # Ilk gorulen N (mesaj sayisi kadar) ID, katalogdaki ID sirasiyla (kucukten buyuge) esit olmali.
        first_n = found_ids[: len(ids_in_catalog_order)]
        self.assertEqual([x.upper() for x in first_n], [i.upper() for i in ids_in_catalog_order])

    def test_html_has_byte_diagram_for_header_and_all_templates(self) -> None:
        # Bayt-yerlesim diyagrami (yatt-bayt-serit) baslik + kullanilan tum
        # govde sablonlari icin bulunmali. Baslik(1) + kullanilan sablonlar.
        used_bodies = {m["body"] for m in self.catalog["messages"]}
        response_bodies = set()
        for m in self.catalog["messages"]:
            body = m["body"]
            response_bodies.add(body if body in ("trace", "cit") else "response_std")
        template_count = len(used_bodies | response_bodies)
        serit_count = self.html.count('class="yatt-bayt-serit"')
        # Baslik seridi + her sablon icin bir serit.
        self.assertGreaterEqual(serit_count, 1 + template_count)
        self.assertIn("yatt-bayt-serit", self.html)

    def test_html_has_print_media_block(self) -> None:
        self.assertIn("@media print", self.html)

    def test_html_contains_notes_constraints_section(self) -> None:
        # v1 notlari: bit-alani LSB-first, uiZaman v1'de 0, BUS_HATASI,
        # disabled olcum uiHam=0, CRC/magic yok, little-endian.
        for needle in ["LSB", "uiZaman", "BUS_HATASI", "little", "endian"]:
            with self.subTest(needle):
                self.assertIn(needle, self.html)


class YattManifestEnrichmentTests(unittest.TestCase):
    def test_html_with_manifest_includes_device_table_and_cit_cnames(self) -> None:
        manifest = _fake_manifest(2)
        html = build_yatt_html(load_catalog(), manifest)
        for device in manifest["devices"]:
            self.assertIn(device["id"], html)
            self.assertIn(device["part"], html)
        for measurement in manifest["cit"]["olcumler"]:
            self.assertIn(measurement["cname"], html)

    def test_html_with_manifest_is_still_deterministic(self) -> None:
        manifest = _fake_manifest(2)
        first = build_yatt_html(load_catalog(), manifest)
        second = build_yatt_html(load_catalog(), manifest)
        self.assertEqual(first, second)

    def test_html_without_manifest_still_builds(self) -> None:
        html = build_yatt_html(load_catalog(), None)
        self.assertTrue(html.strip())


class YattSystemTopologyTests(unittest.TestCase):
    """Task 5 (cok-kartli topoloji): YATT'a 'Sistem Topolojisi' bolumu.

    Kart tanimliyken kart tablosu (ad/rol/not/cihaz sayisi) + konnektor tablosu
    (ad/kartlar/hat/mux kanali/not); kart tanimsizken (manifest yok ya da
    manifest["boards"] yok) bolum HIC gorunmemeli (geriye uyum/determinizm —
    docs/superpowers/specs/2026-08-04-multi-board-topology-design.md §7).
    """

    def test_html_with_boards_includes_board_and_connector_details(self) -> None:
        manifest = _fake_boarded_manifest(2)
        html = build_yatt_html(load_catalog(), manifest)
        self.assertIn("Sistem Topolojisi", html)
        # Her iki kart adi.
        self.assertIn("Ana Kart", html)
        self.assertIn("RF Kart", html)
        # Her iki rol (ana kart gorsel vurgulu rozet + cevre karti).
        self.assertIn("ana kart", html)
        self.assertIn("çevre kartı", html)
        # Konnektor adi, hat (denetleyici kimligi), mux kanali.
        self.assertIn("J7 → J1", html)
        self.assertIn("ps_i2c_0", html)
        self.assertIn("u10_tca9548a", html)
        self.assertIn("ch 3", html)

    def test_markdown_with_boards_includes_board_and_connector_details(self) -> None:
        manifest = _fake_boarded_manifest(2)
        md = build_yatt_markdown(load_catalog(), manifest)
        self.assertIn("Sistem Topolojisi", md)
        self.assertIn("Ana Kart", md)
        self.assertIn("RF Kart", md)
        self.assertIn("ana kart", md)
        self.assertIn("çevre kartı", md)
        self.assertIn("J7 → J1", md)
        self.assertIn("ps_i2c_0", md)
        self.assertIn("u10_tca9548a", md)
        self.assertIn("ch 3", md)

    def test_html_without_boards_omits_topology_section_even_with_manifest(self) -> None:
        # Manifest VAR (devices/cit dolu) ama "boards" YOK -> bolum hic gorunmemeli.
        manifest = _fake_manifest(2)
        self.assertNotIn("boards", manifest)
        html = build_yatt_html(load_catalog(), manifest)
        self.assertNotIn("Sistem Topolojisi", html)
        self.assertNotIn("sistem-topolojisi", html)

    def test_html_without_manifest_omits_topology_section(self) -> None:
        html = build_yatt_html(load_catalog(), None)
        self.assertNotIn("Sistem Topolojisi", html)

    def test_markdown_without_boards_omits_topology_section(self) -> None:
        manifest = _fake_manifest(2)
        md = build_yatt_markdown(load_catalog(), manifest)
        self.assertNotIn("Sistem Topolojisi", md)

    def test_markdown_without_manifest_omits_topology_section(self) -> None:
        md = build_yatt_markdown(load_catalog(), None)
        self.assertNotIn("Sistem Topolojisi", md)

    def test_html_with_boards_is_still_deterministic(self) -> None:
        manifest = _fake_boarded_manifest(2)
        first = build_yatt_html(load_catalog(), manifest)
        second = build_yatt_html(load_catalog(), manifest)
        self.assertEqual(first, second)

    def test_markdown_with_boards_is_still_deterministic(self) -> None:
        manifest = _fake_boarded_manifest(2)
        first = build_yatt_markdown(load_catalog(), manifest)
        second = build_yatt_markdown(load_catalog(), manifest)
        self.assertEqual(first, second)

    def test_html_with_boards_is_still_self_contained(self) -> None:
        manifest = _fake_boarded_manifest(2)
        html = build_yatt_html(load_catalog(), manifest)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)

    def test_html_boards_toc_entry_present(self) -> None:
        manifest = _fake_boarded_manifest(2)
        html = build_yatt_html(load_catalog(), manifest)
        self.assertIn('href="#sistem-topolojisi"', html)
        self.assertIn("Sistem Topolojisi</a>", html)

    def test_html_boards_connector_without_mux_shows_dash_not_crash(self) -> None:
        # via_mux opsiyonel: konnektor mux'suz dogrudan hatta olabilir.
        manifest = _fake_boarded_manifest(2)
        manifest["connectors"][0]["bus"] = {"controller_id": "ps_i2c_0"}
        html = build_yatt_html(load_catalog(), manifest)
        self.assertIn("Sistem Topolojisi", html)
        self.assertIn("ps_i2c_0", html)

    def test_html_boards_without_connectors_still_shows_board_table_only(self) -> None:
        manifest = _fake_boarded_manifest(2)
        manifest["connectors"] = []
        html = build_yatt_html(load_catalog(), manifest)
        self.assertIn("Sistem Topolojisi", html)
        self.assertIn("Ana Kart", html)


class YattCitOffsetCrossCheckTests(unittest.TestCase):
    """Finding 1: backend/cit.py ve backend/yatt.py CIT offset matematigi
    birbirinden BAGIMSIZ turemez — bu test her ikisini de import edip
    cit.py'nin GERCEK sabitlerinden (import edilen degerlerden, sayilari
    tekrar yazmadan) beklenen offset/boy listesini turetir ve
    yatt._cit_layout_rows(n) ile birebir karsilastirir. Taraflardan biri
    (flag_words formulu, _PREFIX_SIZE, _CIT_HEADER_SIZE, _OLCUM_SIZE) tek
    tarafli degisirse bu test KIRILIR.
    """

    def _expected_rows(self, n: int) -> list[tuple[int | None, int | None, str]]:
        # cit.py'nin GERCEK ozel sabitlerini import ederek (sayilari elle
        # tekrarlamadan) beklenen (offset, size, name) uclusunu kur.
        prefix_size = cit._PREFIX_SIZE  # uiIstekSayac(4) + uiDurum(4)
        header_size = cit._CIT_HEADER_SIZE  # uiSayac(4) + uiZaman(4)
        olcum_size = cit._OLCUM_SIZE  # iDeger(4)+uiHam(4)+uiDurum(4)
        flag_words = cit._flag_words_size(n)

        rows: list[tuple[int | None, int | None, str]] = [
            (0, 4, "uiIstekSayac"),
            (4, 4, "uiDurum"),
            (prefix_size, 4, "uiSayac"),
            (prefix_size + 4, 4, "uiZaman"),
            (prefix_size + header_size, flag_words, "bayrak_words"),
        ]
        olcum_off = prefix_size + header_size + flag_words
        for i in range(n):
            rows.append((olcum_off + i * olcum_size, olcum_size, f"arrOlcum[{i}]"))
        return rows

    def test_cit_layout_rows_match_cit_decoder_math(self) -> None:
        for n in (1, 2, 32, 33, 40):
            with self.subTest(n=n):
                actual = [(row["offset"], row["size"], row["name"]) for row in _cit_layout_rows(n)]
                expected = self._expected_rows(n)
                self.assertEqual(actual, expected)

                # Toplam govde boyu da decode_board_cit'in expected_size hesabiyla
                # (_PREFIX_SIZE + _CIT_HEADER_SIZE + flag_words + n*_OLCUM_SIZE)
                # birebir uyusmali — yerlesim satirlari son bayta kadar dogru olsun.
                last = actual[-1]
                total_from_layout = last[0] + last[1] if n > 0 else actual[-1][0] + actual[-1][1]
                expected_total = (
                    cit._PREFIX_SIZE + cit._CIT_HEADER_SIZE
                    + cit._flag_words_size(n) + n * cit._OLCUM_SIZE
                )
                self.assertEqual(total_from_layout, expected_total)


class YattApiTests(unittest.TestCase):
    def setUp(self) -> None:
        from backend.main import app

        self.client = TestClient(app)

    def test_catalog_endpoint_shape(self) -> None:
        res = self.client.get("/api/yatt/catalog")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertIn("messages", body)
        self.assertIn("crc32", body)
        self.assertIn("status_codes", body)
        self.assertIn("body_layouts", body)
        self.assertEqual(len(body["messages"]), len(load_catalog()["messages"]))
        self.assertTrue(body["crc32"].startswith("0x"))

    def test_catalog_endpoint_body_layouts_contains_template_keys(self) -> None:
        res = self.client.get("/api/yatt/catalog")
        self.assertEqual(res.status_code, 200)
        body_layouts = res.json()["body_layouts"]
        for key in ("request_std", "response_std", "trace", "cit"):
            with self.subTest(key):
                self.assertIn(key, body_layouts)
                self.assertTrue(body_layouts[key])

        first_field = body_layouts["request_std"][0]
        self.assertEqual(first_field["name"], "uiCihazIndeks")
        self.assertEqual(first_field["offset"], 0)

    def test_catalog_endpoint_body_layouts_matches_backend_source(self) -> None:
        res = self.client.get("/api/yatt/catalog")
        self.assertEqual(res.json()["body_layouts"], body_layouts_json())

    def test_export_html_returns_download(self) -> None:
        res = self.client.post("/api/yatt/export", json={"fmt": "html"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Content-Disposition", res.headers)
        self.assertIn("attachment", res.headers["Content-Disposition"])
        self.assertIn("PING", res.text)

    def test_export_md_returns_download(self) -> None:
        res = self.client.post("/api/yatt/export", json={"fmt": "md"})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Content-Disposition", res.headers)
        self.assertIn("PING", res.text)

    def test_export_with_manifest_includes_cit(self) -> None:
        manifest = _fake_manifest(2)
        res = self.client.post("/api/yatt/export", json={"fmt": "html", "manifest": manifest})
        self.assertEqual(res.status_code, 200)
        self.assertIn("Vcc3v3Rf", res.text)

    def test_export_rejects_unknown_format(self) -> None:
        res = self.client.post("/api/yatt/export", json={"fmt": "pdf"})
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()
