import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Loader2 } from "lucide-react";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { useBoardConnection } from "@/store/connection";
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

/** Uygulama başlığındaki "Canlı telemetri" anahtarı: önce açık bir test bench
 * session'ını paylaşır, yoksa kayıtlı bağlantı ayarlarıyla kendi session'ını
 * açar ve cihazları sırayla yoklar. Başlıkta yaşadığı için ekranlar arası
 * geçişte kapanmaz; değerler şematikteki cihaz node'larında akar. */
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

  const board = useBoardConnection();
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
    if (!active || !board.connected) return;
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
            session_id: board.sessionId,
            timeout_s: 4,
          });
          if (cancelled) return;
          setTelemetry(target.id, shortValue(response.parsed));
        } catch (err) {
          if (cancelled) return;
          setError(err instanceof Error ? err.message : String(err));
          setActive(false);
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
  }, [active, targets, board.sessionId, board.connected, setTelemetry]);

  async function toggle() {
    if (busy) return;
    if (active) {
      setActive(false);
      clearTelemetry();
      return;
    }
    if (!manifest || targets.length === 0) {
      setError("Telemetri için test bench manifest'i gerekli (önce Generate).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      // Ortak kart bağlantısını paylaşır; kopuksa kayıtlı ayarlarla kurar
      // (CoreSight dahil). Telemetri kapatılınca bağlantıya dokunulmaz.
      const ok = board.connected || (await board.connect());
      if (ok) {
        setActive(true);
      } else {
        setError(useBoardConnection.getState().lastError || "Bağlantı kurulamadı.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative">
      <Button
        size="sm"
        variant={active ? "primary" : "ghost"}
        onClick={() => void toggle()}
        disabled={busy}
        title="Açık test bench session'ını paylaşır (yoksa kayıtlı ayarlarla bağlanır) ve kartı periyodik yoklar; değerler şematikteki cihaz node'larında görünür. Ekran değiştirince kapanmaz."
      >
        {busy ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
        ) : (
          <Activity className={cn("h-4 w-4", active && "text-ok")} aria-hidden />
        )}
        Telemetri {active ? "AÇIK" : "kapalı"}
      </Button>
      {error ? (
        <p className="absolute right-0 top-full z-20 mt-1 w-72 rounded border border-danger/30 bg-bg/95 px-2 py-1 text-right font-mono text-[10px] text-danger shadow-lg backdrop-blur-sm">
          {error}
        </p>
      ) : null}
    </div>
  );
}
