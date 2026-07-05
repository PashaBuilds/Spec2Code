"""user_descriptors: kullanıcı descriptor'ı çözümleme önceliği, doğrulayıcı ve üretim.

Amaç: paketli uygulamada kullanıcı kendi entegresinin YAML'ını user_descriptors/
klasörüne koyduğunda (veya Import ekranından yüklediğinde) Generate / Test Bench /
Registers zincirinin yerleşik entegrelerle birebir aynı şekilde çalışması.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from orchestrator import codegen
from orchestrator.descriptor_check import validate_descriptor
from tests.test_testbench import add_zynqmp_ps_ethernet, load_sample_spec

VALID_DESCRIPTOR = """\
descriptor_version: "1.0"
part: "MYMON16"
manufacturer: "Acme"
summary: "Kurgusal 2 kanalli monitor (user descriptor testi)."
transport:
  type: i2c
  address_width: 8
  default_address: 0x4C
  byte_order: big
access_primitives:
  read_register:  { pattern: write_addr_then_read, width_bytes: 1 }
  write_register: { pattern: write_addr_then_data, width_bytes: 1 }
registers:
  - name: STATUS
    offset: 0x00
    width: 8
    access: ro
    reset: 0x00
    fields:
      - { name: T_READY, bits: "1" }
  - name: CONTROL
    offset: 0x01
    width: 8
    access: rw
    reset: 0x00
  - { name: T_MSB, offset: 0x06, width: 8, access: ro, reset: 0x00 }
  - { name: T_LSB, offset: 0x07, width: 8, access: ro, reset: 0x00 }
operations:
  - name: device_init
    description: "Etkinlestir."
    steps:
      - { op: write_register, reg: CONTROL, value: 0x10 }
  - name: temperature_read
    returns: "int32"
    description: "0.01 C."
    convert: { mask: 0x1FFF, signed_bits: 13, scale_num: 625, scale_den: 100, unit: "0.01 C" }
    steps:
      - { op: poll, reg: STATUS, field: T_READY, until: 1 }
      - { op: read_register, reg: T_MSB }
      - { op: read_register, reg: T_LSB }
test_hints:
  post_init_status: { reg: STATUS }
  self_test: { description: "Sicaklik okunur." }
