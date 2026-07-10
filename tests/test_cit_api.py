"""Task 8: CIT decode + REST endpointleri.

decode_board_cit: elle kurulmus SBoardCit bytes -> alan dogrulamasi (bkz.
tests/test_cit_codegen.py._decode_cit_response icin ayni bayt yerlesimi).
Endpoint testleri FastAPI TestClient + monkeypatch edilmis
TestbenchSessionManager.send_named ile calisir (gercek soket yok).
send_named icin ayrica PersistentHandler benzeri gercek TCP fake-session
entegrasyon testi (tests/test_testbench.py kalibiyla).
"""
from __future__ import annotations

import socketserver
import struct
import threading
import unittest

from fastapi.testclient import TestClient

from backend import s2cmsg
from backend.cit import decode_board_cit
from backend.testbench import TestbenchSessionManager


def _pad4(data: bytes) -> bytes:
    remainder = len(data) % 4
    return data if remainder == 0 else data + b"\x00" * (4 - remainder)


def _sboard_cit_bytes(sayac: int, zaman: int, olcumler: list[dict], flag_bits: list[int]) -> bytes:
    """SBoardCit govdesi: uiSayac(4)+uiZaman(4)+bayrak_words+arrOlcum[N]*12."""
    n = len(olcumler)
    flag_words = ((n + 31) // 32) * 4
    flags = 0
    for bit in flag_bits:
        flags |= 1 << bit
    body = struct.pack("<II", sayac, zaman)
    body += flags.to_bytes(flag_words, "little")
    for item in olcumler:
        body += struct.pack("<iII", item["iDeger"], item["uiHam"], item["uiDurum"])
    return body


def _cit_response_body(istek_sayac: int, durum: int, cit_bytes: bytes) -> bytes:
    return struct.pack("<II", istek_sayac, durum) + cit_bytes


def _fake_manifest_cit(n: int = 2) -> dict:
    return {
        "cit": {
            "olcumler": [
                {
                    "index": 0, "device": "u1_ltc2991", "device_index": 0, "part": "LTC2991",
                    "op": "voltage_read", "name": "VCC_3V3_RF", "cname": "Vcc3v3Rf",
                    "unit": "mV", "min": 3135, "max": 3465, "severity": "critical", "enabled": True,
                },
                {
                    "index": 1, "device": "u2_ad7414", "device_index": 1, "part": "AD7414",
                    "op": "temperature_read", "name": "AD_TEMP", "cname": "AdTemp",
                    "unit": "C", "min": 2000, "max": 3000, "severity": "warning", "enabled": True,
                },
            ][:n],
            "bit_sirasi": ["Vcc3v3Rf", "AdTemp"][:n],
        },
    }


class DecodeBoardCitTests(unittest.TestCase):
    def test_decode_ok_and_nok_measurements(self) -> None:
        # Bayrak biti = OKUMA BASARISI (limit degil). Limit/OK-NOK karari host'ta;
        # decode yalniz read_ok + ham/deger + manifest varsayilan limitlerini tasir.
        manifest = _fake_manifest_cit(2)
        cit_bytes = _sboard_cit_bytes(
            sayac=7, zaman=123456,
            olcumler=[
                {"iDeger": 3300, "uiHam": 0xABCD, "uiDurum": 0},  # okuma basarili
                {"iDeger": 9999, "uiHam": 0x1234, "uiDurum": 0},  # okuma bayragi set degil
            ],
            flag_bits=[0],  # yalniz olcum 0 okuma-basarili biti set
        )
        body = _cit_response_body(istek_sayac=42, durum=0, cit_bytes=cit_bytes)

        result = decode_board_cit(body, manifest)

        self.assertEqual(result["durum"], 0)
        self.assertEqual(result["sayac"], 7)
        self.assertEqual(result["zaman"], 123456)
        self.assertEqual(len(result["olcumler"]), 2)

        first = result["olcumler"][0]
        self.assertEqual(first["index"], 0)
        self.assertEqual(first["name"], "VCC_3V3_RF")
        self.assertEqual(first["cname"], "Vcc3v3Rf")
        self.assertEqual(first["part"], "LTC2991")
        self.assertEqual(first["device"], "u1_ltc2991")
        self.assertEqual(first["op"], "voltage_read")
        self.assertEqual(first["unit"], "mV")
        self.assertEqual(first["raw"], 0xABCD)
        self.assertEqual(first["value"], 3300)
        self.assertTrue(first["read_ok"])
        self.assertEqual(first["durum"], 0)
        self.assertEqual(first["min"], 3135)  # manifest varsayilani (host store ile override edilir)
        self.assertEqual(first["max"], 3465)
        self.assertEqual(first["severity"], "critical")
        self.assertTrue(first["enabled"])

        second = result["olcumler"][1]
        self.assertEqual(second["value"], 9999)
        self.assertEqual(second["raw"], 0x1234)
        self.assertFalse(second["read_ok"])  # okuma-basarili biti set degil
        self.assertEqual(second["severity"], "warning")

    def test_decode_multiword_flags_bit_i_word_i_div_32(self) -> None:
        # 40 olcum -> 2 bayrak kelimesi (((40+31)//32)*4 = 8 bayt). Bit 33
        # (ikinci kelimede) set edilirse yalniz olcum 33 ok olmali.
        olcumler_manifest = [
            {
                "index": i, "device": f"u{i}", "device_index": i, "part": f"PART{i}",
                "op": "voltage_read", "name": f"M{i}", "cname": f"M{i}",
                "unit": "mV", "min": None, "max": None, "severity": "warning", "enabled": True,
            }
            for i in range(40)
        ]
        manifest = {"cit": {"olcumler": olcumler_manifest, "bit_sirasi": [m["cname"] for m in olcumler_manifest]}}
        olcumler = [{"iDeger": i, "uiHam": i, "uiDurum": 0} for i in range(40)]
        cit_bytes = _sboard_cit_bytes(sayac=1, zaman=1, olcumler=olcumler, flag_bits=[33])
        body = _cit_response_body(istek_sayac=1, durum=0, cit_bytes=cit_bytes)

        result = decode_board_cit(body, manifest)

        for item in result["olcumler"]:
            if item["index"] == 33:
                self.assertTrue(item["read_ok"])
            else:
                self.assertFalse(item["read_ok"])

    def test_decode_read_ok_flag_reflects_board_read_success(self) -> None:
        manifest = {
            "cit": {
                "olcumler": [{
                    "index": 0, "device": "u1", "device_index": 0, "part": "P",
                    "op": "voltage_read", "name": "N", "cname": "N",
                    "unit": "mV", "min": None, "max": None, "severity": "warning", "enabled": True,
                }],
                "bit_sirasi": ["N"],
            },
        }
        cit_bytes = _sboard_cit_bytes(sayac=1, zaman=1, olcumler=[{"iDeger": 5000, "uiHam": 5000, "uiDurum": 0}], flag_bits=[0])
        body = _cit_response_body(istek_sayac=1, durum=0, cit_bytes=cit_bytes)
        result = decode_board_cit(body, manifest)
        self.assertTrue(result["olcumler"][0]["read_ok"])

    def test_decode_short_body_raises_clear_error(self) -> None:
        manifest = _fake_manifest_cit(2)
        with self.assertRaises(ValueError) as ctx:
            decode_board_cit(b"\x00" * 4, manifest)
        message = str(ctx.exception)
        self.assertIn("manifest", message.lower())

    def test_decode_body_length_mismatch_with_manifest_raises_clear_error(self) -> None:
        # Manifest 2 olcum bekliyor ama govde yalniz 1 olcum tasiyor.
        manifest = _fake_manifest_cit(2)
        cit_bytes = _sboard_cit_bytes(
            sayac=1, zaman=1,
            olcumler=[{"iDeger": 1, "uiHam": 1, "uiDurum": 0}],
            flag_bits=[0],
        )
        body = _cit_response_body(istek_sayac=1, durum=0, cit_bytes=cit_bytes)
        with self.assertRaises(ValueError) as ctx:
            decode_board_cit(body, manifest)
        message = str(ctx.exception)
        self.assertIn("manifest", message.lower())

    def test_decode_no_cit_in_manifest_raises(self) -> None:
        with self.assertRaises(ValueError):
            decode_board_cit(b"\x00" * 100, {})


class SendNamedIntegrationTests(unittest.TestCase):
    """Gercek TCP soket uzerinden send_named: CIT_RUN yaniti doner, sayac eslesir."""

    def test_send_named_returns_prefix_and_raw_body(self) -> None:
        manifest = _fake_manifest_cit(1)
        cit_bytes = _sboard_cit_bytes(sayac=1, zaman=99, olcumler=[{"iDeger": 42, "uiHam": 42, "uiDurum": 0}], flag_bits=[0])

        class CitHandler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                data = self.request.recv(4096)
                frames = s2cmsg.FrameParser().feed(data)
                command_id, counter, _body = frames[0]
                response_body = _cit_response_body(istek_sayac=counter, durum=0, cit_bytes=cit_bytes)
                response = s2cmsg.pack_frame(command_id | s2cmsg.RESPONSE_BIT, counter, response_body)
                self.request.sendall(response)

        with socketserver.TCPServer(("127.0.0.1", 0), CitHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                manager = TestbenchSessionManager()
                manager.connect("cit1", "127.0.0.1", server.server_address[1], 2.0)
                prefix, raw_body = manager.send_named("cit1", "CIT_RUN", timeout_s=2.0)
                self.assertEqual(prefix["durum"], 0)
                decoded = decode_board_cit(
                    struct.pack("<II", prefix["istek_sayac"], prefix["durum"]) + raw_body,
                    manifest,
                )
                self.assertEqual(decoded["olcumler"][0]["value"], 42)
                manager.disconnect("cit1")
            finally:
                server.shutdown()


def _build_test_client():
    from backend.main import app
    return TestClient(app)


class CitEndpointSmokeTests(unittest.TestCase):
    """Sahte oturum: manager.send_named monkeypatch edilir, endpoint JSON sekli dogrulanir."""

    def test_cit_run_endpoint_returns_decoded_json(self) -> None:
        import backend.api.routes as routes_module

        manifest = _fake_manifest_cit(1)
        cit_bytes = _sboard_cit_bytes(sayac=3, zaman=555, olcumler=[{"iDeger": 10, "uiHam": 10, "uiDurum": 0}], flag_bits=[0])

        def fake_send_named(session_id: str, name: str, timeout_s: float = 10.0):
            self.assertEqual(name, "CIT_RUN")
            return {"istek_sayac": 9, "durum": 0}, cit_bytes

        original = routes_module.testbench_sessions.send_named
        routes_module.testbench_sessions.send_named = fake_send_named  # type: ignore[method-assign]
        try:
            client = _build_test_client()
            resp = client.post("/api/testbench/cit/run", json={
                "session_id": "s1", "manifest": manifest, "timeout_s": 5.0,
            })
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertEqual(data["durum"], 0)
            self.assertEqual(data["sayac"], 3)
            self.assertEqual(data["zaman"], 555)
            self.assertEqual(data["olcumler"][0]["value"], 10)
        finally:
            routes_module.testbench_sessions.send_named = original  # type: ignore[method-assign]

    def test_cit_run_endpoint_missing_cit_in_manifest_returns_400(self) -> None:
        client = _build_test_client()
        resp = client.post("/api/testbench/cit/run", json={
            "session_id": "s1", "manifest": {}, "timeout_s": 5.0,
        })
        self.assertEqual(resp.status_code, 400)

    def test_cit_run_endpoint_unsupported_status_returns_200_with_flag(self) -> None:
        import backend.api.routes as routes_module

        manifest = _fake_manifest_cit(1)

        def fake_send_named(session_id: str, name: str, timeout_s: float = 10.0):
            # DESTEKLENMIYOR (7): govde SBoardCit tasimayabilir/gecersiz olabilir.
            return {"istek_sayac": 1, "durum": 7}, b""

        original = routes_module.testbench_sessions.send_named
        routes_module.testbench_sessions.send_named = fake_send_named  # type: ignore[method-assign]
        try:
            client = _build_test_client()
            resp = client.post("/api/testbench/cit/run", json={
                "session_id": "s1", "manifest": manifest, "timeout_s": 5.0,
            })
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertEqual(data["durum"], 7)
            self.assertEqual(data["olcumler"], [])
            self.assertTrue(data["desteklenmiyor"])
        finally:
            routes_module.testbench_sessions.send_named = original  # type: ignore[method-assign]


if __name__ == "__main__":
    unittest.main()
