import json
import re
import socketserver
import tempfile
import threading
import unittest
from pathlib import Path

from backend.testbench import (
    TestbenchCommand as BenchCommand,
    TestbenchSessionManager as SessionManager,
    format_command,
    parse_response,
    send_command,
)
from backend.vitis_errors import map_vitis_errors
from orchestrator import codegen


ROOT = Path(__file__).resolve().parent.parent


def current_app_version() -> str:
    text = (ROOT / "frontend" / "src" / "lib" / "version.ts").read_text(encoding="utf-8")
    match = re.search(r'"(v\d+\.\d+\.\d+)"', text)
    if not match:
        raise AssertionError("APP_VERSION fallback was not found")
    return match.group(1)


def load_sample_spec(project_name: str) -> dict:
    spec = json.loads((ROOT / "specs/samples/radar_io_board.spec.json").read_text(encoding="utf-8"))
    spec["project"] = {**spec["project"], "name": project_name}
    return spec


def add_zynqmp_ps_ethernet(spec: dict) -> None:
    spec["controllers"].append({
        "id": "ps_eth_0",
        "type": "eth",
        "instance": "XPAR_XEMACPS_0",
        "base_address": "0xFF0B0000",
        "device_id": 0,
        "driver": "XEmacPs",
        "source": "xparameters",
        "zone": "ps",
    })


class OneShotHandler(socketserver.BaseRequestHandler):
    response = b"S2C|id=7|ok=1|status=0|value=0x12|data=AABB|message=ok\n"

    def handle(self) -> None:
        self.request.recv(4096)
        self.request.sendall(self.response)


class PersistentHandler(socketserver.BaseRequestHandler):
    requests: list[str] = []
    responses = [
        b"S2C|id=1|ok=1|status=0|value=0x11|message=first\n",
        b"S2C|id=2|ok=1|status=0|value=0x22|message=second\n",
    ]

    def handle(self) -> None:
        reader = self.request.makefile("rb")
        for response in self.responses:
            line = reader.readline()
            if not line:
                break
            self.__class__.requests.append(line.decode("ascii", errors="replace").strip())
            self.request.sendall(response)


