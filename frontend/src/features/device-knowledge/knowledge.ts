import { getTiClockBitfields } from "./tiClockBitfields";

export interface KnowledgeSource {
  label: string;
  url: string;
}

export interface KnowledgeRegisterField {
  bits: string;
  name: string;
  meaning: string;
  values?: string[];
}

export interface KnowledgeRegister {
  name: string;
  address: string;
  width: string;
  access: string;
  reset?: string;
  purpose: string;
  fields?: KnowledgeRegisterField[];
}

export type KnowledgeTransferTone = "neutral" | "warn" | "danger";

export interface KnowledgeRegisterTransfer {
  title: string;
  access: string;
  txBytes: string;
  rxBytes: string;
  tx: string[];
  rx: string[];
  code: string[];
  note?: string;
  tone?: KnowledgeTransferTone;
}

export interface KnowledgeRecipe {
  title: string;
  goal: string;
  steps: string[];
}

export type KnowledgePinTone =
  | "analog"
  | "bus"
  | "control"
  | "power"
  | "ground"
  | "memory"
  | "nc";

export interface KnowledgePin {
  number?: string;
  name: string;
  role: string;
  tone: KnowledgePinTone;
  side?: "left" | "right";
}

export interface KnowledgePinGroup {
  label: string;
  pins: string[];
  tone: KnowledgePinTone;
  description: string;
}

export interface KnowledgePinMap {
  packageName: string;
  view: string;
  verification: string;
  note: string;
  pins: KnowledgePin[];
  groups: KnowledgePinGroup[];
}

export interface DeviceKnowledgePack {
  part: string;
  reviewedAt: string;
  scope: string;
  sources: KnowledgeSource[];
  overview: string;
  keyFacts: string[];
  configuration: string[];
  registers: KnowledgeRegister[];
  recipes: KnowledgeRecipe[];
  gotchas: string[];
  codegenNotes: string[];
  pinMap?: KnowledgePinMap;
}

const flashStatusFields: KnowledgeRegisterField[] = [
  {
    bits: "B7",
    name: "SRWD",
    meaning: "Status register write-protect biti; WP# kullanımıyla birlikte protection/config yazımlarını kilitlemek için kullanılır.",
    values: ["0: status register yazımı enable", "1: WP# low iken status register nonvolatile bitleri read-only"],
  },
  {
    bits: "B6",
    name: "BP3",
    meaning: "Block protect alanının üst biti; BP[3:0] ve TB ile protected alanın boyutunu belirler.",
    values: ["0: BP[3:0] koduna 0 katkısı", "1: BP[3:0] koduna 1 katkısı"],
  },
  {
    bits: "B5",
    name: "TB",
    meaning: "Protected alanın flash adres uzayının üstünden mi altından mı başladığını seçer.",
    values: ["0: protection alanı top tarafından başlar", "1: protection alanı bottom tarafından başlar"],
  },
  {
    bits: "B4:B2",
    name: "BP[2:0]",
    meaning: "Block protect kodunun alt bitleri; hangi sector/block aralığının write-protected olduğunu belirler.",
    values: [
      "000: BP3=0 iken protected alan yok",
      "001..111: BP3 ve TB ile birlikte protected sector aralığını seçer",
    ],
  },
  {
    bits: "B1",
    name: "WEL",
    meaning: "Write Enable Latch; 1 ise program/erase/write-status operasyonu kabul edilebilir.",
    values: ["0: write-enable latch kapalı", "1: write-enable latch açık"],
  },
  {
    bits: "B0",
    name: "WIP",
    meaning: "Write In Progress; program, erase veya status-write sürerken 1 olur.",
    values: ["0: cihaz hazır", "1: operasyon devam ediyor"],
  },
];

const flashReadIdFields: KnowledgeRegisterField[] = [
  { bits: "Opcode", name: "0x9F", meaning: "JEDEC ID read komutu." },
  { bits: "Response byte 0", name: "Manufacturer ID", meaning: "Üretici kimliği." },
  { bits: "Response byte 1..2", name: "Device ID", meaning: "Memory type ve capacity bilgisini taşıyan device ID byte'ları." },
];

const oldNewDataValues = ["0: register datası eski / yeni conversion yok", "1: register yeni conversion datası içerir"];
const disabledEnabledValues = ["0: disabled / varsayılan kapalı", "1: enabled"];
const filterValues = ["0: filter disabled / varsayılan", "1: filter enabled"];
const celsiusKelvinValues = ["0: Celsius / varsayılan", "1: Kelvin"];
const voltageTemperatureValues = ["0: voltage mode / varsayılan", "1: temperature mode"];
const singleEndedDifferentialValues = [
  "0: single-ended voltage / varsayılan",
  "1: differential pair; çiftin ilk pini single-ended olarak da okunur",
];
const signValues = ["0: pozitif veya non-negative code", "1: negatif code"];
const unusedValues = ["x: kullanılmaz; conversion hesabına dahil edilmez"];

function cModule(part: string) {
  const mod = part.toLowerCase().replace(/[^a-z0-9]/g, "");
  return mod && !/^[a-z]/.test(mod) ? `dev${mod}` : mod;
}

