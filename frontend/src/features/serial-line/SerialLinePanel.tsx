import { useEffect, useMemo, useRef, useState } from "react";
import { AudioWaveform, Eraser, Pause, Play } from "lucide-react";
import { Badge, Button, Card, Label } from "@/components/ui";
import BusWaveform from "@/features/device-knowledge/BusWaveform";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import { api } from "@/lib/api";
import { stripAnsi, timeLabel } from "@/lib/console";
import { formatConvertedValue } from "@/lib/units";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { KnowledgeRegisterTransfer } from "@/features/device-knowledge/knowledge";
import type {
  TestbenchManifest,
  TestbenchManifestDevice,
  TestbenchOperation,
  TestbenchSessionStatus,
} from "@/lib/types";

const TRAFFIC_POLL_MS = 500;
const SESSIONS_POLL_MS = 2000;
const MAX_CARDS = 40;
const MAX_WAVES_PER_CARD = 3;

/** Manifest'teki bus transfer planı adımı (codegen _op_wire_plan üretir). */
interface WireStep {
  kind: string;
  reg?: string;
  addr?: number;
  value?: number;
  length?: number | null;
  count?: number;
  note?: string;
  repeat?: string;
  runtime?: boolean;
  cmd?: string;
  opcode?: number;
  addr_bytes?: number;
  first_word?: string;
}

/** S2C satırını key=value sözlüğüne çözer; S2C satırı değilse null. */
export function parseS2CLine(line: string): Record<string, string> | null {
  const text = stripAnsi(line).trim();
  if (!text.startsWith("S2C|")) return null;
  const parsed: Record<string, string> = {};
  for (const token of text.split("|").slice(1)) {
    const eq = token.indexOf("=");
    if (eq > 0) parsed[token.slice(0, eq).trim()] = token.slice(eq + 1).trim();
  }
  return parsed;
}

interface TransferCard {
  key: string;
  id: string;
  txAt: number;
  rxAt?: number;
  tx: Record<string, string>;
  txLine: string;
  rx?: Record<string, string>;
  rxLine?: string;
}

function hexByte(value: number): string {
  return `0x${(value & 0xff).toString(16).toUpperCase().padStart(2, "0")}`;
}

function hexAddr(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}

function dataBytes(dataHex: string): string[] {
  const clean = (dataHex || "").replace(/[^0-9a-fA-F]/g, "");
  const bytes: string[] = [];
  for (let i = 0; i + 2 <= clean.length; i += 2) bytes.push(`0x${clean.slice(i, i + 2).toUpperCase()}`);
  return bytes;
}

function parseNumberish(text: string | undefined): number | null {
  if (!text) return null;
  const parsed = Number.parseInt(text, text.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) ? parsed : null;
}

/** SPI TICS frame yerleşimi (UI gösterimi): LMK04832/ADAR1000 addr<<8 +
 * 8-bit veri, LMX ailesi addr<<16 + 16-bit veri — Bilgi ekranındaki
 * sözleşmenin aynısı. */
function spiFrameModel(part: string): { addrShift: number; dataBits: number } {
  const upper = part.toUpperCase();
  if (upper === "LMK04832" || upper === "ADAR1000") return { addrShift: 8, dataBits: 8 };
  return { addrShift: 16, dataBits: 16 };
}

function spiWordBytes(rw: 0 | 1, regAddr: number, data: number, addrShift: number): string[] {
  const word = ((rw << 23) | ((regAddr << addrShift) & 0x7fffff) | (data & ((1 << addrShift) - 1))) >>> 0;
  return [hexByte(word >> 16), hexByte(word >> 8), hexByte(word)];
}

function symbolic(count: number): string[] {
  if (count <= 1) return ["DATA"];
  if (count === 2) return ["MSB", "LSB"];
  return Array.from({ length: Math.min(count, 4) }, (_, i) => `D${count - 1 - i}`);
}

/** Kartın bus diyagramları: manifest'teki kablo planı gerçek adres/register
 * adlarıyla katalog transferlerine çevrilir. Ham (birimsiz) okumalarda yanıt
 * baytları diyagramdaki RX hücrelerine yazılır; dönüştürülmüş sonuçlarda
 * kablo baytları ajanda kaldığından hücreler MSB/LSB etiketiyle kalır ve
 * sonuç ayrıca "= değer" rozetinde gösterilir (uydurma bayt yok). */
