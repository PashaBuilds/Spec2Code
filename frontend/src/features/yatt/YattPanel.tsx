import { Fragment, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, Download, FileText, Loader2 } from "lucide-react";
import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import { findManifest, loadCachedManifest } from "@/features/testbench/manifest";
import type { TestbenchManifest, YattBodyField, YattCatalogResponse, YattMessage } from "@/lib/types";

// Govde sablon alan tabloları backend'den gelir (GET /api/yatt/catalog ->
// body_layouts), backend/yatt.py _BODY_LAYOUTS'un JSON-serilestirilmis hali
// (bkz. yatt.body_layouts_json()) — burada elle kopyalanmis bir sabit YOK,
// tek dogruluk kaynagi backend'dir.
function formatOffset(f: YattBodyField): string {
  return f.offset === null || f.offset === undefined ? "değişken" : String(f.offset);
}

function formatSize(f: YattBodyField): string {
  return f.size === null || f.size === undefined ? "değişken" : String(f.size);
}

const DIR_LABEL: Record<string, { label: string; tone: "accent" | "neutral" | "ok" }> = {
  req: { label: "istek/yanıt", tone: "accent" },
  unsolicited: { label: "kendiliğinden", tone: "neutral" },
};

function responseBodyName(body: string): string {
  if (body === "trace") return "trace";
  if (body === "cit") return "cit";
  return "response_std";
}

function bodyDisplay(message: YattMessage): string {
  const response = responseBodyName(message.body);
  return message.body === response ? message.body : `${message.body} → ${response}`;
}

