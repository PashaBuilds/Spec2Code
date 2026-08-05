import type { Board, Controller, Device, Mux, Zone } from "@/lib/types";
import { effectiveBoardId, mainBoardId } from "@/lib/boards";

// Auto-layout for the schematic (Brief 9). A deterministic 3-column layered layout
// (controllers -> muxes/direct-devices -> mux-devices). Chosen over dagre because dagre's
// browser bundle produced invalid (NaN) positions via CJS/ESM interop; a manual layered
// layout is portable, dependency-free, and fully deterministic - the user never hand-arranges.

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
  device: { w: 230, h: 126 },
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

/* --- Kart (fiziksel PCB) kutulari -------------------------------------------
 *
 * Kart tanimliyken kanvas KART SERITLERINE bolunur: her kart kendi icerigini
 * bugunku 3 kolonlu duzenle (computeLayout) yerlestirir, seritler dikey olarak
 * ust uste binmeyecek sekilde siralanir. Boylece:
 *  - tek kartli (yalniz ana kart) projede yerlesim BUGUNKUNUN AYNISI kalir,
 *  - kart kutusu icindeki cihazlarda delik/bosluk olusmaz (baska kartin
 *    cihazlari araya girmez),
 *  - kolon X'leri korunur, yani elektriksel soldan-saga akis bozulmaz.
 *
 * BOARD_PAD, computeZoneRects'in kullandigi 24px paddan buyuk; BOARD_HEADER de
 * zone etiketinin 18px payini kapsar. Bu yuzden ana karttaki zone kutulari her
 * zaman kart kutusunun ICINDE kalir (ayri bir kesisim hesabina gerek yok).
 */
const BOARD_PAD = 30;
const BOARD_HEADER = 42;
const BOARD_GAP = 74;
const EMPTY_BOARD = { w: 380, h: 150 };

export interface BoardRect {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  /** Icerigi saran en kucuk olcu — kullanici kutuyu bunun altina kucultemez. */
  minW: number;
  minH: number;
}

export interface BoardLayout {
  /** Tum dugumlerin GLOBAL kanvas konumu (serit kaydirmasi uygulanmis). */
  pos: Map<string, Pos>;
  rects: BoardRect[];
  /** dugum kimligi -> kart kimligi (React Flow parentId'si bundan turer). */
  boardOf: Map<string, string>;
}

function boundsOf(items: Iterable<Pos>): { minX: number; minY: number; maxX: number; maxY: number } | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  let seen = false;
  for (const p of items) {
    seen = true;
    minX = Math.min(minX, p.x);
    minY = Math.min(minY, p.y);
    maxX = Math.max(maxX, p.x + p.w);
    maxY = Math.max(maxY, p.y + p.h);
  }
  return seen ? { minX, minY, maxX, maxY } : null;
}

export function computeBoardLayout(
  boards: Board[],
  controllers: Controller[],
  muxes: Mux[],
  devices: Device[],
  sizes: Record<string, { w: number; h: number }> = {},
): BoardLayout {
  const pos = new Map<string, Pos>();
  const rects: BoardRect[] = [];
  const boardOf = new Map<string, string>();
  const mainId = mainBoardId(boards);
  // Ana kart her zaman en ustte: denetleyiciler (dolayisiyla zone kutulari)
  // orada durur, kartlar arasi hatlar yukaridan asagi okunur.
  const ordered = [...boards].sort((a, b) => Number(b.id === mainId) - Number(a.id === mainId));

  let nextTop = 0;
  for (const board of ordered) {
    const isMain = board.id === mainId;
    const boardMuxes = muxes.filter((m) => effectiveBoardId(m, boards) === board.id);
    const boardDevices = devices.filter((d) => effectiveBoardId(d, boards) === board.id);
    // Denetleyiciler tanimi geregi ANA KARTTADIR (tasarim §3, tek FPGA ilkesi).
    const local = computeLayout(isMain ? controllers : [], boardMuxes, boardDevices);
    const bounds = boundsOf(local.values());

    const rectX = bounds ? bounds.minX - BOARD_PAD : 60;
    const innerTop = bounds ? bounds.minY - BOARD_PAD - BOARD_HEADER : 0;
    const minW = bounds ? bounds.maxX + BOARD_PAD - rectX : EMPTY_BOARD.w;
    const minH = bounds ? bounds.maxY + BOARD_PAD - innerTop : EMPTY_BOARD.h;
    const size = sizes[board.id];
    const w = Math.max(minW, size?.w ?? 0);
    const h = Math.max(minH, size?.h ?? 0);

    const dy = nextTop - innerTop;
    for (const [id, p] of local) {
      pos.set(id, { ...p, y: p.y + dy });
      boardOf.set(id, board.id);
    }
    rects.push({ id: board.id, x: rectX, y: nextTop, w, h, minW, minH });
    nextTop += h + BOARD_GAP;
  }

  return { pos, rects, boardOf };
}

// Bounding boxes for the platform zones, sized to enclose their controllers (Brief 9.2).
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
