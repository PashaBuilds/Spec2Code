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

type LayoutItem = {
  id: string;
  w: number;
  h: number;
  parentId: string;
  order: number;
  desiredY: number;
};

function centerY(pos: Pos): number {
  return pos.y + pos.h / 2;
}

function stackHeight(items: { h: number }[]): number {
  if (!items.length) return 0;
  return items.reduce((sum, item) => sum + item.h, 0) + GAP * (items.length - 1);
}

function placeOrderedGroups(
  pos: Map<string, Pos>,
  items: LayoutItem[],
  colX: number,
): void {
  const groups = new Map<string, LayoutItem[]>();
  for (const item of items) {
    const existing = groups.get(item.parentId) ?? [];
    existing.push(item);
    groups.set(item.parentId, existing);
  }

  const orderedGroups = [...groups.values()]
    .map((group) => group.sort((a, b) => a.order - b.order))
    .sort((a, b) => a[0].desiredY - b[0].desiredY);

  let nextY = 60;
  for (const group of orderedGroups) {
    const groupY = Math.max(group[0].desiredY - stackHeight(group) / 2, nextY);
    let y = groupY;
    for (const item of group) {
      pos.set(item.id, { x: colX, y, w: item.w, h: item.h });
      y += item.h + GAP;
    }
    nextY = y;
  }
}

export function computeLayout(
  controllers: Controller[],
  muxes: Mux[],
  devices: Device[],
): Map<string, Pos> {
  const pos = new Map<string, Pos>();

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

  const controllerIndex = new Map(ctrlSorted.map((controller, index) => [controller.id, index]));
  const layerOneItems: LayoutItem[] = [
    ...muxes.map((mux, index) => {
      const parent = pos.get(mux.controller_id);
      return {
        id: mux.id,
        parentId: mux.controller_id,
        order: index,
        desiredY: parent ? centerY(parent) : 60,
        ...SIZE.mux,
      };
    }),
    ...directDevices.map((device, index) => {
      const parent = pos.get(device.attach.controller_id);
      return {
        id: device.id,
        parentId: device.attach.controller_id,
        order: muxes.length + index,
        desiredY: parent ? centerY(parent) : 60,
        ...SIZE.device,
      };
    }),
  ].sort((a, b) => {
    const parentDelta =
      (controllerIndex.get(a.parentId) ?? Number.MAX_SAFE_INTEGER) -
      (controllerIndex.get(b.parentId) ?? Number.MAX_SAFE_INTEGER);
    return parentDelta || a.order - b.order;
  });
  placeOrderedGroups(pos, layerOneItems, COL_X[1]);

  const muxIndex = new Map(
    [...muxes]
      .sort((a, b) => {
        const ay = pos.get(a.id)?.y ?? Number.MAX_SAFE_INTEGER;
        const by = pos.get(b.id)?.y ?? Number.MAX_SAFE_INTEGER;
        return ay - by;
      })
      .map((mux, index) => [mux.id, index]),
  );
  const muxDeviceItems = muxDevices
    .map((device, index) => {
      const muxId = device.attach.via_mux?.mux_id ?? "";
      const parent = pos.get(muxId);
      return {
        id: device.id,
        parentId: muxId,
        order: device.attach.via_mux?.channel ?? index,
        desiredY: parent ? centerY(parent) : 60,
        ...SIZE.device,
      };
    })
    .sort((a, b) => {
      const parentDelta =
        (muxIndex.get(a.parentId) ?? Number.MAX_SAFE_INTEGER) -
        (muxIndex.get(b.parentId) ?? Number.MAX_SAFE_INTEGER);
      return parentDelta || a.order - b.order;
    });
  placeOrderedGroups(pos, muxDeviceItems, COL_X[2]);

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
