import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, ArrowDownToLine, ArrowUpFromLine, BookOpen, Code2, ExternalLink, ListChecks, Loader2, Search, Send, Settings2 } from "lucide-react";
import { Badge, Button, Input, Tabs, TabsContent, TabsList, TabsTrigger, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import {
  getDeviceKnowledge,
  getRegisterTransfers,
  type DeviceKnowledgePack,
  type KnowledgeRegister,
  type KnowledgeRecipe,
  type KnowledgeRegisterTransfer,
} from "./knowledge";
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

function normalizeSearchText(value: string) {
  return value
    .toLowerCase()
    .replace(/[_\-./:#[\]()]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function compactSearchText(value: string) {
  return normalizeSearchText(value).replace(/\s+/g, "");
}

const QUERY_STOPWORDS = new Set([
  "bir",
  "bu",
  "da",
  "de",
  "icin",
  "için",
  "ile",
  "mi",
  "ne",
  "nereden",
  "nasil",
  "nasıl",
  "register",
  "bit",
  "field",
  "oku",
  "okuma",
  "yaz",
  "yazma",
]);

function questionTerms(question: string) {
  return normalizeSearchText(question)
    .split(" ")
    .map((term) => term.trim())
    .filter((term) => term.length >= 2 && !QUERY_STOPWORDS.has(term));
}

function scoreText(value: string, terms: string[]) {
  const normalized = normalizeSearchText(value);
  const compact = compactSearchText(value);
  return terms.reduce((score, term) => {
    const compactTerm = term.replace(/\s+/g, "");
    if (normalized.includes(term)) return score + 2;
    if (compactTerm && compact.includes(compactTerm)) return score + 1;
    return score;
  }, 0);
}

function transferContextText(transfers: KnowledgeRegisterTransfer[]) {
  return transfers
    .map((transfer) => [
      transfer.title,
      transfer.access,
      transfer.txBytes,
      transfer.rxBytes,
      transfer.tx.join(" "),
      transfer.rx.join(" "),
      transfer.code.join(" "),
      transfer.note ?? "",
    ].join(" "))
    .join("\n");
}

function registerContextText(part: string, reg: KnowledgeRegister) {
  const fields = (reg.fields ?? [])
    .map((field) => `${field.bits} ${field.name} ${field.meaning} ${(field.values ?? []).join(" ")}`)
    .join("\n");
  return [
    reg.name,
    reg.address,
    reg.access,
    reg.width,
    reg.reset ?? "",
    reg.purpose,
    fields,
    transferContextText(getRegisterTransfers(part, reg)),
  ].join("\n");
}

function buildKnowledgeAskContext(pack: DeviceKnowledgePack, question: string) {
  const terms = questionTerms(question);
  const rankedRegisters = pack.registers
    .map((reg) => ({ reg, score: scoreText(registerContextText(pack.part, reg), terms) }))
    .sort((a, b) => b.score - a.score);
  const selectedRegisters = rankedRegisters.some((item) => item.score > 0)
    ? rankedRegisters.filter((item) => item.score > 0).slice(0, 18)
    : rankedRegisters.slice(0, 24);

  const lines: string[] = [
    `PART: ${pack.part}`,
    `REVIEWED_AT: ${pack.reviewedAt}`,
    `SCOPE: ${pack.scope}`,
    "",
    "OVERVIEW:",
    pack.overview,
    "",
    "KARAR NOKTALARI:",
    ...pack.keyFacts.map((item) => `- ${item}`),
    "",
    "KONFIGURASYON:",
    ...pack.configuration.map((item) => `- ${item}`),
    "",
    "SORUYA EN YAKIN REGISTERLAR:",
  ];

  selectedRegisters.forEach(({ reg }) => {
    const transfers = getRegisterTransfers(pack.part, reg);
    lines.push(`- ${reg.name} address=${reg.address} access=${reg.access} width=${reg.width}${reg.reset ? ` reset=${reg.reset}` : ""}`);
    lines.push(`  purpose: ${reg.purpose}`);
    if (reg.fields?.length) {
      lines.push("  bitfields:");
      reg.fields.forEach((field) => {
        lines.push(`    - ${field.bits} ${field.name}: ${field.meaning}`);
        if (field.values?.length) {
          lines.push(`      values: ${field.values.join("; ")}`);
        }
      });
    }
    if (transfers.length) {
      lines.push("  driver view:");
      transfers.forEach((transfer) => {
        lines.push(`    - ${transfer.title} access=${transfer.access} tx_bytes=${transfer.txBytes} rx_bytes=${transfer.rxBytes}`);
        lines.push(`      TX: ${transfer.tx.join(" | ")}`);
        lines.push(`      RX: ${transfer.rx.join(" | ")}`);
        lines.push(`      code: ${transfer.code.join(" ")}`);
        if (transfer.note) lines.push(`      note: ${transfer.note}`);
      });
    }
  });

  lines.push("", "RECETELER:");
  pack.recipes.forEach((recipe) => {
    lines.push(`- ${recipe.title}: ${recipe.goal}`);
    recipe.steps.forEach((step, index) => lines.push(`  ${index + 1}. ${step}`));
  });

  lines.push("", "DIKKAT:");
  pack.gotchas.forEach((item) => lines.push(`- ${item}`));
  lines.push("", "CODEGEN NOTLARI:");
  pack.codegenNotes.forEach((item) => lines.push(`- ${item}`));
  lines.push("", "TUM REGISTER/KOMUT AD INDEKSI:");
  pack.registers.forEach((reg) => {
    const fields = (reg.fields ?? []).map((field) => field.name).join(", ");
    lines.push(`- ${reg.name} ${reg.address}${fields ? ` fields=[${fields}]` : ""}`);
  });
  lines.push("", "KAYNAKLAR:");
  pack.sources.forEach((source) => lines.push(`- ${source.label}: ${source.url}`));

  return lines.join("\n");
}

function textMatchesSearch(values: Array<string | undefined>, normalizedQuery: string, compactQuery: string) {
  return values.filter(Boolean).some((value) => {
    const normalizedValue = normalizeSearchText(value!);
    return normalizedValue.includes(normalizedQuery) || compactSearchText(value!).includes(compactQuery);
  });
}

function registerSearchResult(reg: KnowledgeRegister, query: string) {
  const normalizedQuery = normalizeSearchText(query);
  const compactQuery = compactSearchText(query);
  const fields = reg.fields ?? [];

  if (!normalizedQuery) {
    return { reg, registerMatch: false, matchedFields: [] };
  }

  const registerMatch = textMatchesSearch(
    [reg.name],
    normalizedQuery,
    compactQuery,
  );
  const matchedFields = fields.filter((field) =>
    textMatchesSearch(
      [field.name],
      normalizedQuery,
      compactQuery,
    ),
  );

  return { reg, registerMatch, matchedFields };
}

function transferToneClass(tone: KnowledgeRegisterTransfer["tone"]) {
  if (tone === "danger") return "border-danger/40 bg-danger/10";
  if (tone === "warn") return "border-warn/40 bg-warn/10";
  return "border-border bg-elev";
}

function transferBadgeTone(tone: KnowledgeRegisterTransfer["tone"]) {
  if (tone === "danger") return "danger" as const;
  if (tone === "warn") return "warn" as const;
  return "neutral" as const;
}

function TransferRow({
  icon,
  label,
  bytes,
  values,
}: {
  icon: ReactNode;
  label: string;
  bytes: string;
  values: string[];
}) {
  return (
    <div className="grid gap-2 sm:grid-cols-[82px_minmax(0,1fr)]">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase text-muted">
        {icon}
        <span>{label}</span>
        <span className="rounded bg-inset px-1.5 py-0.5 font-mono normal-case text-faint">{bytes}</span>
      </div>
      <div className="flex min-w-0 flex-wrap gap-1.5">
        {values.map((value) => (
          <span key={value} className="max-w-full truncate rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[10px] text-text">
            {value}
          </span>
        ))}
      </div>
    </div>
  );
}

function TransferPreview({ transfers }: { transfers: KnowledgeRegisterTransfer[] }) {
  if (!transfers.length) return null;

  return (
    <div className="mb-3 space-y-2">
      <div className="flex items-center gap-2 text-xs font-semibold text-text">
        <Code2 className="h-3.5 w-3.5 text-accent" aria-hidden />
        Driver view
      </div>
      <div className="grid gap-2 xl:grid-cols-2">
        {transfers.map((transfer) => (
          <div
            key={`${transfer.title}-${transfer.tx.join("|")}-${transfer.rx.join("|")}`}
            className={cn("rounded-md border px-3 py-2", transferToneClass(transfer.tone))}
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-text">{transfer.title}</span>
              <Badge tone={transferBadgeTone(transfer.tone)} className="font-mono">
                {transfer.access}
              </Badge>
            </div>
            <div className="space-y-2">
              <TransferRow
                icon={<ArrowUpFromLine className="h-3 w-3 text-accent" aria-hidden />}
                label="TX"
                bytes={transfer.txBytes}
                values={transfer.tx}
              />
              <TransferRow
                icon={<ArrowDownToLine className="h-3 w-3 text-accent" aria-hidden />}
                label="RX"
                bytes={transfer.rxBytes}
                values={transfer.rx}
              />
              <pre className="overflow-x-auto rounded border border-border bg-bg px-2 py-1.5 font-mono text-[11px] leading-relaxed text-muted">
                {transfer.code.join("\n")}
              </pre>
              {transfer.note && <p className="text-[11px] leading-relaxed text-faint">{transfer.note}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function RegisterExplorer({ part, registers }: { part: string; registers: KnowledgeRegister[] }) {
  const [selectedKey, setSelectedKey] = useState(() => (registers[0] ? registerKey(registers[0]) : ""));
  const [searchQuery, setSearchQuery] = useState("");
  const [showDriverView, setShowDriverView] = useState(false);
  const normalizedQuery = normalizeSearchText(searchQuery);
  const searchActive = normalizedQuery.length > 0;
  const searchResults = useMemo(
    () => registers.map((reg) => registerSearchResult(reg, searchQuery)),
    [registers, searchQuery],
  );
  const filteredResults = useMemo(
    () =>
      searchActive
        ? searchResults.filter((result) => result.registerMatch || result.matchedFields.length > 0)
        : searchResults,
    [searchActive, searchResults],
  );
  const selectedResult = useMemo(
    () => filteredResults.find((result) => registerKey(result.reg) === selectedKey) ?? filteredResults[0],
    [filteredResults, selectedKey],
  );
  const selectedRegister = selectedResult?.reg;
  const transfers = useMemo(
    () => (selectedRegister ? getRegisterTransfers(part, selectedRegister) : []),
    [part, selectedRegister],
  );
  const fieldsToShow = useMemo(() => {
    if (!selectedRegister?.fields) return [];
    if (searchActive && selectedResult?.matchedFields.length) return selectedResult.matchedFields;
    return selectedRegister.fields;
  }, [searchActive, selectedRegister, selectedResult]);

  useEffect(() => {
    if (!registers.length) {
      setSelectedKey("");
      return;
    }

    if (!filteredResults.length) {
      setSelectedKey("");
      return;
    }

    if (!filteredResults.some((result) => registerKey(result.reg) === selectedKey)) {
      setSelectedKey(registerKey(filteredResults[0].reg));
    }
  }, [filteredResults, registers.length, selectedKey]);

  if (!registers.length) {
    return (
      <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
        Register bilgisi henüz eklenmemiş.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-inset/40 p-2">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint"
            aria-hidden
          />
          <Input
            type="search"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            placeholder="Register veya bit field ara..."
            aria-label="Register ve bit field filtrele"
            className="pl-9"
          />
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-faint">
          <span>
            {searchActive
              ? `${filteredResults.length}/${registers.length} register eşleşti`
              : `${registers.length} register listeleniyor`}
          </span>
          {searchActive && (
            <span>
              Sadece register adı ve bit field adı aranır.
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-[minmax(220px,280px)_minmax(0,1fr)]">
        <div className="max-h-[620px] min-h-0 space-y-1 overflow-y-auto rounded-md border border-border bg-inset/40 p-1.5">
          {filteredResults.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-1 px-3 py-12 text-center">
              <Search className="h-5 w-5 text-faint" aria-hidden />
              <p className="text-xs text-muted">Bu aramayla eşleşen register yok.</p>
              <p className="text-[11px] text-faint">Register adı veya bit field adıyla tekrar dene.</p>
            </div>
          ) : (
            filteredResults.map((result) => {
              const reg = result.reg;
              const key = registerKey(reg);
              const active = key === registerKey(selectedRegister!);
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
                    {searchActive && result.registerMatch && (
                      <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] text-accent">
                        register
                      </span>
                    )}
                    {searchActive && result.matchedFields.length > 0 && (
                      <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] text-accent">
                        {result.matchedFields.length} bit field
                      </span>
                    )}
                  </div>
                  {searchActive && result.matchedFields.length > 0 && (
                    <div className="mt-1.5 flex min-w-0 flex-wrap gap-1">
                      {result.matchedFields.slice(0, 3).map((field) => (
                        <span
                          key={`${key}-${field.bits}-${field.name}`}
                          className="max-w-full truncate rounded border border-border bg-inset px-1.5 py-0.5 font-mono text-[10px] text-muted"
                        >
                          {field.name}
                        </span>
                      ))}
                      {result.matchedFields.length > 3 && (
                        <span className="rounded bg-inset px-1.5 py-0.5 text-[10px] text-faint">
                          +{result.matchedFields.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })
          )}
        </div>

        {selectedRegister ? (
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

        {searchActive && selectedResult?.matchedFields.length ? (
          <div className="mb-2 rounded-md border border-accent/25 bg-accent/10 px-2 py-1.5 text-[11px] text-accent">
            Bu register içinde {selectedResult.matchedFields.length}/{selectedRegister.fields?.length ?? 0} bit field eşleşti.
          </div>
        ) : null}

        {fieldsToShow.length > 0 ? (
          <div className="space-y-2">
            {fieldsToShow.map((field) => (
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

        {transfers.length > 0 && (
          <div className="mt-3 border-t border-border pt-3">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setShowDriverView((value) => !value)}
            >
              <Code2 className="h-3.5 w-3.5" aria-hidden />
              {showDriverView ? "Driver view'u gizle" : "Driver view'u göster"}
            </Button>
            {showDriverView && <div className="mt-3"><TransferPreview transfers={transfers} /></div>}
          </div>
        )}
          </div>
        ) : (
          <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
            Aramayla eşleşen register seçimi yok.
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

function askErrorMessage(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "string") return parsed;
    if (parsed?.error) return String(parsed.error);
    if (parsed?.message) return String(parsed.message);
    if (Array.isArray(parsed?.errors) && parsed.errors[0]?.message) return String(parsed.errors[0].message);
  } catch {
    /* raw string is already useful */
  }
  return raw;
}

function KnowledgeAskPanel({ pack }: { pack: DeviceKnowledgePack }) {
  const llm = useStore((s) => s.llm);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [meta, setMeta] = useState<{ model: string; contextChars: number } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError("");
    setAnswer("");
    setMeta(null);
    try {
      const context = buildKnowledgeAskContext(pack, trimmed);
      const response = await api.knowledgeAsk({
        part: pack.part,
        question: trimmed,
        context,
        llm,
      });
      setAnswer(response.answer);
      setMeta({ model: response.model, contextChars: response.context_chars });
    } catch (err) {
      setError(askErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-inset p-3">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Search className="h-3.5 w-3.5 text-accent" aria-hidden />
            <h4 className="text-xs font-semibold text-text">Knowledge sorusu</h4>
          </div>
          <Badge tone={llm.enabled ? "accent" : "warn"}>
            LLM {llm.enabled ? "on" : "off"}
          </Badge>
        </div>
        <Textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Örn. PLL2 lock nereden okunur? Bu register'a nasıl yazılır? Flash sector erase akışı nedir?"
          className="min-h-24"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[11px] leading-relaxed text-faint">
            Cevap sadece {pack.part} bilgi paketi ve driver view context'i üzerinden üretilir.
          </p>
          <Button type="button" size="sm" onClick={submit} disabled={!question.trim() || loading}>
            {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Send className="h-3.5 w-3.5" aria-hidden />}
            Sor
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs leading-relaxed text-danger">
          {error}
        </div>
      )}

      {answer && (
        <div className="rounded-md border border-border bg-elev p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold text-text">Cevap</span>
            {meta && (
              <span className="font-mono text-[10px] text-faint">
                {meta.model} / {meta.contextChars} chars
              </span>
            )}
          </div>
          <div className="whitespace-pre-wrap text-xs leading-relaxed text-muted">{answer}</div>
        </div>
      )}
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
          <TabsTrigger value="ask">Soru</TabsTrigger>
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
          <RegisterExplorer part={pack.part} registers={pack.registers} />
        </TabsContent>

        <TabsContent value="recipes">
          <RecipeList recipes={pack.recipes} />
        </TabsContent>

        <TabsContent value="ask">
          <KnowledgeAskPanel pack={pack} />
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
