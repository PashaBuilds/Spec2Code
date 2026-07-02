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
  TestbenchSessionConnectRequest,
  TestbenchSessionStatus,
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

  testbenchConnect: (payload: TestbenchSessionConnectRequest) =>
    req<TestbenchSessionStatus>("/api/testbench/session/connect", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  testbenchDisconnect: (sessionId: string) =>
    req<TestbenchSessionStatus>("/api/testbench/session/disconnect", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    }),

  testbenchSessionStatus: (sessionId: string) =>
    req<TestbenchSessionStatus>(`/api/testbench/session/${encodeURIComponent(sessionId)}`),

  testbenchSerialPorts: () =>
    req<{ ports: import("./types").SerialPortInfo[] }>("/api/testbench/serial/ports").then((r) => r.ports),

  testbenchConsoleRead: (sessionId: string, since: number) =>
    req<{ seq: number; entries: import("./types").SerialConsoleEntry[] }>("/api/testbench/console/read", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, since }),
    }),

  testbenchConsoleWrite: (sessionId: string, text: string) =>
    req<{ ok: boolean }>("/api/testbench/console/write", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, text }),
    }),

  runOnBoard: (payload: import("./types").RunOnBoardRequest) =>
    req<{ runboard_job_id: string }>("/api/vitis/run-on-board", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  runOnBoardResult: (jobId: string) =>
    req<import("./types").RunOnBoardResult>(`/api/vitis/run-on-board/${encodeURIComponent(jobId)}/result`),

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

export function openRunboardSocket(
  jobId: string,
  onEvent: (e: import("./types").JobEvent) => void,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/runboard/${jobId}`);
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
