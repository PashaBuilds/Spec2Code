import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Device, DeviceDescriptor } from "@/lib/types";
import { Input, Label } from "@/components/ui";

type Props = {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
};

type BoardDataKey = {
  key: string;
  ops: string[];
  unit: string;
};

/** İnsan-okur etiket: descriptor anahtarı → başlık (bilinenler için Türkçe). */
const KEY_LABELS: Record<string, string> = {
  sense_resistor_mohms: "Şönt (sense) direnci, mΩ",
};

/**
 * Kart verisi gerektiren dönüşüm anahtarları: descriptor op'larının
 * `convert.scale_den_config` alanından türer (ör. LTC2945 `current_read` →
 * `sense_resistor_mohms`). Codegen bu anahtarı `device.config` içinde arar;
 * op açıkça istenmişse ve anahtar yoksa üretim HATA verir.
 */
function boardDataKeys(descriptor: DeviceDescriptor | null): BoardDataKey[] {
  const out = new Map<string, BoardDataKey>();
  for (const op of descriptor?.operations ?? []) {
    const convert = (op.convert ?? {}) as Record<string, unknown>;
    const key = convert.scale_den_config;
    if (typeof key !== "string" || !key) continue;
    const entry = out.get(key) ?? { key, ops: [], unit: String(convert.unit ?? "") };
    entry.ops.push(op.name);
    out.set(key, entry);
  }
  return [...out.values()];
}

export default function GenericConfigEditor({ device, config, onChange }: Props) {
  const [descriptor, setDescriptor] = useState<DeviceDescriptor | null>(null);

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

  const keys = useMemo(() => boardDataKeys(descriptor), [descriptor]);
  const requested = new Set(device.operations_requested ?? []);

  return (
    <div className="rounded-md border border-border bg-inset px-3 py-3">
      <div className="font-mono text-xs text-muted">{device.part}</div>
      {keys.length === 0 ? (
        <div className="mt-1 text-xs text-faint">descriptor defaults</div>
      ) : (
        <div className="mt-2 space-y-2">
          <div className="text-xs text-faint">
            Kart verisi: bu değerler descriptor'da değil kartta belirlenir; ilgili op istenmişse
            üretim için zorunludur.
          </div>
          {keys.map((item) => {
            const raw = config[item.key];
            const value = typeof raw === "number" ? raw : Number(raw ?? "");
            const needed = item.ops.some((op) => requested.has(op));
            const missing = needed && !(value > 0);
            return (
              <div key={item.key} className="space-y-1">
                <Label className="text-xs">
                  {KEY_LABELS[item.key] ?? item.key}
                  <span className="ml-1 font-mono text-[11px] text-faint">
                    ({item.ops.join(", ")}{item.unit ? ` → ${item.unit}` : ""})
                  </span>
                </Label>
                <Input
                  type="number"
                  min={1}
                  step={1}
                  value={Number.isFinite(value) && value > 0 ? value : ""}
                  placeholder={needed ? "zorunlu (pozitif tam sayı)" : "isteğe bağlı"}
                  aria-invalid={missing || undefined}
                  className={missing ? "border-danger" : undefined}
                  onChange={(event) => {
                    const next = { ...config };
                    const parsed = Number.parseInt(event.target.value, 10);
                    if (Number.isFinite(parsed) && parsed > 0) next[item.key] = parsed;
                    else delete next[item.key];
                    onChange(next);
                  }}
                />
                {missing && (
                  <div className="text-[11px] text-danger">
                    {item.ops.filter((op) => requested.has(op)).join(", ")} istendi; bu alan boşken
                    Generate hata verir.
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
