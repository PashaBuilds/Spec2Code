"""Schematic disa aktarimi: draw.io XML (kart basina sayfa) ve Excel (kart basina sayfa)."""

from __future__ import annotations

import io
import re
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend import xlsx_min  # noqa: E402
from backend.schematic_export import board_sheets, drawio_xml, xlsx_bytes  # noqa: E402


def _spec(with_boards: bool = True) -> dict:
    spec = {
        "project": {"name": "demo_board", "platform": "microblaze_7series", "target_core": "microblaze_0", "runtime": "bare_metal"},
        "controllers": [
            {"id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0", "base_address": "0x40800000", "driver": "XIic", "zone": "pl", "source": "xsa"},
            {"id": "pl_spi_0", "type": "spi", "instance": "XPAR_AXI_QUAD_SPI_0", "base_address": "0x44A00000", "driver": "XSpi", "zone": "pl", "source": "xsa"},
        ],
        "muxes": [{"id": "main_tca9548a", "part": "TCA9548A", "controller_id": "pl_i2c_0", "i2c_address": "0x70", "channels": 8, "board_id": "main"}],
        "devices": [
            {"id": "main_adt7420", "part": "ADT7420", "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x4B"}, "board_id": "main",
             "operations_requested": ["temperature_read"], "tests_requested": ["self_test"]},
            {"id": "rf_ltc2991", "part": "LTC2991", "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x48", "via_mux": {"mux_id": "main_tca9548a", "channel": 2}}, "board_id": "rf_kart"},
            {"id": "rf_s25fl", "part": "S25FL128S", "attach": {"controller_id": "pl_spi_0", "spi_chip_select": 0}, "board_id": "rf_kart", "simulate": True},
            {"id": "orphan_ds1682", "part": "DS1682", "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x6B"}, "board_id": "yok_boyle_kart"},
        ],
        "connectors": [{"id": "j1", "name": "J1 I2C", "from_board": "main", "to_board": "rf_kart",
                        "bus": {"controller_id": "pl_i2c_0", "via_mux": {"mux_id": "main_tca9548a", "channel": 2}}, "notes": "10 pin"}],
    }
    if with_boards:
        spec["boards"] = [{"id": "main", "name": "Ana Kart", "role": "main"}, {"id": "rf_kart", "name": "RF Kart: v2?", "role": "peripheral"}]
    return spec


def _workbook_sheet_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("xl/workbook.xml"))
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        return [s.get("name") for s in root.iter(f"{ns}sheet")]


class ExcelExportTests(unittest.TestCase):
    def test_one_sheet_per_board_main_first_and_names_sanitized(self) -> None:
        sheets = board_sheets(_spec())
        self.assertEqual([name for name, _ in sheets], ["Ana Kart", "RF Kart_ v2_"])
        main_rows, rf_rows = sheets[0][1], sheets[1][1]
        main_text = "\n".join(" | ".join(str(c) for c in row) for row in main_rows)
        rf_text = "\n".join(" | ".join(str(c) for c in row) for row in rf_rows)
        self.assertIn("main_adt7420", main_text)
        # board_id bilinmeyen cihaz ana karta duser (sessizce kaybolmaz)
        self.assertIn("orphan_ds1682", main_text)
        self.assertNotIn("rf_ltc2991", main_text)
        self.assertIn("rf_ltc2991", rf_text)
        self.assertIn("main_tca9548a | 2", rf_text)  # mux + kanal sutunlari
        self.assertIn("CS0", rf_text)
        self.assertIn("evet", rf_text)  # sanal cihaz
        self.assertIn("J1 I2C", main_text)
        self.assertIn("J1 I2C", rf_text)
        self.assertIn("XPAR_AXI_QUAD_SPI_0", rf_text)  # kartin kullandigi denetleyici

    def test_no_boards_gives_single_implicit_sheet(self) -> None:
        sheets = board_sheets(_spec(with_boards=False))
        self.assertEqual(len(sheets), 1)
        self.assertEqual(sheets[0][0], "demo_board")
        text = "\n".join(" | ".join(str(c) for c in row) for row in sheets[0][1])
        for dev in ("main_adt7420", "rf_ltc2991", "rf_s25fl", "orphan_ds1682"):
            self.assertIn(dev, text)

    def test_xlsx_workbook_has_all_sheets_and_round_trips_first_sheet(self) -> None:
        data = xlsx_bytes(_spec())
        self.assertEqual(_workbook_sheet_names(data), ["Ana Kart", "RF Kart_ v2_"])
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = set(z.namelist())
            self.assertIn("xl/worksheets/sheet2.xml", names)
            content_types = z.read("[Content_Types].xml").decode("utf-8")
            self.assertIn("/xl/worksheets/sheet2.xml", content_types)
        first = xlsx_min.read_first_sheet(data)
        self.assertEqual(first[0][0], "Kart")
        self.assertEqual(first[0][1], "Ana Kart")

    def test_single_sheet_writer_still_works(self) -> None:
        data = xlsx_min.write_sheet([["a", "b"], ["1", "2"]], "Tek")
        self.assertEqual(_workbook_sheet_names(data), ["Tek"])
        self.assertEqual(xlsx_min.read_first_sheet(data), [["a", "b"], ["1", "2"]])


class DrawioExportTests(unittest.TestCase):
    def test_pages_per_board_plus_system_page(self) -> None:
        xml = drawio_xml(_spec())
        root = ET.fromstring(xml)
        self.assertEqual(root.tag, "mxfile")
        pages = [d.get("name") for d in root.findall("diagram")]
        self.assertEqual(pages, ["Sistem", "Ana Kart", "RF Kart: v2?"])
        self.assertIn("rf_ltc2991", xml)
        self.assertIn("ch2", xml)  # mux kanali kenar etiketi
        self.assertIn("I2C 0x4B", xml)
        self.assertIn("SPI CS0", xml)
        self.assertIn("J1 I2C", xml)
        self.assertIn("orphan_ds1682", xml)
        # her sayfa gecerli mxGraphModel; kenarlar var olan hucrelere baglanir
        for diagram in root.findall("diagram"):
            cells = diagram.find("mxGraphModel/root").findall("mxCell")
            ids = {c.get("id") for c in cells}
            for cell in cells:
                if cell.get("edge") == "1":
                    self.assertIn(cell.get("source"), ids)
                    self.assertIn(cell.get("target"), ids)
                self.assertIn(cell.get("parent") or "0", ids | {"0"})

    def test_single_board_has_no_system_page(self) -> None:
        root = ET.fromstring(drawio_xml(_spec(with_boards=False)))
        self.assertEqual([d.get("name") for d in root.findall("diagram")], ["demo_board"])
        self.assertTrue(re.search(r'style="swimlane', ET.tostring(root, encoding="unicode")))


if __name__ == "__main__":
    unittest.main()
