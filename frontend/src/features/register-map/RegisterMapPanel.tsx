import { useEffect, useMemo, useRef, useState } from "react";
import { Cpu, Download, FileCode2, FileSpreadsheet, FileUp, FilePlus2, Loader2, Radio, RefreshCw, Save, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { useBoardConnection } from "@/store/connection";
import { cn } from "@/lib/utils";

/** Register Map editörü (Spec2Code içi ikiz): sayısal ekipten gelen register
 * haritasını düzenle, self-contained HTML olarak paylaş, JSON olarak sakla,
 * .h/.c C kodu üret. Register genişliği offset'lerden çıkarılır (sabit 4 bayt
 * değil); skaler/bitfield ayrımı alanlardan otomatik, canlı rozette gösterilir.
 * Veri modeli JSON; self-contained HTML editör aynı şemayı paylaşır. */

interface RegField { name: string; bits: string; description?: string }
interface Register { name: string; offset: string; reset: string; reserved?: boolean; description?: string; fields?: RegField[] }
interface RegMap { name: string; base_address: string; description?: string; registers: Register[] }
interface RegDoc { version?: number; maps: RegMap[] }

function parseInt0(v: string): number { const s = (v || "").trim();
  return /^0[xX][0-9a-fA-F]+$/.test(s) ? parseInt(s, 16) : (/^\d+$/.test(s) ? parseInt(s, 10) : NaN); }
function bitSpan(bits: string): [number, number] | null {
  const m = /^(\d+)(?::(\d+))?$/.exec((bits || "").trim()); if (!m) return null;
  const a = +m[1]; const b = m[2] !== undefined ? +m[2] : +m[1]; return a >= b ? [a, b] : null; }
const ident = (s: string) => /^[A-Za-z_]\w*$/.test(s || "");

// Binary <-> base64 (Excel dosyalari base64 olarak backend'e gider/gelir).
function arrayBufferToBase64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf); let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}
function base64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64); const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}
function downloadBytes(name: string, bytes: Uint8Array, mime: string) {
  const url = URL.createObjectURL(new Blob([bytes as BlobPart], { type: mime }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}

// --- Genişlik / tip çıkarımı (backend register_map.py ile birebir) --------- //
function rawType(width: number): { c: string; prefix: string } | null {
  const map: Record<number, { c: string; prefix: string }> = {
    1: { c: "unsigned char", prefix: "uc" }, 2: { c: "unsigned short", prefix: "us" },
    4: { c: "unsigned int", prefix: "ui" }, 8: { c: "unsigned long long", prefix: "ull" },
  };
  return map[width] || null;
}
function highestBit(reg: Register): number {
  let hb = -1; (reg.fields || []).forEach((f) => { const s = bitSpan(f.bits); if (s) hb = Math.max(hb, s[0]); }); return hb;
}
function roundUpWidth(hb: number): number { const n = hb + 1; for (const w of [1, 2, 4, 8]) if (n <= w * 8) return w; return 8; }
function pascal(name: string): string {
  return (name || "").split(/[_\s]+/).filter(Boolean).map((p) => p[0].toUpperCase() + p.slice(1)).join("") || "Map";
}
/** Sıralı register'lar için byte genişlikleri: sonraki offset farkı; son
 * register alanlarından 1/2/4/8'e yuvarlanır (alan yoksa 4). */
function inferWidths(regs: Register[]): number[] {
  const sorted = regs.slice().sort((a, b) => (parseInt0(a.offset) || 0) - (parseInt0(b.offset) || 0));
  return sorted.map((r, i) => {
    const off = parseInt0(r.offset) || 0;
    if (i + 1 < sorted.length) return (parseInt0(sorted[i + 1].offset) || 0) - off;
    const hb = highestBit(r); return hb >= 0 ? roundUpWidth(hb) : 4;
  });
}
function isScalar(reg: Register, width: number): boolean {
  if (reg.reserved) return false;
  const fields = reg.fields || [];
  if (!fields.length) return true;
  if (fields.length === 1) { const s = bitSpan(fields[0].bits); if (s && s[1] === 0 && s[0] === width * 8 - 1) return true; }
  return false;
}
/** Canlı rozet metni: üretilecek C üye tipini gösterir. */
function memberDesc(reg: Register, width: number): string {
  if (reg.reserved) return `${width}B · reserved · ucReserved[]`;
  if (isScalar(reg, width)) { const p = rawType(width)?.prefix || "uc"; return `${width}B · skaler · ${p}${pascal(reg.name)}`; }
  return `${width}B · bitfield · S${pascal(reg.name)}`;
}

export default function RegisterMapPanel() {
  const [doc, setDoc] = useState<RegDoc | null>(null);
  const [activeMap, setActiveMap] = useState(0);
  const [mode, setMode] = useState<"edit" | "live">("edit");
  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<Record<string, string> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // İlk açılışta backend örneğiyle başla (tek doğruluk kaynağı: aynı şema).
  useEffect(() => {
    api.registerMapExample().then((r) => setDoc(r.document as RegDoc)).catch(() => setDoc({ version: 1, maps: [] }));
  }, []);

  const map = doc?.maps[activeMap];

  const localErrors = useMemo(() => validateLocal(doc), [doc]);

  function patch(mutator: (d: RegDoc) => void) {
    setDoc((prev) => { if (!prev) return prev; const next = structuredClone(prev); mutator(next); return next; });
    setPreview(null);
  }

  async function importFile(file: File | undefined) {
    if (!file) return;
    setBusy(true); setErrors([]); setNotice("");
    try {
      if (file.name.endsWith(".xlsx")) {
        const b64 = arrayBufferToBase64(await file.arrayBuffer());
        const res = await api.registerMapImportXlsx(b64);
        setDoc(res.document as RegDoc); setActiveMap(0);
        setNotice(`${file.name} (Excel) yüklendi.`); if (!res.valid) setErrors(res.errors);
      } else if (file.name.endsWith(".json")) {
        const parsed = JSON.parse(await file.text()) as RegDoc;
        const v = await api.registerMapValidate(parsed);
        setDoc(parsed); setActiveMap(0);
        setNotice(`${file.name} yüklendi.`); if (!v.valid) setErrors(v.errors);
      } else {
        const res = await api.registerMapImportHtml(await file.text());
        setDoc(res.document as RegDoc); setActiveMap(0);
        setNotice(`${file.name} içindeki register map yüklendi.`); if (!res.valid) setErrors(res.errors);
      }
    } catch (err) {
      setErrors([err instanceof Error ? err.message : String(err)]);
    } finally {
      setBusy(false); if (fileRef.current) fileRef.current.value = "";
    }
  }

  function download(name: string, content: string, mime: string) {
    const url = URL.createObjectURL(new Blob([content], { type: mime }));
    const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
  }

  async function exportHtml() {
    if (!doc) return;
    setBusy(true); setErrors([]);
    try {
      const res = await api.registerMapExportHtml(doc);
      download((doc.maps[0]?.name || "register_map") + "_map.html", res.html, "text/html");
      setNotice("Self-contained HTML editör indirildi — sayısal ekiple paylaşabilirsin.");
    } catch (err) { setErrors([err instanceof Error ? err.message : String(err)]); }
    finally { setBusy(false); }
  }

  async function exportXlsx() {
    if (!doc) return;
    setBusy(true); setErrors([]);
    try {
      const res = await api.registerMapExportXlsx(doc);
      downloadBytes((doc.maps[0]?.name || "register_map") + "_map.xlsx", base64ToBytes(res.xlsx_base64),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
      setNotice("Excel (katı şablon) indirildi — sayısal ekiple paylaşabilirsin.");
    } catch (err) { setErrors([err instanceof Error ? err.message : String(err)]); }
    finally { setBusy(false); }
  }

  async function generateC() {
    if (!doc) return;
    setBusy(true); setErrors([]);
    try {
      const res = await api.registerMapGenerate(doc);
      setPreview(res.files);
      setNotice(`${Object.keys(res.files).length} dosya üretildi.`);
    } catch (err) { setErrors([err instanceof Error ? err.message : String(err)]); }
    finally { setBusy(false); }
  }

  const downloadExampleHtml = async () => {
    setBusy(true);
    try { const r = await api.registerMapExample(); download("register_map_ornek.html", r.html, "text/html");
      setNotice("Örnek self-contained editör indirildi."); }
    catch (err) { setErrors([err instanceof Error ? err.message : String(err)]); }
    finally { setBusy(false); }
  };

  // Vivado'da üretilen "Register Map Test IP"nin haritasını (adres + register +
  // bitfield) getirir. Adres, Vivado üretimi atadıysa localStorage'dan gelir.
  const loadTestIp = async () => {
    setBusy(true); setErrors([]);
    try {
      const base = (localStorage.getItem("spec2code.regmap.testIpBase") || "").trim();
      const r = await api.registerMapTestIp(base || undefined);
      setDoc(r.document as RegDoc); setActiveMap(0);
      setNotice(base ? `Test IP haritası yüklendi (Vivado'nun atadığı adres: ${base}).` : "Test IP haritası yüklendi (varsayılan adres — Vivado'da IP üretince gerçek adresle gelir).");
    } catch (err) { setErrors([err instanceof Error ? err.message : String(err)]); }
    finally { setBusy(false); }
  };

  if (!doc) return <div className="p-6 text-sm text-muted">Yükleniyor…</div>;

  return (
    <div className="mx-auto max-w-6xl space-y-4">
      <Card className="p-4">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <Cpu className="h-4 w-4 text-accent" aria-hidden />
          <h3 className="text-sm font-semibold text-text">Register Map — struct/union header üretici</h3>
          <span className="text-xs text-faint">memory-mapped donanım bloğu → .h/.c</span>
        </div>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          Sayısal ekipten gelen register haritasını buradan düzenle; register genişliği offset'lerden
          çıkarılır, bit alanları LSB-first, init reset değerlerine eşitler, offset'ler <code>static_assert</code>
          ile mühürlenir. Sayısalcıya paylaşmak için <b>self-contained HTML editör</b> ya da <b>katı
          şablonlu Excel</b> ver — ikisi de aynı şemayı taşır, geri alıp içe aktarabilirsin.
        </p>
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept=".html,.json,.xlsx" className="hidden" onChange={(e) => void importFile(e.target.files?.[0])} />
          <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={busy}><FileUp className="h-4 w-4" /> İçe aktar (HTML/JSON/Excel)</Button>
          <Button size="sm" variant="outline" onClick={() => void exportHtml()} disabled={busy}><Download className="h-4 w-4" /> HTML editör dışa aktar</Button>
          <Button size="sm" variant="outline" onClick={() => void exportXlsx()} disabled={busy}><FileSpreadsheet className="h-4 w-4" /> Excel dışa aktar</Button>
          <Button size="sm" variant="outline" onClick={() => doc && download((doc.maps[0]?.name || "register_map") + ".json", JSON.stringify(doc, null, 2), "application/json")}><Download className="h-4 w-4" /> JSON dışa aktar</Button>
          <Button size="sm" variant="outline" onClick={() => void downloadExampleHtml()} disabled={busy}><FilePlus2 className="h-4 w-4" /> Örnek editör indir</Button>
          <Button size="sm" variant="outline" onClick={() => void loadTestIp()} disabled={busy}><Cpu className="h-4 w-4" /> Test IP haritasını yükle</Button>
          <Button size="sm" onClick={() => void generateC()} disabled={busy || localErrors.length > 0} className="ml-auto">
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCode2 className="h-4 w-4" />} C kodu üret
          </Button>
        </div>
        {notice ? <p className="mt-2 rounded border border-ok/25 bg-ok/10 px-2 py-1.5 text-[11px] text-ok">{notice}</p> : null}
        {(errors.length > 0 || localErrors.length > 0) ? (
          <div className="mt-2 rounded border border-danger/30 bg-danger/10 px-2 py-1.5 text-[11px] text-danger">
            {[...localErrors, ...errors].slice(0, 6).map((e, i) => <div key={i}>{e}</div>)}
            {localErrors.length + errors.length > 6 ? <div>… +{localErrors.length + errors.length - 6}</div> : null}
          </div>
        ) : null}
        <div className="mt-3 flex gap-1 border-t border-border pt-3">
          <Button size="sm" variant={mode === "edit" ? "outline" : "ghost"} onClick={() => setMode("edit")}><Cpu className="h-4 w-4" /> Düzenle / kod üret</Button>
          <Button size="sm" variant={mode === "live" ? "outline" : "ghost"} onClick={() => setMode("live")}><Radio className="h-4 w-4" /> Canlı İzleme</Button>
        </div>
      </Card>

      {mode === "live" ? (
        <LiveMonitor doc={doc} activeMap={activeMap} setActiveMap={setActiveMap} />
      ) : (<>
      <Card className="p-4">
        {/* Map sekmeleri */}
        <div className="mb-3 flex flex-wrap items-center gap-1.5">
          {doc.maps.map((m, i) => (
            <button key={i} onClick={() => setActiveMap(i)}
              className={cn("rounded-md border px-2.5 py-1 font-mono text-xs", i === activeMap ? "border-accent/50 bg-accent/15 text-text" : "border-border bg-inset text-muted hover:text-text")}>
              {m.name || `map${i}`}
            </button>
          ))}
          <Button size="sm" variant="outline" onClick={() => { patch((d) => d.maps.push({ name: `yeni_map${doc.maps.length}`, base_address: "0xA0000000", registers: [] })); setActiveMap(doc.maps.length); }}>
            <FilePlus2 className="h-4 w-4" /> map
          </Button>
          {doc.maps.length > 1 ? (
            <Button size="sm" variant="outline" className="text-danger" onClick={() => { patch((d) => d.maps.splice(activeMap, 1)); setActiveMap(0); }}>
              <Trash2 className="h-4 w-4" /> map sil
            </Button>
          ) : null}
        </div>

        {map ? (
          <>
            <div className="mb-3 grid gap-2 md:grid-cols-3">
              <div className="space-y-1"><Label>Map adı (C tanımlayıcı)</Label>
                <Input className={cn("font-mono text-xs", !ident(map.name) && "border-danger")} value={map.name} onChange={(e) => patch((d) => { d.maps[activeMap].name = e.target.value; })} /></div>
              <div className="space-y-1"><Label>Base adres</Label>
                <Input className={cn("font-mono text-xs", isNaN(parseInt0(map.base_address)) && "border-danger")} value={map.base_address} onChange={(e) => patch((d) => { d.maps[activeMap].base_address = e.target.value; })} /></div>
              <div className="space-y-1"><Label>Açıklama</Label>
                <Input value={map.description || ""} onChange={(e) => patch((d) => { d.maps[activeMap].description = e.target.value; })} /></div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-xs">
                <thead>
                  <tr className="text-left text-muted">
                    <th className="border-b border-border p-1.5">Offset</th>
                    <th className="border-b border-border p-1.5">İsim</th>
                    <th className="border-b border-border p-1.5">Reset</th>
                    <th className="border-b border-border p-1.5">Rsvd</th>
                    <th className="border-b border-border p-1.5">Bit alanları (LSB-first)</th>
                    <th className="border-b border-border p-1.5" />
                  </tr>
                </thead>
                <tbody>
                  {(() => {
                    const sorted = map.registers.slice().sort((a, b) => (parseInt0(a.offset) || 0) - (parseInt0(b.offset) || 0));
                    const widths = inferWidths(map.registers);
                    return sorted.map((reg, si) => {
                    const ri = map.registers.indexOf(reg);
                    const width = widths[si];
                    return (
                      <tr key={ri} className="align-top">
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-20 font-mono text-xs", isNaN(parseInt0(reg.offset)) && "border-danger")} value={reg.offset} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].offset = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-32 font-mono text-xs", !ident(reg.name) && "border-danger")} value={reg.name} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].name = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-32 font-mono text-xs", isNaN(parseInt0(reg.reset)) && "border-danger")} value={reg.reset} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].reset = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5 text-center"><input type="checkbox" checked={!!reg.reserved} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].reserved = e.target.checked; })} className="accent-[var(--accent)]" /></td>
                        <td className="border-b border-border p-1.5">
                          <div className="mb-1 font-mono text-[10px] text-accent/80">{memberDesc(reg, width)}</div>
                          {reg.reserved ? <span className="text-faint">reserved — {width} bayt yer tutar (offset'ten çıkarıldı)</span> : (
                            <div className="space-y-1">
                              <BitStrip fields={reg.fields || []} width={width} />
                              {(reg.fields || []).map((f, fi) => (
                                <div key={fi} className="flex flex-wrap items-center gap-1">
                                  <Input className={cn("h-6 w-28 font-mono text-[11px]", !ident(f.name) && "border-danger")} value={f.name} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].fields![fi].name = e.target.value; })} />
                                  <Input className={cn("h-6 w-16 font-mono text-[11px]", !bitSpan(f.bits) && "border-danger")} value={f.bits} placeholder="15:8" onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].fields![fi].bits = e.target.value; })} />
                                  <Input className="h-6 min-w-24 flex-1 text-[11px]" placeholder="açıklama" value={f.description || ""} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].fields![fi].description = e.target.value; })} />
                                  <button className="text-danger" onClick={() => patch((d) => { d.maps[activeMap].registers[ri].fields!.splice(fi, 1); })}>×</button>
                                </div>
                              ))}
                              <Button size="sm" variant="outline" className="h-6 text-[11px]" onClick={() => patch((d) => { const r = d.maps[activeMap].registers[ri]; r.fields = r.fields || []; r.fields.push({ name: "YENI", bits: "0", description: "" }); })}>+ bit alanı</Button>
                            </div>
                          )}
                        </td>
                        <td className="border-b border-border p-1.5"><button className="text-danger" onClick={() => patch((d) => { d.maps[activeMap].registers.splice(ri, 1); })}><Trash2 className="h-3.5 w-3.5" /></button></td>
                      </tr>
                    );
                    });
                  })()}
                </tbody>
              </table>
            </div>
            <Button size="sm" variant="outline" className="mt-2" onClick={() => patch((d) => {
              const regs = d.maps[activeMap].registers;
              const maxOff = regs.reduce((a, r) => Math.max(a, parseInt0(r.offset) || 0), -4);
              regs.push({ name: "YENI_REG", offset: "0x" + ((maxOff + 4) >>> 0).toString(16).toUpperCase().padStart(2, "0"), reset: "0x00000000", reserved: false, fields: [] });
            })}><FilePlus2 className="h-4 w-4" /> Register ekle</Button>
          </>
        ) : null}
      </Card>

      {preview ? (
        <Card className="p-0">
          <div className="flex items-center gap-2 border-b border-border px-4 py-2">
            <Save className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-sm font-semibold text-text">Üretilen kod</span>
            <Badge tone="ok">{Object.keys(preview).length} dosya</Badge>
          </div>
          <div className="space-y-3 p-4">
            {Object.entries(preview).map(([name, content]) => (
              <div key={name}>
                <div className="mb-1 flex items-center gap-2">
                  <code className="text-xs text-accent">{name}</code>
                  <Button size="sm" variant="outline" className="h-6 text-[11px]" onClick={() => download(name, content, "text/plain")}><Download className="h-3.5 w-3.5" /> indir</Button>
                </div>
                <pre className="max-h-72 overflow-auto rounded-md border border-border bg-inset p-3 font-mono text-[11px] leading-relaxed text-muted">{content}</pre>
              </div>
            ))}
          </div>
        </Card>
      ) : null}
      </>)}
    </div>
  );
}

