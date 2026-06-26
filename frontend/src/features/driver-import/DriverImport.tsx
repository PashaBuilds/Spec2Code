// Driver source import — the 3-step .c/.h feeding flow (Brief §12).
// 1) scan a folder for driver source pairs, 2) review/correct the proposed part,
// 3) pick a role and persist the confirmation back to the backend.
import * as React from "react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import type { DriverMatch } from "@/lib/types";
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

type Role = "as_is" | "llm_exemplar" | "descriptor_source";

const ROLE_OPTIONS: { value: Role; label: string }[] = [
  { value: "as_is", label: "as-is output" },
  { value: "llm_exemplar", label: "LLM exemplar" },
  { value: "descriptor_source", label: "descriptor source" },
];

const NONE = "__none__"; // Select needs a non-empty value sentinel for "unassigned".

type RowState = {
  part: string; // the (possibly corrected) part, or "" when unassigned
  role: Role;
  saving: boolean;
  saved: boolean;
  error: string | null;
};

function basename(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] || path;
}

function confidenceTone(c: number): "ok" | "warn" | "neutral" {
  if (c >= 0.9) return "ok";
  if (c >= 0.5) return "warn";
  return "neutral";
}

function pct(c: number): string {
  return `${Math.round(c * 100)}%`;
}

function StepLabel({ n, title }: { n: number; title: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="flex h-5 w-5 items-center justify-center rounded-full border border-border bg-inset text-[11px] font-mono text-muted">
        {n}
      </span>
      <span className="text-xs font-medium uppercase tracking-wide text-muted">{title}</span>
    </div>
  );
}

