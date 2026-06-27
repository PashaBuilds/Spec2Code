import {
  LTC2991_PAIRS,
  ltc2991ModeMeta,
  normalizeLtc2991Config,
  type Ltc2991ModeTone,
  type Ltc2991PairKey,
} from "@/features/device-config/ltc2991Model";

const PIN_LEFT = ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8"];
const PIN_RIGHT = ["VCC", "ADR2", "ADR1", "ADR0", "PWM", "SCL", "SDA", "GND"];
const PIN_Y = [60, 88, 116, 144, 172, 200, 228, 256];

const TONE_STYLE: Record<Ltc2991ModeTone, { stroke: string; fill: string; text: string }> = {
  off: { stroke: "var(--faint)", fill: "color-mix(in srgb, var(--faint) 10%, transparent)", text: "var(--faint)" },
  se: { stroke: "var(--accent)", fill: "color-mix(in srgb, var(--accent) 13%, transparent)", text: "var(--accent)" },
  diff: { stroke: "var(--ok)", fill: "color-mix(in srgb, var(--ok) 13%, transparent)", text: "var(--ok)" },
  current: { stroke: "var(--warn)", fill: "color-mix(in srgb, var(--warn) 13%, transparent)", text: "var(--warn)" },
  temp: { stroke: "var(--danger)", fill: "color-mix(in srgb, var(--danger) 13%, transparent)", text: "var(--danger)" },
  aux: { stroke: "var(--muted)", fill: "color-mix(in srgb, var(--muted) 12%, transparent)", text: "var(--muted)" },
};

const PAIR_ROW: Record<Ltc2991PairKey, { y1: number; y2: number }> = {
  v1_v2: { y1: 60, y2: 88 },
  v3_v4: { y1: 116, y2: 144 },
  v5_v6: { y1: 172, y2: 200 },
  v7_v8: { y1: 228, y2: 256 },
};

function PinRow({
  side,
  pin,
  index,
}: {
  side: "left" | "right";
  pin: string;
  index: number;
}) {
  const y = PIN_Y[index];
  const isLeft = side === "left";
  const x1 = isLeft ? 116 : 276;
  const x2 = isLeft ? 146 : 246;
  const textX = isLeft ? 28 : 314;
  const anchor = isLeft ? "start" : "end";
  const pinNo = isLeft ? index + 1 : 16 - index;

  return (
    <g>
      <line x1={x1} y1={y} x2={x2} y2={y} stroke="var(--border)" strokeWidth="2" />
      <circle cx={x1} cy={y} r="3" fill="var(--accent)" />
      <text x={textX} y={y + 4} textAnchor={anchor} className="fill-text font-mono text-[11px]">
        {pin}
      </text>
      <text
        x={isLeft ? 104 : 288}
        y={y + 3}
        textAnchor={isLeft ? "end" : "start"}
        className="fill-faint font-mono text-[9px]"
      >
        {pinNo}
      </text>
    </g>
  );
}

export default function Ltc2991PinMap({ config }: { config?: Record<string, unknown> }) {
  const cfg = normalizeLtc2991Config(config);

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-inset p-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <div>
            <h4 className="text-xs font-semibold text-text">Pinout & measurement map</h4>
            <p className="mt-1 text-[11px] text-faint">MSOP-16 top view, pair colors follow current config.</p>
          </div>
          <div className="rounded border border-border bg-elev px-2 py-1 font-mono text-[10px] text-muted">
            V1..V8
          </div>
        </div>

        <svg
          viewBox="0 0 420 310"
          role="img"
          aria-label="LTC2991 MSOP-16 pin and measurement pair map"
          className="h-auto w-full"
        >
          <rect x="146" y="38" width="100" height="236" rx="12" fill="var(--elev)" stroke="var(--border)" />
          <path d="M184 38a12 8 0 0 0 24 0" fill="var(--bg)" stroke="var(--border)" />
          <text x="196" y="138" textAnchor="middle" className="fill-text font-mono text-[14px] font-bold">
            LTC2991
          </text>
          <text x="196" y="158" textAnchor="middle" className="fill-faint font-mono text-[10px]">
            I2C monitor
          </text>

          {PIN_LEFT.map((pin, index) => (
            <PinRow key={pin} side="left" pin={pin} index={index} />
          ))}
          {PIN_RIGHT.map((pin, index) => (
            <PinRow key={pin} side="right" pin={pin} index={index} />
          ))}

          {LTC2991_PAIRS.map((pair) => {
            const mode = ltc2991ModeMeta(cfg.pairs[pair.key].mode);
            const style = TONE_STYLE[mode.tone];
            const row = PAIR_ROW[pair.key];
            const centerY = (row.y1 + row.y2) / 2;
            return (
              <g key={pair.key}>
                <path
                  d={`M76 ${row.y1 - 10} h-14 v${row.y2 - row.y1 + 20} h14`}
                  fill="none"
                  stroke={style.stroke}
                  strokeWidth="2"
                  strokeLinecap="round"
                />
                <rect x="38" y={centerY - 10} width="62" height="20" rx="4" fill={style.fill} stroke={style.stroke} />
                <text x="69" y={centerY + 4} textAnchor="middle" fill={style.text} className="font-mono text-[9px] font-bold">
                  {pair.label} {mode.shortLabel}
                </text>
              </g>
            );
          })}

          <rect x="300" y="92" width="84" height="88" rx="8" fill="color-mix(in srgb, var(--accent) 8%, transparent)" stroke="var(--border)" />
          <text x="342" y="114" textAnchor="middle" className="fill-text font-mono text-[10px] font-bold">
            Digital
          </text>
          <text x="342" y="134" textAnchor="middle" className="fill-muted font-mono text-[10px]">
            SDA / SCL
          </text>
          <text x="342" y="152" textAnchor="middle" className="fill-muted font-mono text-[10px]">
            ADR0..2
          </text>
          <text x="342" y="170" textAnchor="middle" className="fill-faint font-mono text-[10px]">
            PWM
          </text>

          <rect x="300" y="198" width="84" height="44" rx="8" fill="color-mix(in srgb, var(--muted) 10%, transparent)" stroke="var(--border)" />
          <text x="342" y="218" textAnchor="middle" className="fill-text font-mono text-[10px] font-bold">
            Supply
          </text>
          <text x="342" y="236" textAnchor="middle" className="fill-muted font-mono text-[10px]">
            VCC / GND
          </text>
        </svg>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {LTC2991_PAIRS.map((pair) => {
          const cfgPair = cfg.pairs[pair.key];
          const mode = ltc2991ModeMeta(cfgPair.mode);
          const style = TONE_STYLE[mode.tone];
          return (
            <div key={pair.key} className="rounded-md border border-border bg-inset px-2 py-2">
              <div className="flex items-center justify-between gap-2">
                <span className="font-mono text-xs text-text">{pair.label}</span>
                <span
                  className="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                  style={{ borderColor: style.stroke, color: style.text, background: style.fill }}
                >
                  {mode.label}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-faint">
                Pins {pair.pins[0]} and {pair.pins[1]} share one pair-level measurement mode.
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

