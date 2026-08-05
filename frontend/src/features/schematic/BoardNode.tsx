import { useEffect, useRef, useState } from "react";
import {
  Handle,
  NodeResizeControl,
  Position,
  type NodeProps,
} from "@xyflow/react";
import { CircuitBoard, Cpu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";

/** Kart kutusu (React Flow parent/group node).
 *
 * Kutu cihazlarin ARKASINDA durur: zIndex 0 verilir, cocuk dugumler React
 * Flow'un `calculateChildXYZ` kuralindan otomatik olarak parent+1 alir. Govde
 * de bilincli olarak "delik"tir — yalniz kenarlik/baslik boyanir, ic alan
 * saydamdir; bu sayede cihaz tiklamalari ve suruklemeleri kutuya takilmaz.
 */
export interface BoardNodeData {
  boardId: string;
  name: string;
  isMain: boolean;
  /** Kutu icindeki entegre + switch sayisi. */
  count: number;
  /** Icerigi saran en kucuk olcu — kullanici bunun altina kucultemez. */
  minW: number;
  minH: number;
  [key: string]: unknown;
}

export function BoardNode({ data, selected }: NodeProps) {
  const d = data as BoardNodeData;
  const renameBoard = useStore((s) => s.renameBoard);
  const setBoardSize = useStore((s) => s.setBoardSize);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(d.name);
  const inputRef = useRef<HTMLInputElement>(null);
  const headerRef = useRef<HTMLDivElement>(null);
  const nameRef = useRef(d.name);
  nameRef.current = d.name;

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  // Cift tik dinleyicisi DOGRUDAN baslik elemanina baglanir: React'in kok
  // delegasyonu bu olayi hic gormuyor, cunku React Flow'un zoom katmani
  // (zoomOnDoubleClick) dblclick'i ust katmanda yutuyor — olculdu: olay
  // hedefte tetikleniyor, document'e ulasmiyor, kanvas 0.55 -> 1.10
  // yakinlasiyordu. Burada durdurulunca hem ad duzenlenir hem de kanvas
  // yakinlasmaz.
  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const onDoubleClick = (event: MouseEvent) => {
      event.preventDefault();
      event.stopPropagation();
      setDraft(nameRef.current);
      setEditing(true);
    };
    el.addEventListener("dblclick", onDoubleClick);
    return () => el.removeEventListener("dblclick", onDoubleClick);
  }, []);

  function commit() {
    setEditing(false);
    if (draft.trim() && draft.trim() !== d.name) renameBoard(d.boardId, draft.trim());
  }

  const accent = d.isMain ? "var(--accent)" : "var(--zone-ps)";
  return (
    <div
      className="relative h-full w-full rounded-xl"
      style={{
        // Ic alan neredeyse saydam: altindaki nokta izgara ve kablolar gorunur
        // kalir, kutu "kart plakasi" gibi durur.
        background: `color-mix(in srgb, ${accent} 5%, transparent)`,
        border: `1px solid color-mix(in srgb, ${accent} ${selected ? 90 : 45}%, transparent)`,
        boxShadow: selected
          ? `0 0 0 1px ${accent}, 0 0 22px -6px color-mix(in srgb, ${accent} 70%, transparent)`
          : "inset 0 0 40px -24px rgba(0,0,0,0.9)",
      }}
    >
      {/* Baslik seridi: kullanicinin verdigi ad (cift tikla duzenlenir). */}
      <div
        ref={headerRef}
        className="absolute inset-x-0 top-0 flex h-[30px] items-center gap-2 rounded-t-xl px-3"
        style={{
          background: `color-mix(in srgb, ${accent} 16%, var(--elev))`,
          borderBottom: `1px solid color-mix(in srgb, ${accent} 38%, transparent)`,
        }}
        title="Kart adını değiştirmek için çift tıkla"
      >
        <CircuitBoard className="h-3.5 w-3.5 shrink-0" style={{ color: accent }} />
        {editing ? (
          <input
            ref={inputRef}
            className="nodrag nopan h-[20px] min-w-0 flex-1 rounded border border-accent bg-inset px-1.5 font-mono text-[12px] text-text outline-none"
            value={draft}
            autoFocus
            onChange={(e) => setDraft(e.target.value)}
            onMouseDown={(e) => e.stopPropagation()}
            onBlur={commit}
            onKeyDown={(e) => {
              e.stopPropagation();
              if (e.key === "Enter") commit();
              if (e.key === "Escape") setEditing(false);
            }}
          />
        ) : (
          <span
            className="text-silk min-w-0 flex-1 truncate font-mono text-[12px] font-semibold"
            style={{ color: "var(--text)" }}
          >
            {d.name}
          </span>
        )}
        {d.isMain && (
          <span
            className="inline-flex shrink-0 items-center gap-1 rounded border px-1.5 py-[1px] font-mono text-[9px] font-bold uppercase tracking-wider"
            style={{
              color: accent,
              borderColor: `color-mix(in srgb, ${accent} 55%, transparent)`,
              background: "color-mix(in srgb, var(--bg) 70%, transparent)",
            }}
            title="Denetleyicilerin (FPGA/PS) bulunduğu ana kart"
          >
            <Cpu className="h-2.5 w-2.5" /> ana kart
          </span>
        )}
        <span
          className={cn(
            "shrink-0 rounded border border-border bg-bg/70 px-1.5 py-[1px] font-mono text-[9px] font-semibold",
            d.count ? "text-muted" : "text-faint",
          )}
          title="Karttaki entegre + switch sayısı"
        >
          {d.count} birim
        </span>
      </div>

      {d.count === 0 && (
        <span className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-center font-mono text-[11px] text-faint">
          Boş kart — entegreleri buraya sürükleyin
        </span>
      )}

      {/* Kartlar arasi konnektor uclari. Yon serit sirasina gore secilir. */}
      <Handle id="board-in-top" type="target" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="board-out-top" type="source" position={Position.Top} style={{ opacity: 0 }} />
      <Handle id="board-in-bottom" type="target" position={Position.Bottom} style={{ opacity: 0 }} />
      <Handle id="board-out-bottom" type="source" position={Position.Bottom} style={{ opacity: 0 }} />

      {/* Yalniz sag-alt tutamak: yerlesim turetilmis oldugundan sol/ust
          boyutlandirma dugumu KAYDIRIR, sonraki turetimde geri zipliyordu. */}
      {selected && (
        <NodeResizeControl
          position="bottom-right"
          minWidth={d.minW}
          minHeight={d.minH}
          onResize={(_, params) => setBoardSize(d.boardId, { w: params.width, h: params.height })}
          style={{ background: "transparent", border: "none" }}
        >
          <span
            className="absolute bottom-1 right-1 block h-3 w-3 cursor-nwse-resize rounded-[2px]"
            style={{ background: `color-mix(in srgb, ${accent} 70%, transparent)` }}
          />
        </NodeResizeControl>
      )}
    </div>
  );
}
