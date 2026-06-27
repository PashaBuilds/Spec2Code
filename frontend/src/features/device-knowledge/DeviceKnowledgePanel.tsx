import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BookOpen, ExternalLink, ListChecks, Settings2 } from "lucide-react";
import { Badge, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui";
import { cn } from "@/lib/utils";
import { getDeviceKnowledge, type KnowledgeRegister, type KnowledgeRecipe } from "./knowledge";
import DevicePinMap from "./DevicePinMap";

function EmptyKnowledge({ part }: { part: string }) {
  return (
    <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
      {part} için statik bilgi paketi henüz eklenmemiş.
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item) => (
        <li key={item} className="flex gap-2 text-xs leading-relaxed text-muted">
          <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function registerKey(reg: KnowledgeRegister) {
  return `${reg.name}-${reg.address}`;
}

function RegisterExplorer({ registers }: { registers: KnowledgeRegister[] }) {
  const [selectedKey, setSelectedKey] = useState(() => (registers[0] ? registerKey(registers[0]) : ""));
  const selectedRegister = useMemo(
    () => registers.find((reg) => registerKey(reg) === selectedKey) ?? registers[0],
    [registers, selectedKey],
  );

  useEffect(() => {
    if (!registers.length) {
      setSelectedKey("");
      return;
    }

    if (!registers.some((reg) => registerKey(reg) === selectedKey)) {
      setSelectedKey(registerKey(registers[0]));
    }
  }, [registers, selectedKey]);

  if (!selectedRegister) {
    return (
      <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
        Register bilgisi henüz eklenmemiş.
      </div>
    );
  }

  return (
    <div className="grid gap-3 lg:grid-cols-[minmax(220px,280px)_minmax(0,1fr)]">
      <div className="min-h-0 space-y-1 rounded-md border border-border bg-inset/40 p-1.5">
        {registers.map((reg) => {
          const key = registerKey(reg);
          const active = key === registerKey(selectedRegister);
          const fieldCount = reg.fields?.length ?? 0;

          return (
            <button
              key={key}
              type="button"
              onClick={() => setSelectedKey(key)}
              aria-pressed={active}
              className={cn(
                "w-full rounded-md border px-2.5 py-2 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
                active
                  ? "border-accent/60 bg-accent/15 text-text"
                  : "border-transparent text-muted hover:border-border hover:bg-elev hover:text-text",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <span className="min-w-0 truncate font-mono text-xs font-semibold">{reg.name}</span>
                <span className="shrink-0 font-mono text-[10px] text-accent">{reg.address}</span>
              </div>
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Badge tone="neutral" className="font-mono">
                  {reg.access}
                </Badge>
                <span className="font-mono text-[10px] text-faint">{reg.width}</span>
                {fieldCount > 0 && (
                  <span className="rounded bg-elev px-1.5 py-0.5 text-[10px] text-faint">
                    {fieldCount} alan
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <div className="min-w-0 rounded-md border border-border bg-inset p-3">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <h4 className="truncate font-mono text-sm font-semibold text-text">{selectedRegister.name}</h4>
            <p className="mt-1 text-xs leading-relaxed text-muted">{selectedRegister.purpose}</p>
          </div>
          <div className="flex shrink-0 flex-wrap gap-1.5">
            <Badge tone="accent" className="font-mono">
              {selectedRegister.address}
            </Badge>
            <Badge tone="neutral" className="font-mono">
              {selectedRegister.access}
            </Badge>
            {selectedRegister.reset && (
              <Badge tone="neutral" className="font-mono">
                reset {selectedRegister.reset}
              </Badge>
            )}
          </div>
        </div>

        {selectedRegister.fields && selectedRegister.fields.length > 0 ? (
          <div className="space-y-2">
            {selectedRegister.fields.map((field) => (
              <div
                key={`${selectedRegister.name}-${field.bits}-${field.name}`}
                className="rounded-md border border-border bg-elev px-3 py-2"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[10px] text-accent">
                    {field.bits}
                  </span>
                  <span className="font-mono text-xs font-semibold text-text">{field.name}</span>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">{field.meaning}</p>
                {field.values && field.values.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {field.values.map((value) => (
                      <span key={value} className="rounded bg-inset px-1.5 py-0.5 text-[10px] text-faint">
                        {value}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-md border border-border bg-elev px-3 py-2 text-xs leading-relaxed text-muted">
            Bu register/komut için ayrı bitfield ayrımı yok; işlem anlamı üstteki amaç satırında verilmiştir.
          </div>
        )}
      </div>
    </div>
  );
}

function RecipeList({ recipes }: { recipes: KnowledgeRecipe[] }) {
  return (
    <div className="space-y-3">
      {recipes.map((recipe) => (
        <div key={recipe.title} className="rounded-md border border-border bg-inset/50 p-3">
          <div className="mb-1 flex items-center gap-2">
            <ListChecks className="h-3.5 w-3.5 text-accent" aria-hidden />
            <h4 className="text-xs font-semibold text-text">{recipe.title}</h4>
          </div>
          <p className="mb-2 text-xs text-muted">{recipe.goal}</p>
          <ol className="space-y-1.5 pl-4">
            {recipe.steps.map((step, index) => (
              <li key={`${recipe.title}-${index}`} className="list-decimal text-xs leading-relaxed text-muted">
                {step}
              </li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}

export default function DeviceKnowledgePanel({
  part,
  config,
  compact = false,
  className,
}: {
  part: string;
  config?: Record<string, unknown>;
  compact?: boolean;
  className?: string;
}) {
  const pack = getDeviceKnowledge(part);
  if (!pack) return <EmptyKnowledge part={part} />;
  const hasPinMap = Boolean(pack.pinMap);

  return (
    <div className={cn("space-y-3", className)}>
      <div className="rounded-md border border-border bg-inset p-3">
        <div className="mb-2 flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-accent" aria-hidden />
              <h3 className="truncate text-sm font-semibold text-text">{pack.part} bilgi paketi</h3>
            </div>
            <p className="mt-1 text-xs text-faint">{pack.scope}</p>
          </div>
          <Badge tone="neutral" className="shrink-0">
            gözden geçirildi {pack.reviewedAt}
          </Badge>
        </div>
        <p className="text-xs leading-relaxed text-muted">{pack.overview}</p>
      </div>

      <Tabs defaultValue="overview" className="space-y-3">
        <TabsList className="flex w-full overflow-x-auto">
          <TabsTrigger value="overview">Özet</TabsTrigger>
          {hasPinMap && <TabsTrigger value="pinmap">Pin haritası</TabsTrigger>}
          <TabsTrigger value="registers">Register</TabsTrigger>
          <TabsTrigger value="recipes">Reçete</TabsTrigger>
          <TabsTrigger value="notes">Dikkat</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-3">
          <div className="space-y-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold text-text">
              <Settings2 className="h-3.5 w-3.5 text-accent" aria-hidden />
              Kullanıma dair karar noktaları
            </h4>
            <BulletList items={pack.keyFacts} />
          </div>
          {!compact && (
            <div className="space-y-2">
              <h4 className="text-xs font-semibold text-text">Konfigürasyon</h4>
              <BulletList items={pack.configuration} />
            </div>
          )}
        </TabsContent>

        {hasPinMap && (
          <TabsContent value="pinmap">
            <DevicePinMap part={pack.part} pinMap={pack.pinMap!} config={config} />
          </TabsContent>
        )}

        <TabsContent value="registers">
          <RegisterExplorer registers={pack.registers} />
        </TabsContent>

        <TabsContent value="recipes">
          <RecipeList recipes={pack.recipes} />
        </TabsContent>

        <TabsContent value="notes" className="space-y-3">
          <div className="space-y-2">
            <h4 className="flex items-center gap-2 text-xs font-semibold text-text">
              <AlertTriangle className="h-3.5 w-3.5 text-warn" aria-hidden />
              Dikkat edilmesi gerekenler
            </h4>
            <BulletList items={pack.gotchas} />
          </div>
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-text">Codegen notları</h4>
            <BulletList items={pack.codegenNotes} />
          </div>
          <div className="space-y-1">
            <h4 className="text-xs font-semibold text-text">Kaynak</h4>
            {pack.sources.map((source) => (
              <a
                key={source.url}
                className="flex min-w-0 items-center gap-1.5 text-xs text-accent hover:underline"
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink className="h-3 w-3 shrink-0" aria-hidden />
                <span className="truncate">{source.label}</span>
              </a>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
