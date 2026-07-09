"""Host-side TCP/serial/CoreSight bridge for the generated Spec2Code target test bench agent."""

from __future__ import annotations

import collections
import os
import queue
import socket
import struct
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from backend import s2cmsg

#: Ring size of the serial console line buffer kept per session.
SERIAL_CONSOLE_MAX_LINES = 2000

#: Ring size of the per-session TX/RX traffic buffer (Veri Akisi ekrani).
TRAFFIC_MAX_LINES = 2000

#: How long to wait for xsdb's jtagterminal to report its bridge port.
CORESIGHT_BRIDGE_TIMEOUT_S = 60.0


@dataclass(frozen=True)
class TestbenchCommand:
    host: str
    port: int
    device: str
    operation: str
    command_id: int = 1
    device_index: int = 0xFFFFFFFF
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
    processor: str = ""
    hw_server_url: str = ""
    dcc_port: int = 0


class TestbenchSessionError(RuntimeError):
    """Raised when a persistent target test bench session is not usable."""


def _clean_token(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch not in "|\r\n")


def _pack_command(command: TestbenchCommand) -> bytes:
    """S2C-MSG istek cercevesi kur. Bilinmeyen op -> KeyError (yutulmaz)."""
    return s2cmsg.pack_request(
        command.operation,
        int(command.command_id),
        device_index=int(command.device_index) & 0xFFFFFFFF,
        register_address=int(command.register_address or 0) & 0xFFFFFFFF,
        address=int(command.address or 0) & 0xFFFFFFFF,
        length=max(0, int(command.length or 0)),
        value=command.value,
        data=bytes.fromhex(command.data_hex or ""),
    )


def _request_frame_summary(command: TestbenchCommand, request: bytes) -> str:
    """Decode ``request`` (bytes just sent) back into a readable summary line."""
    frame = s2cmsg.FrameParser().feed(request)[0]
    return s2cmsg.decode_frame_summary(frame)


def send_command(command: TestbenchCommand) -> TestbenchResult:
    with socket.create_connection((command.host, int(command.port)), timeout=max(0.2, command.timeout_s)) as sock:
        sock.settimeout(max(0.2, command.timeout_s))
        request = _pack_command(command)
        sock.sendall(request)
        parser = s2cmsg.FrameParser()
        deadline = time.time() + max(0.2, command.timeout_s)
        frames: list[tuple[int, int, bytes]] = []
        while not frames:
            remaining = deadline - time.time()
            if remaining <= 0:
                raise OSError("testbench tcp response timeout")
            sock.settimeout(max(0.05, remaining))
            chunk = sock.recv(4096)
            if not chunk:
                raise OSError("testbench tcp connection closed before response")
            frames = parser.feed(chunk)
        frame = frames[0]
        return TestbenchResult(
            request_line=_request_frame_summary(command, request),
            response_line=s2cmsg.decode_frame_summary(frame),
            parsed=s2cmsg.unpack_response(frame),
        )


