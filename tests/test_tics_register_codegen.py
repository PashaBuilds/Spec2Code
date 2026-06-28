import tempfile
import unittest
from pathlib import Path

from backend.validators.wiring import validate_wiring
from orchestrator import codegen, tics


def tics_spec() -> dict:
    return {
        "schema_version": "1.0",
        "project": {
            "name": "unit_tics_codegen",
            "platform": "zynq_ultrascale",
            "target_core": "a53_0",
            "runtime": "freertos",
            "output_mode": "dropin",
        },
        "coding_standard_ref": "std/default.ruleset.json",
        "llm": {"enabled": False},
        "controllers": [
            {
                "id": "ps_spi_0",
                "type": "spi",
                "instance": "XPAR_XSPIPS_0",
                "base_address": "0xFF040000",
                "device_id": 0,
                "driver": "XSpiPs",
                "source": "xparameters",
                "zone": "ps",
            }
        ],
        "muxes": [],
        "devices": [
            {
                "id": "u1_lmk04832",
                "part": "LMK04832",
                "descriptor_ref": "descriptors/lmk04832.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 0, "reset_gpio": None},
                "config": {"ticspro_registers": ["0x000080", "0x016612"]},
                "operations_requested": ["device_init"],
                "tests_requested": ["self_test"],
            },
            {
                "id": "u2_lmx2820",
                "part": "LMX2820",
                "descriptor_ref": "descriptors/lmx2820.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 1, "reset_gpio": None},
                "config": {"ticspro_registers": ["0x4B0800", "0x00251C"]},
                "operations_requested": ["device_init"],
                "tests_requested": ["self_test"],
            },
            {
                "id": "u3_lmx1204",
                "part": "LMX1204",
                "descriptor_ref": "descriptors/lmx1204.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 2, "reset_gpio": None},
                "config": {"ticspro_registers": ["0x000001", "0x020223", "0x000000"]},
                "operations_requested": ["device_init"],
                "tests_requested": ["self_test"],
            },
        ],
        "generation_options": {"qc_max_rounds": 3, "include_doxygen": True, "line_ending": "crlf"},
    }


class TicsRegisterCodegenTests(unittest.TestCase):
    def test_tics_word_decode_uses_descriptor_model(self) -> None:
        lmk = tics.decode_word(0x016612, {
            "address_bits": 15,
            "address_shift": 8,
            "data_bits": 8,
            "rw_bit": 23,
        })
        self.assertEqual(lmk.address, 0x166)
        self.assertEqual(lmk.value, 0x12)

        lmx = tics.decode_word(0x4B0800, {
            "address_bits": 7,
            "address_shift": 16,
            "data_bits": 16,
            "rw_bit": 23,
        })
        self.assertEqual(lmx.address, 0x4B)
        self.assertEqual(lmx.value, 0x0800)

    def test_validator_rejects_read_frames_in_tics_array(self) -> None:
        spec = tics_spec()
        spec["devices"][0]["config"]["ticspro_registers"] = ["0x800080"]

        result = validate_wiring(spec)

        messages = [issue["message"] for issue in result["errors"]]
        self.assertTrue(any("expected write value" in message for message in messages))

    def test_codegen_emits_tics_arrays_and_mock_plan(self) -> None:
        spec = tics_spec()
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]

            written = {Path(path).relative_to(out_dir).as_posix() for path in codegen.generate(spec, out_dir)}

            self.assertIn("drivers/lmk04832.h", written)
            self.assertIn("drivers/lmk04832.c", written)
            self.assertIn("drivers/lmx2820.h", written)
            self.assertIn("drivers/lmx2820.c", written)
            self.assertIn("drivers/lmx1204.h", written)
            self.assertIn("drivers/lmx1204.c", written)

            lmk_source = (out_dir / "drivers" / "lmk04832.c").read_text(encoding="utf-8")
            self.assertIn("0x000080U,  /* address 0x0, value 0x80 */", lmk_source)
            self.assertIn("0x016612U,  /* address 0x166, value 0x12 */", lmk_source)
            self.assertIn("lmk04832RegisterWrite(spSpi, S_uiArrLmk04832InitSequence[uiIndex]);", lmk_source)

            lmx_header = (out_dir / "drivers" / "lmx2820.h").read_text(encoding="utf-8")
            lmx_source = (out_dir / "drivers" / "lmx2820.c").read_text(encoding="utf-8")
            self.assertIn("#define LMX2820_POST_INIT_DELAY_MS 10U", lmx_header)
            self.assertIn("lmx2820DelayMs(LMX2820_POST_INIT_DELAY_MS);", lmx_source)
            self.assertIn("lmx2820RegisterWrite(spSpi, 0x00251CU);", lmx_source)

            mock_plan = (out_dir / "tests" / "unit_tics_codegen_mock_plan.c").read_text(encoding="utf-8")
            self.assertIn("{ 0x4BU, 0x08U, 0x00U }", mock_plan)
            self.assertGreaterEqual(mock_plan.count("{ 0x00U, 0x25U, 0x1CU }"), 2)


if __name__ == "__main__":
    unittest.main()
