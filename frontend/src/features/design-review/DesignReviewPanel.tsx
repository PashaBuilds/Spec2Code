import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Files, GitBranch, ListChecks } from "lucide-react";
import { api } from "@/lib/api";
import type { ProjectSpec, SpecValidation, ValidationIssue } from "@/lib/types";
import { useStore } from "@/store/useStore";
import { Badge, Card } from "@/components/ui";
import { buildDesignReview, type ReviewFilePlan } from "@/features/design-review/designReview";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

export default function DesignReviewPanel() {
  const project = useStore((s) => s.project);
  const controllers = useStore((s) => s.controllers);
  const muxes = useStore((s) => s.muxes);
  const devices = useStore((s) => s.devices);
  const llm = useStore((s) => s.llm);
  const buildSpec = useStore((s) => s.buildSpec);
  const [validation, setValidation] = useState<SpecValidation | null>(null);
  const [validateError, setValidateError] = useState<string | null>(null);

  const spec = useMemo(() => buildSpec(), [buildSpec, project, controllers, muxes, devices, llm]);
  const specKey = useMemo(() => JSON.stringify(spec), [spec]);
  const review = useMemo(() => buildDesignReview(spec), [spec]);

  useEffect(() => {
    let active = true;
    setValidateError(null);
    api.validate(JSON.parse(specKey) as ProjectSpec)
      .then((result) => {
        if (active) setValidation(result);
      })
      .catch((error) => {
        if (active) {
          setValidation(null);
          setValidateError(error instanceof Error ? error.message : String(error));
        }
      });
    return () => {
      active = false;
    };
  }, [specKey]);

  const errors = validation?.errors ?? [];
  const warnings = validation?.wiring?.warnings ?? [];
  const status = validateError
    ? { tone: "danger" as Tone, label: "review error" }
    : validation?.valid
      ? { tone: warnings.length ? "warn" as Tone : "ok" as Tone, label: warnings.length ? "warning" : "ready" }
      : { tone: "danger" as Tone, label: "blocked" };

  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-border px-3 py-2">
        <div className="flex items-center gap-2">
          {status.tone === "ok" ? (
            <CheckCircle2 className="h-4 w-4 text-ok" />
          ) : (
            <AlertTriangle className="h-4 w-4 text-warn" />
          )}
          <span className="text-xs font-medium text-muted">Design Review</span>
        </div>
        <Badge tone={status.tone}>{status.label}</Badge>
      </div>

      <div className="grid gap-3 p-3 xl:grid-cols-3">
        <Metric icon={GitBranch} label="Topology" value={`${review.connectionCount} node`} />
        <Metric icon={ListChecks} label="Init writes" value={`${review.initWrites.length} write`} />
        <Metric icon={Files} label="Output plan" value={`${review.files.length} file`} />
      </div>

      {validateError ? (
        <div className="border-t border-border px-3 py-2 text-xs text-danger">{validateError}</div>
      ) : null}

      {errors.length > 0 || warnings.length > 0 ? (
        <div className="space-y-1 border-t border-border p-3">
          {[...errors, ...warnings].slice(0, 5).map((issue, index) => (
            <IssueRow key={`${issue.path}-${index}`} issue={issue} />
          ))}
        </div>
      ) : null}

      <div className="grid gap-3 border-t border-border p-3 xl:grid-cols-2">
        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">
            Bağlantılar
          </div>
          <div className="space-y-1">
            {review.connections.slice(0, 6).map((item) => (
              <div key={item.id} className="grid grid-cols-[1fr_auto] gap-2 rounded bg-inset px-2 py-1.5">
                <span className="min-w-0 truncate font-mono text-xs text-muted">{item.id}</span>
                <span className="font-mono text-xs text-text">{item.endpoint}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">
            Init planı
          </div>
          <div className="space-y-1">
            {review.initWrites.length ? (
              review.initWrites.slice(0, 6).map((item, index) => (
                <div key={`${item.deviceId}-${item.reg}-${index}`} className="grid grid-cols-[1fr_auto] gap-2 rounded bg-inset px-2 py-1.5">
                  <span className="min-w-0 truncate font-mono text-xs text-muted">
                    {item.deviceId}.{item.reg}
                  </span>
                  <span className="font-mono text-xs text-text">{item.value}</span>
                </div>
              ))
            ) : (
              <span className="text-xs text-faint">Init write yok.</span>
            )}
          </div>
        </div>
      </div>

      <div className="border-t border-border p-3">
        <div className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-faint">
          Beklenen dosyalar
        </div>
        <div className="flex flex-wrap gap-1.5">
          {review.files.slice(0, 14).map((file) => (
            <FilePill key={file.path} file={file} />
          ))}
          {review.files.length > 14 ? <Badge tone="neutral">+{review.files.length - 14}</Badge> : null}
        </div>
      </div>
    </Card>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof GitBranch;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border bg-inset px-3 py-2">
      <div className="flex items-center gap-2 text-xs text-faint">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="mt-1 font-mono text-sm text-text">{value}</div>
    </div>
  );
}

function IssueRow({ issue }: { issue: ValidationIssue }) {
  const tone: Tone = issue.severity === "warning" ? "warn" : "danger";
  return (
    <div className="flex items-start gap-2 text-xs">
      <Badge tone={tone} className="shrink-0">
        {issue.severity ?? "error"}
      </Badge>
      <span className="min-w-0 flex-1 text-muted">
        <span className="font-mono text-faint">{issue.path}</span> {issue.message}
      </span>
    </div>
  );
}

function FilePill({ file }: { file: ReviewFilePlan }) {
  const tone: Record<ReviewFilePlan["kind"], Tone> = {
    driver: "accent",
    test: "neutral",
    mock: "ok",
    meta: "warn",
  };
  return (
    <Badge tone={tone[file.kind]} className="font-mono">
      {file.path}
    </Badge>
  );
}
