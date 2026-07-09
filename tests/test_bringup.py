import struct
import threading
import time
import unittest

from backend import s2cmsg
from backend.bringup import (
    BringupConfig,
    BringupJob,
    BringupJobManager,
    build_plan,
    render_certificate_html,
)
from backend.testbench import TestbenchSessionManager


def _pad4(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


def _ok_response_frame(op_name: str, counter: int, *, deger: int = 0x2991, metin: bytes = b"ok") -> bytes:
    body = (struct.pack("<IIiII", counter, 0, 0, deger, 0)
            + struct.pack("<I", len(metin)) + _pad4(metin))
    command_id = s2cmsg.message_id_for_op(op_name) | s2cmsg.RESPONSE_BIT
    return s2cmsg.pack_frame(command_id, counter, body)


def sample_manifest() -> dict:
    op = {
        "risk": "safe", "implemented": True, "fixed_read_length": None,
        "requires_address": False, "requires_length": False,
        "requires_data": False, "requires_register": False, "requires_value": False,
    }
    return {
        "schema_version": "1.0",
        "project": "bringup_unit",
        "agent_version": "v0.0.0",
        "transport_agent": "uart",
        "devices": [
            {
                "id": "u3_mt25qu02g", "part": "MT25QU02G", "transport": "qspi",
                "operations": [
                    {**op, "name": "data_read", "label": "Data read", "requires_address": True},
                    {**op, "name": "id_read", "label": "JEDEC ID oku"},
                    {**op, "name": "device_init", "label": "Init", "risk": "risky"},
                ],
            },
            {
                "id": "u1_ltc2991", "part": "LTC2991", "transport": "i2c",
                "operations": [
                    {**op, "name": "voltage_read", "label": "Voltaj oku"},
                    {**op, "name": "device_init", "label": "Init", "risk": "risky"},
                ],
            },
            {
                "id": "u2_lmk04832", "part": "LMK04832", "transport": "spi",
                "operations": [{**op, "name": "pll1_lock_detect", "label": "PLL1 lock"}],
            },
        ],
    }


class BuildPlanTests(unittest.TestCase):
    def test_orders_categories_and_filters_manual_ops(self) -> None:
        plan = build_plan(sample_manifest(), include_init=True)
        parts = [step.part for step in plan]
        # power (LTC2991) before clock (LMK04832) before memory (MT25QU02G)
        self.assertLess(parts.index("LTC2991"), parts.index("LMK04832"))
        self.assertLess(parts.index("LMK04832"), parts.index("MT25QU02G"))
        # manual-address data_read is excluded from the unattended plan
        self.assertNotIn("data_read", [step.operation for step in plan])
        # init comes before that device's reads
        ltc_ops = [step.operation for step in plan if step.part == "LTC2991"]
        self.assertEqual(ltc_ops[0], "device_init")
        # id_read sorts before other reads of the same device
        mt_ops = [step.operation for step in plan if step.part == "MT25QU02G"]
        self.assertEqual(mt_ops, ["device_init", "id_read"])

    def test_include_init_false_drops_risky_init(self) -> None:
        plan = build_plan(sample_manifest(), include_init=False)
        self.assertNotIn("device_init", [step.operation for step in plan])
        self.assertTrue(all(step.risk == "safe" for step in plan))


class AutoResponderSerial:
    """Fake serial that answers every S2C-MSG request with durum=0 (ok)."""

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
            for command_id, counter, _body in self._parser.feed(data):
                entry = s2cmsg.load_catalog()["by_id"][command_id & ~s2cmsg.RESPONSE_BIT]
                self.rx += _ok_response_frame(entry["op"], counter)
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        with self._lock:
            self._closed = True


class BringupRunTests(unittest.TestCase):
    def test_run_collects_results_and_certificate_renders(self) -> None:
        sessions = TestbenchSessionManager()
        fake = AutoResponderSerial()
        sessions.connect_serial("mc1", "COM9", 115200, 2.0, serial_factory=lambda _p, _b, _t: fake)

        import backend.bringup as bringup_module
        original = bringup_module.testbench_sessions
        bringup_module.testbench_sessions = sessions
        try:
            job = BringupJob(id="bringup_test", config=BringupConfig(
                session_id="mc1", manifest=sample_manifest(), include_init=True, timeout_s=2.0))
            BringupJobManager()._blocking(job)
        finally:
            bringup_module.testbench_sessions = original
            sessions.disconnect("mc1")

        result = job.result
        self.assertIsNotNone(result)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["passed"], result["total"])
        id_read_command_id = s2cmsg.message_id_for_op("id_read")
        self.assertTrue(any(
            struct.unpack_from("<I", request, 0)[0] == id_read_command_id
            for request in fake.requests))

        certificate = render_certificate_html(result)
        self.assertIn("bringup_unit", certificate)
        self.assertIn("GEÇTİ", certificate)
        self.assertIn("MT25QU02G", certificate)
        self.assertIn("Saat ağacı", certificate)


if __name__ == "__main__":
    unittest.main()
