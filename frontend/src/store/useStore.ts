import { create } from "zustand";
import type {
  CatalogDevice,
  Controller,
  Core,
  DescriptorMeta,
  Device,
  GeneratedFile,
  JobEvent,
  LlmConfig,
  Mux,
  PlatformId,
  ProjectMeta,
  ProjectSpec,
  QcReport,
  Runtime,
  Zone,
} from "@/lib/types";

export type Step = "setup" | "schematic" | "generate";

interface JobState {
  id: string | null;
  status: "idle" | "running" | "done" | "error";
  events: JobEvent[];
  files: GeneratedFile[];
  qc: QcReport | null;
}

interface StoreState {
  step: Step;
  project: ProjectMeta;
  codingStandardRef: string;
  llm: LlmConfig;

  zones: Zone[];
  cores: Core[];
  controllers: Controller[];
  unmatched: { instance: string; base_address: string; reason: string }[];
  muxes: Mux[];
  devices: Device[];

  catalog: CatalogDevice[];
  descriptors: DescriptorMeta[];

  selectedId: string | null;
  job: JobState;
  counter: number;

  // actions
  setStep: (s: Step) => void;
  setProject: (p: Partial<ProjectMeta>) => void;
  setLlm: (p: Partial<LlmConfig>) => void;
  applyParse: (r: {
    controllers: Controller[];
    unmatched: { instance: string; base_address: string; reason: string }[];
    zones: Zone[];
    cores: Core[];
  }) => void;
  loadSpec: (spec: ProjectSpec, context?: { zones?: Zone[]; cores?: Core[] }) => void;
  setCatalog: (c: CatalogDevice[]) => void;
  setDescriptors: (d: DescriptorMeta[]) => void;
  select: (id: string | null) => void;

  addMux: (m: Omit<Mux, "id">) => string;
  addDevice: (d: Omit<Device, "id">) => string;
  updateDevice: (id: string, patch: Partial<Device>) => void;
  updateDeviceAttach: (id: string, patch: Partial<Device["attach"]>) => void;
  removeNode: (id: string) => void;

  buildSpec: () => ProjectSpec;

  setJob: (patch: Partial<JobState>) => void;
  pushEvent: (e: JobEvent) => void;
  resetJob: () => void;
}

const DEFAULT_PROJECT: ProjectMeta = {
  name: "my_io_board",
  platform: "zynq_ultrascale",
  target_core: "a53_0",
  runtime: "freertos",
  output_mode: "dropin",
};

const DEFAULT_CODING_STANDARD = "std/default.ruleset.json";
const DEFAULT_LLM: LlmConfig = {
  enabled: false,
  base_url: "",
  model: "",
  api_key: "",
  timeout_s: 120,
  max_tokens: 4096,
  max_response_chars: 120000,
  retries: 0,
};
const slug = (part: string) => part.toLowerCase().replace(/[^a-z0-9]/g, "");

function inferCounter(muxes: Mux[], devices: Device[]): number {
  return Math.max(
    0,
    ...[...muxes.map((m) => m.id), ...devices.map((d) => d.id)].map((id) => {
      const match = /^u(\d+)_/.exec(id);
      return match ? Number(match[1]) : 0;
    }),
  );
}

export const useStore = create<StoreState>((set, get) => ({
  step: "setup",
  project: { ...DEFAULT_PROJECT },
  codingStandardRef: DEFAULT_CODING_STANDARD,
  llm: { ...DEFAULT_LLM },

  zones: [],
  cores: [],
  controllers: [],
  unmatched: [],
  muxes: [],
  devices: [],

  catalog: [],
  descriptors: [],

  selectedId: null,
  job: { id: null, status: "idle", events: [], files: [], qc: null },
  counter: 0,

  setStep: (step) => set({ step }),
  setProject: (p) => set((s) => ({ project: { ...s.project, ...p } })),
  setLlm: (p) => set((s) => ({ llm: { ...s.llm, ...p } })),

  applyParse: (r) =>
    set({
      controllers: r.controllers,
      unmatched: r.unmatched ?? [],
      zones: r.zones ?? [],
      cores: r.cores ?? [],
      muxes: [],
      devices: [],
      selectedId: null,
    }),

  loadSpec: (spec, context) =>
    set({
      step: spec.controllers?.length ? "schematic" : "setup",
      project: { ...DEFAULT_PROJECT, ...spec.project },
      codingStandardRef: DEFAULT_CODING_STANDARD,
      llm: spec.llm?.enabled
        ? { ...DEFAULT_LLM, ...spec.llm }
        : { ...DEFAULT_LLM },
      zones: context?.zones ?? [],
      cores: context?.cores ?? [],
      controllers: spec.controllers ?? [],
      muxes: spec.muxes ?? [],
      devices: spec.devices ?? [],
      unmatched: [],
      selectedId: null,
      counter: inferCounter(spec.muxes ?? [], spec.devices ?? []),
      job: { id: null, status: "idle", events: [], files: [], qc: null },
    }),

  setCatalog: (catalog) => set({ catalog }),
  setDescriptors: (descriptors) => set({ descriptors }),
  select: (selectedId) => set({ selectedId }),

  addMux: (m) => {
    const n = get().counter + 1;
    const id = `u${n}_${slug(m.part)}`;
    set((s) => ({ muxes: [...s.muxes, { ...m, id }], counter: n, selectedId: id }));
    return id;
  },

  addDevice: (d) => {
    const n = get().counter + 1;
    const id = `u${n}_${slug(d.part)}`;
    set((s) => ({ devices: [...s.devices, { ...d, id }], counter: n, selectedId: id }));
    return id;
  },

  updateDevice: (id, patch) =>
    set((s) => ({ devices: s.devices.map((d) => (d.id === id ? { ...d, ...patch } : d)) })),

  updateDeviceAttach: (id, patch) =>
    set((s) => ({
      devices: s.devices.map((d) =>
        d.id === id ? { ...d, attach: { ...d.attach, ...patch } } : d,
      ),
    })),

  removeNode: (id) =>
    set((s) => ({
      devices: s.devices
        .filter((d) => d.id !== id)
        .map((d) =>
          d.attach.via_mux?.mux_id === id
            ? { ...d, attach: { ...d.attach, via_mux: null } }
            : d,
        ),
      // remove a mux and detach any device that used it
      muxes: s.muxes.filter((m) => m.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
    })),

  buildSpec: () => {
    const s = get();
    return {
      schema_version: "1.0",
      project: s.project,
      coding_standard_ref: DEFAULT_CODING_STANDARD,
      llm: s.llm.enabled
        ? s.llm
        : { enabled: false },
      controllers: s.controllers,
      devices: s.devices,
      muxes: s.muxes,
      generation_options: { qc_max_rounds: 3, include_doxygen: true, line_ending: "crlf" },
    };
  },

  setJob: (patch) => set((s) => ({ job: { ...s.job, ...patch } })),
  pushEvent: (e) => set((s) => ({ job: { ...s.job, events: [...s.job.events, e] } })),
  resetJob: () => set({ job: { id: null, status: "idle", events: [], files: [], qc: null } }),
}));

export const PLATFORM_LABELS: Record<PlatformId, string> = {
  zynq_7000: "Zynq-7000",
  zynq_ultrascale: "Zynq UltraScale+",
  versal: "Versal ACAP",
  microblaze_7series: "MicroBlaze (7-series)",
};

export const RUNTIMES: Runtime[] = ["bare_metal", "freertos"];
