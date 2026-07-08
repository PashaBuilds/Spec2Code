import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Loader2, PlugZap, Radar, Send, ShieldCheck, XCircle } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import BoardConnectionCard from "@/components/BoardConnectionCard";
import FlashTransferCard from "./FlashTransferCard";
import I2cScanCard from "./I2cScanCard";
import { api } from "@/lib/api";
import { timeLabelMs } from "@/lib/console";
import { asciiFromDataHex, formatConvertedValue } from "@/lib/units";
import { cn } from "@/lib/utils";
import { useBoardConnection } from "@/store/connection";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest, saveCachedManifest } from "./manifest";
import type {
  TestbenchCommandResponse,
  TestbenchManifest,
  TestbenchManifestDevice,
  TestbenchOperation,
  TestbenchRegister,
} from "@/lib/types";

function parseNumber(value: string): number | null {
  const text = value.trim();
  if (!text) return null;
  const parsed = Number.parseInt(text, text.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function hex(value: number, width = 2): string {
  return `0x${value.toString(16).toUpperCase().padStart(width, "0")}`;
}

function cleanHexData(value: string): string {
  return value.replace(/[^0-9a-fA-F]/g, "").toUpperCase();
}

function byteGroups(data: string): string[] {
  return cleanHexData(data).match(/.{1,2}/g) ?? [];
}

function needsRegister(op: TestbenchOperation): boolean {
  return Boolean(op.requires_register) || op.name === "register_read" || op.name === "register_write";
}

function needsValue(op: TestbenchOperation): boolean {
  return Boolean(op.requires_value) || op.name === "register_write" || op.name === "byte_write";
}

function needsAddress(op: TestbenchOperation): boolean {
  return Boolean(op.requires_address) || ["data_read", "page_program", "page_write", "byte_write", "sector_erase"].includes(op.name);
}

function needsLength(op: TestbenchOperation): boolean {
  return Boolean(op.requires_length) || op.name === "data_read";
}

function needsData(op: TestbenchOperation): boolean {
  return Boolean(op.requires_data) || ["page_program", "page_write"].includes(op.name);
}

function operationNote(device: TestbenchManifestDevice, op: TestbenchOperation): string {
  if (device.part === "LTC2991" && op.name === "current_read") {
    return "Raw differential kod döner (işaret + 14 bit, two's complement): Vsense_µV = kod × 19.075. Akım = Vsense / Rshunt hesabı, pair'e özgü shunt değeriyle application tarafında yapılır.";
  }
  if (device.part === "LTC2991" && op.name === "voltage_read") {
    return "Sekiz single-ended kanal milivolt cinsinden döner (LSB 305.18 µV; 0–5000 mV, negatifler 0'a kırpılır).";
  }
  if (device.part === "LTC2991" && op.name === "temperature_read") {
    return "İç sıcaklık santi-santigrat (0.01 °C) cinsinden işaretli döner: 2350 = 23.50 °C.";
  }
  if (device.part === "LTC2991" && op.name === "vcc_read") {
    return "VCC milivolt cinsinden döner (2500 mV + kod × 305.18 µV).";
  }
  if (op.name.includes("erase")) {
    return "Erase işlemi flash içeriğini geri dönüşsüz değiştirir; address ilgili sector içinden verilmelidir.";
  }
  if (op.name.includes("program") || op.name.endsWith("_write")) {
    return "Write/program işlemi hedef cihaz state'ini değiştirir; gönderilen data hex çift byte olarak yorumlanır.";
  }
  if (op.name === "device_init" && op.description) {
    // Post-init doğrulama okuması ("Başarıda X geri okunur") burada anlatılır.
    return op.description;
  }
  if (op.fixed_read_length && op.fixed_read_length > 0) {
    return `Cevap ${op.fixed_read_length} byte data alanı döndürür.`;
  }
  return op.description || "Bu operasyon generated target test bench agent üzerinden gerçek driver fonksiyonunu çağırır.";
}

function registerLabel(register: TestbenchRegister): string {
  return `${register.name} (${hex(register.offset, register.offset > 0xff ? 4 : 2)})`;
}

interface ResultMeta {
  sentAtMs: number;
  durationMs: number;
}

function ResultPanel({
  result,
  meta,
  operation,
}: {
  result: TestbenchCommandResponse | null;
  meta: ResultMeta | null;
  operation: TestbenchOperation | null;
}) {
  if (!result) {
    return (
      <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
        Henüz komut gönderilmedi. İlk cevap burada request, response ve decode edilmiş alanlarla görünecek.
      </div>
    );
  }

  const ok = result.parsed.ok === "1";
  const data = result.parsed.data ?? "";
  const bytes = byteGroups(data);
  // Sürüm sorgusu: data ASCII sürüm taşır (eski firmware'de boş — mesajdan
  // ayıklanır); cihaz operasyonu metasıyla ASLA decode edilmez.
  const isVersionQuery = result.request_line.includes("op=spec2code_version");
  const versionText = isVersionQuery
    ? asciiFromDataHex(data) ?? /v\d+\.\d+\.\d+/.exec(result.parsed.message ?? "")?.[0] ?? null
    : null;
  const decoded = isVersionQuery ? versionText : formatConvertedValue(operation, result.parsed);

  return (
    <div className={cn("rounded-md border p-3", ok ? "border-ok/30 bg-ok/10" : "border-danger/30 bg-danger/10")}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {ok ? <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden /> : <XCircle className="h-4 w-4 text-danger" aria-hidden />}
        <Badge tone={ok ? "ok" : "danger"}>{ok ? "ok" : "hata"}</Badge>
        <Badge tone="neutral">status {result.parsed.status ?? "-"}</Badge>
        {result.parsed.value ? <Badge tone="accent">value {result.parsed.value}</Badge> : null}
        {decoded ? (
          <span className="rounded-md border border-ok/40 bg-ok/15 px-2 py-0.5 font-mono text-sm font-semibold text-ok">
            = {decoded}
          </span>
        ) : null}
        {meta ? (
          <span className="ml-auto font-mono text-[11px] text-muted" title="Gönderim zamanı ve komutun toplam gidiş-dönüş süresi">
            {timeLabelMs(meta.sentAtMs, { ms: true })} · {meta.durationMs} ms
          </span>
        ) : null}
      </div>

      <div className="grid gap-2 text-[11px] md:grid-cols-2">
        <div>
          <div className="mb-1 text-faint">Request</div>
          <code className="block break-all rounded border border-border bg-bg p-2 font-mono text-text">{result.request_line}</code>
        </div>
        <div>
          <div className="mb-1 text-faint">Response</div>
          <code className="block break-all rounded border border-border bg-bg p-2 font-mono text-text">{result.response_line}</code>
        </div>
      </div>

      <div className="mt-3">
        <div className="mb-1 text-[11px] text-faint">Data bytes</div>
        {bytes.length ? (
          <div className="flex flex-wrap gap-1">
            {bytes.map((byte, index) => (
              <span key={`${byte}-${index}`} className="rounded border border-border bg-bg px-1.5 py-0.5 font-mono text-[11px] text-text">
                {byte.padEnd(2, "0")}
              </span>
            ))}
          </div>
        ) : (
          <span className="text-xs text-muted">Data alanı boş.</span>
        )}
      </div>

      {result.parsed.message ? (
        <div className="mt-3">
          <div className="mb-1 text-[11px] text-faint">Mesaj</div>
          <p className="break-all text-xs leading-relaxed text-text">{result.parsed.message}</p>
        </div>
      ) : null}
    </div>
  );
}

export default function TestBenchPanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const activeManifest = useMemo(() => findManifest(manifestFiles), [manifestFiles]);
  const [cachedManifest, setCachedManifest] = useState<TestbenchManifest | null>(() => loadCachedManifest(projectName));
  const manifest = activeManifest ?? (jobStatus === "running" ? null : cachedManifest);
  const manifestSource = activeManifest ? "active" : manifest ? "cached" : "none";
  // Bağlantı global: tüm ekranlar tek session'ı paylaşır (store/connection).
  const board = useBoardConnection();
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [selectedOperationName, setSelectedOperationName] = useState("");
  // Flash cihazlarında "Dosya transferi" AYRI bir moddur: seçilince tekil
  // operasyon paneli gizlenir, yalnız FlashTransferCard görünür (saha isteği:
  // dosya oku/.bin yaz kutusu id_read/data_read/page_program panellerine
  // sızmamalı).
  const [flashTransferMode, setFlashTransferMode] = useState(false);
  const [registerName, setRegisterName] = useState("");
  const [registerAddress, setRegisterAddress] = useState("");
  const [address, setAddress] = useState("0x0");
  const [length, setLength] = useState("16");
  const [value, setValue] = useState("0x00");
  const [dataHex, setDataHex] = useState("");
  const [commandId, setCommandId] = useState(1);
  const [running, setRunning] = useState(false);
  const [versionRunning, setVersionRunning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TestbenchCommandResponse | null>(null);
  const [resultMeta, setResultMeta] = useState<ResultMeta | null>(null);
  // Cevabı ÜRETEN operasyon: decode rozeti buna göre çözülür (sürüm
  // sorgusu null bırakır; seçili op ile decode edilirse "0 °C" gibi
  // yanlış çözümler çıkar — saha bulgusu).
  const [resultOperation, setResultOperation] = useState<TestbenchOperation | null>(null);
  // Sol menü görünümü: entegre sayfaları veya I2C Hat Tarama sayfası.
  const [view, setView] = useState<"device" | "i2c-scan">("device");

  const selectedDevice = useMemo(
    () => manifest?.devices.find((device) => device.id === selectedDeviceId) ?? manifest?.devices[0] ?? null,
    [manifest, selectedDeviceId],
  );
  const selectedOperation = useMemo(
    () => selectedDevice?.operations.find((op) => op.name === selectedOperationName) ?? selectedDevice?.operations[0] ?? null,
    [selectedDevice, selectedOperationName],
  );
  const isConnected = board.connected;

  useEffect(() => {
    setCachedManifest(loadCachedManifest(projectName));
  }, [projectName]);

  useEffect(() => {
    if (!activeManifest) return;
    saveCachedManifest(projectName, activeManifest);
    setCachedManifest(activeManifest);
  }, [activeManifest, projectName]);

  useEffect(() => {
    if (!manifest?.devices.length) return;
    setSelectedDeviceId((current) =>
      manifest.devices.some((device) => device.id === current) ? current : manifest.devices[0].id,
    );
  }, [manifest]);

  useEffect(() => {
    if (!selectedDevice?.operations.length) return;
    setSelectedOperationName((current) =>
      selectedDevice.operations.some((op) => op.name === current) ? current : selectedDevice.operations[0].name,
    );
    setRegisterName((current) =>
      selectedDevice.registers.some((reg) => reg.name === current) ? current : selectedDevice.registers[0]?.name ?? "",
    );
  }, [selectedDevice]);

  // Manifest'in agent'ına göre varsayılan transport (kullanıcı daha önce
  // elle seçmediyse): uart -> seri, coresight -> CoreSight DCC.
  useEffect(() => {
    if (localStorage.getItem("spec2code.testbench.transport")) return;
    if (manifest?.transport_agent === "uart") useBoardConnection.getState().update({ transport: "serial" });
    if (manifest?.transport_agent === "coresight") useBoardConnection.getState().update({ transport: "coresight" });
  }, [manifest]);

  function reconcileSessionAfterError(message: string) {
    // Yanıt zaman aşımı bağlantıyı düşürmemeli: gerçek durum backend'den sorulur.
    setError(message);
    board.reconcile(message);
  }

  async function send() {
    if (!selectedDevice || !selectedOperation || running || versionRunning) return;
    if (!isConnected) {
      setError("Önce kart bağlantısı kur (soldaki ortak bağlantı kartı).");
      return;
    }
    if (selectedOperation.risk === "risky") {
      const ok = window.confirm(`${selectedOperation.label} kart üzerindeki cihaz state'ini değiştirebilir. Devam edilsin mi?`);
      if (!ok) return;
    }

    const register = selectedDevice.registers.find((reg) => reg.name === registerName);
    const manualRegister = parseNumber(registerAddress);
    const nextCommandId = commandId;
    setCommandId((current) => current + 1);
    setRunning(true);
    setError("");

    const sentAtMs = Date.now();
    const startedAt = performance.now();
    try {
      const response = await api.testbenchCommand({
        host: board.transport === "tcp" ? board.host.trim() : board.transport,
        port: board.transport === "tcp" ? parseNumber(board.port) ?? 0 : 0,
        device: selectedDevice.id,
        operation: selectedOperation.name,
        command_id: nextCommandId,
        session_id: board.sessionId,
        register: register?.name ?? registerName,
        register_address: register?.offset ?? manualRegister,
        address: needsAddress(selectedOperation) ? parseNumber(address) : null,
        length: needsLength(selectedOperation) ? parseNumber(length) : null,
        value: needsValue(selectedOperation) ? parseNumber(value) : null,
        data_hex: needsData(selectedOperation) ? cleanHexData(dataHex) : "",
        timeout_s: board.timeoutSeconds(),
      });
      setResult(response);
      setResultOperation(selectedOperation);
      setResultMeta({ sentAtMs, durationMs: Math.round(performance.now() - startedAt) });
    } catch (err) {
      reconcileSessionAfterError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  async function queryAgentVersion() {
    if (!isConnected || running || versionRunning) return;
    const nextCommandId = commandId;
    setCommandId((current) => current + 1);
    setVersionRunning(true);
    setError("");

    const sentAtMs = Date.now();
    const startedAt = performance.now();
    try {
      const response = await api.testbenchCommand({
        host: board.transport === "tcp" ? board.host.trim() : board.transport,
        port: board.transport === "tcp" ? parseNumber(board.port) ?? 0 : 0,
        device: "spec2code",
        operation: "spec2code_version",
        command_id: nextCommandId,
        session_id: board.sessionId,
        timeout_s: board.timeoutSeconds(),
      });
      setResult(response);
      setResultOperation(null);
      setResultMeta({ sentAtMs, durationMs: Math.round(performance.now() - startedAt) });
    } catch (err) {
      reconcileSessionAfterError(err instanceof Error ? err.message : String(err));
    } finally {
      setVersionRunning(false);
    }
  }

  if (!manifest) {
    return (
      <Card className="relative mx-auto max-w-3xl p-6">
        <div className="flex items-start gap-3">
          <PlugZap className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
          <div>
            <h2 className="text-sm font-semibold text-text">
              {jobStatus === "running" ? "Generate devam ediyor" : "Test Bench hazır değil"}
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              {jobStatus === "running"
                ? "Generate tamamlandığında tests/spec2code_testbench_manifest.json üretilecek ve bu sayfa otomatik olarak aktif hale gelecek."
                : "Önce Generate çalıştır ve console tarafında RESULT satırını gör. Generate sonucu tests/spec2code_testbench_manifest.json içerdiğinde bu sayfa kart üzerindeki TCP agent'a komut gönderebilir."}
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
      <aside className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
        <div className="border-b border-border px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <PlugZap className="h-4 w-4 text-accent" aria-hidden />
              <span className="text-sm font-semibold text-text">Target test bench</span>
            </div>
            <div className="flex items-center gap-2">
              {manifestSource === "cached" ? <Badge tone="warn">son başarılı generate</Badge> : null}
              {manifest.agent_version ? <Badge tone="neutral">agent {manifest.agent_version}</Badge> : null}
              <Badge tone="accent">{manifest.devices.length} entegre</Badge>
            </div>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-faint">{manifest.protocol}</p>
          {manifestSource === "cached" ? (
            <p className="mt-2 rounded-md border border-warn/30 bg-warn/10 px-2 py-1.5 text-xs leading-relaxed text-warn">
              Aktif generate sonucu tarayıcı state'inde yok; son başarılı generate manifest'i tarayıcı hafızasından yüklendi.
              Topolojiyi değiştirdiysen tekrar Generate çalıştır.
            </p>
          ) : null}
        </div>

        <div className="space-y-3 p-3">
          <BoardConnectionCard />
          <Button size="sm" variant="outline" onClick={queryAgentVersion} disabled={!isConnected || running || versionRunning} className="w-full">
            {versionRunning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
            Sürüm sorgula
          </Button>

          {manifest.i2c_scan && manifest.i2c_scan.controllers.length > 0 ? (
            <div className="space-y-1.5">
              <Label>Hat Tarama</Label>
              <button
                type="button"
                onClick={() => setView("i2c-scan")}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors",
                  view === "i2c-scan"
                    ? "border-accent/50 bg-accent/10 text-text"
                    : "border-border bg-inset text-muted hover:text-text",
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate font-mono text-xs">I2C</span>
                  <span className="block truncate text-[11px] text-faint">adres haritası · 0x08–0x77</span>
                </span>
                <Radar className="h-4 w-4 shrink-0 text-accent" aria-hidden />
              </button>
            </div>
          ) : null}

          <div className="space-y-1.5">
            <Label>Entegre</Label>
            {manifest.devices.map((device) => (
              <button
                key={device.id}
                type="button"
                onClick={() => {
                  setView("device");
                  setSelectedDeviceId(device.id);
                  setResult(null);
                  setResultMeta(null);
                }}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors",
                  view === "device" && selectedDevice?.id === device.id
                    ? "border-accent/50 bg-accent/10 text-text"
                    : "border-border bg-inset text-muted hover:text-text",
                )}
              >
                <span className="min-w-0">
                  <span className="block truncate font-mono text-xs">{device.id}</span>
                  <span className="block truncate text-[11px] text-faint">{device.part}</span>
                </span>
                <Badge tone="neutral">{device.transport.toUpperCase()}</Badge>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
        {view === "i2c-scan" ? (
          <div className="p-4">
            <div className="mb-4">
              <div className="flex items-center gap-2">
                <Radar className="h-4 w-4 text-accent" aria-hidden />
                <h2 className="text-sm font-semibold text-text">I2C Hat Taraması</h2>
              </div>
              <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted">
                Hattın tam adres haritası: doğrudan hat + her switch'in her kanalı sırasıyla. Cihaz kimliği
                çıkarılmaz — yalnız "bu pozisyonda bu adres cevap veriyor" bilgisi döner.
              </p>
            </div>
            <I2cScanCard
              manifest={manifest}
              sessionId={board.sessionId}
              connected={isConnected}
              timeoutSeconds={board.timeoutSeconds()}
            />
          </div>
        ) : selectedDevice && selectedOperation ? (
          <div className="p-4">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-accent" aria-hidden />
                  <h2 className="text-sm font-semibold text-text">{selectedDevice.part}</h2>
                  <Badge tone="neutral" className="font-mono">{selectedDevice.id}</Badge>
                </div>
                {/* Bağlantı zinciri: modelin cihaza NASIL ulaştığı (denetleyici →
                    switch kanalı → adres). Saha arızalarının klasiği model/kart
                    uyuşmazlığıdır — zincir burada tek bakışta doğrulanır. */}
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
                  <span className="rounded border border-border bg-inset px-1.5 py-0.5 text-muted">
                    {selectedDevice.attach?.controller_id ?? selectedDevice.transport}
                  </span>
                  {selectedDevice.attach?.via_mux ? (
                    <>
                      <span className="text-faint">→</span>
                      <span className="rounded border border-warn/40 bg-warn/10 px-1.5 py-0.5 text-warn">
                        switch {selectedDevice.attach.via_mux.mux_id} · kanal {selectedDevice.attach.via_mux.channel}
                      </span>
                    </>
                  ) : selectedDevice.transport.startsWith("i2c") ? (
                    <>
                      <span className="text-faint">→</span>
                      <span className="rounded border border-border bg-inset px-1.5 py-0.5 text-faint" title="Modelde switch bağlantısı yok: operasyonlar kanal SEÇMEDEN doğrudan hatta konuşur. Cihaz fiziksel olarak switch arkasındaysa bu zincir yanlıştır ve okumalar NACK ile düşer.">
                        switch yok (doğrudan hat)
                      </span>
                    </>
                  ) : null}
                  {selectedDevice.attach?.i2c_address ? (
                    <>
                      <span className="text-faint">→</span>
                      <span className="rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 text-accent">
                        adres {selectedDevice.attach.i2c_address}
                      </span>
                    </>
                  ) : null}
                  {typeof selectedDevice.attach?.spi_chip_select === "number" ? (
                    <>
                      <span className="text-faint">→</span>
                      <span className="rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 text-accent">
                        CS {selectedDevice.attach.spi_chip_select}
                      </span>
                    </>
                  ) : null}
                </div>
                <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted">
                  Bu ekran generated target agent ile konuşur; gerçek kart tarafında TCP server'ın bu agent dispatch fonksiyonunu çağırması gerekir.
                </p>
              </div>
              <Badge tone={selectedOperation.risk === "risky" ? "warn" : "ok"}>
                {selectedOperation.risk === "risky" ? "state değiştirir" : "read-only"}
              </Badge>
            </div>

            <div className="mb-4 flex flex-wrap gap-2">
              {selectedDevice.operations.map((op) => (
                <button
                  key={op.name}
                  type="button"
                  onClick={() => {
                    setSelectedOperationName(op.name);
                    setFlashTransferMode(false);
                    setResult(null);
                    setResultMeta(null);
                  }}
                  className={cn(
                    "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                    !flashTransferMode && selectedOperation.name === op.name
                      ? "border-accent/50 bg-accent/15 text-text"
                      : "border-border bg-inset text-muted hover:text-text",
                  )}
                >
                  <span className="block font-semibold">{op.label || op.name}</span>
                  <span className="block font-mono text-[10px] text-faint">{op.name}</span>
                </button>
              ))}
              {/* Flash cihazları için ayrı bir toplu "Dosya transferi" modu. */}
              {selectedDevice.operations.some((op) => op.name === "data_read" || op.name === "page_program") ? (
                <button
                  type="button"
                  onClick={() => setFlashTransferMode(true)}
                  className={cn(
                    "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                    flashTransferMode
                      ? "border-accent/50 bg-accent/15 text-text"
                      : "border-border bg-inset text-muted hover:text-text",
                  )}
                >
                  <span className="block font-semibold">Dosya transferi</span>
                  <span className="block font-mono text-[10px] text-faint">oku → .bin / .bin → yaz</span>
                </button>
              ) : null}
            </div>

            {flashTransferMode ? null : (
            <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
              <div className="space-y-3">
                <div className="rounded-md border border-border bg-inset p-3">
                  <div className="mb-2 flex items-center gap-2">
                    {selectedOperation.risk === "risky" ? (
                      <AlertTriangle className="h-4 w-4 text-warn" aria-hidden />
                    ) : (
                      <ShieldCheck className="h-4 w-4 text-ok" aria-hidden />
                    )}
                    <span className="text-xs font-semibold text-text">{selectedOperation.label}</span>
                  </div>
                  <p className="text-xs leading-relaxed text-muted">{operationNote(selectedDevice, selectedOperation)}</p>
                </div>

                {needsRegister(selectedOperation) && (
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <Label>Register</Label>
                      <select
                        value={registerName}
                        onChange={(event) => setRegisterName(event.target.value)}
                        className="h-9 w-full rounded-md border border-border bg-inset px-3 font-mono text-sm text-text focus:outline-none focus:ring-1 focus:ring-accent"
                      >
                        {selectedDevice.registers.map((register) => (
                          <option key={register.name} value={register.name}>
                            {registerLabel(register)}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <Label>Manual register address</Label>
                      <Input value={registerAddress} onChange={(event) => setRegisterAddress(event.target.value)} placeholder="opsiyonel 0x00" />
                    </div>
                  </div>
                )}

                {(needsAddress(selectedOperation) || needsLength(selectedOperation)) && (
                  <div className="grid gap-3 md:grid-cols-2">
                    {needsAddress(selectedOperation) && (
                      <div>
                        <Label>Address</Label>
                        <Input value={address} onChange={(event) => setAddress(event.target.value)} placeholder="0x00000000" />
                      </div>
                    )}
                    {needsLength(selectedOperation) && (
                      <div>
                        <Label>Length</Label>
                        <Input value={length} onChange={(event) => setLength(event.target.value)} placeholder="16" />
                      </div>
                    )}
                  </div>
                )}

                {needsValue(selectedOperation) && (
                  <div>
                    <Label>Value</Label>
                    <Input value={value} onChange={(event) => setValue(event.target.value)} placeholder="0x00" />
                  </div>
                )}

                {needsData(selectedOperation) && (
                  <div>
                    <Label>Data hex</Label>
                    <Input value={dataHex} onChange={(event) => setDataHex(event.target.value)} placeholder="DE AD BE EF" />
                    <div className="mt-2 flex flex-wrap gap-1">
                      {byteGroups(dataHex).slice(0, 32).map((byte, index) => (
                        <span key={`${byte}-${index}`} className="rounded border border-border bg-bg px-1.5 py-0.5 font-mono text-[11px] text-muted">
                          {byte.padEnd(2, "0")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div className="flex flex-wrap items-center gap-2">
                  <Button onClick={send} disabled={running || versionRunning || !isConnected}>
                    {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Send className="h-4 w-4" aria-hidden />}
                    Gönder
                  </Button>
                  <Badge tone="neutral" className="font-mono">id={commandId}</Badge>
                  {selectedOperation.fixed_read_length ? (
                    <Badge tone="accent">{selectedOperation.fixed_read_length} byte RX</Badge>
                  ) : null}
                </div>

                {error ? (
                  <div className="rounded-md border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">
                    {error}
                  </div>
                ) : null}
              </div>

              <ResultPanel result={result} meta={resultMeta} operation={resultOperation} />
            </div>
            )}

            {flashTransferMode ? (
              <FlashTransferCard device={selectedDevice} />
            ) : null}
          </div>
        ) : (
          <div className="p-4 text-sm text-muted">Bu manifest içinde test bench operasyonu bulunamadı.</div>
        )}
      </section>
    </div>
  );
}
