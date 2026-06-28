export interface TiClockBitfield {
  bits: string;
  name: string;
  meaning: string;
  values?: string[];
}

type TiClockPart = "LMK04832" | "LMX2820" | "LMX1204";

type TiClockBitfieldMap = Record<TiClockPart, Record<string, TiClockBitfield[]>>;

export const TI_CLOCK_BITFIELDS: TiClockBitfieldMap = {
  LMK04832: {
    "0x000": [
      {
        bits: "B7",
        name: "RESET",
        meaning: "Software reset bitidir; 1 yazıldığında reset ister ve otomatik temizlenir.",
        values: [
          "0: normal operation",
          "1: reset request"
        ]
      },
      {
        bits: "B6:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4",
        name: "SPI_3WIRE_DIS",
        meaning: "3-wire SPI modunu kapatır; 4-wire readback topolojilerinde kullanılır.",
        values: [
          "0: 3-wire SPI enabled",
          "1: 3-wire SPI disabled"
        ]
      },
      {
        bits: "B3:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x002": [
      {
        bits: "B7:B1",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B0",
        name: "POWERDOWN",
        meaning: "Cihaz genel power-down kontrolüdür.",
        values: [
          "0: normal operation",
          "1: power down device"
        ]
      }
    ],
    "0x003": [
      {
        bits: "B7:B0",
        name: "ID_DEVICE_TYPE",
        meaning: "Read-only kimlik alanıdır; cihaz/product type bilgisini taşır."
      }
    ],
    "0x004": [
      {
        bits: "B7:B0",
        name: "ID_PROD[15:8]",
        meaning: "Read-only kimlik alanıdır; cihaz/product/vendor bilgisinin ilgili byte’ını taşır."
      }
    ],
    "0x005": [
      {
        bits: "B7:B0",
        name: "ID_PROD[7:0]",
        meaning: "Read-only kimlik alanıdır; cihaz/product/vendor bilgisinin ilgili byte’ını taşır."
      }
    ],
    "0x006": [
      {
        bits: "B7:B0",
        name: "ID_MASKREV",
        meaning: "Read-only kimlik alanıdır; cihaz/product/vendor bilgisinin ilgili byte’ını taşır."
      }
    ],
    "0x00C": [
      {
        bits: "B7:B0",
        name: "ID_VNDR[15:8]",
        meaning: "Read-only kimlik alanıdır; cihaz/product/vendor bilgisinin ilgili byte’ını taşır."
      }
    ],
    "0x00D": [
      {
        bits: "B7:B0",
        name: "ID_VNDR[7:0]",
        meaning: "Read-only kimlik alanıdır; cihaz/product/vendor bilgisinin ilgili byte’ını taşır."
      }
    ],
    "0x100": [
      {
        bits: "B7:B0",
        name: "DCLK0_1_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x101": [
      {
        bits: "B7:B0",
        name: "DCLK0_1_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x102": [
      {
        bits: "B7",
        name: "CLKout0_1_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout0_1_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout0_1_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK0_1_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK0_1_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK0_1_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x103": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout0_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK0_1_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK0_1_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK0_1_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK0_1_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK0_1_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x104": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout1_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK0_1_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK0_1_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK0_1_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK0_1_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x105": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK0_1_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK0_1_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x106": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK0_1_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x107": [
      {
        bits: "B7:B4",
        name: "CLKout1_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout0_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x108": [
      {
        bits: "B7:B0",
        name: "DCLK2_3_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x109": [
      {
        bits: "B7:B0",
        name: "DCLK2_3_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x10A": [
      {
        bits: "B7",
        name: "CLKout2_3_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout2_3_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout2_3_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK2_3_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK2_3_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK2_3_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x10B": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout2_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK2_3_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK2_3_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK2_3_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK2_3_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK2_3_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x10C": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout3_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK2_3_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK2_3_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK2_3_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK2_3_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x10D": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK2_3_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK2_3_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x10E": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK2_3_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x10F": [
      {
        bits: "B7:B4",
        name: "CLKout3_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout2_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x110": [
      {
        bits: "B7:B0",
        name: "DCLK4_5_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x111": [
      {
        bits: "B7:B0",
        name: "DCLK4_5_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x112": [
      {
        bits: "B7",
        name: "CLKout4_5_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout4_5_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout4_5_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK4_5_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK4_5_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK4_5_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x113": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout4_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK4_5_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK4_5_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK4_5_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK4_5_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK4_5_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x114": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout5_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK4_5_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK4_5_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK4_5_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK4_5_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x115": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK4_5_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK4_5_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x116": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK4_5_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x117": [
      {
        bits: "B7:B4",
        name: "CLKout5_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout4_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x118": [
      {
        bits: "B7:B0",
        name: "DCLK6_7_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x119": [
      {
        bits: "B7:B0",
        name: "DCLK6_7_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x11A": [
      {
        bits: "B7",
        name: "CLKout6_7_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout6_7_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout6_7_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK6_7_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK6_7_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK6_7_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x11B": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout6_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK6_7_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK6_7_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK6_7_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK6_7_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK6_7_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x11C": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout7_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK6_7_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK6_7_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK6_7_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK6_7_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x11D": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK6_7_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK6_7_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x11E": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK6_7_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x11F": [
      {
        bits: "B7:B4",
        name: "CLKout7_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout6_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x120": [
      {
        bits: "B7:B0",
        name: "DCLK8_9_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x121": [
      {
        bits: "B7:B0",
        name: "DCLK8_9_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x122": [
      {
        bits: "B7",
        name: "CLKout8_9_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout8_9_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout8_9_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK8_9_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK8_9_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK8_9_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x123": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout8_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK8_9_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK8_9_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK8_9_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK8_9_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK8_9_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x124": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout9_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK8_9_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK8_9_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK8_9_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK8_9_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x125": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK8_9_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK8_9_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x126": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK8_9_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x127": [
      {
        bits: "B7:B4",
        name: "CLKout9_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout8_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x128": [
      {
        bits: "B7:B0",
        name: "DCLK10_11_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x129": [
      {
        bits: "B7:B0",
        name: "DCLK10_11_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x12A": [
      {
        bits: "B7",
        name: "CLKout10_11_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout10_11_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout10_11_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK10_11_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK10_11_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK10_11_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x12B": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout10_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK10_11_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK10_11_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK10_11_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK10_11_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK10_11_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x12C": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout11_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK10_11_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK10_11_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK10_11_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK10_11_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x12D": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK10_11_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK10_11_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x12E": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK10_11_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x12F": [
      {
        bits: "B7:B4",
        name: "CLKout11_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout10_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x130": [
      {
        bits: "B7:B0",
        name: "DCLK12_13_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x131": [
      {
        bits: "B7:B0",
        name: "DCLK12_13_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x132": [
      {
        bits: "B7",
        name: "CLKout12_13_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "CLKout12_13_ODL",
        meaning: "Output drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B5",
        name: "CLKout12_13_IDL",
        meaning: "Input drive level seçimidir; higher current/lower noise floor davranışını etkiler."
      },
      {
        bits: "B4",
        name: "DCLK12_13_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "DCLK12_13_DDLY[9:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      },
      {
        bits: "B1:B0",
        name: "DCLK12_13_DIV[9:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x133": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout12_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "DCLK12_13_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "DCLK12_13_BYP",
        meaning: "Even clock için high-performance bypass path kontrolüdür.",
        values: [
          "0: normal path",
          "1: bypass path"
        ]
      },
      {
        bits: "B2",
        name: "DCLK12_13_DCC",
        meaning: "Duty-cycle correction kontrol alanıdır; device clock divider çıkışında duty-cycle düzeltmesini açar."
      },
      {
        bits: "B1",
        name: "DCLK12_13_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "DCLK12_13_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x134": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "CLKout13_SRC_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "SCLK12_13_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3:B2",
        name: "SCLK12_13_DIS_MODE",
        meaning: "SYSREF global power-down aktifken çıkışın disable davranışını seçer."
      },
      {
        bits: "B1",
        name: "SCLK12_13_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B0",
        name: "SCLK12_13_HS",
        meaning: "Half-step faz ayarıdır; ilgili clock/SYSREF yolunda yarım cycle faz kaydırma davranışını kontrol eder."
      }
    ],
    "0x135": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "SCLK12_13_ADLY_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4:B0",
        name: "SCLK12_13_ADLY",
        meaning: "Analog delay alanıdır; SYSREF analog gecikme yolunu ve yaklaşık delay step değerini kontrol eder."
      }
    ],
    "0x136": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "SCLK12_13_DDLY",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x137": [
      {
        bits: "B7:B4",
        name: "CLKout13_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      },
      {
        bits: "B3:B0",
        name: "CLKout12_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x138": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6:B5",
        name: "VCO_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4",
        name: "OSCout_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B3:B0",
        name: "OSCout_FMT",
        meaning: "Output format seçim alanıdır; clock çıkış standardı veya sürücü formatı bu alandan belirlenir."
      }
    ],
    "0x139": [
      {
        bits: "B7:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4",
        name: "SYSREF_REQ_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B3",
        name: "SYNC_BYPASS",
        meaning: "SYNC polarity invert ve ilgili circuitry bypass kontrolüdür.",
        values: [
          "0: normal",
          "1: bypass"
        ]
      },
      {
        bits: "B2",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B1:B0",
        name: "SYSREF_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      }
    ],
    "0x13A": [
      {
        bits: "B7:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4:B0",
        name: "SYSREF_DIV[12:8]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x13B": [
      {
        bits: "B7:B0",
        name: "SYSREF_DIV[7:0]",
        meaning: "Divider/counter değerinin ilgili bit alanıdır; çok byte alanlarda MSB/LSB register’ları birlikte yorumlanır."
      }
    ],
    "0x13C": [
      {
        bits: "B7:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4:B0",
        name: "SYSREF_DDLY[12:8]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x13D": [
      {
        bits: "B7:B0",
        name: "SYSREF_DDLY[7:0]",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x13E": [
      {
        bits: "B7:B2",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B1:B0",
        name: "SYSREF_PULSE_CNT",
        meaning: "SYSREF pulser modunda üretilecek pulse sayısını seçer."
      }
    ],
    "0x13F": [
      {
        bits: "B7",
        name: "PLL2_RCLK_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "PLL2_NCLK_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B4:B3",
        name: "PLL1_NCLK_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B2:B1",
        name: "FB_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B0",
        name: "FB_MUX_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      }
    ],
    "0x140": [
      {
        bits: "B7",
        name: "PLL1_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B6",
        name: "VCO_LDO_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B5",
        name: "VCO_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B4",
        name: "OSCin_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B3",
        name: "SYSREF_GBL_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B2",
        name: "SYSREF_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B1",
        name: "SYSREF_DDLY_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B0",
        name: "SYSREF_PLSR_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      }
    ],
    "0x141": [
      {
        bits: "B7",
        name: "DDLYd_SYSREF_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B6",
        name: "DDLYd12_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B5",
        name: "DDLYd10_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4",
        name: "DDLYd8_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B3",
        name: "DDLYd6_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B2",
        name: "DDLYd4_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B1",
        name: "DDLYd2_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B0",
        name: "DDLYd0_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      }
    ],
    "0x142": [
      {
        bits: "B7:B0",
        name: "DDLYd_STEP_CNT",
        meaning: "Digital delay alanıdır; SYNC/SYSREF veya device clock faz gecikmesini register image üzerinden belirler."
      }
    ],
    "0x143": [
      {
        bits: "B7",
        name: "SYSREF_CLR",
        meaning: "SYSREF/SYNC üretim, delay veya routing davranışını kontrol eden alandır."
      },
      {
        bits: "B6",
        name: "SYNC_1SHOT_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B5",
        name: "SYNC_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B4",
        name: "SYNC_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B3",
        name: "SYNC_PLL2_DLD",
        meaning: "SYNC event kaynağı olarak PLL2 digital lock detect'i kullanır; 1 iken SYNC, PLL2_DLD=1 olana kadar assert tutulabilir.",
        values: [
          "0: PLL2 DLD, SYNC üretimini etkilemez",
          "1: PLL2 DLD=1 olana kadar SYNC assert davranışına katılır"
        ]
      },
      {
        bits: "B2",
        name: "SYNC_PLL1_DLD",
        meaning: "SYNC event kaynağı olarak PLL1 digital lock detect'i kullanır; 1 iken SYNC, PLL1_DLD=1 olana kadar assert tutulabilir.",
        values: [
          "0: PLL1 DLD, SYNC üretimini etkilemez",
          "1: PLL1 DLD=1 olana kadar SYNC assert davranışına katılır"
        ]
      },
      {
        bits: "B1:B0",
        name: "SYNC_MODE",
        meaning: "SYNC event üretim metodunu seçer; SYNC pini ve etkinse PLL1/PLL2 DLD flag'lerinin pulser/SYNC akışını nasıl tetikleyeceğini belirler.",
        values: [
          "0: SYNC pini ve DLD flag'leri SYNC event üretmez",
          "1: SYNC event, SYNC pini veya etkin DLD flag'i ile üretilir",
          "2: pulser üzerinden SYNC/SYSREF pulse üretimi; tetik SYNC pini veya etkin DLD flag'i olabilir",
          "3: register 0x13E yazımı ile pulser üzerinden SYNC/SYSREF pulse üretimi"
        ]
      }
    ],
    "0x144": [
      {
        bits: "B7",
        name: "SYNC_DISSYSREF",
        meaning: "SYSREF/SYNC üretim, delay veya routing davranışını kontrol eden alandır."
      },
      {
        bits: "B6",
        name: "SYNC_DIS12",
        meaning: "DCLKout12/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B5",
        name: "SYNC_DIS10",
        meaning: "DCLKout10/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B4",
        name: "SYNC_DIS8",
        meaning: "DCLKout8/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B3",
        name: "SYNC_DIS6",
        meaning: "DCLKout6/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B2",
        name: "SYNC_DIS4",
        meaning: "DCLKout4/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B1",
        name: "SYNC_DIS2",
        meaning: "DCLKout2/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      },
      {
        bits: "B0",
        name: "SYNC_DIS0",
        meaning: "DCLKout0/SYSREF ilişkili output divider'ın SYNC event ile hizalanmasını engeller; 1 iken ilgili output normal çalışmaya devam eder."
      }
    ],
    "0x145": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "PLL1R_SYNC_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B5:B4",
        name: "PLL1R_SYNC_SRC",
        meaning: "PLL1 R divider senkronizasyonu için tetik kaynağını seçer; PLL1R_SYNC_EN ile birlikte kullanılır.",
        values: [
          "0: reserved",
          "1: SYNC pini",
          "2: CLKin0",
          "3: reserved"
        ]
      },
      {
        bits: "B3",
        name: "PLL2R_SYNC_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B2:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x146": [
      {
        bits: "B7",
        name: "CLKin_SEL_PIN_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B6",
        name: "CLKin_SEL_PIN_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B5",
        name: "CLKin2_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4",
        name: "CLKin1_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B3",
        name: "CLKin0_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B2",
        name: "CLKin2_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      },
      {
        bits: "B1",
        name: "CLKin1_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      },
      {
        bits: "B0",
        name: "CLKin0_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      }
    ],
    "0x147": [
      {
        bits: "B7",
        name: "CLKin_SEL_AUTO_REVERT_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B6",
        name: "CLKin_SEL_AUTO_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B5:B4",
        name: "CLKin_SEL_MANUAL",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      },
      {
        bits: "B3:B2",
        name: "CLKin1_DEMUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B1:B0",
        name: "CLKin0_DEMUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      }
    ],
    "0x148": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B3",
        name: "CLKin_SEL0_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B2:B0",
        name: "CLKin_SEL0_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      }
    ],
    "0x149": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "SDIO_RDBK_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      },
      {
        bits: "B5:B3",
        name: "CLKin_SEL1_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B2:B0",
        name: "CLKin_SEL1_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      }
    ],
    "0x14A": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B3",
        name: "RESET_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B2:B0",
        name: "RESET_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      }
    ],
    "0x14B": [
      {
        bits: "B7:B6",
        name: "LOS_TIMEOUT",
        meaning: "CLKin üzerinde aktivite görülmediğinde loss-of-signal kaynaklı clock switch event oluşması için kullanılan timeout/frekans eşiğini seçer.",
        values: [
          "0: 5 MHz typical",
          "1: 25 MHz typical",
          "2: 100 MHz typical",
          "3: 200 MHz typical"
        ]
      },
      {
        bits: "B5",
        name: "LOS_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B4",
        name: "TRACK_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B3",
        name: "HOLDOVER_FORCE",
        meaning: "Cihazı yazılımla holdover moduna zorlar; normal otomatik giriş koşullarından bağımsız holdover davranışı test/servis için kullanılabilir."
      },
      {
        bits: "B2",
        name: "MAN_DAC_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      },
      {
        bits: "B1:B0",
        name: "MAN_DAC[9:8]",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      }
    ],
    "0x14C": [
      {
        bits: "B7:B0",
        name: "MAN_DAC[7:0]",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      }
    ],
    "0x14D": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "DAC_TRIP_LOW",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      }
    ],
    "0x14E": [
      {
        bits: "B7:B6",
        name: "DAC_CLK_MULT",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      },
      {
        bits: "B5:B0",
        name: "DAC_TRIP_HIGH",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      }
    ],
    "0x14F": [
      {
        bits: "B7:B0",
        name: "DAC_CLK_CNTR",
        meaning: "Holdover DAC kontrol/readback alanıdır; manual DAC, threshold veya tracking bilgisini taşır."
      }
    ],
    "0x150": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "CLKin_OVERRIDE",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      },
      {
        bits: "B5",
        name: "HOLDOVER_EXIT_MODE",
        meaning: "Holdover çıkış kararının LOS durumuna mı yoksa PLL1 digital lock detect durumuna mı dayanacağını seçer.",
        values: [
          "0: LOS status aktif clock'u geçerli gösterdiğinde holdover'dan çık",
          "1: PLL1 phase detector/DLD geçerli clock'u onayladığında holdover'dan çık"
        ]
      },
      {
        bits: "B4",
        name: "HOLDOVER_PLL1_DET",
        meaning: "PLL1 DLD high'dan low'a düştüğünde holdover/clock switch event üretimini etkinleştirir.",
        values: [
          "0: PLL1 DLD düşüşü clock switch event üretmez",
          "1: PLL1 DLD düşüşü clock switch event üretir"
        ]
      },
      {
        bits: "B3",
        name: "LOS_EXTERNAL_INPUT",
        meaning: "Internal LOS devresi yerine harici pinleri CLKin LOS status kaynağı olarak kullanır; CLKin_SEL0/1 ve Status_LD1 pin type ayarı input olmalıdır.",
        values: [
          "0: internal LOS kullanılır",
          "1: external LOS input pinleri kullanılır"
        ]
      },
      {
        bits: "B2",
        name: "HOLDOVER_VTUNE_DET",
        meaning: "DAC Vtune rail detector'ı etkinleştirir; DAC belirlenen Vtune eşiğine ulaştığında mevcut clock invalid kabul edilip switch event üretilebilir.",
        values: [
          "0: Vtune detector disabled",
          "1: Vtune detector enabled"
        ]
      },
      {
        bits: "B1",
        name: "CLKin_SWITCH_CP_TRI",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      },
      {
        bits: "B0",
        name: "HOLDOVER_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      }
    ],
    "0x151": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "HOLDOVER_DLD_CNT[13:8]",
        meaning: "Holdover'dan çıkmadan önce PLL1 phase detector tarafında görülmesi gereken geçerli clock sayısının üst bitleridir."
      }
    ],
    "0x152": [
      {
        bits: "B7:B0",
        name: "HOLDOVER_DLD_CNT[7:0]",
        meaning: "Holdover'dan çıkmadan önce PLL1 phase detector tarafında görülmesi gereken geçerli clock sayısının alt bitleridir."
      }
    ],
    "0x153": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "CLKin0_R[13:8]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x154": [
      {
        bits: "B7:B0",
        name: "CLKin0_R[7:0]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x155": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "CLKin1_R[13:8]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x156": [
      {
        bits: "B7:B0",
        name: "CLKin1_R[7:0]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x157": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "CLKin2_R[13:8]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x158": [
      {
        bits: "B7:B0",
        name: "CLKin2_R[7:0]",
        meaning: "CLKin input seçimi, enable, demux veya loss-of-signal davranışını kontrol eder."
      }
    ],
    "0x159": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "PLL1_N[13:8]",
        meaning: "PLL1 feedback N divider değerinin üst bitleridir; PLL1 phase detector feedback oranını belirler."
      }
    ],
    "0x15A": [
      {
        bits: "B7:B0",
        name: "PLL1_N[7:0]",
        meaning: "PLL1 feedback N divider değerinin alt bitleridir; 14-bit PLL1_N değeri için 0 geçerli değildir."
      }
    ],
    "0x15B": [
      {
        bits: "B7:B6",
        name: "PLL1_WND_SIZE",
        meaning: "PLL1 digital lock detect için phase-error pencere boyutunu seçer; hata bu pencerenin altında kaldığında PLL1 lock counter artar.",
        values: [
          "0: 4 ns",
          "1: 9 ns",
          "2: 19 ns",
          "3: 43 ns"
        ]
      },
      {
        bits: "B5",
        name: "PLL1_CP_TRI",
        meaning: "PLL1 charge pump output pinini tri-state durumuna alır.",
        values: [
          "0: CPout1 active",
          "1: CPout1 tri-state"
        ]
      },
      {
        bits: "B4",
        name: "PLL1_CP_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B3:B0",
        name: "PLL1_CP_GAIN",
        meaning: "PLL1 charge pump output current seviyesini seçer; datasheet tablosunda 0=50 uA, 15=1550 uA aralığı verilir."
      }
    ],
    "0x15C": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "PLL1_DLD_CNT[13:8]",
        meaning: "PLL1 digital lock detect assert olmadan önce reference/feedback faz hatasının PLL1_WND_SIZE içinde kalması gereken cycle sayısının üst bitleridir."
      }
    ],
    "0x15D": [
      {
        bits: "B7:B0",
        name: "PLL1_DLD_CNT[7:0]",
        meaning: "PLL1 digital lock detect assert olmadan önce reference/feedback faz hatasının PLL1_WND_SIZE içinde kalması gereken cycle sayısının alt bitleridir."
      }
    ],
    "0x15E": [
      {
        bits: "B7:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4:B0",
        name: "HOLDOVER_EXIT_NADJ",
        meaning: "Holdover çıkışında resetlenen PLL1 R ve PLL1 N divider'ları arasındaki relatif timing offset'i 2's complement değer olarak ayarlar."
      }
    ],
    "0x15F": [
      {
        bits: "B7:B3",
        name: "PLL1_LD_MUX",
        meaning: "Mux/source seçim alanıdır; hangi internal/external kaynağın kullanılacağını belirler."
      },
      {
        bits: "B2:B0",
        name: "PLL1_LD_TYPE",
        meaning: "Pin veya buffer type seçim alanıdır; input/output davranışı ve board bağlantısına göre ayarlanır."
      }
    ],
    "0x160": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3:B0",
        name: "PLL2_R[11:8]",
        meaning: "PLL2 reference R divider değerinin üst bitleridir; PLL2 phase detector referans frekansını belirler."
      }
    ],
    "0x161": [
      {
        bits: "B7:B0",
        name: "PLL2_R[7:0]",
        meaning: "PLL2 reference R divider değerinin alt bitleridir; 12-bit PLL2_R oranı PLL2 PFD frekansını belirler."
      }
    ],
    "0x162": [
      {
        bits: "B7:B5",
        name: "PLL2_P",
        meaning: "PLL2 N prescaler değerini seçer; VCO output'u PLL2 N divider'a gitmeden önce bu prescaler üzerinden bölünür.",
        values: [
          "0: divide 8",
          "1: divide 2",
          "2: divide 2",
          "3: divide 3",
          "4: divide 4",
          "5: divide 5",
          "6: divide 6",
          "7: divide 7"
        ]
      },
      {
        bits: "B4:B2",
        name: "OSCin_FREQ",
        meaning: "PLL2 frequency calibration rutininin doğru çalışması için OSCin/OSCin* üzerinden PLL2 phase detector'a gelen referans frekans aralığını bildirir.",
        values: [
          "0: 0..63 MHz",
          "1: >63..127 MHz",
          "2: >127..255 MHz",
          "3: reserved",
          "4: >255..500 MHz",
          "5..7: reserved"
        ]
      },
      {
        bits: "B1",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B0",
        name: "PLL2_REF_2X_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      }
    ],
    "0x163": [
      {
        bits: "B7:B2",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B1:B0",
        name: "PLL2_N_CAL[17:16]",
        meaning: "Cascaded 0-delay modunda PLL2 frequency calibration sırasında kullanılan PLL2_N_CAL divider değerinin üst bitleridir."
      }
    ],
    "0x164": [
      {
        bits: "B7:B0",
        name: "PLL2_N_CAL[15:8]",
        meaning: "Cascaded 0-delay modunda PLL2 frequency calibration sırasında kullanılan PLL2_N_CAL divider değerinin orta bitleridir."
      }
    ],
    "0x165": [
      {
        bits: "B7:B0",
        name: "PLL2_N_CAL[7:0]",
        meaning: "Cascaded 0-delay modunda PLL2 frequency calibration sırasında kullanılan PLL2_N_CAL divider değerinin alt bitleridir."
      }
    ],
    "0x166": [
      {
        bits: "B7:B2",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B1:B0",
        name: "PLL2_N[17:16]",
        meaning: "PLL2 feedback N divider değerinin üst bitleridir; 0-delay calibration dışındaki normal PLL2_N değerine katılır."
      }
    ],
    "0x167": [
      {
        bits: "B7:B0",
        name: "PLL2_N[15:8]",
        meaning: "PLL2 feedback N divider değerinin orta bitleridir; register 0x168 yazımı PLL2_FCAL_DIS=0 ise VCO calibration başlatır."
      }
    ],
    "0x168": [
      {
        bits: "B7:B0",
        name: "PLL2_N[7:0]",
        meaning: "PLL2 feedback N divider değerinin alt bitleridir; PLL2_N programlaması internal VCO calibration akışında kritik son yazımlardan biridir."
      }
    ],
    "0x169": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6:B5",
        name: "PLL2_WND_SIZE",
        meaning: "PLL2 digital lock detect için phase-error pencere boyutunu ve izin verilen maksimum phase detector frekansını seçer.",
        values: [
          "0: reserved",
          "1: 320 MHz / 1 ns",
          "2: 240 MHz / 1.8 ns",
          "3: 160 MHz / 2.6 ns"
        ]
      },
      {
        bits: "B4:B3",
        name: "PLL2_CP_GAIN",
        meaning: "PLL2 charge pump output current seviyesini seçer; PLL2_CP_TRI ile birlikte charge pump davranışını belirler.",
        values: [
          "0: reserved",
          "1: reserved",
          "2: 1600 uA",
          "3: 3200 uA"
        ]
      },
      {
        bits: "B2",
        name: "PLL2_CP_POL",
        meaning: "Polarity kontrol alanıdır; normal/inverted davranışı seçer.",
        values: [
          "0: normal polarity",
          "1: inverted polarity"
        ]
      },
      {
        bits: "B1",
        name: "PLL2_CP_TRI",
        meaning: "PLL2 charge pump output'unu tri-state durumuna alır.",
        values: [
          "0: disabled",
          "1: tri-state"
        ]
      },
      {
        bits: "B0",
        name: "PLL2_DLD_EN",
        meaning: "Enable kontrol alanıdır; ilgili fonksiyon, pin yolu veya clock bloğunu açıp kapatır.",
        values: [
          "0: disabled/not enabled",
          "1: enabled"
        ]
      }
    ],
    "0x16A": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5:B0",
        name: "PLL2_DLD_CNT[13:8]",
        meaning: "PLL2 digital lock detect assert olmadan önce reference/feedback faz hatasının PLL2_WND_SIZE içinde kalması gereken cycle sayısının üst bitleridir."
      }
    ],
    "0x16B": [
      {
        bits: "B7:B0",
        name: "PLL2_DLD_CNT[7:0]",
        meaning: "PLL2 digital lock detect assert olmadan önce reference/feedback faz hatasının PLL2_WND_SIZE içinde kalması gereken cycle sayısının alt bitleridir."
      }
    ],
    "0x16C": [
      {
        bits: "B7:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x173": [
      {
        bits: "B7",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B6",
        name: "PLL2_PRE_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B5",
        name: "PLL2_PD",
        meaning: "Power-down kontrol alanıdır; ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.",
        values: [
          "0: normal/enabled",
          "1: power-down"
        ]
      },
      {
        bits: "B4:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x177": [
      {
        bits: "B7:B6",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B5",
        name: "PLL1R_RST",
        meaning: "PLL1 R divider senkronizasyonu için divider'ı reset/arm eder; PLL1R_SYNC_EN ve seçilen sync kaynağıyla birlikte 1 sonra 0 yazılır."
      },
      {
        bits: "B4:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x182": [
      {
        bits: "B7:B2",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B1",
        name: "CLR_PLL1_LD_LOST",
        meaning: "Latched RB_PLL1_DLD_LOST durumunu temizlemek için 1 sonra 0 yazılır; 0 iken sonraki PLL1 DLD falling edge tekrar lost set edebilir.",
        values: [
          "0: sonraki PLL1 DLD falling edge lost bitini set edebilir",
          "1: RB_PLL1_DLD_LOST clear durumda tutulur"
        ]
      },
      {
        bits: "B0",
        name: "CLR_PLL2_LD_LOST",
        meaning: "Latched RB_PLL2_DLD_LOST durumunu temizlemek için 1 sonra 0 yazılır; 0 iken sonraki PLL2 DLD falling edge tekrar lost set edebilir.",
        values: [
          "0: sonraki PLL2 DLD falling edge lost bitini set edebilir",
          "1: RB_PLL2_DLD_LOST clear durumda tutulur"
        ]
      }
    ],
    "0x183": [
      {
        bits: "B7:B4",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B3",
        name: "RB_PLL1_DLD_LOST",
        meaning: "PLL1 digital lock detect falling edge görüldüğünde set olan latched lost status bitidir; PLL1 DLD low iken clear edilirse set olmaz.",
        values: [
          "0: PLL1 DLD lost latched değil",
          "1: PLL1 DLD high'dan low'a düşmüş"
        ]
      },
      {
        bits: "B2",
        name: "RB_PLL1_DLD",
        meaning: "PLL1 digital lock detect anlık readback bitidir.",
        values: [
          "0: PLL1 DLD low; PLL1 lock detect assert değil",
          "1: PLL1 DLD high; PLL1 lock detect assert"
        ]
      },
      {
        bits: "B1",
        name: "RB_PLL2_DLD_LOST",
        meaning: "PLL2 digital lock detect falling edge görüldüğünde set olan latched lost status bitidir; PLL2 DLD low iken clear edilirse set olmaz.",
        values: [
          "0: PLL2 DLD lost latched değil",
          "1: PLL2 DLD high'dan low'a düşmüş"
        ]
      },
      {
        bits: "B0",
        name: "RB_PLL2_DLD",
        meaning: "PLL2 digital lock detect anlık readback bitidir; geçerli okuma için PLL2 DLD veya PLL1+PLL2 DLD status pin mux'a verilmeli ya da PLL2_DLD_EN=1 olmalıdır.",
        values: [
          "0: PLL2 DLD low; PLL2 lock detect assert değil",
          "1: PLL2 DLD high; PLL2 lock detect assert"
        ]
      }
    ],
    "0x184": [
      {
        bits: "B7:B6",
        name: "RB_DAC_VALUE[9:8]",
        meaning: "Holdover DAC readback değerinin üst iki bitidir; 0x185 ile birlikte 10-bit RB_DAC_VALUE oluşturur."
      },
      {
        bits: "B5",
        name: "RB_CLKin2_SEL",
        meaning: "CLKin2'nin PLL1 input'u olarak seçili olup olmadığını gösteren readback bitidir.",
        values: [
          "0: CLKin2 PLL1 input'u olarak seçili değil",
          "1: CLKin2 PLL1 input'u olarak seçili"
        ]
      },
      {
        bits: "B4",
        name: "RB_CLKin1_SEL",
        meaning: "CLKin1'in PLL1 input'u olarak seçili olup olmadığını gösteren readback bitidir.",
        values: [
          "0: CLKin1 PLL1 input'u olarak seçili değil",
          "1: CLKin1 PLL1 input'u olarak seçili"
        ]
      },
      {
        bits: "B3",
        name: "RB_CLKin0_SEL",
        meaning: "CLKin0'ın PLL1 input'u olarak seçili olup olmadığını gösteren readback bitidir.",
        values: [
          "0: CLKin0 PLL1 input'u olarak seçili değil",
          "1: CLKin0 PLL1 input'u olarak seçili"
        ]
      },
      {
        bits: "B2",
        name: "RB_CLKin2_LOS",
        meaning: "CLKin2 loss-of-signal durumunu gösteren readback bitidir.",
        values: [
          "0: CLKin2 LOS active değil",
          "1: CLKin2 LOS active"
        ]
      },
      {
        bits: "B1",
        name: "RB_CLKin1_LOS",
        meaning: "CLKin1 loss-of-signal durumunu gösteren readback bitidir.",
        values: [
          "0: CLKin1 LOS active değil",
          "1: CLKin1 LOS active"
        ]
      },
      {
        bits: "B0",
        name: "RB_CLKin0_LOS",
        meaning: "CLKin0 loss-of-signal durumunu gösteren readback bitidir.",
        values: [
          "0: CLKin0 LOS active değil",
          "1: CLKin0 LOS active"
        ]
      }
    ],
    "0x185": [
      {
        bits: "B7:B0",
        name: "RB_DAC_VALUE[7:0]",
        meaning: "Holdover DAC readback değerinin alt sekiz bitidir; 0x184[7:6] ile birlikte 10-bit DAC value okunur."
      }
    ],
    "0x188": [
      {
        bits: "B7:B5",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      },
      {
        bits: "B4",
        name: "RB_HOLDOVER",
        meaning: "Cihazın holdover modunda olup olmadığını gösteren readback status bitidir.",
        values: [
          "0: holdover active değil",
          "1: holdover active"
        ]
      },
      {
        bits: "B3:B0",
        name: "NA",
        meaning: "Reserved/sabit alan; TI datasheet bu bitlerin belirtilen reset/program değerinden farklı kullanılmamasını ister."
      }
    ],
    "0x555": [
      {
        bits: "B7:B0",
        name: "SPI_LOCK",
        meaning: "SPI register yazımlarını kilitleyen alandır; 0 unlock, 1..255 lock davranışı verir.",
        values: [
          "0: registers unlocked",
          "1..255: registers locked"
        ]
      }
    ]
  },
  LMX2820: {
    "0x00": [
      {
        bits: "15:14",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      },
      {
        bits: "13",
        name: "INSTCAL_SKIP_ACAL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Disable this bit when doing instant calibration. When not using instant calibration, it is recommended to enable it for faster VCO Calibration."
      },
      {
        bits: "12:11",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "10:9",
        name: "FCAL_HPFD_ADJ",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Set this field in accordance to the phase detector frequency for optimal VCO calibration.",
        values: [
          "0x0: fPD ≤ 100 MHz",
          "0x1: 100 MHz < fPD ≤ 150 MHz",
          "0x2: 150 MHz < fPD ≤ 200 MHz",
          "0x3: fPD > 200 MHz"
        ]
      },
      {
        bits: "8:7",
        name: "FCAL_LPFD_ADJ",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Set this field in accordance to the phase detector frequency for optimal VCO calibration.",
        values: [
          "0x0: fPD ≥ 10 MHz",
          "0x1: 10 MHz > fPD ≥ 5 MHz",
          "0x2: 5 MHz > fPD ≥ 2.5 MHz",
          "0x3: fPD < 2.5 MHz"
        ]
      },
      {
        bits: "6",
        name: "DBLR_CAL_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables VCO doubler calibration.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      },
      {
        bits: "4",
        name: "FCAL_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables and activates VCO calibration. Writing register R0 with this bit set to a 1 enables and triggers VCO calibration.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "3:2",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "1",
        name: "RESET",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Resets all registers to silicon default values. This bit is self-clearing.",
        values: [
          "0x0: Normal operation",
          "0x1: Reset"
        ]
      },
      {
        bits: "0",
        name: "POWERDOWN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Powers down the device.",
        values: [
          "0x0: Normal operation",
          "0x1: Power down"
        ]
      }
    ],
    "0x01": [
      {
        bits: "15",
        name: "PHASE_SYNC_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables phase synchronization. A Low-High-Low pulse is required at the PSYNC pin to trigger synchronization.Enable SYSREF requires PHASE_SYNC_EN = 1.",
        values: [
          "0x0: Normal operation",
          "0x1: Phase synchronization enabled"
        ]
      },
      {
        bits: "14:6",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x15E. TI açıklaması: Program 0x15E to this field."
      },
      {
        bits: "5",
        name: "LD_VTUNE_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Selects lock detect type. VCOCal lock detect asserts a HIGH output after the VCO has finished calibration and the LD_DLY timeout counter is finished. VCOCal and Vtune lock detect asserts a HIGH output when VCOCal lock detect would assert a signal and the tuning voltage to the VCO is within acceptable limits.",
        values: [
          "0x0: VCOCal lock detect",
          "0x1: VCOCal and Vtune lock detect"
        ]
      },
      {
        bits: "4:2",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "1",
        name: "INSTCAL_DBLR_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets this bit to 1 if VCO doubler is engaged.",
        values: [
          "0x0: Normal operation",
          "0x1: VCO doubler is engaged"
        ]
      },
      {
        bits: "0",
        name: "INSTCAL_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables instant calibration.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      }
    ],
    "0x02": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      },
      {
        bits: "14:12",
        name: "CAL_CLK_DIV",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Divides down the state machine clock (fsm) during VCO calibration. Maximum fsm is 200 MHz. fsm = fOSCIN / (2CAL_CLK_DIV). All other values are reserved",
        values: [
          "0x0: fOSCIN ≤ 200 MHz",
          "0x1: fOSCIN ≤ 400 MHz",
          "0x2: fOSCIN ≤ 800 MHz",
          "0x3: All other fOSCIN values"
        ]
      },
      {
        bits: "11:1",
        name: "INSTCAL_DLY",
        meaning: "R/W alan; reset 0x1F4. TI açıklaması: Sets the wait time for instant calibration. INSTCAL_DLY = T x fOSCIN / (2CAL_CLK_DIV). T = 2.5 x CBIASVCO / 4.7 µF. CBIASVCO is the bypass capacitor at pin 3."
      },
      {
        bits: "0",
        name: "QUICK_RECAL_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Starts VCO calibration with the current VCO_SEL, VCO_CAPCTRL and VCO_DACISET values.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      }
    ],
    "0x03": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x41. TI açıklaması: Program 0x41 to this field."
      }
    ],
    "0x04": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x4204. TI açıklaması: Program 0x4204 to this field."
      }
    ],
    "0x05": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3832. TI açıklaması: Program 0x32 to this field."
      }
    ],
    "0x06": [
      {
        bits: "15:8",
        name: "ACAL_CMP_DLY",
        meaning: "R/W alan; reset 0xA. TI açıklaması: VCO amplitude calibration delay. Lowering this value can speed up calibration time. If too low, phase noise may not be optimal due to insufficient time to reach final calibrated amplitude. Delay time = ACAL_CMP_DLY x 2 x state machine clock cycle."
      },
      {
        bits: "7:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x43. TI açıklaması: Program 0x43 to this field."
      }
    ],
    "0x07": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xC8. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x08": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xC802. TI açıklaması: Program 0xC802 to this field."
      }
    ],
    "0x09": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x5. TI açıklaması: Program 0x5 to this field."
      }
    ],
    "0x0A": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "12",
        name: "PFD_DLY_MANUAL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables manual PFD_DLY adjustment.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "11",
        name: "VCO_DACISET_FORCE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Forces the VCO to use the current setting specified by VCO_DACISET. Useful for full-assisted VCO calibration and debugging purposes.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "10:8",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "7",
        name: "VCO_CAPCTRL_FORCE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Forces the VCO to use the sub-band specified by VCO_CAPCTRL. Useful for full-assisted VCO calibration and debugging purposes.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "6:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x0B": [
      {
        bits: "15:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x30. TI açıklaması: Program 0x30 to this field."
      },
      {
        bits: "4",
        name: "OSC_2X",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables reference input doubler.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "3:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Program 0x2 to this field."
      }
    ],
    "0x0C": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field. Bit Field Type Reset Description"
      },
      {
        bits: "12:10",
        name: "MULT",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Sets reference path frequency multiplier value. All other values are reserved",
        values: [
          "0x1: Bypassed",
          "0x3: x3",
          "0x4: x4",
          "0x5: x5",
          "0x6: x6",
          "0x7: x7"
        ]
      },
      {
        bits: "9:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x8. TI açıklaması: Program 0x8 to this field."
      }
    ],
    "0x0D": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "12:5",
        name: "PLL_R",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Sets reference path Post-R divider value."
      },
      {
        bits: "4:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x18. TI açıklaması: Program 0x18 to this field."
      }
    ],
    "0x0E": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Program 0x3 to this field."
      },
      {
        bits: "11:0",
        name: "PLL_R_PRE",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Sets reference path Pre-R divider value."
      }
    ],
    "0x0F": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Program 0x2 to this field."
      },
      {
        bits: "11",
        name: "PFD_POL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the polarity of phase detector. Internal VCO operation requires negative Vtune with non-inverting loop filter.",
        values: [
          "0x0: Negative Vtune",
          "0x1: Positive Vtune"
        ]
      },
      {
        bits: "10:9",
        name: "PFD_SINGLE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Uses single PFD when PFDIN input is enabled. The actual charge pump current is equal to half the current setting made in CPG. Bit Field Type Reset Description",
        values: [
          "0x0: Normal operation",
          "0x1: Not used",
          "0x2: Not used",
          "0x3: Single PFD"
        ]
      },
      {
        bits: "8:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      }
    ],
    "0x10": [
      {
        bits: "15:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x138. TI açıklaması: Program 0xB8 to this field."
      },
      {
        bits: "4:1",
        name: "CPG",
        meaning: "R/W alan; reset 0xE. TI açıklaması: Sets charge pump gain value. All other values are reserved",
        values: [
          "0x0: Tri-state",
          "0x1: 1.4 mA",
          "0x4: 5.6 mA",
          "0x5: 7 mA",
          "0x6: 11.2 mA",
          "0x7: 12.6 mA",
          "0x8: 2.8 mA",
          "0x9: 4.2 mA",
          "0x12: 8.4 mA",
          "0x13: 9.8 mA",
          "0x14: 14 mA",
          "0x15: 15.4 mA"
        ]
      },
      {
        bits: "0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x11": [
      {
        bits: "5:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "6",
        name: "LD_TYPE",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Defines lock detect monitor type. One-Shot detects lock only after the VCO calibrates and the LD_DLY timeout counter is finished. Continuous lock detect checks for lock all the time, including when the input reference is removed.",
        values: [
          "0x0: One-Shot",
          "0x1: Continuous"
        ]
      },
      {
        bits: "15:7",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x28. TI açıklaması: Program 0x2B to this field."
      }
    ],
    "0x12": [
      {
        bits: "15:0",
        name: "LD_DLY",
        meaning: "R/W alan; reset 0x3E8. TI açıklaması: Lock detect assertion delay. This is the delay that is added after the VCO calibration is completed before indicating lock. This delay is only applied if LD_VTUNE_EN = 1. Delay time = LD_DLY / fPD."
      }
    ],
    "0x13": [
      {
        bits: "15:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x109. TI açıklaması: Program 0x109 to this field."
      },
      {
        bits: "4:3",
        name: "TEMPSENSE_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables temperature sensor.",
        values: [
          "0x0: Disabled",
          "0x1: Reserved",
          "0x2: Reserved",
          "0x3: Enabled"
        ]
      },
      {
        bits: "2:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x14": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x13. TI açıklaması: Program 0x13 to this field."
      },
      {
        bits: "8:0",
        name: "VCO_DACISET",
        meaning: "R/W alan; reset 0x12C. TI açıklaması: User specified start VCO current setting for calibration. Unless QUICK_RECAL_EN = 1, VCO calibration will always start with the VCO current setting that is specified in this field."
      }
    ],
    "0x15": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1C64. TI açıklaması: Program 0x1C64 to this field."
      }
    ],
    "0x16": [
      {
        bits: "15:13",
        name: "VCO_SEL",
        meaning: "R/W alan; reset 0x7. TI açıklaması: User specified start VCO core for calibration. Unless QUICK_RECAL_EN = 1, VCO calibration will always start with the VCO core that is specified in this field. ...",
        values: [
          "0x0: Reserved",
          "0x1: VCO1",
          "0x2: VCO2",
          "0x6: VCO6",
          "0x7: VCO7"
        ]
      },
      {
        bits: "12:8",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Program 0x2 to this field."
      },
      {
        bits: "7:0",
        name: "VCO_CAPCTRL",
        meaning: "R/W alan; reset 0xBF. TI açıklaması: User specified start VCO sub-band for calibration. Valid values are 191 to 0, where the higher number represents a lower frequency band. Unless QUICK_RECAL_EN = 1, VCO calibration will always start with the VCO sub-band that is specified in this field."
      }
    ],
    "0x17": [
      {
        bits: "15:1",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x881. TI açıklaması: Program 0x881 to this field."
      },
      {
        bits: "0",
        name: "VCO_SEL_FORCE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Forces the VCO to use the core specified by VCO_SEL. Useful for full-assisted VCO calibration and debugging purposes.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      }
    ],
    "0x18": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xE34. TI açıklaması: Program 0xE34 to this field."
      }
    ],
    "0x19": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x624. TI açıklaması: Program 0x624 to this field."
      }
    ],
    "0x1A": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xDB0. TI açıklaması: Program 0xDB0 to this field."
      }
    ],
    "0x1B": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x8001. TI açıklaması: Program 0x8001 to this field."
      }
    ],
    "0x1C": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x639. TI açıklaması: Program 0x639 to this field."
      }
    ],
    "0x1D": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x318C. TI açıklaması: Program 0x318C to this field."
      }
    ],
    "0x1E": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xB18C. TI açıklaması: Program 0xB18C to this field."
      }
    ],
    "0x1F": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x401. TI açıklaması: Program 0x401 to this field."
      }
    ],
    "0x20": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field. Bit Field Type Reset Description"
      },
      {
        bits: "11:9",
        name: "CHDIVB",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets divider value for RFOUTB.",
        values: [
          "0x0: Divide by 2",
          "0x1: Divide by 4",
          "0x2: Divide by 8",
          "0x3: Divide by 16",
          "0x4: Divide by 32",
          "0x5: Divide by 64",
          "0x6: Divide by 128",
          "0x7: Reserved"
        ]
      },
      {
        bits: "8:6",
        name: "CHDIVA",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets divider value for RFOUTA.",
        values: [
          "0x0: Divide by 2",
          "0x1: Divide by 4",
          "0x2: Divide by 8",
          "0x3: Divide by 16",
          "0x4: Divide by 32",
          "0x5: Divide by 64",
          "0x6: Divide by 128",
          "0x7: Reserved"
        ]
      },
      {
        bits: "5:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      }
    ],
    "0x21": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x22": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "11",
        name: "LOOPBACK_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables loop back mode. In this mode, both RFIN input path and internal VCO are active, the synthesizer will try to lock to the internal VCO. EXTVCO_EN must be set to 0 in this mode.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "10:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "4",
        name: "EXTVCO_DIV",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Sets external VCO input divider value.",
        values: [
          "0x0: Divide by 2",
          "0x1: Bypassed"
        ]
      },
      {
        bits: "3:1",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field. Bit Field Type Reset Description"
      },
      {
        bits: "0",
        name: "EXTVCO_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables external VCO mode. Set this bit to 1 will enables RFIN input path but disables internal VCO, the synthesizer will try to lock to an external source appear at RFIN pin. In loop back mode, this bit has to be set to 0, RFIN input path will be enabled by the LOOPBACK_EN bit.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      }
    ],
    "0x23": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      },
      {
        bits: "12",
        name: "MASH_RESET_N",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Resets the MASH (active LOW).",
        values: [
          "0x0: Reset",
          "0x1: Normal operation"
        ]
      },
      {
        bits: "11:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "8:7",
        name: "MASH_ORDER",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Sets the MASH order.",
        values: [
          "0x0: Integer mode",
          "0x1: First order",
          "0x2: Second order",
          "0x3: Third order"
        ]
      },
      {
        bits: "6",
        name: "MASHSEED_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables MASHSEED for phase adjustment.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "5:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x24": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "14:0",
        name: "PLL_N",
        meaning: "R/W alan; reset 0x38. TI açıklaması: Sets N divider value (integer portion)."
      }
    ],
    "0x25": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field. Bit Field Type Reset Description"
      },
      {
        bits: "14:9",
        name: "PFD_DLY",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Sets N divider delay time in phase detector. Effective only when PFD_DLY_MANUAL = 1. All other values must be set in accordance to the N divider value",
        values: [
          "0x0: Reserved"
        ]
      },
      {
        bits: "8:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x100. TI açıklaması: Program 0x100 to this field."
      }
    ],
    "0x26": [
      {
        bits: "15:0",
        name: "PLL_DEN[31:16]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the upper 16 bits of fractional denominator (DEN)."
      }
    ],
    "0x27": [
      {
        bits: "15:0",
        name: "PLL_DEN[15:0]",
        meaning: "R/W alan; reset 0x3E8. TI açıklaması: Sets the lower 16 bits of fractional denominator (DEN)."
      }
    ],
    "0x28": [
      {
        bits: "15:0",
        name: "MASH_SEED[31:16]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the upper 16 bits of MASH_SEED."
      }
    ],
    "0x29": [
      {
        bits: "15:0",
        name: "MASH_SEED[15:0]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the lower 16 bits of MASH SEED."
      }
    ],
    "0x2A": [
      {
        bits: "15:0",
        name: "PLL_NUM[31:16]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the upper 16 bits of fractional numerator (NUM)."
      }
    ],
    "0x2B": [
      {
        bits: "15:0",
        name: "PLL_NUM[15:0]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the lower 16 bits of fractional numerator (NUM)."
      }
    ],
    "0x2C": [
      {
        bits: "15:0",
        name: "INSTCAL_PLL_NUM[31:16]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the upper 16 bits of INSTCAL_PLL_NUM. INSTCAL_PLL_NUM = 232 x (PLL_NUM / PLL_DEN)."
      }
    ],
    "0x2D": [
      {
        bits: "15:0",
        name: "INSTCAL_PLL_NUM[15:0]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the lower 16 bits of INSTCAL_PLL_NUM. INSTCAL_PLL_NUM = 232 x (PLL_NUM / PLL_DEN)."
      }
    ],
    "0x2E": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x300. TI açıklaması: Program 0x300 to this field."
      }
    ],
    "0x2F": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x300. TI açıklaması: Program 0x300 to this field."
      }
    ],
    "0x30": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x4180. TI açıklaması: Program 0x4180 to this field."
      }
    ],
    "0x31": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x32": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x80. TI açıklaması: Program 0x80 to this field."
      }
    ],
    "0x33": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x203F. TI açıklaması: Program 0x203F to this field."
      }
    ],
    "0x34": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x35": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x36": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x37": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Program 0x2 to this field."
      }
    ],
    "0x38": [
      {
        bits: "15:6",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "5:0",
        name: "EXTPFD_DIV",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Sets external PFD input divider value. Set this field to 0 is not allowed. A value of 1 means bypassed."
      }
    ],
    "0x39": [
      {
        bits: "15:1",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "0",
        name: "PFD_SEL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables PFDIN input. When using PFDIN input, the charge pump has to be set to single PFD by setting PFD_SINGLE = 0x3.",
        values: [
          "0x0: Enabled",
          "0x1: Disabled"
        ]
      }
    ],
    "0x3A": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x3B": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1388. TI açıklaması: Program 0x1388 to this field."
      }
    ],
    "0x3C": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1F4. TI açıklaması: Program 0x1F4 to this field."
      }
    ],
    "0x3D": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3E8. TI açıklaması: Program 0x3E8 to this field."
      }
    ],
    "0x3E": [
      {
        bits: "15:0",
        name: "MASH_RST_COUNT[31:16]",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the upper 16 bits of MASH reset delay. This is the delay that is necessary after the MASH engine is reset during phase synchronization when PLL_NUM is not equal to zero. The delay time must be set to greater than the lock time of the PLL. Delay time = MASH_RST_COUNT x (2CAL_CLK_DIV) / fOSCIN. This field can be set to 0 when PLL_NUM = 0."
      }
    ],
    "0x3F": [
      {
        bits: "15:0",
        name: "MASH_RST_COUNT[15:0]",
        meaning: "R/W alan; reset 0xC350. TI açıklaması: Sets the lower 16 bits of MASH reset delay."
      }
    ],
    "0x40": [
      {
        bits: "15:10",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x10. TI açıklaması: Program 0x10 to this field."
      },
      {
        bits: "9:8",
        name: "SYSREF_INP_FMT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets SRREQ pin input format. differential termination differential termination",
        values: [
          "0x0: CMOS input at SRREQ_P pin, 1.8-V to 3.3-V logic",
          "0x1: AC-couple CMOS input at SRREQ_P pin",
          "0x2: AC-coupled differential LVDS input, requires external 100-Ω",
          "0x3: DC-coupled differential LVDS input, requires external 100-Ω"
        ]
      },
      {
        bits: "7:5",
        name: "SYSREF_DIV_PRE",
        meaning: "R/W alan; reset 0x4. TI açıklaması: This divider is used to get the frequency input to SYSREF_DIV within acceptable limits. All other values are reserved Bit Field Type Reset Description",
        values: [
          "0x1: Divide by 2",
          "0x2: Divide by 4",
          "0x4: Divide by 8"
        ]
      },
      {
        bits: "4",
        name: "SYSREF_REPEAT_NS",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables asynchronous SYSREF repeater mode. In this mode, the SYSREF signal coming from the SRREQ pin will be passed through to the SROUT pin without reclocking.",
        values: [
          "0x0: If SYSREF_REPEAT = 1",
          "0x1: Enabled"
        ]
      },
      {
        bits: "3",
        name: "SYSREF_PULSE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Defines SYSREF master mode. In continuous mode, SYSREF pulses are generated continuously. Pulsed mode allows multiple pulses (as determined by SYSREF_PULSE_CNT) to be sent out whenever the SRREQ pins go HIGH.",
        values: [
          "0x0: Continuous mode",
          "0x1: Pulsed mode"
        ]
      },
      {
        bits: "2",
        name: "SYSREF_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREF mode.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "1",
        name: "SYSREF_REPEAT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Defines SYSREF mode. In master mode, SYSREF pulses are generated internally. In repeater mode, SYSREF pulses are generated in response to the SRREQ pins.",
        values: [
          "0x0: Master mode",
          "0x1: Repeater mode"
        ]
      },
      {
        bits: "0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x41": [
      {
        bits: "15:11",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "10:0",
        name: "SYSREF_DIV",
        meaning: "R/W alan; reset 0x1. TI açıklaması: This divider further divides the output frequency for the SYSREF."
      }
    ],
    "0x42": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "11:6",
        name: "JESD_DAC2_CTRL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Programmable delay adjustment for SYSREF mode."
      },
      {
        bits: "5:0",
        name: "JESD_DAC1_CTRL",
        meaning: "R/W alan; reset 0x3F. TI açıklaması: Programmable delay adjustment for SYSREF mode."
      }
    ],
    "0x43": [
      {
        bits: "15:12",
        name: "SYSREF_PULSE_CNT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Defines how many pulses are sent in SYSREF pulsed mode. Bit Field Type Reset Description"
      },
      {
        bits: "11:6",
        name: "JESD_DAC4_CTRL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Programmable delay adjustment for SYSREF mode."
      },
      {
        bits: "5:0",
        name: "JESD_DAC3_CTRL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Programmable delay adjustment for SYSREF mode."
      }
    ],
    "0x44": [
      {
        bits: "15:6",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "5",
        name: "INPIN_IGNORE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Disables PSYNC pin. Keep this bit equals 1 unless phase sync is required.",
        values: [
          "0x0: Enables pin",
          "0x1: Disables pin"
        ]
      },
      {
        bits: "4:1",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "0",
        name: "PSYNC_INP_FMT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets PSYNC pin input format. differential termination",
        values: [
          "0x0: CMOS input, 1.8-V to 3.3-V logic",
          "0x1: AC-coupled differential LVDS input, requires external 100-Ω"
        ]
      }
    ],
    "0x45": [
      {
        bits: "15:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "4",
        name: "SROUT_PD",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Powerdowns SYSREF output buffer.",
        values: [
          "0x0: Normal operation",
          "0x1: Power down"
        ]
      },
      {
        bits: "3:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Program 0x1 to this field."
      }
    ],
    "0x46": [
      {
        bits: "15:8",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "7",
        name: "DBLBUF_OUTMUX_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables double buffering for OUTA_MUX and OUTB_MUX. Changes of these registers will only be effective after R0 is programmed. Bit Field Type Reset Description",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "6",
        name: "DBLBUF_OUTBUF_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables double buffering for OUTA_PD and OUTB_PD. Changes of these registers will only be effective after R0 is programmed.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "5",
        name: "DBLBUF_CHDIV_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables double buffering for CHDIVA and CHDIVB. Changes of these registers will only be effective after R0 is programmed.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "4",
        name: "DBLBUF_PLL_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables double buffering for PLL_N, PLL_NUM, PLL_DEN, MULT, PLL_R, PLL_R_PRE, MASH_ORDER and PFD_DLY. Changes of these registers will only be effective after R0 is programmed.",
        values: [
          "0x0: Disabled",
          "0x1: Enabled"
        ]
      },
      {
        bits: "3:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xE. TI açıklaması: Program 0xE to this field."
      }
    ],
    "0x47": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x48": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x49": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x4A": [
      {
        bits: "15:14",
        name: "rb_LD",
        meaning: "R alan; reset 0x0. TI açıklaması: Reads back lock detect status.",
        values: [
          "0x0: Unlocked",
          "0x1: Unlocked",
          "0x2: Locked",
          "0x3: Invalid"
        ]
      },
      {
        bits: "13",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      },
      {
        bits: "12:5",
        name: "rb_VCO_CAPCTRL",
        meaning: "R alan; reset 0x0. TI açıklaması: Reads back the actual CAPCTRL value that the VCO calibration has chosen."
      },
      {
        bits: "4:2",
        name: "rb_VCO_SEL",
        meaning: "R alan; reset 0x0. TI açıklaması: Reads back the actual VCO that the VCO calibration has selected. ...",
        values: [
          "0x0: Invalid",
          "0x1: VCO1",
          "0x2: VCO2",
          "0x6: VCO6",
          "0x7: VCO7"
        ]
      },
      {
        bits: "1:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x4B": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      },
      {
        bits: "8:0",
        name: "rb_VCO_DACISET",
        meaning: "R alan; reset 0x0. TI açıklaması: Reads back the actual DACISET value that the VCO calibration has chosen."
      }
    ],
    "0x4C": [
      {
        bits: "15:11",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      },
      {
        bits: "10:0",
        name: "rb_TEMP_SENS",
        meaning: "R alan; reset 0x0. TI açıklaması: Reads back temperature sensor code. Temperature in °C = 0.85 x code - 415. Resolution is 0.6°C per code. Measurement accuracy is ±5 degrees."
      }
    ],
    "0x4D": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x2B. TI açıklaması: Program 0x3 to this field."
      },
      {
        bits: "8",
        name: "PINMUTE_POL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the polarity of mute control for MUTE pin. Bit Field Type Reset Description",
        values: [
          "0x0: Active HIGH",
          "0x1: Active LOW"
        ]
      },
      {
        bits: "7:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xCC. TI açıklaması: Program 0x8 to this field."
      }
    ],
    "0x4E": [
      {
        bits: "15:5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "4",
        name: "OUTA_PD",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Power downs RFOUTA.",
        values: [
          "0x0: Normal operation",
          "0x1: Power down"
        ]
      },
      {
        bits: "3:2",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "1:0",
        name: "OUTA_MUX",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Selects the input source to RFOUTA.",
        values: [
          "0x0: Channel divider",
          "0x1: VCO",
          "0x2: VCO doubler",
          "0x3: Reserved"
        ]
      }
    ],
    "0x4F": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "8",
        name: "OUTB_PD",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Power downs RFOUTB.",
        values: [
          "0x0: Normal operation",
          "0x1: Power down"
        ]
      },
      {
        bits: "7:6",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      },
      {
        bits: "5:4",
        name: "OUTB_MUX",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Selects the input source to RFOUTB.",
        values: [
          "0x0: Channel divider",
          "0x1: VCO",
          "0x2: VCO doubler",
          "0x3: Reserved"
        ]
      },
      {
        bits: "3:1",
        name: "OUTA_PWR",
        meaning: "R/W alan; reset 0x7. TI açıklaması: Adjusts RFOUTA output power. Higher numbers give more output power."
      },
      {
        bits: "0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x50": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field. Bit Field Type Reset Description"
      },
      {
        bits: "8:6",
        name: "OUTB_PWR",
        meaning: "R/W alan; reset 0x7. TI açıklaması: Adjusts RFOUTB output power. Higher numbers give more output power."
      },
      {
        bits: "5:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x51": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x52": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x53": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xF00. TI açıklaması: Program 0xF00 to this field."
      }
    ],
    "0x54": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x40. TI açıklaması: Program 0x40 to this field."
      }
    ],
    "0x55": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x56": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x40. TI açıklaması: Program 0x40 to this field."
      }
    ],
    "0x57": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xFF00. TI açıklaması: Program 0xFF00 to this field."
      }
    ],
    "0x58": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3FF. TI açıklaması: Program 0x3FF to this field."
      }
    ],
    "0x59": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x5A": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x5B": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x5C": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x5D": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1000. TI açıklaması: Program 0x1000 to this field."
      }
    ],
    "0x5E": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x5F": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x60": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x17F8. TI açıklaması: Program 0x17F8 to this field."
      }
    ],
    "0x61": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x62": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1C80. TI açıklaması: Program 0x1C80 to this field."
      }
    ],
    "0x63": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x19B9. TI açıklaması: Program 0x19B9 to this field."
      }
    ],
    "0x64": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x533. TI açıklaması: Program 0x533 to this field."
      }
    ],
    "0x65": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x3E8. TI açıklaması: Program 0x3E8 to this field."
      }
    ],
    "0x66": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x28. TI açıklaması: Program 0x28 to this field."
      }
    ],
    "0x67": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x14. TI açıklaması: Program 0x14 to this field."
      }
    ],
    "0x68": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x14. TI açıklaması: Program 0x14 to this field."
      }
    ],
    "0x69": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xA. TI açıklaması: Program 0xA to this field."
      }
    ],
    "0x6A": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x6B": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x6C": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x6D": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x6E": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1F. TI açıklaması: Program 0x1F to this field."
      }
    ],
    "0x6F": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Program 0x0 to this field."
      }
    ],
    "0x70": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0xFFFF. TI açıklaması: Program 0xFFFF to this field."
      }
    ],
    "0x71": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x72": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x73": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x74": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x75": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x76": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x77": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x78": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x79": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ],
    "0x7A": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Not used. Read back only."
      }
    ]
  },
  LMX1204: {
    "0x00": [
      {
        bits: "15:3",
        name: "RESERVED",
        meaning: "R alan; reset 0x0000. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "2",
        name: "POWERDOWN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the device in a low-power state. The states of other registers are maintained."
      },
      {
        bits: "1",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set this bit to 0x0."
      },
      {
        bits: "0",
        name: "RESET",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Soft Reset. Resets the entire logic and registers (equivalent to power-on reset). Self-clearing on next register write."
      }
    ],
    "0x02": [
      {
        bits: "15:11",
        name: "RESERVED",
        meaning: "R alan; reset 0x00. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "10",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set this bit to 0x0."
      },
      {
        bits: "9:6",
        name: "SMCLK_DIV_PRE",
        meaning: "R/W alan; reset 0x8. TI açıklaması: Sets pre-divider for state machine clock. The state machine clock is divided from CLKIN. The output of the pre-divider must be ≤ 1600 MHz. Values other than those listed below are reserved.",
        values: [
          "0x2: ÷2",
          "0x4: ÷4",
          "0x8: ÷8"
        ]
      },
      {
        bits: "5",
        name: "SMCLK_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables the state machine clock generator. Only required to calibrate the multiplier, and for multiplier lock detect (including on MUXOUT pin). If the multiplier is not used, or if the multiplier lock detect feature is not used, the state machine clock generator can be disabled to minimize crosstalk."
      },
      {
        bits: "4:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x03. TI açıklaması: Reserved. If this register is written, set these bits to 0x03."
      }
    ],
    "0x03": [
      {
        bits: "15",
        name: "CH3_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CH3 (CLKOUT3, SYSREFOUT3). Setting this bit to 0x0 completely disables all CH3 circuitry, overriding the state of other powerdown/enable bits."
      },
      {
        bits: "14",
        name: "CH2_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CH2 (CLKOUT2, SYSREFOUT2). Setting this bit to 0x0 completely disables all CH2 circuitry, overriding the state of other powerdown/enable bits."
      },
      {
        bits: "13",
        name: "CH1_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CH1 (CLKOUT1, SYSREFOUT1). Setting this bit to 0x0 completely disables all CH1 circuitry, overriding the state of other powerdown/enable bits."
      },
      {
        bits: "12",
        name: "CH0_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CH0 (CLKOUT0, SYSREFOUT0). Setting this bit to 0x0 completely disables all CH0 circuitry, overriding the state of other powerdown/enable bits."
      },
      {
        bits: "11",
        name: "LOGIC_MUTE_CAL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Mutes LOGIC outputs (LOGICLKOUT, LOGISYSREFOUT) during multiplier calibration."
      },
      {
        bits: "10",
        name: "CH3_MUTE_CAL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Mutes CH3 (CLKOUT3, SYSREFOUT3) during multiplier calibration."
      },
      {
        bits: "9",
        name: "CH2_MUTE_CAL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Mutes CH2 (CLKOUT2, SYSREFOUT2) during multiplier calibration."
      },
      {
        bits: "8",
        name: "CH1_MUTE_CAL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Mutes CH1 (CLKOUT1, SYSREFOUT1) during multiplier calibration."
      },
      {
        bits: "7",
        name: "CH0_MUTE_CAL",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Mutes CH0 (CLKOUT0, SYSREFOUT0) during multiplier calibration."
      },
      {
        bits: "6:3",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set these bits to 0x0."
      },
      {
        bits: "2:0",
        name: "SMCLK_DIV",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Sets state machine clock divider. Further divides the output of the state machine clock pre-divider. Input frequency from SMCLK_DIV_PRE must be ≤ 1600 MHz. Output frequency must be ≤ 30 MHz. Divide value is 2SMCLK_DIV.",
        values: [
          "0x0: ÷1",
          "0x1: ÷2",
          "0x2: ÷4",
          "0x3: ÷8",
          "0x4: ÷16",
          "0x5: ÷32",
          "0x6: ÷64",
          "0x7: ÷128"
        ]
      }
    ],
    "0x04": [
      {
        bits: "15:14",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "13:11",
        name: "CLKOUT1_PWR",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Sets the output power of CLKOUT1. Larger values correspond to higher output power."
      },
      {
        bits: "10:8",
        name: "CLKOUT0_PWR",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Sets the output power of CLKOUT0. Larger values correspond to higher output power."
      },
      {
        bits: "7",
        name: "SYSREFOUT3_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREFOUT3 output buffer."
      },
      {
        bits: "6",
        name: "SYSREFOUT2_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREFOUT2 output buffer."
      },
      {
        bits: "5",
        name: "SYSREFOUT1_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREFOUT1 output buffer."
      },
      {
        bits: "4",
        name: "SYSREFOUT0_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREFOUT0 output buffer."
      },
      {
        bits: "3",
        name: "CLKOUT3_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CLKOUT3 output buffer."
      },
      {
        bits: "2",
        name: "CLKOUT2_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CLKOUT2 output buffer."
      },
      {
        bits: "1",
        name: "CLKOUT1_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CLKOUT1 output buffer."
      },
      {
        bits: "0",
        name: "CLKOUT0_EN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Enables CLKOUT0 output buffer."
      }
    ],
    "0x05": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "14:12",
        name: "SYSREFOUT2_PWR",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets the output power of SYSREFOUT2. Larger values correspond to higher output power. SYSREFOUT2_VCM must be set properly to bring the output common-mode voltage within permissible limits. See also R6 Register."
      },
      {
        bits: "11:9",
        name: "SYSREFOUT1_PWR",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets the output power of SYSREFOUT1. Larger values correspond to higher output power. SYSREFOUT1_VCM must be set properly to bring the output common-mode voltage within permissible limits. See also R6 Register."
      },
      {
        bits: "8:6",
        name: "SYSREFOUT0_PWR",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets the output power of SYSREFOUT0. Larger values correspond to higher output power. SYSREFOUT0_VCM must be set properly to bring the output common-mode voltage within permissible limits. See also R6 Register."
      },
      {
        bits: "5:3",
        name: "CLKOUT3_PWR",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Sets the output power of CLKOUT3. Larger values correspond to higher output power."
      },
      {
        bits: "2:0",
        name: "CLKOUT2_PWR",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Sets the output power of CLKOUT2. Larger values correspond to higher output power."
      }
    ],
    "0x06": [
      {
        bits: "15",
        name: "LOGICLKOUT_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables the LOGICLKOUT output buffer."
      },
      {
        bits: "14:12",
        name: "SYSREFOUT3_VCM",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the output common mode of SYSREFOUT3. SYSREFOUT3_PWR must be set properly to bring the minimum and maximum output voltage within permissible limits."
      },
      {
        bits: "11:9",
        name: "SYSREFOUT2_VCM",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the output common mode of SYSREFOUT2. SYSREFOUT2_PWR must be set properly to bring the minimum and maximum output voltage within permissible limits. See also R5 Register."
      },
      {
        bits: "8:6",
        name: "SYSREFOUT1_VCM",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the output common mode of SYSREFOUT1. SYSREFOUT1_PWR must be set properly to bring the minimum and maximum output voltage within permissible limits. See also R5 Register."
      },
      {
        bits: "5:3",
        name: "SYSREFOUT0_VCM",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the output common mode of SYSREFOUT0. SYSREFOUT0_PWR must be set properly to bring the minimum and maximum output voltage within permissible limits. See also R5 Register."
      },
      {
        bits: "2:0",
        name: "SYSREFOUT3_PWR",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets the output power of SYSREFOUT3. Larger values correspond to higher output power. SYSREFOUT3_VCM must be set properly to bring the output common-mode voltage within permissible limits."
      }
    ],
    "0x07": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "14:13",
        name: "LOGISYSREFOUT_VCM",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output common mode of LOGISYSREFOUT in LVDS format. Other output formats (CML, LVPECL) ignore this field.",
        values: [
          "0x0: 1.2 V",
          "0x1: 1.1 V",
          "0x2: 1.0 V",
          "0x3: 0.9 V"
        ]
      },
      {
        bits: "12:11",
        name: "LOGICLKOUT_VCM",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output common mode of LOGICLKOUT in LVDS format. Other output formats (CML, LVPECL) ignore this field.",
        values: [
          "0x0: 1.2 V",
          "0x1: 1.1 V",
          "0x2: 1.0 V",
          "0x3: 0.9 V"
        ]
      },
      {
        bits: "10:9",
        name: "LOGISYSREFOUT_PRED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output power of the LOGISYSREFOUT pre-driver. Larger RV_PWR values correspond to higher output power. Default value is sufficient for typical use."
      },
      {
        bits: "8:7",
        name: "LOGICLKOUT_PREDRV_",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output power of the LOGICLKOUT pre-driver. Larger values PWR correspond to higher output power. Default value is sufficient for typical use."
      },
      {
        bits: "6:4",
        name: "LOGISYSREFOUT_PWR",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output power of LOGISYSREFOUT in CML format. Larger values correspond to higher output power. Other output formats (LVDS, LVPECL) ignore this field. Valid range is 0x0 to 0x3."
      },
      {
        bits: "3:1",
        name: "LOGICLKOUT_PWR",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the output power of LOGICLKOUT in CML format. Larger values correspond to higher output power. Other output formats (LVDS, LVPECL) ignore this field. Valid range is 0x0 to 0x3."
      },
      {
        bits: "0",
        name: "LOGISYSREFOUT_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables LOGISYSREFOUT output buffer."
      }
    ],
    "0x08": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R alan; reset 0x00. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "8:6",
        name: "LOGICLK_DIV_PRE",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets pre-divider value for logic clock divider. Output of the pre-divider must be ≤ 3.2 GHz. Values other than those listed below are reserved.",
        values: [
          "0x1: ÷1",
          "0x2: ÷2",
          "0x4: ÷4"
        ]
      },
      {
        bits: "5",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Reserved. If this register is written, set this bit to 0x1."
      },
      {
        bits: "4",
        name: "LOGIC_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables LOGICLK subsystem (LOGICLKOUT, LOGISYSREFOUT). Setting this bit to 0x0 completely disables all LOGICLKOUT and LOGISYSREFOUT circuitry, overriding the state of other powerdown/ enable bits."
      },
      {
        bits: "3:2",
        name: "LOGISYSREFOUT_FMT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Selects the output driver format of the LOGISYSREFOUT output. LVDS allows for common mode control with LOGISYSREFOUT_VCM field. CML allows for output power control with LOGISYSREFOUT_PWR field. CML format requires external 50-Ω pull-up resistors. LVPECL requires external 220-Ω emitter resistors to GND when AC-coupled, or 50-Ω to VCC - 2 V (0.5 V) when DC-coupled. See also R7 Register.",
        values: [
          "0x0: LVDS",
          "0x1: LVPECL",
          "0x2: CML",
          "0x3: Reserved"
        ]
      },
      {
        bits: "1:0",
        name: "LOGICLKOUT_FMT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Selects the output driver format of the LOGICLKOUT output. LVDS allows for common mode control with LOGICLKOUT_VCM field. CML allows for output power control with LOGICLKOUT_PWR field. CML format requires external 50-Ω pull-up resistors. LVPECL requires external 220-Ω emitter resistors to GND when AC-coupled, or 50-Ω to VCC - 2 V (0.5 V) when DC-coupled. See also R7 Register.",
        values: [
          "0x0: LVDS",
          "0x1: LVPECL",
          "0x2: CML",
          "0x3: Reserved"
        ]
      }
    ],
    "0x09": [
      {
        bits: "15:14",
        name: "SYSREFREQ_VCM",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the internal DC Bias for the SYSREFREQ pins. Bias must be enabled for AC-coupled inputs; but can be enabled and overdriven, or disabled, for DC-coupled inputs. SYSREFREQ DC pin voltage must be in the range of 0.7 V to VCC, including minimum and maximum signal swing.",
        values: [
          "0x0: 1.3 V",
          "0x1: 1.1 V",
          "0x2: 1.5 V",
          "0x3: Disabled (DC-coupled only)"
        ]
      },
      {
        bits: "13",
        name: "SYNC_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables synchronization path for the dividers and allows the clock position capture circuitry to be enabled. Used for multi-device synchronization. Redundant if SYSREF_EN = 0x1."
      },
      {
        bits: "12",
        name: "LOGICLK_DIV_PD",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Disables the LOGICLK divider. LOGICLK pre-divider remains enabled. Used to reduce current consumption when bypassing the LOGICLK divider. When LOGICLK_DIV_PRE = 0x2 or 0x4, this bit must be set to 0x0."
      },
      {
        bits: "11",
        name: "LOGICLK_DIV_BYPASS",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Bypasses the LOGICLK divider, deriving LOGICLK output directly from the pre-divider. Used to achieve divide-by-1 when LOGICLK_DIV_PRE = 0x1. When LOGICLK_DIV_PRE = 0x2 or 0x4, this bit must be set to 0x0. When LOGICLK_DIV_BYPASS = 0x1, set R90[6:5] = 0x3 and R79[9:8] = 0x0. When LOGICLK_DIV_BYPASS = 0x0, if R90[6:5] = 0x3 due to previous user setting, set R90[6:5] = 0x0. When LOGICLK_DIV_BYPASS = 0x1, the LOGICLKOUT frequency must be ≤ 800 MHz to avoid amplitude degradation. See also R79 Register and R90 Register."
      },
      {
        bits: "10",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set this bit to 0x0."
      },
      {
        bits: "9:0",
        name: "LOGICLK_DIV",
        meaning: "R/W alan; reset 0x1E. TI açıklaması: Sets LOGICLK divider value. Maximum input frequency from LOGICLK_DIV_PRE must be ≤ 3200 MHz. The maximum LOGICLKOUT frequency must be ≤ 800 MHz to avoid amplitude degradation. ...",
        values: [
          "0x0: Reserved",
          "0x1: Reserved",
          "0x2: ÷2",
          "0x3: ÷3",
          "0x1FF: ÷1023"
        ]
      }
    ],
    "0x0B": [
      {
        bits: "15:0",
        name: "rb_CLKPOS[15:0]",
        meaning: "R alan; reset 0xFFFF. TI açıklaması: Stores a snapshot of the CLKIN signal rising edge positions relative to a SYSREFREQ rising edge, with the snapshot starting from the LSB and ending at the MSB. Each bit represents a sample of the CLKIN signal, separated by a delay determined by the SYSREFREQ_DELAY_STEPSIZE field. The first and last bits of rb_CLKPOS are always set, indicating uncertainty at the capture window boundary conditions. CLKIN rising edges are represented by every sequence of two set bits from LSB to MSB, including bits at the boundary conditions. The position of the CLKIN rising edges in the snapshot, along with the CLKIN signal period and the delay step size, can be used to compute the value of SYSREFREQ_DELAY_STEP which maximizes setup and hold times for SYNC signals on the SYSREFREQ pins. See also R12 Register, R13 Register, R14 Register, and R15 Register."
      }
    ],
    "0x0C": [
      {
        bits: "15:0",
        name: "rb_CLKPOS[31:16]",
        meaning: "R alan; reset 0xFFFF. TI açıklaması: MSBs of rb_CLKPOS field. See also R11 Register, R13 Register, R14 Register, and R15 Register."
      }
    ],
    "0x0D": [
      {
        bits: "15:2",
        name: "RESERVED",
        meaning: "R alan; reset 0x0000. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "1:0",
        name: "SYSREFREQ_DELAY_STEPSIZE",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the step size of the delay element used in the SYSREFREQ path, both for SYSREFREQ input delay and for clock position captures. The recommended frequency range for each step size creates the maximum number of usable steps for a given CLKIN frequency. The ranges include some overlap to account for process and temperature variations. If the CLKIN frequency is covered by an overlapping span, larger delay step sizes improve the likelihood of detecting a CLKIN rising edge during a clock position capture. However, since larger values include more delay steps, larger step sizes have greater total delay variation across PVT relative to smaller step sizes. See also R11 Register, R12 Register, R14 Register, and R15 Register.",
        values: [
          "0x0: 28 ps (1.4 GHz to 2.7 GHz)",
          "0x1: 15 ps (2.4 GHz to 4.7 GHz)",
          "0x2: 11 ps (3.1 GHz to 5.7 GHz)",
          "0x3: 8 ps (4.5 GHz to 12.8 GHz)"
        ]
      }
    ],
    "0x0E": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x00. TI açıklaması: Reserved. If this register is written, set these bits to 0x00."
      },
      {
        bits: "8",
        name: "SYNC_MUTE_PD",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Removes the mute condition on the SYSREFOUT and LOGISYSREFOUT pins during SYNC mode (SYSREFREQ_MODE = 0x0). Since the SYNC operation also resets the SYSREF dividers, the mute condition is usually desirable, and this bit can be left at the default value."
      },
      {
        bits: "7:3",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x00. TI açıklaması: Reserved. If this register is written, set these bits to 0x00."
      },
      {
        bits: "2",
        name: "CLKPOS_CAPTURE_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables the windowing circuit which captures the clock position in the rb_CLKPOS registers with respect to a SYSREF edge. The windowing circuit must be cleared by toggling SYSREFREQ_CLR high then low before a clock position capture. The first rising edge on the SYSREFREQ pins after clearing the windowing circuit triggers the capture. The capture circuitry greatly increases supply current, and does not need to be enabled to delay the SYSREFREQ signal in SYNC or SYSREF modes. Once the desired value of SYSREFREQ_DELAY_STEP is determined, set this bit to 0x0 to minimize current consumption. If SYNC_EN = 0x0 and SYSREF_EN = 0x0, the value of this bit is ignored, and the windowing circuit is disabled. See also R11 Register, R12 Register, R13 Register, and R15 Register."
      },
      {
        bits: "1",
        name: "SYSREFREQ_MODE",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Selects the function of the SYSREFREQ pins.",
        values: [
          "0x0: SYNC Pin",
          "0x1: SYSREFREQ Pin"
        ]
      },
      {
        bits: "0",
        name: "SYSREFREQ_LATCH",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Latches the internal SYSREFREQ state to logic high on the first rising edge of the SYSREFREQ pins. This latch can be cleared by setting SYSREFREQ_CLR to 0x1, or bypassed by setting SYSREFREQ_LATCH to 0x0. See also R15 Register."
      }
    ],
    "0x0F": [
      {
        bits: "15:12",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "11:10",
        name: "SYSREF_DIV_PRE",
        meaning: "R/W alan; reset 0x2. TI açıklaması: Sets the SYSREF pre-divider. Maximum output frequency must be ≤ 3.2 GHz.",
        values: [
          "0x0: ÷1",
          "0x1: ÷2",
          "0x2: ÷4",
          "0x3: Reserved"
        ]
      },
      {
        bits: "9:8",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Reserved. If this register is written, set these bits to 0x1."
      },
      {
        bits: "7",
        name: "SYSREF_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables SYSREF subsystem (and SYNC subsystem when SYSREFREQ_MODE = 0x0). Setting this bit to 0x0 completely disables all SYNC, SYSREF, and clock position capture circuitry, overriding the state of other powerdown/enable bits except SYNC_EN. If SYNC_EN = 0x1, the SYNC path and clock position capture circuitry are still enabled, regardless of the state of SYSREF_EN."
      },
      {
        bits: "6:1",
        name: "SYSREFREQ_DELAY_STEP",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay line step for the external SYSREFREQ signal. Each delay line step delays the SYSREFREQ signal by an amount equal to SYSREFREQ_DELAY_STEP x SYSREFREQ_DELAY_STEPSIZE. In SYNC mode, the value for this field can be determined based on the rb_CLKPOS value to satisfy the internal setup and hold time of the SYNC signal with respect to the CLKIN signal. In SYSREF Repeater Mode, the value for this field can be used as a coarse global delay. Values greater than 0x3F are invalid. Since larger values include more delay steps, larger values have greater total step size variation across PVT relative to smaller values. Refer to the data sheet or the device TICS Pro profile for detailed description of the delay step computation procedure. See also R11 Register, R12 Register, R13 Register, and R14 Register."
      },
      {
        bits: "0",
        name: "SYSREFREQ_CLR",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Clears SYSREFREQ_LATCH, which resets the SYSREFREQ input latch, the internal divider synchronization retimers, and the clock position capture flip-flops comprising rb_CLKPOS. When set, holds the internal SYSREFREQ signal low in all modes except SYSREF repeater mode, overriding the state of SYSREFREQ_SPI. This bit must be set and cleared once before the SYNC or clock position capture operations are performed. See also R14 Register."
      }
    ],
    "0x10": [
      {
        bits: "15:12",
        name: "SYSREF_PULSE_COUN",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Programs the number of pulses generated in pulser mode. The T pulser is a counter gating the SYSREF divider; consequently, the pulse duration and frequency are equal to the duty cycle and frequency of the SYSREF divider output, respectively. ...",
        values: [
          "0x0: Reserved",
          "0x1: 1 pulse",
          "0x2: 2 pulses",
          "0xF: 15 pulses"
        ]
      },
      {
        bits: "11:0",
        name: "SYSREF_DIV",
        meaning: "R/W alan; reset 0x3. TI açıklaması: Sets the SYSREF divider. Maximum input frequency from SYSREF_DIV_PRE must be ≤ 3200 MHz. Maximum output frequency must be ≤ 100 MHz. Odd divides (with duty cycle != 50%) are only allowed when the delay generators are bypassed. See also R72 Register. ...",
        values: [
          "0x0: Reserved",
          "0x1: Reserved",
          "0x2: ÷2",
          "0x3: ÷3",
          "0xFFF: ÷4095"
        ]
      }
    ],
    "0x11": [
      {
        bits: "15:11",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "10:4",
        name: "SYSREFOUT0_DELAY_I",
        meaning: "R/W alan; reset 0x7F. TI açıklaması: Sets the delay step for the SYSREFOUT0 delay generator. Must satisfy SYSREFOUT0_DELAY_I + SYSREFOUT0_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R18 Register and R22 Register."
      },
      {
        bits: "3:2",
        name: "SYSREFOUT0_DELAY_P",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the quadrature phase of the interpolator clock used for the HASE SYSREFOUT0 delay generator retimer. Consult the data sheet for configuration instructions. See also R18 Register and R22 Register.",
        values: [
          "0x0: ICLK",
          "0x1: QCLK",
          "0x2: QCLK",
          "0x3: ICLK"
        ]
      },
      {
        bits: "1:0",
        name: "SYSREF_MODE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Controls how the SYSREF signal is generated or repeated. See also SYSREF_DELAY_BYPASS in R79 Register for additional configuration options.",
        values: [
          "0x0: Continuous (Generator Mode)",
          "0x1: Pulser (Generator Mode)",
          "0x2: Repeater (Repeater Mode)",
          "0x3: Reserved"
        ]
      }
    ],
    "0x12": [
      {
        bits: "15:9",
        name: "SYSREFOUT1_DELAY_I",
        meaning: "R/W alan; reset 0x7F. TI açıklaması: Sets the delay step for the SYSREFOUT1 delay generator. Must satisfy SYSREFOUT1_DELAY_I + SYSREFOUT1_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R19 Register and R22 Register."
      },
      {
        bits: "8:7",
        name: "SYSREFOUT1_DELAY_P",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the quadrature phase of the interpolator clock used for the HASE SYSREFOUT1 delay generator retimer. Consult the data sheet for configuration instructions. See also R19 Register and R22 Register.",
        values: [
          "0x0: ICLK",
          "0x1: QCLK",
          "0x2: QCLK",
          "0x3: ICLK"
        ]
      },
      {
        bits: "6:0",
        name: "SYSREFOUT0_DELAY_Q",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay step for the SYSREFOUT0 delay generator. Must satisfy SYSREFOUT0_DELAY_I + SYSREFOUT0_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R17 Register and R22 Register."
      }
    ],
    "0x13": [
      {
        bits: "15:9",
        name: "SYSREFOUT2_DELAY_I",
        meaning: "R/W alan; reset 0x7F. TI açıklaması: Sets the delay step for the SYSREFOUT2 delay generator. Must satisfy SYSREFOUT2_DELAY_I + SYSREFOUT2_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R20 Register and R23 Register."
      },
      {
        bits: "8:7",
        name: "SYSREFOUT2_DELAY_P",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the quadrature phase of the interpolator clock used for the HASE SYSREFOUT2 delay generator retimer. Consult the data sheet for configuration instructions. See also R20 Register and R23 Register.",
        values: [
          "0x0: ICLK",
          "0x1: QCLK",
          "0x2: QCLK",
          "0x3: ICLK"
        ]
      },
      {
        bits: "6:0",
        name: "SYSREFOUT1_DELAY_Q",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay step for the SYSREFOUT1 delay generator. Must satisfy SYSREFOUT1_DELAY_I + SYSREFOUT1_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R18 Register and R22 Register."
      }
    ],
    "0x14": [
      {
        bits: "15:9",
        name: "SYSREFOUT3_DELAY_I",
        meaning: "R/W alan; reset 0x7F. TI açıklaması: Sets the delay step for the SYSREFOUT3 delay generator. Must satisfy SYSREFOUT3_DELAY_I + SYSREFOUT3_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R21 Register and R23 Register."
      },
      {
        bits: "8:7",
        name: "SYSREFOUT3_DELAY_P",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the quadrature phase of the interpolator clock used for the HASE SYSREFOUT3 delay generator retimer. Consult the data sheet for configuration instructions. See also R21 Register and R23 Register.",
        values: [
          "0x0: ICLK",
          "0x1: QCLK",
          "0x2: QCLK",
          "0x3: ICLK"
        ]
      },
      {
        bits: "6:0",
        name: "SYSREFOUT2_DELAY_Q",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay step for the SYSREFOUT2 delay generator. Must satisfy SYSREFOUT2_DELAY_I + SYSREFOUT2_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R19 Register and R23 Register."
      }
    ],
    "0x15": [
      {
        bits: "15:9",
        name: "LOGISYSREFOUT_DELA",
        meaning: "R/W alan; reset 0x7F. TI açıklaması: Sets the delay step for the LOGISYSREFOUT delay Y_I generator. Must satisfy LOGISYSREFOUT_DELAY_I + LOGISYSREFOUT_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R22 Register and R23 Register."
      },
      {
        bits: "8:7",
        name: "LOGISYSREFOUT_DELA",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the quadrature phase of the interpolator clock used for the Y_PHASE LOGISYSREFOUT delay generator retimer. Consult the data sheet for configuration instructions. See also R22 Register and R23 Register.",
        values: [
          "0x0: ICLK",
          "0x1: QCLK",
          "0x2: QCLK",
          "0x3: ICLK"
        ]
      },
      {
        bits: "6:0",
        name: "SYSREFOUT3_DELAY_Q",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay step for the SYSREFOUT3 delay generator. Must satisfy SYSREFOUT3_DELAY_I + SYSREFOUT3_DELAY_Q = 0x7F. Consult the data sheet for configuration instructions. See also R20 Register and R23 Register."
      }
    ],
    "0x16": [
      {
        bits: "15:14",
        name: "SYSREFOUT1_DELAY_S",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the frequency range of the SYSREFOUT1 delay generator. Set CALE according to fINTERPOLATOR frequency. Consult the data sheet for configuration instructions. See also R18 Register and R19 Register.",
        values: [
          "0x0: 400 MHz to 800 MHz",
          "0x1: 200 MHz to 400 MHz",
          "0x2: 150 MHz to 200 MHz",
          "0x3: Reserved"
        ]
      },
      {
        bits: "13:12",
        name: "SYSREFOUT0_DELAY_S",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the frequency range of the SYSREFOUT0 delay generator. Set CALE according to fINTERPOLATOR frequency. Consult the data sheet for configuration instructions. See also R17 Register and R18 Register.",
        values: [
          "0x0: 400 MHz to 800 MHz",
          "0x1: 200 MHz to 400 MHz",
          "0x2: 150 MHz to 200 MHz",
          "0x3: Reserved"
        ]
      },
      {
        bits: "11:9",
        name: "SYSREF_DELAY_DIV",
        meaning: "R/W alan; reset 0x4. TI açıklaması: Sets the delay generator clock division, determining fINTERPOLATOR and the delay generator resolution. Values other than those listed below are reserved. See also R23 Register.",
        values: [
          "0x0: ÷2 (≤ 1.6 GHz)",
          "0x1: ÷4 (1.6 GHz to 3.2 GHz)",
          "0x2: ÷8 (3.2 GHz to 6.4 GHz)",
          "0x4: ÷16 (6.4 GHz to 12.8 GHz)"
        ]
      },
      {
        bits: "8:7",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set these bits to 0x0."
      },
      {
        bits: "6:0",
        name: "LOGISYSREFOUT_DELA",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the delay step for the LOGISYSREFOUT delay Y_Q generator. Must satisfy LOGISYSREFOUT_DELAY_I + LOGISYSREFOUT_DELAY_Q = 0x7F. See also R21 Register and R23 Register."
      }
    ],
    "0x17": [
      {
        bits: "15",
        name: "EN_TEMPSENSE",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables the on-die temperature sensor. Temperature sensor counter (EN_TS_COUNT) must also be enabled for readback. See also R24 Register."
      },
      {
        bits: "14",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Reserved. If this register is written, set this bit to 0x1."
      },
      {
        bits: "13",
        name: "MUXOUT_EN",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables or tri-states the MUXOUT pin driver. See also R86 Register.",
        values: [
          "0x0: Tri-State",
          "0x1: Push-Pull"
        ]
      },
      {
        bits: "12:7",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x00. TI açıklaması: Reserved. If this register is written, set these bits to 0x00."
      },
      {
        bits: "6",
        name: "MUXOUT_SEL",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Selects MUXOUT pin function.",
        values: [
          "0x0: Lock Detect (Multiplier Only)",
          "0x1: SDO (SPI readback)"
        ]
      },
      {
        bits: "5:4",
        name: "LOGISYSREFOUT_DELA",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the frequency range of the LOGISYSREFOUT delay generator. Y_SCALE Set according to fINTERPOLATOR frequency. Consult the data sheet for configuration instructions. See also R21 Register and R22 Register.",
        values: [
          "0x0: 400 MHz to 800 MHz",
          "0x1: 200 MHz to 400 MHz",
          "0x2: 150 MHz to 200 MHz",
          "0x3: Reserved"
        ]
      },
      {
        bits: "3:2",
        name: "SYSREFOUT3_DELAY_S",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the frequency range of the SYSREFOUT3 delay generator. Set CALE according to fINTERPOLATOR frequency. Consult the data sheet for configuration instructions. See also R20 Register, R21 Register, and R22 Register.",
        values: [
          "0x0: 400 MHz to 800 MHz",
          "0x1: 200 MHz to 400 MHz",
          "0x2: 150 MHz to 200 MHz",
          "0x3: Reserved"
        ]
      },
      {
        bits: "1:0",
        name: "SYSREFOUT2_DELAY_S",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Sets the frequency range of the SYSREFOUT2 delay generator. Set CALE according to fINTERPOLATOR frequency. Consult the data sheet for configuration instructions. See also R19 Register, R20 Register, and R22 Register.",
        values: [
          "0x0: 400 MHz to 800 MHz",
          "0x1: 200 MHz to 400 MHz",
          "0x2: 150 MHz to 200 MHz",
          "0x3: Reserved"
        ]
      }
    ],
    "0x18": [
      {
        bits: "15:14",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "13:12",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Reserved. If this register is written, set these bits to 0x0."
      },
      {
        bits: "11:1",
        name: "rb_TEMPSENSE",
        meaning: "R alan; reset 0x7FF. TI açıklaması: Output of on-die temperature sensor. Readback code can be converted to junction temperature (in °C) according to the following equation: TJ = 0.65 * rb_TEMPSENSE - 351"
      },
      {
        bits: "0",
        name: "EN_TS_COUNT",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Enables temperature sensor counter. Temperature sensor (EN_TEMPSENSE) must be enabled for accurate data. See also R23 Register."
      }
    ],
    "0x19": [
      {
        bits: "15:7",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x004. TI açıklaması: Reserved. If this register is written, set these bits to 0x004."
      },
      {
        bits: "6",
        name: "CLK_DIV_RST",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Resets the main clock divider. If the clock divider value is changed during operation, set this bit high then low after setting the new divider value. Synchronizing the device with the SYSREFREQ pins in SYSREFREQ_MODE = 0x0 and SYNC_EN = 0x1 also resets the main clock divider. This bit has no effect when outside of Divider Mode."
      },
      {
        bits: "5:3",
        name: "CLK_DIV",
        meaning: "R/W alan; reset 0x2. TI açıklaması: CLK_DIV and CLK_MULT are aliases for the same field. CLK_MULT When CLK_MUX = 0x2 (Divider Mode), sets the clock divider equal to CLK_DIV + 1. Valid range is 0x1 to 0x7. Setting CLK_DIV = 0x0 disables the main clock divider and reverts to buffer mode. When CLK_MUX = 0x3 (Multiplier Mode), sets the multiplier equal to CLK_MULT. Valid range is 0x1 to 0x4. Setting CLK_MULT to an invalid value disables the multiplier and reverts to buffer mode. When CLK_MUX = 0x1 (buffer mode), this field is ignored."
      },
      {
        bits: "2:0",
        name: "CLK_MUX",
        meaning: "R/W alan; reset 0x1. TI açıklaması: Selects the function of the device. Multiplier Mode requires writing several other registers (R33, R34, and R67) to values differing from POR defaults, as well as configuring the state machine clock (R2 and R3), before multiplier calibration. Writing any value to R0 (as long as POWERDOWN = 0x0 and RESET = 0x0) triggers a multiplier calibration. Values other than those listed below are reserved.",
        values: [
          "0x1: Buffer Mode",
          "0x2: Divider Mode",
          "0x3: Multiplier Mode"
        ]
      }
    ],
    "0x1C": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "12",
        name: "FORCE_VCO",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Forces the multiplier PLL's VCO to the value selected by VCO_SEL. Not required for Multiplier Mode programming, but can optionally be used to reduce calibration time."
      },
      {
        bits: "11:9",
        name: "VCO_SEL",
        meaning: "R/W alan; reset 0x5. TI açıklaması: User specified start VCO for multiplier PLL. When FORCE_VCO = 0x0, multiplier calibration starts from the VCO set by this field. When FORCE_VCO = 0x1, this field sets the VCO core used by the multiplier. Not required for Multiplier Mode programming, but can optionally be used to reduce calibration time."
      },
      {
        bits: "8:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x008. TI açıklaması: Reserved. If this register is written, set these bits to 0x008."
      }
    ],
    "0x1D": [
      {
        bits: "15:13",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "12:8",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x5. TI açıklaması: Reserved. If this register is written, set these bits to 0x05."
      },
      {
        bits: "7:0",
        name: "CAPCTRL",
        meaning: "R/W alan; reset 0xFF. TI açıklaması: Sets the starting value for the VCO tuning capacitance during multiplier calibration. Not required for Multiplier Mode programming, but can optionally be used to reduce calibration time."
      }
    ],
    "0x21": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x7777. TI açıklaması: Reserved. If the Multiplier Mode is used, set to 0x5666 before calibration. Otherwise, writing this register can be skipped."
      }
    ],
    "0x22": [
      {
        bits: "15:14",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "13:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0000. TI açıklaması: Reserved. If the Multiplier Mode is used, set to 0x04C5 before calibration. Otherwise, writing this register can be skipped."
      }
    ],
    "0x41": [
      {
        bits: "15:9",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x22. TI açıklaması: Since this register is only used for readback, avoid writing these bits when possible. If this register must be written, set these bits to 0x22. Readback can differ from default and written values."
      },
      {
        bits: "8:4",
        name: "rb_VCO_SEL",
        meaning: "R alan; reset 0x1F. TI açıklaması: Readback multiplier PLL's VCO core selection. Can be optionally used in conjunction with VCO_SEL and FORCE_VCO fields to improve calibration time.",
        values: [
          "0xF: VCO5",
          "0x17: VCO4",
          "0x1B: VCO3",
          "0x1D: VCO2",
          "0x1E: VCO1"
        ]
      },
      {
        bits: "3:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Since this register is only used for readback, avoid writing these bits when possible. If this register must be written, set these bits to 0x0."
      }
    ],
    "0x43": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x50C8. TI açıklaması: Reserved. If the Multiplier Mode is used, set to 0x51CB before calibration. Otherwise, writing this register can be skipped."
      }
    ],
    "0x48": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "14:4",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x000. TI açıklaması: Reserved. Set to 0x000."
      },
      {
        bits: "3",
        name: "PULSER_LATCH",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Latches the pulser input when programmed to 0x1. When this bit is set, external signals on SYSREFREQ pins in pulser mode (SYSREF_MODE = 0x1) can not trigger the pulser more than once, until this bit is cleared. This bit is provided to enable changing SYSREF_MODE in repeater mode without risk of accidentally triggering the pulser."
      },
      {
        bits: "2",
        name: "SYSREFREQ_SPI",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Trigger SYSREFREQ via SPI. Setting this bit emulates the behavior of a logic HIGH at SYSREFREQ pins. External signals on SYSREFREQ pins are ignored while this bit is set."
      },
      {
        bits: "1:0",
        name: "SYSREF_DELAY_BYPASS",
        meaning: "R/W alan; reset 0x0. TI açıklaması: Option to bypass delay generator retiming. Under normal circumstances (SYSREF_DELAY_BYPASS = 0) the delay generator is engaged for continuous or pulser modes (Generator Modes), and bypassed in Repeater Mode. Generally this configuration is desirable: the delay generators rely on a signal generated by the SYSREF_DELAY_DIV from the CLKIN frequency, so the Generator Mode SYSREF signal is always well-aligned to the delay generator; in repeater mode, external signal sources can typically utilize a different delay mechanism. In certain cases, bypassing the delay generator retiming in Generator Mode by setting SYSREF_DELAY_BYPASS = 0x1 can substantially reduce the device current consumption if the SYSREF delay can be compensated at the JESD receiver. In other cases, retiming the SYSREFREQ signal to the delay generators by setting SYSREF_DELAY_BYPASS = 0x2 can improve the accuracy of the SYSREF output phase with respect to the CLKIN phase, or can vary the delay of individual outputs independently, as long as coherent phase relationship exists between the interpolator divider phase and the SYSREFREQ phase.",
        values: [
          "0x0: Engage in Generator Mode, Bypass in Repeater Mode",
          "0x1: Bypass in All Modes",
          "0x2: Engage in All Modes",
          "0x3: Reserved"
        ]
      }
    ],
    "0x4B": [
      {
        bits: "15:10",
        name: "RESERVED",
        meaning: "R alan; reset 0x57. TI açıklaması: Read-only. Writes to these bits are ignored. Readback can differ from default values."
      },
      {
        bits: "9:8",
        name: "rb_LD",
        meaning: "R alan; reset 0x3. TI açıklaması: Multiplier PLL Lock Detect. Read-only. Field value has no meaning if device is not in Multiplier Mode.",
        values: [
          "0x0: Unlocked (VTUNE low)",
          "0x1: Reserved",
          "0x2: Locked",
          "0x3: Unlocked (VTUNE high)"
        ]
      },
      {
        bits: "7:4",
        name: "RESERVED",
        meaning: "R alan; reset 0x1. TI açıklaması: Read-only. Writes to these bits are ignored. Readback can differ from default values."
      },
      {
        bits: "3:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x6. TI açıklaması: Reserved. Since this register is only used for readback, avoid writing these bits when possible. If this register must be written, set to 0x6."
      }
    ],
    "0x4F": [
      {
        bits: "15",
        name: "RESERVED",
        meaning: "R alan; reset 0x0. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "14:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0104. TI açıklaması: Reserved. Set to 0x0104 immediately after setting LOGICLK_DIV_BYPASS = 0x1; R90 must also be written immediately afterward. If LOGICLK_DIV_BYPASS is not used or set to 0x0, this register does not need to be written and can be skipped. See also R90 Register."
      }
    ],
    "0x56": [
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x0000. TI açıklaması: Reserved. This register must be set to 0x0004 to allow MUXOUT_EN to tri-state the MUXOUT pin after SPI readback. If SPI readback is not required, or if tri-state is not required on the MUXOUT pin, writing this register can be skipped, forcing MUXOUT_EN to 0x1 (push-pull mode)."
      }
    ],
    "0x5A": [
      {
        bits: "15:8",
        name: "RESERVED",
        meaning: "R alan; reset 0x00. TI açıklaması: Reserved (not used)."
      },
      {
        bits: "15:0",
        name: "RESERVED",
        meaning: "R/W alan; reset 0x00. TI açıklaması: Reserved. Set to 0x60 immediately after setting LOGICLK_DIV_BYPASS = 0x1 and setting R79 = 0x0104. If LOGICLK_DIV_BYPASS is not used or left at the default value, this register does not need to be written and can be skipped. However, if transitioning from LOGICLK_DIV_BYPASS = 0x1 to 0x0, this register must be re-written to 0x00. See also R79 Register."
      }
    ]
  }
};

