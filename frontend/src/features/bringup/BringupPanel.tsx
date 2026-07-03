import { useEffect, useMemo, useRef, useState } from "react";
import {
  Award,
  CheckCircle2,
  Link2,
  Loader2,
  Rocket,
  Unplug,
  XCircle,
} from "lucide-react";
import { Badge, Button, Card, Input, Label } from "@/components/ui";
import BoardConnectionCard from "@/components/BoardConnectionCard";
import { useBoardConnection } from "@/store/connection";
import { api, openBringupSocket } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type { JobEvent, TestbenchManifest } from "@/lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  power: "Güç / izleme",
  sensor: "Sensörler",
  clock: "Saat ağacı",
  memory: "Bellekler",
  rf: "RF",
  other: "Diğer",
};

interface PlanStep {
  index: number;
  device_id: string;
  part: string;
  operation: string;
  label: string;
  category: string;
  risk: string;
}

interface StepState {
  state: "pending" | "running" | "pass" | "fail";
  value?: string;
  data?: string;
  error?: string;
  duration_ms?: number;
}

function StageLight({ state }: { state: "pending" | "running" | "pass" | "fail" }) {
  return (
    <span
      className={cn(
        "inline-block h-2.5 w-2.5 shrink-0 rounded-full",
        state === "pass" && "bg-ok shadow-[0_0_8px_var(--ok)]",
        state === "fail" && "bg-danger shadow-[0_0_8px_var(--danger)]",
        state === "running" && "bg-warn shadow-[0_0_8px_var(--warn)] animate-pulse-soft",
        state === "pending" && "bg-faint/40",
      )}
    />
  );
}

