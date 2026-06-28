import { Activity } from "lucide-react";
import { Badge } from "@/components/ui";
import { cn } from "@/lib/utils";
import type { KnowledgeRegisterTransfer } from "./knowledge";

type Protocol = "i2c" | "spi";
type ByteRole = "tx" | "rx";
type BitTone = "normal" | "ack" | "idle" | "master" | "slave";

interface ByteFrame {
  label: string;
  bits: string[];
  role: ByteRole;
}

const I2C_PARTS = new Set(["LTC2991", "TCA9548A", "AD7414", "DS1682", "LTC2945"]);
const SPI_PARTS = new Set(["MT25Q128", "MT25QU02G", "LMK04832", "LMX2820", "LMX1204"]);

function protocolForPart(part: string): Protocol | null {
  const normalized = part.toUpperCase();
  if (I2C_PARTS.has(normalized)) return "i2c";
  if (SPI_PARTS.has(normalized)) return "spi";
  return null;
}

function isReadTransfer(transfer: KnowledgeRegisterTransfer) {
  return transfer.access.toUpperCase().includes("READ") && !transfer.rxBytes.toLowerCase().startsWith("0 byte");
}

function isWriteTransfer(transfer: KnowledgeRegisterTransfer) {
  return transfer.access.toUpperCase().includes("WRITE");
}

function byteCount(value: string) {
  const lower = value.toLowerCase();
  if (lower.startsWith("0 byte")) return 0;
  const repeated = /(\d+)\s*x\s*(\d+)\s*byte/.exec(lower);
  if (repeated) return Number(repeated[1]) * Number(repeated[2]);
  const direct = /(\d+)\s*byte/.exec(lower);
  return direct ? Number(direct[1]) : undefined;
}

function symbolicBits(prefix = "b") {
  return Array.from({ length: 8 }, (_, index) => `${prefix}${7 - index}`);
}

function hexBits(value: number) {
  return Array.from({ length: 8 }, (_, index) => ((value >> (7 - index)) & 1 ? "1" : "0"));
}

function firstHexByte(value: string) {
  const match = /0x([0-9A-Fa-f]{1,2})(?:U|u)?\b/.exec(value);
  return match ? Number.parseInt(match[1], 16) : null;
}

function descendingBits(prefix: string, high: number, low: number) {
  return Array.from({ length: high - low + 1 }, (_, index) => `${prefix}${high - index}`);
}

function ticsFrames(label: string, role: ByteRole): ByteFrame[] | null {
  if (!/R\/W=0/.test(label)) return null;

  if (/A14:A0/.test(label)) {
    return [
      { label: "W=0 + A14:A8", bits: ["0", ...descendingBits("A", 14, 8)], role },
      { label: "A7:A0", bits: descendingBits("A", 7, 0), role },
      { label: "D7:D0", bits: descendingBits("D", 7, 0), role },
    ];
  }

  if (/A6:A0/.test(label)) {
    return [
      { label: "W=0 + A6:A0", bits: ["0", ...descendingBits("A", 6, 0)], role },
      { label: "D15:D8", bits: descendingBits("D", 15, 8), role },
      { label: "D7:D0", bits: descendingBits("D", 7, 0), role },
    ];
  }

  return null;
}

function addressFrames(label: string, role: ByteRole): ByteFrame[] | null {
  const match = /A(\d+):A0/.exec(label);
  if (!match) return null;
  const topBit = Number(match[1]);
  const byteTotal = Math.ceil((topBit + 1) / 8);
  const paddedTopBit = byteTotal * 8 - 1;

  return Array.from({ length: byteTotal }, (_, index) => {
    const paddedHigh = paddedTopBit - index * 8;
    const paddedLow = paddedHigh - 7;
    const high = Math.min(topBit, paddedHigh);
    const low = Math.max(0, paddedLow);
    const bits = Array.from({ length: 8 }, (_, bitIndex) => {
      const bitNumber = paddedHigh - bitIndex;
      return bitNumber <= topBit && bitNumber >= 0 ? `A${bitNumber}` : "0";
    });
    return {
      label: paddedHigh > topBit ? `0 + A${high}:A${low}` : `A${high}:A${low}`,
      bits,
      role,
    };
  });
}