const GENERIC_MEANING_MARKERS = [
  "Enable kontrol alanıdır",
  "Polarity kontrol alanıdır",
  "Mux/source seçim alanıdır",
  "Pin veya buffer type seçim alanıdır",
  "Power-down kontrol alanıdır",
  "CLKin input seçimi",
  "SYSREF/SYNC üretim",
  "Holdover DAC kontrol/readback",
  "Mode seçim alanıdır",
];

function isGenericMeaning(meaning: string) {
  return GENERIC_MEANING_MARKERS.some((marker) => meaning.includes(marker));
}

function readableFieldName(name: string) {
  return name
    .replace(/\[[^\]]+\]/g, "")
    .replace(/^RB_/, "readback ")
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function inferredValues(name: string): string[] | undefined {
  if (/(_EN|_ENABLE)$/.test(name)) return ["0: disabled", "1: enabled"];
  if (/_PD$/.test(name) || name.endsWith("_POWERDOWN")) return ["0: normal/enabled", "1: power-down"];
  if (/_POL$/.test(name)) return ["0: normal/non-inverted polarity", "1: inverted polarity"];
  if (/_TRI$/.test(name)) return ["0: active", "1: tri-state"];
  if (/^RB_.*_(LOS|DLD|LD|SEL)$/.test(name)) return ["0: status false/not active", "1: status true/active"];
  return undefined;
}

