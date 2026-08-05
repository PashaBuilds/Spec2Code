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
