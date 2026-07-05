"""Örnek kullanıcı descriptor'ı — tek doğruluk kaynağı.

Import ekranındaki "örnek şablonu indir" bu içeriği verir; testler aynı
içeriğin doğrulayıcıdan ve TAM üretimden (sürücü + dispatch + manifest)
geçtiğini kanıtlar. Yani kullanıcının indirdiği şablon her zaman bilinen-iyi
bir başlangıç noktasıdır. Kılavuz 15.0'daki yazım rehberiyle birlikte okunur.
"""

EXAMPLE_FILE_NAME = "mymon16_ornek.yaml"

EXAMPLE_USER_DESCRIPTOR = """\
# Ornek kullanici descriptor'i - MYMON16 (kurgusal 8-bit register haritali
# I2C monitor). Kendi entegren icin kopyalayip uyarlayabilirsin; yazim
# kurallari Kilavuz 15.0 "Descriptor yazim rehberi" bolumundedir.
#
# Onemli: register offsetlerini/bitlerini/formulleri DATASHEET'ten birebir al.
descriptor_version: "1.0"
part: "MYMON16"              # Sematikte kullanacagin parca adiyla birebir
manufacturer: "Acme"
summary: "Kurgusal 2 kanalli monitor (ornek sablon)."
transport:
  type: i2c                  # i2c | spi
  address_width: 8
  default_address: 0x4C      # Gercek adres SEMATIKTEN gelir; bu varsayilandir
  byte_order: big            # Cok baytli degerin birlesme sirasi: big | little
access_primitives:
  read_register:  { pattern: write_addr_then_read, width_bytes: 1 }
  write_register: { pattern: write_addr_then_data, width_bytes: 1 }
registers:
  # Adlar C makrosuna donusur (MYMON16_REG_STATUS): BUYUK_HARF_ALT_CIZGI,
  # ad ve offset benzersiz. width: 16 yazarsan o register tek islemde
  # 2 bayt okunur/yazilir (tek genis register); 8-bit ardisik registerlar
  # tek tek okunur.
  - name: STATUS
    offset: 0x00
    width: 8
    access: ro               # ro | rw | wo | reserved
    reset: 0x00              # Registers ekraninda diff'in "beklenen" sutunu
    fields:                  # poll adimi alan ADIYLA calisir - burada tanimli olmali
      - { name: T_READY, bits: "1" }
  - name: CONTROL
    offset: 0x01
    width: 8
    access: rw
    reset: 0x00
  - { name: T_MSB, offset: 0x06, width: 8, access: ro, reset: 0x00 }
  - { name: T_LSB, offset: 0x07, width: 8, access: ro, reset: 0x00 }
operations:
  # Her operasyon bir C fonksiyonu + Test Bench butonu olur.
  # returns yoksa yalniz is yapar; uint8/uint16/uint32/int32 -> skaler
  # (okunan toplam bayt <= 4); "uint16[8]" -> dizi (read_channels ile).
  - name: device_init
    description: "Olcumu etkinlestirir. Basarida STATUS geri okunur."
    steps:
      - { op: write_register, reg: CONTROL, value: 0x10 }
  - name: temperature_read
    returns: "int32"
    description: "Sicaklik, 0.01 C (13-bit two's complement, LSB 0.0625 C)."
    # deger = isaret_genislet((ham >> rshift) & mask, signed_bits)
    #         * scale_num / scale_den (+ offset, clamp_min opsiyonel)
    convert: { mask: 0x1FFF, signed_bits: 13, scale_num: 625, scale_den: 100, unit: "0.01 C" }
    steps:
      - { op: poll, reg: STATUS, field: T_READY, until: 1 }   # butce otomatik ~0.5 s
      - { op: read_register, reg: T_MSB }                     # 1. bayt (big -> MSB)
      - { op: read_register, reg: T_LSB }                     # 2. bayt
test_hints:
  post_init_status: { reg: STATUS }   # init basarisinda data alani bos donmez
  self_test: { description: "Sicaklik okunur; state degistiren yazma yok." }
"""
