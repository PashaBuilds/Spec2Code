import { useEffect, useMemo, useState } from "react";
import { BookOpen, CheckCircle2, CircleDashed, Loader2, Search, Send, ShieldCheck } from "lucide-react";
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

const ASK_STAGES = [
  {
    id: "context",
    label: "Context hazırlanıyor",
    detail: "Soruya yakın entegre, register, bit field, reçete ve driver view satırları seçiliyor.",
    progress: 26,
  },
  {
    id: "llm",
    label: "LLM cevabı bekleniyor",
    detail: "OpenAI uyumlu lokal endpoint'e doğrulanmış context ile istek gönderildi.",
    progress: 68,
  },
  {
    id: "grounding",
    label: "Cevap kontrol ediliyor",
    detail: "Backend, cevaptaki register/opcode/bitfield tokenlarını verilen context ile karşılaştırıyor.",
    progress: 88,
  },
  {
    id: "format",
    label: "Cevap düzenleniyor",
    detail: "Cevap okunabilir başlık, liste ve teknik token bloklarına ayrılıyor.",
    progress: 96,
  },
] as const;

const KNOWLEDGE_CONTEXT_LIMIT_CHARS = 220_000;

type AskStageId = (typeof ASK_STAGES)[number]["id"] | "done" | "error";

type AskProgressState = {
  stage: AskStageId;
  value: number;
  detail?: string;
};

function wait(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
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

function cleanAnswerText(value: string) {
  return value
    .trim()
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+$/gm, "")
    .replace(/\n{3,}/g, "\n\n");
}

