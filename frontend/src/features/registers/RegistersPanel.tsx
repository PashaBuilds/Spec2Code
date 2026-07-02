import { useEffect, useMemo, useState } from "react";
import { Camera, Grid3X3, Link2, Loader2, Unplug } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type {
  DescriptorRegister,
  DeviceDescriptor,
  RegisterSnapshot,
  SerialPortInfo,
  TestbenchManifest,
  TestbenchManifestDevice,
} from "@/lib/types";

interface StoredSnapshot {
  taken_at: number;
  values: Record<string, string>;
}

function makeSessionId(): string {
  const globalCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return `rg_${globalCrypto.randomUUID()}`;
  }
  return `rg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

function historyKey(project: string, deviceId: string): string {
  return `spec2code.regsnap.${project || "default"}.${deviceId}`;
}

function loadHistory(project: string, deviceId: string): StoredSnapshot[] {
  try {
    const raw = localStorage.getItem(historyKey(project, deviceId));
    return raw ? (JSON.parse(raw) as StoredSnapshot[]) : [];
  } catch {
    return [];
  }
}

function saveHistory(project: string, deviceId: string, history: StoredSnapshot[]): void {
  try {
    localStorage.setItem(historyKey(project, deviceId), JSON.stringify(history.slice(-8)));
  } catch {
    /* history is a convenience only */
  }
}

function parseHex(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number.parseInt(value, value.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function hex(value: number, width: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(Math.ceil(width / 4), "0")}`;
}

/** "7:4" -> [7,6,5,4]; "3" -> [3] */
function bitsOfField(bits: string): number[] {
  const match = /^(\d+)(?::(\d+))?$/.exec(bits.trim());
  if (!match) return [];
  const high = Number.parseInt(match[1], 10);
  const low = match[2] !== undefined ? Number.parseInt(match[2], 10) : high;
  const result: number[] = [];
  for (let bit = Math.max(high, low); bit >= Math.min(high, low); bit -= 1) result.push(bit);
  return result;
}

function fieldForBit(register: DescriptorRegister | undefined, bit: number) {
  return register?.fields?.find((f) => bitsOfField(f.bits).includes(bit));
}

function timeLabel(at: number): string {
  const date = new Date(at * 1000);
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
}

function BitGrid({
  width,
  actual,
  baseline,
  register,
}: {
  width: number;
  actual: number | null;
  baseline: number | null;
  register?: DescriptorRegister;
}) {
  const bits = Array.from({ length: width }, (_, i) => width - 1 - i);
  return (
    <div className="flex gap-[3px]">
      {bits.map((bit) => {
        const actualBit = actual === null ? null : (actual >> bit) & 1;
        const baseBit = baseline === null ? null : (baseline >> bit) & 1;
        const differs = actualBit !== null && baseBit !== null && actualBit !== baseBit;
        const field = fieldForBit(register, bit);
        const title = [
          `bit ${bit}${field ? ` — ${field.name}` : ""}`,
          field?.description ?? "",
          actualBit === null ? "değer yok" : `okunan=${actualBit}`,
          baseBit === null ? "" : `beklenen=${baseBit}`,
        ].filter(Boolean).join("\n");
        return (
          <span
            key={bit}
            title={title}
            className={cn(
              "grid h-5 w-5 shrink-0 place-items-center rounded-[3px] border font-mono text-[9px] leading-none",
              differs
                ? "border-danger bg-danger/25 text-danger"
                : actualBit === 1
                  ? "border-accent/50 bg-accent/20 text-accent"
                  : "border-border bg-inset text-faint",
              field && "cursor-help",
            )}
          >
            {actualBit === null ? "·" : actualBit}
          </span>
        );
      })}
    </div>
  );
}

