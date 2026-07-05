/** Dönüştürülmüş operasyon sonuçlarını insan-okur hale getirir.
 *
 * Ajan, mühendislik birimli sonuçları value alanında tamsayı olarak taşır
 * (santi-°C, mV, mA...); UI bunu ondalık + birimle gösterir: 0xF23 → 38.75 °C.
 * Birim bilgisi manifest'teki result_returns/result_unit alanlarından gelir.
 */

interface ResultMetaSource {
  result_returns?: string;
  result_unit?: string;
}

function toSigned32(value: number): number {
  return value > 0x7fffffff ? value - 0x100000000 : value;
}

function parseHexish(text: string | undefined): number | null {
  if (!text) return null;
  const parsed = Number.parseInt(text, text.toLowerCase().startsWith("0x") ? 16 : 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function unitSuffix(unit: string): string {
  return unit === "uV" ? "µV" : unit;
}

function formatScalar(value: number, unit: string): string | null {
  if (unit === "0.01 C") return `${(value / 100).toFixed(2)} °C`;
  if (unit === "0.01 %RH") return `${(value / 100).toFixed(2)} %RH`;
  if (["mV", "mA", "mW", "uV", "s"].includes(unit)) return `${value} ${unitSuffix(unit)}`;
  return null;
}

/** data alanındaki big-endian u16 çiftlerini sayıya çevirir. */
export function u16ValuesFromDataHex(dataHex: string): number[] {
  const clean = (dataHex || "").replace(/[^0-9a-fA-F]/g, "");
  const values: number[] = [];
  for (let i = 0; i + 4 <= clean.length; i += 4) {
    values.push(Number.parseInt(clean.slice(i, i + 4), 16));
  }
  return values;
}

/** Başarılı bir yanıt için "38.75 °C" / "3312 mV" biçimli metin; birimsiz
 * (raw) operasyonlarda null döner ve mevcut hex gösterimi yeterli kalır. */
export function formatConvertedValue(
  op: ResultMetaSource | null | undefined,
  parsed: Record<string, string>,
): string | null {
  if (!op || parsed.ok !== "1") return null;
  const returns = (op.result_returns ?? "").toLowerCase();
  const unit = op.result_unit ?? "";
  if (!returns) return null;

  const arrayMatch = /\[(\d+)\]/.exec(returns);
  if (arrayMatch) {
    if (!unit) return null; // raw kanal kodları (ör. LTC2991 current) hex kalır
    const values = u16ValuesFromDataHex(parsed.data ?? "");
    if (values.length === 0) return null;
    return `${values.join(", ")} ${unitSuffix(unit)}`;
  }

  const raw = parseHexish(parsed.value);
  if (raw === null) return null;
  const value = returns.includes("int32") && !returns.includes("uint32") ? toSigned32(raw) : raw;
  const formatted = formatScalar(value, unit);
  if (formatted) return formatted;
  // Birimsiz sayısal dönüşler (status/id gibi) için ondalık karşılık yeterli.
  if (["uint8", "uint16", "uint32", "int32"].includes(returns)) return `${value}`;
  return null;
}
