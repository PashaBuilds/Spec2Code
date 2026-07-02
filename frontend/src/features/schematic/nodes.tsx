import { Handle, Position, useViewport, type NodeProps } from "@xyflow/react";
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
import { busBadgeStyle, busColor, busLabel } from "@/lib/busColors";
import type { Ltc2991ModeTone } from "@/features/device-config/ltc2991Model";

const CTRL_ICON: Record<string, typeof Cpu> = {
  i2c: Share2,
  spi: Cpu,
  qspi: Cpu,
  gpio: ToggleRight,
  uart: Terminal,
  dma: Activity,
};

/* Below this zoom the nodes drop secondary detail and show only the part
   name, so a zoomed-out board stays legible instead of becoming noise. */
const LOD_ZOOM = 0.55;

function useDetailed(): boolean {
  return useViewport().zoom >= LOD_ZOOM;
}

/** Decorative IC pin stubs along a package edge (copper pads). */
function PinStrip({ side, count }: { side: "left" | "right"; count: number }) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute bottom-3 top-3 flex flex-col justify-between",
        side === "left" ? "-left-[5px]" : "-right-[5px]",
      )}
    >
      {Array.from({ length: count }, (_, i) => (
        <span key={i} className="block h-[3px] w-[5px] rounded-[1px] bg-pad" />
      ))}
    </div>
  );
}

/** Pin-1 index dot, like the recessed marker on a real package. */
function PinOneDot() {
  return (
    <span
      aria-hidden
      className="absolute left-1.5 top-1.5 h-1.5 w-1.5 rounded-full border border-border bg-bg"
    />
  );
}

function StatusLed({ ok, title }: { ok: boolean; title: string }) {
  return (
    <span
      title={title}
      className={cn(
        "ml-auto h-2 w-2 shrink-0 rounded-full",
        ok
          ? "bg-ok shadow-[0_0_6px_var(--ok)]"
          : "bg-warn shadow-[0_0_6px_var(--warn)] animate-pulse-soft",
      )}
    />
  );
}

export function ZoneNode({ data }: NodeProps) {
  const d = data as unknown as { label: string; color: string };
  return (
    <div
      className="rounded-xl"
      style={{
        width: "100%",
        height: "100%",
        background: `color-mix(in srgb, ${d.color} 8%, transparent)`,
        border: `1px dashed color-mix(in srgb, ${d.color} 45%, transparent)`,
      }}
    >
      <span
        className="text-silk absolute left-3 top-2 font-mono text-[11px] font-semibold"
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
  const zColor = zoneColor(d.zone);
  const detailed = useDetailed();
  return (
    <div
      className={cn(
        "relative w-[200px] rounded-lg border bg-chip-body px-3 py-2.5 transition-shadow",
        selected ? "border-accent shadow-copper-glow" : "border-chip-body-edge shadow-node",
      )}
      style={{ borderLeft: `3px solid ${zColor}` }}
    >
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" style={{ color: zColor }} />
        <span className={cn("text-silk truncate font-mono text-text", detailed ? "text-sm" : "text-base")}>
          {d.label}
        </span>
        {detailed && (
          <span className="ml-auto inline-flex shrink-0 items-center gap-1 text-[10px] text-faint">
            <Lock className="h-3 w-3" /> ro
          </span>
        )}
      </div>
      {detailed && (
        <>
          <div className="mt-1.5 flex items-center justify-between">
            <span
              className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase"
              style={busBadgeStyle(d.type)}
            >
              {busLabel(d.type)}
            </span>
            <span className="font-mono text-[11px] text-accent">{d.base_address}</span>
          </div>
          {d.driver && <div className="mt-1 truncate font-mono text-[10px] text-faint">{d.driver}</div>}
        </>
      )}
      <Handle type="source" position={Position.Right} style={{ background: busColor(d.type) }} />
    </div>
  );
}

export function MuxNode({ data, selected }: NodeProps) {
  const d = data as unknown as { part: string; i2c_address: string; channels: number };
  const detailed = useDetailed();
  return (
    <div
      className={cn(
        "relative w-[168px] rounded-lg border bg-chip-body px-3 py-2.5 transition-shadow",
        selected ? "border-accent shadow-copper-glow" : "border-chip-body-edge shadow-node",
      )}
    >
      <PinOneDot />
      <PinStrip side="left" count={3} />
      <PinStrip side="right" count={4} />
      <div className="flex items-center gap-2 pl-2">
        <GitFork className="h-4 w-4 shrink-0 text-accent" />
        <span className={cn("text-silk truncate font-mono text-text", detailed ? "text-sm" : "text-base")}>
          {d.part}
        </span>
      </div>
      {detailed && (
        <>
          <div className="mt-1.5 flex items-center justify-between pl-2">
            <span
              className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase"
              style={busBadgeStyle("i2c")}
            >
              mux
            </span>
            <span className="font-mono text-[11px] text-accent">{d.i2c_address}</span>
          </div>
          <div className="mt-1 pl-2 font-mono text-[10px] text-faint">{d.channels} channels</div>
        </>
      )}
      <Handle type="target" position={Position.Left} style={{ background: busColor("i2c") }} />
      <Handle type="source" position={Position.Right} style={{ background: busColor("i2c") }} />
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
    telemetry?: string;
  };
  const Icon = d.transport === "spi" || d.transport === "qspi" ? HardDrive : Box;
  const detailed = useDetailed();
  return (
    <div
      className={cn(
        "relative w-[230px] rounded-lg border bg-chip-body px-3 py-2.5 transition-shadow",
        selected ? "border-accent shadow-copper-glow" : "border-chip-body-edge shadow-node",
      )}
    >
      <PinOneDot />
      <PinStrip side="left" count={4} />
      <PinStrip side="right" count={4} />
      <div className="flex items-center gap-2 pl-2">
        <Icon className="h-4 w-4 shrink-0 text-muted" />
        <span className={cn("text-silk truncate font-mono text-text", detailed ? "text-sm" : "text-base")}>
          {d.part}
        </span>
        <StatusLed
          ok={d.hasDescriptor}
          title={d.hasDescriptor ? "descriptor available" : "no descriptor"}
        />
      </div>
      {detailed && (
        <>
          <div className="mt-1.5 flex items-center justify-between pl-2">
            <span
              className="rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase"
              style={busBadgeStyle(d.transport)}
            >
              {busLabel(d.transport)}
            </span>
            <span className="font-mono text-[11px] text-accent">{d.sub}</span>
          </div>
          {d.configSummary && d.configSummary.length > 0 && (
            <div className="mt-2 grid grid-cols-2 gap-1 pl-2">
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
        </>
      )}
      {d.telemetry ? (
        <div className="ml-2 mt-1.5 flex items-center gap-1.5 rounded border border-ok/25 bg-ok/10 px-1.5 py-0.5">
          <span className="h-1.5 w-1.5 shrink-0 animate-pulse-soft rounded-full bg-ok" aria-hidden />
          <span className="truncate font-mono text-[10px] font-semibold text-ok" title="canlı okuma">
            {d.telemetry}
          </span>
        </div>
      ) : null}
      <Handle type="target" position={Position.Left} style={{ background: busColor(d.transport) }} />
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
