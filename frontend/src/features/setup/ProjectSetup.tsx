import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PLATFORM_LABELS, RUNTIMES, useStore } from "@/store/useStore";
import type { PlatformId, PlatformInfo } from "@/lib/types";
import {
  Badge,
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
  const llm = useStore((s) => s.llm);
  const setLlm = useStore((s) => s.setLlm);
  const [platforms, setPlatforms] = useState<PlatformInfo[]>([]);

  useEffect(() => {
    api.platforms().then(setPlatforms).catch(() => setPlatforms([]));
  }, []);

  const current = platforms.find((p) => p.id === project.platform);
  const cores = current?.cores ?? [];

  return (
    <Card className="p-5">
      <h2 className="mb-4 text-sm font-semibold text-text">Project</h2>
      <div className="space-y-4">
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
          <Input value="std/default.ruleset.json" readOnly className="text-faint" />
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
      </div>
    </Card>
  );
}
