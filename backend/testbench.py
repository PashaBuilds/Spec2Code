"""Host-side TCP bridge for the generated Spec2Code target test bench agent."""

from __future__ import annotations

import socket
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


def send_command(command: TestbenchCommand) -> TestbenchResult:
    request_line = format_command(command)
    with socket.create_connection((command.host, int(command.port)), timeout=max(0.2, command.timeout_s)) as sock:
        sock.settimeout(max(0.2, command.timeout_s))
        sock.sendall(request_line.encode("ascii"))
        chunks: list[bytes] = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
    response_line = b"".join(chunks).decode("ascii", errors="replace").strip()
    return TestbenchResult(
        request_line=request_line.strip(),
        response_line=response_line,
        parsed=parse_response(response_line),
    )
