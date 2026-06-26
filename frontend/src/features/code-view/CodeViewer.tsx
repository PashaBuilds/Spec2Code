import { useMemo, useState, type ReactNode } from "react";
import CodeMirror from "@uiw/react-codemirror";
import { cpp } from "@codemirror/lang-cpp";
import { oneDark } from "@codemirror/theme-one-dark";
import { Archive, Download, FileCode2, FileJson, FileText, Folder } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";
import type { GeneratedFile, QcViolation } from "@/lib/types";
import { Card, Badge } from "@/components/ui";

type Tone = "neutral" | "accent" | "ok" | "warn" | "danger";

type FileNode = {
  type: "file";
  name: string;
  path: string;
  displayPath: string;
};

type FolderNode = {
  type: "folder";
  name: string;
  children: TreeNode[];
};

type TreeNode = FileNode | FolderNode;

function severityTone(severity: string): Tone {
  const s = severity.toLowerCase();
  if (s === "error") return "danger";
  if (s === "warning") return "warn";
  return "neutral"; // style / info / anything else
}

function generatedPath(file: GeneratedFile): string {
  if (file.relative_path) return file.relative_path;
  const normalized = file.path.replace(/\\/g, "/");
  const parts = normalized.split("/").filter(Boolean);
  if (parts[0] === "outputs" && parts.length > 2) {
    return parts.slice(2).join("/");
  }
  return parts[parts.length - 1] ?? file.name;
}

function sortTree(nodes: TreeNode[]): TreeNode[] {
  nodes.sort((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const node of nodes) {
    if (node.type === "folder") sortTree(node.children);
  }
  return nodes;
}

function buildTree(files: GeneratedFile[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const file of files) {
    const displayPath = generatedPath(file);
    const parts = displayPath.split("/").filter(Boolean);
    let children = root;

    for (let i = 0; i < Math.max(parts.length - 1, 0); i += 1) {
      const name = parts[i];
      let folder = children.find(
        (node): node is FolderNode => node.type === "folder" && node.name === name,
      );
      if (!folder) {
        folder = { type: "folder", name, children: [] };
        children.push(folder);
      }
      children = folder.children;
    }

    children.push({
      type: "file",
      name: parts[parts.length - 1] ?? file.name,
      path: file.path,
      displayPath,
    });
  }

  return sortTree(root);
}

function fileIcon(name: string) {
  if (name.endsWith(".c") || name.endsWith(".h")) return FileCode2;
  if (name.endsWith(".json")) return FileJson;
  return FileText;
}

function DownloadLink({
  href,
  download,
  children,
  className,
}: {
  href: string;
  download?: string | boolean;
  children: ReactNode;
  className?: string;
}) {
  return (
    <a
      href={href}
      download={download}
      className={cn(
        "inline-flex h-8 items-center justify-center gap-2 rounded-md border border-border bg-transparent px-3 text-sm font-medium text-text transition-colors hover:bg-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
        className,
      )}
    >
      {children}
    </a>
  );
}

function TreeRows({
  nodes,
  activePath,
  onSelect,
  level = 0,
}: {
  nodes: TreeNode[];
  activePath: string;
  onSelect: (path: string) => void;
  level?: number;
}) {
  return (
    <>
      {nodes.map((node) => {
        if (node.type === "folder") {
          return (
            <div key={`${level}-${node.name}`}>
              <div
                className="flex h-8 items-center gap-2 rounded px-2 text-xs font-medium text-muted"
                style={{ paddingLeft: 8 + level * 14 }}
              >
                <Folder className="h-4 w-4 shrink-0 text-accent" />
                <span className="truncate">{node.name}</span>
              </div>
              <TreeRows
                nodes={node.children}
                activePath={activePath}
                onSelect={onSelect}
                level={level + 1}
              />
            </div>
          );
        }

        const Icon = fileIcon(node.name);
        return (
          <button
            key={node.path}
            type="button"
            onClick={() => onSelect(node.path)}
            className={cn(
              "flex h-8 w-full items-center gap-2 rounded px-2 text-left text-xs transition-colors",
              node.path === activePath
                ? "bg-accent/15 text-text"
                : "text-muted hover:bg-inset hover:text-text",
            )}
            style={{ paddingLeft: 8 + level * 14 }}
            title={node.displayPath}
          >
            <Icon className="h-4 w-4 shrink-0 text-faint" />
            <span className="min-w-0 flex-1 truncate font-mono">{node.name}</span>
          </button>
        );
      })}
    </>
  );
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
  const jobId = useStore((s) => s.job.id);
  const files = useStore((s) => s.job.files);
  const qc = useStore((s) => s.job.qc);
  const [active, setActive] = useState<string>(() => files[0]?.path ?? "");
  const tree = useMemo(() => buildTree(files), [files]);

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
  const activeFile = files.find((f) => f.path === activePath) ?? files[0];
  const activeDisplayPath = generatedPath(activeFile);
  const activeDownloadUrl = jobId ? api.jobFileDownloadUrl(jobId, activeFile.path) : null;
  const allDownloadUrl = jobId ? api.jobDownloadUrl(jobId) : null;

  const errorCount = qc
    ? qc.final_violations.filter((v) => v.severity.toLowerCase() === "error").length
    : 0;

  const violations = qc
    ? qc.final_violations.filter((v) => {
        const violationFile = v.file.replace(/\\/g, "/");
        return violationFile.endsWith(activeDisplayPath) || violationFile.endsWith(activeFile.name);
      })
    : [];

  return (
    <div className="flex min-h-0 flex-col gap-4">
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
        <Badge tone="neutral">{files.length} files</Badge>
        {qc?.warning ? (
          <span className="text-xs text-warn">{qc.warning}</span>
        ) : null}
        {allDownloadUrl ? (
          <DownloadLink href={allDownloadUrl} download className="ml-auto">
            <Archive className="h-4 w-4" />
            Download all
          </DownloadLink>
        ) : null}
      </div>

      <div className="grid min-h-0 gap-3 xl:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="min-h-0 overflow-hidden rounded-lg border border-border bg-elev">
          <div className="flex h-10 items-center justify-between border-b border-border px-3">
            <span className="text-xs font-medium text-muted">Generated files</span>
            <Badge tone="neutral">{files.length}</Badge>
          </div>
          <div className="max-h-[64vh] overflow-auto p-2">
            <TreeRows nodes={tree} activePath={activePath} onSelect={setActive} />
          </div>
        </aside>

        <section className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="min-w-0 flex-1 truncate font-mono text-xs text-muted">
              {activeDisplayPath}
            </span>
            {activeDownloadUrl ? (
              <DownloadLink href={activeDownloadUrl} download={activeFile.name}>
                <Download className="h-4 w-4" />
                Download file
              </DownloadLink>
            ) : null}
          </div>

          <div className="overflow-hidden rounded-lg border border-border bg-inset">
            <CodeMirror
              value={activeFile.content}
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
              <span className="min-w-0 truncate font-mono text-xs text-faint">
                {activeDisplayPath}
              </span>
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
                  <span className="text-xs text-muted">No findings for this file.</span>
                )}
              </div>
            )}
          </Card>
        </section>
      </div>
    </div>
  );
}
