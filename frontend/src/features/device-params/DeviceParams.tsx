// Protocol-aware device parameter editor (Brief §10).
// Edits the selected device's attach/operations/tests; fields shown depend on
// the resolved controller's transport type (i2c | spi | qspi | gpio).
import * as React from "react";
import { useStore } from "@/store/useStore";
import type { Controller, DescriptorMeta, Device, Mux } from "@/lib/types";
import {
  Badge,
  Button,
  Card,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui";
import { cn } from "@/lib/utils";

const NONE = "__none__";

function Section({
  title,
  children,
  className,
}: {
  title: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-3 border-t border-border px-4 py-4 first:border-t-0", className)}>
      <h3 className="text-[11px] font-semibold uppercase tracking-wide text-faint">{title}</h3>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  );
}

export default function DeviceParams() {
  const selectedId = useStore((s) => s.selectedId);
  const devices = useStore((s) => s.devices);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const descriptors = useStore((s) => s.descriptors);
  const updateDevice = useStore((s) => s.updateDevice);
  const updateDeviceAttach = useStore((s) => s.updateDeviceAttach);
  const removeNode = useStore((s) => s.removeNode);

  const device: Device | undefined = devices.find((d) => d.id === selectedId);

  if (!device) {
    return (
      <Card className="p-6 text-sm text-muted">
        Select a device to edit its parameters.
      </Card>
    );
  }

  const attach = device.attach;
  const controller: Controller | undefined = controllers.find((c) => c.id === attach.controller_id);
  const descriptor: DescriptorMeta | undefined = descriptors.find((d) => d.part === device.part);
  const transport = (controller?.type ?? "").toLowerCase();

  const isI2c = transport === "i2c";
  const isSpiLike = transport === "spi" || transport === "qspi";

  // Muxes that hang off the same controller as this device.
  const eligibleMuxes: Mux[] = muxes.filter((m) => m.controller_id === attach.controller_id);
  const selectedMux: Mux | undefined = attach.via_mux
    ? eligibleMuxes.find((m) => m.id === attach.via_mux!.mux_id)
    : undefined;

  const operations = descriptor?.operations ?? [];
  const requested = device.operations_requested ?? operations;
  const opChecked = (name: string) => requested.includes(name);

  const toggleOp = (name: string, checked: boolean) => {
    const base = device.operations_requested ?? operations;
    const next = checked ? [...base, name] : base.filter((o) => o !== name);
    // preserve descriptor order, dedupe
    const ordered = operations.filter((o) => next.includes(o));
    updateDevice(device.id, { operations_requested: ordered });
  };

  const selfTestChecked = (device.tests_requested ?? []).includes("self_test");
  const toggleSelfTest = (checked: boolean) => {
    updateDevice(device.id, { tests_requested: checked ? ["self_test"] : [] });
  };

  const onMuxChange = (value: string) => {
    if (value === NONE) {
      updateDeviceAttach(device.id, { via_mux: null });
      return;
    }
    updateDeviceAttach(device.id, { via_mux: { mux_id: value, channel: 0 } });
  };

  const onChannelChange = (value: string) => {
    if (!attach.via_mux) return;
    updateDeviceAttach(device.id, {
      via_mux: { mux_id: attach.via_mux.mux_id, channel: Number(value) },
    });
  };

  const transportLabel = controller?.type ? controller.type.toUpperCase() : "—";

  return (
    <Card className="overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-border bg-inset/40 px-4 py-3">
        <div className="min-w-0 space-y-0.5">
          <div className="truncate font-mono text-sm text-text">{device.id}</div>
          <div className="truncate text-xs text-muted">{device.part}</div>
          {controller && (
            <div className="truncate font-mono text-[11px] text-faint">{controller.instance}</div>
          )}
        </div>
        <Badge tone="accent">{transportLabel}</Badge>
      </div>

      {/* I2C connection */}
      {isI2c && (
        <Section title="I2C Connection">
          <Field label="I2C address">
            <Input
              value={attach.i2c_address ?? ""}
              placeholder="0x48"
              onChange={(e) => updateDeviceAttach(device.id, { i2c_address: e.target.value })}
            />
          </Field>

          <Field label="Via mux">
            <Select value={attach.via_mux?.mux_id ?? NONE} onValueChange={onMuxChange}>
              <SelectTrigger>
                <SelectValue placeholder="none" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={NONE}>none</SelectItem>
                {eligibleMuxes.map((m) => (
                  <SelectItem key={m.id} value={m.id}>
                    {m.id} ({m.part})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          {selectedMux && (
            <Field label="Mux channel">
              <Select value={String(attach.via_mux?.channel ?? 0)} onValueChange={onChannelChange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Array.from({ length: selectedMux.channels }, (_, i) => (
                    <SelectItem key={i} value={String(i)}>
                      channel {i}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
          )}

          <div className="grid grid-cols-2 gap-3">
            <Field label="Reset GPIO">
              <Input
                value={attach.reset_gpio == null ? "" : String(attach.reset_gpio)}
                placeholder="optional"
                onChange={(e) =>
                  updateDeviceAttach(device.id, {
                    reset_gpio: e.target.value === "" ? null : e.target.value,
                  })
                }
              />
            </Field>
            <Field label="IRQ line">
              <Input
                value={attach.irq_line == null ? "" : String(attach.irq_line)}
                placeholder="optional"
                onChange={(e) =>
                  updateDeviceAttach(device.id, {
                    irq_line: e.target.value === "" ? null : e.target.value,
                  })
                }
              />
            </Field>
          </div>
        </Section>
      )}

      {/* SPI / QSPI connection */}
      {isSpiLike && (
        <Section title={`${transportLabel} Connection`}>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Chip select">
              <Input
                type="number"
                value={attach.spi_chip_select == null ? "" : String(attach.spi_chip_select)}
                placeholder="0"
                onChange={(e) =>
                  updateDeviceAttach(device.id, {
                    spi_chip_select: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </Field>
            <Field label="Address width">
              <Input
                readOnly
                disabled
                value={attach.address_width == null ? "—" : String(attach.address_width)}
                className="text-faint"
              />
            </Field>
          </div>

          <Field label="Reset GPIO">
            <Input
              value={attach.reset_gpio == null ? "" : String(attach.reset_gpio)}
              placeholder="optional"
              onChange={(e) =>
                updateDeviceAttach(device.id, {
                  reset_gpio: e.target.value === "" ? null : e.target.value,
                })
              }
            />
          </Field>
        </Section>
      )}

      {/* Operations */}
      <Section title="Operations">
        {operations.length === 0 ? (
          <p className="text-xs text-faint">No operations declared in descriptor.</p>
        ) : (
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            {operations.map((op) => (
              <label
                key={op}
                className="flex cursor-pointer items-center gap-2 text-sm text-text"
              >
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 accent-accent"
                  checked={opChecked(op)}
                  onChange={(e) => toggleOp(op, e.target.checked)}
                />
                <span className="font-mono text-xs">{op}</span>
              </label>
            ))}
          </div>
        )}
      </Section>

      {/* Tests */}
      <Section title="Tests">
        <label className="flex cursor-pointer items-center gap-2 text-sm text-text">
          <input
            type="checkbox"
            className="h-3.5 w-3.5 accent-accent"
            checked={selfTestChecked}
            onChange={(e) => toggleSelfTest(e.target.checked)}
          />
          <span className="font-mono text-xs">self_test</span>
        </label>
      </Section>

      {/* Danger zone */}
      <Section title="Danger Zone">
        <Button variant="danger" size="sm" onClick={() => removeNode(device.id)}>
          Remove device
        </Button>
      </Section>
    </Card>
  );
}