function inferTiClockMeaning(part: TiClockPart, address: string, field: TiClockBitfield) {
  const name = field.name;
  const label = readableFieldName(name);
  const lower = name.toLowerCase();

  if (!isGenericMeaning(field.meaning)) return field.meaning;
  if (name === "NA" || name === "RESERVED") return field.meaning;

  if (name.startsWith("RB_")) {
    if (lower.includes("_los")) return `${label} bit'i ilgili clock input loss-of-signal durumunu SPI readback ile okutur.`;
    if (lower.includes("_sel")) return `${label} bit'i ilgili clock input'un PLL1 yolu için seçili olup olmadığını SPI readback ile okutur.`;
    if (lower.includes("_dac")) return `${label} alanı holdover DAC readback değerinin bir parçasıdır.`;
    if (lower.includes("_holdover")) return `${label} bit'i cihazın holdover status durumunu SPI readback ile okutur.`;
    if (lower.includes("_dld") || lower.includes("_ld")) return `${label} bit'i PLL digital lock detect/readback status bilgisini okutur.`;
    return `${label} alanı ${part} iç status bilgisini SPI readback ile okutur.`;
  }

  if (lower.includes("dld_cnt")) {
    return `${label} alanı digital lock detect assert olmadan önce PLL reference/feedback faz hatasının pencere içinde kalması gereken cycle count değerinin parçasıdır.`;
  }
  if (lower.includes("_dld") || lower.includes("_ld")) {
    return `${label} alanı ilgili PLL digital lock detect sinyalini, lock-lost latch'ini veya bu sinyalin SYNC/status yoluna bağlanmasını kontrol eder.`;
  }
  if (lower.includes("holdover")) {
    return `${label} alanı holdover giriş/çıkış kararı, holdover sayacı veya holdover status davranışını belirler.`;
  }
  if (lower.includes("los")) {
    return `${label} alanı clock input loss-of-signal algılama, timeout veya harici LOS kaynağı davranışını belirler.`;
  }
  if (lower.includes("clkin")) {
    return `${label} alanı CLKin seçimi, CLKin routing/demux, input enable veya input buffer davranışını belirler.`;
  }
  if (lower.includes("sysref") || lower.includes("sync")) {
    return `${label} alanı SYSREF/SYNC üretimi, divider reset/hizalama veya output senkronizasyon maskesi davranışını belirler.`;
  }
  if (lower.includes("_mux")) {
    return `${label} alanı ilgili pin/status/output mux kaynağını seçer.`;
  }
  if (lower.includes("_type")) {
    return `${label} alanı ilgili pinin input/output tipi veya output driver tipini seçer.`;
  }
  if (lower.includes("_pd") || lower.endsWith("powerdown")) {
    return `${label} alanı ilgili clock/PLL/SYSREF bloğunu normal çalışma ile power-down arasında seçer.`;
  }
  if (lower.includes("_en") || lower.endsWith("enable")) {
    return `${label} alanı ilgili ${part} fonksiyonunu etkinleştirir veya devre dışı bırakır.`;
  }
  if (lower.includes("_pol")) {
    return `${label} alanı ilgili sinyalin polarity davranışını seçer.`;
  }
  if (lower.includes("_div") || lower.includes("_r[") || lower.includes("_n[")) {
    return `${label} alanı ilgili divider/counter oranının register image içindeki bitlerini taşır.`;
  }
  if (lower.includes("dac")) {
    return `${label} alanı holdover DAC değeri, tracking eşiği veya DAC clock davranışını belirler.`;
  }

  return `${label} alanı ${part} ${address} register'ında ilgili clock/synthesizer davranışını belirler.`;
}

function enrichTiClockField(part: TiClockPart, address: string, field: TiClockBitfield): TiClockBitfield {
  const meaning = inferTiClockMeaning(part, address, field);
  return {
    ...field,
    meaning,
    values: field.values ?? inferredValues(field.name),
  };
}

export function getTiClockBitfields(part: TiClockPart, address: string): TiClockBitfield[] | undefined {
  return TI_CLOCK_BITFIELDS[part]?.[address]?.map((field) => enrichTiClockField(part, address, field));
}
