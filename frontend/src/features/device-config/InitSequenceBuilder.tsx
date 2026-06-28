import { useEffect, useMemo, useState } from "react";
import { Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Device, DeviceDescriptor, DescriptorField, InitSequenceWrite } from "@/lib/types";
import { Badge, Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";

type Props = {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
};

export default function InitSequenceBuilder({ device, config, onChange }: Props) {
  const [descriptor, setDescriptor] = useState<DeviceDescriptor | null>(null);
  const [selectedReg, setSelectedReg] = useState("");
  const [value, setValue] = useState(0);

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

  const writableRegisters = useMemo(
    () =>
      (descriptor?.registers ?? []).filter((reg) => {
        const access = (reg.access ?? "rw").toLowerCase();
        return descriptor?.transport.type === "i2c" && access.includes("w") && !access.includes("*") && (reg.width ?? 8) <= 8;
      }),
    [descriptor],
  );

  const sequence = normalizeSequence(config.init_sequence);
  const selected = writableRegisters.find((reg) => reg.name === selectedReg) ?? writableRegisters[0];
  const currentWrite = selected ? sequence.find((item) => item.reg === selected.name) : undefined;

  useEffect(() => {
    if (!selectedReg && writableRegisters[0]) {
      setSelectedReg(writableRegisters[0].name);
    }
  }, [selectedReg, writableRegisters]);

  useEffect(() => {
    if (!selected) return;
    setValue(currentWrite?.value ?? Number(selected.reset ?? 0));
  }, [currentWrite?.value, selected?.name, selected?.reset]);

  if (!descriptor || writableRegisters.length === 0) {
    return null;
  }

  const maxValue = maskForWidth(selected.width ?? 8);

  const addOrUpdate = () => {
    if (!selected) return;
    const nextWrite: InitSequenceWrite = {
      reg: selected.name,
      value: value & maxValue,
      note: "UI init builder",
    };
    const without = sequence.filter((item) => item.reg !== selected.name);
    onChange({ ...config, init_sequence: [...without, nextWrite] });
  };

  const remove = (reg: string) => {
    const next = sequence.filter((item) => item.reg !== reg);
    onChange({ ...config, init_sequence: next });
  };

  return (
    <div className="space-y-3 rounded-md border border-border bg-inset p-3" data-testid="init-sequence-builder">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium text-muted">Init Sequence Builder</span>
        <Badge tone={sequence.length ? "accent" : "neutral"}>{sequence.length} write</Badge>
      </div>

      <div className="grid grid-cols-[1fr_88px] gap-2">
        <div className="space-y-1.5">
          <Label>Register</Label>
          <Select
            value={selected?.name ?? ""}
            onValueChange={(next) => setSelectedReg(next)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {writableRegisters.map((reg) => (
                <SelectItem key={reg.name} value={reg.name}>
                  {reg.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Value</Label>
          <Input
            value={hex(value & maxValue)}
            onChange={(event) => setValue(parseHex(event.target.value, value) & maxValue)}
          />
        </div>
      </div>

      {selected.fields?.length ? (
        <div className="grid grid-cols-2 gap-2">
          {selected.fields.map((field) => (
            <BitFieldControl
              key={field.name}
              field={field}
              value={value}
              onChange={(next) => setValue(next & maxValue)}
            />
          ))}
        </div>
      ) : null}

      <Button type="button" size="sm" variant="outline" className="w-full" onClick={addOrUpdate}>
        Init write ekle
      </Button>

      {sequence.length > 0 ? (
        <div className="space-y-1 border-t border-border pt-2">
          {sequence.map((item) => (
            <div key={item.reg} className="flex items-center gap-2 rounded bg-bg px-2 py-1.5">
              <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted">{item.reg}</span>
              <span className="font-mono text-xs text-text">{hex(item.value)}</span>
              <button
                type="button"
                className="grid h-6 w-6 place-items-center rounded text-faint hover:bg-danger/15 hover:text-danger"
                onClick={() => remove(item.reg)}
                aria-label={`${item.reg} init write sil`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function BitFieldControl({
  field,
  value,
  onChange,
}: {
  field: DescriptorField;
  value: number;
  onChange: (value: number) => void;
}) {
  const range = bitRange(field.bits);
  const width = range.high - range.low + 1;
  const current = (value >> range.low) & maskForWidth(width);

  if (width === 1) {
    return (
      <label className="flex h-8 cursor-pointer items-center justify-between rounded border border-border bg-bg px-2 text-xs text-muted">
        <span className="min-w-0 truncate font-mono">{field.name}</span>
        <input
          type="checkbox"
          className="h-3.5 w-3.5 accent-accent"
          checked={current === 1}
          onChange={(event) => onChange(setField(value, range.low, width, event.target.checked ? 1 : 0))}
        />
      </label>
    );
  }

  return (
    <div className="space-y-1 rounded border border-border bg-bg p-2">
      <Label className="block truncate font-mono">{field.name}</Label>
      <Input
        type="number"
        min={0}
        max={maskForWidth(width)}
        value={current}
        onChange={(event) => onChange(setField(value, range.low, width, Number(event.target.value)))}
        className="h-7 px-2 text-xs"
      />
    </div>
  );
}

function normalizeSequence(raw: unknown): InitSequenceWrite[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item): InitSequenceWrite | null => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      if (typeof row.reg !== "string") return null;
      const value = typeof row.value === "number" ? row.value : parseHex(String(row.value ?? "0"), 0);
      const write: InitSequenceWrite = {
        reg: row.reg,
        value,
      };
      if (typeof row.note === "string") write.note = row.note;
      return write;
    })
    .filter((item): item is InitSequenceWrite => item !== null);
}

function bitRange(bits: string): { high: number; low: number } {
  const parts = bits.split(":").map((part) => Number(part));
  if (parts.length === 1) return { high: parts[0], low: parts[0] };
  return { high: Math.max(parts[0], parts[1]), low: Math.min(parts[0], parts[1]) };
}

function maskForWidth(width: number): number {
  return width >= 31 ? 0x7fffffff : (1 << width) - 1;
}

function setField(value: number, low: number, width: number, next: number): number {
  const mask = maskForWidth(width) << low;
  return (value & ~mask) | ((next << low) & mask);
}

function parseHex(raw: string, fallback: number): number {
  const normalized = raw.trim();
  if (!normalized) return 0;
  const parsed = Number(normalized.startsWith("0x") || normalized.startsWith("0X") ? normalized : `0x${normalized}`);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function hex(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}
