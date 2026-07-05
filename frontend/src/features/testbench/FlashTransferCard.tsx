import { useRef, useState } from "react";
import { Download, HardDrive, Loader2, Upload } from "lucide-react";
import { Badge, Button, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useBoardConnection } from "@/store/connection";
import type { TestbenchManifestDevice } from "@/lib/types";

/** Komut başına protokol data alanı sınırı (SPEC2CODE_TESTBENCH_DATA_MAX). */
const CHUNK_BYTES = 256;
/** Tek aktarım üst sınırı (UI): protokol sınırı değil, zaman sınırı — DCC
 * üzerinde 256 baytlık komut ~0.5 s sürer; 1 MiB ≈ 4096 komut. Daha büyük
 * dump'lar için TCP/UART transportu önerilir. */
const MAX_TRANSFER_BYTES = 1024 * 1024;
/** Komut id bandı: UI sayacı (1..) ve tarama bandıyla (7000+) çakışmasın. */
const TRANSFER_COMMAND_ID_BASE = 9000;

function parseNumber(value: string): number | null {
  const text = value.trim();
  if (!text) return null;
  const parsed = Number.parseInt(text, text.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function hexAddr(value: number): string {
  return `0x${value.toString(16).toUpperCase()}`;
}

function bytesFromDataHex(dataHex: string): Uint8Array {
  const clean = (dataHex || "").replace(/[^0-9a-fA-F]/g, "");
  const bytes = new Uint8Array(Math.floor(clean.length / 2));
  for (let i = 0; i < bytes.length; i++) bytes[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16);
  return bytes;
}

function hexFromBytes(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).toUpperCase().padStart(2, "0")).join("");
}