function wireTransfers(
  card: TransferCard,
  device: TestbenchManifestDevice | null,
  operation: TestbenchOperation | null,
): Array<{ transfer: KnowledgeRegisterTransfer; title: string }> {
  if (!device) return [];
  const wire = (operation as { wire?: WireStep[] } | null)?.wire;
  if (!wire || wire.length === 0) return [];
  const isI2c = device.transport.startsWith("i2c");
  const rawFill = Boolean(card.rx) && (operation?.result_unit ?? "") === "";
  const rxAll = dataBytes(card.rx?.data ?? "");
  let rxCursor = 0;
  const takeRx = (count: number): string[] | null => {
    if (!rawFill) return null;
    const slice = rxAll.slice(rxCursor, rxCursor + count);
    rxCursor += count;
    return slice.length === count ? slice : null;
  };
  const spi = spiFrameModel(device.part);

  const out: Array<{ transfer: KnowledgeRegisterTransfer; title: string }> = [];
  for (const step of wire) {
    // Generic register_read/register_write: register çalışma zamanında
    // istekten gelir.
    const regAddr = step.runtime ? parseNumberish(card.tx.reg_addr) ?? 0 : step.addr ?? 0;
    const regName = step.runtime ? (card.tx.reg || card.tx.reg_addr || "REG") : step.reg ?? "REG";
    const regLabel = `${regName} (${hexAddr(regAddr)})`;
    const writeValue = step.runtime ? parseNumberish(card.tx.value) ?? 0 : step.value ?? 0;
    const pollNote = step.repeat === "poll" ? `${step.note ?? "hazır olana dek tekrarlanır"} (×N)` : step.note;

    if (step.kind === "reg_read") {
      const length = step.length ?? 1;
      const real = takeRx(length);
      out.push({
        title: `${regName} oku${step.repeat === "poll" ? " (poll)" : ""}`,
        transfer: isI2c
          ? {
              title: regLabel, access: "READ", txBytes: "1 byte", rxBytes: `${length} byte`,
              tx: [regLabel], rx: real ?? symbolic(length), code: [], note: pollNote,
            }
          : {
              title: regLabel, access: "READ", txBytes: "3 byte", rxBytes: `${spi.dataBits / 8} byte`,
              tx: spiWordBytes(1, regAddr, 0, spi.addrShift), rx: real ?? symbolic(spi.dataBits / 8),
              code: [], note: pollNote,
            },
      });
    } else if (step.kind === "reg_read_channels") {
      const count = step.count ?? 8;
      out.push({
        title: `${count} kanal oku (${regName}…)`,
        transfer: {
          title: regLabel, access: "READ",
          txBytes: `${count * 2} x 1 byte register pointer`,
          rxBytes: `${count * 2} byte toplam (${count} x MSB+LSB)`,
          tx: [`${regName} + 2n`, `${regName} + 2n + 1`],
          rx: ["MSB", "LSB"], code: [],
          note: `n = 0..${count - 1}; her kanal için MSB+LSB okunur`,
        },
      });
    } else if (step.kind === "reg_write") {
      out.push({
        title: `${regName} yaz`,
        transfer: isI2c
          ? {
              title: regLabel, access: "WRITE", txBytes: "2 byte", rxBytes: "0 byte",
              tx: [regLabel, hexByte(writeValue)], rx: ["-"], code: [], note: step.note,
            }
          : {
              title: regLabel, access: "WRITE", txBytes: "3 byte", rxBytes: "0 byte",
              tx: spiWordBytes(0, regAddr, writeValue, spi.addrShift), rx: ["-"], code: [], note: step.note,
            },
      });
    } else if (step.kind === "tics_init") {
      const first = parseNumberish(step.first_word) ?? 0;
      out.push({
        title: `TICS init dizisi (${step.count ?? 0} word)`,
        transfer: {
          title: "TICS Pro word", access: "WRITE",
          txBytes: `${step.count ?? 0} x 3 byte`, rxBytes: "0 byte",
          tx: [hexByte(first >> 16), hexByte(first >> 8), hexByte(first)], rx: ["-"], code: [],
          note: `${step.count ?? 0} word sırayla yazılır — ilki gösteriliyor`,
        },
      });
    } else if (step.kind === "cmd" || step.kind === "cmd_read" || step.kind === "cmd_write") {
      const opcode = step.opcode ?? 0;
      const addrBytes = step.addr_bytes ?? 0;
      const length = step.length ?? null;
      const isRead = step.kind === "cmd_read";
      const real = isRead && length ? takeRx(length) : null;
      out.push({
        title: `${step.cmd ?? "CMD"} (${hexByte(opcode)})`,
        transfer: {
          title: step.cmd ?? "CMD",
          access: isRead ? "READ" : "WRITE",
          txBytes: `${1 + addrBytes} byte${step.kind === "cmd_write" ? " + payload" : ""}`,
          rxBytes: isRead ? (length ? `${length} byte` : "N byte") : "0 byte",
          tx: [hexByte(opcode), ...(addrBytes ? [`ADDR[${addrBytes}]`] : [])],
          rx: isRead ? (real ?? symbolic(length ?? 2)) : ["-"],
          code: [], note: step.note,
        },
      });
    }
  }
  return out;
}