export default function BringupPanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);
  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  // Bağlantı global tek session'dan (store/connection) — CoreSight dahil.
  const board = useBoardConnection();
  const sessionId = board.sessionId;
  const connected = board.connected;
  const [includeInit, setIncludeInit] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [steps, setSteps] = useState<PlanStep[]>([]);
  const [stepStates, setStepStates] = useState<Record<number, StepState>>({});
  const [summary, setSummary] = useState<{ passed: number; failed: number } | null>(null);
  const [jobId, setJobId] = useState("");
  const closeSocketRef = useRef<null | (() => void)>(null);

  useEffect(() => {
    return () => {
      closeSocketRef.current?.();
      void api.testbenchDisconnect(sessionId).catch(() => undefined);
    };
  }, [sessionId]);

  function applyEvent(event: JobEvent) {
    if (event.event === "bringup.plan" && Array.isArray(event.steps)) {
      const plan = event.steps as PlanStep[];
      setSteps(plan);
      setStepStates(Object.fromEntries(plan.map((step) => [step.index, { state: "pending" as const }])));
    } else if (event.event === "bringup.step_start" && typeof event.index === "number") {
      const index = event.index;
      setStepStates((current) => ({ ...current, [index]: { ...current[index], state: "running" } }));
    } else if (event.event === "bringup.step_done" && typeof event.index === "number") {
      const index = event.index;
      setStepStates((current) => ({
        ...current,
        [index]: {
          state: event.ok ? "pass" : "fail",
          value: typeof event.value === "string" ? event.value : "",
          data: typeof event.data === "string" ? event.data : "",
          error: typeof event.error === "string" ? event.error : "",
          duration_ms: typeof event.duration_ms === "number" ? event.duration_ms : undefined,
        },
      }));
    } else if (event.event === "bringup.summary") {
      setSummary({
        passed: typeof event.passed === "number" ? event.passed : 0,
        failed: typeof event.failed === "number" ? event.failed : 0,
      });
    } else if (event.event === "bringup.error" && typeof event.message === "string") {
      setError(event.message);
    }
  }

  async function start() {
    if (!manifest || !connected || running) return;
    closeSocketRef.current?.();
    setSteps([]);
    setStepStates({});
    setSummary(null);
    setError("");
    setJobId("");
    setRunning(true);
    try {
      const response = await api.bringupStart({
        session_id: sessionId,
        manifest,
        include_init: includeInit,
        timeout_s: 5,
      });
      setJobId(response.bringup_job_id);
      closeSocketRef.current = openBringupSocket(
        response.bringup_job_id,
        applyEvent,
        () => setRunning(false),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setRunning(false);
    }
  }

  const categories = useMemo(() => {
    const order: string[] = [];
    for (const step of steps) {
      if (!order.includes(step.category)) order.push(step.category);
    }
    return order;
  }, [steps]);

  function categoryState(category: string): "pending" | "running" | "pass" | "fail" {
    const catSteps = steps.filter((step) => step.category === category);
    const states = catSteps.map((step) => stepStates[step.index]?.state ?? "pending");
    if (states.some((state) => state === "running")) return "running";
    if (states.some((state) => state === "fail")) return "fail";
    if (states.length > 0 && states.every((state) => state === "pass")) return "pass";
    return "pending";
  }

  if (!manifest) {
    return (
      <Card className="mx-auto max-w-3xl p-6">
        <div className="flex items-start gap-3">
          <Rocket className="mt-0.5 h-5 w-5 text-accent" aria-hidden />
          <div>
            <h2 className="text-sm font-semibold text-text">Mission Control hazır değil</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Bring-up sihirbazı, Generate sonucundaki test bench manifest&apos;ini kullanır. Önce Generate
              çalıştır; ardından bu ekran kartın tüm entegrelerini güç → saat → çevre birimleri sırasıyla
              yoklayıp bir &quot;board birth certificate&quot; üretir.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  const done = !running && summary !== null;
  const allPassed = done && summary!.failed === 0;

  return (
    <div className="grid h-full min-h-0 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
      <aside className="min-h-0 space-y-3 overflow-auto rounded-lg border border-border bg-elev p-3">
        <div className="flex items-center gap-2">
          <Rocket className="h-4 w-4 text-accent" aria-hidden />
          <span className="text-sm font-semibold text-text">Mission Control</span>
          <Badge tone={connected ? "ok" : "neutral"}>{connected ? "bağlı" : "kopuk"}</Badge>
        </div>
        <p className="text-xs leading-relaxed text-faint">
          Kart üzerindeki agent&apos;a bağlan, tek tuşla bütün entegreleri sırayla yokla.
        </p>

        <BoardConnectionCard compact />

        <label className="flex items-center gap-2 text-xs text-muted">
          <input
            type="checkbox"
            checked={includeInit}
            onChange={(e) => setIncludeInit(e.target.checked)}
            disabled={running}
            className="accent-[var(--accent)]"
          />
          device_init adımlarını dahil et
        </label>

        <Button className="w-full" onClick={() => void start()} disabled={!connected || running}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Rocket className="h-4 w-4" aria-hidden />}
          Bring-up başlat
        </Button>

        {error ? (
          <p className="rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
        ) : null}

        {done ? (
          <div className={cn(
            "rounded-md border p-3",
            allPassed ? "border-ok/40 bg-ok/10" : "border-warn/40 bg-warn/10",
          )}>
            <div className="mb-2 flex items-center gap-2 text-sm font-semibold">
              {allPassed
                ? <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden />
                : <XCircle className="h-4 w-4 text-warn" aria-hidden />}
              <span className={allPassed ? "text-ok" : "text-warn"}>
                {summary!.passed}/{summary!.passed + summary!.failed} adım geçti
              </span>
            </div>
            {jobId ? (
              <a href={api.bringupCertificateUrl(jobId)} download>
                <Button size="sm" variant="outline" className="w-full">
                  <Award className="h-4 w-4" aria-hidden /> Birth certificate indir
                </Button>
              </a>
            ) : null}
          </div>
        ) : null}
      </aside>

      <section className="min-h-0 overflow-auto rounded-lg border border-border bg-elev">
        {steps.length === 0 ? (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-faint">
            <p>
              Plan, bring-up başlatıldığında burada aşama aşama yanacak:<br />
              <span className="font-mono text-xs">güç → sensör → saat ağacı → bellek → RF</span>
            </p>
          </div>
        ) : (
          <div className="space-y-4 p-4">
            {categories.map((category) => {
              const catState = categoryState(category);
              return (
                <div key={category} className="rounded-md border border-border bg-inset/50">
                  <div className="flex items-center gap-2 border-b border-border px-3 py-2">
                    <StageLight state={catState} />
                    <span className="text-silk font-mono text-xs font-semibold">
                      {CATEGORY_LABELS[category] ?? category}
                    </span>
                    <span className="ml-auto font-mono text-[10px] text-faint">
                      {steps.filter((s) => s.category === category).length} adım
                    </span>
                  </div>
                  <div className="divide-y divide-border/60">
                    {steps.filter((step) => step.category === category).map((step) => {
                      const state = stepStates[step.index] ?? { state: "pending" as const };
                      return (
                        <div key={step.index} className="grid grid-cols-[16px_150px_minmax(0,1fr)_auto] items-center gap-2 px-3 py-1.5">
                          <StageLight state={state.state} />
                          <span className="truncate font-mono text-xs text-text">{step.part}</span>
                          <span className="truncate text-xs text-muted" title={step.label || step.operation}>
                            {step.label || step.operation}
                          </span>
                          <span className="font-mono text-[11px]">
                            {state.state === "pass" && (
                              <span className="text-ok">{state.value || state.data?.slice(0, 16) || "OK"}</span>
                            )}
                            {state.state === "fail" && (
                              <span className="text-danger" title={state.error}>{state.error ? "İLETİŞİM" : "FAIL"}</span>
                            )}
                            {state.state === "running" && <span className="text-warn">çalışıyor…</span>}
                            {state.state === "pending" && <span className="text-faint">—</span>}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
