import { create } from "zustand";
import { persist } from "zustand/middleware";
import type {
  Board,
  CatalogDevice,
  Connector,
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
import { MAIN_BOARD_ID, boardNodeId, boardSlug, mainBoardId, uniqueId } from "@/lib/boards";

export type Step = "setup" | "schematic" | "generate";

export interface BusLogEntry {
  at: number;
  device: string;
  operation: string;
  ok: boolean;
  duration_ms: number;
  detail: string;
}

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
  /** Fiziksel kartlar. BOS = kart katmani kapali (kanvas ve uretilen cikti
   *  bugunkuyle birebir ayni kalir). Ilk kart eklendiginde ANA kart olur. */
  boards: Board[];
  connectors: Connector[];
  /** Yalniz UI: kullanicinin buyuttugu kart kutusu olculeri. Spec'e GITMEZ
   *  (sema boards[] icin additionalProperties:false). */
  boardSizes: Record<string, { w: number; h: number }>;

  catalog: CatalogDevice[];
  descriptors: DescriptorMeta[];

  selectedId: string | null;
  job: JobState;
  previousFiles: GeneratedFile[];
  counter: number;

  /** Canlı telemetri: şematikteki cihaz node'larında gösterilen son okumalar. */
  telemetry: Record<string, { text: string; at: number }>;
  setTelemetry: (deviceId: string, text: string) => void;
  clearTelemetry: () => void;

  /** Host'tan gönderilen S2C işlemlerinin kronolojik kaydı (timeline). */
  busLog: BusLogEntry[];
  pushBusLog: (entry: BusLogEntry) => void;

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

  addBoard: (name: string) => string;
  renameBoard: (id: string, name: string) => void;
  updateBoard: (id: string, patch: Partial<Omit<Board, "id">>) => void;
  deleteBoard: (id: string) => void;
  /** Cihaz VEYA mux'u bir karta tasir (sematikte surukle-birak). */
  setDeviceBoard: (deviceId: string, boardId: string) => void;
  setBoardSize: (id: string, size: { w: number; h: number }) => void;
  addConnector: (c: Omit<Connector, "id">) => string;
  updateConnector: (id: string, patch: Partial<Omit<Connector, "id">>) => void;
  deleteConnector: (id: string) => void;

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
  testbench_transport: "auto",
};

const DEFAULT_CODING_STANDARD = "std/default.ruleset.json";
const DEFAULT_SAFE_OPERATIONS_BY_PART: Record<string, string[]> = {
  LMK04832: [
    "pll1_lock_detect",
    "pll1_lock_loss",
    "pll2_lock_detect",
    "pll2_lock_loss",
  ],
};
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

/** `board_id` alanini tamamen kaldirir (undefined birakmak yerine) — kart
 *  tanimsiz projede spec'e bu anahtar HIC girmemeli. */
function withoutBoardId<T extends { board_id?: string }>(item: T): T {
  if (item.board_id === undefined) return item;
  const next = { ...item };
  delete next.board_id;
  return next;
}

/** Sema boards[]/connectors[] icin additionalProperties:false; bos notlar ve
 *  null via_mux gonderilmez (null, "type: object" dogrulamasini kirar). */
function specBoard(board: Board): Board {
  const clean: Board = { id: board.id, name: board.name, role: board.role };
  if (board.notes && board.notes.trim()) clean.notes = board.notes.trim();
  return clean;
}

function specConnector(connector: Connector): Connector {
  const clean: Connector = {
    id: connector.id,
    name: connector.name,
    from_board: connector.from_board,
    to_board: connector.to_board,
    bus: { controller_id: connector.bus.controller_id },
  };
  const via = connector.bus.via_mux;
  if (via) clean.bus.via_mux = { mux_id: via.mux_id, channel: via.channel };
  if (connector.notes && connector.notes.trim()) clean.notes = connector.notes.trim();
  return clean;
}

function inferCounter(muxes: Mux[], devices: Device[]): number {
  return Math.max(
    0,
    ...[...muxes.map((m) => m.id), ...devices.map((d) => d.id)].map((id) => {
      const match = /^u(\d+)_/.exec(id);
      return match ? Number(match[1]) : 0;
    }),
  );
}

