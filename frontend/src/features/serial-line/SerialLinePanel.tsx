import { useEffect, useMemo, useRef, useState } from "react";
import { AudioWaveform, Eraser, Pause, Play } from "lucide-react";
import { Badge, Button, Card, Label } from "@/components/ui";
import BusWaveform from "@/features/device-knowledge/BusWaveform";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import { api } from "@/lib/api";
import { stripAnsi, timeLabel } from "@/lib/console";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { KnowledgeRegisterTransfer } from "@/features/device-knowledge/knowledge";
import type { TestbenchManifest, TestbenchManifestDevice, TestbenchSessionStatus } from "@/lib/types";

const TRAFFIC_POLL_MS = 500;
const SESSIONS_POLL_MS = 2000;
const MAX_CARDS = 40;

/** decode_frame_summary (backend/s2cmsg.py) çıktısını çözer: "{AD} ({istek|yanit}) sayac={n} govde={n}B".
 * Bu, S2C-MSG binary çerçevesinin insan-okunur özetidir — trafik girdisinde
 * ayrıştırılmış device/register/data alanları YOK (tel artık binary), yalnız
 * işlem adı + sayaç (id) + yön çözülür. Bus-seviyesi bit izleme bu yüzden
 * komut çerçevesinden değil, ajanın TRACE metin satırlarından beslenir
 * (aşağıdaki parseTraceLine) — bkz. backend/testbench.py `_traffic_push`
 * text alanı. */
function parseOzet(ozet: string): { name: string; dir: "istek" | "yanit"; sayac: number; bodyBytes: number } | null {
  const match = /^(\S+) \((istek|yanit)\) sayac=(\d+) govde=(\d+)B$/.exec(ozet.trim());
  if (!match) return null;
  return { name: match[1], dir: match[2] as "istek" | "yanit", sayac: Number(match[3]), bodyBytes: Number(match[4]) };
}

/** Ajanın canlı bus izi: "S2C-LOG|D|TRACE|id=..|bus=..|..." satırı.
 * Sürücülerin en alt seviye gönder/al fonksiyonları her GERÇEK transferden
 * sonra yayınlar (log seviyesi debug iken). Bu satır formatı S2C-MSG'ye
 * geçişten ETKİLENMEDİ: ajan hâlâ düz metin log satırı yazıyor, yalnız komut
 * çerçeveleri binary oldu. İki kaynaktan gelir: (1) konsol satırları (seri
 * transport'ta iz aynı UART'a xil_printf ile de düşer), (2) traffic
 * girdisinin `text` alanı (backend artık unsolicited TRACE_EVENT
 * çerçevesini decode edip bunu da taşıyor — TCP/CoreSight trace'leri
 * konsol ringine hiç girmediğinden bu ikinci kaynak olmadan TCP'de iz hiç
 * görünmezdi). */
export function parseTraceLine(line: string): Record<string, string> | null {
  const text = stripAnsi(line).trim();
  const marker = text.indexOf("TRACE|");
  if (!text.startsWith("S2C-LOG|") || marker < 0) return null;
  const parsed: Record<string, string> = {};
  for (const token of text.slice(marker + "TRACE|".length).split("|")) {
    const eq = token.indexOf("=");
    if (eq > 0) parsed[token.slice(0, eq).trim()] = token.slice(eq + 1).trim();
  }
  return parsed.id ? parsed : null;
}

interface TraceRec {
  bus?: string;
  addr?: string;
  reg?: string;
  dir?: string;
  cs?: string;
  len?: string;
  data?: string;
  tx?: string;
  rx?: string;
}

interface TransferCard {
  key: string;
  sayac: number;
  name: string;
  txAt: number;
  rxAt?: number;
  txHex: string;
  txOzet: string;
  rxHex?: string;
  rxOzet?: string;
  traces: TraceRec[];
}