export default function RegistersPanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  const devices = useMemo(
    () =>
      (manifest?.devices ?? []).filter(
        (device) =>
          device.registers.length > 0 &&
          device.operations.some((op) => op.name === "register_read"),
      ),
    [manifest],
  );

  const [sessionId] = useState(makeSessionId);
  const [transport, setTransport] = useState<"tcp" | "serial">(() =>
    localStorage.getItem("spec2code.testbench.transport") === "serial" ? "serial" : "tcp");
  const [host, setHost] = useState(() => localStorage.getItem("spec2code.testbench.host") ?? "127.0.0.1");
  const [port, setPort] = useState(() => localStorage.getItem("spec2code.testbench.port") ?? "5000");
  const [serialPort, setSerialPort] = useState(() => localStorage.getItem("spec2code.testbench.serialPort") ?? "");
  const [baud, setBaud] = useState(() => localStorage.getItem("spec2code.testbench.baud") ?? "115200");
  const [serialPorts, setSerialPorts] = useState<SerialPortInfo[]>([]);
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [descriptor, setDescriptor] = useState<DeviceDescriptor | null>(null);
  const [snapshot, setSnapshot] = useState<RegisterSnapshot | null>(null);
  const [history, setHistory] = useState<StoredSnapshot[]>([]);
  const [baselineKey, setBaselineKey] = useState<string>("reset");
  const [taking, setTaking] = useState(false);

  const selectedDevice: TestbenchManifestDevice | null =
    devices.find((device) => device.id === selectedDeviceId) ?? devices[0] ?? null;

  useEffect(() => {
    if (!selectedDevice) return;
    setSelectedDeviceId((current) => (devices.some((d) => d.id === current) ? current : selectedDevice.id));
    setSnapshot(null);
    setHistory(loadHistory(projectName, selectedDevice.id));
    setBaselineKey("reset");
    api.descriptor(selectedDevice.part)
      .then(setDescriptor)
      .catch(() => setDescriptor(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevice?.id, projectName]);

  useEffect(() => {
    if (transport !== "serial") return;
    api.testbenchSerialPorts()
      .then((list) => {
        setSerialPorts(list);
        setSerialPort((current) => current || list[0]?.device || "");
      })
      .catch(() => setSerialPorts([]));
  }, [transport]);

  useEffect(() => {
    return () => {
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
    };
  }, [sessionId]);

  async function connect() {
    if (busy || connected) return;
    setBusy(true);
    setError("");
    try {
      const status = await api.testbenchConnect(
        transport === "serial"
          ? { session_id: sessionId, transport: "serial", serial_port: serialPort.trim(), baud: Number.parseInt(baud, 10) || 115200, timeout_s: 5 }
          : { session_id: sessionId, transport: "tcp", host: host.trim(), port: Number.parseInt(port, 10) || 0, timeout_s: 5 },
      );
      setConnected(Boolean(status.connected));
      if (!status.connected) setError(status.last_error || "Bağlantı kurulamadı.");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    try {
      await api.testbenchDisconnect(sessionId);
    } catch {
      /* ignore */
    } finally {
      setConnected(false);
      setBusy(false);
    }
  }

  async function takeSnapshot() {
    if (!selectedDevice || !connected || taking) return;
    setTaking(true);
    setError("");
    try {
      const result = await api.registerSnapshot({
        session_id: sessionId,
        device_id: selectedDevice.id,
        registers: selectedDevice.registers.map((reg) => ({ name: reg.name, offset: reg.offset })),
        timeout_s: 5,
      });
      setSnapshot(result);
      const stored: StoredSnapshot = {
        taken_at: result.taken_at,
        values: Object.fromEntries(
          result.registers.filter((item) => item.ok).map((item) => [item.name, item.value]),
        ),
      };
      const nextHistory = [...history, stored].slice(-8);
      setHistory(nextHistory);
      saveHistory(projectName, selectedDevice.id, nextHistory);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setTaking(false);
    }
  }

  function baselineValue(regName: string): number | null {
    if (baselineKey === "reset") {
      const reg = descriptor?.registers?.find((item) => item.name === regName);
      return typeof reg?.reset === "number" ? reg.reset : null;
    }
    const stored = history.find((item) => String(item.taken_at) === baselineKey);
    return parseHex(stored?.values[regName]);
  }

  if (!manifest || devices.length === 0) {
    return (
      <Card className="mx-auto max-w-3xl p-6">
        <div className="flex items-start gap-3">
          <Grid3X3 className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
          <div>
            <h2 className="text-sm font-semibold text-text">Register görünümü hazır değil</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Bu ekran, Generate sonucu <code className="font-mono">register_read</code> operasyonu ve register
              haritası içeren cihazlar için canlı register snapshot&apos;ı alır; beklenen (reset) değerlerle bit
              bit karşılaştırır. Önce Generate çalıştır.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const diffCount = snapshot
    ? snapshot.registers.filter((item) => {
        const actual = parseHex(item.value);
        const base = baselineValue(item.name);
        return item.ok && actual !== null && base !== null && actual !== base;
      }).length
    : 0;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="min-h-0 space-y-3 overflow-auto rounded-lg border border-border bg-elev p-3">
        <div className="flex items-center gap-2">
          <Grid3X3 className="h-4 w-4 text-accent" aria-hidden />
          <span className="text-sm font-semibold text-text">Register snapshot</span>
          <Badge tone={connected ? "ok" : "neutral"}>{connected ? "bağlı" : "kopuk"}</Badge>
        </div>

        <div>
          <Label>Cihaz</Label>
          <select
            value={selectedDevice?.id ?? ""}
            onChange={(event) => setSelectedDeviceId(event.target.value)}
            className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            {devices.map((device) => (
              <option key={device.id} value={device.id}>
                {device.part} — {device.id}
              </option>
            ))}
          </select>
        </div>

        <div>
          <Label>Transport</Label>
          <div className="mt-1 grid grid-cols-2 gap-1 rounded-md border border-border bg-inset p-1">
            {(["tcp", "serial"] as const).map((option) => (
              <button
                key={option}
                type="button"
                disabled={connected || busy}
                onClick={() => setTransport(option)}
                className={cn(
                  "rounded px-2 py-1 font-mono text-[11px] font-semibold uppercase transition-colors",
                  transport === option ? "bg-accent-dim text-accent" : "text-muted hover:text-text",
                )}
              >
                {option === "tcp" ? "TCP" : "Seri"}
              </button>
            ))}
          </div>
        </div>

        {transport === "tcp" ? (
          <div className="grid grid-cols-[minmax(0,1fr)_80px] gap-2">
            <div>
              <Label>Host</Label>
              <Input value={host} onChange={(e) => setHost(e.target.value)} disabled={connected || busy} />
            </div>
            <div>
              <Label>Port</Label>
              <Input value={port} onChange={(e) => setPort(e.target.value)} disabled={connected || busy} />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-[minmax(0,1fr)_88px] gap-2">
            <div>
              <Label>Seri port</Label>
              <select
                value={serialPort}
                onChange={(e) => setSerialPort(e.target.value)}
                disabled={connected || busy}
                className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
              >
                {serialPort && !serialPorts.some((p) => p.device === serialPort) ? (
                  <option value={serialPort}>{serialPort}</option>
                ) : null}
                {serialPorts.map((info) => (
                  <option key={info.device} value={info.device}>{info.device}</option>
                ))}
              </select>
            </div>
            <div>
              <Label>Baud</Label>
              <Input value={baud} onChange={(e) => setBaud(e.target.value)} disabled={connected || busy} />
            </div>
          </div>
        )}

        <div className="flex gap-2">
          {connected ? (
            <Button size="sm" variant="outline" onClick={() => void disconnect()} disabled={busy}>
              <Unplug className="h-4 w-4" aria-hidden /> Kes
            </Button>
          ) : (
            <Button size="sm" onClick={() => void connect()} disabled={busy}>
              {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Link2 className="h-4 w-4" aria-hidden />}
              Bağlan
            </Button>
          )}
          <Button size="sm" onClick={() => void takeSnapshot()} disabled={!connected || taking}>
            {taking ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Camera className="h-4 w-4" aria-hidden />}
            Snapshot al
          </Button>
        </div>

        <div>
          <Label>Karşılaştırma tabanı</Label>
          <select
            value={baselineKey}
            onChange={(event) => setBaselineKey(event.target.value)}
            className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            <option value="reset">Reset değerleri (datasheet)</option>
            {[...history].reverse().map((item) => (
              <option key={item.taken_at} value={String(item.taken_at)}>
                Snapshot {timeLabel(item.taken_at)}
              </option>
            ))}
          </select>
        </div>

        {snapshot ? (
          <div className="rounded-md border border-border bg-inset p-2 text-[11px] text-muted">
            <div>{snapshot.read_ok}/{snapshot.total} register okundu ({snapshot.duration_ms} ms)</div>
            <div className={cn("mt-1 font-semibold", diffCount > 0 ? "text-warn" : "text-ok")}>
              {diffCount > 0 ? `${diffCount} register beklenenden farklı` : "Tüm registerlar taban ile aynı"}
            </div>
          </div>
        ) : null}

        {error ? (
          <p className="rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
        ) : null}
      </aside>

      <section className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
        {!snapshot ? (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-faint">
            <p>
              Bağlan ve &quot;Snapshot al&quot; ile {selectedDevice?.part} register haritasını oku.<br />
              Bitler beklenen değerle karşılaştırılır; farklı bitler kırmızı yanar,
              bit üzerine gelince datasheet alan adı görünür.
            </p>
          </div>
        ) : (
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-elev">
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
                <th className="px-3 py-2">Register</th>
                <th className="px-3 py-2">Adres</th>
                <th className="px-3 py-2">Okunan</th>
                <th className="px-3 py-2">Beklenen</th>
                <th className="px-3 py-2">Bitler (MSB → LSB)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {snapshot.registers.map((item) => {
                const descReg = descriptor?.registers?.find((reg) => reg.name === item.name);
                const width = descReg?.width ?? 8;
                const actual = item.ok ? parseHex(item.value) : null;
                const base = baselineValue(item.name);
                const differs = actual !== null && base !== null && actual !== base;
                return (
                  <tr key={item.name} className={cn(differs && "bg-danger/5")}>
                    <td className="px-3 py-1.5 font-mono text-text">{item.name}</td>
                    <td className="px-3 py-1.5 font-mono text-faint">
                      {item.offset === null ? "—" : hex(item.offset, 8)}
                    </td>
                    <td className={cn("px-3 py-1.5 font-mono", item.ok ? "text-accent" : "text-danger")}>
                      {item.ok ? (actual !== null ? hex(actual, width) : item.value) : (item.error || "HATA")}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-muted">
                      {base === null ? "—" : hex(base, width)}
                    </td>
                    <td className="px-3 py-1.5">
                      <BitGrid width={width} actual={actual} baseline={base} register={descReg} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
