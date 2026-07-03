/** Konsol/akış ekranlarının ortak yardımcıları (tek kopya). */

/* eslint-disable-next-line no-control-regex */
const ANSI_RE = new RegExp("\\[[0-9;]*[A-Za-z]", "g");

export function stripAnsi(line: string): string {
  return line.replace(ANSI_RE, "");
}

function formatClock(date: Date, withMs: boolean): string {
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");
  if (!withMs) return `${hh}:${mm}:${ss}`;
  const ms = String(date.getMilliseconds()).padStart(3, "0");
  return `${hh}:${mm}:${ss}.${ms}`;
}

/** Backend zaman damgaları unix SANİYE cinsindendir. */
export function timeLabel(atSeconds: number, options?: { ms?: boolean }): string {
  return formatClock(new Date(atSeconds * 1000), options?.ms !== false);
}

/** Tarayıcı tarafı zaman damgaları (Date.now) MİLİSANİYE cinsindendir. */
export function timeLabelMs(atMs: number, options?: { ms?: boolean }): string {
  return formatClock(new Date(atMs), options?.ms === true);
}

export function downloadTextLog(prefix: string, body: string): void {
  const blob = new Blob([body], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${prefix}_${new Date().toISOString().replace(/[:.]/g, "-")}.log`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function makeSessionId(prefix: string): string {
  const globalCrypto = typeof globalThis !== "undefined" ? globalThis.crypto : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === "function") {
    return `${prefix}_${globalCrypto.randomUUID()}`;
  }
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}
