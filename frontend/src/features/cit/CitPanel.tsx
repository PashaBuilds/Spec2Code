import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, HeartPulse, Loader2, Pause, Play, RefreshCw } from "lucide-react";
import { Badge, Button, Card, Input } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type { CitDecodeMeasurement, CitDecodeResult, Device, DeviceCitMeasurement, TestbenchManifest } from "@/lib/types";

const AUTO_REFRESH_MS = 5000;

// s2cmsg.py STATUS_LABELS ile birebir (Turkce kisa etiketler).
const STATUS_LABELS: Record<number, string> = {
  0: "OK",
  1: "GENEL_HATA",
  2: "GECERSIZ_MESAJ",
  3: "GECERSIZ_PARAMETRE",
  4: "CIHAZ_YOK",
  5: "BUS_HATASI",
  6: "ZAMAN_ASIMI",
  7: "DESTEKLENMIYOR",
};

function statusLabel(durum: number): string {
  return STATUS_LABELS[durum] ?? `DURUM_${durum}`;
}

function timeLabel(atMs: number): string {
  const date = new Date(atMs);
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
}

function hex(value: number): string {
  return `0x${(value >>> 0).toString(16).toUpperCase().padStart(8, "0")}`;
}

/** Bu ölçüme ait store override'ı (device.config.cit.measurements[]), op ile eşlenir. */
function storeOverride(
  measurements: DeviceCitMeasurement[] | undefined,
  op: string,
): DeviceCitMeasurement | undefined {
  return measurements?.find((m) => m.op === op);
}

/**
 * Ölçümün CANLI (efektif) politikası: store override (varsa) > manifest varsayılanı.
 * Kart yalnız ham+değer+okuma-durumu döner; limit/OK-NOK/önem/enabled kararı HOST'ta,
 * store'daki güncel değerlerle burada hesaplanır (koda gömülü değil, ekrandan canlı).
 */
type Effective = {
  name: string;
  min: number | null;
  max: number | null;
  severity: "critical" | "warning";
  enabled: boolean;
  readOk: boolean; // kart okuma başarısı (durum === 0)
  limitOk: boolean; // limit yok VEYA değer aralıkta
  ok: boolean; // readOk && limitOk — ekranda gösterilen verdict
};

function effectiveOf(measurement: CitDecodeMeasurement, device: Device | undefined): Effective {
  const override = storeOverride(device?.config?.cit?.measurements, measurement.op);
  const name = override?.name ?? measurement.name;
  // Override VARSA değerleri olduğu gibi kullan (kullanıcı limiti bilerek boşalttıysa null = limitsiz).
  const min = override ? (override.min ?? null) : (measurement.min ?? null);
  const max = override ? (override.max ?? null) : (measurement.max ?? null);
  const severityRaw = override?.severity ?? measurement.severity;
  const severity = severityRaw === "critical" ? "critical" : "warning";
  const enabled = override?.enabled ?? measurement.enabled;
  const readOk = measurement.durum === 0;
  const limitOk = min === null || max === null ? true : measurement.value >= min && measurement.value <= max;
  return { name, min, max, severity, enabled, readOk, limitOk, ok: readOk && limitOk };
}

function badgeTone(measurement: CitDecodeMeasurement, eff: Effective): "danger" | "warn" | "ok" | "neutral" {
  if (measurement.durum === 7) return "neutral"; // eski firmware / desteklenmiyor
  if (measurement.durum !== 0) return "danger";
  if (eff.ok) return "ok";
  return eff.severity === "critical" ? "danger" : "warn";
}

function badgeLabel(measurement: CitDecodeMeasurement, eff: Effective): string {
  if (measurement.durum !== 0) return statusLabel(measurement.durum);
  return eff.ok ? "OK" : "NOK";
}