function withDefaultSafeOperations(devices: Device[], descriptors: DescriptorMeta[]): Device[] {
  if (!devices.length || !descriptors.length) return devices;
  const operationsByPart = new Map(
    descriptors.map((descriptor) => [descriptor.part.toUpperCase(), descriptor.operations]),
  );

  return devices.map((device) => {
    const part = device.part.toUpperCase();
    const defaultOps = DEFAULT_SAFE_OPERATIONS_BY_PART[part] ?? [];
    if (!defaultOps.length) return device;

    const descriptorOps = operationsByPart.get(part) ?? [];
    const selectableOps = defaultOps.filter((op) => descriptorOps.includes(op));
    if (!selectableOps.length) return device;

    const requested = device.operations_requested ?? [];
    const hasOnlyInit = requested.length === 1 && requested[0] === "device_init";
    if (!hasOnlyInit) return device;

    const nextRequested = descriptorOps.filter(
      (op) => op === "device_init" || selectableOps.includes(op),
    );
    return { ...device, operations_requested: nextRequested };
  });
}

// Proje/şema/cihazlar tarayıcıda kalıcıdır: sayfa yenilense de emek kaybolmaz.
// Üretilen dosya içerikleri (job.files) bilinçli olarak persist edilmez —
// localStorage kotasını zorlar; testbench manifest'i zaten ayrıca cache'lenir.
export const useStore = create<StoreState>()(persist((set, get) => ({
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
  boards: [],
  connectors: [],
  boardSizes: {},

  catalog: [],
  descriptors: [],

  selectedId: null,
  job: { id: null, status: "idle", events: [], files: [], qc: null },
  previousFiles: [],
  counter: 0,

  telemetry: {},
  setTelemetry: (deviceId, text) =>
    set((s) => ({ telemetry: { ...s.telemetry, [deviceId]: { text, at: Date.now() } } })),
  clearTelemetry: () => set({ telemetry: {} }),

  busLog: [],
  pushBusLog: (entry) => set((s) => ({ busLog: [...s.busLog, entry].slice(-200) })),

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
      // Yeni tasarim = yeni topoloji: kartlar da sifirlanir.
      boards: [],
      connectors: [],
      boardSizes: {},
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
      devices: withDefaultSafeOperations(spec.devices ?? [], get().descriptors),
      boards: spec.boards ?? [],
      connectors: spec.connectors ?? [],
      boardSizes: {},
      unmatched: [],
      selectedId: null,
      counter: inferCounter(spec.muxes ?? [], spec.devices ?? []),
      job: { id: null, status: "idle", events: [], files: [], qc: null },
      previousFiles: [],
    }),

  setCatalog: (catalog) => set({ catalog }),
  setDescriptors: (descriptors) =>
    set((s) => ({ descriptors, devices: withDefaultSafeOperations(s.devices, descriptors) })),
  select: (selectedId) => set({ selectedId }),

  // Kart tanimliyken yeni birim varsayilan olarak ANA KARTA duser; kart
  // tanimsizken board_id anahtari hic yazilmaz (kartsiz cikti degismez).
  addMux: (m) => {
    const s0 = get();
    const n = s0.counter + 1;
    const id = `u${n}_${slug(m.part)}`;
    const board = s0.boards.length ? { board_id: mainBoardId(s0.boards) } : {};
    set((s) => ({ muxes: [...s.muxes, { ...m, ...board, id }], counter: n, selectedId: id }));
    return id;
  },

  addDevice: (d) => {
    const s0 = get();
    const n = s0.counter + 1;
    const id = `u${n}_${slug(d.part)}`;
    const board = s0.boards.length ? { board_id: mainBoardId(s0.boards) } : {};
    set((s) => ({ devices: [...s.devices, { ...d, ...board, id }], counter: n, selectedId: id }));
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

  // İlk "Kart ekle" ANA kartı yaratır ve mevcut her şeyi ona taşır: kartsız
  // proje ile birebir aynı topoloji, artık adı var.
  addBoard: (name) => {
    const s0 = get();
    const first = s0.boards.length === 0;
    const label = (name ?? "").trim() || (first ? "Ana Kart" : `Kart ${s0.boards.length + 1}`);
    const id = first
      ? MAIN_BOARD_ID
      : uniqueId(boardSlug(label, `kart_${s0.boards.length + 1}`), s0.boards.map((b) => b.id));
    const board: Board = { id, name: label, role: first ? "main" : "peripheral" };
    set((s) => ({
      boards: [...s.boards, board],
      devices: first ? s.devices.map((d) => ({ ...d, board_id: id })) : s.devices,
      muxes: first ? s.muxes.map((m) => ({ ...m, board_id: id })) : s.muxes,
      selectedId: boardNodeId(id),
    }));
    return id;
  },

  renameBoard: (id, name) =>
    set((s) => ({
      boards: s.boards.map((b) => (b.id === id ? { ...b, name: name.trim() || b.name } : b)),
    })),

  updateBoard: (id, patch) =>
    set((s) => ({ boards: s.boards.map((b) => (b.id === id ? { ...b, ...patch } : b)) })),

  // Silinen kartin cihazlari ANA KARTA duser (asla kaybolmaz). Son kart da
  // silinirse proje kartsiz duruma geri doner: board_id anahtarlari temizlenir.
  deleteBoard: (id) =>
    set((s) => {
      const remaining = s.boards.filter((b) => b.id !== id);
      if (!remaining.length) {
        return {
          boards: [],
          connectors: [],
          boardSizes: {},
          devices: s.devices.map(withoutBoardId),
          muxes: s.muxes.map(withoutBoardId),
          selectedId: null,
        };
      }
      // "Tam olarak bir main kart" degismezi: ana kart silindiyse ilk kalan
      // kart ana kart olur (denetleyiciler tanimi geregi orada sayilir).
      const boards = remaining.some((b) => b.role === "main")
        ? remaining
        : remaining.map((b, i) => (i === 0 ? { ...b, role: "main" as const } : b));
      const fallback = mainBoardId(boards);
      const boardSizes = Object.fromEntries(
        Object.entries(s.boardSizes).filter(([key]) => key !== id),
      );
      return {
        boards,
        boardSizes,
        connectors: s.connectors.filter((c) => c.from_board !== id && c.to_board !== id),
        devices: s.devices.map((d) => (d.board_id === id ? { ...d, board_id: fallback } : d)),
        muxes: s.muxes.map((m) => (m.board_id === id ? { ...m, board_id: fallback } : m)),
        selectedId: null,
      };
    }),

  setDeviceBoard: (deviceId, boardId) =>
    set((s) => ({
      devices: s.devices.map((d) => (d.id === deviceId ? { ...d, board_id: boardId } : d)),
      muxes: s.muxes.map((m) => (m.id === deviceId ? { ...m, board_id: boardId } : m)),
    })),

  setBoardSize: (id, size) => set((s) => ({ boardSizes: { ...s.boardSizes, [id]: size } })),

  addConnector: (c) => {
    const s0 = get();
    const id = uniqueId(
      boardSlug(c.name, `konnektor_${s0.connectors.length + 1}`),
      s0.connectors.map((x) => x.id),
    );
    set((s) => ({ connectors: [...s.connectors, { ...c, id }] }));
    return id;
  },

  updateConnector: (id, patch) =>
    set((s) => ({ connectors: s.connectors.map((c) => (c.id === id ? { ...c, ...patch } : c)) })),

  deleteConnector: (id) => set((s) => ({ connectors: s.connectors.filter((c) => c.id !== id) })),

  buildSpec: () => {
    const s = get();
    // Kart tanimsizken spec'te ne boards/connectors anahtari ne de board_id
    // bulunur — uretilen cikti bugunkuyle bayt-bayt ayni kalir (tasarim §4.1).
    const boardsOn = s.boards.length > 0;
    const devices = withDefaultSafeOperations(s.devices, s.descriptors);
    const spec: ProjectSpec = {
      schema_version: "1.0",
      project: s.project,
      coding_standard_ref: DEFAULT_CODING_STANDARD,
      llm: s.llm.enabled
        ? s.llm
        : { enabled: false },
      controllers: s.controllers,
      devices: boardsOn ? devices : devices.map(withoutBoardId),
      muxes: boardsOn ? s.muxes : s.muxes.map(withoutBoardId),
      generation_options: { qc_max_rounds: 3, include_doxygen: true, line_ending: "crlf" },
    };
    if (boardsOn) {
      spec.boards = s.boards.map(specBoard);
      if (s.connectors.length) spec.connectors = s.connectors.map(specConnector);
    }
    return spec;
  },

  setJob: (patch) => set((s) => ({ job: { ...s.job, ...patch } })),
  pushEvent: (e) => set((s) => ({ job: { ...s.job, events: [...s.job.events, e] } })),
  resetJob: () =>
    set((s) => ({
      previousFiles: s.job.files.length > 0 ? s.job.files : s.previousFiles,
      job: { id: null, status: "idle", events: [], files: [], qc: null },
    })),
}), {
  name: "spec2code-store",
  partialize: (s) => ({
    step: s.step,
    project: s.project,
    llm: s.llm,
    zones: s.zones,
    cores: s.cores,
    controllers: s.controllers,
    unmatched: s.unmatched,
    muxes: s.muxes,
    devices: s.devices,
    boards: s.boards,
    connectors: s.connectors,
    boardSizes: s.boardSizes,
    counter: s.counter,
  }),
}));

export const PLATFORM_LABELS: Record<PlatformId, string> = {
  zynq_7000: "Zynq-7000",
  zynq_ultrascale: "Zynq UltraScale+",
  versal: "Versal ACAP",
  microblaze_7series: "MicroBlaze (7-series)",
};

export const RUNTIMES: Runtime[] = ["bare_metal", "freertos"];
