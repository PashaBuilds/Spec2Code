import type { Controller, Device, Mux, Zone } from "@/lib/types";

// Auto-layout for the schematic (Brief §9). A deterministic 3-column layered layout
// (controllers → muxes/direct-devices → mux-devices). Chosen over dagre because dagre's
// browser bundle produced invalid (NaN) positions via CJS/ESM interop; a manual layered
// layout is portable, dependency-free, and fully deterministic — the user never hand-arranges.

export interface Pos {
  x: number;
  y: number;
  w: number;
  h: number;
}
export interface ZoneRect {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
}

const SIZE = {
  controller: { w: 200, h: 78 },
  mux: { w: 168, h: 70 },
  device: { w: 210, h: 84 },
};
const COL_X = [60, 430, 800];
const GAP = 34;

export function computeLayout(
  controllers: Controller[],
  muxes: Mux[],
  devices: Device[],
): Map<string, Pos> {
  const pos = new Map<string, Pos>();
  const place = (items: { id: string; w: number; h: number }[], colX: number) => {
    let y = 60;
    for (const it of items) {
      pos.set(it.id, { x: colX, y, w: it.w, h: it.h });
      y += it.h + GAP;
    }
  };

  // Controllers grouped by zone, with an extra gap between zone bands so zone boxes
  // (computeZoneRects) never overlap vertically.
  const ctrlSorted = [...controllers].sort((a, b) =>
    `${a.zone}|${a.type}|${a.instance}`.localeCompare(`${b.zone}|${b.type}|${b.instance}`),
  );
  const directDevices = devices.filter((d) => !d.attach.via_mux);
  const muxDevices = devices.filter((d) => d.attach.via_mux);

  let cy = 60;
  let prevZone: string | null = null;
  for (const c of ctrlSorted) {
    if (prevZone !== null && c.zone !== prevZone) cy += 64; // gap between zone bands
    pos.set(c.id, { x: COL_X[0], y: cy, ...SIZE.controller });
    cy += SIZE.controller.h + GAP;
    prevZone = c.zone;
  }
  place(
    [
      ...muxes.map((m) => ({ id: m.id, ...SIZE.mux })),
      ...directDevices.map((d) => ({ id: d.id, ...SIZE.device })),
    ],
    COL_X[1],
  );
  place(muxDevices.map((d) => ({ id: d.id, ...SIZE.device })), COL_X[2]);
  return pos;
}

// Bounding boxes for the platform zones, sized to enclose their controllers (Brief §9.2).
export function computeZoneRects(
  zones: Zone[],
  controllers: Controller[],
  pos: Map<string, Pos>,
): ZoneRect[] {
  const pad = 24;
  const rects: ZoneRect[] = [];
  for (const zone of zones) {
    const pts = controllers
      .filter((c) => c.zone === zone.id)
      .map((c) => pos.get(c.id))
      .filter(Boolean) as Pos[];
    if (!pts.length) continue;
    const minX = Math.min(...pts.map((p) => p.x)) - pad;
    const minY = Math.min(...pts.map((p) => p.y)) - pad - 18;
    const maxX = Math.max(...pts.map((p) => p.x + p.w)) + pad;
    const maxY = Math.max(...pts.map((p) => p.y + p.h)) + pad;
    rects.push({ id: zone.id, label: zone.label, x: minX, y: minY, w: maxX - minX, h: maxY - minY });
  }
  return rects;
}
