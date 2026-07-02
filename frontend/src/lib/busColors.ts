import type React from "react";

/** Canonical bus color language for the whole app.
 *
 * One transport = one color, everywhere: schematic wires, node badges,
 * knowledge views, logs, timelines. CSS variables live in theme/tokens.css;
 * keep the two files in sync.
 */

export type BusKind =
  | "i2c"
  | "spi"
  | "qspi"
  | "eth"
  | "uart"
  | "can"
  | "sdio"
  | "gpio";

const BUS_VAR: Record<BusKind, string> = {
  i2c: "var(--bus-i2c)",
  spi: "var(--bus-spi)",
  qspi: "var(--bus-qspi)",
  eth: "var(--bus-eth)",
  uart: "var(--bus-uart)",
  can: "var(--bus-can)",
  sdio: "var(--bus-sdio)",
  gpio: "var(--bus-gpio)",
};

const BUS_LABEL: Record<BusKind, string> = {
  i2c: "I2C",
  spi: "SPI",
  qspi: "QSPI",
  eth: "ETH",
  uart: "UART",
  can: "CAN",
  sdio: "SDIO",
  gpio: "GPIO",
};

export function busKind(transport: string | undefined | null): BusKind {
  const key = (transport ?? "").toLowerCase();
  if (key.includes("qspi")) return "qspi";
  if (key.includes("i2c")) return "i2c";
  if (key.includes("spi")) return "spi";
  if (key.includes("eth") || key.includes("emac") || key.includes("gem")) return "eth";
  if (key.includes("uart")) return "uart";
  if (key.includes("can")) return "can";
  if (key.includes("sd")) return "sdio";
  return "gpio";
}

/** CSS color value (var(--bus-*)) for inline style usage. */
export function busColor(transport: string | undefined | null): string {
  return BUS_VAR[busKind(transport)];
}

/** Human badge label (I2C, SPI, QSPI, ...). */
export function busLabel(transport: string | undefined | null): string {
  return BUS_LABEL[busKind(transport)];
}

/** Tinted badge style: colored text + faint same-hue background. */
export function busBadgeStyle(transport: string | undefined | null): React.CSSProperties {
  const color = busColor(transport);
  return {
    color,
    backgroundColor: `color-mix(in srgb, ${color} 14%, transparent)`,
    borderColor: `color-mix(in srgb, ${color} 45%, transparent)`,
  };
}
