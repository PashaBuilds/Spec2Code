import json
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from backend.testbench import TestbenchCommand, format_command, parse_response, send_command
from backend.vitis_errors import map_vitis_errors
from orchestrator import codegen


ROOT = Path(__file__).resolve().parent.parent


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


class OneShotHandler(socketserver.BaseRequestHandler):
    response = b"S2C|id=7|ok=1|status=0|value=0x12|data=AABB|message=ok\n"

    def handle(self) -> None:
        self.request.recv(4096)
        self.request.sendall(self.response)


class TestbenchTests(unittest.TestCase):
    def test_command_formatter_and_response_parser(self) -> None:
        line = format_command(TestbenchCommand(
            host="127.0.0.1",
            port=5000,
            device="u1_ltc2991",
            operation="register_read",
            command_id=7,
            register="STATUS_HIGH",
            register_address=0x01,
            data_hex="DE AD|BE EF",
        ))

        self.assertEqual(
            line,
            "S2C|id=7|device=u1_ltc2991|op=register_read|reg=STATUS_HIGH|reg_addr=0x1|data=DEADBEEF\n",
        )
        self.assertEqual(parse_response("S2C|id=7|ok=1|data=AABB\n")["data"], "AABB")

    def test_send_command_reads_one_line_response(self) -> None:
        with socketserver.TCPServer(("127.0.0.1", 0), OneShotHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = send_command(TestbenchCommand(
                host="127.0.0.1",
                port=server.server_address[1],
                device="u1_ltc2991",
                operation="status_read",
                command_id=7,
            ))
            thread.join(timeout=2)

        self.assertEqual(result.parsed["ok"], "1")
        self.assertEqual(result.parsed["data"], "AABB")

    def test_codegen_filters_testbench_to_requested_operations(self) -> None:
        spec = load_sample_spec("unit_testbench_filter")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            ops = (out_dir / "tests" / "unit_testbench_filter_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("ltc2991VoltageRead", ops)
        self.assertNotIn("ltc2991VccRead", ops)
        self.assertNotIn("ltc2991CurrentRead", ops)
        ltc_ops = {op["name"] for op in manifest["devices"][0]["operations"]}
        self.assertIn("voltage_read", ltc_ops)
        self.assertNotIn("vcc_read", ltc_ops)
        self.assertNotIn("current_read", ltc_ops)

    def test_ltc2991_current_operation_generates_driver_dispatch_and_manifest(self) -> None:
        spec = load_sample_spec("unit_ltc2991_current")
        spec["devices"][0]["operations_requested"] = [
            "device_init",
            "voltage_read",
            "current_read",
            "temperature_read",
            "vcc_read",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            header = (out_dir / "drivers" / "ltc2991.h").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_ltc2991_current_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("int ltc2991CurrentRead(XIicPs* spIic, unsigned short* uspCurrent);", header)
        self.assertIn("ltc2991CurrentRead(spIic, usArrValues)", ops)
        current = next(op for op in manifest["devices"][0]["operations"] if op["name"] == "current_read")
        self.assertEqual(current["fixed_read_length"], 16)
        self.assertEqual(current["risk"], "safe")

    def test_i2c_eeprom_testbench_uses_memory_operations_not_register_macros(self) -> None:
        spec = load_sample_spec("unit_eeprom_testbench")
        spec["devices"] = [
            {
                "id": "u1_24lc32a",
                "part": "24LC32A",
                "descriptor_ref": "descriptors/24lc32a.yaml",
                "attach": {
                    "controller_id": "ps_i2c_0",
                    "i2c_address": "0x50",
                    "via_mux": None,
                    "reset_gpio": None,
                    "irq_line": None,
                },
                "operations_requested": ["device_init", "data_read", "byte_write", "page_write"],
                "tests_requested": ["self_test"],
            },
        ]
        spec["muxes"] = []
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            ops = (out_dir / "tests" / "unit_eeprom_testbench_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertNotIn("DEV24LC32A_REG_", ops)
        self.assertNotIn("register_read", ops)
        self.assertIn("dev24lc32aDataRead(spIic, spRequest->uiAddress, ucArrData, uiLength)", ops)
        self.assertIn("dev24lc32aByteWrite(spIic, spRequest->uiAddress, (unsigned char)spRequest->uiValue)", ops)
        self.assertIn("dev24lc32aPageWrite(spIic, spRequest->uiAddress, spRequest->ucArrData, spRequest->uiDataLength)", ops)
        ops_by_name = {op["name"]: op for op in manifest["devices"][0]["operations"]}
        self.assertTrue(ops_by_name["data_read"]["requires_address"])
        self.assertTrue(ops_by_name["data_read"]["requires_length"])
        self.assertTrue(ops_by_name["page_write"]["requires_data"])

    def test_vitis_error_mapper_classifies_common_build_failures(self) -> None:
        issues = map_vitis_errors(
            "drivers/foo.c:12:10: fatal error: xiicps.h: No such file or directory\n"
            "collect2.exe: error: ld returned 1 exit status\n"
            "undefined reference to `ltc2991VccRead'\n"
            "main.c:8:5: error: 'XPAR_XIICPS_0_DEVICE_ID' undeclared\n"
        )
        categories = {issue["category"] for issue in issues}
        self.assertIn("missing_include", categories)
        self.assertIn("undefined_reference", categories)
        self.assertIn("missing_xparameter", categories)


if __name__ == "__main__":
    unittest.main()
