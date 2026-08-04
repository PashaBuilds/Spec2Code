import unittest

from backend.validators.wiring import validate_wiring
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


_I2C_CONTROLLER = {
    "id": "ps_i2c_0", "type": "i2c", "instance": "XIicPs", "driver": "XIicPs",
    "base_address": "0xFF020000", "device_id": 0, "source": "xparameters", "zone": "ps",
}
_MUX = {
    "id": "u10_tca9548a", "part": "TCA9548A", "controller_id": "ps_i2c_0",
    "i2c_address": "0x70", "channels": 4,
}
_DEVICE_MAIN = {
    "id": "u1_ltc2991", "part": "LTC2991",
    "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x48"},
}
_DEVICE_RF = {
    "id": "u2_tmp101", "part": "TMP101",
    "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x49",
               "via_mux": {"mux_id": "u10_tca9548a", "channel": 0}},
}


class WiringValidationTests(unittest.TestCase):
    """backend/validators/wiring.py'e eklenen kart/konnektor kurallari (Adim 6)."""

    def _spec(self, **extra: object) -> dict:
        spec = {
            "project": {"name": "demo", "platform": "zynq_ultrascale",
                        "target_core": "psu_cortexa53_0", "runtime": "bare_metal"},
            "controllers": [dict(_I2C_CONTROLLER)],
            "muxes": [dict(_MUX)],
            "devices": [dict(_DEVICE_MAIN), dict(_DEVICE_RF)],
        }
        spec.update(extra)
        return spec

    def test_two_main_boards_is_an_error(self) -> None:
        spec = self._spec(boards=[
            {"id": "main", "name": "Ana Kart", "role": "main"},
            {"id": "aux", "name": "Yardimci Kart", "role": "main"},
        ])
        result = validate_wiring(spec)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["path"] == "/boards" and "main" in e["message"]
                             for e in result["errors"]), result["errors"])

    def test_undefined_device_board_id_is_an_error(self) -> None:
        spec = self._spec(boards=[{"id": "main", "name": "Ana Kart", "role": "main"}])
        spec["devices"][1]["board_id"] = "ghost"
        result = validate_wiring(spec)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["path"] == "/devices/1/board_id" and "tanimsiz kart" in e["message"]
                             for e in result["errors"]), result["errors"])

    def test_connector_with_identical_endpoints_is_an_error(self) -> None:
        spec = self._spec(
            boards=[{"id": "main", "name": "Ana Kart", "role": "main"},
                    {"id": "rf", "name": "RF Kart", "role": "peripheral"}],
            connectors=[{"id": "j1", "name": "J1", "from_board": "main", "to_board": "main",
                         "bus": {"controller_id": "ps_i2c_0"}}],
        )
        result = validate_wiring(spec)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["path"] == "/connectors/0/to_board"
                             and "iki ucu ayni kart olamaz" in e["message"]
                             for e in result["errors"]), result["errors"])

    def test_out_of_range_mux_channel_on_connector_is_an_error(self) -> None:
        spec = self._spec(
            boards=[{"id": "main", "name": "Ana Kart", "role": "main"},
                    {"id": "rf", "name": "RF Kart", "role": "peripheral"}],
            connectors=[{"id": "j1", "name": "J1", "from_board": "main", "to_board": "rf",
                         "bus": {"controller_id": "ps_i2c_0",
                                 "via_mux": {"mux_id": "u10_tca9548a", "channel": 9}}}],
        )
        result = validate_wiring(spec)
        self.assertFalse(result["valid"])
        self.assertTrue(any(e["path"] == "/connectors/0/bus/via_mux/channel" for e in result["errors"]),
                         result["errors"])

    def test_undocumented_remote_board_is_a_warning_not_an_error(self) -> None:
        spec = self._spec(boards=[{"id": "main", "name": "Ana Kart", "role": "main"},
                                   {"id": "rf", "name": "RF Kart", "role": "peripheral"}])
        spec["devices"][1]["board_id"] = "rf"
        result = validate_wiring(spec)
        self.assertTrue(result["valid"], result["errors"])
        self.assertTrue(any("baglantisini belgeleyen konnektor yok" in w["message"]
                             for w in result["warnings"]), result["warnings"])

    def test_spec_without_boards_produces_no_new_issues(self) -> None:
        """Kart alani hic kullanilmayan (mevcut) projeler icin sifir yeni sonuc."""
        result = validate_wiring(self._spec())
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
