import { useEffect, useMemo, useRef, useState } from "react";
import { AudioWaveform, Eraser, Pause, Play } from "lucide-react";
import { Badge, Button, Card, Label } from "@/components/ui";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import { api } from "@/lib/api";
import { timeLabel } from "@/lib/console";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { TestbenchManifest, TestbenchSessionStatus } from "@/lib/types";

const TRAFFIC_POLL_MS = 500;
const SESSIONS_POLL_MS = 2000;
const MAX_CARDS = 40;

/** decode_frame_summary (backend/s2cmsg.py) çıktısını çözer: "{AD} ({istek|yanit}) sayac={n} govde={n}B".
 * Bu, S2C-MSG binary çerçevesinin insan-okunur özetidir — trafik girdisinde
 * ayrıştırılmış device/register/data alanları YOK (tel artık binary; bkz.
 * Task 3 raporu "Mimari not"), yalnız işlem adı + sayaç (id) + yön çözülür. */
function parseOzet(ozet: string): { name: string; dir: "istek" | "yanit"; sayac: number; bodyBytes: number } | null {
  const match = /^(\S+) \((istek|yanit)\) sayac=(\d+) govde=(\d+)B$/.exec(ozet.trim());
  if (!match) return null;
  return { name: match[1], dir: match[2] as "istek" | "yanit", sayac: Number(match[3]), bodyBytes: Number(match[4]) };
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
}

function transportLabel(status: TestbenchSessionStatus): string {
  if (status.transport === "serial") return `seri ${status.serial_port ?? ""}`.trim();
  if (status.transport === "coresight") return `CoreSight DCC (${status.processor ?? ""})`;
  return `TCP ${status.host}:${status.port}`;
}

/** Akış'ın kardeşi: her S2C-MSG istek/yanıt çifti sayaç (id) ile eşleştirilir
 * ve manifest'teki operasyon etiketiyle gösterilir. Tel artık binary
 * olduğundan (S2C-MSG) trafik girdisi yalnız hex dökümü + insan-okunur özet
 * taşır — device/register/data alanları burada AYRIŞTIRILAMAZ (bkz. Task 3
 * raporu "Mimari not"); bus-seviyesi dalga biçimi diyagramları bu yüzden
 * kaldırıldı, kart yalnız istek/yanıt hex+özetini yan yana gösterir. */
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
  // İşlem adı (katalog NAME, ör. VOLTAGE_READ) → manifest operation label
  // eşlemesi: yalnız görüntü amaçlı, birden çok cihaz aynı op'u paylaşırsa
  // ilk eşleşen etiket kullanılır.
  const operationLabelByName = useMemo(() => {
    const map = new Map<string, string>();
    for (const device of manifest?.devices ?? []) {
      for (const op of device.operations) {
        if (!map.has(op.name)) map.set(op.name, op.label || op.name);
      }
    }
    return map;
  }, [manifest]);

  const [sessions, setSessions] = useState<TestbenchSessionStatus[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [cards, setCards] = useState<TransferCard[]>([]);
  const [paused, setPaused] = useState(false);
  const [error, setError] = useState("");
  const sinceRef = useRef(0);
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
            const parsed = parseOzet(entry.ozet);
            if (!parsed) continue; // konsol metni / çözülemeyen özet — kart değil
            if (parsed.dir === "istek") {
              const key = `${entry.seq}`;
              pendingRef.current.set(parsed.sayac, key);
              next = [
                { key, sayac: parsed.sayac, name: parsed.name, txAt: entry.at, txHex: entry.hex, txOzet: entry.ozet },
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
          Her kart bir S2C-MSG istek/yanıt çiftidir (sayaç eşleşmeli). İşlem adı katalogdan
          çözülür; ham hex dökümü ve özet satırı her iki yön için ayrı ayrı gösterilir.
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
            const label = operationLabelByName.get(card.name.toLowerCase()) ?? card.name;
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
                  <Badge tone="accent">{label}</Badge>
                  {card.rxOzet ? (
                    <Badge tone="ok">yanıt geldi</Badge>
                  ) : (
                    <Badge tone="warn">yanıt bekliyor</Badge>
                  )}
                  {durationMs !== null ? <span className="font-mono text-faint">{durationMs} ms</span> : null}
                </div>

                <div className="space-y-1">
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
