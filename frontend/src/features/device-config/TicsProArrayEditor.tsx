import { useEffect, useMemo, useState } from "react";
import { ChevronDown, Check, Copy, FileCode2, Info } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Device, DeviceDescriptor } from "@/lib/types";
import { Badge, Button, Label, Textarea } from "@/components/ui";

type Props = {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
};

interface RegisterModel {
  frame_bits?: number;
  address_bits?: number;
  address_shift?: number;
  data_bits?: number;
  rw_bit?: number;
  write_value?: number;
  default_order?: "ascending" | "descending" | "exported";
  max_sck_hz?: number;
  rewrite_last_address?: number;
  rewrite_last_address_after_ms?: number;
}

export default function TicsProArrayEditor({ device, config, onChange }: Props) {
  const [descriptor, setDescriptor] = useState<DeviceDescriptor | null>(null);
  const [draft, setDraft] = useState(() => wordsFromConfig(config).join("\n"));

  useEffect(() => {
    let active = true;
    api.descriptor(device.part)
      .then((next) => {
        if (active) setDescriptor(next);
      })
      .catch(() => {
        if (active) setDescriptor(null);
      });
    return () => {
      active = false;
    };
  }, [device.part]);

  useEffect(() => {
    setDraft(wordsFromConfig(config).join("\n"));
  }, [device.id]);

  const model = descriptor?.transport.register_model;
  const supportsTics = descriptor?.transport.type === "spi" && model?.ticspro_words;
  const isTicsExport = ["LMK04832", "LMX2820", "LMX1204", "LMX1205"].includes(device.part.toUpperCase());
  const configKey = isTicsExport ? "ticspro_registers" : "register_words";
  const parsedWords = useMemo(() => parseWords(draft), [draft]);
  const decoded = useMemo(
    () => parsedWords.map((word) => decodeWord(word, model)),
    [model, parsedWords],
  );
  const first = decoded[0];
  const last = decoded[decoded.length - 1];
  // 15-bit adres + 8-bit veri kayıt modeli: codegen bu şekilleri "3 bayt/mesaj"
  // unsigned char dizisi olarak üretir (orchestrator/cmodel.py
  // _is_lmk_byte_register_model). LMX parçaları (7-bit adres + 16-bit veri)
  // bu şekli kullanmaz; önizleme onlarda gösterilmez.
  const isByteRegisterModel = model?.address_bits === 15 && model?.data_bits === 8;

  if (!supportsTics || !model) {
    return null;
  }

  const onTextChange = (value: string) => {
    setDraft(value);
    onChange({
      ...config,
      [configKey]: parseWords(value).map((word) => wordHex(word)),
    });
  };

  return (
    <div className="space-y-3 rounded-md border border-border bg-inset p-3" data-testid="ticspro-array-editor">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-xs font-medium text-muted">
              {isTicsExport ? "TICS Pro register array" : "SPI register init array"}
            </span>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-faint">
            {isTicsExport
              ? "TICS Pro export içindeki 24-bit word değerlerini buraya yapıştır. Sıra değiştirilmeden init sırasında SPI üzerinden MSB-first yazılır."
              : "Doğrulanmış 24-bit SPI register word değerlerini buraya yapıştır. Sıra değiştirilmeden init sırasında SPI üzerinden MSB-first yazılır."}
          </p>
        </div>
        <Badge tone={parsedWords.length ? "accent" : "warn"}>{parsedWords.length} word</Badge>
      </div>

      <div className="space-y-1.5">
        <Label>{isTicsExport ? "TICS Pro çıktısı" : "Register word listesi"}</Label>
        <Textarea
          value={draft}
          onChange={(event) => onTextChange(event.target.value)}
          spellCheck={false}
          placeholder={isTicsExport
            ? "const unsigned int lmx[] = {\n    0x4B0800,\n    0x00051C\n};"
            : "const unsigned int adar1000Init[] = {\n    0x000080,\n    0x002E7F\n};"}
          className="min-h-40 text-xs"
        />
      </div>

      <div className="grid gap-2 text-[11px] sm:grid-cols-2">
        <InfoPill label="Frame" value={`${model.frame_bits ?? 24} bit`} />
        <InfoPill label="SPI mode" value={`mode ${model.spi_mode ?? 0}`} />
        <InfoPill label="Sıra" value={orderLabel(model.default_order)} />
        <InfoPill label="Max SCK" value={formatHz(model.max_sck_hz)} />
        {first && <InfoPill label="İlk adres" value={addressHex(first.address, model)} />}
        {last && <InfoPill label="Son adres" value={addressHex(last.address, model)} />}
      </div>

      {model.rewrite_last_address_after_ms && model.rewrite_last_address != null ? (
        <p className="flex gap-2 rounded border border-warn/30 bg-warn/10 px-2 py-1.5 text-[11px] leading-relaxed text-muted">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" aria-hidden />
          Bu cihazda init array yazıldıktan sonra {model.rewrite_last_address_after_ms} ms beklenir ve{" "}
          {addressHex(model.rewrite_last_address, model)} adresindeki son word tekrar yazılır.
        </p>
      ) : null}

      {isByteRegisterModel ? (
        <CPreviewSection part={device.part} words={parsedWords} draft={draft} />
      ) : null}
    </div>
  );
}

