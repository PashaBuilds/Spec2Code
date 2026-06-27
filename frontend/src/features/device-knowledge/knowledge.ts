export interface KnowledgeSource {
  label: string;
  url: string;
}

export interface KnowledgeRegister {
  name: string;
  address: string;
  width: string;
  access: string;
  reset?: string;
  purpose: string;
  fields?: string[];
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

const PACKS: Record<string, DeviceKnowledgePack> = {
  LTC2991: {
    part: "LTC2991",
    reviewedAt: "2026-06-27",
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
        fields: ["V1/V2 busy biti"],
      },
      {
        name: "STATUS_HIGH",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "V1/V2, V3/V4, V5/V6, V7/V8, iç sıcaklık ve VCC ölçümlerini enable eder.",
        fields: ["iç sıcaklık/VCC enable", "pair enable bitleri"],
      },
      {
        name: "CONTROL_V1V4",
        address: "0x06",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "V1/V2 ve V3/V4 pair mode bitleri.",
        fields: ["V1/V2 differential", "V1/V2 temperature", "V3/V4 differential", "V3/V4 temperature"],
      },
      {
        name: "CONTROL_V5V8",
        address: "0x07",
        width: "8",
        access: "RW",
        reset: "0x00",
        purpose: "V5/V6 ve V7/V8 pair mode bitleri.",
        fields: ["V5/V6 differential", "V5/V6 temperature", "V7/V8 differential", "V7/V8 temperature"],
      },
      {
        name: "V1_MSB..V8_LSB",
        address: "0x0A..0x19",
        width: "her biri 16",
        access: "RO",
        purpose: "Harici girişler için raw ölçüm sonuç register'ları.",
      },
      {
        name: "T_INTERNAL",
        address: "0x1A..0x1B",
        width: "16",
        access: "RO",
        purpose: "Raw iç sıcaklık sonucu.",
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
    reviewedAt: "2026-06-27",
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
        fields: ["CH0_EN bit 0", "CH1_EN bit 1", "CH2_EN bit 2", "CH3_EN bit 3", "CH4..CH7 bit 4..7"],
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
    reviewedAt: "2026-06-27",
    scope: "Güvenli single-SPI NOR flash read, program, erase ve JEDEC ID akışları.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
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
      },
      {
        name: "READ_STATUS",
        address: "0x05",
        width: "opcode",
        access: "RO",
        purpose: "Status register okumak; özellikle WIP/busy durumunu takip etmek.",
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Program/erase operasyonlarından önce write enable latch etmek.",
      },
      {
        name: "READ_DATA",
        address: "0x03",
        width: "opcode + 24-bit address",
        access: "RO",
        purpose: "Konservatif array read command.",
      },
      {
        name: "PAGE_PROGRAM",
        address: "0x02",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "Write enable sonrası en fazla bir page programlamak.",
      },
      {
        name: "SUBSECTOR/SECTOR_ERASE",
        address: "0x20 / 0xD8",
        width: "opcode + 24-bit address",
        access: "WO",
        purpose: "4 KB subsector veya 64 KB sector erase yapmak.",
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
    reviewedAt: "2026-06-27",
    scope: "4-byte address command akışına sahip 2 Gbit SPI NOR flash.",
    sources: [
      {
        label: "Micron MT25Q serial NOR product page",
        url: "https://www.micron.com/products/storage/nor-flash/serial-nor",
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
      },
      {
        name: "WRITE_ENABLE",
        address: "0x06",
        width: "opcode",
        access: "WO",
        purpose: "Mode enter, program ve erase akışlarından önce gereklidir.",
      },
      {
        name: "ENTER_4BYTE",
        address: "0xB7",
        width: "opcode",
        access: "WO",
        purpose: "Yüksek adres aralığı için 4-byte address mode'a geçmek.",
      },
      {
        name: "READ_DATA_4B",
        address: "0x13",
        width: "opcode + 32-bit address",
        access: "RO",
        purpose: "4-byte address ile array data okumak.",
      },
      {
        name: "PAGE_PROGRAM_4B",
        address: "0x12",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "4-byte address kullanarak bir page programlamak.",
      },
      {
        name: "ERASE_4B",
        address: "0x21 / 0xDC",
        width: "opcode + 32-bit address",
        access: "WO",
        purpose: "4-byte address ile 4 KB subsector veya 64 KB sector erase yapmak.",
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
    reviewedAt: "2026-06-27",
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
        fields: ["TEMP_CODE bits 15:6"],
      },
      {
        name: "CONFIGURATION",
        address: "0x01",
        width: "8",
        access: "RW",
        reset: "0x40",
        purpose: "Power, alert, polarity, reset ve one-shot kontrolleri.",
        fields: ["POWER_DOWN", "FILTER_BYPASS", "ALERT_ENABLE", "ALERT_POLARITY", "ALERT_RESET", "ONE_SHOT"],
      },
      {
        name: "THIGH",
        address: "0x02",
        width: "8",
        access: "RW",
        reset: "0x50",
        purpose: "High temperature alert threshold değeri.",
      },
      {
        name: "TLOW",
        address: "0x03",
        width: "8",
        access: "RW",
        reset: "0x4B",
        purpose: "Low temperature alert threshold değeri.",
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
    reviewedAt: "2026-06-27",
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
      },
      {
        name: "ALARM",
        address: "0x01..0x04",
        width: "32",
        access: "RW",
        reset: "0x00000000",
        purpose: "Quarter-second tick cinsinden alarm trip point.",
      },
      {
        name: "ETC",
        address: "0x05..0x08",
        width: "32",
        access: "RO",
        reset: "0x00000000",
        purpose: "Quarter-second tick cinsinden elapsed-time counter.",
      },
      {
        name: "EVENT",
        address: "0x09..0x0A + CFG[0]",
        width: "17",
        access: "RO",
        reset: "0x00000",
        purpose: "Event count değeri.",
      },
      {
        name: "USER EEPROM",
        address: "0x0B..0x14",
        width: "10 bytes",
        access: "RW",
        purpose: "Küçük nonvolatile user field.",
      },
      {
        name: "CONTROL COMMANDS",
        address: "0x1D..0x1F",
        width: "8 each",
        access: "WO",
        purpose: "Reset, write disable ve memory disable command'ları.",
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
      "Reset/write-disable command'ları smoke test içine konulmamalıdır.",
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
    reviewedAt: "2026-06-27",
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
        purpose: "ADC mode, snapshot, VIN monitor, shutdown ve multiplier selection.",
        fields: ["SNAPSHOT_ENABLE", "ADC_BUSY", "VIN_MONITOR", "SHUTDOWN", "MULTIPLIER_SELECT"],
      },
      {
        name: "ALERT/STATUS/FAULT",
        address: "0x01..0x03",
        width: "her biri 8",
        access: "RW/RO",
        purpose: "Alert enable/status ve fault reporting.",
      },
      {
        name: "FAULT_CLEAR",
        address: "0x04",
        width: "8",
        access: "RW",
        purpose: "Fault clear yolu.",
      },
      {
        name: "POWER",
        address: "0x05..0x07",
        width: "24",
        access: "RO",
        purpose: "Raw calculated power register.",
      },
      {
        name: "SENSE",
        address: "0x14..0x15",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit shunt/sense ADC image.",
      },
      {
        name: "VIN",
        address: "0x1E..0x1F",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit VIN ADC image.",
      },
      {
        name: "ADIN",
        address: "0x28..0x29",
        width: "16 transfer",
        access: "RO",
        purpose: "Raw 12-bit auxiliary ADC image.",
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

export function getDeviceKnowledge(part: string): DeviceKnowledgePack | undefined {
  return PACKS[part.toUpperCase()];
}

export function hasDeviceKnowledge(part: string): boolean {
  return Boolean(getDeviceKnowledge(part));
}
