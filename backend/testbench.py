"""Host-side TCP/serial bridge for the generated Spec2Code target test bench agent."""

from __future__ import annotations

import collections
import queue
import socket
import threading
import time
from dataclasses import dataclass, field

#: Ring size of the serial console line buffer kept per session.
SERIAL_CONSOLE_MAX_LINES = 2000


@dataclass(frozen=True)
class TestbenchCommand:
    host: str
    port: int
    device: str
    operation: str
    command_id: int = 1
    register: str = ""
    register_address: int | None = None
    address: int | None = None
    length: int | None = None
    value: int | None = None
    data_hex: str = ""
    timeout_s: float = 5.0


@dataclass
class TestbenchResult:
    request_line: str
    response_line: str
    parsed: dict[str, str] = field(default_factory=dict)


@dataclass
class TestbenchSessionStatus:
    session_id: str
    host: str = ""
    port: int = 0
    connected: bool = False
    connected_at: float | None = None
    last_used_at: float | None = None
    last_error: str = ""
    transport: str = "tcp"
    serial_port: str = ""
    baud: int = 0


class TestbenchSessionError(RuntimeError):
    """Raised when a persistent target test bench session is not usable."""


def _clean_token(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch not in "|\r\n")


def _hex_data(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch in "0123456789abcdefABCDEF")


def format_command(command: TestbenchCommand) -> str:
    parts = [
        "S2C",
        f"id={int(command.command_id)}",
        f"device={_clean_token(command.device)}",
        f"op={_clean_token(command.operation)}",
    ]
    if command.register:
        parts.append(f"reg={_clean_token(command.register)}")
    if command.register_address is not None:
        parts.append(f"reg_addr=0x{int(command.register_address) & 0xFFFFFFFF:X}")
    if command.address is not None:
        parts.append(f"address=0x{int(command.address) & 0xFFFFFFFF:X}")
    if command.length is not None:
        parts.append(f"length={max(0, int(command.length))}")
    if command.value is not None:
        parts.append(f"value=0x{int(command.value) & 0xFFFFFFFF:X}")
    data = _hex_data(command.data_hex)
    if data:
        parts.append(f"data={data}")
    return "|".join(parts) + "\n"


