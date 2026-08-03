import { useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Loader2, ToggleLeft } from "lucide-react";
import { Badge, Button, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { timeLabel } from "@/lib/console";
import type { GpioOpResult, TestbenchManifest } from "@/lib/types";

/** 32-bit hex/decimal alan çözümü; boş = 0. Geçersiz metin null döner. */
function parseU32(text: string): number | null {
  const clean = text.trim();
  if (clean === "") return 0;
  const parsed = /^0[xX]/.test(clean) ? Number.parseInt(clean.slice(2), 16) : Number.parseInt(clean, 10);
  if (!Number.isFinite(parsed) || parsed < 0 || parsed > 0xffffffff) return null;
  return parsed >>> 0;
}

function hex32(value: number): string {
  return `0x${(value >>> 0).toString(16).toUpperCase().padStart(8, "0")}`;
}

/** 32 bitin sabit genişlikli ikili gösterimi (MSB solda, nibble aralıklı). */
function bits32(value: number): string {
  const raw = (value >>> 0).toString(2).padStart(32, "0");
  return (raw.match(/.{1,4}/g) ?? []).join(" ");
}

/** AXI GPIO denetleyici op'ları: gpio_read / gpio_write.
 *
 * Hedef bir CİHAZ değil, AXI GPIO çekirdeğinin KENDİSİDİR (LED/reset bankası
 * gibi bir parça karşılığı olmayan hatlar) — tıpkı I2C hat taraması gibi.
 * Tel'e giden hedef manifest `gpio.controllers[].index` değeridir; controller_id
 * string'i tel'e ULAŞMAZ.
 *
 * Yön (TRI) davranışı bilinçli olarak asimetriktir ve kartta da öyle üretilir:
 * yazma maskelenen pinleri ÇIKIŞ yapar, okuma yönü HİÇ DEĞİŞTİRMEZ. */
export default function GpioCard({
  manifest,
  sessionId,
  connected,
  timeoutSeconds,
}: {
  manifest: TestbenchManifest | null;
  sessionId: string;
  connected: boolean;
  timeoutSeconds: number;
}) {
  const gpio = manifest?.gpio ?? null;
  const controllers = gpio?.controllers ?? [];

  const [controllerId, setControllerId] = useState("");
  const [channel, setChannel] = useState(1);
  const [maskText, setMaskText] = useState("0x0");
  const [valueText, setValueText] = useState("0x0");
  const [running, setRunning] = useState<"gpio_read" | "gpio_write" | null>(null);
  const [error, setError] = useState("");
  const [result, setResult] = useState<GpioOpResult | null>(null);

  const activeController = controllers.some((c) => c.id === controllerId)
    ? controllerId
    : controllers[0]?.id ?? "";

  if (!gpio || controllers.length === 0) return null;

  async function run(op: "gpio_read" | "gpio_write") {
    if (!connected || running || !activeController) return;
    const mask = parseU32(maskText);
    const value = parseU32(valueText);
    if (mask === null) {
      setError("Maske 32 bitlik bir sayı olmalı (0x… veya ondalık). 0 = tüm pinler.");
      return;
    }
    if (op === "gpio_write" && value === null) {
      setError("Değer 32 bitlik bir sayı olmalı (0x… veya ondalık).");
      return;
    }
    setRunning(op);
    setError("");
    try {
      const controller = controllers.find((c) => c.id === activeController);
      const response = await api.gpioOp({
        session_id: sessionId,
        controller_id: activeController,
        // Manifest indeksi tel'e giden ASIL hedeftir (bkz. dosya başı notu).
        controller_index: controller ? controller.index : 0xffffffff,
        op,
        channel,
        mask,
        value: op === "gpio_write" ? (value ?? 0) : 0,
        timeout_s: timeoutSeconds,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setRunning(null);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-elev p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <ToggleLeft className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-text">AXI GPIO</h3>
        <Badge tone="neutral">kanal 1–2 · 32 bit</Badge>
        {result ? (
          <span className="ml-auto font-mono text-[11px] text-muted">
            {timeLabel(result.taken_at)} · {result.duration_ms} ms
          </span>
        ) : null}
      </div>

      <p className="mb-3 text-xs leading-relaxed text-muted">
        Seçili AXI GPIO çekirdeğinin bir kanalını doğrudan okur/yazar — hedef bir entegre değil,
        çekirdeğin kendisidir. <strong>Yazma</strong> yalnızca maskedeki pinleri ÇIKIŞ yapar (aynı
        kanaldaki diğer pinlerin ve diğer kanalın yönü korunur), sonra oku-değiştir-yaz uygular.{" "}
        <strong>Okuma</strong> yönü hiç değiştirmez: sürülen bir hattı (tutulan reset, enable) giriş
        yapmak yıkıcı olurdu. Maske 0 = tüm 32 pin.
      </p>

      <div className="mb-3 flex flex-wrap items-end gap-3">
        <div className="min-w-56">
          <Label>Denetleyici</Label>
          <select
            value={activeController}
            onChange={(event) => setControllerId(event.target.value)}
            className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            {controllers.map((controller) => (
              <option key={controller.id} value={controller.id}>
                {controller.id} — {controller.instance}
              </option>
            ))}
          </select>
        </div>
        <div className="w-28">
          <Label>Kanal</Label>
          <select
            value={channel}
            onChange={(event) => setChannel(Number.parseInt(event.target.value, 10))}
            className="h-9 w-full rounded-md border border-border bg-inset px-2 font-mono text-xs text-text"
          >
            {(gpio.channels ?? [1, 2]).map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
        <div className="w-40">
          <Label>Maske</Label>
          <Input
            value={maskText}
            onChange={(event) => setMaskText(event.target.value)}
            className="font-mono text-xs"
            placeholder="0x0 = tüm pinler"
          />
        </div>
        <div className="w-40">
          <Label>Değer (yazma)</Label>
          <Input
            value={valueText}
            onChange={(event) => setValueText(event.target.value)}
            className="font-mono text-xs"
            placeholder="0x0"
          />
        </div>
        <Button onClick={() => void run("gpio_read")} disabled={!connected || running !== null}>
          {running === "gpio_read" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <ArrowDownToLine className="h-4 w-4" aria-hidden />
          )}
          {running === "gpio_read" ? "Okunuyor..." : "Oku"}
        </Button>
        <Button
          variant="danger"
          onClick={() => void run("gpio_write")}
          disabled={!connected || running !== null}
        >
          {running === "gpio_write" ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <ArrowUpFromLine className="h-4 w-4" aria-hidden />
          )}
          {running === "gpio_write" ? "Yazılıyor..." : "Yaz"}
        </Button>
        {!connected ? <span className="text-xs text-faint">Önce karta bağlan.</span> : null}
      </div>

      {error ? (
        <p className="mb-3 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="rounded-md border border-ok/30 bg-ok/10 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge tone="ok">{result.op}</Badge>
            <Badge tone="neutral">kanal {result.channel}</Badge>
            <Badge tone="neutral">maske {hex32(result.mask)}</Badge>
            <span className="rounded-md border border-ok/40 bg-ok/15 px-2 py-0.5 font-mono text-sm font-semibold text-ok">
              {hex32(result.value)}
            </span>
          </div>
          <div className="text-[11px] text-faint">bitler (MSB → LSB)</div>
          <code className="block break-all font-mono text-xs text-text">{bits32(result.value)}</code>
          {result.message ? (
            <p className="mt-2 break-all text-xs leading-relaxed text-muted">{result.message}</p>
          ) : null}
        </div>
      ) : (
        <div className="rounded-md border border-border bg-inset p-3 text-xs text-muted">
          Henüz işlem yapılmadı. Sonuç burada kalıcı olarak görünecek.
        </div>
      )}
    </section>
  );
}
