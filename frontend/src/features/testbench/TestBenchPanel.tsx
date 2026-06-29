import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Cpu, Loader2, PlugZap, Send, ShieldCheck, XCircle } from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type {
  GeneratedFile,
  TestbenchCommandResponse,
  TestbenchManifest,
  TestbenchManifestDevice,
  TestbenchOperation,
  TestbenchRegister,
} from "@/lib/types";

function generatedPath(file: GeneratedFile): string {
  if (file.relative_path) return file.relative_path;
  const normalized = file.path.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts[0] === "outputs" && parts.length > 2) return parts.slice(2).join("/");
  return parts[parts.length - 1] ?? file.name;
}

function findManifest(files: GeneratedFile[]): TestbenchManifest | null {
  const file = files.find((item) => generatedPath(item) === "tests/spec2code_testbench_manifest.json");
  if (!file?.content) return null;
  try {
    return JSON.parse(file.content) as TestbenchManifest;
  } catch {
    return null;
  }
}

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
  const manifest = useMemo(() => findManifest(files), [files]);
  const [host, setHost] = useState(() => localStorage.getItem("spec2code.testbench.host") ?? "127.0.0.1");
  const [port, setPort] = useState(() => localStorage.getItem("spec2code.testbench.port") ?? "5000");
  const [timeout, setTimeoutValue] = useState(() => localStorage.getItem("spec2code.testbench.timeout") ?? "5");
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

  useEffect(() => {
    if (!manifest?.devices.length) return;
    setSelectedDeviceId((current) => current || manifest.devices[0].id);
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

  async function send() {
    if (!selectedDevice || !selectedOperation || running) return;
    const parsedPort = parseNumber(port);
    if (!host.trim() || parsedPort == null || parsedPort <= 0) {
      setError("Host veya port geçerli değil.");
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
        host: host.trim(),
        port: parsedPort,
        device: selectedDevice.id,
        operation: selectedOperation.name,
        command_id: nextCommandId,
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
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(false);
    }
  }

  if (!manifest) {
    return (
      <Card className="relative mx-auto max-w-3xl p-6">
        <div className="flex items-start gap-3">
          <PlugZap className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
          <div>
            <h2 className="text-sm font-semibold text-text">Test Bench hazır değil</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Önce generate çalıştır. Generate sonucu `tests/spec2code_testbench_manifest.json` üretildiğinde bu sayfa kart üzerindeki TCP agent'a komut gönderebilir.
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
            <Badge tone="accent">{manifest.devices.length} entegre</Badge>
          </div>
          <p className="mt-1 text-xs leading-relaxed text-faint">{manifest.protocol}</p>
        </div>

        <div className="space-y-3 p-3">
          <div className="grid grid-cols-[minmax(0,1fr)_88px] gap-2">
            <div>
              <Label>Host</Label>
              <Input value={host} onChange={(event) => setHost(event.target.value)} />
            </div>
            <div>
              <Label>Port</Label>
              <Input value={port} onChange={(event) => setPort(event.target.value)} />
            </div>
          </div>
          <div>
            <Label>Timeout sn</Label>
            <Input value={timeout} onChange={(event) => setTimeoutValue(event.target.value)} />
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
                  <Button onClick={send} disabled={running}>
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
