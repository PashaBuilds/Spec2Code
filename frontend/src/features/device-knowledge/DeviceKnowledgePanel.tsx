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

function RegisterTable({ registers }: { registers: KnowledgeRegister[] }) {
  return (
    <div className="max-h-64 overflow-auto rounded-md border border-border">
      <table className="min-w-[620px] border-collapse text-left text-xs">
        <thead className="sticky top-0 bg-inset text-[10px] uppercase tracking-wide text-faint">
          <tr>
            <th className="border-b border-border px-2 py-2 font-semibold">Ad</th>
            <th className="border-b border-border px-2 py-2 font-semibold">Adres/op</th>
            <th className="border-b border-border px-2 py-2 font-semibold">Genişlik</th>
            <th className="border-b border-border px-2 py-2 font-semibold">Erişim</th>
            <th className="border-b border-border px-2 py-2 font-semibold">Amaç</th>
          </tr>
        </thead>
        <tbody>
          {registers.map((reg) => (
            <tr key={`${reg.name}-${reg.address}`} className="border-b border-border/60 last:border-0">
              <td className="px-2 py-2 align-top font-mono text-text">{reg.name}</td>
              <td className="px-2 py-2 align-top font-mono text-accent">{reg.address}</td>
              <td className="px-2 py-2 align-top font-mono text-muted">{reg.width}</td>
              <td className="px-2 py-2 align-top font-mono text-muted">{reg.access}</td>
              <td className="px-2 py-2 align-top text-muted">
                <div>{reg.purpose}</div>
                {reg.fields && reg.fields.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {reg.fields.map((field) => (
                      <span
                        key={field}
                        className="rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[10px] text-faint"
                      >
                        {field}
                      </span>
                    ))}
                  </div>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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
          <RegisterTable registers={pack.registers} />
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
