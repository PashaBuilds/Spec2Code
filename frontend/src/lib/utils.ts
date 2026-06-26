import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const ZONE_COLOR: Record<string, string> = {
  ps: "var(--zone-ps)",
  pl: "var(--zone-pl)",
  noc: "var(--zone-noc)",
  aie: "var(--zone-aie)",
};

export function zoneColor(zone: string): string {
  return ZONE_COLOR[zone] ?? "var(--faint)";
}
