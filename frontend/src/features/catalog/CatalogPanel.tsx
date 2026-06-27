import * as React from "react";
import { BookOpen, Cpu, HardDrive, Network, Search } from "lucide-react";
import { Card, Badge, Button, Input } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { CatalogDevice, DeviceStatus } from "@/lib/types";
import { useStore } from "@/store/useStore";
import DeviceKnowledgePanel from "@/features/device-knowledge/DeviceKnowledgePanel";
import { hasDeviceKnowledge } from "@/features/device-knowledge/knowledge";

type Mode = "browse" | "pick";

interface CatalogPanelProps {
  mode?: Mode;
  onPick?: (dev: CatalogDevice) => void;
  controllerType?: string;
}

const STATUS_META: Record<
  DeviceStatus,
  { tone: "ok" | "warn" | "accent"; label: string }
> = {
  builtin: { tone: "ok", label: "built-in" },
  needs_source: { tone: "warn", label: "needs source" },
  from_datasheet: { tone: "accent", label: "from datasheet" },
};

/** Icon hint keyed off the device transport. */
function transportIcon(transport: string): React.ReactNode {
  const t = transport.toLowerCase();
  const cls = "h-4 w-4 text-faint shrink-0";
  if (t.startsWith("i2c")) return <Network className={cls} aria-hidden />;
  if (t === "spi" || t === "qspi") return <HardDrive className={cls} aria-hidden />;
  return <Cpu className={cls} aria-hidden />;
}

/**
 * Whether a device transport is compatible with the given controller type.
 * i2c controller ↔ i2c / i2c_mux devices; spi/qspi controller ↔ spi devices.
 * Unknown pairings are treated as compatible (no de-emphasis).
 */
function isCompatible(controllerType: string | undefined, transport: string): boolean {
  if (!controllerType) return true;
  const c = controllerType.toLowerCase();
  const t = transport.toLowerCase();
  if (c.startsWith("i2c")) return t === "i2c" || t === "i2c_mux";
  if (c === "spi" || c === "qspi") return t === "spi";
  return true;
}

export default function CatalogPanel({
  mode = "browse",
  onPick,
  controllerType,
}: CatalogPanelProps) {
  const catalog = useStore((s) => s.catalog);
  const [query, setQuery] = React.useState("");
  const [expandedPart, setExpandedPart] = React.useState<string | null>(null);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter((d) =>
      [d.part, d.summary, d.transport]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(q)),
    );
  }, [catalog, query]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="relative">
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
          aria-hidden
        />
        <Input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by part, summary, or transport…"
          aria-label="Filter catalog devices"
          className="pl-9"
        />
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
            <Search className="h-5 w-5 text-faint" aria-hidden />
            <p className="text-sm text-muted">No devices match your filter.</p>
            <p className="text-xs text-faint">
              {catalog.length === 0 ? "The catalog is empty." : "Try a different term."}
            </p>
          </div>
        ) : (
          filtered.map((dev) => (
            <DeviceCard
              key={dev.part}
              dev={dev}
              mode={mode}
              onPick={onPick}
              controllerType={controllerType}
              expanded={expandedPart === dev.part}
              onToggleKnowledge={() =>
                setExpandedPart((part) => (part === dev.part ? null : dev.part))
              }
            />
          ))
        )}
      </div>
    </div>
  );
}

interface DeviceCardProps {
  dev: CatalogDevice;
  mode: Mode;
  onPick?: (dev: CatalogDevice) => void;
  controllerType?: string;
  expanded: boolean;
  onToggleKnowledge: () => void;
}

function DeviceCard({
  dev,
  mode,
  onPick,
  controllerType,
  expanded,
  onToggleKnowledge,
}: DeviceCardProps) {
  const status = STATUS_META[dev.status];
  const isBuiltin = dev.status === "builtin";
  const clickable = mode === "pick" && isBuiltin;
  const dimmed = clickable && !isCompatible(controllerType, dev.transport);
  const hasKnowledge = hasDeviceKnowledge(dev.part);

  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          {transportIcon(dev.transport)}
          <span className="truncate font-mono text-text">{dev.part}</span>
          <Badge tone="neutral">{dev.transport}</Badge>
        </div>
        <Badge tone={status.tone} className="shrink-0">
          {status.label}
        </Badge>
      </div>
      <p className="mt-1.5 text-xs text-muted">{dev.summary}</p>
      {mode === "pick" && !isBuiltin && (
        <p className="mt-2 text-[11px] text-faint">
          provide .c/.h or datasheet (see Driver Import)
        </p>
      )}
      {mode === "browse" && hasKnowledge && (
        <div className="mt-3">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-7 px-2 text-xs"
            onClick={onToggleKnowledge}
            aria-expanded={expanded}
          >
            <BookOpen className="h-3.5 w-3.5" />
            {expanded ? "Hide knowledge" : "Open knowledge"}
          </Button>
        </div>
      )}
      {mode === "browse" && expanded && (
        <div className="mt-3 border-t border-border pt-3">
          <DeviceKnowledgePanel part={dev.part} compact />
        </div>
      )}
    </>
  );

  if (clickable) {
    return (
      <button
        type="button"
        onClick={() => onPick?.(dev)}
        className={cn(
          "w-full rounded-lg text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
          dimmed && "opacity-50",
        )}
        aria-label={`Pick ${dev.part}`}
      >
        <Card className="border-border bg-elev px-3 py-2.5 transition-colors hover:border-accent/60 hover:bg-inset">
          {body}
        </Card>
      </button>
    );
  }

  return (
    <Card className="px-3 py-2.5">
      {body}
    </Card>
  );
}