function parseNumberish(text: string | undefined): number | null {
  const parsed = Number.parseInt(text ?? "", (text ?? "").toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function hexPairs(hex: string | undefined): string[] {
  const clean = (hex ?? "").replace(/[^0-9a-fA-F]/g, "");
  const bytes: string[] = [];
  for (let i = 0; i + 2 <= clean.length; i += 2) bytes.push(`0x${clean.slice(i, i + 2).toUpperCase()}`);
  return bytes;
}

/** Kartın canlı bus diyagramları: her GERÇEK bus transferi sırasıyla bir
 * diyagram olur (kanal kanal). Ardışık aynı register/aynı yön okumaları
 * (poll) ×k olarak katlanır — iterasyonlar gerçekten yaşanmıştır, yalnız
 * gösterim sıkıştırılır. */
function traceTransfers(
  card: TransferCard,
  device: TestbenchManifestDevice | null,
): Array<{ transfer: KnowledgeRegisterTransfer; title: string }> {
  if (card.traces.length === 0) return [];
  const regNameByAddr = new Map<number, string>();
  for (const reg of device?.registers ?? []) regNameByAddr.set(reg.offset, reg.name);

  interface Group { trace: TraceRec; count: number }
  const groups: Group[] = [];
  for (const trace of card.traces) {
    const previous = groups[groups.length - 1];
    const sameAsPrevious =
      previous &&
      previous.trace.bus === trace.bus &&
      previous.trace.reg === trace.reg &&
      previous.trace.dir === trace.dir &&
      previous.trace.tx === trace.tx;
    if (sameAsPrevious) {
      previous.count += 1;
      previous.trace = trace; // son iterasyonun gerçek verisi gösterilir
    } else {
      groups.push({ trace, count: 1 });
    }
  }

  return groups.map(({ trace, count }) => {
    const suffix = count > 1 ? ` ×${count}` : "";
    if (trace.bus === "i2c") {
      const regAddr = parseNumberish(trace.reg) ?? 0;
      const regName = regNameByAddr.get(regAddr) ?? trace.reg ?? "REG";
      const regLabel = `${regName} (${trace.reg ?? "?"})`;
      const bytes = hexPairs(trace.data);
      // İzdeki gerçek slave adresi: SLA baytı gerçek bitleriyle çizilir.
      const busAddress = parseNumberish(trace.addr) ?? undefined;
      if ((trace.dir ?? "r") === "w") {
        return {
          title: `${regName} yaz${suffix}`,
          transfer: {
            title: regLabel, access: "WRITE", txBytes: `${1 + bytes.length} byte`, rxBytes: "0 byte",
            tx: [regLabel, ...bytes], rx: ["-"], code: [],
            note: count > 1 ? `${count} kez tekrarlandı` : undefined,
            i2cAddress: busAddress,
          },
        };
      }
      return {
        title: `${regName} oku${suffix}`,
        transfer: {
          title: regLabel, access: "READ", txBytes: "1 byte", rxBytes: `${bytes.length || 1} byte`,
          tx: [regLabel], rx: bytes.length ? bytes : ["DATA"], code: [],
          note: count > 1 ? `hazır olana dek ${count} kez okundu` : undefined,
          i2cAddress: busAddress,
        },
      };
    }
    const txBytesList = hexPairs(trace.tx === "-" ? "" : trace.tx);
    const rxBytesList = trace.rx && trace.rx !== "-" ? hexPairs(trace.rx) : [];
    const isRead = rxBytesList.length > 0;
    return {
      title: `SPI frame${suffix}`,
      transfer: {
        title: `SPI (CS${trace.cs ?? "?"})`, access: isRead ? "READ" : "WRITE",
        txBytes: `${txBytesList.length} byte`, rxBytes: isRead ? `${rxBytesList.length} byte` : "0 byte",
        tx: txBytesList.length ? txBytesList : ["TX"], rx: isRead ? rxBytesList : ["-"], code: [],
        note: count > 1 ? `${count} kez tekrarlandı` : undefined,
      },
    };
  });
}

function transportLabel(status: TestbenchSessionStatus): string {
  if (status.transport === "serial") return `seri ${status.serial_port ?? ""}`.trim();
  if (status.transport === "coresight") return `CoreSight DCC (${status.processor ?? ""})`;
  return `TCP ${status.host}:${status.port}`;
}

/** Akış'ın kardeşi: her S2C-MSG istek/yanıt çifti sayaç (id) ile eşleştirilir.
 * Komut çerçeveleri artık binary olduğundan (S2C-MSG) kart üstündeki
 * device/op/register alanları çerçeve özetinden AYRIŞTIRILAMAZ — yalnız
 * katalogdaki işlem adı (name) ve sayaç çözülür (ozet + hex ham dökümü
 * her zaman gösterilir). Ajanın gerçek bus transferlerini bit seviyesinde
 * gösteren canlı dalga formu ise TRACE metin satırlarından (id ile karta
 * eşlenir) beslenir — bu satırların formatı S2C-MSG geçişinden etkilenmedi. */
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
  // İşlem adı (katalog NAME, ör. VOLTAGE_READ) → manifest operation label +
  // cihaz eşlemesi: yalnız görüntü/register-adı çözümü amaçlı, birden çok
  // cihaz aynı op'u paylaşırsa ilk eşleşen kullanılır (kart üstünde hangi
  // FİZİKSEL cihazın konuştuğu artık çerçeve özetinden ayrıştırılamıyor).
  const opIndex = useMemo(() => {
    const map = new Map<string, { label: string; device: TestbenchManifestDevice }>();
    for (const device of manifest?.devices ?? []) {
      for (const op of device.operations) {
        if (!map.has(op.name)) map.set(op.name, { label: op.label || op.name, device });
      }
    }
    return map;
  }, [manifest]);

  const [sessions, setSessions] = useState<TestbenchSessionStatus[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [cards, setCards] = useState<TransferCard[]>([]);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");
  const trafficSinceRef = useRef(0);
  const consoleSinceRef = useRef(0);
  const pendingRef = useRef<Map<number, string>>(new Map()); // sayac -> card key

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
    trafficSinceRef.current = 0;
    consoleSinceRef.current = 0;
    pendingRef.current.clear();
    setCards([]);
    setError("");
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || paused) return;
    let cancelled = false;

    /** Bir TRACE kayıt satırını, sayaç (id) eşleşen bekleyen komut kartına ekler. */
    function appendTrace(cardsIn: TransferCard[], rawLine: string): TransferCard[] {
      const trace = parseTraceLine(rawLine);
      if (!trace) return cardsIn;
      const key = pendingRef.current.get(Number(trace.id));
      if (!key) return cardsIn;
      return cardsIn.map((card) =>
        card.key === key ? { ...card, traces: [...card.traces, trace as TraceRec] } : card,
      );
    }

    const timer = window.setInterval(async () => {
      try {
        const [trafficRes, consoleRes] = await Promise.all([
          api.testbenchTraffic(sessionId, trafficSinceRef.current),
          api.testbenchConsoleRead(sessionId, consoleSinceRef.current),
        ]);
        if (cancelled) return;
        trafficSinceRef.current = trafficRes.seq;
        consoleSinceRef.current = consoleRes.seq;
        setError("");
        if (trafficRes.entries.length === 0 && consoleRes.entries.length === 0) return;
        setCards((current) => {
          let next = current;
          for (const entry of trafficRes.entries) {
            if (entry.text) {
              // Unsolicited TRACE_EVENT/BUS_TRACE_EVENT çerçevesi: backend
              // decode edip text alanına koydu (bkz. backend/testbench.py
              // _traffic_push). TCP/CoreSight'ta trace'ler yalnız buradan gelir.
              for (const line of entry.text.split("\n")) next = appendTrace(next, line);
              continue;
            }
            const parsed = parseOzet(entry.ozet);
            if (!parsed) continue; // konsol metni / çözülemeyen özet — kart değil
            if (parsed.dir === "istek") {
              const key = `${entry.seq}`;
              pendingRef.current.set(parsed.sayac, key);
              next = [
                {
                  key, sayac: parsed.sayac, name: parsed.name, txAt: entry.at,
                  txHex: entry.hex, txOzet: entry.ozet, traces: [],
                },
                ...next,
              ].slice(0, MAX_CARDS);
            } else {
              const key = pendingRef.current.get(parsed.sayac);
              if (!key) continue;
              pendingRef.current.delete(parsed.sayac);
              next = next.map((card) =>
                card.key === key
                  ? { ...card, rxAt: entry.at, rxHex: entry.hex, rxOzet: entry.ozet }
                  : card,
              );
            }
          }
          // Seri transport: TRACE satırları aynı zamanda konsol ringine de
          // düşer (backend _handle_frame). Trafik girdisinin `text` alanı
          // yalnız binary çerçeveyi taşıyan session'larda (TCP/CoreSight)
          // zorunlu tek kaynaktır; seri'de konsol de aynı satırları verir —
          // iki kaynağı da beslemek zararsız (aynı id'ye ekleniyor, yalnız
          // görsel tekrar olabilir ama eski davranış da tekilleştirme
          // yapmıyordu).
          for (const entry of consoleRes.entries) next = appendTrace(next, entry.line);
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
          Her kart bir S2C-MSG istek/yanıt çiftidir (sayaç eşleşmeli).{" "}
          <span className="font-semibold text-text">
            Canlı bit izleme için bağlantı kartından log seviyesini 5 (debug) yap
          </span>
          : ajan her gerçek bus transferini raporlar ve diyagramlar GERÇEK TX/RX baytlarıyla, kanal
          kanal sırayla çizilir (poll tekrarları ×k olarak katlanır). İz yokken yalnız istek/yanıt
          özeti ve ham hex gösterilir.
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
              ? "Transfer bekleniyor... Test Bench'ten komut gönderin; her komut burada istek/yanıt kartı olarak görünecek."
              : "Önce Test Bench veya Registers ekranından bir bağlantı kurun; session burada listelenecek."}
          </p>
        ) : (
          cards.map((card) => {
            const opEntry = opIndex.get(card.name.toLowerCase());
            const device = opEntry?.device ?? null;
            const waves = traceTransfers(card, device);
            const durationMs = card.rxAt !== undefined ? Math.max(0, Math.round((card.rxAt - card.txAt) * 1000)) : null;
            return (
              <div
                key={card.key}
                className={cn(
                  "rounded-lg border p-3",
                  !card.rxOzet ? "border-warn/40 bg-warn/5" : "border-border bg-elev",
                )}
              >
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  <span className="font-mono text-faint">{timeLabel(card.txAt)}</span>
                  <Badge tone="neutral">sayaç {card.sayac}</Badge>
                  <Badge tone="accent">{opEntry?.label ?? card.name}</Badge>
                  {card.rxOzet ? (
                    <Badge tone="ok">yanıt geldi</Badge>
                  ) : (
                    <Badge tone="warn">yanıt bekliyor</Badge>
                  )}
                  {durationMs !== null ? <span className="font-mono text-faint">{durationMs} ms</span> : null}
                  {waves.length > 0 ? <Badge tone="ok">canlı iz</Badge> : null}
                </div>

                {waves.length > 0 && device ? (
                  <div className="max-h-[460px] space-y-2 overflow-y-auto pr-1">
                    {waves.map((wave, index) => (
                      <div key={`${card.key}-w${index}`}>
                        <div className="mb-1 font-mono text-[10px] uppercase tracking-wide text-faint">
                          {index + 1}/{waves.length} — {wave.title}
                        </div>
                        <BusWaveform
                          part={device.part}
                          transfer={wave.transfer}
                          transport={device.transport === "spi" ? "spi" : "i2c"}
                          defaultOpen
                        />
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="mt-2 space-y-1">
                  <div>
                    <div className="mb-0.5 text-[10px] uppercase tracking-wide text-faint">→ TX özet</div>
                    <code className="block break-all rounded border border-border bg-inset px-2 py-1 font-mono text-[11px] text-text">
                      {card.txOzet}
                    </code>
                    <code className="mt-0.5 block break-all px-2 font-mono text-[10px] text-faint">{card.txHex}</code>
                  </div>
                  {card.rxOzet ? (
                    <div>
                      <div className="mb-0.5 text-[10px] uppercase tracking-wide text-faint">← RX özet</div>
                      <code className="block break-all rounded border border-border bg-inset px-2 py-1 font-mono text-[11px] text-muted">
                        {card.rxOzet}
                      </code>
                      <code className="mt-0.5 block break-all px-2 font-mono text-[10px] text-faint">{card.rxHex}</code>
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
