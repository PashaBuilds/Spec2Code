import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ArrowDownToLine, Eraser, Pause, Play, Plug, SendHorizonal, Unplug } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import { api } from "@/lib/api";
import { downloadTextLog, stripAnsi, timeLabel } from "@/lib/console";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { TelnetLogEntry, TestbenchSessionStatus, TrafficEntry } from "@/lib/types";

const TRAFFIC_POLL_MS = 500;
const SESSIONS_POLL_MS = 2000;
const TELNET_LOG_POLL_MS = 1000;
const TELNET_LOG_MAX_LINES = 2000;


function transportLabel(status: TestbenchSessionStatus): string {
  if (status.transport === "serial") return `seri ${status.serial_port ?? ""}`.trim();
  if (status.transport === "coresight") return `CoreSight DCC (${status.processor ?? "psu_cortexa53_0"})`;
  return `TCP ${status.host}:${status.port}`;
}

// RX özet rengi: çerçeve özeti (S2C-MSG binary — "AD (istek/yanıt) ...")
// bus renginde, konsol/log metni (ASCII fallback) soluk kalır — akış
// kalabalıkken çerçeve/konsol ayrımı göz atarken bile seçilsin (saha isteği).
function rxOzetTone(ozet: string): string {
  if (/\(istek\)|\(yanıt\)/.test(ozet)) return "text-bus-uart";
  return "text-muted";
}

/** Telnet log kartı: firmware'in ürettiği port 23 log sunucusuna (PS Ethernet
 * varsa) bağlanıp satırları PuTTY'nin yanında Akış ekranında da izler. S2C-MSG
 * trafiğinden bağımsız düz metin akışıdır — SerialLinePanel'in bit-seviyesi
 * dalga-formu ayrıştırıcısına BESLENMEZ (kapsam dışı, kasıtlı). */
