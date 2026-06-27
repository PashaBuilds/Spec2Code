import * as React from "react";
import { BookOpen, Cpu, HardDrive, Network, Search } from "lucide-react";
import { Card, Badge, Input } from "@/components/ui";
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
  builtin: { tone: "ok", label: "hazır" },
  needs_source: { tone: "warn", label: "kaynak gerekli" },
  from_datasheet: { tone: "accent", label: "datasheet kaynaklı" },
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
 * i2c controller <-> i2c / i2c_mux devices; spi/qspi controller <-> spi devices.
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
  const [selectedPart, setSelectedPart] = React.useState<string | null>(null);

  const filtered = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return catalog;
    return catalog.filter((d) =>
      [d.part, d.summary, d.transport]
        .filter(Boolean)
        .some((field) => field.toLowerCase().includes(q)),
    );
  }, [catalog, query]);

  const selected = React.useMemo(() => {
    if (mode !== "browse") return null;
    return filtered.find((dev) => dev.part === selectedPart) ?? filtered[0] ?? null;
  }, [filtered, mode, selectedPart]);

  if (mode === "browse") {
    return (
      <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
        <aside className="flex min-h-0 flex-col rounded-lg border border-border bg-elev">
          <div className="border-b border-border p-3">
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
                aria-hidden
              />
              <Input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Entegre ara..."
                aria-label="Katalog entegrelerini filtrele"
                className="pl-9"
              />
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
                <Search className="h-5 w-5 text-faint" aria-hidden />
                <p className="text-sm text-muted">Filtreyle eşleşen entegre yok.</p>
                <p className="text-xs text-faint">
                  {catalog.length === 0 ? "Katalog boş." : "Farklı bir ifade dene."}
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                {filtered.map((dev) => (
                  <CatalogListItem
                    key={dev.part}
                    dev={dev}
                    selected={selected?.part === dev.part}
                    onSelect={() => setSelectedPart(dev.part)}
                  />
                ))}
              </div>
            )}
          </div>
        </aside>

        <section className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
          {selected ? <CatalogDetail dev={selected} /> : <EmptyCatalogDetail />}
        </section>
      </div>
    );
  }

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
          placeholder="Part, özet veya transport ile filtrele..."
          aria-label="Katalog cihazlarını filtrele"
          className="pl-9"
        />
      </div>

      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center gap-1 py-12 text-center">
            <Search className="h-5 w-5 text-faint" aria-hidden />
            <p className="text-sm text-muted">Filtreyle eşleşen cihaz yok.</p>
            <p className="text-xs text-faint">
              {catalog.length === 0 ? "Katalog boş." : "Farklı bir ifade dene."}
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
}

function DeviceCard({
  dev,
  mode,
  onPick,
  controllerType,
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
          .c/.h veya datasheet verilmeli (Driver Import ekranına bak)
        </p>
      )}
      {mode === "browse" && hasKnowledge && <Badge tone="accent">bilgi paketi</Badge>}
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
        aria-label={`${dev.part} seç`}
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

function CatalogListItem({
  dev,
  selected,
  onSelect,
}: {
  dev: CatalogDevice;
  selected: boolean;
  onSelect: () => void;
}) {
  const status = STATUS_META[dev.status];
  const hasKnowledge = hasDeviceKnowledge(dev.part);

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "w-full rounded-md border px-3 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        selected
          ? "border-accent/60 bg-accent/15 text-text"
          : "border-transparent text-muted hover:border-border hover:bg-inset hover:text-text",
      )}
      aria-pressed={selected}
    >
      <div className="flex items-center gap-2">
        {transportIcon(dev.transport)}
        <span className="min-w-0 flex-1 truncate font-mono text-sm">{dev.part}</span>
        <Badge tone={status.tone} className="shrink-0">
          {status.label}
        </Badge>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <Badge tone="neutral">{dev.transport}</Badge>
        {hasKnowledge && (
          <span className="inline-flex items-center gap-1 text-[11px] text-accent">
            <BookOpen className="h-3 w-3" aria-hidden />
            bilgi
          </span>
        )}
      </div>
      <p className="mt-1 line-clamp-2 text-xs text-faint">{dev.summary}</p>
    </button>
  );
}

function CatalogDetail({ dev }: { dev: CatalogDevice }) {
  const status = STATUS_META[dev.status];

  return (
    <div className="min-h-full p-5">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-4 border-b border-border pb-4">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {transportIcon(dev.transport)}
            <h2 className="font-mono text-xl font-semibold text-text">{dev.part}</h2>
            <Badge tone="neutral">{dev.transport}</Badge>
            <Badge tone={status.tone}>{status.label}</Badge>
          </div>
          <p className="max-w-3xl text-sm leading-relaxed text-muted">{dev.summary}</p>
        </div>
        {dev.descriptor && (
          <div className="rounded-md border border-border bg-inset px-3 py-2 text-right">
            <div className="text-[10px] uppercase tracking-wide text-faint">Descriptor</div>
            <div className="mt-1 font-mono text-xs text-muted">{dev.descriptor}</div>
          </div>
        )}
      </div>

      <DeviceKnowledgePanel part={dev.part} />
    </div>
  );
}

function EmptyCatalogDetail() {
  return (
    <div className="flex h-full min-h-[420px] flex-col items-center justify-center gap-2 p-6 text-center">
      <Search className="h-5 w-5 text-faint" aria-hidden />
      <p className="text-sm text-muted">Bir entegre seç.</p>
      <p className="text-xs text-faint">Seçilen entegrenin pin, register, reçete ve dikkat notları burada açılır.</p>
    </div>
  );
}
