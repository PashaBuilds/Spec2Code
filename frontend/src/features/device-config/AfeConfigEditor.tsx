import { useEffect, useMemo, useState } from "react";
import { FileCode2, Info } from "lucide-react";
import type { Device } from "@/lib/types";
import { Badge, Input, Label, Textarea } from "@/components/ui";

type Props = {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
};

/** Latte hex çıktısı: satır başına bir 32-bit sözcük (`0x11223344,`). Bayt gruplama YOK (TICS'ten farklı). */
function parseAfeWords(raw: string): number[] {
  const tokens = raw.match(/0[xX][0-9A-Fa-f]{1,8}/g) ?? [];
  return tokens.map((t) => Number.parseInt(t.slice(2), 16) >>> 0);
}

function wordHex(word: number): string {
  return `0x${(word >>> 0).toString(16).toUpperCase().padStart(8, "0")}`;
}

function textFromConfig(config: Record<string, unknown>): string {
  const raw = config.afe_config_words;
  if (typeof raw === "string") return raw;
  if (Array.isArray(raw)) {
    return raw
      .map((item) => (typeof item === "number" ? wordHex(item) : typeof item === "string" ? item : null))
      .filter((item): item is string => item !== null)
      .join("\n");
  }
  return "";
}

/**
 * AFE7900 (TI AFE79xx C API) kart verisi: Latte config sözcükleri + log seviyesi + TDD override.
 * Codegen bu sözcükleri `drivers/<mod>_config.c` dizisine gömer ve `afeDeviceBringupFromMem` ile uygular.
 */
export default function AfeConfigEditor({ device, config, onChange }: Props) {
  const [draft, setDraft] = useState(() => textFromConfig(config));
  useEffect(() => {
    setDraft(textFromConfig(config));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device.id]);

  const words = useMemo(() => parseAfeWords(draft), [draft]);
  const lineCount = draft.split(/\r?\n/).filter((l) => l.trim()).length;
  const logLevel = Number(config.log_level ?? 0);
  const tddOverride = config.tdd_override === undefined ? true : Boolean(config.tdd_override);

  const onTextChange = (value: string) => {
    setDraft(value);
    // Ham metin saklanır (satır sırası ve yorumlar korunur); codegen aynı regex ile ayrıştırır.
    onChange({ ...config, afe_config_words: value });
  };

  return (
    <div className="space-y-3 rounded-md border border-border bg-inset p-3" data-testid="afe-config-editor">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-xs font-medium text-muted">AFE config (Latte hex)</span>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-faint">
            Latte&apos;nin ürettiği hex dosyasını buraya yapıştır: satır başına bir 32-bit sözcük
            (<span className="font-mono">0x11223344,</span>). Sıra değiştirilmez; TI API
            <span className="font-mono"> afeDeviceBringupFromMem</span> ile sözcük sözcük uygulanır.
          </p>
        </div>
        <Badge tone={words.length ? "accent" : "warn"}>{words.length ? `${words.length} sözcük` : "boş"}</Badge>
      </div>

      <div className="space-y-1.5">
        <Label>Latte çıktısı</Label>
        <Textarea
          value={draft}
          onChange={(event) => onTextChange(event.target.value)}
          spellCheck={false}
          placeholder={"0x11223344,\n0x55667788,\n0x99AABBCC,"}
          className="min-h-40 text-xs"
        />
        {lineCount > 0 && words.length !== lineCount ? (
          <p className="flex gap-2 rounded border border-warn/30 bg-warn/10 px-2 py-1.5 text-[11px] leading-relaxed text-warn">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
            {lineCount} dolu satır var ama {words.length} sözcük ayrıştı; her satırda tek bir 0x... değeri olmalı.
          </p>
        ) : null}
        {words.length === 0 ? (
          <p className="text-[11px] text-warn">Sözcük yoksa üretim S2C-CODEGEN-AFE-001 hatasıyla durur.</p>
        ) : null}
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label>TI log seviyesi (0 ERROR … 4 DEBUG)</Label>
          <Input
            type="number"
            min={0}
            max={4}
            value={Number.isFinite(logLevel) ? logLevel : 0}
            onChange={(event) => onChange({ ...config, log_level: Math.max(0, Math.min(4, Number(event.target.value) || 0)) })}
          />
        </div>
        <label className="flex items-center gap-2 self-end pb-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={tddOverride}
            onChange={(event) => onChange({ ...config, tdd_override: event.target.checked })}
          />
          Bring-up sonrası TDD override (rx=15, fb=0, tx=15)
        </label>
      </div>
    </div>
  );
}
