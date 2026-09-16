import { Plus, Trash2, ListPlus } from "lucide-react";
import { useStore } from "@/store/useStore";
import type { BoardControl, BoardControlBit, BoardControlRole } from "@/lib/types";
import { Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { CUSTOM_PIN, catalogBits, catalogPinByName, catalogPins } from "./boardPinCatalog";

/**
 * Kart kontrol GPIO'su (board_control): sirket kartlarinda tek bir dual-channel AXI GPIO'nun 1. kanali cikis
 * (AFE reset, JESD cekirdek fiziksel resetleri, Versal'da LCPLL reset), 2. kanali giris (GT PLL lock'lari).
 * Pin adlari SABIT katalogdan secilir (boardPinCatalog.ts, kullanici karari 2026-09-16): ad secilince kanal, rol,
 * aktif seviye ve hedef kendiliginden dolar; kullanici yalniz bit numarasini girer. Katalog disi pin icin "ozel" satiri.
 * Generate drivers/ip/boardctl uretir; jesdlink fiziksel reseti ve lock kontrolunu, AFE7900 AFE reset kaldirmayi bundan alir.
 */
const ROLES: Array<[BoardControlRole, string]> = [
  ["afe_reset", "AFE reset (açılışta aktif, bring-up öncesi kalkar)"],
  ["jesd_rx_core_reset", "JESD RX çekirdek fiziksel reset"],
  ["jesd_tx_core_reset", "JESD TX çekirdek fiziksel reset"],
  ["pll_reset", "GT HSCLK/LCPLL reset (yalnız Versal: PHY reset, JESD darbesine katılır)"],
  ["pll_lock", "GT PLL lock girişi (1 beklenir)"],
  ["sysref", "SYSREF darbesi çıkışı"],
  ["generic", "genel (LMX/LMK vb., dokunulmaz)"],
];

const EMPTY_BIT: BoardControlBit = { name: "", channel: 1, bit: 0, role: "generic", active_low: false, target: "" };

export default function BoardControlCard() {
  const controllers = useStore((s) => s.controllers);
  const platform = useStore((s) => s.project.platform);
  const boardControl = useStore((s) => s.boardControl);
  const setBoardControl = useStore((s) => s.setBoardControl);
  const gpios = controllers.filter((c) => c.type === "gpio");
  const bc: BoardControl = boardControl ?? { gpio_id: "", jesd_reset_ms: 100, afe_count: 1, bits: [] };
  const afeCount = bc.afe_count ?? 1;
  const catalog = catalogPins(platform, Math.max(afeCount, 1));

  const update = (patch: Partial<BoardControl>) => setBoardControl({ ...bc, ...patch });
  const setAfeCount = (n: number) => update({ afe_count: Math.max(1, Math.min(8, n)) });
  const updateBit = (index: number, patch: Partial<BoardControlBit>) =>
    update({ bits: bc.bits.map((b, i) => (i === index ? { ...b, ...patch } : b)) });
  const removeBit = (index: number) => update({ bits: bc.bits.filter((_, i) => i !== index) });
  const addBit = () => update({ bits: [...bc.bits, { ...EMPTY_BIT }] });
  const nextFreeBit = (channel: 1 | 2) => {
    const used = new Set(bc.bits.filter((b) => b.channel === channel).map((b) => b.bit));
    let bit = 0;
    while (used.has(bit) && bit < 31) bit++;
    return bit;
  };
  const pickCatalog = (index: number, name: string) => {
    if (name === CUSTOM_PIN) {
      updateBit(index, { name: "" });
      return;
    }
    const pin = catalogPinByName(platform, Math.max(afeCount, 1), name);
    if (!pin) return;
    const current = bc.bits[index];
    updateBit(index, {
      name: pin.name, channel: pin.channel, role: pin.role, active_low: pin.active_low, target: pin.target,
      bit: current.channel === pin.channel ? current.bit : nextFreeBit(pin.channel),
    });
  };
  const fillFromCatalog = () => update({ bits: catalogBits(platform, afeCount) });
  const isCatalogRow = (b: BoardControlBit) => catalog.some((p) => p.name === b.name);
  const duplicate = (b: BoardControlBit) => bc.bits.filter((o) => o.channel === b.channel && o.bit === b.bit).length > 1;

  if (gpios.length === 0) return null;

  return (
    <div className="rounded-md border border-border/60 bg-inset/40 px-3 py-2 text-xs">
      <div className="mb-1 font-semibold text-text">Kart kontrol GPIO (reset / PLL lock bitleri)</div>
      <p className="mb-2 text-[11px] text-muted">
        Dual-channel AXI GPIO: kanal 1 çıkış (AFE reset, JESD çekirdek fiziksel resetleri{platform === "versal" ? ", LCPLL reset" : ""}), kanal 2 giriş
        (GT PLL lock'ları). Pin adları sabit katalogdan seçilir; kanal, rol ve aktif seviye kendiliğinden dolar, sen yalnız bit
        numarasını girersin. Boş bırakılırsa üretilmez.
      </p>
      <div className="mb-2 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Label className="text-[11px]">GPIO</Label>
          <Select value={bc.gpio_id || "__none"} onValueChange={(v) => setBoardControl(v === "__none" ? null : { ...bc, gpio_id: v })}>
            <SelectTrigger className="h-7 w-56 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="__none">— yok —</SelectItem>
              {gpios.map((g) => (
                <SelectItem key={g.id} value={g.id}>{g.id} · {g.instance} · {g.base_address}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {bc.gpio_id && (
          <>
            <div className="flex items-center gap-2">
              <Label className="text-[11px]">JESD fiziksel reset (ms)</Label>
              <Input
                className="h-7 w-20 text-xs"
                value={bc.jesd_reset_ms ?? 100}
                onChange={(e) => update({ jesd_reset_ms: Math.max(1, Number(e.target.value) || 100) })}
              />
            </div>
            <div className="flex items-center gap-2">
              <Label className="text-[11px]">AFE sayısı</Label>
              <Select value={String(afeCount)} onValueChange={(v) => setAfeCount(Number(v) || 1)}>
                <SelectTrigger className="h-7 w-16 text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6, 7, 8].map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" onClick={fillFromCatalog} title="Tabloyu platforma göre katalog pinleriyle doldurur (bitler sırayla 0..n; kartına göre düzelt)">
                <ListPlus className="h-3.5 w-3.5" /> Katalogdan doldur
              </Button>
            </div>
          </>
        )}
      </div>
      {bc.gpio_id && (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead className="text-muted">
              <tr>
                <th className="pr-2 text-left font-normal">Pin (katalog)</th>
                <th className="pr-2 text-left font-normal">Kanal</th>
                <th className="pr-2 text-left font-normal">Bit</th>
                <th className="pr-2 text-left font-normal">Rol</th>
                <th className="pr-2 text-left font-normal">Aktif-düşük</th>
                <th className="pr-2 text-left font-normal">Hedef</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {bc.bits.map((b, i) => {
                const fromCatalog = isCatalogRow(b);
                return (
                  <tr key={i}>
                    <td className="py-0.5 pr-2">
                      <div className="flex items-center gap-1">
                        <Select value={fromCatalog ? b.name : CUSTOM_PIN} onValueChange={(v) => pickCatalog(i, v)}>
                          <SelectTrigger className="h-7 w-72 font-mono text-[11px]"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {catalog.map((p) => <SelectItem key={p.name} value={p.name}><span className="font-mono">{p.name}</span> <span className="text-muted">· {p.note}</span></SelectItem>)}
                            <SelectItem value={CUSTOM_PIN}>özel pin (adı elle yaz)</SelectItem>
                          </SelectContent>
                        </Select>
                        {!fromCatalog && (
                          <Input className="h-7 w-44 font-mono text-[11px]" value={b.name} placeholder="özel_pin_adi"
                            onChange={(e) => updateBit(i, { name: e.target.value })} />
                        )}
                      </div>
                    </td>
                    <td className="pr-2">
                      {fromCatalog ? (
                        <span className="font-mono">{b.channel === 1 ? "1 çıkış" : "2 giriş"}</span>
                      ) : (
                        <Select value={String(b.channel)} onValueChange={(v) => updateBit(i, { channel: v === "2" ? 2 : 1 })}>
                          <SelectTrigger className="h-7 w-24 text-[11px]"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="1">1 çıkış</SelectItem>
                            <SelectItem value="2">2 giriş</SelectItem>
                          </SelectContent>
                        </Select>
                      )}
                    </td>
                    <td className="pr-2">
                      <Input className={"h-7 w-14 text-[11px]" + (duplicate(b) ? " border-danger" : "")} value={b.bit}
                        title={duplicate(b) ? "aynı kanalda aynı bit iki kez" : undefined}
                        onChange={(e) => updateBit(i, { bit: Math.min(31, Math.max(0, Number(e.target.value) || 0)) })} />
                    </td>
                    <td className="pr-2">
                      {fromCatalog ? (
                        <span className="text-muted">{ROLES.find(([r]) => r === b.role)?.[1] ?? b.role}</span>
                      ) : (
                        <Select value={b.role} onValueChange={(v) => updateBit(i, { role: v as BoardControlRole })}>
                          <SelectTrigger className="h-7 w-64 text-[11px]"><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {ROLES.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      )}
                    </td>
                    <td className="pr-2 text-center">
                      <input type="checkbox" checked={b.active_low} disabled={fromCatalog} onChange={(e) => updateBit(i, { active_low: e.target.checked })} />
                    </td>
                    <td className="pr-2">
                      {fromCatalog ? (
                        <span className="font-mono">{b.target}</span>
                      ) : (
                        <Input className="h-7 w-32 font-mono text-[11px]" value={b.target ?? ""} placeholder="afe1 / jesd204c_rx"
                          onChange={(e) => updateBit(i, { target: e.target.value })} />
                      )}
                    </td>
                    <td>
                      <Button variant="ghost" size="sm" onClick={() => removeBit(i)} title="satırı sil"><Trash2 className="h-3.5 w-3.5" /></Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <Button variant="outline" size="sm" className="mt-1" onClick={addBit}><Plus className="h-3.5 w-3.5" /> Satır ekle</Button>
        </div>
      )}
    </div>
  );
}
