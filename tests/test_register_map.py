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

    def test_non_multiple_of_four_offset_is_allowed(self) -> None:
        # 4-byte varsayimi kalkti: 0x02 gibi offset artik gecerli (2 bayt genislik).
        doc = self._doc()
        doc["maps"][0]["registers"][1]["offset"] = "0x02"
        self.assertEqual(rm.validate_register_document(doc), [])

    def test_field_must_fit_in_inferred_width(self) -> None:
        # Offset 0x00, sonraki 0x02 -> genislik 2 bayt (16 bit); bit 20 sigmaz.
        doc = {"maps": [{"name": "pl_blk", "base_address": "0xA0000000", "registers": [
            {"name": "A", "offset": "0x00", "reset": "0x0", "fields": [{"name": "WIDE", "bits": "20:16"}]},
            {"name": "B", "offset": "0x02", "reset": "0x0", "fields": [{"name": "X", "bits": "0"}]},
        ]}]}
        errs = rm.validate_register_document(doc)
        self.assertTrue(any("sığmıyor" in e for e in errs))

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
        # Karisik genislik senaryosu:
        #  CONFIG @0x00 (sonraki 0x02 -> 2B) bitfield -> SCONFIG, usValue
        #  angle  @0x02 (sonraki 0x04 -> 2B) tek 15:0 alan -> skaler usAngle
        #  RSVD   @0x04 (sonraki 0x08 -> 4B) reserved -> ucReserved0[4]
        #  temperature @0x08 (SON, alan 31:0 -> 4B) skaler -> uiTemperature
        return {"maps": [{
            "name": "pl_mix", "base_address": "0xA0020000",
            "registers": [
                {"name": "CONFIG", "offset": "0x00", "reset": "0x1",
                 "fields": [{"name": "EN", "bits": "0"}, {"name": "MODE", "bits": "2:1"}]},
                {"name": "angle", "offset": "0x02", "reset": "0x0",
                 "fields": [{"name": "ANGLE", "bits": "15:0"}]},
                {"name": "RSVD", "offset": "0x04", "reset": "0x0", "reserved": True},
                {"name": "temperature", "offset": "0x08", "reset": "0x0",
                 "fields": [{"name": "TEMP", "bits": "31:0"}]},
            ],
        }]}

    def test_header_variable_width_scalar_bitfield_reserved(self) -> None:
        h = rm.generate_header(self._doc()["maps"][0])
        self.assertNotIn("typedef union", h)
        self.assertNotIn("sBits", h)
        # Bitfield register 2 bayt -> ham us + bit alanlari unsigned short.
        self.assertIn("unsigned short usValue;", h)
        self.assertIn("unsigned short EN : 1;", h)
        self.assertIn("unsigned short MODE : 2;", h)
        self.assertIn("unsigned short : 13;", h)   # 16 - (1+2) anonim kuyruk
        self.assertIn("} __attribute__((packed)) SCONFIG;", h)
        # Tek tam-genislik alan -> skaler (union yok): 2B usAngle, 4B uiTemperature.
        self.assertIn("unsigned short usAngle;", h)
        self.assertIn("unsigned int uiTemperature;", h)
        # Reserved -> bayt dizisi (0x04..0x07, 4 bayt).
        self.assertIn("unsigned char ucReserved0[4];", h)
        # Reset sabitleri genislik kadar hane: CONFIG 2B -> 0x0001, temp 4B.
        self.assertIn("#define PL_MIX_CONFIG_RESET 0x0001", h)
        self.assertIn("#define PL_MIX_TEMPERATURE_RESET 0x00000000", h)
        self.assertIn("#define PL_MIX_BASE_ADDRESS 0xA0020000", h)
        # Dis struct packed + offset muhurleri (skaler/reserved/bitfield hepsi).
        self.assertIn("} __attribute__((packed)) SPlMixRegs;", h)
        self.assertIn("offsetof(SPlMixRegs, SCONFIG) == 0x0", h)
        self.assertIn("offsetof(SPlMixRegs, usAngle) == 0x2", h)
        self.assertIn("offsetof(SPlMixRegs, ucReserved0) == 0x4", h)
        self.assertIn("offsetof(SPlMixRegs, uiTemperature) == 0x8", h)

    def test_source_init_scalar_direct_bitfield_via_raw(self) -> None:
        c = rm.generate_source(self._doc()["maps"][0])
        self.assertIn("static SPlMixRegs* const S_spPlMix = (SPlMixRegs*)(PL_MIX_BASE_ADDRESS);", c)
        self.assertIn("void pl_mixInit(void)", c)
        # Bitfield: ham genislik uyesinden (usValue). Skaler: dogrudan.
        self.assertIn("S_spPlMix->SCONFIG.usValue = PL_MIX_CONFIG_RESET;", c)
        self.assertIn("S_spPlMix->usAngle = PL_MIX_ANGLE_RESET;", c)
        self.assertIn("S_spPlMix->uiTemperature = PL_MIX_TEMPERATURE_RESET;", c)
        # Reserved init'te atlanir.
        self.assertNotIn("ucReserved0", c)

    def test_generate_files_names(self) -> None:
        files = rm.generate_files(self._doc())
        self.assertEqual(set(files), {"pl_mix_regs.h", "pl_mix.c"})

    def test_dump_function_prints_registers_and_fields_by_name(self) -> None:
        h = rm.generate_header(self._doc()["maps"][0])
        c = rm.generate_source(self._doc()["maps"][0])
        # Prototip header'da, fonksiyon source'ta; REGMAP_PRINTF makrosu.
        self.assertIn("void pl_mixDump(void);", h)
        self.assertIn("void pl_mixDump(void)", c)
        self.assertIn("#define REGMAP_PRINTF printf", c)
        self.assertIn("#ifndef REGMAP_NO_DUMP", c)
        # Bitfield register: ham deger + her alan adiyla ([bit] etiketiyle).
        self.assertIn("S_spPlMix->SCONFIG.usValue", c)
        self.assertIn('"EN"', c)
        self.assertIn("S_spPlMix->SCONFIG.EN", c)
        self.assertIn('"MODE"', c)
        self.assertIn('"[2:1]"', c)
        # Skaler register: dogrudan degiskeniyle.
        self.assertIn("S_spPlMix->uiTemperature", c)
        self.assertIn('"temperature"', c)
        # Reserved dump'ta atlanir.
        self.assertNotIn("ucReserved0", c)


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