function downloadBlob(bytes: Uint8Array<ArrayBuffer>, filename: string) {
  const url = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

interface Progress {
  done: number;
  total: number;
  startedAt: number;
  label: string;
}

/** Flash <-> binary dosya aktarımı: okuma chunk chunk data_read ile .bin
 * indirir; yazma .bin dosyasını sayfa hizalı page_program komutlarıyla
 * yazar (NOR: ilgili alan önceden silinmiş olmalı — program yalnız 1->0
 * çevirir) ve istenirse geri okuyup doğrular. Komut başına 256 bayt
 * protokol sınırıdır; kart aktarımı chunk'lara böler. */
export default function FlashTransferCard({ device }: { device: TestbenchManifestDevice }) {
  const board = useBoardConnection();
  const isConnected = board.connected;
  const hasRead = device.operations.some((op) => op.name === "data_read");
  const hasWrite = device.operations.some((op) => op.name === "page_program");
  const [readAddress, setReadAddress] = useState("0x0");
  const [readLength, setReadLength] = useState("4096");
  const [writeAddress, setWriteAddress] = useState("0x0");
  const [writeFile, setWriteFile] = useState<File | null>(null);
  const [verifyAfterWrite, setVerifyAfterWrite] = useState(true);
  const [busy, setBusy] = useState<"" | "read" | "write">("");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState("");
  const cancelRef = useRef(false);
  const commandIdRef = useRef(TRANSFER_COMMAND_ID_BASE);

  if (!hasRead && !hasWrite) return null;

  async function sendChunkCommand(operation: string, address: number, length: number | null, dataHex: string) {
    commandIdRef.current += 1;
    return api.testbenchCommand({
      host: board.transport === "tcp" ? board.host.trim() : board.transport,
      port: board.transport === "tcp" ? parseNumber(board.port) ?? 0 : 0,
      device: device.id,
      operation,
      command_id: commandIdRef.current,
      session_id: board.sessionId,
      address,
      length,
      data_hex: dataHex,
      timeout_s: board.timeoutSeconds(),
    });
  }

  /** Aralığı chunk chunk okur; her chunk'ın bayt sayısı doğrulanır. */
  async function readRange(address: number, length: number, label: string): Promise<Uint8Array<ArrayBuffer>> {
    const out = new Uint8Array(length);
    const startedAt = performance.now();
    let offset = 0;
    while (offset < length) {
      if (cancelRef.current) throw new Error(`iptal edildi (${offset}/${length} bayt okunmuştu)`);
      const chunk = Math.min(CHUNK_BYTES, length - offset);
      const response = await sendChunkCommand("data_read", address + offset, chunk, "");
      if (response.parsed.ok !== "1") {
        throw new Error(`${hexAddr(address + offset)} okuması başarısız: ${response.parsed.message ?? "yanıt yok"}`);
      }
      const bytes = bytesFromDataHex(response.parsed.data ?? "");
      if (bytes.length !== chunk) {
        throw new Error(`${hexAddr(address + offset)}: ${chunk} bayt beklendi, ${bytes.length} bayt döndü`);
      }
      out.set(bytes, offset);
      offset += chunk;
      setProgress({ done: offset, total: length, startedAt, label });
    }
    return out;
  }

  async function runRead() {
    const address = parseNumber(readAddress);
    const length = parseNumber(readLength);
    if (address == null || length == null || length === 0) {
      setError("Adres ve uzunluk geçerli olmalı (uzunluk > 0).");
      return;
    }
    if (length > MAX_TRANSFER_BYTES) {
      setError(`Tek aktarım üst sınırı ${MAX_TRANSFER_BYTES / 1024} KiB (protokol değil zaman sınırı: komut başına ${CHUNK_BYTES} bayt gider).`);
      return;
    }
    setBusy("read");
    setError("");
    setSummary("");
    cancelRef.current = false;
    try {
      const startedAt = performance.now();
      const bytes = await readRange(address, length, "okunuyor");
      const seconds = (performance.now() - startedAt) / 1000;
      const name = `${device.id}_${hexAddr(address)}_${length}B.bin`;
      downloadBlob(bytes, name);
      setSummary(
        `${length} bayt okundu (${seconds.toFixed(1)} sn, ~${Math.round(length / Math.max(seconds, 0.001))} B/s) → ${name} · ilk 16 bayt: ${hexFromBytes(bytes.slice(0, 16))}`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
      setProgress(null);
    }
  }

  async function runWrite() {
    const address = parseNumber(writeAddress);
    if (address == null || !writeFile) {
      setError("Hedef adres ve .bin dosyası gerekli.");
      return;
    }
    if (writeFile.size === 0 || writeFile.size > MAX_TRANSFER_BYTES) {
      setError(`Dosya 1 bayt ile ${MAX_TRANSFER_BYTES / 1024} KiB arasında olmalı.`);
      return;
    }
    const confirmed = window.confirm(
      `${writeFile.name} (${writeFile.size} bayt) → ${device.part} ${hexAddr(address)}..${hexAddr(address + writeFile.size - 1)} yazılacak.\n\n` +
      `DİKKAT: NOR flash programlama yalnız 1→0 çevirir; hedef alan önceden SİLİNMİŞ (0xFF) olmalıdır, yoksa veri bozuk yazılır ve doğrulama düşer. Devam edilsin mi?`,
    );
    if (!confirmed) return;
    setBusy("write");
    setError("");
    setSummary("");
    cancelRef.current = false;
    try {
      const bytes = new Uint8Array(await writeFile.arrayBuffer());
      const startedAt = performance.now();
      let offset = 0;
      while (offset < bytes.length) {
        if (cancelRef.current) throw new Error(`iptal edildi (${offset}/${bytes.length} bayt yazılmıştı)`);
        // Sayfa hizalama: page_program sayfa sınırını aşamaz (256B sayfa).
        const target = address + offset;
        const chunk = Math.min(CHUNK_BYTES - (target % CHUNK_BYTES), bytes.length - offset);
        const response = await sendChunkCommand("page_program", target, null, hexFromBytes(bytes.subarray(offset, offset + chunk)));
        if (response.parsed.ok !== "1") {
          throw new Error(`${hexAddr(target)} yazımı başarısız: ${response.parsed.message ?? "yanıt yok"}`);
        }
        offset += chunk;
        setProgress({ done: offset, total: bytes.length, startedAt, label: "yazılıyor" });
      }
      const writeSeconds = (performance.now() - startedAt) / 1000;
      if (verifyAfterWrite) {
        const readBack = await readRange(address, bytes.length, "doğrulanıyor");
        for (let i = 0; i < bytes.length; i++) {
          if (readBack[i] !== bytes[i]) {
            throw new Error(
              `doğrulama düştü: ${hexAddr(address + i)} adresinde 0x${bytes[i].toString(16).toUpperCase().padStart(2, "0")} beklendi, ` +
              `0x${readBack[i].toString(16).toUpperCase().padStart(2, "0")} okundu (alan silinmemiş olabilir)`,
            );
          }
        }
      }
      setSummary(
        `${bytes.length} bayt yazıldı (${writeSeconds.toFixed(1)} sn)${verifyAfterWrite ? " ve geri okumayla birebir doğrulandı" : ""}.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy("");
      setProgress(null);
    }
  }

  const percent = progress ? Math.round((progress.done / progress.total) * 100) : 0;
  const etaSeconds = progress && progress.done > 0
    ? ((performance.now() - progress.startedAt) / progress.done) * (progress.total - progress.done) / 1000
    : null;

  return (
    <div className="rounded-md border border-border bg-inset p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <HardDrive className="h-4 w-4 text-accent" aria-hidden />
        <span className="text-xs font-semibold text-text">Binary dosya aktarımı</span>
        <Badge tone="neutral">komut başına {CHUNK_BYTES} bayt</Badge>
        <Badge tone="neutral">tek aktarım ≤ {MAX_TRANSFER_BYTES / 1024} KiB</Badge>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Aktarım {CHUNK_BYTES} baytlık komutlara bölünür (protokol data alanı sınırı); üst sınır zaman
        pratikliğidir — büyük aktarımlarda TCP/UART, CoreSight DCC'den belirgin hızlıdır.
      </p>

      {hasRead ? (
        <div className="mb-3 flex flex-wrap items-end gap-3">
          <div className="w-36">
            <Label>Başlangıç adresi</Label>
            <Input value={readAddress} onChange={(e) => setReadAddress(e.target.value)} placeholder="0x0" disabled={busy !== ""} />
          </div>
          <div className="w-36">
            <Label>Uzunluk (bayt)</Label>
            <Input value={readLength} onChange={(e) => setReadLength(e.target.value)} placeholder="4096" disabled={busy !== ""} />
          </div>
          <Button onClick={() => void runRead()} disabled={busy !== "" || !isConnected}>
            {busy === "read" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Download className="h-4 w-4" aria-hidden />}
            Oku ve .bin indir
          </Button>
          {!isConnected ? <span className="pb-2 text-xs text-faint">Önce karta bağlan.</span> : null}
        </div>
      ) : null}

      {hasWrite ? (
        <div className="mb-3 flex flex-wrap items-end gap-3 border-t border-border pt-3">
          <div className="min-w-56">
            <Label>.bin dosyası</Label>
            <input
              type="file"
              data-testid="flash-write-file"
              onChange={(e) => setWriteFile(e.target.files?.[0] ?? null)}
              disabled={busy !== ""}
              className="block w-full text-xs text-muted file:mr-2 file:rounded-md file:border file:border-border file:bg-inset file:px-2 file:py-1.5 file:text-xs file:text-text"
            />
          </div>
          <div className="w-36">
            <Label>Hedef adres</Label>
            <Input value={writeAddress} onChange={(e) => setWriteAddress(e.target.value)} placeholder="0x0" disabled={busy !== ""} />
          </div>
          <label className="flex items-center gap-1.5 pb-2 text-xs text-muted">
            <input type="checkbox" checked={verifyAfterWrite} onChange={(e) => setVerifyAfterWrite(e.target.checked)} disabled={busy !== ""} />
            yazım sonrası geri okuyup doğrula
          </label>
          <Button variant="outline" onClick={() => void runWrite()} disabled={busy !== "" || !writeFile || !isConnected} className="border-warn/50 text-warn">
            {busy === "write" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Upload className="h-4 w-4" aria-hidden />}
            Dosyayı flash'a yaz
          </Button>
        </div>
      ) : null}

      {progress ? (
        <div className="mb-2">
          <div className="mb-1 flex items-center justify-between text-[11px] text-muted">
            <span>
              {progress.label}: {progress.done}/{progress.total} bayt ({percent}%)
              {etaSeconds != null ? ` · kalan ~${Math.ceil(etaSeconds)} sn` : ""}
            </span>
            <button type="button" onClick={() => { cancelRef.current = true; }} className="text-danger hover:underline">
              İptal
            </button>
          </div>
          <div className="h-1.5 overflow-hidden rounded bg-bg">
            <div className="h-full bg-accent transition-all" style={{ width: `${percent}%` }} />
          </div>
        </div>
      ) : null}

      {error ? (
        <p className="rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
      ) : null}
      {summary ? (
        <p className={cn("rounded border border-ok/30 bg-ok/10 p-2 text-[11px] text-ok")} data-testid="flash-transfer-summary">
          {summary}
        </p>
      ) : null}
    </div>
  );
}
