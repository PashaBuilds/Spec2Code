"""Telnet log host istemcisi (backend/telnet_log.py) + REST endpointleri.

Kapsam: firmware'in urettigi telnet (port 23) log sunucusuna baglanan host
tarafi istemci oturumu. Gercek sahte telnet sunucusu socketserver ile kosar
(tests/test_testbench.py kalibiyla); satirlar CRLF ile gelir, IAC baytlari
(0xFF ile baslayan 3-baytlik dizinler) savunmaci sekilde ayiklanir (board bunu
hic uretmez ama istemci gene de temizler). REUSE: ring/seq/read seklinde
backend/testbench.py _TrafficRing / serial console kalibini yansitir ama bu
modul S2C-MSG transportu DEGILDIR (bagimsiz).
"""
from __future__ import annotations

import gc
import socket
import socketserver
import threading
import time
import unittest
import warnings

from fastapi.testclient import TestClient

from backend.telnet_log import TelnetLogError, TelnetLogManager


class LineDumpHandler(socketserver.BaseRequestHandler):
    """Sahte telnet log sunucusu: baglanti kurulunca kuyruklanmis satirlari yollar, sonra bekler."""

    lines: list[bytes] = []
    #: handle() donmeden once ekstra bekleme (kapanma/timeout testleri icin).
    hold_open_s = 0.0

    def handle(self) -> None:
        for line in self.__class__.lines:
            self.request.sendall(line)
        deadline = time.time() + self.__class__.hold_open_s
        while time.time() < deadline:
            self.request.settimeout(0.05)
            try:
                chunk = self.request.recv(64)
                if not chunk:
                    break
            except socket.timeout:
                continue


