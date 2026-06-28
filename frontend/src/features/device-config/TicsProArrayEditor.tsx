import { useEffect, useMemo, useState } from "react";
import { FileCode2, Info } from "lucide-react";
import { api } from "@/lib/api";
import type { Device, DeviceDescriptor } from "@/lib/types";
import { Badge, Label, Textarea } from "@/components/ui";

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
  const parsedWords = useMemo(() => parseWords(draft), [draft]);
  const decoded = useMemo(
    () => parsedWords.map((word) => decodeWord(word, model)),
    [model, parsedWords],
  );
  const first = decoded[0];
  const last = decoded[decoded.length - 1];

  if (!supportsTics || !model) {
    return null;
  }

  const onTextChange = (value: string) => {
    setDraft(value);
    onChange({
      ...config,
      ticspro_registers: parseWords(value).map((word) => wordHex(word)),
    });
  };

  return (
    <div className="space-y-3 rounded-md border border-border bg-inset p-3" data-testid="ticspro-array-editor">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-xs font-medium text-muted">TICS Pro register array</span>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-faint">
            TICS Pro export içindeki 24-bit word değerlerini buraya yapıştır. Sıra değiştirilmeden init sırasında
            SPI üzerinden MSB-first yazılır.
          </p>
        </div>
        <Badge tone={parsedWords.length ? "accent" : "warn"}>{parsedWords.length} word</Badge>
      </div>

      <div className="space-y-1.5">
        <Label>TICS Pro çıktısı</Label>
        <Textarea
          value={draft}
          onChange={(event) => onTextChange(event.target.value)}
          spellCheck={false}
          placeholder={"const unsigned int lmx[] = {\n    0x4B0800,\n    0x00051C\n};"}
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
    </div>
  );
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
  const raw = config.ticspro_registers;
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
