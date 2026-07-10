"""Host-side telnet log istemcisi: firmware'in urettigi port 23 log sunucusuna baglanip
canli satirlari (Akis konsoluna beslemek uzere) tutar.

Bagimsizdir: backend/testbench.py'daki S2C-MSG oturumlarindan (TCP/serial/CoreSight)
ayri bir modul. Board'un telnet feed'i send-only duz metin (CRLF) satirlaridir; bu
istemci hicbir S2C-MSG cercevesi parse ETMEZ, yalniz satir ayirir. Ring/seq/read seklinde
backend/testbench.py `_TrafficRing` / seri konsol kalibini yansitir (aym sekil: per-session
bounded deque + monoton seq + `read(session_id, since_seq)`), ama bu modul ONLARI
IMPORT ETMEZ / paylasmaz.
"""

from __future__ import annotations

import collections
import socket
import threading
import time
import uuid

#: Per-session ring buyuklugu (Akis konsolu ekrani icin yeterli gecmis).
TELNET_LOG_MAX_LINES = 2000


class TelnetLogError(RuntimeError):
    """Telnet log oturumu bulunamadi ya da baglanti kurulamadi/kullanilamaz durumda."""


def _strip_telnet_iac(data: bytes) -> bytes:
    """IAC (0xFF) ile baslayan temel telnet komut dizilerini ayikla.

    Board bu baytlari HIC uretmez (send-only, opsiyon muzakeresi yok) ama
    istemci savunmaci davranir: IAC + (WILL/WONT/DO/DONT) + secenek (3 bayt)
    ve cift IAC (0xFF 0xFF -> literal 0xFF) kaliplarini tanir. Taninmayan tek
    basina IAC baytı da atlanir (guvenli varsayilan: 1 bayt ayikla).

    Not: kacis sonrasi literal 0xFF, cagiran `_flush_lines`/`_flush_partial_line`
    icinde `decode("ascii", errors="replace")` asamasindan gectigi icin
    U+FFFD (replacement char) olarak gorunur — 0xFF gecerli ASCII degildir.
    Board hicbir zaman IAC uretmedigi icin bu pratikte hic tetiklenmez;
    bilinen ve kabul edilen bir sinirlama.
    """
    IAC = 0xFF
    SB, SE = 0xFA, 0xF0
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        byte = data[i]
        if byte != IAC:
            out.append(byte)
            i += 1
            continue
        # byte == IAC
        if i + 1 >= n:
            i += 1  # yalniz IAC ile bitti - ayikla
            continue
        next_byte = data[i + 1]
        if next_byte == IAC:
            out.append(IAC)  # kacis: literal 0xFF
            i += 2
            continue
        if next_byte in (0xFB, 0xFC, 0xFD, 0xFE):  # WILL/WONT/DO/DONT + 1 secenek baytı
            i += 3
            continue
        if next_byte == SB:
            # Subnegotiation: IAC SE'ye kadar ayikla.
            end = data.find(bytes([IAC, SE]), i + 2)
            i = end + 2 if end >= 0 else n
            continue
        # Diger 2-baytlik komutlar (NOP, DM, vs.)
        i += 2
    return bytes(out)


