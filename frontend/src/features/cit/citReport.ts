/**
 * CIT raporu (HTML): son okunan CIT kosusunu bring-up "birth certificate" ile ayni ruhta,
 * kendi kendine yeten (air-gap guvenli, yazdirilabilir) tek dosya olarak uretir.
 *
 * Icerik: genel karar (GECTI / NOK / HATA), ozet sayilari, her entegre kendi cerceveli
 * kutusunda (parca, kimlik, adres/CS, switch, SANAL), her olcum satiri: ad, deger + birim,
 * canli limit (ekran biriminde), kartin karari (OK yesil / NOK kirmizi / HATA sari /
 * limitsiz gri-yesil). Degerler ve karar KARTTAN gelir (cit/ katmani); ekran yorum katmaz.
 */
import type { CitDecodeMeasurement, CitDecodeResult, TestbenchManifestDevice } from "@/lib/types";

export interface CitReportRow {
  m: CitDecodeMeasurement;
  eff: { name: string; min: number | null; max: number | null; enabled: boolean; pending: boolean; readOk: boolean; ok: boolean };
}

export interface CitReportGroup {
  id: string;
  manifestDevice: TestbenchManifestDevice | undefined;
  rows: CitReportRow[];
}

export interface CitReportSection {
  boardName: string;
  groups: CitReportGroup[];
}

export interface CitReportInput {
  projectName: string;
  appVersion: string;
  result: CitDecodeResult;
  ranAt: number | null;
  sections: CitReportSection[];
  boardsDeclared: boolean;
  transport?: string;
  formatValue: (value: number, unit: string | null) => { text: string; unit: string };
  limitText: (eff: { min: number | null; max: number | null }, unit: string | null) => string;
  statusLabel: (durum: number) => string;
}