function CPreviewSection({ part, words, draft }: { part: string; words: number[]; draft: string }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const hasContent = draft.trim().length > 0;
  const preview = useMemo(() => (words.length ? buildCConfigPreview(part, words) : null), [part, words]);

  const onCopy = async () => {
    if (!preview) return;
    try {
      await navigator.clipboard.writeText(preview.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="rounded-md border border-border bg-bg">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2 text-xs font-medium text-muted">
          <ChevronDown
            className={cn("h-3.5 w-3.5 shrink-0 text-faint transition-transform", open && "rotate-180")}
            aria-hidden
          />
          C önizleme (üretilen düzen)
        </span>
        {preview ? (
          <Badge tone="neutral">
            {preview.wordCount} mesaj · {preview.byteCount} bayt
          </Badge>
        ) : null}
      </button>

      {open ? (
        <div className="space-y-2 border-t border-border px-3 py-2.5">
          {preview ? (
            <>
              <div className="flex items-center justify-between gap-2">
                <span className="text-[11px] text-faint">üretilen dosya: drivers/{part.toLowerCase()}.c</span>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 gap-1.5 px-2 text-[11px]"
                  onClick={onCopy}
                >
                  {copied ? (
                    <>
                      <Check className="h-3.5 w-3.5" aria-hidden />
                      Kopyalandı
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" aria-hidden />
                      Kopyala
                    </>
                  )}
                </Button>
              </div>
              <pre className="max-h-64 overflow-auto rounded border border-border bg-inset p-2 font-mono text-[11px] leading-relaxed text-text">
                {preview.code}
              </pre>
            </>
          ) : (
            <p className="text-[11px] leading-relaxed text-warn">
              {hasContent
                ? "Önizleme için geçerli kayıt gerek."
                : "Önizleme için en az bir kayıt yapıştırın."}
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function buildCConfigPreview(part: string, words: number[]) {
  const moduleName = modulePascalName(part);
  const symbolName = `S_ucArr${moduleName}ConfigFile`;
  const countName = `${part.toUpperCase()}_CONFIG_FILE_BYTE_COUNT`;
  const byteCount = words.length * 3;

  const lines: string[] = [
    `#define ${countName} ${byteCount}U`,
    "",
    "/*",
    " * Format: 3 bytes per message.",
    " *    Byte 0: Address High (bit 7 = R/W, 0 = write)",
    " *    Byte 1: Address Low",
    " *    Byte 2: Data",
    " */",
    `static const unsigned char ${symbolName}[${countName}] =`,
    "{",
  ];
  for (const word of words) {
    const byte0 = (word >> 16) & 0xff;
    const byte1 = (word >> 8) & 0xff;
    const byte2 = word & 0xff;
    lines.push(`    ${hex2(byte0)}, ${hex2(byte1)}, ${hex2(byte2)},`);
  }
  lines.push("};", "");

  return { code: lines.join("\n"), wordCount: words.length, byteCount };
}

function modulePascalName(part: string): string {
  const alnum = part
    .split("")
    .filter((ch) => /[a-zA-Z0-9]/.test(ch))
    .join("")
    .toLowerCase();
  return alnum.slice(0, 1).toUpperCase() + alnum.slice(1);
}

function hex2(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}

function InfoPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2 rounded border border-border bg-bg px-2 py-1.5">
      <span className="text-faint">{label}</span>
      <span className="truncate font-mono text-muted">{value}</span>
    </div>
  );
}

function wordsFromConfig(config: Record<string, unknown>): string[] {
  const raw = Array.isArray(config.ticspro_registers) ? config.ticspro_registers : config.register_words;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => {
      if (typeof item === "number") return wordHex(item);
      if (typeof item === "string") return wordHex(parseNumber(item));
      return null;
    })
    .filter((item): item is string => item !== null);
}

function parseWords(raw: string): number[] {
  const hexTokens = raw.match(/0[xX][0-9A-Fa-f]+/g);
  if (hexTokens?.length) return hexTokens.map(parseNumber);
  const decimalTokens = raw.match(/(?<![A-Za-z0-9_])-?\d+(?![A-Za-z0-9_])/g);
  return decimalTokens?.map(parseNumber) ?? [];
}

function parseNumber(raw: string | number): number {
  if (typeof raw === "number") return raw;
  const normalized = raw.trim();
  if (!normalized) return 0;
  return Number(normalized.startsWith("0x") || normalized.startsWith("0X") ? normalized : Number(normalized));
}

function decodeWord(word: number, model?: RegisterModel) {
  const addressBits = model?.address_bits ?? 7;
  const addressShift = model?.address_shift ?? model?.data_bits ?? 16;
  const dataBits = model?.data_bits ?? 16;
  const addressMask = (1 << addressBits) - 1;
  const dataMask = dataBits >= 31 ? 0x7fffffff : (1 << dataBits) - 1;
  return {
    word,
    address: (word >> addressShift) & addressMask,
    value: word & dataMask,
  };
}

function wordHex(word: number): string {
  const safe = Number.isFinite(word) ? word : 0;
  return `0x${(safe & 0xffffff).toString(16).toUpperCase().padStart(6, "0")}`;
}

function addressHex(address: number, model?: RegisterModel): string {
  const digits = Math.max(2, Math.ceil((model?.address_bits ?? 7) / 4));
  return `0x${address.toString(16).toUpperCase().padStart(digits, "0")}`;
}

function orderLabel(order?: RegisterModel["default_order"]): string {
  if (order === "ascending") return "artan";
  if (order === "descending") return "azalan";
  return "export sırası";
}

function formatHz(value?: number): string {
  if (!value) return "-";
  if (value >= 1_000_000) return `${value / 1_000_000} MHz`;
  if (value >= 1_000) return `${value / 1_000} kHz`;
  return `${value} Hz`;
}
