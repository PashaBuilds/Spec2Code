import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, Rocket, Usb } from "lucide-react";
import { Badge, Button, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { api, openRunboardSocket } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { JobEvent } from "@/lib/types";

interface RunOnBoardCardProps {
  vitisPath: string;
  workspacePath: string;
  platformName: string;
  appName: string;
  processor: string;
  platform: string;
  ready: boolean;
}

type FpgaChoice = "auto" | "yes" | "no";

/** JTAG üzerinden reset -> psu_init -> (bit) -> ELF indir -> çalıştır. */
export default function RunOnBoardCard({
  vitisPath,
  workspacePath,
  platformName,
  appName,
  processor,
  platform,
  ready,
}: RunOnBoardCardProps) {
  const [programFpga, setProgramFpga] = useState<FpgaChoice>("auto");
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const closeSocketRef = useRef<null | (() => void)>(null);

  useEffect(() => () => closeSocketRef.current?.(), []);

  const canRun = Boolean(vitisPath.trim() && workspacePath.trim() && platformName.trim() && appName.trim()) && !running;

  async function run() {
    if (!canRun) return;
    closeSocketRef.current?.();
    setEvents([]);
    setError("");
    setDone(false);
    setRunning(true);
    try {
      const response = await api.runOnBoard({
        vitis_path: vitisPath.trim(),
        workspace_path: workspacePath.trim(),
        platform_name: platformName.trim(),
        app_name: appName.trim(),
        processor: processor.trim(),
        platform: platform as import("@/lib/types").PlatformId,
        program_fpga: programFpga,
        timeout_s: 300,
      });
      closeSocketRef.current = openRunboardSocket(
        response.runboard_job_id,
        (event) => {
          setEvents((current) => [...current, event]);
          if (event.event === "runboard.error" && typeof event.message === "string") {
            setError(event.message);
          }
        },
        () => {
          setRunning(false);
          void api.runOnBoardResult(response.runboard_job_id).then((result) => {
            if (result.status === "done") setDone(true);
            if (result.error) setError(result.error);
          }).catch(() => undefined);
        },
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setRunning(false);
    }
  }

  return (
    <div className={cn(
      "mt-3 rounded-md border p-3",
      done ? "border-ok/40 bg-ok/5" : "border-border bg-inset/60",
    )}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Rocket className="h-4 w-4 text-accent" aria-hidden />
          <span className="text-xs font-semibold text-text">Board&apos;da çalıştır (JTAG / xsdb)</span>
          {done ? <Badge tone="ok">çalışıyor</Badge> : null}
        </div>
        <div className="flex items-center gap-2">
          <Badge tone="neutral">{processor}</Badge>
          <Badge tone="neutral">{appName || "app"}</Badge>
        </div>
      </div>
      <p className="mb-3 text-[11px] leading-relaxed text-muted">
        Kart JTAG boot modunda ve USB-JTAG kablosu takılı olmalı. Akış:{" "}
        {platform === "versal"
          ? "PDI programla (PLM + PL dahil) → ELF indir → başlat"
          : platform === "zynq_7000"
            ? "sistem reset → ps7_init → bitstream (varsa) → ELF indir → başlat"
            : "sistem reset → psu_init → bitstream (varsa) → ELF indir → başlat"}
        . Uygulama çıktısını UART konsolundan izleyebilirsin.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <div className={cn("w-44", platform === "versal" && "hidden")}>
          <Label htmlFor="runboard-fpga">PL bitstream</Label>
          <Select value={programFpga} onValueChange={(value) => setProgramFpga(value as FpgaChoice)}>
            <SelectTrigger id="runboard-fpga">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">Auto (bulunursa yükle)</SelectItem>
              <SelectItem value="yes">Zorunlu yükle</SelectItem>
              <SelectItem value="no">Yükleme</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button type="button" onClick={run} disabled={!canRun}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Usb className="h-4 w-4" aria-hidden />}
          Yükle &amp; Çalıştır
        </Button>
        {!ready ? (
          <span className="text-[11px] text-faint">İpucu: önce workspace build&apos;inin ELF ürettiğinden emin ol.</span>
        ) : null}
      </div>
      {error ? (
        <p className="mt-2 whitespace-pre-wrap rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">
          {error}
        </p>
      ) : null}
      {events.length > 0 ? (
        <div className="mt-2 max-h-32 overflow-auto rounded border border-border bg-bg p-2">
          {events
            .filter((event) => typeof event.message === "string")
            .map((event, index) => (
              <div key={index} className="grid grid-cols-[64px_minmax(0,1fr)] gap-2 py-0.5 text-[11px]">
                <span className="font-mono text-faint">{String(event.stage ?? "")}</span>
                <span className={cn("min-w-0", event.event === "runboard.error" ? "text-danger" : "text-muted")}>
                  {String(event.message)}
                </span>
              </div>
            ))}
          {done ? (
            <div className="mt-1 flex items-center gap-1.5 text-[11px] text-ok">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden /> ELF board üzerinde çalışıyor.
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
