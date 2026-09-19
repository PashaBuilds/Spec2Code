// Yapay zeka ile üretim — descriptor: referans metninden (datasheet register tablosu, sürücü
// başlığı) descriptor YAML adayı. Model çıktısı backend'de doğrulayıcıdan geçene kadar hatalar
// modele geri verilir; kabul edilen aday KAYDEDİLMEZ — burada önizlenir/düzenlenir, mevcut
// Doğrula/Kaydet uçlarından user_descriptors'a girer. Statik akış (codegen + QC) değişmez.
import * as React from "react";
import { CheckCircle2, CircleDashed, Loader2, Save, Sparkles, Download } from "lucide-react";
import { api } from "@/lib/api";
import { useStore } from "@/store/useStore";
import type { LlmDescriptorRound } from "@/lib/types";
import { Badge, Button, Input, Label, Textarea } from "@/components/ui";
import UserDescriptorImport from "@/features/driver-import/UserDescriptorImport";

const ROUND_OPTIONS = [1, 2, 3, 4, 5];

export default function AiDescriptorPanel() {
  const llm = useStore((s) => s.llm);
  const [part, setPart] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [hints, setHints] = React.useState("");
  const [rounds, setRounds] = React.useState(3);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [log, setLog] = React.useState<LlmDescriptorRound[]>([]);
  const [accepted, setAccepted] = React.useState<boolean | null>(null);
  const [yamlText, setYamlText] = React.useState("");
  const [checked, setChecked] = React.useState<{ valid: boolean; errors: string[] } | null>(null);
  const [notice, setNotice] = React.useState("");
  const [startedAt, setStartedAt] = React.useState<number | null>(null);
  const [elapsed, setElapsed] = React.useState(0);

  React.useEffect(() => {
    if (!busy || startedAt === null) return;
    const timer = window.setInterval(() => setElapsed(Math.round((Date.now() - startedAt) / 1000)), 500);
    return () => window.clearInterval(timer);
  }, [busy, startedAt]);

  const configured = Boolean(llm.enabled && llm.base_url && llm.model);

  async function generate() {
    setBusy(true);
    setError("");
    setNotice("");
    setChecked(null);
    setLog([]);
    setAccepted(null);
    setStartedAt(Date.now());
    setElapsed(0);
    try {
      const result = await api.llmDescriptor({ part: part.trim(), reference, hints, rounds, llm });
      setLog(result.rounds);
      setAccepted(result.accepted);
      setYamlText(result.yaml);
      if (!result.accepted) {
        setError(`${result.rounds.length} turda doğrulayıcıdan geçmedi; son aday aşağıda, elle düzeltip Doğrula/Kaydet yapabilirsin.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function validate(): Promise<boolean> {
    setNotice("");
    try {
      const result = await api.validateUserDescriptor(yamlText);
      setChecked({ valid: result.valid, errors: result.errors });
      return result.valid;
    } catch (err) {
      setChecked({ valid: false, errors: [err instanceof Error ? err.message : String(err)] });
      return false;
    }
  }

  async function save() {
    if (!(await validate())) return;
    try {
      const result = await api.uploadUserDescriptor(yamlText);
      setNotice(`${result.part} kaydedildi (${result.saved}).${result.overrides_builtin ? " Yerleşik descriptor'ı gölgeliyor." : ""} Şematikte parça seçicide görünür; Generate statik zincirden üretir.`);
      window.dispatchEvent(new CustomEvent("user-descriptors-changed"));
    } catch (err) {
      setChecked({ valid: false, errors: [err instanceof Error ? err.message : String(err)] });
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([yamlText], { type: "text/yaml" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${part.toLowerCase().replace(/[^a-z0-9]/g, "") || "descriptor"}.yaml`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-elev p-4" data-testid="ai-descriptor-panel">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <Sparkles className="h-4 w-4 text-accent" aria-hidden />
          <h3 className="text-sm font-semibold text-text">Referans metninden descriptor</h3>
          <Badge tone={configured ? "accent" : "warn"}>{configured ? llm.model : "endpoint girilmedi (Setup)"}</Badge>
        </div>
        <p className="mb-3 text-xs leading-relaxed text-muted">
          Datasheet'in register tablosunu (adres, ad, reset, bit alanları, SPI/I2C çerçeve tarifi) ya da üreticinin
          sürücü başlığındaki register tanımlarını yapıştır. Model bir YAML adayı yazar; backend adayı descriptor
          doğrulayıcısından geçirir, hata varsa hataları modele geri verip yeniden ister (tur sınırı aşağıda).
          Kabul edilen aday kaydedilmez: burada gözden geçir, gerekirse düzelt, Doğrula ve Kaydet. Üretim, Test Bench ve
          CİT yerleşik entegrelerle aynı statik zincirden çalışır.
        </p>
        <p className="mb-3 rounded border border-warn/30 bg-warn/10 p-2 text-[11px] text-warn">
          Referans metni endpoint'e gönderilir. Bulut sağlayıcıda (DeepSeek, OpenAI...) şirket içi belge paylaşma;
          yerel/şirket içi OpenAI-uyumlu model kullan.
        </p>

        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          <div className="space-y-2">
            <div>
              <Label>Parça adı *</Label>
              <Input value={part} onChange={(e) => setPart(e.target.value)} placeholder="ADXL362" data-testid="ai-part" />
            </div>
            <div>
              <Label>Referans metni *</Label>
              <Textarea
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                placeholder={"0x00 DEVID_AD reset 0xAD R ...\n0x0E XDATA_L ... 12-bit signed, LSB first\nSPI: mode 0, command byte 0x0A write / 0x0B read, then address, then data"}
                className="min-h-56 text-xs"
                data-testid="ai-reference"
              />
            </div>
          </div>
          <div className="space-y-2">
            <div>
              <Label>Ek yönerge (isteğe bağlı)</Label>
              <Textarea
                value={hints}
                onChange={(e) => setHints(e.target.value)}
                placeholder={"Örn: id_read uint32 = DEVID_AD<<16 | DEVID_MST<<8 | PARTID; x/y/z int16 (L,H little); frame_bits 24, fixed_bits 0x0A0000"}
                className="min-h-28 text-xs"
              />
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <Label>Tur sınırı</Label>
                <select
                  value={rounds}
                  onChange={(e) => setRounds(Number(e.target.value))}
                  className="h-9 rounded-md border border-border bg-inset px-2 text-sm text-text"
                >
                  {ROUND_OPTIONS.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <Button onClick={() => void generate()} disabled={busy || !configured || !part.trim() || !reference.trim()} data-testid="ai-generate">
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {busy ? `Üretiliyor… ${elapsed} sn` : "Descriptor üret"}
              </Button>
            </div>
            {log.length > 0 && (
              <table className="w-full text-left text-xs">
                <thead className="text-[10px] uppercase tracking-wide text-faint">
                  <tr><th className="py-1">Tur</th><th>Süre</th><th>Doğrulayıcı</th></tr>
                </thead>
                <tbody>
                  {log.map((r) => (
                    <tr key={r.round} className="border-t border-border">
                      <td className="py-1">{r.round}</td>
                      <td>{r.seconds} sn</td>
                      <td className={r.errors.length ? "text-danger" : "text-ok"}>
                        {r.errors.length ? `${r.errors.length} hata: ${r.errors[0]}` : "geçti"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        {error && <p className="mt-3 rounded border border-danger/30 bg-danger/10 p-2 text-xs text-danger">{error}</p>}

        {yamlText && (
          <div className="mt-3 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              {accepted ? <CheckCircle2 className="h-4 w-4 text-ok" aria-hidden /> : <CircleDashed className="h-4 w-4 text-warn" aria-hidden />}
              <span className="text-xs text-text">{accepted ? "Aday doğrulayıcıdan geçti — gözden geçir ve kaydet." : "Aday (doğrulanmadı) — düzelt ve Doğrula."}</span>
              <span className="ml-auto flex gap-2">
                <Button size="sm" variant="outline" onClick={() => void validate()} data-testid="ai-validate">Doğrula</Button>
                <Button size="sm" variant="outline" onClick={download}><Download className="h-3.5 w-3.5" /> İndir</Button>
                <Button size="sm" onClick={() => void save()} data-testid="ai-save"><Save className="h-3.5 w-3.5" /> Kaydet</Button>
              </span>
            </div>
            <Textarea value={yamlText} onChange={(e) => { setYamlText(e.target.value); setChecked(null); }} className="min-h-72 text-[11px]" data-testid="ai-yaml" />
            {checked && !checked.valid && (
              <pre className="max-h-40 overflow-auto rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] text-danger">{checked.errors.join("\n")}</pre>
            )}
            {checked?.valid && !notice && <p className="text-[11px] text-ok">Doğrulama geçti.</p>}
            {notice && <p className="rounded border border-ok/30 bg-ok/10 p-2 text-[11px] text-ok" data-testid="ai-notice">{notice}</p>}
          </div>
        )}
      </section>

      <UserDescriptorImport />
    </div>
  );
}
