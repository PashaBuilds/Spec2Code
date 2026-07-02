import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Link2, Loader2, PlugZap, Send, ShieldCheck, Unplug, XCircle } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest, saveCachedManifest } from "./manifest";
import type {
  TestbenchCommandResponse,
  TestbenchManifest,
  TestbenchManifestDevice,
  TestbenchOperation,
  TestbenchRegister,
  TestbenchSessionStatus,
} from "@/lib/types";

type ConnectionState = "disconnected" | "connecting" | "connected" | "disconnecting";

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

function makeSessionId(): string {
  const globalCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return `tb_${globalCrypto.randomUUID()}`;
  }
  return `tb_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
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
    return "Bu cevap raw differential/current channel code döndürür. Current hesabı için seçili pair'in shunt milliohm değeri application tarafında kullanılmalıdır.";
  }
  if (device.part === "LTC2991" && op.name === "voltage_read") {
    return "Sekiz kanalın raw 16-bit transfer image değerleri iki byte MSB/LSB sırasıyla döner.";
  }
  if (op.name.includes("erase")) {
    return "Erase işlemi flash içeriğini geri dönüşsüz değiştirir; address ilgili sector içinden verilmelidir.";
  }
  if (op.name.includes("program") || op.name.endsWith("_write")) {
    return "Write/program işlemi hedef cihaz state'ini değiştirir; gönderilen data hex çift byte olarak yorumlanır.";
  }
  if (op.fixed_read_length && op.fixed_read_length > 0) {
    return `Cevap ${op.fixed_read_length} byte data alanı döndürür.`;
  }
  return op.description || "Bu operasyon generated target test bench agent üzerinden gerçek driver fonksiyonunu çağırır.";
}

function registerLabel(register: TestbenchRegister): string {
  return `${register.name} (${hex(register.offset, register.offset > 0xff ? 4 : 2)})`;
}

function ResultPanel({ result }: { result: TestbenchCommandResponse | null }) {
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

  return (
    <div className={cn("rounded-md border p-3", ok ? "border-ok/30 bg-ok/10" : "border-danger/30 bg-danger/10")}>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {ok ? <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden /> : <XCircle className="h-4 w-4 text-danger" aria-hidden />}
        <Badge tone={ok ? "ok" : "danger"}>{ok ? "ok" : "hata"}</Badge>
        <Badge tone="neutral">status {result.parsed.status ?? "-"}</Badge>
        {result.parsed.value ? <Badge tone="accent">value {result.parsed.value}</Badge> : null}
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
        <p className="mt-3 text-xs leading-relaxed text-muted">{result.parsed.message}</p>
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
  const [host, setHost] = useState(() => localStorage.getItem("spec2code.testbench.host") ?? "127.0.0.1");
  const [port, setPort] = useState(() => localStorage.getItem("spec2code.testbench.port") ?? "5000");
  const [timeout, setTimeoutValue] = useState(() => localStorage.getItem("spec2code.testbench.timeout") ?? "5");
  const [transport, setTransport] = useState<"tcp" | "serial">(() =>
    localStorage.getItem("spec2code.testbench.transport") === "serial" ? "serial" : "tcp");
  const [serialPort, setSerialPort] = useState(() => localStorage.getItem("spec2code.testbench.serialPort") ?? "");
  const [baud, setBaud] = useState(() => localStorage.getItem("spec2code.testbench.baud") ?? "115200");
  const [serialPorts, setSerialPorts] = useState<import("@/lib/types").SerialPortInfo[]>([]);
  const [sessionId] = useState(makeSessionId);
  const [connectionState, setConnectionState] = useState<ConnectionState>("disconnected");
  const [sessionStatus, setSessionStatus] = useState<TestbenchSessionStatus | null>(null);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [selectedOperationName, setSelectedOperationName] = useState("");
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

  const selectedDevice = useMemo(
    () => manifest?.devices.find((device) => device.id === selectedDeviceId) ?? manifest?.devices[0] ?? null,
    [manifest, selectedDeviceId],
  );
  const selectedOperation = useMemo(
    () => selectedDevice?.operations.find((op) => op.name === selectedOperationName) ?? selectedDevice?.operations[0] ?? null,
    [selectedDevice, selectedOperationName],
  );
  const isConnected = connectionState === "connected" && Boolean(sessionStatus?.connected);
  const connectionBusy = connectionState === "connecting" || connectionState === "disconnecting";
  const connectionLocked = isConnected || connectionBusy;
  const connectionTone = isConnected ? "ok" : connectionBusy ? "warn" : "neutral";
  const connectionLabel = isConnected ? "bağlı" : connectionState === "connecting" ? "bağlanıyor" : connectionState === "disconnecting" ? "kesiliyor" : "kopuk";

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

  useEffect(() => {
    return () => {
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
    };
  }, [sessionId]);

  // UART agent'lı manifest'te varsayılan transport seri olsun (kullanıcı
  // daha önce elle seçmediyse).
  useEffect(() => {
    if (localStorage.getItem("spec2code.testbench.transport")) return;
    if (manifest?.transport_agent === "uart") setTransport("serial");
  }, [manifest]);

  const refreshSerialPorts = async () => {
    try {
      const ports = await api.testbenchSerialPorts();
      setSerialPorts(ports);
      if (!serialPort && ports.length > 0) setSerialPort(ports[0].device);
    } catch {
      setSerialPorts([]);
    }
  };

  useEffect(() => {
    if (transport === "serial") void refreshSerialPorts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [transport]);

  async function connect() {
    if (connectionBusy || isConnected) return;
    const parsedPort = parseNumber(port);
    const parsedTimeout = parseNumber(timeout) ?? 5;
    if (transport === "tcp" && (!host.trim() || parsedPort == null || parsedPort <= 0)) {
      setError("Host veya port geçerli değil.");
      return;
    }
    if (transport === "serial" && !serialPort.trim()) {
      setError("Seri port seç (ör. COM4).");
      return;
    }

    localStorage.setItem("spec2code.testbench.host", host.trim());
    localStorage.setItem("spec2code.testbench.port", port.trim());
    localStorage.setItem("spec2code.testbench.timeout", timeout.trim());
    localStorage.setItem("spec2code.testbench.transport", transport);
    localStorage.setItem("spec2code.testbench.serialPort", serialPort.trim());
    localStorage.setItem("spec2code.testbench.baud", baud.trim());

    setConnectionState("connecting");
    setError("");
    try {
      const status = await api.testbenchConnect(
        transport === "serial"
          ? {
              session_id: sessionId,
              transport: "serial",
              serial_port: serialPort.trim(),
              baud: parseNumber(baud) ?? 115200,
              timeout_s: parsedTimeout,
            }
          : {
              session_id: sessionId,
              transport: "tcp",
              host: host.trim(),
              port: parsedPort ?? 0,
              timeout_s: parsedTimeout,
            },
      );
      setSessionStatus(status);
      setConnectionState(status.connected ? "connected" : "disconnected");
      if (!status.connected) {
        setError(status.last_error || (transport === "serial" ? "Seri bağlantı kurulamadı." : "TCP bağlantısı kurulamadı."));
      }
    } catch (err) {
      setSessionStatus(null);
      setConnectionState("disconnected");
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function disconnect() {
    if (connectionState === "disconnected" || connectionState === "connecting") return;
    setConnectionState("disconnecting");
    setError("");
    try {
      const status = await api.testbenchDisconnect(sessionId);
      setSessionStatus(status);
    } catch (err) {
      setSessionStatus((current) => current ? { ...current, connected: false, last_error: err instanceof Error ? err.message : String(err) } : current);
    } finally {
      setConnectionState("disconnected");
    }
  }

  async function send() {
    if (!selectedDevice || !selectedOperation || running || versionRunning) return;
    const parsedPort = transport === "serial" ? 0 : parseNumber(port);
    if (transport === "tcp" && (!host.trim() || parsedPort == null || parsedPort <= 0)) {
      setError("Host veya port geçerli değil.");
      return;
    }
    if (!isConnected) {
      setError(transport === "serial" ? "Önce kart ile seri bağlantı kur." : "Önce kart ile TCP bağlantısı kur.");
      return;
    }
    if (selectedOperation.risk === "risky") {
      const ok = window.confirm(`${selectedOperation.label} kart üzerindeki cihaz state'ini değiştirebilir. Devam edilsin mi?`);
      if (!ok) return;
    }

    localStorage.setItem("spec2code.testbench.host", host.trim());
    localStorage.setItem("spec2code.testbench.port", port.trim());
    localStorage.setItem("spec2code.testbench.timeout", timeout.trim());

    const register = selectedDevice.registers.find((reg) => reg.name === registerName);
    const manualRegister = parseNumber(registerAddress);
    const nextCommandId = commandId;
    setCommandId((current) => current + 1);
    setRunning(true);
    setError("");

    try {
      const response = await api.testbenchCommand({
        host: transport === "serial" ? "serial" : host.trim(),
        port: parsedPort ?? 0,
        device: selectedDevice.id,
        operation: selectedOperation.name,
        command_id: nextCommandId,
        session_id: sessionId,
        register: register?.name ?? registerName,
        register_address: register?.offset ?? manualRegister,
        address: needsAddress(selectedOperation) ? parseNumber(address) : null,
        length: needsLength(selectedOperation) ? parseNumber(length) : null,
        value: needsValue(selectedOperation) ? parseNumber(value) : null,
        data_hex: needsData(selectedOperation) ? cleanHexData(dataHex) : "",
        timeout_s: parseNumber(timeout) ?? 5,
      });
      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      setSessionStatus((current) => current ? { ...current, connected: false, last_error: message } : current);
      setConnectionState("disconnected");
    } finally {
      setRunning(false);
    }
  }

  async function queryAgentVersion() {
    if (!isConnected || running || versionRunning) return;
    const parsedPort = transport === "serial" ? 0 : parseNumber(port);
    if (transport === "tcp" && (!host.trim() || parsedPort == null || parsedPort <= 0)) {
      setError("Host veya port geçerli değil.");
      return;
    }

    const nextCommandId = commandId;
    setCommandId((current) => current + 1);
    setVersionRunning(true);
    setError("");

    try {
      const response = await api.testbenchCommand({
        host: transport === "serial" ? "serial" : host.trim(),
        port: parsedPort ?? 0,
        device: "spec2code",
        operation: "spec2code_version",
        command_id: nextCommandId,
        session_id: sessionId,
        timeout_s: parseNumber(timeout) ?? 5,
      });
      setResult(response);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      setSessionStatus((current) => current ? { ...current, connected: false, last_error: message } : current);
      setConnectionState("disconnected");
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
          <div>
            <Label>Transport</Label>
            <div className="mt-1 grid grid-cols-2 gap-1 rounded-md border border-border bg-inset p-1">
              {(["tcp", "serial"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  disabled={connectionLocked}
                  onClick={() => setTransport(option)}
                  className={cn(
                    "rounded px-2 py-1 font-mono text-[11px] font-semibold uppercase transition-colors",
                    transport === option
                      ? "bg-accent-dim text-accent"
                      : "text-muted hover:text-text",
                    connectionLocked && "opacity-60",
                  )}
                >
                  {option === "tcp" ? "TCP (lwIP)" : "Seri (UART)"}
                </button>
              ))}
            </div>
          </div>
          {transport === "tcp" ? (
            <div className="grid grid-cols-[minmax(0,1fr)_88px] gap-2">
              <div>
                <Label>Host</Label>
                <Input value={host} onChange={(event) => setHost(event.target.value)} disabled={connectionLocked} />
              </div>
              <div>
                <Label>Port</Label>
                <Input value={port} onChange={(event) => setPort(event.target.value)} disabled={connectionLocked} />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-[minmax(0,1fr)_96px] gap-2">
              <div>
                <Label>Seri port</Label>
                <div className="flex gap-1">
                  <select
                    value={serialPort}
                    onChange={(event) => setSerialPort(event.target.value)}
                    disabled={connectionLocked}
                    className="h-9 w-full min-w-0 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
                  >
                    {serialPort && !serialPorts.some((p) => p.device === serialPort) ? (
                      <option value={serialPort}>{serialPort}</option>
                    ) : null}
                    {serialPorts.length === 0 && !serialPort ? <option value="">port bulunamadı</option> : null}
                    {serialPorts.map((info) => (
                      <option key={info.device} value={info.device} title={info.description}>
                        {info.device}
                      </option>
                    ))}
                  </select>
                  <Button size="sm" variant="outline" onClick={() => void refreshSerialPorts()} disabled={connectionLocked} title="Portları yenile">
                    ⟳
                  </Button>
                </div>
              </div>
              <div>
                <Label>Baud</Label>
                <Input value={baud} onChange={(event) => setBaud(event.target.value)} disabled={connectionLocked} />
              </div>
            </div>
          )}
          <div>
            <Label>Timeout sn</Label>
            <Input value={timeout} onChange={(event) => setTimeoutValue(event.target.value)} disabled={connectionLocked} />
          </div>

          <div className={cn(
            "rounded-md border px-3 py-2",
            isConnected ? "border-ok/30 bg-ok/10" : connectionBusy ? "border-warn/30 bg-warn/10" : "border-border bg-inset",
          )}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <Badge tone={connectionTone}>{connectionLabel}</Badge>
              <span className="font-mono text-[10px] text-faint">{sessionId.slice(0, 11)}</span>
            </div>
            <p className="mb-3 text-xs leading-relaxed text-muted">
              Komutlar tek {transport === "serial" ? "seri (COM)" : "TCP"} session üzerinden satır satır gönderilir;
              bağlantı koparsa tekrar Bağlan gerekir.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button size="sm" onClick={connect} disabled={connectionBusy || isConnected}>
                {connectionState === "connecting" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Link2 className="h-4 w-4" aria-hidden />}
                Bağlan
              </Button>
              <Button size="sm" variant="outline" onClick={disconnect} disabled={connectionState !== "connected"}>
                {connectionState === "disconnecting" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Unplug className="h-4 w-4" aria-hidden />}
                Kes
              </Button>
              <Button size="sm" variant="outline" onClick={queryAgentVersion} disabled={!isConnected || running || versionRunning}>
                {versionRunning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ShieldCheck className="h-4 w-4" aria-hidden />}
                Sürüm sorgula
              </Button>
            </div>
            {sessionStatus?.last_error ? (
              <p className="mt-2 break-all text-[11px] text-danger">{sessionStatus.last_error}</p>
            ) : null}
          </div>

          <div className="space-y-1.5">
            <Label>Entegre</Label>
            {manifest.devices.map((device) => (
              <button
                key={device.id}
                type="button"
                onClick={() => {
                  setSelectedDeviceId(device.id);
                  setResult(null);
                }}
                className={cn(
                  "flex w-full items-center justify-between gap-2 rounded-md border px-3 py-2 text-left transition-colors",
                  selectedDevice?.id === device.id
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
        {selectedDevice && selectedOperation ? (
          <div className="p-4">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-accent" aria-hidden />
                  <h2 className="text-sm font-semibold text-text">{selectedDevice.part}</h2>
                  <Badge tone="neutral" className="font-mono">{selectedDevice.id}</Badge>
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
                    setResult(null);
                  }}
                  className={cn(
                    "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                    selectedOperation.name === op.name
                      ? "border-accent/50 bg-accent/15 text-text"
                      : "border-border bg-inset text-muted hover:text-text",
                  )}
                >
                  <span className="block font-semibold">{op.label || op.name}</span>
                  <span className="block font-mono text-[10px] text-faint">{op.name}</span>
                </button>
              ))}
            </div>

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

              <ResultPanel result={result} />
            </div>
          </div>
        ) : (
          <div className="p-4 text-sm text-muted">Bu manifest içinde test bench operasyonu bulunamadı.</div>
        )}
      </section>
    </div>
  );
}
