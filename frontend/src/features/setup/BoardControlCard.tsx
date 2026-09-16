import { Plus, Trash2 } from "lucide-react";
import { useStore } from "@/store/useStore";
import type { BoardControl, BoardControlBit, BoardControlRole } from "@/lib/types";
import { Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";

/**
 * Kart kontrol GPIO'su (board_control): sirket kartlarinda tek bir dual-channel AXI GPIO'nun 1. kanali cikis
 * (AFE reset, JESD cekirdek fiziksel resetleri, PLL resetleri, LMX/LMK kontrol), 2. kanali giris (GT PLL lock'lari).
 * Bit yerlesimi karttan karta degistigi icin burada tablo olarak girilir; Generate drivers/ip/boardctl uretir,
 * jesdlink bring-up'i fiziksel reseti ve lock kontrolunu, AFE7900 surucusu AFE reset kaldirmayi bundan alir.
 */
const ROLES: Array<[BoardControlRole, string]> = [
  ["afe_reset", "AFE reset (açılışta aktif, bring-up öncesi kalkar)"],
  ["jesd_rx_core_reset", "JESD RX çekirdek fiziksel reset"],
  ["jesd_tx_core_reset", "JESD TX çekirdek fiziksel reset"],
  ["pll_reset", "GT HSCLK/LCPLL reset (pasif tutulur)"],
  ["pll_lock", "GT PLL lock girişi (1 beklenir)"],
  ["sysref", "SYSREF darbesi çıkışı"],
  ["generic", "genel (LMX/LMK vb., dokunulmaz)"],
];

const EMPTY_BIT: BoardControlBit = { name: "", channel: 1, bit: 0, role: "generic", active_low: false, target: "" };

export default function BoardControlCard() {
  const controllers = useStore((s) => s.controllers);
  const boardControl = useStore((s) => s.boardControl);
  const setBoardControl = useStore((s) => s.setBoardControl);
  const gpios = controllers.filter((c) => c.type === "gpio");
  const bc: BoardControl = boardControl ?? { gpio_id: "", jesd_reset_ms: 100, bits: [] };

  const update = (patch: Partial<BoardControl>) => setBoardControl({ ...bc, ...patch });
  const updateBit = (index: number, patch: Partial<BoardControlBit>) =>
    update({ bits: bc.bits.map((b, i) => (i === index ? { ...b, ...patch } : b)) });
  const removeBit = (index: number) => update({ bits: bc.bits.filter((_, i) => i !== index) });
  const addBit = () => update({ bits: [...bc.bits, { ...EMPTY_BIT }] });

  if (gpios.length === 0) return null;

  return (
    <div className="rounded-md border border-border/60 bg-inset/40 px-3 py-2 text-xs">
      <div className="mb-1 font-semibold text-text">Kart kontrol GPIO (reset / PLL lock bitleri)</div>
      <p className="mb-2 text-[11px] text-muted">
        Dual-channel AXI GPIO: kanal 1 çıkış (AFE reset, JESD çekirdek fiziksel resetleri, PLL resetleri), kanal 2 giriş
        (GT PLL lock'ları). Bring-up: fiziksel JESD reset → AFE reset kaldır → AFE bring-up → register reset → lock kontrolü.
        Boş bırakılırsa üretilmez.
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
          <div className="flex items-center gap-2">
            <Label className="text-[11px]">JESD fiziksel reset (ms)</Label>
            <Input
              className="h-7 w-20 text-xs"
              value={bc.jesd_reset_ms ?? 100}
              onChange={(e) => update({ jesd_reset_ms: Math.max(1, Number(e.target.value) || 100) })}
            />
          </div>
        )}
      </div>
      {bc.gpio_id && (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead className="text-muted">
              <tr>
                <th className="pr-2 text-left font-normal">Pin adı (şematik)</th>
                <th className="pr-2 text-left font-normal">Kanal</th>
                <th className="pr-2 text-left font-normal">Bit</th>
                <th className="pr-2 text-left font-normal">Rol</th>
                <th className="pr-2 text-left font-normal">Aktif-düşük</th>
                <th className="pr-2 text-left font-normal">Hedef</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {bc.bits.map((b, i) => (
                <tr key={i}>
                  <td className="py-0.5 pr-2">
                    <Input className="h-7 w-56 font-mono text-[11px]" value={b.name} placeholder="afe1_reset_active_low"
                      onChange={(e) => updateBit(i, { name: e.target.value })} />
                  </td>
                  <td className="pr-2">
                    <Select value={String(b.channel)} onValueChange={(v) => updateBit(i, { channel: v === "2" ? 2 : 1 })}>
                      <SelectTrigger className="h-7 w-24 text-[11px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1 çıkış</SelectItem>
                        <SelectItem value="2">2 giriş</SelectItem>
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="pr-2">
                    <Input className="h-7 w-14 text-[11px]" value={b.bit}
                      onChange={(e) => updateBit(i, { bit: Math.min(31, Math.max(0, Number(e.target.value) || 0)) })} />
                  </td>
                  <td className="pr-2">
                    <Select value={b.role} onValueChange={(v) => updateBit(i, { role: v as BoardControlRole })}>
                      <SelectTrigger className="h-7 w-64 text-[11px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {ROLES.map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </td>
                  <td className="pr-2 text-center">
                    <input type="checkbox" checked={b.active_low} onChange={(e) => updateBit(i, { active_low: e.target.checked })} />
                  </td>
                  <td className="pr-2">
                    <Input className="h-7 w-32 font-mono text-[11px]" value={b.target ?? ""} placeholder="afe1 / jesd204c_rx"
                      onChange={(e) => updateBit(i, { target: e.target.value })} />
                  </td>
                  <td>
                    <Button variant="ghost" size="sm" onClick={() => removeBit(i)} title="satırı sil"><Trash2 className="h-3.5 w-3.5" /></Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Button variant="outline" size="sm" className="mt-1" onClick={addBit}><Plus className="h-3.5 w-3.5" /> Bit ekle</Button>
        </div>
      )}
    </div>
  );
}
