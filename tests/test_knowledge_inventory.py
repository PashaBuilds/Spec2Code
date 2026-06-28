import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_TS = ROOT / "frontend" / "src" / "features" / "device-knowledge" / "knowledge.ts"


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


if __name__ == "__main__":
    unittest.main()