export default function CitPanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const devices = useStore((s) => s.devices);
  const updateDevice = useStore((s) => s.updateDevice);

  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  const board = useBoardConnection();
  const sessionId = board.sessionId;
  const connected = board.connected;

  const [result, setResult] = useState<CitDecodeResult | null>(null);
  const [lastRunAt, setLastRunAt] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState("");
  const [editingOp, setEditingOp] = useState<string>("");
  const [editDraft, setEditDraft] = useState<{ name: string; min: string; max: string; severity: "critical" | "warning" }>(
    { name: "", min: "", max: "", severity: "warning" },
  );
  const runningRef = useRef(false);

  const hasCit = Boolean(manifest?.cit?.olcumler?.length);

  async function runCit(kind: "run" | "read") {
    if (!manifest || !hasCit || !connected || runningRef.current) return;
    runningRef.current = true;
    setBusy(true);
    setError("");
    try {
      const response = kind === "run"
        ? await api.citRun(sessionId, manifest, board.timeoutSeconds())
        : await api.citRead(sessionId, manifest, board.timeoutSeconds());
      setResult(response);
      setLastRunAt(Date.now());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      runningRef.current = false;
      setBusy(false);
    }
  }

  // Periyodik otomatik yenile: CIT_READ (yeniden koşturmadan, son sonucu okur).
  useEffect(() => {
    if (!autoRefresh || !connected || !hasCit) return;
    let cancelled = false;
    const timer = window.setInterval(() => {
      if (cancelled) return;
      void runCit("read");
    }, AUTO_REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, connected, hasCit, sessionId, manifest]);

  function deviceForMeasurement(measurement: CitDecodeMeasurement) {
    return devices.find((d) => d.id === measurement.device);
  }

  function startEdit(measurement: CitDecodeMeasurement) {
    const eff = effectiveOf(measurement, deviceForMeasurement(measurement));
    setEditingOp(measurement.op + "|" + measurement.device);
    setEditDraft({
      name: eff.name,
      min: eff.min === null ? "" : String(eff.min),
      max: eff.max === null ? "" : String(eff.max),
      severity: eff.severity,
    });
  }

  function cancelEdit() {
    setEditingOp("");
  }

  /** Bir ölçümün store override'ını (op ile) günceller/ekler — anında canlı yansır. */
  function writeOverride(measurement: CitDecodeMeasurement, patch: Partial<DeviceCitMeasurement>) {
    const device = deviceForMeasurement(measurement);
    if (!device) return;
    const existing = device.config?.cit?.measurements ?? [];
    const current = storeOverride(existing, measurement.op);
    const next: DeviceCitMeasurement = {
      op: measurement.op,
      name: current?.name,
      min: current?.min,
      max: current?.max,
      severity: current?.severity ?? (measurement.severity === "critical" ? "critical" : "warning"),
      enabled: current?.enabled ?? measurement.enabled,
      ...patch,
    };
    const filtered = existing.filter((m) => m.op !== measurement.op);
    updateDevice(device.id, {
      config: { ...device.config, cit: { measurements: [...filtered, next] } },
    });
  }

  function saveEdit(measurement: CitDecodeMeasurement) {
    const min = editDraft.min.trim() === "" ? undefined : Number(editDraft.min);
    const max = editDraft.max.trim() === "" ? undefined : Number(editDraft.max);
    writeOverride(measurement, {
      name: editDraft.name.trim() || undefined,
      min: Number.isFinite(min as number) ? min : undefined,
      max: Number.isFinite(max as number) ? max : undefined,
      severity: editDraft.severity,
    });
    setEditingOp("");
  }

  function toggleEnabled(measurement: CitDecodeMeasurement) {
    const eff = effectiveOf(measurement, deviceForMeasurement(measurement));
    writeOverride(measurement, { enabled: !eff.enabled });
  }

  if (!manifest || !hasCit) {
    return (
      <Card className="mx-auto max-w-3xl p-6">
        <div className="flex items-start gap-3">
          <HeartPulse className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
          <div>
            <h2 className="text-sm font-semibold text-text">CİT sayfası hazır değil</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {!manifest
                ? "Bu ekran, kartı tek atımda test eden CİT (Cihaz İçi Test) koşusunun ham + işlenmiş ölçümlerini ve OK/NOK durumunu gösterir. Önce Generate çalıştır."
                : "Bu üretimde CİT olcumu yok: hiçbir cihazda birimli okuma (voltage_read/temperature_read gibi) op'u seçilmemiş. Şematik ekranından cihaz operasyonlarını gözden geçir."}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const measurements = result?.olcumler ?? [];
  const rows = measurements.map((m) => ({ m, eff: effectiveOf(m, deviceForMeasurement(m)) }));
  const activeRows = rows.filter((r) => r.eff.enabled);
  const disabledCount = rows.length - activeRows.length;
  const criticalNok = activeRows.filter((r) => !r.eff.ok && r.eff.severity === "critical").length;
  const warningNok = activeRows.filter((r) => !r.eff.ok && r.eff.severity !== "critical").length;
  const okCount = activeRows.filter((r) => r.eff.ok).length;

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <Card className="shrink-0 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <HeartPulse className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-sm font-semibold text-text">CİT — Cihaz İçi Test</span>
            <Badge tone={connected ? "ok" : "neutral"}>{connected ? "bağlı" : "kopuk"}</Badge>
          </div>

          <Badge tone={criticalNok > 0 ? "danger" : "neutral"}>kritik NOK {criticalNok}</Badge>
          <Badge tone={warningNok > 0 ? "warn" : "neutral"}>uyarı NOK {warningNok}</Badge>
          <Badge tone="ok">OK {okCount}</Badge>
          {disabledCount > 0 ? <Badge tone="neutral">kapalı: {disabledCount}</Badge> : null}
          {result?.desteklenmiyor ? <Badge tone="warn">DESTEKLENMIYOR</Badge> : null}

          <span className="text-[11px] text-faint">
            {lastRunAt ? `son koşu ${timeLabel(lastRunAt)}` : "henüz koşulmadı"}
            {result ? ` · sayaç ${result.sayac}` : ""}
          </span>

          <span className="ml-auto flex items-center gap-2">
            <Button size="sm" onClick={() => void runCit("run")} disabled={!connected || busy}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Activity className="h-4 w-4" aria-hidden />}
              CİT koştur
            </Button>
            <Button size="sm" variant="outline" onClick={() => void runCit("read")} disabled={!connected || busy}>
              <RefreshCw className="h-4 w-4" aria-hidden /> Son CİT'i oku
            </Button>
            <Button
              size="sm"
              variant={autoRefresh ? "outline" : "ghost"}
              onClick={() => setAutoRefresh((v) => !v)}
              title="5 sn'de bir Son CİT'i oku"
            >
              {autoRefresh ? <Pause className="h-4 w-4" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
              oto-yenile
            </Button>
          </span>
        </div>
        <p className="mt-1.5 text-[11px] text-faint">
          Limit / önem / aç-kapa değişiklikleri <b className="text-muted">anında</b> uygulanır — kod üretmeye ya da
          karta yeniden yüklemeye gerek yok. Bağlantı üstteki ortak karttan (Test Bench) gelir.
        </p>
        {error ? (
          <p className="mt-2 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
        ) : null}
      </Card>

      <Card className="min-h-0 flex-1 overflow-auto p-0">
        {measurements.length === 0 ? (
          <div className="p-6 text-center text-xs text-faint">
            {connected
              ? "Henüz veri yok — \"CİT koştur\" ile kartı tek atımda test et."
              : "Önce karta bağlan, sonra \"CİT koştur\"."}
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-elev">
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
                <th className="px-3 py-2">Ad</th>
                <th className="px-3 py-2">Cihaz</th>
                <th className="px-3 py-2">Ham</th>
                <th className="px-3 py-2">Değer</th>
                <th className="px-3 py-2">Min/Max</th>
                <th className="px-3 py-2">Önem</th>
                <th className="px-3 py-2">Durum</th>
                <th className="px-3 py-2">Düzenle</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {rows.map(({ m: measurement, eff }) => {
                const device = deviceForMeasurement(measurement);
                const editKey = measurement.op + "|" + measurement.device;
                const editing = editingOp === editKey;
                return (
                  <tr key={editKey} className={cn(!eff.enabled && "opacity-50")}>
                    <td className="px-3 py-1.5 font-mono text-text">{eff.name}</td>
                    <td className="px-3 py-1.5 font-mono text-faint">
                      {measurement.part} · {measurement.device}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-faint">{hex(measurement.raw)}</td>
                    <td className="px-3 py-1.5 font-mono text-text">
                      {measurement.value}
                      {measurement.unit ? <span className="text-faint"> {measurement.unit}</span> : null}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-muted">
                      {editing ? (
                        <div className="flex items-center gap-1">
                          <Input
                            value={editDraft.min}
                            onChange={(e) => setEditDraft((d) => ({ ...d, min: e.target.value }))}
                            placeholder="min"
                            className="h-6 w-16 px-1 text-[11px]"
                          />
                          <span>..</span>
                          <Input
                            value={editDraft.max}
                            onChange={(e) => setEditDraft((d) => ({ ...d, max: e.target.value }))}
                            placeholder="max"
                            className="h-6 w-16 px-1 text-[11px]"
                          />
                        </div>
                      ) : eff.min !== null && eff.max !== null ? (
                        `${eff.min}..${eff.max}`
                      ) : (
                        "limitsiz"
                      )}
                    </td>
                    <td className="px-3 py-1.5">
                      {editing ? (
                        <select
                          value={editDraft.severity}
                          onChange={(e) => setEditDraft((d) => ({ ...d, severity: e.target.value as "critical" | "warning" }))}
                          className="h-6 rounded-md border border-border bg-inset px-1 font-mono text-[11px] text-text"
                        >
                          <option value="warning">warning</option>
                          <option value="critical">critical</option>
                        </select>
                      ) : (
                        <Badge tone={eff.severity === "critical" ? "danger" : "neutral"}>{eff.severity}</Badge>
                      )}
                    </td>
                    <td className="px-3 py-1.5">
                      <Badge tone={badgeTone(measurement, eff)}>{badgeLabel(measurement, eff)}</Badge>
                    </td>
                    <td className="px-3 py-1.5">
                      {editing ? (
                        <div className="flex items-center gap-1">
                          <Input
                            value={editDraft.name}
                            onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))}
                            placeholder="isim"
                            className="h-6 w-28 px-1 text-[11px]"
                          />
                          <Button size="sm" variant="ghost" className="h-6 px-2 text-ok" onClick={() => saveEdit(measurement)}>
                            kaydet
                          </Button>
                          <Button size="sm" variant="ghost" className="h-6 px-2 text-faint" onClick={cancelEdit}>
                            iptal
                          </Button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-muted hover:text-accent"
                            onClick={() => startEdit(measurement)}
                            disabled={!device}
                            title={device ? "isim/limit/önem düzenle (anında uygulanır)" : "cihaz spec'te bulunamadı"}
                          >
                            düzenle
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-faint"
                            onClick={() => toggleEnabled(measurement)}
                            disabled={!device}
                            title={eff.enabled ? "devre dışı bırak" : "etkinleştir"}
                          >
                            {eff.enabled ? "kapat" : "aç"}
                          </Button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