class TelnetLogManagerTests(unittest.TestCase):
    def test_connect_read_reports_lines_in_order_without_iac_bytes(self) -> None:
        LineDumpHandler.lines = [
            b"boot ok\r\n",
            b"S2C-LOG|I|hello\xff\xfb\x01world\r\n",  # IAC WILL (0x01) icine gomulu
            b"tail\n",  # yalniz LF ile biten satir da kabul edilmeli
        ]
        LineDumpHandler.hold_open_s = 0.3
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            result = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            self.assertTrue(result["status"]["connected"])
            session_id = result["session_id"]

            deadline = time.time() + 2.0
            entries: list[dict] = []
            seq = 0
            while time.time() < deadline and len(entries) < 3:
                seq, fresh = manager.read(session_id, seq)
                entries.extend(fresh)
                if len(entries) < 3:
                    time.sleep(0.05)
            thread.join(timeout=2)
            manager.disconnect(session_id)

        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["line"], "boot ok")
        self.assertEqual(entries[1]["line"], "S2C-LOG|I|helloworld")  # IAC dizisi ayiklandi
        self.assertEqual(entries[2]["line"], "tail")
        # Monoton artan seq.
        self.assertEqual([entry["seq"] for entry in entries], sorted(entry["seq"] for entry in entries))

    def test_read_since_seq_only_returns_new_entries(self) -> None:
        LineDumpHandler.lines = [b"a\r\n", b"b\r\n"]
        LineDumpHandler.hold_open_s = 0.2
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            status = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            session_id = status["session_id"]

            deadline = time.time() + 2.0
            seq = 0
            while time.time() < deadline:
                seq, fresh = manager.read(session_id, 0)
                if len(fresh) >= 2:
                    break
                time.sleep(0.05)
            thread.join(timeout=2)

            # since=seq (the latest) -> no new entries.
            seq2, none_entries = manager.read(session_id, seq)
            self.assertEqual(none_entries, [])
            self.assertEqual(seq2, seq)
            manager.disconnect(session_id)

    def test_connect_to_closed_port_raises_clear_error(self) -> None:
        # Baglanti reddedilen bir port (kapali local port) acik hata mesaji vermeli.
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            closed_port = server.server_address[1]
        manager = TelnetLogManager()
        with self.assertRaises(TelnetLogError) as ctx:
            manager.connect("127.0.0.1", closed_port, 1.0)
        self.assertTrue(str(ctx.exception))

    def test_status_reports_disconnected_after_server_closes(self) -> None:
        LineDumpHandler.lines = [b"only one line\r\n"]
        LineDumpHandler.hold_open_s = 0.0
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            status = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            session_id = status["session_id"]
            thread.join(timeout=2)

        # Sunucu kapandi (handle_request tek seferlik ve socket ile blok disinda
        # kapatildi); okuma dongusu bunu status'e yansitmali.
        deadline = time.time() + 2.0
        disconnected = False
        while time.time() < deadline:
            current = manager.status(session_id)
            if not current["connected"]:
                disconnected = True
                break
            time.sleep(0.05)
        self.assertTrue(disconnected)

    def test_disconnect_unknown_session_raises(self) -> None:
        manager = TelnetLogManager()
        with self.assertRaises(TelnetLogError):
            manager.disconnect("does-not-exist")

    def test_status_unknown_session_raises(self) -> None:
        manager = TelnetLogManager()
        with self.assertRaises(TelnetLogError):
            manager.status("does-not-exist")

    def test_read_unknown_session_raises(self) -> None:
        manager = TelnetLogManager()
        with self.assertRaises(TelnetLogError):
            manager.read("does-not-exist", 0)

    def test_disconnect_closes_socket_and_reports_status(self) -> None:
        LineDumpHandler.lines = []
        LineDumpHandler.hold_open_s = 1.0
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            status = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            session_id = status["session_id"]

            disconnected_status = manager.disconnect(session_id)
            self.assertFalse(disconnected_status["connected"])
            thread.join(timeout=2)

    def test_iac_iac_escape_produces_line_without_crash(self) -> None:
        # 0xFF 0xFF (IAC IAC kacisi) -> literal 0xFF; ardindan ASCII decode
        # asamasinda replacement char'a duser (board bunu hic uretmez ama
        # istemci savunmaci: crash olmamali, satir gene de gelmeli).
        LineDumpHandler.lines = [b"before\xff\xffafter\r\n"]
        LineDumpHandler.hold_open_s = 0.3
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            result = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            session_id = result["session_id"]

            deadline = time.time() + 2.0
            entries: list[dict] = []
            seq = 0
            while time.time() < deadline and not entries:
                seq, fresh = manager.read(session_id, seq)
                entries.extend(fresh)
                if not entries:
                    time.sleep(0.05)
            thread.join(timeout=2)
            manager.disconnect(session_id)

        self.assertEqual(len(entries), 1)
        # Literal 0xFF ASCII decode'da replacement char'a duser; crash yok,
        # satir once/sonra kismi metniyle birlikte gelir.
        self.assertIn("before", entries[0]["line"])
        self.assertIn("after", entries[0]["line"])

    def test_server_drop_flushes_partial_line_and_closes_socket_without_leak(self) -> None:
        # Son satir LF olmadan gelir; sunucu sonra baglantiyi kapatir.
        # Beklenen: (1) kismi satir ring'e flush edilir, (2) status disconnected
        # olur, (3) soket gercekten kapanir (ResourceWarning yok).
        LineDumpHandler.lines = [b"complete line\r\n", b"partial-no-newline"]
        LineDumpHandler.hold_open_s = 0.0
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            manager = TelnetLogManager()
            status = manager.connect("127.0.0.1", server.server_address[1], 2.0)
            session_id = status["session_id"]
            session = manager._session(session_id)
            thread.join(timeout=2)

            deadline = time.time() + 2.0
            disconnected = False
            while time.time() < deadline:
                current = manager.status(session_id)
                if not current["connected"]:
                    disconnected = True
                    break
                time.sleep(0.05)
            self.assertTrue(disconnected)

            deadline = time.time() + 2.0
            entries: list[dict] = []
            while time.time() < deadline and len(entries) < 2:
                _, fresh = manager.read(session_id, 0)
                entries = fresh
                if len(entries) < 2:
                    time.sleep(0.05)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["line"], "complete line")
            self.assertEqual(entries[1]["line"], "partial-no-newline")

            closed_sock = session._sock
            self.assertIsNone(closed_sock)

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                del session
                gc.collect()
                gc.collect()
            resource_warnings = [w for w in caught if issubclass(w.category, ResourceWarning)]
            self.assertEqual(resource_warnings, [])

            manager.disconnect(session_id)

    def test_connect_prunes_disconnected_sessions_after_repeated_drops(self) -> None:
        # 3 kez connect/drop dongusu sonrasi manager'da disconnected oturum
        # birikmemeli (prune-on-connect, TTL thread'i olmadan).
        manager = TelnetLogManager()
        for _ in range(3):
            LineDumpHandler.lines = [b"line\r\n"]
            LineDumpHandler.hold_open_s = 0.0
            with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
                thread = threading.Thread(target=server.handle_request, daemon=True)
                thread.start()
                status = manager.connect("127.0.0.1", server.server_address[1], 2.0)
                session_id = status["session_id"]
                thread.join(timeout=2)

            deadline = time.time() + 2.0
            while time.time() < deadline:
                if not manager.status(session_id)["connected"]:
                    break
                time.sleep(0.05)

        # Son connect() cagrisi onceki iki kopuk oturumu budamis olmali;
        # haritada en fazla 1 (en son eklenen, henuz kopuk olarak yakalanmis
        # olabilir) oturum kalmali.
        self.assertLessEqual(len(manager._sessions), 1)


