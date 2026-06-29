// Typed API client for the Spec2Code backend (Brief 18). Paths are relative so the Vite
// dev proxy (and production same-origin serving) both work.

import type {
  CatalogDevice,
  DescriptorMeta,
  DeviceDescriptor,
  GeneratedFile,
  KnowledgeAskRequest,
  KnowledgeAskResponse,
  ParseResult,
  PlatformInfo,
  ProjectSpec,
  TestbenchCommandRequest,
  TestbenchCommandResponse,
  DriverMatch,
  SpecValidation,
  VitisCompileIssue,
  VitisWorkspaceRequest,
  VitisWorkspaceResult,
} from "./types";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

export const api = {
  health: () => req<{ status: string; tools: Record<string, string | null> }>("/api/health"),

  platforms: () => req<{ platforms: PlatformInfo[] }>("/api/platforms").then((r) => r.platforms),

  platform: (platformId: string) =>
    req<PlatformInfo & { platform?: string }>(`/api/platforms/${encodeURIComponent(platformId)}`).then((p) => ({
      ...p,
      id: p.id ?? (p.platform as PlatformInfo["id"]),
    })),

  parseXparameters: (text: string, platform: string) =>
    req<ParseResult>("/api/xparameters/parse", {
      method: "POST",
      body: JSON.stringify({ text, platform }),
    }),

  catalog: () =>
    req<{ devices: CatalogDevice[]; statuses: Record<string, string> }>("/api/catalog"),

  descriptors: () =>
    req<{ descriptors: DescriptorMeta[] }>("/api/descriptors").then((r) => r.descriptors),

  descriptor: (part: string) =>
    req<DeviceDescriptor>(`/api/descriptors/${part}`),

  knowledgeAsk: (payload: KnowledgeAskRequest) =>
    req<KnowledgeAskResponse>("/api/knowledge/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  validate: (spec: ProjectSpec) =>
    req<SpecValidation>("/api/spec/validate", {
      method: "POST",
      body: JSON.stringify({ spec }),
    }),

  rulesetDefault: () =>
    req<{ ruleset: Record<string, unknown>; schema: Record<string, unknown> }>("/api/rulesets/default"),

  generate: (spec: ProjectSpec, max_rounds = 3) =>
    req<{ job_id: string }>("/api/generate", {
      method: "POST",
      body: JSON.stringify({ spec, max_rounds }),
    }),

  jobResult: (jobId: string) =>
    req<{
      job_id: string;
      status: string;
      error: string | null;
      result: { out_dir: string; files: string[]; qc: import("./types").QcReport } | null;
      files: GeneratedFile[];
    }>(`/api/jobs/${jobId}/result`),

  jobDownloadUrl: (jobId: string) => `/api/jobs/${encodeURIComponent(jobId)}/download`,

  jobVitisDownloadUrl: (jobId: string) => `/api/jobs/${encodeURIComponent(jobId)}/vitis`,

  createVitisWorkspace: (jobId: string, payload: VitisWorkspaceRequest) =>
    req<{ vitis_job_id: string }>(`/api/jobs/${encodeURIComponent(jobId)}/vitis/workspace`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  vitisWorkspaceResult: (vitisJobId: string) =>
    req<VitisWorkspaceResult>(`/api/vitis/jobs/${encodeURIComponent(vitisJobId)}/result`),

  mapVitisCompileErrors: (log: string) =>
    req<{ issues: VitisCompileIssue[] }>("/api/vitis/compile-errors/map", {
      method: "POST",
      body: JSON.stringify({ log }),
    }),

  testbenchCommand: (payload: TestbenchCommandRequest) =>
    req<TestbenchCommandResponse>("/api/testbench/command", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  jobFileDownloadUrl: (jobId: string, filePath: string) =>
    `/api/jobs/${encodeURIComponent(jobId)}/files/${encodePath(filePath)}`,

  scanDrivers: (folder: string) =>
    req<{ matches: DriverMatch[] }>("/api/drivers/scan", {
      method: "POST",
      body: JSON.stringify({ folder }),
    }).then((r) => r.matches),

  confirmDriver: (stem: string, part: string, role: string, files: string[]) =>
    req<{ ok: boolean }>("/api/drivers/confirm", {
      method: "POST",
      body: JSON.stringify({ stem, part, role, files }),
    }),
};

// WebSocket helper for the generate console. Returns a closer.
export function openJobSocket(
  jobId: string,
  onEvent: (e: import("./types").JobEvent) => void,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/jobs/${jobId}`);
  ws.onmessage = (m) => {
    const data = JSON.parse(m.data);
    if (data.event === "__closed__") {
      ws.close();
      onClose?.();
      return;
    }
    onEvent(data);
  };
  ws.onerror = () => onClose?.();
  return () => ws.close();
}

export function openVitisSocket(
  vitisJobId: string,
  onEvent: (e: import("./types").JobEvent) => void,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/vitis/${vitisJobId}`);
  ws.onmessage = (m) => {
    const data = JSON.parse(m.data);
    if (data.event === "__closed__") {
      ws.close();
      onClose?.();
      return;
    }
    onEvent(data);
  };
  ws.onerror = () => onClose?.();
  return () => ws.close();
}
