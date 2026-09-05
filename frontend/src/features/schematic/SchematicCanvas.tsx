import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  applyNodeChanges,
  useReactFlow,
  type Edge,
  type Node,
  type NodeChange,
  type ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// Re-fits the view after nodes are measured and whenever the graph changes.
function FitView({ signature }: { signature: string }) {
  const rf = useReactFlow();
  useEffect(() => {
    const id = setTimeout(() => rf.fitView({ padding: 0.18, duration: 220 }), 90);
    return () => clearTimeout(id);
  }, [signature, rf]);
  return null;
}
import { useStore } from "@/store/useStore";
import { computeBoardLayout, computeLayout, computeZoneRects, type BoardRect, type Pos } from "./layout";
import { nodeTypes } from "./nodes";
import { edgeTypes } from "./edges";
import { zoneColor } from "@/lib/utils";
import { busColor } from "@/lib/busColors";
import { channelColor } from "./channelColors";
import { boardNodeId, effectiveBoardId, mainBoardId } from "@/lib/boards";
import { VisualBackdrop } from "@/components/visuals";
import { ltc2991NodeSummary } from "@/features/device-config/ltc2991Model";
import type { Controller } from "@/lib/types";

// One bus = one color, wire included. `color` (CSS currentColor) feeds the
// selection drop-shadow in index.css so the glow matches the trace.
function wireProps(transport: string): Partial<Edge> {
  const stroke = busColor(transport);
  return {
    type: "smoothstep",
    pathOptions: { borderRadius: 14 },
    style: { stroke, color: stroke },
    labelStyle: { fill: stroke },
  } as Partial<Edge>;
}

// Konnektor etiketindeki hat adi: "ps_i2c_0" -> "I2C0" (sahada kullanilan ad).
function busTag(ctrl: Controller | undefined, controllerId: string): string {
  if (!ctrl) return controllerId;
  const index = /(\d+)\s*$/.exec(ctrl.id)?.[1] ?? "";
  return `${ctrl.type.toUpperCase()}${index}`;
}

/** Kablo demeti rengi: hicbir bus rengiyle karismasin diye notr celik tonu. */
const CONNECTOR_COLOR = "var(--silk)";

/** Birakma noktasi (fare veya dokunma) — hedef kart bununla secilir. */
function pointerPoint(event: MouseEvent | TouchEvent): { x: number; y: number } | null {
  if ("clientX" in event) return { x: event.clientX, y: event.clientY };
  const touch = event.changedTouches?.[0];
  return touch ? { x: touch.clientX, y: touch.clientY } : null;
}

