import { useRef, useState } from "react";
import { Upload, FileCode, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { Badge, Button, Card } from "@/components/ui";
import { VisualBackdrop } from "@/components/visuals";

export default function XparametersUpload() {
  const project = useStore((s) => s.project);
  const applyParse = useStore((s) => s.applyParse);
  const setStep = useStore((s) => s.setStep);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [count, setCount] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) setText(await f.text());
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
      <h2 className="mb-1 text-sm font-semibold text-text">xparameters.h</h2>
      <p className="mb-4 text-xs text-faint">
        Upload the Vivado/Vitis BSP header. Controllers are extracted automatically and placed into
        their platform zones (read-only).
      </p>

      <div className="mb-3 flex items-center gap-2">
        <input ref={fileRef} type="file" accept=".h" onChange={onFile} className="hidden" />
        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
          <Upload className="h-4 w-4" /> Choose file
        </Button>
        {count !== null && <Badge tone="ok">{count} controllers</Badge>}
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        placeholder="…or paste #define XPAR_XIICPS_0_BASEADDR 0xFF020000 …"
        className="h-48 w-full resize-none rounded-md border border-border bg-inset p-3 font-mono text-xs text-text placeholder:text-faint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
      />

      {error && <div className="mt-2 text-xs text-danger">{error}</div>}

      <div className="mt-4 flex items-center gap-2">
        <Button onClick={parse} disabled={busy || !text.trim()}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileCode className="h-4 w-4" />}
          Parse &amp; build schematic
        </Button>
      </div>
      </div>
    </Card>
  );
}
