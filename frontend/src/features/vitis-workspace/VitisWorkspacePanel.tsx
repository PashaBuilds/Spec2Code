import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, FolderCog, Loader2, Play, TerminalSquare } from "lucide-react";
import { Badge, Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { api, openVitisSocket } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { JobEvent, VitisCompileIssue, VitisWorkspaceResult } from "@/lib/types";

const VITIS_STAGES = [
  { id: "locate", label: "XSCT", progress: 14 },
  { id: "version", label: "Sürüm", progress: 25 },
  { id: "stage_sources", label: "Kaynaklar", progress: 40 },
  { id: "script", label: "Script", progress: 55 },
  { id: "run", label: "Build", progress: 72 },
  { id: "done", label: "Hazır", progress: 100 },
] as const;

type VitisStageId = (typeof VITIS_STAGES)[number]["id"] | "start" | "error" | "end";
type CustomIpDriverPolicy = "auto_none" | "keep";

function defaultVitisProcessor(platform: string, targetCore: string) {
  if (platform === "zynq_ultrascale") {
    const a53 = /^a53_(\d)$/.exec(targetCore);
    if (a53) return `psu_cortexa53_${a53[1]}`;
    const r5 = /^r5_(\d)$/.exec(targetCore);
    if (r5) return `psu_cortexr5_${r5[1]}`;
  }
  if (platform === "versal") {
    const a72 = /^a72_(\d)$/.exec(targetCore);
    if (a72) return `psv_cortexa72_${a72[1]}`;
    const r5 = /^r5_(\d)$/.exec(targetCore);
    if (r5) return `psv_cortexr5_${r5[1]}`;
  }
  return targetCore;
}

function runtimeForVitis(runtime: string) {
  return runtime === "freertos" ? "freertos10_xilinx" : "standalone";
}

function safeProjectName(value: string, fallback: string) {
  return value.replace(/[^A-Za-z0-9_]+/g, "_").replace(/^_+|_+$/g, "") || fallback;
}

function cleanPathInput(value: string) {
  return value.trim().replace(/^["']|["']$/g, "");
}

function customIpDriverPolicyFromStorage(): CustomIpDriverPolicy {
  return localStorage.getItem("spec2code.customIpDriverPolicy") === "keep" ? "keep" : "auto_none";
}

function fieldError(error: unknown) {
  const raw = error instanceof Error ? error.message : String(error);
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed === "string") return parsed;
    if (parsed?.message) return String(parsed.message);
    if (parsed?.error) return String(parsed.error);
  } catch {
    /* keep raw */
  }
  return raw;
}

function latestProgress(events: JobEvent[]) {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const value = events[index].progress;
    if (typeof value === "number") return Math.max(0, Math.min(100, value));
  }
  return 0;
}

function latestStage(events: JobEvent[]): VitisStageId | null {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const stage = events[index].stage;
    if (typeof stage === "string") return stage as VitisStageId;
  }
  return null;
}

function statusMessage(events: JobEvent[]) {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const message = events[index].message;
    if (typeof message === "string") return message;
  }
  return "Vitis workspace akışı bekliyor.";
}

