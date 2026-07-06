// Descriptor Sihirbazı: formdan descriptor YAML'ı üretir. Hata sınıflarını
// imkânsızlaştırma ilkesi: register/alan referansları elle yazılmaz, tablodan
// SEÇİLİR; convert formülü örnek ham değerle CANLI önizlenir; YAML sağda
// gerçek zamanlı akar. Kapsam v1: I2C register cihazları — TICS SPI / flash /
// EEPROM arketipleri için Kılavuz 15.0 + örnek şablon kullanılır.
import * as React from "react";
import { Check, Loader2, Plus, Trash2, Wand2, X } from "lucide-react";
import { api } from "@/lib/api";
import { Badge, Button, Input, Label } from "@/components/ui";
import { cn } from "@/lib/utils";

/* ---------- durum modeli ---------- */

interface FieldRow {
  name: string;
  bits: string;
  description: string;
}

interface RegisterRow {
  name: string;
  offset: string;   // "0x00"
  width: 8 | 16;
  access: "ro" | "rw" | "wo";
  reset: string;    // "0x00"
  fields: FieldRow[];
}

type StepOp = "write_register" | "read_register" | "read_registers" | "read_channels" | "poll" | "comment";

interface StepRow {
  op: StepOp;
  reg: string;
  value: string;    // write_register
  length: string;   // read_registers
  count: string;    // read_channels
  field: string;    // poll
  until: "0" | "1"; // poll
  mask: string;     // read_register (ops.)
  shift: string;    // read_register (ops.)
  note: string;     // comment
}

interface ConvertForm {
  enabled: boolean;
  mask: string;
  rshift: string;
  signedBits: string;
  scaleNum: string;
  scaleDen: string;
  offset: string;
  clampMin: string;
  unsigned: boolean;
  unit: string;
}

interface OperationRow {
  name: string;
  returns: "" | "uint8" | "uint16" | "uint32" | "int32" | "uint16[]";
  arrayCount: string; // uint16[] için
  description: string;
  convert: ConvertForm;
  steps: StepRow[];
}

const EMPTY_CONVERT: ConvertForm = {
  enabled: false, mask: "0xFFFF", rshift: "0", signedBits: "0",
  scaleNum: "1", scaleDen: "1", offset: "0", clampMin: "", unsigned: false, unit: "",
};

const NEW_STEP: StepRow = {
  op: "read_register", reg: "", value: "0x00", length: "2", count: "8",
  field: "", until: "1", mask: "", shift: "", note: "",
};

const UNITS = ["", "0.01 C", "0.01 %RH", "mV", "mA", "mW", "uV", "s"];

/* ---------- yardımcılar ---------- */

