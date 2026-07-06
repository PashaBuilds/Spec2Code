import { BaseEdge, type EdgeProps } from "@xyflow/react";

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
  const d = data as { lane?: unknown; laneCount?: unknown } | undefined;
  const lane = typeof d?.lane === "number" && d.lane >= 0 ? d.lane : 0;
  const laneCount = typeof d?.laneCount === "number" && d.laneCount > lane ? d.laneCount : lane + 1;
  // Küçük kanal soldaki şeritte: mux çıkış sırası (üstten alta) ile şerit
  // sırası (soldan sağa) aynı kalır, kablolar birbirini kesmez. Dar yerleşimde
  // mux'tan çıkmadan dönmemek için kaynak tarafında pay bırakılır.
  const laneX = Math.max(targetX - LANE_BASE - (laneCount - 1 - lane) * LANE_STEP, sourceX + 12);
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
  return <BaseEdge id={id} path={path} style={style} markerEnd={markerEnd} />;
}

export const edgeTypes = { channel: ChannelWireEdge };