class TestbenchTests(unittest.TestCase):
    def test_command_formatter_and_response_parser(self) -> None:
        line = format_command(BenchCommand(
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

        version_line = format_command(BenchCommand(
            host="127.0.0.1",
            port=5000,
            device="spec2code",
            operation="spec2code_version",
            command_id=8,
        ))
        self.assertEqual(version_line, "S2C|id=8|device=spec2code|op=spec2code_version\n")

    def test_send_command_reads_one_line_response(self) -> None:
        with socketserver.TCPServer(("127.0.0.1", 0), OneShotHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            result = send_command(BenchCommand(
                host="127.0.0.1",
                port=server.server_address[1],
                device="u1_ltc2991",
                operation="status_read",
                command_id=7,
            ))
            thread.join(timeout=2)

        self.assertEqual(result.parsed["ok"], "1")
        self.assertEqual(result.parsed["data"], "AABB")

    def test_session_manager_reuses_one_tcp_connection(self) -> None:
        PersistentHandler.requests = []
        manager = SessionManager()
        with socketserver.TCPServer(("127.0.0.1", 0), PersistentHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager.connect("unit_persistent", "127.0.0.1", server.server_address[1], 2)
            try:
                first = manager.send("unit_persistent", BenchCommand(
                    host="127.0.0.1",
                    port=server.server_address[1],
                    device="u1_ltc2991",
                    operation="status_read",
                    command_id=1,
                ))
                second = manager.send("unit_persistent", BenchCommand(
                    host="127.0.0.1",
                    port=server.server_address[1],
                    device="u1_ltc2991",
                    operation="voltage_read",
                    command_id=2,
                ))
            finally:
                manager.disconnect("unit_persistent")
                thread.join(timeout=2)

        self.assertEqual(first.parsed["value"], "0x11")
        self.assertEqual(second.parsed["value"], "0x22")
        self.assertEqual(len(PersistentHandler.requests), 2)
        self.assertIn("op=status_read", PersistentHandler.requests[0])
        self.assertIn("op=voltage_read", PersistentHandler.requests[1])

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

    def test_duplicate_i2c_part_emits_one_register_resolver(self) -> None:
        spec = load_sample_spec("unit_duplicate_ltc2991_testbench")
        second = json.loads(json.dumps(spec["devices"][0]))
        second["id"] = "u99_ltc2991"
        second["attach"] = {**second["attach"], "via_mux": None}
        spec["devices"].append(second)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            ops = (out_dir / "tests" / "unit_duplicate_ltc2991_testbench_testbench_ops.c").read_text(encoding="utf-8")

        self.assertEqual(ops.count("static int ltc2991TestbenchRegisterResolve"), 1)
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrDevice, "u12_ltc2991")', ops)
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrDevice, "u99_ltc2991")', ops)

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

    def test_lwip_target_agent_is_generated_for_zynqmp_ps_ethernet(self) -> None:
        spec = load_sample_spec("unit_lwip_agent")
        add_zynqmp_ps_ethernet(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            lwip_header = (out_dir / "tests" / "spec2code_testbench_lwip.h").read_text(encoding="utf-8")
            lwip_source = (out_dir / "tests" / "spec2code_testbench_lwip.c").read_text(encoding="utf-8")
            main_header = (out_dir / "tests" / "spec2code_testbench_lwip_main.h").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_lwip_main.c").read_text(encoding="utf-8")

        self.assertIn("SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT 5000U", lwip_header)
        self.assertIn("XPAR_XEMACPS_0_BASEADDR", lwip_source)
        self.assertIn("xemac_add", lwip_source)
        self.assertIn("tcp_bind(S_spServerPcb, IP_ADDR_ANY, usPort)", lwip_source)
        self.assertIn("spec2codeTestbenchDispatchLine", lwip_source)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", lwip_source)
        self.assertIn("XSpiPs* spec2codeTestbenchSpiPsHandleGet", lwip_source)
        self.assertIn("int main(void);", main_header)
        self.assertIn("spec2codeTestbenchLwipInputPoll();", main_source)

    def test_testbench_agent_version_command_is_generated(self) -> None:
        spec = load_sample_spec("unit_agent_version")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            protocol_source = (out_dir / "tests" / "spec2code_testbench_protocol.c").read_text(encoding="utf-8")
            ops_source = (out_dir / "tests" / "unit_agent_version_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads((out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        version = current_app_version()
        self.assertEqual(manifest["agent_version"], version)
        self.assertIn(f'#define SPEC2CODE_TESTBENCH_AGENT_VERSION "{version}"', ops_source)
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "spec2code_version")', ops_source)
        self.assertIn('spec2codeTestbenchMessageSet(spResponse, "Spec2Code " SPEC2CODE_TESTBENCH_AGENT_VERSION);', ops_source)
        self.assertIn("if (spRequest->cArrOperation[0] == '\\0')", protocol_source)

    def test_lwip_target_agent_is_not_generated_without_ethernet(self) -> None:
        spec = load_sample_spec("unit_no_lwip_agent")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            self.assertFalse((out_dir / "tests" / "spec2code_testbench_lwip.c").exists())
            self.assertFalse((out_dir / "tests" / "spec2code_testbench_lwip_main.c").exists())

    def test_vitis_error_mapper_classifies_common_build_failures(self) -> None:
        issues = map_vitis_errors(
            "drivers/foo.c:12:10: fatal error: xiicps.h: No such file or directory\n"
            "collect2.exe: error: ld returned 1 exit status\n"
            "undefined reference to `ltc2991VccRead'\n"
            "main.c:8:5: error: 'XPAR_XIICPS_0_DEVICE_ID' undeclared\n"
            "cc1.exe: fatal error: *.c: Invalid argument\n"
            "make[1]: *** [Makefile:46: psu_cortexa53_0/libsrc/mem_pcie_intr_v1_0/src/make.libs] Error 2\n"
        )
        categories = {issue["category"] for issue in issues}
        self.assertIn("missing_include", categories)
        self.assertIn("undefined_reference", categories)
        self.assertIn("missing_xparameter", categories)
        self.assertIn("custom_ip_bsp_driver", categories)


if __name__ == "__main__":
    unittest.main()