def parse_response(line: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for token in line.strip().split("|"):
        if "=" not in token:
            continue
        key, value = token.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def _read_response_line(sock: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise OSError("testbench tcp connection closed before response")
        chunks.append(chunk)
        if b"\n" in chunk:
            break
    return b"".join(chunks).decode("ascii", errors="replace").strip()


def _send_over_socket(sock: socket.socket, command: TestbenchCommand) -> TestbenchResult:
    request_line = format_command(command)
    sock.sendall(request_line.encode("ascii"))
    response_line = _read_response_line(sock)
    return TestbenchResult(
        request_line=request_line.strip(),
        response_line=response_line,
        parsed=parse_response(response_line),
    )


def send_command(command: TestbenchCommand) -> TestbenchResult:
    with socket.create_connection((command.host, int(command.port)), timeout=max(0.2, command.timeout_s)) as sock:
        sock.settimeout(max(0.2, command.timeout_s))
        return _send_over_socket(sock, command)


class _TestbenchTcpSession:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.host = ""
        self.port = 0
        self.timeout_s = 5.0
        self.connected_at: float | None = None
        self.last_used_at: float | None = None
        self.last_error = ""
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()

    def status(self) -> TestbenchSessionStatus:
        with self._lock:
            return TestbenchSessionStatus(
                session_id=self.session_id,
                host=self.host,
                port=self.port,
                connected=self._sock is not None,
                connected_at=self.connected_at,
                last_used_at=self.last_used_at,
                last_error=self.last_error,
            )

    def connect(self, host: str, port: int, timeout_s: float) -> TestbenchSessionStatus:
        with self._lock:
            self.close()
            self.host = host
            self.port = int(port)
            self.timeout_s = max(0.2, float(timeout_s))
            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.timeout_s)
                sock.settimeout(self.timeout_s)
            except OSError as exc:
                self.last_error = str(exc)
                raise
            self._sock = sock
            now = time.time()
            self.connected_at = now
            self.last_used_at = now
            self.last_error = ""
            return self.status()

    def close(self) -> None:
        sock = self._sock
        self._sock = None
        self.connected_at = None
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def send(self, command: TestbenchCommand) -> TestbenchResult:
        with self._lock:
            if self._sock is None:
                raise TestbenchSessionError("testbench tcp session is not connected")
            session_command = TestbenchCommand(
                host=self.host,
                port=self.port,
                device=command.device,
                operation=command.operation,
                command_id=command.command_id,
                register=command.register,
                register_address=command.register_address,
                address=command.address,
                length=command.length,
                value=command.value,
                data_hex=command.data_hex,
                timeout_s=self.timeout_s,
            )
            try:
                result = _send_over_socket(self._sock, session_command)
            except OSError as exc:
                self.last_error = str(exc)
                self.close()
                raise
            self.last_used_at = time.time()
            self.last_error = ""
            return result


class _TestbenchSerialSession:
    """Persistent serial (COM) session for the UART test bench agent.

    A reader thread splits incoming bytes into lines. Every line lands in a
    bounded console ring (for the UART console UI); lines that look like
    protocol responses ("S2C|...|ok=...") are additionally queued for
    ``send()``. Console noise between responses is therefore harmless even
    when the agent shares the console UART with xil_printf output.
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.port_name = ""
        self.baud = 115200
        self.timeout_s = 5.0
        self.connected_at: float | None = None
        self.last_used_at: float | None = None
        self.last_error = ""
        self._serial = None
        self._lock = threading.RLock()
        self._send_lock = threading.Lock()
        self._stop = threading.Event()
        self._responses: "queue.Queue[str]" = queue.Queue()
        self._console: collections.deque[dict] = collections.deque(maxlen=SERIAL_CONSOLE_MAX_LINES)
        self._console_seq = 0

    def status(self) -> TestbenchSessionStatus:
        with self._lock:
            return TestbenchSessionStatus(
                session_id=self.session_id,
                connected=self._serial is not None,
                connected_at=self.connected_at,
                last_used_at=self.last_used_at,
                last_error=self.last_error,
                transport="serial",
                serial_port=self.port_name,
                baud=self.baud,
            )

    def connect(self, port_name: str, baud: int, timeout_s: float, *, serial_factory=None) -> TestbenchSessionStatus:
        with self._lock:
            self.close()
            self.port_name = port_name
            self.baud = int(baud)
            self.timeout_s = max(0.2, float(timeout_s))
            try:
                if serial_factory is not None:
                    handle = serial_factory(self.port_name, self.baud, self.timeout_s)
                else:
                    import serial  # lazy: only the serial transport needs pyserial

                    if "://" in self.port_name:
                        # pyserial URL handlers (loop://, socket://...) — used for
                        # hardware-less smoke tests.
                        handle = serial.serial_for_url(self.port_name, baudrate=self.baud, timeout=0.2)
                    else:
                        handle = serial.Serial(self.port_name, self.baud, timeout=0.2)
            except OSError as exc:
                self.last_error = str(exc)
                raise
            self._serial = handle
            self._stop.clear()
            reader = threading.Thread(
                target=self._reader_loop,
                name=f"s2c-serial-{self.session_id}",
                daemon=True,
            )
            reader.start()
            now = time.time()
            self.connected_at = now
            self.last_used_at = now
            self.last_error = ""
            return self.status()

    def close(self) -> None:
        self._stop.set()
        handle = self._serial
        self._serial = None
        self.connected_at = None
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass

    def _console_push(self, line: str) -> None:
        with self._lock:
            self._console_seq += 1
            self._console.append({"seq": self._console_seq, "at": time.time(), "line": line})

    def _reader_loop(self) -> None:
        buffer = bytearray()
        while not self._stop.is_set():
            handle = self._serial
            if handle is None:
                return
            try:
                chunk = handle.read(256)
            except (OSError, ValueError) as exc:
                with self._lock:
                    if not self._stop.is_set():
                        self.last_error = str(exc)
                return
            if not chunk:
                continue
            buffer.extend(chunk)
            while True:
                index = buffer.find(b"\n")
                if index < 0:
                    break
                raw = bytes(buffer[:index])
                del buffer[: index + 1]
                line = raw.decode("ascii", errors="replace").rstrip("\r")
                if not line:
                    continue
                self._console_push(line)
                if line.startswith("S2C|") and "|ok=" in line:
                    self._responses.put(line)

    def console_since(self, since_seq: int) -> tuple[int, list[dict]]:
        with self._lock:
            entries = [entry for entry in self._console if entry["seq"] > since_seq]
            return self._console_seq, entries

    def write_raw(self, text: str) -> None:
        with self._lock:
            handle = self._serial
            if handle is None:
                raise TestbenchSessionError("testbench serial session is not connected")
            payload = text if text.endswith("\n") else text + "\r\n"
            try:
                handle.write(payload.encode("ascii", errors="replace"))
                handle.flush()
            except OSError as exc:
                self.last_error = str(exc)
                self.close()
                raise
            self.last_used_at = time.time()

    def send(self, command: TestbenchCommand) -> TestbenchResult:
        request_line = format_command(command)
        with self._send_lock:
            with self._lock:
                handle = self._serial
                if handle is None:
                    raise TestbenchSessionError("testbench serial session is not connected")
                while True:  # drop stale responses from earlier timeouts
                    try:
                        self._responses.get_nowait()
                    except queue.Empty:
                        break
                try:
                    handle.write(request_line.encode("ascii"))
                    handle.flush()
                except OSError as exc:
                    self.last_error = str(exc)
                    self.close()
                    raise
            # Wait outside the state lock so the reader thread and console
            # polling stay live while we block on the response.
            try:
                response_line = self._responses.get(timeout=self.timeout_s)
            except queue.Empty:
                with self._lock:
                    self.last_error = f"no response within {self.timeout_s}s"
                raise TestbenchSessionError(
                    f"testbench serial response timeout after {self.timeout_s}s")
        with self._lock:
            self.last_used_at = time.time()
            self.last_error = ""
        return TestbenchResult(
            request_line=request_line.strip(),
            response_line=response_line,
            parsed=parse_response(response_line),
        )


def list_serial_ports() -> list[dict]:
    """Available COM ports for the UI dropdown (empty when pyserial is absent)."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return []
    ports = []
    for info in list_ports.comports():
        ports.append({
            "device": info.device,
            "description": info.description or "",
            "hwid": info.hwid or "",
        })
    return sorted(ports, key=lambda item: item["device"])


class TestbenchSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, _TestbenchTcpSession | _TestbenchSerialSession] = {}
        self._lock = threading.RLock()

    def _clean_session_id(self, session_id: str) -> str:
        clean_id = _clean_token(session_id)
        if not clean_id:
            raise TestbenchSessionError("testbench session_id is empty")
        return clean_id

    def _session(self, session_id: str) -> _TestbenchTcpSession | _TestbenchSerialSession:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
            if session is None:
                session = _TestbenchTcpSession(clean_id)
                self._sessions[clean_id] = session
            return session

    def _replace_session(self, session_id: str, session) -> None:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            old = self._sessions.pop(clean_id, None)
            self._sessions[clean_id] = session
        if old is not None:
            old.close()

    def connect(self, session_id: str, host: str, port: int, timeout_s: float) -> TestbenchSessionStatus:
        session = _TestbenchTcpSession(self._clean_session_id(session_id))
        self._replace_session(session_id, session)
        return session.connect(host.strip(), int(port), timeout_s)

    def connect_serial(
        self,
        session_id: str,
        port_name: str,
        baud: int,
        timeout_s: float,
        *,
        serial_factory=None,
    ) -> TestbenchSessionStatus:
        session = _TestbenchSerialSession(self._clean_session_id(session_id))
        self._replace_session(session_id, session)
        return session.connect(port_name.strip(), int(baud), timeout_s, serial_factory=serial_factory)

    def _serial_session(self, session_id: str) -> _TestbenchSerialSession:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
        if not isinstance(session, _TestbenchSerialSession):
            raise TestbenchSessionError("testbench serial session is not connected")
        return session

    def console(self, session_id: str, since_seq: int) -> tuple[int, list[dict]]:
        return self._serial_session(session_id).console_since(int(since_seq))

    def write_raw(self, session_id: str, text: str) -> None:
        self._serial_session(session_id).write_raw(text)

    def disconnect(self, session_id: str) -> TestbenchSessionStatus:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.pop(clean_id, None)
        if session is None:
            return TestbenchSessionStatus(session_id=clean_id)
        session.close()
        return session.status()

    def status(self, session_id: str) -> TestbenchSessionStatus:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
        return session.status() if session is not None else TestbenchSessionStatus(session_id=clean_id)

    def send(self, session_id: str, command: TestbenchCommand) -> TestbenchResult:
        return self._session(session_id).send(command)


testbench_sessions = TestbenchSessionManager()
