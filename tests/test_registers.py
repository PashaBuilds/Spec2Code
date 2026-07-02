import re
import threading
import time
import unittest

import backend.registers as registers_module
from backend.registers import snapshot_registers
from backend.testbench import TestbenchSessionManager


class RegisterResponderSerial:
    """Fake serial answering register_read with value = reg_addr + 1."""

    def __init__(self) -> None:
        self.rx = bytearray()
        self.requests: list[str] = []
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
        text = data.decode("ascii", errors="replace")
        with self._lock:
            self.requests.append(text.strip())
            request_id = (re.search(r"id=(\d+)", text) or [None, "0"])[1]
            addr_match = re.search(r"reg_addr=0x([0-9A-Fa-f]+)", text)
            value = (int(addr_match.group(1), 16) + 1) if addr_match else 0
            self.rx += f"S2C|id={request_id}|ok=1|status=0|value=0x{value:02X}|message=ok\r\n".encode("ascii")
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        with self._lock:
            self._closed = True


class RegisterSnapshotTests(unittest.TestCase):
    def test_snapshot_reads_each_register_and_reports_values(self) -> None:
        sessions = TestbenchSessionManager()
        fake = RegisterResponderSerial()
        sessions.connect_serial("regs1", "COM9", 115200, 2.0, serial_factory=lambda _p, _b, _t: fake)
        original = registers_module.testbench_sessions
        registers_module.testbench_sessions = sessions
        try:
            snapshot = snapshot_registers("regs1", "u1_ltc2991", [
                {"name": "STATUS_LOW", "offset": 0x00},
                {"name": "CONTROL_V1V4", "offset": 0x06},
                {"name": "PWM_T_INTERNAL_CONTROL", "offset": 0x08},
            ], timeout_s=2.0)
        finally:
            registers_module.testbench_sessions = original
            sessions.disconnect("regs1")

        self.assertEqual(snapshot["total"], 3)
        self.assertEqual(snapshot["read_ok"], 3)
        values = {item["name"]: item["value"] for item in snapshot["registers"]}
        self.assertEqual(values["STATUS_LOW"], "0x01")
        self.assertEqual(values["CONTROL_V1V4"], "0x07")
        self.assertEqual(values["PWM_T_INTERNAL_CONTROL"], "0x09")
        self.assertTrue(all("op=register_read" in request for request in fake.requests))

    def test_snapshot_marks_remaining_registers_when_session_is_dead(self) -> None:
        sessions = TestbenchSessionManager()
        original = registers_module.testbench_sessions
        registers_module.testbench_sessions = sessions
        try:
            snapshot = snapshot_registers("missing", "u1_ltc2991", [
                {"name": "A", "offset": 0}, {"name": "B", "offset": 1},
            ], timeout_s=0.5)
        finally:
            registers_module.testbench_sessions = original
        self.assertEqual(snapshot["read_ok"], 0)
        self.assertEqual(len(snapshot["registers"]), 2)
        self.assertTrue(snapshot["registers"][1]["error"].startswith("atlandı"))


if __name__ == "__main__":
    unittest.main()
