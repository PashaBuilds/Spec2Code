import { useState } from "react";
import { CheckCircle2, Loader2, ShieldCheck, XCircle } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { api } from "@/lib/api";
import { timeLabelMs } from "@/lib/console";
import { asciiFromDataHex } from "@/lib/units";
import type { BoardTransport } from "@/store/connection";

interface VersionQueryResult {
  ok: boolean;
  versionText: string | null;
  status: string | null;
  message: string;
  requestLine: string;
  responseLine: string;
  sentAtMs: number;
  durationMs: number;
}

/** Ajan sürümü: I2C Hat Taraması ile aynı kalıpta KENDİ collapsible kartı.
 * Kök neden (bkz. rapor): eski akışta sonuç TestBenchPanel'in paylaşılan
 * result/resultOperation state'ine yazılıyordu ama ResultPanel yalnızca
 * view==="device" dalında render ediliyordu — i2c-scan görünümündeyken
 * "Sürüm sorgula"ya basmak sonucu hesaplıyor ama HİÇBİR YERDE göstermiyordu.
 * Burada state kartın kendisinde tutulur ve bölüm/cihaz değişiminden
 * etkilenmez; sonuç HER ZAMAN bu kartın içinde kalıcı görünür. */
export default function VersionQueryCard({
  connected,
  transport,
  host,
  port,
  sessionId,
  timeoutSeconds,
}: {
  connected: boolean;
  transport: BoardTransport;
  host: string;
  port: string;
  sessionId: string;
  timeoutSeconds: number;
}) {
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<VersionQueryResult | null>(null);

  function parsePort(): number {
    const parsed = Number.parseInt(port.trim(), 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  async function query() {
    if (!connected || running) return;
    setRunning(true);
    setError("");
    const sentAtMs = Date.now();
    const startedAt = performance.now();
    try {
      const response = await api.testbenchCommand({
        host: transport === "tcp" ? host.trim() : transport,
        port: transport === "tcp" ? parsePort() : 0,
        device: "spec2code",
        operation: "spec2code_version",
        session_id: sessionId,
        timeout_s: timeoutSeconds,
      });
      const data = response.parsed.data ?? "";
      const versionText =
        asciiFromDataHex(data) ?? /v\d+\.\d+\.\d+/.exec(response.parsed.message ?? "")?.[0] ?? null;
      setResult({
        ok: response.parsed.ok === "1",
        versionText,
        status: response.parsed.status ?? null,
        message: response.parsed.message ?? "",
        requestLine: response.request_line,
        responseLine: response.response_line,
        sentAtMs,
        durationMs: Math.round(performance.now() - startedAt),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-elev p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <ShieldCheck className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-text">Ajan Sürümü</h3>
        {result ? (
          <Badge tone={result.ok ? "ok" : "danger"}>{result.ok ? "ok" : "hata"}</Badge>
        ) : null}
        {result ? (
          <span className="ml-auto font-mono text-[11px] text-muted">
            {timeLabelMs(result.sentAtMs, { ms: true })} · {result.durationMs} ms
          </span>
        ) : null}
      </div>

      <p className="mb-3 text-xs leading-relaxed text-muted">
        Karttaki generated test bench agent'ının sürümünü sorgular (S2C-MSG <code>spec2code_version</code>
        operasyonu). Sonuç bu kartta kalır — başka bir entegre veya bölüm seçmek sonucu silmez.
      </p>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Button onClick={() => void query()} disabled={!connected || running}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
          {running ? "Sorgulanıyor..." : "Sürümü sorgula"}
        </Button>
        {!connected ? <span className="text-xs text-faint">Önce karta bağlan.</span> : null}
      </div>

      {error ? (
        <p className="mb-3 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
      ) : null}

      {result ? (
        <div className={`rounded-md border p-3 ${result.ok ? "border-ok/30 bg-ok/10" : "border-danger/30 bg-danger/10"}`}>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            {result.ok ? <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden /> : <XCircle className="h-4 w-4 text-danger" aria-hidden />}
            <Badge tone={result.ok ? "ok" : "danger"}>{result.ok ? "ok" : "hata"}</Badge>
            {result.status ? <Badge tone="neutral">status {result.status}</Badge> : null}
            {result.versionText ? (
              <span className="rounded-md border border-ok/40 bg-ok/15 px-2 py-0.5 font-mono text-sm font-semibold text-ok">
                agent {result.versionText}
              </span>
            ) : null}
          </div>

          <div className="grid gap-2 text-[11px] md:grid-cols-2">
            <div>
              <div className="mb-1 text-faint">Request</div>
              <code className="block break-all rounded border border-border bg-bg p-2 font-mono text-text">{result.requestLine}</code>
            </div>
            <div>
              <div className="mb-1 text-faint">Response</div>
              <code className="block break-all rounded border border-border bg-bg p-2 font-mono text-text">{result.responseLine}</code>
            </div>
          </div>

          {result.message ? (
            <div className="mt-3">
              <div className="mb-1 text-[11px] text-faint">Mesaj</div>
              <p className="break-all text-xs leading-relaxed text-text">{result.message}</p>
            </div>
          ) : null}

          {!result.ok ? (
            <p className="mt-3 text-xs leading-relaxed text-danger">
              {result.message || "Sürüm sorgusu başarısız döndü."}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
          Henüz sorgu gönderilmedi. Sonuç burada kalıcı olarak görünecek.
        </div>
      )}
    </section>
  );
}