function byteFrameFromLabel(label: string, role: ByteRole): ByteFrame[] {
  const trimmed = label.trim();
  const tics = ticsFrames(trimmed, role);
  if (tics) return tics;

  const address = addressFrames(trimmed, role);
  if (address) return address;

  const hex = firstHexByte(trimmed);
  if (hex != null) {
    return [{ label: trimmed, bits: hexBits(hex), role }];
  }

  if (/\[0\.\.|uiLength|payload|ucp|buffer|ucArr|data/i.test(trimmed)) {
    return [{ label: trimmed, bits: symbolicBits(role === "rx" ? "D" : "P"), role }];
  }

  if (/addr\[[0-9]+:[0-9]+\]/i.test(trimmed)) {
    const match = /addr\[([0-9]+):([0-9]+)\]/i.exec(trimmed);
    if (match) {
      const high = Number(match[1]);
      return [{ label: trimmed, bits: Array.from({ length: 8 }, (_, index) => `A${high - index}`), role }];
    }
  }

  return [{ label: trimmed, bits: symbolicBits(role === "rx" ? "D" : "b"), role }];
}

function framesFromValues(values: string[], role: ByteRole, countHint?: number) {
  const cleanValues = values.filter((value) => value !== "-");
  const sourceValues =
    role === "rx" && countHint && countHint > 0
      ? cleanValues.slice(0, Math.max(1, Math.min(cleanValues.length, countHint)))
      : cleanValues;
  const frames = sourceValues.flatMap((value) => byteFrameFromLabel(value, role));
  if (frames.length > 0) return frames;
  if (countHint && countHint > 0) {
    return Array.from({ length: Math.min(countHint, 4) }, (_, index) => ({
      label: role === "rx" ? `RX[${index}]` : `TX[${index}]`,
      bits: symbolicBits(role === "rx" ? "D" : "b"),
      role,
    }));
  }
  return [];
}

function visibleFrames(frames: ByteFrame[], countHint?: number) {
  const maxFrames = 6;
  const visible = frames.slice(0, maxFrames);
  const hiddenByFrames = Math.max(0, frames.length - visible.length);
  const hiddenByCount = countHint && countHint > visible.length ? countHint - visible.length : 0;
  return { visible, hidden: Math.max(hiddenByFrames, hiddenByCount) };
}

function ClockPulse({ muted = false }: { muted?: boolean }) {
  return (
    <span className="relative block h-4 w-6" aria-hidden>
      <span className={cn("absolute left-0 right-0 top-3 border-t", muted ? "border-faint/40" : "border-accent/70")} />
      <span className={cn("absolute left-1 right-1 top-1 h-2 border-l border-r border-t", muted ? "border-faint/40" : "border-accent/70")} />
    </span>
  );
}

function BitCell({ bit, tone = "normal" }: { bit: string; tone?: BitTone }) {
  return (
    <div
      className={cn(
        "grid h-6 min-w-7 place-items-center rounded border px-1 font-mono text-[10px]",
        tone === "master"
          ? "border-accent/40 bg-accent/15 text-accent"
          : tone === "slave"
            ? "border-ok/35 bg-ok/15 text-ok"
            : tone === "ack"
          ? "border-ok/30 bg-ok/10 text-ok"
          : tone === "idle"
            ? "border-border bg-bg text-faint"
            : "border-border bg-inset text-text",
      )}
    >
      {bit}
    </div>
  );
}

function EventChip({ label }: { label: string }) {
  return (
    <div className="grid h-[96px] min-w-[66px] place-items-center rounded border border-accent/30 bg-accent/10 px-2 text-center font-mono text-[10px] text-accent">
      {label}
    </div>
  );
}

function I2cByte({
  frame,
  dataDriver,
  ackDriver,
  ackLabel = "ACK",
}: {
  frame: ByteFrame;
  dataDriver: "master" | "slave";
  ackDriver: "master" | "slave";
  ackLabel?: string;
}) {
  return (
    <div className="inline-grid min-w-max grid-rows-[18px_20px_26px_26px] gap-1 rounded-md border border-border bg-bg p-2">
      <div className="truncate font-mono text-[10px] text-muted">{frame.label}</div>
      <div className="grid grid-cols-9 gap-1">
        {frame.bits.map((_, index) => <ClockPulse key={`${frame.label}-scl-${index}`} />)}
        <ClockPulse muted />
      </div>
      <div className="grid grid-cols-9 gap-1">
        {frame.bits.map((bit, index) => <BitCell key={`${frame.label}-sda-${index}`} bit={bit} tone={dataDriver} />)}
        <BitCell bit={ackLabel} tone={ackDriver} />
      </div>
      <div className="grid grid-cols-9 gap-1 text-center font-mono text-[9px] text-faint">
        {frame.bits.map((_, index) => <span key={`${frame.label}-clk-${index}`}>{index + 1}</span>)}
        <span>9</span>
      </div>
    </div>
  );
}

function I2cWaveform({ transfer }: { transfer: KnowledgeRegisterTransfer }) {
  const read = isReadTransfer(transfer);
  const txCount = byteCount(transfer.txBytes);
  const rxCount = byteCount(transfer.rxBytes);
  const tx = visibleFrames(framesFromValues(transfer.tx, "tx", txCount), txCount);
  const rx = visibleFrames(framesFromValues(transfer.rx, "rx", rxCount), rxCount);
  const repeatedPattern = /x\s*\d+\s*byte|tekrar|toplam|\+ uiIndex/i.test(transfer.txBytes + " " + transfer.tx.join(" "));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">I2C</Badge>
        <Badge tone="neutral">SCL pulse başına 1 bit</Badge>
        <Badge tone="neutral">byte sonrası 9. clock ACK/NACK</Badge>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-faint">
        <span className="inline-flex items-center gap-1.5">
          <span className="grid h-4 w-4 place-items-center rounded-sm border border-accent/50 bg-accent/20 font-mono text-[9px] font-semibold text-accent" aria-hidden>
            M
          </span>
          master sürüyor
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="grid h-4 w-4 place-items-center rounded-sm border border-ok/50 bg-ok/20 font-mono text-[9px] font-semibold text-ok" aria-hidden>
            S
          </span>
          slave sürüyor
        </span>
        <span>Tek fiziksel SDA hattı gösterilir; renk aktif sürücüyü belirtir.</span>
      </div>
      <div className="overflow-x-auto rounded-md border border-border bg-elev p-3">
        <div className="mb-2 grid grid-cols-[64px_minmax(0,1fr)] gap-2 text-[10px] text-faint">
          <span>SCL</span>
          <span>Her kutudaki pulse bir clock darbesidir.</span>
          <span>SDA</span>
          <span>Tek SDA hattında master/slave aktif sürücü rengiyle ayrılır; adres catalog'da instance bağımsız olduğu için semboliktir.</span>
        </div>
        <div className="flex min-w-max items-start gap-2">
          <EventChip label="START" />
          <I2cByte
            frame={{ label: "SLA+W", bits: ["A6", "A5", "A4", "A3", "A2", "A1", "A0", "W"], role: "tx" }}
            dataDriver="master"
            ackDriver="slave"
          />
          {tx.visible.map((frame, index) => (
            <I2cByte key={`${frame.label}-${index}`} frame={frame} dataDriver="master" ackDriver="slave" />
          ))}
          {tx.hidden > 0 && <EventChip label={`+${tx.hidden} byte`} />}
          {read && (
            <>
              <EventChip label="RESTART" />
              <I2cByte
                frame={{ label: "SLA+R", bits: ["A6", "A5", "A4", "A3", "A2", "A1", "A0", "R"], role: "tx" }}
                dataDriver="master"
                ackDriver="slave"
              />
              {rx.visible.map((frame, index) => (
                <I2cByte
                  key={`${frame.label}-${index}`}
                  frame={frame}
                  dataDriver="slave"
                  ackDriver="master"
                  ackLabel={index === rx.visible.length - 1 && rx.hidden === 0 ? "NACK" : "ACK"}
                />
              ))}
              {rx.hidden > 0 && <EventChip label={`+${rx.hidden} byte`} />}
            </>
          )}
          <EventChip label="STOP" />
        </div>
      </div>
      {(repeatedPattern || tx.hidden > 0 || rx.hidden > 0) && (
        <p className="text-[11px] leading-relaxed text-faint">
          Bu işlemde aynı byte-level pattern birden çok register/data byte için tekrar eder; diyagram okunabilirlik için ilk byte'ları ve tekrar sayısını gösterir.
        </p>
      )}
    </div>
  );
}

