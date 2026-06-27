import * as React from "react";
import { Card, Badge } from "@/components/ui";
import { VisualBackdrop } from "@/components/visuals";
import { cn } from "@/lib/utils";
import type { JobEvent } from "@/lib/types";
import { useStore } from "@/store/useStore";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

/** A single rendered console line: a colored prefix badge + a human label. */
interface Line {
  tone: Tone;
  prefix: string;
  text: React.ReactNode;
  /** Faint divider line (job.end) — rendered without a badge. */
  divider?: boolean;
}

/** Pull a value off a loosely-typed JobEvent, falling back to a placeholder. */
function field(e: JobEvent, key: string, fallback = "?"): string {
  const v = e[key];
  if (v === undefined || v === null) return fallback;
  return String(v);
}

/** Render the "extra" fields of an event (everything but `event`/`_seq`) as compact JSON. */
function extrasJson(e: JobEvent): string {
  const { event: _event, _seq, ...rest } = e;
  void _event;
  void _seq;
  const keys = Object.keys(rest);
  if (keys.length === 0) return "";
  try {
    return JSON.stringify(rest);
  } catch {
    return "";
  }
}

/** Map a raw job event to a renderable console line (Brief §6 / §19). */
function describe(e: JobEvent): Line {
  switch (e.event) {
    case "job.start":
      return {
        tone: "accent",
        prefix: "PIPELINE",
        text: `starting generation for ${field(e, "project")}`,
      };
    case "codegen.unit":
      return {
        tone: "neutral",
        prefix: "CODEGEN",
        text: `${field(e, "part")} (${field(e, "transport")}) → ${field(e, "module")}.c/.h`,
      };
    case "codegen.done":
      return {
        tone: "ok",
        prefix: "CODEGEN",
        text: `${field(e, "files")} files written`,
      };
    case "imported_sources.copied":
      return {
        tone: Number(e.missing ?? 0) > 0 ? "warn" : "ok",
        prefix: "IMPORT",
        text: `${field(e, "files", "0")} reference file(s), missing=${field(e, "missing", "0")}`,
      };
    case "imported_sources.error":
      return {
        tone: "warn",
        prefix: "IMPORT",
        text: field(e, "message", "imported source manifest could not be read"),
      };
    case "qc.round": {
      const errors = Number(e.errors ?? 0);
      return {
        tone: errors > 0 ? "warn" : "ok",
        prefix: `QC r${field(e, "round")}`,
        text: `errors=${field(e, "errors", "0")} warnings=${field(
          e,
          "warnings",
          "0",
        )} total=${field(e, "total", "0")}`,
      };
    }
    case "qc.fix":
      return {
        tone: "warn",
        prefix: "QC FIX",
        text: `feeding ${field(e, "errors", "0")} violations back to LLM`,
      };
    case "llm.request":
      return {
        tone: "accent",
        prefix: "LLM",
        text: `${field(e, "task")} using ${field(e, "model", "model?")} timeout=${field(
          e,
          "timeout_s",
          "?",
        )}s max_tokens=${field(e, "max_tokens", "?")}`,
      };
    case "llm.done":
      return {
        tone: "ok",
        prefix: "LLM",
        text: `${field(e, "task")} completed with ${field(e, "chars", "0")} chars`,
      };
    case "llm.check":
      return {
        tone: "accent",
        prefix: "LLM QC",
        text: `checking candidate for ${field(e, "file", "file?")}`,
      };
    case "llm.accepted":
      return {
        tone: "ok",
        prefix: "LLM QC",
        text: `candidate accepted for ${field(e, "file", "file?")} warnings=${field(e, "warnings", "0")}`,
      };
    case "llm.rejected":
      return {
        tone: "danger",
        prefix: "LLM QC",
        text: `candidate rejected for ${field(e, "file", "file?")}: ${field(
          e,
          "message",
          "unknown reason",
        )}`,
      };
    case "llm.skipped":
      return {
        tone: "warn",
        prefix: "LLM",
        text: `${field(e, "task")} skipped: ${field(e, "reason", "unknown reason")}`,
      };
    case "llm.error":
      return {
        tone: "danger",
        prefix: "LLM",
        text: `${field(e, "task", "task")} failed: ${field(e, "message", "unknown error")}`,
      };
    case "qc.done": {
      const passed = Boolean(e.passed);
      const warning = typeof e.warning === "string" ? e.warning : "";
      const base = passed
        ? "passed — 0 errors"
        : `stopped with ${field(e, "errors", "0")} error(s)`;
      return {
        tone: passed ? "ok" : "danger",
        prefix: "QC",
        text: warning ? `${base} (${warning})` : base,
      };
    }
    case "result.ready":
      return {
        tone: "ok",
        prefix: "RESULT",
        text: `${field(e, "files")} files, qc_passed=${field(e, "qc_passed")}`,
      };
    case "error":
      return {
        tone: "danger",
        prefix: "ERROR",
        text: field(e, "message", "unknown error"),
      };
    case "job.end":
      return {
        tone: "neutral",
        prefix: "",
        text: `— job ${field(e, "status")} —`,
        divider: true,
      };
    default: {
      const extras = extrasJson(e);
      return {
        tone: "neutral",
        prefix: e.event || "event",
        text: extras ? <span className="text-faint">{extras}</span> : "",
      };
    }
  }
}