class _TrafficRing:
    """Per-session TX/RX line ring shared by every transport.

    Feeds the Veri Akisi (data flow) screen: each protocol line that leaves
    (tx) or arrives (rx) is recorded with a timestamp so the user can watch
    the live conversation regardless of transport (TCP, serial, CoreSight).
    """

    def __init__(self) -> None:
        self._traffic: collections.deque[dict] = collections.deque(maxlen=TRAFFIC_MAX_LINES)
        self._traffic_seq = 0
        self._traffic_lock = threading.Lock()

    def _traffic_push(self, direction: str, data: bytes) -> None:
        """Record one TX/RX entry as ``{"dir","hex","ozet"[,"text"]}``.

        ``data`` is either a raw S2C-MSG frame (protocol traffic) or a plain
        byte string (e.g. a manual console write via ``write_raw`` that never
        goes through the FrameParser). Frame bytes decode to a catalog-based
        summary via ``decode_frame_summary``; anything else falls back to a
        printable text summary so manual console input still shows up.

        When every frame in ``data`` is an unsolicited TRACE_EVENT/
        BUS_TRACE_EVENT frame, the entry also carries ``text``: the decoded
        ``S2C-LOG|D|TRACE|...`` line(s) (``s2cmsg.unpack_trace``). The Seri
        Hat panel's bit-level bus-waveform view parses that text the same way
        it always has — the binary migration changed the wire format, not
        the trace text the agent emits, so this is the ingestion point that
        feeds the waveform from the new traffic stream.
        """
        if not data:
            return
        frames = s2cmsg.FrameParser().feed(data)
        consumed = sum(s2cmsg.HEADER_SIZE + len(body) for _cid, _ctr, body in frames)
        entry: dict = {
            "seq": 0,
            "at": time.time(),
            "dir": direction,
            "hex": data[:64].hex().upper(),
        }
        if frames and consumed == len(data):
            # The whole payload parsed as one or more well-formed frames
            # (the only bytes we ever push here are exact pack_frame() output
            # or plain text) — no leftover/garbage bytes.
            entry["ozet"] = "; ".join(s2cmsg.decode_frame_summary(frame) for frame in frames)
            if all(s2cmsg.is_unsolicited(frame[0]) for frame in frames):
                text = "\n".join(s2cmsg.unpack_trace(frame)["text"] for frame in frames)
                if text:
                    entry["text"] = text
        else:
            entry["ozet"] = data.decode("ascii", errors="replace").strip() or "(bos)"
        with self._traffic_lock:
            self._traffic_seq += 1
            entry["seq"] = self._traffic_seq
            self._traffic.append(entry)

    def traffic_since(self, since_seq: int) -> tuple[int, list[dict]]:
        with self._traffic_lock:
            entries = [entry for entry in self._traffic if entry["seq"] > since_seq]
            return self._traffic_seq, entries


