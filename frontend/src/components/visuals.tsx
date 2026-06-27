import type { CSSProperties } from "react";
import { cn } from "@/lib/utils";

type VisualAsset = "setup" | "generate" | "schematic";
type VisualMask = "header" | "side" | "empty" | "canvas" | "none";

const VISUAL_ASSETS: Record<VisualAsset, string> = {
  setup: "/visuals/setup-board.webp",
  generate: "/visuals/generate-qc.webp",
  schematic: "/visuals/schematic-traces.webp",
};

const MASKS: Record<VisualMask, string | undefined> = {
  header: "linear-gradient(to bottom, rgba(0,0,0,1), rgba(0,0,0,0.58) 54%, rgba(0,0,0,0))",
  side: "linear-gradient(105deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.72) 46%, rgba(0,0,0,1) 100%)",
  empty: "linear-gradient(105deg, rgba(0,0,0,0.18), rgba(0,0,0,0.9) 58%, rgba(0,0,0,0.96))",
  canvas: "radial-gradient(circle at 50% 50%, rgba(0,0,0,0.82), rgba(0,0,0,0.18) 58%, rgba(0,0,0,0))",
  none: undefined,
};

interface VisualBackdropProps {
  asset: VisualAsset;
  className?: string;
  opacity?: number;
  position?: string;
  size?: string;
  mask?: VisualMask;
}

export function VisualBackdrop({
  asset,
  className,
  opacity = 0.32,
  position = "center",
  size = "cover",
  mask = "none",
}: VisualBackdropProps) {
  const maskImage = MASKS[mask];
  const style: CSSProperties = {
    backgroundImage: `url(${VISUAL_ASSETS[asset]})`,
    backgroundPosition: position,
    backgroundSize: size,
    opacity,
    maskImage,
    WebkitMaskImage: maskImage,
  };

  return (
    <div
      aria-hidden
      className={cn("pointer-events-none absolute inset-0 bg-no-repeat", className)}
      style={style}
    />
  );
}