const STATUS_PILL: Record<
  "idle" | "running" | "done" | "error",
  { tone: Tone; label: string }
> = {
  idle: { tone: "neutral", label: "idle" },
  running: { tone: "accent", label: "running" },
  done: { tone: "ok", label: "done" },
  error: { tone: "danger", label: "error" },
};

export default function GenerateConsole() {
  const job = useStore((s) => s.job);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const eventCount = job.events.length;

  // Auto-scroll to the newest line whenever a line is appended.
  React.useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [eventCount]);

  const pill = STATUS_PILL[job.status];

  return (
    <Card className="flex h-full min-h-0 flex-col overflow-hidden">
      {/* Header row: status pill + event count */}
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
        <div className="flex items-center gap-2">
          <Badge
            tone={pill.tone}
            className={cn(
              "font-mono uppercase tracking-wide",
              job.status === "running" && "animate-pulse",
            )}
          >
            {pill.label}
          </Badge>
          <span className="font-mono text-xs text-muted">generate console</span>
        </div>
        <span className="font-mono text-xs text-faint">
          {eventCount} {eventCount === 1 ? "event" : "events"}
        </span>
      </div>

      {/* Terminal log */}
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto bg-bg p-3 font-mono text-xs leading-relaxed"
      >
        {eventCount === 0 ? (
          <div className="relative min-h-full overflow-hidden rounded-md border border-border/70 bg-inset px-4 py-10">
            <VisualBackdrop asset="generate" opacity={0.3} position="left bottom" mask="empty" />
            <div className="relative z-10 max-w-sm">
              <Badge tone="neutral" className="font-mono">
                READY
              </Badge>
              <p className="mt-3 text-sm text-text">No run yet.</p>
              <p className="mt-1 text-xs text-muted">
                Configure the schematic, then Generate will stream codegen, LLM, and QC events here.
              </p>
            </div>
          </div>
        ) : (
          <ul className="space-y-1">
            {job.events.map((e, i) => {
              const line = describe(e);
              const key = typeof e._seq === "number" ? e._seq : i;
              if (line.divider) {
                return (
                  <li
                    key={key}
                    className="select-none py-1 text-center text-faint"
                  >
                    {line.text}
                  </li>
                );
              }
              return (
                <li key={key} className="flex items-start gap-2">
                  <Badge tone={line.tone} className="shrink-0 font-mono">
                    {line.prefix}
                  </Badge>
                  <span className="min-w-0 break-words text-text">{line.text}</span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Card>
  );
}
