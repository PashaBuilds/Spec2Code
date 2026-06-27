import {
  LTC2991_PAIRS,
  ltc2991ModeMeta,
  normalizeLtc2991Config,
  type Ltc2991ModeTone,
} from "@/features/device-config/ltc2991Model";
import type { KnowledgePin, KnowledgePinMap, KnowledgePinTone } from "./knowledge";

const PIN_TOP = 44;
const PIN_STEP = 25;
const CHIP_X = 196;
const CHIP_W = 112;

const TONE_STYLE: Record<KnowledgePinTone, { stroke: string; fill: string; text: string }> = {
  analog: { stroke: "var(--ok)", fill: "color-mix(in srgb, var(--ok) 14%, transparent)", text: "var(--ok)" },
  bus: { stroke: "var(--accent)", fill: "color-mix(in srgb, var(--accent) 13%, transparent)", text: "var(--accent)" },
  control: { stroke: "var(--warn)", fill: "color-mix(in srgb, var(--warn) 13%, transparent)", text: "var(--warn)" },
  power: { stroke: "var(--danger)", fill: "color-mix(in srgb, var(--danger) 12%, transparent)", text: "var(--danger)" },
  ground: { stroke: "var(--muted)", fill: "color-mix(in srgb, var(--muted) 12%, transparent)", text: "var(--muted)" },
  memory: { stroke: "var(--accent)", fill: "color-mix(in srgb, var(--accent) 18%, transparent)", text: "var(--accent)" },
  nc: { stroke: "var(--faint)", fill: "color-mix(in srgb, var(--faint) 10%, transparent)", text: "var(--faint)" },
};

const LTC_MODE_STYLE: Record<Ltc2991ModeTone, { stroke: string; fill: string; text: string }> = {
  off: { stroke: "var(--faint)", fill: "color-mix(in srgb, var(--faint) 10%, transparent)", text: "var(--faint)" },
  se: { stroke: "var(--accent)", fill: "color-mix(in srgb, var(--accent) 13%, transparent)", text: "var(--accent)" },
  diff: { stroke: "var(--ok)", fill: "color-mix(in srgb, var(--ok) 13%, transparent)", text: "var(--ok)" },
  current: { stroke: "var(--warn)", fill: "color-mix(in srgb, var(--warn) 13%, transparent)", text: "var(--warn)" },
  temp: { stroke: "var(--danger)", fill: "color-mix(in srgb, var(--danger) 13%, transparent)", text: "var(--danger)" },
  aux: { stroke: "var(--muted)", fill: "color-mix(in srgb, var(--muted) 12%, transparent)", text: "var(--muted)" },
};

function splitPins(pins: KnowledgePin[]) {
  const left = pins.filter((pin, index) => pin.side === "left" || (!pin.side && index < Math.ceil(pins.length / 2)));
  const right = pins.filter((pin, index) => pin.side === "right" || (!pin.side && index >= Math.ceil(pins.length / 2)));
  return { left, right };
}

function pinY(index: number) {
  return PIN_TOP + index * PIN_STEP;
}

function PinRow({
  pin,
  index,
  side,
}: {
  pin: KnowledgePin;
  index: number;
  side: "left" | "right";
}) {
  const y = pinY(index);
  const style = TONE_STYLE[pin.tone];
  const isLeft = side === "left";
  const lineStart = isLeft ? CHIP_X - 42 : CHIP_X + CHIP_W + 42;
  const lineEnd = isLeft ? CHIP_X : CHIP_X + CHIP_W;
  const textX = isLeft ? 78 : 442;
  const numberX = isLeft ? CHIP_X - 8 : CHIP_X + CHIP_W + 8;

  return (
    <g>
      <line x1={lineStart} y1={y} x2={lineEnd} y2={y} stroke={style.stroke} strokeWidth="2" strokeLinecap="round" />
      <circle cx={lineStart} cy={y} r="3" fill={style.stroke} />
      <text x={textX} y={y + 4} textAnchor={isLeft ? "start" : "end"} className="fill-text font-mono text-[11px] font-bold">
        {pin.name}
      </text>
      {pin.number && (
        <text x={numberX} y={y + 3} textAnchor={isLeft ? "end" : "start"} className="fill-faint font-mono text-[9px]">
          {pin.number}
        </text>
      )}
    </g>
  );
}

