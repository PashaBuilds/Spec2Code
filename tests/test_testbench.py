import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from backend.testbench import (
    TestbenchCommand as BenchCommand,
    TestbenchSessionError as SessionError,
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


class StaleThenAnswerHandler(socketserver.BaseRequestHandler):
    """Saha senaryosu: ilk komuta cevap gelmez (ajan meşgul), ikinci komut
    gönderilince önce GEÇ kalan ilk cevap, sonra doğru cevap gelir."""

    def handle(self) -> None:
        reader = self.request.makefile("rb")
        if not reader.readline():
            return
        if not reader.readline():
            return
        self.request.sendall(b"S2C|id=1|ok=1|status=0|value=0x11|message=late\n")
        self.request.sendall(b"S2C|id=2|ok=1|status=0|value=0x22|message=fresh\n")


class StaleOnlyFakeSerial(FakeSerial):
    """Komut id=4 gönderilince yalnız BAYAT (id=9) bir yanıt kuyruklar."""

    def write(self, data: bytes) -> int:
        with self._lock:
            self.written.append(bytes(data))
            if b"id=4" in data:
                self.rx += b"S2C|id=9|ok=1|status=0|value=0x99|message=stale\r\n"
        return len(data)


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

    def test_tcp_timeout_keeps_session_and_stale_response_is_skipped(self) -> None:
        # Saha bulgusu (2026-07-05): ajan bir komutu uzun sürede işlerken
        # timeout'a uğrayan TCP oturumu KAPANIYOR ve sonraki komut geç kalan
        # yanıtı kendi cevabı sanabiliyordu. Beklenen: timeout oturumu açık
        # bırakır; id eşleşmeyen geç yanıt sonraki gönderimde atlanır.
        manager = SessionManager()
        with socketserver.TCPServer(("127.0.0.1", 0), StaleThenAnswerHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager.connect("unit_stale", "127.0.0.1", server.server_address[1], 0.5)
            try:
                with self.assertRaises(SessionError):
                    manager.send("unit_stale", BenchCommand(
                        host="127.0.0.1", port=server.server_address[1],
                        device="u1_ltc2991", operation="temperature_read", command_id=1))
                # Timeout oturumu düşürmemeli.
                self.assertTrue(manager.status("unit_stale").connected)
                second = manager.send("unit_stale", BenchCommand(
                    host="127.0.0.1", port=server.server_address[1],
                    device="u1_ltc2991", operation="vcc_read", command_id=2))
            finally:
                manager.disconnect("unit_stale")
                thread.join(timeout=2)

        # Geç kalan id=1 yanıtı atlanır; komut kendi (id=2) yanıtını alır.
        self.assertEqual(second.parsed["id"], "2")
        self.assertEqual(second.parsed["value"], "0x22")

    def test_serial_stale_response_is_not_returned_as_result(self) -> None:
        # Önceki davranış: id eşleşmeyen satır "fallback" olarak komutun
        # cevabıymış gibi dönüyordu. Beklenen: yalnız id=0 (parse hatası)
        # fallback olur; bayat id'ler düşer ve komut timeout ile biter.
        fake = StaleOnlyFakeSerial()
        manager = SessionManager()
        manager.connect_serial(
            "ser_stale", "COM8", 115200, 0.4, serial_factory=lambda _p, _b, _t: fake)
        try:
            with self.assertRaises(SessionError):
                manager.send("ser_stale", BenchCommand(
                    host="", port=0, device="u1_ltc2991",
                    operation="temperature_read", command_id=4))
        finally:
            manager.disconnect("ser_stale")

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

    def test_ltm4681_pmbus_codegen_l11_l16_and_word_register_filter(self) -> None:
        # LTM4681 (Rev A datasheet): PMBus dual-die module. READ_VOUT is
        # Linear16 with exponent hardwired to -12 (VOUT_MODE=0x14) -> mV =
        # raw*1000/4096; VIN/IOUT/TEMP/POUT are Linear11 (dynamic exponent).
        spec = load_sample_spec("unit_ltm4681")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [{
            "id": "u1_ltm4681", "part": "LTM4681",
            "descriptor_ref": "descriptors/ltm4681.yaml",
            "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x4F",
                       "via_mux": None, "reset_gpio": None, "irq_line": None},
            "operations_requested": ["device_init", "id_read", "status_read", "vout_read",
                                     "voltage_read", "current_read", "temperature_read", "power_read"],
            "tests_requested": ["self_test"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            driver = (out_dir / "drivers" / "ltm4681.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        # Linear11 decode: two's complement 11-bit mantissa + 5-bit exponent,
        # 64-bit intermediate so positive exponents cannot overflow.
        self.assertIn("iCode -= 2048", driver)
        self.assertIn("iExp -= 32", driver)
        self.assertIn("llValue", driver)
        # Linear16 VOUT with fixed -12 exponent.
        self.assertIn("* 1000U) / 4096U", driver)
        device_entry = manifest["devices"][0]
        regs_by_name = {reg["name"]: reg for reg in device_entry["registers"]}
        # Word (16-bit) PMBus komutlari da artik listede: generic R/W
        # genislik-farkindali ve SMBus read/write-word ile ayni tel bicimini
        # kullanir (komut + 2 bayt, little-endian). Byte komutlar 8 kalir.
        self.assertIn("PAGE", regs_by_name)
        self.assertIn("STATUS_BYTE", regs_by_name)
        self.assertEqual(regs_by_name["STATUS_BYTE"]["width"], 8)
        self.assertIn("READ_VOUT_W", regs_by_name)
        self.assertEqual(regs_by_name["READ_VOUT_W"]["width"], 16)
        ops = {op["name"] for op in device_entry["operations"]}
        self.assertIn("register_write", ops)  # PAGE ile kanal seçimi
        self.assertIn("vout_read", ops)

    def test_spi_tics_register_rw_ops_with_honest_readback_gate(self) -> None:
        # Generic register access over the 24-bit TICS frame: every SPI part
        # with a register model gets register_write (same word format as
        # device_init). register_read is emitted only when the descriptor
        # carries a datasheet-verified readback block; its hardware/config
        # precondition travels to the UI as a "KOŞUL:" note (LMK04832:
        # SNAS688C 8.6 - data on SDIO or a MUX pin; LMX2820: SNAS783C 7.3.6 -
        # dedicated MUXOUT readback output, no config).
        spec = load_sample_spec("unit_spi_reg_rw")
        spec["controllers"] = [
            {"id": "ps_spi_0", "type": "spi", "instance": "XPAR_XSPIPS_0",
             "base_address": "0xFF040000", "device_id": 0, "driver": "XSpiPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {
                "id": "u1_lmk04832", "part": "LMK04832",
                "descriptor_ref": "descriptors/lmk04832.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 0,
                           "reset_gpio": None, "irq_line": None},
                "operations_requested": ["device_init", "pll1_lock_detect"],
                "tests_requested": ["self_test"],
                "config": {"ticspro_registers": ["0x000010", "0x016302"]},
            },
            {
                "id": "u2_lmx2820", "part": "LMX2820",
                "descriptor_ref": "descriptors/lmx2820.yaml",
                "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 1,
                           "reset_gpio": None, "irq_line": None},
                "operations_requested": ["device_init"],
                "tests_requested": ["self_test"],
                "config": {"ticspro_registers": ["0x004070", "0x230000"]},
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            ops_source = (out_dir / "tests" / f"{spec['project']['name']}_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        devices = {device["id"]: device for device in manifest["devices"]}
        lmk_ops = {op["name"]: op for op in devices["u1_lmk04832"]["operations"]}
        lmx_ops = {op["name"]: op for op in devices["u2_lmx2820"]["operations"]}
        self.assertIn("register_write", lmk_ops)
        self.assertIn("register_read", lmk_ops)
        self.assertIn("KOŞUL", lmk_ops["register_read"]["description"])
        self.assertIn("SPI_3WIRE_DIS", lmk_ops["register_read"]["description"])
        self.assertIn("register_write", lmx_ops)
        self.assertIn("register_read", lmx_ops)
        self.assertIn("MUXOUT", lmx_ops["register_read"]["description"])
        self.assertEqual(lmx_ops["register_read"]["fixed_read_length"], 2)  # 16-bit veri
        # 16-bit LMX registers are the native frame width -> in the manifest.
        lmx_regs = {reg["name"]: reg for reg in devices["u2_lmx2820"]["registers"]}
        self.assertIn("R0", lmx_regs)
        self.assertEqual(lmx_regs["R0"]["width"], 16)
        self.assertEqual(lmx_regs["R74"]["access"], "ro")  # rb_* durum registerlari

        # Agent side: shared SPI helpers + wide (15-bit) resolver + packing.
        self.assertIn("spec2codeTestbenchSpiRegisterWrite", ops_source)
        self.assertIn("spec2codeTestbenchSpiRegisterRead", ops_source)
        self.assertIn("unsigned int* uipReg", ops_source)
        # LMK04832 write word: addr<<8 | 8-bit data; read word carries R/W=1 at bit 23.
        self.assertIn("((uiReg & 0x7FFFU) << 8U) | ((unsigned int)spRequest->uiValue & 0xFFU)", ops_source)
        self.assertIn("((unsigned int)1U << 23U) | ((uiReg & 0x7FFFU) << 8U)", ops_source)
        # LMX2820 words: addr<<16 | 16-bit data; read pulls 2 data bytes.
        self.assertIn("((uiReg & 0x7FU) << 16U) | ((unsigned int)spRequest->uiValue & 0xFFFFU)", ops_source)
        self.assertIn("((unsigned int)1U << 23U) | ((uiReg & 0x7FU) << 16U)", ops_source)

    def test_ltc2991_reads_convert_to_engineering_units(self) -> None:
        # 2991f data format: SE LSB 305.18 uV, T_internal 0.0625 C (13-bit
        # two's complement), VCC = 2.5 V + code * 305.18 uV. Reads must return
        # mV / santi-Celsius, not raw transfer images.
        spec = load_sample_spec("unit_ltc2991_units")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [{
            "id": "u1_ltc2991", "part": "LTC2991",
            "descriptor_ref": "descriptors/ltc2991.yaml",
            "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x48",
                       "via_mux": None, "reset_gpio": None, "irq_line": None},
            "operations_requested": ["device_init", "voltage_read", "temperature_read", "vcc_read"],
            "tests_requested": ["self_test"],
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            driver = (out_dir / "drivers" / "ltc2991.c").read_text(encoding="utf-8")
            header = (out_dir / "drivers" / "ltc2991.h").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_ltc2991_units_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        # Voltage: mV with sign strip + clamp (LSB 305.18 uV -> *30518/100000).
        self.assertIn("(iCode * 30518) / 100000", driver)
        self.assertIn("iCode -= 32768", driver)
        # Temperature: santi-Celsius, 13-bit two's complement, signed int out.
        self.assertIn("(iCode * 25) / 4", driver)
        self.assertIn("iCode -= 8192", driver)
        self.assertIn("int* ipTemperature", header)
        # VCC: +2500 mV offset.
        self.assertIn("iCode += 2500", driver)
        # Dispatch carries the signed scalar (int32 path).
        self.assertIn("int iValue;", ops)
        self.assertIn("ltc2991TemperatureRead(spIic, &iValue)", ops)
        ltc_ops = {op["name"]: op for op in manifest["devices"][0]["operations"]}
        self.assertEqual(ltc_ops["temperature_read"]["fixed_read_length"], 4)
        self.assertIn("mV", ltc_ops["voltage_read"]["label"])
        # UI'nin ondalık + birim çözebilmesi için sonuç metaverisi (0xF23 ->
        # 38.75 C gösterimi bu alanlardan beslenir).
        self.assertEqual(ltc_ops["temperature_read"]["result_returns"], "int32")
        self.assertEqual(ltc_ops["temperature_read"]["result_unit"], "0.01 C")
        self.assertEqual(ltc_ops["voltage_read"]["result_returns"], "voltages[8]")
        self.assertEqual(ltc_ops["voltage_read"]["result_unit"], "mV")
        self.assertEqual(ltc_ops["register_read"]["result_returns"], "uint8")
        # Seri Hat kablo planı: poll (STATUS_LOW) + 8 kanal MSB/LSB okuması.
        voltage_wire = ltc_ops["voltage_read"]["wire"]
        self.assertEqual(voltage_wire[0]["kind"], "reg_read")
        self.assertEqual(voltage_wire[0]["reg"], "STATUS_LOW")
        self.assertEqual(voltage_wire[0]["repeat"], "poll")
        self.assertEqual(voltage_wire[1]["kind"], "reg_read_channels")
        self.assertEqual(voltage_wire[1]["count"], 8)
        init_wire = ltc_ops["device_init"]["wire"]
        self.assertEqual([step["kind"] for step in init_wire],
                         ["reg_write", "reg_write", "reg_write", "reg_write", "reg_read"])
        self.assertEqual(init_wire[2]["value"], 0x10)  # repeated acquisition
        self.assertTrue(ltc_ops["register_read"]["wire"][0]["runtime"])

        # Saha regresyonu (2026-07-05, gerçek ZynqMP): repeated-acquisition
        # modunda BUSY hiç düşmediğinden "BUSY==0 bekle" poll'u 100000
        # deneme (~46 s) sonunda status=1 ile bitiyordu. Beklenen davranış:
        # ölçüme özgü READY biti beklenir ve poll bütçesi ~0.5 s tavandır.
        self.assertIn("LTC2991_POLL_TIMEOUT 1000U", header)
        self.assertIn("((ucPoll >> 1) & 0x1U) != 1U", driver)  # T_INTERNAL_READY == 1
        self.assertIn("(ucPoll & 0x1U) != 1U", driver)         # VCC_READY / V1_READY == 1
        self.assertNotIn("((ucPoll >> 2) & 0x1U) != 0U", driver)  # BUSY beklemesi kalktı
        # device_init, testbench'in başlattığı paylaşılan denetleyiciyi
        # yeniden CfgInitialize etmemeli (mt25qu02g'de XST_DEVICE_IS_STARTED
        # olarak görüldü; I2C'de canlı SCLK ayarını bozuyordu).
        self.assertIn("if (spIic->IsReady != XIL_COMPONENT_IS_READY)", driver)
        # Canlı bus izi: sürücünün en alt seviye okuma/yazması her gerçek
        # transferi raporlar (zayıf kanca; test bench güçlü impl TRACE satırı
        # yayınlar, Seri Hat gerçek baytlarla diyagram çizer).
        self.assertIn("spec2codeBusTraceI2c(LTC2991_I2C_ADDR, ucReg, 'r', ucpValue, 1U);", driver)
        self.assertIn("spec2codeBusTraceI2c(LTC2991_I2C_ADDR, ucReg, 'w', &ucValue, 1U);", driver)
        self.assertIn("spec2codeTestbenchTraceSetId(spRequest->uiId);", ops)

    def test_ltc2945_current_read_uses_board_shunt_config(self) -> None:
        # Akım = Vsense / Rsense; şönt kart verisidir. config.sense_resistor_mohms
        # verilince mA dönüşümü üretilmeli, açıkça istenip config yoksa
        # anlaşılır hata, varsayılan listede config yoksa sessizce düşmeli.
        def build_spec(config: dict | None, requested: list[str] | None) -> dict:
            spec = load_sample_spec("unit_ltc2945_current")
            spec["controllers"] = [
                {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
                 "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
                 "source": "xparameters", "zone": "ps"},
            ]
            spec["muxes"] = []
            device = {
                "id": "u1_ltc2945", "part": "LTC2945",
                "descriptor_ref": "descriptors/ltc2945.yaml",
                "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x67",
                           "via_mux": None, "reset_gpio": None, "irq_line": None},
                "tests_requested": ["self_test"],
            }
            if config is not None:
                device["config"] = config
            if requested is not None:
                device["operations_requested"] = requested
            spec["devices"] = [device]
            return spec

        with tempfile.TemporaryDirectory() as tmp:
            spec = build_spec({"sense_resistor_mohms": 5}, ["device_init", "current_read"])
            out_dir = Path(tmp) / "with_shunt"
            written = {Path(path).relative_to(out_dir).as_posix() for path in codegen.generate(spec, out_dir)}
            driver = (out_dir / "drivers" / "ltc2945.c").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_ltc2945_current_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        # I_mA = kod * 25 uV / R_mohm (5 mohm sönt).
        self.assertIn("(iCode * 25) / 5", driver)
        # Trace altyapısı dosyaları üretilir (zayıf kanca + güçlü impl).
        self.assertIn("drivers/spec2code_bus_trace.h", written)
        self.assertIn("tests/spec2code_testbench_trace.c", written)
        ltc_ops = {op["name"]: op for op in manifest["devices"][0]["operations"]}
        self.assertIn("current_read", ltc_ops)
        self.assertIn("mA", ltc_ops["current_read"]["label"])
        # device_init doğrulaması: CONTROL geri okunur, data 1 bayt taşır.
        self.assertIn("spec2codeTestbenchI2cRegisterRead(spIic, LTC2945_I2C_ADDR, LTC2945_REG_CONTROL, &ucValue)", ops)
        self.assertEqual(ltc_ops["device_init"]["fixed_read_length"], 1)

        # Config yokken varsayılan (tümü) listesinden sessizce düşer.
        with tempfile.TemporaryDirectory() as tmp:
            spec = build_spec(None, None)
            out_dir = Path(tmp) / "no_shunt_default"
            codegen.generate(spec, out_dir)
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        default_ops = {op["name"] for op in manifest["devices"][0]["operations"]}
        self.assertNotIn("current_read", default_ops)
        self.assertIn("sense_read", default_ops)

        # Config yokken açık istek anlaşılır hata vermeli.
        with tempfile.TemporaryDirectory() as tmp:
            spec = build_spec(None, ["current_read"])
            out_dir = Path(tmp) / "no_shunt_explicit"
            with self.assertRaises(Exception) as ctx:
                codegen.generate(spec, out_dir)
        self.assertIn("sense_resistor_mohms", str(ctx.exception))

    def test_spi_device_init_returns_post_init_status_readback(self) -> None:
        # device_init yanıtının data alanı boş kalmamalı: SPI parçalarında
        # descriptor'daki post_init_status registeri geri okunur.
        spec = load_sample_spec("unit_spi_post_init")
        spec["controllers"] = [
            {"id": "ps_spi_0", "type": "spi", "instance": "XPAR_XSPIPS_0",
             "base_address": "0xFF040000", "device_id": 0, "driver": "XSpiPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [{
            "id": "u1_lmk04832", "part": "LMK04832",
            "descriptor_ref": "descriptors/lmk04832.yaml",
            "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 0,
                       "reset_gpio": None, "irq_line": None},
            "operations_requested": ["device_init"],
            "tests_requested": ["self_test"],
            "config": {"ticspro_registers": ["0x000010"]},
        }]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            ops = (out_dir / "tests" / "unit_spi_post_init_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("LMK04832_REG_RB_PLL_STATUS", ops)
        self.assertIn("spec2codeTestbenchSpiRegisterRead(spSpi, LMK04832_SPI_SELECT", ops)
        device_ops = {op["name"]: op for op in manifest["devices"][0]["operations"]}
        self.assertEqual(device_ops["device_init"]["fixed_read_length"], 1)
        self.assertIn("RB_PLL_STATUS", device_ops["device_init"]["description"])

    def test_i2c_scan_ops_and_manifest_topology(self) -> None:
        # Hat taraması: ajan global i2c_scan (0x08..0x77 yoklama) ve
        # i2c_mux_set (switch kontrol baytı) oplarını sunar; manifest UI'ye
        # taranabilir denetleyicileri ve mux topolojisini bildirir.
        # SAHA BULGUSU (2026-07-05): prob YAZMA olmalı — recv-polled prob
        # gerçek kartta NACK'te de XST_SUCCESS döndürüp her adresi "dolu"
        # gösterdi. Kanal taramasında aktif switch adresi atlanır (0x00
        # yazılsaydı seçili kanal kapanırdı).
        spec = load_sample_spec("unit_i2c_scan")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            ops = (out_dir / "tests" / "unit_i2c_scan_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "i2c_scan")', ops)
        self.assertIn("for (uiScanAddr = 0x08U; uiScanAddr <= 0x77U; uiScanAddr++)", ops)
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "i2c_mux_set")', ops)
        # Prob 0x00 yazmasıdır; okuma probu üretimden kalkmıştır.
        scan_block = ops.split('"i2c_scan"')[1].split('"i2c_mux_set"')[0]
        self.assertIn("XIicPs_MasterSendPolled(spScanIic, &ucProbe, 1, (unsigned short)uiScanAddr)", scan_block)
        self.assertNotIn("XIicPs_MasterRecvPolled", scan_block)
        self.assertIn("if (uiScanAddr == spRequest->uiAddress)", scan_block)
        scan = manifest["i2c_scan"]
        self.assertEqual(scan["range"], [8, 119])
        self.assertIn("write", scan["probe"])
        self.assertTrue(scan["skip_address_param"])
        controller_ids = {c["id"] for c in scan["controllers"]}
        self.assertIn("ps_i2c_0", controller_ids)
        self.assertTrue(all("address" in m and "channels" in m for m in scan["muxes"]))

    def test_i2c_scan_orchestration_builds_channel_map(self) -> None:
        # Orkestrasyon: switch'ler kapatılır -> doğrudan tarama -> her kanal
        # sırayla seçilip taranır -> switch kapatılır. Kanal içeriği, doğrudan
        # hatta görünen adreslerden ve switch'in kendisinden arındırılır.
        from backend import i2c_scan as scan_mod

        mux = {"id": "u1_tca9548a", "part": "TCA9548A", "address": 0x70, "channels": 2}
        calls: list[tuple[str, int | None, int | None]] = []
        state = {"mask": 0}

        def fake_send(session_id, command):
            calls.append((command.operation, command.address, command.value))
            if command.operation == "spec2code_version":
                line = f"S2C|id={command.command_id}|ok=1|status=0|value=0x0|data=|message=Spec2Code v0.1.106"
            elif command.operation == "i2c_mux_set":
                state["mask"] = int(command.value or 0)
                line = f"S2C|id={command.command_id}|ok=1|status=0|value=0x{state['mask']:X}|data=|message=ok"
            else:
                found = [0x70, 0x4A]
                if state["mask"] & 0x01:
                    found.append(0x48)
                if state["mask"] & 0x02:
                    found.extend([0x40, 0x4A])  # 0x4A dogrudan hatta da var (golge)
                data = "".join(f"{a:02X}" for a in sorted(set(found)))
                line = f"S2C|id={command.command_id}|ok=1|status=0|value=0x{len(found):X}|data={data}|message=ok"
            return type("R", (), {"parsed": parse_response(line)})()

        original = scan_mod.testbench_sessions.send
        scan_mod.testbench_sessions.send = fake_send  # type: ignore[assignment]
        try:
            result = scan_mod.scan_bus("s1", "ps_i2c_0", [mux], timeout_s=1.0)
        finally:
            scan_mod.testbench_sessions.send = original  # type: ignore[assignment]

        self.assertEqual(result["direct_addresses"], [0x4A])
        self.assertEqual(result["switch_addresses"], [0x70])
        # Ajan surumu taramadan once sorgulanir ve sonuca islenir: eski
        # ELF'in okuma probu sessizce hepsi-ACK haritasi uretebildiginden
        # UI surumu gorup uyarabilmelidir.
        self.assertEqual(result["agent_version"], "v0.1.106")
        self.assertTrue(result["probe_is_write"])
        self.assertFalse(result["suspect_all_ack"])
        channels = result["muxes"][0]["channels"]
        self.assertEqual(channels[0], {"channel": 0, "addresses": [0x48]})
        # 0x4A dogrudan hatta oldugundan kanal iceriginden arindirilir.
        self.assertEqual(channels[1], {"channel": 1, "addresses": [0x40]})
        # Sira: surum sorgusu, once kapat, dogrudan tara, ch0 sec/tara,
        # ch1 sec/tara, kapat.
        ops_order = [op for op, _, _ in calls]
        self.assertEqual(ops_order, ["spec2code_version",
                                     "i2c_mux_set", "i2c_scan", "i2c_mux_set", "i2c_scan",
                                     "i2c_mux_set", "i2c_scan", "i2c_mux_set"])
        self.assertEqual(calls[1][2], 0x00)
        self.assertEqual(calls[3][2], 0x01)
        self.assertEqual(calls[5][2], 0x02)
        self.assertEqual(calls[7][2], 0x00)
        # Kanal taramalarinda aktif switch adresi ajana atlatilir (yazma
        # probu 0x00'i switch'e yazsaydi secili kanal kapanirdi); dogrudan
        # taramada atlama yoktur.
        self.assertIsNone(calls[2][1])
        self.assertEqual(calls[4][1], 0x70)
        self.assertEqual(calls[6][1], 0x70)

    def test_i2c_scan_flags_stale_agent_and_implausible_all_ack_map(self) -> None:
        # SAHA BULGUSU (2026-07-05): eski ELF (okuma probu) 0x08-0x77'nin
        # TAMAMINI "cevap veriyor" gosterdi; kullanici "build edildi"
        # sanip eski ELF ile bosuna ugrasti. Beklenen: tarama ajan
        # surumunu sorgular, v0.1.105 oncesini isaretler ve hepsi-ACK
        # haritasini fiziksel olarak supheli olarak dondurur.
        from backend import i2c_scan as scan_mod

        def fake_send(session_id, command):
            if command.operation == "spec2code_version":
                line = f"S2C|id={command.command_id}|ok=1|status=0|value=0x0|data=|message=Spec2Code v0.1.104"
            else:
                data = "".join(f"{a:02X}" for a in range(0x08, 0x78))
                line = f"S2C|id={command.command_id}|ok=1|status=0|value=0x70|data={data}|message=i2c_scan ok"
            return type("R", (), {"parsed": parse_response(line)})()

        original = scan_mod.testbench_sessions.send
        scan_mod.testbench_sessions.send = fake_send  # type: ignore[assignment]
        try:
            result = scan_mod.scan_bus("s1", "ps_i2c_0", [], timeout_s=1.0)
        finally:
            scan_mod.testbench_sessions.send = original  # type: ignore[assignment]

        self.assertEqual(result["agent_version"], "v0.1.104")
        self.assertFalse(result["probe_is_write"])
        self.assertTrue(result["suspect_all_ack"])
        self.assertEqual(len(result["direct_addresses"]), 112)

    def test_multiple_devices_of_same_part_get_isolated_modules(self) -> None:
        # SAHA BULGUSU (2026-07-05): aynı parçadan birden çok cihaz varken
        # modül adı parçadan türediği için her örnek AYNI ltc2991.c'yi ve
        # tek LTC2991_I2C_ADDR sabitini paylaşıyordu — kullanıcı hangi
        # cihazı seçerse seçsin hep aynı fiziksel çip okunuyordu. Beklenen:
        # her örnek kendi modülü/dosyası/adres sabitiyle üretilir.
        spec = load_sample_spec("unit_multi_ltc2991")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {"id": "u1_ltc2991", "part": "LTC2991",
             "descriptor_ref": "descriptors/ltc2991.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x48",
                        "via_mux": None, "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "temperature_read"],
             "tests_requested": ["self_test"]},
            {"id": "u2_ltc2991", "part": "LTC2991",
             "descriptor_ref": "descriptors/ltc2991.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x49",
                        "via_mux": None, "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "temperature_read"],
             "tests_requested": ["self_test"]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            written = {Path(path).relative_to(out_dir).as_posix() for path in codegen.generate(spec, out_dir)}
            first = (out_dir / "drivers" / "ltc2991.h").read_text(encoding="utf-8")
            second = (out_dir / "drivers" / "ltc2991b.h").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_multi_ltc2991_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("drivers/ltc2991.c", written)
        self.assertIn("drivers/ltc2991b.c", written)
        self.assertIn("#define LTC2991_I2C_ADDR 0x48U", first)
        self.assertIn("#define LTC2991B_I2C_ADDR 0x49U", second)
        # Dispatch her cihazı kendi modülüne bağlar.
        self.assertIn("ltc2991TemperatureRead(spIic, &iValue)", ops)
        self.assertIn("ltc2991bTemperatureRead(spIic, &iValue)", ops)
        self.assertIn("LTC2991B_I2C_ADDR", ops)  # ikinci cihazın register/post-init yolu
        parts = [device["id"] for device in manifest["devices"]]
        self.assertEqual(parts, ["u1_ltc2991", "u2_ltc2991"])

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

    def test_i2c_failures_name_their_stage_and_block_reads_use_single_byte_primitive(self) -> None:
        # SAHA BULGUSU (2026-07-05): DS1682 elapsed_read tek satir "failed"
        # ile dustu - iz yok, asama yok. Ayni kartta register snapshot
        # (tek-bayt okumalar) 21/21 basariliydi; fark TEK pointer + COK
        # BAYTLI blok recv idi. Beklenen: (1) read_registers ardisik
        # register adreslerini kanitli tek-bayt okumalarla toplar (sayac
        # tutarliligi icin iki gecis + uyusmazsa ucuncu), (2) her I2C
        # basarisizligi spec2codeBusTraceI2cError kancasiyla adres/register/
        # asama raporlar (testbench guclu impl. ERROR seviyesinde loglar),
        # (3) mux kanal secimi de ayni kancayi kullanir.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = [
            {"id": "u1_tca9548a", "part": "TCA9548A", "controller_id": "ps_i2c_0",
             "i2c_address": "0x70", "channels": 8},
        ]
        spec["devices"] = [
            {"id": "u8_ds1682", "part": "DS1682",
             "descriptor_ref": "descriptors/ds1682.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x6B",
                        "via_mux": {"mux_id": "u1_tca9548a", "channel": 5},
                        "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "elapsed_read", "event_read"],
             "tests_requested": ["self_test"]},
        ]
        add_zynqmp_ps_ethernet(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            ds1682 = (out_dir / "drivers" / "ds1682.c").read_text(encoding="utf-8")
            mux_source = (out_dir / "drivers" / "tca9548a.c").read_text(encoding="utf-8")
            trace_header = (out_dir / "drivers" / "spec2code_bus_trace.h").read_text(encoding="utf-8")
            trace_source = (out_dir / "tests" / "spec2code_testbench_trace.c").read_text(encoding="utf-8")

        # (1) Blok recv uretimden kalkti; ardisik adresler tek-bayt okunur.
        self.assertNotIn("XIicPs_MasterRecvPolled(spIic, ucpBuffer, (int)uiLength", ds1682)
        self.assertIn("ds1682RegisterRead(spIic, (unsigned char)(ucReg + uiIndex), &ucpBuffer[uiIndex]);", ds1682)
        # Iki gecis + uyusmazsa ucuncu (DS1682 ETC 0.25 s'de artar).
        self.assertEqual(ds1682.count("ds1682RegistersReadOnce(spIic, ucReg,"), 3)
        # (2) Basarisizlik asamasi raporlanir: pointer/recv/yazma.
        self.assertIn("spec2codeBusTraceI2cError(DS1682_I2C_ADDR, ucReg, 'p', iStatus);", ds1682)
        self.assertIn("spec2codeBusTraceI2cError(DS1682_I2C_ADDR, ucReg, 'r', iStatus);", ds1682)
        # ('w' asamasi register_write kullanan cihazlarda uretilir; bu op
        # kumesi salt okuma oldugundan yazma yardimcisi budanir.)
        # (3) Mux secimi de konusur; kanca zayif varsayilanla driver'da,
        # guclu ERROR-log implementasyonuyla testbench'te bulunur.
        self.assertIn("spec2codeBusTraceI2cError(TCA9548A_I2C_ADDR, ucChannel, 'm', iStatus);", mux_source)
        self.assertIn("void spec2codeBusTraceI2cError(unsigned char ucAddress, unsigned char ucReg,", trace_header)
        self.assertIn("TRACEERR|id=%u|bus=i2c|addr=0x%02X|reg=0x%02X|asama=%c|status=%d", trace_source)

    def test_uint32_returning_ops_are_wired_into_the_testbench_dispatcher(self) -> None:
        # SAHA KOK NEDENI (2026-07-06, karar fotografi 13:10): v0.1.113
        # ajaninda DS1682 elapsed_read "op basla" ile AYNI milisaniyede
        # status=1 dustu; seviye 5'te dahi tek I2C izi/TRACEERR yoktu. Sebep:
        # testbench op eslemesinde uint32 dali yoktu - returns "uint32" olan
        # TUM *_read op'lari (DS1682 elapsed/alarm/event, LTC2945 power)
        # surucuyu HIC cagirmadan "operation signature not mapped"
        # yakalayicisina dusuyordu; genel "<op> failed" mesaji da bu ipucunu
        # eziyordu. Beklenen: uint32 op surucu fonksiyonunu cagirir, ham deger
        # value + 4 big-endian bayt olarak doner.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = [
            {"id": "u1_tca9548a", "part": "TCA9548A", "controller_id": "ps_i2c_0",
             "i2c_address": "0x70", "channels": 8},
        ]
        spec["devices"] = [
            {"id": "u8_ds1682", "part": "DS1682",
             "descriptor_ref": "descriptors/ds1682.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x6B",
                        "via_mux": {"mux_id": "u1_tca9548a", "channel": 5},
                        "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "elapsed_read", "alarm_read", "event_read"],
             "tests_requested": ["self_test"]},
            {"id": "u7_ltc2945", "part": "LTC2945",
             "descriptor_ref": "descriptors/ltc2945.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x6F",
                        "via_mux": None, "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "power_read"],
             "tests_requested": ["self_test"]},
        ]
        add_zynqmp_ps_ethernet(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            ops_source = (out_dir / "tests" / f"{spec['project']['name']}_testbench_ops.c").read_text(encoding="utf-8")

        # uint32 op'lar artik gercek surucu cagrisina baglanir...
        self.assertIn("iStatus = ds1682ElapsedRead(", ops_source)
        self.assertIn("iStatus = ds1682AlarmRead(", ops_source)
        self.assertIn("iStatus = ds1682EventRead(", ops_source)
        self.assertIn("iStatus = ltc2945PowerRead(", ops_source)
        # ...ham deger value + 4 big-endian bayt olarak doner...
        self.assertIn("unsigned int uiValue32;", ops_source)
        self.assertIn("(unsigned char)((uiValue32 >> 24U) & 0xFFU)", ops_source)
        # ...ve hicbir op sessiz always-fail yakalayicisina dusmez.
        self.assertNotIn("operation signature not mapped", ops_source)

    def test_every_catalog_descriptor_read_op_maps_to_a_driver_call(self) -> None:
        # Yapisal koruma: katalogdaki (veya yeni eklenen) bir descriptor'in
        # returns tipi testbench eslemesinden duserse ajan o op icin bus'a hic
        # cikmadan fail eden kod uretir - bu test sinifi hatayi uretim aninda
        # yakalar. Kural: *_read op'lari "operation signature not mapped"
        # yakalayicisina dusmez.
        get_descriptor = codegen.make_descriptor_loader(codegen._ROOT)
        descriptor_dir = codegen._ROOT / "descriptors"
        for yaml_path in sorted(descriptor_dir.glob("*.yaml")):
            descriptor = get_descriptor(f"descriptors/{yaml_path.name}")
            entry = {"module": "swp", "hvar": "spHandle",
                     "descriptor": descriptor, "device": {"id": "sweep"}}
            for op in descriptor.get("operations", []):
                op_name = str(op.get("name", ""))
                if not op_name.endswith("_read"):
                    continue
                lines = codegen._testbench_call_lines(entry, op)
                self.assertFalse(
                    any("operation signature not mapped" in line for line in lines),
                    msg=f"{yaml_path.name}: {op_name} testbench'e baglanmamis "
                        f"(returns={op.get('returns')!r})",
                )

    def test_wide_registers_use_single_transaction_and_reach_manifest(self) -> None:
        # REGRESYON KORUMASI: read_registers iki farkli anlam tasir.
        # (a) DS1682/LTC2945: ardisik AYRI adresler -> tek-bayt okumalarla
        #     toplanir (blok recv sahada dusuyor).
        # (b) AD7414/TMP101 TEMPERATURE: TEK genis (16-bit) register ->
        #     baytlar ayni adresin ICINDE; pointer + 2 bayt TEK islemde
        #     (sahada kanitli). Tek-bayt yontemi burada YANLIS olurdu:
        #     ikinci bayt 0x01'deki CONFIGURATION'dan gelirdi.
        # Ayrica manifest artik 16-bit registerlari da listeler (Registers
        # ekraninda AD7414'un 0. registeri gorunur) ve generic R/W ajan
        # tarafinda genislik-farkindalidir.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_i2c_0", "type": "i2c", "instance": "XPAR_XIICPS_0",
             "base_address": "0xFF020000", "device_id": 0, "driver": "XIicPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {"id": "u9_ad7414", "part": "AD7414",
             "descriptor_ref": "descriptors/ad7414.yaml",
             "attach": {"controller_id": "ps_i2c_0", "i2c_address": "0x4A",
                        "via_mux": None, "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init", "temperature_read", "config_read"],
             "tests_requested": ["self_test"]},
        ]
        add_zynqmp_ps_ethernet(spec)

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            driver = (out_dir / "drivers" / "ad7414.c").read_text(encoding="utf-8")
            ops = (out_dir / "tests" / "unit_no_spi_testbench_testbench_ops.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        # Manifest register listesi TUM entegrelerde offset'e gore artan
        # siralidir (SAHA istegi: katalog birlestirmesi sona eklendigi icin
        # LMK04832'de liste karisik gorunuyordu).
        for device in manifest["devices"]:
            offsets = [int(r["offset"]) for r in device["registers"]]
            self.assertEqual(offsets, sorted(offsets), device["part"])
        # (b) genis register: tek islemde 2 bayt; ardisik-adres yolu YOK.
        self.assertIn("ad7414RegisterReadWide(spIic, AD7414_REG_TEMPERATURE, &ucArrBytes[0U], 2U);", driver)
        self.assertNotIn("ad7414RegistersRead(spIic, AD7414_REG_TEMPERATURE", driver)
        # Manifest 16-bit registeri genisligiyle listeler.
        ad7414 = next(d for d in manifest["devices"] if d["part"] == "AD7414")
        temp = next(r for r in ad7414["registers"] if r["name"] == "TEMPERATURE")
        self.assertEqual(temp["width"], 16)
        self.assertEqual(temp["offset"], 0)
        # Generic R/W genislik-farkindali: cozucu + tek-islem yardimcilar.
        self.assertIn("ad7414TestbenchRegisterWidthBytes", ops)
        self.assertIn("spec2codeTestbenchI2cRegisterReadWide(", ops)
        self.assertIn("spec2codeTestbenchI2cRegisterWriteWide(", ops)

    def test_lmk04832_manifest_registers_are_offset_sorted(self) -> None:
        # SAHA istegi: LMK04832 descriptor'inda katalog birlestirmesi yeni
        # registerlari dosyanin SONUNA ekledi (RESET, PLL2_N_CAL_0..
        # RB_PLL_STATUS ondeydi); Registers ekrani dosya sirasini gosterip
        # karisik gorunuyordu. Manifest artik offset'e gore artan siralar.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_spi_0", "type": "spi", "instance": "XPAR_XSPIPS_0",
             "base_address": "0xFF040000", "device_id": 0, "driver": "XSpiPs",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {"id": "u6_lmk04832", "part": "LMK04832",
             "descriptor_ref": "descriptors/lmk04832.yaml",
             "attach": {"controller_id": "ps_spi_0", "spi_chip_select": 0,
                        "reset_gpio": None, "irq_line": None},
             "operations_requested": ["device_init"],
             "tests_requested": ["self_test"],
             "config": {"ticspro_registers": ["0x000010"]}},
        ]
        add_zynqmp_ps_ethernet(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            manifest = json.loads(
                (out_dir / "tests" / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))
        lmk = next(d for d in manifest["devices"] if d["part"] == "LMK04832")
        offsets = [int(r["offset"]) for r in lmk["registers"]]
        self.assertEqual(offsets, sorted(offsets))
        self.assertGreater(len(offsets), 100)  # tam harita (125) tasiniyor
        # Dosyada sona eklenmis 0x002, siralamada RESET(0x000)'in hemen
        # arkasina gelir; PLL2_N_CAL_0 (0x163) artik basta degildir.
        self.assertEqual(offsets[0], 0x000)
        self.assertEqual(offsets[1], 0x002)

    def test_agent_line_buffer_fits_full_data_payload_and_guards_overflow(self) -> None:
        # SAHA BULGUSU (2026-07-05): 256 baytlik flash okumasi timeout'a
        # dustu. Cevap satiri ~750 karakterdir (prefix ~64 + 512 hex data +
        # message 160) ama LINE_MAX 512 idi: ResponseFormat kirpip FAILURE
        # dondu, UART/CoreSight ajani kirpik satiri \n'siz gonderdi -> host
        # satiri tamamlayamayip timeout; kirpik govde bir SONRAKI cevapla
        # yapisti (id=47+id=48 tek satir olarak gorunduler). Beklenen:
        # 1024'luk tampon (istek tarafi da 256B page_program payload'i
        # icin gerekli) + tasma bekcisi (kirpik satir yerine data'siz
        # "response line overflow" cevabi).
        spec = load_sample_spec("unit_no_spi_testbench")
        add_zynqmp_ps_ethernet(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            agent_sources = "\n".join(
                p.read_text(encoding="utf-8")
                for p in tests_dir.glob("spec2code_testbench_*.c"))
            ops_source = (tests_dir / "unit_no_spi_testbench_testbench_ops.c").read_text(encoding="utf-8")

        self.assertIn("#define SPEC2CODE_TESTBENCH_LINE_MAX 1024U", agent_sources)
        self.assertNotIn("SPEC2CODE_TESTBENCH_LINE_MAX 512U", agent_sources)
        self.assertIn('spec2codeTestbenchMessageSet(&sResponse, "response line overflow");', ops_source)

    def test_qspi_flash_command_read_splits_tx_and_rx_messages(self) -> None:
        # SAHA BULGUSU (2026-07-05): mt25qu02g data_read (address=0x0
        # length=4) ajani KILITLEDI - "op basla" son log, TRACE/cevap yok,
        # sonraki tum komutlar cevapsiz. Kok neden: command_read TEK mesajda
        # TX|RX kombine gonderiyordu. Toplam 1+4+4=9 bayt >= 8 oldugundan
        # transfer DMA okuma yoluna girer ve XQspiPsu_SetupRxDma 4'e
        # bolunmeyen uzunlukta Msg->ByteCount'u kirpar (9->8, resmi surucu
        # xqspipsu_hw.c) - ayni ByteCount'u TX kurulumu 9 olarak kullandi;
        # tek ortak alan iki yonu birden temsil edemez ve polled dongu
        # sonsuz bekler. id_read'in calismasi toplam 4 baytin surucu
        # tarafindan IO moduna dusurulmesindendir (<8 bayt kurali).
        # Beklenen: resmi ornek akisi - cmd+addr TX-only mesaj + veri
        # RX-only mesaj (CS iki giris boyunca asserted), RX tamponu DMA
        # cache-invalidate icin 64B hizali.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {
                "id": "ps_qspi_0", "type": "qspi", "instance": "XPAR_XQSPIPSU_0",
                "base_address": "0xFF0F0000", "device_id": 0, "driver": "XQspiPsu",
                "source": "xparameters", "zone": "ps",
            },
        ]
        spec["muxes"] = []
        spec["devices"] = [
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
            driver = (out_dir / "drivers" / "mt25qu02g.c").read_text(encoding="utf-8")

        self.assertIn("sArrMessage[0].ByteCount = uiHeader;", driver)
        self.assertIn("sArrMessage[0].Flags = XQSPIPSU_MSG_FLAG_TX;", driver)
        self.assertIn("sArrMessage[1].ByteCount = uiLength;", driver)
        self.assertIn("sArrMessage[1].Flags = XQSPIPSU_MSG_FLAG_RX;", driver)
        self.assertIn("sArrMessage, 2U);", driver)
        self.assertIn("__attribute__((aligned(64)))", driver)
        # Kilitlenen kombine desen bu birimde bir daha uretilmemeli.
        self.assertNotIn("XQSPIPSU_MSG_FLAG_TX | XQSPIPSU_MSG_FLAG_RX", driver)

    def test_qspi_flash_stripes_data_phase_in_parallel_mode_only(self) -> None:
        # SAHA BULGUSU (2026-07-08): MT25QU02G dual-parallel'de beklenen
        # formatta okunamadi. Kok neden: veri fazinda XQSPIPSU_MSG_FLAG_STRIPE
        # yoktu. Resmi qspipsu flash ornegi (v1_16) ile dogrulandi: STRIPE
        # YALNIZ veri fazina (data read RX / page program TX payload) ve
        # YALNIZ ConnectionMode PARALLEL iken eklenir; komut/adres/dummy'ye ve
        # ID okumaya EKLENMEZ. Single flash'ta kosul false, davranis degismez.
        spec = load_sample_spec("unit_no_spi_testbench")
        spec["controllers"] = [
            {"id": "ps_qspi_0", "type": "qspi", "instance": "XPAR_XQSPIPSU_0",
             "base_address": "0xFF0F0000", "device_id": 0, "driver": "XQspiPsu",
             "source": "xparameters", "zone": "ps"},
        ]
        spec["muxes"] = []
        spec["devices"] = [
            {"id": "u2_mt25qu02g", "part": "MT25QU02G",
             "descriptor_ref": "descriptors/mt25qu02g.yaml",
             "attach": {"controller_id": "ps_qspi_0", "spi_chip_select": 0,
                        "address_width": 32, "reset_gpio": None},
             "operations_requested": ["device_init", "id_read", "data_read", "page_program"],
             "tests_requested": ["self_test"]},
        ]
        add_zynqmp_ps_ethernet(spec)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            driver = (out_dir / "drivers" / "mt25qu02g.c").read_text(encoding="utf-8")

        # Runtime PARALLEL kosulu (single flash'i etkilemez) + stripe |= .
        self.assertIn("Config.ConnectionMode == XQSPIPSU_CONNECTION_MODE_PARALLEL", driver)
        self.assertIn("|= XQSPIPSU_MSG_FLAG_STRIPE;", driver)
        # command_read: stripe RX veri mesajina; command_write: veri ayri
        # mesaj + uiMsgCount ile kosullu (verisiz cagride tek mesaj).
        self.assertEqual(driver.count("|= XQSPIPSU_MSG_FLAG_STRIPE;"), 2)
        self.assertIn("uiMsgCount", driver)
        self.assertIn("if (uiLength > 0U)", driver)
        # ID okuma (command_send) stripe kullanmaz: tek TX opcode.
        idx = driver.find("CommandSend")
        # Stripe yalniz iki veri fazinda; ID/komut fazinda gecmez (sayi 2).

    @unittest.skipUnless(shutil.which("gcc") or shutil.which("cc"), "host C compiler required")
    def test_generated_request_parser_round_trips_on_host_compiler(self) -> None:
        # Regresyon (sahada bulundu): satir kopyalama TextCopy ile yapilinca
        # ilk '|' karakterinde kesiliyor, tampon "S2C"ye dusuyor ve HER istek
        # "request parse failed" (id=0) donuyordu. Uretilen parser'i gercek
        # bir derleyiciyle derleyip ayni istegi uctan uca cozuyoruz.
        compiler = shutil.which("gcc") or shutil.which("cc")
        spec = load_sample_spec("unit_parse_roundtrip")
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            work = Path(tmp) / "host"
            work.mkdir()
            for name in ("spec2code_testbench_protocol.c", "spec2code_testbench_protocol.h",
                         "spec2code_testbench_log.c", "spec2code_testbench_log.h"):
                shutil.copy2(tests_dir / name, work / name)
            (work / "xstatus.h").write_text(
                "#ifndef XSTATUS_H\n#define XSTATUS_H\n"
                "#define XST_SUCCESS 0\n#define XST_FAILURE 1\n#endif\n",
                encoding="utf-8")
            (work / "xil_printf.h").write_text(
                "#ifndef XIL_PRINTF_H\n#define XIL_PRINTF_H\n"
                "#include <stdio.h>\n#define xil_printf printf\n#endif\n",
                encoding="utf-8")
            (work / "main.c").write_text(
                '#include <stdio.h>\n'
                '#include <string.h>\n'
                '#include "spec2code_testbench_protocol.h"\n'
                '#include "spec2code_testbench_log.h"\n'
                'static char S_cArrLastLog[256];\n'
                'static void logSink(const char* cpLine)\n'
                '{\n'
                '    snprintf(S_cArrLastLog, sizeof(S_cArrLastLog), "%s", cpLine);\n'
                '}\n'
                'static void try_line(const char* cpLine)\n'
                '{\n'
                '    SSpec2codeTestbenchRequest sRequest;\n'
                '    int iStatus = spec2codeTestbenchRequestParse(cpLine, &sRequest);\n'
                '    printf("status=%d id=%u device=[%s] op=[%s] hasval=%u val=%u\\n",\n'
                '           iStatus, sRequest.uiId, sRequest.cArrDevice, sRequest.cArrOperation,\n'
                '           sRequest.uiHasValue, sRequest.uiValue);\n'
                '}\n'
                'int main(void)\n'
                '{\n'
                '    try_line("S2C|id=2|device=spec2code|op=spec2code_version");\n'
                '    try_line("S2C|id=7|device=u12_ltc2991|op=register_read|reg=STATUS|reg_addr=0x1");\n'
                '    try_line("S2C|id=3|device=spec2code|op=log_level|value=4");\n'
                '    try_line("S2C|");\n'
                '    spec2codeLogSinkSet(logSink);\n'
                '    S_cArrLastLog[0] = 0;\n'
                '    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, "gizli");\n'
                '    printf("debug_at_default=[%s]\\n", S_cArrLastLog);\n'
                '    spec2codeLog(SPEC2CODE_LOG_LEVEL_ERROR, "hata kodu=%d", -7);\n'
                '    printf("error_at_default=[%s]", S_cArrLastLog);\n'
                '    printf("set_debug=%u\\n", spec2codeLogLevelSet(SPEC2CODE_LOG_LEVEL_DEBUG));\n'
                '    S_cArrLastLog[0] = 0;\n'
                '    spec2codeLog(SPEC2CODE_LOG_LEVEL_DEBUG, "artik acik");\n'
                '    printf("debug_at_debug=[%s]", S_cArrLastLog);\n'
                '    return 0;\n'
                '}\n',
                encoding="utf-8")
            binary = work / "parse_roundtrip"
            compile_run = subprocess.run(
                [compiler, "-Wall", "-Wextra", "-I", str(work), "-o", str(binary),
                 str(work / "main.c"), str(work / "spec2code_testbench_protocol.c"),
                 str(work / "spec2code_testbench_log.c")],
                capture_output=True, text=True)
            self.assertEqual(compile_run.returncode, 0, compile_run.stderr)
            output = subprocess.run([str(binary)], capture_output=True, text=True).stdout
        lines = output.strip().splitlines()
        self.assertEqual(lines[0], "status=0 id=2 device=[spec2code] op=[spec2code_version] hasval=0 val=0")
        self.assertEqual(lines[1], "status=0 id=7 device=[u12_ltc2991] op=[register_read] hasval=0 val=0")
        self.assertEqual(lines[2], "status=0 id=3 device=[spec2code] op=[log_level] hasval=1 val=4")
        self.assertTrue(lines[3].startswith("status=1"))
        # Log cekirdegi: varsayilan warning'de debug bastirilir, error basilir;
        # seviye debug'a cekilince debug da akar. Satir onek formati sabittir.
        self.assertEqual(lines[4], "debug_at_default=[]")
        self.assertEqual(lines[5], "error_at_default=[S2C-LOG|E|hata kodu=-7")
        self.assertEqual(lines[6], "]set_debug=5")
        self.assertEqual(lines[7], "debug_at_debug=[S2C-LOG|D|artik acik")

    def test_leveled_logging_is_generated_across_the_architecture(self) -> None:
        # Log cekirdegi her transport'ta uretilir; dispatch RX/TX (message),
        # op sonucu (info/error), i2c helper'lari (debug/error) enstrumante;
        # agent donguleri sink'i kendi hattina baglar; log_level op'u calisma
        # zamaninda esik degistirir; manifest seviye haritasini tasir.
        spec = load_sample_spec("unit_logging")
        spec["project"]["testbench_transport"] = "coresight"
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / spec["project"]["name"]
            codegen.generate(spec, out_dir)
            tests_dir = out_dir / "tests"
            log_header = (tests_dir / "spec2code_testbench_log.h").read_text(encoding="utf-8")
            log_source = (tests_dir / "spec2code_testbench_log.c").read_text(encoding="utf-8")
            ops_source = (tests_dir / "unit_logging_testbench_ops.c").read_text(encoding="utf-8")
            cs_source = (tests_dir / "spec2code_testbench_coresight.c").read_text(encoding="utf-8")
            manifest = json.loads(
                (tests_dir / "spec2code_testbench_manifest.json").read_text(encoding="utf-8"))

        self.assertIn("#define SPEC2CODE_LOG_LEVEL_ERROR 1U", log_header)
        self.assertIn("#define SPEC2CODE_LOG_LEVEL_DEBUG 5U", log_header)
        self.assertIn("#define SPEC2CODE_LOG_LEVEL_DEFAULT SPEC2CODE_LOG_LEVEL_WARNING", log_header)
        # Esik kurali: printin seviyesi ayarlanandan buyukse bastirilir.
        self.assertIn("if ((uiLevel > S_uiLogLevel) || (cpFormat == NULL))", log_source)
        # Runtime seviye degisimi + gelen/giden mesaj loglari + op sonucu.
        self.assertIn('spec2codeTestbenchStringEqual(spRequest->cArrOperation, "log_level")', ops_source)
        self.assertIn("spRequest->uiHasValue == 1U", ops_source)
        self.assertIn('spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, "RX %s", cpRequestLine);', ops_source)
        self.assertIn('spec2codeLog(SPEC2CODE_LOG_LEVEL_MESSAGE, "TX %s", cpResponseLine);', ops_source)
        self.assertIn('"op HATA: device=%s op=%s status=%d mesaj=%s"', ops_source)
        self.assertIn('"i2c reg read: addr=0x%02X reg=0x%02X"', ops_source)
        # Agent dongusu loglari kendi kanalina baglar.
        self.assertIn("spec2codeLogSinkSet(spec2codeTestbenchCoresightSendLine);", cs_source)
        self.assertIn('spec2codeLog(SPEC2CODE_LOG_LEVEL_INFO, "board init tamam', cs_source)
        self.assertEqual(manifest["log"]["op"], "log_level")
        self.assertEqual(manifest["log"]["default"], 2)
        self.assertEqual(manifest["log"]["levels"]["debug"], 5)
        self.assertEqual(manifest["log"]["line_prefix"], "S2C-LOG|")

    def test_serial_send_matches_response_by_command_id(self) -> None:
        # Paylasimli kanalda (konsol UART'i, ikinci jtagterminal istemcisi)
        # baska bir istemcinin yaniti kuyruga dusebilir; send() yalnizca
        # istegin id'sine sahip yaniti kabul etmeli.
        class NoisyFakeSerial(FakeSerial):
            def write(self, data: bytes) -> int:
                with self._lock:
                    self.written.append(bytes(data))
                    if b"op=id_read" in data:
                        self.rx += b"S2C|id=99|ok=1|status=0|value=0xBAD|message=stale\r\n"
                        self.rx += b"S2C|id=7|ok=1|status=0|value=0x42|message=ok\r\n"
                return len(data)

        manager = SessionManager()
        manager.connect_serial(
            "ser_id", "COM5", 115200, 2.0, serial_factory=lambda _p, _b, _t: NoisyFakeSerial())
        result = manager.send("ser_id", BenchCommand(
            host="", port=0, device="u1_ltc2991", operation="id_read", command_id=7))
        self.assertEqual(result.parsed["id"], "7")
        self.assertEqual(result.parsed["value"], "0x42")
        manager.disconnect("ser_id")

    def test_serial_send_falls_back_to_mismatched_response_on_timeout(self) -> None:
        # Eski/parse-hatali agent yanitlari id=0 tasir; zaman asiminda bos
        # hata yerine eldeki son yanit gosterilir (mesaji kaybettirme).
        class ParseFailFakeSerial(FakeSerial):
            def write(self, data: bytes) -> int:
                with self._lock:
                    self.written.append(bytes(data))
                    if b"op=id_read" in data:
                        self.rx += b"S2C|id=0|ok=0|status=1|value=0x0|data=|message=request parse failed\r\n"
                return len(data)

        manager = SessionManager()
        manager.connect_serial(
            "ser_fb", "COM6", 115200, 0.4, serial_factory=lambda _p, _b, _t: ParseFailFakeSerial())
        result = manager.send("ser_fb", BenchCommand(
            host="", port=0, device="u1_ltc2991", operation="id_read", command_id=5))
        self.assertEqual(result.parsed["message"], "request parse failed")
        manager.disconnect("ser_fb")

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
        # SAHA BULGUSU (2026-07-05): surum yaniti data alanini bos birakiyordu;
        # surum ASCII baytlari olarak data'da da doner ve UI yesil rozette cozer.
        self.assertIn("const char* pcVersion = SPEC2CODE_TESTBENCH_AGENT_VERSION;", ops_source)
        self.assertIn("spec2codeTestbenchDataPush(spResponse, (unsigned char)pcVersion[uiVersionIndex]);", ops_source)
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
            # SAHA (2026-07-05): paketli uygulama ajani "dev" damgaladi.
            # BOM'lu yazilmis metadata fullmatch'i sessizce kaciriyordu;
            # utf-8-sig okumayla tolere edilir.
            version_file.write_bytes("﻿v9.8.6\r\n".encode("utf-8"))
            self.assertEqual(codegen._app_version(), "v9.8.6")
        finally:
            if backup.exists():
                backup.rename(source_version)
            version_file.unlink(missing_ok=True)
            for name, value in old_env.items():
                if value is not None:
                    os.environ[name] = value

    def test_app_version_falls_back_to_changelog_next_to_the_executable(self) -> None:
        # Frozen (PyInstaller) benzetimi: _ROOT gecici bos dizindir (_MEIPASS
        # gibi - icinde version.ts/changelog yoktur), cwd bos, ama release
        # bundle'inda changelog.md exe'nin YANINDA durur. Eski kod changelog
        # yedegini yalniz _ROOT'ta aradigindan paketli uygulamada bu yedek
        # olu koddu ve ajan "dev" damgalaniyordu.
        old_env = {name: os.environ.pop(name, None) for name in ("SPEC2CODE_VERSION", "VITE_SPEC2CODE_VERSION", "RELEASE_VERSION")}
        old_root = codegen._ROOT
        old_exe = sys.executable
        old_cwd = os.getcwd()
        # TemporaryDirectory yerine elle temizlik: Windows, cwd olarak
        # kullanilan dizini silemez - once chdir geri alinmali.
        tmp = tempfile.mkdtemp()
        try:
            frozen_root = Path(tmp) / "meipass"
            exe_dir = Path(tmp) / "bundle"
            empty_cwd = Path(tmp) / "cwd"
            for p in (frozen_root, exe_dir, empty_cwd):
                p.mkdir()
            (exe_dir / "changelog.md").write_text(
                "# Spec2Code Changelog\n\n## v7.7.7 - 2026-07-05\n\n- test\n", encoding="utf-8")
            exe_path = exe_dir / "Spec2Code.exe"
            exe_path.write_bytes(b"")
            codegen._ROOT = frozen_root
            sys.executable = str(exe_path)
            os.chdir(empty_cwd)
            self.assertEqual(codegen._app_version(), "v7.7.7")
        finally:
            codegen._ROOT = old_root
            sys.executable = old_exe
            os.chdir(old_cwd)
            shutil.rmtree(tmp, ignore_errors=True)
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
