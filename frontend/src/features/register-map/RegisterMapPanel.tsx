import { useEffect, useMemo, useRef, useState } from "react";
import { Cpu, Download, FileCode2, FileUp, FilePlus2, Loader2, Save, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import { cn } from "@/lib/utils";

/** Register Map editörü (Spec2Code içi ikiz): sayısal ekipten gelen register
 * haritasını (base + 4 baytlık register'lar + LSB-first bitfield + reset) tek
 * yerde düzenle, self-contained HTML olarak paylaş, JSON olarak sakla, .h/.c C
 * kodu üret. Veri modeli JSON'dur; self-contained HTML editör aynı şemayı
 * paylaşır (backend export/import). */

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

export default function RegisterMapPanel() {
  const [doc, setDoc] = useState<RegDoc | null>(null);
  const [activeMap, setActiveMap] = useState(0);
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
      const text = await file.text();
      if (file.name.endsWith(".json")) {
        const parsed = JSON.parse(text) as RegDoc;
        const v = await api.registerMapValidate(parsed);
        setDoc(parsed); setActiveMap(0);
        setNotice(`${file.name} yüklendi.`); if (!v.valid) setErrors(v.errors);
      } else {
        const res = await api.registerMapImportHtml(text);
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
          Sayısal ekipten gelen register haritasını buradan düzenle; her register 4 bayt, bit alanları
          LSB-first, init reset değerlerine eşitler, offset'ler <code>static_assert</code> ile mühürlenir.
          Sayısalcıya paylaşmak için <b>self-contained HTML editör</b> ver — Spec2Code'a gerek kalmadan
          tarayıcıda açıp doldurur, "Kaydet" ile aynı dosyaya yazar (Chrome/Edge), çoklu kullanıcıda
          register-düzeyinde birleştirme yapar.
        </p>
        <div className="flex flex-wrap gap-2">
          <input ref={fileRef} type="file" accept=".html,.json" className="hidden" onChange={(e) => void importFile(e.target.files?.[0])} />
          <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} disabled={busy}><FileUp className="h-4 w-4" /> HTML/JSON içe aktar</Button>
          <Button size="sm" variant="outline" onClick={() => void exportHtml()} disabled={busy}><Download className="h-4 w-4" /> HTML editör dışa aktar</Button>
          <Button size="sm" variant="outline" onClick={() => doc && download((doc.maps[0]?.name || "register_map") + ".json", JSON.stringify(doc, null, 2), "application/json")}><Download className="h-4 w-4" /> JSON dışa aktar</Button>
          <Button size="sm" variant="outline" onClick={() => void downloadExampleHtml()} disabled={busy}><FilePlus2 className="h-4 w-4" /> Örnek editör indir</Button>
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
      </Card>

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
                  {map.registers.slice().sort((a, b) => (parseInt0(a.offset) || 0) - (parseInt0(b.offset) || 0)).map((reg) => {
                    const ri = map.registers.indexOf(reg);
                    return (
                      <tr key={ri} className="align-top">
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-20 font-mono text-xs", (parseInt0(reg.offset) % 4 !== 0) && "border-danger")} value={reg.offset} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].offset = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-32 font-mono text-xs", !ident(reg.name) && "border-danger")} value={reg.name} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].name = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5"><Input className={cn("h-7 w-24 font-mono text-xs", isNaN(parseInt0(reg.reset)) && "border-danger")} value={reg.reset} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].reset = e.target.value; })} /></td>
                        <td className="border-b border-border p-1.5 text-center"><input type="checkbox" checked={!!reg.reserved} onChange={(e) => patch((d) => { d.maps[activeMap].registers[ri].reserved = e.target.checked; })} className="accent-[var(--accent)]" /></td>
                        <td className="border-b border-border p-1.5">
                          {reg.reserved ? <span className="text-faint">reserved — 4 bayt yer tutar</span> : (
                            <div className="space-y-1">
                              <BitStrip fields={reg.fields || []} />
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
                  })}
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
    </div>
  );
}

function BitStrip({ fields }: { fields: RegField[] }) {
  const used = new Array(32).fill(0);
  fields.forEach((f) => { const s = bitSpan(f.bits); if (s) for (let b = s[1]; b <= s[0] && b < 32; b++) used[b]++; });
  return (
    <div className="flex flex-wrap gap-0.5">
      {Array.from({ length: 32 }, (_, i) => 31 - i).map((b) => (
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
      if (isNaN(o) || o % 4 !== 0) errs.push(`${m.name}.${r.name}: offset 4'ün katı olmalı`);
      else if (offs[o]) errs.push(`${m.name}: offset ${r.offset} çakışıyor (${offs[o]} & ${r.name})`);
      else offs[o] = r.name;
      if (isNaN(parseInt0(r.reset))) errs.push(`${m.name}.${r.name}: reset geçersiz`);
      if (!r.reserved) { let mask = 0; (r.fields || []).forEach((f) => { const s = bitSpan(f.bits);
        if (!s) { errs.push(`${m.name}.${r.name}.${f.name}: bit biçimi hatalı`); return; }
        const fm = ((1 << (s[0] - s[1] + 1)) - 1) << s[1]; if (mask & fm) errs.push(`${m.name}.${r.name}.${f.name}: bit çakışması`); mask |= fm; }); }
    });
  });
  return errs;
}
