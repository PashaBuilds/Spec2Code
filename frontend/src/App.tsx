import { useEffect, useState, type ReactNode } from "react";
import { Activity, AudioWaveform, BookOpen, BookOpenText, Boxes, Command, Cpu, FileInput, Grid3X3, Play, Loader2, Library, PlugZap, Rocket } from "lucide-react";
import { api, openJobSocket } from "@/lib/api";
import { APP_VERSION } from "@/lib/version";
import { PLATFORM_LABELS, useStore, type Step } from "@/store/useStore";
import { cn } from "@/lib/utils";
import { Badge, Button } from "@/components/ui";
import ProjectSetup from "@/features/setup/ProjectSetup";
import DesignUpload from "@/features/setup/DesignUpload";
import SchematicCanvas from "@/features/schematic/SchematicCanvas";
import SidePanel from "@/features/schematic/SidePanel";
import GenerateConsole from "@/features/generate-console/GenerateConsole";
import CodeViewer from "@/features/code-view/CodeViewer";
import CatalogPanel from "@/features/catalog/CatalogPanel";
import DescriptorWizard from "@/features/driver-import/DescriptorWizard";
import DriverImport from "@/features/driver-import/DriverImport";
import UserDescriptorImport from "@/features/driver-import/UserDescriptorImport";
import DesignReviewPanel from "@/features/design-review/DesignReviewPanel";
import KnowledgeAskPanel from "@/features/device-knowledge/KnowledgeAskPanel";
import TestBenchPanel from "@/features/testbench/TestBenchPanel";
import TransactionTimeline from "@/features/testbench/TransactionTimeline";
import TelemetryControl from "@/features/schematic/TelemetryControl";
import { useBoardConnection } from "@/store/connection";
import TrafficPanel from "@/features/traffic/TrafficPanel";
import BringupPanel from "@/features/bringup/BringupPanel";
import RegistersPanel from "@/features/registers/RegistersPanel";
import DocsPanel from "@/features/docs/DocsPanel";
import VivadoDesignPanel from "@/features/vivado/VivadoDesignPanel";
import SerialLinePanel from "@/features/serial-line/SerialLinePanel";
import CommandPalette, { type PaletteCommand } from "@/components/CommandPalette";

