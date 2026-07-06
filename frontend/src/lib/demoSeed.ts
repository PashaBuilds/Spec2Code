import { useStore } from "@/store/useStore";
import type { Controller, Device, Mux, Zone } from "@/lib/types";

/** Dev-only schematic seed: open the app with `?demo` to render a
 * representative board (ZynqMP PS, I2C mux fan-out, QSPI flash, GEM)
 * without uploading an xparameters.h or running the backend. */
export function maybeSeedDemo(): void {
  if (!new URLSearchParams(window.location.search).has("demo")) return;

  const zones: Zone[] = [{ id: "ps", label: "PS — Processing System" }];
  // Canonical driver names + XPAR instances: the demo must generate real
  // code end-to-end exactly like a parsed design would.
  const controllers: Controller[] = [
    { id: "ps_i2c_0", type: "i2c", instance: "XPAR_XIICPS_0", base_address: "0xFF020000", driver: "XIicPs", source: "xparameters", zone: "ps" },
    { id: "ps_i2c_1", type: "i2c", instance: "XPAR_XIICPS_1", base_address: "0xFF030000", driver: "XIicPs", source: "xparameters", zone: "ps" },
    { id: "ps_qspi_0", type: "qspi", instance: "XPAR_XQSPIPSU_0", base_address: "0xFF0F0000", driver: "XQspiPsu", source: "xparameters", zone: "ps" },
    { id: "ps_spi_0", type: "spi", instance: "XPAR_XSPIPS_0", base_address: "0xFF040000", driver: "XSpiPs", source: "xparameters", zone: "ps" },
    { id: "ps_uart_0", type: "uart", instance: "XPAR_XUARTPS_0", base_address: "0xFF000000", driver: "XUartPs", source: "xparameters", zone: "ps" },
    { id: "ps_gem_3", type: "eth", instance: "XPAR_XEMACPS_3", base_address: "0xFF0E0000", driver: "XEmacPs", source: "xparameters", zone: "ps" },
  ];
  const muxes: Mux[] = [
    { id: "u1_tca9548a", part: "TCA9548A", controller_id: "ps_i2c_0", i2c_address: "0x70", channels: 8 },
  ];
  // Mux arkası dağılım saha kartını taklit eder: paylaşılan kanallar (ch3 ve
  // ch4'te ikişer entegre) + komşu tekil kanallar — kanal kablosu ayrışmasının
  // görsel doğrulaması bu düzenle yapılır.
  const devices: Device[] = [
    {
      id: "u2_ltc2991",
      part: "LTC2991",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x48", via_mux: { mux_id: "u1_tca9548a", channel: 3 } },
    },
    {
      id: "u3_sht21",
      part: "SHT21",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x40", via_mux: { mux_id: "u1_tca9548a", channel: 2 } },
    },
    {
      id: "u7_ltc2945",
      part: "LTC2945",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x6F", via_mux: { mux_id: "u1_tca9548a", channel: 3 } },
    },
    {
      id: "u8_ltc2991",
      part: "LTC2991",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x49", via_mux: { mux_id: "u1_tca9548a", channel: 4 } },
    },
    {
      id: "u9_ltc2991",
      part: "LTC2991",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x4A", via_mux: { mux_id: "u1_tca9548a", channel: 4 } },
    },
    {
      id: "u10_ds1682",
      part: "DS1682",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x6B", via_mux: { mux_id: "u1_tca9548a", channel: 5 } },
    },
    {
      id: "u4_tmp101",
      part: "TMP101",
      attach: { controller_id: "ps_i2c_1", i2c_address: "0x4A" },
    },
    {
      id: "u5_mt25qu02g",
      part: "MT25QU02G",
      attach: { controller_id: "ps_qspi_0", spi_chip_select: 0 },
    },
    {
      id: "u6_lmk04832",
      part: "LMK04832",
      attach: { controller_id: "ps_spi_0", spi_chip_select: 0 },
      // Kısa temsili TICS Pro dizisi: 4-wire (SPI_3WIRE_DIS=1) + PLL2 N.
      config: { ticspro_registers: ["0x000010", "0x016302", "0x018300"] },
    },
  ];

  useStore.setState({ step: "schematic", zones, controllers, muxes, devices });
}
