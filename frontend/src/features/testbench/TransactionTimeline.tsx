import { useMemo } from "react";
import { AudioWaveform } from "lucide-react";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";

const WINDOW_MS = 60_000;

function timeLabel(at: number): string {
  const date = new Date(at);
  return `${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}:${String(date.getSeconds()).padStart(2, "0")}`;
}

/** Host'tan gönderilen S2C işlemlerinin son 60 sn'lik şerit görünümü +
 * son işlemler listesi (Test Bench, telemetri ve register okumaları dahil). */
export default function TransactionTimeline() {
  const busLog = useStore((s) => s.busLog);
  const now = Date.now();
  const windowed = useMemo(
    () => busLog.filter((entry) => now - entry.at <= WINDOW_MS),
    [busLog, now],
  );

  if (busLog.length === 0) return null;

  return (
    <div className="mt-3 shrink-0 rounded-lg border border-border bg-elev">
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <AudioWaveform className="h-3.5 w-3.5 text-accent" aria-hidden />
        <span className="text-xs font-semibold text-text">İşlem zaman çizelgesi</span>
        <span className="font-mono text-[10px] text-faint">son 60 sn • {windowed.length} işlem</span>
      </div>
      <div className="relative mx-3 mt-2 h-8 overflow-hidden rounded border border-border bg-bg">
        {windowed.map((entry, index) => {
          const x = 100 - ((now - entry.at) / WINDOW_MS) * 100;
          return (
            <span
              key={`${entry.at}-${index}`}
              title={`${timeLabel(entry.at)} ${entry.device} • ${entry.operation} (${entry.duration_ms} ms)`}
              className={cn(
                "absolute top-1 h-6 w-[3px] rounded-sm",
                entry.ok ? "bg-ok/80" : "bg-danger",
              )}
              style={{ left: `${x}%` }}
            />
          );
        })}
      </div>
      <div className="max-h-28 overflow-auto px-3 py-2">
        {[...busLog].slice(-10).reverse().map((entry, index) => (
          <div key={`${entry.at}-${index}`} className="grid grid-cols-[64px_minmax(0,1fr)_auto_auto] gap-2 py-0.5 font-mono text-[11px]">
            <span className="text-faint">{timeLabel(entry.at)}</span>
            <span className="truncate text-muted">
              {entry.device} <span className="text-faint">•</span> {entry.operation}
            </span>
            <span className={entry.ok ? "text-ok" : "text-danger"}>{entry.ok ? "OK" : "HATA"}</span>
            <span className="text-faint">{entry.duration_ms} ms</span>
          </div>
        ))}
      </div>
    </div>
  );
}
