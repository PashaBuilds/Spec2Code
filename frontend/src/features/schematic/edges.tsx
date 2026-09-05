import { BaseEdge, EdgeLabelRenderer, type EdgeProps } from "@xyflow/react";

// Kanal kablosu: mux çıkışından kanal başına AYRI dikey şeritte (lane) yürüyen
// ortogonal hat. React Flow smoothstep tüm kenarları kaynak-hedef orta
// noktasında büktüğünden farklı kanalların kabloları tek dikey hatta çakışıp
// okunmaz oluyordu (saha bulgusu, v0.1.113). Şeridin X'i kanal sırasına göre
// kaydırılır; aynı kanalı paylaşan kablolar aynı çıkıştan aynı şeridi kullanır
// ve ortak bara gibi görünür — istenen davranış.
//
// Şeritler HEDEF tarafına demirlenir: cihaz kolonunun hemen solundaki koridor
// yalnız kablolara ait; kaynak tarafına demirlemek şeritleri orta kolondaki
// mux-dışı düğümlerin (ör. doğrudan bağlı entegreler) gövdesine sokuyordu.
const LANE_BASE = 24; // cihaz kolonu sol kenarından son şeride mesafe (px)
const LANE_STEP = 14; // ardışık şeritler arası mesafe (px)
const CORNER = 12; // köşe yuvarlatma yarıçapı (px)

export function ChannelWireEdge(props: EdgeProps) {
  const { id, sourceX, sourceY, targetX, targetY, style, data, markerEnd } = props;
  const d = data as { lane?: unknown; laneCount?: unknown; offset?: unknown; label?: unknown } | undefined;
  const lane = typeof d?.lane === "number" && d.lane >= 0 ? d.lane : 0;
  const laneCount = typeof d?.laneCount === "number" && d.laneCount > lane ? d.laneCount : lane + 1;
  // Denetleyici (bus) kabloları mux kanal şeritlerinin SOLUNDA ayrı bir koridor
  // kullanır (offset): her denetleyicinin kendi dikey omurgası olur — I2C ve SPI
  // hatları tek kabloymuş gibi üst üste binmez (saha bulgusu, v0.1.161).
  const offset = typeof d?.offset === "number" && d.offset >= 0 ? d.offset : 0;
  const label = typeof d?.label === "string" && d.label ? d.label : "";
  // Küçük kanal soldaki şeritte: mux çıkış sırası (üstten alta) ile şerit
  // sırası (soldan sağa) aynı kalır, kablolar birbirini kesmez. Dar yerleşimde
  // mux'tan çıkmadan dönmemek için kaynak tarafında pay bırakılır.
  const laneX = Math.max(targetX - LANE_BASE - offset - (laneCount - 1 - lane) * LANE_STEP, sourceX + 12);
  const dy = targetY - sourceY;
  const dirY = Math.sign(dy);
  const radius = Math.min(
    CORNER,
    Math.abs(dy) / 2,
    Math.max(laneX - sourceX, 0),
    Math.max(targetX - laneX, 0),
  );
  const path =
    dirY === 0
      ? `M ${sourceX},${sourceY} L ${targetX},${targetY}`
      : [
          `M ${sourceX},${sourceY}`,
          `L ${laneX - radius},${sourceY}`,
          `Q ${laneX},${sourceY} ${laneX},${sourceY + dirY * radius}`,
          `L ${laneX},${targetY - dirY * radius}`,
          `Q ${laneX},${targetY} ${laneX + radius},${targetY}`,
          `L ${targetX},${targetY}`,
        ].join(" ");
  // Etiket kablo üzerinde tekrarlanmaz: "ch N" tek yerde, mux çıkışında
  // (MuxNode) kablosuyla aynı renkte durur; kablo rengi kanalı söyler.
  const stroke = (style as { stroke?: string } | undefined)?.stroke;
  return (
    <>
      <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />
      {label ? (
        <EdgeLabelRenderer>
          <div
            className="pointer-events-none rounded border bg-elev px-1.5 py-0.5 font-mono text-[10px] font-semibold"
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${laneX}px, ${targetY - dirY * Math.max(Math.abs(dy) / 2, radius + 8)}px)`,
              borderColor: stroke,
              color: stroke,
            }}
          >
            {label}
          </div>
        </EdgeLabelRenderer>
      ) : null}
    </>
  );
}

export const edgeTypes = { channel: ChannelWireEdge };
