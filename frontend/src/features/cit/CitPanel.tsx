import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Check, Cpu, HeartPulse, Loader2, Pause, Pencil, Play, Power, RefreshCw, X } from "lucide-react";
import { Badge, Button, Card, Input } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import { MAIN_BOARD_ID } from "@/lib/boards";
import type {
  CitDecodeMeasurement,
  CitDecodeResult,
  Device,
  DeviceCitMeasurement,
  TestbenchManifest,
  TestbenchManifestDevice,
} from "@/lib/types";

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

/** Henüz koşulmamış ölçüm: manifestten türetilen yer tutucu (durum -1). */
const PENDING_DURUM = -1;

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

/** Değer + birim: sıcaklık "0.01 C" -> °C; voltajlar TAM SAYI mV (unsigned short, ondalık yok). */
function formatValue(value: number, unit: string | null): { text: string; unit: string } {
  if (unit === "0.01 C") return { text: (value / 100).toFixed(2), unit: "°C" };
  if (unit === "mV") return { text: String(Math.round(value)), unit: "mV" };
  return { text: String(value), unit: unit ?? "" };
}

/** Op adı -> kanal grubu başlığı (dizi dönüşlü op'lar için). */
function channelGroupTitle(op: string, unit: string | null): string {
  const base = op === "voltage_read" ? "Voltaj kanalları" : op === "current_read" ? "Akım kanalları" : op;
  return unit ? `${base} · ${unit}` : base;
}

/** Op adı -> kısa okunur etiket (skaler ölçüm satırı için). */
function opLabel(op: string): string {
  const map: Record<string, string> = {
    temperature_read: "Sıcaklık",
    voltage_read: "Voltaj",
    current_read: "Akım",
    power_read: "Güç",
    sense_read: "Şönt gerilimi",
    adin_read: "ADIN",
    vcc_read: "VCC",
    vout_read: "VOUT",
    humidity_read: "Nem",
    elapsed_read: "Geçen süre",
    pll1_lock_detect: "PLL1 kilit",
    pll2_lock_detect: "PLL2 kilit",
    pll1_lock_loss: "PLL1 kilit kaybı",
    pll2_lock_loss: "PLL2 kilit kaybı",
    multiplier_lock_detect: "Çarpan kilit",
  };
  return map[op] ?? op;
}

const BUS_ACCENT: Record<string, string> = {
  i2c: "border-l-bus-i2c",
  spi: "border-l-bus-spi",
  qspi: "border-l-bus-qspi",
  gpio: "border-l-bus-gpio",
};

/** Bu ölçüme ait store override'ı (device.config.cit.measurements[]), op + kanal ile eşlenir. */
function storeOverride(
  measurements: DeviceCitMeasurement[] | undefined,
  op: string,
  channel: number | undefined,
): DeviceCitMeasurement | undefined {
  return measurements?.find((m) => m.op === op && (m.channel ?? undefined) === channel);
}

/** Kanalsız (genel) override: kanallı op'ta limit/önem/enabled'ı bütün kanallara uygular. */
function genericOverride(
  measurements: DeviceCitMeasurement[] | undefined,
  op: string,
): DeviceCitMeasurement | undefined {
  return measurements?.find((m) => m.op === op && m.channel === undefined);
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
  pending: boolean; // henüz koşulmadı
  readOk: boolean; // kart okuma başarısı (durum === 0)
  limitOk: boolean; // limit yok VEYA değer aralıkta
  ok: boolean; // readOk && limitOk — ekranda gösterilen verdict
};

function effectiveOf(measurement: CitDecodeMeasurement, device: Device | undefined): Effective {
  const list = device?.config?.cit?.measurements;
  const exact = storeOverride(list, measurement.op, measurement.channel);
  // Kanallı ölçümde kanalsız override limit/önem/enabled'ı verir (isim hariç) — codegen ile aynı kural.
  const generic = measurement.channel !== undefined ? genericOverride(list, measurement.op) : undefined;
  const override = exact ?? generic;
  const name = exact?.name ?? measurement.name;
  // Override VARSA değerleri olduğu gibi kullan (kullanıcı limiti bilerek boşalttıysa null = limitsiz).
  const min = override ? (override.min ?? null) : (measurement.min ?? null);
  const max = override ? (override.max ?? null) : (measurement.max ?? null);
  const severityRaw = override?.severity ?? measurement.severity;
  const severity = severityRaw === "critical" ? "critical" : "warning";
  const enabled = override?.enabled ?? measurement.enabled;
  const pending = measurement.durum === PENDING_DURUM;
  const readOk = measurement.durum === 0;
  const limitOk = min === null || max === null ? true : measurement.value >= min && measurement.value <= max;
  return { name, min, max, severity, enabled, pending, readOk, limitOk, ok: readOk && limitOk };
}

