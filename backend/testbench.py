"""Host-side TCP bridge for the generated Spec2Code target test bench agent."""

from __future__ import annotations

import socket
import threading
import time
from dataclasses import dataclass, field


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


class TestbenchSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, _TestbenchTcpSession] = {}
        self._lock = threading.RLock()

    def _clean_session_id(self, session_id: str) -> str:
        clean_id = _clean_token(session_id)
        if not clean_id:
            raise TestbenchSessionError("testbench session_id is empty")
        return clean_id

    def _session(self, session_id: str) -> _TestbenchTcpSession:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
            if session is None:
                session = _TestbenchTcpSession(clean_id)
                self._sessions[clean_id] = session
            return session

    def connect(self, session_id: str, host: str, port: int, timeout_s: float) -> TestbenchSessionStatus:
        return self._session(session_id).connect(host.strip(), int(port), timeout_s)

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
