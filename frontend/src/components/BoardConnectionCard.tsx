import { useEffect, useState } from "react";
import { Link2, Loader2, Unplug } from "lucide-react";
import { Badge, Button, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useBoardConnection, type BoardTransport } from "@/store/connection";
import type { SerialPortInfo } from "@/lib/types";

let S_logLevelCommandId = 9000;

/** Tek kart bağlantısı: Test Bench, UART konsolu, Bring-up, Registers ve
 * telemetri aynı session'ı paylaşır — bir kez bağlanmak yeter. Seri port ve
 * CoreSight köprüsü fiziksel olarak tek istemci kaldırdığı için bu kart
 * uygulamadaki TEK bağlanma noktasıdır. */
export default function BoardConnectionCard({ compact = false }: { compact?: boolean }) {
  const board = useBoardConnection();
  const [serialPorts, setSerialPorts] = useState<SerialPortInfo[]>([]);
  const [agentLogLevel, setAgentLogLevel] = useState("2");
  const [logLevelBusy, setLogLevelBusy] = useState(false);

  const locked = board.connected || board.busy;
  const tone = board.connected ? "ok" : board.busy ? "warn" : "neutral";
  const label = board.connected ? "bağlı" : board.busy ? "çalışıyor" : "kopuk";

  async function refreshSerialPorts() {
    try {
      const ports = await api.testbenchSerialPorts();
      setSerialPorts(ports);
      if (!board.serialPort && ports.length > 0) board.update({ serialPort: ports[0].device });
    } catch {
      setSerialPorts([]);
    }
  }

  useEffect(() => {
    if (board.transport === "serial") void refreshSerialPorts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [board.transport]);

  async function applyAgentLogLevel(value: string) {
    setAgentLogLevel(value);
    if (!board.connected || logLevelBusy) return;
    setLogLevelBusy(true);
    try {
      await api.testbenchCommand({
        host: board.transport === "tcp" ? board.host.trim() : board.transport,
        port: board.transport === "tcp" ? Number.parseInt(board.port, 10) || 0 : 0,
        device: "spec2code",
        operation: "log_level",
        command_id: S_logLevelCommandId++,
        session_id: board.sessionId,
        value: Number.parseInt(value, 10) || 2,
        timeout_s: board.timeoutSeconds(),
      });
    } catch (err) {
      board.reconcile(err instanceof Error ? err.message : String(err));
    } finally {
      setLogLevelBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <div>
        <Label>Bağlantı (tüm ekranlar için ortak)</Label>
        <div className="mt-1 grid grid-cols-3 gap-1 rounded-md border border-border bg-inset p-1">
          {(["tcp", "serial", "coresight"] as const).map((option) => (
            <button
              key={option}
              type="button"
              disabled={locked}
              onClick={() => board.update({ transport: option as BoardTransport })}
              className={cn(
                "rounded px-2 py-1 font-mono text-[11px] font-semibold uppercase transition-colors",
                board.transport === option ? "bg-accent-dim text-accent" : "text-muted hover:text-text",
                locked && "opacity-60",
              )}
            >
              {option === "tcp" ? "TCP" : option === "serial" ? "Seri" : "CoreSight"}
            </button>
          ))}
        </div>
      </div>
      {board.transport === "tcp" ? (
        <div className="grid grid-cols-[minmax(0,1fr)_88px] gap-2">
          <div>
            <Label>Host</Label>
            <Input value={board.host} onChange={(e) => board.update({ host: e.target.value })} disabled={locked} />
          </div>
          <div>
            <Label>Port</Label>
            <Input value={board.port} onChange={(e) => board.update({ port: e.target.value })} disabled={locked} />
          </div>
        </div>
      ) : board.transport === "coresight" ? (
        <div className="space-y-2">
          <div>
            <Label>Vitis kurulum yolu</Label>
            <Input
              value={board.csVitisPath}
              onChange={(e) => board.update({ csVitisPath: e.target.value })}
              disabled={locked}
              placeholder="D:\Xilinx\Vitis\2023.2"
              spellCheck={false}
            />
          </div>
          <div>
            <Label>SmartLynq / hw_server (opsiyonel)</Label>
            <Input
              value={board.csHwServerUrl}
              onChange={(e) => board.update({ csHwServerUrl: e.target.value })}
              disabled={locked}
              placeholder="boş = lokal USB JTAG; 192.168.0.10[:3121]"
              spellCheck={false}
            />
          </div>
          <div>
            <Label>Çekirdek (DCC)</Label>
            <Input
              value={board.csProcessor}
              onChange={(e) => board.update({ csProcessor: e.target.value })}
              disabled={locked}
              placeholder={`boş = Setup'tan: ${board.effectiveProcessor()}`}
              spellCheck={false}
            />
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-[minmax(0,1fr)_96px] gap-2">
          <div>
            <Label>Seri port</Label>
            <div className="flex gap-1">
              <select
                value={board.serialPort}
                onChange={(e) => board.update({ serialPort: e.target.value })}
                disabled={locked}
                className="h-9 w-full min-w-0 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
              >
                {board.serialPort && !serialPorts.some((p) => p.device === board.serialPort) ? (
                  <option value={board.serialPort}>{board.serialPort}</option>
                ) : null}
                {serialPorts.length === 0 && !board.serialPort ? <option value="">port bulunamadı</option> : null}
                {serialPorts.map((info) => (
                  <option key={info.device} value={info.device} title={info.description}>
                    {info.device}
                  </option>
                ))}
              </select>
              <Button size="sm" variant="outline" onClick={() => void refreshSerialPorts()} disabled={locked} title="Portları yenile">
                ⟳
              </Button>
            </div>
          </div>
          <div>
            <Label>Baud</Label>
            <Input value={board.baud} onChange={(e) => board.update({ baud: e.target.value })} disabled={locked} />
          </div>
        </div>
      )}
      {!compact ? (
        <div>
          <Label>Timeout sn</Label>
          <Input value={board.timeoutS} onChange={(e) => board.update({ timeoutS: e.target.value })} disabled={locked} />
        </div>
      ) : null}

      <div className={cn(
        "rounded-md border px-3 py-2",
        board.connected ? "border-ok/30 bg-ok/10" : board.busy ? "border-warn/30 bg-warn/10" : "border-border bg-inset",
      )}>
        <div className="mb-2 flex items-center justify-between gap-2">
          <Badge tone={tone}>{label}</Badge>
          <span className="font-mono text-[10px] text-faint">{board.sessionId.slice(0, 12)}</span>
        </div>
        {!compact ? (
          <p className="mb-3 text-xs leading-relaxed text-muted">
            Tek {board.transport === "serial" ? "seri (COM)" : board.transport === "coresight" ? "CoreSight DCC (xsdb jtagterminal köprüsü)" : "TCP"} session
            tüm ekranlarca paylaşılır; komutlar satır satır gönderilir.
            {board.transport === "coresight" ? " İlk bağlantı xsdb açılışı nedeniyle ~10-30 sn sürebilir." : ""}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => void board.connect()} disabled={board.busy || board.connected}>
            {board.busy && !board.connected ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Link2 className="h-4 w-4" aria-hidden />}
            Bağlan
          </Button>
          <Button size="sm" variant="outline" onClick={() => void board.disconnect()} disabled={!board.connected}>
            {board.busy && board.connected ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Unplug className="h-4 w-4" aria-hidden />}
            Kes
          </Button>
        </div>
        {board.connected ? (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-[11px] text-muted">Agent log seviyesi</span>
            <select
              value={agentLogLevel}
              onChange={(e) => void applyAgentLogLevel(e.target.value)}
              disabled={logLevelBusy}
              className="h-7 min-w-0 flex-1 rounded-md border border-border bg-inset px-1.5 font-mono text-[11px] text-text"
              title="Karttaki agent'ın log eşiği; S2C-LOG satırları konsol ve Veri Akışı'nda görünür."
            >
              <option value="1">1 — error</option>
              <option value="2">2 — warning (varsayılan)</option>
              <option value="3">3 — message (TX/RX)</option>
              <option value="4">4 — info</option>
              <option value="5">5 — debug</option>
            </select>
          </div>
        ) : null}
        {board.lastError ? (
          <p className="mt-2 break-all text-[11px] text-danger">{board.lastError}</p>
        ) : null}
      </div>
    </div>
  );
}