/** Bir register'ın ham değerini bit alanlarına çözer (istemci tarafı). */
function decodeFields(reg: Register, rawv: number): { name: string; bits: string; value: number }[] {
  return (reg.fields || []).map((f) => {
    const s = bitSpan(f.bits);
    if (!s) return { name: f.name, bits: f.bits, value: 0 };
    const n = s[0] - s[1] + 1;
    const mask = n >= 32 ? 0xffffffff : (1 << n) - 1;
    return { name: f.name, bits: s[0] === s[1] ? `${s[0]}` : `${s[0]}:${s[1]}`, value: ((rawv >>> s[1]) & mask) >>> 0 };
  });
}
function hexPad(v: number, width: number): string {
  const digits = width <= 4 ? width * 2 : 8;
  return "0x" + (v >>> 0).toString(16).toUpperCase().padStart(digits, "0");
}

/** Register Map "Canlı İzleme": hangi bağlantı olursa olsun (seri/JTAG-CoreSight/
 * TCP) Test Bench ajanına `mem_read`/`mem_write` komutu gönderir — ajan hedefte
 * `Xil_In32`/`Xil_Out32` ile register'ın base+offset adresini doğrudan okur/yazar.
 * Firmware'de UART/Serve() kurmaya gerek yok. Bitfield maskelemesi istemcide. */