function stripOuterMarkdown(value: string) {
  return value
    .trim()
    .replace(/^#{1,6}\s+/, "")
    .replace(/^\*\*(.+)\*\*:?$/, "$1")
    .trim();
}

function renderInlineText(value: string) {
  const clean = value.replace(/\*\*([^*]+)\*\*/g, "$1");
  const tokenPattern = /(`[^`]+`|0x[0-9A-Fa-f]+|[A-Z][A-Z0-9_#]{2,}(?:\[[^\]]+\])?|[a-z][A-Za-z0-9]*\([^)]*\))/g;
  const pieces = clean.split(tokenPattern).filter((piece) => piece.length > 0);

  return pieces.map((piece, index) => {
    const withoutBackticks = piece.startsWith("`") && piece.endsWith("`") ? piece.slice(1, -1) : piece;
    const codeLike = withoutBackticks !== piece || tokenPattern.test(piece);
    tokenPattern.lastIndex = 0;
    if (codeLike) {
      return (
        <code key={`${piece}-${index}`} className="rounded border border-border bg-bg px-1 py-0.5 font-mono text-[11px] text-text">
          {withoutBackticks}
        </code>
      );
    }
    return <span key={`${piece}-${index}`}>{piece}</span>;
  });
}

type AnswerBlock =
  | { type: "heading"; text: string }
  | { type: "paragraph"; text: string }
  | { type: "bullet"; text: string }
  | { type: "number"; index: string; text: string }
  | { type: "kv"; keyText: string; valueText: string };

function answerBlocks(answer: string): AnswerBlock[] {
  return cleanAnswerText(answer)
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const heading = /^(?:#{1,6}\s+)?\*\*([^*]+)\*\*:?\s*$/.exec(line) ?? /^#{1,6}\s+(.+)$/.exec(line);
      if (heading) return { type: "heading", text: stripOuterMarkdown(heading[1]) };

      const numbered = /^(\d+)[.)]\s+(.+)$/.exec(line);
      if (numbered) return { type: "number", index: numbered[1], text: numbered[2].trim() };

      const bullet = /^[-*]\s+(.+)$/.exec(line);
      if (bullet) return { type: "bullet", text: bullet[1].trim() };

      const boldKv = /^\*\*([^*]+)\*\*:?\s+(.+)$/.exec(line);
      if (boldKv) return { type: "kv", keyText: stripOuterMarkdown(boldKv[1]), valueText: boldKv[2].trim() };

      const kv = /^([A-Za-zÇĞİÖŞÜçğıöşü0-9_/#()[\] .-]{2,28}):\s+(.+)$/.exec(line);
      if (kv && !/^https?:\/\//.test(line)) return { type: "kv", keyText: kv[1].trim(), valueText: kv[2].trim() };

      return { type: "paragraph", text: line };
    });
}

function FormattedAnswer({ answer }: { answer: string }) {
  const blocks = answerBlocks(answer);

  return (
    <div className="space-y-2.5 text-xs leading-relaxed text-muted">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          return (
            <div key={`${block.type}-${index}`} className="pt-2 first:pt-0">
              <div className="flex items-center gap-2 border-b border-border/70 pb-1">
                <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
                <h4 className="text-xs font-semibold text-text">{block.text}</h4>
              </div>
            </div>
          );
        }

        if (block.type === "kv") {
          return (
            <div key={`${block.type}-${index}`} className="grid gap-1 rounded border border-border/70 bg-bg/50 px-2 py-1.5 sm:grid-cols-[150px_minmax(0,1fr)]">
              <span className="font-mono text-[11px] font-semibold text-faint">{block.keyText}</span>
              <span>{renderInlineText(block.valueText)}</span>
            </div>
          );
        }

        if (block.type === "bullet") {
          return (
            <div key={`${block.type}-${index}`} className="flex gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-accent" aria-hidden />
              <p>{renderInlineText(block.text)}</p>
            </div>
          );
        }

        if (block.type === "number") {
          return (
            <div key={`${block.type}-${index}`} className="grid grid-cols-[22px_minmax(0,1fr)] gap-2">
              <span className="grid h-5 w-5 place-items-center rounded border border-border bg-bg font-mono text-[10px] text-faint">{block.index}</span>
              <p>{renderInlineText(block.text)}</p>
            </div>
          );
        }

        return <p key={`${block.type}-${index}`}>{renderInlineText(block.text)}</p>;
      })}
    </div>
  );
}

function AskProgress({ state }: { state: AskProgressState }) {
  const activeIndex = state.stage === "done"
    ? ASK_STAGES.length
    : state.stage === "error"
      ? ASK_STAGES.findIndex((stage) => stage.id === "llm")
      : ASK_STAGES.findIndex((stage) => stage.id === state.stage);
  const activeStage = ASK_STAGES.find((stage) => stage.id === state.stage);

  return (
    <div className="mt-3 rounded-md border border-border bg-inset/70 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {state.stage === "done" ? (
            <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden />
          ) : state.stage === "error" ? (
            <CircleDashed className="h-4 w-4 text-danger" aria-hidden />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
          )}
          <span className="text-xs font-semibold text-text">
            {state.stage === "done" ? "Cevap hazır" : state.stage === "error" ? "Akış hata ile durdu" : activeStage?.label}
          </span>
        </div>
        <span className="font-mono text-[10px] text-faint">{Math.round(state.value)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            state.stage === "error" ? "bg-danger" : state.stage === "done" ? "bg-ok" : "bg-accent",
          )}
          style={{ width: `${Math.max(4, Math.min(100, state.value))}%` }}
        />
      </div>
      <div className="mt-3 grid gap-1.5 sm:grid-cols-4">
        {ASK_STAGES.map((stage, index) => {
          const done = state.stage === "done" || index < activeIndex;
          const active = state.stage === stage.id;
          return (
            <div
              key={stage.id}
              className={cn(
                "rounded border px-2 py-1.5",
                done ? "border-ok/30 bg-ok/10" : active ? "border-accent/40 bg-accent/10" : "border-border bg-bg/50",
              )}
            >
              <div className="flex items-center gap-1.5">
                {done ? (
                  <CheckCircle2 className="h-3 w-3 text-ok" aria-hidden />
                ) : active ? (
                  <Loader2 className="h-3 w-3 animate-spin text-accent" aria-hidden />
                ) : (
                  <CircleDashed className="h-3 w-3 text-faint" aria-hidden />
                )}
                <span className={cn("text-[10px] font-semibold", done ? "text-ok" : active ? "text-accent" : "text-faint")}>{stage.label}</span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-faint">
        {state.detail ?? activeStage?.detail ?? "Akış tamamlandı."}
      </p>
    </div>
  );
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
  const [progress, setProgress] = useState<AskProgressState | null>(null);
  const registerCount = useMemo(() => packs.reduce((sum, pack) => sum + pack.registers.length, 0), [packs]);

  useEffect(() => {
    if (!loading) return;
    const timer = window.setInterval(() => {
      setProgress((current) => {
        if (!current || current.stage !== "llm") return current;
        return { ...current, value: Math.min(82, current.value + 2) };
      });
    }, 700);
    return () => window.clearInterval(timer);
  }, [loading]);

  async function submit() {
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setLoading(true);
    setError("");
    setAnswer("");
    setMeta(null);
    setProgress({ stage: "context", value: ASK_STAGES[0].progress, detail: ASK_STAGES[0].detail });
    try {
      const context = buildKnowledgeAskContext(packs, trimmed);
      setProgress({ stage: "llm", value: ASK_STAGES[1].progress, detail: ASK_STAGES[1].detail });
      const response = await api.knowledgeAsk({
        part: "GLOBAL_VERIFIED_KNOWLEDGE",
        question: trimmed,
        context,
        llm,
      });
      setProgress({ stage: "grounding", value: ASK_STAGES[2].progress, detail: ASK_STAGES[2].detail });
      await wait(120);
      setProgress({ stage: "format", value: ASK_STAGES[3].progress, detail: ASK_STAGES[3].detail });
      await wait(80);
      setAnswer(response.answer);
      setMeta({
        model: response.model,
        contextChars: response.context_chars,
        grounded: response.grounded ?? false,
      });
      setProgress({ stage: "done", value: 100, detail: "Cevap context kontrolünden geçti ve okunabilir formata dönüştürüldü." });
    } catch (err) {
      setError(askErrorMessage(err));
      setProgress({ stage: "error", value: 100, detail: "Hata mesajı backend veya LLM katmanından geldi; ayrıntı aşağıda gösteriliyor." });
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
          <p className="mt-1 max-w-3xl text-[11px] leading-relaxed text-warn">
            Bilgi notu: Knowledge Ask en fazla {KNOWLEDGE_CONTEXT_LIMIT_CHARS.toLocaleString("tr-TR")} karakter context gönderir. Qwen 256K için uygundur; daha küçük modellerde soru daha dar tutulmalıdır.
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

      {progress && <AskProgress state={progress} />}

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
          <FormattedAnswer answer={answer} />
        </div>
      )}
    </section>
  );
}