export default function DriverImport() {
  const catalog = useStore((s) => s.catalog);

  const [folder, setFolder] = React.useState("");
  const [scanning, setScanning] = React.useState(false);
  const [scanError, setScanError] = React.useState<string | null>(null);
  const [scanned, setScanned] = React.useState(false);
  const [matches, setMatches] = React.useState<DriverMatch[]>([]);
  const [rows, setRows] = React.useState<Record<string, RowState>>({});

  const updateRow = React.useCallback((stem: string, patch: Partial<RowState>) => {
    setRows((prev) => ({ ...prev, [stem]: { ...prev[stem], ...patch } }));
  }, []);

  const handleScan = React.useCallback(async () => {
    const target = folder.trim();
    if (!target || scanning) return;
    setScanning(true);
    setScanError(null);
    try {
      const result = await api.scanDrivers(target);
      const nextRows: Record<string, RowState> = {};
      for (const m of result) {
        nextRows[m.stem] = {
          part: m.part ?? "",
          role: "as_is",
          saving: false,
          saved: false,
          error: null,
        };
      }
      setMatches(result);
      setRows(nextRows);
      setScanned(true);
    } catch (err) {
      setScanError(err instanceof Error ? err.message : String(err));
      setMatches([]);
      setRows({});
      setScanned(false);
    } finally {
      setScanning(false);
    }
  }, [folder, scanning]);

  const handleConfirm = React.useCallback(
    async (match: DriverMatch) => {
      const row = rows[match.stem];
      if (!row || row.saving || !row.part) return;
      updateRow(match.stem, { saving: true, error: null });
      try {
        const res = await api.confirmDriver(match.stem, row.part, row.role, match.files);
        if (!res.ok) throw new Error("Backend rejected the confirmation.");
        updateRow(match.stem, { saving: false, saved: true, error: null });
      } catch (err) {
        updateRow(match.stem, {
          saving: false,
          saved: false,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    },
    [rows, updateRow],
  );

  return (
    <div className="space-y-6 text-text">
      {/* STEP 1 — scan */}
      <Card className="bg-elev p-4">
        <StepLabel n={1} title="Scan folder" />
        <p className="mt-2 text-xs text-faint">
          Point at a folder of driver sources. Matching <span className="font-mono">.c</span>/
          <span className="font-mono">.h</span> pairs are grouped by stem.
        </p>
        <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-end">
          <div className="flex-1 space-y-1">
            <Label htmlFor="driver-folder">Source folder</Label>
            <Input
              id="driver-folder"
              value={folder}
              placeholder="/path/to/driver/sources"
              onChange={(e) => setFolder(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void handleScan();
              }}
            />
          </div>
          <Button onClick={() => void handleScan()} disabled={scanning || !folder.trim()}>
            {scanning ? "Scanning…" : "Scan folder"}
          </Button>
        </div>
        {scanError && (
          <div className="mt-3 rounded-md border border-danger/40 bg-danger/15 px-3 py-2 text-xs text-danger">
            {scanError}
          </div>
        )}
      </Card>

      {/* STEP 2 + 3 — review/confirm + role/persist */}
      <Card className="bg-elev p-4">
        <div className="flex items-center justify-between">
          <StepLabel n={2} title="Review & confirm" />
          {matches.length > 0 && (
            <span className="text-[11px] font-mono text-faint">
              {matches.length} match{matches.length === 1 ? "" : "es"}
            </span>
          )}
        </div>

        {!scanned ? (
          <p className="mt-4 text-xs text-faint">Scan a folder to see proposed driver matches.</p>
        ) : matches.length === 0 ? (
          <div className="mt-4 rounded-md border border-border bg-inset px-3 py-6 text-center text-xs text-faint">
            no .c/.h matched
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {matches.map((m) => {
              const row = rows[m.stem];
              if (!row) return null;
              const tone = confidenceTone(m.confidence);
              const roleLabel =
                ROLE_OPTIONS.find((r) => r.value === row.role)?.label ?? row.role;
              return (
                <Card key={m.stem} className="bg-inset p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm text-text">{m.stem}</span>
                    <Badge tone={tone}>{pct(m.confidence)}</Badge>
                    {row.saved && <Badge tone="ok">saved</Badge>}
                  </div>

                  <div className="mt-1 font-mono text-xs text-faint">
                    {m.files.map((f) => basename(f)).join(" + ") || "—"}
                  </div>

                  {m.signals.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {m.signals.map((sig, i) => (
                        <span
                          key={`${m.stem}-sig-${i}`}
                          className="rounded bg-elev px-1.5 py-0.5 text-[10px] font-mono text-muted"
                        >
                          {sig}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* STEP 2 — correct part / STEP 3 — pick role */}
                  <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <div className="space-y-1">
                      <Label>Part</Label>
                      <Select
                        value={row.part === "" ? NONE : row.part}
                        onValueChange={(v) =>
                          updateRow(m.stem, {
                            part: v === NONE ? "" : v,
                            saved: false,
                            error: null,
                          })
                        }
                      >
                        <SelectTrigger className="font-mono">
                          <SelectValue placeholder="Select part…" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={NONE} className="font-mono text-faint">
                            unassigned
                          </SelectItem>
                          {catalog.map((d) => (
                            <SelectItem key={d.part} value={d.part} className="font-mono">
                              {d.part}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-1">
                      <Label>Role</Label>
                      <Select
                        value={row.role}
                        onValueChange={(v) =>
                          updateRow(m.stem, { role: v as Role, saved: false, error: null })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLE_OPTIONS.map((r) => (
                            <SelectItem key={r.value} value={r.value}>
                              {r.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="mt-3 flex items-center justify-between gap-3">
                    <div className="min-w-0 text-[11px] text-faint">
                      {row.saved ? (
                        <span className="font-mono text-ok">
                          {m.files.map((f) => basename(f)).join(" + ")} → {row.part} (
                          {pct(m.confidence)})
                        </span>
                      ) : row.error ? (
                        <span className="text-danger">{row.error}</span>
                      ) : (
                        <span className="text-faint">
                          {row.part ? (
                            <>
                              will save as <span className="font-mono text-muted">{row.part}</span> ·{" "}
                              {roleLabel}
                            </>
                          ) : (
                            "pick a part to enable saving"
                          )}
                        </span>
                      )}
                    </div>
                    <Button
                      size="sm"
                      variant={row.saved ? "outline" : "primary"}
                      onClick={() => void handleConfirm(m)}
                      disabled={row.saving || !row.part}
                    >
                      {row.saving ? "Saving…" : row.saved ? "Re-save" : "Confirm & save"}
                    </Button>
                  </div>
                </Card>
              );
            })}

            <div className="pt-1">
              <StepLabel n={3} title="Role & persist" />
              <p className="mt-1 text-[11px] text-faint">
                Each confirmed pair is written to the catalog with its chosen role.
              </p>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
