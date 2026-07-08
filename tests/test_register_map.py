import unittest

from backend import register_map as rm


class RegisterMapValidationTests(unittest.TestCase):
    def _doc(self, **over):
        base = {
            "maps": [{
                "name": "pl_blk", "base_address": "0xA0000000",
                "registers": [
                    {"name": "CTRL", "offset": "0x00", "reset": "0x1",
                     "fields": [{"name": "EN", "bits": "0"}, {"name": "MODE", "bits": "2:1"}]},
                    {"name": "STAT", "offset": "0x04", "reset": "0x0",
                     "fields": [{"name": "BUSY", "bits": "0"}]},
                ],
            }],
        }
        base["maps"][0].update(over)
        return base

    def test_valid_document_passes(self) -> None:
        self.assertEqual(rm.validate_register_document(self._doc()), [])

    def test_offset_must_be_multiple_of_four(self) -> None:
        doc = self._doc()
        doc["maps"][0]["registers"][1]["offset"] = "0x06"
        errs = rm.validate_register_document(doc)
        self.assertTrue(any("4'ün katı" in e for e in errs))

    def test_duplicate_offset_rejected(self) -> None:
        doc = self._doc()
        doc["maps"][0]["registers"][1]["offset"] = "0x00"
        errs = rm.validate_register_document(doc)
        self.assertTrue(any("zaten" in e for e in errs))

    def test_overlapping_bitfields_rejected(self) -> None:
        doc = self._doc()
        doc["maps"][0]["registers"][0]["fields"] = [
            {"name": "A", "bits": "3:0"}, {"name": "B", "bits": "2:2"},
        ]
        errs = rm.validate_register_document(doc)
        self.assertTrue(any("ÇAKIŞIYOR" in e for e in errs))

    def test_bad_identifier_rejected(self) -> None:
        doc = self._doc()
        doc["maps"][0]["registers"][0]["name"] = "1CTRL"
        errs = rm.validate_register_document(doc)
        self.assertTrue(any("tanımlayıcı" in e for e in errs))


class RegisterMapCodegenTests(unittest.TestCase):
    def _doc(self):
        return {"maps": [{
            "name": "pl_radar", "base_address": "0xA0010000",
            "registers": [
                {"name": "CTRL", "offset": "0x00", "reset": "0x00000001",
                 "fields": [{"name": "EN", "bits": "0"}, {"name": "GAIN", "bits": "7:4"}]},
                {"name": "RSVD", "offset": "0x04", "reset": "0x0", "reserved": True},
                {"name": "STAT", "offset": "0x10", "reset": "0x0",
                 "fields": [{"name": "LOCK", "bits": "0"}, {"name": "CODE", "bits": "31:24"}]},
            ],
        }]}

    def test_header_has_union_packed_reset_and_static_assert(self) -> None:
        h = rm.generate_header(self._doc()["maps"][0])
        # Union + ham deger + LSB-first bitfield + packed.
        self.assertIn("typedef union __attribute__((packed))", h)
        self.assertIn("unsigned int uiValue;", h)
        self.assertIn("unsigned int uiEN : 1U;", h)
        self.assertIn("unsigned int uiGAIN : 4U;", h)
        # LSB-first: EN(0) once, sonra 1..3 reserved, sonra GAIN(4).
        self.assertIn("uiReservedBits0 : 3U;", h)
        # Reset sabiti + base.
        self.assertIn("#define PL_RADAR_CTRL_RESET 0x00000001U", h)
        self.assertIn("#define PL_RADAR_BASE_ADDRESS 0xA0010000U", h)
        # Offset deligi 0x08-0x0C icin dolgu + STAT offset muhru 0x10.
        self.assertIn("unsigned int uiReserved0[2U];", h)
        self.assertIn("offsetof(SPlRadarRegs, uSTAT) == 0x10U", h)

    def test_source_maps_base_and_init_writes_reset(self) -> None:
        c = rm.generate_source(self._doc()["maps"][0])
        self.assertIn("static SPlRadarRegs* const S_spPlRadar = (SPlRadarRegs*)(PL_RADAR_BASE_ADDRESS);", c)
        self.assertIn("void pl_radarInit(void)", c)
        self.assertIn("S_spPlRadar->uCTRL.uiValue = PL_RADAR_CTRL_RESET;", c)
        # Reserved register init'te atlanir.
        self.assertNotIn("uRSVD.uiValue", c)

    def test_generate_files_names(self) -> None:
        files = rm.generate_files(self._doc())
        self.assertEqual(set(files), {"pl_radar_regs.h", "pl_radar.c"})


class RegisterMapHtmlRoundTripTests(unittest.TestCase):
    def test_build_html_embeds_and_extract_recovers_document(self) -> None:
        doc = rm.blank_document()
        html = rm.build_html(doc)
        self.assertIn("spec2code-registermap-data", html)
        # Veri yer tutucusu (yorum sarmali) gercek JSON ile degistirilmis olmali.
        # Bare "__SPEC2CODE_REGISTERMAP_DATA__" editorun kendi loadEmbedded()
        # calisma-zamani kontrolunde gecer; onu degil yer tutucuyu ariyoruz.
        self.assertNotIn("/*__SPEC2CODE_REGISTERMAP_DATA__*/", html)
        recovered = rm.extract_document_from_html(html)
        self.assertEqual(recovered["maps"][0]["name"], doc["maps"][0]["name"])
        self.assertEqual(rm.validate_register_document(recovered), [])

    def test_blank_document_is_valid_and_compiles_conceptually(self) -> None:
        doc = rm.blank_document()
        self.assertEqual(rm.validate_register_document(doc), [])
        files = rm.generate_files(doc)
        self.assertTrue(any(name.endswith("_regs.h") for name in files))


if __name__ == "__main__":
    unittest.main()