export default function SchematicCanvas() {
  const zones = useStore((s) => s.zones);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const devices = useStore((s) => s.devices);
  const descriptors = useStore((s) => s.descriptors);
  const selectedId = useStore((s) => s.selectedId);
  const select = useStore((s) => s.select);
  const telemetry = useStore((s) => s.telemetry);
  const boards = useStore((s) => s.boards);
  const connectors = useStore((s) => s.connectors);
  const boardSizes = useStore((s) => s.boardSizes);
  const setDeviceBoard = useStore((s) => s.setDeviceBoard);

  // Surukleme sirasinda o dugumden `extent: "parent"` kaldirilir; aksi halde
  // cihaz kendi kart kutusunun kenarina yapisip baska karta goturulemez.
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const instanceRef = useRef<ReactFlowInstance | null>(null);

  const { nodes, edges, boardRects } = useMemo(() => {
    // Kart tanimli DEGILSE bu blok hic calismaz: dugumler, konumlar ve
    // ReactFlow ozellikleri bugunkuyle birebir ayni kalir (tasarim §5).
    const boardsOn = boards.length > 0;
    const boardLayout = boardsOn
      ? computeBoardLayout(boards, controllers, muxes, devices, boardSizes)
      : null;
    const pos: Map<string, Pos> = boardLayout
      ? boardLayout.pos
      : computeLayout(controllers, muxes, devices);
    const boardRects: BoardRect[] = boardLayout?.rects ?? [];
    const rectById = new Map(boardRects.map((r) => [r.id, r]));
    const mainId = boardsOn ? mainBoardId(boards) : "";
    // Kutu icindeki dugumun konumu PARENT'A GORELIDIR.
    const place = (id: string, p: { x: number; y: number }, boardId?: string) => {
      const bid = boardId ?? boardLayout?.boardOf.get(id);
      const rect = bid ? rectById.get(bid) : undefined;
      if (!rect) return { position: { x: p.x, y: p.y } };
      return { position: { x: p.x - rect.x, y: p.y - rect.y }, parentId: boardNodeId(rect.id) };
    };
    const zoneRects = computeZoneRects(zones, controllers, pos);
    const ctrlById = Object.fromEntries(controllers.map((c) => [c.id, c]));
    const hasDescriptor = (part: string) =>
      descriptors.some((d) => d.part === part) ||
      ["LTC2991", "TCA9548A", "MT25Q128", "MT25QU02G", "AD7414", "TMP101", "SHT21", "24LC32A", "DS1682", "LTC2945", "LTM4681"].includes(part);

    const nodes: Node[] = [];
    // Kart kutulari EN ONCE eklenir: React Flow parent dugumun cocuklarindan
    // once gelmesini sart kosar; zIndex 0 ile de cihazlarin ARKASINDA kalirlar.
    for (const rect of boardRects) {
      const board = boards.find((b) => b.id === rect.id);
      if (!board) continue;
      const count =
        devices.filter((d) => effectiveBoardId(d, boards) === rect.id).length +
        muxes.filter((m) => effectiveBoardId(m, boards) === rect.id).length;
      nodes.push({
        id: boardNodeId(rect.id),
        type: "board",
        position: { x: rect.x, y: rect.y },
        data: {
          boardId: rect.id,
          name: board.name,
          isMain: board.role === "main",
          count,
          minW: rect.minW,
          minH: rect.minH,
        },
        selected: boardNodeId(rect.id) === selectedId,
        draggable: false,
        zIndex: 0,
        width: rect.w,
        height: rect.h,
        style: { width: rect.w, height: rect.h },
      });
    }
    for (const z of zoneRects) {
      nodes.push({
        id: `zone-${z.id}`,
        type: "zone",
        // Zone kutulari denetleyicileri sarar, onlar da ana karttadir.
        ...place(`zone-${z.id}`, z, boardsOn ? mainId : undefined),
        data: { label: z.label, color: zoneColor(z.id) },
        draggable: false,
        selectable: false,
        zIndex: 0,
        width: z.w,
        height: z.h,
        style: { width: z.w, height: z.h },
      });
    }
    for (const c of controllers) {
      const p = pos.get(c.id);
      if (!p) continue;
      nodes.push({
        id: c.id,
        type: "controller",
        ...place(c.id, p),
        data: { label: c.instance, type: c.type, base_address: c.base_address, driver: c.driver, zone: c.zone },
        selected: c.id === selectedId,
        draggable: false,
        zIndex: 1,
      });
    }
    // Switch kanal hatlarının ayrışması için: her mux'ta GERÇEKTEN kullanılan
    // kanallar. MuxNode kanal başına ayrı çıkış noktası (handle) çizer; aynı
    // kanalı paylaşan entegrelerin kabloları aynı noktadan çıkar (ortak hat),
    // farklı kanallar üst üste binmez.
    const muxUsedChannels = new Map<string, number[]>();
    for (const d of devices) {
      const via = d.attach.via_mux;
      if (!via) continue;
      const list = muxUsedChannels.get(via.mux_id) ?? [];
      if (!list.includes(via.channel)) list.push(via.channel);
      muxUsedChannels.set(via.mux_id, list);
    }
    muxUsedChannels.forEach((list) => list.sort((a, b) => a - b));

    for (const m of muxes) {
      const p = pos.get(m.id);
      if (!p) continue;
      nodes.push({
        id: m.id,
        type: "mux",
        ...place(m.id, p),
        data: {
          part: m.part,
          i2c_address: m.i2c_address,
          channels: m.channels,
          usedChannels: muxUsedChannels.get(m.id) ?? [],
        },
        selected: m.id === selectedId,
        draggable: boardsOn,
        extent: boardsOn && draggingId !== m.id ? "parent" : undefined,
        zIndex: 1,
      });
    }
    for (const d of devices) {
      const p = pos.get(d.id);
      if (!p) continue;
      const ctrl = ctrlById[d.attach.controller_id];
      const transport = ctrl?.type ?? "i2c";
      const sub =
        transport === "spi" || transport === "qspi"
          ? `CS ${d.attach.spi_chip_select ?? 0}`
          : String(d.attach.i2c_address ?? "-");
      nodes.push({
        id: d.id,
        type: "device",
        ...place(d.id, p),
        data: {
          part: d.part,
          sub,
          transport,
          hasDescriptor: hasDescriptor(d.part),
          simulate: Boolean(d.simulate),
          configSummary: d.part.toUpperCase() === "LTC2991" ? ltc2991NodeSummary(d.config) : [],
          telemetry: telemetry[d.id]?.text ?? "",
        },
        selected: d.id === selectedId,
        draggable: boardsOn,
        extent: boardsOn && draggingId !== d.id ? "parent" : undefined,
        zIndex: 1,
      });
    }

    const edges: Edge[] = [];
    // Denetleyici başına AYRI dikey omurga: doğrudan kablo taşıyan her
    // denetleyici, cihaz kolonunun solundaki bus koridorunda kendi şeridini alır
    // (mux kanal şeritlerinin daha solunda). Aynı denetleyicinin kabloları aynı
    // şeridi paylaşır (ortak bara görünümü), farklı denetleyicilerinki ayrılır.
    const busLaneOf = new Map<string, number>();
    for (const m of muxes) if (ctrlById[m.controller_id] && !busLaneOf.has(m.controller_id)) busLaneOf.set(m.controller_id, busLaneOf.size);
    for (const d of devices) {
      if (!d.attach.via_mux && ctrlById[d.attach.controller_id] && !busLaneOf.has(d.attach.controller_id)) busLaneOf.set(d.attach.controller_id, busLaneOf.size);
    }
    const BUS_LANE_OFFSET = 44;
    const busWire = (controllerId: string, transport: string, label: string): Partial<Edge> => {
      const stroke = busColor(transport);
      return {
        type: "channel",
        data: { lane: busLaneOf.get(controllerId) ?? 0, laneCount: Math.max(busLaneOf.size, 1), offset: BUS_LANE_OFFSET, label },
        style: { stroke, color: stroke },
      } as Partial<Edge>;
    };
    for (const m of muxes) {
      if (ctrlById[m.controller_id]) {
        edges.push({
          id: `e-${m.controller_id}-${m.id}`,
          source: m.controller_id,
          target: m.id,
          ...busWire(m.controller_id, "i2c", "I2C"),
        });
      }
    }
    for (const d of devices) {
      const via = d.attach.via_mux;
      const ctrl = ctrlById[d.attach.controller_id];
      if (via) {
        // Kanal kablosu kanalın KENDİ rengini taşır; "ch N" etiketi kablo
        // üzerinde tekrarlanmaz, yalnız mux çıkışında (MuxNode) durur.
        const stroke = channelColor(via.channel);
        const used = muxUsedChannels.get(via.mux_id) ?? [];
        edges.push({
          id: `e-${via.mux_id}-${d.id}`,
          source: via.mux_id,
          // Kanal başına ayrı çıkış + ayrı dikey şerit (ChannelWireEdge):
          // yalnız aynı kanalın kabloları çakışır.
          sourceHandle: `ch-${via.channel}`,
          target: d.id,
          type: "channel",
          data: { lane: Math.max(used.indexOf(via.channel), 0), laneCount: used.length },
          style: { stroke, color: stroke },
        });
      } else if (ctrl) {
        const lbl =
          ctrl.type === "spi" || ctrl.type === "qspi"
            ? `${ctrl.type.toUpperCase()} CS${d.attach.spi_chip_select ?? 0}`
            : "I2C";
        edges.push({
          id: `e-${ctrl.id}-${d.id}`,
          source: ctrl.id,
          target: d.id,
          ...busWire(ctrl.id, ctrl.type, lbl),
        });
      }
    }
    // Kartlar arasi FIZIKSEL konnektorler: elektriksel yolu degistirmez, hattin
    // kart degistirdigi yeri BELGELER. Bus kablolarindan bilincli olarak farkli
    // gorunur (kesikli, kalin, ok basli, notr renk).
    for (const c of connectors) {
      const from = rectById.get(c.from_board);
      const to = rectById.get(c.to_board);
      if (!from || !to) continue;
      const downstream = to.y >= from.y;
      const via = c.bus.via_mux;
      const label = [
        c.name,
        busTag(ctrlById[c.bus.controller_id], c.bus.controller_id),
        via ? `mux ch${via.channel}` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      edges.push({
        id: `conn-${c.id}`,
        source: boardNodeId(c.from_board),
        target: boardNodeId(c.to_board),
        sourceHandle: downstream ? "board-out-bottom" : "board-out-top",
        targetHandle: downstream ? "board-in-top" : "board-in-bottom",
        type: "smoothstep",
        ...({ pathOptions: { borderRadius: 18 } } as Partial<Edge>),
        label,
        selected: `conn-${c.id}` === selectedId,
        zIndex: 6,
        style: { stroke: CONNECTOR_COLOR, color: CONNECTOR_COLOR, strokeWidth: 2.5, strokeDasharray: "10 6" },
        labelStyle: { fill: CONNECTOR_COLOR },
        markerEnd: { type: MarkerType.ArrowClosed, color: CONNECTOR_COLOR, width: 16, height: 16 },
      });
    }
    return { nodes, edges, boardRects };
  }, [zones, controllers, muxes, devices, descriptors, selectedId, telemetry, boards, connectors, boardSizes, draggingId]);

  // Yerlesim TURETILMISTIR (store -> computeLayout). Surukleme yalnizca bir
  // JEST'tir: React Flow'un konum degisikligi gecici olarak uygulanir, birakinca
  // ya kart degisir (store) ya da dugum kendi yerlesim yerine geri doner.
  const [flowNodes, setFlowNodes] = useState<Node[]>(nodes);
  useEffect(() => setFlowNodes(nodes), [nodes]);
  const onNodesChange = useCallback((changes: NodeChange<Node>[]) => {
    // YALNIZ konum degisiklikleri uygulanir: secim/olcu React Flow'un kendi ic
    // durumunda kalir, boylece store'dan turetilen dugumler bozulmaz.
    const moves = changes.filter((c) => c.type === "position");
    if (!moves.length) return;
    setFlowNodes((current) => applyNodeChanges(moves, current));
  }, []);

  const handleDragStop = useCallback(
    (event: MouseEvent | TouchEvent, node: Node) => {
      setDraggingId(null);
      if (!boards.length) return;
      const instance = instanceRef.current;
      const item =
        devices.find((d) => d.id === node.id) ?? muxes.find((m) => m.id === node.id);
      const screen = pointerPoint(event);
      if (!instance || !item || !screen) return;
      // Hedef kart FARE KONUMUNA gore secilir (dugumun kendisi `extent`
      // kismindan dolayi kirpilmis olabilir).
      const point = instance.screenToFlowPosition(screen);
      const hit = boardRects.find(
        (r) => point.x >= r.x && point.x <= r.x + r.w && point.y >= r.y && point.y <= r.y + r.h,
      );
      // Kutularin disina birakilan cihaz ANA KARTA doner.
      const target = hit?.id ?? mainBoardId(boards);
      if (target !== effectiveBoardId(item, boards)) setDeviceBoard(node.id, target);
      else setFlowNodes(nodes);
    },
    [boards, boardRects, devices, muxes, nodes, setDeviceBoard],
  );

  if (!controllers.length) {
    return (
      <div className="absolute inset-0 overflow-hidden bg-bg">
        <VisualBackdrop asset="schematic" opacity={0.18} position="center" size="cover" mask="canvasWide" />
        <div className="relative z-10 flex h-full items-center justify-center px-6 text-center text-sm text-faint">
          <p className="rounded-md border border-border/70 bg-bg/70 px-3 py-2 backdrop-blur-sm">
            Upload a <span className="mx-1 font-mono text-muted">.xsa</span> in Setup to render the schematic.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 overflow-hidden bg-bg">
      <VisualBackdrop asset="schematic" opacity={0.11} position="center" size="cover" mask="canvasWide" />
      <ReactFlow
        nodes={flowNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        onNodesChange={onNodesChange}
        onNodeClick={(_, n) => select(n.id.startsWith("zone-") ? null : n.id)}
        onNodeDragStart={(_, n) => setDraggingId(n.id)}
        onNodeDragStop={handleDragStop}
        onPaneClick={() => select(null)}
        onInit={(inst) => {
          instanceRef.current = inst;
          inst.fitView({ padding: 0.18 });
        }}
        nodesDraggable={false}
        fitView
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
      >
        <FitView
          signature={`${controllers.length}-${muxes.length}-${devices.length}-${boards.length}-${connectors.length}`}
        />
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--border)" />
        <Controls showInteractive={false} className="!bg-elev !border-border" />
        <MiniMap
          pannable
          zoomable
          nodeStrokeWidth={2}
          nodeColor={(n) => (n.type === "zone" || n.type === "board" ? "transparent" : "var(--chip-body)")}
          nodeStrokeColor={(n) =>
            n.type === "zone"
              ? "var(--border)"
              : n.type === "board"
                ? "var(--accent)"
                : n.selected
                  ? "var(--accent)"
                  : "var(--chip-body-edge)"
          }
        />
      </ReactFlow>
    </div>
  );
}
