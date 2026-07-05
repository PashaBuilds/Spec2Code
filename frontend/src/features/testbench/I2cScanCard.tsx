import { useMemo, useState } from "react";
import { Loader2, Radar } from "lucide-react";
import { Badge, Button, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { timeLabel } from "@/lib/console";
import { cn } from "@/lib/utils";
import type { I2cScanResult, TestbenchManifest } from "@/lib/types";

function hexAddr(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}

interface ExpectedDevice {
  id: string;
  part: string;
  address: number;
}

/** Pozisyon anahtarı: doğrudan hat "direct", switch arkası "muxId:kanal". */
function positionKey(muxId: string | null, channel: number | null): string {
  return muxId == null ? "direct" : `${muxId}:${channel}`;
}

/** Şematik modeli: seçili denetleyicideki I2C cihazları pozisyon pozisyon.
 * Tarama sonucu bu beklentiyle karşılaştırılır — eşleşen adresin yanına
 * cihaz yazılır, modelde olmayan adres ve cevap vermeyen modelli cihaz
 * ayrıca işaretlenir. */
function expectedDevicesByPosition(
  manifest: TestbenchManifest | null,
  controllerId: string,
): Map<string, ExpectedDevice[]> {
  const out = new Map<string, ExpectedDevice[]>();
  for (const device of manifest?.devices ?? []) {
    const attach = device.attach;
    if (!attach || attach.controller_id !== controllerId || !attach.i2c_address) continue;
    const address = Number.parseInt(String(attach.i2c_address), 16);
    if (!Number.isFinite(address)) continue;
    const key = positionKey(attach.via_mux?.mux_id ?? null, attach.via_mux?.channel ?? null);
    const list = out.get(key) ?? [];
    list.push({ id: device.id, part: device.part, address });
    out.set(key, list);
  }
  return out;
}

/** Bir pozisyonun adres çipleri: bulunanlar (şematik eşleşmesiyle) +
 * şematikte beklenip cevap vermeyenler. */
function PositionChips({
  addresses,
  expected,
  empty = "—",
}: {
  addresses: number[];
  expected: ExpectedDevice[];
  empty?: string;
}) {
  const missing = expected.filter((device) => !addresses.includes(device.address));
  if (addresses.length === 0 && missing.length === 0) {
    return <span className="text-xs text-faint">{empty}</span>;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {addresses.map((address) => {
        const match = expected.find((device) => device.address === address);
        return match ? (
          <span
            key={address}
            className="rounded border border-ok/40 bg-ok/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-ok"
            title={`Şematikle eşleşti: ${match.part} (${match.id})`}
          >
            {hexAddr(address)} · {match.id}
          </span>
        ) : (
          <span
            key={address}
            className="rounded border border-accent/40 bg-accent/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-accent"
            title="Bu pozisyonda bu adreste şematikte modellenmiş cihaz yok."
          >
            {hexAddr(address)} · şematikte yok
          </span>
        );
      })}
      {missing.map((device) => (
        <span
          key={`missing-${device.address}-${device.id}`}
          className="rounded border border-dashed border-danger/50 bg-danger/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-danger"
          title={`Şematikte bu pozisyonda ${device.part} (${device.id}) ${hexAddr(device.address)} adresinde modellenmiş ama taramada cevap vermedi.`}
        >
          {hexAddr(device.address)} · {device.id} · cevap yok
        </span>
      ))}
    </div>
  );
}

/** I2C hat taraması: 0x08..0x77 adres yoklaması + switch arkası kanal kanal
 * harita. Yalnız "bu pozisyonda bu adres cevap veriyor" bilgisi döner —
 * cihaz kimliği çıkarılmaz. Prob 1-baytlık 0x00 YAZMAsıdır (recv-polled
 * prob sahada NACK'te de başarı döndürdü); kanal taramasında aktif
 * switch'in kendi adresi ajana atlatılır. */
export default function I2cScanCard({
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
  const scanInfo = manifest?.i2c_scan ?? null;
  const [controllerId, setControllerId] = useState("");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<I2cScanResult | null>(null);

  const controllers = scanInfo?.controllers ?? [];
  const activeController = controllers.some((c) => c.id === controllerId)
    ? controllerId
    : controllers[0]?.id ?? "";
  const muxes = useMemo(
    () => (scanInfo?.muxes ?? []).filter((mux) => mux.controller_id === activeController),
    [scanInfo, activeController],
  );

  if (!scanInfo || controllers.length === 0) return null;

  async function runScan() {
    if (!connected || scanning || !activeController) return;
    setScanning(true);
    setError("");
    try {
      const scan = await api.i2cScan({
        session_id: sessionId,
        controller_id: activeController,
        muxes: muxes.map((mux) => ({ id: mux.id, part: mux.part, address: mux.address, channels: mux.channels })),
        // Tek tarama ~112 yoklama; switch başına kanal sayısı kadar tarama
        // daha koşar — komut başına zaman aşımı yeterli genişlikte olsun.
        timeout_s: Math.max(10, timeoutSeconds * 2),
      });
      setResult(scan);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setScanning(false);
    }
  }

  const muxById = new Map((scanInfo.muxes ?? []).map((mux) => [mux.address, mux]));
  // Şematik beklentisi: sonuç hangi denetleyiciyle alındıysa ona göre
  // (denetleyici seçimi sonradan değişmiş olabilir).
  const expectedByPosition = expectedDevicesByPosition(manifest, result?.controller_id ?? activeController);

  return (
    <section className="rounded-lg border border-border bg-elev p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Radar className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-text">I2C hat taraması</h3>
        <Badge tone="neutral">0x08–0x77</Badge>
        {result?.agent_version ? (
          <Badge tone={result.probe_is_write ? "neutral" : "warn"}>ajan {result.agent_version}</Badge>
        ) : result ? (
          <Badge tone="warn">ajan sürümü alınamadı</Badge>
        ) : null}
        {result ? (
          <span className="ml-auto font-mono text-[11px] text-muted">
            {timeLabel(result.taken_at)} · {result.duration_ms} ms
          </span>
        ) : null}
      </div>

      {result && result.probe_is_write === false ? (
        <p className="mb-3 rounded border border-danger/30 bg-danger/10 p-2 text-xs leading-relaxed text-danger">
          Karttaki ajan {result.agent_version ?? "sürümü belirsiz"} — yazma-problu tarama v0.1.105+
          firmware gerektirir. Eski ELF'in okuma probu gerçek kartta NACK'te de başarı raporladı ve
          tüm adresleri "cevap veriyor" gösterdi. Kaynakları güncelle + build sonrası ÜRETİLEN yeni
          ELF'i karta yükleyip "Sürüm sorgula" ile doğrula.
        </p>
      ) : null}
      {result?.suspect_all_ack ? (
        <p className="mb-3 rounded border border-warn/30 bg-warn/10 p-2 text-xs leading-relaxed text-warn">
          0x08–0x77 aralığının neredeyse tamamı cevap verdi — bu fiziksel olarak olağan dışıdır.
          Tipik nedenler: eski firmware'in okuma probu veya SDA'sı LOW'a takılı bir hat. Harita bu
          haliyle güvenilir değildir.
        </p>
      ) : null}
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Hattaki her adres 1-baytlık yazma (0x00) ile yoklanır — bu bayt çoğu cihazda yalnız register
        pointer'ını sıfırlar. Switch (I2C mux) varsa arkasındaki her kanal sırasıyla seçilip ayrıca
        taranır ve tam harita çıkarılır; kanal taranırken aktif switch'in kendi adresi atlanır. Yalnız
        adres/pozisyon bilgisi döner — cihaz kimliği çıkarılmaz.
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
        <Button onClick={() => void runScan()} disabled={!connected || scanning}>
          {scanning ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Radar className="h-4 w-4" aria-hidden />}
          {scanning ? "Taranıyor..." : "Hattı tara"}
        </Button>
        {muxes.length > 0 ? (
          <Badge tone="accent">{muxes.length} switch · kanal kanal taranır</Badge>
        ) : (
          <Badge tone="neutral">switch yok — yalnız doğrudan hat</Badge>
        )}
        {!connected ? <span className="text-xs text-faint">Önce karta bağlan.</span> : null}
      </div>

      {error ? (
        <p className="mb-3 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
      ) : null}

      {result ? (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-xs">
            <thead className="bg-inset">
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
                <th className="px-3 py-2">Pozisyon</th>
                <th className="px-3 py-2">Cevap veren adresler</th>
                <th className="px-3 py-2 text-right">Adet</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              <tr>
                <td className="px-3 py-2 font-mono text-text">Doğrudan hat</td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <PositionChips
                      addresses={result.direct_addresses}
                      expected={expectedByPosition.get("direct") ?? []}
                      empty="cihaz yok"
                    />
                    {result.switch_addresses.map((address) => (
                      <span
                        key={address}
                        className="rounded border border-warn/40 bg-warn/10 px-1.5 py-0.5 font-mono text-[11px] font-semibold text-warn"
                        title="I2C switch (kanallari asagida ayrica taranmistir)"
                      >
                        {hexAddr(address)} · switch{muxById.get(address) ? ` ${muxById.get(address)!.id}` : ""}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 text-right font-mono text-muted">
                  {result.direct_addresses.length + result.switch_addresses.length}
                </td>
              </tr>
              {result.muxes.map((mux) => (
                <>
                  <tr key={`${mux.id}-head`} className="bg-inset/60">
                    <td className="px-3 py-1.5 font-mono text-[11px] text-warn" colSpan={3}>
                      {mux.id} — {mux.part} ({hexAddr(mux.address)}) arkası
                    </td>
                  </tr>
                  {mux.channels.map((channel) => (
                    <tr key={`${mux.id}-ch${channel.channel}`} className={cn(channel.addresses.length === 0 && "opacity-70")}>
                      <td className="px-3 py-1.5 pl-6 font-mono text-muted">kanal {channel.channel}</td>
                      <td className="px-3 py-1.5">
                        <PositionChips
                          addresses={channel.addresses}
                          expected={expectedByPosition.get(positionKey(mux.id, channel.channel)) ?? []}
                          empty="boş"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono text-muted">{channel.addresses.length}</td>
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
