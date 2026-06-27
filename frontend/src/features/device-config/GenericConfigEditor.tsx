import type { Device } from "@/lib/types";

export default function GenericConfigEditor({ device }: {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}) {
  return (
    <div className="rounded-md border border-border bg-inset px-3 py-3">
      <div className="font-mono text-xs text-muted">{device.part}</div>
      <div className="mt-1 text-xs text-faint">descriptor defaults</div>
    </div>
  );
}