"""


class _UserDirMixin(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.user_dir = Path(self._tmp.name)
        self._old_env = os.environ.get("SPEC2CODE_USER_DESCRIPTORS")
        os.environ["SPEC2CODE_USER_DESCRIPTORS"] = str(self.user_dir)

    def tearDown(self) -> None:
        if self._old_env is None:
            os.environ.pop("SPEC2CODE_USER_DESCRIPTORS", None)
        else:
            os.environ["SPEC2CODE_USER_DESCRIPTORS"] = self._old_env
        self._tmp.cleanup()


class DescriptorValidatorTests(unittest.TestCase):
    def test_valid_descriptor_passes(self) -> None:
        import yaml

        self.assertEqual(validate_descriptor(yaml.safe_load(VALID_DESCRIPTOR)), [])

    def test_structural_errors_are_reported_in_turkish_with_paths(self) -> None:
        import yaml

        doc = yaml.safe_load(VALID_DESCRIPTOR)
        doc["registers"].append({"name": "STATUS", "offset": 0x00, "width": 8, "access": "xx"})
        doc["operations"][1]["steps"][0]["field"] = "YOK"
        doc["operations"][1]["steps"].append({"op": "read_magic", "reg": "STATUS"})
        doc["operations"][1]["returns"] = "float"
        errors = "\n".join(validate_descriptor(doc))
        self.assertIn("tekrar ediyor", errors)          # ad + offset benzersizliği
        self.assertIn("ro/rw/wo/reserved", errors)       # access kümesi
        self.assertIn("fields listesinde yok", errors)   # poll alanı
        self.assertIn("desteklenmiyor", errors)          # bilinmeyen adım
        self.assertIn("returns", errors)                 # dönüş biçimi

    def test_scalar_read_budget_is_enforced(self) -> None:
        import yaml

        doc = yaml.safe_load(VALID_DESCRIPTOR)
        doc["operations"][1]["steps"] = [
            {"op": "read_register", "reg": "T_MSB"} for _ in range(5)
        ]
        errors = "\n".join(validate_descriptor(doc))
        self.assertIn("4'ü aşamaz", errors)


class ResolutionPrecedenceTests(_UserDirMixin):
    def test_user_descriptor_shadows_builtin_by_part_and_by_ref(self) -> None:
        # Kullanıcı, yerleşik bir haritayı düzeltebilmeli: aynı ada sahip
        # dosya hem ad-bazlı hem ref-bazlı çözümde yerleşiği gölgeler.
        (self.user_dir / "ltc2991.yaml").write_text(
            'part: "LTC2991"\nsummary: "USER OVERRIDE"\ntransport: { type: i2c }\n',
            encoding="utf-8")
        loader = codegen.make_descriptor_loader()
        self.assertEqual(loader("LTC2991").get("summary"), "USER OVERRIDE")
        self.assertEqual(loader("descriptors/ltc2991.yaml").get("summary"), "USER OVERRIDE")

    def test_builtin_resolution_still_works_without_user_file(self) -> None:
        loader = codegen.make_descriptor_loader()
        self.assertEqual(loader("LTC2991").get("part"), "LTC2991")


class UserDescriptorGenerateTests(_UserDirMixin):
    def test_generate_produces_full_support_from_user_descriptor_only(self) -> None:
        # Yerleşik katalogda OLMAYAN parça yalnız user_descriptors/ içinde:
        # Generate sürücüyü, testbench dispatch'ini ve manifest'i yerleşik
        # entegrelerle birebir aynı zincirden üretmeli.
        (self.user_dir / "mymon16.yaml").write_text(VALID_DESCRIPTOR, encoding="utf-8")
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {"id": "u1_mymon16", "part": "MYMON16",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x4C",
                        "via_mux": None, "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "temperature_read"],
             "tests_requested": ["self_test"]},
        ]
        add_zynqmp_ps_ethernet(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            driver = (out_dir / "drivers" / "mymon16.c").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_no_spi_testbench_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("int mymon16TemperatureRead(XIicPs* spIic, int* ipTemperature)", driver)
        self.assertIn("mymon16DeviceInit", ops)
        device = next(d for d in manifest["devices"] if d["part"] == "MYMON16")
        self.assertEqual({r["name"] for r in device["registers"]},
                         {"STATUS", "CONTROL", "T_MSB", "T_LSB"})
        op_names = {op["name"] for op in device["operations"]}
        self.assertIn("temperature_read", op_names)
        self.assertIn("register_read", op_names)
        temp_op = next(op for op in device["operations"] if op["name"] == "temperature_read")
        self.assertEqual(temp_op["result_unit"], "0.01 C")


class UserDescriptorRoutesTests(_UserDirMixin):
    def test_upload_validates_saves_and_lists_with_shadow_flag(self) -> None:
        from backend.api import routes

        result = routes.upload_user_descriptor(routes.UserDescriptorUpload(content=VALID_DESCRIPTOR))
        self.assertEqual(result["saved"], "mymon16.yaml")
        self.assertFalse(result["overrides_builtin"])
        listed = routes.list_user_descriptors()
        self.assertEqual(listed["dir"], str(self.user_dir))
        entry = next(e for e in listed["descriptors"] if e["part"] == "MYMON16")
        self.assertEqual(entry["registers"], 4)
        # /descriptors birlesik listesinde "user" kaynakli gorunur.
        merged = routes.list_descriptors()["descriptors"]
        mymon = next(d for d in merged if d["part"] == "MYMON16")
        self.assertEqual(mymon["source"], "user")
        # Katalogda parca secici icin cihaz olarak yer alir.
        catalog = routes.get_catalog()
        user_devices = [d for d in catalog["devices"] if d.get("status") == "user"]
        self.assertTrue(any(d["part"] == "MYMON16" for d in user_devices))
        routes.delete_user_descriptor("mymon16.yaml")
        self.assertFalse((self.user_dir / "mymon16.yaml").exists())

    def test_upload_rejects_invalid_descriptor_with_field_errors(self) -> None:
        from backend.api import routes

        broken = VALID_DESCRIPTOR.replace('op: poll', 'op: pool')
        with self.assertRaises(HTTPException) as ctx:
            routes.upload_user_descriptor(routes.UserDescriptorUpload(content=broken))
        detail = ctx.exception.detail
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertTrue(any("desteklenmiyor" in e for e in detail["errors"]))

    def test_delete_rejects_path_escape(self) -> None:
        from backend.api import routes

        with self.assertRaises(HTTPException):
            routes.delete_user_descriptor("..\\descriptors\\ltc2991.yaml")


if __name__ == "__main__":
    unittest.main()
