/** Tarayicida dosya indirme yardimcilari (Blob -> <a download>). */

export function downloadBlob(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = name;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function downloadBytes(name: string, bytes: Uint8Array, mime: string): void {
  downloadBlob(name, new Blob([bytes as BlobPart], { type: mime }));
}

export function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
