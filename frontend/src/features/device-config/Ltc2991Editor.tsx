import { Badge, Button, Input, Label } from "@/components/ui";
import type { Device } from "@/lib/types";
import {
  LTC2991_MODES,
  LTC2991_PAIRS,
  defaultLtc2991Config,
  ltc2991ModeMeta,
  normalizeLtc2991Config,
  type Ltc2991Config,
  type Ltc2991PairConfig,
  type Ltc2991PairKey,
} from "./ltc2991Model";

export { defaultLtc2991Config };

export default function Ltc2991Editor({
  config,
  onChange,
}: {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  const cfg = normalizeLtc2991Config(config);
  const preview = initPreview(cfg);

  const updatePair = (key: Ltc2991PairKey, patch: Partial<Ltc2991PairConfig>) => {
    onChange({
      ...cfg,
      pairs: {
        ...cfg.pairs,
        [key]: { ...cfg.pairs[key], ...patch },
      },
    });
  };

  return (
    <div className="space-y-4" data-testid="ltc2991-config-editor">
      <div className="space-y-2">
        {LTC2991_PAIRS.map((pair) => {
          const item = cfg.pairs[pair.key];
          return (
            <div key={pair.key} className="rounded-md border border-border bg-inset p-2">
              <div className="flex items-center gap-2">
                <div className="w-14 shrink-0 font-mono text-xs text-text">{pair.label}</div>
                <div className="grid min-w-0 flex-1 grid-cols-5 gap-1">
                  {LTC2991_MODES.map((mode) => (
                    <Button
                      key={mode.value}
                      type="button"
                      variant={item.mode === mode.value ? "primary" : "outline"}
                      size="sm"
                      className="h-7 px-1 text-[11px]"
                      onClick={() => updatePair(pair.key, { mode: mode.value })}
                    >
                      {mode.label}
                    </Button>
                  ))}
                </div>
              </div>
              {item.mode === "current_shunt" && (
                <div className="mt-2 grid grid-cols-[1fr_96px] items-end gap-2">
                  <Label>Shunt</Label>
                  <Input
                    type="number"
                    min={0}
                    step={0.1}
                    value={item.shunt_milliohm ?? ""}
                    placeholder="mOhm"
                    onChange={(e) =>
                      updatePair(pair.key, {
                        shunt_milliohm: e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Toggle
          label="Internal temp"
          checked={cfg.internal_temperature}
          onChange={(checked) => onChange({ ...cfg, internal_temperature: checked })}
        />
        <Toggle
          label="VCC read"
          checked={cfg.vcc_read}
          onChange={(checked) => onChange({ ...cfg, vcc_read: checked })}
        />
      </div>

      <div className="rounded-md border border-border bg-inset p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-xs font-medium text-muted">Init sequence</span>
          <Badge tone="accent">{preview.length} writes</Badge>
        </div>
        <div className="space-y-1">
          {preview.map((row) => (
            <div key={row.reg} className="flex items-center justify-between gap-3 font-mono text-xs">
              <span className="truncate text-muted">{row.reg}</span>
              <span className="text-text">{row.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex h-9 cursor-pointer items-center justify-between rounded-md border border-border bg-inset px-3 text-xs text-muted">
      <span>{label}</span>
      <input
        type="checkbox"
        className="h-3.5 w-3.5 accent-accent"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
    </label>
  );
}

function initPreview(cfg: Ltc2991Config): Array<{ reg: string; value: string }> {
  let enable = cfg.internal_temperature || cfg.vcc_read ? 0x08 : 0x00;
  const controls = { CONTROL_V1V4: 0, CONTROL_V5V8: 0 };
  for (const pair of LTC2991_PAIRS) {
    const mode = ltc2991ModeMeta(cfg.pairs[pair.key].mode);
    if (mode.value !== "disabled") enable |= 1 << pair.enableBit;
    controls[pair.reg] |= mode.bits << pair.shift;
  }
  return [
    { reg: "STATUS_HIGH", value: hex(enable) },
    { reg: "CONTROL_V1V4", value: hex(controls.CONTROL_V1V4) },
    { reg: "CONTROL_V5V8", value: hex(controls.CONTROL_V5V8) },
  ];
}

function hex(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}