function VitisProgress({
  events,
  running,
  error,
}: {
  events: JobEvent[];
  running: boolean;
  error: string;
}) {
  const progress = latestProgress(events);
  const stage = latestStage(events);
  const activeIndex = stage === "done"
    ? VITIS_STAGES.length
    : stage === "error"
      ? VITIS_STAGES.findIndex((item) => item.id === "run")
      : VITIS_STAGES.findIndex((item) => item.id === stage);

  return (
    <div className="rounded-md border border-border bg-inset/70 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {error ? (
            <CircleDashed className="h-4 w-4 text-danger" aria-hidden />
          ) : stage === "done" ? (
            <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden />
          ) : running ? (
            <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden />
          ) : (
            <CircleDashed className="h-4 w-4 text-faint" aria-hidden />
          )}
          <span className="text-xs font-semibold text-text">
            {error ? "Vitis akışı hata ile durdu" : stage === "done" ? "Workspace hazır" : running ? "Workspace oluşturuluyor" : "Hazır"}
          </span>
        </div>
        <span className="font-mono text-[10px] text-faint">{Math.round(progress)}%</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-bg">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-300",
            error ? "bg-danger" : stage === "done" ? "bg-ok" : "bg-accent",
          )}
          style={{ width: `${Math.max(events.length ? 4 : 0, progress)}%` }}
        />
      </div>
      <div className="mt-3 grid gap-1.5 sm:grid-cols-3 xl:grid-cols-6">
        {VITIS_STAGES.map((item, index) => {
          const done = stage === "done" || index < activeIndex;
          const active = stage === item.id;
          return (
            <div
              key={item.id}
              className={cn(
                "rounded border px-2 py-1.5",
                done ? "border-ok/30 bg-ok/10" : active ? "border-accent/40 bg-accent/10" : "border-border bg-bg/50",
              )}
            >
              <div className="flex items-center gap-1.5">
                {done ? (
                  <CheckCircle2 className="h-3 w-3 text-ok" aria-hidden />
                ) : active ? (
                  <Loader2 className="h-3 w-3 animate-spin text-accent" aria-hidden />
                ) : (
                  <CircleDashed className="h-3 w-3 text-faint" aria-hidden />
                )}
                <span className={cn("text-[10px] font-semibold", done ? "text-ok" : active ? "text-accent" : "text-faint")}>
                  {item.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-faint">{error || statusMessage(events)}</p>
    </div>
  );
}

function CompileIssuesPanel({ issues }: { issues: VitisCompileIssue[] }) {
  if (issues.length === 0) return null;
  return (
    <div className="mt-3 rounded-md border border-danger/30 bg-danger/10">
      <div className="flex items-center justify-between gap-2 border-b border-danger/20 px-3 py-2">
        <div className="flex items-center gap-2">
          <AlertTriangle className="h-3.5 w-3.5 text-danger" aria-hidden />
          <span className="text-xs font-semibold text-danger">Vitis compile hata eşleştirme</span>
        </div>
        <Badge tone="danger">{issues.length} issue</Badge>
      </div>
      <div className="divide-y divide-danger/15">
        {issues.slice(0, 8).map((issue, index) => (
          <div key={`${issue.category}-${index}`} className="px-3 py-2 text-[11px] leading-relaxed">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <Badge tone="danger" className="font-mono">{issue.category}</Badge>
              {issue.symbol ? <code className="rounded border border-danger/20 bg-bg px-1 py-0.5 font-mono text-text">{issue.symbol}</code> : null}
              {issue.file ? (
                <span className="min-w-0 break-all font-mono text-faint">
                  {issue.file}{issue.line ? `:${issue.line}` : ""}
                </span>
              ) : null}
            </div>
            <p className="text-text">{issue.message}</p>
            <p className="mt-1 text-muted">{issue.suggestion}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export function VitisWorkspacePanel({ jobId }: { jobId: string }) {
  const project = useStore((s) => s.project);
  const defaultNameBase = useMemo(() => safeProjectName(project.name, "spec2code"), [project.name]);
  const defaultProcessor = useMemo(
    () => defaultVitisProcessor(project.platform, project.target_core),
    [project.platform, project.target_core],
  );
  const [vitisPath, setVitisPath] = useState(() => localStorage.getItem("spec2code.vitisPath") ?? "");
  const [xsaPath, setXsaPath] = useState(() => localStorage.getItem("spec2code.xsaPath") ?? "");
  const [workspacePath, setWorkspacePath] = useState(() => localStorage.getItem("spec2code.workspacePath") ?? "");
  const [processor, setProcessor] = useState(defaultProcessor);
  const [platformName, setPlatformName] = useState(() => localStorage.getItem("spec2code.platformName") ?? "");
  const [systemName, setSystemName] = useState(() => localStorage.getItem("spec2code.systemName") ?? "");
  const [appName, setAppName] = useState(() => localStorage.getItem("spec2code.appName") ?? "");
  const [customIpDriverPolicy, setCustomIpDriverPolicy] = useState<CustomIpDriverPolicy>(customIpDriverPolicyFromStorage);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [compileIssues, setCompileIssues] = useState<VitisCompileIssue[]>([]);
  const [result, setResult] = useState<VitisWorkspaceResult["result"] | null>(null);
  const closeSocketRef = useRef<null | (() => void)>(null);

  useEffect(() => {
    setProcessor((current) => current || defaultProcessor);
  }, [defaultProcessor]);

  useEffect(() => {
    setPlatformName((current) => current || `${defaultNameBase}_platform`);
    setSystemName((current) => current || `${defaultNameBase}_system`);
    setAppName((current) => current || `${defaultNameBase}_app`);
  }, [defaultNameBase]);

  useEffect(() => () => closeSocketRef.current?.(), []);

  async function refreshResult(vitisJobId: string) {
    try {
      const response = await api.vitisWorkspaceResult(vitisJobId);
      setResult(response.result);
      setCompileIssues(response.result?.compile_issues ?? []);
      if (response.error) setError(response.error);
    } catch (err) {
      setError(fieldError(err));
    }
  }

  async function start() {
    const vitisInput = cleanPathInput(vitisPath);
    const xsaInput = cleanPathInput(xsaPath);
    const workspaceInput = cleanPathInput(workspacePath);
    if (!vitisInput || !xsaInput || !workspaceInput || running) return;
    if (!xsaInput.toLowerCase().endsWith(".xsa")) {
      setError("XSA alanına klasör değil, doğrudan .xsa dosyasının tam yolu verilmelidir.");
      return;
    }
    closeSocketRef.current?.();
    setEvents([]);
    setResult(null);
    setCompileIssues([]);
    setError("");
    setRunning(true);
    localStorage.setItem("spec2code.vitisPath", vitisInput);
    localStorage.setItem("spec2code.xsaPath", xsaInput);
    localStorage.setItem("spec2code.workspacePath", workspaceInput);
    localStorage.setItem("spec2code.platformName", platformName.trim());
    localStorage.setItem("spec2code.systemName", systemName.trim());
    localStorage.setItem("spec2code.appName", appName.trim());
    localStorage.setItem("spec2code.customIpDriverPolicy", customIpDriverPolicy);

    try {
      const response = await api.createVitisWorkspace(jobId, {
        vitis_path: vitisInput,
        xsa_path: xsaInput,
        workspace_path: workspaceInput,
        processor: processor.trim() || defaultProcessor,
        runtime: runtimeForVitis(project.runtime),
        platform_name: platformName.trim(),
        system_name: systemName.trim(),
        app_name: appName.trim(),
        timeout_s: 1800,
        custom_ip_driver_policy: customIpDriverPolicy,
      });

      closeSocketRef.current = openVitisSocket(
        response.vitis_job_id,
        (event) => {
          setEvents((current) => [...current, event]);
          if (event.event === "vitis.error" && typeof event.message === "string") {
            setError(event.message);
          }
          if (event.event === "vitis.compile_errors" && Array.isArray(event.issues)) {
            setCompileIssues(event.issues as VitisCompileIssue[]);
          }
          if (event.event === "vitis.done") {
            void refreshResult(response.vitis_job_id);
          }
        },
        () => {
          setRunning(false);
          void refreshResult(response.vitis_job_id);
        },
      );
    } catch (err) {
      setError(fieldError(err));
      setRunning(false);
    }
  }

  const xsaLooksLikeFile = cleanPathInput(xsaPath).toLowerCase().endsWith(".xsa");
  const canStart = Boolean(
    cleanPathInput(vitisPath) &&
    cleanPathInput(xsaPath) &&
    xsaLooksLikeFile &&
    cleanPathInput(workspacePath) &&
    platformName.trim() &&
    systemName.trim() &&
    appName.trim(),
  ) && !running;
  const workspaceReady = result?.successful === true && !error;
  const workspaceFailed = Boolean(result && (error || result.successful === false));

  return (
    <section className="rounded-lg border border-border bg-elev p-4">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <FolderCog className="h-4 w-4 text-accent" aria-hidden />
            <h3 className="text-sm font-semibold text-text">Vitis workspace</h3>
          </div>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted">
            Generate çıktısını `.xsa` ile birleştirip Windows üzerindeki Vitis/XSCT ile platform ve application workspace üretir.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-1.5">
          <Badge tone="neutral">{runtimeForVitis(project.runtime)}</Badge>
          <Badge tone="neutral">{processor || defaultProcessor}</Badge>
          <Badge tone="neutral">{platformName || `${defaultNameBase}_platform`}</Badge>
          {result ? <Badge tone={workspaceFailed ? "warn" : "ok"}>Vitis {result.vitis_version}</Badge> : null}
          {result?.requires_lwip ? <Badge tone="accent">lwIP {result.lwip_api_mode || "gerekli"}</Badge> : null}
          {result?.custom_ip_driver_policy === "keep" ? <Badge tone="neutral">custom IP keep</Badge> : null}
          {result?.custom_pl_ip_candidates?.length ? <Badge tone="warn">custom IP none {result.custom_pl_ip_candidates.length}</Badge> : null}
        </div>
      </div>

      <div className="grid gap-3">
        <div>
          <Label htmlFor="vitis-path">Vitis dizini</Label>
          <Input
            id="vitis-path"
            value={vitisPath}
            onChange={(event) => setVitisPath(event.target.value)}
            placeholder="C:\\Xilinx\\Vitis\\2024.2"
          />
        </div>
        <div>
          <Label htmlFor="xsa-path">XSA dosyası</Label>
          <Input
            id="xsa-path"
            value={xsaPath}
            onChange={(event) => setXsaPath(event.target.value)}
            placeholder="D:\\Projects\\board\\export\\board.xsa"
          />
          {xsaPath.trim() && !xsaLooksLikeFile ? (
            <p className="mt-1 text-[11px] text-danger">Klasör değil, doğrudan `.xsa` dosyasının tam yolunu gir.</p>
          ) : (
            <p className="mt-1 text-[11px] text-faint">Dosya staging içine kopyalanır; XSCT bu geçici kopyayı kullanır.</p>
          )}
        </div>
        <div>
          <Label htmlFor="workspace-path">Workspace dizini</Label>
          <Input
            id="workspace-path"
            value={workspacePath}
            onChange={(event) => setWorkspacePath(event.target.value)}
            placeholder="D:\\VitisWorkspaces\\spec2code"
          />
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        <div>
          <Label htmlFor="vitis-platform-name">Platform proje adı</Label>
          <Input
            id="vitis-platform-name"
            value={platformName}
            onChange={(event) => setPlatformName(event.target.value)}
            placeholder={`${defaultNameBase}_platform`}
          />
        </div>
        <div>
          <Label htmlFor="vitis-system-name">System proje adı</Label>
          <Input
            id="vitis-system-name"
            value={systemName}
            onChange={(event) => setSystemName(event.target.value)}
            placeholder={`${defaultNameBase}_system`}
          />
        </div>
        <div>
          <Label htmlFor="vitis-app-name">Application proje adı</Label>
          <Input
            id="vitis-app-name"
            value={appName}
            onChange={(event) => setAppName(event.target.value)}
            placeholder={`${defaultNameBase}_app`}
          />
        </div>
      </div>

      <div className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,1fr)_minmax(240px,0.8fr)_auto]">
        <div>
          <Label htmlFor="vitis-processor">Processor</Label>
          <Input
            id="vitis-processor"
            value={processor}
            onChange={(event) => setProcessor(event.target.value)}
            placeholder={defaultProcessor}
          />
        </div>
        <div>
          <Label htmlFor="vitis-custom-ip-driver">Custom PL IP driver</Label>
          <Select value={customIpDriverPolicy} onValueChange={(value) => setCustomIpDriverPolicy(value as CustomIpDriverPolicy)}>
            <SelectTrigger id="vitis-custom-ip-driver">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto_none">Auto: custom IP - none</SelectItem>
              <SelectItem value="keep">BSP default'u koru</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex items-end">
          <Button type="button" onClick={start} disabled={!canStart} className="w-full lg:w-auto">
            {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Play className="h-4 w-4" aria-hidden />}
            Workspace oluştur
          </Button>
        </div>
      </div>

      {(events.length > 0 || error || result) && (
        <div className="mt-3">
          <VitisProgress events={events} running={running} error={error} />
          <CompileIssuesPanel issues={compileIssues} />
        </div>
      )}

      {events.length > 0 && (
        <div className="mt-3 rounded-md border border-border bg-inset">
          <div className="flex items-center gap-2 border-b border-border px-3 py-2">
            <TerminalSquare className="h-3.5 w-3.5 text-accent" aria-hidden />
            <span className="text-xs font-semibold text-text">Vitis job log</span>
          </div>
          <div className="max-h-40 overflow-auto p-2">
            {events
              .filter((event) => typeof event.message === "string")
              .map((event, index) => (
                <div key={`${event.event}-${index}`} className="grid grid-cols-[76px_minmax(0,1fr)] gap-2 rounded px-2 py-1 text-[11px]">
                  <span className="font-mono text-faint">{String(event.stage ?? event.event)}</span>
                  <span className="min-w-0 text-muted">{String(event.message)}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {workspaceFailed && result && (
        <div className="mt-3 rounded-md border border-danger/30 bg-danger/10 p-3 text-[11px] leading-relaxed text-muted">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-3.5 w-3.5 text-danger" aria-hidden />
            <span className="font-semibold text-danger">Workspace tamamlanmadı</span>
            {typeof result.xsct_exit_code === "number" ? (
              <Badge tone={result.xsct_exit_code === 0 ? "warn" : "danger"}>exit {result.xsct_exit_code}</Badge>
            ) : null}
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <div>
              <span className="font-semibold text-danger">stderr log</span>
              <div className="mt-1 break-all font-mono text-text">{result.stderr_log}</div>
            </div>
            <div>
              <span className="font-semibold text-danger">stdout log</span>
              <div className="mt-1 break-all font-mono text-text">{result.stdout_log}</div>
            </div>
          </div>
          {result.xsct_stderr_tail ? (
            <div className="mt-3">
              <span className="font-semibold text-danger">stderr son satırlar</span>
              <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-danger/20 bg-bg p-2 font-mono text-[11px] text-text">
                {result.xsct_stderr_tail}
              </pre>
            </div>
          ) : null}
          {result.xsct_stdout_tail ? (
            <div className="mt-3">
              <span className="font-semibold text-muted">stdout son satırlar</span>
              <pre className="mt-1 max-h-32 overflow-auto whitespace-pre-wrap rounded border border-border bg-bg p-2 font-mono text-[11px] text-text">
                {result.xsct_stdout_tail}
              </pre>
            </div>
          ) : null}
        </div>
      )}

      {workspaceReady && result && (
        <div className="mt-3 grid gap-2 rounded-md border border-ok/30 bg-ok/10 p-3 text-[11px] leading-relaxed text-muted md:grid-cols-2">
          <div>
            <span className="font-semibold text-ok">Workspace</span>
            <div className="mt-1 break-all font-mono text-text">{result.workspace_path}</div>
          </div>
          <div>
            <span className="font-semibold text-ok">Projeler</span>
            <div className="mt-1 flex flex-wrap items-center gap-2">
              {result.platform_name ? (
                <code className="rounded border border-ok/30 bg-bg px-1 py-0.5 font-mono text-text">{result.platform_name}</code>
              ) : null}
              {result.system_name ? (
                <code className="rounded border border-ok/30 bg-bg px-1 py-0.5 font-mono text-text">{result.system_name}</code>
              ) : null}
              <code className="rounded border border-ok/30 bg-bg px-1 py-0.5 font-mono text-text">{result.app_name}</code>
              <code className="rounded border border-ok/30 bg-bg px-1 py-0.5 font-mono text-text">{result.processor}</code>
            </div>
          </div>
          <div>
            <span className="font-semibold text-ok">Script</span>
            <div className="mt-1 break-all font-mono text-text">{result.script_path}</div>
          </div>
          <div>
            <span className="font-semibold text-ok">Log</span>
            <div className="mt-1 break-all font-mono text-text">{result.stdout_log}</div>
          </div>
        </div>
      )}
    </section>
  );
}
