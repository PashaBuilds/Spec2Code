import json
import os
import re
import socketserver
import tempfile
import threading
import time
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


def add_zynqmp_ps_uart(spec: dict) -> None:
    spec["controllers"].append({
        "id": "ps_uart_0",
        "type": "uart",
        "instance": "XPAR_XUARTPS_0",
        "base_address": "0xFF000000",
        "device_id": 0,
        "driver": "XUartPs",
        "source": "xparameters",
        "zone": "ps",
    })


def add_versal_ps_uart(spec: dict) -> None:
    spec["controllers"].append({
        "id": "ps_uart_0",
        "type": "uart",
        "instance": "XPAR_XUARTPSV_0",
        "base_address": "0xFF000000",
        "device_id": 0,
        "driver": "XUartPsv",
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


class FakeSerial:
    """In-memory serial double: queues a scripted response after each request write."""

    def __init__(self) -> None:
        self.rx = bytearray()
        self.written: list[bytes] = []
        self._lock = threading.Lock()
        self._closed = False

    def read(self, size: int) -> bytes:
        with self._lock:
            if self._closed:
                raise OSError("fake serial closed")
            chunk = bytes(self.rx[:size])
            del self.rx[:size]
        if not chunk:
            time.sleep(0.005)
        return chunk

    def write(self, data: bytes) -> int:
        with self._lock:
            self.written.append(bytes(data))
            if b"op=voltage_read" in data:
                # Console noise on a shared UART must be tolerated by the host.
                self.rx += b"boot noise line\r\n"
                self.rx += b"S2C|id=3|ok=1|status=0|value=0x1A2B|message=ok\r\n"
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        with self._lock:
            self._closed = True


class CoresightEchoHandler(socketserver.StreamRequestHandler):
    """Fake jtagterminal socket: behaves like the generated CoreSight agent."""

    def handle(self) -> None:
        self.wfile.write(b"Spec2Code test bench dev | transport: CoreSight DCC (psu_coresight_0)\r\n")
        self.wfile.flush()
        while True:
            line = self.rfile.readline()
            if not line:
                return
            text = line.strip()
            if not text:
                self.wfile.write(b"> \r\n")
            elif text.startswith(b"S2C|"):
                self.wfile.write(b"S2C|id=5|ok=1|status=0|value=0x42|message=ok\n")
            self.wfile.flush()


class TestbenchTests(unittest.TestCase):
    def test_serial_session_skips_console_noise_and_reads_protocol_response(self) -> None:
        fake = FakeSerial()
        manager = SessionManager()
        status = manager.connect_serial(
            "ser1", "COM7", 115200, 2.0, serial_factory=lambda _p, _b, _t: fake)
        self.assertTrue(status.connected)
        self.assertEqual(status.transport, "serial")
        self.assertEqual(status.serial_port, "COM7")
        self.assertEqual(status.baud, 115200)

        result = manager.send("ser1", BenchCommand(
            host="", port=0, device="u1_ltc2991", operation="voltage_read", command_id=3))
        self.assertEqual(result.parsed["ok"], "1")
        self.assertEqual(result.parsed["value"], "0x1A2B")
        self.assertTrue(result.request_line.startswith("S2C|id=3|device=u1_ltc2991|op=voltage_read"))

        _seq, entries = manager.console("ser1", 0)
        lines = [entry["line"] for entry in entries]
        self.assertIn("boot noise line", lines)
        self.assertTrue(any(line.startswith("S2C|id=3") for line in lines))

        manager.write_raw("ser1", "hello")
        self.assertIn(b"hello\r\n", fake.written)

        # Veri Akisi: giden istek tx, gelen her satir rx olarak kaydedilir.
        _tseq, traffic = manager.traffic("ser1", 0)
        tx_lines = [entry["line"] for entry in traffic if entry["dir"] == "tx"]
        rx_lines = [entry["line"] for entry in traffic if entry["dir"] == "rx"]
        self.assertTrue(any(line.startswith("S2C|id=3") for line in tx_lines))
        self.assertIn("hello", tx_lines)
        self.assertIn("boot noise line", rx_lines)
        self.assertTrue(any(line.startswith("S2C|id=3") and "|ok=" in line for line in rx_lines))
        manager.disconnect("ser1")

    def test_serial_session_times_out_without_response(self) -> None:
        from backend.testbench import TestbenchSessionError

        fake = FakeSerial()
        manager = SessionManager()
        manager.connect_serial(
            "ser2", "COM9", 115200, 0.3, serial_factory=lambda _p, _b, _t: fake)
        with self.assertRaises(TestbenchSessionError):
            manager.send("ser2", BenchCommand(
                host="", port=0, device="u1_ltc2991", operation="id_read", command_id=4))
        manager.disconnect("ser2")
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

    def test_tcp_session_records_tx_rx_traffic(self) -> None:
        manager = SessionManager()
        with socketserver.TCPServer(("127.0.0.1", 0), PersistentHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager.connect("unit_traffic", "127.0.0.1", server.server_address[1], 2)
            try:
                manager.send("unit_traffic", BenchCommand(
                    host="", port=0, device="u1_ltc2991", operation="status_read", command_id=1))
                manager.send("unit_traffic", BenchCommand(
                    host="", port=0, device="u1_ltc2991", operation="voltage_read", command_id=2))
                seq, entries = manager.traffic("unit_traffic", 0)
                # since ile artimli okuma: yalnizca yeni kayitlar doner.
                _seq2, newer = manager.traffic("unit_traffic", 2)
            finally:
                manager.disconnect("unit_traffic")
                thread.join(timeout=2)

        self.assertEqual(seq, 4)
        self.assertEqual([entry["dir"] for entry in entries], ["tx", "rx", "tx", "rx"])
        self.assertIn("op=status_read", entries[0]["line"])
        self.assertIn("message=first", entries[1]["line"])
        self.assertEqual(len(newer), 2)

    def test_coresight_session_bridges_over_fake_jtagterminal_socket(self) -> None:
        # Kopru sahte: bridge_factory xsdb yerine hazir bir TCP portu verir;
        # oturumun geri kalani gercek yol (_TcpBridgeStream + reader thread).
        # pyserial bilerek KULLANILMAZ: paketli exe'de socket:// URL isleyicisi
        # bulunamiyordu ("invalid URL, protocol 'socket' not known").
        server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), CoresightEchoHandler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        manager = SessionManager()
        try:
            status = manager.connect_coresight(
                "cs1", "C:/fake/Vitis", "192.168.0.10", "psu_cortexa53_0", 2.0,
                bridge_factory=lambda _v, _u, _p: (None, server.server_address[1]))
            self.assertTrue(status.connected)
            self.assertEqual(status.transport, "coresight")
            self.assertEqual(status.processor, "psu_cortexa53_0")
            self.assertEqual(status.hw_server_url, "TCP:192.168.0.10:3121")
            self.assertEqual(status.dcc_port, server.server_address[1])

            result = manager.send("cs1", BenchCommand(
                host="", port=0, device="u1_ltc2991", operation="id_read", command_id=5))
            self.assertEqual(result.parsed["ok"], "1")
            self.assertEqual(result.parsed["value"], "0x42")

            # Enter (bos satir) -> agent "> " canlilik istemi doner.
            manager.write_raw("cs1", "")
            deadline = time.time() + 2.0
            prompt_seen = banner_seen = False
            while time.time() < deadline and not (prompt_seen and banner_seen):
                _seq, entries = manager.console("cs1", 0)
                lines = [entry["line"] for entry in entries]
                prompt_seen = any(line.strip() == ">" for line in lines)
                banner_seen = any("Spec2Code test bench" in line for line in lines)
                time.sleep(0.02)
            self.assertTrue(banner_seen, "banner did not arrive over the DCC bridge")
            self.assertTrue(prompt_seen, "liveness prompt did not arrive after Enter")

            _tseq, traffic = manager.traffic("cs1", 0)
            directions = {entry["dir"] for entry in traffic}
            self.assertEqual(directions, {"tx", "rx"})

            sessions = manager.list_sessions()
            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0].transport, "coresight")
        finally:
            manager.disconnect("cs1")
            server.shutdown()
            server.server_close()

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

    def test_lwip_agent_for_freertos_uses_official_socket_mode_pattern(self) -> None:
        # Mirrors the official Xilinx freertos_lwip_echo_server structure:
        # main -> sys_thread_new + vTaskStartScheduler; lwip_init in a thread;
        # xemac_add + xemacif_input_thread in a network thread; the agent
        # itself uses the socket API (BSP api_mode = SOCKET_API).
        spec = load_sample_spec("unit_lwip_agent")
        add_zynqmp_ps_ethernet(spec)
        self.assertEqual(spec["project"]["runtime"], "freertos")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            lwip_header = (out_dir / "tests" / "spec2code_testbench_lwip.h").read_text(encoding="utf-8")
            lwip_source = (out_dir / "tests" / "spec2code_testbench_lwip.c").read_text(encoding="utf-8")
            main_header = (out_dir / "tests" / "spec2code_testbench_lwip_main.h").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_lwip_main.c").read_text(encoding="utf-8")

        self.assertIn("SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT 5000U", lwip_header)
        self.assertIn("SPEC2CODE_TESTBENCH_THREAD_STACKSIZE", lwip_header)
        self.assertIn("void spec2codeTestbenchLwipMainThread(void* vpArg);", lwip_header)
        self.assertIn("XPAR_XEMACPS_0_BASEADDR", lwip_source)
        self.assertIn("xemac_add", lwip_source)
        self.assertIn("lwip_socket(AF_INET, SOCK_STREAM, 0)", lwip_source)
        self.assertIn("xemacif_input_thread", lwip_source)
        self.assertIn("spec2codeTestbenchDispatchLine", lwip_source)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", lwip_source)
        self.assertIn("XSpiPs* spec2codeTestbenchSpiPsHandleGet", lwip_source)
        # Raw-mode constructs must not leak into the socket-mode agent.
        self.assertNotIn("tcp_bind(", lwip_source)
        self.assertNotIn("xemacif_input(&S_sNetif)", lwip_source)
        self.assertIn("int main(void);", main_header)
        self.assertIn("vTaskStartScheduler();", main_source)
        self.assertIn("sys_thread_new", main_source)

    def test_lwip_agent_for_bare_metal_uses_raw_polling_pattern(self) -> None:
        # Mirrors the official standalone lwip_echo_server: RAW API callbacks
        # plus an xemacif_input polling loop (BSP api_mode = RAW_API).
        spec = load_sample_spec("unit_lwip_agent_raw")
        spec["project"]["runtime"] = "bare_metal"
        add_zynqmp_ps_ethernet(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            lwip_source = (out_dir / "tests" / "spec2code_testbench_lwip.c").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_lwip_main.c").read_text(encoding="utf-8")

        self.assertIn("tcp_bind(S_spServerPcb, IP_ADDR_ANY, usPort)", lwip_source)
        self.assertIn("xemacif_input(&S_sNetif)", lwip_source)
        self.assertNotIn("lwip_socket(", lwip_source)
        self.assertNotIn("vTaskStartScheduler", main_source)
        self.assertIn("spec2codeTestbenchLwipInputPoll();", main_source)

    def test_uart_agent_generated_when_transport_is_uart(self) -> None:
        # Polled XUartPs agent per the official xuartps polled example; shares
        # the S2C line protocol and ignores non-"S2C|" console noise.
        spec = load_sample_spec("unit_uart_agent")
        add_zynqmp_ps_ethernet(spec)
        add_zynqmp_ps_uart(spec)
        spec["project"]["testbench_transport"] = "uart"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            uart_header = (out_dir / "tests" / "spec2code_testbench_uart.h").read_text(encoding="utf-8")
            uart_source = (out_dir / "tests" / "spec2code_testbench_uart.c").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_uart_main.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            lwip_generated = (out_dir / "tests" / "spec2code_testbench_lwip.c").exists()

        self.assertIn("XPAR_XUARTPS_0_DEVICE_ID", uart_header)
        self.assertIn("SPEC2CODE_TESTBENCH_UART_BAUD 115200U", uart_header)
        self.assertIn("XUartPs_CfgInitialize", uart_source)
        self.assertIn("XUartPs_SetBaudRate", uart_source)
        self.assertIn("XUartPs_Recv(&S_sTestbenchUart, &ucByte, 1U)", uart_source)
        self.assertIn("spec2codeTestbenchDispatchLine", uart_source)
        self.assertIn("spec2codeTestbenchUartLineIsRequest", uart_source)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", uart_source)
        self.assertIn("spec2codeTestbenchBoardInit();", main_source)
        self.assertIn("S2C-UART-AGENT-READY", main_source)
        # Explicit UART choice must not also emit the lwIP agent.
        self.assertFalse(lwip_generated)
        self.assertEqual(manifest["transport_agent"], "uart")
        self.assertEqual(manifest["uart"]["instance"], "XPAR_XUARTPS_0")

    def test_versal_uart_agent_uses_uartpsv_api(self) -> None:
        # Versal's PS UART is XUartPsv (xuartpsv.h) - same call shape as
        # XUartPs but a distinct driver; the agent must not mix the two.
        spec = load_sample_spec("unit_versal_uart_agent")
        spec["project"]["platform"] = "versal"
        add_versal_ps_uart(spec)
        spec["project"]["testbench_transport"] = "uart"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            uart_header = (out_dir / "tests" / "spec2code_testbench_uart.h").read_text(encoding="utf-8")
            uart_source = (out_dir / "tests" / "spec2code_testbench_uart.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("XPAR_XUARTPSV_0_DEVICE_ID", uart_header)
        self.assertIn('#include "xuartpsv.h"', uart_source)
        self.assertIn("XUartPsv_CfgInitialize", uart_source)
        self.assertIn("XUartPsv_SetBaudRate", uart_source)
        self.assertIn("XUartPsv_Recv(&S_sTestbenchUart, &ucByte, 1U)", uart_source)
        self.assertNotIn("xuartps.h", uart_source.replace("xuartpsv.h", ""))
        self.assertNotIn("XUartPs_", uart_source.replace("XUartPsv_", ""))
        self.assertEqual(manifest["transport_agent"], "uart")
        self.assertEqual(manifest["uart"]["driver"], "XUartPsv")

    def test_self_test_skips_device_init_when_not_requested(self) -> None:
        # Regression (found on zc702): requesting only read ops + self_test
        # used to emit a self test that called <part>DeviceInit anyway ->
        # undefined reference at link time.
        spec = load_sample_spec("unit_selftest_no_init")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xE0004000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [{
            "id": "u1_tmp101", "part": "TMP101",
            "descriptor_ref": "descriptors/tmp101.yaml",
            "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x4A",
                       "via_mux": None, "reset_gpio": None, "irq_line": None},
            "operations_requested": ["temperature_read"],
            "tests_requested": ["self_test"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            test_source = (out_dir / "tests" / "tmp101_test.c").read_text(encoding="utf-8")
        self.assertNotIn("tmp101DeviceInit", test_source)
        self.assertIn("tmp101TemperatureRead", test_source)

    def test_microblaze_uartlite_agent_and_axi_device_gate(self) -> None:
        # MicroBlaze: the UARTLITE agent is generated (single-call init,
        # hardware-fixed baud), and attaching a device to an AXI IIC
        # controller fails loudly instead of emitting XIicPs code that
        # could never compile against the xiic BSP.
        from orchestrator import cmodel

        spec = load_sample_spec("unit_microblaze")
        spec["project"]["platform"] = "microblaze_7series"
        spec["project"]["runtime"] = "bare_metal"
        spec["project"]["testbench_transport"] = "uart"
        spec["controllers"] = [
            {"id": "pl_uart_0", "type": "uart", "instance": "XPAR_AXI_UARTLITE_0",
             "base_address": "0x40600000", "device_id": 0, "driver": "XUartLite",
             "source": "xparameters", "zone": "pl"},
            {"id": "pl_i2c_0", "type": "i2c", "instance": "XPAR_AXI_IIC_0",
             "base_address": "0x40800000", "device_id": 0, "driver": "XIic",
             "source": "xparameters", "zone": "pl"},
        ]
        spec["muxes"] = []
        spec["devices"] = []
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            uart_source = (out_dir / "tests" / "spec2code_testbench_uart.c").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_uart_main.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn('#include "xuartlite.h"', uart_source)
        self.assertIn("XUartLite_Initialize(&S_sTestbenchUart, SPEC2CODE_TESTBENCH_UART_DEVICE_ID)", uart_source)
        self.assertNotIn("SetBaudRate", uart_source)
        self.assertNotIn("LookupConfig", uart_source)
        self.assertIn("uartlite", main_source)
        self.assertEqual(manifest["uart"]["driver"], "XUartLite")

        # Honest gate: a device on the AXI IIC controller must be rejected.
        spec["devices"] = [{
            "id": "u1_tmp101", "part": "TMP101",
            "descriptor_ref": "descriptors/tmp101.yaml",
            "attach": {"controller_id": "pl_i2c_0", "i2c_address": "0x4A",
                       "via_mux": None, "reset_gpio": None, "irq_line": None},
            "operations_requested": ["temperature_read"],
            "tests_requested": [],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cmodel.CodegenError) as ctx:
                codegen.generate(spec, Path(tmp) / "out")
            self.assertIn("does not support", str(ctx.exception))
            self.assertIn("XIic", str(ctx.exception))

    def test_coresight_agent_generated_when_transport_is_coresight(self) -> None:
        # JTAG DCC agent (coresightps_dcc): ayni S2C protokolu, kablo olarak
        # yalnizca JTAG gerekir; host kopruyu xsdb jtagterminal ile kurar.
        spec = load_sample_spec("unit_coresight_agent")
        add_zynqmp_ps_ethernet(spec)  # explicit coresight secimi ETH'i ezmeli
        spec["project"]["testbench_transport"] = "coresight"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            cs_header = (out_dir / "tests" / "spec2code_testbench_coresight.h").read_text(encoding="utf-8")
            cs_source = (out_dir / "tests" / "spec2code_testbench_coresight.c").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_coresight_main.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            lwip_generated = (out_dir / "tests" / "spec2code_testbench_lwip.c").exists()
            uart_generated = (out_dir / "tests" / "spec2code_testbench_uart.c").exists()

        self.assertIn("int spec2codeTestbenchCoresightInit(void);", cs_header)
        self.assertIn('#include "xcoresightpsdcc.h"', cs_source)
        self.assertIn("XCoresightPs_DccRecvByte(0U)", cs_source)
        self.assertIn("XCoresightPs_DccSendByte(0U,", cs_source)
        self.assertIn("spec2codeTestbenchDispatchLine", cs_source)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", cs_source)
        # Bos satir (Enter) canlilik istemi agent dongusunde olmali.
        self.assertIn('spec2codeTestbenchCoresightSendLine("> \\r\\n");', cs_source)
        version = current_app_version()
        self.assertIn(f"Spec2Code test bench {version}", main_source)
        self.assertIn("proje: unit_coresight_agent", main_source)
        self.assertIn("S2C-CORESIGHT-AGENT-READY", main_source)
        # Banner iki kanala da basilmali: seri konsol (xil_printf/stdout=UART)
        # ve DCC (jtagterminal koprusu). BSP stdout ayarina dokunulmaz.
        self.assertIn(f'xil_printf("Spec2Code test bench {version}', main_source)
        self.assertIn(f'spec2codeTestbenchCoresightBannerLine("Spec2Code test bench {version}', main_source)
        self.assertIn('xil_printf("S2C-CORESIGHT-AGENT-READY', main_source)
        self.assertFalse(lwip_generated)
        self.assertFalse(uart_generated)
        self.assertEqual(manifest["transport_agent"], "coresight")
        self.assertEqual(manifest["coresight"]["device"], "psu_coresight_0")
        self.assertEqual(manifest["coresight"]["processor"], "psu_cortexa53_0")

    def test_coresight_transport_rejected_outside_zynqmp(self) -> None:
        from orchestrator import cmodel

        spec = load_sample_spec("unit_coresight_gate")
        spec["project"]["platform"] = "versal"
        add_versal_ps_uart(spec)
        spec["project"]["testbench_transport"] = "coresight"
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(cmodel.CodegenError) as ctx:
                codegen.generate(spec, Path(tmp) / "out")
        self.assertIn("psu_coresight_0", str(ctx.exception))

    def test_uart_agent_banner_and_enter_prompt(self) -> None:
        # Acilista surum/proje banner'i; Enter'a (bos satir) "> " istemi -
        # cakilma/takilma kontrolu seri konsoldan yapilabilsin.
        spec = load_sample_spec("unit_uart_banner")
        add_zynqmp_ps_uart(spec)
        spec["project"]["testbench_transport"] = "uart"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            uart_source = (out_dir / "tests" / "spec2code_testbench_uart.c").read_text(encoding="utf-8")
            main_source = (out_dir / "tests" / "spec2code_testbench_uart_main.c").read_text(encoding="utf-8")

        version = current_app_version()
        self.assertIn(f"Spec2Code test bench {version}", main_source)
        self.assertIn("proje: unit_uart_banner", main_source)
        self.assertIn("transport: UART", main_source)
        self.assertIn('spec2codeTestbenchUartSendLine("> \\r\\n");', uart_source)
        # CR tek basina da satiri bitirmeli (PuTTY Enter'i yalniz CR gonderir).
        self.assertIn("uiPrevWasCr", uart_source)

    def test_testbench_transport_auto_prefers_eth_and_falls_back_to_uart(self) -> None:
        spec = load_sample_spec("unit_transport_auto")
        add_zynqmp_ps_ethernet(spec)
        add_zynqmp_ps_uart(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["transport_agent"], "lwip")
            self.assertTrue((out_dir / "tests" / "spec2code_testbench_lwip.c").exists())
            self.assertFalse((out_dir / "tests" / "spec2code_testbench_uart.c").exists())

        spec = load_sample_spec("unit_transport_auto_uart")
        add_zynqmp_ps_uart(spec)  # no Ethernet controller this time
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["transport_agent"], "uart")
            self.assertTrue((out_dir / "tests" / "spec2code_testbench_uart.c").exists())
            self.assertFalse((out_dir / "tests" / "spec2code_testbench_lwip.c").exists())

    def test_testbench_omits_controller_types_missing_from_hardware(self) -> None:
        # ZCU102-like design: PS SPI disabled, only I2C + QSPI (+ PS Ethernet).
        # BSP will not contain xspips.h, so generated code must not include it.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {
                "id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
                "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
                "source": "xparameters", "zone": "ps",
            },
            {
                "id": "ps_qspi_0", "type": "qspi", "instance": "XPAR_XQSPIPSU_0",
                "base_address": "0xFF0F0000", "device_id": 0, "driver": "XQspiPsu",
                "source": "xparameters", "zone": "ps",
            },
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {
                "id": "u1_ltc2991", "part": "LTC2991",
                "descriptor_ref": "descriptors/ltc2991.yaml",
                "attach": {
                    "controller_id": "ps_i2c_0", "i2c_address": "0x48",
                    "via_mux": None, "reset_gpio": None, "irq_line": None,
                },
                "operations_requested": ["device_init", "voltage_read", "temperature_read"],
                "tests_requested": ["self_test"],
            },
            {
                "id": "u2_mt25qu02g", "part": "MT25QU02G",
                "descriptor_ref": "descriptors/mt25qu02g.yaml",
                "attach": {
                    "controller_id": "ps_qspi_0", "spi_chip_select": 0,
                    "address_width": 32, "reset_gpio": None,
                },
                "operations_requested": ["device_init", "id_read", "data_read"],
                "tests_requested": ["self_test"],
            },
        ]
        add_zynqmp_ps_ethernet(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)

            ops_header = (out_dir / "tests" / "unit_no_spi_testbench_testbench_ops.h").read_text(encoding="utf-8")
            ops_source = (out_dir / "tests" / "unit_no_spi_testbench_testbench_ops.c").read_text(encoding="utf-8")
            lwip_source = (out_dir / "tests" / "spec2code_testbench_lwip.c").read_text(encoding="utf-8")

        for content in (ops_header, ops_source, lwip_source):
            self.assertNotIn("xspips.h", content)
            self.assertNotIn("XSpiPs", content)
        self.assertIn('#include "xiicps.h"', ops_header)
        self.assertIn('#include "xqspipsu.h"', ops_header)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", ops_header)
        self.assertIn("XQspiPsu* spec2codeTestbenchQspiPsuHandleGet", ops_header)
        self.assertIn("XIicPs* spec2codeTestbenchIicPsHandleGet", lwip_source)
        self.assertIn("XQspiPsu* spec2codeTestbenchQspiPsuHandleGet", lwip_source)

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

    def test_app_version_can_be_read_from_packaged_metadata_without_frontend_source(self) -> None:
        version_file = ROOT / "spec2code_version.txt"
        source_version = ROOT / "frontend" / "src" / "lib" / "version.ts"
        backup = source_version.with_suffix(".ts.testbak")
        self.assertFalse(backup.exists())
        old_env = {name: os.environ.pop(name, None) for name in ("SPEC2CODE_VERSION", "VITE_SPEC2CODE_VERSION", "RELEASE_VERSION")}
        try:
            version_file.write_text("v9.8.7\n", encoding="utf-8")
            source_version.rename(backup)
            self.assertEqual(codegen._app_version(), "v9.8.7")
        finally:
            if backup.exists():
                backup.rename(source_version)
            version_file.unlink(missing_ok=True)
            for name, value in old_env.items():
                if value is not None:
                    os.environ[name] = value

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

    def test_vitis_error_mapper_does_not_treat_freertos_archive_tail_as_root_cause(self) -> None:
        issues = map_vitis_errors("aarch64-none-elf-ar: creating ../../lib/libfreertos.a\n")

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["category"], "unclassified")
        self.assertNotIn("aarch64-none-elf-ar", issues[0]["message"])
        self.assertIn("BSP archive", issues[0]["suggestion"])


if __name__ == "__main__":
    unittest.main()
