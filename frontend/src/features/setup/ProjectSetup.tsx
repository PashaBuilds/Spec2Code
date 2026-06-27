import { useEffect, useRef, useState } from "react";
import { Download, FileJson, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { PLATFORM_LABELS, RUNTIMES, useStore } from "@/store/useStore";
import type { LlmConfig, PlatformId, PlatformInfo, ProjectSpec } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";
import { VisualBackdrop } from "@/components/visuals";

const PREFIXES = [
  ["unsigned char", "uc"],
  ["char", "c"],
  ["unsigned short", "us"],
  ["short", "s"],
  ["unsigned int", "ui"],
  ["int", "i"],
  ["unsigned long", "ul"],
  ["unsigned long long", "ull"],
];

export default function ProjectSetup() {
  const project = useStore((s) => s.project);
  const setProject = useStore((s) => s.setProject);
  const codingStandardRef = useStore((s) => s.codingStandardRef);
  const llm = useStore((s) => s.llm);
  const setLlm = useStore((s) => s.setLlm);
  const buildSpec = useStore((s) => s.buildSpec);
  const loadSpec = useStore((s) => s.loadSpec);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);
  const [tools, setTools] = useState<Record<string, string | null>>({});
  const [projectIoMessage, setProjectIoMessage] = useState<string | null>(null);
  const [projectIoError, setProjectIoError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    api.platforms().then(setPlatforms).catch(() => setPlatforms([]));
    api.health().then((h) => setTools(h.tools)).catch(() => setTools({}));
  }, []);

  const current = platforms.find((p) => p.id === project.platform);
  const cores = current?.cores ?? [];
  const setLlmNumber = (
    key: "timeout_s" | "max_tokens" | "max_response_chars" | "retries",
    value: string,
  ) => {
    setLlm({ [key]: value === "" ? undefined : Number(value) } as Partial<LlmConfig>);
  };

  function downloadSpec() {
    setProjectIoMessage(null);
    setProjectIoError(null);
    const spec = buildSpec();
    const blob = new Blob([JSON.stringify(spec, null, 2) + "\n"], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${spec.project.name}.project.spec.json`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setProjectIoMessage("project.spec.json exported");
  }

  async function loadProjectSpec(file: File | undefined) {
    if (!file) return;
    setProjectIoMessage(null);
    setProjectIoError(null);
    try {
      const spec = JSON.parse(await file.text()) as ProjectSpec;
      const validation = await api.validate(spec);
      if (!validation.valid) {
        throw new Error(validation.errors.map((e) => `${e.path}: ${e.message}`).join("; "));
      }
      const platform = await api.platform(spec.project.platform);
      loadSpec(spec, { zones: platform.zones, cores: platform.cores });
      setProjectIoMessage(`${file.name} loaded`);
    } catch (err) {
      setProjectIoError(err instanceof Error ? err.message : String(err));
    } finally {
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <Card className="relative overflow-hidden p-5">
      <VisualBackdrop asset="setup" className="h-32" opacity={0.42} position="right top" mask="header" />
      <div className="relative z-10">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-text">Project</h2>
        <div className="flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={(e) => void loadProjectSpec(e.target.files?.[0])}
          />
          <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
            <Upload className="h-4 w-4" /> Load
          </Button>
          <Button variant="outline" size="sm" onClick={downloadSpec}>
            <Download className="h-4 w-4" /> Save
          </Button>
        </div>
      </div>
      <div className="space-y-4">
        {(projectIoMessage || projectIoError) && (
          <div
            className={
              projectIoError
                ? "rounded-md border border-danger/40 bg-danger/15 px-3 py-2 text-xs text-danger"
                : "rounded-md border border-ok/30 bg-ok/10 px-3 py-2 text-xs text-ok"
            }
          >
            {projectIoError ?? projectIoMessage}
          </div>
        )}

        <div className="space-y-1.5">
          <Label>Project name</Label>
          <Input
            value={project.name}
            onChange={(e) => setProject({ name: e.target.value.replace(/[^A-Za-z0-9_]/g, "_") })}
            placeholder="radar_io_board"
          />
        </div>

        <div className="space-y-1.5">
          <Label>Platform</Label>
          <Select
            value={project.platform}
            onValueChange={(v) => {
              const p = platforms.find((x) => x.id === (v as PlatformId));
              setProject({ platform: v as PlatformId, target_core: p?.cores[0]?.id ?? project.target_core });
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(PLATFORM_LABELS) as PlatformId[]).map((id) => (
                <SelectItem key={id} value={id}>
                  {PLATFORM_LABELS[id]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {current && <p className="text-xs text-faint">{current.summary}</p>}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Target core</Label>
            <Select value={project.target_core} onValueChange={(v) => setProject({ target_core: v })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {cores.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Runtime</Label>
            <Select value={project.runtime} onValueChange={(v) => setProject({ runtime: v as never })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RUNTIMES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {r === "freertos" ? "FreeRTOS" : "bare-metal"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-sm text-text">
              <FileJson className="h-4 w-4 text-accent" />
              Sabit kodlama standardi
            </div>
            <Badge tone="neutral">{codingStandardRef}</Badge>
          </div>
          <div className="space-y-2 text-xs text-muted">
            <p>
              Generate ve QC her zaman default ruleset ile calisir; Word/JSON standard import
              akisi kullanilmaz.
            </p>
            <div className="grid grid-cols-2 gap-2">
              {PREFIXES.map(([type, prefix]) => (
                <div key={type} className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-faint">{type}</span>
                  <span className="font-mono text-text">{prefix}</span>
                </div>
              ))}
            </div>
            <div className="grid gap-1 font-mono text-[11px] text-faint">
              <span>camelCase identifiers, Allman braces, 4 spaces, CRLF</span>
              <span>struct S*, enum E*, struct pointer sp, arrays prefix+Arr</span>
              <span>global G_ + prefix, static S_ + prefix</span>
            </div>
          </div>
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <label className="flex cursor-pointer items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-text">
              LLM assist
              <Badge tone={llm.enabled ? "accent" : "neutral"}>{llm.enabled ? "on" : "off"}</Badge>
            </span>
            <input
              type="checkbox"
              checked={llm.enabled}
              onChange={(e) => setLlm({ enabled: e.target.checked })}
              className="h-4 w-4 accent-[var(--accent)]"
            />
          </label>
          <p className="mt-1 text-xs text-faint">
            Deterministic by default. When on, an OpenAI-compatible endpoint can assist QC fixes
            (QC still gates every accepted change).
          </p>
          {llm.enabled && (
            <div className="mt-3 space-y-2">
              <Input
                value={llm.base_url ?? ""}
                onChange={(e) => setLlm({ base_url: e.target.value })}
                placeholder="base_url (e.g. http://localhost:1234/v1)"
              />
              <Input
                value={llm.model ?? ""}
                onChange={(e) => setLlm({ model: e.target.value })}
                placeholder="exact model name exposed by the server"
              />
              <div className="grid grid-cols-2 gap-2">
                <Input
                  value={llm.api_key ?? ""}
                  onChange={(e) => setLlm({ api_key: e.target.value })}
                  placeholder="api_key (optional)"
                  type="password"
                />
                <Input
                  type="number"
                  min={1}
                  value={llm.timeout_s ?? ""}
                  onChange={(e) => setLlmNumber("timeout_s", e.target.value)}
                  placeholder="timeout seconds"
                />
              </div>
              <div className="grid grid-cols-3 gap-2">
                <Input
                  type="number"
                  min={128}
                  value={llm.max_tokens ?? ""}
                  onChange={(e) => setLlmNumber("max_tokens", e.target.value)}
                  placeholder="max_tokens"
                />
                <Input
                  type="number"
                  min={1024}
                  value={llm.max_response_chars ?? ""}
                  onChange={(e) => setLlmNumber("max_response_chars", e.target.value)}
                  placeholder="max chars"
                />
                <Input
                  type="number"
                  min={0}
                  max={3}
                  value={llm.retries ?? ""}
                  onChange={(e) => setLlmNumber("retries", e.target.value)}
                  placeholder="retries"
                />
              </div>
              <p className="text-[11px] text-faint">
                Enter the exact model id from the OpenAI-compatible server, e.g. a Kimi or Qwen model name.
              </p>
            </div>
          )}
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <div className="mb-2 flex items-center gap-2 text-sm text-text">
            <FileJson className="h-4 w-4 text-accent" />
            Toolchain
          </div>
          <div className="grid grid-cols-2 gap-2">
            {["clang-format", "clang-tidy", "cppcheck", "libclang"].map((name) => (
              <div key={name} className="flex min-w-0 items-center justify-between gap-2">
                <span className="truncate font-mono text-[11px] text-muted">{name}</span>
                <Badge tone={tools[name] ? "ok" : "warn"}>{tools[name] ? "ok" : "missing"}</Badge>
              </div>
            ))}
          </div>
        </div>
      </div>
      </div>
    </Card>
  );
}
