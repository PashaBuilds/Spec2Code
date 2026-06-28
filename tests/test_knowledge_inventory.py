import re
import unittest
from pathlib import Path

import yaml

from backend.api.routes import _knowledge_answer_unsupported_tokens
from backend.validators.wiring import validate_wiring


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_TS = ROOT / "frontend" / "src" / "features" / "device-knowledge" / "knowledge.ts"
TI_CLOCK_BITFIELDS_TS = ROOT / "frontend" / "src" / "features" / "device-knowledge" / "tiClockBitfields.ts"
DESCRIPTORS = ROOT / "descriptors"


def section(name: str) -> str:
    text = KNOWLEDGE_TS.read_text(encoding="utf-8")
    start = text.index(f"const {name}")
    next_const = text.find("\nconst ", start + 1)
    next_function = text.find("\nfunction ", start + 1)
    candidates = [index for index in (next_const, next_function) if index != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def function_section(name: str) -> str:
    text = KNOWLEDGE_TS.read_text(encoding="utf-8")
    start = text.index(f"function {name}")
    next_function = text.find("\nfunction ", start + 1)
    next_const = text.find("\nconst ", start + 1)
    candidates = [index for index in (next_function, next_const) if index != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def descriptor(name: str) -> dict:
    with (DESCRIPTORS / f"{name}.yaml").open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


class KnowledgeInventoryTests(unittest.TestCase):
    def test_ti_clock_register_inventory_counts_are_complete(self) -> None:
        lmk = section("LMK04832_REGISTER_ROWS")
        lmx1204 = section("LMX1204_REGISTER_ROWS")
        lmx2820 = section("LMX2820_REGISTER_ROWS")

        self.assertEqual(len(re.findall(r"\[0x[0-9A-F]{3},", lmk)), 125)
        self.assertEqual(len(re.findall(r"address: 0x[0-9A-F]{2}", lmx1204)), 35)
        self.assertEqual(len(re.findall(r"address: 0x[0-9A-F]{2}", lmx2820)), 123)

        self.assertIn("[0x555, \"SPI_LOCK\"]", lmk)
        self.assertIn("{ address: 0x5A, name: \"R90\"", lmx1204)
        self.assertIn("{ address: 0x7A, reset: \"0x0\" }", lmx2820)

    def test_ti_clock_bitfield_inventory_is_wired_for_all_registers(self) -> None:
        text = TI_CLOCK_BITFIELDS_TS.read_text(encoding="utf-8")

        def part_section(part: str) -> str:
            start = text.index(f"{part}: {{")
            next_part = min(
                [idx for idx in (text.find("\n  LM", start + 1), text.find("\n};", start + 1)) if idx != -1]
            )
            return text[start:next_part]

        lmk = part_section("LMK04832")
        lmx2820 = part_section("LMX2820")
        lmx1204 = part_section("LMX1204")

        self.assertEqual(len(re.findall(r'^\s+"0x[0-9A-F]{3}": \[', lmk, flags=re.MULTILINE)), 125)
        self.assertEqual(len(re.findall(r'^\s+"0x[0-9A-F]{2}": \[', lmx2820, flags=re.MULTILINE)), 123)
        self.assertEqual(len(re.findall(r'^\s+"0x[0-9A-F]{2}": \[', lmx1204, flags=re.MULTILINE)), 35)

        for required in [
            "PLL2_REF_2X_EN",
            "MASH_RST_COUNT[31:16]",
            "MASH_RST_COUNT[15:0]",
            "SYSREFREQ_DELAY_STEPSIZE",
            "SYSREFREQ_DELAY_STEP",
            "SYSREF_DELAY_BYPASS",
        ]:
            self.assertIn(required, text)

        self.assertNotIn("R${row.address} image", KNOWLEDGE_TS.read_text(encoding="utf-8"))

    def test_ti_clock_bitfield_meanings_do_not_use_placeholder_text(self) -> None:
        text = TI_CLOCK_BITFIELDS_TS.read_text(encoding="utf-8")
        all_knowledge_text = "\n".join(
            [
                KNOWLEDGE_TS.read_text(encoding="utf-8"),
                TI_CLOCK_BITFIELDS_TS.read_text(encoding="utf-8"),
            ]
        )

        for placeholder in [
            "Readback/status alanıdır; cihaz iç durumunu SPI readback ile okumak için kullanılır.",
            "TI register map içindeki bitfield alanıdır; TICS Pro export bu alanı register image içinde programlar.",
            "PLL konfigürasyon/status alanıdır; ilgili PLL divider, charge pump, lock-detect veya sync davranışını etkiler.",
        ]:
            self.assertNotIn(placeholder, all_knowledge_text)

        self.assertIn("PLL2 digital lock detect anlık readback bitidir", text)
        self.assertIn("PLL2_DLD_EN=1", text)

    def test_knowledge_answer_guard_rejects_context_external_code_tokens(self) -> None:
        context = "PART=LMK04832\nRB_PLL2_DLD address=0x183\nPLL2 digital lock detect."

        self.assertEqual(
            _knowledge_answer_unsupported_tokens("RB_PLL2_DLD 0x183 register'ından okunur.", context),
            [],
        )
        self.assertIn(
            "FAKE_PLL_STATUS",
            _knowledge_answer_unsupported_tokens("FAKE_PLL_STATUS 0x999 register'ından okunur.", context),
        )

    def test_non_clock_descriptor_register_maps_cover_datasheet_rows(self) -> None:
        ltc2991 = descriptor("ltc2991")
        ds1682 = descriptor("ds1682")
        ltc2945 = descriptor("ltc2945")
        ad7414 = descriptor("ad7414")

        self.assertEqual(len(ltc2991["registers"]), 30)
        self.assertIn("PWM_T_INTERNAL_CONTROL", {row["name"] for row in ltc2991["registers"]})
        self.assertEqual({row["offset"] for row in ltc2991["registers"] if row["name"].startswith("RESERVED_")}, {2, 3, 4, 5})

        self.assertEqual(len(ds1682["registers"]), 24)
        self.assertIn("USER_10", {row["name"] for row in ds1682["registers"]})
        self.assertIn("WRITE_MEMORY_DISABLE", {row["name"] for row in ds1682["registers"]})

        self.assertEqual(len(ltc2945["registers"]), 50)
        ltc2945_offsets = {row["name"]: row["offset"] for row in ltc2945["registers"]}
        self.assertEqual(ltc2945_offsets["ADIN_MSB"], 0x28)
        self.assertEqual(ltc2945_offsets["MIN_ADIN_THRESHOLD_LSB"], 0x31)

        ad7414_resets = {row["name"]: row.get("reset") for row in ad7414["registers"]}
        self.assertEqual(ad7414_resets["THIGH"], 0x7F)
        self.assertEqual(ad7414_resets["TLOW"], 0x80)

    def test_non_clock_catalog_has_full_command_and_register_inventory(self) -> None:
        text = KNOWLEDGE_TS.read_text(encoding="utf-8")
        mt25q = section("mt25qCommandRows")
        ltc2945 = function_section("ltc2945RegisterRows")
        ds1682 = function_section("ds1682Registers")
        ltc2991 = function_section("ltc2991Registers")

        self.assertEqual(len(re.findall(r'name: "[A-Z0-9_]+"', mt25q)), 82)
        for required in [
            "READ_FLAG_STATUS",
            "WRITE_NONVOLATILE_CONFIG",
            "QUAD_IO_FAST_READ_4B",
            "SUBSECTOR_ERASE_32K_4B",
            "WRITE_PASSWORD",
            "CRC_CHECK",
        ]:
            self.assertIn(required, mt25q)

        for required in [
            "MAX_POWER_THRESHOLD_MSB2",
            "MIN_SENSE_THRESHOLD_LSB",
            "MAX_VIN_THRESHOLD_MSB",
            "MIN_ADIN_THRESHOLD_LSB",
        ]:
            self.assertIn(required, ltc2945)

        self.assertIn("PWM_T_INTERNAL_CONTROL", ltc2991)
        self.assertIn("PWM_THRESHOLD_MSB", ltc2991)
        self.assertIn("Array.from({ length: 10 }", ds1682)
        self.assertIn('registers: mt25qRegisters("MT25QU02G")', text)

    def test_rw_star_registers_are_not_allowed_in_manual_init(self) -> None:
        spec = {
            "controllers": [
                {
                    "id": "i2c0",
                    "type": "i2c",
                    "instance": "XPAR_XIICPS_0",
                    "base_address": "0xFF020000",
                    "device_id": 0,
                    "driver": "XIicPs",
                    "source": "xparameters",
                    "zone": "ps",
                }
            ],
            "muxes": [],
            "devices": [
                {
                    "id": "u1",
                    "part": "LTC2945",
                    "descriptor_ref": "descriptors/ltc2945.yaml",
                    "attach": {"controller_id": "i2c0", "i2c_address": "0x67"},
                    "config": {"init_sequence": [{"reg": "POWER_MSB2", "value": 0}]},
                    "operations_requested": ["device_init"],
                }
            ],
        }

        result = validate_wiring(spec)

        messages = [issue["message"] for issue in result["errors"]]
        self.assertTrue(any("POWER_MSB2" in message and "not writable" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
