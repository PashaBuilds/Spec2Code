import { create } from "zustand";
import { api } from "@/lib/api";
import { defaultVitisProcessor } from "@/lib/board";
import { makeSessionId } from "@/lib/console";
import type { TestbenchSessionStatus } from "@/lib/types";
import { useStore } from "@/store/useStore";

export type BoardTransport = "tcp" | "serial" | "coresight";

/** Board hedefi profili: tüm paneller TEK bağlantıyı paylaşır. Ayarlar
 * tarayıcıda kalıcıdır; SmartLynq adresi ve Vitis yolu Run on Board /
 * Vitis workspace ile aynı anahtarlardan beslenir (tek doğru kaynak). */

const HW_SERVER_KEY = "spec2code.board.hwServerUrl";
const VITIS_PATH_KEY = "spec2code.vitisPath";

const FIELD_KEYS: Record<string, string> = {
  transport: "spec2code.testbench.transport",
  host: "spec2code.testbench.host",
  port: "spec2code.testbench.port",
  timeoutS: "spec2code.testbench.timeout",
  serialPort: "spec2code.testbench.serialPort",
  baud: "spec2code.testbench.baud",
  csVitisPath: "spec2code.testbench.csVitisPath",
  csHwServerUrl: HW_SERVER_KEY,
  csProcessor: "spec2code.testbench.csProcessor",
};

function read(key: string, fallback = ""): string {
  try {
    return window.localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // localStorage kapalıysa ayarlar yalnızca bu oturumda kalır
  }
}

type BoardSettings = {
  transport: BoardTransport;
  host: string;
  port: string;
  timeoutS: string;
  serialPort: string;
  baud: string;
  csVitisPath: string;
  csHwServerUrl: string;
  csProcessor: string;
};

interface BoardConnectionState extends BoardSettings {
  sessionId: string;
  connected: boolean;
  busy: boolean;
  lastError: string;
  status: TestbenchSessionStatus | null;
  /** Ayar değişikliği: state + localStorage birlikte güncellenir. */
  update: (patch: Partial<BoardSettings>) => void;
  /** Boşsa Setup'taki hedef çekirdekten türetilen işlemci. */
  effectiveProcessor: () => string;
  timeoutSeconds: () => number;
  connect: () => Promise<boolean>;
  disconnect: () => Promise<void>;
  /** Komut hatası sonrası: bağlantıyı düşürme, gerçek durumu backend'den sor. */
  reconcile: (message: string) => void;
}

function initialTransport(): BoardTransport {
  const saved = read(FIELD_KEYS.transport);
  return saved === "serial" || saved === "coresight" ? saved : "tcp";
}

export const useBoardConnection = create<BoardConnectionState>((set, get) => ({
  sessionId: makeSessionId("board"),
  transport: initialTransport(),
  host: read(FIELD_KEYS.host, "127.0.0.1"),
  port: read(FIELD_KEYS.port, "5000"),
  timeoutS: read(FIELD_KEYS.timeoutS, "5"),
  serialPort: read(FIELD_KEYS.serialPort),
  baud: read(FIELD_KEYS.baud, "115200"),
  csVitisPath: read(FIELD_KEYS.csVitisPath) || read(VITIS_PATH_KEY),
  // Eski anahtarlardan migrasyon: testbench/runboard ayrışık adresleri tek profile iner.
  csHwServerUrl: read(HW_SERVER_KEY) || read("spec2code.testbench.csHwServerUrl") || read("spec2code.runboard.hwServerUrl"),
  csProcessor: read(FIELD_KEYS.csProcessor),
  connected: false,
  busy: false,
  lastError: "",
  status: null,

  update: (patch) => {
    set(patch);
    for (const [field, value] of Object.entries(patch)) {
      const key = FIELD_KEYS[field];
      if (key && typeof value === "string") write(key, value.trim());
    }
    if (typeof patch.transport === "string") write(FIELD_KEYS.transport, patch.transport);
    // Vitis yolu tek doğru kaynak: workspace paneliyle paylaşılan anahtara da yaz.
    if (typeof patch.csVitisPath === "string" && patch.csVitisPath.trim()) {
      write(VITIS_PATH_KEY, patch.csVitisPath.trim());
    }
  },

  effectiveProcessor: () => {
    const own = get().csProcessor.trim();
    if (own) return own;
    const project = useStore.getState().project;
    return defaultVitisProcessor(project.platform, project.target_core);
  },

  timeoutSeconds: () => {
    const parsed = Number.parseFloat(get().timeoutS);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 5;
  },

  connect: async () => {
    const state = get();
    if (state.busy || state.connected) return state.connected;
    if (state.transport === "tcp") {
      const port = Number.parseInt(state.port, 10);
      if (!state.host.trim() || !Number.isFinite(port) || port <= 0) {
        set({ lastError: "Host veya port geçerli değil." });
        return false;
      }
    }
    if (state.transport === "serial" && !state.serialPort.trim()) {
      set({ lastError: "Seri port seç (ör. COM4)." });
      return false;
    }
    if (state.transport === "coresight" && !state.csVitisPath.trim()) {
      set({ lastError: "CoreSight için Vitis kurulum yolu gerekli (xsdb oradan bulunur)." });
      return false;
    }
    set({ busy: true, lastError: "" });
    try {
      const status = await api.testbenchConnect(
        state.transport === "serial"
          ? {
              session_id: state.sessionId,
              transport: "serial",
              serial_port: state.serialPort.trim(),
              baud: Number.parseInt(state.baud, 10) || 115200,
              timeout_s: get().timeoutSeconds(),
            }
          : state.transport === "coresight"
            ? {
                session_id: state.sessionId,
                transport: "coresight",
                vitis_path: state.csVitisPath.trim(),
                hw_server_url: state.csHwServerUrl.trim(),
                processor: get().effectiveProcessor(),
                timeout_s: get().timeoutSeconds(),
              }
            : {
                session_id: state.sessionId,
                transport: "tcp",
                host: state.host.trim(),
                port: Number.parseInt(state.port, 10) || 0,
                timeout_s: get().timeoutSeconds(),
              },
      );
      set({
        status,
        connected: Boolean(status.connected),
        lastError: status.connected
          ? ""
          : status.last_error
            || (state.transport === "serial"
              ? "Seri bağlantı kurulamadı."
              : state.transport === "coresight"
                ? "CoreSight köprüsü kurulamadı."
                : "TCP bağlantısı kurulamadı."),
      });
      return Boolean(status.connected);
    } catch (err) {
      set({ status: null, connected: false, lastError: err instanceof Error ? err.message : String(err) });
      return false;
    } finally {
      set({ busy: false });
    }
  },

  disconnect: async () => {
    const state = get();
    set({ busy: true });
    try {
      const status = await api.testbenchDisconnect(state.sessionId);
      set({ status });
    } catch {
      // zaten kopuk
    } finally {
      set({ connected: false, busy: false });
    }
  },

  reconcile: (message) => {
    set({ lastError: message });
    void api.testbenchSessionStatus(get().sessionId)
      .then((status) => set({ status, connected: Boolean(status.connected) }))
      .catch(() => set({ status: null, connected: false }));
  },
}));
