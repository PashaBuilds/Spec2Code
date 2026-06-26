import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, Save, Upload, Wand2 } from "lucide-react";
import { api } from "@/lib/api";
import type { LlmConfig, RulesetResult, ValidationIssue } from "@/lib/types";
import { Badge, Button, Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui";
import { cn } from "@/lib/utils";

type Ruleset = Record<string, any>;

const PREFIX_KEYS = [
  "uint8_t",
  "uint16_t",
  "uint32_t",
  "uint64_t",
  "int32_t",
  "struct_pointer",
  "static_var",
  "pointer",
];

interface RulesetStudioProps {
  llm: LlmConfig;
  onSaved: (ref: string) => void;
}

function cloneRuleset(ruleset: Record<string, unknown>): Ruleset {
  return JSON.parse(JSON.stringify(ruleset)) as Ruleset;
}

function asText(value: unknown): string {
  if (value === undefined || value === null) return "";
  return String(value);
}

function valuePreview(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function bufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

function issueTone(issue: ValidationIssue): "warn" | "danger" {
  return issue.severity === "warning" ? "warn" : "danger";
}

export default function RulesetStudio({ llm, onSaved }: RulesetStudioProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [sourceText, setSourceText] = useState("");
  const [sourceName, setSourceName] = useState("coding-standard.md");
  const [sourceBase64, setSourceBase64] = useState("");
  const [result, setResult] = useState<RulesetResult | null>(null);
  const [saveName, setSaveName] = useState("company");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const ruleset = result?.ruleset as Ruleset | undefined;
  const valid = Boolean(result?.valid);
  const checks = result?.checks ?? [];
  const issues = result?.issues ?? [];
  const diffs = result?.diff ?? [];

  function setRuleset(mutator: (next: Ruleset) => void) {
    if (!result?.ruleset) return;
    const next = cloneRuleset(result.ruleset);
    mutator(next);
    setResult({ ...result, ruleset: next, valid: false });
  }

  async function loadFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setSourceName(file.name);
    try {
      if (file.name.toLowerCase().endsWith(".json")) {
        const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
        setSourceText("");
        setSourceBase64("");
        setBusy("validate");
        setResult(await api.validateRuleset(parsed));
        return;
      }
      if (file.name.toLowerCase().endsWith(".docx")) {
        setSourceText("");
        setSourceBase64(bufferToBase64(await file.arrayBuffer()));
        return;
      }
      setSourceBase64("");
      setSourceText(await file.text());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function extractRuleset() {
    setError(null);
    setBusy("extract");
    try {
      setResult(await api.extractRuleset({
        filename: sourceName,
        text: sourceBase64 ? "" : sourceText,
        content_base64: sourceBase64,
        llm,
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function validateRuleset() {
    if (!ruleset) return;
    setError(null);
    setBusy("validate");
    try {
      setResult(await api.validateRuleset(ruleset));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  async function saveRuleset() {
    if (!ruleset) return;
    setError(null);
    setBusy("save");
    try {
      const saved = await api.saveRuleset(saveName, ruleset);
      setResult(saved);
      if (saved.ref) onSaved(saved.ref);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mt-3 rounded-md border border-border bg-inset p-3" data-testid="ruleset-studio">
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm text-text">
          <Wand2 className="h-4 w-4 text-accent" />
          Coding Standard Studio
          {result && <Badge tone={valid ? "ok" : "warn"}>{valid ? "valid" : "review"}</Badge>}
        </div>
        <input
          ref={fileRef}
          type="file"
          accept=".docx,.md,.txt,.json,application/json,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="hidden"
          onChange={(event) => void loadFile(event.target.files?.[0])}
        />
        <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
          <Upload className="h-4 w-4" /> Source
        </Button>
      </div>

      {error && (
        <div className="mb-3 rounded-md border border-danger/40 bg-danger/15 px-3 py-2 text-xs text-danger">
          {error}
        </div>
      )}

      <div className="space-y-3">
        <div className="space-y-1.5">
          <Label>Source text</Label>
          <textarea
            data-testid="ruleset-source-text"
            value={sourceText}
            onChange={(event) => {
              setSourceText(event.target.value);
              setSourceBase64("");
              setSourceName(sourceName || "coding-standard.md");
            }}
            placeholder={sourceBase64 ? `${sourceName} ready` : "Paste coding standard text or load .docx/.md/.txt"}
            className="min-h-24 w-full resize-y rounded-md border border-border bg-panel px-3 py-2 font-mono text-xs text-text placeholder:text-faint focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-accent"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            data-testid="ruleset-build"
            size="sm"
            onClick={() => void extractRuleset()}
            disabled={busy !== null || (!sourceBase64 && !sourceText.trim())}
          >
            <Wand2 className="h-4 w-4" /> {busy === "extract" ? "Building..." : "Build candidate"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => void validateRuleset()} disabled={busy !== null || !ruleset}>
            <CheckCircle2 className="h-4 w-4" /> Validate
          </Button>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <Input
              data-testid="ruleset-save-name"
              value={saveName}
              onChange={(event) => setSaveName(event.target.value)}
              placeholder="company"
              className="min-w-0"
            />
            <Button data-testid="ruleset-save" size="sm" onClick={() => void saveRuleset()} disabled={busy !== null || !ruleset || !valid}>
              <Save className="h-4 w-4" /> Save
            </Button>
          </div>
        </div>

        {result?.llm_error && (
          <div className="rounded-md border border-warn/40 bg-warn/10 px-3 py-2 text-xs text-warn">
            LLM: {result.llm_error}
          </div>
        )}

        {ruleset && (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Brace style</Label>
                <Select
                  value={asText(ruleset.formatting?.brace_style)}
                  onValueChange={(value) => setRuleset((next) => { next.formatting.brace_style = value; })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="allman">allman</SelectItem>
                    <SelectItem value="attach">attach</SelectItem>
                    <SelectItem value="k&r">k&amp;r</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Max line</Label>
                <Input
                  type="number"
                  min={60}
                  max={180}
                  value={asText(ruleset.formatting?.max_line_length)}
                  onChange={(event) => setRuleset((next) => {
                    next.formatting.max_line_length = Number(event.target.value);
                  })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Indent</Label>
                <Input value={asText(ruleset.formatting?.indent)} readOnly />
              </div>
              <div className="space-y-1.5">
                <Label>Line ending</Label>
                <Input value={asText(ruleset.formatting?.line_ending)} readOnly />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Function regex</Label>
              <Input
                value={asText(ruleset.naming?.function_regex)}
                onChange={(event) => setRuleset((next) => { next.naming.function_regex = event.target.value; })}
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5">
                <Label>Print terminator</Label>
                <Input
                  value={asText(ruleset.print_conventions?.line_terminator_in_prints)}
                  onChange={(event) => setRuleset((next) => {
                    next.print_conventions.line_terminator_in_prints = event.target.value;
                  })}
                />
              </div>
              <label className="flex items-end gap-2 pb-2 text-xs text-muted">
                <input
                  type="checkbox"
                  checked={Boolean(ruleset.doxygen?.required_on_public_functions)}
                  onChange={(event) => setRuleset((next) => {
                    next.doxygen.required_on_public_functions = event.target.checked;
                  })}
                  className="h-4 w-4 accent-[var(--accent)]"
                />
                Doxygen public functions
              </label>
            </div>

            <div className="space-y-1.5">
              <Label>Hungarian prefixes</Label>
              <div className="grid grid-cols-2 gap-2">
                {PREFIX_KEYS.map((key) => (
                  <div key={key} className="grid grid-cols-[minmax(0,1fr)_70px] items-center gap-2">
                    <span className="truncate font-mono text-[11px] text-muted">{key}</span>
                    <Input
                      value={asText(ruleset.naming?.hungarian_prefixes?.[key])}
                      onChange={(event) => setRuleset((next) => {
                        next.naming.hungarian_prefixes[key] = event.target.value;
                      })}
                      className="h-8 px-2"
                    />
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Checks</Label>
                <div className="space-y-1">
                  {checks.map((check) => (
                    <div key={check.name} className="flex items-start gap-2 text-xs">
                      {check.passed ? (
                        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ok" />
                      ) : (
                        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-danger" />
                      )}
                      <span className={check.passed ? "text-muted" : "text-danger"}>
                        {check.name}: {check.detail}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="space-y-1.5">
                <Label>Issues</Label>
                <div className="max-h-32 space-y-1 overflow-auto">
                  {issues.length === 0 && <div className="text-xs text-muted">none</div>}
                  {issues.map((issue, index) => (
                    <div key={`${issue.path}-${index}`} className="text-xs">
                      <Badge tone={issueTone(issue)}>{issue.severity ?? "error"}</Badge>{" "}
                      <span className={issue.severity === "warning" ? "text-warn" : "text-danger"}>
                        {issue.path}: {issue.message}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Diff vs default</Label>
              <div className="max-h-32 overflow-auto rounded border border-border bg-panel p-2">
                {diffs.length === 0 && <div className="text-xs text-muted">no changes</div>}
                {diffs.map((diff) => (
                  <div key={diff.path} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-2 text-[11px]">
                    <span className="truncate font-mono text-muted">{diff.path}</span>
                    <span className="truncate font-mono text-accent">{valuePreview(diff.candidate)}</span>
                  </div>
                ))}
              </div>
            </div>

            <details className="rounded border border-border bg-panel p-2">
              <summary className="flex cursor-pointer items-center gap-2 text-xs text-muted">
                <FileText className="h-3.5 w-3.5" /> JSON preview
              </summary>
              <pre className={cn("mt-2 max-h-48 overflow-auto text-[11px] text-muted")}>
                {JSON.stringify(ruleset, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </div>
    </div>
  );
}
