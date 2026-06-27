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
  return part.toLowerCase().replace(/[^a-z0-9]/g, "");
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

  if (normalized === "RO" || normalized === "RW" || normalized === "COR") {
    transfers.push(
      readonlyTransfer(part, reg, address, "1 byte", [valueName], [
        `${cFunc(part, "register_read")}(spIic, ${regMacro(part, reg)}, &${valueName});`,
      ], {
        title: normalized === "COR" ? "Read + clear" : "Read",
        note: normalized === "COR" ? "Okuma sonrası latched clear davranışı vardır." : undefined,
      }),
    );
  }

  if (normalized === "WO" || normalized === "RW") {
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

const PACKS: Record<string, DeviceKnowledgePack> = {
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
    registers: [
      {
        name: "STATUS_LOW",
        address: "0x00",
        width: "8",
        access: "RO",
        reset: "0x00",
        purpose: "Harici kanal dönüşümleri için busy/status bitleri.",
        fields: [
          { bits: "B7", name: "V8 ready", meaning: "V8 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B6", name: "V7 ready", meaning: "V7 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B5", name: "V6 ready", meaning: "V6 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B4", name: "V5 ready", meaning: "V5 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B3", name: "V4 ready", meaning: "V4 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B2", name: "V3 ready", meaning: "V3 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B1", name: "V2 ready", meaning: "V2 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B0", name: "V1 ready", meaning: "V1 sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
        ],
      },
      {
        name: "STATUS_HIGH",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "V1/V2, V3/V4, V5/V6, V7/V8, iç sıcaklık ve VCC ölçümlerini enable eder.",
        fields: [
          { bits: "B7", name: "V7/V8/TR4 enable", meaning: "V7/V8 pair veya TR4 ölçüm grubunu enable eder.", values: disabledEnabledValues },
          { bits: "B6", name: "V5/V6/TR3 enable", meaning: "V5/V6 pair veya TR3 ölçüm grubunu enable eder.", values: disabledEnabledValues },
          { bits: "B5", name: "V3/V4/TR2 enable", meaning: "V3/V4 pair veya TR2 ölçüm grubunu enable eder.", values: disabledEnabledValues },
          { bits: "B4", name: "V1/V2/TR1 enable", meaning: "V1/V2 pair veya TR1 ölçüm grubunu enable eder.", values: disabledEnabledValues },
          { bits: "B3", name: "T_INT/VCC enable", meaning: "İç sıcaklık ve VCC dönüşümlerini enable eder.", values: disabledEnabledValues },
          { bits: "B2", name: "Busy", meaning: "Conversion devam ederken set olan read-only busy biti.", values: ["0: sleep/idle / varsayılan", "1: conversion devam ediyor"] },
          { bits: "B1", name: "T_INT ready", meaning: "İç sıcaklık sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
          { bits: "B0", name: "VCC ready", meaning: "VCC sonucunda yeni data hazır olduğunu gösterir.", values: oldNewDataValues },
        ],
      },
      {
        name: "CONTROL_V1V4",
        address: "0x06",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "V1/V2 ve V3/V4 pair mode bitleri.",
        fields: [
          { bits: "B7", name: "V3/V4 filter", meaning: "V3/V4 ölçüm grubunda dijital filter ayarını belirler.", values: filterValues },
          { bits: "B6", name: "TR2 Kelvin", meaning: "TR2 remote temperature sonucu için Celsius/Kelvin formatını seçer.", values: celsiusKelvinValues },
          { bits: "B5", name: "V3/V4 temperature", meaning: "V3/V4 pair'ini remote temperature ölçümü için kullanır.", values: voltageTemperatureValues },
          { bits: "B4", name: "V3/V4 differential", meaning: "V3/V4 pair'ini differential voltage/current ölçüm yolu olarak kullanır.", values: singleEndedDifferentialValues },
          { bits: "B3", name: "V1/V2 filter", meaning: "V1/V2 ölçüm grubunda dijital filter ayarını belirler.", values: filterValues },
          { bits: "B2", name: "TR1 Kelvin", meaning: "TR1 remote temperature sonucu için Celsius/Kelvin formatını seçer.", values: celsiusKelvinValues },
          { bits: "B1", name: "V1/V2 temperature", meaning: "V1/V2 pair'ini remote temperature ölçümü için kullanır.", values: voltageTemperatureValues },
          { bits: "B0", name: "V1/V2 differential", meaning: "V1/V2 pair'ini differential voltage/current ölçüm yolu olarak kullanır.", values: singleEndedDifferentialValues },
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
          { bits: "B7", name: "V7/V8 filter", meaning: "V7/V8 ölçüm grubunda dijital filter ayarını belirler.", values: filterValues },
          { bits: "B6", name: "TR4 Kelvin", meaning: "TR4 remote temperature sonucu için Celsius/Kelvin formatını seçer.", values: celsiusKelvinValues },
          { bits: "B5", name: "V7/V8 temperature", meaning: "V7/V8 pair'ini remote temperature ölçümü için kullanır.", values: voltageTemperatureValues },
          { bits: "B4", name: "V7/V8 differential", meaning: "V7/V8 pair'ini differential voltage/current ölçüm yolu olarak kullanır.", values: singleEndedDifferentialValues },
          { bits: "B3", name: "V5/V6 filter", meaning: "V5/V6 ölçüm grubunda dijital filter ayarını belirler.", values: filterValues },
          { bits: "B2", name: "TR3 Kelvin", meaning: "TR3 remote temperature sonucu için Celsius/Kelvin formatını seçer.", values: celsiusKelvinValues },
          { bits: "B1", name: "V5/V6 temperature", meaning: "V5/V6 pair'ini remote temperature ölçümü için kullanır.", values: voltageTemperatureValues },
          { bits: "B0", name: "V5/V6 differential", meaning: "V5/V6 pair'ini differential voltage/current ölçüm yolu olarak kullanır.", values: singleEndedDifferentialValues },
        ],
      },
      {
        name: "V1_MSB..V8_LSB",
        address: "0x0A..0x19",
        width: "her biri 16",
        access: "RO",
        purpose: "Harici girişler için raw ölçüm sonuç register'ları.",
        fields: [
          { bits: "Voltage/current MSB B7", name: "Data valid", meaning: "İlgili conversion sonucunda yeni data hazır olduğunda set olur.", values: oldNewDataValues },
          { bits: "Voltage/current MSB B6", name: "Sign", meaning: "Signed voltage/current ölçüm formatlarında işaret bitidir.", values: signValues },
          { bits: "Voltage/current MSB B5:B0", name: "D13:D8", meaning: "14-bit raw conversion sonucunun üst data bitleri." },
          { bits: "Temperature/diode MSB B7", name: "Data valid", meaning: "Remote temperature veya diode-voltage sonucunda yeni data hazır olduğunda set olur.", values: oldNewDataValues },
          { bits: "Temperature/diode MSB B6:B5", name: "Unused", meaning: "13-bit temperature/diode-voltage formatında kullanılmaz.", values: unusedValues },
          { bits: "Temperature/diode MSB B4:B0", name: "D12:D8", meaning: "13-bit raw temperature veya diode-voltage sonucunun üst data bitleri." },
          { bits: "LSB B7:B0", name: "D7:D0", meaning: "Raw conversion sonucunun alt data bitleri." },
        ],
      },
      {
        name: "T_INTERNAL",
        address: "0x1A..0x1B",
        width: "16",
        access: "RO",
        purpose: "Raw iç sıcaklık sonucu.",
        fields: [
          { bits: "MSB B7", name: "Data valid", meaning: "İç sıcaklık conversion sonucunda yeni data hazır olduğunda set olur.", values: oldNewDataValues },
          { bits: "MSB B6:B5", name: "Unused", meaning: "13-bit temperature formatında kullanılmaz.", values: unusedValues },
          { bits: "MSB B4:B0", name: "D12:D8", meaning: "İç sıcaklık için raw conversion code üst data bitleri." },
          { bits: "LSB B7:B0", name: "D7:D0", meaning: "İç sıcaklık için raw conversion code alt data bitleri." },
        ],
      },
      {
        name: "VCC",
        address: "0x1C..0x1D",
        width: "16",
        access: "RO",
        purpose: "Raw VCC ölçüm sonucu.",
        fields: [
          { bits: "MSB B7", name: "Data valid", meaning: "VCC conversion sonucunda yeni data hazır olduğunda set olur.", values: oldNewDataValues },
          { bits: "MSB B6", name: "Sign", meaning: "VCC measurement formatındaki sign bitidir; datasheet formatında VCC = result + 2.5V olarak yorumlanır.", values: signValues },
          { bits: "MSB/LSB data", name: "VCC code", meaning: "VCC için raw conversion code; mühendislik birimine çeviri datasheet formülüne bırakılır." },
        ],
      },
    ],
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
    registers: [
      {
        name: "READ_ID",
        address: "0x9F",
        width: "opcode",
        access: "RO",
        purpose: "JEDEC manufacturer/device identification bilgisini okumak.",
        fields: flashReadIdFields,
      },
      {
        name: "READ_STATUS",
        address: "0x05",
        width: "opcode",
        access: "RO",
        purpose: "Status register okumak; özellikle WIP/busy durumunu takip etmek.",
        fields: flashStatusFields,
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Program/erase operasyonlarından önce write enable latch etmek.",
        fields: [
          { bits: "Opcode", name: "0x06", meaning: "Write Enable komutu." },
          { bits: "Yan etki", name: "WEL=1", meaning: "Başarılı komut sonrası status register içindeki WEL biti set olur." },
        ],
      },
      {
        name: "READ_DATA",
        address: "0x03",
        width: "opcode + 24-bit address",
        access: "RO",
        purpose: "Konservatif array read command.",
        fields: [
          { bits: "Opcode", name: "0x03", meaning: "Single-SPI normal read komutu." },
          { bits: "A23:A0", name: "24-bit address", meaning: "Okumanın başlayacağı byte adresi." },
          { bits: "Data stream", name: "MISO bytes", meaning: "Adres sonrası ardışık memory byte'ları okunur." },
        ],
      },
      {
        name: "PAGE_PROGRAM",
        address: "0x02",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "Write enable sonrası en fazla bir page programlamak.",
        fields: [
          { bits: "Opcode", name: "0x02", meaning: "Page Program komutu." },
          { bits: "A23:A0", name: "24-bit address", meaning: "Programlamanın başlayacağı page içi adres." },
          { bits: "Payload", name: "1..256 byte", meaning: "Tek page sınırı içinde programlanacak data byte'ları." },
        ],
      },
      {
        name: "SUBSECTOR/SECTOR_ERASE",
        address: "0x20 / 0xD8",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "4 KB subsector veya 64 KB sector erase yapmak.",
        fields: [
          { bits: "Opcode", name: "0x20", meaning: "4 KB subsector erase komutu." },
          { bits: "Opcode", name: "0xD8", meaning: "64 KB sector erase komutu." },
          { bits: "A23:A0", name: "24-bit address", meaning: "Erase edilecek subsector/sector içinde herhangi bir adres." },
        ],
      },
    ],
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
    registers: [
      {
        name: "READ_ID",
        address: "0x9F",
        width: "opcode",
        access: "RO",
        purpose: "JEDEC ID okumak ve cihazın erişilebilir olduğunu doğrulamak.",
        fields: flashReadIdFields,
      },
      {
        name: "READ_STATUS",
        address: "0x05",
        width: "opcode",
        access: "RO",
        purpose: "Status register okumak; özellikle WIP/busy ve WEL durumlarını takip etmek.",
        fields: flashStatusFields,
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Mode enter, program ve erase akışlarından önce gereklidir.",
        fields: [
          { bits: "Opcode", name: "0x06", meaning: "Write Enable komutu." },
          { bits: "Yan etki", name: "WEL=1", meaning: "Başarılı komut sonrası status register içindeki WEL biti set olur." },
        ],
      },
      {
        name: "ENTER_4BYTE",
        address: "0xB7",
        width: "opcode",
        access: "WO",
        purpose: "Yüksek adres aralığı için 4-byte address mode'a geçmek.",
        fields: [
          { bits: "Opcode", name: "0xB7", meaning: "4-byte address mode'a geçiş komutu." },
          { bits: "Yan etki", name: "32-bit addressing", meaning: "Sonraki full-range erişimler 4-byte adres komutlarıyla uyumlu hale gelir." },
        ],
      },
      {
        name: "READ_DATA_4B",
        address: "0x13",
        width: "opcode + 32-bit address",
        access: "RO",
        purpose: "4-byte address ile array data okumak.",
        fields: [
          { bits: "Opcode", name: "0x13", meaning: "4-byte address normal read komutu." },
          { bits: "A31:A0", name: "32-bit address", meaning: "Okumanın başlayacağı byte adresi." },
          { bits: "Data stream", name: "MISO bytes", meaning: "Adres sonrası ardışık memory byte'ları okunur." },
        ],
      },
      {
        name: "PAGE_PROGRAM_4B",
        address: "0x12",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "4-byte address kullanarak bir page programlamak.",
        fields: [
          { bits: "Opcode", name: "0x12", meaning: "4-byte address page program komutu." },
          { bits: "A31:A0", name: "32-bit address", meaning: "Programlamanın başlayacağı page içi adres." },
          { bits: "Payload", name: "1..256 byte", meaning: "Tek page sınırı içinde programlanacak data byte'ları." },
        ],
      },
      {
        name: "ERASE_4B",
        address: "0x21 / 0xDC",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "4-byte address ile 4 KB subsector veya 64 KB sector erase yapmak.",
        fields: [
          { bits: "Opcode", name: "0x21", meaning: "4-byte address 4 KB subsector erase komutu." },
          { bits: "Opcode", name: "0xDC", meaning: "4-byte address 64 KB sector erase komutu." },
          { bits: "A31:A0", name: "32-bit address", meaning: "Erase edilecek subsector/sector içinde herhangi bir adres." },
        ],
      },
    ],
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
    registers: [
      {
        name: "CONFIGURATION",
        address: "0x00",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Alarm flag, write-disable flag'leri, alarm output seçimi, reset enable ve event MSB.",
        fields: [
          { bits: "B7", name: "Reserved", meaning: "Normal kullanımda 0 olarak bırakılır.", values: ["0: normal kullanım", "1: reserved; kullanma"] },
          { bits: "B6", name: "AF", meaning: "Alarm flag; elapsed-time counter alarm değerine ulaştığında set olur.", values: ["0: alarm match yok", "1: alarm match oldu; reset command dışında clear edilemez"] },
          { bits: "B5", name: "WDF", meaning: "Write-disable flag; write-disable komutu sonrası set olur.", values: ["0: alarm/event/ETC yazımları disable değil", "1: alarm/event/ETC read-only; clear edilemez"] },
          { bits: "B4", name: "WMDF", meaning: "Write-memory-disable flag; user EEPROM alanı için disable durumunu gösterir.", values: ["0: user EEPROM yazımı disable değil", "1: user EEPROM read-only; clear edilemez"] },
          { bits: "B3", name: "AOS", meaning: "Alarm output select; ALARM pininin pulse veya constant alarm output davranışını seçer.", values: ["0: pulse/flash output mode; AP etkisiz", "1: alarm aktifken constant output; AP polarity belirler"] },
          { bits: "B2", name: "RE", meaning: "Reset enable; reset komutu kabul edilmeden önce 1 yapılmalıdır.", values: ["0: reset command disabled", "1: reset command enabled"] },
          { bits: "B1", name: "AP", meaning: "Alarm polarity; yalnızca AOS=1 constant output modunda etkilidir.", values: ["0: alarm öncesi high-Z, match sonrası low", "1: alarm öncesi low, match sonrası high-Z"] },
          { bits: "B0", name: "ECMSB", meaning: "17-bit event counter değerinin en üst bitidir.", values: ["0: event counter bit16 = 0", "1: event counter bit16 = 1"] },
        ],
      },
      {
        name: "ALARM",
        address: "0x01..0x04",
        width: "32",
        access: "RW",
        reset: "0x00000000",
        purpose: "Quarter-second tick cinsinden alarm trip point.",
        fields: [
          { bits: "0x01", name: "ALRM0", meaning: "Alarm değerinin en düşük byte'ı." },
          { bits: "0x02", name: "ALRM1", meaning: "Alarm değerinin ikinci byte'ı." },
          { bits: "0x03", name: "ALRM2", meaning: "Alarm değerinin üçüncü byte'ı." },
          { bits: "0x04", name: "ALRM3", meaning: "Alarm değerinin en yüksek byte'ı." },
        ],
      },
      {
        name: "ETC",
        address: "0x05..0x08",
        width: "32",
        access: "RO",
        reset: "0x00000000",
        purpose: "Quarter-second tick cinsinden elapsed-time counter.",
        fields: [
          { bits: "0x05", name: "ETC0", meaning: "Elapsed-time counter değerinin en düşük byte'ı." },
          { bits: "0x06", name: "ETC1", meaning: "Elapsed-time counter değerinin ikinci byte'ı." },
          { bits: "0x07", name: "ETC2", meaning: "Elapsed-time counter değerinin üçüncü byte'ı." },
          { bits: "0x08", name: "ETC3", meaning: "Elapsed-time counter değerinin en yüksek byte'ı." },
        ],
      },
      {
        name: "EVENT",
        address: "0x09..0x0A + CFG[0]",
        width: "17",
        access: "RO",
        reset: "0x00000",
        purpose: "Event count değeri.",
        fields: [
          { bits: "0x09", name: "ECNT0", meaning: "Event counter değerinin düşük byte'ı." },
          { bits: "0x0A", name: "ECNT1", meaning: "Event counter değerinin yüksek byte'ı." },
          { bits: "CONFIG B0", name: "ECMSB", meaning: "17-bit event counter değerinin bit16 alanı.", values: ["0: event counter bit16 = 0", "1: event counter bit16 = 1"] },
        ],
      },
      {
        name: "USER EEPROM",
        address: "0x0B..0x14",
        width: "10 bytes",
        access: "RW",
        purpose: "Küçük nonvolatile user field.",
        fields: [
          { bits: "0x0B..0x14", name: "User bytes", meaning: "Uygulama tarafından kullanılabilen 10 byte nonvolatile alan." },
        ],
      },
      {
        name: "RESET_COMMAND",
        address: "0x1D",
        width: "command byte",
        access: "WO",
        purpose: "Reset komutu; RE biti set edilmeden kabul edilmemelidir.",
        fields: [
          { bits: "Ön koşul", name: "CONFIG.RE", meaning: "Reset command kabulü için CONFIGURATION içindeki RE biti enable edilmelidir.", values: ["0: reset command kabul edilmez", "1: reset command kabul edilebilir"] },
          { bits: "Command address", name: "0x1D", meaning: "Reset işlemi için ayrılmış command adresi; normal smoke test içinde kullanılmaz." },
          { bits: "Command payload", name: "0x55, 0x55", meaning: "Reset için aynı command byte iki kez yazılmalıdır.", values: ["0x55 iki kez: reset sequence", "diğer: reset sequence değil"] },
        ],
      },
      {
        name: "WRITE_DISABLE",
        address: "0x1E",
        width: "command byte",
        access: "WO",
        purpose: "Write-disable komutu; kalıcı/production-only işlem olarak ele alınmalıdır.",
        fields: [
          { bits: "Command address", name: "0x1E", meaning: "Write-disable işlemi için ayrılmış command adresi." },
          { bits: "Command payload", name: "0xAA, 0xAA", meaning: "Write-disable için aynı command byte iki kez yazılmalıdır.", values: ["0xAA iki kez: WDF set edilir", "diğer: write-disable sequence değil"] },
          { bits: "Yan etki", name: "WDF", meaning: "Komut sonrası CONFIGURATION içindeki write-disable flag set olur.", values: ["0: komut uygulanmamış veya flag set değil", "1: alarm/event/ETC read-only"] },
        ],
      },
      {
        name: "WRITE_MEMORY_DISABLE",
        address: "0x1F",
        width: "command byte",
        access: "WO",
        purpose: "User EEPROM write-memory-disable komutu; production-only işlem olarak ele alınmalıdır.",
        fields: [
          { bits: "Command address", name: "0x1F", meaning: "Write-memory-disable işlemi için ayrılmış command adresi." },
          { bits: "Command payload", name: "0xF0, 0xF0", meaning: "Write-memory-disable için aynı command byte iki kez yazılmalıdır.", values: ["0xF0 iki kez: WMDF set edilir", "diğer: write-memory-disable sequence değil"] },
          { bits: "Yan etki", name: "WMDF", meaning: "Komut sonrası CONFIGURATION içindeki write-memory-disable flag set olur.", values: ["0: komut uygulanmamış veya flag set değil", "1: user EEPROM read-only"] },
        ],
      },
    ],
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
    registers: [
      {
        name: "CONTROL",
        address: "0x00",
        width: "8",
        access: "RW",
        reset: "0x05",
        purpose: "Snapshot mode/channel, test mode, ADC busy, VIN monitor, shutdown ve multiplier selection.",
        fields: [
          { bits: "B7", name: "Snapshot mode", meaning: "Conversion akışını continuous veya snapshot olarak seçer.", values: ["0: continuous conversion / varsayılan", "1: snapshot mode"] },
          { bits: "B6:B5", name: "Snapshot ADC channel", meaning: "Snapshot mode kullanıldığında hangi ADC kanalının yakalanacağını seçer.", values: ["00: SENSE", "01: VIN", "10: ADIN", "11: reserved / kullanma"] },
          { bits: "B4", name: "Test mode enable", meaning: "Normal uygulama kodunda kullanılmaması gereken test mode bitidir.", values: ["0: disabled / varsayılan", "1: enabled"] },
          { bits: "B3", name: "ADC busy", meaning: "ADC conversion devam ederken set olan status bitidir.", values: ["0: ADC idle", "1: ADC busy"] },
          { bits: "B2", name: "VIN monitor", meaning: "VIN ölçümünün VDD pininden mi SENSE+ pininden mi yapılacağını seçer.", values: ["0: VDD pinini monitor et", "1: SENSE+ pinini monitor et / varsayılan"] },
          { bits: "B1", name: "Shutdown enable", meaning: "ADC ölçüm bloklarını shutdown moduna alır.", values: ["0: disabled / varsayılan", "1: shutdown enabled"] },
          { bits: "B0", name: "Multiplier select", meaning: "Power multiplier için ADIN veya SENSE+ girişini seçer.", values: ["0: ADIN", "1: SENSE+ / varsayılan"] },
        ],
      },
      {
        name: "ALERT_ENABLE",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Power, SENSE, VIN ve ADIN limitleri için ALERT enable maskesi.",
        fields: ltc2945LimitFields("enable"),
      },
      {
        name: "STATUS",
        address: "0x02",
        width: "8",
        access: "RO",
        reset: "0x00",
        purpose: "Power, SENSE, VIN ve ADIN limit koşullarının anlık status bitleri.",
        fields: ltc2945LimitFields("status"),
      },
      {
        name: "FAULT",
        address: "0x03",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "Power, SENSE, VIN ve ADIN limit koşulları için latched fault bitleri.",
        fields: ltc2945LimitFields("fault"),
      },
      {
        name: "FAULT_CLEAR",
        address: "0x04",
        width: "8",
        access: "CoR",
        reset: "0x00",
        purpose: "Fault clear yolu.",
        fields: ltc2945LimitFields("clear"),
      },
      {
        name: "POWER",
        address: "0x05..0x07",
        width: "24",
        access: "RO",
        purpose: "Raw calculated power register.",
        fields: [
          { bits: "0x05", name: "POWER_MSB2", meaning: "24-bit raw power code değerinin bit23..bit16 alanı." },
          { bits: "0x06", name: "POWER_MSB1", meaning: "24-bit raw power code değerinin bit15..bit8 alanı." },
          { bits: "0x07", name: "POWER_LSB", meaning: "24-bit raw power code değerinin bit7..bit0 alanı." },
        ],
      },
      {
        name: "SENSE",
        address: "0x14..0x15",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit shunt/sense ADC image.",
        fields: [
          { bits: "MSB B7:B0", name: "SENSE[11:4]", meaning: "12-bit raw sense ADC code değerinin üst sekiz biti." },
          { bits: "LSB B7:B4", name: "SENSE[3:0]", meaning: "12-bit raw sense ADC code değerinin alt dört biti." },
          { bits: "LSB B3:B0", name: "Unused", meaning: "12-bit conversion code hesabına dahil edilmez.", values: unusedValues },
        ],
      },
      {
        name: "VIN",
        address: "0x1E..0x1F",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit VIN ADC image.",
        fields: [
          { bits: "MSB B7:B0", name: "VIN[11:4]", meaning: "12-bit raw VIN ADC code değerinin üst sekiz biti." },
          { bits: "LSB B7:B4", name: "VIN[3:0]", meaning: "12-bit raw VIN ADC code değerinin alt dört biti." },
          { bits: "LSB B3:B0", name: "Unused", meaning: "12-bit conversion code hesabına dahil edilmez.", values: unusedValues },
        ],
      },
      {
        name: "ADIN",
        address: "0x28..0x29",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit auxiliary ADC image.",
        fields: [
          { bits: "MSB B7:B0", name: "ADIN[11:4]", meaning: "12-bit raw ADIN ADC code değerinin üst sekiz biti." },
          { bits: "LSB B7:B4", name: "ADIN[3:0]", meaning: "12-bit raw ADIN ADC code değerinin alt dört biti." },
          { bits: "LSB B3:B0", name: "Unused", meaning: "12-bit conversion code hesabına dahil edilmez.", values: unusedValues },
        ],
      },
    ],
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

  if (normalizedPart === "LTC2991") {
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
        return [];
    }
  }

  return [];
}

export function getDeviceKnowledge(part: string): DeviceKnowledgePack | undefined {
  return PACKS[part.toUpperCase()];
}

export function hasDeviceKnowledge(part: string): boolean {
  return Boolean(getDeviceKnowledge(part));
}
