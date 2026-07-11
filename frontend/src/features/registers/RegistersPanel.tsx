import { useEffect, useMemo, useRef, useState } from "react";
import { Camera, Check, Grid3X3, Loader2, Pencil, X } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import BoardConnectionCard from "@/components/BoardConnectionCard";
import { useBoardConnection } from "@/store/connection";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type {
  DescriptorRegister,
  DeviceDescriptor,
  RegisterSnapshot,
  TestbenchManifest,
  TestbenchManifestDevice,
  TestbenchRegister,
} from "@/lib/types";

interface StoredSnapshot {
  taken_at: number;
  values: Record<string, string>;
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

function isWriteOnly(register: TestbenchRegister): boolean {
  return (register.access ?? "").toLowerCase() === "wo";
}

function isWritable(register: TestbenchRegister): boolean {
  const access = (register.access ?? "").toLowerCase();
  return access === "rw" || access === "wo";
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
          device.operations.some((op) => op.name === "register_read" || op.name === "register_write"),
      ),
    [manifest],
  );

  // Bağlantı global tek session'dan (store/connection) — CoreSight dahil.
  const board = useBoardConnection();
  const sessionId = board.sessionId;
  const connected = board.connected;
  const [error, setError] = useState("");
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [descriptor, setDescriptor] = useState<DeviceDescriptor | null>(null);
  const [snapshot, setSnapshot] = useState<RegisterSnapshot | null>(null);
  const [history, setHistory] = useState<StoredSnapshot[]>([]);
  const [baselineKey, setBaselineKey] = useState<string>("reset");
  const [taking, setTaking] = useState(false);
  // Yazım sonrası tek register doğrulama okuması / write-only son değer.
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const [written, setWritten] = useState<Record<string, string>>({});
  const [editingReg, setEditingReg] = useState<string>("");
  const [editValue, setEditValue] = useState<string>("");
  const [writingReg, setWritingReg] = useState<string>("");
  const commandIdRef = useRef(1);

  const selectedDevice: TestbenchManifestDevice | null =
    devices.find((device) => device.id === selectedDeviceId) ?? devices[0] ?? null;
  const readOp = selectedDevice?.operations.find((op) => op.name === "register_read") ?? null;
  const writeOp = selectedDevice?.operations.find((op) => op.name === "register_write") ?? null;
  // SPI readback donanım koşulu manifest'e "KOŞUL: ..." olarak işlenir.
  const readCondition = readOp?.description?.split("KOŞUL:")[1]?.trim() ?? "";

  useEffect(() => {
    if (!selectedDevice) return;
    setSelectedDeviceId((current) => (devices.some((d) => d.id === current) ? current : selectedDevice.id));
    setSnapshot(null);
    setOverrides({});
    setWritten({});
    setEditingReg("");
    setHistory(loadHistory(projectName, selectedDevice.id));
    setBaselineKey("reset");
    api.descriptor(selectedDevice.part)
      .then(setDescriptor)
      .catch(() => setDescriptor(null));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevice?.id, projectName]);

  async function takeSnapshot() {
    if (!selectedDevice || !readOp || !connected || taking) return;
    setTaking(true);
    setError("");
    try {
      // register_read CIHAZ-adreslidir: hedef tel'de uiCihazIndeks ile taşınır
      // (device string tel'e ULAŞMAZ). İndeks manifest devices[] (FİLTRESİZ)
      // sırasındaki cihaz indeksidir — yukarıdaki `devices` filtreli olduğundan
      // indeks oradan alınmaz.
      const deviceIndex = (manifest?.devices ?? []).findIndex((d) => d.id === selectedDevice.id);
      const result = await api.registerSnapshot({
        session_id: sessionId,
        device_id: selectedDevice.id,
        device_index: deviceIndex >= 0 ? deviceIndex : 0xffffffff,
        registers: selectedDevice.registers
          .filter((reg) => !isWriteOnly(reg))
          .map((reg) => ({ name: reg.name, offset: reg.offset })),
        timeout_s: 5,
      });
      setSnapshot(result);
      setOverrides({});
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

  function commandBase() {
    return {
      host: board.transport === "tcp" ? board.host.trim() : board.transport,
      port: board.transport === "tcp" ? parseHex(board.port) ?? 0 : 0,
      session_id: sessionId,
      timeout_s: board.timeoutSeconds(),
    };
  }

  async function writeRegister(register: TestbenchRegister) {
    if (!selectedDevice || !writeOp || !connected || writingReg) return;
    const width = register.width ?? 8;
    const parsed = parseHex(editValue.trim());
    const max = (1 << width) - 1;
    if (parsed === null || parsed < 0 || parsed > max) {
      setError(`Geçersiz değer: ${register.name} için 0x00..${hex(max, width)} aralığında hex/ondalık gir.`);
      return;
    }
    const ok = window.confirm(
      `${selectedDevice.part} ${register.name} (${hex(register.offset, 8)}) registerına ${hex(parsed, width)} yazılacak. ` +
      "Kart üzerindeki cihaz state'i değişir. Devam edilsin mi?",
    );
    if (!ok) return;
    setWritingReg(register.name);
    setError("");
    try {
      const response = await api.testbenchCommand({
        ...commandBase(),
        device: selectedDevice.id,
        operation: "register_write",
        command_id: commandIdRef.current++,
        register: register.name,
        register_address: register.offset,
        value: parsed,
      });
      if (response.parsed.ok !== "1") {
        setError(response.parsed.message || "register_write başarısız");
        return;
      }
      setEditingReg("");
      if (readOp && !isWriteOnly(register)) {
        // Yazımı tek register okumasıyla doğrula, satırı yerinde güncelle.
        const verify = await api.testbenchCommand({
          ...commandBase(),
          device: selectedDevice.id,
          operation: "register_read",
          command_id: commandIdRef.current++,
          register: register.name,
          register_address: register.offset,
        });
        if (verify.parsed.ok === "1" && verify.parsed.value) {
          setOverrides((prev) => ({ ...prev, [register.name]: verify.parsed.value }));
        }
      } else {
        setWritten((prev) => ({ ...prev, [register.name]: hex(parsed, width) }));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setWritingReg("");
    }
  }

  function snapshotEntry(regName: string) {
    return snapshot?.registers.find((item) => item.name === regName) ?? null;
  }

  function actualValue(register: TestbenchRegister): number | null {
    const override = overrides[register.name];
    if (override !== undefined) return parseHex(override);
    const entry = snapshotEntry(register.name);
    return entry?.ok ? parseHex(entry.value) : null;
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
              Bu ekran, Generate sonucu register haritası ve <code className="font-mono">register_read</code>/
              <code className="font-mono">register_write</code> operasyonları içeren cihazlar için canlı register
              okuma/yazma sağlar; okunan değerleri beklenen (reset) değerlerle bit bit karşılaştırır. Önce Generate
              çalıştır.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const diffCount = selectedDevice
    ? selectedDevice.registers.filter((reg) => {
        const actual = actualValue(reg);
        const base = baselineValue(reg.name);
        return actual !== null && base !== null && actual !== base;
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

        <BoardConnectionCard compact />

        <Button
          className="w-full"
          onClick={() => void takeSnapshot()}
          disabled={!connected || taking || !readOp}
          title={readOp ? undefined : "Bu cihazda register okuması yok"}
        >
          {taking ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Camera className="h-4 w-4" aria-hidden />}
          Snapshot al
        </Button>

        {!readOp && writeOp ? (
          <p className="rounded-md border border-warn/30 bg-warn/10 p-2 text-[11px] leading-relaxed text-warn">
            Bu cihaz için register okuması üretilmedi: SPI readback donanım-koşullu (ör. MUXOUT pin
            fonksiyonu) ve bu parça için doğrulanmadı. Satırlardan yazma yapılabilir; geri okuma yok.
          </p>
        ) : null}

        {readCondition ? (
          <p className="rounded-md border border-warn/30 bg-warn/10 p-2 text-[11px] leading-relaxed text-warn">
            Okuma koşulu: {readCondition}
          </p>
        ) : null}

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
        {!selectedDevice ? null : (
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-elev">
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
                <th className="px-3 py-2">Register</th>
                <th className="px-3 py-2">Adres</th>
                <th className="px-3 py-2">Erişim</th>
                <th className="px-3 py-2">Okunan</th>
                <th className="px-3 py-2">Beklenen</th>
                <th className="px-3 py-2">Bitler (MSB → LSB)</th>
                {writeOp ? <th className="px-3 py-2">Yaz</th> : null}
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {selectedDevice.registers.map((reg) => {
                const descReg = descriptor?.registers?.find((item) => item.name === reg.name);
                const width = reg.width ?? descReg?.width ?? 8;
                const entry = snapshotEntry(reg.name);
                const actual = actualValue(reg);
                const base = baselineValue(reg.name);
                const differs = actual !== null && base !== null && actual !== base;
                const writable = Boolean(writeOp) && isWritable(reg) && connected;
                const editing = editingReg === reg.name;
                const busy = writingReg === reg.name;
                return (
                  <tr key={reg.name} className={cn(differs && "bg-danger/5")}>
                    <td className="px-3 py-1.5 font-mono text-text">{reg.name}</td>
                    <td className="px-3 py-1.5 font-mono text-faint">{hex(reg.offset, 8)}</td>
                    <td className="px-3 py-1.5 font-mono text-faint">{(reg.access || "rw").toLowerCase()}</td>
                    <td
                      className={cn(
                        "px-3 py-1.5 font-mono",
                        entry && !entry.ok ? "text-danger" : actual !== null ? "text-accent" : "text-faint",
                      )}
                    >
                      {entry && !entry.ok
                        ? entry.error || "HATA"
                        : actual !== null
                          ? hex(actual, width)
                          : isWriteOnly(reg)
                            ? written[reg.name]
                              ? `${written[reg.name]} (yazıldı)`
                              : "yazılır-okunmaz"
                            : written[reg.name]
                              ? `${written[reg.name]} (yazıldı)`
                              : "—"}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-muted">
                      {base === null ? "—" : hex(base, width)}
                    </td>
                    <td className="px-3 py-1.5">
                      <BitGrid width={width} actual={actual} baseline={base} register={descReg} />
                    </td>
                    {writeOp ? (
                      <td className="px-3 py-1.5">
                        {!isWritable(reg) ? (
                          <span className="font-mono text-[10px] text-faint" title="read-only register">ro</span>
                        ) : editing ? (
                          <div className="flex items-center gap-1">
                            <Input
                              value={editValue}
                              onChange={(event) => setEditValue(event.target.value)}
                              onKeyDown={(event) => {
                                if (event.key === "Enter") void writeRegister(reg);
                                if (event.key === "Escape") setEditingReg("");
                              }}
                              placeholder={hex(0, width)}
                              className="h-6 w-20 px-1 font-mono text-[11px]"
                              autoFocus
                              disabled={busy}
                            />
                            <Button
                              variant="ghost"
                              className="h-6 w-6 p-0 text-ok"
                              onClick={() => void writeRegister(reg)}
                              disabled={busy}
                              title="Yaz (Enter)"
                            >
                              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Check className="h-3.5 w-3.5" aria-hidden />}
                            </Button>
                            <Button
                              variant="ghost"
                              className="h-6 w-6 p-0 text-faint"
                              onClick={() => setEditingReg("")}
                              disabled={busy}
                              title="İptal (Esc)"
                            >
                              <X className="h-3.5 w-3.5" aria-hidden />
                            </Button>
                          </div>
                        ) : (
                          <Button
                            variant="ghost"
                            className="h-6 w-6 p-0 text-muted hover:text-accent"
                            onClick={() => {
                              setEditingReg(reg.name);
                              setEditValue(actual !== null ? hex(actual, width) : "");
                            }}
                            disabled={!writable}
                            title={connected ? "Register yaz" : "Önce karta bağlan"}
                          >
                            <Pencil className="h-3.5 w-3.5" aria-hidden />
                          </Button>
                        )}
                      </td>
                    ) : null}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {selectedDevice && !snapshot && readOp ? (
          <div className="border-t border-border/60 p-3 text-center text-[11px] text-faint">
            Bağlan ve &quot;Snapshot al&quot; ile {selectedDevice.part} register haritasını canlı oku; bitler beklenen
            değerle karşılaştırılır, kalem ile rw registerlara yazılır.
          </div>
        ) : null}
      </section>
    </div>
  );
}
