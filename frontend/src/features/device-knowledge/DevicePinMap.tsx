import { useEffect, useMemo, useState, type KeyboardEvent } from "react";
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

type PositionedPin = KnowledgePin & {
  key: string;
  side: "left" | "right";
  rowIndex: number;
};

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

const TONE_LABEL: Record<KnowledgePinTone, string> = {
  analog: "Analog",
  bus: "Bus",
  control: "Control",
  power: "Power",
  ground: "Ground",
  memory: "Memory",
  nc: "N.C.",
};

function arrangePins(pins: KnowledgePin[]) {
  const midpoint = Math.ceil(pins.length / 2);
  const left: PositionedPin[] = [];
  const right: PositionedPin[] = [];

  pins.forEach((pin, index) => {
    const side = pin.side ?? (index < midpoint ? "left" : "right");
    const target = side === "left" ? left : right;
    target.push({
      ...pin,
      side,
      rowIndex: target.length,
      key: `${pin.number ?? "x"}-${pin.name}-${index}`,
    });
  });

  return { left, right, all: [...left, ...right] };
}

function pinY(index: number) {
  return PIN_TOP + index * PIN_STEP;
}

function PinRow({
  pin,
  selected,
  onSelect,
}: {
  pin: PositionedPin;
  selected: boolean;
  onSelect: () => void;
}) {
  const y = pinY(pin.rowIndex);
  const style = TONE_STYLE[pin.tone];
  const isLeft = pin.side === "left";
  const lineStart = isLeft ? CHIP_X - 42 : CHIP_X + CHIP_W + 42;
  const lineEnd = isLeft ? CHIP_X : CHIP_X + CHIP_W;
  const textX = isLeft ? 78 : 442;
  const numberX = isLeft ? CHIP_X - 8 : CHIP_X + CHIP_W + 8;
  const targetX = isLeft ? textX - 8 : textX - 88;
  const targetW = 96;

  function handleKeyDown(event: KeyboardEvent<SVGGElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect();
    }
  }

  return (
    <g
      role="button"
      tabIndex={0}
      aria-label={`${pin.name} pin detayını göster`}
      className="cursor-pointer outline-none"
      onClick={onSelect}
      onKeyDown={handleKeyDown}
    >
      <title>{pin.role}</title>
      <rect
        x={targetX}
        y={y - 11}
        width={targetW}
        height="22"
        rx="5"
        fill={selected ? style.fill : "transparent"}
        stroke={selected ? style.stroke : "transparent"}
      />
      <line
        x1={lineStart}
        y1={y}
        x2={lineEnd}
        y2={y}
        stroke={style.stroke}
        strokeWidth={selected ? 3 : 2}
        strokeLinecap="round"
      />
      <circle cx={lineStart} cy={y} r={selected ? 4 : 3} fill={style.stroke} />
      <text
        x={textX}
        y={y + 4}
        textAnchor={isLeft ? "start" : "end"}
        fill={selected ? style.text : "var(--text)"}
        className="font-mono text-[11px] font-bold"
      >
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

function SelectedPinPanel({
  part,
  pin,
  pinMap,
  config,
}: {
  part: string;
  pin: PositionedPin;
  pinMap: KnowledgePinMap;
  config?: Record<string, unknown>;
}) {
  const style = TONE_STYLE[pin.tone];
  const groups = pinMap.groups.filter((group) => group.pins.includes(pin.name));
  const ltcPair = part.toUpperCase() === "LTC2991"
    ? LTC2991_PAIRS.find((pair) => pair.pins.includes(pin.name))
    : undefined;
  const ltcMode = ltcPair ? ltc2991ModeMeta(normalizeLtc2991Config(config).pairs[ltcPair.key].mode) : undefined;
  const ltcStyle = ltcMode ? LTC_MODE_STYLE[ltcMode.tone] : undefined;

  return (
    <div className="rounded-md border border-border bg-elev p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: style.stroke }} />
            <h5 className="font-mono text-sm font-semibold text-text">{pin.name}</h5>
            {pin.number && <span className="rounded bg-inset px-1.5 py-0.5 font-mono text-[10px] text-faint">Pin {pin.number}</span>}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted">{pin.role}</p>
        </div>
        <span
          className="shrink-0 rounded border px-2 py-1 font-mono text-[10px]"
          style={{ borderColor: style.stroke, color: style.text, background: style.fill }}
        >
          {TONE_LABEL[pin.tone]}
        </span>
      </div>

      {ltcPair && ltcMode && ltcStyle && (
        <div className="mt-3 rounded-md border border-border bg-inset px-3 py-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="font-mono text-xs text-text">{ltcPair.label} pair</span>
            <span
              className="rounded border px-1.5 py-0.5 font-mono text-[10px]"
              style={{ borderColor: ltcStyle.stroke, color: ltcStyle.text, background: ltcStyle.fill }}
            >
              {ltcMode.label}
            </span>
          </div>
          <p className="mt-1 text-[11px] leading-relaxed text-faint">
            Bu seçim {ltcPair.reg} ve STATUS_HIGH init yazımlarını etkiler.
          </p>
        </div>
      )}

      {groups.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {groups.map((group) => {
            const groupStyle = TONE_STYLE[group.tone];
            return (
              <span
                key={group.label}
                className="rounded border px-1.5 py-0.5 text-[10px]"
                style={{ borderColor: groupStyle.stroke, color: groupStyle.text, background: groupStyle.fill }}
                title={group.description}
              >
                {group.label}
              </span>
            );
          })}
        </div>
      )}

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
  const { left, right, all } = useMemo(() => arrangePins(pinMap.pins), [pinMap.pins]);
  const firstPinKey = all[0]?.key ?? "";
  const [selectedKey, setSelectedKey] = useState(firstPinKey);

  useEffect(() => {
    setSelectedKey(firstPinKey);
  }, [firstPinKey, part]);

  const selectedPin = all.find((pin) => pin.key === selectedKey) ?? all[0];
  const rowCount = Math.max(left.length, right.length, 4);
  const chipH = (rowCount - 1) * PIN_STEP + 36;
  const viewH = PIN_TOP + (rowCount - 1) * PIN_STEP + 48;
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
            <p className="mt-1 max-w-2xl text-[10px] leading-relaxed text-faint">{pinMap.note}</p>
          </div>
          <div className="rounded border border-border bg-elev px-2 py-1 font-mono text-[10px] text-muted">
            {part}
          </div>
        </div>

        <div className="grid items-start gap-3 xl:grid-cols-[minmax(0,1fr)_280px]">
          <svg viewBox={`0 0 520 ${viewH}`} role="img" aria-label={`${part} pin haritası`} className="mx-auto h-auto w-full max-w-[560px]">
            <rect x={CHIP_X} y="36" width={CHIP_W} height={chipH} rx="12" fill="var(--elev)" stroke="var(--border)" />
            <path d={`M${CHIP_X + 44} 36a18 9 0 0 0 36 0`} fill="var(--bg)" stroke="var(--border)" />
            <text x={CHIP_X + CHIP_W / 2} y={36 + chipH / 2 - 6} textAnchor="middle" className="fill-text font-mono text-[14px] font-bold">
              {part}
            </text>
            <text x={CHIP_X + CHIP_W / 2} y={36 + chipH / 2 + 14} textAnchor="middle" className="fill-faint font-mono text-[10px]">
              {chipSubtitle}
            </text>

            {left.map((pin) => (
              <PinRow key={pin.key} pin={pin} selected={pin.key === selectedPin?.key} onSelect={() => setSelectedKey(pin.key)} />
            ))}
            {right.map((pin) => (
              <PinRow key={pin.key} pin={pin} selected={pin.key === selectedPin?.key} onSelect={() => setSelectedKey(pin.key)} />
            ))}
          </svg>

          {selectedPin && <SelectedPinPanel part={part} pin={selectedPin} pinMap={pinMap} config={config} />}
        </div>
      </div>
    </div>
  );
}
