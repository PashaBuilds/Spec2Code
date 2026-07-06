import { useRef, useState } from "react";
import { Upload, FileArchive, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { Badge, Button, Card, Input } from "@/components/ui";
import { VisualBackdrop } from "@/components/visuals";
import type { PlatformId, XsaParseResult } from "@/lib/types";

/** Donanım tasarımı girişi: tek .xsa (veya eski SDK akışının .hdf'i).
 * xparameters.h yükleme desteği kaldırıldı — XSA/HDF içindeki .hwh aynı
 * bilgiyi (ve fazlasını) taşır; platform, çekirdek ve denetleyiciler otomatik
 * algılanır. Dosya yolu Vitis workspace adımına otomatik taşınır (paylaşılan
 * anahtar: spec2code.xsaPath). */
export default function DesignUpload() {
  const project = useStore((s) => s.project);
  const applyParse = useStore((s) => s.applyParse);
  const setProject = useStore((s) => s.setProject);
  const setStep = useStore((s) => s.setStep);
  const [designPath, setDesignPath] = useState(() => localStorage.getItem("spec2code.xsaPath") ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const [detected, setDetected] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function applyResult(res: XsaParseResult) {
    // Platform ve hedef çekirdek dosyadan gelir; Vitis adımı da aynı dosyayı
    // kullansın diye yol paylaşılan anahtara yazılır.
    setProject({
      platform: res.platform as PlatformId,
      target_core: res.cores[0]?.id ?? project.target_core,
    });
    applyParse(res);
    localStorage.setItem("spec2code.xsaPath", res.xsa_path);
    setDesignPath(res.xsa_path);
    setCount(res.controllers.length);
    setDetected(res.platform);
    setStep("schematic");
  }

  async function onDesignFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true);
    setError(null);
    try {
      applyResult(await api.uploadXsa(f));
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function parseFromPath() {
    if (!designPath.trim()) return;
    setBusy(true);
    setError(null);
    try {
      applyResult(await api.parseXsaPath(designPath.trim()));
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
          Tek dosya yeter: Vivado <span className="font-mono text-muted">.xsa</span> (2019.2+) veya eski
          SDK akışının <span className="font-mono text-muted">.hdf</span>&apos;i. Platform ve denetleyiciler
          otomatik algılanır; Vitis adımı bu dosyayı otomatik kullanır.
        </p>

        <div className="mb-3 flex items-center gap-2">
          <input ref={fileRef} type="file" accept=".xsa,.hdf" onChange={onDesignFile} className="hidden" />
          <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={busy}>
            <Upload className="h-4 w-4" /> .xsa / .hdf seç
          </Button>
          {detected && <Badge tone="accent">{detected}</Badge>}
          {count !== null && <Badge tone="ok">{count} controllers</Badge>}
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={designPath}
            onChange={(e) => setDesignPath(e.target.value)}
            placeholder="...veya tam yol: D:\\proje\\board.xsa"
            className="font-mono text-xs"
            onKeyDown={(e) => {
              if (e.key === "Enter") void parseFromPath();
            }}
          />
          <Button onClick={() => void parseFromPath()} disabled={busy || !designPath.trim()}>
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileArchive className="h-4 w-4" />}
            Şemayı kur
          </Button>
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-faint">
          Dosya içindeki hardware handoff (.hwh) okunur: PS çevre birimleri, PL IP&apos;leri ve adres
          haritası şematiğe dökülür; tanınmayan custom IP&apos;ler ayrıca listelenir. Not: Vitis workspace
          kurulumu <span className="font-mono text-muted">.xsa</span> gerektirir — .hdf yalnız şematik ve
          kod üretimi için kullanılabilir.
        </p>

        {error && <div className="mt-2 text-xs text-danger">{error}</div>}
      </div>
    </Card>
  );
}
