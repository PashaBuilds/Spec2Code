import type { Device } from "@/lib/types";
import { useStore } from "@/store/useStore";
import GenericConfigEditor from "@/features/device-config/GenericConfigEditor";
import Ltc2991Editor, { defaultLtc2991Config } from "@/features/device-config/Ltc2991Editor";
import type { ComponentType } from "react";

type EditorProps = {
  device: Device;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
};

const EDITORS: Record<string, ComponentType<EditorProps>> = {
  LTC2991: Ltc2991Editor,
};

export function defaultDeviceConfig(part: string): Record<string, unknown> | undefined {
  if (part.toUpperCase() === "LTC2991") return defaultLtc2991Config();
  return undefined;
}

export default function DeviceConfigEditor({ device }: { device: Device }) {
  const updateDevice = useStore((s) => s.updateDevice);
  const Editor = EDITORS[device.part.toUpperCase()] ?? GenericConfigEditor;
  const config = (device.config ?? defaultDeviceConfig(device.part) ?? {}) as Record<string, unknown>;

  return (
    <Editor
      device={device}
      config={config}
      onChange={(next) => updateDevice(device.id, { config: next })}
    />
  );
}
