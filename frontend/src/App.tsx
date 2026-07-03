import { useEffect, useState } from "react";
import { Activity, BookOpen, Boxes, Cable, Cpu, FileInput, Grid3X3, Play, Loader2, Library, PlugZap, Rocket } from "lucide-react";
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
import TestBenchPanel from "@/features/testbench/TestBenchPanel";
import TransactionTimeline from "@/features/testbench/TransactionTimeline";
import UartConsolePanel from "@/features/uart-console/UartConsolePanel";
import TrafficPanel from "@/features/traffic/TrafficPanel";
import BringupPanel from "@/features/bringup/BringupPanel";
import RegistersPanel from "@/features/registers/RegistersPanel";
import CommandPalette, { type PaletteCommand } from "@/components/CommandPalette";

type View = "flow" | "knowledge" | "catalog" | "testbench" | "uart" | "traffic" | "bringup" | "registers" | "import";

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

  const paletteCommands: PaletteCommand[] = [
    { id: "setup", label: "Setup ekranına git", hint: "adım", keywords: "proje platform runtime", run: () => { setStep("setup"); setView("flow"); } },
    { id: "schematic", label: "Schematic ekranına git", hint: "adım", keywords: "şema devre kablo node", run: () => { setStep("schematic"); setView("flow"); } },
    { id: "generate-view", label: "Generate ekranına git", hint: "adım", keywords: "kod üret konsol", run: () => { setStep("generate"); setView("flow"); } },
    { id: "run-generate", label: "Generate çalıştır", hint: "aksiyon", keywords: "kod üret başlat build", run: () => { void runGenerate(); } },
    { id: "knowledge", label: "Bilgi soru merkezi", hint: "görünüm", keywords: "knowledge datasheet soru", run: () => setView("knowledge") },
    { id: "catalog", label: "Entegre kataloğu", hint: "görünüm", keywords: "catalog parça ic", run: () => setView("catalog") },
    { id: "testbench", label: "Test Bench", hint: "görünüm", keywords: "tcp seri komut agent", run: () => setView("testbench") },
    { id: "uart", label: "UART konsolu", hint: "görünüm", keywords: "seri com konsol log", run: () => setView("uart") },
    { id: "traffic", label: "Veri Akışı — TX/RX trafiği", hint: "görünüm", keywords: "trafik veri akış tx rx coresight dcc jtag", run: () => setView("traffic") },
    { id: "bringup", label: "Bring-up — Mission Control", hint: "görünüm", keywords: "bringup sihirbaz sertifika", run: () => setView("bringup") },
    { id: "registers", label: "Register snapshot & diff", hint: "görünüm", keywords: "register bit ısı haritası", run: () => setView("registers") },
    { id: "import", label: "Driver import", hint: "görünüm", keywords: "sürücü kaynak içe aktar", run: () => setView("import") },
  ];

  return (
    <div className="flex h-screen flex-col bg-bg text-text">
      <CommandPalette commands={paletteCommands} />
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
            variant={view === "testbench" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "testbench" ? "flow" : "testbench")}
          >
            <PlugZap className="h-4 w-4" /> Test Bench
          </Button>
          <Button
            variant={view === "uart" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "uart" ? "flow" : "uart")}
          >
            <Cable className="h-4 w-4" /> UART
          </Button>
          <Button
            variant={view === "traffic" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "traffic" ? "flow" : "traffic")}
          >
            <Activity className="h-4 w-4" /> Akış
          </Button>
          <Button
            variant={view === "bringup" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "bringup" ? "flow" : "bringup")}
          >
            <Rocket className="h-4 w-4" /> Bring-up
          </Button>
          <Button
            variant={view === "registers" ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === "registers" ? "flow" : "registers")}
          >
            <Grid3X3 className="h-4 w-4" /> Registers
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
        ) : view === "testbench" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Test Bench</h2>
            <div className="min-h-0 flex-1">
              <TestBenchPanel />
            </div>
            <TransactionTimeline />
          </div>
        ) : view === "uart" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">UART konsolu</h2>
            <div className="min-h-0 flex-1">
              <UartConsolePanel />
            </div>
          </div>
        ) : view === "traffic" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Veri Akışı — host ↔ agent TX/RX</h2>
            <div className="min-h-0 flex-1">
              <TrafficPanel />
            </div>
          </div>
        ) : view === "bringup" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Bring-up — Mission Control</h2>
            <div className="min-h-0 flex-1">
              <BringupPanel />
            </div>
          </div>
        ) : view === "registers" ? (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Register snapshot &amp; diff</h2>
            <div className="min-h-0 flex-1">
              <RegistersPanel />
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
