import json
import random
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
            {
                "id": "u4_adar1000",
                "part": "ADAR1000",
                "descriptor_ref": "descriptors/adar1000.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 3, "reset_gpio": None},
                "config": {"register_words": ["0x000080", "0x002E7F"]},
                "operations_requested": ["device_init"],
                "tests_requested": ["self_test"],
            },
            {
                "id": "u5_lmx1205",
                "part": "LMX1205",
                "descriptor_ref": "descriptors/lmx1205.yaml",
                # SNAS850 6.3.7 sirasi: RESET toggle, programlama, son yazim
                # DEV_IOPT_CTRL=0x6 (R55/0x37).
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 4, "reset_gpio": None},
                "config": {"ticspro_registers": ["0x000001", "0x000000", "0x0200BF", "0x370006"]},
                "operations_requested": ["device_init", "multiplier_lock_detect"],
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

    def test_validator_reports_non_multiple_of_three_byte_paste_as_error(self) -> None:
        spec = tics_spec()
        # Saha hatasi: kullanici 3-bayt/mesaj formatinda bir dosya yapistirdi
        # ama satirlardan biri eksik/kesik. Enough byte tokens to cross the
        # byte-dump volume threshold (unambiguously a byte-triplet paste),
        # plus one incomplete trailing message (2 bytes instead of 3).
        rng = random.Random(7)
        triplets = [(rng.randint(0, 0x7F), rng.randint(0, 0xFF), rng.randint(0, 0xFF)) for _ in range(4)]
        lines = [f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets]
        lines.append("0x00, 0x00,")
        spec["devices"][0]["config"]["ticspro_registers"] = "\n".join(lines)

        result = validate_wiring(spec)

        messages = [issue["message"] for issue in result["errors"]]
        self.assertTrue(any("3" in message and "kati" in message for message in messages))

    def test_codegen_emits_tics_arrays_and_testbench_manifest(self) -> None:
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
            self.assertIn("drivers/adar1000.h", written)
            self.assertIn("drivers/adar1000.c", written)

            lmk_source = (out_dir / "drivers" / "lmk04832.c").read_text(encoding="utf-8")
            # LMK04832: TICS Pro array now emits as a 3-byte-per-message
            # unsigned char array (saha isteği), not the unsigned int word
            # array LMX-style parts still use below.
            self.assertIn("Format: 3 bytes per message.", lmk_source)
            self.assertIn("Byte 0: Address High", lmk_source)
            self.assertIn("Byte 1: Address Low", lmk_source)
            self.assertIn("Byte 2: Data", lmk_source)
            self.assertIn("static const unsigned char S_ucArrLmk04832ConfigFile[LMK04832_CONFIG_FILE_BYTE_COUNT] =", lmk_source)
            self.assertIn("0x00, 0x00, 0x80,", lmk_source)
            self.assertIn("0x01, 0x66, 0x12,", lmk_source)
            self.assertIn(
                "iStatus = lmk04832RegisterWrite(spSpi, ((unsigned int)S_ucArrLmk04832ConfigFile[uiIndex] << 16U) | "
                "((unsigned int)S_ucArrLmk04832ConfigFile[uiIndex + 1U] << 8U) | "
                "(unsigned int)S_ucArrLmk04832ConfigFile[uiIndex + 2U]);",
                lmk_source,
            )

            lmx_header = (out_dir / "drivers" / "lmx2820.h").read_text(encoding="utf-8")
            lmx_source = (out_dir / "drivers" / "lmx2820.c").read_text(encoding="utf-8")
            self.assertIn("#define LMX2820_POST_INIT_DELAY_MS 10U", lmx_header)
            self.assertIn("lmx2820DelayMs(LMX2820_POST_INIT_DELAY_MS);", lmx_source)
            self.assertIn("lmx2820RegisterWrite(spSpi, 0x00251CU);", lmx_source)

            adar_header = (out_dir / "drivers" / "adar1000.h").read_text(encoding="utf-8")
            adar_source = (out_dir / "drivers" / "adar1000.c").read_text(encoding="utf-8")
            self.assertIn("#define ADAR1000_REG_RX_ENABLES 0x2EU", adar_header)
            # ADAR1000 shares the LMK-style 15-bit-address/8-bit-data TICS Pro
            # register model (descriptors/adar1000.yaml), so it gets the same
            # 3-byte-per-message unsigned char array format.
            self.assertIn("static const unsigned char S_ucArrAdar1000ConfigFile[ADAR1000_CONFIG_FILE_BYTE_COUNT] =", adar_source)
            self.assertIn("0x00, 0x2E, 0x7F,", adar_source)
            self.assertIn(
                "iStatus = adar1000RegisterWrite(spSpi, ((unsigned int)S_ucArrAdar1000ConfigFile[uiIndex] << 16U) | "
                "((unsigned int)S_ucArrAdar1000ConfigFile[uiIndex + 1U] << 8U) | "
                "(unsigned int)S_ucArrAdar1000ConfigFile[uiIndex + 2U]);",
                adar_source,
            )

            # LMX1205 (SNAS850): 20 MHz SPI, multiplier lock detect R37 bit 0,
            # MUXOUT auto-readback -> generic register_read manifest'te.
            self.assertIn("drivers/lmx1205.h", written)
            self.assertIn("drivers/lmx1205.c", written)
            lmx1205_header = (out_dir / "drivers" / "lmx1205.h").read_text(encoding="utf-8")
            lmx1205_source = (out_dir / "drivers" / "lmx1205.c").read_text(encoding="utf-8")
            self.assertIn("#define LMX1205_SPI_MAX_SCK_HZ 20000000U", lmx1205_header)
            self.assertIn("#define LMX1205_REG_R37 0x25U", lmx1205_header)
            self.assertIn("int lmx1205MultiplierLockDetect(XSpiPs* spSpi, unsigned char* ucpMultiplier);", lmx1205_header)
            self.assertIn("0x370006U,  /* address 0x37, value 0x6 */", lmx1205_source)
            self.assertIn("lmx1205RegisterWrite(spSpi, S_uiArrLmx1205InitSequence[uiIndex]);", lmx1205_source)

            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            parts = {device["part"] for device in manifest["devices"]}
            self.assertIn("LMK04832", parts)
            self.assertIn("LMX2820", parts)
            self.assertIn("LMX1204", parts)
            self.assertIn("ADAR1000", parts)
            self.assertIn("LMX1205", parts)
            lmx1205_entry = next(device for device in manifest["devices"] if device["part"] == "LMX1205")
            lmx1205_ops = {op["name"]: op for op in lmx1205_entry["operations"]}
            self.assertIn("multiplier_lock_detect", lmx1205_ops)
            self.assertIn("register_read", lmx1205_ops)
            self.assertIn("MUXOUT", lmx1205_ops["register_read"]["description"])
            self.assertIn("register_write", lmx1205_ops)
            lmx1205_regs = {reg["name"]: reg for reg in lmx1205_entry["registers"]}
            self.assertEqual(lmx1205_regs["R55"]["offset"], 0x37)
            self.assertEqual(lmx1205_regs["R37"]["access"], "ro")
            retired_fragments = ("spec2code_" + "mo" + "ck", "_" + "mo" + "ck" + "_plan")
            self.assertFalse(any(any(fragment in path.lower() for fragment in retired_fragments) for path in written))

    def test_lmk_pll_lock_status_operations_are_generated_for_testbench(self) -> None:
        spec = tics_spec()
        spec["project"]["name"] = "unit_lmk_pll_status"
        spec["devices"] = [spec["devices"][0]]
        spec["devices"][0]["operations_requested"] = [
            "device_init",
            "pll1_lock_detect",
            "pll1_lock_loss",
            "pll2_lock_detect",
            "pll2_lock_loss",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]

            codegen.generate(spec, out_dir)

            lmk_header = (out_dir / "drivers" / "lmk04832.h").read_text(encoding="utf-8")
            lmk_source = (out_dir / "drivers" / "lmk04832.c").read_text(encoding="utf-8")
            ops_source = (out_dir / "tests" / "unit_lmk_pll_status_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        lmk_ops = {op["name"]: op for op in manifest["devices"][0]["operations"]}
        for op_name in ("pll1_lock_detect", "pll1_lock_loss", "pll2_lock_detect", "pll2_lock_loss"):
            self.assertIn(op_name, lmk_ops)
            self.assertEqual(lmk_ops[op_name]["fixed_read_length"], 1)
            self.assertEqual(lmk_ops[op_name]["risk"], "safe")
        self.assertIn("#define LMK04832_REG_RB_PLL_STATUS 0x183U", lmk_header)
        self.assertIn("int lmk04832Pll1LockDetect(XSpiPs* spSpi, unsigned char* ucpPll1);", lmk_header)
        self.assertIn("uiWord = ((unsigned int)1U << 23U) | (((unsigned int)uiReg & 0x7FFFU) << 8U);", lmk_source)
        self.assertIn("iStatus = lmk04832RegisterRead(spSpi, LMK04832_REG_RB_PLL_STATUS, &ucArrBytes[0U]);", lmk_source)
        self.assertIn("*ucpPll1 = (unsigned char)((((unsigned char)ucArrBytes[0U] & 0x4U) >> 2U));", lmk_source)
        self.assertIn("lmk04832Pll2LockLoss(spSpi, &ucValue);", ops_source)


def _sample_triplet_lines(count: int) -> list[tuple[int, int, int]]:
    rng = random.Random(42)
    lines = []
    for _ in range(count):
        b0 = rng.randint(0, 0x7F)  # bit7=0 (write), matches R/W=write requirement
        b1 = rng.randint(0, 0xFF)
        b2 = rng.randint(0, 0xFF)
        lines.append((b0, b1, b2))
    return lines


class TicsTripletParseTests(unittest.TestCase):
    """Saha hatasi: kullanici zaten 3-bayt/mesaj C formatindaki LMK export'unu
    yapistirdi (0x00, 0x00, 0x90, / ... 126 satir), editor/parser her bayt
    tokenini ayri bir 24-bit register word sandi (378 sahte kayit). Bu testler
    orchestrator.tics.parse_words'un dogru semantigi -- native TICS Pro
    satiri / bare 24-bit word / bayt-uclusu satiri / duz 3N bayt blogu --
    tanidigini ve gecersiz girdilerde ValueError firlattigini dogrular.
    """

    def test_native_bare_word_line_is_single_message(self) -> None:
        self.assertEqual(tics.parse_words("0x016612"), [0x016612])

    def test_multiple_native_word_lines_are_kept_as_is(self) -> None:
        # All tokens clearly exceed a single byte (0xFF), so this is
        # unambiguously a native 24-bit word list, not a byte-triplet paste.
        raw = "0x016612\n0x4B0800\n0x230000\n"
        self.assertEqual(tics.parse_words(raw), [0x016612, 0x4B0800, 0x230000])

    def test_short_all_byte_like_text_blob_is_not_reinterpreted(self) -> None:
        # Code-review regression: a short free-text blob (not a stored
        # list) where every token is <=0xFF - e.g. the ?demo seed values
        # pasted as plain text instead of already stored as a JSON list -
        # must stay as separate native words below the volume threshold,
        # the same as the equivalent list-storage case already covered by
        # test_short_list_of_small_native_words_is_not_reinterpreted.
        raw = "0x10, 0x63, 0x00"
        self.assertEqual(tics.parse_words(raw), [0x10, 0x63, 0x00])

    def test_short_native_word_blob_with_small_values_is_not_reinterpreted(self) -> None:
        # Regression: this is the repo's own ?demo seed data
        # (frontend/src/lib/demoSeed.ts, u6_lmk04832 -
        # "4-wire (SPI_3WIRE_DIS=1) + PLL2 N"), a short, legitimate native
        # word list where every token happens to be <=0xFF. Below the
        # byte-dump volume threshold this must be kept as native words, not
        # flagged as ambiguous or regrouped into triplets.
        raw = "0x000010\n0x016302\n0x018300\n"
        self.assertEqual(tics.parse_words(raw), [0x000010, 0x016302, 0x018300])

    def test_long_ambiguous_mixed_byte_and_word_blob_is_an_error(self) -> None:
        # Once a blob is long enough to plausibly be a byte-triplet dump,
        # mixing lone-byte-looking tokens with clear 24-bit words is
        # unsafe to resolve either way and must raise.
        triplets = _sample_triplet_lines(4)  # 12 byte tokens
        lines = [f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets]
        lines.append("0x016612")  # inject one unambiguous 24-bit word token (13 tokens total)
        raw = "\n".join(lines)
        with self.assertRaises(ValueError):
            tics.parse_words(raw)

    def test_single_byte_triplet_line_below_volume_threshold_is_ambiguous(self) -> None:
        # A single 3-byte-per-message line (1 message, 3 byte tokens) is
        # indistinguishable in isolation from 3 native words that all
        # happen to be <=0xFF (see the short-native-word-list regression
        # tests above), so below the volume threshold it is kept as
        # separate native words rather than guessed into one grouped word.
        raw = "0x00, 0x00, 0x90,"
        self.assertEqual(tics.parse_words(raw), [0x00, 0x00, 0x90])

    def test_byte_triplet_lines_user_exact_format_above_threshold(self) -> None:
        # Enough triplet lines (>= _BYTE_DUMP_MIN_LEN byte tokens) to cross
        # the volume threshold: this is the user's exact reported format,
        # just short of the full 126-line report - each line becomes one
        # grouped 24-bit message.
        triplets = _sample_triplet_lines(5)  # 15 byte tokens, above threshold
        raw = "\n".join(f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets)
        expected = [(b0 << 16) | (b1 << 8) | b2 for b0, b1, b2 in triplets]
        self.assertEqual(tics.parse_words(raw), expected)

    def test_flat_byte_blob_without_trailing_commas_groups_in_threes(self) -> None:
        triplets = _sample_triplet_lines(5)  # 15 byte tokens, above threshold
        raw = " ".join(f"0x{b0:02X} 0x{b1:02X} 0x{b2:02X}" for b0, b1, b2 in triplets)
        expected = [(b0 << 16) | (b1 << 8) | b2 for b0, b1, b2 in triplets]
        self.assertEqual(tics.parse_words(raw), expected)

    def test_126_triplet_lines_yield_126_messages(self) -> None:
        triplets = _sample_triplet_lines(126)
        raw = "\n".join(f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets)

        words = tics.parse_words(raw)

        self.assertEqual(len(words), 126)
        expected = [(b0 << 16) | (b1 << 8) | b2 for b0, b1, b2 in triplets]
        self.assertEqual(words, expected)

    def test_byte_token_count_not_multiple_of_three_is_an_error(self) -> None:
        # Enough byte tokens to cross the byte-dump volume threshold (so
        # this is unambiguously treated as a byte-triplet paste), but one
        # short line truncates the last message to 2 bytes instead of 3.
        triplets = _sample_triplet_lines(4)  # 12 byte tokens
        lines = [f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets]
        lines.append("0x00, 0x00,")  # incomplete trailing message (14 tokens total)
        raw = "\n".join(lines)
        with self.assertRaises(ValueError) as ctx:
            tics.parse_words(raw)
        self.assertIn("3", str(ctx.exception))

    def test_short_mixed_byte_and_word_tokens_is_kept_as_native_words(self) -> None:
        # Below the byte-dump volume threshold, a short blob mixing a bare
        # 24-bit word with plain byte tokens is far more plausibly a small
        # native word list (see the ?demo seed regression test above) than
        # a byte-triplet dump, so it must not raise.
        raw = "0x016612\n0x00, 0x90\n"
        self.assertEqual(tics.parse_words(raw), [0x016612, 0x00, 0x90])

    def test_list_of_already_broken_byte_strings_is_tolerated(self) -> None:
        # Tolerance for configs already saved in the broken 378-entry shape
        # (each list item one lone byte token) before this fix landed. Needs
        # to be long enough to be distinguishable from a short, legitimate
        # native-word list that coincidentally contains only small values
        # (real fixtures do have e.g. "0x000000"/"0x000010").
        triplets = _sample_triplet_lines(12)
        raw = [f"0x{b:02X}" for triplet in triplets for b in triplet]
        expected = [(b0 << 16) | (b1 << 8) | b2 for b0, b1, b2 in triplets]
        self.assertEqual(tics.parse_words(raw), expected)

    def test_short_list_of_small_native_words_is_not_reinterpreted(self) -> None:
        # Regression guard: a short list of legitimate native words that
        # happen to all be <=0xFF (address 0, small value - this occurs in
        # real descriptors, e.g. LMX1204/LMX1205 fixtures) must be kept
        # as-is, not treated as a broken byte dump.
        raw = ["0x000001", "0x000000", "0x000010"]
        self.assertEqual(tics.parse_words(raw), [0x000001, 0x000000, 0x000010])

    def test_documented_residual_risk_12_uniform_small_native_words(self) -> None:
        # Documents an accepted, code-reviewed residual risk (see the
        # comment in orchestrator/tics.py, parse_words list branch): a
        # list of >=12 entries, count a multiple of 3, where every entry
        # is a genuine native word that all happen to be <=0xFF (register
        # address 0x0000 for every single entry) is still misread as a
        # byte dump. Not realistic for a real TICS Pro export (no init
        # sequence targets the same zero address a dozen-plus times);
        # this test pins the current, intentional behavior rather than
        # silently leaving it uncovered.
        raw = ["0x01"] * 12
        result = tics.parse_words(raw)
        self.assertEqual(len(result), 4)
        self.assertNotEqual(result, [0x01] * 12)

    def test_list_of_canonical_word_strings_is_unaffected(self) -> None:
        raw = ["0x000080", "0x016612"]
        self.assertEqual(tics.parse_words(raw), [0x000080, 0x016612])


class TicsTripletEndToEndCodegenTests(unittest.TestCase):
    def test_pasted_3n_triplet_config_generates_matching_c_array(self) -> None:
        triplets = _sample_triplet_lines(126)
        pasted_lines = [f"0x{b0:02X}, 0x{b1:02X}, 0x{b2:02X}," for b0, b1, b2 in triplets]
        raw_paste = "\n".join(pasted_lines)

        spec = tics_spec()
        spec["devices"] = [spec["devices"][0]]
        spec["devices"][0]["config"]["ticspro_registers"] = raw_paste

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            lmk_source = (out_dir / "drivers" / "lmk04832.c").read_text(encoding="utf-8")

        self.assertIn("#define LMK04832_CONFIG_FILE_BYTE_COUNT 378U", lmk_source)
        for line in pasted_lines:
            self.assertIn(line, lmk_source)


if __name__ == "__main__":
    unittest.main()
