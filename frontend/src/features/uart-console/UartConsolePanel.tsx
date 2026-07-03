import { useEffect, useRef, useState } from "react";
import { ArrowDownToLine, Cable, Eraser, Link2, Loader2, SendHorizonal, Unplug } from "lucide-react";
import { Badge, Button, Card, Input } from "@/components/ui";
import { api } from "@/lib/api";
import { downloadTextLog, stripAnsi, timeLabel } from "@/lib/console";
import { cn } from "@/lib/utils";
import { useBoardConnection } from "@/store/connection";
import type { SerialConsoleEntry } from "@/lib/types";

const POLL_MS = 500;

function lineTone(line: string): string {
  if (line.startsWith("S2C|") || line.startsWith("S2C-LOG|")) return "text-bus-uart";
  if (/error|fail|hata|basarisiz/i.test(line)) return "text-danger";
  if (/ready|listening|running|basari|ok\b/i.test(line)) return "text-ok";
  return "text-text";
}

/** Karttan gelen satırları canlı gösteren konsol. Bağlantı, tüm ekranların
 * paylaştığı tek kart bağlantısıdır (seri veya CoreSight DCC); TCP'de konsol
 * kanalı yoktur. */
export default function UartConsolePanel() {
  const board = useBoardConnection();
  const [entries, setEntries] = useState<SerialConsoleEntry[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const sinceRef = useRef(0);
  const logRef = useRef<HTMLDivElement | null>(null);

  const consoleAvailable = board.connected && board.transport !== "tcp";

  // Yeni session/bağlantıda akışı baştan al.
  useEffect(() => {
    sinceRef.current = 0;
    setEntries([]);
    setError("");
  }, [board.sessionId, board.connected]);

  // RX polling loop while the shared connection is up.
  useEffect(() => {
    if (!consoleAvailable) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const { seq, entries: fresh } = await api.testbenchConsoleRead(board.sessionId, sinceRef.current);
        if (cancelled) return;
        sinceRef.current = seq;
        setError("");
        if (fresh.length > 0) {
          setEntries((current) => [...current, ...fresh].slice(-2000));
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [consoleAvailable, board.sessionId]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  async function sendLine() {
    // Boş satıra da izin var: çıplak Enter, agent'ın "> " canlılık istemini
    // tetikler (çakılma/takılma kontrolü).
    if (!consoleAvailable) return;
    const text = input;
    setInput("");
    try {
      await api.testbenchConsoleWrite(board.sessionId, text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <Card className="flex h-full min-h-0 flex-col p-0">
      <div className="flex flex-wrap items-center gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Cable className="h-4 w-4 text-bus-uart" aria-hidden />
          <span className="text-sm font-semibold text-text">Konsol</span>
          <Badge tone={board.connected ? "ok" : "neutral"}>
            {board.connected
              ? board.transport === "serial"
                ? `seri ${board.serialPort}`
                : board.transport === "coresight"
                  ? "CoreSight DCC"
                  : "TCP (konsol yok)"
              : "kopuk"}
          </Badge>
        </div>
        <p className="min-w-0 flex-1 truncate text-[11px] text-faint">
          Bağlantı ortak karttan yönetilir (Test Bench ekranındaki bağlantı kartı).
        </p>
        <div className="flex gap-2">
          {board.connected ? (
            <Button size="sm" variant="outline" onClick={() => void board.disconnect()} disabled={board.busy}>
              <Unplug className="h-4 w-4" aria-hidden /> Kes
            </Button>
          ) : (
            <Button size="sm" onClick={() => void board.connect()} disabled={board.busy} title="Kayıtlı bağlantı ayarlarıyla bağlan">
              {board.busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Link2 className="h-4 w-4" aria-hidden />}
              Bağlan
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setEntries([])} title="Ekranı temizle">
            <Eraser className="h-4 w-4" aria-hidden />
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => downloadTextLog("uart_console", entries.map((entry) => `${timeLabel(entry.at)}  ${stripAnsi(entry.line)}`).join("\n"))}
            disabled={entries.length === 0}
            title="Logu indir"
          >
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
      {board.connected && board.transport === "tcp" ? (
        <p className="mx-4 mt-2 rounded border border-warn/30 bg-warn/10 px-2 py-1.5 text-[11px] text-warn">
          TCP bağlantısında konsol kanalı yok; boot çıktısı ve S2C-LOG satırları için seri veya CoreSight bağlantısı kullan.
        </p>
      ) : null}

      <div
        ref={logRef}
        className="min-h-0 flex-1 overflow-auto bg-bg px-4 py-2 font-mono text-[12px] leading-relaxed"
      >
        {entries.length === 0 ? (
          <p className="mt-6 text-center text-xs text-faint">
            {consoleAvailable
              ? "Veri bekleniyor... Kart resetlendiğinde boot çıktısı burada akacak."
              : "Ortak bağlantı kartından seri veya CoreSight ile bağlanınca karttan gelen her satır burada listelenir."}
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
          placeholder={consoleAvailable ? "Karta gönderilecek satır — boş Enter '>' canlılık istemi döndürür" : "Önce seri/CoreSight ile bağlan"}
          disabled={!consoleAvailable}
          className="font-mono text-xs"
        />
        <Button type="submit" size="sm" disabled={!consoleAvailable}>
          <SendHorizonal className="h-4 w-4" aria-hidden /> Gönder
        </Button>
      </form>
    </Card>
  );
}
