import { useMemo, useState } from "react";
import { BookOpen, Loader2, Search, Send, ShieldCheck } from "lucide-react";
import { Badge, Button, Textarea } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import {
  getRegisterTransfers,
  listDeviceKnowledge,
  type DeviceKnowledgePack,
  type KnowledgeRegister,
  type KnowledgeRecipe,
  type KnowledgeRegisterTransfer,
} from "./knowledge";

const QUERY_STOPWORDS = new Set([
  "bir",
  "bu",
  "da",
  "de",
  "hangi",
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
  "entegre",
  "entegreler",
  "oku",
  "okuma",
  "yaz",
  "yazma",
  "var",
]);

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

function questionTerms(question: string) {
  return normalizeSearchText(question)
    .split(" ")
    .map((term) => term.trim())
    .filter((term) => term.length >= 2 && !QUERY_STOPWORDS.has(term));
}

function scoreText(value: string, terms: string[]) {
  if (!terms.length) return 0;
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
    part,
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

function packContextText(pack: DeviceKnowledgePack) {
  return [
    pack.part,
    pack.scope,
    pack.overview,
    ...pack.keyFacts,
    ...pack.configuration,
    ...pack.gotchas,
    ...pack.codegenNotes,
    ...pack.sources.map((source) => `${source.label} ${source.url}`),
  ].join("\n");
}

function recipeContextText(pack: DeviceKnowledgePack, recipe: KnowledgeRecipe) {
  return [pack.part, recipe.title, recipe.goal, ...recipe.steps].join("\n");
}

export function buildKnowledgeAskContext(packs: DeviceKnowledgePack[], question: string) {
  const terms = questionTerms(question);
  const rankedPacks = packs
    .map((pack) => ({ pack, score: scoreText(packContextText(pack), terms) }))
    .sort((a, b) => b.score - a.score || a.pack.part.localeCompare(b.pack.part));
  const selectedPacks = rankedPacks.some((item) => item.score > 0)
    ? rankedPacks.filter((item) => item.score > 0).slice(0, 12).map((item) => item.pack)
    : rankedPacks.map((item) => item.pack);

  const rankedRegisters = packs
    .flatMap((pack) =>
      pack.registers.map((reg) => ({
        pack,
        reg,
        score: scoreText(registerContextText(pack.part, reg), terms),
      })),
    )
    .sort((a, b) => b.score - a.score || a.pack.part.localeCompare(b.pack.part) || a.reg.name.localeCompare(b.reg.name));
  const selectedRegisters = rankedRegisters.some((item) => item.score > 0)
    ? rankedRegisters.filter((item) => item.score > 0).slice(0, 36)
    : rankedRegisters.slice(0, 36);

  const rankedRecipes = packs
    .flatMap((pack) =>
      pack.recipes.map((recipe) => ({
        pack,
        recipe,
        score: scoreText(recipeContextText(pack, recipe), terms),
      })),
    )
    .sort((a, b) => b.score - a.score || a.pack.part.localeCompare(b.pack.part) || a.recipe.title.localeCompare(b.recipe.title));
  const selectedRecipes = rankedRecipes.some((item) => item.score > 0)
    ? rankedRecipes.filter((item) => item.score > 0).slice(0, 14)
    : rankedRecipes.slice(0, 14);

  const lines: string[] = [
    "PART: GLOBAL_VERIFIED_KNOWLEDGE",
    "KISIT: Bu context sadece Spec2Code icindeki statik ve gözden geçirilmiş knowledge paketlerinden üretildi. Context dışı bilgi kullanılmamalıdır.",
    `PAKET_SAYISI: ${packs.length}`,
    `REGISTER_KOMUT_SAYISI: ${packs.reduce((sum, pack) => sum + pack.registers.length, 0)}`,
    "",
    "PAKETLER:",
  ];

  packs.forEach((pack) => {
    lines.push(`- ${pack.part} reviewed_at=${pack.reviewedAt}`);
    lines.push(`  scope: ${pack.scope}`);
    lines.push(`  overview: ${pack.overview}`);
  });

  lines.push("", "SORUYA EN YAKIN ENTEGRELER:");
  selectedPacks.forEach((pack) => {
    lines.push(`- ${pack.part}: ${pack.overview}`);
    pack.keyFacts.forEach((item) => lines.push(`  fact: ${item}`));
    pack.configuration.forEach((item) => lines.push(`  config: ${item}`));
  });

  lines.push("", "SORUYA EN YAKIN REGISTER/KOMUTLAR:");
  selectedRegisters.forEach(({ pack, reg }) => {
    const transfers = getRegisterTransfers(pack.part, reg);
    lines.push(`- part=${pack.part} name=${reg.name} address=${reg.address} access=${reg.access} width=${reg.width}${reg.reset ? ` reset=${reg.reset}` : ""}`);
    lines.push(`  purpose: ${reg.purpose}`);
    if (reg.fields?.length) {
      lines.push("  bitfields:");
      reg.fields.forEach((field) => {
        lines.push(`    - ${field.bits} ${field.name}: ${field.meaning}`);
        if (field.values?.length) lines.push(`      values: ${field.values.join("; ")}`);
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
  selectedRecipes.forEach(({ pack, recipe }) => {
    lines.push(`- part=${pack.part} ${recipe.title}: ${recipe.goal}`);
    recipe.steps.forEach((step, index) => lines.push(`  ${index + 1}. ${step}`));
  });

  lines.push("", "DIKKAT VE CODEGEN NOTLARI:");
  selectedPacks.forEach((pack) => {
    lines.push(`- ${pack.part}`);
    pack.gotchas.forEach((item) => lines.push(`  gotcha: ${item}`));
    pack.codegenNotes.forEach((item) => lines.push(`  codegen: ${item}`));
  });

  lines.push("", "TUM REGISTER/KOMUT AD INDEKSI:");
  packs.forEach((pack) => {
    lines.push(`- ${pack.part}`);
    pack.registers.forEach((reg) => {
      const fields = (reg.fields ?? []).map((field) => field.name).join(", ");
      lines.push(`  - ${reg.name} ${reg.address}${fields ? ` fields=[${fields}]` : ""}`);
    });
  });

  lines.push("", "KAYNAKLAR:");
  packs.forEach((pack) => {
    pack.sources.forEach((source) => lines.push(`- ${pack.part} ${source.label}: ${source.url}`));
  });

  return lines.join("\n");
}

function askErrorMessage(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "string") return parsed;
    if (parsed?.error) return String(parsed.error);
    if (parsed?.message) return String(parsed.message);
    if (Array.isArray(parsed?.unsupported_tokens) && parsed.unsupported_tokens.length > 0) {
      return `LLM cevabı context dışı token içerdi: ${parsed.unsupported_tokens.join(", ")}`;
    }
    if (Array.isArray(parsed?.errors) && parsed.errors[0]?.message) return String(parsed.errors[0].message);
  } catch {
    /* raw string is already useful */
  }
  return raw;
}

export default function KnowledgeAskPanel({
  className,
  packs = listDeviceKnowledge(),
}: {
  className?: string;
  packs?: DeviceKnowledgePack[];
}) {
  const llm = useStore((s) => s.llm);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [meta, setMeta] = useState<{ model: string; contextChars: number; grounded: boolean } | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const registerCount = useMemo(() => packs.reduce((sum, pack) => sum + pack.registers.length, 0), [packs]);

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError("");
    setAnswer("");
    setMeta(null);
    try {
      const context = buildKnowledgeAskContext(packs, trimmed);
      const response = await api.knowledgeAsk({
        part: "GLOBAL_VERIFIED_KNOWLEDGE",
        question: trimmed,
        context,
        llm,
      });
      setAnswer(response.answer);
      setMeta({
        model: response.model,
        contextChars: response.context_chars,
        grounded: response.grounded ?? false,
      });
    } catch (err) {
      setError(askErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className={cn("rounded-lg border border-border bg-elev p-4", className)}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-sm font-semibold text-text">Bilgi soru merkezi</h3>
          </div>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted">
            Soru serbesttir; cevap context olarak sadece doğrulanmış katalog bilgi paketi, register, bit field, reçete ve driver view satırlarından beslenir.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <Badge tone={llm.enabled ? "accent" : "warn"}>LLM {llm.enabled ? "on" : "off"}</Badge>
          <Badge tone="neutral">{packs.length} entegre</Badge>
          <Badge tone="neutral">{registerCount} register/komut</Badge>
          <Badge tone="ok">
            <ShieldCheck className="h-3 w-3" aria-hidden />
            context kontrolü
          </Badge>
        </div>
      </div>

      <Textarea
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={(event) => {
          if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
            event.preventDefault();
            void submit();
          }
        }}
        placeholder="Örn. LMK04832 PLL2 lock nereden okunur? Flash sector erase için hangi byte'lar gider? LTC2991 differential ayarı hangi register'ları etkiler?"
        className="min-h-20"
      />

      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] leading-relaxed text-faint">
          Context seçiminde register/bit field adı, açıklama, driver view ve kaynak satırları puanlanır. Context dışında bilgi yoksa model bunu açıkça söylemelidir.
        </p>
        <Button type="button" size="sm" onClick={submit} disabled={!question.trim() || loading}>
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Send className="h-3.5 w-3.5" aria-hidden />}
          Sor
        </Button>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs leading-relaxed text-danger">
          {error}
        </div>
      )}

      {answer && (
        <div className="mt-3 rounded-md border border-border bg-inset p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Search className="h-3.5 w-3.5 text-accent" aria-hidden />
              <span className="text-xs font-semibold text-text">Cevap</span>
            </div>
            {meta && (
              <span className="font-mono text-[10px] text-faint">
                {meta.model} / {meta.contextChars} chars / {meta.grounded ? "kontrol ok" : "kontrol yok"}
              </span>
            )}
          </div>
          <div className="whitespace-pre-wrap text-xs leading-relaxed text-muted">{answer}</div>
        </div>
      )}
    </section>
  );
}
