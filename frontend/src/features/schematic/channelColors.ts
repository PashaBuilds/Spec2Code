// I2C switch kanal renkleri: her kanalın kablosu VE "ch N" etiketi aynı
// renktedir, farklı kanallar farklı renk alır (saha isteği - kanal takibi
// göz ile yapılır). Palet koyu PCB temasında birbirinden net ayrışan, bus
// renkleriyle (I2C turuncu, SPI camgöbeği, QSPI mor) karışmayan tonlardan
// seçildi. Kanal numarası sabit kaldıkça rengi de sabittir (TCA9548A: 0..7).
const CHANNEL_COLORS = [
  "#fbbf24", // ch0 kehribar
  "#38bdf8", // ch1 gök mavisi
  "#34d399", // ch2 zümrüt
  "#f472b6", // ch3 pembe
  "#a78bfa", // ch4 eflatun
  "#f87171", // ch5 mercan
  "#a3e635", // ch6 limon yeşili
  "#2dd4bf", // ch7 turkuaz
];

export function channelColor(channel: number): string {
  const n = CHANNEL_COLORS.length;
  return CHANNEL_COLORS[((channel % n) + n) % n];
}
