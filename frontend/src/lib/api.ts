// Typed API client for the Spec2Code backend (Brief 18). Paths are relative so the Vite
// dev proxy (and production same-origin serving) both work.

import type {
  CatalogDevice,
  DescriptorMeta,
  DeviceDescriptor,
  GeneratedFile,
  KnowledgeAskRequest,
  KnowledgeAskResponse,
  PlatformInfo,
  ProjectSpec,
  TestbenchCommandRequest,
  TestbenchCommandResponse,
  TestbenchSessionConnectRequest,
  TestbenchSessionStatus,
  DriverMatch,
  SpecValidation,
  UserDescriptorEntry,
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

  parseXsaPath: (path: string) =>
    req<import("./types").XsaParseResult>("/api/xsa/parse", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  uploadXsa: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch("/api/xsa/upload", { method: "POST", body: form });
    if (!res.ok) {
      let detail: unknown = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {
        /* ignore */
      }
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return res.json() as Promise<import("./types").XsaParseResult>;
  },

  catalog: () =>
    req<{ devices: CatalogDevice[]; statuses: Record<string, string> }>("/api/catalog"),

  descriptors: () =>
    req<{ descriptors: DescriptorMeta[] }>("/api/descriptors").then((r) => r.descriptors),

  descriptor: (part: string) =>
    req<DeviceDescriptor>(`/api/descriptors/${part}`),

  userDescriptors: () =>
    req<{ dir: string; descriptors: UserDescriptorEntry[] }>("/api/user-descriptors"),

  userDescriptorExample: () =>
    req<{ file: string; content: string }>("/api/user-descriptors/example"),

  validateUserDescriptor: (content: string) =>
    req<{ valid: boolean; errors: string[]; part: string | null }>("/api/user-descriptors/validate", {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  uploadUserDescriptor: (content: string) =>
    req<{ saved: string; part: string; dir: string; overrides_builtin: boolean }>("/api/user-descriptors", {
      method: "POST",
      body: JSON.stringify({ content }),
    }),

  deleteUserDescriptor: (fileName: string) =>
    req<{ deleted: string }>(`/api/user-descriptors/${encodeURIComponent(fileName)}`, { method: "DELETE" }),

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

  registerMapValidate: (document: unknown) =>
    req<{ valid: boolean; errors: string[] }>("/api/register-map/validate", {
      method: "POST", body: JSON.stringify({ document }),
    }),

  registerMapGenerate: (document: unknown) =>
    req<{ files: Record<string, string> }>("/api/register-map/generate", {
      method: "POST", body: JSON.stringify({ document }),
    }),

  registerMapExportHtml: (document: unknown) =>
    req<{ html: string }>("/api/register-map/export-html", {
      method: "POST", body: JSON.stringify({ document }),
    }),

  registerMapImportHtml: (html: string) =>
    req<{ document: unknown; valid: boolean; errors: string[] }>("/api/register-map/import-html", {
      method: "POST", body: JSON.stringify({ html }),
    }),

  registerMapExportXlsx: (document: unknown) =>
    req<{ xlsx_base64: string }>("/api/register-map/export-xlsx", {
      method: "POST", body: JSON.stringify({ document }),
    }),

  registerMapImportXlsx: (xlsx_base64: string) =>
    req<{ document: unknown; valid: boolean; errors: string[] }>("/api/register-map/import-xlsx", {
      method: "POST", body: JSON.stringify({ xlsx_base64 }),
    }),

  registerMapExample: () =>
    req<{ document: unknown; html: string }>("/api/register-map/example"),

  vivadoDdrParts: () =>
    req<{
      zynq_ultrascale: Array<{
        id: string; label: string; description: string;
        device_capacity: string; dram_width: string;
        speed_bins: string[]; default_speed_bin: string;
        bus_widths: string[]; chip_gb: number;
      }>;
    }>("/api/vivado/ddr-parts"),

  vivadoMioOptions: () =>
    req<{ zynq_ultrascale: Record<string, { width: number; default: string; options: string[] }> }>(
      "/api/vivado/mio-options",
    ),

  vivadoDesignStart: (payload: {
    vivado_path: string;
    platform: string;
    part: string;
    temp_path: string;
    design_name: string;
    peripherals: Array<{ kind: string; mio: string; qspi_mode?: string; qspi_data_mode?: string; qspi_fbclk?: boolean }>;
    ref_clk_mhz: string;
    ddr_mode: string;
    ddr_params: Record<string, string>;
    ddr_model: string;
    ddr_bus_width: string;
    ddr_speed_bin: string;
    make_bitstream: boolean;
    timeout_s: number;
  }) =>
    req<{ vivado_job_id: string }>("/api/vivado/design", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  vivadoParts: (payload: { vivado_path: string; refresh?: boolean; cached_only?: boolean }) =>
    req<{
      platforms: Record<string, Record<string, string[]>> | null;
      total: number;
      cached: boolean;
    }>("/api/vivado/parts", { method: "POST", body: JSON.stringify(payload) }),

  vivadoDesignResult: (vivadoJobId: string) =>
    req<{
      vivado_job_id: string;
      status: string;
      error: string | null;
      result: { successful?: boolean; xsa_path?: string; image_path?: string; xsa_bit_path?: string } | null;
    }>(`/api/vivado/jobs/${encodeURIComponent(vivadoJobId)}/result`),

  mapVitisCompileErrors: (log: string) =>
    req<{ issues: VitisCompileIssue[] }>("/api/vitis/compile-errors/map", {
      method: "POST",
      body: JSON.stringify({ log }),
    }),

  testbenchCommand: async (payload: TestbenchCommandRequest) => {
    const startedAt = performance.now();
    const record = (ok: boolean, detail: string) => {
      // Host-initiated transactions feed the Test Bench timeline.
      import("@/store/useStore").then(({ useStore }) => {
        useStore.getState().pushBusLog({
          at: Date.now(),
          device: payload.device,
          operation: payload.operation,
          ok,
          duration_ms: Math.round(performance.now() - startedAt),
          detail,
        });
      }).catch(() => undefined);
    };
    try {
      const response = await req<TestbenchCommandResponse>("/api/testbench/command", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      record(response.parsed.ok === "1", response.parsed.value || response.parsed.data || response.parsed.message || "");
      return response;
    } catch (err) {
      record(false, err instanceof Error ? err.message : String(err));
      throw err;
    }
  },

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

  testbenchTraffic: (sessionId: string, since: number) =>
    req<{ seq: number; entries: import("./types").TrafficEntry[] }>("/api/testbench/traffic", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, since }),
    }),

  testbenchSessions: () =>
    req<{ sessions: import("./types").TestbenchSessionStatus[] }>("/api/testbench/sessions").then((r) => r.sessions),

  runOnBoard: (payload: import("./types").RunOnBoardRequest) =>
    req<{ runboard_job_id: string }>("/api/vitis/run-on-board", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  runOnBoardResult: (jobId: string) =>
    req<import("./types").RunOnBoardResult>(`/api/vitis/run-on-board/${encodeURIComponent(jobId)}/result`),

  bringupStart: (payload: { session_id: string; manifest: import("./types").TestbenchManifest; include_init?: boolean; timeout_s?: number }) =>
    req<{ bringup_job_id: string }>("/api/bringup/start", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  bringupResult: (jobId: string) =>
    req<import("./types").BringupResult>(`/api/bringup/${encodeURIComponent(jobId)}/result`),

  bringupCertificateUrl: (jobId: string) => `/api/bringup/${encodeURIComponent(jobId)}/certificate`,

  registerSnapshot: (payload: { session_id: string; device_id: string; registers: Array<{ name: string; offset: number }>; timeout_s?: number }) =>
    req<import("./types").RegisterSnapshot>("/api/registers/snapshot", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  i2cScan: (payload: { session_id: string; controller_id: string; muxes: Array<{ id: string; part?: string; address: number; channels: number }>; timeout_s?: number }) =>
    req<import("./types").I2cScanResult>("/api/testbench/i2c-scan", {
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

export function openBringupSocket(
  jobId: string,
  onEvent: (e: import("./types").JobEvent) => void,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/bringup/${jobId}`);
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

export function openVivadoSocket(
  vivadoJobId: string,
  onEvent: (e: Record<string, unknown>) => void,
  onClose?: () => void,
): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/vivado/${vivadoJobId}`);
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
