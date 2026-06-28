import { useEffect, useState } from "react";
import { BookOpen, Boxes, Cpu, FileInput, Play, Loader2, Library } from "lucide-react";
import { api, openJobSocket } from "@/lib/api";
import { APP_VERSION } from "@/lib/version";
import { PLATFORM_LABELS, useStore, type Step } from "@/store/useStore";
import { cn } from "@/lib/utils";
import { Badge, Button } from "@/components/ui";
import ProjectSetup from "@/features/setup/ProjectSetup";
import XparametersUpload from "@/features/setup/XparametersUpload";
import SchematicCanvas from "@/features/schematic/SchematicCanvas";
import SidePanel from "@/features/schematic/SidePanel";
import GenerateConsole from "@/features/generate-console/GenerateConsole";
import CodeViewer from "@/features/code-view/CodeViewer";
import CatalogPanel from "@/features/catalog/CatalogPanel";
import DriverImport from "@/features/driver-import/DriverImport";
import DesignReviewPanel from "@/features/design-review/DesignReviewPanel";
import KnowledgeAskPanel from "@/features/device-knowledge/KnowledgeAskPanel";

type View = "flow" | "knowledge" | "catalog" | "import";

const STEPS: { id: Step; label: string; icon: typeof Cpu }[] = [
  { id: "setup", label: "Setup", icon: Cpu },
  { id: "schematic", label: "Schematic", icon: Boxes },
  { id: "generate", label: "Generate", icon: Play },
];

export default function App() {
  const step = useStore((s) => s.step);
  const setStep = useStore((s) => s.setStep);
  const project = useStore((s) => s.project);
  const llm = useStore((s) => s.llm);
  const devices = useStore((s) => s.devices);
  const buildSpec = useStore((s) => s.buildSpec);
  const setCatalog = useStore((s) => s.setCatalog);
  const setDescriptors = useStore((s) => s.setDescriptors);
  const resetJob = useStore((s) => s.resetJob);
  const setJob = useStore((s) => s.setJob);
  const pushEvent = useStore((s) => s.pushEvent);
  const jobStatus = useStore((s) => s.job.status);

  const [view, setView] = useState<View>("flow");
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    api.catalog().then((c) => setCatalog(c.devices)).catch(() => {});
    api.descriptors().then(setDescriptors).catch(() => {});
  }, [setCatalog, setDescriptors]);

  async function runGenerate() {
    setGenError(null);
    const spec = buildSpec();
    setView("flow");
    setStep("generate");
    try {
      const v = await api.validate(spec);
      if (!v.valid) {
        setGenError("Spec/preflight invalid: " + v.errors.map((e) => `${e.path} ${e.message}`).join("; "));
        return;
      }
      resetJob();
      setJob({ status: "running" });
      const { job_id } = await api.generate(spec);
      setJob({ id: job_id });
      openJobSocket(
        job_id,
        (e) => pushEvent(e),
        async () => {
          const res = await api.jobResult(job_id);
          setJob({
            status: res.status === "done" ? "done" : "error",
            files: res.files,
            qc: res.result?.qc ?? null,
          });
        },
      );
    } catch (err) {
      setGenError(String(err instanceof Error ? err.message : err));
      setJob({ status: "error" });
    }
  }

  return (
    <div className="flex h-screen flex-col bg-bg text-text">
      {/* header */}
      <header className="flex h-14 shrink-0 items-center gap-4 border-b border-border px-4">
        <div className="flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded bg-accent/15 font-mono text-sm font-bold text-accent">
            S2
          </div>
          <span className="font-semibold">Spec2Code</span>
          <Badge tone="accent" className="font-mono">
            {APP_VERSION}
          </Badge>
        </div>

        <nav className="flex items-center gap-1">
          {STEPS.map((s) => (
            <button
              key={s.id}
              onClick={() => {
                setStep(s.id);
                setView("flow");
              }}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                step === s.id && view === "flow"
                  ? "bg-inset text-text"
                  : "text-muted hover:text-text",
              )}
            >
              <s.icon className="h-4 w-4" />
              {s.label}
            </button>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden font-mono text-xs text-faint md:inline">{project.name}</span>
          <Badge tone="neutral">{PLATFORM_LABELS[project.platform]}</Badge>
          <Badge tone={llm.enabled ? "accent" : "neutral"}>LLM {llm.enabled ? "on" : "off"}</Badge>
          <Button
            variant={view === "knowledge" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "knowledge" ? "flow" : "knowledge")}
          >
            <BookOpen className="h-4 w-4" /> Bilgi
          </Button>
          <Button
            variant={view === "catalog" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "catalog" ? "flow" : "catalog")}
          >
            <Library className="h-4 w-4" /> Catalog
          </Button>
          <Button
            variant={view === "import" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "import" ? "flow" : "import")}
          >
            <FileInput className="h-4 w-4" /> Import
          </Button>
          <Button onClick={runGenerate} disabled={jobStatus === "running" || !devices.length}>
            {jobStatus === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Generate
          </Button>
        </div>
      </header>

      {genError && (
        <div className="shrink-0 border-b border-danger/30 bg-danger/10 px-4 py-2 text-xs text-danger">
          {genError}
        </div>
      )}

      {/* body */}
      <main className="min-h-0 flex-1">
        {view === "knowledge" ? (
          <div className="mx-auto flex h-full max-w-5xl flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Bilgi soru merkezi</h2>
            <div className="min-h-0 flex-1 overflow-auto">
              <KnowledgeAskPanel />
            </div>
          </div>
        ) : view === "catalog" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Entegre kataloğu</h2>
            <div className="min-h-0 flex-1">
              <CatalogPanel mode="browse" />
            </div>
          </div>
        ) : view === "import" ? (
          <div className="mx-auto h-full max-w-3xl overflow-auto p-6">
            <h2 className="mb-4 text-sm font-semibold">Import driver sources</h2>
            <DriverImport />
          </div>
        ) : step === "setup" ? (
          <div className="mx-auto grid max-w-5xl gap-5 p-6 md:grid-cols-2">
            <ProjectSetup />
            <XparametersUpload />
          </div>
        ) : step === "schematic" ? (
          <div className="flex h-full min-h-0">
            <div className="relative min-w-0 flex-1 border-r border-border">
              <SchematicCanvas />
            </div>
            <aside className="w-[360px] shrink-0 overflow-auto p-4">
              <SidePanel />
            </aside>
          </div>
        ) : (
          <div className="grid h-full grid-cols-1 lg:grid-cols-2">
            <div className="flex min-h-0 flex-col gap-4 overflow-auto border-r border-border p-4">
              <DesignReviewPanel />
              <div className="min-h-[320px] flex-1">
                <GenerateConsole />
              </div>
            </div>
            <div className="min-h-0 overflow-auto p-4">
              <CodeViewer />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