function esc(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function stamp(atMs: number | null): string {
  const d = atMs ? new Date(atMs) : new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

type Verdict = "ok" | "nok" | "err" | "off";

function rowVerdict(row: CitReportRow): Verdict {
  if (row.eff.pending) return "off";
  if (row.m.durum !== 0) return "err";
  if (!row.eff.enabled) return "off";
  return row.eff.ok ? "ok" : "nok";
}

const VERDICT_LABEL: Record<Verdict, string> = { ok: "OK", nok: "NOK", err: "HATA", off: "OK" };

function groupVerdict(rows: CitReportRow[]): Verdict {
  const v = rows.map(rowVerdict);
  if (v.includes("err")) return "err";
  if (v.includes("nok")) return "nok";
  return "ok";
}

export function citReportFileName(projectName: string, result: CitDecodeResult, ranAt: number | null): string {
  const safe = (projectName || "kart").replace(/[^A-Za-z0-9_]+/g, "_");
  const d = ranAt ? new Date(ranAt) : new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `cit_raporu_${safe}_${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}_${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}_kosu${result.sayac}.html`;
}

export function renderCitReportHtml(input: CitReportInput): string {
  const allRows = input.sections.flatMap((s) => s.groups.flatMap((g) => g.rows));
  const counts = { ok: 0, nok: 0, err: 0, off: 0 };
  for (const row of allRows) counts[rowVerdict(row)]++;
  const deviceCount = input.sections.reduce((n, s) => n + s.groups.length, 0);
  const overall: Verdict = counts.err > 0 ? "err" : counts.nok > 0 ? "nok" : "ok";
  const overallText = overall === "ok" ? "GEÇTİ" : overall === "nok" ? "LİMİT DIŞI (NOK)" : "OKUMA HATASI";
  const overallClass = overall;

  const problemRows = allRows.filter((r) => rowVerdict(r) === "nok" || rowVerdict(r) === "err");
  const problems = problemRows.length
    ? `<section class="problems">
      <h2>Dikkat gerektirenler (${problemRows.length})</h2>
      <ul>${problemRows
        .map((r) => {
          const v = rowVerdict(r);
          const shown = input.formatValue(r.m.value, r.m.unit);
          const detail = v === "err" ? input.statusLabel(r.m.durum) : `${shown.text} ${shown.unit} · limit ${input.limitText(r.eff, r.m.unit)}`;
          return `<li><span class="pill ${v}">${VERDICT_LABEL[v]}</span> <b class="mono">${esc(r.m.device)}</b> · ${esc(r.eff.name)} — <span class="mono">${esc(detail)}</span></li>`;
        })
        .join("")}</ul>
    </section>`
    : `<section class="problems clean"><h2>Tüm ölçümler limit içinde, okuma hatası yok.</h2></section>`;

  const cards = input.sections
    .map((section) => {
      const heading = input.boardsDeclared ? `<h2 class="board">${esc(section.boardName)}</h2>` : "";
      const groupHtml = section.groups
        .map((group) => {
          const md = group.manifestDevice;
          const part = group.rows[0]?.m.part ?? md?.part ?? group.id;
          const attach = md?.attach;
          const addr = attach?.i2c_address
            ? `${attach.i2c_address}`
            : attach?.spi_chip_select !== undefined && attach?.spi_chip_select !== null
              ? `CS${attach.spi_chip_select}`
              : "";
          const mux = attach?.via_mux ? ` · ${attach.via_mux.mux_id} ch${attach.via_mux.channel}` : "";
          const gv = groupVerdict(group.rows);
          const okCount = group.rows.filter((r) => rowVerdict(r) === "ok" || rowVerdict(r) === "off").length;
          const rowsHtml = group.rows
            .map((r) => {
              const v = rowVerdict(r);
              const shown = r.eff.pending ? { text: "—", unit: "" } : input.formatValue(r.m.value, r.m.unit);
              const limit = r.eff.enabled ? input.limitText(r.eff, r.m.unit) : "limitsiz";
              const status = v === "err" ? `HATA · ${input.statusLabel(r.m.durum)}` : VERDICT_LABEL[v];
              // Varsayilan kanal adi (<KIMLIK>_V<k>) tekrar yazilmaz: kutu basligi kimligi zaten gosterir.
              const isDefaultName = r.m.channel_label !== undefined && new RegExp(`_${r.m.channel_label}$`, "i").test(r.eff.name) && r.eff.name.toUpperCase().startsWith(r.m.device.toUpperCase());
              const label = r.m.channel_label ? `<span class="ch">${esc(r.m.channel_label)}</span>` : "";
              const nameHtml = isDefaultName ? "" : ` ${esc(r.eff.name)}`;
              return `<tr class="${v}">
                <td class="name">${label}${nameHtml}</td>
                <td class="mono num">${esc(shown.text)}${shown.unit ? ` <span class="unit">${esc(shown.unit)}</span>` : ""}</td>
                <td class="mono">${esc(limit)}</td>
                <td class="status"><span class="pill ${v}">${esc(status)}</span></td>
              </tr>`;
            })
            .join("");
          return `<article class="card ${gv}">
            <header>
              <div>
                <span class="part">${esc(part)}</span>
                <span class="mono id">${esc(group.id)}</span>
                ${addr ? `<span class="mono meta">${esc(addr)}${esc(mux)}</span>` : ""}
                ${md?.transport ? `<span class="meta">${esc(String(md.transport).toUpperCase())}</span>` : ""}
                ${md?.simulated ? `<span class="tag">SANAL</span>` : ""}
              </div>
              <span class="pill ${gv}">${gv === "ok" ? `${okCount}/${group.rows.length} OK` : VERDICT_LABEL[gv]}</span>
            </header>
            <table>
              <thead><tr><th>Ölçüm</th><th>Değer</th><th>Limit</th><th>Karar</th></tr></thead>
              <tbody>${rowsHtml}</tbody>
            </table>
          </article>`;
        })
        .join("");
      return `${heading}<div class="grid">${groupHtml}</div>`;
    })
    .join("");

  return `<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CİT Raporu — ${esc(input.projectName)} — koşu #${input.result.sayac}</title>
<style>
  :root { --ok: #1d8348; --nok: #b03a2e; --err: #b9770e; --off: #7b8a8b; --ink: #1c2833; --muted: #566573; --line: #d5dbdb; --paper: #fbfcfc; }
  * { box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 36px 28px; max-width: 1080px; margin-inline: auto; color: var(--ink); background: white; }
  h1 { font-size: 24px; margin: 0 0 2px; letter-spacing: 0.01em; }
  h2 { font-size: 14px; margin: 26px 0 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }
  h2.board { border-bottom: 2px solid var(--line); padding-bottom: 6px; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 18px; }
  .verdict { display: inline-flex; align-items: center; gap: 10px; padding: 8px 18px; border-radius: 8px; color: white; font-weight: 800; letter-spacing: 0.08em; font-size: 15px; }
  .verdict.ok { background: var(--ok); } .verdict.nok { background: var(--nok); } .verdict.err { background: var(--err); }
  .meta-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 18px 0 8px; }
  .meta-grid div { border: 1px solid var(--line); border-radius: 8px; padding: 9px 12px; background: var(--paper); }
  .meta-grid b { display: block; font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 2px; }
  .meta-grid span { font-size: 15px; font-family: Consolas, 'Cascadia Mono', monospace; }
  .meta-grid span.ok { color: var(--ok); } .meta-grid span.nok { color: var(--nok); } .meta-grid span.err { color: var(--err); }
  .problems { border: 1px solid var(--line); border-left: 5px solid var(--nok); border-radius: 8px; padding: 10px 14px; margin-top: 16px; background: #fdf2f0; }
  .problems.clean { border-left-color: var(--ok); background: #eefaf1; }
  .problems h2 { margin: 0 0 6px; color: var(--ink); text-transform: none; letter-spacing: 0; font-size: 13px; }
  .problems ul { margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.7; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(460px, 1fr)); gap: 14px; }
  @media (max-width: 520px) { .grid { grid-template-columns: 1fr; } }
  .card { border: 1px solid var(--line); border-left: 5px solid var(--ok); border-radius: 10px; overflow: hidden; background: white; break-inside: avoid; }
  .card.nok { border-left-color: var(--nok); } .card.err { border-left-color: var(--err); }
  .card header { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 9px 12px; background: var(--paper); border-bottom: 1px solid var(--line); }
  .card header > div { display: flex; flex-wrap: wrap; align-items: baseline; gap: 8px; }
  .part { font-weight: 800; font-size: 14px; } .id { color: var(--muted); font-size: 12px; } .meta { color: var(--muted); font-size: 11px; }
  .tag { font-size: 10px; border: 1px solid var(--err); color: var(--err); border-radius: 4px; padding: 0 5px; letter-spacing: 0.06em; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th, td { padding: 6px 12px; text-align: left; border-bottom: 1px solid #eef0f0; vertical-align: top; }
  td.name { min-width: 130px; overflow-wrap: break-word; } td.mono:not(.num) { white-space: nowrap; }
  th { font-size: 10px; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); background: white; }
  tr:last-child td { border-bottom: 0; }
  tr.nok td { background: #fdf2f0; } tr.err td { background: #fef6e7; } tr.off td { color: var(--muted); }
  .num { font-weight: 700; font-size: 14px; white-space: nowrap; } .unit { font-weight: 400; font-size: 11px; color: var(--muted); }
  .ch { display: inline-block; min-width: 26px; font-family: Consolas, monospace; font-size: 11px; color: var(--muted); }
  .mono { font-family: Consolas, 'Cascadia Mono', monospace; }
  .status { white-space: nowrap; }
  .pill { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 800; letter-spacing: 0.05em; color: white; }
  .pill.ok { background: var(--ok); } .pill.nok { background: var(--nok); } .pill.err { background: var(--err); } .pill.off { background: #aab7b8; }
  footer { margin-top: 28px; font-size: 11px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 10px; }
  @media print { body { padding: 8mm; } .grid { grid-template-columns: repeat(2, 1fr); } .card { box-shadow: none; } }
</style>
</head>
<body>
  <h1>CİT Raporu — ${esc(input.projectName)}</h1>
  <div class="sub">Cihaz İçi Test: kartın kendi <span class="mono">sistemCitRead()</span> kararı, koşu #${input.result.sayac} · ${esc(stamp(input.ranAt))}</div>
  <span class="verdict ${overallClass}">${overallText}</span>
  <div class="meta-grid">
    <div><b>Proje</b><span>${esc(input.projectName)}</span></div>
    <div><b>Tarih</b><span>${esc(stamp(input.ranAt))}</span></div>
    <div><b>Koşu</b><span>#${input.result.sayac}</span></div>
    <div><b>Entegre</b><span>${deviceCount}</span></div>
    <div><b>Ölçüm</b><span>${allRows.length}</span></div>
    <div><b>Limit içi (OK)</b><span class="ok">${counts.ok + counts.off}</span></div>
    <div><b>Limit dışı (NOK)</b><span class="${counts.nok ? "nok" : ""}">${counts.nok}</span></div>
    <div><b>Okuma hatası</b><span class="${counts.err ? "err" : ""}">${counts.err}</span></div>
    ${input.transport ? `<div><b>Bağlantı</b><span>${esc(input.transport)}</span></div>` : ""}
  </div>
  ${problems}
  ${cards}
  <footer>Spec2Code ${esc(input.appVersion)} tarafından üretildi • değerler ve OK/NOK kararı karttaki cit/ katmanından (CIT_READ) • limitler ekranda gördüğün birimde, "limitsiz" = yalnız okuma • ${counts.off ? `${counts.off} ölçüm limitsiz` : "tüm ölçümlerde limit uygulandı"}</footer>
</body>
</html>
`;
}