type Tone = "danger" | "warn" | "ok" | "neutral";

function badgeTone(measurement: CitDecodeMeasurement, eff: Effective): Tone {
  if (eff.pending) return "neutral";
  if (measurement.durum === 7) return "neutral"; // eski firmware / desteklenmiyor
  if (measurement.durum !== 0) return "danger";
  if (eff.ok) return "ok";
  return eff.severity === "critical" ? "danger" : "warn";
}

function badgeLabel(measurement: CitDecodeMeasurement, eff: Effective): string {
  if (eff.pending) return "—";
  if (measurement.durum !== 0) return statusLabel(measurement.durum);
  return eff.ok ? "OK" : "NOK";
}

const TONE_TEXT: Record<Tone, string> = {
  danger: "text-danger",
  warn: "text-warn",
  ok: "text-ok",
  neutral: "text-faint",
};
const TONE_DOT: Record<Tone, string> = {
  danger: "bg-danger",
  warn: "bg-warn",
  ok: "bg-ok",
  neutral: "bg-faint/50",
};
const TONE_TILE: Record<Tone, string> = {
  danger: "border-danger/50 bg-danger/10",
  warn: "border-warn/50 bg-warn/10",
  ok: "border-ok/40 bg-ok/[0.07]",
  neutral: "border-border bg-inset/60",
};

type Row = { m: CitDecodeMeasurement; eff: Effective; key: string };

/** Özet rozeti: en kötü durum kazanır (kritik > uyarı > OK); kapalı-only grup "kapalı". */
function summaryOf(rows: Row[]): { label: string; tone: Tone } {
  const active = rows.filter((r) => r.eff.enabled);
  if (active.length === 0) return { label: "kapalı", tone: "neutral" };
  if (active.every((r) => r.eff.pending)) return { label: `${active.length} ölçüm`, tone: "neutral" };
  const critical = active.filter((r) => !r.eff.pending && !r.eff.ok && r.eff.severity === "critical").length;
  const warning = active.filter((r) => !r.eff.pending && !r.eff.ok && r.eff.severity !== "critical").length;
  if (critical > 0) return { label: `${critical} kritik NOK`, tone: "danger" };
  if (warning > 0) return { label: `${warning} uyarı NOK`, tone: "warn" };
  const ok = active.filter((r) => r.eff.ok).length;
  return { label: `${ok}/${active.length} OK`, tone: "ok" };
}

/** Manifestten yer tutucu ölçüm listesi (koşu öncesi kutular boş değerle durur). */
function pendingMeasurements(manifest: TestbenchManifest): CitDecodeMeasurement[] {
  return (manifest.cit?.olcumler ?? []).map((m) => ({
    index: m.index,
    name: m.name,
    cname: m.cname,
    part: m.part,
    device: m.device,
    board_id: m.board_id ?? MAIN_BOARD_ID,
    op: m.op,
    unit: m.unit ?? null,
    raw: 0,
    value: 0,
    read_ok: false,
    durum: PENDING_DURUM,
    min: m.min ?? null,
    max: m.max ?? null,
    severity: m.severity,
    enabled: m.enabled,
    channel: m.channel,
    channels: m.channels,
    channel_label: m.channel_label,
  }));
}

type DeviceGroup = {
  id: string;
  manifestDevice: TestbenchManifestDevice | undefined;
  boardId: string;
  rows: Row[];
};