function SpiByte({
  frame,
  direction,
}: {
  frame: ByteFrame;
  direction: "mosi" | "miso";
}) {
  const mosiBits = direction === "mosi" ? frame.bits : Array.from({ length: 8 }, () => "x");
  const misoBits = direction === "miso" ? frame.bits : Array.from({ length: 8 }, () => "Z");
  const rowClass = "grid grid-cols-[44px_repeat(8,1.75rem)] items-center gap-1";
  const labelClass = "font-mono text-[9px] font-semibold uppercase text-muted";

  return (
    <div className="inline-grid min-w-max gap-1 rounded-md border border-border bg-bg p-2">
      <div className="ml-[48px] truncate font-mono text-[10px] text-muted">{frame.label}</div>
      <div className={rowClass}>
        <span className={labelClass}>SCK</span>
        {frame.bits.map((_, index) => <ClockPulse key={`${frame.label}-sck-${index}`} />)}
      </div>
      <div className={rowClass}>
        <span className={labelClass}>MOSI</span>
        {mosiBits.map((bit, index) => <BitCell key={`${frame.label}-mosi-${index}`} bit={bit} tone={direction === "mosi" ? "normal" : "idle"} />)}
      </div>
      <div className={rowClass}>
        <span className={labelClass}>MISO</span>
        {misoBits.map((bit, index) => <BitCell key={`${frame.label}-miso-${index}`} bit={bit} tone={direction === "miso" ? "normal" : "idle"} />)}
      </div>
      <div className={`${rowClass} text-center font-mono text-[9px] text-faint`}>
        <span className={labelClass}>CLK</span>
        {frame.bits.map((_, index) => <span key={`${frame.label}-clk-${index}`}>{index + 1}</span>)}
      </div>
    </div>
  );
}