function cPrefix(part: string) {
  return part.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

function pascalSuffix(name: string) {
  return name
    .split("_")
    .filter(Boolean)
    .map((part) => part.slice(0, 1).toUpperCase() + part.slice(1).toLowerCase())
    .join("");
}

function cFunc(part: string, action: string) {
  return `${cModule(part)}${pascalSuffix(action)}`;
}

function regMacro(part: string, reg: string) {
  return `${cPrefix(part)}_REG_${reg}`;
}

function cmdMacro(part: string, cmd: string) {
  return `${cPrefix(part)}_CMD_${cmd}`;
}

function readonlyTransfer(
  part: string,
  reg: string,
  address: string,
  rxBytes: string,
  rx: string[],
  code: string[],
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return {
    title: options.title ?? "Read",
    access: "READ",
    txBytes: "1 byte",
    rxBytes,
    tx: [`${regMacro(part, reg)} (${address})`],
    rx,
    code,
    note: options.note,
    tone: options.tone,
  };
}

function writeonlyTransfer(
  part: string,
  reg: string,
  address: string,
  value: string,
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return {
    title: options.title ?? "Write",
    access: "WRITE",
    txBytes: "2 byte",
    rxBytes: "0 byte",
    tx: [`${regMacro(part, reg)} (${address})`, value],
    rx: ["-"],
    code: options.code ?? [`${cFunc(part, "register_write")}(spIic, ${regMacro(part, reg)}, ${value});`],
    note: options.note,
    tone: options.tone,
  };
}

function i2cRegisterTransfers(
  part: string,
  reg: string,
  address: string,
  access: string,
  valueName = "ucValue",
): KnowledgeRegisterTransfer[] {
  const normalized = access.toUpperCase();
  const transfers: KnowledgeRegisterTransfer[] = [];

  if (normalized.includes("R")) {
    transfers.push(
      readonlyTransfer(part, reg, address, "1 byte", [valueName], [
        `${cFunc(part, "register_read")}(spIic, ${regMacro(part, reg)}, &${valueName});`,
      ], {
        title: normalized === "COR" ? "Read + clear" : "Read",
        note: normalized === "COR" ? "Okuma sonrası latched clear davranışı vardır." : undefined,
      }),
    );
  }

  if (normalized.includes("W")) {
    transfers.push(writeonlyTransfer(part, reg, address, valueName));
  }

  return transfers;
}

function i2cBlockReadTransfer(
  part: string,
  reg: string,
  address: string,
  length: number,
  bufferName: string,
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return readonlyTransfer(part, reg, address, `${length} byte`, [`${bufferName}[0..${length - 1}]`], [
    `${cFunc(part, "registers_read")}(spIic, ${regMacro(part, reg)}, ${bufferName}, ${length}U);`,
  ], options);
}

function i2cGroupedWriteTransfer(
  part: string,
  reg: string,
  address: string,
  length: number,
  bufferName: string,
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return {
    title: options.title ?? "Write bytes",
    access: "WRITE",
    txBytes: `${length * 2} byte toplam (${length} x register+data)`,
    rxBytes: "0 byte",
    tx: [`${regMacro(part, reg)} (${address}) + uiIndex`, `${bufferName}[uiIndex]`],
    rx: ["-"],
    code: options.code ?? [
      `for (uiIndex = 0U; uiIndex < ${length}U; uiIndex++)`,
      `{`,
      `    ${cFunc(part, "register_write")}(spIic, (unsigned char)(${regMacro(part, reg)} + uiIndex), ${bufferName}[uiIndex]);`,
      `}`,
    ],
    note: options.note,
    tone: options.tone,
  };
}

function flashReadTransfer(
  part: string,
  cmd: string,
  opcode: string,
  addressBytes: number,
  rxBytes: string,
  rx: string[],
  code: string[],
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return {
    title: options.title ?? "Read",
    access: "READ",
    txBytes: options.txBytes ?? `${1 + addressBytes} byte${addressBytes > 0 ? " + read clock" : ""}`,
    rxBytes: options.rxBytes ?? rxBytes,
    tx: [`${cmdMacro(part, cmd)} (${opcode})`, ...(addressBytes > 0 ? [`A${addressBytes * 8 - 1}:A0`] : [])],
    rx,
    code,
    note: options.note,
    tone: options.tone,
  };
}

function flashWriteTransfer(
  part: string,
  cmd: string,
  opcode: string,
  addressBytes: number,
  txPayload: string,
  code: string[],
  options: Partial<KnowledgeRegisterTransfer> = {},
): KnowledgeRegisterTransfer {
  return {
    title: options.title ?? "Write",
    access: "WRITE",
    txBytes: options.txBytes ?? `${1 + addressBytes} byte${txPayload ? " + payload" : ""}`,
    rxBytes: options.rxBytes ?? "0 byte",
    tx: [`${cmdMacro(part, cmd)} (${opcode})`, ...(addressBytes > 0 ? [`A${addressBytes * 8 - 1}:A0`] : []), ...(txPayload ? [txPayload] : [])],
    rx: ["-"],
    code,
    note: options.note,
    tone: options.tone,
  };
}

function genericFlashTransfers(
  part: string,
  reg: KnowledgeRegister,
  handle: string,
  defaultAddressBytes: number,
): KnowledgeRegisterTransfer[] {
  const row = mt25qCommandRows.find((item) => item.name === reg.name);
  const opcode = row?.opcode.split("/")[0].trim() ?? reg.address.split("/")[0].trim();
  const addressBytes =
    row?.addressBytes === "4" ? 4 :
    row?.addressBytes === "3" ? 3 :
    row?.addressBytes === "3/4" ? defaultAddressBytes :
    0;
  const dataBytes = row?.dataBytes ?? "0";
  const access = reg.access.toUpperCase();
  const transfers: KnowledgeRegisterTransfer[] = [];

  if (access.includes("R")) {
    transfers.push(
      flashReadTransfer(part, reg.name, opcode, addressBytes, dataBytes === "0" ? "0 byte" : dataBytes, ["ucArrData[0..uiLength-1]"], [
        `${cFunc(part, "command_read")}(${handle}, ${cmdMacro(part, reg.name)}, uiAddress, ${addressBytes}U, ucArrData, uiLength);`,
      ], {
        txBytes: addressBytes > 0 ? `${1 + addressBytes} byte` : "1 byte",
        note: row?.dummyCycles && row.dummyCycles !== "0"
          ? `${row.dummyCycles} dummy cycle gerektirir; controller transfer helper'i bunu explicit clocklamalidir.`
          : undefined,
      }),
    );
  }

  if (access.includes("W")) {
    const payload = dataBytes === "0" ? "" : "ucArrPayload[0..uiLength-1]";
    transfers.push(
      flashWriteTransfer(part, reg.name, opcode, addressBytes, payload, [
        dataBytes === "0"
          ? `${cFunc(part, "command_send")}(${handle}, ${cmdMacro(part, reg.name)});`
          : `${cFunc(part, "command_write")}(${handle}, ${cmdMacro(part, reg.name)}, uiAddress, ${addressBytes}U, ucArrPayload, uiLength);`,
      ], {
        txBytes: `${1 + addressBytes} byte${payload ? " + payload" : ""}`,
        note: ["PAGE_PROGRAM", "ERASE", "CONFIG", "STATUS", "LOCK", "PASSWORD"].some((token) => reg.name.includes(token))
          ? "Bu komut oncesinde WRITE_ENABLE ve sonrasinda status/flag polling gerekebilir."
          : undefined,
        tone: reg.name.includes("ERASE") || reg.name.includes("PASSWORD") || reg.name.includes("LOCK") ? "warn" : undefined,
      }),
    );
  }

  return transfers;
}

const ltc2945LimitFields = (kind: "enable" | "status" | "fault" | "clear"): KnowledgeRegisterField[] => {
  const verb =
    kind === "enable"
      ? "Bu koşul için ALERT üretimini enable eder."
      : kind === "clear"
        ? "Karşılık gelen latched fault durumunun clear/read yolunu temsil eder."
        : kind === "fault"
          ? "Bu limit koşulunun latched fault olarak görüldüğünü gösterir."
          : "Bu limit koşulunun o anda aktif olduğunu gösterir.";
  const values =
    kind === "enable"
      ? ["0: alert disabled", "1: alert enabled"]
      : kind === "status"
        ? ["0: koşul aktif değil", "1: koşul aktif"]
        : kind === "clear"
          ? ["0: latched fault yok", "1: latched fault vardı; CoR read sonrası clear edilir"]
          : ["0: latched fault yok", "1: latched fault oluştu"];

  return [
    { bits: "B7", name: "Max POWER", meaning: verb, values },
    { bits: "B6", name: "Min POWER", meaning: verb, values },
    { bits: "B5", name: "Max SENSE", meaning: verb, values },
    { bits: "B4", name: "Min SENSE", meaning: verb, values },
    { bits: "B3", name: "Max VIN", meaning: verb, values },
    { bits: "B2", name: "Min VIN", meaning: verb, values },
    { bits: "B1", name: "Max ADIN", meaning: verb, values },
    { bits: "B0", name: "Min ADIN", meaning: verb, values },
  ];
};

function byteFields(label: string): KnowledgeRegisterField[] {
  return [
    {
      bits: "B7:B0",
      name: label,
      meaning: `${label} alaninin bu register icindeki 8-bit parcasidir.`,
    },
  ];
}

function reservedFields(note = "Datasheet tarafinda reserved olarak ayrilmistir; yazarken reset/default deger korunmalidir."): KnowledgeRegisterField[] {
  return [{ bits: "B7:B0", name: "Reserved", meaning: note }];
}

function ltc2991ExternalMsbFields(): KnowledgeRegisterField[] {
  return [
    { bits: "B7", name: "Data valid", meaning: "Ilgili channel sonucunda yeni conversion datasinin hazir oldugunu gosterir.", values: oldNewDataValues },
    { bits: "B6", name: "Sign", meaning: "Signed voltage/current formatinda isaret bitidir.", values: signValues },
    { bits: "B5:B0", name: "D13:D8 / D12:D8", meaning: "Voltage/current icin 14-bit, temperature/diode-voltage icin 13-bit raw code ust bitleridir." },
  ];
}

function ltc2991ExternalLsbFields(): KnowledgeRegisterField[] {
  return [
    { bits: "B7:B0", name: "D7:D0", meaning: "External input raw conversion sonucunun alt 8 bitidir." },
  ];
}

function ltc2991TemperatureMsbFields(label: string): KnowledgeRegisterField[] {
  return [
    { bits: "B7", name: "Data valid", meaning: `${label} sonucunda yeni conversion datasinin hazir oldugunu gosterir.`, values: oldNewDataValues },
    { bits: "B6:B5", name: "Unused", meaning: "13-bit temperature formatinda kullanilmaz.", values: unusedValues },
    { bits: "B4:B0", name: "D12:D8", meaning: `${label} raw conversion code ust bitleridir.` },
  ];
}

function ltc2991Registers(): KnowledgeRegister[] {
  const externalRows: KnowledgeRegister[] = [];
  for (let channel = 1; channel <= 8; channel++) {
    const base = 0x0A + (channel - 1) * 2;
    externalRows.push(
      {
        name: `V${channel}_MSB`,
        address: hexAddress(base),
        width: "8",
        access: "RO",
        purpose: `V${channel} raw conversion sonucunun MSB byte'i.`,
        fields: ltc2991ExternalMsbFields(),
      },
      {
        name: `V${channel}_LSB`,
        address: hexAddress(base + 1),
        width: "8",
        access: "RO",
        purpose: `V${channel} raw conversion sonucunun LSB byte'i.`,
        fields: ltc2991ExternalLsbFields(),
      },
    );
  }

  return [
    {
      name: "STATUS_LOW",
      address: "0x00",
      width: "8",
      access: "RO",
      reset: "0x00",
      purpose: "External V1..V8 conversion ready bitleri.",
      fields: [
        { bits: "B7", name: "V8 ready", meaning: "V8 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B6", name: "V7 ready", meaning: "V7 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B5", name: "V6 ready", meaning: "V6 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B4", name: "V5 ready", meaning: "V5 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B3", name: "V4 ready", meaning: "V4 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B2", name: "V3 ready", meaning: "V3 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B1", name: "V2 ready", meaning: "V2 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B0", name: "V1 ready", meaning: "V1 sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
      ],
    },
    {
      name: "STATUS_HIGH",
      address: "0x01",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "External pair enable bitleri, T_INTERNAL/VCC enable biti, busy ve T_INTERNAL/VCC ready bitleri.",
      fields: [
        { bits: "B7", name: "V7/V8/TR4 enable", meaning: "V7/V8 pair veya TR4 olcum grubunu enable eder.", values: disabledEnabledValues },
        { bits: "B6", name: "V5/V6/TR3 enable", meaning: "V5/V6 pair veya TR3 olcum grubunu enable eder.", values: disabledEnabledValues },
        { bits: "B5", name: "V3/V4/TR2 enable", meaning: "V3/V4 pair veya TR2 olcum grubunu enable eder.", values: disabledEnabledValues },
        { bits: "B4", name: "V1/V2/TR1 enable", meaning: "V1/V2 pair veya TR1 olcum grubunu enable eder.", values: disabledEnabledValues },
        { bits: "B3", name: "T_INTERNAL/VCC enable", meaning: "Ic sicaklik ve VCC conversion grubunu enable eder.", values: disabledEnabledValues },
        { bits: "B2", name: "Busy", meaning: "Conversion devam ederken set olan busy bitidir.", values: ["0: sleep/idle / hazir", "1: conversion devam ediyor"] },
        { bits: "B1", name: "T_INTERNAL ready", meaning: "Ic sicaklik sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B0", name: "VCC ready", meaning: "VCC sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
      ],
    },
    {
      name: "RESERVED_02",
      address: "0x02",
      width: "8",
      access: "N/A",
      purpose: "Datasheet register map icinde reserved adres.",
      fields: reservedFields(),
    },
    {
      name: "RESERVED_03",
      address: "0x03",
      width: "8",
      access: "N/A",
      purpose: "Datasheet register map icinde reserved adres.",
      fields: reservedFields(),
    },
    {
      name: "RESERVED_04",
      address: "0x04",
      width: "8",
      access: "N/A",
      purpose: "Datasheet register map icinde reserved adres.",
      fields: reservedFields(),
    },
    {
      name: "RESERVED_05",
      address: "0x05",
      width: "8",
      access: "N/A",
      purpose: "Datasheet register map icinde reserved adres.",
      fields: reservedFields(),
    },
    {
      name: "CONTROL_V1V4",
      address: "0x06",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "V1/V2 ve V3/V4 pair mode bitleri.",
      fields: [
        { bits: "B7", name: "V3/V4 filter", meaning: "V3/V4 olcum grubunda digital filter ayarini belirler.", values: filterValues },
        { bits: "B6", name: "TR2 Kelvin", meaning: "TR2 remote temperature sonucu icin Celsius/Kelvin formatini secer.", values: celsiusKelvinValues },
        { bits: "B5", name: "V3/V4 temperature", meaning: "V3/V4 pair'ini remote temperature olcumu icin kullanir.", values: voltageTemperatureValues },
        { bits: "B4", name: "V3/V4 differential", meaning: "V3/V4 pair'ini differential voltage/current yolu olarak kullanir.", values: singleEndedDifferentialValues },
        { bits: "B3", name: "V1/V2 filter", meaning: "V1/V2 olcum grubunda digital filter ayarini belirler.", values: filterValues },
        { bits: "B2", name: "TR1 Kelvin", meaning: "TR1 remote temperature sonucu icin Celsius/Kelvin formatini secer.", values: celsiusKelvinValues },
        { bits: "B1", name: "V1/V2 temperature", meaning: "V1/V2 pair'ini remote temperature olcumu icin kullanir.", values: voltageTemperatureValues },
        { bits: "B0", name: "V1/V2 differential", meaning: "V1/V2 pair'ini differential voltage/current yolu olarak kullanir.", values: singleEndedDifferentialValues },
      ],
    },
    {
      name: "CONTROL_V5V8",
      address: "0x07",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "V5/V6 ve V7/V8 pair mode bitleri.",
      fields: [
        { bits: "B7", name: "V7/V8 filter", meaning: "V7/V8 olcum grubunda digital filter ayarini belirler.", values: filterValues },
        { bits: "B6", name: "TR4 Kelvin", meaning: "TR4 remote temperature sonucu icin Celsius/Kelvin formatini secer.", values: celsiusKelvinValues },
        { bits: "B5", name: "V7/V8 temperature", meaning: "V7/V8 pair'ini remote temperature olcumu icin kullanir.", values: voltageTemperatureValues },
        { bits: "B4", name: "V7/V8 differential", meaning: "V7/V8 pair'ini differential voltage/current yolu olarak kullanir.", values: singleEndedDifferentialValues },
        { bits: "B3", name: "V5/V6 filter", meaning: "V5/V6 olcum grubunda digital filter ayarini belirler.", values: filterValues },
        { bits: "B2", name: "TR3 Kelvin", meaning: "TR3 remote temperature sonucu icin Celsius/Kelvin formatini secer.", values: celsiusKelvinValues },
        { bits: "B1", name: "V5/V6 temperature", meaning: "V5/V6 pair'ini remote temperature olcumu icin kullanir.", values: voltageTemperatureValues },
        { bits: "B0", name: "V5/V6 differential", meaning: "V5/V6 pair'ini differential voltage/current yolu olarak kullanir.", values: singleEndedDifferentialValues },
      ],
    },
    {
      name: "PWM_T_INTERNAL_CONTROL",
      address: "0x08",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "PWM output ve internal temperature format/control register'i.",
      fields: [
        { bits: "B7", name: "PWM threshold LSB", meaning: "PWM threshold degerinin en dusuk bitidir; 0x09 register'i ust 8 biti tasir." },
        { bits: "B6", name: "PWM inverted", meaning: "PWM output polaritesini secer.", values: ["0: normal polarity", "1: inverted polarity"] },
        { bits: "B5", name: "PWM enable", meaning: "PWM output fonksiyonunu enable eder.", values: disabledEnabledValues },
        { bits: "B4", name: "PWM mode", meaning: "PWM comparator/input davranisini secer; board kullanimi varsa datasheet akisi ile birlikte degerlendirilmelidir." },
        { bits: "B3", name: "T_INTERNAL Kelvin", meaning: "Ic sicaklik sonucunda Celsius/Kelvin formatini secer.", values: celsiusKelvinValues },
        { bits: "B2:B0", name: "Reserved", meaning: "Reserved alan; yazarken 0 tutulmalidir.", values: ["000: normal kullanım", "diger: reserved; kullanma"] },
      ],
    },
    {
      name: "PWM_THRESHOLD_MSB",
      address: "0x09",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "PWM threshold degerinin ust 8 biti.",
      fields: byteFields("PWM_THRESHOLD[8:1]"),
    },
    ...externalRows,
    {
      name: "T_INTERNAL_MSB",
      address: "0x1A",
      width: "8",
      access: "RO",
      purpose: "Raw internal temperature MSB byte'i.",
      fields: ltc2991TemperatureMsbFields("Internal temperature"),
    },
    {
      name: "T_INTERNAL_LSB",
      address: "0x1B",
      width: "8",
      access: "RO",
      purpose: "Raw internal temperature LSB byte'i.",
      fields: byteFields("T_INTERNAL[7:0]"),
    },
    {
      name: "VCC_MSB",
      address: "0x1C",
      width: "8",
      access: "RO",
      purpose: "Raw VCC conversion MSB byte'i.",
      fields: [
        { bits: "B7", name: "Data valid", meaning: "VCC conversion sonucunda yeni data hazir oldugunu gosterir.", values: oldNewDataValues },
        { bits: "B6", name: "Sign", meaning: "VCC measurement formatindaki sign bitidir; datasheet formatinda VCC = result + 2.5V olarak yorumlanir.", values: signValues },
        { bits: "B5:B0", name: "VCC code MSB", meaning: "VCC raw conversion code ust data bitleri." },
      ],
    },
    {
      name: "VCC_LSB",
      address: "0x1D",
      width: "8",
      access: "RO",
      purpose: "Raw VCC conversion LSB byte'i.",
      fields: byteFields("VCC[7:0]"),
    },
  ];
}

function ds1682Registers(): KnowledgeRegister[] {
  const alarmRows = ["LOW", "LOW_MID", "HIGH_MID", "HIGH"].map((suffix, index) => ({
    name: `ALARM_${suffix}`,
    address: hexAddress(0x01 + index),
    width: "8",
    access: "RW",
    reset: "0x00",
    purpose: `32-bit alarm trip point degerinin byte ${index} parcasi; little-endian siradadir.`,
    fields: byteFields(`ALARM[${index * 8 + 7}:${index * 8}]`),
  }));
  const elapsedRows = ["LOW", "LOW_MID", "HIGH_MID", "HIGH"].map((suffix, index) => ({
    name: `ETC_${suffix}`,
    address: hexAddress(0x05 + index),
    width: "8",
    access: "RO",
    reset: "0x00",
    purpose: `32-bit elapsed-time counter degerinin byte ${index} parcasi; quarter-second tick ve little-endian siradadir.`,
    fields: byteFields(`ETC[${index * 8 + 7}:${index * 8}]`),
  }));
  const userRows = Array.from({ length: 10 }, (_, index) => ({
    name: `USER_${index + 1}`,
    address: hexAddress(0x0B + index),
    width: "8",
    access: "RW",
    reset: "0x00",
    purpose: `User EEPROM byte ${index + 1}.`,
    fields: byteFields(`USER_${index + 1}`),
  }));

  return [
    {
      name: "CONFIGURATION",
      address: "0x00",
      width: "8",
      access: "RW",
      reset: "0x00",
      purpose: "Alarm flag, write-disable flag'leri, alarm output secimi, reset enable ve event MSB.",
      fields: [
        { bits: "B7", name: "Reserved", meaning: "Normal kullanimda 0 olarak birakilir.", values: ["0: normal kullanim", "1: reserved; kullanma"] },
        { bits: "B6", name: "AF", meaning: "Alarm flag; elapsed-time counter alarm degerine ulastiginda set olur.", values: ["0: alarm match yok", "1: alarm match oldu; reset command disinda clear edilemez"] },
        { bits: "B5", name: "WDF", meaning: "Write-disable flag; write-disable komutu sonrasi set olur.", values: ["0: alarm/event/ETC yazimlari disable degil", "1: alarm/event/ETC read-only; clear edilemez"] },
        { bits: "B4", name: "WMDF", meaning: "Write-memory-disable flag; user EEPROM alaninin disable durumunu gosterir.", values: ["0: user EEPROM yazimi disable degil", "1: user EEPROM read-only; clear edilemez"] },
        { bits: "B3", name: "AOS", meaning: "Alarm output select; ALARM pininin pulse veya constant alarm output davranisini secer.", values: ["0: pulse/flash output mode; AP etkisiz", "1: alarm aktifken constant output; AP polarity belirler"] },
        { bits: "B2", name: "RE", meaning: "Reset enable; reset komutu kabul edilmeden once 1 yapilmalidir.", values: ["0: reset command disabled", "1: reset command enabled"] },
        { bits: "B1", name: "AP", meaning: "Alarm polarity; yalnizca AOS=1 constant output modunda etkilidir.", values: ["0: alarm oncesi high-Z, match sonrasi low", "1: alarm oncesi low, match sonrasi high-Z"] },
        { bits: "B0", name: "ECMSB", meaning: "17-bit event counter degerinin en ust bitidir.", values: ["0: event counter bit16 = 0", "1: event counter bit16 = 1"] },
      ],
    },
    ...alarmRows,
    ...elapsedRows,
    {
      name: "EVENT_LOW",
      address: "0x09",
      width: "8",
      access: "RO",
      reset: "0x00",
      purpose: "17-bit event counter degerinin bit7..bit0 parcasi.",
      fields: byteFields("EVENT[7:0]"),
    },
    {
      name: "EVENT_HIGH",
      address: "0x0A",
      width: "8",
      access: "RO",
      reset: "0x00",
      purpose: "17-bit event counter degerinin bit15..bit8 parcasi; bit16 CONFIGURATION.ECMSB alanindadir.",
      fields: byteFields("EVENT[15:8]"),
    },
    ...userRows,
    {
      name: "RESET_COMMAND",
      address: "0x1D",
      width: "command byte",
      access: "WO",
      purpose: "Reset komutu; RE biti set edilmeden kabul edilmemelidir.",
      fields: [
        { bits: "On kosul", name: "CONFIGURATION.RE", meaning: "Reset command kabul icin CONFIGURATION icindeki RE biti enable edilmelidir.", values: ["0: reset command kabul edilmez", "1: reset command kabul edilebilir"] },
        { bits: "Command payload", name: "0x55, 0x55", meaning: "Reset icin ayni command byte iki kez yazilmalidir.", values: ["0x55 iki kez: reset sequence", "diger: reset sequence degil"] },
      ],
    },
    {
      name: "WRITE_DISABLE",
      address: "0x1E",
      width: "command byte",
      access: "WO",
      purpose: "Alarm, event counter ve elapsed-time counter yazimlarini kalici olarak disable eder.",
      fields: [
        { bits: "Command payload", name: "0xAA, 0xAA", meaning: "Write-disable icin ayni command byte iki kez yazilmalidir.", values: ["0xAA iki kez: WDF set edilir", "diger: write-disable sequence degil"] },
        { bits: "Yan etki", name: "WDF", meaning: "Komut sonrasi CONFIGURATION icindeki write-disable flag set olur.", values: ["0: flag set degil", "1: alarm/event/ETC read-only"] },
      ],
    },
    {
      name: "WRITE_MEMORY_DISABLE",
      address: "0x1F",
      width: "command byte",
      access: "WO",
      purpose: "User EEPROM write-memory-disable komutu; production-only islem olarak ele alinmalidir.",
      fields: [
        { bits: "Command payload", name: "0xF0, 0xF0", meaning: "Write-memory-disable icin ayni command byte iki kez yazilmalidir.", values: ["0xF0 iki kez: WMDF set edilir", "diger: write-memory-disable sequence degil"] },
        { bits: "Yan etki", name: "WMDF", meaning: "Komut sonrasi CONFIGURATION icindeki write-memory-disable flag set olur.", values: ["0: flag set degil", "1: user EEPROM read-only"] },
      ],
    },
  ];
}

function ltc2945AdcFields(prefix: string): KnowledgeRegisterField[] {
  return [
    { bits: "MSB B7:B0", name: `${prefix}[11:4]`, meaning: `${prefix} 12-bit ADC code degerinin ust sekiz biti.` },
    { bits: "LSB B7:B4", name: `${prefix}[3:0]`, meaning: `${prefix} 12-bit ADC code degerinin alt dort biti.` },
    { bits: "LSB B3:B0", name: "Unused", meaning: "12-bit conversion code hesabina dahil edilmez.", values: unusedValues },
  ];
}

function ltc2945PowerFields(prefix: string): KnowledgeRegisterField[] {
  return [
    { bits: "MSB2 B7:B0", name: `${prefix}[23:16]`, meaning: `${prefix} 24-bit raw power code ust byte.` },
    { bits: "MSB1 B7:B0", name: `${prefix}[15:8]`, meaning: `${prefix} 24-bit raw power code orta byte.` },
    { bits: "LSB B7:B0", name: `${prefix}[7:0]`, meaning: `${prefix} 24-bit raw power code alt byte.` },
  ];
}

function ltc2945RegisterRows(): KnowledgeRegister[] {
  const powerLike = (name: string, address: number, prefix: string, access = "RO"): KnowledgeRegister => ({
    name,
    address: hexAddress(address),
    width: "8",
    access,
    reset: "0x00",
    purpose: `${prefix} 24-bit power register image byte'i.`,
    fields: name.endsWith("_MSB2") ? ltc2945PowerFields(prefix.split("[")[0]) : byteFields(prefix),
  });
  const adcLike = (name: string, address: number, prefix: string, access = "RO"): KnowledgeRegister => ({
    name,
    address: hexAddress(address),
    width: "8",
    access,
    reset: "0x00",
    purpose: `${prefix} 12-bit ADC register image byte'i.`,
    fields: name.endsWith("_MSB") ? ltc2945AdcFields(prefix.split("[")[0]) : byteFields(prefix),
  });

  return [
    {
      name: "CONTROL",
      address: "0x00",
      width: "8",
      access: "RW",
      reset: "0x05",
      purpose: "Snapshot mode/channel, test mode, ADC busy, VIN monitor, shutdown ve multiplier selection.",
      fields: [
        { bits: "B7", name: "Snapshot mode", meaning: "Conversion akisinin continuous veya snapshot olacagini secer.", values: ["0: continuous conversion / varsayilan", "1: snapshot mode"] },
        { bits: "B6:B5", name: "Snapshot ADC channel", meaning: "Snapshot mode icin yakalanacak ADC kanalini secer.", values: ["00: SENSE", "01: VIN", "10: ADIN", "11: reserved / kullanma"] },
        { bits: "B4", name: "Test mode enable", meaning: "Normal application code icinde kullanilmamasi gereken test mode bitidir.", values: ["0: disabled / varsayilan", "1: enabled"] },
        { bits: "B3", name: "ADC busy", meaning: "ADC conversion devam ederken set olan status bitidir.", values: ["0: ADC idle", "1: ADC busy"] },
        { bits: "B2", name: "VIN monitor", meaning: "VIN olcumunun VDD pininden mi SENSE+ pininden mi yapilacagini secer.", values: ["0: VDD pinini monitor et", "1: SENSE+ pinini monitor et / varsayilan"] },
        { bits: "B1", name: "Shutdown enable", meaning: "ADC olcum bloklarini shutdown moduna alir.", values: ["0: disabled / varsayilan", "1: shutdown enabled"] },
        { bits: "B0", name: "Multiplier select", meaning: "Power multiplier icin ADIN veya SENSE+ girisini secer.", values: ["0: ADIN", "1: SENSE+ / varsayilan"] },
      ],
    },
    { name: "ALERT_ENABLE", address: "0x01", width: "8", access: "RW", reset: "0x00", purpose: "Power, SENSE, VIN ve ADIN limitleri icin ALERT enable maskesi.", fields: ltc2945LimitFields("enable") },
    { name: "STATUS", address: "0x02", width: "8", access: "RO", reset: "0x00", purpose: "Power, SENSE, VIN ve ADIN limit kosullarinin anlik status bitleri.", fields: ltc2945LimitFields("status") },
    { name: "FAULT", address: "0x03", width: "8", access: "RW", reset: "0x00", purpose: "Power, SENSE, VIN ve ADIN limit kosullari icin latched fault bitleri.", fields: ltc2945LimitFields("fault") },
    { name: "FAULT_CLEAR", address: "0x04", width: "8", access: "CoR", reset: "0x00", purpose: "FAULT register'i read-and-clear yolu.", fields: ltc2945LimitFields("clear") },
    powerLike("POWER_MSB2", 0x05, "POWER[23:16]"),
    powerLike("POWER_MSB1", 0x06, "POWER[15:8]"),
    powerLike("POWER_LSB", 0x07, "POWER[7:0]"),
    powerLike("MAX_POWER_MSB2", 0x08, "MAX_POWER[23:16]", "RW*"),
    powerLike("MAX_POWER_MSB1", 0x09, "MAX_POWER[15:8]", "RW*"),
    powerLike("MAX_POWER_LSB", 0x0A, "MAX_POWER[7:0]", "RW*"),
    powerLike("MIN_POWER_MSB2", 0x0B, "MIN_POWER[23:16]", "RW*"),
    powerLike("MIN_POWER_MSB1", 0x0C, "MIN_POWER[15:8]", "RW*"),
    powerLike("MIN_POWER_LSB", 0x0D, "MIN_POWER[7:0]", "RW*"),
    powerLike("MAX_POWER_THRESHOLD_MSB2", 0x0E, "MAX_POWER_THRESHOLD[23:16]", "RW"),
    powerLike("MAX_POWER_THRESHOLD_MSB1", 0x0F, "MAX_POWER_THRESHOLD[15:8]", "RW"),
    powerLike("MAX_POWER_THRESHOLD_LSB", 0x10, "MAX_POWER_THRESHOLD[7:0]", "RW"),
    powerLike("MIN_POWER_THRESHOLD_MSB2", 0x11, "MIN_POWER_THRESHOLD[23:16]", "RW"),
    powerLike("MIN_POWER_THRESHOLD_MSB1", 0x12, "MIN_POWER_THRESHOLD[15:8]", "RW"),
    powerLike("MIN_POWER_THRESHOLD_LSB", 0x13, "MIN_POWER_THRESHOLD[7:0]", "RW"),
    adcLike("SENSE_MSB", 0x14, "SENSE[11:4]"),
    adcLike("SENSE_LSB", 0x15, "SENSE[3:0]"),
    adcLike("MAX_SENSE_MSB", 0x16, "MAX_SENSE[11:4]", "RW*"),
    adcLike("MAX_SENSE_LSB", 0x17, "MAX_SENSE[3:0]", "RW*"),
    adcLike("MIN_SENSE_MSB", 0x18, "MIN_SENSE[11:4]", "RW*"),
    adcLike("MIN_SENSE_LSB", 0x19, "MIN_SENSE[3:0]", "RW*"),
    adcLike("MAX_SENSE_THRESHOLD_MSB", 0x1A, "MAX_SENSE_THRESHOLD[11:4]", "RW"),
    adcLike("MAX_SENSE_THRESHOLD_LSB", 0x1B, "MAX_SENSE_THRESHOLD[3:0]", "RW"),
    adcLike("MIN_SENSE_THRESHOLD_MSB", 0x1C, "MIN_SENSE_THRESHOLD[11:4]", "RW"),
    adcLike("MIN_SENSE_THRESHOLD_LSB", 0x1D, "MIN_SENSE_THRESHOLD[3:0]", "RW"),
    adcLike("VIN_MSB", 0x1E, "VIN[11:4]"),
    adcLike("VIN_LSB", 0x1F, "VIN[3:0]"),
    adcLike("MAX_VIN_MSB", 0x20, "MAX_VIN[11:4]", "RW*"),
    adcLike("MAX_VIN_LSB", 0x21, "MAX_VIN[3:0]", "RW*"),
    adcLike("MIN_VIN_MSB", 0x22, "MIN_VIN[11:4]", "RW*"),
    adcLike("MIN_VIN_LSB", 0x23, "MIN_VIN[3:0]", "RW*"),
    adcLike("MAX_VIN_THRESHOLD_MSB", 0x24, "MAX_VIN_THRESHOLD[11:4]", "RW"),
    adcLike("MAX_VIN_THRESHOLD_LSB", 0x25, "MAX_VIN_THRESHOLD[3:0]", "RW"),
    adcLike("MIN_VIN_THRESHOLD_MSB", 0x26, "MIN_VIN_THRESHOLD[11:4]", "RW"),
    adcLike("MIN_VIN_THRESHOLD_LSB", 0x27, "MIN_VIN_THRESHOLD[3:0]", "RW"),
    adcLike("ADIN_MSB", 0x28, "ADIN[11:4]"),
    adcLike("ADIN_LSB", 0x29, "ADIN[3:0]"),
    adcLike("MAX_ADIN_MSB", 0x2A, "MAX_ADIN[11:4]", "RW*"),
    adcLike("MAX_ADIN_LSB", 0x2B, "MAX_ADIN[3:0]", "RW*"),
    adcLike("MIN_ADIN_MSB", 0x2C, "MIN_ADIN[11:4]", "RW*"),
    adcLike("MIN_ADIN_LSB", 0x2D, "MIN_ADIN[3:0]", "RW*"),
    adcLike("MAX_ADIN_THRESHOLD_MSB", 0x2E, "MAX_ADIN_THRESHOLD[11:4]", "RW"),
    adcLike("MAX_ADIN_THRESHOLD_LSB", 0x2F, "MAX_ADIN_THRESHOLD[3:0]", "RW"),
    adcLike("MIN_ADIN_THRESHOLD_MSB", 0x30, "MIN_ADIN_THRESHOLD[11:4]", "RW"),
    adcLike("MIN_ADIN_THRESHOLD_LSB", 0x31, "MIN_ADIN_THRESHOLD[3:0]", "RW"),
  ];
}

type FlashCommandRow = {
  name: string;
  opcode: string;
  access: "RO" | "WO" | "RW";
  addressBytes: "0" | "3" | "4" | "3/4";
  dummyCycles: string;
  dataBytes: string;
  purpose: string;
  fields?: KnowledgeRegisterField[];
};

const flashFlagStatusFields: KnowledgeRegisterField[] = [
  { bits: "B7", name: "Program/erase controller", meaning: "Internal program/erase controller hazirlik durumunu gosterir.", values: ["0: busy", "1: ready"] },
  { bits: "B6", name: "Erase suspend", meaning: "Erase operasyonunun suspend durumunu gosterir.", values: ["0: clear", "1: erase suspended"] },
  { bits: "B5", name: "Erase error", meaning: "Erase isleminin basarisiz oldugunu veya protection hatasini gosterir.", values: ["0: clear", "1: failure/protection error"] },
  { bits: "B4", name: "Program error", meaning: "Program isleminin veya CRC check'in basarisiz oldugunu gosterir.", values: ["0: clear", "1: failure/protection error"] },
  { bits: "B3", name: "Reserved", meaning: "Reserved alan; ignore et.", values: ["0: reserved default"] },
  { bits: "B2", name: "Program suspend", meaning: "Program operasyonunun suspend durumunu gosterir.", values: ["0: clear", "1: program suspended"] },
  { bits: "B1", name: "Protection error", meaning: "Protected array veya locked OTP alanina yazma/erase denemesi hatasini gosterir.", values: ["0: clear", "1: protection error"] },
  { bits: "B0", name: "Addressing mode", meaning: "Adresleme modunu gosterir.", values: ["0: 3-byte addressing", "1: 4-byte addressing"] },
];

const flashNonvolatileConfigFields: KnowledgeRegisterField[] = [
  { bits: "B15:B12", name: "Dummy clock cycles", meaning: "Fast read komutlarindan sonraki dummy clock sayisini belirler." },
  { bits: "B11:B9", name: "Output driver strength", meaning: "DQ output driver strength ayaridir." },
  { bits: "B8:B6", name: "XIP bits", meaning: "XIP davranisini nonvolatile olarak belirleyen bitlerdir; normal driver akisi icinde degistirilmez." },
  { bits: "B5:B4", name: "Reserved", meaning: "Reserved alan; default deger korunmalidir." },
  { bits: "B3", name: "Reset/hold function", meaning: "DQ3/HOLD#/RESET# fonksiyon secimiyle iliskili nonvolatile ayardir." },
  { bits: "B2", name: "Dual I/O protocol", meaning: "Dual protocol enable davranisini etkiler; controller pinleriyle birlikte dogrulanmalidir." },
  { bits: "B1", name: "Quad I/O protocol", meaning: "Quad protocol enable davranisini etkiler; controller pinleriyle birlikte dogrulanmalidir." },
  { bits: "B0", name: "Address bytes", meaning: "Power-up/default addressing davranisini belirler.", values: ["0: 3-byte default", "1: 4-byte default / segment secimi"] },
];

const flashVolatileConfigFields: KnowledgeRegisterField[] = [
  { bits: "B7:B4", name: "Dummy clock cycles", meaning: "Fast read icin volatile dummy clock sayisini belirler." },
  { bits: "B3", name: "XIP", meaning: "Volatile XIP enable/terminate davranisi." },
  { bits: "B2", name: "Wrap", meaning: "Burst wrap davranisiyla iliskili volatile ayar." },
  { bits: "B1:B0", name: "Output driver / reserved", meaning: "Variant'a bagli output veya reserved bitler; datasheet defaultu korunmalidir." },
];

const flashEnhancedVolatileConfigFields: KnowledgeRegisterField[] = [
  { bits: "B7", name: "Quad I/O protocol", meaning: "Quad I/O protocol enable davranisini belirler.", values: ["0: quad protocol enabled", "1: quad protocol disabled / default variant'a bagli"] },
  { bits: "B6", name: "Dual I/O protocol", meaning: "Dual I/O protocol enable davranisini belirler." },
  { bits: "B5:B4", name: "Reset/hold function", meaning: "DQ3/HOLD#/RESET# fonksiyon secimiyle iliskili volatile ayarlar." },
  { bits: "B3:B0", name: "Output driver / reserved", meaning: "Variant'a bagli output veya reserved alan; default deger korunmalidir." },
];

const mt25qCommandRows: FlashCommandRow[] = [
  { name: "RESET_ENABLE", opcode: "0x66", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "RESET_MEMORY komutunu kabul ettirmek icin once gonderilir." },
  { name: "RESET_MEMORY", opcode: "0x99", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Software reset islemini tamamlar; genelde RESET_ENABLE sonrasi kullanilir." },
  { name: "READ_ID", opcode: "0x9E / 0x9F", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..20", purpose: "JEDEC/device ID bilgisini okur.", fields: flashReadIdFields },
  { name: "MULTIPLE_IO_READ_ID", opcode: "0xAF", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..20", purpose: "Dual/quad capable bus uzerinden ID okuma komutu." },
  { name: "READ_SFDP", opcode: "0x5A", access: "RO", addressBytes: "3", dummyCycles: "8", dataBytes: "1..n", purpose: "Serial Flash Discoverable Parameters tablosunu okur." },
  { name: "READ_DATA", opcode: "0x03", access: "RO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..n", purpose: "Normal single-SPI array read komutu." },
  { name: "FAST_READ", opcode: "0x0B", access: "RO", addressBytes: "3/4", dummyCycles: "8", dataBytes: "1..n", purpose: "Dummy clock ile single-SPI fast read." },
  { name: "DUAL_OUTPUT_FAST_READ", opcode: "0x3B", access: "RO", addressBytes: "3/4", dummyCycles: "8", dataBytes: "1..n", purpose: "Dual output fast read; DQ1/DQ0 data cikisi kullanir." },
  { name: "DUAL_IO_FAST_READ", opcode: "0xBB", access: "RO", addressBytes: "3/4", dummyCycles: "8", dataBytes: "1..n", purpose: "Dual input/output fast read; address ve data dual hat kullanir." },
  { name: "QUAD_OUTPUT_FAST_READ", opcode: "0x6B", access: "RO", addressBytes: "3/4", dummyCycles: "8/10", dataBytes: "1..n", purpose: "Quad output fast read; data quad hatlardan gelir." },
  { name: "QUAD_IO_FAST_READ", opcode: "0xEB", access: "RO", addressBytes: "3/4", dummyCycles: "10", dataBytes: "1..n", purpose: "Quad input/output fast read; address ve data quad hat kullanir." },
  { name: "DTR_FAST_READ", opcode: "0x0D", access: "RO", addressBytes: "3/4", dummyCycles: "6/8", dataBytes: "1..n", purpose: "DTR single-SPI fast read." },
  { name: "DTR_DUAL_OUTPUT_FAST_READ", opcode: "0x3D", access: "RO", addressBytes: "3/4", dummyCycles: "6", dataBytes: "1..n", purpose: "DTR dual output fast read." },
  { name: "DTR_DUAL_IO_FAST_READ", opcode: "0xBD", access: "RO", addressBytes: "3/4", dummyCycles: "6", dataBytes: "1..n", purpose: "DTR dual I/O fast read." },
  { name: "DTR_QUAD_OUTPUT_FAST_READ", opcode: "0x6D", access: "RO", addressBytes: "3/4", dummyCycles: "6/8", dataBytes: "1..n", purpose: "DTR quad output fast read." },
  { name: "DTR_QUAD_IO_FAST_READ", opcode: "0xED", access: "RO", addressBytes: "3/4", dummyCycles: "8", dataBytes: "1..n", purpose: "DTR quad input/output fast read." },
  { name: "QUAD_IO_WORD_READ", opcode: "0xE7", access: "RO", addressBytes: "3/4", dummyCycles: "4", dataBytes: "1..n", purpose: "Quad I/O word read komutu." },
  { name: "READ_DATA_4B", opcode: "0x13", access: "RO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..n", purpose: "4-byte address normal read." },
  { name: "FAST_READ_4B", opcode: "0x0C", access: "RO", addressBytes: "4", dummyCycles: "8/10", dataBytes: "1..n", purpose: "4-byte address fast read." },
  { name: "DUAL_OUTPUT_FAST_READ_4B", opcode: "0x3C", access: "RO", addressBytes: "4", dummyCycles: "8", dataBytes: "1..n", purpose: "4-byte address dual output fast read." },
  { name: "DUAL_IO_FAST_READ_4B", opcode: "0xBC", access: "RO", addressBytes: "4", dummyCycles: "8", dataBytes: "1..n", purpose: "4-byte address dual I/O fast read." },
  { name: "QUAD_OUTPUT_FAST_READ_4B", opcode: "0x6C", access: "RO", addressBytes: "4", dummyCycles: "8/10", dataBytes: "1..n", purpose: "4-byte address quad output fast read." },
  { name: "QUAD_IO_FAST_READ_4B", opcode: "0xEC", access: "RO", addressBytes: "4", dummyCycles: "10", dataBytes: "1..n", purpose: "4-byte address quad I/O fast read." },
  { name: "DTR_FAST_READ_4B", opcode: "0x0E", access: "RO", addressBytes: "4", dummyCycles: "6/8", dataBytes: "1..n", purpose: "4-byte address DTR fast read." },
  { name: "DTR_DUAL_IO_FAST_READ_4B", opcode: "0xBE", access: "RO", addressBytes: "4", dummyCycles: "6", dataBytes: "1..n", purpose: "4-byte address DTR dual I/O fast read." },
  { name: "DTR_QUAD_IO_FAST_READ_4B", opcode: "0xEE", access: "RO", addressBytes: "4", dummyCycles: "8", dataBytes: "1..n", purpose: "4-byte address DTR quad I/O fast read." },
  { name: "WRITE_ENABLE", opcode: "0x06", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Program/erase/register write komutlari oncesinde WEL bitini set eder." },
  { name: "WRITE_DISABLE", opcode: "0x04", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "WEL bitini clear eder." },
  { name: "READ_STATUS", opcode: "0x05", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Status register okuma; WIP/WEL/protection bitleri icin kullanilir.", fields: flashStatusFields },
  { name: "READ_FLAG_STATUS", opcode: "0x70", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Program/erase ready ve hata flag'lerini okur.", fields: flashFlagStatusFields },
  { name: "READ_NONVOLATILE_CONFIG", opcode: "0xB5", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "2..n", purpose: "Nonvolatile configuration register okuma.", fields: flashNonvolatileConfigFields },
  { name: "READ_VOLATILE_CONFIG", opcode: "0x85", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Volatile configuration register okuma.", fields: flashVolatileConfigFields },
  { name: "READ_ENHANCED_VOLATILE_CONFIG", opcode: "0x65", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Enhanced volatile configuration register okuma.", fields: flashEnhancedVolatileConfigFields },
  { name: "READ_EXTENDED_ADDRESS", opcode: "0xC8", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Extended address register okuma; 3-byte mode'da segment secimini gosterir." },
  { name: "READ_GENERAL_PURPOSE", opcode: "0x96", access: "RO", addressBytes: "0", dummyCycles: "8", dataBytes: "1..n", purpose: "General purpose read register okuma." },
  { name: "WRITE_STATUS", opcode: "0x01", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "1", purpose: "Status register yazma; write enable on kosulu vardir.", fields: flashStatusFields },
  { name: "WRITE_NONVOLATILE_CONFIG", opcode: "0xB1", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "2", purpose: "Nonvolatile configuration register yazma; production-only dikkat gerektirir.", fields: flashNonvolatileConfigFields },
  { name: "WRITE_VOLATILE_CONFIG", opcode: "0x81", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "1", purpose: "Volatile configuration register yazma.", fields: flashVolatileConfigFields },
  { name: "WRITE_ENHANCED_VOLATILE_CONFIG", opcode: "0x61", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "1", purpose: "Enhanced volatile configuration register yazma.", fields: flashEnhancedVolatileConfigFields },
  { name: "WRITE_EXTENDED_ADDRESS", opcode: "0xC5", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "1", purpose: "Extended address register yazma; 3-byte addressing segment secimi icindir." },
  { name: "CLEAR_FLAG_STATUS", opcode: "0x50", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Flag status register hata bitlerini temizler." },
  { name: "PAGE_PROGRAM", opcode: "0x02", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..256", purpose: "3-byte/4-byte mode page program komutu." },
  { name: "DUAL_INPUT_FAST_PROGRAM", opcode: "0xA2", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..256", purpose: "Dual input fast program komutu." },
  { name: "EXTENDED_DUAL_INPUT_FAST_PROGRAM", opcode: "0xD2", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..256", purpose: "Extended dual input fast program komutu." },
  { name: "QUAD_INPUT_FAST_PROGRAM", opcode: "0x32", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..256", purpose: "Quad input fast program komutu." },
  { name: "EXTENDED_QUAD_INPUT_FAST_PROGRAM", opcode: "0x38", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..256", purpose: "Extended quad input fast program komutu." },
  { name: "PAGE_PROGRAM_4B", opcode: "0x12", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..256", purpose: "4-byte address page program." },
  { name: "QUAD_INPUT_FAST_PROGRAM_4B", opcode: "0x34", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..256", purpose: "4-byte address quad input fast program." },
  { name: "EXTENDED_QUAD_INPUT_FAST_PROGRAM_4B", opcode: "0x3E", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..256", purpose: "4-byte address extended quad input fast program." },
  { name: "SUBSECTOR_ERASE_32K", opcode: "0x52", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "0", purpose: "32 KB subsector erase." },
  { name: "SUBSECTOR_ERASE", opcode: "0x20", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "0", purpose: "4 KB subsector erase." },
  { name: "SECTOR_ERASE", opcode: "0xD8", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "0", purpose: "64 KB sector erase." },
  { name: "BULK_ERASE", opcode: "0xC7 / 0x60", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Tum flash array erase; cok dikkatli kullanilmalidir." },
  { name: "SECTOR_ERASE_4B", opcode: "0xDC", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "0", purpose: "4-byte address 64 KB sector erase." },
  { name: "SUBSECTOR_ERASE_4B", opcode: "0x21", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "0", purpose: "4-byte address 4 KB subsector erase." },
  { name: "SUBSECTOR_ERASE_32K_4B", opcode: "0x5C", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "0", purpose: "4-byte address 32 KB subsector erase." },
  { name: "PROGRAM_ERASE_SUSPEND", opcode: "0x75", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Devam eden program/erase operasyonunu suspend eder." },
  { name: "PROGRAM_ERASE_RESUME", opcode: "0x7A", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Suspend edilmis program/erase operasyonunu devam ettirir." },
  { name: "READ_OTP_ARRAY", opcode: "0x4B", access: "RO", addressBytes: "3/4", dummyCycles: "8/10", dataBytes: "1..64", purpose: "One-time-programmable array okuma." },
  { name: "PROGRAM_OTP_ARRAY", opcode: "0x42", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..64", purpose: "One-time-programmable array programlama." },
  { name: "ENTER_4BYTE", opcode: "0xB7", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "4-byte address mode'a gecis." },
  { name: "EXIT_4BYTE", opcode: "0xE9", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "4-byte address mode'dan cikis." },
  { name: "ENTER_QUAD_IO", opcode: "0x35", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Quad input/output protocol modunu enable eder." },
  { name: "RESET_QUAD_IO", opcode: "0xF5", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Quad input/output protocol modunu resetler." },
  { name: "ENTER_DEEP_POWER_DOWN", opcode: "0xB9", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Deep power-down moduna giris." },
  { name: "RELEASE_FROM_DEEP_POWER_DOWN", opcode: "0xAB", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Deep power-down modundan cikis." },
  { name: "READ_SECTOR_PROTECTION", opcode: "0x2D", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Advanced sector protection durumunu okur." },
  { name: "PROGRAM_SECTOR_PROTECTION", opcode: "0x2C", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "2", purpose: "Advanced sector protection programlama." },
  { name: "READ_VOLATILE_LOCK_BITS", opcode: "0xE8", access: "RO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1..n", purpose: "Volatile lock bitlerini okur." },
  { name: "WRITE_VOLATILE_LOCK_BITS", opcode: "0xE5", access: "WO", addressBytes: "3/4", dummyCycles: "0", dataBytes: "1", purpose: "Volatile lock bitlerini yazar." },
  { name: "READ_NONVOLATILE_LOCK_BITS", opcode: "0xE2", access: "RO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..n", purpose: "Nonvolatile lock bitlerini okur." },
  { name: "WRITE_NONVOLATILE_LOCK_BITS", opcode: "0xE3", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "0", purpose: "Nonvolatile lock bitlerini yazar." },
  { name: "ERASE_NONVOLATILE_LOCK_BITS", opcode: "0xE4", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Nonvolatile lock bitlerini erase eder." },
  { name: "READ_GLOBAL_FREEZE_BIT", opcode: "0xA7", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Global freeze bit durumunu okur." },
  { name: "WRITE_GLOBAL_FREEZE_BIT", opcode: "0xA6", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Global freeze bit yazar." },
  { name: "READ_PASSWORD", opcode: "0x27", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "1..n", purpose: "Password protection alanini okur." },
  { name: "WRITE_PASSWORD", opcode: "0x28", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "8", purpose: "Password protection alanini yazar." },
  { name: "UNLOCK_PASSWORD", opcode: "0x29", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "8", purpose: "Password unlock sequence gonderir." },
  { name: "READ_VOLATILE_LOCK_BITS_4B", opcode: "0xE0", access: "RO", addressBytes: "4", dummyCycles: "0", dataBytes: "1..n", purpose: "4-byte address volatile lock bit okuma." },
  { name: "WRITE_VOLATILE_LOCK_BITS_4B", opcode: "0xE1", access: "WO", addressBytes: "4", dummyCycles: "0", dataBytes: "1", purpose: "4-byte address volatile lock bit yazma." },
  { name: "INTERFACE_ACTIVATION", opcode: "0x9B", access: "WO", addressBytes: "0", dummyCycles: "0", dataBytes: "0", purpose: "Advanced function interface activation komutu." },
  { name: "CRC_CHECK", opcode: "0x9B / 0x27", access: "RO", addressBytes: "0", dummyCycles: "0", dataBytes: "10 veya 18", purpose: "Cyclic redundancy check operation." },
];

function mt25qRegisters(part: "MT25Q128" | "MT25QU02G"): KnowledgeRegister[] {
  const large = part === "MT25QU02G";
  return mt25qCommandRows.map((row) => {
    const effectiveAddressBytes = row.addressBytes === "3/4" ? (large ? "4" : "3") : row.addressBytes;
    const widthParts = ["opcode"];
    if (effectiveAddressBytes !== "0") widthParts.push(`${effectiveAddressBytes}-byte address`);
    if (row.dummyCycles !== "0") widthParts.push(`${row.dummyCycles} dummy cycles`);
    if (row.dataBytes !== "0") widthParts.push(`${row.dataBytes} data byte`);
    return {
      name: row.name,
      address: row.opcode,
      width: widthParts.join(" + "),
      access: row.access,
      purpose: row.purpose,
      fields: row.fields ?? [
        { bits: "Opcode", name: row.opcode, meaning: `${row.name} komut opcode degeri.` },
        ...(effectiveAddressBytes !== "0" ? [{ bits: "Address", name: `${effectiveAddressBytes}-byte address`, meaning: "Gonderilecek array/register adres byte'lari MSB-first siradadir." }] : []),
        ...(row.dummyCycles !== "0" ? [{ bits: "Dummy", name: `${row.dummyCycles} cycles`, meaning: "Data fazindan once controller tarafindan clocklanan dummy cycle sayisi." }] : []),
        ...(row.dataBytes !== "0" ? [{ bits: "Data", name: row.dataBytes, meaning: row.access === "RO" ? "Cihazdan okunacak byte sayisi." : "Cihaza gonderilecek payload byte sayisi." }] : []),
      ],
    };
  });
}

const tics24Fields: KnowledgeRegisterField[] = [
  {
    bits: "Word[23]",
    name: "R/W",
    meaning: "SPI frame içindeki erişim yönü bitidir.",
    values: ["0: write", "1: read"],
  },
  {
    bits: "Word address alanı",
    name: "Address",
    meaning: "Cihaz register adresidir; LMK04832 için 15 bit, LMX2820/LMX1204/LMX1205 için 7 bit yorumlanır.",
  },
  {
    bits: "Word data alanı",
    name: "Data",
    meaning: "Cihaz register data alanıdır; LMK04832 için 8 bit, LMX2820/LMX1204/LMX1205 için 16 bit yazılır.",
  },
];

function ticsRegisterTransfer(part: string, reg: KnowledgeRegister): KnowledgeRegisterTransfer[] {
  const upper = part.toUpperCase();
  const addressLabel = reg.address;
  const dataBits = upper === "LMK04832" ? "D7:D0" : "D15:D0";
  const addressBits = upper === "LMK04832" ? "A14:A0" : "A6:A0";
  return [
    {
      title: "TICS Pro word write",
      access: "WRITE",
      txBytes: "3 byte",
      rxBytes: "0 byte",
      tx: [`R/W=0 + ${addressBits} (${addressLabel}) + ${dataBits}`],
      rx: ["-"],
      code: [
        `/* TICS Pro export -> config.ticspro_registers */`,
        `${cFunc(part, "device_init")}(spSpi);`,
      ],
      note: "Generated driver tek register API'si yerine TICS Pro array'ini sırayı bozmadan init sırasında gönderir.",
    },
  ];
}

function hexAddress(address: number, digits = 2): string {
  return `0x${address.toString(16).toUpperCase().padStart(digits, "0")}`;
}

function ticsFrameRegister(): KnowledgeRegister {
  return {
    name: "TICS_24BIT_WORD",
    address: "word",
    width: "24",
    access: "WO",
    purpose: "TICS Pro export satırındaki tek SPI register write frame'i.",
    fields: tics24Fields,
  };
}

type TiClockPart = "LMK04832" | "LMX2820" | "LMX1204" | "LMX1205";

function tiClockFields(part: TiClockPart, address: string, fallbackName: string): KnowledgeRegisterField[] {
  return getTiClockBitfields(part, address) ?? [
    {
      bits: part === "LMK04832" ? "D7:D0" : "D15:D0",
      name: fallbackName,
      meaning: "Bu register için bitfield kaydı bulunamadı; TI datasheet/register map doğrulaması gerektirir.",
    },
  ];
}

const LMK04832_REGISTER_ROWS: Array<[number, string]> = [
  [0x000, "RESET / SPI_3WIRE_DIS"], [0x002, "POWERDOWN"], [0x003, "ID_DEVICE_TYPE"],
  [0x004, "ID_PROD[15:8]"], [0x005, "ID_PROD[7:0]"], [0x006, "ID_MASKREV"],
  [0x00C, "ID_VNDR[15:8]"], [0x00D, "ID_VNDR[7:0]"],
  [0x100, "DCLK0_1_DIV[7:0]"], [0x101, "DCLK0_1_DDLY[7:0]"],
  [0x102, "CLKout0_1/DCLK0_1 control"], [0x103, "DCLK0_1 source/control"],
  [0x104, "SCLK0_1 source/control"], [0x105, "SCLK0_1 analog delay"],
  [0x106, "SCLK0_1 digital delay"], [0x107, "CLKout1/CLKout0 format"],
  [0x108, "DCLK2_3_DIV[7:0]"], [0x109, "DCLK2_3_DDLY[7:0]"],
  [0x10A, "CLKout2_3/DCLK2_3 control"], [0x10B, "DCLK2_3 source/control"],
  [0x10C, "SCLK2_3 source/control"], [0x10D, "SCLK2_3 analog delay"],
  [0x10E, "SCLK2_3 digital delay"], [0x10F, "CLKout3/CLKout2 format"],
  [0x110, "DCLK4_5_DIV[7:0]"], [0x111, "DCLK4_5_DDLY[7:0]"],
  [0x112, "CLKout4_5/DCLK4_5 control"], [0x113, "DCLK4_5 source/control"],
  [0x114, "SCLK4_5 source/control"], [0x115, "SCLK4_5 analog delay"],
  [0x116, "SCLK4_5 digital delay"], [0x117, "CLKout5/CLKout4 format"],
  [0x118, "DCLK6_7_DIV[7:0]"], [0x119, "DCLK6_7_DDLY[7:0]"],
  [0x11A, "CLKout6_7/DCLK6_7 control"], [0x11B, "DCLK6_7 source/control"],
  [0x11C, "SCLK6_7 source/control"], [0x11D, "SCLK6_7 analog delay"],
  [0x11E, "SCLK6_7 digital delay"], [0x11F, "CLKout7/CLKout6 format"],
  [0x120, "DCLK8_9_DIV[7:0]"], [0x121, "DCLK8_9_DDLY[7:0]"],
  [0x122, "CLKout8_9/DCLK8_9 control"], [0x123, "DCLK8_9 source/control"],
  [0x124, "SCLK8_9 source/control"], [0x125, "SCLK8_9 analog delay"],
  [0x126, "SCLK8_9 digital delay"], [0x127, "CLKout9/CLKout8 format"],
  [0x128, "DCLK10_11_DIV[7:0]"], [0x129, "DCLK10_11_DDLY[7:0]"],
  [0x12A, "CLKout10_11/DCLK10_11 control"], [0x12B, "DCLK10_11 source/control"],
  [0x12C, "SCLK10_11 source/control"], [0x12D, "SCLK10_11 analog delay"],
  [0x12E, "SCLK10_11 digital delay"], [0x12F, "CLKout11/CLKout10 format"],
  [0x130, "DCLK12_13_DIV[7:0]"], [0x131, "DCLK12_13_DDLY[7:0]"],
  [0x132, "CLKout12_13/DCLK12_13 control"], [0x133, "DCLK12_13 source/control"],
  [0x134, "SCLK12_13 source/control"], [0x135, "SCLK12_13 analog delay"],
  [0x136, "SCLK12_13 digital delay"], [0x137, "CLKout13/CLKout12 format"],
  [0x138, "VCO_MUX / OSCout_MUX / OSCout_FMT"], [0x139, "SYSREF_REQ_EN / SYNC_BYPASS / SYSREF_MUX"],
  [0x13A, "SYSREF_DIV[12:8]"], [0x13B, "SYSREF_DIV[7:0]"],
  [0x13C, "SYSREF_DDLY[12:8]"], [0x13D, "SYSREF_DDLY[7:0]"],
  [0x13E, "SYSREF_PULSE_CNT"], [0x13F, "PLL2_RCLK_MUX / PLL2_NCLK_MUX / feedback mux"],
  [0x140, "PLL1/VCO/OSCin/SYSREF power-down"], [0x141, "SYSREF DDLY enable mask"],
  [0x142, "DDLYd_STEP_CNT"], [0x143, "SYSREF_CLR / SYNC control"],
  [0x144, "SYNC disable mask"], [0x145, "PLL1R/PLL2R sync source"],
  [0x146, "CLKin enable/type"], [0x147, "CLKin selection/demux"],
  [0x148, "CLKin_SEL0 mux/type"], [0x149, "CLKin_SEL1 mux/type"],
  [0x14A, "RESET_MUX / RESET_TYPE"], [0x14B, "LOS/HOLDOVER/MAN_DAC control"],
  [0x14C, "MAN_DAC[7:0]"], [0x14D, "DAC_TRIP_LOW"], [0x14E, "DAC_TRIP_HIGH"],
  [0x14F, "DAC_CLK_CNTR"], [0x150, "Holdover and CLKin switching control"],
  [0x151, "HOLDOVER_DLD_CNT[13:8]"], [0x152, "HOLDOVER_DLD_CNT[7:0]"],
  [0x153, "CLKin0_R[13:8]"], [0x154, "CLKin0_R[7:0]"],
  [0x155, "CLKin1_R[13:8]"], [0x156, "CLKin1_R[7:0]"],
  [0x157, "CLKin2_R[13:8]"], [0x158, "CLKin2_R[7:0]"],
  [0x159, "PLL1_N[13:8]"], [0x15A, "PLL1_N[7:0]"],
  [0x15B, "PLL1 window / charge-pump control"], [0x15C, "PLL1_DLD_CNT[13:8]"],
  [0x15D, "PLL1_DLD_CNT[7:0]"], [0x15E, "HOLDOVER_EXIT_NADJ"],
  [0x15F, "PLL1_LD_MUX / PLL1_LD_TYPE"], [0x160, "PLL2_R[11:8]"],
  [0x161, "PLL2_R[7:0]"], [0x162, "PLL2_P / OSCin_FREQ / PLL2_REF_2X_EN"],
  [0x163, "PLL2_N_CAL[17:16]"], [0x164, "PLL2_N_CAL[15:8]"], [0x165, "PLL2_N_CAL[7:0]"],
  [0x166, "PLL2_N[17:16]"], [0x167, "PLL2_N[15:8]"], [0x168, "PLL2_N[7:0]"],
  [0x169, "PLL2 window / charge-pump / DLD control"], [0x16A, "PLL2_DLD_CNT[13:8]"],
  [0x16B, "PLL2_DLD_CNT[7:0]"], [0x16C, "Reserved"], [0x173, "PLL2_PRE_PD / PLL2_PD"],
  [0x177, "PLL1R_RST"], [0x182, "Clear PLL lock-lost flags"],
  [0x183, "PLL DLD/readback status"], [0x184, "CLKin select/LOS readback + DAC[9:8]"],
  [0x185, "RB_DAC_VALUE[7:0]"], [0x188, "Holdover/DAC rail readback"], [0x555, "SPI_LOCK"],
];

function lmk04832Registers(): KnowledgeRegister[] {
  return [
    ticsFrameRegister(),
    ...LMK04832_REGISTER_ROWS.map(([address, summary]) => ({
      name: `REG_${hexAddress(address, 3).slice(2)}`,
      address: hexAddress(address, 3),
      width: "8",
      access: address >= 0x182 && address !== 0x555 ? "RO/RW status" : "RW",
      purpose: `LMK04832 Table 5 register map girdisi: ${summary}.`,
      fields: tiClockFields("LMK04832", hexAddress(address, 3), summary),
    })),
  ];
}

const LMX1204_REGISTER_ROWS = [
  { address: 0x00, name: "R0", reset: "0x0000", feature: "Powerdown, Reset, Multiplier Mode Calibration" },
  { address: 0x02, name: "R2", reset: "0x0223", feature: "Multiplier Mode state-machine clock" },
  { address: 0x03, name: "R3", reset: "0xFF86", feature: "Multiplier Mode state-machine clock, output enables" },
  { address: 0x04, name: "R4", reset: "0x360F", feature: "Output enables, CLKOUT power" },
  { address: 0x05, name: "R5", reset: "0x4936", feature: "CLKOUT power, SYSREFOUT power" },
  { address: 0x06, name: "R6", reset: "0x36D6", feature: "LOGICLK enable, SYSREFOUT power/VCM" },
  { address: 0x07, name: "R7", reset: "0x0000", feature: "LOGICLK and LOGISYSREF" },
  { address: 0x08, name: "R8", reset: "0x0120", feature: "LOGICLK and LOGISYSREF" },
  { address: 0x09, name: "R9", reset: "0x001E", feature: "LOGICLK divider, SYNC, SYSREFREQ" },
  { address: 0x0B, name: "R11", reset: "0xFFFF", feature: "SYSREFREQ windowing readback" },
  { address: 0x0C, name: "R12", reset: "0xFFFF", feature: "SYSREFREQ windowing readback" },
  { address: 0x0D, name: "R13", reset: "0x0003", feature: "SYSREFREQ windowing" },
  { address: 0x0E, name: "R14", reset: "0x0002", feature: "SYSREFREQ windowing, SYNC, SYSREF" },
  { address: 0x0F, name: "R15", reset: "0x0901", feature: "SYSREFREQ windowing, SYNC, SYSREF" },
  { address: 0x10, name: "R16", reset: "0x1003", feature: "SYSREF" },
  { address: 0x11, name: "R17", reset: "0x07F0", feature: "SYSREF, SYSREFOUT0 delay" },
  { address: 0x12, name: "R18", reset: "0xFE00", feature: "SYSREFOUT delay" },
  { address: 0x13, name: "R19", reset: "0xFE00", feature: "SYSREFOUT delay" },
  { address: 0x14, name: "R20", reset: "0xFE00", feature: "SYSREFOUT delay" },
  { address: 0x15, name: "R21", reset: "0xFE00", feature: "SYSREFOUT delay" },
  { address: 0x16, name: "R22", reset: "0x0800", feature: "SYSREFOUT delay" },
  { address: 0x17, name: "R23", reset: "0x4000", feature: "Temperature sensor, MUXOUT, SYSREFOUT delay" },
  { address: 0x18, name: "R24", reset: "0x0FFE", feature: "Temperature sensor" },
  { address: 0x19, name: "R25", reset: "0x0211", feature: "Multiplier Mode, Divider Mode" },
  { address: 0x1C, name: "R28", reset: "0x0A08", feature: "Multiplier Mode optional partial-assist calibration" },
  { address: 0x1D, name: "R29", reset: "0x05FF", feature: "Multiplier Mode optional partial-assist calibration" },
  { address: 0x21, name: "R33", reset: "0x7777", feature: "Multiplier Mode reserved, must write in multiplier mode" },
  { address: 0x22, name: "R34", reset: "0x0000", feature: "Multiplier Mode reserved, must write in multiplier mode" },
  { address: 0x41, name: "R65", reset: "0x45F0", feature: "Multiplier Mode read-only, optional partial-assist calibration" },
  { address: 0x43, name: "R67", reset: "0x50C8", feature: "Multiplier Mode reserved, must write in multiplier mode" },
  { address: 0x48, name: "R72", reset: "0x0000", feature: "SYSREF" },
  { address: 0x4B, name: "R75", reset: "0xE716", feature: "Multiplier Mode read-only, optional lock detect" },
  { address: 0x4F, name: "R79", reset: "0x0104", feature: "LOGICLK divider reserved, optional divider bypass" },
  { address: 0x56, name: "R86", reset: "0x0000", feature: "MUXOUT reserved, optional tri-state" },
  { address: 0x5A, name: "R90", reset: "0x0000", feature: "LOGICLK divider reserved, optional divider bypass" },
];

function lmx1204Registers(): KnowledgeRegister[] {
  return [
    ticsFrameRegister(),
    ...LMX1204_REGISTER_ROWS.map((row) => ({
      name: row.name,
      address: hexAddress(row.address, 2),
      width: "16",
      access: ["R11", "R12", "R24", "R65", "R75"].includes(row.name) ? "RO/RW mixed" : "RW",
      reset: row.reset,
      purpose: `LMX1204 Table 1-1 register map girdisi: ${row.feature}.`,
      fields: tiClockFields("LMX1204", hexAddress(row.address, 2), row.feature),
    })),
  ];
}

// SNAS850 Table 7-1 (Advance Information, Aralik 2024). Listede olmayan
// offsetler reserved'dir ve degistirilmemelidir.
const LMX1205_REGISTER_ROWS = [
  { address: 0x00, name: "R0", reset: "0x0000", feature: "Powerdown and Reset" },
  { address: 0x01, name: "R1", reset: "0x000A", feature: "MUXOUT pin setting (LD_DIS, READBACK_CTRL)" },
  { address: 0x02, name: "R2", reset: "0x00BF", feature: "Channels, Logic Clock, SYSREF, SYNC and Temp Sensor Enable" },
  { address: 0x03, name: "R3", reset: "0x0000", feature: "CLKIN Delay" },
  { address: 0x04, name: "R4", reset: "0x000D", feature: "CLKOUT0 Enables, Power and Delay" },
  { address: 0x05, name: "R5", reset: "0x000D", feature: "CLKOUT1 Enables, Power and Delay" },
  { address: 0x06, name: "R6", reset: "0x000D", feature: "CLKOUT2 Enables, Power and Delay" },
  { address: 0x07, name: "R7", reset: "0x000D", feature: "CLKOUT3 Enables, Power and Delay" },
  { address: 0x08, name: "R8", reset: "0x5CA9", feature: "SYSREFOUT0 Enables, Power, VCM" },
  { address: 0x09, name: "R9", reset: "0x5CA9", feature: "SYSREFOUT1 Enables, Power, VCM" },
  { address: 0x0A, name: "R10", reset: "0x5CA9", feature: "SYSREFOUT2 Enables, Power, VCM" },
  { address: 0x0B, name: "R11", reset: "0x5CA9", feature: "SYSREFOUT3 Enables, Power, VCM" },
  { address: 0x0C, name: "R12", reset: "0x002B", feature: "LOGICLK Enables, Power, VCM and Output Formats" },
  { address: 0x0D, name: "R13", reset: "0x002B", feature: "LOGISYSREF Enables, Power, VCM and Output Formats" },
  { address: 0x0E, name: "R14", reset: "0x0084", feature: "LOGICLK Dividers" },
  { address: 0x0F, name: "R15", reset: "0x0002", feature: "LOGICLK2 Enables, Dividers" },
  { address: 0x10, name: "R16", reset: "0x0030", feature: "SYSREFREQ Input" },
  { address: 0x11, name: "R17", reset: "0x0005", feature: "SYSREFREQ Input" },
  { address: 0x12, name: "R18", reset: "0x0000", feature: "SYSREFREQ Input (SYSREFREQ_DLY)" },
  { address: 0x13, name: "R19", reset: "0x0004", feature: "SYSREF Output (mode, pulse count, delay bypass)" },
  { address: 0x14, name: "R20", reset: "0x8082", feature: "SYSREF Output Dividers" },
  { address: 0x15, name: "R21", reset: "0x01FC", feature: "SYSREFOUT0 Delay" },
  { address: 0x16, name: "R22", reset: "0x01FC", feature: "SYSREFOUT1 Delay" },
  { address: 0x17, name: "R23", reset: "0x01FC", feature: "SYSREFOUT2 Delay" },
  { address: 0x18, name: "R24", reset: "0x01FC", feature: "SYSREFOUT3 Delay" },
  { address: 0x19, name: "R25", reset: "0x01FC", feature: "LOGISYSREFOUT Delay" },
  { address: 0x1A, name: "R26", reset: "0x00D1", feature: "State Machine Clock (SMCLK_DIV/PRE/EN)" },
  { address: 0x1B, name: "R27", reset: "0x3609", feature: "Clock MUX, Clock Dividers/Multiplier (FCAL)" },
  { address: 0x1D, name: "R29", reset: "0x0000", feature: "SYSREFREQ Windowing readback - rb_CLKPOS[31:16]" },
  { address: 0x1E, name: "R30", reset: "0x0000", feature: "SYSREFREQ Windowing readback - rb_CLKPOS[15:0]" },
  { address: 0x1F, name: "R31", reset: "0x0000", feature: "Temperature Sensor readback - rb_TEMPSENSE" },
  { address: 0x20, name: "R32", reset: "0x0000", feature: "Device Version ID readback - rb_VER_ID" },
  { address: 0x24, name: "R36", reset: "0x84A3", feature: "Multiplier Mode (Reserved)" },
  { address: 0x25, name: "R37", reset: "0x0000", feature: "Lock Detect readback - rb_LOCK_DETECT" },
  { address: 0x27, name: "R39", reset: "0x78E1", feature: "Multiplier Mode (Reserved)" },
  { address: 0x28, name: "R40", reset: "0x78E1", feature: "Multiplier Mode (Reserved)" },
  { address: 0x29, name: "R41", reset: "0x78F3", feature: "Multiplier Mode (Reserved)" },
  { address: 0x2A, name: "R42", reset: "0x76F3", feature: "Multiplier Mode (Reserved)" },
  { address: 0x2B, name: "R43", reset: "0x7707", feature: "Multiplier Mode (Reserved)" },
  { address: 0x2C, name: "R44", reset: "0x7707", feature: "Multiplier Mode (Reserved)" },
  { address: 0x2D, name: "R45", reset: "0x2ABF", feature: "Multiplier Mode (Reserved)" },
  { address: 0x36, name: "R54", reset: "0x0000", feature: "Multiplier Mode (Reserved, bits 15:14 read-only)" },
  { address: 0x37, name: "R55", reset: "0x0000", feature: "Current Optimization (DEV_IOPT_CTRL)" },
  { address: 0x4D, name: "R77", reset: "0x0000", feature: "Multiplier Mode (Reserved)" },
];

function lmx1205Registers(): KnowledgeRegister[] {
  return [
    ticsFrameRegister(),
    ...LMX1205_REGISTER_ROWS.map((row) => ({
      name: row.name,
      address: hexAddress(row.address, 2),
      width: "16",
      access: ["R29", "R30", "R31", "R32", "R37"].includes(row.name)
        ? "RO readback"
        : row.name === "R54"
          ? "RO/RW mixed"
          : "RW",
      reset: row.reset,
      purpose: `LMX1205 Table 7-1 register map girdisi: ${row.feature}.`,
      fields: tiClockFields("LMX1205", hexAddress(row.address, 2), row.feature),
    })),
  ];
}

const LMX2820_REGISTER_ROWS = [
  { address: 0x00, reset: "0x4070" }, { address: 0x01, reset: "0x57A0" }, { address: 0x02, reset: "0xB3E8" }, { address: 0x03, reset: "0x41" }, { address: 0x04, reset: "0x4204" }, { address: 0x05, reset: "0x3832" }, { address: 0x06, reset: "0xA43" }, { address: 0x07, reset: "0xC8" },
  { address: 0x08, reset: "0xC802" }, { address: 0x09, reset: "0x5" }, { address: 0x0A, reset: "0x0" }, { address: 0x0B, reset: "0x603" }, { address: 0x0C, reset: "0x408" }, { address: 0x0D, reset: "0x38" }, { address: 0x0E, reset: "0x3001" }, { address: 0x0F, reset: "0x2001" },
  { address: 0x10, reset: "0x271C" }, { address: 0x11, reset: "0x1440" }, { address: 0x12, reset: "0x3E8" }, { address: 0x13, reset: "0x2120" }, { address: 0x14, reset: "0x272C" }, { address: 0x15, reset: "0x1C64" }, { address: 0x16, reset: "0xE2BF" }, { address: 0x17, reset: "0x1102" },
  { address: 0x18, reset: "0xE34" }, { address: 0x19, reset: "0x624" }, { address: 0x1A, reset: "0xDB0" }, { address: 0x1B, reset: "0x8001" }, { address: 0x1C, reset: "0x639" }, { address: 0x1D, reset: "0x318C" }, { address: 0x1E, reset: "0xB18C" }, { address: 0x1F, reset: "0x401" },
  { address: 0x20, reset: "0x1001" }, { address: 0x21, reset: "0x0" }, { address: 0x22, reset: "0x10" }, { address: 0x23, reset: "0x3100" }, { address: 0x24, reset: "0x38" }, { address: 0x25, reset: "0x500" }, { address: 0x26, reset: "0x0" }, { address: 0x27, reset: "0x3E8" },
  { address: 0x28, reset: "0x0" }, { address: 0x29, reset: "0x0" }, { address: 0x2A, reset: "0x0" }, { address: 0x2B, reset: "0x0" }, { address: 0x2C, reset: "0x0" }, { address: 0x2D, reset: "0x0" }, { address: 0x2E, reset: "0x300" }, { address: 0x2F, reset: "0x300" },
  { address: 0x30, reset: "0x4180" }, { address: 0x31, reset: "0x0" }, { address: 0x32, reset: "0x80" }, { address: 0x33, reset: "0x203F" }, { address: 0x34, reset: "0x0" }, { address: 0x35, reset: "0x0" }, { address: 0x36, reset: "0x0" }, { address: 0x37, reset: "0x2" },
  { address: 0x38, reset: "0x1" }, { address: 0x39, reset: "0x1" }, { address: 0x3A, reset: "0x0" }, { address: 0x3B, reset: "0x1388" }, { address: 0x3C, reset: "0x1F4" }, { address: 0x3D, reset: "0x3E8" }, { address: 0x3E, reset: "0x0" }, { address: 0x3F, reset: "0xC350" },
  { address: 0x40, reset: "0x4080" }, { address: 0x41, reset: "0x1" }, { address: 0x42, reset: "0x3F" }, { address: 0x43, reset: "0x0" }, { address: 0x44, reset: "0x0" }, { address: 0x45, reset: "0x11" }, { address: 0x46, reset: "0x1E" }, { address: 0x47, reset: "0x0" },
  { address: 0x48, reset: "0x0" }, { address: 0x49, reset: "0x0" }, { address: 0x4A, reset: "0x0" }, { address: 0x4B, reset: "0x0" }, { address: 0x4C, reset: "0x0" }, { address: 0x4D, reset: "0x56CC" }, { address: 0x4E, reset: "0x1" }, { address: 0x4F, reset: "0x11E" },
  { address: 0x50, reset: "0x1C0" }, { address: 0x51, reset: "0x0" }, { address: 0x52, reset: "0x0" }, { address: 0x53, reset: "0xF00" }, { address: 0x54, reset: "0x40" }, { address: 0x55, reset: "0x0" }, { address: 0x56, reset: "0x40" }, { address: 0x57, reset: "0xFF00" },
  { address: 0x58, reset: "0x3FF" }, { address: 0x59, reset: "0x0" }, { address: 0x5A, reset: "0x0" }, { address: 0x5B, reset: "0x0" }, { address: 0x5C, reset: "0x0" }, { address: 0x5D, reset: "0x1000" }, { address: 0x5E, reset: "0x0" }, { address: 0x5F, reset: "0x0" },
  { address: 0x60, reset: "0x17F8" }, { address: 0x61, reset: "0x0" }, { address: 0x62, reset: "0x1C80" }, { address: 0x63, reset: "0x19B9" }, { address: 0x64, reset: "0x533" }, { address: 0x65, reset: "0x3E8" }, { address: 0x66, reset: "0x28" }, { address: 0x67, reset: "0x14" },
  { address: 0x68, reset: "0x14" }, { address: 0x69, reset: "0xA" }, { address: 0x6A, reset: "0x0" }, { address: 0x6B, reset: "0x0" }, { address: 0x6C, reset: "0x0" }, { address: 0x6D, reset: "0x0" }, { address: 0x6E, reset: "0x1F" }, { address: 0x6F, reset: "0x0" },
  { address: 0x70, reset: "0xFFFF" }, { address: 0x71, reset: "0x0" }, { address: 0x72, reset: "0x0" }, { address: 0x73, reset: "0x0" }, { address: 0x74, reset: "0x0" }, { address: 0x75, reset: "0x0" }, { address: 0x76, reset: "0x0" }, { address: 0x77, reset: "0x0" },
  { address: 0x78, reset: "0x0" }, { address: 0x79, reset: "0x0" }, { address: 0x7A, reset: "0x0" },
];

function lmx2820Registers(): KnowledgeRegister[] {
  return [
    ticsFrameRegister(),
    ...LMX2820_REGISTER_ROWS.map((row) => ({
      name: `R${row.address}`,
      address: hexAddress(row.address, 2),
      width: "16",
      access: "RW",
      reset: row.reset,
      purpose: `LMX2820 SNAU251A register map girdisi R${row.address}; TICS Pro export bu 16-bit register image değerini üretir.`,
      fields: tiClockFields("LMX2820", hexAddress(row.address, 2), `R${row.address}`),
    })),
  ];
}

const adarBitValues = ["0: disabled / clear", "1: enabled / set"];
const adarReservedValues = ["0: normal kullanımda 0 yaz", "1: reserved; ADI guidance olmadan kullanma"];

type AdarRegisterRow = {
  name: string;
  address: number | string;
  width?: string;
  access: string;
  reset?: string;
  purpose: string;
  fields?: KnowledgeRegisterField[];
};

function adarReserved(bits: string): KnowledgeRegisterField {
  return {
    bits,
    name: "Reserved",
    meaning: "Datasheet tarafından application control alanı olarak tanımlanmamıştır; read-modify-write sırasında mevcut değer korunmalı veya 0 yazılmalıdır.",
    values: adarReservedValues,
  };
}

function adarIdentityFields(label: string): KnowledgeRegisterField[] {
  return [
    { bits: "D7:D0", name: label, meaning: `${label} kimlik byte'ıdır; cihaz tanıma ve sanity read için kullanılır.` },
  ];
}

function adarGainFields(direction: "RX" | "TX"): KnowledgeRegisterField[] {
  return [
    {
      bits: "D7",
      name: "CH_ATTN",
      meaning: `${direction} channel attenuator kontrol bitidir; VGA code ile birlikte channel gain/attenuation ayarını etkiler.`,
      values: ["0: attenuator bit clear", "1: attenuator bit set"],
    },
    {
      bits: "D6:D0",
      name: "VGA_GAIN[6:0]",
      meaning: `${direction} channel VGA gain/attenuation code alanıdır; beam calibration tablosundan gelen gain değeri buraya yazılır.`,
    },
  ];
}

function adarPhaseFields(direction: "RX" | "TX", axis: "I" | "Q"): KnowledgeRegisterField[] {
  return [
    {
      bits: "D5",
      name: "VM_POL",
      meaning: `${direction} channel vector modulator ${axis} kolunun polarity bitidir; 0/180 derece tarafını seçerek phase quadrant bilgisini taşır.`,
      values: ["0: positive polarity", "1: inverted polarity"],
    },
    {
      bits: "D4:D0",
      name: "VM_GAIN[4:0]",
      meaning: `${direction} channel vector modulator ${axis} kolunun gain code alanıdır; ADI phase table I/Q code çiftleri bu alanları birlikte ayarlar.`,
    },
    adarReserved("D7:D6"),
  ];
}

function adarChannelEnableFields(direction: "RX" | "TX"): KnowledgeRegisterField[] {
  return [
    { bits: "D6", name: "CH1_EN", meaning: `${direction} channel 1 RF path enable bitidir.`, values: adarBitValues },
    { bits: "D5", name: "CH2_EN", meaning: `${direction} channel 2 RF path enable bitidir.`, values: adarBitValues },
    { bits: "D4", name: "CH3_EN", meaning: `${direction} channel 3 RF path enable bitidir.`, values: adarBitValues },
    { bits: "D3", name: "CH4_EN", meaning: `${direction} channel 4 RF path enable bitidir.`, values: adarBitValues },
    {
      bits: "D2",
      name: direction === "RX" ? "RX_LNA_EN" : "TX_DRV_EN",
      meaning: direction === "RX" ? "RX LNA bias/enable yolunu açar." : "TX driver enable yolunu açar.",
      values: adarBitValues,
    },
    { bits: "D1", name: "VM_EN", meaning: `${direction} vector modulator enable bitidir.`, values: adarBitValues },
    { bits: "D0", name: "VGA_EN", meaning: `${direction} VGA enable bitidir.`, values: adarBitValues },
    adarReserved("D7"),
  ];
}

function adarBiasFields(label: string): KnowledgeRegisterField[] {
  return [
    { bits: "D7:D0", name: label, meaning: `${label} bias DAC/code değeridir; RF performans, sıcaklık ve board calibration sonucuna göre seçilmelidir.` },
  ];
}

function adarBeamPositionFields(): KnowledgeRegisterField[] {
  return [
    { bits: "B6:B0", name: "VGA_GAIN[6:0]", meaning: "Beam position içindeki channel VGA gain/attenuation code alanıdır." },
    { bits: "B7", name: "ATTENUATOR", meaning: "Beam position içinde channel attenuator bitidir.", values: ["0: attenuator bit clear", "1: attenuator bit set"] },
    { bits: "B12:B8", name: "VM_I_GAIN[4:0]", meaning: "Vector modulator I kolu gain code alanıdır." },
    { bits: "B13", name: "VM_I_POL", meaning: "Vector modulator I kolu polarity bitidir.", values: ["0: positive polarity", "1: inverted polarity"] },
    { bits: "B20:B16", name: "VM_Q_GAIN[4:0]", meaning: "Vector modulator Q kolu gain code alanıdır." },
    { bits: "B21", name: "VM_Q_POL", meaning: "Vector modulator Q kolu polarity bitidir.", values: ["0: positive polarity", "1: inverted polarity"] },
    adarReserved("B23:B22"),
  ];
}

function adarRxBiasRamFields(): KnowledgeRegisterField[] {
  return [
    { bits: "B7:B0", name: "EXT_LNA_OFF", meaning: "External LNA off-state bias code değeridir." },
    { bits: "B15:B8", name: "EXT_LNA_ON", meaning: "External LNA on-state bias code değeridir." },
    { bits: "B19:B16", name: "RX_VGA_BIAS", meaning: "RX VGA bias current code alanıdır." },
    { bits: "B22:B20", name: "RX_VM_BIAS", meaning: "RX vector modulator bias current code alanıdır." },
    { bits: "B27:B23", name: "RX_LNA_BIAS", meaning: "RX LNA bias current code alanıdır." },
    adarReserved("B31:B28"),
  ];
}

function adarTxBiasRamFields(): KnowledgeRegisterField[] {
  return [
    { bits: "B7:B0", name: "EXT_PA1_BIAS_OFF", meaning: "External PA1 off-state bias code değeridir." },
    { bits: "B15:B8", name: "EXT_PA2_BIAS_OFF", meaning: "External PA2 off-state bias code değeridir." },
    { bits: "B23:B16", name: "EXT_PA3_BIAS_OFF", meaning: "External PA3 off-state bias code değeridir." },
    { bits: "B31:B24", name: "EXT_PA1_BIAS_ON", meaning: "External PA1 on-state bias code değeridir." },
    { bits: "B39:B32", name: "EXT_PA2_BIAS_ON", meaning: "External PA2 on-state bias code değeridir." },
    { bits: "B47:B40", name: "EXT_PA3_BIAS_ON", meaning: "External PA3 on-state bias code değeridir." },
    { bits: "B55:B48", name: "EXT_PA4_BIAS_OFF", meaning: "External PA4 off-state bias code değeridir." },
    { bits: "B63:B56", name: "EXT_PA4_BIAS_ON", meaning: "External PA4 on-state bias code değeridir." },
    { bits: "B67:B64", name: "TX_VGA_BIAS", meaning: "TX VGA bias current code alanıdır." },
    { bits: "B70:B68", name: "TX_VM_BIAS", meaning: "TX vector modulator bias current code alanıdır." },
    { bits: "B74:B72", name: "TX_DRV_BIAS", meaning: "TX driver bias current code alanıdır." },
    adarReserved("B79:B75"),
  ];
}

function adar1000Fields(name: string): KnowledgeRegisterField[] {
  if (name === "INTERFACE_CONFIG_A") {
    return [
      { bits: "D7", name: "SOFTRESET", meaning: "1 yazıldığında digital register interface reset akışını tetikler.", values: ["0: reset yok", "1: soft reset request"] },
      { bits: "D6", name: "LSB_FIRST", meaning: "SPI bit sırasını seçer; Spec2Code ve datasheet default akışı MSB-first kabul eder.", values: ["0: MSB-first", "1: LSB-first"] },
      { bits: "D5", name: "ADDR_ASCN", meaning: "Multi-byte SPI erişimlerinde adres auto-increment yönünü kontrol eder.", values: ["0: normal/autodecrement default akışı", "1: ascending address mode"] },
      { bits: "D4", name: "SDOACTIVE", meaning: "SDO/readback driver davranışını etkinleştirir; 4-wire readback için gereklidir.", values: adarBitValues },
      { bits: "D3", name: "SDOACTIVE_", meaning: "SDOACTIVE alanının complement shadow bitidir; datasheet yazım pattern'inde birlikte kullanılır.", values: ["0: SDOACTIVE=1 için complement", "1: SDOACTIVE=0 için complement"] },
      { bits: "D2", name: "ADDR_ASCN_", meaning: "ADDR_ASCN complement shadow bitidir.", values: ["0: ADDR_ASCN=1 için complement", "1: ADDR_ASCN=0 için complement"] },
      { bits: "D1", name: "LSB_FIRST_", meaning: "LSB_FIRST complement shadow bitidir.", values: ["0: LSB_FIRST=1 için complement", "1: LSB_FIRST=0 için complement"] },
      { bits: "D0", name: "SOFTRESET_", meaning: "SOFTRESET complement shadow bitidir.", values: ["0: SOFTRESET=1 için complement", "1: SOFTRESET=0 için complement"] },
    ];
  }
  if (name === "INTERFACE_CONFIG_B") {
    return [
      { bits: "D7:D0", name: "Interface option bits", meaning: "SPI interface davranışına ait ek seçeneklerdir; default bring-up'ta değiştirilmemelidir." },
    ];
  }
  if (name === "DEV_CONFIG") {
    return [
      { bits: "D7:D0", name: "Device config bits", meaning: "Cihaz seviyesindeki digital configuration alanıdır; default akışta ADI referans ayarları korunmalıdır." },
    ];
  }
  if (["CHIP_TYPE", "PRODUCT_ID_H", "PRODUCT_ID_L", "SPI_REV", "VENDOR_ID_H", "VENDOR_ID_L", "REV_ID"].includes(name)) {
    return adarIdentityFields(name);
  }
  if (name === "SCRATCH_PAD") {
    return [
      { bits: "D7:D0", name: "SCRATCH", meaning: "SPI write/read sanity testi için kullanılan volatile scratch byte; örnek testlerde 0xAD/0xEA pattern'leri kullanılabilir." },
    ];
  }
  if (name === "TRANSFER_REG") {
    return [
      { bits: "D7:D0", name: "Transfer control", meaning: "Buffered/shadow register içeriklerinin active control alanlarına aktarımında kullanılan transfer kontrol byte'ıdır." },
    ];
  }
  const gain = /^CH[1-4]_(RX|TX)_GAIN$/.exec(name);
  if (gain) return adarGainFields(gain[1] as "RX" | "TX");

  const phase = /^CH[1-4]_(RX|TX)_PHASE_([IQ])$/.exec(name);
  if (phase) return adarPhaseFields(phase[1] as "RX" | "TX", phase[2] as "I" | "Q");

  if (name === "LD_WRK_REGS") {
    return [
      { bits: "D1", name: "LDTX_OVERRIDE", meaning: "TX load/work register override kontrolüdür.", values: adarBitValues },
      { bits: "D0", name: "LDRX_OVERRIDE", meaning: "RX load/work register override kontrolüdür.", values: adarBitValues },
      adarReserved("D7:D2"),
    ];
  }
  if (/^CH[1-4]_PA_BIAS_ON$/.test(name)) return adarBiasFields("PA_BIAS_ON");
  if (/^CH[1-4]_PA_BIAS_OFF$/.test(name)) return adarBiasFields("PA_BIAS_OFF");
  if (name === "LNA_BIAS_ON") return adarBiasFields("LNA_BIAS_ON");
  if (name === "LNA_BIAS_OFF") return adarBiasFields("LNA_BIAS_OFF");
  if (name === "RX_ENABLES") return adarChannelEnableFields("RX");
  if (name === "TX_ENABLES") return adarChannelEnableFields("TX");
  if (name === "MISC_ENABLES") {
    return [
      { bits: "D7", name: "SW_DRV_TR_MODE_SEL", meaning: "T/R switch driver mode seçimini etkiler.", values: adarBitValues },
      { bits: "D6", name: "BIAS_CTRL", meaning: "Bias control path seçimini belirler.", values: adarBitValues },
      { bits: "D5", name: "BIAS_EN", meaning: "Internal bias generator/control bloklarını enable eder.", values: adarBitValues },
      { bits: "D4", name: "LNA_BIAS_OUT_EN", meaning: "External LNA bias output enable bitidir.", values: adarBitValues },
      { bits: "D3", name: "CH1_DET_EN", meaning: "Channel 1 detector enable bitidir.", values: adarBitValues },
      { bits: "D2", name: "CH2_DET_EN", meaning: "Channel 2 detector enable bitidir.", values: adarBitValues },
      { bits: "D1", name: "CH3_DET_EN", meaning: "Channel 3 detector enable bitidir.", values: adarBitValues },
      { bits: "D0", name: "CH4_DET_EN", meaning: "Channel 4 detector enable bitidir.", values: adarBitValues },
    ];
  }
  if (name === "SW_CTRL") {
    return [
      { bits: "D7", name: "SW_DRV_TR_STATE", meaning: "T/R switch driver state kontrol bitidir.", values: adarBitValues },
      { bits: "D6", name: "TX_EN", meaning: "TX path global enable kontrolüdür.", values: adarBitValues },
      { bits: "D5", name: "RX_EN", meaning: "RX path global enable kontrolüdür.", values: adarBitValues },
      { bits: "D4", name: "SW_DRV_EN_TR", meaning: "T/R switch driver enable kaynağını T/R state ile ilişkilendirir.", values: adarBitValues },
      { bits: "D3", name: "SW_DRV_EN_POL", meaning: "Switch driver enable polarity seçimini yapar.", values: ["0: active-low style polarity", "1: active-high style polarity"] },
      { bits: "D2", name: "TR_SOURCE", meaning: "T/R kontrol kaynağını pin veya SPI tarafına yönlendirir.", values: ["0: external T/R control", "1: SPI controlled T/R path"] },
      { bits: "D1", name: "TR_SPI", meaning: "SPI üzerinden T/R state seçimini yapar.", values: ["0: RX side selected", "1: TX side selected"] },
      { bits: "D0", name: "POL", meaning: "External polarity/control yorumunu tersler.", values: ["0: non-inverted", "1: inverted"] },
    ];
  }
  if (name === "ADC_CTRL") {
    return [
      { bits: "D7", name: "ADC_CLKFREQ_SEL", meaning: "Aux ADC clock frequency seçimini yapar.", values: ["0: default ADC clock range", "1: alternate ADC clock range"] },
      { bits: "D6", name: "AC_EN", meaning: "Aux ADC analog circuit enable bitidir.", values: adarBitValues },
      { bits: "D5", name: "CLK_EN", meaning: "Aux ADC clock enable bitidir.", values: adarBitValues },
      { bits: "D4", name: "ST_CONV", meaning: "Aux ADC conversion başlatır.", values: ["0: conversion start yok", "1: conversion başlat"] },
      { bits: "D3:D1", name: "MUX_SEL[2:0]", meaning: "Aux ADC'nin ölçeceği internal/aux mux kanalını seçer." },
      { bits: "D0", name: "ADC_EOC", meaning: "Aux ADC conversion complete status bitidir; polling için kullanılır.", values: ["0: conversion devam ediyor", "1: conversion tamamlandı"] },
    ];
  }
  if (name === "ADC_OUTPUT") {
    return [
      { bits: "D7:D0", name: "ADC_OUTPUT", meaning: "Aux ADC conversion sonucu; önce ADC_EOC=1 görülmelidir." },
    ];
  }
  if (["BIAS_CURRENT_RX_LNA", "BIAS_CURRENT_RX", "BIAS_CURRENT_TX", "BIAS_CURRENT_TX_DRV"].includes(name)) {
    return adarBiasFields(name);
  }
  if (name === "MEM_CTRL") {
    return [
      { bits: "D7", name: "SCAN_MODE_EN", meaning: "Beam RAM üzerinden scan mode akışını enable eder.", values: adarBitValues },
      { bits: "D6", name: "BEAM_RAM_BYPASS", meaning: "Beam RAM bypass edilirse active beam değerleri doğrudan work register'lardan gelir.", values: ["0: beam RAM aktif olabilir", "1: beam RAM bypass"] },
      { bits: "D5", name: "BIAS_RAM_BYPASS", meaning: "Bias RAM bypass edilirse bias değerleri doğrudan register'lardan gelir.", values: ["0: bias RAM aktif olabilir", "1: bias RAM bypass"] },
      { bits: "D3", name: "TX_BEAM_STEP_EN", meaning: "TX beam step sequencer enable bitidir.", values: adarBitValues },
      { bits: "D2", name: "RX_BEAM_STEP_EN", meaning: "RX beam step sequencer enable bitidir.", values: adarBitValues },
      { bits: "D1", name: "TX_CHX_RAM_BYPASS", meaning: "TX channel RAM fetch path bypass bitidir.", values: adarBitValues },
      { bits: "D0", name: "RX_CHX_RAM_BYPASS", meaning: "RX channel RAM fetch path bypass bitidir.", values: adarBitValues },
      adarReserved("D4"),
    ];
  }
  if (name === "RX_CHX_MEM" || name === "TX_CHX_MEM" || /^R[XT]_CH[1-4]_MEM$/.test(name)) {
    return [
      { bits: "D7", name: "CHX_RAM_FETCH", meaning: "Set edildiğinde seçili beam position bilgisini RAM'den ilgili channel work register'larına çeker.", values: ["0: fetch yok", "1: RAM fetch request"] },
      { bits: "D6:D0", name: "BEAM_POSITION[6:0]", meaning: "RAM içindeki beam position index değeridir; ADI driver ve datasheet 0..120 aralığını kullanır.", values: ["0..120: geçerli beam position", "121..127: kullanma"] },
    ];
  }
  if (name === "TX_TO_RX_DELAY_CTRL" || name === "RX_TO_TX_DELAY_CTRL") {
    return [
      { bits: "D7:D4", name: "DELAY1[3:0]", meaning: "T/R geçiş sekansındaki ilk delay code alanıdır." },
      { bits: "D3:D0", name: "DELAY2[3:0]", meaning: "T/R geçiş sekansındaki ikinci delay code alanıdır." },
    ];
  }
  if (/_BEAM_STEP_(START|STOP)$/.test(name)) {
    return [
      { bits: "D6:D0", name: "BEAM_STEP_INDEX[6:0]", meaning: "Scan sequencer start/stop beam position index değeridir; normal aralık 0..120 olmalıdır.", values: ["0..120: geçerli beam position", "121..127: kullanma"] },
      adarReserved("D7"),
    ];
  }
  if (name === "RX_BIAS_RAM_CTL" || name === "TX_BIAS_RAM_CTL") {
    return [
      { bits: "D3", name: "BIAS_RAM_FETCH", meaning: "Set edildiğinde seçili bias setting RAM'den active bias register'larına çekilir.", values: ["0: fetch yok", "1: bias RAM fetch request"] },
      { bits: "D2:D0", name: "BIAS_SETTING_INDEX[2:0]", meaning: "RAM içindeki bias setting index değeridir; ADI driver 1..7 aralığını kullanır.", values: ["1..7: geçerli bias setting", "0: kullanma / default dışı"] },
      adarReserved("D7:D4"),
    ];
  }
  if (name === "LDO_TRIM_CTL_0" || name === "LDO_TRIM_CTL_1") {
    return [
      { bits: "D1:D0", name: "LDO_TRIM_SEL[1:0]", meaning: "Internal LDO trim select alanıdır; üretim/factory trim dışı kullanımda değiştirilmemelidir." },
      adarReserved("D7:D2"),
    ];
  }
  if (name === "RAM_RX_BEAM_POSITION" || name === "RAM_TX_BEAM_POSITION") return adarBeamPositionFields();
  if (name === "RAM_RX_BIAS_SETTING") return adarRxBiasRamFields();
  if (name === "RAM_TX_BIAS_SETTING") return adarTxBiasRamFields();

  return [
    { bits: "D7:D0", name, meaning: `${name} register image alanıdır; ADAR1000 init ve bring-up sırasında datasheet sırasına göre yazılır/okunur.` },
  ];
}

function adarSpiFrameRegister(): KnowledgeRegister {
  return {
    name: "SPI_24BIT_FRAME",
    address: "word",
    width: "24",
    access: "RW",
    purpose: "ADAR1000 SPI transaction formatı; her register erişimi 24-bit word olarak clocklanır.",
    fields: [
      { bits: "Word[23]", name: "R/W", meaning: "SPI erişim yönünü seçer.", values: ["0: write", "1: read"] },
      { bits: "Word[22:21]", name: "ADDR[14:13]", meaning: "Aynı CS hattında dört ADAR1000'e kadar device address seçimi için kullanılır." },
      { bits: "Word[20:8]", name: "REG_ADDR[12:0]", meaning: "Register/RAM adresinin alt 13 bitidir." },
      { bits: "Word[7:0]", name: "DATA[7:0]", meaning: "Write sırasında yazılan data byte; read sırasında dummy byte clocklanırken MISO/SDO data üretir." },
    ],
  };
}

const ADAR1000_REGISTER_ROWS: AdarRegisterRow[] = [
  { name: "INTERFACE_CONFIG_A", address: 0x000, access: "RW", reset: "0x00", purpose: "SPI interface reset, bit order, address increment ve SDO/readback davranışı." },
  { name: "INTERFACE_CONFIG_B", address: 0x001, access: "RW", reset: "0x00", purpose: "SPI interface ek configuration alanı; default durumda korunmalıdır." },
  { name: "DEV_CONFIG", address: 0x002, access: "RW", reset: "0x00", purpose: "Device-level digital configuration alanı." },
  { name: "CHIP_TYPE", address: 0x003, access: "RO", reset: "0x00", purpose: "Cihaz tipi kimlik byte'ı." },
  { name: "PRODUCT_ID_H", address: 0x004, access: "RO", reset: "0x00", purpose: "Product ID üst byte." },
  { name: "PRODUCT_ID_L", address: 0x005, access: "RO", reset: "0x00", purpose: "Product ID alt byte." },
  { name: "SCRATCH_PAD", address: 0x00A, access: "RW", reset: "0x00", purpose: "SPI write/read sanity testi için scratch register." },
  { name: "SPI_REV", address: 0x00B, access: "RO", reset: "0x00", purpose: "SPI/register interface revision bilgisi." },
  { name: "VENDOR_ID_H", address: 0x00C, access: "RO", reset: "0x00", purpose: "Vendor ID üst byte." },
  { name: "VENDOR_ID_L", address: 0x00D, access: "RO", reset: "0x00", purpose: "Vendor ID alt byte." },
  { name: "TRANSFER_REG", address: 0x00F, access: "RW", reset: "0x00", purpose: "Shadow/work register transfer kontrolü." },
  ...Array.from({ length: 4 }, (_, index) => ({
    name: `CH${index + 1}_RX_GAIN`,
    address: 0x010 + index,
    access: "RW",
    reset: "0x00",
    purpose: `RX channel ${index + 1} VGA gain ve attenuator control register'ı.`,
  })),
  ...Array.from({ length: 4 }, (_, index) => ([
    { name: `CH${index + 1}_RX_PHASE_I`, address: 0x014 + index * 2, access: "RW", reset: "0x00", purpose: `RX channel ${index + 1} vector modulator I gain/polarity register'ı.` },
    { name: `CH${index + 1}_RX_PHASE_Q`, address: 0x015 + index * 2, access: "RW", reset: "0x00", purpose: `RX channel ${index + 1} vector modulator Q gain/polarity register'ı.` },
  ])).flat(),
  ...Array.from({ length: 4 }, (_, index) => ({
    name: `CH${index + 1}_TX_GAIN`,
    address: 0x01C + index,
    access: "RW",
    reset: "0x00",
    purpose: `TX channel ${index + 1} VGA gain ve attenuator control register'ı.`,
  })),
  ...Array.from({ length: 4 }, (_, index) => ([
    { name: `CH${index + 1}_TX_PHASE_I`, address: 0x020 + index * 2, access: "RW", reset: "0x00", purpose: `TX channel ${index + 1} vector modulator I gain/polarity register'ı.` },
    { name: `CH${index + 1}_TX_PHASE_Q`, address: 0x021 + index * 2, access: "RW", reset: "0x00", purpose: `TX channel ${index + 1} vector modulator Q gain/polarity register'ı.` },
  ])).flat(),
  { name: "LD_WRK_REGS", address: 0x028, access: "WO", reset: "0x00", purpose: "Load/work register override kontrolü." },
  ...Array.from({ length: 4 }, (_, index) => ({ name: `CH${index + 1}_PA_BIAS_ON`, address: 0x029 + index, access: "RW", reset: "0x00", purpose: `TX external PA channel ${index + 1} on-state bias code.` })),
  { name: "LNA_BIAS_ON", address: 0x02D, access: "RW", reset: "0x00", purpose: "RX external LNA on-state bias code." },
  { name: "RX_ENABLES", address: 0x02E, access: "RW", reset: "0x00", purpose: "RX channel, LNA, VM ve VGA enable register'ı." },
  { name: "TX_ENABLES", address: 0x02F, access: "RW", reset: "0x00", purpose: "TX channel, driver, VM ve VGA enable register'ı." },
  { name: "MISC_ENABLES", address: 0x030, access: "RW", reset: "0x00", purpose: "Bias, detector ve switch-driver yardımcı enable alanları." },
  { name: "SW_CTRL", address: 0x031, access: "RW", reset: "0x00", purpose: "TX/RX switch, SPI controlled T/R state ve polarity control register'ı." },
  { name: "ADC_CTRL", address: 0x032, access: "RW", reset: "0x00", purpose: "Internal auxiliary ADC clock, mux, start-conversion ve EOC status register'ı." },
  { name: "ADC_OUTPUT", address: 0x033, access: "RO", reset: "0x00", purpose: "Internal auxiliary ADC conversion result byte." },
  { name: "BIAS_CURRENT_RX_LNA", address: 0x034, access: "RW", reset: "0x00", purpose: "RX LNA bias current code." },
  { name: "BIAS_CURRENT_RX", address: 0x035, access: "RW", reset: "0x00", purpose: "RX path bias current code." },
  { name: "BIAS_CURRENT_TX", address: 0x036, access: "RW", reset: "0x00", purpose: "TX path bias current code." },
  { name: "BIAS_CURRENT_TX_DRV", address: 0x037, access: "RW", reset: "0x00", purpose: "TX driver bias current code." },
  { name: "MEM_CTRL", address: 0x038, access: "RW", reset: "0x00", purpose: "Beam RAM, bias RAM, scan mode ve channel RAM bypass/fetch path kontrolü." },
  { name: "RX_CHX_MEM", address: 0x039, access: "RW", reset: "0x00", purpose: "RX tüm channel'lar için ortak beam RAM fetch/index register'ı." },
  { name: "TX_CHX_MEM", address: 0x03A, access: "RW", reset: "0x00", purpose: "TX tüm channel'lar için ortak beam RAM fetch/index register'ı." },
  ...Array.from({ length: 4 }, (_, index) => ({ name: `RX_CH${index + 1}_MEM`, address: 0x03D + index, access: "RW", reset: "0x00", purpose: `RX channel ${index + 1} için beam RAM fetch/index register'ı.` })),
  ...Array.from({ length: 4 }, (_, index) => ({ name: `TX_CH${index + 1}_MEM`, address: 0x041 + index, access: "RW", reset: "0x00", purpose: `TX channel ${index + 1} için beam RAM fetch/index register'ı.` })),
  { name: "REV_ID", address: 0x045, access: "RO", reset: "0x00", purpose: "Silicon revision ID byte." },
  ...Array.from({ length: 4 }, (_, index) => ({ name: `CH${index + 1}_PA_BIAS_OFF`, address: 0x046 + index, access: "RW", reset: "0x00", purpose: `TX external PA channel ${index + 1} off-state bias code.` })),
  { name: "LNA_BIAS_OFF", address: 0x04A, access: "RW", reset: "0x00", purpose: "RX external LNA off-state bias code." },
  { name: "TX_TO_RX_DELAY_CTRL", address: 0x04B, access: "RW", reset: "0x00", purpose: "TX'ten RX'e geçişte switch/bias timing delay code alanları." },
  { name: "RX_TO_TX_DELAY_CTRL", address: 0x04C, access: "RW", reset: "0x00", purpose: "RX'ten TX'e geçişte switch/bias timing delay code alanları." },
  { name: "TX_BEAM_STEP_START", address: 0x04D, access: "RW", reset: "0x00", purpose: "TX scan sequencer start beam position index'i." },
  { name: "TX_BEAM_STEP_STOP", address: 0x04E, access: "RW", reset: "0x00", purpose: "TX scan sequencer stop beam position index'i." },
  { name: "RX_BEAM_STEP_START", address: 0x04F, access: "RW", reset: "0x00", purpose: "RX scan sequencer start beam position index'i." },
  { name: "RX_BEAM_STEP_STOP", address: 0x050, access: "RW", reset: "0x00", purpose: "RX scan sequencer stop beam position index'i." },
  { name: "RX_BIAS_RAM_CTL", address: 0x051, access: "RW", reset: "0x00", purpose: "RX bias RAM setting index ve fetch kontrolü." },
  { name: "TX_BIAS_RAM_CTL", address: 0x052, access: "RW", reset: "0x00", purpose: "TX bias RAM setting index ve fetch kontrolü." },
  { name: "LDO_TRIM_CTL_0", address: 0x400, access: "RW", reset: "0x00", purpose: "Internal LDO trim control; normal firmware flow içinde değiştirilmemelidir." },
  { name: "LDO_TRIM_CTL_1", address: 0x401, access: "RW", reset: "0x00", purpose: "Internal LDO trim control; normal firmware flow içinde değiştirilmemelidir." },
  { name: "RAM_RX_BEAM_POSITION", address: "0x1000 + (position << 4) + channel*4 + byte[0..2]", width: "24", access: "RW", purpose: "RX beam RAM position image; 121 position x 4 channel için VGA/VM I/VM Q kodlarını tutar.", fields: adarBeamPositionFields() },
  { name: "RAM_TX_BEAM_POSITION", address: "0x1800 + (position << 4) + channel*4 + byte[0..2]", width: "24", access: "RW", purpose: "TX beam RAM position image; 121 position x 4 channel için VGA/VM I/VM Q kodlarını tutar.", fields: adarBeamPositionFields() },
  { name: "RAM_RX_BIAS_SETTING", address: "0x1780 + (setting << 4) + bias byte offsets", width: "32", access: "RW", purpose: "RX bias RAM setting image; external LNA ve RX bias kodlarını tutar.", fields: adarRxBiasRamFields() },
  { name: "RAM_TX_BIAS_SETTING", address: "0x1F80 + (setting << 4) + bias byte offsets", width: "80", access: "RW", purpose: "TX bias RAM setting image; external PA ve TX bias kodlarını tutar.", fields: adarTxBiasRamFields() },
];

function adar1000Registers(): KnowledgeRegister[] {
  return [
    adarSpiFrameRegister(),
    ...ADAR1000_REGISTER_ROWS.map((row) => ({
      name: row.name,
      address: typeof row.address === "number" ? hexAddress(row.address, row.address > 0xFF ? 3 : 2) : row.address,
      width: row.width ?? "8",
      access: row.access,
      reset: row.reset,
      purpose: row.purpose,
      fields: row.fields ?? adar1000Fields(row.name),
    })),
  ];
}

function adar1000RegisterTransfers(reg: KnowledgeRegister): KnowledgeRegisterTransfer[] {
  if (reg.name === "SPI_24BIT_FRAME") {
    return [
      {
        title: "SPI write frame",
        access: "WRITE",
        txBytes: "3 byte",
        rxBytes: "0 byte",
        tx: ["R/W=0 + A14:A0 + D7:D0"],
        rx: ["-"],
        code: ["adar1000DeviceInit(spSpi);"],
        note: "Generated init register_words array'indeki her word'u bu 24-bit formatta gönderir.",
      },
      {
        title: "SPI read frame",
        access: "READ",
        txBytes: "3 byte",
        rxBytes: "1 byte",
        tx: ["R/W=1 + A14:A0 + 0x00"],
        rx: ["D7:D0"],
        code: ["/* Readback helper eklenirse aynı 24-bit frame R/W=1 ile kullanılır. */"],
        note: "Readback için SDO/SDIO bağlantısı ve INTERFACE_CONFIG_A.SDOACTIVE davranışı board topolojisine göre doğrulanmalıdır.",
      },
    ];
  }

  const access = reg.access.toUpperCase();
  const macro = regMacro("ADAR1000", reg.name);
  const addressLabel = reg.address;
  const transfers: KnowledgeRegisterTransfer[] = [];

  if (access.includes("R")) {
    transfers.push({
      title: "SPI register read",
      access: "READ",
      txBytes: "3 byte",
      rxBytes: "1 byte",
      tx: [`R/W=1 + A14:A0 (${addressLabel}) + 0x00`],
      rx: ["ucValue / D7:D0"],
      code: [`adar1000RegisterRead(spSpi, ${macro}, &ucValue);`],
      note: "Catalog formatı register-level helper mantığını gösterir; generated init şu anda register_words array'ini yazar.",
    });
  }

  if (access.includes("W")) {
    transfers.push({
      title: "SPI register write",
      access: "WRITE",
      txBytes: "3 byte",
      rxBytes: "0 byte",
      tx: [`R/W=0 + A14:A0 (${addressLabel}) + ucValue`],
      rx: ["-"],
      code: [`adar1000RegisterWrite(spSpi, ${macro}, ucValue);`],
      note: reg.name.startsWith("RAM_")
        ? "RAM adresi position/channel/setting parametrelerinden hesaplanmalıdır; beam/bias image power-up sonrası yeniden yüklenmelidir."
        : undefined,
    });
  }

  return transfers;
}

function tmp101TemperatureFields(prefix: string): KnowledgeRegisterField[] {
  return [
    { bits: "Byte1 D7:D0", name: `${prefix}[11:4]`, meaning: "12-bit two's-complement sıcaklık/threshold kodunun üst sekiz biti." },
    { bits: "Byte2 D7:D4", name: `${prefix}[3:0]`, meaning: "12-bit sıcaklık/threshold kodunun alt dört biti." },
    { bits: "Byte2 D3:D0", name: "ZERO_PAD", meaning: "Datasheet formatında 0 okunur/yazılır; sıcaklık hesabına dahil edilmez.", values: ["0000: normal", "diğer: kullanma / ignore"] },
  ];
}

function tmp101Registers(): KnowledgeRegister[] {
  return [
    {
      name: "TEMPERATURE",
      address: "0x00",
      width: "16",
      access: "RO",
      reset: "0x0000",
      purpose: "Son conversion sonucunu 12-bit two's-complement sıcaklık kodu olarak verir.",
      fields: tmp101TemperatureFields("TEMP"),
    },
    {
      name: "CONFIGURATION",
      address: "0x01",
      width: "8",
      access: "RW",
      reset: "0x00; OS/ALERT readback power-up sonrası 1 olabilir",
      purpose: "Shutdown, one-shot, resolution, fault queue, ALERT polarity ve thermostat mode ayarları.",
      fields: [
        {
          bits: "D7",
          name: "OS_ALERT",
          meaning: "Write tarafında shutdown modundayken one-shot conversion başlatır; read tarafında comparator status/ALERT durumunu bildirir.",
          values: [
            "write 0: one-shot başlatma yok",
            "write 1: SD=1 iken tek conversion başlat",
            "read POL=0: 1 normal, 0 THIGH fault aktif",
            "read POL=1: okunan polarite terslenir",
          ],
        },
        {
          bits: "D6:D5",
          name: "R[1:0]",
          meaning: "ADC resolution ve tipik conversion time seçimi.",
          values: ["00: 9 bit, 0.5 C, 40 ms", "01: 10 bit, 0.25 C, 80 ms", "10: 11 bit, 0.125 C, 160 ms", "11: 12 bit, 0.0625 C, 320 ms"],
        },
        {
          bits: "D4:D3",
          name: "F[1:0]",
          meaning: "ALERT üretmeden önce gereken ardışık fault measurement sayısı.",
          values: ["00: 1 fault", "01: 2 fault", "10: 4 fault", "11: 6 fault"],
        },
        { bits: "D2", name: "POL", meaning: "TMP101 ALERT pininin aktif seviyesini seçer.", values: ["0: active low", "1: active high"] },
        { bits: "D1", name: "TM", meaning: "Thermostat mode seçimi.", values: ["0: comparator mode", "1: interrupt mode; alert read/SMBus alert ile clear edilir"] },
        { bits: "D0", name: "SD", meaning: "Shutdown mode kontrolü.", values: ["0: continuous conversion", "1: shutdown; serial interface açık kalır"] },
      ],
    },
    {
      name: "TLOW",
      address: "0x02",
      width: "16",
      access: "RW",
      reset: "0x4B00",
      purpose: "ALERT alt eşik değeri; power-up default 75 C.",
      fields: tmp101TemperatureFields("L"),
    },
    {
      name: "THIGH",
      address: "0x03",
      width: "16",
      access: "RW",
      reset: "0x5000",
      purpose: "ALERT üst eşik değeri; power-up default 80 C.",
      fields: tmp101TemperatureFields("H"),
    },
  ];
}

const sht21MeasurementFields = (label: string): KnowledgeRegisterField[] => [
  { bits: "Byte0 D7:D0", name: `${label}[15:8]`, meaning: "Ham ölçüm sonucunun MSB byte'ı." },
  { bits: "Byte1 D7:D2", name: `${label}[7:2]`, meaning: "Ham ölçüm sonucunun alt data bitleri; fiziksel değere çevirmeden önce status bitleri temizlenmelidir." },
  { bits: "Byte1 D1", name: "MEAS_TYPE", meaning: "Ölçüm tipini bildirir.", values: ["0: temperature", "1: humidity"] },
  { bits: "Byte1 D0", name: "STATUS_RESERVED", meaning: "Şu an atanmış değildir; fiziksel hesapta 0 kabul edilmelidir.", values: ["0: normal", "1: reserved / hesapta temizle"] },
  { bits: "Byte2 D7:D0", name: "CRC8", meaning: "MSB ve LSB/status byte'ları için CRC-8 checksum; polynomial x8 + x5 + x4 + 1." },
];

function sht21Registers(): KnowledgeRegister[] {
  return [
    {
      name: "TRIGGER_T_HOLD",
      address: "0xE3",
      width: "24",
      access: "RO",
      purpose: "Hold-master temperature measurement komutu; sensör ölçüm boyunca SCL hattını tutabilir.",
      fields: sht21MeasurementFields("T_RAW"),
    },
    {
      name: "TRIGGER_RH_HOLD",
      address: "0xE5",
      width: "24",
      access: "RO",
      purpose: "Hold-master relative humidity measurement komutu; sensör ölçüm boyunca SCL hattını tutabilir.",
      fields: sht21MeasurementFields("RH_RAW"),
    },
    {
      name: "TRIGGER_T_NO_HOLD",
      address: "0xF3",
      width: "24",
      access: "RO",
      purpose: "No-hold temperature measurement komutu; master ölçüm bitene kadar read address ile ACK polling yapar.",
      fields: sht21MeasurementFields("T_RAW"),
    },
    {
      name: "TRIGGER_RH_NO_HOLD",
      address: "0xF5",
      width: "24",
      access: "RO",
      purpose: "No-hold relative humidity measurement komutu; master ölçüm bitene kadar read address ile ACK polling yapar.",
      fields: sht21MeasurementFields("RH_RAW"),
    },
    {
      name: "USER_REGISTER",
      address: "read 0xE7 / write 0xE6",
      width: "8",
      access: "RW",
      reset: "0x02",
      purpose: "Measurement resolution, end-of-battery flag, heater ve OTP reload davranışını taşır.",
      fields: [
        { bits: "D7,D0", name: "RES[1:0]", meaning: "Measurement resolution seçimi.", values: ["00: RH 12 bit / T 14 bit", "01: RH 8 bit / T 12 bit", "10: RH 10 bit / T 13 bit", "11: RH 11 bit / T 11 bit"] },
        { bits: "D6", name: "END_OF_BATTERY", meaning: "Besleme seviyesi düşük flag'i; measurement sonrasında güncellenir.", values: ["0: VDD > 2.25 V", "1: VDD < 2.25 V"] },
        { bits: "D5:D3", name: "RESERVED", meaning: "Reserved bitlerdir; user register yazmadan önce mevcut değer okunup korunmalıdır." },
        { bits: "D2", name: "HEATER", meaning: "On-chip heater diagnostic amaçlı enable edilir.", values: ["0: heater off", "1: heater on"] },
        { bits: "D1", name: "OTP_RELOAD_DISABLE", meaning: "OTP reload güvenlik davranışını kontrol eder.", values: ["0: her measurement öncesi OTP reload aktif", "1: OTP reload disabled; önerilen default değildir"] },
      ],
    },
    {
      name: "SOFT_RESET",
      address: "0xFE",
      width: "0",
      access: "WO",
      purpose: "Sensörü power cycle olmadan yeniden başlatır; işlem 15 ms'den kısa sürer.",
      fields: [{ bits: "Command", name: "0xFE", meaning: "Soft reset command byte'ıdır; data payload yoktur." }],
    },
  ];
}

function lc32aRegisters(): KnowledgeRegister[] {
  return [
    {
      name: "CONTROL_BYTE",
      address: "1010 A2 A1 A0 R/W",
      width: "8",
      access: "RW",
      purpose: "I2C control byte formatı; A2:A0 strap pinleri slave address'i seçer.",
      fields: [
        { bits: "B7:B4", name: "CONTROL_CODE", meaning: "24XX32A EEPROM ailesi için sabit device type kodu.", values: ["1010: EEPROM access"] },
        { bits: "B3:B1", name: "CHIP_SELECT A2:A0", meaning: "A2/A1/A0 pin seviyeleriyle eşleşmelidir; aynı bus üzerinde sekiz cihaza kadar seçim sağlar." },
        { bits: "B0", name: "R_W", meaning: "Transfer yönünü seçer.", values: ["0: write", "1: read"] },
      ],
    },
    {
      name: "WORD_ADDRESS",
      address: "A11:A0",
      width: "16 transfer / 12 effective",
      access: "W",
      purpose: "Okuma/yazma için memory byte adresi; high address byte içindeki üst dört bit don't-care.",
      fields: [
        { bits: "High byte B7:B4", name: "DONT_CARE", meaning: "Cihaz sadece A11:A0 adres alanını kullanır; üst dört bit don't-care kabul edilir." },
        { bits: "High byte B3:B0", name: "A11:A8", meaning: "4 Kbyte memory array adresinin üst dört biti." },
        { bits: "Low byte B7:B0", name: "A7:A0", meaning: "Memory byte adresinin alt sekiz biti." },
      ],
    },
    {
      name: "CURRENT_ADDRESS_READ",
      address: "internal pointer",
      width: "8",
      access: "RO",
      purpose: "Internal address pointer'ın gösterdiği sonraki byte'ı okur; önceki erişimden sonra pointer otomatik artar.",
      fields: [{ bits: "D7:D0", name: "DATA", meaning: "EEPROM'dan okunan data byte." }],
    },
    {
      name: "RANDOM_READ",
      address: "word address + repeated start",
      width: "8",
      access: "RO",
      purpose: "Önce word address yazılır, repeated start sonrası read control byte ile hedef byte okunur.",
      fields: [{ bits: "D7:D0", name: "DATA", meaning: "Seçilen memory adresinden okunan data byte." }],
    },
    {
      name: "SEQUENTIAL_READ",
      address: "word address + N bytes",
      width: "8 x N",
      access: "RO",
      purpose: "Random read gibi başlar; master ACK verdikçe EEPROM sonraki adresleri gönderir ve 0xFFF sonrası 0x000'a döner.",
      fields: [{ bits: "D7:D0", name: "DATA[n]", meaning: "Ardışık EEPROM data byte'ları." }],
    },
    {
      name: "BYTE_WRITE",
      address: "word address + 1 data",
      width: "8",
      access: "WO",
      purpose: "Tek EEPROM byte'ı yazar; STOP sonrası internal write cycle başlar.",
      fields: [{ bits: "D7:D0", name: "DATA", meaning: "Programlanacak tek EEPROM byte'ı." }],
    },
    {
      name: "PAGE_WRITE",
      address: "word address + 1..32 data",
      width: "8 x 1..32",
      access: "WO",
      purpose: "Aynı physical page içinde en fazla 32 byte yazar; page boundary aşılırsa data aynı page başına wrap eder.",
      fields: [
        { bits: "A4:A0", name: "PAGE_OFFSET", meaning: "32-byte page içindeki byte offset; write sırasında internal counter artar." },
        { bits: "D7:D0", name: "DATA[n]", meaning: "Page buffer'a alınan data byte'ları." },
      ],
    },
    {
      name: "ACK_POLL",
      address: "control byte write",
      width: "0",
      access: "RO",
      purpose: "Internal write cycle sırasında cihaz ACK vermez; ACK tekrar gelince sonraki operasyon güvenlidir.",
      fields: [{ bits: "ACK", name: "WRITE_CYCLE_DONE", meaning: "Control byte write denemesi ACK alıyorsa internal write cycle bitmiştir.", values: ["NACK: write cycle devam ediyor", "ACK: cihaz hazır"] }],
    },
  ];
}

const PACKS: Record<string, DeviceKnowledgePack> = {
  ADAR1000: {
    part: "ADAR1000",
    reviewedAt: "2026-06-29",
    scope: "4-channel X/Ku-band beamforming, RX/TX gain/phase, RAM beam table, bias RAM ve SPI bring-up.",
    sources: [
      {
        label: "Analog Devices ADAR1000 product page",
        url: "https://www.analog.com/en/products/adar1000.html",
      },
      {
        label: "Analog Devices ADAR1000 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ADAR1000.pdf",
      },
      {
        label: "Analog Devices ADAR1000 Linux driver",
        url: "https://github.com/analogdevicesinc/linux/blob/main/drivers/iio/beamformer/adar1000.c",
      },
    ],
    overview:
      "4 kanal X-band/Ku-band beamformer entegresidir. Her channel için RX/TX tarafında VGA gain, vector modulator I/Q gain-polarity, bias control, beam RAM position ve T/R switch control alanları vardır. Spec2Code bu cihazda beam synthesis yapmaz; doğrulanmış register word array'ini ve catalog içindeki register/RAM bilgisini firmware bring-up için kullanır.",
    keyFacts: [
      "SPI erişimi 24-bit word formatındadır: R/W biti, 15-bit adres ve 8-bit data alanı MSB-first gönderilir.",
      "A14:A13 alanı aynı chip-select hattında birden fazla ADAR1000 kullanıldığında device address seçimi için kullanılır.",
      "Write için R/W=0, read için R/W=1 kullanılır; readback tarafında SDO/SDIO bağlantısı ve SDOACTIVE configuration board topolojisine göre doğrulanmalıdır.",
      "RX/TX gain ve phase ayarı channel başına ayrıdır; phase için I/Q vector modulator gain-polarity code çiftleri birlikte değerlendirilmelidir.",
      "Beam RAM position aralığı 0..120, bias RAM setting aralığı 1..7 olarak ele alınmalıdır.",
    ],
    configuration: [
      "Bring-up için önce SPI sanity read/write yap: SCRATCH_PAD register'ına test pattern yazıp readback yap.",
      "TX/RX path enable etmeden önce bias current, PA/LNA bias ve switch control değerleri board RF tasarımıyla uyumlu olmalıdır.",
      "Beam RAM kullanılıyorsa tüm position table power-up sonrası explicit yüklenmeli; RAM içeriği kalıcı kabul edilmemelidir.",
      "Scan mode veya RAM fetch kullanılıyorsa MEM_CTRL, CHx_MEM ve BIAS_RAM_CTL register'ları aynı state machine mantığında yönetilmelidir.",
    ],
    registers: adar1000Registers(),
    recipes: [
      {
        title: "SPI sanity check",
        goal: "ADAR1000 register interface'in doğru çalıştığını doğrulamak.",
        steps: [
          "INTERFACE_CONFIG_A içindeki SDO/readback davranışını board SPI topolojisine göre ayarla.",
          "SCRATCH_PAD register'ına 0xAD yaz ve readback ile aynı değeri oku.",
          "Aynı testi 0xEA gibi ikinci bir pattern ile tekrar ederek stuck-at durumlarını ayıkla.",
        ],
      },
      {
        title: "Tek channel RX path açma",
        goal: "Channel 1 üzerinde kontrollü RX ölçümü başlatmak.",
        steps: [
          "BIAS_CURRENT_RX_LNA, BIAS_CURRENT_RX ve LNA_BIAS_ON değerlerini RF tasarımına göre yaz.",
          "CH1_RX_GAIN, CH1_RX_PHASE_I ve CH1_RX_PHASE_Q değerlerini doğrulanmış calibration tablosundan yaz.",
          "RX_ENABLES içinde CH1_EN, RX_LNA_EN, VM_EN ve VGA_EN bitlerini set et.",
          "SW_CTRL ile RX path'i seç ve RF ölçümü önce düşük riskli power seviyesinde yap.",
        ],
      },
      {
        title: "Beam RAM position yükleme",
        goal: "Bir beam position için tüm channel gain/phase değerlerini RAM'e almak.",
        steps: [
          "RX veya TX RAM base adresini seç: RX için 0x1000, TX için 0x1800.",
          "Her channel için 3 byte beam image yaz: VGA gain/attenuator, VM I gain/polarity, VM Q gain/polarity.",
          "MEM_CTRL içinde ilgili RAM bypass bitlerini temizle.",
          "CHx_MEM veya CHX_MEM üzerinden position index ve CHX_RAM_FETCH bitini kullanarak değerleri work register'lara çek.",
        ],
      },
      {
        title: "Aux ADC okuma",
        goal: "Internal auxiliary ADC sonucunu firmware ile almak.",
        steps: [
          "ADC_CTRL içinde AC_EN, CLK_EN, MUX_SEL ve ST_CONV alanlarını yaz.",
          "ADC_CTRL.ADC_EOC biti 1 olana kadar timeout'lu poll yap.",
          "ADC_OUTPUT register'ını oku ve işlem bittiğinde ADC_CTRL değerini temizle.",
        ],
      },
    ],
    gotchas: [
      "Readback 3-wire/4-wire SPI topolojisine bağlıdır; SDOACTIVE yanlış bırakılırsa bus contention veya sürekli high-Z görülebilir.",
      "Channel enable bitlerini bias ve switch state kurulmadan açmak RF path üzerinde istenmeyen transient üretebilir.",
      "Beam RAM ve bias RAM kalıcı storage değildir; deterministic init akışı bunları her power-up sonrası yeniden yüklemelidir.",
      "LDO trim ve reserved alanlar normal firmware tuning alanı değildir; ADI guidance olmadan değiştirilmeyecek kabul edilmelidir.",
      "Aynı CS hattında birden fazla ADAR1000 varsa A14:A13 device address alanı ve broadcast/write-all davranışı açıkça test edilmelidir.",
    ],
    codegenNotes: [
      "Spec2Code ADAR1000 için device.config.register_words listesindeki 24-bit word'leri sırayı bozmadan SPI üzerinden yazar.",
      "Descriptor frame modeli R/W bitini doğrular; write init array içinde R/W=1 olan word hata üretir.",
      "Generated header ADAR1000_REG_* offset makrolarını içerir; düşük seviyeli register read/write helper'ları ileride public API olarak genişletilebilir.",
      "Catalog içindeki driver view register transfer formatını gösterir; şu an generated public operation deterministic device_init akışıdır.",
    ],
    pinMap: {
      packageName: "88-terminal LGA_CAV",
      view: "Fonksiyonel pin görünümü",
      verification: "Analog Devices ADAR1000 datasheet pin configuration ve pin function tablolarıyla kontrol edildi; burada software bring-up için kritik gruplar öne çıkarılır.",
      note: "Tam ball/pad yerleşimi PCB layout sırasında datasheet package drawing üzerinden ayrıca doğrulanmalıdır.",
      pins: [
        { name: "CSB", role: "SPI chip select, active low", tone: "bus", side: "left" },
        { name: "SCLK", role: "SPI clock", tone: "bus", side: "left" },
        { name: "SDIO", role: "SPI serial data input / 3-wire data", tone: "bus", side: "left" },
        { name: "SDO", role: "SPI serial data output / 4-wire readback", tone: "bus", side: "left" },
        { name: "ADDR0", role: "SPI device address strap", tone: "control", side: "left" },
        { name: "ADDR1", role: "SPI device address strap", tone: "control", side: "left" },
        { name: "RESETB", role: "Hardware reset, active low", tone: "control", side: "left" },
        { name: "TR", role: "External transmit/receive state control", tone: "control", side: "left" },
        { name: "POL", role: "External polarity/control input", tone: "control", side: "left" },
        { name: "RX1..RX4", role: "Channel RX RF inputs", tone: "analog", side: "right" },
        { name: "TX1..TX4", role: "Channel TX RF outputs", tone: "analog", side: "right" },
        { name: "RF_IO1..RF_IO4", role: "Antenna-side RF channel ports", tone: "analog", side: "right" },
        { name: "DET1..DET4", role: "Channel detector outputs/inputs", tone: "analog", side: "right" },
        { name: "LNA_BIAS", role: "External LNA bias output", tone: "analog", side: "right" },
        { name: "PA_BIAS1..4", role: "External PA bias outputs", tone: "analog", side: "right" },
        { name: "VDD*", role: "Analog/digital supply rails", tone: "power", side: "right" },
        { name: "GND/EPAD", role: "Ground and exposed pad", tone: "ground", side: "right" },
      ],
      groups: [
        { label: "SPI", pins: ["CSB", "SCLK", "SDIO", "SDO", "ADDR0", "ADDR1"], tone: "bus", description: "24-bit register/RAM erişimi ve multi-drop address seçimi." },
        { label: "T/R control", pins: ["TR", "POL", "RESETB"], tone: "control", description: "External TX/RX state, polarity ve reset davranışı." },
        { label: "RF channels", pins: ["RX1..RX4", "TX1..TX4", "RF_IO1..RF_IO4"], tone: "analog", description: "Beamforming path; gain/phase register'ları bu channel'ları ayarlar." },
        { label: "Bias/detector", pins: ["DET1..DET4", "LNA_BIAS", "PA_BIAS1..4"], tone: "analog", description: "Bias RAM/register ve detector enable alanlarıyla yönetilir." },
      ],
    },
  },

  LTC2991: {
    part: "LTC2991",
    reviewedAt: "2026-06-28",
    scope: "Gerilim, akım, iç sıcaklık ve VCC izleme kullanım senaryoları.",
    sources: [
      {
        label: "Analog Devices LTC2991 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/2991ff.pdf",
      },
    ],
    overview:
      "8 kanallı I2C monitor entegresidir. V1/V2, V3/V4, V5/V6 ve V7/V8 çiftleri single-ended gerilim, differential gerilim, shunt üzerinden akım veya remote temperature tarzı ölçümler için konfigüre edilebilir. İç sıcaklık ve VCC ölçümü de açılabilir.",
    keyFacts: [
      "Default 7-bit adres ailesi 0x48..0x4F aralığındadır; adres pinleriyle seçilir.",
      "Register erişimi 8-bit register pointer ile yapılır; MSB/LSB okumaları big-endian kabul edilir.",
      "Pair mode CONTROL_V1V4 ve CONTROL_V5V8 ile belirlenir; conversion enable bitleri STATUS_HIGH içindedir.",
      "Önce raw okumalar dışarı verilir; board-level scaling uygulama profiline ait olmalıdır.",
    ],
    configuration: [
      "Her pair için bir mode seçilir: off, single-ended gerilim, differential gerilim, akım veya sıcaklık.",
      "Current mode seçilirse shunt direnç değeri device config içinde tutulmalıdır; böylece ileride üretilen kod doğru conversion helper sunabilir.",
      "İç sıcaklık ve VCC sadece kart bu okumaları gerçekten kullanıyorsa açılmalı; aksi halde init minimal tutulmalıdır.",
    ],
    registers: ltc2991Registers(),
    recipes: [
      {
        title: "V1/V2 üzerinde differential gerilim",
        goal: "V1 ile V2 arasındaki gerilim farkını ölçmek.",
        steps: [
          "Device konfigürasyon panelinde V1/V2 mode değerini differential gerilim yap.",
          "Üretilen init, CONTROL_V1V4 yazar ve STATUS_HIGH üzerinden V1/V2 conversion enable eder.",
          "Busy biti temizlendikten sonra V1_MSB/V1_LSB oku; board scaling raw driver dışında kalsın.",
        ],
      },
      {
        title: "Akım ölçümü",
        goal: "Bir kanal pair'ini shunt direnç ile kullanmak.",
        steps: [
          "Pair için current mode seç ve shunt değerini milliohm olarak gir.",
          "Üretilen raw read fonksiyonunu stabil interface olarak kullan; akım hesabı raw code ve shunt değeriyle yapılabilir.",
          "Hassasiyet önemliyse shunt toleransını application code içinde açıkça belirt.",
        ],
      },
      {
        title: "İç sıcaklık sanity read",
        goal: "Board analog girişlerine bağlı kalmadan cihazın cevap verdiğini doğrulamak.",
        steps: [
          "İç sıcaklık okumasını enable et.",
          "İç sıcaklık busy bitini poll et.",
          "T_INTERNAL_MSB/T_INTERNAL_LSB oku ve raw code değerini logla.",
        ],
      },
    ],
    gotchas: [
      "Init sonrasında conversion datasını körlemesine hemen okuma; ilgili busy biti poll edilmeli veya conversion delay eklenmeli.",
      "Differential/current/temperature mode seçimleri pair seviyesindedir; bir input'u değiştirmek eş input'u da etkileyebilir.",
      "Birden fazla LTC2991 aynı strap pinleriyle kullanılırsa adres çakışması yaygındır; mux üzerinden bağla veya adres pinlerini değiştir.",
    ],
    codegenNotes: [
      "Spec2Code şu anda device.config üzerinden STATUS_HIGH, CONTROL_V1V4 ve CONTROL_V5V8 için init sequence üretir.",
      "Üretilen API önce raw read fonksiyonlarını sunar; kalibre edilmiş engineering-unit helper'lar açık board scaling ile eklenmelidir.",
    ],
    pinMap: {
      packageName: "MSOP-16",
      view: "Üst görünüm",
      verification: "Analog Devices LTC2991 datasheet pin configuration bilgisiyle kontrol edildi.",
      note: "V1..V8 analog girişleri pair halinde çalışır; pair mode seçimi init sequence içindeki CONTROL register yazımlarını etkiler.",
      pins: [
        { number: "1", name: "V1", role: "Analog giriş / V1-V2 pair", tone: "analog", side: "left" },
        { number: "2", name: "V2", role: "Analog giriş / V1-V2 pair", tone: "analog", side: "left" },
        { number: "3", name: "V3", role: "Analog giriş / V3-V4 pair", tone: "analog", side: "left" },
        { number: "4", name: "V4", role: "Analog giriş / V3-V4 pair", tone: "analog", side: "left" },
        { number: "5", name: "V5", role: "Analog giriş / V5-V6 pair", tone: "analog", side: "left" },
        { number: "6", name: "V6", role: "Analog giriş / V5-V6 pair", tone: "analog", side: "left" },
        { number: "7", name: "V7", role: "Analog giriş / V7-V8 pair", tone: "analog", side: "left" },
        { number: "8", name: "V8", role: "Analog giriş / V7-V8 pair", tone: "analog", side: "left" },
        { number: "16", name: "VCC", role: "Besleme", tone: "power", side: "right" },
        { number: "15", name: "ADR2", role: "I2C adres strap biti", tone: "control", side: "right" },
        { number: "14", name: "ADR1", role: "I2C adres strap biti", tone: "control", side: "right" },
        { number: "13", name: "ADR0", role: "I2C adres strap biti", tone: "control", side: "right" },
        { number: "12", name: "PWM", role: "PWM output / control", tone: "control", side: "right" },
        { number: "11", name: "SCL", role: "I2C clock", tone: "bus", side: "right" },
        { number: "10", name: "SDA", role: "I2C data", tone: "bus", side: "right" },
        { number: "9", name: "GND", role: "Toprak", tone: "ground", side: "right" },
      ],
      groups: [
        { label: "V1/V2", pins: ["V1", "V2"], tone: "analog", description: "Single-ended, differential, current veya remote temperature mode." },
        { label: "V3/V4", pins: ["V3", "V4"], tone: "analog", description: "Aynı pair-level measurement mode değerini paylaşır." },
        { label: "V5/V6", pins: ["V5", "V6"], tone: "analog", description: "CONTROL_V5V8 üzerinden konfigüre edilir." },
        { label: "V7/V8", pins: ["V7", "V8"], tone: "analog", description: "CONTROL_V5V8 üzerinden konfigüre edilir." },
        { label: "I2C", pins: ["SCL", "SDA", "ADR0", "ADR1", "ADR2"], tone: "bus", description: "Bus erişimi ve adres seçimi." },
      ],
    },
  },

  TCA9548A: {
    part: "TCA9548A",
    reviewedAt: "2026-06-28",
    scope: "Tek upstream hat üzerinden 8 downstream I2C kanal anahtarlama.",
    sources: [
      {
        label: "Texas Instruments TCA9548A datasheet",
        url: "https://www.ti.com/lit/ds/symlink/tca9548a.pdf",
      },
    ],
    overview:
      "8 kanallı I2C switch entegresidir. Normal bir register pointer kullanmaz; kanal seçimi, her biti bir downstream kanalı enable eden tek bir control byte yazarak yapılır.",
    keyFacts: [
      "Default adres ailesi 0x70..0x77 aralığındadır; A0/A1/A2 pinleriyle seçilir.",
      "0x00 yazmak tüm downstream kanalları disable eder.",
      "Birden fazla bit set edilerek birden fazla kanal açılabilir; Spec2Code öngörülebilir routing için default olarak tek aktif kanal kullanır.",
      "Mux, aynı downstream I2C adresini kullanan parçaları ayırmak ve bus capacitance segmentasyonu için kullanışlıdır.",
    ],
    configuration: [
      "Mux adresini ayarla, ardından downstream cihazları 0..7 arası kanal numarasına bağla.",
      "Kart bilinçli olarak bus fan-out istemiyorsa yalnızca tek kanalı aktif tut.",
    ],
    registers: [
      {
        name: "CONTROL",
        address: "direct byte",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Spec2Code içindeki pseudo register; gerçek cihaz erişimi tek control byte yazımıdır.",
        fields: [
          { bits: "B7", name: "CH7_EN", meaning: "SC7/SD7 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B6", name: "CH6_EN", meaning: "SC6/SD6 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B5", name: "CH5_EN", meaning: "SC5/SD5 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B4", name: "CH4_EN", meaning: "SC4/SD4 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B3", name: "CH3_EN", meaning: "SC3/SD3 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B2", name: "CH2_EN", meaning: "SC2/SD2 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B1", name: "CH1_EN", meaning: "SC1/SD1 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
          { bits: "B0", name: "CH0_EN", meaning: "SC0/SD0 downstream kanalını enable eder.", values: ["0: kanal kapalı", "1: kanal açık"] },
        ],
      },
    ],
    recipes: [
      {
        title: "Tek kanal seçimi",
        goal: "Tek bir downstream cihazla haberleşmek.",
        steps: [
          "Control byte içine 1 << channel değerini yaz.",
          "Downstream cihaz transaction'ını aynı upstream I2C controller üzerinden yap.",
          "İzolasyon gerekiyorsa transaction sonrasında opsiyonel olarak 0x00 yaz.",
        ],
      },
      {
        title: "Tekrarlı I2C adreslerini çözme",
        goal: "Aynı adrese sahip birden fazla aynı parçayı kullanmak.",
        steps: [
          "Her aynı adresli parçayı farklı mux kanalına yerleştir.",
          "Her cihaz adresini değiştirmeden bırak.",
          "Her device access öncesinde ilgili kanalı seç.",
        ],
      },
    ],
    gotchas: [
      "Channel control byte öncesinde register address gönderilmez.",
      "Birden fazla kanal enable edilirse aynı adresteki downstream cihazlar çakışır.",
      "Reset sonrası tüm kanallar disabled durumdadır; init veya ilk access mutlaka kanal seçmelidir.",
    ],
    codegenNotes: [
      "Spec2Code camelCase channel select helper üretir ve downstream device access öncesine mux seçimini ekler.",
    ],
    pinMap: {
      packageName: "TSSOP/VSSOP-24",
      view: "Üst görünüm",
      verification: "Texas Instruments TCA9548A datasheet Table 4-1 pin functions bilgisiyle kontrol edildi.",
      note: "Downstream hatlar SDn/SCn çifti olarak düşünülmelidir; her kanal için ayrı pull-up referansı olabilir.",
      pins: [
        { number: "1", name: "A0", role: "I2C adres strap biti", tone: "control", side: "left" },
        { number: "2", name: "A1", role: "I2C adres strap biti", tone: "control", side: "left" },
        { number: "3", name: "RESET", role: "Aktif-low reset", tone: "control", side: "left" },
        { number: "4", name: "SD0", role: "Downstream channel 0 data", tone: "bus", side: "left" },
        { number: "5", name: "SC0", role: "Downstream channel 0 clock", tone: "bus", side: "left" },
        { number: "6", name: "SD1", role: "Downstream channel 1 data", tone: "bus", side: "left" },
        { number: "7", name: "SC1", role: "Downstream channel 1 clock", tone: "bus", side: "left" },
        { number: "8", name: "SD2", role: "Downstream channel 2 data", tone: "bus", side: "left" },
        { number: "9", name: "SC2", role: "Downstream channel 2 clock", tone: "bus", side: "left" },
        { number: "10", name: "SD3", role: "Downstream channel 3 data", tone: "bus", side: "left" },
        { number: "11", name: "SC3", role: "Downstream channel 3 clock", tone: "bus", side: "left" },
        { number: "12", name: "GND", role: "Toprak", tone: "ground", side: "left" },
        { number: "24", name: "VCC", role: "Besleme", tone: "power", side: "right" },
        { number: "23", name: "SDA", role: "Upstream I2C data", tone: "bus", side: "right" },
        { number: "22", name: "SCL", role: "Upstream I2C clock", tone: "bus", side: "right" },
        { number: "21", name: "A2", role: "I2C adres strap biti", tone: "control", side: "right" },
        { number: "20", name: "SC7", role: "Downstream channel 7 clock", tone: "bus", side: "right" },
        { number: "19", name: "SD7", role: "Downstream channel 7 data", tone: "bus", side: "right" },
        { number: "18", name: "SC6", role: "Downstream channel 6 clock", tone: "bus", side: "right" },
        { number: "17", name: "SD6", role: "Downstream channel 6 data", tone: "bus", side: "right" },
        { number: "16", name: "SC5", role: "Downstream channel 5 clock", tone: "bus", side: "right" },
        { number: "15", name: "SD5", role: "Downstream channel 5 data", tone: "bus", side: "right" },
        { number: "14", name: "SC4", role: "Downstream channel 4 clock", tone: "bus", side: "right" },
        { number: "13", name: "SD4", role: "Downstream channel 4 data", tone: "bus", side: "right" },
      ],
      groups: [
        { label: "Upstream", pins: ["SCL", "SDA"], tone: "bus", description: "Controller tarafındaki I2C hattı." },
        { label: "Channel 0..7", pins: ["SC0", "SD0", "SC1", "SD1", "SC2", "SD2", "SC3", "SD3", "SC4", "SD4", "SC5", "SD5", "SC6", "SD6", "SC7", "SD7"], tone: "bus", description: "Seçilen downstream I2C segmentleri." },
        { label: "Address/reset", pins: ["A0", "A1", "A2", "RESET"], tone: "control", description: "Adres seçimi ve bus recovery reset hattı." },
      ],
    },
  },

  MT25Q128: {
    part: "MT25Q128",
    reviewedAt: "2026-06-28",
    scope: "Güvenli single-SPI NOR flash read, program, erase ve JEDEC ID akışları.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
      },
      {
        label: "Micron MT25Q family datasheet copy",
        url: "https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8880/557_mt25q-qlkt-l-512-abb-0.pdf",
      },
    ],
    overview:
      "128 Mbit SPI NOR flash entegresidir; genellikle 16 MB nonvolatile memory olarak kullanılır. Mevcut Spec2Code profili 3-byte addressing ve konservatif single-SPI command setini kullanır.",
    keyFacts: [
      "3-byte address width, tüm 128 Mbit adres aralığı için yeterlidir.",
      "Read/program/erase operasyonlarında write-enable ve busy polling sırası korunmalıdır.",
      "Parça ailesi daha hızlı dual/quad read mode'ları destekleyebilir; mevcut generated driver bilinçli olarak güvenli base command setinde kalır.",
      "Page program boyutu tipik olarak 256 byte'tır; page boundary aşan yazmalar application logic tarafından bölünmelidir.",
    ],
    configuration: [
      "Parçayı SPI/QSPI controller instance'a bağlamak için chip-select kullan.",
      "Bu descriptor için address width 24 bit kalmalıdır.",
      "Flash reset pini işlemciye bağlıysa board reset GPIO ekle; bağlı değilse gereksizdir.",
    ],
    registers: mt25qRegisters("MT25Q128"),
    recipes: [
      {
        title: "JEDEC ID okuma",
        goal: "Wiring ve chip-select doğrulamak.",
        steps: ["Chip-select assert et.", "0x9F gönder.", "Üç ID byte oku; all-0x00/all-0xFF değerlerini reddet."],
      },
      {
        title: "Page program",
        goal: "Byte verilerini bir page içine programlamak.",
        steps: [
          "WRITE_ENABLE gönder.",
          "24-bit address ile PAGE_PROGRAM gönder.",
          "Page boundary izin verdiğinden fazlasını yazma.",
          "WIP temizlenene kadar READ_STATUS poll et.",
        ],
      },
    ],
    gotchas: [
      "Bitleri 0'dan tekrar 1'e çevirmek gerekiyorsa program öncesinde erase yapılmalıdır.",
      "Program ve erase süreleri normal SPI read'e göre uzundur; WIP her zaman poll edilmelidir.",
      "Board pinleri, controller mode ve volatile/nonvolatile config bitleri bilinçli ayarlanmadan quad read/program kullanılmamalıdır.",
    ],
    codegenNotes: [
      "Spec2Code şu anda read, program, sector erase ve ID read için güvenli 3-byte command seti üretir.",
    ],
    pinMap: {
      packageName: "8-pin SPI NOR sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "Micron MT25Q 128Mb datasheet signal descriptions ve 8-pin package bilgisiyle kontrol edildi.",
      note: "Pin numaraları 8-pin SPI NOR package için geçerlidir; farklı orderable/package kodunda datasheet package tablosu esas alınmalıdır.",
      pins: [
        { number: "1", name: "S#", role: "Chip select", tone: "control", side: "left" },
        { number: "2", name: "DQ1", role: "SO / IO1", tone: "memory", side: "left" },
        { number: "3", name: "W#/DQ2", role: "Write protect / IO2", tone: "memory", side: "left" },
        { number: "4", name: "VSS", role: "Toprak", tone: "ground", side: "left" },
        { number: "8", name: "VCC", role: "Besleme", tone: "power", side: "right" },
        { number: "7", name: "DQ3/HOLD#", role: "Hold / IO3", tone: "memory", side: "right" },
        { number: "6", name: "C", role: "SPI clock", tone: "bus", side: "right" },
        { number: "5", name: "DQ0", role: "SI / IO0", tone: "memory", side: "right" },
      ],
      groups: [
        { label: "Single SPI", pins: ["S#", "C", "DQ0", "DQ1"], tone: "bus", description: "Mevcut driver güvenli single-SPI command setini kullanır." },
        { label: "Quad-ready", pins: ["DQ0", "DQ1", "W#/DQ2", "DQ3/HOLD#"], tone: "memory", description: "Quad mode için controller, pin mux ve flash config ayrıca doğrulanmalıdır." },
      ],
    },
  },

  MT25QU02G: {
    part: "MT25QU02G",
    reviewedAt: "2026-06-28",
    scope: "4-byte address command akışına sahip 2 Gbit SPI NOR flash.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
      },
      {
        label: "Micron MT25Q family datasheet copy",
        url: "https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/8880/557_mt25q-qlkt-l-512-abb-0.pdf",
      },
    ],
    overview:
      "2 Gbit SPI NOR flash entegresidir. Tüm adres aralığı için 32-bit addressing gerekir; Spec2Code 4-byte command opcode'ları kullanır ve init sırasında enter-4-byte-mode komutu üretir.",
    keyFacts: [
      "Tam 256 MB alan için 4-byte addressing gerekir.",
      "Üretilen profile 0xB7 enter-4-byte mode ve 4-byte read/program/erase opcode'ları kullanır.",
      "Parça ailesi exact variant ve controller wiring durumuna göre dual/quad/octal transfer mode destekleyebilir; bu profil deterministik 4-byte SPI command akışında kalır.",
      "Büyük flash parçalarında application-level storage layout içinde die/bank boundary etkileri olabilir.",
    ],
    configuration: [
      "Chip-select bilgisini SPI/QSPI controller'a bağla.",
      "Address width 32 bit kalmalıdır.",
      "Kart quad/dual transfer mode'u bilinçli enable ediyorsa ileride explicit mode field kullanılmalıdır.",
    ],
    registers: mt25qRegisters("MT25QU02G"),
    recipes: [
      {
        title: "Güvenli init",
        goal: "Full-range access için cihazı hazırlamak.",
        steps: [
          "WRITE_ENABLE gönder.",
          "ENTER_4BYTE gönder.",
          "Wiring sanity check için JEDEC ID oku.",
        ],
      },
      {
        title: "Full-range read",
        goal: "16 MB boundary ötesini doğru okumak.",
        steps: [
          "READ_DATA_4B (0x13) kullan.",
          "32-bit address gönder.",
          "Controller transfer mode, generated command profile ile uyumlu kalmalıdır.",
        ],
      },
    ],
    gotchas: [
      "2 Gbit flash üzerinde 3-byte command sessizce yanlış bölgeyi adresleyebilir.",
      "Program/erase sonrasında status her zaman poll edilmelidir.",
      "Dual/quad mode için board-level pin ve controller konfigürasyonu gerekir; yalnızca part number'dan çıkarım yapılmamalıdır.",
    ],
    codegenNotes: [
      "Spec2Code şu anda init, read, program ve erase için 4-byte-safe command üretir.",
      "Gelecekteki flash configuration panel, protocol width değişimini yalnızca controller ve board pinleri explicit ise yapmalıdır.",
    ],
    pinMap: {
      packageName: "MT25QU02G sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "Micron MT25Q 2Gb datasheet signal descriptions bilgisiyle kontrol edildi; burada package ball numarası verilmez.",
      note: "MT25QU02G package/ball map orderable package koduna bağlıdır; burada yalnızca codegen açısından kullanılan kesin sinyal adları gösterilir.",
      pins: [
        { name: "S#", role: "Chip select", tone: "control", side: "left" },
        { name: "C", role: "SPI/QSPI clock", tone: "bus", side: "left" },
        { name: "DQ0", role: "IO0 / data in", tone: "memory", side: "left" },
        { name: "DQ1", role: "IO1 / data out", tone: "memory", side: "left" },
        { name: "W#/DQ2", role: "IO2 / write protect function", tone: "memory", side: "right" },
        { name: "DQ3/HOLD#", role: "IO3 / hold function", tone: "memory", side: "right" },
        { name: "RESET#", role: "Reset input", tone: "control", side: "right" },
        { name: "VCC", role: "Core/IO besleme", tone: "power", side: "right" },
        { name: "VSS", role: "Toprak", tone: "ground", side: "right" },
      ],
      groups: [
        { label: "QSPI bus", pins: ["S#", "C", "DQ0", "DQ1", "W#/DQ2", "DQ3/HOLD#"], tone: "memory", description: "Protocol width explicit seçilmeden generated driver single/4-byte command güvenli çizgide kalır." },
        { label: "Addressing", pins: ["S#", "C", "DQ0", "DQ1"], tone: "bus", description: "Bu parçada full range access için 32-bit address command gerekir." },
      ],
    },
  },

  AD7414: {
    part: "AD7414",
    reviewedAt: "2026-06-28",
    scope: "Sıcaklık okuma ve alert threshold konfigürasyonu.",
    sources: [
      {
        label: "Analog Devices AD7414/AD7415 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ad7414_7415.pdf",
      },
    ],
    overview:
      "10-bit two's-complement sıcaklık sonucuna ve programlanabilir high/low alert threshold değerlerine sahip I2C temperature sensor'dür. Yaygın read-only kullanım için continuous conversion modunda açılır.",
    keyFacts: [
      "Default adres ailesi 0x48'den başlar ve address-select pinlerine bağlıdır.",
      "Sıcaklık sonucu iki byte olarak okunur; kullanılacak sıcaklık bitleri üst 10 bittir.",
      "Configuration register power-down, one-shot, alert davranışı, polarity ve filtering ayarlarını kontrol eder.",
      "Threshold register'ları alert kullanım senaryoları için 8-bit tarzı trip point değerleridir.",
    ],
    configuration: [
      "Basit board monitoring için I2C init sonrasında zorunlu device register write gerekmez.",
      "One-shot veya power-down sadece application conversion timing'i explicit yönetiyorsa kullanılmalıdır.",
      "Alert polarity ve threshold değerleri yalnızca ALERT pini bağlı ve kullanılıyorsa ayarlanmalıdır.",
    ],
    registers: [
      {
        name: "TEMPERATURE",
        address: "0x00",
        width: "16",
        access: "RO",
        reset: "0x0000",
        purpose: "Raw sıcaklık transfer image.",
        fields: [
          { bits: "Byte1 D7:D0", name: "TEMP[9:2]", meaning: "10-bit two's-complement sıcaklık kodunun üst sekiz biti." },
          { bits: "Byte2 D7:D6", name: "TEMP[1:0]", meaning: "10-bit sıcaklık kodunun en düşük iki biti." },
          { bits: "Byte2 D5", name: "ALERT flag", meaning: "ALERT pininin okunan mantık seviyesini taşır.", values: ["0: ALERT pini low", "1: ALERT pini high"] },
          { bits: "Byte2 D4", name: "THIGH flag", meaning: "Sıcaklık THIGH eşiğini geçtiğinde set olan flag.", values: ["0: flag clear", "1: sıcaklık THIGH üstünde"] },
          { bits: "Byte2 D3", name: "TLOW flag", meaning: "Sıcaklık TLOW eşiğinin altına indiğinde set olan flag.", values: ["0: flag clear", "1: sıcaklık TLOW altında"] },
          { bits: "Byte2 D2:D0", name: "Reserved", meaning: "Temperature conversion data için kullanılmaz; okunan değer uygulama hesabına dahil edilmemelidir.", values: ["000: read as zero / ignore", "diğer: reserved; application hesabına dahil etme"] },
        ],
      },
      {
        name: "CONFIGURATION",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x40",
        purpose: "Power, alert, polarity, reset ve one-shot kontrolleri.",
        fields: [
          { bits: "D7", name: "Power-down", meaning: "Cihazı low-power shutdown moduna alır.", values: ["0: normal çalışma", "1: power-down"] },
          { bits: "D6", name: "Filter", meaning: "Temperature filtering davranışını seçer.", values: ["0: filtering bypass", "1: filtering aktif"] },
          { bits: "D5", name: "ALERT disable", meaning: "ALERT output davranışını kapatır/açar.", values: ["0: ALERT aktif", "1: ALERT disabled"] },
          { bits: "D4", name: "ALERT polarity", meaning: "ALERT pininin aktif seviyesini seçer.", values: ["0: active low", "1: active high"] },
          { bits: "D3", name: "ALERT reset", meaning: "Interrupt/latch modunda ALERT durumunu resetlemek için kullanılır.", values: ["0: reset komutu yok / readback 0", "1: ALERT latch reset edilir; bit saklanmaz"] },
          { bits: "D2", name: "One-shot", meaning: "Power-down modundayken tek conversion başlatır.", values: ["0: one-shot başlatma yok / readback 0", "1: tek conversion başlatılır; bit saklanmaz"] },
          { bits: "D1:D0", name: "Factory settings", meaning: "Normal kullanımda 0 tutulmalıdır.", values: ["00: normal kullanım", "diğer: factory/reserved; kullanma"] },
        ],
      },
      {
        name: "THIGH",
        address: "0x02",
        width: "8",
        access: "RW",
        reset: "0x7F",
        purpose: "High temperature alert threshold değeri.",
        fields: [
          { bits: "D7", name: "Sign/MSB", meaning: "8-bit signed threshold kodunun üst bitidir.", values: signValues },
          { bits: "D6:D0", name: "Threshold code", meaning: "High threshold için 1 derece C adımlı signed sıcaklık kodu." },
        ],
      },
      {
        name: "TLOW",
        address: "0x03",
        width: "8",
        access: "RW",
        reset: "0x80",
        purpose: "Low temperature alert threshold değeri.",
        fields: [
          { bits: "D7", name: "Sign/MSB", meaning: "8-bit signed threshold kodunun üst bitidir.", values: signValues },
          { bits: "D6:D0", name: "Threshold code", meaning: "Low threshold için 1 derece C adımlı signed sıcaklık kodu." },
        ],
      },
    ],
    recipes: [
      {
        title: "Sıcaklık okuma",
        goal: "Güncel raw sıcaklık değerini almak.",
        steps: [
          "Register pointer 0x00 yaz.",
          "İki byte oku.",
          "10-bit signed code kullanmak için transfer image değerini right-shift et.",
        ],
      },
      {
        title: "Alert threshold kurulumu",
        goal: "ALERT pinini hardware trip signal olarak kullanmak.",
        steps: [
          "THIGH ve TLOW yaz.",
          "Alert enable ve polarity konfigüre et.",
          "Alert clear/reset davranışını application içinde yönet.",
        ],
      },
    ],
    gotchas: [
      "Raw temperature code signed'dır; negatif sıcaklıklar unsigned gibi yorumlanmamalıdır.",
      "One-shot mode, conversion start ile read arasında explicit timing gerektirir.",
      "Alert davranışı yalnızca pin gerçekten bağlıysa enable edilmeli; değilse config minimal tutulmalıdır.",
    ],
    codegenNotes: [
      "Spec2Code bu parça için basit init, temperature_read ve config_read operasyonları üretir.",
    ],
    pinMap: {
      packageName: "AD7414 sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "Analog Devices AD7414/AD7415 datasheet pin function bilgisiyle kontrol edildi; package pin sırası özellikle verilmez.",
      note: "Paket pin sırası seçilen orderable/package'a göre doğrulanmalıdır; bu harita software açısından kullanılan temel sinyalleri gösterir.",
      pins: [
        { name: "SDA", role: "I2C data", tone: "bus", side: "left" },
        { name: "SCL", role: "I2C clock", tone: "bus", side: "left" },
        { name: "AS", role: "Address select", tone: "control", side: "left" },
        { name: "VDD", role: "Besleme", tone: "power", side: "right" },
        { name: "GND", role: "Toprak", tone: "ground", side: "right" },
        { name: "ALERT", role: "Over-temperature interrupt / alert", tone: "control", side: "right" },
      ],
      groups: [
        { label: "I2C", pins: ["SDA", "SCL", "AS"], tone: "bus", description: "Register erişimi ve adres seçimi." },
        { label: "Alert", pins: ["ALERT"], tone: "control", description: "Threshold kullanılıyorsa firmware tarafında açıkça konfigüre edilmeli." },
      ],
    },
  },

  TMP101: {
    part: "TMP101",
    reviewedAt: "2026-06-29",
    scope: "Sıcaklık okuma, programmable resolution, one-shot/shutdown ve ALERT threshold davranışı.",
    sources: [
      {
        label: "Texas Instruments TMP100/TMP101 datasheet",
        url: "https://www.ti.com/lit/gpn/TMP101",
      },
    ],
    overview:
      "TMP101, I2C/SMBus uyumlu dijital sıcaklık sensörüdür. TMP100 ailesiyle aynı register modelini kullanır; TMP101 tarafında tek address pin ve ALERT output bulunur.",
    keyFacts: [
      "TMP101 adresleri ADD0 seviyesine bağlıdır: ADD0=0 için 0x48, float için 0x49, ADD0=1 için 0x4A.",
      "Temperature, TLOW ve THIGH register'ları 12-bit two's-complement sıcaklık formatı taşır; alt dört bit zero-pad olarak kalır.",
      "Configuration register reset değeri 0x00'dır; OS/ALERT readback power-up sonrası 1 görülebilir.",
      "Resolution seçimi R1:R0 alanıyla yapılır; 9/10/11/12 bit için tipik conversion süreleri 40/80/160/320 ms'dir.",
      "I2C fast-mode 400 kHz desteklenir; high-speed mode için master code akışı gerekir, Spec2Code default 100 kHz güvenli başlar.",
    ],
    configuration: [
      "Basit monitoring için init sırasında device register write gerekmez; continuous conversion default olarak aktiftir.",
      "ALERT pini kullanılacaksa TLOW/THIGH, POL, TM ve F[1:0] birlikte düşünülmelidir.",
      "One-shot kullanılacaksa SD=1 yapılır, OS_ALERT=1 yazılır ve seçilen resolution conversion süresi kadar beklenir.",
    ],
    registers: tmp101Registers(),
    recipes: [
      {
        title: "Sıcaklık okuma",
        goal: "Son conversion sonucunu raw 12-bit transfer image olarak almak.",
        steps: [
          "Pointer register'a TEMPERATURE adresi 0x00 yaz.",
          "İki byte oku; MSB önce gelir.",
          "16-bit image içinden TEMP[11:0] alanını kullan; Byte2 D3:D0 zero-pad olduğu için hesapta ignore edilir.",
        ],
      },
      {
        title: "ALERT threshold kurulumu",
        goal: "TMP101 ALERT pinini comparator veya interrupt mode için kullanmak.",
        steps: [
          "TLOW ve THIGH register'larına 12-bit sıcaklık formatında threshold image yaz.",
          "CONFIGURATION içinden POL, TM ve F[1:0] alanlarını seç.",
          "Interrupt mode'da ALERT clear davranışını read operasyonları veya SMBus alert response akışıyla yönet.",
        ],
      },
    ],
    gotchas: [
      "TMP101 temperature code signed'dır; negatif sıcaklıkları unsigned değer gibi yorumlama.",
      "THIGH/TLOW karşılaştırmalarında 12 bitin tamamı kullanılır; resolution daha düşük olsa bile threshold alt bitleri ALERT davranışını etkileyebilir.",
      "ALERT open-drain/pull-up topolojisi board üzerinde doğrulanmadan POL/TM değişikliği yapma.",
    ],
    codegenNotes: [
      "Spec2Code bu parça için `tmp101DeviceInit`, `tmp101TemperatureRead` ve `tmp101ConfigRead` üretir.",
      "Threshold write ve one-shot gibi board/application policy gerektiren ayarlar init sequence builder ile ayrıca eklenebilir.",
    ],
    pinMap: {
      packageName: "SOT-23-6 / TMP101 sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "TI TMP100/TMP101 datasheet package ve pin description bilgisiyle kontrol edildi; software açısından kullanılan sinyaller gösterilir.",
      note: "Pin numarası package varyantına göre kontrol edilmelidir; ADD0 strap ve ALERT pull-up board tasarımında önemlidir.",
      pins: [
        { name: "SDA", role: "I2C/SMBus data", tone: "bus", side: "left" },
        { name: "SCL", role: "I2C/SMBus clock", tone: "bus", side: "left" },
        { name: "ADD0", role: "Address select: 0/float/1", tone: "control", side: "left" },
        { name: "ALERT", role: "Open-drain alert / SMBus alert", tone: "control", side: "right" },
        { name: "V+", role: "Besleme", tone: "power", side: "right" },
        { name: "GND", role: "Toprak", tone: "ground", side: "right" },
      ],
      groups: [
        { label: "I2C", pins: ["SDA", "SCL", "ADD0"], tone: "bus", description: "Register pointer write/read akışı ve slave address seçimi." },
        { label: "Alert", pins: ["ALERT"], tone: "control", description: "Threshold, polarity ve thermostat mode ile birlikte anlam kazanır." },
      ],
    },
  },

  SHT21: {
    part: "SHT21",
    reviewedAt: "2026-06-29",
    scope: "Temperature/RH measurement command'ları, user register, CRC ve soft reset akışları.",
    sources: [
      {
        label: "Sensirion SHT21 datasheet",
        url: "https://sensirion.com/file/datasheet_sht21",
      },
    ],
    overview:
      "SHT21, I2C üzerinden command tabanlı çalışan humidity ve temperature sensor'dür. Klasik register pointer yerine measurement command gönderilir; sonuç iki data byte + opsiyonel CRC byte olarak okunur.",
    keyFacts: [
      "7-bit I2C address 0x40'tır; datasheet header olarak write için 1000 0000, read için 1000 0001 gösterir.",
      "Temperature command'ları: 0xE3 hold master, 0xF3 no-hold master.",
      "Relative humidity command'ları: 0xE5 hold master, 0xF5 no-hold master.",
      "User register read command 0xE7, write command 0xE6, soft reset command 0xFE'dir.",
      "Measurement frame içindeki iki LSB status bitidir; fiziksel değere çevirmeden önce 0 yapılmalıdır.",
      "CRC-8 polynomial x8 + x5 + x4 + 1 kullanılır.",
    ],
    configuration: [
      "Default resolution RH 12 bit / T 14 bit'tir.",
      "User register yazarken reserved bitler korunmalıdır; önce read, sonra sadece istenen bitleri değiştirerek write yap.",
      "No-hold mode başka I2C işler için daha uygundur; ölçüm bitene kadar read address ACK polling gerekir.",
      "Hold-master mode daha basit transaction üretir ama sensör ölçüm boyunca SCL hattını tutabilir.",
    ],
    registers: sht21Registers(),
    recipes: [
      {
        title: "Temperature measurement",
        goal: "Sıcaklık ham ölçüm frame'ini almak.",
        steps: [
          "Hold-master için 0xE3 veya no-hold için 0xF3 command byte gönder.",
          "Hold-master modda sensör ölçüm bitene kadar SCL'i tutabilir; no-hold modda read address ACK gelene kadar poll et.",
          "MSB, LSB/status ve CRC byte'ını oku; checksum doğrula.",
          "Fiziksel hesap öncesi LSB içindeki status bitlerini temizle.",
        ],
      },
      {
        title: "User register güvenli yazım",
        goal: "Resolution veya heater bitlerini reserved bitleri bozmadan değiştirmek.",
        steps: [
          "0xE7 ile user register oku.",
          "Reserved bitleri aynen koru; sadece RES[1:0] veya HEATER gibi hedef alanları değiştir.",
          "0xE6 command + yeni user register byte'ını yaz.",
        ],
      },
    ],
    gotchas: [
      "CRC byte'ını okumadan transaction kısaltılabilir ama güvenilirlik için özellikle kablolu/noisy ortamda CRC kontrolü önerilir.",
      "Heater diagnostic içindir; sürekli açık bırakılırsa humidity ölçümünü bilinçli olarak değiştirir.",
      "OTP_RELOAD_DISABLE bitini production gerekçesi olmadan değiştirme.",
      "NC pad'ler floating kalmalıdır; exposed/center pad VSS ile ilişkilidir.",
    ],
    codegenNotes: [
      "Spec2Code `sht21TemperatureRead`, `sht21HumidityRead` ve `sht21UserRegisterRead` üretir.",
      "Generated measurement helper hold-master command yolunu modellediği için no-hold polling policy application seviyesinde ayrıca ele alınabilir.",
    ],
    pinMap: {
      packageName: "DFN-6 / SHT21 top-view sinyal haritası",
      view: "Üst görünüm / fonksiyonel",
      verification: "Sensirion SHT21 datasheet Table 2 pin assignment bilgisiyle kontrol edildi.",
      note: "NC pinler floating kalmalıdır; SDA/SCL open-drain olduğundan pull-up gerekir.",
      pins: [
        { number: "1", name: "SDA", role: "I2C data", tone: "bus", side: "left" },
        { number: "2", name: "VSS", role: "Ground", tone: "ground", side: "left" },
        { number: "3", name: "NC", role: "No connect / floating", tone: "nc", side: "left" },
        { number: "4", name: "NC", role: "No connect / floating", tone: "nc", side: "right" },
        { number: "5", name: "VDD", role: "Besleme", tone: "power", side: "right" },
        { number: "6", name: "SCL", role: "I2C clock", tone: "bus", side: "right" },
      ],
      groups: [
        { label: "I2C", pins: ["SDA", "SCL"], tone: "bus", description: "Command send, measurement read ve user register access." },
        { label: "Power", pins: ["VDD", "VSS"], tone: "power", description: "2.1 V - 3.6 V supply range içinde kullanılmalıdır." },
      ],
    },
  },

  "24LC32A": {
    part: "24LC32A",
    reviewedAt: "2026-06-29",
    scope: "32-Kbit I2C EEPROM byte/page write, random/sequential read, ACK polling ve write protect davranışı.",
    sources: [
      {
        label: "Microchip 24AA32A/24LC32A datasheet",
        url: "https://ww1.microchip.com/downloads/aemDocuments/documents/MPD/ProductDocuments/DataSheets/24AA32A-24LC32A-32-Kbit-I2C-Serial-EEPROM-DS20001713.pdf",
      },
    ],
    overview:
      "24LC32A, 4096 byte memory array'e sahip 32-Kbit I2C serial EEPROM'dur. Access modeli register değil memory word address tabanlıdır; write sonrası internal programming cycle bitene kadar ACK polling gerekir.",
    keyFacts: [
      "Control byte formatı 1010 A2 A1 A0 R/W şeklindedir; A2:A0 pinleri 7-bit address'in alt bitlerini seçer.",
      "Default strap A2=A1=A0=0 kabul edilirse 7-bit I2C address 0x50 olur.",
      "Memory address 12 bittir: A11:A0. Transferde iki address byte gönderilir; high byte üst dört bit don't-care'dir.",
      "Page buffer 32 byte'tır; page write aynı physical page içinde kalmalıdır.",
      "STOP sonrası internal write cycle başlar; bu sırada cihaz ACK üretmez. ACK tekrar gelince sonraki işlem güvenlidir.",
      "WP pini VCC'ye bağlıysa array write-protected olur; VSS'ye bağlıysa write enable'dır.",
    ],
    configuration: [
      "Init sırasında EEPROM'a command yazılmaz; sadece I2C controller hazırlanır.",
      "Page write yaparken `(address % 32) + length <= 32` kuralı firmware tarafında enforce edilmelidir.",
      "Write sonrası fixed delay yerine ACK polling daha deterministik ve hızlıdır.",
      "SOT-23 package'da address pinleri dışarıda yoktur; datasheet bu durumda A2:A1:A0 = 0 kullanımını belirtir.",
    ],
    registers: lc32aRegisters(),
    recipes: [
      {
        title: "Random read",
        goal: "Herhangi bir EEPROM adresinden byte veya block okumak.",
        steps: [
          "Write control byte ile başla ve iki byte word address gönder.",
          "Repeated start üret.",
          "Read control byte gönder ve data byte'larını oku.",
          "Son byte'ta NACK + STOP ile transferi bitir.",
        ],
      },
      {
        title: "Page write",
        goal: "Aynı physical page içinde birden fazla byte yazmak.",
        steps: [
          "Write control byte, high address byte ve low address byte gönder.",
          "1..32 data byte gönder; page boundary aşılmamalıdır.",
          "STOP ile internal write cycle'ı başlat.",
          "Control byte write denemesi ACK alana kadar ACK polling yap.",
        ],
      },
    ],
    gotchas: [
      "32 byte sınırı aşılırsa ya da page boundary geçilirse EEPROM aynı page başına wrap eder ve önceki data overwrite olabilir.",
      "WP pini high ise cihaz command'ı ACK'leyebilir ama array içine data yazılmaz.",
      "Sequential read 0xFFF adresinden sonra 0x000'a dönebilir; block read length application tarafından sınırlandırılmalıdır.",
      "EEPROM endurance page bazlı düşünülmelidir; küçük write bile page refresh/write cycle oluşturabilir.",
    ],
    codegenNotes: [
      "Spec2Code bu parça için `dev24lc32aDeviceInit`, `dev24lc32aDataRead`, `dev24lc32aByteWrite` ve `dev24lc32aPageWrite` üretir.",
      "Function adı `dev24lc32a` prefix'iyle başlar çünkü C identifier rakamla başlayamaz.",
    ],
    pinMap: {
      packageName: "8-pin package / 24LC32A sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "Microchip 24AA32A/24LC32A datasheet pin function table ve device addressing bilgisiyle kontrol edildi.",
      note: "Paket pin numarası selected package'a göre kontrol edilmelidir; burada software açısından temel sinyaller ve strap pinleri gösterilir.",
      pins: [
        { name: "A0", role: "Chip address input", tone: "control", side: "left" },
        { name: "A1", role: "Chip address input", tone: "control", side: "left" },
        { name: "A2", role: "Chip address input", tone: "control", side: "left" },
        { name: "VSS", role: "Ground", tone: "ground", side: "left" },
        { name: "SDA", role: "I2C data", tone: "bus", side: "right" },
        { name: "SCL", role: "I2C clock", tone: "bus", side: "right" },
        { name: "WP", role: "Write protect", tone: "control", side: "right" },
        { name: "VCC", role: "Besleme", tone: "power", side: "right" },
      ],
      groups: [
        { label: "I2C", pins: ["SDA", "SCL", "A0", "A1", "A2"], tone: "bus", description: "Control byte ve word address transferleri." },
        { label: "Write protect", pins: ["WP"], tone: "control", description: "VCC: write protect, VSS: write enable." },
      ],
    },
  },

  DS1682: {
    part: "DS1682",
    reviewedAt: "2026-06-28",
    scope: "Elapsed-time counter, alarm değeri ve event counter okumaları.",
    sources: [
      {
        label: "Analog Devices / Maxim DS1682 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ds1682.pdf",
      },
    ],
    overview:
      "I2C interface'e sahip total elapsed-time recorder entegresidir; alarm storage, event counter ve user EEPROM byte'ları içerir. Kartın kalıcı operating-time accounting ihtiyacı varsa kullanışlıdır.",
    keyFacts: [
      "Descriptor tarafından kullanılan default I2C adresi 0x6B'dir.",
      "Elapsed time counter, quarter-second tick cinsinden 32-bit little-endian değer olarak okunur.",
      "Event counter 17 bit'tir: bir MSB bit CONFIGURATION içinde, kalan bitler EVENT_HIGH/EVENT_LOW içindedir.",
      "Bazı write-disable ve memory-disable operasyonları tek yönlü veya kalıcıdır; bunlar production-only action olarak ele alınmalıdır.",
    ],
    configuration: [
      "Read-only monitoring için zorunlu startup command gerekmez.",
      "Alarm polarity/output yalnızca alarm pini board design içinde kullanılıyorsa konfigüre edilmelidir.",
      "Destructive command'lar normal self-test akışlarından uzak tutulmalıdır.",
    ],
    registers: ds1682Registers(),
    recipes: [
      {
        title: "Elapsed-time okuma",
        goal: "Kalıcı operating time değerini okumak.",
        steps: [
          "ETC_LOW ile ETC_HIGH arasını oku.",
          "Byte'ları little-endian olarak birleştir.",
          "Application engineering unit istiyorsa quarter-second tick değerini saniyeye çevir.",
        ],
      },
      {
        title: "Event counter okuma",
        goal: "Tam 17-bit event count değerini okumak.",
        steps: [
          "Event MSB için CONFIGURATION bit 0 oku.",
          "EVENT_LOW ve EVENT_HIGH oku.",
          "bit16:CONFIGURATION[0], bits15..8:EVENT_HIGH, bits7..0:EVENT_LOW olacak şekilde birleştir.",
        ],
      },
    ],
    gotchas: [
      "Reset/write-disable/write-memory-disable command'ları smoke test içine konulmamalıdır.",
      "EEPROM-backed write işlemlerinde timing ve endurance etkileri olabilir.",
      "Multi-byte counter okumaları tutarlı yapılmalıdır; application atomicity istiyorsa rollover window çevresine retry logic eklenmelidir.",
    ],
    codegenNotes: [
      "Spec2Code config, elapsed time, alarm ve event count için read-oriented operasyonlar üretir.",
    ],
    pinMap: {
      packageName: "SO-8",
      view: "Üst görünüm",
      verification: "Analog Devices / Maxim DS1682 datasheet pin description ve 8-pin top view bilgisiyle kontrol edildi.",
      note: "Elapsed-time ve event counter davranışı board üzerindeki EVENT/ALARM bağlantılarıyla anlam kazanır.",
      pins: [
        { number: "1", name: "EVENT", role: "Event count input", tone: "control", side: "left" },
        { number: "2", name: "N.C.", role: "No connect", tone: "nc", side: "left" },
        { number: "3", name: "ALARM", role: "Alarm output", tone: "control", side: "left" },
        { number: "4", name: "GND", role: "Toprak", tone: "ground", side: "left" },
        { number: "8", name: "VCC", role: "Besleme", tone: "power", side: "right" },
        { number: "7", name: "N.C.", role: "No connect", tone: "nc", side: "right" },
        { number: "6", name: "SDA", role: "I2C data", tone: "bus", side: "right" },
        { number: "5", name: "SCL", role: "I2C clock", tone: "bus", side: "right" },
      ],
      groups: [
        { label: "Counter", pins: ["EVENT", "ALARM"], tone: "control", description: "EVENT sayımı ve alarm çıkışı board amacıyla eşleşmeli." },
        { label: "I2C", pins: ["SDA", "SCL"], tone: "bus", description: "Elapsed time, alarm ve event register okumaları." },
      ],
    },
  },

  LTC2945: {
    part: "LTC2945",
    reviewedAt: "2026-06-28",
    scope: "Raw power, sense/current, VIN, ADIN, status ve fault monitor okumaları.",
    sources: [
      {
        label: "Analog Devices LTC2945 datasheet",
        url: "https://www.analog.com/media/en/technical-documentation/data-sheets/ltc2945.pdf",
      },
    ],
    overview:
      "Wide-range I2C power monitor entegresidir. Shunt sense voltage, VIN ve auxiliary ADIN ölçer; ayrıca 24-bit power calculation register sunar.",
    keyFacts: [
      "Descriptor default adresi 0x67'dir; bu, CEh write-address seçeneğinin yaygın 7-bit formuna karşılık gelir.",
      "Continuous SENSE/VIN power monitoring için CONTROL reset/profile değeri 0x05 kullanılır.",
      "Power 24-bit raw değerdir; sense, VIN ve ADIN okumaları iki byte transfer içinde 12-bit raw image olarak gelir.",
      "Engineering-unit conversion Rsense ve board scaling değerlerine bağlıdır.",
    ],
    configuration: [
      "Raw code değerlerini çevirmeden önce Rsense ve board scaling application layer içinde belirlenmelidir.",
      "Snapshot mode yalnızca simultaneous channel capture gerekiyorsa kullanılmalıdır.",
      "Alert/fault limitleri sadece alert line bağlı ve test edilmişse konfigüre edilmelidir.",
    ],
    registers: ltc2945RegisterRows(),
    recipes: [
      {
        title: "Power monitor başlatma",
        goal: "Continuous raw monitoring başlatmak.",
        steps: [
          "CONTROL = 0x05 yaz.",
          "Cihazın erişilebilir olduğunu doğrulamak için STATUS oku.",
          "İhtiyaca göre POWER, SENSE, VIN ve ADIN raw register'larını oku.",
        ],
      },
      {
        title: "Sense üzerinden akım",
        goal: "Raw sense code değerini daha sonra board current değerine çevirmek.",
        steps: [
          "SENSE_MSB/SENSE_LSB oku.",
          "Datasheet transfer formatına göre raw 12-bit code değerini çıkar.",
          "Rsense ve board calibration işlemini low-level driver dışında uygula.",
        ],
      },
    ],
    gotchas: [
      "Raw code değerini volt/amp/watt değerine çevirmek board-specific bir iştir; bilinmeyen Rsense generic driver içine gömülmemelidir.",
      "Snapshot timing önemliyse ADC_BUSY kontrol edilmeli veya bilinen conversion cadence kullanılmalıdır.",
      "Fault bitleri documented clear path üzerinden temizlenene kadar latched kalabilir.",
    ],
    codegenNotes: [
      "Spec2Code status, power, sense, voltage ve ADIN için raw read API'leri üretir.",
    ],
    pinMap: {
      packageName: "LTC2945 sinyal haritası",
      view: "Fonksiyonel görünüm",
      verification: "Analog Devices LTC2945 datasheet pin functions bilgisiyle kontrol edildi; package pin sırası özellikle verilmez.",
      note: "LTC2945 I2C tarafında SDAI/SDAO ayrımı kullanır; normal I2C kullanımında board bağlantısı datasheet tavsiyesine göre yapılmalıdır.",
      pins: [
        { name: "SENSE+", role: "Shunt high-side sense", tone: "analog", side: "left" },
        { name: "SENSE-", role: "Shunt low-side sense", tone: "analog", side: "left" },
        { name: "VDD", role: "Supply / bus voltage sense", tone: "power", side: "left" },
        { name: "ADIN", role: "Auxiliary ADC input", tone: "analog", side: "left" },
        { name: "INTVCC", role: "Internal regulator decoupling", tone: "power", side: "left" },
        { name: "SDAI", role: "I2C data input", tone: "bus", side: "right" },
        { name: "SDAO", role: "I2C data output", tone: "bus", side: "right" },
        { name: "SCL", role: "I2C clock", tone: "bus", side: "right" },
        { name: "ADR0", role: "I2C address select", tone: "control", side: "right" },
        { name: "ADR1", role: "I2C address select", tone: "control", side: "right" },
        { name: "ALERT", role: "Alert output", tone: "control", side: "right" },
        { name: "GND", role: "Toprak", tone: "ground", side: "right" },
      ],
      groups: [
        { label: "Power path", pins: ["SENSE+", "SENSE-", "VDD"], tone: "analog", description: "Raw power/current/voltage okumalarının kaynağı." },
        { label: "Aux ADC", pins: ["ADIN"], tone: "analog", description: "Board-specific auxiliary ölçüm." },
        { label: "I2C", pins: ["SDAI", "SDAO", "SCL", "ADR0", "ADR1"], tone: "bus", description: "Register erişimi ve adres seçimi." },
        { label: "Alert", pins: ["ALERT"], tone: "control", description: "Fault/alert limitleri kullanılacaksa board hattı doğrulanmalıdır." },
      ],
    },
  },

  LMK04832: {
    part: "LMK04832",
    reviewedAt: "2026-06-28",
    scope: "TICS Pro export ile JESD204B clock jitter cleaner init akışı.",
    sources: [
      {
        label: "Texas Instruments LMK04832 datasheet",
        url: "https://www.ti.com/lit/ds/symlink/lmk04832.pdf",
      },
    ],
    overview:
      "Dual-loop PLL mimarisine sahip düşük jitter clock cleaner'dır. Spec2Code bu cihazda PLL/divider hesabı yapmaz; TICS Pro'da doğrulanmış 24-bit register word array'ini init sırasında sırayı bozmadan SPI üzerinden yazar.",
    keyFacts: [
      "SPI frame 24 bittir: R/W biti, 15-bit register adresi ve 8-bit data alanı MSB-first gönderilir.",
      "Write için R/W=0 olmalıdır; CS low tutulur, son bit sonrası CS rising edge ile word latch edilir.",
      "Datasheet genel olarak register'ların numerik sırada programlanmasını önerir; TICS Pro export sırası korunmalıdır.",
      "Internal VCO kullanılırken PLL2_N register'ları diğer PLL2 divider ayarlarından sonra yazılmalıdır; TICS Pro bunu sırada çözer.",
    ],
    configuration: [
      "TICS Pro'da clock tree, PLL1/PLL2, output formatları ve SYSREF ayarlarını oluştur.",
      "Export edilen hex register array'i cihaz konfigürasyon panelindeki TICS Pro alanına yapıştır.",
      "Generated driver array'i 3 byte SPI write olarak uygular; application code frekans hesabı veya register sort işlemi yapmaz.",
    ],
    registers: lmk04832Registers(),
    recipes: [
      {
        title: "TICS Pro ile deterministic init",
        goal: "Doğrulanmış clock tree ayarlarını karta taşımak.",
        steps: [
          "TICS Pro'da hedef input/output frekanslarını ve output formatlarını doğrula.",
          "Register export içindeki 24-bit hex word array'ini Spec2Code TICS alanına yapıştır.",
          "Generate sonrası driver init array sırasını TICS Pro export sırası ile karşılaştır.",
        ],
      },
      {
        title: "PLL2 kalibrasyon sırası",
        goal: "Internal VCO kullanılan tasarımlarda hatalı calibration sırasından kaçınmak.",
        steps: [
          "PLL2 power-down bitlerinin TICS export içinde doğru temizlendiğini kontrol et.",
          "PLL2_N / PLL2_N_CAL yazımlarının TICS Pro'nun verdiği sırada kaldığından emin ol.",
          "Spec2Code içinde array'i elle sort etme; generated driver export sırasını uygular.",
        ],
      },
    ],
    gotchas: [
      "Bu cihazda register listesi çok geniştir; manuel tek tek register edit etmek yerine TICS Pro export kullanılmalıdır.",
      "SPI hatları lock sırasında gereksiz toggle edilirse phase-noise davranışı etkilenebilir; paylaşımlı SPI bus'ta CS disiplinine dikkat et.",
      "Generated driver frekans doğrulaması yapmaz; clock plan doğrulaması TICS Pro ve board bring-up ölçümüyle yapılmalıdır.",
    ],
    codegenNotes: [
      "Spec2Code config.ticspro_registers listesindeki her word'ü üç byte olarak MSB-first gönderir.",
      "R/W biti write değilse backend validation error üretir.",
      "Test Bench manifest aynı cihazları canlı hedef debug operasyonları için listeler.",
    ],
    pinMap: {
      packageName: "LLP-64",
      view: "Fonksiyonel pin görünümü",
      verification: "TI LMK04832 datasheet pinout ve pin function tablolarındaki isimlerle kontrol edildi.",
      note: "Pin haritası clock/input/control gruplarını öne çıkarır; tüm supply pinleri package layout üzerinden ayrıca board seviyesinde kontrol edilmelidir.",
      pins: [
        { number: "18", name: "CS*", role: "SPI chip select", tone: "bus", side: "left" },
        { number: "19", name: "SCK", role: "SPI clock", tone: "bus", side: "left" },
        { number: "20", name: "SDIO", role: "SPI data / readback", tone: "bus", side: "left" },
        { number: "5", name: "RESET/GPO", role: "Reset input veya GPO", tone: "control", side: "left" },
        { number: "6", name: "SYNC/SYSREF_REQ", role: "SYNC veya SYSREF request", tone: "control", side: "left" },
        { number: "37", name: "CLKin0", role: "Reference clock input 0", tone: "analog", side: "right" },
        { number: "38", name: "CLKin0*", role: "Reference clock input 0 complement", tone: "analog", side: "right" },
        { number: "34", name: "CLKin1/Fin/FBCLKin", role: "Reference / feedback input", tone: "analog", side: "right" },
        { number: "43", name: "OSCin", role: "Oscillator input", tone: "analog", side: "right" },
        { number: "44", name: "OSCin*", role: "Oscillator input complement", tone: "analog", side: "right" },
        { name: "CLKout0..13", role: "Programmable device clock / SYSREF outputs", tone: "analog", side: "right" },
        { name: "Status_LD1/2", role: "Programmable status / lock detect", tone: "control", side: "right" },
      ],
      groups: [
        { label: "SPI", pins: ["CS*", "SCK", "SDIO"], tone: "bus", description: "24-bit register programming yolu." },
        { label: "Reference", pins: ["CLKin0", "CLKin0*", "CLKin1/Fin/FBCLKin", "OSCin", "OSCin*"], tone: "analog", description: "PLL reference ve oscillator girişleri." },
        { label: "Outputs", pins: ["CLKout0..13"], tone: "analog", description: "Device clock ve SYSREF output çiftleri." },
      ],
    },
  },

  LMX2820: {
    part: "LMX2820",
    reviewedAt: "2026-06-28",
    scope: "TICS Pro export ile RF synthesizer init ve VCO calibration akışı.",
    sources: [
      {
        label: "Texas Instruments LMX2820 datasheet",
        url: "https://www.ti.com/lit/ds/symlink/lmx2820.pdf",
      },
      {
        label: "Texas Instruments LMX2820 register map",
        url: "https://www.ti.com/lit/pdf/snau251",
      },
    ],
    overview:
      "22.6 GHz'e kadar geniş bant RF synthesizer'dır. PLL_N, fractional numerator/denominator, MASH ve VCO calibration gibi ayarlar uygulamaya çok bağlıdır; Spec2Code bu hesapları yapmaz, TICS Pro export array'ini güvenli init akışına çevirir.",
    keyFacts: [
      "SPI write frame 24 bittir: R/W=0, 7-bit register adresi ve 16-bit register data alanı gönderilir.",
      "Datasheet power-on sequence register'ların azalan sırada yazılmasını ve R0'ın son yazılmasını ister.",
      "İlk programlamadan sonra 10 ms beklenir ve R0 tekrar yazılarak VCO calibration stabil LDO/reference koşullarında tetiklenir.",
      "Birçok PLL register'ı double-buffered davranır; değişiklikler R0 yazıldığında etkinleşir.",
    ],
    configuration: [
      "TICS Pro'da output frequency, reference, MASH, SYSREF ve calibration ayarlarını tamamla.",
      "Export edilen register array'i Spec2Code TICS Pro alanına yapıştır; array sırası değiştirilmez.",
      "Generated init tüm array'i yazar, 10 ms bekler ve export içinde bulunan son R0 word'ünü tekrar yazar.",
    ],
    registers: lmx2820Registers(),
    recipes: [
      {
        title: "İlk power-on init",
        goal: "TICS Pro ayarlarını VCO calibration ile güvenli biçimde başlatmak.",
        steps: [
          "Power rail'lerin minimum çalışma seviyesine ulaştığından emin ol.",
          "TICS Pro export array'ini azalan register sırasıyla yapıştır; R0 sonlarda olmalıdır.",
          "Generated driver array'i yazar, 10 ms bekler ve R0'ı tekrar yazar.",
        ],
      },
      {
        title: "Frequency change",
        goal: "Yeni PLL ayarlarını runtime'da güvenli uygulamak.",
        steps: [
          "Yeni frekans için TICS Pro'dan ayrı bir register array üret.",
          "Double-buffered alanların R0 ile apply edildiğini dikkate al.",
          "Mute/lock detect davranışı application seviyesinde açıkça yönetilmelidir.",
        ],
      },
    ],
    gotchas: [
      "R0 final write sadece data write değildir; FCAL_EN=1 ise calibration trigger davranışı vardır.",
      "Export array içinde reserved register değerleri varsa elle silme; TI register map unlisted offsets konusunda uyarır.",
      "Analog PLL lock süresi, dijital VCO calibration süresine eklenir; init return eder etmez RF çıkışın final lock'ta olduğu varsayılmamalıdır.",
    ],
    codegenNotes: [
      "Descriptor LMX2820 için post-init 10 ms delay + son R0 rewrite kuralını taşır.",
      "Generated driver array write'larına ek olarak R0 tekrar write işlemini de uygular.",
      "Spec2Code frekans synthesis hesabı yapmaz; TICS Pro export word'leri kaynak kabul edilir.",
    ],
    pinMap: {
      packageName: "VQFN-48",
      view: "Fonksiyonel pin görünümü",
      verification: "TI LMX2820 datasheet Table 5-1 pin functions bilgisiyle kontrol edildi.",
      note: "RF ve reference pinleri AC coupling/termination gerektirir; pin map bağlantı ailelerini gösterir, matching network hesabı yerine geçmez.",
      pins: [
        { number: "39", name: "CS#", role: "SPI latch / chip select", tone: "bus", side: "left" },
        { number: "18", name: "SCK", role: "SPI clock", tone: "bus", side: "left" },
        { number: "19", name: "SDI", role: "SPI data input", tone: "bus", side: "left" },
        { number: "23", name: "MUXOUT", role: "SPI readback / mux output", tone: "control", side: "left" },
        { number: "1", name: "CE", role: "Chip enable", tone: "control", side: "left" },
        { number: "37", name: "MUTE", role: "Output buffer mute", tone: "control", side: "left" },
        { number: "8", name: "OSCIN_P", role: "Reference input +", tone: "analog", side: "right" },
        { number: "9", name: "OSCIN_N", role: "Reference input -", tone: "analog", side: "right" },
        { number: "28", name: "RFIN", role: "External VCO input", tone: "analog", side: "right" },
        { number: "30", name: "RFOUTA_N", role: "RF output A -", tone: "analog", side: "right" },
        { number: "31", name: "RFOUTA_P", role: "RF output A +", tone: "analog", side: "right" },
        { number: "25", name: "RFOUTB_N", role: "RF output B -", tone: "analog", side: "right" },
        { number: "26", name: "RFOUTB_P", role: "RF output B +", tone: "analog", side: "right" },
      ],
      groups: [
        { label: "SPI", pins: ["CS#", "SCK", "SDI", "MUXOUT"], tone: "bus", description: "Register programming ve readback yolu." },
        { label: "RF", pins: ["RFOUTA_N", "RFOUTA_P", "RFOUTB_N", "RFOUTB_P", "RFIN"], tone: "analog", description: "RF output/input ağı." },
        { label: "Control", pins: ["CE", "MUTE"], tone: "control", description: "Power ve output mute davranışı." },
      ],
    },
  },

  LMX1204: {
    part: "LMX1204",
    reviewedAt: "2026-06-28",
    scope: "TICS Pro export ile JESD clock/SYSREF buffer init akışı.",
    sources: [
      {
        label: "Texas Instruments LMX1204 datasheet",
        url: "https://www.ti.com/lit/ds/symlink/lmx1204.pdf",
      },
      {
        label: "Texas Instruments LMX1204 register map",
        url: "https://www.ti.com/lit/pdf/snau269",
      },
    ],
    overview:
      "Clock/SYSREF distribution, multiplier ve divider işlevleri için kullanılan JESD odaklı clock cihazıdır. Bazı reserved register güncellemeleri POR/reset sonrası gerekli olabilir; bu nedenle TICS Pro export'u kaynak kabul edilir.",
    keyFacts: [
      "SPI write frame 24 bittir: R/W=0, 7-bit address ve 16-bit data MSB-first gönderilir.",
      "Datasheet SPI için CPOL=0, CPHA=0 önerir ve SPI read/write hızını 2 MHz max olarak verir.",
      "Initial programming R0 RESET=1 ile başlar, sonra gerekli register'lar azalan adreste yazılır.",
      "TICS Pro export varsayılan olarak gerekli reserved register updates değerlerini içerir; bunlar elle ayıklanmamalıdır.",
    ],
    configuration: [
      "TICS Pro'da CLKIN, CLKOUT, SYSREFOUT, multiplier/divider ve output format ayarlarını oluştur.",
      "Export edilen hex register array'i Spec2Code TICS Pro alanına yapıştır.",
      "Generated driver 24-bit word'leri aynen yazar; LMX1204 için SPI clock prescaler kart tarafında 2 MHz sınırını aşmayacak şekilde doğrulanmalıdır.",
    ],
    registers: lmx1204Registers(),
    recipes: [
      {
        title: "Initial programming",
        goal: "POR/reset sonrası gerekli reserved updates dahil güvenli init yapmak.",
        steps: [
          "TICS Pro export'u R0 RESET=1 yazımıyla başlayacak şekilde al.",
          "Export edilen tüm word'leri Spec2Code alanına yapıştır; reserved görünen satırları silme.",
          "Generate sonrası driver init array eleman sayısını export count ile karşılaştır.",
        ],
      },
      {
        title: "Readback kullanımı",
        goal: "MUXOUT readback hattını paylaşımlı SPI bus'ta güvenli kullanmak.",
        steps: [
          "Readback gerekiyorsa MUXOUT pininin bus paylaşımını board seviyesinde doğrula.",
          "Readback sonrasında MUXOUT_EN kontrolüyle tri-state davranışı gerektiğinde application seviyesinde yönet.",
          "Spec2Code mevcut generated init yolunda readback API üretmez; init deterministic write-only kalır.",
        ],
      },
    ],
    gotchas: [
      "LMX1204 SPI max 2 MHz değerini aşma; hızlı SPI clock kullanan ortak bus'ta prescaler ayrıca kontrol edilmelidir.",
      "MUXOUT readback sonrası otomatik tri-state olmayabilir; paylaşımlı readback hattında bu kritik bir board kuralıdır.",
      "R0 yazımı multiplier calibration tetikleyebilir; init array sırası ve R0 içeriği TICS Pro'dan geldiği gibi kalmalıdır.",
    ],
    codegenNotes: [
      "Spec2Code LMX1204 için TICS Pro word'lerini write-only init sequence olarak üretir.",
      "Backend validation 24-bit word sınırını ve R/W write bitini kontrol eder.",
      "Reserved update satırları TICS Pro export'tan geldiğinde korunur; codegen bunları filtrelemez.",
    ],
    pinMap: {
      packageName: "VQFN-40",
      view: "Fonksiyonel pin görünümü",
      verification: "TI LMX1204 datasheet pin functions tablosundaki pin isimleriyle kontrol edildi.",
      note: "Clock/SYSREF pinleri diferansiyel çiftlerdir; pin map mantıksal grupları gösterir, layout/matching rehberi yerine geçmez.",
      pins: [
        { number: "10", name: "CS#", role: "SPI chip select", tone: "bus", side: "left" },
        { number: "8", name: "SCK", role: "SPI clock", tone: "bus", side: "left" },
        { number: "9", name: "SDI", role: "SPI data input", tone: "bus", side: "left" },
        { number: "1", name: "MUXOUT", role: "Readback / lock status mux output", tone: "control", side: "left" },
        { number: "6", name: "CLKIN_P", role: "Reference clock input +", tone: "analog", side: "right" },
        { number: "7", name: "CLKIN_N", role: "Reference clock input -", tone: "analog", side: "right" },
        { number: "14/15", name: "CLKOUT0_P/N", role: "Clock output 0 pair", tone: "analog", side: "right" },
        { number: "18/19", name: "CLKOUT1_P/N", role: "Clock output 1 pair", tone: "analog", side: "right" },
        { number: "32/33", name: "CLKOUT2_N/P", role: "Clock output 2 pair", tone: "analog", side: "right" },
        { number: "36/37", name: "CLKOUT3_N/P", role: "Clock output 3 pair", tone: "analog", side: "right" },
        { number: "11/12", name: "SYSREFOUT0_P/N", role: "SYSREF output 0 pair", tone: "analog", side: "right" },
        { number: "39/40", name: "SYSREFOUT3_N/P", role: "SYSREF output 3 pair", tone: "analog", side: "right" },
      ],
      groups: [
        { label: "SPI", pins: ["CS#", "SCK", "SDI", "MUXOUT"], tone: "bus", description: "Programming ve optional readback." },
        { label: "Clock", pins: ["CLKIN_P", "CLKIN_N", "CLKOUT0_P/N", "CLKOUT1_P/N", "CLKOUT2_N/P", "CLKOUT3_N/P"], tone: "analog", description: "Reference ve clock output çiftleri." },
        { label: "SYSREF", pins: ["SYSREFOUT0_P/N", "SYSREFOUT3_N/P"], tone: "analog", description: "JESD SYSREF output çiftleri." },
      ],
    },
  },

  LMX1205: {
    part: "LMX1205",
    reviewedAt: "2026-07-05",
    scope: "TICS Pro export ile 0.3-12.8 GHz JESD buffer/multiplier/divider init akışı.",
    sources: [
      {
        label: "Texas Instruments LMX1205 datasheet (SNAS850)",
        url: "https://www.ti.com/lit/ds/symlink/lmx1205.pdf",
      },
    ],
    overview:
      "0.3-12.8 GHz aralığında 4 clock + 4 SYSREF çıkışı ve LOGICLK/LOGISYSREF dağıtımı yapan JESD odaklı buffer/multiplier/divider cihazıdır. Register haritası LMX1204'ten tamamen farklıdır; datasheet ADVANCE INFORMATION (preproduction) statüsündedir, alanlar sonraki revizyonlarda değişebilir.",
    keyFacts: [
      "SPI frame 24 bittir: R/W (0=write, 1=read), 7-bit address ve 16-bit data MSB-first gönderilir (SNAS850 Fig. 5-1).",
      "SPI hızı max 20 MHz'dir (LMX1204'ün 10 katı); CPOL=0, CPHA=0 önerilir.",
      "Readback MUXOUT pininde otomatiktir: pin okuma işlemi sırasında kendiliğinden aktifleşir, işlem bitince otomatik tri-state olur — LMX1204'teki MUXOUT_SEL/R86 adımları bu parçada yoktur.",
      "READBACK_CTRL (R1 bit 3) reset 1'dir: yazılan register değerleri okunur; 0 yapılırsa dahili state-machine durumu okunur.",
      "Bring-up sırası (6.3.7): güç → RESET 1→0 toggle (arada ≥1 µs) → register programlama → son yazım DEV_IOPT_CTRL=0x6 (R55).",
      "Dahili sıcaklık sensörü: T[°C] = 0.65 × rb_TEMPSENSE − 351 (R31 bits 10:0; 6.3.2 Eq. 1).",
    ],
    configuration: [
      "TICS Pro'da CLKIN, CLKOUT, SYSREFOUT, LOGICLK ve buffer/multiplier/divider modunu oluştur; hex register export al.",
      "Export edilen array'i Spec2Code TICS Pro alanına yapıştır; RESET toggle ile başlayıp DEV_IOPT_CTRL=0x6 ile bittiğini doğrula (6.3.7 gereksinimi).",
      "Multiplier modunda R27 FCAL_EN=1 yazımı kalibrasyon tetikler (ilk kalibrasyon ~5 ms); 4.2 GHz üstünde MULT_HIPFD_EN R0 ile birlikte togglelanır.",
    ],
    registers: lmx1205Registers(),
    recipes: [
      {
        title: "Initial programming",
        goal: "POR sonrası SNAS850 6.3.7 sırasına uygun güvenli init yapmak.",
        steps: [
          "Besleme raylarından sonra ≥100 µs bekle (6.3.1); TICS Pro export'unu RESET 1→0 toggle ile başlat.",
          "Register'ları programla; reserved görünen multiplier satırlarını export'tan geldiği gibi koru (program değerleri reset değerlerinden farklı olabilir).",
          "Son yazım olarak DEV_IOPT_CTRL=0x6 (R55) gönder; multiplier modunda kalibrasyondan sonra 0x1'e çekilir (Table 7-45).",
        ],
      },
      {
        title: "Readback kullanımı",
        goal: "MUXOUT üzerinden register ve durum okumak.",
        steps: [
          "MUXOUT'u MISO'ya bağla; okuma frame'i R/W=1 ile gönderildiğinde pin otomatik aktifleşir, sonra tri-state olur.",
          "Multiplier modunda paylaşımlı bus'ta okuma öncesi LD_DIS=1 (R1 bit 4) yaz — MUXOUT aynı zamanda lock-detect çıkışıdır.",
          "rb_LOCK_DETECT (R37 bit 0), rb_TEMPSENSE (R31) ve rb_VER_ID (R32) Registers ekranından canlı okunabilir.",
        ],
      },
    ],
    gotchas: [
      "SNAS850 ADVANCE INFORMATION statüsündedir: register reset/alanları sonraki revizyonlarda değişebilir; silikonla doğrula.",
      "Multiplier-reserved register'larda önerilen program değerleri reset değerlerinden farklı olabilir (ör. R39/R40 alan 8:4 reset 0xE, program 0x16) — TICS Pro export'u kaynak kabul et, elle değer türetme.",
      "RESET biti bir sonraki register yazımında kendini temizler; açık 1→0 toggle ≥1 µs arayla önerilir.",
      "DEV_IOPT_CTRL=0x6 son yazımı atlanırsa akım optimizasyonu eksik kalır; tüm modlarda (powerdown dahil) zorunludur.",
    ],
    codegenNotes: [
      "Spec2Code LMX1205 için TICS Pro word'lerini write-only init sequence olarak üretir; multiplier_lock_detect operasyonu R37 bit 0'ı okur.",
      "Registers ekranı generic register_read/register_write ile 16-bit erişim sağlar; MUXOUT auto-readback sayesinde okuma koşulu yalnız pin bağlantısıdır.",
      "Backend validation 24-bit word sınırını ve R/W write bitini kontrol eder.",
    ],
    pinMap: {
      packageName: "VQFN-40 (RHA)",
      view: "Fonksiyonel pin görünümü",
      verification: "SNAS850 Table 4-1 / Figure 4-1 pin tablosuyla kontrol edildi.",
      note: "Clock/SYSREF pinleri diferansiyel çiftlerdir; pin map mantıksal grupları gösterir, layout/matching rehberi yerine geçmez. CE/hardware enable pini yoktur — güç kontrolü SPI üzerindendir (R0 POWERDOWN).",
      pins: [
        { number: "10", name: "CS#", role: "SPI chip select (aktif düşük, 200 Ω seri direnç)", tone: "bus", side: "left" },
        { number: "8", name: "SCK", role: "SPI clock", tone: "bus", side: "left" },
        { number: "9", name: "SDI", role: "SPI data input", tone: "bus", side: "left" },
        { number: "1", name: "MUXOUT", role: "Auto readback / multiplier lock status", tone: "control", side: "left" },
        { number: "2/3", name: "SYSREFREQ_P/N", role: "SYSREF request girişi (JESD204B/C)", tone: "analog", side: "left" },
        { number: "6/7", name: "CLKIN_P/N", role: "Reference clock girişi", tone: "analog", side: "right" },
        { number: "14/15", name: "CLKOUT0_N/P", role: "Clock output 0 çifti", tone: "analog", side: "right" },
        { number: "18/19", name: "CLKOUT1_N/P", role: "Clock output 1 çifti", tone: "analog", side: "right" },
        { number: "32/33", name: "CLKOUT2_N/P", role: "Clock output 2 çifti", tone: "analog", side: "right" },
        { number: "36/37", name: "CLKOUT3_N/P", role: "Clock output 3 çifti", tone: "analog", side: "right" },
        { number: "11/12", name: "SYSREFOUT0_N/P", role: "SYSREF output 0 çifti", tone: "analog", side: "right" },
        { number: "39/40", name: "SYSREFOUT3_N/P", role: "SYSREF output 3 çifti", tone: "analog", side: "right" },
        { number: "27/28", name: "LOGICLKOUT0_N/P", role: "Logic clock çifti (CML/LVDS)", tone: "analog", side: "right" },
        { number: "23/24", name: "LOGISYSREFOUT_N/P", role: "Logic SYSREF / LOGICLKOUT1 çifti", tone: "analog", side: "right" },
        { number: "20", name: "BIAS01", role: "Multiplier bypass (kullanılmıyorsa açık)", tone: "control", side: "left" },
        { number: "31", name: "BIAS23", role: "Multiplier bypass (kullanılmıyorsa açık)", tone: "control", side: "left" },
      ],
      groups: [
        { label: "SPI", pins: ["CS#", "SCK", "SDI", "MUXOUT"], tone: "bus", description: "Programming ve auto-readback." },
        { label: "Clock", pins: ["CLKIN_P/N", "CLKOUT0_N/P", "CLKOUT1_N/P", "CLKOUT2_N/P", "CLKOUT3_N/P"], tone: "analog", description: "Reference ve clock output çiftleri." },
        { label: "SYSREF", pins: ["SYSREFREQ_P/N", "SYSREFOUT0_N/P", "SYSREFOUT3_N/P"], tone: "analog", description: "JESD SYSREF request/output çiftleri." },
        { label: "Logic", pins: ["LOGICLKOUT0_N/P", "LOGISYSREFOUT_N/P"], tone: "analog", description: "FPGA logic clock/SYSREF çıkışları." },
      ],
    },
  },
};

export function getRegisterTransfers(part: string, reg: KnowledgeRegister): KnowledgeRegisterTransfer[] {
  const normalizedPart = part.toUpperCase();

  if (normalizedPart === "TCA9548A") {
    return [
      {
        title: "Select channel",
        access: "WRITE",
        txBytes: "1 byte",
        rxBytes: "0 byte",
        tx: ["(unsigned char)(1U << ucChannel)"],
        rx: ["-"],
        code: ["tca9548aChannelSelect(spIic, ucChannel);"],
        note: "Bu cihazda register address yok; gönderilen tek byte control byte'tır.",
      },
      {
        title: "Disable all",
        access: "WRITE",
        txBytes: "1 byte",
        rxBytes: "0 byte",
        tx: ["0x00U"],
        rx: ["-"],
        code: ["tca9548aChannelDisable(spIic);"],
      },
    ];
  }

  if (normalizedPart === "LMK04832" || normalizedPart === "LMX2820" || normalizedPart === "LMX1204" || normalizedPart === "LMX1205") {
    return ticsRegisterTransfer(normalizedPart, reg);
  }

  if (normalizedPart === "ADAR1000") {
    return adar1000RegisterTransfers(reg);
  }

  if (normalizedPart === "LTC2991") {
    if (/^V[1-8]_MSB$/.test(reg.name)) {
      const channel = Number(reg.name.slice(1, 2));
      return [
        {
          title: `Read V${channel}`,
          access: "READ",
          txBytes: "1 byte",
          rxBytes: "2 byte",
          tx: [`LTC2991_REG_V${channel}_MSB (${reg.address})`],
          rx: ["ucArrBytes[0]", "ucArrBytes[1]", `usV${channel}`],
          code: ["ltc2991VoltageRead(spIic, usArrVoltages);"],
          note: "Generated helper tum V1..V8 kanallarini okur; burada secilen channel icin MSB/LSB transfer formatı gosterilir.",
        },
      ];
    }

    switch (reg.name) {
      case "V1_MSB..V8_LSB":
        return [
          {
            title: "Read all channels",
            access: "READ",
            txBytes: "16 x 1 byte register pointer",
            rxBytes: "16 byte toplam (8 x MSB+LSB)",
            tx: ["LTC2991_REG_V1_MSB + (ucIndex * 2U)", "LTC2991_REG_V1_MSB + (ucIndex * 2U) + 1U"],
            rx: ["ucMsb", "ucLsb", "usArrVoltages[ucIndex]"],
            code: ["ltc2991VoltageRead(spIic, usArrVoltages);"],
          },
        ];
      case "T_INTERNAL":
      case "T_INTERNAL_MSB":
        return [
          {
            title: "Read internal temperature",
            access: "READ",
            txBytes: "2 x 1 byte register pointer",
            rxBytes: "2 byte",
            tx: ["LTC2991_REG_T_INTERNAL_MSB", "LTC2991_REG_T_INTERNAL_LSB"],
            rx: ["ucArrBytes[0]", "ucArrBytes[1]", "usTemperature"],
            code: ["ltc2991TemperatureRead(spIic, &usTemperature);"],
          },
        ];
      case "VCC":
      case "VCC_MSB":
        return [
          {
            title: "Read VCC",
            access: "READ",
            txBytes: "2 x 1 byte register pointer",
            rxBytes: "2 byte",
            tx: ["LTC2991_REG_VCC_MSB", "LTC2991_REG_VCC_LSB"],
            rx: ["ucArrBytes[0]", "ucArrBytes[1]", "usVcc"],
            code: ["ltc2991VccRead(spIic, &usVcc);"],
          },
        ];
      default:
        return i2cRegisterTransfers("LTC2991", reg.name, reg.address, reg.access, "ucValue");
    }
  }

  if (normalizedPart === "AD7414") {
    switch (reg.name) {
      case "TEMPERATURE":
        return [
          {
            title: "Read temperature",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: ["AD7414_REG_TEMPERATURE (0x00)"],
            rx: ["ucArrBytes[0]", "ucArrBytes[1]", "usTemperature"],
            code: ["ad7414TemperatureRead(spIic, &usTemperature);"],
          },
        ];
      case "CONFIGURATION":
        return [
          readonlyTransfer("AD7414", "CONFIGURATION", reg.address, "1 byte", ["ucConfig"], [
            "ad7414ConfigRead(spIic, &ucConfig);",
          ]),
          writeonlyTransfer("AD7414", "CONFIGURATION", reg.address, "ucConfig"),
        ];
      default:
        return i2cRegisterTransfers("AD7414", reg.name, reg.address, reg.access, "ucValue");
    }
  }

  if (normalizedPart === "TMP101") {
    switch (reg.name) {
      case "TEMPERATURE":
        return [
          {
            title: "Read temperature",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: ["TMP101_REG_TEMPERATURE (0x00)"],
            rx: ["ucArrBytes[0]", "ucArrBytes[1]", "usTemperature"],
            code: ["tmp101TemperatureRead(spIic, &usTemperature);"],
            note: "İki byte MSB-first okunur; TEMP[11:0] üst 12 bittir, alt dört bit zero-pad.",
          },
        ];
      case "CONFIGURATION":
        return [
          readonlyTransfer("TMP101", "CONFIGURATION", reg.address, "1 byte", ["ucConfig"], [
            "tmp101ConfigRead(spIic, &ucConfig);",
          ]),
          writeonlyTransfer("TMP101", "CONFIGURATION", reg.address, "ucConfig"),
        ];
      case "TLOW":
      case "THIGH":
        return [
          {
            title: "Read threshold",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: [`TMP101_REG_${reg.name} (${reg.address})`],
            rx: ["ucArrBytes[0]", "ucArrBytes[1]"],
            code: [`tmp101RegistersRead(spIic, TMP101_REG_${reg.name}, ucArrBytes, 2U);`],
            note: "Threshold image temperature register ile aynı 12-bit two's-complement formattadır.",
          },
          {
            title: "Write threshold",
            access: "WRITE",
            txBytes: "3 byte",
            rxBytes: "0 byte",
            tx: [`TMP101_REG_${reg.name} (${reg.address})`, "ucMsb", "ucLsb"],
            rx: ["-"],
            code: [`tmp101RegisterWrite(spIic, TMP101_REG_${reg.name}, ucMsb);`, "/* LSB için block write helper gerekir; generated minimal API threshold write üretmez. */"],
            note: "Generated default API threshold write üretmez; iki data byte aynı pointer transaction içinde gönderilmelidir.",
            tone: "warn",
          },
        ];
      default:
        return i2cRegisterTransfers("TMP101", reg.name, reg.address, reg.access, "ucValue");
    }
  }

  if (normalizedPart === "SHT21") {
    if (reg.name === "TRIGGER_T_HOLD" || reg.name === "TRIGGER_T_NO_HOLD") {
      return [
        {
          title: reg.name.endsWith("NO_HOLD") ? "No-hold temperature read" : "Hold-master temperature read",
          access: "READ",
          txBytes: "1 byte",
          rxBytes: "3 byte",
          tx: [`SHT21_REG_${reg.name} (${reg.address})`],
          rx: ["ucArrBytes[0] MSB", "ucArrBytes[1] LSB/status", "ucArrBytes[2] CRC8"],
          code: ["sht21TemperatureRead(spIic, &uiTemperature);"],
          note: reg.name.endsWith("NO_HOLD")
            ? "No-hold modda command sonrası read address ACK gelene kadar polling gerekir; generated helper hold-master path kullanır."
            : "Hold-master modda sensör ölçüm bitene kadar SCL hattını tutabilir.",
        },
      ];
    }
    if (reg.name === "TRIGGER_RH_HOLD" || reg.name === "TRIGGER_RH_NO_HOLD") {
      return [
        {
          title: reg.name.endsWith("NO_HOLD") ? "No-hold humidity read" : "Hold-master humidity read",
          access: "READ",
          txBytes: "1 byte",
          rxBytes: "3 byte",
          tx: [`SHT21_REG_${reg.name} (${reg.address})`],
          rx: ["ucArrBytes[0] MSB", "ucArrBytes[1] LSB/status", "ucArrBytes[2] CRC8"],
          code: ["sht21HumidityRead(spIic, &uiHumidity);"],
          note: reg.name.endsWith("NO_HOLD")
            ? "No-hold modda command sonrası read address ACK gelene kadar polling gerekir; generated helper hold-master path kullanır."
            : "Hold-master modda sensör ölçüm bitene kadar SCL hattını tutabilir.",
        },
      ];
    }
    if (reg.name === "USER_REGISTER") {
      return [
        {
          title: "Read user register",
          access: "READ",
          txBytes: "1 byte",
          rxBytes: "1 byte",
          tx: ["SHT21_REG_USER_REGISTER_READ (0xE7)"],
          rx: ["ucUser"],
          code: ["sht21UserRegisterRead(spIic, &ucUser);"],
          note: "Reserved bitleri korumak için write öncesinde bu byte okunmalıdır.",
        },
        {
          title: "Write user register",
          access: "WRITE",
          txBytes: "2 byte",
          rxBytes: "0 byte",
          tx: ["SHT21_REG_USER_REGISTER_WRITE (0xE6)", "ucUser"],
          rx: ["-"],
          code: ["sht21RegisterWrite(spIic, SHT21_REG_USER_REGISTER_WRITE, ucUser);"],
          note: "Reserved bitler önceki read değerinden korunmalıdır.",
        },
      ];
    }
    if (reg.name === "SOFT_RESET") {
      return [
        {
          title: "Soft reset",
          access: "WRITE",
          txBytes: "1 byte",
          rxBytes: "0 byte",
          tx: ["SHT21_REG_SOFT_RESET (0xFE)"],
          rx: ["-"],
          code: ["/* command-only transfer: send 0xFE, payload yok; reset < 15 ms sürer. */"],
          note: "Generated default init bunu otomatik göndermez; application reset istiyorsa command-only helper eklenmelidir.",
          tone: "warn",
        },
      ];
    }
    return i2cRegisterTransfers("SHT21", reg.name, reg.address, reg.access, "ucValue");
  }

  if (normalizedPart === "24LC32A") {
    switch (reg.name) {
      case "CONTROL_BYTE":
        return [
          {
            title: "Control byte",
            access: "READ/WRITE",
            txBytes: "1 byte header",
            rxBytes: "operation'a bağlı",
            tx: ["1010 A2 A1 A0 R/W"],
            rx: ["ACK/NACK"],
            code: ["/* XIicPs 7-bit address olarak 0x50..0x57 kullanılır; R/W bitini controller üretir. */"],
            note: "Firmware API'sinde 7-bit I2C address kullanılır; datasheet control byte bu adresin wire-level gösterimidir.",
          },
        ];
      case "WORD_ADDRESS":
      case "RANDOM_READ":
        return [
          {
            title: "Random/block read",
            access: "READ",
            txBytes: "2 byte address",
            rxBytes: "uiLength byte",
            tx: ["(uiAddress >> 8) & 0x0F", "uiAddress & 0xFF"],
            rx: ["ucArrBuffer[0..uiLength-1]"],
            code: ["dev24lc32aDataRead(spIic, uiAddress, ucArrBuffer, uiLength);"],
            note: "Write-address phase pointer'ı kurar; repeated-start/read phase data byte'larını alır.",
          },
        ];
      case "SEQUENTIAL_READ":
        return [
          {
            title: "Sequential read",
            access: "READ",
            txBytes: "2 byte start address",
            rxBytes: "N byte",
            tx: ["A11:A8", "A7:A0"],
            rx: ["DATA[0..N-1]"],
            code: ["dev24lc32aDataRead(spIic, uiAddress, ucArrBuffer, uiLength);"],
            note: "EEPROM ACK gördükçe sonraki adresi gönderir; son byte'ta master NACK + STOP üretir.",
          },
        ];
      case "BYTE_WRITE":
        return [
          {
            title: "Byte write",
            access: "WRITE",
            txBytes: "3 byte",
            rxBytes: "0 byte",
            tx: ["A11:A8", "A7:A0", "ucValue"],
            rx: ["-"],
            code: ["dev24lc32aByteWrite(spIic, uiAddress, ucValue);"],
            note: "STOP sonrası internal write cycle başlar; generated helper ACK polling yapar.",
          },
        ];
      case "PAGE_WRITE":
        return [
          {
            title: "Page write",
            access: "WRITE",
            txBytes: "2 byte address + 1..32 data byte",
            rxBytes: "0 byte",
            tx: ["A11:A8", "A7:A0", "ucpBuffer[0..uiLength-1]"],
            rx: ["-"],
            code: ["dev24lc32aPageWrite(spIic, uiAddress, ucpBuffer, uiLength);"],
            note: "Generated helper page boundary aşımını reddeder; datasheet aksi halde current page başına wrap edeceğini belirtir.",
            tone: "warn",
          },
        ];
      case "ACK_POLL":
        return [
          {
            title: "ACK polling",
            access: "READ",
            txBytes: "control byte write denemesi",
            rxBytes: "ACK/NACK",
            tx: ["1010 A2 A1 A0 W"],
            rx: ["ACK: ready", "NACK: write cycle busy"],
            code: ["/* dev24lc32aByteWrite/PageWrite içinde internal ack poll helper çağrılır. */"],
            note: "Write cycle sırasında EEPROM ACK üretmez; ACK döndüğünde bir sonraki operasyon güvenlidir.",
          },
        ];
      default:
        return [];
    }
  }

  if (normalizedPart === "DS1682") {
    switch (reg.name) {
      case "CONFIGURATION":
        return [
          readonlyTransfer("DS1682", "CONFIGURATION", reg.address, "1 byte", ["ucConfig"], [
            "ds1682ConfigRead(spIic, &ucConfig);",
          ]),
          writeonlyTransfer("DS1682", "CONFIGURATION", reg.address, "ucConfig"),
        ];
      case "ALARM":
      case "ALARM_LOW":
        return [
          {
            title: "Read alarm",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "4 byte",
            tx: ["DS1682_REG_ALARM_LOW (0x01)"],
            rx: ["ucArrBytes[0..3]", "uiAlarm"],
            code: ["ds1682AlarmRead(spIic, &uiAlarm);"],
          },
          i2cGroupedWriteTransfer("DS1682", "ALARM_LOW", "0x01", 4, "ucArrAlarm", {
            title: "Write alarm",
            note: "Alarm değeri little-endian byte sırasıyla ALARM_LOW..ALARM_HIGH alanlarına yazılır.",
          }),
        ];
      case "ETC":
      case "ETC_LOW":
        return [
          {
            title: "Read elapsed time",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "4 byte",
            tx: ["DS1682_REG_ETC_LOW (0x05)"],
            rx: ["ucArrBytes[0..3]", "uiElapsed"],
            code: ["ds1682ElapsedRead(spIic, &uiElapsed);"],
          },
        ];
      case "EVENT":
      case "EVENT_LOW":
      case "EVENT_HIGH":
        return [
          {
            title: "Read event counter",
            access: "READ",
            txBytes: "3 x 1 byte register pointer",
            rxBytes: "3 byte",
            tx: ["DS1682_REG_CONFIGURATION", "DS1682_REG_EVENT_LOW", "DS1682_REG_EVENT_HIGH"],
            rx: ["CONFIGURATION[0]", "EVENT_LOW", "EVENT_HIGH", "uiEvent"],
            code: ["ds1682EventRead(spIic, &uiEvent);"],
          },
        ];
      case "USER EEPROM":
      case "USER_1":
        return [
          i2cBlockReadTransfer("DS1682", "USER_1", "0x0B", 10, "ucArrUser"),
          i2cGroupedWriteTransfer("DS1682", "USER_1", "0x0B", 10, "ucArrUser", {
            note: "EEPROM endurance ve write timing uygulama seviyesinde yönetilmelidir.",
          }),
        ];
      case "RESET_COMMAND":
        return [
          {
            title: "Reset command",
            access: "WRITE",
            txBytes: "2 x 2 byte",
            rxBytes: "0 byte",
            tx: ["DS1682_REG_RESET_COMMAND (0x1D)", "0x55U", "tekrar: 0x55U"],
            rx: ["-"],
            code: [
              "ds1682RegisterWrite(spIic, DS1682_REG_RESET_COMMAND, 0x55U);",
              "ds1682RegisterWrite(spIic, DS1682_REG_RESET_COMMAND, 0x55U);",
            ],
            note: "CONFIGURATION.RE=1 olmadan kabul edilmez; normal smoke test içinde çalıştırılmamalıdır.",
            tone: "danger",
          },
        ];
      case "WRITE_DISABLE":
        return [
          {
            title: "Write-disable command",
            access: "WRITE",
            txBytes: "2 x 2 byte",
            rxBytes: "0 byte",
            tx: ["DS1682_REG_WRITE_DISABLE (0x1E)", "0xAAU", "tekrar: 0xAAU"],
            rx: ["-"],
            code: [
              "ds1682RegisterWrite(spIic, DS1682_REG_WRITE_DISABLE, 0xAAU);",
              "ds1682RegisterWrite(spIic, DS1682_REG_WRITE_DISABLE, 0xAAU);",
            ],
            note: "WDF set eder; production-only işlem gibi ele alınmalıdır.",
            tone: "danger",
          },
        ];
      case "WRITE_MEMORY_DISABLE":
        return [
          {
            title: "Write-memory-disable command",
            access: "WRITE",
            txBytes: "2 x 2 byte",
            rxBytes: "0 byte",
            tx: ["DS1682_REG_WRITE_MEMORY_DISABLE (0x1F)", "0xF0U", "tekrar: 0xF0U"],
            rx: ["-"],
            code: [
              "ds1682RegisterWrite(spIic, DS1682_REG_WRITE_MEMORY_DISABLE, 0xF0U);",
              "ds1682RegisterWrite(spIic, DS1682_REG_WRITE_MEMORY_DISABLE, 0xF0U);",
            ],
            note: "WMDF set eder; user EEPROM alanını read-only hale getirir.",
            tone: "danger",
          },
        ];
      default:
        return i2cRegisterTransfers("DS1682", reg.name, reg.address, reg.access, "ucValue");
    }
  }

  if (normalizedPart === "LTC2945") {
    switch (reg.name) {
      case "STATUS":
        return [
          readonlyTransfer("LTC2945", "STATUS", reg.address, "1 byte", ["ucStatus"], [
            "ltc2945StatusRead(spIic, &ucStatus);",
          ]),
        ];
      case "POWER":
      case "POWER_MSB2":
        return [
          {
            title: "Read power",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "3 byte",
            tx: ["LTC2945_REG_POWER_MSB2 (0x05)"],
            rx: ["ucArrBytes[0..2]", "uiPower"],
            code: ["ltc2945PowerRead(spIic, &uiPower);"],
          },
        ];
      case "SENSE":
      case "SENSE_MSB":
        return [
          {
            title: "Read sense",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: ["LTC2945_REG_SENSE_MSB (0x14)"],
            rx: ["ucArrBytes[0..1]", "usSense"],
            code: ["ltc2945SenseRead(spIic, &usSense);"],
          },
        ];
      case "VIN":
      case "VIN_MSB":
        return [
          {
            title: "Read VIN",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: ["LTC2945_REG_VIN_MSB (0x1E)"],
            rx: ["ucArrBytes[0..1]", "usVoltage"],
            code: ["ltc2945VoltageRead(spIic, &usVoltage);"],
          },
        ];
      case "ADIN":
      case "ADIN_MSB":
        return [
          {
            title: "Read ADIN",
            access: "READ",
            txBytes: "1 byte",
            rxBytes: "2 byte",
            tx: ["LTC2945_REG_ADIN_MSB (0x28)"],
            rx: ["ucArrBytes[0..1]", "usAdin"],
            code: ["ltc2945AdinRead(spIic, &usAdin);"],
          },
        ];
      default:
        return i2cRegisterTransfers("LTC2945", reg.name, reg.address, reg.access, "ucValue");
    }
  }

  if (normalizedPart === "MT25Q128" || normalizedPart === "MT25QU02G") {
    const isLargeFlash = normalizedPart === "MT25QU02G";
    const handle = isLargeFlash ? "spQspi" : "spSpi";
    const addrBytes = isLargeFlash ? 4 : 3;
    const addrLabel = isLargeFlash ? "A31:A0" : "A23:A0";

    switch (reg.name) {
      case "READ_ID":
        return [
          flashReadTransfer(part, "READ_ID", "0x9F", 0, "3 byte", ["ucArrId[0..2]"], [
            `${cFunc(part, "id_read")}(${handle}, ucArrId);`,
          ]),
        ];
      case "READ_STATUS":
        return [
          flashReadTransfer(part, "READ_STATUS", "0x05", 0, "1 byte", ["ucStatus"], [
            `${cFunc(part, "command_read")}(${handle}, ${cmdMacro(part, "READ_STATUS")}, 0U, 0U, &ucStatus, 1U);`,
          ]),
        ];
      case "WRITE_ENABLE":
        return [
          flashWriteTransfer(part, "WRITE_ENABLE", "0x06", 0, "", [
            `${cFunc(part, "command_send")}(${handle}, ${cmdMacro(part, "WRITE_ENABLE")});`,
          ], {
            title: "Send command",
            note: "Program/erase/config write öncesinde WEL bitini set eder.",
          }),
        ];
      case "ENTER_4BYTE":
        return [
          flashWriteTransfer(part, "ENTER_4BYTE", "0xB7", 0, "", [
            `${cFunc(part, "command_send")}(${handle}, ${cmdMacro(part, "ENTER_4BYTE")});`,
          ], {
            title: "Send command",
            note: "MT25QU02G device_init akışı önce WRITE_ENABLE, sonra ENTER_4BYTE gönderir.",
          }),
        ];
      case "READ_DATA_4B":
      case "READ_DATA":
        return [
          flashReadTransfer(part, "READ_DATA", isLargeFlash ? "0x13" : "0x03", addrBytes, "uiLength byte", ["ucpBuffer[0..uiLength-1]"], [
            `${cFunc(part, "data_read")}(${handle}, uiAddress, ucpBuffer, uiLength);`,
          ], {
            txBytes: `${1 + addrBytes} byte (${addrLabel})`,
          }),
        ];
      case "PAGE_PROGRAM_4B":
      case "PAGE_PROGRAM":
        return [
          flashWriteTransfer(part, "PAGE_PROGRAM", isLargeFlash ? "0x12" : "0x02", addrBytes, "ucpData[0..uiLength-1]", [
            `${cFunc(part, "page_program")}(${handle}, uiAddress, ucpData, uiLength);`,
          ], {
            txBytes: `${1 + addrBytes} byte (${addrLabel}) + uiLength byte payload`,
            note: "Public function program öncesinde WRITE_ENABLE gönderir; page boundary uygulama tarafından korunmalıdır.",
          }),
        ];
      case "ERASE_4B":
      case "SUBSECTOR/SECTOR_ERASE":
        return [
          flashWriteTransfer(part, "SECTOR_ERASE", isLargeFlash ? "0xDC" : "0xD8", addrBytes, "", [
            `${cFunc(part, "sector_erase")}(${handle}, uiAddress);`,
          ], {
            title: "Erase 64 KB sector",
            txBytes: `${1 + addrBytes} byte (${addrLabel})`,
            note: "Public function erase öncesinde WRITE_ENABLE gönderir.",
            tone: "warn",
          }),
          flashWriteTransfer(part, "SUBSECTOR_ERASE", isLargeFlash ? "0x21" : "0x20", addrBytes, "", [
            `${cFunc(part, "command_write")}(${handle}, ${cmdMacro(part, "SUBSECTOR_ERASE")}, uiAddress, ${addrBytes}U, NULL, 0U);`,
          ], {
            title: "Erase 4 KB subsector",
            txBytes: `${1 + addrBytes} byte (${addrLabel})`,
            note: "Bu raw helper formatıdır; mevcut public operation yalnızca 64 KB sector erase üretir.",
            tone: "warn",
          }),
        ];
      default:
        return genericFlashTransfers(part, reg, handle, addrBytes);
    }
  }

  return [];
}

export function getDeviceKnowledge(part: string): DeviceKnowledgePack | undefined {
  return PACKS[part.toUpperCase()];
}

export function listDeviceKnowledge(): DeviceKnowledgePack[] {
  return Object.values(PACKS).sort((a, b) => a.part.localeCompare(b.part));
}

export function hasDeviceKnowledge(part: string): boolean {
  return Boolean(getDeviceKnowledge(part));
}
