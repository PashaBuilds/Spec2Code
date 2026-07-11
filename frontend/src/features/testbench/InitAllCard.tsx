import { useState } from "react";
import { CheckCircle2, Loader2, Zap, XCircle } from "lucide-react";
import { Badge, Button } from "@/components/ui";
import { api } from "@/lib/api";
import type { BoardTransport } from "@/store/connection";
import type { TestbenchManifestDevice } from "@/lib/types";

interface InitStepResult {
  deviceId: string;
  part: string;
  ok: boolean;
  message: string;
}

/** Manifest'teki her cihaz için sırayla (paralel DEĞİL — bus disiplini)
 * device_init koşar. Saha isteği: CIT/YATT'tan önce her entegrenin
 * "device init uygula"sına tek tek basmak gerekiyordu, tek tuşla toplu
 * ilklendirme okumaların fail olmasını önler. Bir cihaz fail olsa da
 * devam eder — kısmi ilklendirme yine de değerlidir. */
export default function InitAllCard({
  devices,
  connected,
  transport,
  host,
  port,
  sessionId,
  timeoutSeconds,
}: {
  devices: TestbenchManifestDevice[];
  connected: boolean;
  transport: BoardTransport;
  host: string;
  port: string;
  sessionId: string;
  timeoutSeconds: number;
}) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ index: number; total: number; label: string } | null>(null);
  const [results, setResults] = useState<InitStepResult[] | null>(null);

  const initDevices = devices.filter((device) => device.operations.some((op) => op.name === "device_init"));
  if (initDevices.length === 0) return null;

  function parsePort(): number {
    const parsed = Number.parseInt(port.trim(), 10);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  async function runAll() {
    if (!connected || running) return;
    setRunning(true);
    setResults(null);
    const collected: InitStepResult[] = [];
    for (let i = 0; i < initDevices.length; i += 1) {
      const device = initDevices[i];
      setProgress({ index: i + 1, total: initDevices.length, label: `${device.part} · ${device.id}` });
      try {
        // eslint-disable-next-line no-await-in-loop -- bilerek sıralı: bus disiplini, paralel koşmaz.
        const response = await api.testbenchCommand({
          host: transport === "tcp" ? host.trim() : transport,
          port: transport === "tcp" ? parsePort() : 0,
          device: device.id,
          operation: "device_init",
          session_id: sessionId,
          timeout_s: timeoutSeconds,
        });
        const ok = response.parsed.ok === "1";
        collected.push({
          deviceId: device.id,
          part: device.part,
          ok,
          message: ok ? "" : response.parsed.message || `status ${response.parsed.status ?? "-"}`,
        });
      } catch (err) {
        collected.push({
          deviceId: device.id,
          part: device.part,
          ok: false,
          message: err instanceof Error ? err.message : String(err),
        });
      }
    }
    setResults(collected);
    setProgress(null);
    setRunning(false);
  }

  const passed = results?.filter((r) => r.ok).length ?? 0;

  return (
    <div className="rounded-md border border-accent/30 bg-accent/5 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Zap className="h-4 w-4 text-accent" aria-hidden />
        <span className="text-xs font-semibold text-text">Toplu ilklendirme</span>
        <Badge tone="neutral">{initDevices.length} cihaz</Badge>
        {results ? (
          <Badge tone={passed === results.length ? "ok" : "warn"} className="ml-auto">
            {passed}/{results.length} başarılı
          </Badge>
        ) : null}
      </div>

      <Button size="sm" onClick={() => void runAll()} disabled={!connected || running} className="w-full">
        {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Zap className="h-4 w-4" aria-hidden />}
        {running ? "İlklendiriliyor..." : "Bütün cihazları ilklendir"}
      </Button>

      {running && progress ? (
        <p className="mt-2 font-mono text-[11px] text-muted">
          {progress.index}/{progress.total} · {progress.label}
        </p>
      ) : null}

      {!connected ? <p className="mt-2 text-[11px] text-faint">Önce karta bağlan.</p> : null}

      {results ? (
        <ul className="mt-2 space-y-1">
          {results.map((r) => (
            <li
              key={r.deviceId}
              className="flex items-center gap-1.5 rounded border border-border bg-inset px-2 py-1 font-mono text-[11px]"
            >
              {r.ok ? (
                <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-ok" aria-hidden />
              ) : (
                <XCircle className="h-3.5 w-3.5 shrink-0 text-danger" aria-hidden />
              )}
              <span className="truncate text-text">{r.part} · {r.deviceId}</span>
              <span className={r.ok ? "ml-auto text-ok" : "ml-auto truncate text-danger"}>
                {r.ok ? "OK" : `HATA${r.message ? `(${r.message})` : ""}`}
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