class _TelnetLogSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.host = ""
        self.port = 0
        self.connected_at: float | None = None
        self.last_error = ""
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._lines: collections.deque[dict] = collections.deque(maxlen=TELNET_LOG_MAX_LINES)
        self._seq = 0
        self._buffer = bytearray()

    def status(self) -> dict:
        with self._lock:
            return {
                "session_id": self.session_id,
                "host": self.host,
                "port": self.port,
                "connected": self._sock is not None,
                "connected_at": self.connected_at,
                "last_error": self.last_error,
            }

    def connect(self, host: str, port: int, timeout_s: float) -> dict:
        with self._lock:
            self.close()
            self.host = host
            self.port = int(port)
            try:
                sock = socket.create_connection((self.host, self.port), timeout=max(0.2, float(timeout_s)))
                sock.settimeout(0.2)
            except OSError as exc:
                self.last_error = f"telnet log sunucusuna baglanilamadi ({host}:{port}): {exc}"
                raise TelnetLogError(self.last_error) from exc
            self._sock = sock
            self.connected_at = time.time()
            self.last_error = ""
            self._stop.clear()
            reader = threading.Thread(
                target=self._reader_loop, name=f"s2c-telnet-log-{self.session_id}", daemon=True,
            )
            reader.start()
            return self.status()

    def close(self) -> None:
        self._stop.set()
        sock = self._sock
        self._sock = None
        self.connected_at = None
        self._buffer.clear()
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _push_line(self, line: str) -> None:
        with self._lock:
            self._seq += 1
            self._lines.append({"seq": self._seq, "at": time.time(), "line": line})

    def _flush_lines(self) -> None:
        while True:
            index_lf = self._buffer.find(b"\n")
            if index_lf < 0:
                break
            raw = bytes(self._buffer[:index_lf])
            del self._buffer[: index_lf + 1]
            if raw.endswith(b"\r"):
                raw = raw[:-1]
            clean = _strip_telnet_iac(raw)
            line = clean.decode("ascii", errors="replace")
            if line:
                self._push_line(line)

    def _flush_partial_line(self) -> None:
        """Bufferda kalan (LF ile bitmeyen) son kismi satiri ring'e yaz.

        Sunucu baglantiyi kapattiginda son satir LF ile gelmemis olabilir;
        bu veri aksi halde sessizce kaybolurdu.
        """
        if not self._buffer:
            return
        raw = bytes(self._buffer)
        self._buffer.clear()
        if raw.endswith(b"\r"):
            raw = raw[:-1]
        clean = _strip_telnet_iac(raw)
        line = clean.decode("ascii", errors="replace")
        if line:
            self._push_line(line)

    def _reader_loop(self) -> None:
        while not self._stop.is_set():
            sock = self._sock
            if sock is None:
                return
            try:
                chunk = sock.recv(1024)
            except socket.timeout:
                continue
            except OSError as exc:
                with self._lock:
                    if not self._stop.is_set():
                        self._flush_partial_line()
                        self.last_error = str(exc)
                        self._sock = None
                        self.connected_at = None
                try:
                    sock.close()
                except OSError:
                    pass
                return
            if not chunk:
                # Sunucu baglantiyi kapatti (auto-reconnect YOK; kullanici tekrar baglanir).
                with self._lock:
                    self._flush_partial_line()
                    self.last_error = "karsi taraf baglantiyi kapatti"
                    self._sock = None
                    self.connected_at = None
                try:
                    sock.close()
                except OSError:
                    pass
                return
            with self._lock:
                self._buffer.extend(chunk)
                self._flush_lines()

    def read_since(self, since_seq: int) -> tuple[int, list[dict]]:
        with self._lock:
            entries = [entry for entry in self._lines if entry["seq"] > since_seq]
            return self._seq, entries


class TelnetLogManager:
    """Oturum kaydi: session_id -> _TelnetLogSession. Sunucu session_id uretir (uuid4)."""

    def __init__(self) -> None:
        self._sessions: dict[str, _TelnetLogSession] = {}
        self._lock = threading.RLock()

    def _prune_disconnected(self) -> None:
        """Kopuk oturumlari haritadan cikar (TTL thread'i olmadan sinirli tutar).

        Auto-reconnect kasitli olarak yok; board reboot'lari normal akis oldugu
        icin kopuk oturumlar surekli birikebilir. Her yeni connect() cagrisinda
        bir onceki calisin biraktigi kopuk oturumlari temizleriz.
        """
        with self._lock:
            stale_ids = [sid for sid, session in self._sessions.items() if not session.status()["connected"]]
            for sid in stale_ids:
                session = self._sessions.pop(sid, None)
                if session is not None:
                    session.close()  # savunmaci: zaten kapali olsa da tekrar close() guvenli

    def connect(self, host: str, port: int, timeout_s: float = 5.0) -> dict:
        self._prune_disconnected()
        session_id = f"telnet_{uuid.uuid4().hex[:12]}"
        session = _TelnetLogSession(session_id)
        with self._lock:
            self._sessions[session_id] = session
        try:
            status = session.connect(host.strip(), int(port), timeout_s)
        except TelnetLogError:
            with self._lock:
                self._sessions.pop(session_id, None)
            raise
        return {"session_id": session_id, "status": status}

    def _session(self, session_id: str) -> _TelnetLogSession:
        with self._lock:
            session = self._sessions.get(session_id)
        if session is None:
            raise TelnetLogError(f"telnet log oturumu bulunamadi: {session_id}")
        return session

    def read(self, session_id: str, since_seq: int) -> tuple[int, list[dict]]:
        return self._session(session_id).read_since(int(since_seq))

    def disconnect(self, session_id: str) -> dict:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            raise TelnetLogError(f"telnet log oturumu bulunamadi: {session_id}")
        session.close()
        return session.status()

    def status(self, session_id: str) -> dict:
        return self._session(session_id).status()


telnet_log_sessions = TelnetLogManager()
