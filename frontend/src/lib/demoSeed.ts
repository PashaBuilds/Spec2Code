import { useStore } from "@/store/useStore";
import type { Controller, Device, Mux, Zone } from "@/lib/types";

/** Dev-only schematic seed: open the app with `?demo` to render a
 * representative board (ZynqMP PS, I2C mux fan-out, QSPI flash, GEM)
 * without uploading an xparameters.h or running the backend. */
export function maybeSeedDemo(): void {
  if (!new URLSearchParams(window.location.search).has("demo")) return;

  const zones: Zone[] = [{ id: "ps", label: "PS — Processing System" }];
  const controllers: Controller[] = [
    { id: "ps_i2c_0", type: "i2c", instance: "I2C0", base_address: "0xFF020000", driver: "iicps", source: "xparameters", zone: "ps" },
    { id: "ps_i2c_1", type: "i2c", instance: "I2C1", base_address: "0xFF030000", driver: "iicps", source: "xparameters", zone: "ps" },
    { id: "ps_qspi_0", type: "qspi", instance: "QSPI", base_address: "0xFF0F0000", driver: "qspipsu", source: "xparameters", zone: "ps" },
    { id: "ps_uart_0", type: "uart", instance: "UART0", base_address: "0xFF000000", driver: "uartps", source: "xparameters", zone: "ps" },
    { id: "ps_gem_3", type: "eth", instance: "GEM3", base_address: "0xFF0E0000", driver: "emacps", source: "xparameters", zone: "ps" },
  ];
  const muxes: Mux[] = [
    { id: "u1_tca9548a", part: "TCA9548A", controller_id: "ps_i2c_0", i2c_address: "0x70", channels: 8 },
  ];
  const devices: Device[] = [
    {
      id: "u2_ltc2991",
      part: "LTC2991",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x48", via_mux: { mux_id: "u1_tca9548a", channel: 0 } },
    },
    {
      id: "u3_sht21",
      part: "SHT21",
      attach: { controller_id: "ps_i2c_0", i2c_address: "0x40", via_mux: { mux_id: "u1_tca9548a", channel: 2 } },
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
  ];

  useStore.setState({ step: "schematic", zones, controllers, muxes, devices });
}