function spiModeNote(part: string) {
  const normalized = part.toUpperCase();
  if (normalized === "LMK04832") return "SPI mode 0, 24-bit frame, MSB-first; max SCK 5 MHz.";
  if (normalized === "LMX1204") return "SPI mode 0, 24-bit frame, MSB-first; max SCK 2 MHz.";
  if (normalized === "LMX2820") return "SPI mode 0, 24-bit frame, MSB-first; max SCK 40 MHz.";
  return "CS# low boyunca opcode/address/data MSB-first clocklanır; dummy/read clocks controller transferiyle üretilir.";
}

function SpiWaveform({ part, transfer }: { part: string; transfer: KnowledgeRegisterTransfer }) {
  const txCount = byteCount(transfer.txBytes);
  const rxCount = byteCount(transfer.rxBytes);
  const tx = visibleFrames(framesFromValues(transfer.tx, "tx", txCount), txCount);
  const rx = visibleFrames(framesFromValues(transfer.rx, "rx", rxCount), rxCount);
  const read = isReadTransfer(transfer);
  const write = isWriteTransfer(transfer);

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone="accent">SPI</Badge>
        <Badge tone="neutral">SCK pulse başına 1 bit</Badge>
        <Badge tone="neutral">CS# low aktif pencere</Badge>
        <Badge tone="neutral">{write && read ? "read/write" : write ? "write" : "read"}</Badge>
      </div>
      <p className="text-[11px] leading-relaxed text-faint">{spiModeNote(part)}</p>
      <div className="overflow-x-auto rounded-md border border-border bg-elev p-3">
        <div className="mb-2 grid grid-cols-[64px_minmax(0,1fr)] gap-2 text-[10px] text-faint">
          <span>CS#</span>
          <span>Soldan sağa low kabul edilir; transfer sonunda high olur.</span>
          <span>Satırlar</span>
          <span>Her byte kartında SCK, MOSI, MISO ve clock numarası kendi satırının solunda gösterilir.</span>
        </div>
        <div className="inline-block min-w-max">
          <div className="mb-2 rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-accent">
            CS# LOW
          </div>
          <div className="flex items-start gap-2">
            {tx.visible.map((frame, index) => (
              <SpiByte key={`${frame.label}-${index}`} frame={frame} direction="mosi" />
            ))}
            {tx.hidden > 0 && <EventChip label={`+${tx.hidden} TX`} />}
            {read && rx.visible.map((frame, index) => (
              <SpiByte key={`${frame.label}-${index}`} frame={frame} direction="miso" />
            ))}
            {read && rx.hidden > 0 && <EventChip label={`+${rx.hidden} RX`} />}
          </div>
          <div className="mt-2 rounded border border-border bg-bg px-2 py-1 font-mono text-[10px] text-accent">
            CS# HIGH
          </div>
        </div>
      </div>
      {(tx.hidden > 0 || rx.hidden > 0) && (
        <p className="text-[11px] leading-relaxed text-faint">
          Payload veya read data değişken uzunluklu olduğunda aynı 8-clock byte pattern'i devam eder; diyagram ilk byte'ları temsil eder.
        </p>
      )}
    </div>
  );
}

export default function BusWaveform({
  part,
  transfer,
}: {
  part: string;
  transfer: KnowledgeRegisterTransfer;
}) {
  const protocol = protocolForPart(part);
  if (!protocol) return null;

  return (
    <details className="rounded-md border border-border bg-inset/50">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2 text-xs font-semibold text-text">
        <span className="flex items-center gap-2">
          <Activity className="h-3.5 w-3.5 text-accent" aria-hidden />
          Bus zaman diyagramı
        </span>
        <span className="text-[10px] font-normal text-faint">protocol-level waveform</span>
      </summary>
      <div className="border-t border-border p-3">
        {protocol === "i2c" ? <I2cWaveform transfer={transfer} /> : <SpiWaveform part={part} transfer={transfer} />}
      </div>
    </details>
  );
}