function parseNum(text: string): number | null {
  const t = text.trim();
  if (!t) return null;
  const value = Number.parseInt(t, t.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(value) ? value : null;
}

function hexOrRaw(text: string): string {
  const value = parseNum(text);
  if (value === null) return text.trim() || "0";
  return `0x${value.toString(16).toUpperCase().padStart(2, "0")}`;
}

function yamlStr(text: string): string {
  return JSON.stringify(text);
}

function moduleOf(part: string): string {
  return part.toLowerCase().replace(/[^a-z0-9]/g, "") || "part";
}

function pascal(name: string): string {
  return name.split(/[^A-Za-z0-9]+/).filter(Boolean)
    .map((p) => p[0].toUpperCase() + p.slice(1)).join("");
}

/** convert önizlemesi — cmodel._emit_convert_lines ile aynı tam sayı matematiği. */
function previewConvert(raw: number, c: ConvertForm): number {
  const mask = parseNum(c.mask) ?? 0xFFFF;
  const rshift = parseNum(c.rshift) ?? 0;
  const signedBits = parseNum(c.signedBits) ?? 0;
  const scaleNum = parseNum(c.scaleNum) ?? 1;
  const scaleDen = parseNum(c.scaleDen) ?? 1;
  const offset = parseNum(c.offset) ?? 0;
  let code = (raw >>> rshift) & mask;
  if (signedBits > 0 && !c.unsigned && code >= 2 ** (signedBits - 1)) code -= 2 ** signedBits;
  code = Math.trunc((code * scaleNum) / scaleDen) + offset;
  const clamp = parseNum(c.clampMin);
  if (c.clampMin.trim() !== "" && clamp !== null && code < clamp) code = clamp;
  return code;
}

function formatPreview(value: number, unit: string): string {
  if (unit === "0.01 C") return `${(value / 100).toFixed(2)} °C`;
  if (unit === "0.01 %RH") return `${(value / 100).toFixed(2)} %RH`;
  if (unit) return `${value} ${unit === "uV" ? "µV" : unit}`;
  return String(value);
}

/* ---------- YAML üretimi ---------- */

function buildYaml(state: {
  part: string; manufacturer: string; summary: string;
  defaultAddress: string; byteOrder: "big" | "little";
  registers: RegisterRow[]; operations: OperationRow[];
  postInitReg: string; selfTest: string;
}): string {
  const lines: string[] = [];
  // Yer tutucu YOK: boş zorunlu alanlar YAML'a boş gider ki doğrulayıcı
  // "geçerli" diyemesin (boş part yeşil rozet üretmişti — UX tuzağı).
  lines.push('descriptor_version: "1.0"');
  lines.push(`part: ${yamlStr(state.part.trim())}`);
  if (state.manufacturer.trim()) lines.push(`manufacturer: ${yamlStr(state.manufacturer.trim())}`);
  lines.push(`summary: ${yamlStr(state.summary.trim() || "...")}`);
  lines.push("transport:");
  lines.push("  type: i2c");
  lines.push("  address_width: 8");
  lines.push(`  default_address: ${hexOrRaw(state.defaultAddress)}`);
  lines.push(`  byte_order: ${state.byteOrder}`);
  lines.push("access_primitives:");
  lines.push("  read_register:  { pattern: write_addr_then_read, width_bytes: 1 }");
  lines.push("  write_register: { pattern: write_addr_then_data, width_bytes: 1 }");
  lines.push("registers:");
  for (const reg of state.registers) {
    lines.push(`  - name: ${reg.name.trim()}`);
    lines.push(`    offset: ${hexOrRaw(reg.offset)}`);
    lines.push(`    width: ${reg.width}`);
    lines.push(`    access: ${reg.access}`);
    if (reg.reset.trim() !== "") lines.push(`    reset: ${hexOrRaw(reg.reset)}`);
    if (reg.fields.length > 0) {
      lines.push("    fields:");
      for (const field of reg.fields) {
        lines.push(`      - name: ${field.name.trim() || "FIELD"}`);
        lines.push(`        bits: "${field.bits.trim() || "0"}"`);
        if (field.description.trim()) lines.push(`        description: ${yamlStr(field.description.trim())}`);
      }
    }
  }
  lines.push("operations:");
  for (const op of state.operations) {
    lines.push(`  - name: ${op.name.trim()}`);
    if (op.returns) {
      const returns = op.returns === "uint16[]" ? `uint16[${parseNum(op.arrayCount) ?? 8}]` : op.returns;
      lines.push(`    returns: "${returns}"`);
    }
    lines.push(`    description: ${yamlStr(op.description.trim() || "...")}`);
    if (op.convert.enabled) {
      const parts = [`mask: ${hexOrRaw(op.convert.mask)}`];
      if ((parseNum(op.convert.rshift) ?? 0) !== 0) parts.push(`rshift: ${parseNum(op.convert.rshift)}`);
      if ((parseNum(op.convert.signedBits) ?? 0) !== 0 && !op.convert.unsigned) {
        parts.push(`signed_bits: ${parseNum(op.convert.signedBits)}`);
      }
      parts.push(`scale_num: ${parseNum(op.convert.scaleNum) ?? 1}`);
      parts.push(`scale_den: ${parseNum(op.convert.scaleDen) ?? 1}`);
      if ((parseNum(op.convert.offset) ?? 0) !== 0) parts.push(`offset: ${parseNum(op.convert.offset)}`);
      if (op.convert.clampMin.trim() !== "") parts.push(`clamp_min: ${parseNum(op.convert.clampMin) ?? 0}`);
      if (op.convert.unsigned) parts.push("unsigned: true");
      if (op.convert.unit) parts.push(`unit: "${op.convert.unit}"`);
      lines.push(`    convert: { ${parts.join(", ")} }`);
    }
    lines.push("    steps:");
    for (const step of op.steps) {
      if (step.op === "comment") {
        lines.push(`      - { op: comment, note: ${yamlStr(step.note || "...")} }`);
      } else if (step.op === "write_register") {
        lines.push(`      - { op: write_register, reg: ${step.reg || "REG"}, value: ${hexOrRaw(step.value)} }`);
      } else if (step.op === "read_register") {
        const extras: string[] = [];
        if (step.mask.trim() !== "") extras.push(`mask: ${hexOrRaw(step.mask)}`);
        if (step.shift.trim() !== "") extras.push(`shift: ${parseNum(step.shift) ?? 0}`);
        lines.push(`      - { op: read_register, reg: ${step.reg || "REG"}${extras.length ? ", " + extras.join(", ") : ""} }`);
      } else if (step.op === "read_registers") {
        lines.push(`      - { op: read_registers, reg: ${step.reg || "REG"}, length: ${parseNum(step.length) ?? 1} }`);
      } else if (step.op === "read_channels") {
        lines.push(`      - { op: read_channels, reg: ${step.reg || "REG"}, count: ${parseNum(step.count) ?? 8} }`);
      } else if (step.op === "poll") {
        lines.push(`      - { op: poll, reg: ${step.reg || "REG"}, field: ${step.field || "FIELD"}, until: ${step.until} }`);
      }
    }
  }
  const hints: string[] = [];
  if (state.postInitReg) hints.push(`  post_init_status: { reg: ${state.postInitReg} }`);
  if (state.selfTest.trim()) hints.push(`  self_test: { description: ${yamlStr(state.selfTest.trim())} }`);
  if (hints.length > 0) {
    lines.push("test_hints:");
    lines.push(...hints);
  }
  return lines.join("\n") + "\n";
}

/* ---------- örnek başlangıç durumu (MYMON16) ---------- */

const EXAMPLE_STATE = {
  part: "MYMON16",
  manufacturer: "Acme",
  summary: "Kurgusal 2 kanalli monitor (sihirbaz ornegi).",
  defaultAddress: "0x4C",
  byteOrder: "big" as const,
  registers: [
    { name: "STATUS", offset: "0x00", width: 8, access: "ro", reset: "0x00",
      fields: [{ name: "T_READY", bits: "1", description: "" }] },
    { name: "CONTROL", offset: "0x01", width: 8, access: "rw", reset: "0x00", fields: [] },
    { name: "T_MSB", offset: "0x06", width: 8, access: "ro", reset: "0x00", fields: [] },
    { name: "T_LSB", offset: "0x07", width: 8, access: "ro", reset: "0x00", fields: [] },
  ] as RegisterRow[],
  operations: [
    { name: "device_init", returns: "" as const, arrayCount: "8",
      description: "Olcumu etkinlestirir.", convert: { ...EMPTY_CONVERT },
      steps: [{ ...NEW_STEP, op: "write_register" as const, reg: "CONTROL", value: "0x10" }] },
    { name: "temperature_read", returns: "int32" as const, arrayCount: "8",
      description: "Sicaklik, 0.01 C (13-bit two's complement).",
      convert: { ...EMPTY_CONVERT, enabled: true, mask: "0x1FFF", signedBits: "13", scaleNum: "625", scaleDen: "100", unit: "0.01 C" },
      steps: [
        { ...NEW_STEP, op: "poll" as const, reg: "STATUS", field: "T_READY", until: "1" as const },
        { ...NEW_STEP, op: "read_register" as const, reg: "T_MSB" },
        { ...NEW_STEP, op: "read_register" as const, reg: "T_LSB" },
      ] },
  ] as OperationRow[],
  postInitReg: "STATUS",
  selfTest: "Sicaklik okunur; yazma yok.",
};

/* ---------- bileşen ---------- */

const inputCls = "h-8 rounded-md border border-border bg-inset px-2 font-mono text-xs text-text";

export default function DescriptorWizard() {
  const [part, setPart] = React.useState("");
  const [manufacturer, setManufacturer] = React.useState("");
  const [summary, setSummary] = React.useState("");
  const [defaultAddress, setDefaultAddress] = React.useState("0x48");
  const [byteOrder, setByteOrder] = React.useState<"big" | "little">("big");
  const [registers, setRegisters] = React.useState<RegisterRow[]>([]);
  const [operations, setOperations] = React.useState<OperationRow[]>([]);
  const [postInitReg, setPostInitReg] = React.useState("");
  const [selfTest, setSelfTest] = React.useState("");
  const [rawSample, setRawSample] = React.useState("0x0F23");
  const [busy, setBusy] = React.useState(false);
  const [checked, setChecked] = React.useState<{ valid: boolean; errors: string[] } | null>(null);
  const [notice, setNotice] = React.useState("");

  const state = { part, manufacturer, summary, defaultAddress, byteOrder, registers, operations, postInitReg, selfTest };
  const yamlText = buildYaml(state);
  const regNames = registers.map((r) => r.name.trim()).filter(Boolean);

  function loadExample() {
    setPart(EXAMPLE_STATE.part);
    setManufacturer(EXAMPLE_STATE.manufacturer);
    setSummary(EXAMPLE_STATE.summary);
    setDefaultAddress(EXAMPLE_STATE.defaultAddress);
    setByteOrder(EXAMPLE_STATE.byteOrder);
    setRegisters(EXAMPLE_STATE.registers.map((r) => ({ ...r, fields: r.fields.map((f) => ({ ...f })) })));
    setOperations(EXAMPLE_STATE.operations.map((o) => ({ ...o, convert: { ...o.convert }, steps: o.steps.map((s) => ({ ...s })) })));
    setPostInitReg(EXAMPLE_STATE.postInitReg);
    setSelfTest(EXAMPLE_STATE.selfTest);
    setChecked(null);
    setNotice("");
  }

  async function validate(): Promise<boolean> {
    setBusy(true);
    setNotice("");
    try {
      const result = await api.validateUserDescriptor(yamlText);
      setChecked({ valid: result.valid, errors: result.errors });
      return result.valid;
    } catch (err) {
      setChecked({ valid: false, errors: [err instanceof Error ? err.message : String(err)] });
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!(await validate())) return;
    setBusy(true);
    try {
      const result = await api.uploadUserDescriptor(yamlText);
      setNotice(`${result.part} kaydedildi (${result.saved}).${result.overrides_builtin ? " Yerleşik descriptor'ı gölgeliyor." : ""}`);
      window.dispatchEvent(new CustomEvent("user-descriptors-changed"));
    } catch (err) {
      setChecked({ valid: false, errors: [err instanceof Error ? err.message : String(err)] });
    } finally {
      setBusy(false);
    }
  }

  function download() {
    const url = URL.createObjectURL(new Blob([yamlText], { type: "text/yaml" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${moduleOf(part)}.yaml`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  /* --- register / operasyon mutasyon yardımcıları --- */
  const patchReg = (i: number, patch: Partial<RegisterRow>) =>
    setRegisters((prev) => prev.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const patchOp = (i: number, patch: Partial<OperationRow>) =>
    setOperations((prev) => prev.map((o, j) => (j === i ? { ...o, ...patch } : o)));
  const patchStep = (oi: number, si: number, patch: Partial<StepRow>) =>
    setOperations((prev) => prev.map((o, j) =>
      j === oi ? { ...o, steps: o.steps.map((s, k) => (k === si ? { ...s, ...patch } : s)) } : o));

  const module = moduleOf(part || "mychip");
  const signatures = operations.filter((o) => o.name.trim()).map((o) => {
    const fn = `${module}${pascal(o.name)}`;
    if (!o.returns) return `int ${fn}(XIicPs* spIic);`;
    if (o.returns === "uint16[]") return `int ${fn}(XIicPs* spIic, unsigned short* uspArrValues);`;
    const ctype = { uint8: "unsigned char", uint16: "unsigned short", uint32: "unsigned int", int32: "int" }[o.returns];
    return `int ${fn}(XIicPs* spIic, ${ctype}* ${o.returns.startsWith("u") ? "up" : "ip"}${pascal(o.name.split("_")[0])});`;
  });

  return (
    <section className="rounded-lg border border-border bg-elev p-4" data-testid="descriptor-wizard">
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <Wand2 className="h-4 w-4 text-accent" aria-hidden />
        <h3 className="text-sm font-semibold text-text">Descriptor Sihirbazı</h3>
        <Badge tone="neutral">v1: I2C register cihazları</Badge>
        <Button size="sm" variant="outline" onClick={loadExample} className="ml-auto" data-testid="wizard-load-example">
          Örnekle doldur
        </Button>
      </div>
      <p className="mb-3 text-xs leading-relaxed text-muted">
        Formu doldur; YAML sağda canlı üretilir, register/alan referansları elle yazılmaz seçilir.
        Değerleri datasheet'ten birebir al. TICS SPI / flash / EEPROM arketipleri için Kılavuz 15.0 +
        örnek şablonu kullan.
      </p>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(320px,420px)]">
        <div className="space-y-4">
          {/* 1 — kimlik */}
          <div className="rounded-md border border-border bg-inset p-3">
            <div className="mb-2 text-xs font-semibold text-text">1 · Kimlik ve transport</div>
            <div className="grid gap-2 md:grid-cols-2">
              <div><Label>Parça adı *</Label><Input value={part} onChange={(e) => setPart(e.target.value)} placeholder="MYCHIP123" data-testid="wizard-part" /></div>
              <div><Label>Üretici</Label><Input value={manufacturer} onChange={(e) => setManufacturer(e.target.value)} /></div>
              <div className="md:col-span-2"><Label>Özet *</Label><Input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Tek cümle özet" /></div>
              <div><Label>Varsayılan I2C adresi</Label><Input value={defaultAddress} onChange={(e) => setDefaultAddress(e.target.value)} placeholder="0x48" /></div>
              <div>
                <Label>Bayt sırası (çok baytlı değerler)</Label>
                <select value={byteOrder} onChange={(e) => setByteOrder(e.target.value as "big" | "little")} className={cn(inputCls, "w-full")}>
                  <option value="big">big (MSB önce)</option>
                  <option value="little">little (LSB önce)</option>
                </select>
              </div>
            </div>
          </div>

          {/* 2 — registers */}
          <div className="rounded-md border border-border bg-inset p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs font-semibold text-text">2 · Register haritası</div>
              <Button size="sm" variant="outline" onClick={() => setRegisters((p) => [...p, { name: "", offset: "0x00", width: 8, access: "rw", reset: "0x00", fields: [] }])} data-testid="wizard-add-register">
                <Plus className="h-3.5 w-3.5" aria-hidden /> Register
              </Button>
            </div>
            {registers.length === 0 ? <p className="text-xs text-faint">Henüz register yok.</p> : null}
            <div className="space-y-2">
              {registers.map((reg, i) => (
                <div key={i} className="rounded border border-border bg-bg p-2">
                  <div className="flex flex-wrap items-end gap-2">
                    <div className="w-40"><Label>Ad</Label><Input value={reg.name} onChange={(e) => patchReg(i, { name: e.target.value.toUpperCase() })} placeholder="STATUS" /></div>
                    <div className="w-20"><Label>Offset</Label><Input value={reg.offset} onChange={(e) => patchReg(i, { offset: e.target.value })} /></div>
                    <div>
                      <Label>Genişlik</Label>
                      <select value={reg.width} onChange={(e) => patchReg(i, { width: Number(e.target.value) as 8 | 16 })} className={inputCls}>
                        <option value={8}>8 bit</option>
                        <option value={16}>16 bit (tek işlemde 2 bayt)</option>
                      </select>
                    </div>
                    <div>
                      <Label>Erişim</Label>
                      <select value={reg.access} onChange={(e) => patchReg(i, { access: e.target.value as RegisterRow["access"] })} className={inputCls}>
                        <option value="ro">ro</option><option value="rw">rw</option><option value="wo">wo</option>
                      </select>
                    </div>
                    <div className="w-20"><Label>Reset</Label><Input value={reg.reset} onChange={(e) => patchReg(i, { reset: e.target.value })} /></div>
                    <button type="button" className="mb-1.5 ml-auto text-danger" title="Sil" onClick={() => setRegisters((p) => p.filter((_, j) => j !== i))}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </div>
                  <div className="mt-2">
                    <div className="mb-1 flex items-center gap-2 text-[11px] text-faint">
                      Bit alanları (poll adımı alan adıyla çalışır)
                      <button type="button" className="text-accent" onClick={() => patchReg(i, { fields: [...reg.fields, { name: "", bits: "0", description: "" }] })}>
                        + alan
                      </button>
                    </div>
                    {reg.fields.map((field, k) => (
                      <div key={k} className="mb-1 flex flex-wrap items-center gap-2">
                        <Input className="w-36" value={field.name} placeholder="READY"
                               onChange={(e) => patchReg(i, { fields: reg.fields.map((f, m) => (m === k ? { ...f, name: e.target.value.toUpperCase() } : f)) })} />
                        <Input className="w-20" value={field.bits} placeholder="7 / 6:5"
                               onChange={(e) => patchReg(i, { fields: reg.fields.map((f, m) => (m === k ? { ...f, bits: e.target.value } : f)) })} />
                        <Input className="min-w-40 flex-1" value={field.description} placeholder="açıklama (ops.)"
                               onChange={(e) => patchReg(i, { fields: reg.fields.map((f, m) => (m === k ? { ...f, description: e.target.value } : f)) })} />
                        <button type="button" className="text-danger" onClick={() => patchReg(i, { fields: reg.fields.filter((_, m) => m !== k) })}>
                          <X className="h-3 w-3" aria-hidden />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 3 — operasyonlar */}
          <div className="rounded-md border border-border bg-inset p-3">
            <div className="mb-2 flex items-center justify-between">
              <div className="text-xs font-semibold text-text">3 · Operasyonlar</div>
              <Button size="sm" variant="outline" onClick={() => setOperations((p) => [...p, { name: "", returns: "", arrayCount: "8", description: "", convert: { ...EMPTY_CONVERT }, steps: [] }])} data-testid="wizard-add-operation">
                <Plus className="h-3.5 w-3.5" aria-hidden /> Operasyon
              </Button>
            </div>
            {operations.length === 0 ? <p className="text-xs text-faint">Henüz operasyon yok. İlk operasyon genelde device_init olur.</p> : null}
            <div className="space-y-3">
              {operations.map((op, oi) => (
                <div key={oi} className="rounded border border-border bg-bg p-2">
                  <div className="flex flex-wrap items-end gap-2">
                    <div className="w-44"><Label>Ad</Label><Input value={op.name} onChange={(e) => patchOp(oi, { name: e.target.value })} placeholder="temperature_read" /></div>
                    <div>
                      <Label>Dönüş</Label>
                      <select value={op.returns} onChange={(e) => patchOp(oi, { returns: e.target.value as OperationRow["returns"] })} className={inputCls}>
                        <option value="">yok (init/komut)</option>
                        <option value="uint8">uint8</option><option value="uint16">uint16</option>
                        <option value="uint32">uint32</option><option value="int32">int32</option>
                        <option value="uint16[]">uint16[N] (kanal dizisi)</option>
                      </select>
                    </div>
                    {op.returns === "uint16[]" ? (
                      <div className="w-16"><Label>N</Label><Input value={op.arrayCount} onChange={(e) => patchOp(oi, { arrayCount: e.target.value })} /></div>
                    ) : null}
                    <div className="min-w-48 flex-1"><Label>Açıklama</Label><Input value={op.description} onChange={(e) => patchOp(oi, { description: e.target.value })} /></div>
                    <button type="button" className="mb-1.5 text-danger" title="Sil" onClick={() => setOperations((p) => p.filter((_, j) => j !== oi))}>
                      <Trash2 className="h-3.5 w-3.5" aria-hidden />
                    </button>
                  </div>

                  {/* adımlar */}
                  <div className="mt-2">
                    <div className="mb-1 flex items-center gap-2 text-[11px] text-faint">
                      Adımlar
                      <button type="button" className="text-accent" onClick={() => patchOp(oi, { steps: [...op.steps, { ...NEW_STEP, reg: regNames[0] ?? "" }] })} data-testid={`wizard-add-step-${oi}`}>
                        + adım
                      </button>
                    </div>
                    {op.steps.map((step, si) => {
                      const fieldOptions = registers.find((r) => r.name.trim() === step.reg)?.fields.map((f) => f.name).filter(Boolean) ?? [];
                      return (
                        <div key={si} className="mb-1 flex flex-wrap items-center gap-2 rounded border border-border/60 p-1.5">
                          <span className="font-mono text-[10px] text-faint">{si + 1}</span>
                          <select value={step.op} onChange={(e) => patchStep(oi, si, { op: e.target.value as StepOp })} className={inputCls}>
                            <option value="write_register">write_register</option>
                            <option value="read_register">read_register</option>
                            <option value="read_registers">read_registers</option>
                            <option value="read_channels">read_channels</option>
                            <option value="poll">poll</option>
                            <option value="comment">comment</option>
                          </select>
                          {step.op !== "comment" ? (
                            <select value={step.reg} onChange={(e) => patchStep(oi, si, { reg: e.target.value, field: "" })} className={inputCls}>
                              <option value="">— register —</option>
                              {regNames.map((n) => <option key={n} value={n}>{n}</option>)}
                            </select>
                          ) : null}
                          {step.op === "write_register" ? <Input className="w-20" value={step.value} onChange={(e) => patchStep(oi, si, { value: e.target.value })} placeholder="0x10" /> : null}
                          {step.op === "read_registers" ? <Input className="w-16" value={step.length} onChange={(e) => patchStep(oi, si, { length: e.target.value })} placeholder="len" /> : null}
                          {step.op === "read_channels" ? <Input className="w-16" value={step.count} onChange={(e) => patchStep(oi, si, { count: e.target.value })} placeholder="N" /> : null}
                          {step.op === "poll" ? (
                            <>
                              <select value={step.field} onChange={(e) => patchStep(oi, si, { field: e.target.value })} className={inputCls}>
                                <option value="">— alan —</option>
                                {fieldOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                              </select>
                              <select value={step.until} onChange={(e) => patchStep(oi, si, { until: e.target.value as "0" | "1" })} className={inputCls}>
                                <option value="1">1 olana dek</option><option value="0">0 olana dek</option>
                              </select>
                            </>
                          ) : null}
                          {step.op === "comment" ? <Input className="min-w-48 flex-1" value={step.note} onChange={(e) => patchStep(oi, si, { note: e.target.value })} placeholder="not" /> : null}
                          <button type="button" className="ml-auto text-danger" onClick={() => patchOp(oi, { steps: op.steps.filter((_, k) => k !== si) })}>
                            <X className="h-3 w-3" aria-hidden />
                          </button>
                        </div>
                      );
                    })}
                  </div>

                  {/* convert */}
                  {op.returns ? (
                    <div className="mt-2 rounded border border-border/60 p-2">
                      <label className="flex items-center gap-1.5 text-[11px] text-muted">
                        <input type="checkbox" checked={op.convert.enabled} onChange={(e) => patchOp(oi, { convert: { ...op.convert, enabled: e.target.checked } })} />
                        convert — mühendislik birimine dönüşüm (yeşil rozet)
                      </label>
                      {op.convert.enabled ? (
                        <div className="mt-2 space-y-2">
                          <div className="flex flex-wrap gap-2">
                            {([["mask", "mask"], ["rshift", "rshift"], ["signedBits", "signed_bits"], ["scaleNum", "scale_num"], ["scaleDen", "scale_den"], ["offset", "offset"], ["clampMin", "clamp_min"]] as const).map(([key, label]) => (
                              <div key={key} className="w-24">
                                <Label>{label}</Label>
                                <Input value={op.convert[key]} onChange={(e) => patchOp(oi, { convert: { ...op.convert, [key]: e.target.value } })} />
                              </div>
                            ))}
                            <div>
                              <Label>unit</Label>
                              <select value={op.convert.unit} onChange={(e) => patchOp(oi, { convert: { ...op.convert, unit: e.target.value } })} className={inputCls}>
                                {UNITS.map((u) => <option key={u} value={u}>{u || "—"}</option>)}
                              </select>
                            </div>
                            <label className="mt-5 flex items-center gap-1 text-[11px] text-muted">
                              <input type="checkbox" checked={op.convert.unsigned} onChange={(e) => patchOp(oi, { convert: { ...op.convert, unsigned: e.target.checked } })} />
                              unsigned
                            </label>
                          </div>
                          <div className="flex flex-wrap items-center gap-2 rounded bg-inset px-2 py-1.5">
                            <span className="text-[11px] text-faint">Canlı önizleme — örnek ham değer:</span>
                            <Input className="w-24" value={rawSample} onChange={(e) => setRawSample(e.target.value)} />
                            <span className="font-mono text-xs font-semibold text-ok" data-testid={`wizard-convert-preview-${oi}`}>
                              = {(() => { const raw = parseNum(rawSample); return raw === null ? "?" : formatPreview(previewConvert(raw, op.convert), op.convert.unit); })()}
                            </span>
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>

          {/* 4 — test hints */}
          <div className="rounded-md border border-border bg-inset p-3">
            <div className="mb-2 text-xs font-semibold text-text">4 · Doğrulama ipuçları</div>
            <div className="grid gap-2 md:grid-cols-2">
              <div>
                <Label>Init sonrası geri okunacak register</Label>
                <select value={postInitReg} onChange={(e) => setPostInitReg(e.target.value)} className={cn(inputCls, "w-full")}>
                  <option value="">— yok —</option>
                  {regNames.map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
              </div>
              <div><Label>Self-test açıklaması</Label><Input value={selfTest} onChange={(e) => setSelfTest(e.target.value)} /></div>
            </div>
          </div>
        </div>

        {/* sağ sütun: canlı YAML + imzalar + eylemler */}
        <div className="space-y-3 self-start xl:sticky xl:top-2">
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => void validate()} disabled={busy} data-testid="wizard-validate">
              {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> : <Check className="h-3.5 w-3.5" aria-hidden />}
              Doğrula
            </Button>
            <Button size="sm" onClick={() => void save()} disabled={busy} data-testid="wizard-save">
              Kaydet (user_descriptors)
            </Button>
            <Button size="sm" variant="outline" onClick={download}>YAML indir</Button>
            {checked ? (
              <Badge tone={checked.valid ? "ok" : "danger"} data-testid="wizard-valid-badge">
                {checked.valid ? "geçerli" : `${checked.errors.length} hata`}
              </Badge>
            ) : null}
          </div>
          {checked && !checked.valid ? (
            <pre className="max-h-40 overflow-auto whitespace-pre-wrap rounded border border-danger/30 bg-danger/10 p-2 font-mono text-[11px] leading-relaxed text-danger">
              {checked.errors.join("\n")}
            </pre>
          ) : null}
          {notice ? <p className="rounded border border-ok/30 bg-ok/10 p-2 text-[11px] text-ok" data-testid="wizard-notice">{notice}</p> : null}
          <div>
            <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-faint">Canlı YAML</div>
            <pre className="max-h-[420px] overflow-auto rounded-md border border-border border-l-2 border-l-accent bg-bg px-3 py-2 font-mono text-[11px] leading-relaxed text-text" data-testid="wizard-yaml">
              {yamlText}
            </pre>
          </div>
          {signatures.length > 0 ? (
            <div>
              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-faint">Üretilecek C imzaları (yaklaşık)</div>
              <pre className="overflow-auto rounded-md border border-border bg-bg px-3 py-2 font-mono text-[11px] leading-relaxed text-muted">
                {signatures.join("\n")}
              </pre>
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
