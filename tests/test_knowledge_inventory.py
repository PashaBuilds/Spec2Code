import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_TS = ROOT / "frontend" / "src" / "features" / "device-knowledge" / "knowledge.ts"
TI_CLOCK_BITFIELDS_TS = ROOT / "frontend" / "src" / "features" / "device-knowledge" / "tiClockBitfields.ts"


def section(name: str) -> str:
    text = KNOWLEDGE_TS.read_text(encoding="utf-8")
    start = text.index(f"const {name}")
    next_const = text.find("\nconst ", start + 1)
    next_function = text.find("\nfunction ", start + 1)
    candidates = [index for index in (next_const, next_function) if index != -1]
    end = min(candidates) if candidates else len(text)
    return text[start:end]


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


if __name__ == "__main__":
    unittest.main()
