/** Kart (fiziksel PCB) katmani — UI tarafindaki tek dogruluk kaynagi.
 *
 * Kurallar `orchestrator/boards.py` ile AYNI olmak zorundadir: burada uretilen
 * kart kimligi spec'e yazilir, uretim tarafi ondan klasor adi ve C tanimlayici
 * turetir. Kart tanimli degilse (boards bos) sistem tek ortuk ana karttir ve
 * kanvas bugunku duzeninde kalir.
 */
import type { Board } from "@/lib/types";

export const MAIN_BOARD_ID = "main";

/** React Flow dugum kimligi cihaz kimlikleriyle carpismasin diye onek alir. */
export const BOARD_NODE_PREFIX = "board-";

/** Turkce harfler ASCII karsiliklarina katlanir (boards.py::_FOLD ile ayni). */
const TR_FOLD: Record<string, string> = {
  "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
  "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
};

function foldAscii(text: string): string {
  return Array.from(text).map((ch) => TR_FOLD[ch] ?? ch).join("");
}

function words(name: string): string[] {
  return foldAscii(name ?? "").split(/[^A-Za-z0-9]+/).filter(Boolean);
}

/** Kart/konnektor adindan snake_case kimlik: "RF Kart" -> "rf_kart".
 *  Sema deseni: ^[a-z][a-z0-9_]*$ */
export function boardSlug(name: string, fallback: string): string {
  const parts = words(name);
  let id = parts.map((w) => w.toLowerCase()).join("_");
  if (!id) id = fallback;
  if (!/^[a-z]/.test(id)) id = `k_${id}`;
  return id;
}

/** Ayni kimlik iki kez uretilmesin: "rf_kart", "rf_kart_2", ... */
export function uniqueId(base: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  if (!used.has(base)) return base;
  let n = 2;
  while (used.has(`${base}_${n}`)) n += 1;
  return `${base}_${n}`;
}

/** Ana kartin kimligi; kart yoksa ortuk "main". */
export function mainBoardId(boards: Board[]): string {
  return (boards.find((b) => b.role === "main") ?? boards[0])?.id ?? MAIN_BOARD_ID;
}

/** Cihaz/mux'un kart kimligi. Tanimsiz kimlik ANA KARTA duser — codegen'deki
 *  `_effective_board_id` ile ayni davranis (cihaz sessizce kaybolmaz). */
export function effectiveBoardId(entity: { board_id?: string }, boards: Board[]): string {
  const main = mainBoardId(boards);
  const bid = entity.board_id;
  if (!bid) return main;
  return boards.some((b) => b.id === bid) ? bid : main;
}

export function boardNodeId(boardId: string): string {
  return `${BOARD_NODE_PREFIX}${boardId}`;
}

/** React Flow dugum kimliginden kart kimligi; kart dugumu degilse null. */
export function boardIdFromNode(nodeId: string | null | undefined): string | null {
  if (!nodeId || !nodeId.startsWith(BOARD_NODE_PREFIX)) return null;
  return nodeId.slice(BOARD_NODE_PREFIX.length);
}

export interface BoardGroup<T> {
  boardId: string;
  boardName: string;
  items: T[];
}

/** Ogeleri kart kimligine gore gruplar (CIT/Test Bench panelleri — Task 4).
 *  Grup sirasi `boardList` sirasini izler (manifest.boards sirasi = kullanicinin
 *  ekleme sirasi, ana kart en basta gelir — bkz. store addBoard). `boardList`'te
 *  TANIMLI OLMAYAN bir board_id (beklenmez ama dogrulayici atlanmis/eski
 *  manifest olabilir) sessizce KAYBOLMAZ: kendi id'siyle ayri bir grup olarak,
 *  ilk gorulme sirasiyla sona eklenir. */
export function groupByBoardId<T>(
  items: T[],
  boardIdOf: (item: T) => string,
  boardList: Array<{ id: string; name: string }>,
): BoardGroup<T>[] {
  const byId = new Map<string, T[]>();
  for (const item of items) {
    const id = boardIdOf(item);
    const bucket = byId.get(id);
    if (bucket) bucket.push(item);
    else byId.set(id, [item]);
  }
  const groups: BoardGroup<T>[] = [];
  for (const board of boardList) {
    const bucket = byId.get(board.id);
    if (bucket) {
      groups.push({ boardId: board.id, boardName: board.name, items: bucket });
      byId.delete(board.id);
    }
  }
  for (const [id, bucket] of byId) {
    groups.push({ boardId: id, boardName: id, items: bucket });
  }
  return groups;
}

/** Cihaz/mux kimligi kurali (kullanici istegi 2026-09-06): `<kart>_<parca>[_<n>]`.
 *  Kart oneki kart ADININ slug'i (kart tanimsizsa "kart"); ayni kartta ayni parcadan birden
 *  fazla cihaz varsa ekleme sirasiyla `_1, _2, ...` (tek ise sonek yok): sakk_ltc2991_1.
 *  Uretilen enum (`I2C_CIHAZ_SAKK_LTC2991_1`), CIT varsayilan adlari ve ekranlar bu kimligi
 *  kullanir. `orchestrator/boards.py::normalize_device_ids` ile AYNI kural. */
export function partSlug(part: string): string {
  return part.toLowerCase().replace(/[^a-z0-9]/g, "") || "cihaz";
}

interface IdItem {
  id: string;
  part: string;
  board_id?: string;
}

function assignIds<T extends IdItem>(items: T[], boards: Board[]): Map<string, string> {
  const prefixOf = (item: T): string => {
    if (!boards.length) return "kart";
    const bid = effectiveBoardId(item, boards);
    const board = boards.find((b) => b.id === bid);
    return board ? boardSlug(board.name, board.id) : bid;
  };
  const counts = new Map<string, number>();
  for (const item of items) {
    const key = `${prefixOf(item)}_${partSlug(item.part)}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  const seen = new Map<string, number>();
  const mapping = new Map<string, string>();
  for (const item of items) {
    const key = `${prefixOf(item)}_${partSlug(item.part)}`;
    const n = (seen.get(key) ?? 0) + 1;
    seen.set(key, n);
    mapping.set(item.id, (counts.get(key) ?? 1) > 1 ? `${key}_${n}` : key);
  }
  return mapping;
}

export interface NormalizedIds<D, M> {
  devices: D[];
  muxes: M[];
  deviceMap: Map<string, string>;
  muxMap: Map<string, string>;
}

/** Kimlikleri kurala gore yeniden adlandirir; degisiklik yoksa null. Mux referanslari
 *  (attach.via_mux.mux_id) da yeni kimlige tasinir. */
export function normalizeDeviceIds<
  D extends IdItem & { attach: { via_mux?: { mux_id: string; channel: number } | null } },
  M extends IdItem,
>(devices: D[], muxes: M[], boards: Board[]): NormalizedIds<D, M> | null {
  const deviceMap = assignIds(devices, boards);
  const muxMap = assignIds(muxes, boards);
  const changed =
    [...deviceMap].some(([from, to]) => from !== to) || [...muxMap].some(([from, to]) => from !== to);
  if (!changed) return null;
  const newDevices = devices.map((d) => {
    const via = d.attach.via_mux;
    const attach = via ? { ...d.attach, via_mux: { ...via, mux_id: muxMap.get(via.mux_id) ?? via.mux_id } } : d.attach;
    return { ...d, id: deviceMap.get(d.id) ?? d.id, attach };
  });
  const newMuxes = muxes.map((m) => ({ ...m, id: muxMap.get(m.id) ?? m.id }));
  return { devices: newDevices, muxes: newMuxes, deviceMap, muxMap };
}
