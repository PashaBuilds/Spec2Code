import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  Activity,
  Box,
  Cpu,
  GitFork,
  HardDrive,
  Lock,
  Share2,
  Terminal,
  ToggleRight,
} from "lucide-react";
import { cn, zoneColor } from "@/lib/utils";
import type { Ltc2991ModeTone } from "@/features/device-config/ltc2991Model";

const CTRL_ICON: Record<string, typeof Cpu> = {
  i2c: Share2,
  spi: Cpu,
  qspi: Cpu,
  gpio: ToggleRight,
  uart: Terminal,
  dma: Activity,
};

export function ZoneNode({ data }: NodeProps) {
  const d = data as unknown as { label: string; color: string };
  return (
    <div
      className="rounded-xl"
      style={{
        width: "100%",
        height: "100%",
        background: `color-mix(in srgb, ${d.color} 8%, transparent)`,
        border: `1px solid color-mix(in srgb, ${d.color} 45%, transparent)`,
      }}
    >
      <span
        className="absolute left-3 top-2 font-mono text-[11px] font-semibold tracking-wide"
        style={{ color: d.color }}
      >
        {d.label}
      </span>
    </div>
  );
}

export function ControllerNode({ data, selected }: NodeProps) {
  const d = data as unknown as {
    label: string;
    type: string;
    base_address: string;
    driver?: string;
    zone: string;
  };
  const Icon = CTRL_ICON[d.type] ?? Box;
  const color = zoneColor(d.zone);
  return (
    <div
      className={cn(
        "relative w-[200px] rounded-lg border bg-elev px-3 py-2.5 transition-shadow",
        selected ? "border-accent shadow-[0_0_0_1px_var(--accent)]" : "border-border",
      )}
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4" style={{ color }} />
        <span className="font-mono text-sm text-text">{d.label}</span>
        <span className="ml-auto inline-flex items-center gap-1 text-[10px] text-faint">
          <Lock className="h-3 w-3" /> ro
        </span>
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className="rounded bg-inset px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted">
          {d.type}
        </span>
        <span className="font-mono text-[11px] text-accent">{d.base_address}</span>
      </div>
      {d.driver && <div className="mt-1 font-mono text-[10px] text-faint">{d.driver}</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function MuxNode({ data, selected }: NodeProps) {
  const d = data as unknown as { part: string; i2c_address: string; channels: number };
  return (
    <div
      className={cn(
        "relative w-[168px] rounded-lg border bg-elev px-3 py-2.5",
        selected ? "border-accent shadow-[0_0_0_1px_var(--accent)]" : "border-border",
      )}
    >
      <div className="flex items-center gap-2">
        <GitFork className="h-4 w-4 text-accent" />
        <span className="font-mono text-sm text-text">{d.part}</span>
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className="rounded bg-inset px-1.5 py-0.5 font-mono text-[10px] text-muted">mux</span>
        <span className="font-mono text-[11px] text-accent">{d.i2c_address}</span>
      </div>
      <div className="mt-1 font-mono text-[10px] text-faint">{d.channels} channels</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export function DeviceNode({ data, selected }: NodeProps) {
  const d = data as unknown as {
    part: string;
    sub: string;
    transport: string;
    hasDescriptor: boolean;
    configSummary?: Array<{ key: string; label: string; tone: Ltc2991ModeTone }>;
  };
  const Icon = d.transport === "spi" ? HardDrive : Box;
  return (
    <div
      className={cn(
        "relative w-[230px] rounded-lg border bg-elev px-3 py-2.5",
        selected ? "border-accent shadow-[0_0_0_1px_var(--accent)]" : "border-border",
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-muted" />
        <span className="font-mono text-sm text-text">{d.part}</span>
        <span
          className={cn(
            "ml-auto h-2 w-2 rounded-full",
            d.hasDescriptor ? "bg-ok" : "bg-warn",
          )}
          title={d.hasDescriptor ? "descriptor available" : "no descriptor"}
        />
      </div>
      <div className="mt-1.5 flex items-center justify-between">
        <span className="rounded bg-inset px-1.5 py-0.5 font-mono text-[10px] uppercase text-muted">
          {d.transport}
        </span>
        <span className="font-mono text-[11px] text-accent">{d.sub}</span>
      </div>
      {d.configSummary && d.configSummary.length > 0 && (
        <div className="mt-2 grid grid-cols-2 gap-1">
          {d.configSummary.map((item) => (
            <span
              key={item.key}
              className={cn(
                "min-w-0 truncate rounded border px-1.5 py-0.5 text-center font-mono text-[9px] font-semibold",
                summaryToneClass(item.tone),
              )}
              title={item.label}
            >
              {item.label}
            </span>
          ))}
        </div>
      )}
      <Handle type="target" position={Position.Left} />
    </div>
  );
}

function summaryToneClass(tone: Ltc2991ModeTone): string {
  switch (tone) {
    case "off":
      return "border-border bg-inset text-faint";
    case "diff":
      return "border-ok/30 bg-ok/10 text-ok";
    case "current":
      return "border-warn/30 bg-warn/10 text-warn";
    case "temp":
      return "border-danger/30 bg-danger/10 text-danger";
    case "aux":
      return "border-muted/25 bg-inset text-muted";
    case "se":
    default:
      return "border-accent/30 bg-accent/10 text-accent";
  }
}

export const nodeTypes = {
  zone: ZoneNode,
  controller: ControllerNode,
  mux: MuxNode,
  device: DeviceNode,
};