function TelnetLogCard() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  const [host, setHost] = useState("");
  const [port, setPort] = useState(23);
  const [sessionId, setSessionId] = useState("");
  const [connected, setConnected] = useState(false);
  const [entries, setEntries] = useState<TelnetLogEntry[]>([]);
  const [error, setError] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const sinceRef = useRef(0);
  const logRef = useRef<HTMLDivElement | null>(null);

  // Manifest'te telnet_log varsa host alanını önceden doldur (kullanıcı
  // henüz elle değiştirmediyse) — yoksa boş bırak.
  useEffect(() => {
    if (manifest?.telnet_log && !host) {
      setHost(manifest.telnet_log.ip);
      setPort(manifest.telnet_log.port);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [manifest]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  async function connect() {
    setError("");
    setConnecting(true);
    try {
      const result = await api.telnetLogConnect(host.trim(), port, 5.0);
      setSessionId(result.session_id);
      setConnected(result.status.connected);
      sinceRef.current = 0;
      setEntries([]);
    } catch (err) {
      setConnected(false);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setConnecting(false);
    }
  }

  async function disconnect() {
    if (!sessionId) return;
    try {
      await api.telnetLogDisconnect(sessionId);
    } catch {
      // kopuk zaten olabilir; durum aşağıda yine "kopuk" gösterilecek
    } finally {
      setConnected(false);
    }
  }

  // Bağlıyken 1 sn'lik poll ile yeni satırları çek; kopunca (sunucu tarafından
  // kapatıldıysa da) rozet "kopuk" olur. Otomatik yeniden bağlanma YOK —
  // kullanıcı Bağlan'a tekrar basar.
  useEffect(() => {
    if (!sessionId || !connected) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const { seq, entries: fresh } = await api.telnetLogRead(sessionId, sinceRef.current);
        if (cancelled) return;
        sinceRef.current = seq;
        if (fresh.length > 0) {
          setEntries((current) => [...current, ...fresh].slice(-TELNET_LOG_MAX_LINES));
        }
        const status = await api.telnetLogStatus(sessionId);
        if (cancelled) return;
        if (!status.connected) {
          setConnected(false);
          setError(status.last_error || "telnet log bağlantısı koptu");
        }
      } catch (err) {
        if (cancelled) return;
        setConnected(false);
        setError(err instanceof Error ? err.message : String(err));
      }
    }, TELNET_LOG_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId, connected]);

  return (
    <div className="border-b border-border">
      <div className="flex flex-wrap items-end gap-3 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-text">Telnet log</span>
          <Badge tone={connected ? "ok" : "neutral"}>{connected ? "bağlı" : "kopuk"}</Badge>
        </div>
        <div className="min-w-40">
          <Label>Host</Label>
          <Input value={host} onChange={(event) => setHost(event.target.value)} placeholder="18.2.75.121" disabled={connected} />
        </div>
        <div className="w-24">
          <Label>Port</Label>
          <Input
            type="number"
            value={port}
            onChange={(event) => setPort(Number(event.target.value) || 23)}
            disabled={connected}
          />
        </div>
        <div className="flex gap-2">
          {connected ? (
            <Button size="sm" variant="outline" onClick={() => void disconnect()} title="Kopar">
              <Unplug className="h-4 w-4" aria-hidden /> Kopar
            </Button>
          ) : (
            <Button size="sm" onClick={() => void connect()} disabled={!host.trim() || connecting} title="Bağlan">
              <Plug className="h-4 w-4" aria-hidden /> {connecting ? "Bağlanıyor..." : "Bağlan"}
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => setEntries([])} disabled={entries.length === 0} title="Ekranı temizle">
            <Eraser className="h-4 w-4" aria-hidden />
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
        <p className="mx-4 mb-2 rounded border border-danger/30 bg-danger/10 px-2 py-1.5 font-mono text-[11px] text-danger">
          {error}
        </p>
      ) : null}

      <div
        ref={logRef}
        className="max-h-48 min-h-[6rem] overflow-auto bg-bg px-4 py-2 font-mono text-[12px] leading-relaxed"
      >
        {entries.length === 0 ? (
          <p className="mt-2 text-center text-xs text-faint">
            {connected ? "Satır bekleniyor..." : "Bağlanınca firmware'in telnet log satırları burada akacak."}
          </p>
        ) : (
          entries.map((entry) => (
            <div key={entry.seq} className="grid grid-cols-[96px_minmax(0,1fr)] items-baseline gap-2">
              <span className="select-none text-faint">{timeLabel(entry.at)}</span>
              <span className="block break-all text-text">{stripAnsi(entry.line)}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/** Canlı TX/RX veri akışı: hangi transport olursa olsun (TCP, seri,
 * CoreSight) host ile agent arasındaki her satırı yönü ve zaman damgasıyla
 * gösterir. Session'lar Test Bench / UART konsolu / telemetri taraflarında
 * açılır; bu ekran onları dinler. */
export default function TrafficPanel() {
  const [sessions, setSessions] = useState<TestbenchSessionStatus[]>([]);
  const [sessionId, setSessionId] = useState("");
  const [entries, setEntries] = useState<TrafficEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const [error, setError] = useState("");
  const [input, setInput] = useState("");
  const sinceRef = useRef(0);
  const logRef = useRef<HTMLDivElement | null>(null);

  const selectedSession = useMemo(
    () => sessions.find((session) => session.session_id === sessionId) ?? null,
    [sessions, sessionId],
  );
  const canWrite = selectedSession?.transport === "serial" || selectedSession?.transport === "coresight";
  const txCount = useMemo(() => entries.filter((entry) => entry.dir === "tx").length, [entries]);
  const rxCount = entries.length - txCount;

  // Aktif session listesi: ekran açıkken periyodik tazelenir.
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

  // Session değişince akışı baştan al.
  useEffect(() => {
    sinceRef.current = 0;
    setEntries([]);
    setError("");
  }, [sessionId]);

  // Trafik polling döngüsü.
  useEffect(() => {
    if (!sessionId || paused) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const { seq, entries: fresh } = await api.testbenchTraffic(sessionId, sinceRef.current);
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
    }, TRAFFIC_POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [sessionId, paused]);

  useEffect(() => {
    if (!autoScroll) return;
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries, autoScroll]);

  async function sendLine() {
    // Boş satıra izin var: çıplak Enter, agent'ın "> " canlılık istemini
    // tetikler (çakılma/takılma kontrolü).
    if (!sessionId || !canWrite) return;
    const text = input;
    setInput("");
    try {
      await api.testbenchConsoleWrite(sessionId, text);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  function downloadLog() {
    downloadTextLog("s2c_traffic", entries
      .map((entry) => `${timeLabel(entry.at)}  ${entry.dir.toUpperCase()}  ${entry.ozet}  [${entry.hex}]`)
      .join("\n"));
  }

  return (
    <Card className="flex h-full min-h-0 flex-col p-0">
      <div className="flex flex-wrap items-end gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-accent" aria-hidden />
          <span className="text-sm font-semibold text-text">Veri Akışı</span>
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
        <div className="flex items-center gap-2">
          <Badge tone="accent">→ TX {txCount}</Badge>
          <Badge tone="ok">← RX {rxCount}</Badge>
        </div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={() => setPaused((current) => !current)} title={paused ? "Devam et" : "Duraklat"}>
            {paused ? <Play className="h-4 w-4" aria-hidden /> : <Pause className="h-4 w-4" aria-hidden />}
          </Button>
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

      <TelnetLogCard />

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
            {sessionId
              ? paused
                ? "Duraklatıldı — devam etmek için ▶ butonuna bas."
                : "Trafik bekleniyor... Test Bench'ten komut gönderin ya da karttan veri gelsin."
              : "Önce Test Bench, UART konsolu veya canlı telemetri ile bir bağlantı kurun; session burada listelenecek."}
          </p>
        ) : (
          entries.map((entry) => (
            <div key={entry.seq} className="grid grid-cols-[96px_44px_minmax(0,1fr)] items-baseline gap-2">
              <span className="select-none text-faint">{timeLabel(entry.at)}</span>
              <span className={cn("select-none font-semibold", entry.dir === "tx" ? "text-accent" : "text-ok")}>
                {entry.dir === "tx" ? "→ TX" : "← RX"}
              </span>
              <span className="min-w-0">
                <span className={cn("block break-all", entry.dir === "tx" ? "text-text" : rxOzetTone(entry.ozet))}>
                  {stripAnsi(entry.ozet)}
                </span>
                <span className="block break-all text-[10px] text-faint">{entry.hex}</span>
              </span>
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
          placeholder={canWrite
            ? "Karta ham satır gönder — boş Enter '>' canlılık istemi döndürür"
            : "Ham gönderim yalnızca seri/CoreSight session'larında (TCP'de komutlar Test Bench'ten)"}
          disabled={!canWrite}
          className="font-mono text-xs"
        />
        <Button type="submit" size="sm" disabled={!canWrite}>
          <SendHorizonal className="h-4 w-4" aria-hidden /> Gönder
        </Button>
      </form>
    </Card>
  );
}
