import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type { TestbenchManifest, TestbenchManifestDevice } from "@/lib/types";

const POLL_INTERVAL_MS = 3000;

/** Cihaz başına telemetriye en uygun güvenli operasyon. */
function pollOperation(device: TestbenchManifestDevice): string | null {
  const safe = device.operations.filter(
    (op) => op.risk === "safe" && !op.requires_address && !op.requires_data && !op.requires_value,
  );
  const byName = (needle: string) => safe.find((op) => op.name.includes(needle))?.name ?? null;
  return (
    byName("temperature") ??
    byName("lock_detect") ??
    byName("vcc") ??
    byName("voltage") ??
    byName("id_read") ??
    (safe[0]?.name ?? null)
  );
}

function shortValue(parsed: Record<string, string>): string {
  if (parsed.value && parsed.value !== "0x0") return parsed.value;
  if (parsed.data) {
    const data = parsed.data;
    return data.length > 8 ? `${data.slice(0, 8)}…` : data;
  }
  return parsed.value || "OK";
}

function makeSessionId(): string {
  const globalCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return `tl_${globalCrypto.randomUUID()}`;
  }
  return `tl_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

/** Şematik üstünde "Canlı telemetri" anahtarı: kayıtlı test bench bağlantı
 * ayarlarıyla kendi session'ını açar ve cihazları sırayla yoklar. */
export default function TelemetryControl() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const projectName = useStore((s) => s.project.name);
  const devices = useStore((s) => s.devices);
  const setTelemetry = useStore((s) => s.setTelemetry);
  const clearTelemetry = useStore((s) => s.clearTelemetry);

  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(files.length > 0 ? files : previousFiles) ?? loadCachedManifest(projectName),
    [files, previousFiles, projectName],
  );

  const [sessionId] = useState(makeSessionId);
  const [active, setActive] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const commandIdRef = useRef(1);

  const targets = useMemo(() => {
    if (!manifest) return [];
    const deviceIds = new Set(devices.map((device) => device.id));
    return manifest.devices
      .filter((device) => deviceIds.size === 0 || deviceIds.has(device.id))
      .map((device) => ({ id: device.id, operation: pollOperation(device) }))
      .filter((item): item is { id: string; operation: string } => Boolean(item.operation));
  }, [manifest, devices]);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;

    async function pollOnce() {
      for (const target of targets) {
        if (cancelled) return;
        try {
          const response = await api.testbenchCommand({
            host: "session",
            port: 0,
            device: target.id,
            operation: target.operation,
            command_id: commandIdRef.current++,
            session_id: sessionId,
            timeout_s: 4,
          });
          if (cancelled) return;
          setTelemetry(target.id, shortValue(response.parsed));
        } catch (err) {
          if (cancelled) return;
          setError(err instanceof Error ? err.message : String(err));
          setActive(false);
          void api.testbenchDisconnect(sessionId).catch(() => undefined);
          return;
        }
      }
    }

    void pollOnce();
    const timer = window.setInterval(() => void pollOnce(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [active, targets, sessionId, setTelemetry]);

  useEffect(() => {
    return () => {
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
    };
  }, [sessionId]);

  async function toggle() {
    if (busy) return;
    if (active) {
      setActive(false);
      clearTelemetry();
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
      return;
    }
    if (!manifest || targets.length === 0) {
      setError("Telemetri için test bench manifest'i gerekli (önce Generate).");
      return;
    }
    setBusy(true);
    setError("");
    const transport = localStorage.getItem("spec2code.testbench.transport") === "serial" ? "serial" : "tcp";
    try {
      const status = await api.testbenchConnect(
        transport === "serial"
          ? {
              session_id: sessionId,
              transport: "serial",
              serial_port: localStorage.getItem("spec2code.testbench.serialPort") ?? "",
              baud: Number.parseInt(localStorage.getItem("spec2code.testbench.baud") ?? "115200", 10) || 115200,
              timeout_s: 4,
            }
          : {
              session_id: sessionId,
              transport: "tcp",
              host: localStorage.getItem("spec2code.testbench.host") ?? "127.0.0.1",
              port: Number.parseInt(localStorage.getItem("spec2code.testbench.port") ?? "5000", 10) || 5000,
              timeout_s: 4,
            },
      );
      if (status.connected) {
        setActive(true);
      } else {
        setError(status.last_error || "Bağlantı kurulamadı.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="absolute right-3 top-3 z-10 flex flex-col items-end gap-1">
      <Button
        size="sm"
        variant={active ? "primary" : "outline"}
        onClick={() => void toggle()}
        disabled={busy}
        title="Test Bench bağlantı ayarlarıyla kartı periyodik yoklar; değerler cihaz node'larında görünür."
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Activity className={cn("h-4 w-4", active && "text-ok")} aria-hidden />
        )}
        Canlı telemetri {active ? "AÇIK" : "kapalı"}
      </Button>
      {error ? (
        <p className="max-w-64 rounded border border-danger/30 bg-bg/90 px-2 py-1 text-right font-mono text-[10px] text-danger backdrop-blur-sm">
          {error}
        </p>
      ) : null}
    </div>
  );
}