class _TestbenchTcpSession(_TrafficRing):
    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id
        self.host = ""
        self.port = 0
        self.timeout_s = 5.0
        self.connected_at: float | None = None
        self.last_used_at: float | None = None
        self.last_error = ""
        self._sock: socket.socket | None = None
        self._lock = threading.RLock()
        # Kismi/gec gelen yanit cerceveleri: timeout sonrasi gelen bayat
        # yanitlar burada birikir ve bir sonraki gonderimde ayiklanir.
        self._parser = s2cmsg.FrameParser()
        self._pending_frames: collections.deque[tuple[int, int, bytes]] = collections.deque()

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
        self._parser = s2cmsg.FrameParser()
        self._pending_frames.clear()
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

    def _pop_frame(self) -> tuple[int, int, bytes] | None:
        if not self._pending_frames:
            return None
        return self._pending_frames.popleft()

    def _handle_incoming(self, chunk: bytes) -> None:
        """Feed ``chunk`` into the frame parser; route unsolicited traces to traffic."""
        for frame in self._parser.feed(chunk):
            self._traffic_push("rx", s2cmsg.pack_frame(frame[0], frame[1], frame[2]))
            if s2cmsg.is_unsolicited(frame[0]):
                continue  # TRACE_EVENT/BUS_TRACE_EVENT: traffic ring only (no response queue)
            self._pending_frames.append(frame)

    def _drain_stale(self, sock: socket.socket) -> None:
        """Önceki timeout'lardan arta kalan geç yanıtları gönderim öncesi ayıkla."""
        try:
            sock.settimeout(0.0)
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                self._handle_incoming(chunk)
        except (BlockingIOError, InterruptedError, socket.timeout):
            pass
        finally:
            sock.settimeout(self.timeout_s)

    def _send_and_await_response(self, request: bytes, expected_counter: int) -> tuple[int, int, bytes]:
        """Istegi yolla, sayaci eslesen yanit cercevesini bekle, dondur.

        Yanit govdesinin ILK 4 baytinin (little-endian u32) istek sayaciyla
        eslesip eslesmedigine bakar — hem standart yanit govdesi
        (uiIstekSayac ilk alan) hem de CIT govdesi (ayni onek) icin dogru
        calisir; her iki cagiran da bu ortak sozlesmeye dayanir. Sayac=0
        govde, ajanin parse-hatasi konvansiyonudur — eslesen yanit gelmezse
        yedek olarak dondurulur.
        """
        with self._lock:
            if self._sock is None:
                raise TestbenchSessionError("testbench tcp session is not connected")
            sock = self._sock
            self._drain_stale(sock)
            self._traffic_push("tx", request)
            try:
                sock.sendall(request)
            except OSError as exc:
                self.last_error = str(exc)
                self.close()
                raise
            # Yaniti sayac ile eslestir: onceki, timeout'a ugramis bir komutun
            # GEC gelen yaniti bu komutun sonucu sanilmamali. Sure dolunca
            # oturumu KAPATMADAN hata ver — ajan mesgulken baglanti kaybi
            # yasanmasin, gec yanit bir sonraki gonderimde ayiklanir.
            deadline = time.time() + self.timeout_s
            fallback_frame: tuple[int, int, bytes] | None = None
            response_frame: tuple[int, int, bytes] | None = None
            try:
                while response_frame is None:
                    frame = self._pop_frame()
                    if frame is not None:
                        command_id, _counter, body = frame
                        if not s2cmsg.is_response(command_id):
                            continue  # istek yansiması değil, gerçek yanıt bekleniyor
                        candidate_counter = struct.unpack_from("<I", body, 0)[0] if len(body) >= 4 else -1
                        if candidate_counter == expected_counter:
                            response_frame = frame
                        elif candidate_counter == 0:
                            fallback_frame = frame
                        continue
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        break
                    sock.settimeout(max(0.05, remaining))
                    try:
                        chunk = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not chunk:
                        raise OSError("testbench tcp connection closed before response")
                    self._handle_incoming(chunk)
            except socket.timeout:
                pass
            except OSError as exc:
                self.last_error = str(exc)
                self.close()
                raise
            finally:
                try:
                    sock.settimeout(self.timeout_s)
                except OSError:
                    pass
            if response_frame is None:
                response_frame = fallback_frame
            if response_frame is None:
                self.last_error = f"no matching response within {self.timeout_s}s"
                raise TestbenchSessionError(
                    f"testbench tcp response timeout after {self.timeout_s}s "
                    "(oturum acik kaldi; ajan mesgul olabilir)")
            self.last_used_at = time.time()
            self.last_error = ""
            return response_frame

    def send(self, command: TestbenchCommand) -> TestbenchResult:
        session_command = TestbenchCommand(
            host=self.host,
            port=self.port,
            device=command.device,
            operation=command.operation,
            command_id=command.command_id,
            device_index=command.device_index,
            register=command.register,
            register_address=command.register_address,
            address=command.address,
            length=command.length,
            value=command.value,
            data_hex=command.data_hex,
            timeout_s=self.timeout_s,
        )
        request = _pack_command(session_command)
        response_frame = self._send_and_await_response(request, int(session_command.command_id))
        return TestbenchResult(
            request_line=_request_frame_summary(session_command, request),
            response_line=s2cmsg.decode_frame_summary(response_frame),
            parsed=s2cmsg.unpack_response(response_frame),
        )

    def send_named(self, name: str, counter: int, timeout_s: float) -> tuple[dict, bytes]:
        """Op'suz katalog mesaji (CIT_RUN/CIT_READ) gonderir; onegi + ham govdeyi dondurur.

        Donus: ({"istek_sayac": int, "durum": int}, ham_govde) — ham_govde
        SYanitOnek'ten SONRAKI baytlardir (CIT icin SBoardCit). CIT govdesi
        standart response layout'una (unpack_response) UYMADIGINDAN burada
        elle parse edilir.
        """
        with self._lock:
            if self._sock is None:
                raise TestbenchSessionError("testbench tcp session is not connected")
        original_timeout = self.timeout_s
        self.timeout_s = max(0.2, float(timeout_s))
        try:
            request = s2cmsg.pack_named_request(name, counter)
            response_frame = self._send_and_await_response(request, counter)
        finally:
            self.timeout_s = original_timeout
        _command_id, _resp_counter, body = response_frame
        if len(body) < 8:
            raise TestbenchSessionError(f"testbench response body too short for {name}")
        istek_sayac, durum = struct.unpack_from("<II", body, 0)
        return {"istek_sayac": istek_sayac, "durum": durum}, body[8:]