type View = "flow" | "knowledge" | "catalog" | "testbench" | "traffic" | "serial" | "bringup" | "registers" | "docs" | "import" | "vivado";

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
  const boardConnected = useBoardConnection((s) => s.connected);
  // Ziyaret edilen ekranlar sökülmez, yalnızca gizlenir (keep-alive):
  // bağlantılar, canlı akışlar ve form durumu sekme geçişinde kaybolmaz.
  const [visitedViews, setVisitedViews] = useState<View[]>(["flow"]);

  useEffect(() => {
    setVisitedViews((current) => (current.includes(view) ? current : [...current, view]));
  }, [view]);

  function keepAlive(id: View, node: ReactNode) {
    if (view !== id && !visitedViews.includes(id)) return null;
    return (
      <div key={id} className={cn("h-full", view !== id && "hidden")}>
        {node}
      </div>
    );
  }

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
    { id: "board-connect", label: "Karta bağlan", hint: "aksiyon", keywords: "bağlan connect board smartlynq coresight seri tcp", run: () => { void useBoardConnection.getState().connect(); } },
    { id: "board-disconnect", label: "Kart bağlantısını kes", hint: "aksiyon", keywords: "kes disconnect kopar", run: () => { void useBoardConnection.getState().disconnect(); } },
    { id: "knowledge", label: "Bilgi soru merkezi", hint: "görünüm", keywords: "knowledge datasheet soru", run: () => setView("knowledge") },
    { id: "catalog", label: "Entegre kataloğu", hint: "görünüm", keywords: "catalog parça ic", run: () => setView("catalog") },
    { id: "testbench", label: "Test Bench", hint: "görünüm", keywords: "tcp seri komut agent", run: () => setView("testbench") },
    { id: "traffic", label: "Veri Akışı — TX/RX trafiği", hint: "görünüm", keywords: "trafik veri akış tx rx coresight dcc jtag", run: () => setView("traffic") },
    { id: "serial", label: "Seri Hat — transfer diyagramları", hint: "görünüm", keywords: "seri hat bus waveform i2c spi transfer diyagram", run: () => setView("serial") },
    { id: "bringup", label: "Bring-up — Mission Control", hint: "görünüm", keywords: "bringup sihirbaz sertifika", run: () => setView("bringup") },
    { id: "registers", label: "Register snapshot & diff", hint: "görünüm", keywords: "register bit ısı haritası", run: () => setView("registers") },
    { id: "docs", label: "Kullanım kılavuzu", hint: "görünüm", keywords: "docs kılavuz yardım dokümantasyon manual help", run: () => setView("docs") },
    { id: "import", label: "Driver import", hint: "görünüm", keywords: "sürücü kaynak içe aktar", run: () => setView("import") },
    { id: "vivado", label: "Vivado Tasarımı — PS'ten XSA/bit üret", hint: "görünüm", keywords: "vivado xsa bit pdi donanım tasarım ps mio ddr", run: () => setView("vivado") },
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
          <span className="hidden font-mono text-xs text-faint lg:inline">{project.name}</span>
          <Badge tone="neutral">{PLATFORM_LABELS[project.platform]}</Badge>
          <Badge tone={llm.enabled ? "accent" : "neutral"}>LLM {llm.enabled ? "on" : "off"}</Badge>
          {/* Başlıkta: hangi ekranda olursanız olun telemetri çalışmaya devam eder. */}
          <TelemetryControl />
          <Button
            variant="ghost"
            size="sm"
            onClick={() => window.dispatchEvent(new Event("s2c:palette"))}
            title="Komut paleti (Ctrl+K / Cmd+K)"
          >
            <Command className="h-4 w-4" /> K
          </Button>
          <Button onClick={runGenerate} disabled={jobStatus === "running" || !devices.length}>
            {jobStatus === "running" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Generate
          </Button>
        </div>
      </header>

      {/* görünüm sekmeleri: ayrı satır — dar ekranda sarar, taşmaz */}
      <nav className="flex flex-wrap items-center gap-1 border-b border-border px-4 py-1">
        {([
          ["knowledge", BookOpen, "Bilgi"],
          ["catalog", Library, "Katalog"],
          ["testbench", PlugZap, "Test Bench"],
          ["traffic", Activity, "Akış"],
          ["serial", AudioWaveform, "Seri Hat"],
          ["bringup", Rocket, "Bring-up"],
          ["registers", Grid3X3, "Registers"],
          ["docs", BookOpenText, "Kılavuz"],
          ["import", FileInput, "Import"],
          ["vivado", Boxes, "Vivado"],
        ] as const).map(([id, Icon, label]) => (
          <Button
            key={id}
            variant={view === id ? "outline" : "ghost"}
            size="sm"
            onClick={() => setView(view === id ? "flow" : id)}
          >
            <Icon className="h-4 w-4" /> {label}
          </Button>
        ))}
        <span className="ml-auto flex items-center gap-2">
          <Badge tone={boardConnected ? "ok" : "neutral"}>
            kart {boardConnected ? "bağlı" : "kopuk"}
          </Badge>
        </span>
      </nav>

      {genError && (
        <div className="shrink-0 border-b border-danger/30 bg-danger/10 px-4 py-2 text-xs text-danger">
          {genError}
        </div>
      )}

      {/* body — keep-alive: ziyaret edilen ekranlar gizlenir ama sökülmez */}
      <main className="min-h-0 flex-1">
        {keepAlive("knowledge", (
          <div className="mx-auto flex h-full max-w-5xl flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Bilgi soru merkezi</h2>
            <div className="min-h-0 flex-1 overflow-auto">
              <KnowledgeAskPanel />
            </div>
          </div>
        ))}
        {keepAlive("catalog", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Entegre kataloğu</h2>
            <div className="min-h-0 flex-1">
              <CatalogPanel mode="browse" />
            </div>
          </div>
        ))}
        {keepAlive("testbench", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Test Bench</h2>
            <div className="min-h-0 flex-1">
              <TestBenchPanel />
            </div>
            <TransactionTimeline />
          </div>
        ))}
        {keepAlive("traffic", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Veri Akışı — host ↔ agent TX/RX</h2>
            <div className="min-h-0 flex-1">
              <TrafficPanel />
            </div>
          </div>
        ))}
        {keepAlive("serial", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Seri Hat — id eşleşmeli transfer diyagramları</h2>
            <div className="min-h-0 flex-1">
              <SerialLinePanel />
            </div>
          </div>
        ))}
        {keepAlive("bringup", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Bring-up — Mission Control</h2>
            <div className="min-h-0 flex-1">
              <BringupPanel />
            </div>
          </div>
        ))}
        {keepAlive("registers", (
          <div className="flex h-full min-h-0 flex-col p-4">
            <h2 className="mb-3 shrink-0 text-sm font-semibold">Register snapshot &amp; diff</h2>
            <div className="min-h-0 flex-1">
              <RegistersPanel />
            </div>
          </div>
        ))}
        {keepAlive("docs", (
          <div className="h-full min-h-0 p-4">
            <DocsPanel />
          </div>
        ))}
        {keepAlive("vivado", (
          <div className="h-full min-h-0 overflow-auto p-4">
            <VivadoDesignPanel />
          </div>
        ))}
        {keepAlive("import", (
          <div className="mx-auto h-full max-w-6xl space-y-6 overflow-auto p-6">
            <DescriptorWizard />
            <UserDescriptorImport />
            {/* Kaynak import'u ikincil: bu dosyalar üretimin YERİNE GEÇMEZ,
                çıktı paketine reference_sources/ altında referans olarak
                eklenir. Birincil yol yukarıdaki descriptor akışıdır. */}
            <details className="rounded-lg border border-border bg-elev p-4">
              <summary className="cursor-pointer list-none text-sm font-semibold text-text">
                Sürücü kaynak referansları (.c/.h) — gelişmiş
                <span className="ml-2 text-xs font-normal text-faint">
                  üretimin yerine geçmez; çıktı paketine referans olarak eklenir
                </span>
              </summary>
              <div className="mt-4">
                <DriverImport />
              </div>
            </details>
          </div>
        ))}
        <div className={cn("h-full", view !== "flow" && "hidden")}>
          {step === "setup" ? (
            <div className="mx-auto grid max-w-5xl gap-5 p-6 md:grid-cols-2">
              <ProjectSetup />
              <DesignUpload />
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
        </div>
      </main>
    </div>
  );
}
