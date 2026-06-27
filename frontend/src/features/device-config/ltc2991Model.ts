export type Ltc2991PairKey = "v1_v2" | "v3_v4" | "v5_v6" | "v7_v8";
export type Ltc2991PairMode =
  | "disabled"
  | "single_ended_voltage"
  | "differential_voltage"
  | "current_shunt"
  | "remote_temperature";

export type Ltc2991PairConfig = {
  mode: Ltc2991PairMode;
  shunt_milliohm: number | null;
};

export type Ltc2991Config = {
  pairs: Record<Ltc2991PairKey, Ltc2991PairConfig>;
  internal_temperature: boolean;
  vcc_read: boolean;
};

export type Ltc2991ModeTone = "off" | "se" | "diff" | "current" | "temp" | "aux";

export const LTC2991_PAIRS: Array<{
  key: Ltc2991PairKey;
  label: string;
  pins: [string, string];
  enableBit: number;
  reg: "CONTROL_V1V4" | "CONTROL_V5V8";
  shift: number;
}> = [
  { key: "v1_v2", label: "V1/V2", pins: ["V1", "V2"], enableBit: 4, reg: "CONTROL_V1V4", shift: 0 },
  { key: "v3_v4", label: "V3/V4", pins: ["V3", "V4"], enableBit: 5, reg: "CONTROL_V1V4", shift: 4 },
  { key: "v5_v6", label: "V5/V6", pins: ["V5", "V6"], enableBit: 6, reg: "CONTROL_V5V8", shift: 0 },
  { key: "v7_v8", label: "V7/V8", pins: ["V7", "V8"], enableBit: 7, reg: "CONTROL_V5V8", shift: 4 },
];

export const LTC2991_MODES: Array<{ value: Ltc2991PairMode; label: string; shortLabel: string; bits: number; tone: Ltc2991ModeTone }> = [
  { value: "disabled", label: "Off", shortLabel: "Off", bits: 0x0, tone: "off" },
  { value: "single_ended_voltage", label: "SE V", shortLabel: "SE", bits: 0x0, tone: "se" },
  { value: "differential_voltage", label: "Diff V", shortLabel: "Diff", bits: 0x1, tone: "diff" },
  { value: "current_shunt", label: "Current", shortLabel: "Cur", bits: 0x1, tone: "current" },
  { value: "remote_temperature", label: "Temp", shortLabel: "Temp", bits: 0x2, tone: "temp" },
];

export function defaultLtc2991Config(): Record<string, unknown> {
  return {
    pairs: {
      v1_v2: { mode: "single_ended_voltage", shunt_milliohm: null },
      v3_v4: { mode: "single_ended_voltage", shunt_milliohm: null },
      v5_v6: { mode: "single_ended_voltage", shunt_milliohm: null },
      v7_v8: { mode: "single_ended_voltage", shunt_milliohm: null },
    },
    internal_temperature: true,
    vcc_read: false,
  };
}

export function normalizeLtc2991Config(raw: Record<string, unknown> | undefined): Ltc2991Config {
  const base = defaultLtc2991Config() as Ltc2991Config;
  const source = raw ?? {};
  const pairs = isRecord(source.pairs) ? source.pairs : {};
  for (const pair of LTC2991_PAIRS) {
    const maybePair = pairs[pair.key];
    const item: Record<string, unknown> = isRecord(maybePair) ? maybePair : {};
    const mode = typeof item.mode === "string" && isLtc2991Mode(item.mode)
      ? item.mode
      : base.pairs[pair.key].mode;
    const shunt = typeof item.shunt_milliohm === "number"
      ? item.shunt_milliohm
      : null;
    base.pairs[pair.key] = { mode, shunt_milliohm: shunt };
  }
  base.internal_temperature =
    typeof source.internal_temperature === "boolean" ? source.internal_temperature : base.internal_temperature;
  base.vcc_read = typeof source.vcc_read === "boolean" ? source.vcc_read : base.vcc_read;
  return base;
}

export function ltc2991ModeMeta(mode: Ltc2991PairMode) {
  return LTC2991_MODES.find((item) => item.value === mode) ?? LTC2991_MODES[1];
}

export function ltc2991NodeSummary(raw: Record<string, unknown> | undefined) {
  const cfg = normalizeLtc2991Config(raw);
  return [
    ...LTC2991_PAIRS.map((pair) => {
      const meta = ltc2991ModeMeta(cfg.pairs[pair.key].mode);
      return {
        key: pair.key,
        label: `${pair.label} ${meta.shortLabel}`,
        tone: meta.tone,
      };
    }),
    ...(cfg.internal_temperature ? [{ key: "internal_temperature", label: "Int Temp", tone: "aux" as const }] : []),
    ...(cfg.vcc_read ? [{ key: "vcc_read", label: "VCC", tone: "aux" as const }] : []),
  ];
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isLtc2991Mode(value: string): value is Ltc2991PairMode {
  return LTC2991_MODES.some((mode) => mode.value === value);
}

