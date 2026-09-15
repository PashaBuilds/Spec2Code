import { useEffect, useMemo, useRef, useState } from "react";
import { Download, Loader2, Play, RefreshCw, Waves } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";
import { useStore } from "@/store/useStore";
import { downloadBytes } from "@/lib/download";

/**
 * Yakalama / Spektrum ekranı.
 *
 * PL'deki `jesd_loopback_util` modülü (scripts/hdl/jesd_loopback_util.v) JESD204C RX çıkışını
 * (256-bit beat = 16 × int16 örnek) BRAM'e yazar; ajan `mem_block` op'uyla (64 sözcük/istek, her
 * transport: UART / Ethernet / CoreSight) okunur. Burada ham örnekler ve FFT'si çizilir.
 *
 * Register haritası (base + offset): 0x08 CTRL (ARM[0], CLEAR[1]), 0x0C STATUS (DONE[0], BUSY[1],
 * RX_VALID_SEEN[2]), 0x10 COUNT, 0x14 DEPTH, 0x1C TX_PHASE_INC, 0x24 TX_BEATS, 0x28 RX_BEATS,
 * 0x8000.. veri (beat k, dilim j: 0x8000 + k*32 + j*4).
 */

const REG = { ID: 0x00, CTRL: 0x08, STATUS: 0x0c, COUNT: 0x10, DEPTH: 0x14, BEAT_BITS: 0x18, PHASE_INC: 0x1c, TX_BEATS: 0x24, RX_BEATS: 0x28, DATA: 0x8000 } as const;
const ID_MAGIC = 0x43415054; // "CAPT"
const WORDS_PER_REQ = 64;      // SPEC2CODE_TESTBENCH_DATA_MAX / 4
const WORDS_PER_BEAT = 8;      // veri penceresi beat basina 32 bayt (BEAT_BITS < 256 ise ust sozcukler 0)
/** Beat basina 16-bit ornek: BEAT_BITS/16 (64B/66B 4 lane: 16; 8B/10B 4 lane: 8). Register okunamadiysa 16. */
function samplesPerBeat(beatBits: number | undefined): number { const n = Math.floor((beatBits || 256) / 16); return n > 0 && n <= 16 ? n : 16; }

function parseInt0(s: string): number {
  const t = s.trim();
  if (!t) return NaN;
  return /^0x/i.test(t) ? parseInt(t, 16) : parseInt(t, 10);
}

