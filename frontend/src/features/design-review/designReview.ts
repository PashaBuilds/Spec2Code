import type { Device, InitSequenceWrite, ProjectSpec } from "@/lib/types";
import { ltc2991InitPreview } from "@/features/device-config/Ltc2991Editor";
import { normalizeLtc2991Config } from "@/features/device-config/ltc2991Model";

export type ReviewConnection = {
  id: string;
  part: string;
  bus: string;
  endpoint: string;
};

export type ReviewInitWrite = {
  deviceId: string;
  part: string;
  reg: string;
  value: string;
  source: "profile" | "builder" | "ticspro";
};

export type ReviewFilePlan = {
  path: string;
  kind: "driver" | "test" | "mock" | "meta";
};

export type DesignReview = {
  connectionCount: number;
  initWrites: ReviewInitWrite[];
  connections: ReviewConnection[];
  files: ReviewFilePlan[];
};

export function buildDesignReview(spec: ProjectSpec): DesignReview {
  const controllers = new Map(spec.controllers.map((controller) => [controller.id, controller]));
  const muxes = new Map(spec.muxes.map((mux) => [mux.id, mux]));
  const connections: ReviewConnection[] = [];
  const initWrites: ReviewInitWrite[] = [];
  const files: ReviewFilePlan[] = [];

  for (const mux of spec.muxes) {
    const controller = controllers.get(mux.controller_id);
    connections.push({
      id: mux.id,
      part: mux.part,
      bus: controller?.instance ?? mux.controller_id,
      endpoint: `I2C ${mux.i2c_address}`,
    });
    pushUnitFiles(files, mux.part);
  }

  for (const device of spec.devices) {
    const controller = controllers.get(device.attach.controller_id);
    const via = device.attach.via_mux ? muxes.get(device.attach.via_mux.mux_id) : null;
    const endpoint = device.attach.i2c_address
      ? `I2C ${device.attach.i2c_address}${via ? ` / ${via.id} ch${device.attach.via_mux?.channel ?? 0}` : ""}`
      : device.attach.spi_chip_select != null
        ? `CS${device.attach.spi_chip_select}`
        : "-";

    connections.push({
      id: device.id,
      part: device.part,
      bus: controller?.instance ?? device.attach.controller_id,
      endpoint,
    });
    pushUnitFiles(files, device.part);
    initWrites.push(...deviceInitWrites(device));
  }

  files.push(
    { path: "tests/spec2code_mock_bus.h", kind: "mock" },
    { path: "tests/spec2code_mock_bus.c", kind: "mock" },
    { path: `tests/${spec.project.name}_mock_plan.h`, kind: "mock" },
    { path: `tests/${spec.project.name}_mock_plan.c`, kind: "mock" },
    { path: "tests/spec2code_testbench_protocol.h", kind: "test" },
    { path: "tests/spec2code_testbench_protocol.c", kind: "test" },
    { path: `tests/${spec.project.name}_testbench_ops.h`, kind: "test" },
    { path: `tests/${spec.project.name}_testbench_ops.c`, kind: "test" },
    { path: "tests/spec2code_testbench_manifest.json", kind: "meta" },
    { path: ".clang-format", kind: "meta" },
    { path: "README.md", kind: "meta" },
    { path: "qc_report.json", kind: "meta" },
  );
  if (hasZynqmpPsEthernet(spec)) {
    files.push(
      { path: "tests/spec2code_testbench_lwip.h", kind: "test" },
      { path: "tests/spec2code_testbench_lwip.c", kind: "test" },
      { path: "tests/spec2code_testbench_lwip_main.h", kind: "test" },
      { path: "tests/spec2code_testbench_lwip_main.c", kind: "test" },
    );
  }

  return {
    connectionCount: connections.length,
    initWrites,
    connections,
    files: dedupeFiles(files),
  };
}

function pushUnitFiles(files: ReviewFilePlan[], part: string) {
  const module = moduleOf(part);
  files.push(
    { path: `drivers/${module}.h`, kind: "driver" },
    { path: `drivers/${module}.c`, kind: "driver" },
    { path: `tests/${module}_test.h`, kind: "test" },
    { path: `tests/${module}_test.c`, kind: "test" },
  );
}

function dedupeFiles(files: ReviewFilePlan[]): ReviewFilePlan[] {
  const seen = new Set<string>();
  return files.filter((file) => {
    if (seen.has(file.path)) return false;
    seen.add(file.path);
    return true;
  });
}

function deviceInitWrites(device: Device): ReviewInitWrite[] {
  const writes: ReviewInitWrite[] = [];
  if (device.part.toUpperCase() === "LTC2991") {
    const cfg = normalizeLtc2991Config(device.config);
    for (const item of ltc2991InitPreview(cfg)) {
      writes.push({
        deviceId: device.id,
        part: device.part,
        reg: item.reg,
        value: item.value,
        source: "profile",
      });
    }
  }

  for (const item of normalizeSequence(device.config?.init_sequence)) {
    writes.push({
      deviceId: device.id,
      part: device.part,
      reg: item.reg,
      value: hex(item.value),
      source: "builder",
    });
  }
  const ticsWords = normalizeTicsWords(device.config?.ticspro_registers);
  if (ticsWords.length > 0) {
    writes.push({
      deviceId: device.id,
      part: device.part,
      reg: "TICS_PRO_ARRAY",
      value: `${ticsWords.length} word`,
      source: "ticspro",
    });
  }
  return writes;
}

function normalizeTicsWords(raw: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item) => (typeof item === "string" ? item : typeof item === "number" ? hex24(item) : null))
    .filter((item): item is string => item !== null);
}

function normalizeSequence(raw: unknown): InitSequenceWrite[] {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item): InitSequenceWrite | null => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      if (typeof row.reg !== "string") return null;
      const value = typeof row.value === "number" ? row.value : Number(row.value ?? 0);
      const write: InitSequenceWrite = {
        reg: row.reg,
        value: Number.isFinite(value) ? value : 0,
      };
      if (typeof row.note === "string") write.note = row.note;
      return write;
    })
    .filter((item): item is InitSequenceWrite => item !== null);
}

function moduleOf(part: string): string {
  return part.toLowerCase().replace(/[^a-z0-9]/g, "");
}

function hasZynqmpPsEthernet(spec: ProjectSpec): boolean {
  return (
    spec.project.platform === "zynq_ultrascale" &&
    spec.controllers.some(
      (controller) =>
        controller.type === "eth" &&
        controller.zone === "ps" &&
        (!controller.driver || controller.driver === "XEmacPs"),
    )
  );
}

function hex(value: number): string {
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}

function hex24(value: number): string {
  return `0x${(value & 0xffffff).toString(16).toUpperCase().padStart(6, "0")}`;
}
