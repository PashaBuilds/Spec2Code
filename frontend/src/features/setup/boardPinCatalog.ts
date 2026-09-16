import type { BoardControlBit, PlatformId } from "@/lib/types";

/**
 * Kart kontrol GPIO'su sabit pin katalogu (kullanici karari 2026-09-16): pin adlari elle yazilmaz, buradan secilir.
 * AFE numarasi 1'den baslar. Kanal, rol, aktif seviye ve hedef pinin dogasindan gelir; kullanici yalniz bit numarasini girer.
 *
 * Cikislar (kanal 1), AFE basina:
 *   afe{N}_reset_active_low                  afe_reset (aktif-dusuk; acilista aktif, bring-up oncesi kalkar)
 *   jesd_afe{N}_rx_core_reset_active_high    jesd_rx_core_reset (fiziksel, darbe)
 *   jesd_afe{N}_tx_core_reset_active_high    jesd_tx_core_reset (fiziksel, darbe)
 *   hsclk_afe{N}_lcpll_reset                 pll_reset - YALNIZ Versal (PHY reset calisma cevresi; darbeye katilir)
 * Girisler (kanal 2), AFE basina:
 *   afe{N}_hsclk{x}_lcpll_lock_{y}  x,y in {0,1}  pll_lock - YALNIZ Versal (4 bit)
 *   afe{N}_qpll_lock                              pll_lock - Versal disi (1 bit)
 * LMK/LMX ve LED pinleri ilk asamada katalog disi ("ozel pin" satiriyla girilebilir).
 */
export interface CatalogPin {
  name: string;
  channel: 1 | 2;
  role: BoardControlBit["role"];
  active_low: boolean;
  target: string;
  /** kisa aciklama (tabloda) */
  note: string;
}

export const CUSTOM_PIN = "__custom";

export function catalogPins(platform: PlatformId | string, afeCount: number): CatalogPin[] {
  const versal = platform === "versal";
  const pins: CatalogPin[] = [];
  for (let n = 1; n <= Math.max(1, afeCount); n++) {
    const afe = `afe${n}`;
    pins.push({ name: `${afe}_reset_active_low`, channel: 1, role: "afe_reset", active_low: true, target: afe, note: "AFE reset (açılışta aktif)" });
    pins.push({ name: `jesd_${afe}_rx_core_reset_active_high`, channel: 1, role: "jesd_rx_core_reset", active_low: false, target: afe, note: "JESD RX fiziksel reset" });
    pins.push({ name: `jesd_${afe}_tx_core_reset_active_high`, channel: 1, role: "jesd_tx_core_reset", active_low: false, target: afe, note: "JESD TX fiziksel reset" });
    if (versal) {
      pins.push({ name: `hsclk_${afe}_lcpll_reset`, channel: 1, role: "pll_reset", active_low: false, target: afe, note: "Versal: LCPLL/PHY reset (darbeye katılır)" });
      for (const x of [0, 1]) for (const y of [0, 1]) {
        pins.push({ name: `${afe}_hsclk${x}_lcpll_lock_${y}`, channel: 2, role: "pll_lock", active_low: false, target: afe, note: `Versal: HSCLK${x} LCPLL lock, quad ${y}` });
      }
    } else {
      pins.push({ name: `${afe}_qpll_lock`, channel: 2, role: "pll_lock", active_low: false, target: afe, note: "GT QPLL lock" });
    }
  }
  return pins;
}

/** Katalogdan tam tablo: bitler katalog sirasiyla 0..n (kullanici kendi kartina gore duzeltir). */
export function catalogBits(platform: PlatformId | string, afeCount: number): BoardControlBit[] {
  let out = 0;
  let inp = 0;
  return catalogPins(platform, afeCount).map((p) => ({
    name: p.name, channel: p.channel, bit: p.channel === 1 ? out++ : inp++, role: p.role, active_low: p.active_low, target: p.target,
  }));
}

export function catalogPinByName(platform: PlatformId | string, afeCount: number, name: string): CatalogPin | undefined {
  return catalogPins(platform, afeCount).find((p) => p.name === name);
}