/** Yerinde radix-2 FFT (re/im). n 2'nin kuvveti olmalı. */
function fft(re: Float64Array, im: Float64Array): void {
  const n = re.length;
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; }
  }
  for (let len = 2; len <= n; len <<= 1) {
    const ang = (-2 * Math.PI) / len;
    const wr = Math.cos(ang), wi = Math.sin(ang);
    for (let i = 0; i < n; i += len) {
      let cr = 1, ci = 0;
      for (let k = 0; k < len / 2; k++) {
        const ar = re[i + k + len / 2] * cr - im[i + k + len / 2] * ci;
        const ai = re[i + k + len / 2] * ci + im[i + k + len / 2] * cr;
        re[i + k + len / 2] = re[i + k] - ar; im[i + k + len / 2] = im[i + k] - ai;
        re[i + k] += ar; im[i + k] += ai;
        const ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

function spectrumDb(samples: Int16Array): { db: Float64Array; n: number } {
  let n = 1;
  while (n * 2 <= samples.length && n < 65536) n *= 2;
  const re = new Float64Array(n), im = new Float64Array(n);
  for (let i = 0; i < n; i++) {
    const w = 0.5 - 0.5 * Math.cos((2 * Math.PI * i) / (n - 1)); // Hann
    re[i] = (samples[i] / 32768) * w;
  }
  fft(re, im);
  const half = n / 2;
  const db = new Float64Array(half);
  let peak = -Infinity;
  for (let i = 0; i < half; i++) { const m = Math.hypot(re[i], im[i]) / (n / 4); db[i] = 20 * Math.log10(m + 1e-12); if (db[i] > peak) peak = db[i]; }
  return { db, n };
}

function useCanvasDraw(draw: (ctx: CanvasRenderingContext2D, w: number, h: number) => void, deps: unknown[]) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth || 600, h = c.clientHeight || 220;
    c.width = Math.round(w * dpr); c.height = Math.round(h * dpr);
    const ctx = c.getContext("2d"); if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    draw(ctx, w, h);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return ref;
}

export default function CapturePanel() {
  const board = useBoardConnection();
  const cmdId = useRef(1);
  const utilIp = useStore((s) => s.customIps.find((ip) => /loopback_util/i.test(ip.ip_name ?? "") || /loopback_util/i.test(ip.id)));
  const [baseText, setBaseText] = useState(utilIp?.base_address ?? "0xA0030000");
  const [fsMhz, setFsMhz] = useState("1600");
  const [phaseIncText, setPhaseIncText] = useState("0x0400");
  const [beatsText, setBeatsText] = useState("256");
  const [lane, setLane] = useState<"all" | "0" | "1" | "2" | "3">("all");
  const [status, setStatus] = useState<Record<string, number>>({});
  const [samples, setSamples] = useState<Int16Array>(new Int16Array(0));
  const [spb, setSpb] = useState(16);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [log, setLog] = useState<string[]>([]);

  useEffect(() => { if (utilIp?.base_address) setBaseText(utilIp.base_address); }, [utilIp?.base_address]);

  const base = parseInt0(baseText) >>> 0;
  const fs = parseFloat(fsMhz) || 0;
  function pushLog(...lines: string[]) { setLog((p) => [...lines, ...p].slice(0, 200)); }

  async function rd32(off: number): Promise<number> {
    const r = await api.testbenchCommand({ host: "session", port: 0, device: "regmap", operation: "mem_read", address: (base + off) >>> 0, length: 4, command_id: cmdId.current++, session_id: board.sessionId, timeout_s: 4 });
    const v = parseInt0(r.parsed.value || "");
    if (isNaN(v)) throw new Error(`mem_read 0x${(base + off).toString(16)}: ${r.parsed.message || "yanıt yok"}`);
    return v >>> 0;
  }
  async function wr32(off: number, value: number): Promise<void> {
    const r = await api.testbenchCommand({ host: "session", port: 0, device: "regmap", operation: "mem_write", address: (base + off) >>> 0, length: 4, value: value >>> 0, command_id: cmdId.current++, session_id: board.sessionId, timeout_s: 4 });
    if (r.parsed.ok !== "1") throw new Error(`mem_write 0x${(base + off).toString(16)}: ${r.parsed.message || "hata"}`);
  }
  async function readBlock(off: number, words: number): Promise<Uint8Array> {
    const r = await api.testbenchCommand({ host: "session", port: 0, device: "regmap", operation: "mem_block", address: (base + off) >>> 0, length: words, command_id: cmdId.current++, session_id: board.sessionId, timeout_s: 6 });
    const hex = r.parsed.data || "";
    if (r.parsed.ok !== "1" || hex.length < words * 8) throw new Error(`mem_block 0x${(base + off).toString(16)}: ${r.parsed.message || "eksik veri"} (${hex.length / 2} bayt)`);
    const out = new Uint8Array(words * 4);
    for (let i = 0; i < out.length; i++) out[i] = parseInt(hex.substr(i * 2, 2), 16);
    return out;
  }

  async function readStatus(): Promise<Record<string, number>> {
    const id = await rd32(REG.ID);
    if (id !== ID_MAGIC) pushLog(`UYARI: ID 0x${id.toString(16).toUpperCase()} ≠ CAPT — base adres yanlış olabilir`);
    const s: Record<string, number> = { id, status: await rd32(REG.STATUS), count: await rd32(REG.COUNT), depth: await rd32(REG.DEPTH), beat_bits: await rd32(REG.BEAT_BITS), phase_inc: await rd32(REG.PHASE_INC), tx_beats: await rd32(REG.TX_BEATS), rx_beats: await rd32(REG.RX_BEATS) };
    setStatus(s);
    pushLog(`durum: DONE=${s.status & 1} BUSY=${(s.status >> 1) & 1} RX_SEEN=${(s.status >> 2) & 1} COUNT=${s.count}/${s.depth} TX_BEATS=${s.tx_beats} RX_BEATS=${s.rx_beats}`);
    return s;
  }

  async function guarded(label: string, fn: () => Promise<void>) {
    if (!board.connected) { pushLog("kart bağlı değil (Test Bench → Bağlan)"); return; }
    setBusy(true); setProgress(label);
    try { await fn(); } catch (err) { pushLog(`HATA: ${err instanceof Error ? err.message : String(err)}`); }
    finally { setBusy(false); setProgress(""); }
  }

  const setTone = () => guarded("ton", async () => {
    const inc = parseInt0(phaseIncText) >>> 0;
    await wr32(REG.PHASE_INC, inc);
    pushLog(`TX_PHASE_INC = 0x${inc.toString(16).toUpperCase()} → ton ≈ ${((inc / 65536) * fs).toFixed(3)} MHz`);
  });

  const capture = () => guarded("yakala", async () => {
    await wr32(REG.CTRL, 0x2); // CLEAR
    await wr32(REG.CTRL, 0x1); // ARM
    for (let i = 0; i < 20; i++) {
      const st = await rd32(REG.STATUS);
      if (st & 1) break;
      await new Promise((r) => setTimeout(r, 50));
    }
    const s = await readStatus();
    if (!(s.status & 1)) pushLog("yakalama DONE olmadı: rx_tvalid gelmiyor (link kurulmadı?) — RX_BEATS sayacına bak");
  });

  const readData = () => guarded("oku", async () => {
    const s = await readStatus();
    const beats = Math.max(0, Math.min(s.count, parseInt0(beatsText) || 0));
    if (!beats) { pushLog("okunacak beat yok (COUNT=0)"); return; }
    const spb = samplesPerBeat(s.beat_bits);
    const totalWords = beats * WORDS_PER_BEAT;
    const bytes = new Uint8Array(totalWords * 4);
    for (let w = 0; w < totalWords; w += WORDS_PER_REQ) {
      const n = Math.min(WORDS_PER_REQ, totalWords - w);
      const chunk = await readBlock(REG.DATA + w * 4, n);
      bytes.set(chunk, w * 4);
      setProgress(`oku ${Math.round(((w + n) / totalWords) * 100)}%`);
    }
    // her beat 32 baytlik pencere: ilk spb ornek gecerli (128-bit beat'te ust 16 bayt sifir)
    const window = new Int16Array(bytes.buffer, 0, beats * WORDS_PER_BEAT * 2);
    const all = new Int16Array(beats * spb);
    for (let b = 0; b < beats; b++) for (let k = 0; k < spb; k++) all[b * spb + k] = window[b * WORDS_PER_BEAT * 2 + k];
    setSamples(all);
    setSpb(spb);
    pushLog(`${beats} beat / ${beats * spb} örnek okundu (BEAT_BITS=${s.beat_bits || 256}, ${Math.ceil(totalWords / WORDS_PER_REQ)} istek)`);
  });

  const captureAndRead = async () => { await capture(); await readData(); };

  const view = useMemo(() => {
    if (lane === "all") return samples;
    const l = parseInt(lane, 10);
    const out = new Int16Array(Math.floor(samples.length / 4));
    let k = 0;
    const perLane = Math.max(1, spb / 4);
    for (let i = 0; i < samples.length; i++) if (Math.floor((i % spb) / perLane) === l) out[k++] = samples[i];
    return out.subarray(0, k);
  }, [samples, lane, spb]);
  const viewFs = lane === "all" ? fs : fs / 4;
  const spec = useMemo(() => (view.length >= 16 ? spectrumDb(view) : null), [view]);
  const peak = useMemo(() => {
    if (!spec) return null;
    let bi = 1;
    for (let i = 1; i < spec.db.length; i++) if (spec.db[i] > spec.db[bi]) bi = i;
    return { bin: bi, mhz: (bi / spec.n) * viewFs, db: spec.db[bi] };
  }, [spec, viewFs]);

  const fg = typeof window !== "undefined" ? getComputedStyle(document.body).color : "#888";
  const rawRef = useCanvasDraw((ctx, w, h) => {
    ctx.strokeStyle = "#9ca3af"; ctx.lineWidth = 0.5; ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
    ctx.beginPath(); ctx.moveTo(0, h / 2); ctx.lineTo(w, h / 2); ctx.stroke();
    if (!view.length) { ctx.fillStyle = fg; ctx.font = "12px sans-serif"; ctx.fillText("veri yok — Yakala + Oku", 12, 20); return; }
    const n = Math.min(view.length, 4096);
    ctx.strokeStyle = "#3b82f6"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i < n; i++) { const x = (i / (n - 1)) * (w - 2) + 1; const y = h / 2 - (view[i] / 32768) * (h / 2 - 4); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
    ctx.stroke();
    ctx.fillStyle = fg; ctx.font = "11px sans-serif";
    ctx.fillText(`${n} örnek (int16) — ${view.length} toplam`, 8, 14);
  }, [view, fg]);
  const fftRef = useCanvasDraw((ctx, w, h) => {
    ctx.strokeStyle = "#9ca3af"; ctx.lineWidth = 0.5; ctx.strokeRect(0.5, 0.5, w - 1, h - 1);
    if (!spec) { ctx.fillStyle = fg; ctx.font = "12px sans-serif"; ctx.fillText("spektrum yok", 12, 20); return; }
    const top = 0, bottom = -120, pad = 24;
    for (let d = 0; d >= bottom; d -= 20) { const y = pad + ((top - d) / (top - bottom)) * (h - pad - 18); ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); ctx.fillStyle = fg; ctx.font = "10px sans-serif"; ctx.fillText(`${d} dB`, 4, y - 2); }
    ctx.strokeStyle = "#f59e0b"; ctx.lineWidth = 1; ctx.beginPath();
    for (let i = 0; i < spec.db.length; i++) { const x = (i / (spec.db.length - 1)) * (w - 2) + 1; const d = Math.max(bottom, Math.min(top, spec.db[i])); const y = pad + ((top - d) / (top - bottom)) * (h - pad - 18); if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }
    ctx.stroke();
    ctx.fillStyle = fg; ctx.font = "11px sans-serif";
    for (let k = 0; k <= 4; k++) { const x = (k / 4) * (w - 2) + 1; ctx.fillText(`${((k / 8) * viewFs).toFixed(0)} MHz`, Math.min(x, w - 56), h - 5); }
    ctx.fillText(`FFT ${spec.n} nokta, Hann — tepe ${peak ? `${peak.mhz.toFixed(3)} MHz (bin ${peak.bin}, ${peak.db.toFixed(1)} dB)` : "-"}`, 8, 14);
  }, [spec, peak, viewFs, fg]);

  const exportCsv = () => {
    const lines = ["index,sample"]; for (let i = 0; i < view.length; i++) lines.push(`${i},${view[i]}`);
    downloadBytes("capture.csv", new TextEncoder().encode(lines.join("\n")), "text/csv");
  };

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <Card className="p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Waves className="h-4 w-4 text-accent" aria-hidden />
          <h3 className="text-sm font-semibold text-text">Yakalama / Spektrum — JESD204C RX örnekleri</h3>
          <span className="text-xs text-faint">PL yakalama BRAM'i → ajan mem_block → ham çizim + FFT</span>
          <span className="ml-auto"><Badge tone={board.connected ? "ok" : "neutral"}>kart {board.connected ? "bağlı" : "kopuk"}</Badge></span>
        </div>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          PL'deki <code>jesd_loopback_util</code> modülü JESD204C RX çıkışını (beat başına 16 × int16 örnek) BRAM'e yazar; TX tarafına
          aynı modülün sinüs NCO'su beslenir. Her transport (UART, Ethernet, CoreSight) üzerinden çalışır; Ethernet'te 1024 beat
          (~32 KB) birkaç saniyede gelir. {utilIp ? `XSA'dan bulunan modül: ${utilIp.id} @ ${utilIp.base_address}.` : "XSA'da modül bulunamadı; base adresi elle gir."}
        </p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="space-y-1"><Label>Base adres</Label><Input value={baseText} onChange={(e) => setBaseText(e.target.value)} className="font-mono" /></div>
          <div className="space-y-1"><Label>Örnekleme hızı fs (MHz)</Label><Input value={fsMhz} onChange={(e) => setFsMhz(e.target.value)} title="Loopback: 16 örnek × core_clk (100 MHz) = 1600 MHz eşdeğeri; gerçek AFE'de ADC hızı" /></div>
          <div className="space-y-1"><Label>TX_PHASE_INC (ton = INC/65536 × fs)</Label><div className="flex gap-1"><Input value={phaseIncText} onChange={(e) => setPhaseIncText(e.target.value)} className="font-mono" /><Button size="sm" variant="outline" onClick={setTone} disabled={busy}>yaz</Button></div></div>
          <div className="space-y-1"><Label>Okunacak beat (×16 örnek)</Label><Input value={beatsText} onChange={(e) => setBeatsText(e.target.value)} /></div>
          <div className="space-y-1"><Label>Görünüm</Label>
            <Select value={lane} onValueChange={(v) => setLane(v as typeof lane)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tüm akış (16 ardışık örnek/beat)</SelectItem>
                <SelectItem value="0">Lane 0 (örnek 0-3)</SelectItem>
                <SelectItem value="1">Lane 1 (örnek 4-7)</SelectItem>
                <SelectItem value="2">Lane 2 (örnek 8-11)</SelectItem>
                <SelectItem value="3">Lane 3 (örnek 12-15)</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => void guarded("durum", async () => { await readStatus(); })} disabled={busy}><RefreshCw className="h-4 w-4" /> Durum</Button>
          <Button size="sm" variant="outline" onClick={capture} disabled={busy}>Yakala (ARM)</Button>
          <Button size="sm" variant="outline" onClick={readData} disabled={busy}>Oku</Button>
          <Button size="sm" onClick={() => void captureAndRead()} disabled={busy}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />} Yakala + Oku + Çiz</Button>
          <Button size="sm" variant="ghost" onClick={exportCsv} disabled={!view.length}><Download className="h-4 w-4" /> CSV</Button>
          {progress && <span className="text-xs text-muted">{progress}</span>}
          {status.depth !== undefined && (
            <span className="ml-auto flex flex-wrap gap-1 text-xs">
              <Badge tone={(status.status & 1) ? "ok" : "neutral"}>DONE {status.status & 1}</Badge>
              <Badge tone={(status.status >> 2) & 1 ? "ok" : "neutral"}>RX_SEEN {(status.status >> 2) & 1}</Badge>
              <Badge tone="neutral">COUNT {status.count}/{status.depth}</Badge>
              <Badge tone="neutral">RX_BEATS {status.rx_beats}</Badge>
            </span>
          )}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-3">
          <div className="mb-2 text-xs font-semibold text-text">Ham örnekler (zaman)</div>
          <canvas ref={rawRef} className="h-56 w-full" />
        </Card>
        <Card className="p-3">
          <div className="mb-2 text-xs font-semibold text-text">Spektrum (FFT, dBFS)</div>
          <canvas ref={fftRef} className="h-56 w-full" />
        </Card>
      </div>

      <Card className="p-3">
        <div className="mb-1 text-xs font-semibold text-text">Etkinlik günlüğü</div>
        <pre className="max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-muted">{log.join("\n") || "—"}</pre>
      </Card>
    </div>
  );
}
