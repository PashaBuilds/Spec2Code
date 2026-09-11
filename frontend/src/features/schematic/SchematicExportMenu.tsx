// Kanvas sag ust: schematic'i draw.io (.drawio) ya da Excel (kart basina sayfa) olarak indir.
// Disa aktarim backend'de spec'ten uretilir (buildSpec), kanvas konumlarina bagli degildir.
import { useState } from "react";
import { Download, FileSpreadsheet, Workflow } from "lucide-react";
import { Panel } from "@xyflow/react";
import { useStore } from "@/store/useStore";
import { api } from "@/lib/api";
import { downloadBlob } from "@/lib/download";
import { Button } from "@/components/ui";

type Kind = "drawio" | "xlsx";

export default function SchematicExportMenu() {
  const buildSpec = useStore((s) => s.buildSpec);
  const [busy, setBusy] = useState<Kind | null>(null);
  const [error, setError] = useState("");

  const run = async (kind: Kind) => {
    if (busy) return;
    setBusy(kind);
    setError("");
    try {
      const spec = buildSpec();
      const name = `${spec.project.name || "spec2code"}-schematic.${kind}`;
      const blob = kind === "drawio" ? await api.schematicExportDrawio(spec) : await api.schematicExportXlsx(spec);
      downloadBlob(name, blob);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Panel position="top-right" className="!m-3">
      <div className="flex items-center gap-1.5 rounded-md border border-border bg-elev/90 p-1 backdrop-blur-sm">
        <span className="flex items-center gap-1 px-1.5 text-[11px] font-semibold uppercase tracking-wide text-faint">
          <Download className="h-3.5 w-3.5" /> Dışa aktar
        </span>
        <Button size="sm" variant="ghost" onClick={() => void run("drawio")} disabled={busy !== null} title="draw.io diyagramı (kart başına sayfa)">
          <Workflow className="mr-1 h-3.5 w-3.5" /> {busy === "drawio" ? "Hazırlanıyor…" : "draw.io"}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => void run("xlsx")} disabled={busy !== null} title="Excel (her sayfa bir kart)">
          <FileSpreadsheet className="mr-1 h-3.5 w-3.5" /> {busy === "xlsx" ? "Hazırlanıyor…" : "Excel"}
        </Button>
      </div>
      {error ? <p className="mt-1 max-w-xs text-right text-[11px] text-danger">{error}</p> : null}
    </Panel>
  );
}