class _TestbenchSerialSession(_TrafficRing):
    """Persistent serial (COM) session for the UART test bench agent.

    A reader thread feeds every incoming chunk into a single-buffer
    ``s2cmsg.ConsoleFrameSplitter``: plain text lands in a bounded console
    ring (for the UART console UI) while binary S2C-MSG frames are decoded
    directly and, once decoded, response frames are queued for ``send()``.
    Because the splitter keeps one running buffer per session (rather than
    scanning each ``read()`` chunk in isolation), a frame signature or body
    split across chunk boundaries is still recovered correctly. Console
    noise between responses is therefore harmless even when the agent shares
    the console UART with xil_printf output.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__()
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
        self._responses: "queue.Queue[tuple[int, int, bytes]]" = queue.Queue()
        self._console: collections.deque[dict] = collections.deque(maxlen=SERIAL_CONSOLE_MAX_LINES)
        self._console_seq = 0
        self._splitter = s2cmsg.ConsoleFrameSplitter()
        self._console_buffer = bytearray()

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
        # Baglanti kapanirken bekletilen kuyruk (chunk sinirinda kalmis
        # tamamlanmamis bir cerceve/console kuyrugu) kaybolmasin diye
        # console'a dusuruluyor.
        leftover = self._splitter.flush()
        if leftover:
            self._console_buffer.extend(leftover)
        self._flush_console_lines(force=True)
        self._splitter = s2cmsg.ConsoleFrameSplitter()
        self._console_buffer = bytearray()
        if handle is not None:
            try:
                handle.close()
            except OSError:
                pass

    def _console_push(self, line: str) -> None:
        with self._lock:
            self._console_seq += 1
            self._console.append({"seq": self._console_seq, "at": time.time(), "line": line})

    def _flush_console_lines(self, *, force: bool = False) -> None:
        """Pop complete ``\\n``-terminated lines out of the console byte buffer.

        ``force`` also flushes a trailing partial line (used when the reader
        is about to hand the same bytes to the frame parser instead, so
        nothing is silently dropped between the two paths).
        """
        while True:
            index = self._console_buffer.find(b"\n")
            if index < 0:
                break
            raw = bytes(self._console_buffer[:index])
            del self._console_buffer[: index + 1]
            line = raw.decode("ascii", errors="replace").rstrip("\r")
            if line:
                self._console_push(line)
        if force and self._console_buffer:
            line = bytes(self._console_buffer).decode("ascii", errors="replace").rstrip("\r")
            self._console_buffer.clear()
            if line:
                self._console_push(line)

    def _handle_frame(self, frame: tuple[int, int, bytes]) -> None:
        command_id, _counter, _body = frame
        self._traffic_push("rx", s2cmsg.pack_frame(*frame))
        if s2cmsg.is_unsolicited(command_id):
            trace = s2cmsg.unpack_trace(frame)
            self._console_push(trace["text"])
            return
        if s2cmsg.is_response(command_id):
            self._responses.put(frame)

    def _reader_loop(self) -> None:
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
            console_bytes, frames = self._splitter.feed(chunk)
            if console_bytes:
                # Plain console/boot-log noise (xil_printf on a shared UART),
                # possibly interleaved with a frame in the same read() burst.
                # Still recorded on the Veri Akisi ring (text fallback ozet)
                # so the live traffic view shows the full conversation. The
                # splitter keeps a single running buffer, so a signature or
                # body split across chunk boundaries is recovered instead of
                # being misrouted here.
                self._console_buffer.extend(console_bytes)
                self._flush_console_lines()
                self._traffic_push("rx", console_bytes)
            for frame in frames:
                self._handle_frame(frame)

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
            payload_bytes = payload.encode("ascii", errors="replace")
            try:
                handle.write(payload_bytes)
                handle.flush()
            except OSError as exc:
                self.last_error = str(exc)
                self.close()
                raise
            self._traffic_push("tx", payload_bytes)
            self.last_used_at = time.time()

    def _write_and_await_response(self, request: bytes, expected_counter: int) -> tuple[int, int, bytes]:
        """Istegi yolla, sayaci eslesen yanit cercevesini bekle, dondur.

        Yanit govdesinin ILK 4 baytini (little-endian u32) sayac olarak okur
        — hem standart yanit govdesi hem CIT govdesi bu ortak onegi paylasir,
        bu yuzden ``send()`` ve ``send_named()`` bu tek helper'i kullanabilir.
        """
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
                    handle.write(request)
                    handle.flush()
                except OSError as exc:
                    self.last_error = str(exc)
                    self.close()
                    raise
                self._traffic_push("tx", request)
            # Wait outside the state lock so the reader thread and console
            # polling stay live while we block on the response. The channel
            # can be shared (console UART, a second jtagterminal client), so
            # match the response by counter; a non-matching response is kept
            # as a fallback so agents that answer with counter=0 (e.g. on
            # parse errors) still surface their message instead of a bare
            # timeout.
            deadline = time.time() + self.timeout_s
            fallback_frame: tuple[int, int, bytes] | None = None
            response_frame: tuple[int, int, bytes] | None = None
            while response_frame is None:
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                try:
                    candidate = self._responses.get(timeout=remaining)
                except queue.Empty:
                    break
                _cid, _counter, candidate_body = candidate
                candidate_counter = struct.unpack_from("<I", candidate_body, 0)[0] if len(candidate_body) >= 4 else -1
                if candidate_counter == expected_counter:
                    response_frame = candidate
                elif candidate_counter == 0:
                    # counter=0 is the agent's parse-error convention; surface
                    # it instead of a bare timeout.
                    fallback_frame = candidate
                # Any other counter is the LATE answer of an earlier,
                # timed-out command. Returning it as this command's result
                # was wrong (the UI showed command A's data under command
                # B); drop it — the traffic ring already recorded the frame.
            if response_frame is None:
                response_frame = fallback_frame
            if response_frame is None:
                with self._lock:
                    self.last_error = f"no response within {self.timeout_s}s"
                raise TestbenchSessionError(
                    f"testbench serial response timeout after {self.timeout_s}s")
        with self._lock:
            self.last_used_at = time.time()
            self.last_error = ""
        return response_frame

    def send(self, command: TestbenchCommand) -> TestbenchResult:
        request = _pack_command(command)
        response_frame = self._write_and_await_response(request, int(command.command_id))
        return TestbenchResult(
            request_line=_request_frame_summary(command, request),
            response_line=s2cmsg.decode_frame_summary(response_frame),
            parsed=s2cmsg.unpack_response(response_frame),
        )

    def send_named(self, name: str, counter: int, timeout_s: float) -> tuple[dict, bytes]:
        """Op'suz katalog mesaji (CIT_RUN/CIT_READ) gonderir; onegi + ham govdeyi dondurur."""
        with self._lock:
            if self._serial is None:
                raise TestbenchSessionError("testbench serial session is not connected")
        original_timeout = self.timeout_s
        self.timeout_s = max(0.2, float(timeout_s))
        try:
            request = s2cmsg.pack_named_request(name, counter)
            response_frame = self._write_and_await_response(request, counter)
        finally:
            self.timeout_s = original_timeout
        _command_id, _resp_counter, body = response_frame
        if len(body) < 8:
            raise TestbenchSessionError(f"testbench response body too short for {name}")
        istek_sayac, durum = struct.unpack_from("<II", body, 0)
        return {"istek_sayac": istek_sayac, "durum": durum}, body[8:]


