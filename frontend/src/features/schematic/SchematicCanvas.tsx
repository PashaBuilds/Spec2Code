import { useEffect, useMemo } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  type Edge,
  type Node,
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
import { computeLayout, computeZoneRects } from "./layout";
import { nodeTypes } from "./nodes";
import { zoneColor } from "@/lib/utils";
import { busColor } from "@/lib/busColors";
import { VisualBackdrop } from "@/components/visuals";
import { ltc2991NodeSummary } from "@/features/device-config/ltc2991Model";

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

export default function SchematicCanvas() {
  const zones = useStore((s) => s.zones);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const devices = useStore((s) => s.devices);
  const descriptors = useStore((s) => s.descriptors);
  const selectedId = useStore((s) => s.selectedId);
  const select = useStore((s) => s.select);
  const telemetry = useStore((s) => s.telemetry);

  const { nodes, edges } = useMemo(() => {
    const pos = computeLayout(controllers, muxes, devices);
    const zoneRects = computeZoneRects(zones, controllers, pos);
    const ctrlById = Object.fromEntries(controllers.map((c) => [c.id, c]));
    const hasDescriptor = (part: string) =>
      descriptors.some((d) => d.part === part) ||
      ["LTC2991", "TCA9548A", "MT25Q128", "MT25QU02G", "AD7414", "TMP101", "SHT21", "24LC32A", "DS1682", "LTC2945", "LTM4681"].includes(part);

    const nodes: Node[] = [];
    for (const z of zoneRects) {
      nodes.push({
        id: `zone-${z.id}`,
        type: "zone",
        position: { x: z.x, y: z.y },
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
        position: { x: p.x, y: p.y },
        data: { label: c.instance, type: c.type, base_address: c.base_address, driver: c.driver, zone: c.zone },
        selected: c.id === selectedId,
        draggable: false,
        zIndex: 1,
      });
    }
    for (const m of muxes) {
      const p = pos.get(m.id);
      if (!p) continue;
      nodes.push({
        id: m.id,
        type: "mux",
        position: { x: p.x, y: p.y },
        data: { part: m.part, i2c_address: m.i2c_address, channels: m.channels },
        selected: m.id === selectedId,
        draggable: false,
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
        position: { x: p.x, y: p.y },
        data: {
          part: d.part,
          sub,
          transport,
          hasDescriptor: hasDescriptor(d.part),
          configSummary: d.part.toUpperCase() === "LTC2991" ? ltc2991NodeSummary(d.config) : [],
          telemetry: telemetry[d.id]?.text ?? "",
        },
        selected: d.id === selectedId,
        draggable: false,
        zIndex: 1,
      });
    }

    const edges: Edge[] = [];
    for (const m of muxes) {
      if (ctrlById[m.controller_id]) {
        edges.push({
          id: `e-${m.controller_id}-${m.id}`,
          source: m.controller_id,
          target: m.id,
          label: "I2C",
          ...wireProps("i2c"),
        });
      }
    }
    for (const d of devices) {
      const via = d.attach.via_mux;
      const ctrl = ctrlById[d.attach.controller_id];
      if (via) {
        edges.push({
          id: `e-${via.mux_id}-${d.id}`,
          source: via.mux_id,
          target: d.id,
          label: `ch ${via.channel}`,
          ...wireProps(ctrl?.type ?? "i2c"),
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
          label: lbl,
          ...wireProps(ctrl.type),
        });
      }
    }
    return { nodes, edges };
  }, [zones, controllers, muxes, devices, descriptors, selectedId, telemetry]);

  if (!controllers.length) {
    return (
      <div className="absolute inset-0 overflow-hidden bg-bg">
        <VisualBackdrop asset="schematic" opacity={0.18} position="center" size="cover" mask="canvasWide" />
        <div className="relative z-10 flex h-full items-center justify-center px-6 text-center text-sm text-faint">
          <p className="rounded-md border border-border/70 bg-bg/70 px-3 py-2 backdrop-blur-sm">
            Upload an <span className="mx-1 font-mono text-muted">xparameters.h</span> to render the schematic.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="absolute inset-0 overflow-hidden bg-bg">
      <VisualBackdrop asset="schematic" opacity={0.11} position="center" size="cover" mask="canvasWide" />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, n) => select(n.id.startsWith("zone-") ? null : n.id)}
        onPaneClick={() => select(null)}
        onInit={(inst) => inst.fitView({ padding: 0.18 })}
        nodesDraggable={false}
        fitView
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
      >
        <FitView signature={`${controllers.length}-${muxes.length}-${devices.length}`} />
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="var(--border)" />
        <Controls showInteractive={false} className="!bg-elev !border-border" />
        <MiniMap
          pannable
          zoomable
          nodeStrokeWidth={2}
          nodeColor={(n) => (n.type === "zone" ? "transparent" : "var(--chip-body)")}
          nodeStrokeColor={(n) =>
            n.type === "zone" ? "var(--border)" : n.selected ? "var(--accent)" : "var(--chip-body-edge)"
          }
        />
      </ReactFlow>
    </div>
  );
}
