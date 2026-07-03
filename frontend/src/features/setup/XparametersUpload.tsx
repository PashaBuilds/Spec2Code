import { useRef, useState } from "react";
import { Upload, FileCode, FileArchive, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";
import { Badge, Button, Card, Input } from "@/components/ui";
import { VisualBackdrop } from "@/components/visuals";
import type { PlatformId, XsaParseResult } from "@/lib/types";

type SourceMode = "xsa" | "xparameters";

export default function XparametersUpload() {
  const project = useStore((s) => s.project);
  const applyParse = useStore((s) => s.applyParse);
  const setProject = useStore((s) => s.setProject);
  const setStep = useStore((s) => s.setStep);
  const [mode, setMode] = useState<SourceMode>(
    () => (localStorage.getItem("spec2code.designSource") === "xparameters" ? "xparameters" : "xsa"),
  );
  const [text, setText] = useState("");
  const [xsaPath, setXsaPath] = useState(() => localStorage.getItem("spec2code.xsaPath") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [detected, setDetected] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const xsaFileRef = useRef<HTMLInputElement>(null);

  function switchMode(next: SourceMode) {
    setMode(next);
    setError(null);
    setCount(null);
    setDetected(null);
    localStorage.setItem("spec2code.designSource", next);
  }

  function applyXsaResult(res: XsaParseResult) {
    // Platform ve hedef çekirdek XSA'dan gelir; Vitis adımı da aynı dosyayı
    // kullansın diye yol paylaşılan anahtara yazılır.
    setProject({
      platform: res.platform as PlatformId,
      target_core: res.cores[0]?.id ?? project.target_core,
    });
    applyParse(res);
    localStorage.setItem("spec2code.xsaPath", res.xsa_path);
    setXsaPath(res.xsa_path);
    setCount(res.controllers.length);
    setDetected(res.platform);
    setStep("schematic");
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) setText(await f.text());
  }

  async function onXsaFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setError(null);
    try {
      applyXsaResult(await api.uploadXsa(f));
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setBusy(false);
      if (xsaFileRef.current) xsaFileRef.current.value = "";
    }
  }

  async function parseXsaFromPath() {
    if (!xsaPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      applyXsaResult(await api.parseXsaPath(xsaPath.trim()));
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setBusy(false);
    }
  }

  async function parse() {
    setBusy(true);
    setError(null);
    try {
      const res = await api.parseXparameters(text, project.platform);
      applyParse(res);
      setCount(res.controllers.length);
      setStep("schematic");
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="relative flex flex-col overflow-hidden p-5">
      <VisualBackdrop asset="setup" opacity={0.2} position="right center" mask="side" />
      <div className="relative z-10 flex min-h-0 flex-1 flex-col">
        <h2 className="mb-1 text-sm font-semibold text-text">Donanım tasarımı</h2>
        <p className="mb-3 text-xs text-faint">
          Tek .xsa dosyası yeter: platform ve denetleyiciler otomatik algılanır, Vitis adımı aynı
          dosyayı kullanır. İstersen klasik xparameters.h yolu da duruyor.
        </p>

        <div className="mb-3 grid grid-cols-2 gap-1 rounded-md border border-border bg-inset p-1">
          {(["xsa", "xparameters"] as const).map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => switchMode(option)}
              className={cn(
                "rounded px-2 py-1 font-mono text-[11px] font-semibold uppercase transition-colors",
                mode === option ? "bg-accent-dim text-accent" : "text-muted hover:text-text",
              )}
            >
              {option === "xsa" ? ".xsa (tek dosya)" : "xparameters.h"}
            </button>
          ))}
        </div>

        {mode === "xsa" ? (
          <>
            <div className="mb-3 flex items-center gap-2">
              <input ref={xsaFileRef} type="file" accept=".xsa" onChange={onXsaFile} className="hidden" />
              <Button variant="outline" size="sm" onClick={() => xsaFileRef.current?.click()} disabled={busy}>
                <Upload className="h-4 w-4" /> .xsa seç
              </Button>
              {detected && <Badge tone="accent">{detected}</Badge>}
              {count !== null && <Badge tone="ok">{count} controllers</Badge>}
            </div>
            <div className="flex items-center gap-2">
              <Input
                value={xsaPath}
                onChange={(e) => setXsaPath(e.target.value)}
                placeholder="...veya tam yol: D:\\proje\\board.xsa"
                className="font-mono text-xs"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void parseXsaFromPath();
                }}
              />
              <Button onClick={() => void parseXsaFromPath()} disabled={busy || !xsaPath.trim()}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileArchive className="h-4 w-4" />}
                Şemayı kur
              </Button>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-faint">
              XSA içindeki hardware handoff (.hwh) okunur: PS çevre birimleri, PL IP&apos;leri ve adres
              haritası şematiğe dökülür; tanınmayan custom IP&apos;ler ayrıca listelenir. Dosya yolu Vitis
              workspace adımına otomatik taşınır.
            </p>
          </>
        ) : (
          <>
            <div className="mb-3 flex items-center gap-2">
              <input ref={fileRef} type="file" accept=".h" onChange={onFile} className="hidden" />
              <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
                <Upload className="h-4 w-4" /> Dosya seç
              </Button>
              {count !== null && <Badge tone="ok">{count} controllers</Badge>}
            </div>

            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              spellCheck={false}
              placeholder="...veya yapıştır: #define XPAR_XIICPS_0_BASEADDR 0xFF020000 ..."
              className="h-40 w-full resize-none rounded-md border border-border bg-inset p-3 font-mono text-xs text-text placeholder:text-faint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
            />

            <div className="mt-4 flex items-center gap-2">
              <Button onClick={parse} disabled={busy || !text.trim()}>
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCode className="h-4 w-4" />}
                Parse &amp; build schematic
              </Button>
            </div>
          </>
        )}

        {error && <div className="mt-2 text-xs text-danger">{error}</div>}
      </div>
    </Card>
  );
}