/** Entegre kutularini PARCA adina gore satirlara boler (ilk gorunme sirasi korunur). */
function partRowsOf(groups: DeviceGroup[]): { part: string; groups: DeviceGroup[] }[] {
  const rows: { part: string; groups: DeviceGroup[] }[] = [];
  for (const group of groups) {
    const part = group.rows[0]?.m.part ?? group.manifestDevice?.part ?? group.id;
    const row = rows.find((r) => r.part === part);
    if (row) row.groups.push(group);
    else rows.push({ part, groups: [group] });
  }
  return rows;
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
  const [editingKey, setEditingKey] = useState<string>("");
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

  function keyOf(measurement: CitDecodeMeasurement): string {
    return `${measurement.device}|${measurement.op}|${measurement.channel ?? ""}`;
  }

  function startEdit(measurement: CitDecodeMeasurement) {
    const eff = effectiveOf(measurement, deviceForMeasurement(measurement));
    setEditingKey(keyOf(measurement));
    setEditDraft({
      name: eff.name,
      min: eff.min === null ? "" : String(eff.min),
      max: eff.max === null ? "" : String(eff.max),
      severity: eff.severity,
    });
  }

  function cancelEdit() {
    setEditingKey("");
  }

  /** Bir ölçümün store override'ını (op + kanal ile) günceller/ekler — anında canlı yansır. */
  function writeOverride(measurement: CitDecodeMeasurement, patch: Partial<DeviceCitMeasurement>) {
    const device = deviceForMeasurement(measurement);
    if (!device) return;
    const existing = device.config?.cit?.measurements ?? [];
    const current = storeOverride(existing, measurement.op, measurement.channel);
    const generic = measurement.channel !== undefined ? genericOverride(existing, measurement.op) : undefined;
    const base = current ?? generic;
    const next: DeviceCitMeasurement = {
      op: measurement.op,
      ...(measurement.channel !== undefined ? { channel: measurement.channel } : {}),
      name: current?.name,
      min: base?.min,
      max: base?.max,
      severity: base?.severity ?? (measurement.severity === "critical" ? "critical" : "warning"),
      enabled: base?.enabled ?? measurement.enabled,
      ...patch,
    };
    const filtered = existing.filter(
      (m) => !(m.op === measurement.op && (m.channel ?? undefined) === measurement.channel),
    );
    updateDevice(device.id, {
      config: { ...device.config, cit: { measurements: [...filtered, next] } },
    });
  }

  function saveEdit(measurement: CitDecodeMeasurement) {
    const min = editDraft.min.trim() === "" ? undefined : Number(editDraft.min);
    const max = editDraft.max.trim() === "" ? undefined : Number(editDraft.max);
    // Isim formda yok: mevcut override adi (varsa) korunur, varsayilan ad spec'ten gelmeye devam eder.
    writeOverride(measurement, {
      min: Number.isFinite(min as number) ? min : undefined,
      max: Number.isFinite(max as number) ? max : undefined,
      severity: editDraft.severity,
    });
    setEditingKey("");
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

  // Koşu sonucu yoksa manifestten yer tutucular: her entegre kutusu koşu öncesi de yerinde durur.
  const measurements: CitDecodeMeasurement[] = result?.olcumler?.length ? result.olcumler : pendingMeasurements(manifest);
  const rows: Row[] = measurements.map((m) => ({ m, eff: effectiveOf(m, deviceForMeasurement(m)), key: keyOf(m) }));
  const activeRows = rows.filter((r) => r.eff.enabled && !r.eff.pending);
  const disabledCount = rows.filter((r) => !r.eff.enabled).length;
  const criticalNok = activeRows.filter((r) => !r.eff.ok && r.eff.severity === "critical").length;
  const warningNok = activeRows.filter((r) => !r.eff.ok && r.eff.severity !== "critical").length;
  const okCount = activeRows.filter((r) => r.eff.ok).length;

  // Entegre başına gruplama — manifest devices[] sırası (her entegrenin yeri sabittir).
  const manifestDevices = manifest.devices ?? [];
  const deviceOrder = new Map(manifestDevices.map((d, i) => [d.id, i] as const));
  const groupsById = new Map<string, DeviceGroup>();
  for (const row of rows) {
    let group = groupsById.get(row.m.device);
    if (!group) {
      group = {
        id: row.m.device,
        manifestDevice: manifestDevices.find((d) => d.id === row.m.device),
        boardId: row.m.board_id || MAIN_BOARD_ID,
        rows: [],
      };
      groupsById.set(row.m.device, group);
    }
    group.rows.push(row);
  }
  const deviceGroups = [...groupsById.values()].sort(
    (a, b) => (deviceOrder.get(a.id) ?? 999) - (deviceOrder.get(b.id) ?? 999),
  );

  // Kart başlıkları YALNIZ proje kart tanımlıyken (manifest.boards dolu).
  const boardList = manifest.boards ?? [];
  const boardsDeclared = boardList.length > 0;
  const boardSections: { boardId: string; boardName: string; groups: DeviceGroup[] }[] = boardsDeclared
    ? boardList
        .map((b) => ({
          boardId: b.id,
          boardName: b.name,
          groups: deviceGroups.filter((g) => g.boardId === b.id),
        }))
        .filter((s) => s.groups.length > 0)
    : [{ boardId: MAIN_BOARD_ID, boardName: "", groups: deviceGroups }];

  function renderEditForm(measurement: CitDecodeMeasurement) {
    // Tek satir: min .. max | onem | kaydet / iptal (isim tekrar yazilmaz; ad ustte zaten gorunur).
    return (
      <div className="mt-2 flex flex-nowrap items-center gap-1 rounded-md border border-accent/30 bg-inset/70 px-1.5 py-1">
        <Input
          value={editDraft.min}
          onChange={(e) => setEditDraft((d) => ({ ...d, min: e.target.value }))}
          placeholder="min"
          className="h-6 w-14 min-w-0 px-1 font-mono text-[11px]"
        />
        <span className="text-[11px] text-faint">..</span>
        <Input
          value={editDraft.max}
          onChange={(e) => setEditDraft((d) => ({ ...d, max: e.target.value }))}
          placeholder="max"
          className="h-6 w-14 min-w-0 px-1 font-mono text-[11px]"
        />
        <select
          value={editDraft.severity}
          onChange={(e) => setEditDraft((d) => ({ ...d, severity: e.target.value as "critical" | "warning" }))}
          className="h-6 min-w-0 flex-1 rounded-md border border-border bg-inset px-1 font-mono text-[11px] text-text"
        >
          <option value="warning">warning</option>
          <option value="critical">critical</option>
        </select>
        <button
          type="button"
          className="rounded p-1 text-ok hover:bg-inset"
          onClick={() => saveEdit(measurement)}
          title="kaydet"
        >
          <Check className="h-3.5 w-3.5" aria-hidden />
        </button>
        <button type="button" className="rounded p-1 text-faint hover:bg-inset" onClick={cancelEdit} title="iptal">
          <X className="h-3.5 w-3.5" aria-hidden />
        </button>
      </div>
    );
  }

  function renderActions(measurement: CitDecodeMeasurement, eff: Effective, device: Device | undefined) {
    return (
      <span className="flex shrink-0 items-center gap-0.5">
        <button
          type="button"
          className="rounded p-1 text-faint hover:bg-inset hover:text-accent disabled:opacity-40"
          onClick={() => startEdit(measurement)}
          disabled={!device}
          title={device ? "isim/limit/önem düzenle (anında uygulanır)" : "cihaz spec'te bulunamadı"}
        >
          <Pencil className="h-3 w-3" aria-hidden />
        </button>
        <button
          type="button"
          className={cn(
            "rounded p-1 hover:bg-inset disabled:opacity-40",
            eff.enabled ? "text-faint hover:text-warn" : "text-warn hover:text-ok",
          )}
          onClick={() => toggleEnabled(measurement)}
          disabled={!device}
          title={eff.enabled ? "devre dışı bırak" : "etkinleştir"}
        >
          <Power className="h-3 w-3" aria-hidden />
        </button>
      </span>
    );
  }

  /** Skaler ölçüm satırı: ad, değer (büyük), limit, durum, düzenle. */
  function renderScalarRow({ m: measurement, eff, key }: Row) {
    const device = deviceForMeasurement(measurement);
    const tone = badgeTone(measurement, eff);
    const shown = formatValue(measurement.value, measurement.unit);
    const editing = editingKey === key;
    return (
      <div key={key} className={cn("rounded-md border border-border/60 bg-inset/40 px-2.5 py-2", !eff.enabled && "opacity-50")}>
        {/* 1. satır: durum noktası + tam isim (kırpılmaz, gerekirse kırılır) + rozet + eylemler */}
        <div className="flex items-start gap-2">
          <span className={cn("mt-1 h-2 w-2 shrink-0 rounded-full", TONE_DOT[tone])} aria-hidden />
          <div className="min-w-0 flex-1 break-all font-mono text-[11px] leading-4 text-text">{eff.name}</div>
          <Badge tone={tone} className="shrink-0 justify-center">{badgeLabel(measurement, eff)}</Badge>
          {renderActions(measurement, eff, device)}
        </div>
        {/* 2. satır: op etiketi + limit (sol) · değer (sağ) */}
        <div className="mt-0.5 flex items-baseline gap-2 pl-4">
          <div className="min-w-0 flex-1 text-[10px] text-faint">
            {opLabel(measurement.op)}
            {eff.min !== null && eff.max !== null ? ` · ${eff.min}..${eff.max}` : " · limitsiz"}
            {eff.severity === "critical" ? " · kritik" : ""}
          </div>
          <div className="shrink-0 text-right" title={eff.pending ? "henüz koşulmadı" : `ham ${hex(measurement.raw)}`}>
            <span className={cn("font-mono text-base font-semibold tabular-nums", TONE_TEXT[tone])}>
              {eff.pending ? "—" : shown.text}
            </span>
            {!eff.pending && shown.unit ? <span className="ml-1 text-[10px] text-faint">{shown.unit}</span> : null}
          </div>
        </div>
        {editing ? renderEditForm(measurement) : null}
      </div>
    );
  }

  /** Kanal karosu (V1..V8): etiket, değer, durum; tıklayınca düzenleme şeridi açılır. */
  function renderChannelTile({ m: measurement, eff, key }: Row) {
    const tone = badgeTone(measurement, eff);
    const shown = formatValue(measurement.value, measurement.unit);
    const selected = editingKey === key;
    const customName = eff.name !== measurement.name || !/_V\d+_\d+$|_I\d+_\d+$/.test(eff.name);
    return (
      <button
        type="button"
        key={key}
        onClick={() => (selected ? cancelEdit() : startEdit(measurement))}
        title={`${eff.name} · ${eff.min !== null && eff.max !== null ? `${eff.min}..${eff.max}` : "limitsiz"} · ${
          eff.pending ? "henüz koşulmadı" : `ham ${hex(measurement.raw)}`
        }`}
        className={cn(
          "flex flex-col items-start rounded-md border px-2 py-1.5 text-left transition-colors",
          TONE_TILE[tone],
          selected && "ring-1 ring-accent",
          !eff.enabled && "opacity-45",
        )}
      >
        <span className="flex w-full items-center justify-between">
          <span className="font-mono text-[10px] font-semibold text-muted">{measurement.channel_label ?? `CH${(measurement.channel ?? 0) + 1}`}</span>
          <span className={cn("h-1.5 w-1.5 rounded-full", TONE_DOT[tone])} aria-hidden />
        </span>
        <span className={cn("font-mono text-sm font-semibold tabular-nums", TONE_TEXT[tone])}>
          {eff.pending ? "—" : shown.text}
        </span>
        {customName ? (
          <span className="w-full truncate font-mono text-[9px] text-faint" title={eff.name}>
            {eff.name}
          </span>
        ) : null}
      </button>
    );
  }

  function renderDeviceCard(group: DeviceGroup) {
    const summary = summaryOf(group.rows);
    const md = group.manifestDevice;
    const part = group.rows[0]?.m.part ?? md?.part ?? group.id;
    const transport = (md?.transport ?? "").toLowerCase();
    const attach = md?.attach;
    const addr = attach?.i2c_address
      ? `${attach.i2c_address}`
      : attach?.spi_chip_select !== undefined && attach?.spi_chip_select !== null
        ? `CS${attach.spi_chip_select}`
        : "";
    const mux = attach?.via_mux ? ` · ${attach.via_mux.mux_id} ch${attach.via_mux.channel}` : "";
    const simulated = Boolean(md?.simulated);

    // Kanallı ölçümler op'a göre gruplanır (V1..V8 karoları), skalerler satır olur.
    const scalarRows = group.rows.filter((r) => r.m.channel === undefined);
    const channelOps = new Map<string, Row[]>();
    for (const row of group.rows) {
      if (row.m.channel === undefined) continue;
      const list = channelOps.get(row.m.op) ?? [];
      list.push(row);
      channelOps.set(row.m.op, list);
    }
    const editingChannelRow = group.rows.find((r) => r.m.channel !== undefined && r.key === editingKey);

    return (
      <Card
        key={group.id}
        className={cn(
          "flex h-full min-w-0 flex-col gap-2 border-l-4 p-3",
          BUS_ACCENT[transport] ?? "border-l-border",
          simulated && "border-dashed bg-[#5b2a86]/20",
        )}
      >
        <div className="flex items-start gap-2">
          <div className={cn("mt-0.5 rounded-md p-1.5", simulated ? "bg-[#7c3aed]/30 text-[#d8b4fe]" : "bg-inset text-accent")}>
            <Cpu className="h-4 w-4" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-sm font-semibold text-text">{part}</span>
              {simulated ? <Badge className="border border-[#c084fc]/60 bg-[#7c3aed]/30 text-[#f3e8ff]">SANAL</Badge> : null}
              {transport ? <Badge tone="neutral" className="uppercase">{transport}</Badge> : null}
            </div>
            <div className="truncate font-mono text-[10px] text-faint">
              {group.id}
              {addr ? ` · ${addr}` : ""}
              {mux}
            </div>
          </div>
          <Badge tone={summary.tone} className="shrink-0">{summary.label}</Badge>
        </div>

        {[...channelOps.entries()].map(([op, list]) => (
          <div key={op} className="rounded-md border border-border/60 bg-inset/30 p-2">
            <div className="mb-1.5 flex items-center justify-between gap-2">
              <span className="truncate text-[10px] font-semibold uppercase tracking-wide text-muted">
                {channelGroupTitle(op, list[0]?.m.unit ?? null)}
              </span>
              <span className="shrink-0 text-[10px] text-faint" title="karoya tıkla: isim/limit düzenle">{list.length} kanal</span>
            </div>
            <div className="grid grid-cols-4 gap-1.5">{list.map(renderChannelTile)}</div>
            {editingChannelRow && editingChannelRow.m.op === op ? (
              <div className="mt-1">
                <div className="mt-1 flex items-center justify-between text-[10px] text-faint">
                  <span>
                    {editingChannelRow.m.channel_label} · {editingChannelRow.eff.name}
                  </span>
                  {renderActions(editingChannelRow.m, editingChannelRow.eff, deviceForMeasurement(editingChannelRow.m))}
                </div>
                {renderEditForm(editingChannelRow.m)}
              </div>
            ) : null}
          </div>
        ))}

        {scalarRows.length > 0 ? <div className="flex flex-col gap-1.5">{scalarRows.map(renderScalarRow)}</div> : null}
      </Card>
    );
  }

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
            {` · ${deviceGroups.length} entegre · ${rows.length} ölçüm`}
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
          Her entegre kendi kutusunda; limit / önem / aç-kapa değişiklikleri <b className="text-muted">anında</b> uygulanır —
          kod üretmeye ya da karta yeniden yüklemeye gerek yok. Bağlantı üstteki ortak karttan (Test Bench) gelir.
          {!result ? (connected ? ' Değerler için "CİT koştur".' : " Önce karta bağlan.") : ""}
        </p>
        {error ? (
          <p className="mt-2 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
        ) : null}
      </Card>

      <div className="min-h-0 flex-1 overflow-auto pr-1">
        {boardSections.map((section) => (
          <div key={section.boardId} className="mb-4">
            {boardsDeclared ? (
              <div className="mb-2 flex items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-text">{section.boardName}</span>
                <Badge tone={summaryOf(section.groups.flatMap((g) => g.rows)).tone}>
                  {summaryOf(section.groups.flatMap((g) => g.rows)).label}
                </Badge>
              </div>
            ) : null}
            {/* Her satirda TEK entegre tipi (parca adi): ayni parcadan 3 tane varsa ucu yan yana,
                tek ise satirda yalniz o. Satir sirasi = manifestteki ilk gorunme sirasi. */}
            {partRowsOf(section.groups).map((row) => (
              <div key={row.part} className="mb-3">
                <div className="mb-1.5 flex items-center gap-2 border-b border-border/60 pb-1">
                  <span className="font-mono text-[11px] font-semibold text-text">{row.part}</span>
                  <span className="text-[10px] text-faint">
                    {row.groups.length > 1 ? `${row.groups.length} adet` : "1 adet"}
                  </span>
                  <Badge tone={summaryOf(row.groups.flatMap((g) => g.rows)).tone} className="ml-auto">
                    {summaryOf(row.groups.flatMap((g) => g.rows)).label}
                  </Badge>
                </div>
                <div className="flex flex-wrap gap-3">
                  {row.groups.map((g) => (
                    <div key={g.id} className="w-[19rem] max-w-full flex-none">
                      {renderDeviceCard(g)}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