function transportLabel(status: TestbenchSessionStatus): string {
  if (status.transport === "serial") return `seri ${status.serial_port ?? ""}`.trim();
  if (status.transport === "coresight") return `CoreSight DCC (${status.processor ?? ""})`;
  return `TCP ${status.host}:${status.port}`;
}

/** Akış'ın kardeşi: her S2C komut/yanıt çifti id ile eşleştirilir ve
 * operasyonun BUS seviyesindeki transferleri katalogdaki zaman diyagramıyla
 * (gerçek register adresleri, init'te gerçek değerler) çizilir. */
export default function SerialLinePanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  const [sessions, setSessions] = useState<TestbenchSessionStatus[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [cards, setCards] = useState<TransferCard[]>([]);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");
  const sinceRef = useRef(0);
  const pendingRef = useRef<Map<string, string>>(new Map()); // id -> card key

  const selectedSession = useMemo(
    () => sessions.find((session) => session.session_id === sessionId) ?? null,
    [sessions, sessionId],
  );

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const list = await api.testbenchSessions();
        if (cancelled) return;
        setSessions(list);
        setSessionId((current) => {
          if (current && list.some((session) => session.session_id === current)) return current;
          const connected = list.find((session) => session.connected) ?? list[0];
          return connected?.session_id ?? "";
        });
      } catch {
        if (!cancelled) setSessions([]);
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), SESSIONS_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    sinceRef.current = 0;
    pendingRef.current.clear();
    setCards([]);
    setError("");
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || paused) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const { seq, entries } = await api.testbenchTraffic(sessionId, sinceRef.current);
        if (cancelled) return;
        sinceRef.current = seq;
        setError("");
        if (entries.length === 0) return;
        setCards((current) => {
          let next = current;
          for (const entry of entries) {
            const parsed = parseS2CLine(entry.line);
            if (!parsed || !parsed.id) continue;
            const isResponse = "ok" in parsed;
            if (!isResponse && parsed.op) {
              const key = `${entry.seq}`;
              pendingRef.current.set(parsed.id, key);
              next = [
                { key, id: parsed.id, txAt: entry.at, tx: parsed, txLine: stripAnsi(entry.line) },
                ...next,
              ].slice(0, MAX_CARDS);
            } else if (isResponse) {
              const key = pendingRef.current.get(parsed.id);
              if (!key) continue;
              pendingRef.current.delete(parsed.id);
              next = next.map((card) =>
                card.key === key
                  ? { ...card, rx: parsed, rxAt: entry.at, rxLine: stripAnsi(entry.line) }
                  : card,
              );
            }
          }
          return next;
        });
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      }
    }, TRAFFIC_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId, paused]);

  function deviceFor(card: TransferCard): TestbenchManifestDevice | null {
    return manifest?.devices.find((device) => device.id === card.tx.device) ?? null;
  }

  function operationFor(card: TransferCard, device: TestbenchManifestDevice | null): TestbenchOperation | null {
    return device?.operations.find((op) => op.name === card.tx.op) ?? null;
  }

  return (
    <Card className="flex h-full min-h-0 flex-col p-0">
      <div className="flex flex-wrap items-end gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <AudioWaveform className="h-4 w-4 text-accent" aria-hidden />
          <span className="text-sm font-semibold text-text">Seri Hat</span>
          <Badge tone={selectedSession?.connected ? "ok" : "neutral"}>
            {selectedSession ? transportLabel(selectedSession) : "session yok"}
          </Badge>
        </div>
        <div className="min-w-64">
          <Label>Session</Label>
          <select
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            className="h-9 w-full min-w-0 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            {sessions.length === 0 ? <option value="">aktif session yok</option> : null}
            {sessions.map((session) => (
              <option key={session.session_id} value={session.session_id}>
                {session.session_id.slice(0, 14)} — {transportLabel(session)}
                {session.connected ? "" : " (kopuk)"}
              </option>
            ))}
          </select>
        </div>
        <Badge tone="accent">{cards.length} transfer</Badge>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setPaused((current) => !current)} title={paused ? "Devam et" : "Duraklat"}>
            {paused ? <Play className="h-4 w-4" aria-hidden /> : <Pause className="h-4 w-4" aria-hidden />}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => {
              setCards([]);
              pendingRef.current.clear();
            }}
            title="Kartları temizle"
          >
            <Eraser className="h-4 w-4" aria-hidden />
          </Button>
        </div>
        <p className="w-full text-[11px] leading-relaxed text-faint">
          Her kart bir S2C komut/yanıt çiftidir (id eşleşmeli) ve operasyonun bus üzerindeki
          transferleri katalogdaki zaman diyagramıyla çizilir. Ham okumalarda yanıt baytları
          diyagrama işlenir; dönüştürülmüş sonuçlarda kablo baytları ajanda kaldığından hücreler
          MSB/LSB olarak kalır, sonuç "=" rozetinde gösterilir.
        </p>
      </div>

      {error ? (
        <p className="mx-4 mt-2 rounded border border-danger/30 bg-danger/10 px-2 py-1.5 font-mono text-[11px] text-danger">
          {error}
        </p>
      ) : null}

      <div className="min-h-0 flex-1 space-y-3 overflow-auto bg-bg px-4 py-3">
        {cards.length === 0 ? (
          <p className="mt-6 text-center text-xs text-faint">
            {sessionId
              ? "Transfer bekleniyor... Test Bench'ten komut gönderin; her komut burada bus diyagramıyla görünecek."
              : "Önce Test Bench veya Registers ekranından bir bağlantı kurun; session burada listelenecek."}
          </p>
        ) : (
          cards.map((card) => {
            const device = deviceFor(card);
            const operation = operationFor(card, device);
            const ok = card.rx?.ok === "1";
            const decoded = card.rx ? formatConvertedValue(operation, card.rx) : null;
            const waves = wireTransfers(card, device, operation);
            const durationMs = card.rxAt !== undefined ? Math.max(0, Math.round((card.rxAt - card.txAt) * 1000)) : null;
            return (
              <div
                key={card.key}
                className={cn(
                  "rounded-lg border p-3",
                  !card.rx ? "border-warn/40 bg-warn/5" : ok ? "border-border bg-elev" : "border-danger/40 bg-danger/5",
                )}
              >
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono text-faint">{timeLabel(card.txAt)}</span>
                  <Badge tone="neutral">#{card.id}</Badge>
                  <span className="font-mono text-text">{card.tx.device ?? "?"}</span>
                  <Badge tone="accent">{operation?.label ?? card.tx.op ?? "?"}</Badge>
                  {card.tx.reg ? <span className="font-mono text-muted">{card.tx.reg}</span> : null}
                  {card.rx ? (
                    <Badge tone={ok ? "ok" : "danger"}>{ok ? "ok" : `hata (status ${card.rx.status ?? "?"})`}</Badge>
                  ) : (
                    <Badge tone="warn">yanıt bekliyor</Badge>
                  )}
                  {durationMs !== null ? <span className="font-mono text-faint">{durationMs} ms</span> : null}
                  {decoded ? (
                    <span className="rounded-md border border-ok/40 bg-ok/15 px-2 py-0.5 font-mono font-semibold text-ok">
                      = {decoded}
                    </span>
                  ) : null}
                </div>

                {waves.length > 0 && device ? (
                  <div className="space-y-2">
                    {waves.slice(0, MAX_WAVES_PER_CARD).map((wave, index) => (
                      <div key={`${card.key}-w${index}`}>
                        <div className="mb-1 font-mono text-[10px] uppercase tracking-wide text-faint">
                          {index + 1}/{waves.length} — {wave.title}
                        </div>
                        <BusWaveform part={device.part} transfer={wave.transfer} defaultOpen />
                      </div>
                    ))}
                    {waves.length > MAX_WAVES_PER_CARD ? (
                      <p className="text-[11px] text-faint">
                        + {waves.length - MAX_WAVES_PER_CARD} transfer daha (aynı desen devam eder)
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="text-[11px] text-faint">
                    Bu operasyon için kablo planı yok (eski üretimden manifest olabilir — yeni Generate sonrası
                    diyagramlar gelir).
                  </p>
                )}

                <details className="mt-2">
                  <summary className="cursor-pointer list-none text-[10px] uppercase tracking-wide text-faint">
                    S2C satırları
                  </summary>
                  <div className="mt-1 space-y-1">
                    <code className="block break-all rounded border border-border bg-inset px-2 py-1 font-mono text-[11px] text-text">
                      → {card.txLine}
                    </code>
                    {card.rxLine ? (
                      <code className="block break-all rounded border border-border bg-inset px-2 py-1 font-mono text-[11px] text-muted">
                        ← {card.rxLine}
                      </code>
                    ) : null}
                  </div>
                </details>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
