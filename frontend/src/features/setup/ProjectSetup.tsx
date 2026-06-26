import { useEffect, useRef, useState } from "react";
import { Download, FileJson, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { PLATFORM_LABELS, RUNTIMES, useStore } from "@/store/useStore";
import type { PlatformId, PlatformInfo, ProjectSpec } from "@/lib/types";
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

export default function ProjectSetup() {
  const project = useStore((s) => s.project);
  const setProject = useStore((s) => s.setProject);
  const codingStandardRef = useStore((s) => s.codingStandardRef);
  const setCodingStandardRef = useStore((s) => s.setCodingStandardRef);
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
    <Card className="p-5">
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

        <div className="space-y-1.5">
          <Label>Coding standard</Label>
          <Input
            value={codingStandardRef}
            onChange={(e) => setCodingStandardRef(e.target.value)}
            placeholder="std/default.ruleset.json"
          />
        </div>

        <div className="rounded-md border border-border bg-inset p-3">
          <label className="flex cursor-pointer items-center justify-between">
            <span className="flex items-center gap-2 text-sm text-text">
              LLM optimization
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
            Deterministic by default. When on, an OpenAI-compatible endpoint produces an optimized
            variant on top (QC still gates it).
          </p>
          {llm.enabled && (
            <div className="mt-3 space-y-2">
              <Input
                value={llm.base_url ?? ""}
                onChange={(e) => setLlm({ base_url: e.target.value })}
                placeholder="base_url (e.g. http://localhost:1234/v1)"
              />
              <div className="grid grid-cols-2 gap-2">
                <Input value={llm.model ?? ""} onChange={(e) => setLlm({ model: e.target.value })} placeholder="model" />
                <Input
                  value={llm.api_key ?? ""}
                  onChange={(e) => setLlm({ api_key: e.target.value })}
                  placeholder="api_key (optional)"
                  type="password"
                />
              </div>
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
    </Card>
  );
}