function Ltc2991PairSummary({ config }: { config?: Record<string, unknown> }) {
  const cfg = normalizeLtc2991Config(config);

  return (
    <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      {LTC2991_PAIRS.map((pair) => {
        const mode = ltc2991ModeMeta(cfg.pairs[pair.key].mode);
        const style = LTC_MODE_STYLE[mode.tone];

        return (
          <div key={pair.key} className="rounded-md border border-border bg-elev px-2.5 py-2">
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-[11px] text-text">{pair.label}</span>
              <span
                className="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                style={{ borderColor: style.stroke, color: style.text, background: style.fill }}
              >
                {mode.label}
              </span>
            </div>
            <p className="mt-1 text-[10px] leading-relaxed text-faint">
              Pin {pair.pins[0]} / {pair.pins[1]} aynı pair config değerini paylaşır.
            </p>
          </div>
        );
      })}
    </div>
  );
}

function PinDetailList({ pins }: { pins: KnowledgePin[] }) {
  return (
    <div className="grid gap-1.5 md:grid-cols-2 xl:grid-cols-3">
      {pins.map((pin, index) => {
        const style = TONE_STYLE[pin.tone];
        return (
          <div key={`${pin.name}-${pin.number ?? index}`} className="flex items-start gap-2 rounded border border-border bg-elev px-2 py-1.5">
            <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full" style={{ background: style.stroke }} />
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-1.5">
                {pin.number && <span className="font-mono text-[10px] text-faint">{pin.number}</span>}
                <span className="font-mono text-[11px] font-semibold text-text">{pin.name}</span>
              </div>
              <p className="text-[10px] leading-snug text-faint">{pin.role}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function DevicePinMap({
  part,
  pinMap,
  config,
}: {
  part: string;
  pinMap: KnowledgePinMap;
  config?: Record<string, unknown>;
}) {
  const { left, right } = splitPins(pinMap.pins);
  const rowCount = Math.max(left.length, right.length, 4);
  const chipH = (rowCount - 1) * PIN_STEP + 36;
  const viewH = PIN_TOP + (rowCount - 1) * PIN_STEP + 48;
  const isLtc2991 = part.toUpperCase() === "LTC2991";
  const chipSubtitle = pinMap.packageName.length > 18 ? "sinyal haritası" : pinMap.packageName;

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-border bg-inset p-3">
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div>
            <h4 className="text-xs font-semibold text-text">Pin / sinyal haritası</h4>
            <p className="mt-1 text-[11px] text-faint">
              {pinMap.packageName} - {pinMap.view}
            </p>
            <p className="mt-1 text-[10px] text-faint">{pinMap.verification}</p>
          </div>
          <div className="rounded border border-border bg-elev px-2 py-1 font-mono text-[10px] text-muted">
            {part}
          </div>
        </div>

        <svg viewBox={`0 0 520 ${viewH}`} role="img" aria-label={`${part} pin haritası`} className="mx-auto h-auto w-full max-w-[560px]">
          <rect x={CHIP_X} y="36" width={CHIP_W} height={chipH} rx="12" fill="var(--elev)" stroke="var(--border)" />
          <path d={`M${CHIP_X + 44} 36a18 9 0 0 0 36 0`} fill="var(--bg)" stroke="var(--border)" />
          <text x={CHIP_X + CHIP_W / 2} y={36 + chipH / 2 - 6} textAnchor="middle" className="fill-text font-mono text-[14px] font-bold">
            {part}
          </text>
          <text x={CHIP_X + CHIP_W / 2} y={36 + chipH / 2 + 14} textAnchor="middle" className="fill-faint font-mono text-[10px]">
            {chipSubtitle}
          </text>

          {left.map((pin, index) => (
            <PinRow key={`${pin.name}-${pin.number ?? index}`} pin={pin} index={index} side="left" />
          ))}
          {right.map((pin, index) => (
            <PinRow key={`${pin.name}-${pin.number ?? index}`} pin={pin} index={index} side="right" />
          ))}
        </svg>

        <p className="mt-2 text-[11px] leading-relaxed text-faint">{pinMap.note}</p>
      </div>

      {isLtc2991 && <Ltc2991PairSummary config={config} />}

      <PinDetailList pins={pinMap.pins} />

      <div className="grid gap-2 md:grid-cols-2">
        {pinMap.groups.map((group) => {
          const style = TONE_STYLE[group.tone];
          return (
            <div key={group.label} className="rounded-md border border-border bg-inset px-3 py-2">
              <div className="mb-1 flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-text">{group.label}</span>
                <span
                  className="rounded border px-1.5 py-0.5 font-mono text-[10px]"
                  style={{ borderColor: style.stroke, color: style.text, background: style.fill }}
                >
                  {group.pins.join(" / ")}
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-faint">{group.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