export default function YattPanel() {
  const files = useStore((s) => s.job.files);
  const previousFiles = useStore((s) => s.previousFiles);
  const jobStatus = useStore((s) => s.job.status);
  const projectName = useStore((s) => s.project.name);

  const manifestFiles = files.length > 0 ? files : jobStatus === "running" ? [] : previousFiles;
  const manifest: TestbenchManifest | null = useMemo(
    () => findManifest(manifestFiles) ?? loadCachedManifest(projectName),
    [manifestFiles, projectName],
  );

  const [catalog, setCatalog] = useState<YattCatalogResponse | null>(null);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<string>("");
  const [exporting, setExporting] = useState<"html" | "md" | "">("");

  useEffect(() => {
    let cancelled = false;
    api.yattCatalog()
      .then((res) => { if (!cancelled) setCatalog(res); })
      .catch((err) => { if (!cancelled) setError(err instanceof Error ? err.message : String(err)); });
    return () => { cancelled = true; };
  }, []);

  const messages = useMemo(
    () => [...(catalog?.messages ?? [])].sort((a, b) => a.id.localeCompare(b.id)),
    [catalog],
  );

  async function doExport(fmt: "html" | "md") {
    setExporting(fmt);
    setError("");
    try {
      const blob = await api.yattExport(fmt, manifest ?? undefined);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `yatt.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setExporting("");
    }
  }

  if (!catalog) {
    return (
      <Card className="mx-auto max-w-3xl p-6">
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          {error ? <span className="text-danger">{error}</span> : "YATT kataloğu yükleniyor…"}
        </div>
      </Card>
    );
  }

  const hasManifestExtras = Boolean(manifest?.devices?.length || manifest?.cit?.olcumler?.length);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <Card className="shrink-0 p-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-accent" aria-hidden />
            <span className="text-sm font-semibold text-text">Arayüz / YATT — S2C-MSG protokol tablosu</span>
          </div>
          <Badge tone="accent" className="font-mono">kontrat CRC32 {catalog.crc32}</Badge>
          <Badge tone="neutral">{messages.length} mesaj</Badge>
          {hasManifestExtras ? (
            <Badge tone="ok" title="Export'a cihaz/CİT tabloları dahil edilecek">manifest zenginleştirmesi hazır</Badge>
          ) : (
            <Badge tone="neutral" title="Generate çalıştırılınca cihaz/CİT tabloları export'a eklenir">manifest yok — katalog-yalın</Badge>
          )}
          <span className="ml-auto flex items-center gap-2">
            <Button size="sm" onClick={() => void doExport("html")} disabled={exporting !== ""}>
              {exporting === "html" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Download className="h-4 w-4" aria-hidden />}
              YATT indir (HTML)
            </Button>
            <Button size="sm" variant="outline" onClick={() => void doExport("md")} disabled={exporting !== ""}>
              {exporting === "md" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Download className="h-4 w-4" aria-hidden />}
              YATT indir (MD)
            </Button>
          </span>
        </div>
        {error ? (
          <p className="mt-2 rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{error}</p>
        ) : null}
      </Card>

      <div className="grid shrink-0 grid-cols-1 gap-3 md:grid-cols-2">
        <Card className="p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">Başlık formatı (12 bayt, LE)</h3>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wide text-faint">
                <th className="py-1 pr-2">alan</th>
                <th className="py-1 pr-2">tip</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {catalog.header.map((f) => (
                <tr key={f.name}>
                  <td className="py-1 pr-2 font-mono text-text">{f.name}</td>
                  <td className="py-1 pr-2 font-mono text-muted">{f.type}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-[11px] leading-relaxed text-faint">
            Yanıt ID = istek ID | 0x80000000 (bit31). Resync: imza <span className="font-mono">.. .. 43 53</span> (istek) /
            <span className="font-mono"> .. .. 43 D3</span> (yanıt); boy sınır aşımı/4'e bölünmezlik → 1 bayt kaydırmalı arama.
          </p>
        </Card>

        <Card className="p-3">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-faint">Hata kodları</h3>
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-[10px] uppercase tracking-wide text-faint">
                <th className="py-1 pr-2">kod</th>
                <th className="py-1 pr-2">etiket</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {Object.entries(catalog.status_codes)
                .sort((a, b) => Number(a[0]) - Number(b[0]))
                .map(([code, label]) => (
                  <tr key={code}>
                    <td className="py-1 pr-2 font-mono text-text">{code}</td>
                    <td className="py-1 pr-2 font-mono text-muted">{label}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card className="min-h-0 flex-1 overflow-auto p-0">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-elev">
            <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">ad</th>
              <th className="px-3 py-2">yön</th>
              <th className="px-3 py-2">gövde şablonu</th>
              <th className="px-3 py-2">açıklama</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {messages.map((message) => {
              const dir = DIR_LABEL[message.dir] ?? { label: message.dir, tone: "neutral" as const };
              const isOpen = expanded === message.id;
              const responseBody = responseBodyName(message.body);
              const bodyLayouts = catalog.body_layouts ?? {};
              const fields = [
                ...(bodyLayouts[message.body] ?? []),
                ...(responseBody !== message.body ? bodyLayouts[responseBody] ?? [] : []),
              ];
              return (
                <Fragment key={message.id}>
                  <tr
                    className="cursor-pointer hover:bg-inset/50"
                    onClick={() => setExpanded(isOpen ? "" : message.id)}
                  >
                    <td className="px-3 py-1.5 font-mono text-text">
                      <span className="mr-1 inline-flex items-center">
                        {isOpen ? <ChevronDown className="h-3 w-3" aria-hidden /> : <ChevronRight className="h-3 w-3" aria-hidden />}
                      </span>
                      {message.id}
                    </td>
                    <td className="px-3 py-1.5 font-mono text-text">{message.name}</td>
                    <td className="px-3 py-1.5">
                      <Badge tone={dir.tone}>{dir.label}</Badge>
                    </td>
                    <td className="px-3 py-1.5 font-mono text-muted">{bodyDisplay(message)}</td>
                    <td className="px-3 py-1.5 text-faint">{message.aciklama}</td>
                  </tr>
                  {isOpen ? (
                    <tr>
                      <td colSpan={5} className="bg-inset/30 px-6 py-3">
                        {fields.length === 0 ? (
                          <span className="text-[11px] text-faint">Bu gövde şablonu için alan tanımı yok.</span>
                        ) : (
                          <table className="w-full text-left text-[11px]">
                            <thead>
                              <tr className="text-[10px] uppercase tracking-wide text-faint">
                                <th className="py-1 pr-3">offset</th>
                                <th className="py-1 pr-3">alan</th>
                                <th className="py-1 pr-3">tip</th>
                                <th className="py-1 pr-3">boy</th>
                                <th className="py-1 pr-3">açıklama</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-border/40">
                              {fields.map((f, i) => (
                                <tr key={i}>
                                  <td className="py-1 pr-3 font-mono text-muted">{formatOffset(f)}</td>
                                  <td className="py-1 pr-3 font-mono text-text">{f.name}</td>
                                  <td className="py-1 pr-3 font-mono text-muted">{f.type}</td>
                                  <td className="py-1 pr-3 font-mono text-muted">{formatSize(f)}</td>
                                  <td className="py-1 pr-3 text-faint">{f.note}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        )}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
