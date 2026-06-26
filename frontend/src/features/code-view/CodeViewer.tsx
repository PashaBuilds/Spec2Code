import { useState } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { cpp } from "@codemirror/lang-cpp";
import { oneDark } from "@codemirror/theme-one-dark";
import { useStore } from "@/store/useStore";
import type { QcViolation } from "@/lib/types";
import { Tabs, TabsList, TabsTrigger, TabsContent, Card, Badge } from "@/components/ui";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

function severityTone(severity: string): Tone {
  const s = severity.toLowerCase();
  if (s === "error") return "danger";
  if (s === "warning") return "warn";
  return "neutral"; // style / info / anything else
}

function ViolationRow({ v }: { v: QcViolation }) {
  return (
    <div className="flex items-start gap-3 border-b border-border px-3 py-2 last:border-b-0">
      <Badge tone={severityTone(v.severity)} className="mt-0.5 shrink-0 uppercase">
        {v.severity}
      </Badge>
      <span className="mt-0.5 shrink-0 font-mono text-xs text-muted">
        {v.line}:{v.column}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="font-mono text-accent">{v.source}</span>
          <span className="font-mono text-muted">{v.rule}</span>
        </div>
        <p className="mt-0.5 text-sm text-text">{v.message}</p>
      </div>
    </div>
  );
}

export default function CodeViewer() {
  const files = useStore((s) => s.job.files);
  const qc = useStore((s) => s.job.qc);
  const [active, setActive] = useState<string>(() => files[0]?.path ?? "");

  if (files.length === 0) {
    return (
      <Card className="flex items-center justify-center px-6 py-12">
        <p className="text-sm text-muted">
          Generated code will appear here after a run.
        </p>
      </Card>
    );
  }

  // Keep active selection valid if the file set changes between runs.
  const activePath = files.some((f) => f.path === active) ? active : files[0].path;

  const errorCount = qc
    ? qc.final_violations.filter((v) => v.severity.toLowerCase() === "error").length
    : 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Overall QC status */}
      <div className="flex flex-wrap items-center gap-3">
        {qc ? (
          qc.passed ? (
            <Badge tone="ok">QC passed</Badge>
          ) : (
            <Badge tone="danger">QC: {errorCount} errors</Badge>
          )
        ) : (
          <Badge tone="neutral">QC pending</Badge>
        )}
        {qc?.warning ? (
          <span className="text-xs text-warn">{qc.warning}</span>
        ) : null}
      </div>

      <Tabs value={activePath} onValueChange={setActive}>
        <TabsList className="flex-wrap">
          {files.map((f) => (
            <TabsTrigger key={f.path} value={f.path}>
              {f.name}
            </TabsTrigger>
          ))}
        </TabsList>

        {files.map((f) => {
          const violations = qc
            ? qc.final_violations.filter((v) => v.file.endsWith(f.name))
            : [];
          return (
            <TabsContent key={f.path} value={f.path} className="mt-3">
              <div className="overflow-hidden rounded-lg border border-border bg-inset">
                <CodeMirror
                  value={f.content}
                  height="60vh"
                  theme={oneDark}
                  extensions={[cpp()]}
                  editable={false}
                  readOnly
                  basicSetup={{ lineNumbers: true, foldGutter: false }}
                />
              </div>

              <Card className="mt-3 bg-elev">
                <div className="flex items-center gap-2 border-b border-border px-3 py-2">
                  <span className="text-xs font-medium text-muted">QC findings</span>
                  <span className="font-mono text-xs text-faint">{f.name}</span>
                </div>
                {violations.length > 0 ? (
                  <div>
                    {violations.map((v, i) => (
                      <ViolationRow key={`${v.rule}-${v.line}-${v.column}-${i}`} v={v} />
                    ))}
                  </div>
                ) : (
                  <div className="px-3 py-3">
                    {qc?.passed ? (
                      <Badge tone="ok">no QC findings</Badge>
                    ) : (
                      <span className="text-xs text-muted">
                        No findings for this file.
                      </span>
                    )}
                  </div>
                )}
              </Card>
            </TabsContent>
          );
        })}
      </Tabs>
    </div>
  );
}