function LiveMonitor({ doc, activeMap, setActiveMap }: { doc: RegDoc; activeMap: number; setActiveMap: (i: number) => void }) {
  const board = useBoardConnection();
  const cmdId = useRef(1);
  const [values, setValues] = useState<Record<string, number>>({});
  const [wr, setWr] = useState<Record<string, string>>({});
  const [log, setLog] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const map = doc.maps[activeMap];
  const base = map ? (parseInt0(map.base_address) || 0) : 0;
  const widths = useMemo(() => (map ? inferWidths(map.registers) : []), [map]);
  const sorted = useMemo(
    () => (map ? map.registers.slice().sort((a, b) => (parseInt0(a.offset) || 0) - (parseInt0(b.offset) || 0)) : []),
    [map],
  );

  function pushLog(...lines: string[]) { setLog((prev) => [...lines, ...prev].slice(0, 300)); }

  async function memRead(addr: number, width: number): Promise<number | null> {
    const resp = await api.testbenchCommand({
      host: "session", port: 0, device: "regmap", operation: "mem_read",
      address: addr, length: width, command_id: cmdId.current++, session_id: board.sessionId, timeout_s: 4,
    });
    pushLog(`rd 0x${(addr >>> 0).toString(16).toUpperCase()} → ${resp.parsed.value ?? resp.parsed.message ?? "?"}`);
    const v = parseInt0(resp.parsed.value || "");
    return isNaN(v) ? null : v;
  }

  async function memWrite(addr: number, width: number, value: number): Promise<number | null> {
    const resp = await api.testbenchCommand({
      host: "session", port: 0, device: "regmap", operation: "mem_write",
      address: addr, length: width, value: value >>> 0, command_id: cmdId.current++, session_id: board.sessionId, timeout_s: 4,
    });
    pushLog(`wr 0x${(addr >>> 0).toString(16).toUpperCase()} = 0x${(value >>> 0).toString(16).toUpperCase()} → ${resp.parsed.value ?? resp.parsed.message ?? "?"}`);
    const v = parseInt0(resp.parsed.value || "");
    return isNaN(v) ? null : v;
  }

  const addrOf = (reg: Register) => (base + (parseInt0(reg.offset) || 0)) >>> 0;

  async function readOne(reg: Register, width: number) {
    if (!board.connected || reg.reserved) return;
    setBusy(true);
    try { const v = await memRead(addrOf(reg), width); if (v !== null) setValues((p) => ({ ...p, [reg.name]: v })); }
    catch (e) { pushLog("HATA: " + (e instanceof Error ? e.message : String(e))); }
    finally { setBusy(false); }
  }

  async function readAll() {
    if (!board.connected || !map) return;
    setBusy(true);
    try {
      for (let i = 0; i < sorted.length; i++) {
        const reg = sorted[i];
        if (reg.reserved) continue;
        const v = await memRead(addrOf(reg), widths[i]);
        if (v !== null) setValues((p) => ({ ...p, [reg.name]: v }));
      }
    } catch (e) { pushLog("HATA: " + (e instanceof Error ? e.message : String(e))); }
    finally { setBusy(false); }
  }

  async function writeRaw(reg: Register, width: number) {
    if (!board.connected) return;
    const v = parseInt0((wr[reg.name] || "").trim());
    if (isNaN(v)) return;
    setBusy(true);
    try { const rb = await memWrite(addrOf(reg), width, v); if (rb !== null) setValues((p) => ({ ...p, [reg.name]: rb })); }
    catch (e) { pushLog("HATA: " + (e instanceof Error ? e.message : String(e))); }
    finally { setBusy(false); }
  }

  async function writeField(reg: Register, width: number, field: RegField) {
    if (!board.connected) return;
    const s = bitSpan(field.bits);
    const fv = parseInt0((wr[`${reg.name}.${field.name}`] || "").trim());
    if (!s || isNaN(fv)) return;
    const n = s[0] - s[1] + 1;
    const mask = (((n >= 32 ? 0xffffffff : (1 << n) - 1) >>> 0) << s[1]) >>> 0;
    setBusy(true);
    try {
      const cur = (await memRead(addrOf(reg), width)) ?? 0;
      const next = (((cur & ~mask) >>> 0) | ((fv << s[1]) & mask)) >>> 0;
      const rb = await memWrite(addrOf(reg), width, next);
      if (rb !== null) setValues((p) => ({ ...p, [reg.name]: rb }));
    } catch (e) { pushLog("HATA: " + (e instanceof Error ? e.message : String(e))); }
    finally { setBusy(false); }
  }

  if (!map) return <Card className="p-4 text-sm text-muted">Map yok.</Card>;

  return (
    <Card className="p-4">
      {/* Map sekmeleri */}
      {doc.maps.length > 1 ? (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {doc.maps.map((m, i) => (
            <button key={i} onClick={() => setActiveMap(i)}
              className={cn("rounded-md border px-2.5 py-1 font-mono text-xs", i === activeMap ? "border-accent/50 bg-accent/15 text-text" : "border-border bg-inset text-muted hover:text-text")}>
              {m.name || `map${i}`}
            </button>
          ))}
        </div>
      ) : null}

      {/* Bağlantı durumu (transport-agnostik: hangi bağlantıysan onu kullanır) */}
      <div className="mb-3 rounded-md border border-border bg-inset p-2.5 text-xs">
        <div className="flex flex-wrap items-center gap-2">
          {board.connected ? (
            <>
              <span className="inline-flex items-center gap-1 text-ok"><span className="h-2 w-2 rounded-full bg-ok" /> Bağlı</span>
              <span className="text-muted">({board.transport})</span>
              <Button size="sm" variant="outline" className="ml-auto h-6 text-[11px]" onClick={() => void board.disconnect()}>Kes</Button>
            </>
          ) : (
            <>
              <span className="text-faint">Bağlı değil ({board.transport})</span>
              <Button size="sm" className="ml-auto h-6 text-[11px]" onClick={() => { setBusy(true); void board.connect().finally(() => setBusy(false)); }} disabled={busy}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Radio className="h-4 w-4" />} Bağlan
              </Button>
              {board.lastError ? <span className="w-full text-danger">{board.lastError}</span> : null}
            </>
          )}
        </div>
        <p className="mt-1 text-[10px] leading-relaxed text-faint">
          Register'lar hedefte <code>Xil_In32</code>/<code>Xil_Out32</code> ile <code>base+offset</code> adresinden doğrudan okunur/yazılır — hangi bağlantı (seri/JTAG/TCP) olursa olsun aynı Test Bench ajanı üzerinden. Bağlantı türü Test Bench/Board ayarlarından. Hedefte Spec2Code Test Bench ajanı koşmalı (üretilen workspace'i yeniden derleyip yükle).
        </p>
      </div>

      <div className="mb-3 flex flex-wrap gap-2">
        <Button size="sm" variant="outline" onClick={() => void readAll()} disabled={busy || !board.connected}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />} Hepsini oku
        </Button>
        <span className="self-center text-[10px] text-faint">base: <code className="text-muted">0x{(base >>> 0).toString(16).toUpperCase()}</code></span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-xs">
          <thead>
            <tr className="text-left text-muted">
              <th className="border-b border-border p-1.5">Register</th>
              <th className="border-b border-border p-1.5">Adres</th>
              <th className="border-b border-border p-1.5">Değer</th>
              <th className="border-b border-border p-1.5">Çözüm / yaz</th>
              <th className="border-b border-border p-1.5" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((reg, si) => {
              const width = widths[si];
              const rawv = values[reg.name];
              const has = rawv !== undefined;
              return (
                <tr key={reg.name + si} className="align-top">
                  <td className="border-b border-border p-1.5 font-mono">{reg.name}<div className="text-[10px] text-faint">{memberDesc(reg, width)}</div></td>
                  <td className="border-b border-border p-1.5 font-mono text-muted">0x{addrOf(reg).toString(16).toUpperCase()}</td>
                  <td className="border-b border-border p-1.5 font-mono">{has ? <span className="text-accent">{hexPad(rawv, width)}</span> : <span className="text-faint">—</span>}</td>
                  <td className="border-b border-border p-1.5">
                    {reg.reserved ? <span className="text-faint">reserved</span> : (reg.fields && reg.fields.length > 0) ? (
                      <div className="space-y-0.5">
                        {(has ? decodeFields(reg, rawv) : (reg.fields || []).map((f) => ({ name: f.name, bits: f.bits, value: NaN }))).map((f, fi) => {
                          const fdef = (reg.fields || [])[fi];
                          return (
                            <div key={fi} className="flex items-center gap-1.5 font-mono text-[11px]">
                              <span className="w-28 truncate text-text">{f.name}</span>
                              <span className="w-12 text-faint">[{f.bits}]</span>
                              <span className={cn("w-16", isNaN(f.value) ? "text-faint" : "text-ok")}>{isNaN(f.value) ? "—" : "0x" + f.value.toString(16).toUpperCase()}</span>
                              <Input className="h-5 w-16 font-mono text-[10px]" placeholder="yaz" value={wr[`${reg.name}.${f.name}`] || ""} onChange={(e) => setWr((p) => ({ ...p, [`${reg.name}.${f.name}`]: e.target.value }))} />
                              <button className="text-[10px] text-accent hover:underline disabled:text-faint" onClick={() => void writeField(reg, width, fdef)} disabled={!board.connected}>yaz</button>
                            </div>
                          );
                        })}
                        <div className="flex items-center gap-1.5 pt-0.5 font-mono text-[11px]">
                          <span className="w-28 text-faint">ham değer</span>
                          <Input className="h-5 w-24 font-mono text-[10px]" placeholder="0x…" value={wr[reg.name] || ""} onChange={(e) => setWr((p) => ({ ...p, [reg.name]: e.target.value }))} />
                          <button className="text-[10px] text-accent hover:underline disabled:text-faint" onClick={() => void writeRaw(reg, width)} disabled={!board.connected}>yaz</button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 font-mono text-[11px]">
                        <span className="text-faint">skaler</span>
                        <Input className="h-5 w-24 font-mono text-[10px]" placeholder="0x…" value={wr[reg.name] || ""} onChange={(e) => setWr((p) => ({ ...p, [reg.name]: e.target.value }))} />
                        <button className="text-[10px] text-accent hover:underline disabled:text-faint" onClick={() => void writeRaw(reg, width)} disabled={!board.connected}>yaz</button>
                      </div>
                    )}
                  </td>
                  <td className="border-b border-border p-1.5">
                    <Button size="sm" variant="outline" className="h-6 text-[11px]" onClick={() => void readOne(reg, width)} disabled={busy || !board.connected || reg.reserved}>oku</Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="mt-3">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-xs text-muted">Etkinlik günlüğü</span>
          <span className="text-[10px] text-faint">okuma/yazma komutları ve cevapları</span>
          {log.length > 0 ? <Button size="sm" variant="ghost" className="ml-auto h-5 text-[10px]" onClick={() => setLog([])}>temizle</Button> : null}
        </div>
        <pre className="max-h-48 min-h-16 overflow-auto rounded-md border border-border bg-inset p-2 font-mono text-[10px] leading-relaxed text-muted">
          {log.length > 0 ? log.join("\n") : (board.connected ? "Bir register'da 'oku' / 'Hepsini oku' — komut ve cevaplar burada akar." : "Önce bağlan (Test Bench/Board ayarlarındaki bağlantı türüyle); bağlı değilken butonlar pasiftir.")}
        </pre>
      </div>
    </Card>
  );
}

function BitStrip({ fields, width }: { fields: RegField[]; width: number }) {
  const bits = Math.min(64, Math.max(8, width * 8));
  const used = new Array(bits).fill(0);
  fields.forEach((f) => { const s = bitSpan(f.bits); if (s) for (let b = s[1]; b <= s[0] && b < bits; b++) used[b]++; });
  return (
    <div className="flex flex-wrap gap-0.5">
      {Array.from({ length: bits }, (_, i) => bits - 1 - i).map((b) => (
        <span key={b} title={`bit ${b}`}
          className={cn("h-3.5 w-3.5 rounded-[2px] border text-center text-[7px] leading-[13px]",
            used[b] === 0 ? "border-border text-faint" : used[b] > 1 ? "border-danger bg-danger/50" : "border-accent bg-accent/30 text-text")}>
          {b % 4 === 0 ? b : ""}
        </span>
      ))}
    </div>
  );
}

function validateLocal(doc: RegDoc | null): string[] {
  if (!doc) return [];
  const errs: string[] = [];
  doc.maps.forEach((m) => {
    if (!ident(m.name)) errs.push(`map adı geçersiz: ${m.name}`);
    if (isNaN(parseInt0(m.base_address))) errs.push(`${m.name}: base adres geçersiz`);
    const offs: Record<number, string> = {};
    m.registers.forEach((r) => {
      const o = parseInt0(r.offset);
      if (isNaN(o) || o < 0) errs.push(`${m.name}.${r.name}: offset geçersiz`);
      else if (offs[o] !== undefined) errs.push(`${m.name}: offset ${r.offset} çakışıyor (${offs[o]} & ${r.name})`);
      else offs[o] = r.name;
      if (isNaN(parseInt0(r.reset))) errs.push(`${m.name}.${r.name}: reset geçersiz`);
      if (!r.reserved) { let mask = 0; (r.fields || []).forEach((f) => { const s = bitSpan(f.bits);
        if (!s) { errs.push(`${m.name}.${r.name}.${f.name}: bit biçimi hatalı`); return; }
        const fm = ((1 << (s[0] - s[1] + 1)) - 1) << s[1]; if (mask & fm) errs.push(`${m.name}.${r.name}.${f.name}: bit çakışması`); mask |= fm; }); }
    });
    // Genişlik çıkarımı sonrası: alan genişliğe sığmalı, bit alanlı register
    // 1/2/4/8 byte olmalı (backend ile birebir).
    const sorted = m.registers.slice().sort((a, b) => (parseInt0(a.offset) || 0) - (parseInt0(b.offset) || 0));
    const widths = inferWidths(m.registers);
    sorted.forEach((r, i) => {
      const w = widths[i];
      if (w < 1) { errs.push(`${m.name}.${r.name}: offset'ler kesin artan olmalı`); return; }
      if (r.reserved) return;
      const hb = highestBit(r);
      if (hb >= 0 && hb >= w * 8) errs.push(`${m.name}.${r.name}: en yüksek bit ${hb}, genişlik ${w} byte — alan sığmıyor`);
      if ((r.fields || []).length && !isScalar(r, w) && !rawType(w)) errs.push(`${m.name}.${r.name}: bit alanlı register genişliği 1/2/4/8 byte olmalı`);
      const rv = parseInt0(r.reset);
      if (!isNaN(rv) && w >= 1 && w <= 4 && rv >= Math.pow(2, w * 8)) errs.push(`${m.name}.${r.name}: reset genişliğe sığmıyor`);
    });
  });
  return errs;
}
