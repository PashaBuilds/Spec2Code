import { Plus, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import type { CatalogDevice } from "@/lib/types";
import { Badge, Button, Card } from "@/components/ui";
import CatalogPanel from "@/features/catalog/CatalogPanel";
import DeviceParams from "@/features/device-params/DeviceParams";

export default function SidePanel() {
  const selectedId = useStore((s) => s.selectedId);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const devices = useStore((s) => s.devices);
  const addMux = useStore((s) => s.addMux);
  const addDevice = useStore((s) => s.addDevice);
  const removeNode = useStore((s) => s.removeNode);

  const device = devices.find((d) => d.id === selectedId);
  const mux = muxes.find((m) => m.id === selectedId);
  const controller = controllers.find((c) => c.id === selectedId);

  async function handlePick(dev: CatalogDevice) {
    if (!controller) return;
    if (dev.transport === "i2c_mux") {
      addMux({ part: dev.part, controller_id: controller.id, i2c_address: "0x70", channels: 8 });
      return;
    }
    const full = await api.descriptor(dev.part).catch(() => null);
    const isSpi = controller.type === "spi" || controller.type === "qspi";
    const attach = isSpi
      ? { controller_id: controller.id, spi_chip_select: 0, address_width: full?.transport.address_width ?? null }
      : {
          controller_id: controller.id,
          i2c_address:
            full?.transport.default_address != null
              ? `0x${full.transport.default_address.toString(16).toUpperCase()}`
              : "0x48",
          via_mux: null,
          reset_gpio: null,
          irq_line: null,
        };
    addDevice({
      part: dev.part,
      descriptor_ref: dev.descriptor ?? null,
      attach,
      operations_requested: full?.operations?.map((o) => o.name),
      tests_requested: ["self_test"],
    });
  }

  if (device) return <DeviceParams />;

  if (mux) {
    const attached = devices.filter((d) => d.attach.via_mux?.mux_id === mux.id);
    return (
      <Card className="p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-mono text-sm text-text">{mux.part}</span>
          <Badge tone="accent">mux</Badge>
        </div>
        <dl className="space-y-2 text-xs">
          <Row k="address" v={mux.i2c_address} />
          <Row k="channels" v={String(mux.channels)} />
          <Row k="controller" v={mux.controller_id} />
          <Row k="attached" v={`${attached.length} device(s)`} />
        </dl>
        <p className="mt-3 text-xs text-faint">
          Add a device to this mux by selecting its controller, adding the device, then setting its
          “via mux” + channel in the device panel.
        </p>
        <Button variant="danger" size="sm" className="mt-3" onClick={() => removeNode(mux.id)}>
          <Trash2 className="h-4 w-4" /> Remove mux
        </Button>
      </Card>
    );
  }

  if (controller) {
    return (
      <div className="flex h-full flex-col">
        <div className="mb-3 flex items-center gap-2">
          <Plus className="h-4 w-4 text-accent" />
          <span className="text-sm text-text">Add a device to</span>
          <span className="font-mono text-sm text-accent">{controller.instance}</span>
        </div>
        <div className="min-h-0 flex-1">
          <CatalogPanel mode="pick" controllerType={controller.type} onPick={handlePick} />
        </div>
      </div>
    );
  }

  return (
    <Card className="p-4">
      <p className="text-sm text-text">Nothing selected</p>
      <p className="mt-1 text-xs text-faint">
        Click a controller in the schematic to attach a device (sensor, flash, or an I2C mux). Click
        a device to edit its protocol parameters.
      </p>
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-faint">{k}</dt>
      <dd className="font-mono text-muted">{v}</dd>
    </div>
  );
}