class _TcpBridgeStream:
    """Minimal file-like byte stream over a TCP socket.

    Speaks the same contract as a pyserial handle with a short read
    timeout: ``read()`` returns b"" when no data is available yet and
    raises OSError when the peer goes away. Used for the CoreSight
    jtagterminal bridge so the coresight transport needs no pyserial at
    all (pyserial's dynamic ``socket://`` URL handler is exactly what
    PyInstaller-packaged builds fail to bundle).
    """

    def __init__(self, host: str, port: int, connect_timeout_s: float) -> None:
        self._sock = socket.create_connection((host, port), timeout=max(1.0, connect_timeout_s))
        self._sock.settimeout(0.2)

    def read(self, size: int) -> bytes:
        try:
            data = self._sock.recv(size)
        except socket.timeout:
            return b""
        if not data:
            raise OSError("coresight bridge socket closed")
        return data

    def write(self, data: bytes) -> int:
        self._sock.sendall(data)
        return len(data)

    def flush(self) -> None:
        pass

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass


class _TestbenchCoresightSession(_TestbenchSerialSession):
    """CoreSight DCC session bridged through xsdb ``jtagterminal -socket``.

    xsdb connects to hw_server (local USB JTAG or a SmartLynq's built-in
    server via ``-url``), selects the target core and opens a local TCP
    socket that carries the Arm DCC byte stream. We then reuse the whole
    serial-session machinery (reader thread, console ring, traffic ring,
    response queue) over a plain socket stream — so the UART console,
    Veri Akisi and S2C commands all work unchanged over JTAG.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)
        self.vitis_path = ""
        self.hw_server_url = ""
        self.processor = "psu_cortexa53_0"
        self.dcc_port = 0
        self._xsdb_proc: subprocess.Popen | None = None

    def status(self) -> TestbenchSessionStatus:
        status = super().status()
        status.transport = "coresight"
        status.processor = self.processor
        status.hw_server_url = self.hw_server_url
        status.dcc_port = self.dcc_port
        return status

    def connect_coresight(
        self,
        vitis_path: str,
        hw_server_url: str,
        processor: str,
        timeout_s: float,
        *,
        bridge_factory=None,
    ) -> TestbenchSessionStatus:
        """Spawn the xsdb bridge, wait for its port, then attach the serial machinery.

        ``bridge_factory(vitis_path, hw_server_url, processor)`` -> (proc|None, port)
        lets tests substitute a fake bridge without a Vitis install.
        """
        from backend.run_on_board import _core_filter, locate_xsdb, normalize_hw_server_url

        self.vitis_path = vitis_path
        self.hw_server_url = normalize_hw_server_url(hw_server_url)
        self.processor = processor.strip() or "psu_cortexa53_0"
        if bridge_factory is not None:
            proc, port = bridge_factory(vitis_path, self.hw_server_url, self.processor)
        else:
            proc, port = self._spawn_bridge(locate_xsdb(vitis_path), _core_filter(self.processor))
        try:
            self.connect(
                f"dcc://127.0.0.1:{port}", 115200, timeout_s,
                serial_factory=lambda _port, _baud, _timeout: _TcpBridgeStream(
                    "127.0.0.1", port, timeout_s))
        except Exception:
            if proc is not None:
                proc.kill()
            raise
        # Assign after connect(): serial connect() calls close(), which would
        # otherwise kill the bridge we just started.
        self.dcc_port = port
        self._xsdb_proc = proc
        return self.status()

    def _spawn_bridge(self, xsdb: Path, core_filter: str) -> tuple[subprocess.Popen, int]:
        connect_cmd = f"connect -url {self.hw_server_url}" if self.hw_server_url else "connect"
        script = "\n".join([
            "catch {fconfigure stdout -buffering line}",
            connect_cmd,
            f"targets -set -nocase -filter {{name =~ {core_filter}}}",
            "set iDccPort [jtagterminal -socket]",
            'puts "S2C-DCC-PORT=$iDccPort"',
            "vwait forever",
            "",
        ])
        script_path = Path(tempfile.mkstemp(prefix="s2c_dcc_", suffix=".tcl")[1])
        script_path.write_text(script, encoding="utf-8")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.Popen(
            [str(xsdb), str(script_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=creationflags,
        )
        port_queue: "queue.Queue[int]" = queue.Queue()
        tail: collections.deque[str] = collections.deque(maxlen=15)

        def _scan_stdout() -> None:
            stream = proc.stdout
            if stream is None:
                return
            for line in stream:
                text = line.strip()
                if text:
                    tail.append(text)
                if text.startswith("S2C-DCC-PORT="):
                    try:
                        port_queue.put(int(text.split("=", 1)[1]))
                    except ValueError:
                        pass

        threading.Thread(target=_scan_stdout, name=f"s2c-dcc-{self.session_id}", daemon=True).start()
        try:
            port = port_queue.get(timeout=CORESIGHT_BRIDGE_TIMEOUT_S)
        except queue.Empty:
            proc.kill()
            detail = "\n".join(tail)
            self.last_error = f"jtagterminal koprusu acilamadi: {detail}" if detail else \
                "jtagterminal koprusu acilamadi (xsdb port bildirmedi)"
            raise TestbenchSessionError(
                "CoreSight koprusu kurulamadi: xsdb jtagterminal portu bildirmedi. "
                "Kartin acik, JTAG kablosunun (USB/SmartLynq) bagli ve uygulamanin "
                "yuklu oldugundan emin olun."
                + (f"\nxsdb ciktisi:\n{detail}" if detail else ""))
        return proc, port

    def close(self) -> None:
        super().close()
        proc = self._xsdb_proc
        self._xsdb_proc = None
        if proc is not None:
            try:
                if os.name == "nt":
                    # xsdb.bat bir surec agaci kurar (cmd -> tclsh); yalniz
                    # ust sureci oldurmek jtagterminal'i yetim birakabilir.
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        capture_output=True, check=False)
                else:
                    proc.kill()
            except OSError:
                pass


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
        self._named_counter = 0

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

    def connect_coresight(
        self,
        session_id: str,
        vitis_path: str,
        hw_server_url: str,
        processor: str,
        timeout_s: float,
        *,
        bridge_factory=None,
    ) -> TestbenchSessionStatus:
        session = _TestbenchCoresightSession(self._clean_session_id(session_id))
        self._replace_session(session_id, session)
        return session.connect_coresight(
            vitis_path, hw_server_url, processor, timeout_s, bridge_factory=bridge_factory)

    def _serial_session(self, session_id: str) -> _TestbenchSerialSession:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
        if not isinstance(session, _TestbenchSerialSession):
            raise TestbenchSessionError("testbench serial session is not connected")
        return session

    def console(self, session_id: str, since_seq: int) -> tuple[int, list[dict]]:
        return self._serial_session(session_id).console_since(int(since_seq))

    def traffic(self, session_id: str, since_seq: int) -> tuple[int, list[dict]]:
        clean_id = self._clean_session_id(session_id)
        with self._lock:
            session = self._sessions.get(clean_id)
        if session is None:
            raise TestbenchSessionError("testbench session not found")
        return session.traffic_since(int(since_seq))

    def list_sessions(self) -> list[TestbenchSessionStatus]:
        with self._lock:
            sessions = list(self._sessions.values())
        return sorted((session.status() for session in sessions), key=lambda item: item.session_id)

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

    def _next_named_counter(self) -> int:
        with self._lock:
            self._named_counter += 1
            return self._named_counter

    def send_named(self, session_id: str, name: str, timeout_s: float = 10.0) -> tuple[dict, bytes]:
        """Op'suz katalog mesaji (PING/VERSION/CIT_RUN/CIT_READ) gonderir.

        Donus: (onek sozlugu {"istek_sayac","durum"}, ham CIT/govde baytlari).
        CIT yaniti standart response layout'undan farkli oldugundan
        (bkz. backend/cit.py) burada s2cmsg.unpack_response KULLANILMAZ —
        cagiran taraf ham baytlari kendi coder'ina (decode_board_cit) verir.
        """
        session = self._session(session_id)
        counter = self._next_named_counter()
        return session.send_named(name, counter, timeout_s=timeout_s)


testbench_sessions = TestbenchSessionManager()
