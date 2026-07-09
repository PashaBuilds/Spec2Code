import struct
import threading
import time
import unittest

import backend.registers as registers_module
from backend import s2cmsg
from backend.registers import snapshot_registers
from backend.testbench import TestbenchSessionManager


def _pad4(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


def _response_frame(op_name: str, counter: int, *, deger: int = 0, metin: bytes = b"ok") -> bytes:
    body = (struct.pack("<IIiII", counter, 0, 0, deger, 0)
            + struct.pack("<I", len(metin)) + _pad4(metin))
    command_id = s2cmsg.message_id_for_op(op_name) | s2cmsg.RESPONSE_BIT
    return s2cmsg.pack_frame(command_id, counter, body)


class RegisterResponderSerial:
    """Fake serial answering register_read with value = reg_addr + 1."""

    def __init__(self) -> None:
        self.rx = bytearray()
        self.requests: list[bytes] = []
        self._lock = threading.Lock()
        self._closed = False
        self._parser = s2cmsg.FrameParser()

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
            self.requests.append(bytes(data))
            for command_id, counter, body in self._parser.feed(data):
                entry = s2cmsg.load_catalog()["by_id"][command_id & ~s2cmsg.RESPONSE_BIT]
                register_address = struct.unpack_from("<I", body, 4)[0]
                value = (register_address + 1) & 0xFFFFFFFF
                self.rx += _response_frame(entry["op"], counter, deger=value)
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
        self.assertEqual(values["STATUS_LOW"], "0x1")
        self.assertEqual(values["CONTROL_V1V4"], "0x7")
        self.assertEqual(values["PWM_T_INTERNAL_CONTROL"], "0x9")
        register_read_id = s2cmsg.message_id_for_op("register_read")
        for request in fake.requests:
            command_id = struct.unpack_from("<I", request, 0)[0]
            self.assertEqual(command_id, register_read_id)

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
