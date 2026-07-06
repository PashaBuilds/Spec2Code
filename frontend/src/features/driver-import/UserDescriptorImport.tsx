// Kullanıcı descriptor içe aktarma: YAML yükle → şema doğrula → user_descriptors/
// klasörüne kaydet. Kaydedilen parça çözümlemede yerleşik kütüphaneden ÖNCE gelir;
// şematik parça seçici, Generate, Test Bench, Registers ve Seri Hat aynı dosyadan
// beslenir. Doğrulama hataları alan alan Türkçe gösterilir.
import * as React from "react";
import { BookOpenCheck, FileUp, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button } from "@/components/ui";
import type { UserDescriptorEntry } from "@/lib/types";

export default function UserDescriptorImport() {
  const [dir, setDir] = React.useState("");
  const [entries, setEntries] = React.useState<UserDescriptorEntry[]>([]);
  const [busy, setBusy] = React.useState(false);
  const [errors, setErrors] = React.useState<string[]>([]);
  const [notice, setNotice] = React.useState("");
  // Örnek şablon backend'den gelir (tek doğruluk kaynağı): testler aynı
  // içeriği doğrulayıcıdan ve TAM üretimden geçirir — indirilen örnek her
  // zaman bilinen-iyi bir başlangıçtır.
  const [example, setExample] = React.useState<{ file: string; content: string } | null>(null);
  const [exampleOpen, setExampleOpen] = React.useState(false);
  const fileRef = React.useRef<HTMLInputElement>(null);

  const loadExample = React.useCallback(async () => {
    if (example) return example;
    const result = await api.userDescriptorExample();
    setExample(result);
    return result;
  }, [example]);

  async function downloadExample() {
    try {
      const ex = await loadExample();
      const url = URL.createObjectURL(new Blob([ex.content], { type: "text/yaml" }));
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = ex.file;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setErrors([err instanceof Error ? err.message : String(err)]);
    }
  }

  async function toggleExample() {
    try {
      await loadExample();
      setExampleOpen((prev) => !prev);
    } catch (err) {
      setErrors([err instanceof Error ? err.message : String(err)]);
    }
  }

  const refresh = React.useCallback(async () => {
    try {
      const result = await api.userDescriptors();
      setDir(result.dir);
      setEntries(result.descriptors);
    } catch {
      /* backend kapalıyken sessiz kal */
    }
  }, []);

  React.useEffect(() => {
    void refresh();
    // Descriptor Sihirbazı kaydettiğinde listeyi tazele.
    const handler = () => void refresh();
    window.addEventListener("user-descriptors-changed", handler);
    return () => window.removeEventListener("user-descriptors-changed", handler);
  }, [refresh]);

  function parseUploadError(message: string): string[] {
    // req() detail'i JSON string'e çevirir: {"message": ..., "errors": [...]}
    try {
      const detail = JSON.parse(message) as { message?: string; errors?: string[] };
      if (detail.errors?.length) return detail.errors;
      if (detail.message) return [detail.message];
    } catch {
      /* düz metin */
    }
    return [message];
  }

  async function handleFiles(files: FileList | null) {
    if (!files?.length || busy) return;
    setBusy(true);
    setErrors([]);
    setNotice("");
    const failures: string[] = [];
    let savedCount = 0;
    for (const file of Array.from(files)) {
      try {
        const content = await file.text();
        const result = await api.uploadUserDescriptor(content);
        savedCount += 1;
        if (result.overrides_builtin) {
          setNotice((prev) =>
            `${prev ? prev + " " : ""}${result.part}: yerleşik descriptor'ı gölgeliyor (kullanıcı dosyası öncelikli).`,
          );
        }
      } catch (err) {
        const detail = parseUploadError(err instanceof Error ? err.message : String(err));
        failures.push(`${file.name}:`, ...detail.map((e) => `  ${e}`));
      }
    }
    if (savedCount > 0) {
      setNotice((prev) => `${savedCount} descriptor kaydedildi.${prev ? " " + prev : ""}`);
      await refresh();
    }
    setErrors(failures);
    setBusy(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleDelete(fileName: string) {
    const confirmed = window.confirm(
      `${fileName} silinecek. Bu parçayı kullanan projelerde Generate, yerleşik descriptor'a (varsa) geri döner. Devam edilsin mi?`,
    );
    if (!confirmed) return;
    try {
      await api.deleteUserDescriptor(fileName);
      setNotice(`${fileName} silindi.`);
      await refresh();
    } catch (err) {
      setErrors([err instanceof Error ? err.message : String(err)]);
    }
  }

  return (
    <section className="rounded-lg border border-border bg-elev p-4">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <BookOpenCheck className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-text">Descriptor içe aktar (özel entegre)</h3>
        <Badge tone="accent">user_descriptors</Badge>
        <Button size="sm" variant="outline" onClick={() => void refresh()} className="ml-auto">
          <RefreshCw className="h-3.5 w-3.5" aria-hidden />
          Yenile
        </Button>
      </div>
      <p className="mb-1 text-xs leading-relaxed text-muted">
        Kendi entegrenin YAML descriptor'ını yükle: şema doğrulanır ve aşağıdaki klasöre kaydedilir.
        Kaydedilen parça şematik parça seçicide görünür; Generate, Test Bench, Registers ve Seri Hat
        yerleşik entegrelerle birebir aynı şekilde bu dosyadan üretilir. Aynı adlı yerleşik parça
        varsa <span className="text-text">kullanıcı dosyası önceliklidir</span>. Yazım kuralları için
        Kılavuz'daki "Descriptor yazım rehberi" bölümüne bak.
      </p>
      {dir ? (
        <p className="mb-3 break-all font-mono text-[11px] text-faint" title="YAML dosyalarını doğrudan bu klasöre de koyabilirsin.">
          klasör: {dir}
        </p>
      ) : null}

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept=".yaml,.yml"
          multiple
          data-testid="user-descriptor-file"
          onChange={(e) => void handleFiles(e.target.files)}
          disabled={busy}
          className="block text-xs text-muted file:mr-2 file:rounded-md file:border file:border-border file:bg-inset file:px-2 file:py-1.5 file:text-xs file:text-text"
        />
        {busy ? <Loader2 className="h-4 w-4 animate-spin text-accent" aria-hidden /> : <FileUp className="h-4 w-4 text-faint" aria-hidden />}
        <Button size="sm" variant="outline" onClick={() => void downloadExample()} data-testid="descriptor-example-download">
          Örnek şablonu indir
        </Button>
        <Button size="sm" variant="outline" onClick={() => void toggleExample()}>
          {exampleOpen ? "Örneği gizle" : "Örneği görüntüle"}
        </Button>
      </div>

      {exampleOpen && example ? (
        <pre
          className="mb-3 max-h-80 overflow-auto rounded-md border border-border border-l-2 border-l-accent bg-bg px-3 py-2.5 font-mono text-[11px] leading-relaxed text-text"
          data-testid="descriptor-example-content"
        >
          {example.content}
        </pre>
      ) : null}

      {errors.length > 0 ? (
        <div className="mb-3 rounded border border-danger/30 bg-danger/10 p-2">
          <div className="mb-1 text-[11px] font-semibold text-danger">Doğrulama hataları — dosya kaydedilmedi:</div>
          <pre className="max-h-48 overflow-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-danger">
            {errors.join("\n")}
          </pre>
        </div>
      ) : null}
      {notice ? (
        <p className="mb-3 rounded border border-ok/30 bg-ok/10 p-2 text-[11px] text-ok" data-testid="user-descriptor-notice">
          {notice}
        </p>
      ) : null}

      {entries.length > 0 ? (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-xs">
            <thead className="bg-inset">
              <tr className="border-b border-border text-[10px] uppercase tracking-wide text-faint">
                <th className="px-3 py-2">Parça</th>
                <th className="px-3 py-2">Dosya</th>
                <th className="px-3 py-2">Transport</th>
                <th className="px-3 py-2 text-right">Register</th>
                <th className="px-3 py-2">Operasyonlar</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {entries.map((entry) => (
                <tr key={entry.file} className={entry.error ? "bg-danger/5" : undefined}>
                  <td className="px-3 py-2 font-mono font-semibold text-text">{entry.part ?? "?"}</td>
                  <td className="px-3 py-2 font-mono text-muted">{entry.file}</td>
                  <td className="px-3 py-2">
                    {entry.error ? (
                      <span className="text-danger" title={entry.error}>bozuk YAML</span>
                    ) : (
                      <Badge tone="neutral">{(entry.transport ?? "?").toUpperCase()}</Badge>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right font-mono text-muted">{entry.registers ?? "-"}</td>
                  <td className="max-w-72 truncate px-3 py-2 font-mono text-[11px] text-muted" title={(entry.operations ?? []).join(", ")}>
                    {(entry.operations ?? []).join(", ")}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => void handleDelete(entry.file)}
                      className="text-danger hover:opacity-80"
                      title="Sil"
                    >
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-xs text-faint">Henüz kullanıcı descriptor'ı yok.</p>
      )}
    </section>
  );
}
