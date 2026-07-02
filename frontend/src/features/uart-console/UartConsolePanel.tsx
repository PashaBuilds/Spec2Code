import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowDownToLine, Cable, Eraser, Link2, Loader2, SendHorizonal, Unplug } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SerialConsoleEntry, SerialPortInfo } from "@/lib/types";

const POLL_MS = 500;
const BAUD_CHOICES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"];

/* eslint-disable-next-line no-control-regex */
const ANSI_RE = new RegExp("\\[[0-9;]*[A-Za-z]", "g");

function stripAnsi(line: string): string {
  return line.replace(ANSI_RE, "");
}

function timeLabel(at: number): string {
  const date = new Date(at * 1000);
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");
  const ms = String(date.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

function lineTone(line: string): string {
  if (line.startsWith("S2C|")) return "text-bus-uart";
  if (/error|fail|hata|basarisiz/i.test(line)) return "text-danger";
  if (/ready|listening|running|basari|ok\b/i.test(line)) return "text-ok";
  return "text-text";
}

function makeSessionId(): string {
  const globalCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return `uc_${globalCrypto.randomUUID()}`;
  }
  return `uc_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

export default function UartConsolePanel() {
  const [sessionId] = useState(makeSessionId);
  const [ports, setPorts] = useState<SerialPortInfo[]>([]);
  const [serialPort, setSerialPort] = useState(() => localStorage.getItem("spec2code.uartconsole.port") ?? "");
  const [baud, setBaud] = useState(() => localStorage.getItem("spec2code.uartconsole.baud") ?? "115200");
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [entries, setEntries] = useState<SerialConsoleEntry[]>([]);
  const [input, setInput] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const sinceRef = useRef(0);
  const logRef = useRef<HTMLDivElement | null>(null);

  const refreshPorts = async () => {
    try {
      const list = await api.testbenchSerialPorts();
      setPorts(list);
      if (!serialPort && list.length > 0) setSerialPort(list[0].device);
    } catch {
      setPorts([]);
    }
  };

  useEffect(() => {
    void refreshPorts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    return () => {
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
    };
  }, [sessionId]);

  // RX polling loop while connected.
  useEffect(() => {
    if (!connected) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const { seq, entries: fresh } = await api.testbenchConsoleRead(sessionId, sinceRef.current);
        if (cancelled) return;
        sinceRef.current = seq;
        if (fresh.length > 0) {
          setEntries((current) => [...current, ...fresh].slice(-2000));
        }
      } catch (err) {
        if (cancelled) return;
        setConnected(false);
        setError(err instanceof Error ? err.message : String(err));
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [connected, sessionId]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  async function connect() {
    if (busy || connected) return;
    if (!serialPort.trim()) {
      setError("Seri port seç (ör. COM4).");
      return;
    }
    localStorage.setItem("spec2code.uartconsole.port", serialPort.trim());
    localStorage.setItem("spec2code.uartconsole.baud", baud.trim());
    setBusy(true);
    setError("");
    try {
      const status = await api.testbenchConnect({
        session_id: sessionId,
        transport: "serial",
        serial_port: serialPort.trim(),
        baud: Number.parseInt(baud, 10) || 115200,
        timeout_s: 5,
      });
      sinceRef.current = 0;
      setConnected(Boolean(status.connected));
      if (!status.connected) setError(status.last_error || "Seri bağlantı kurulamadı.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    if (busy) return;
    setBusy(true);
    try {
      await api.testbenchDisconnect(sessionId);
    } catch {
      /* already broken */
    } finally {
      setConnected(false);
      setBusy(false);
    }
  }

  async function sendLine() {
    const text = input;
    if (!connected || !text.trim()) return;
    setInput("");
    try {
      await api.testbenchConsoleWrite(sessionId, text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function downloadLog() {
    const body = entries.map((entry) => `${timeLabel(entry.at)}  ${stripAnsi(entry.line)}`).join("\n");
    const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `uart_console_${new Date().toISOString().replace(/[:.]/g, "-")}.log`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const portLabel = useMemo(() => {
    const info = ports.find((item) => item.device === serialPort);
    return info?.description ? `${info.device} — ${info.description}` : serialPort;
  }, [ports, serialPort]);

  return (
    <Card className="flex h-full min-h-0 flex-col p-0">
      <div className="flex flex-wrap items-end gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Cable className="h-4 w-4 text-bus-uart" aria-hidden />
          <span className="text-sm font-semibold text-text">UART konsolu</span>
          <Badge tone={connected ? "ok" : "neutral"}>{connected ? "bağlı" : "kopuk"}</Badge>
        </div>
        <div className="min-w-52">
          <Label>Seri port</Label>
          <div className="flex gap-1">
            <select
              value={serialPort}
              onChange={(event) => setSerialPort(event.target.value)}
              disabled={connected || busy}
              className="h-9 w-full min-w-0 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
              title={portLabel}
            >
              {serialPort && !ports.some((p) => p.device === serialPort) ? (
                <option value={serialPort}>{serialPort}</option>
              ) : null}
              {ports.length === 0 && !serialPort ? <option value="">port bulunamadı</option> : null}
              {ports.map((info) => (
                <option key={info.device} value={info.device} title={info.description}>
                  {info.device}
                </option>
              ))}
            </select>
            <Button size="sm" variant="outline" onClick={() => void refreshPorts()} disabled={connected || busy} title="Portları yenile">
              ⟳
            </Button>
          </div>
        </div>
        <div className="w-28">
          <Label>Baud</Label>
          <select
            value={baud}
            onChange={(event) => setBaud(event.target.value)}
            disabled={connected || busy}
            className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            {!BAUD_CHOICES.includes(baud) ? <option value={baud}>{baud}</option> : null}
            {BAUD_CHOICES.map((choice) => (
              <option key={choice} value={choice}>{choice}</option>
            ))}
          </select>
        </div>
        <div className="flex gap-2">
          {connected ? (
            <Button size="sm" variant="outline" onClick={() => void disconnect()} disabled={busy}>
              <Unplug className="h-4 w-4" aria-hidden /> Kes
            </Button>
          ) : (
            <Button size="sm" onClick={() => void connect()} disabled={busy}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Link2 className="h-4 w-4" aria-hidden />}
              Bağlan
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setEntries([])} title="Ekranı temizle">
            <Eraser className="h-4 w-4" aria-hidden />
          </Button>
          <Button size="sm" variant="outline" onClick={downloadLog} disabled={entries.length === 0} title="Logu indir">
            <ArrowDownToLine className="h-4 w-4" aria-hidden />
          </Button>
          <label className="flex items-center gap-1.5 text-[11px] text-muted">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(event) => setAutoScroll(event.target.checked)}
              className="accent-[var(--accent)]"
            />
            oto-kaydır
          </label>
        </div>
      </div>

      {error ? (
        <p className="mx-4 mt-2 rounded border border-danger/30 bg-danger/10 px-2 py-1.5 font-mono text-[11px] text-danger">
          {error}
        </p>
      ) : null}

      <div
        ref={logRef}
        className="min-h-0 flex-1 overflow-auto bg-bg px-4 py-2 font-mono text-[12px] leading-relaxed"
      >
        {entries.length === 0 ? (
          <p className="mt-6 text-center text-xs text-faint">
            {connected
              ? "Veri bekleniyor... Kart resetlendiğinde boot çıktısı burada akacak."
              : "Bağlan'a bastıktan sonra karttan gelen her satır zaman damgasıyla burada listelenir."}
          </p>
        ) : (
          entries.map((entry) => (
            <div key={entry.seq} className="grid grid-cols-[96px_minmax(0,1fr)] gap-2">
              <span className="select-none text-faint">{timeLabel(entry.at)}</span>
              <span className={cn("break-all", lineTone(stripAnsi(entry.line)))}>{stripAnsi(entry.line)}</span>
            </div>
          ))
        )}
      </div>

      <form
        className="flex items-center gap-2 border-t border-border px-4 py-2"
        onSubmit={(event) => {
          event.preventDefault();
          void sendLine();
        }}
      >
        <Input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder={connected ? "Karta gönderilecek satır (Enter ile gönder)" : "Önce bağlan"}
          disabled={!connected}
          className="font-mono text-xs"
        />
        <Button type="submit" size="sm" disabled={!connected || !input.trim()}>
          <SendHorizonal className="h-4 w-4" aria-hidden /> Gönder
        </Button>
      </form>
    </Card>
  );
}