def _build_test_client():
    from backend.main import app
    return TestClient(app)


class TelnetLogRoutesSmokeTests(unittest.TestCase):
    """FastAPI TestClient + gercek TelnetLogManager + sahte telnet sunucusu (gercek soket)."""

    def test_connect_read_disconnect_status_roundtrip(self) -> None:
        LineDumpHandler.lines = [b"route smoke line\r\n"]
        LineDumpHandler.hold_open_s = 0.3
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            thread = threading.Thread(target=server.handle_request, daemon=True)
            thread.start()
            client = _build_test_client()

            resp = client.post("/api/telnet-log/connect", json={
                "host": "127.0.0.1", "port": server.server_address[1], "timeout_s": 2.0,
            })
            self.assertEqual(resp.status_code, 200, resp.text)
            data = resp.json()
            self.assertTrue(data["status"]["connected"])
            session_id = data["session_id"]

            deadline = time.time() + 2.0
            entries: list[dict] = []
            since = 0
            while time.time() < deadline and not entries:
                read_resp = client.get(f"/api/telnet-log/{session_id}/read", params={"since": since})
                self.assertEqual(read_resp.status_code, 200, read_resp.text)
                payload = read_resp.json()
                since = payload["seq"]
                entries = payload["entries"]
                if not entries:
                    time.sleep(0.05)
            thread.join(timeout=2)

            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["line"], "route smoke line")

            status_resp = client.get(f"/api/telnet-log/{session_id}/status")
            self.assertEqual(status_resp.status_code, 200, status_resp.text)

            disc_resp = client.post(f"/api/telnet-log/{session_id}/disconnect")
            self.assertEqual(disc_resp.status_code, 200, disc_resp.text)
            self.assertFalse(disc_resp.json()["connected"])

    def test_connect_route_reports_error_on_refused_connection(self) -> None:
        with socketserver.TCPServer(("127.0.0.1", 0), LineDumpHandler) as server:
            closed_port = server.server_address[1]
        client = _build_test_client()
        resp = client.post("/api/telnet-log/connect", json={
            "host": "127.0.0.1", "port": closed_port, "timeout_s": 1.0,
        })
        self.assertEqual(resp.status_code, 502, resp.text)

    def test_read_route_unknown_session_returns_404(self) -> None:
        client = _build_test_client()
        resp = client.get("/api/telnet-log/does-not-exist/read", params={"since": 0})
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_disconnect_route_unknown_session_returns_404(self) -> None:
        client = _build_test_client()
        resp = client.post("/api/telnet-log/does-not-exist/disconnect")
        self.assertEqual(resp.status_code, 404, resp.text)

    def test_status_route_unknown_session_returns_404(self) -> None:
        client = _build_test_client()
        resp = client.get("/api/telnet-log/does-not-exist/status")
        self.assertEqual(resp.status_code, 404, resp.text)


if __name__ == "__main__":
    unittest.main()
