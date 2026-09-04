# CİT Entegre Katmanı (HAL + Entegre CİT) Tasarımı

Tarih: 2026-09-05. Durum: UYGULANDI v0.1.155 (otonom oturum; kullanıcı isteği doğrultusunda
tasarım kararları burada belgelenir).

## Amaç

Kullanıcının kendi gömülü yazılımına **dosya olarak taşıyabileceği**, hiyerarşik ve
portlanabilir bir CİT (cihaz içi test) katmanı üretmek:

1. **Alt katman (HAL):** I2C ve SPI sarmalayıcıları. Xilinx PS (XIicPs/XSpiPs), AXI
   soft-IP (XIic/XSpi) ve **kullanıcı portu** (Xilinx dışı MCU: iki extern fonksiyon)
   arka uçları tek API arkasında.
2. **Üst katman (entegre CİT):** her entegre için `S<Mod>CitConfig` (adres, mux, timeout —
   çalışma zamanında değiştirilebilir), `S<Mod>Cit` (durum register **bitleri bit bit**,
   ölçümler **bayt/kelime** olarak), `<mod>CitInit()` ve `<mod>CitRead()`.
3. **Sistem toplayıcı:** `SSistemCit` (her cihaz için bir alt struct) + `sistemCitInit()` /
   `sistemCitRead()`; bus örnekleri spec'ten varsayılanla dolar.

## Değişmezlik

Mevcut `drivers/`, `tests/` çıktıları **bayt-bayt değişmez**. Yeni katman yalnız
`outputs/<proje>/cit/` altına **eklenir**. Mevcut test bench / `SBoardCit` sözleşmesi
dokunulmaz.

## Çıktı ağacı

```
cit/
  hal/spec2code_cit_port.h      platform seçimi (#ifndef korumalı makrolar) + durum kodları
  hal/spec2code_i2c_bus.h/.c    SSpec2codeI2cBus, spec2codeI2cBusInit/Write/Read/RegisterRead/
                                RegisterWrite/RegisterReadWide/RegistersRead/MuxSelect
  hal/spec2code_spi_bus.h/.c    SSpec2codeSpiBus, spec2codeSpiBusInit/Transfer
  <mod>_cit.h/.c                entegre başına (I2C register cihazları, SPI TICS register cihazları)
  spec2code_cit_sistem.h/.c     SSistemCitBus + SSistemCit + sistemCitInit/Read
```

Kapsam dışı (CİT dosyası üretilmez, README'de belirtilir): GPIO hat cihazları, komut tabanlı
SPI flash, I2C EEPROM, mux'lar (mux, cihaz config'inde adres+kanal olarak taşınır).

## Struct kuralları

- Durum registerleri: `fields` tanımlı, genişlik ≤ 16 bit, `access: ro` **veya**
  `test_hints.post_init_status.reg`. Her alan `unsigned int uiAlan : n` bit alanı; ham
  register ayrıca `uc`/`us` olarak saklanır.
- Ölçümler: `returns` olan, risk `safe`, çalışma zamanı parametresi gerektirmeyen op'lar.
  Tip eşlemesi mevcut sürücülerle aynı (`uint8→uc`, `int32→i`, `uint32→ui`, diğer→`us`,
  `x[N]` → dizi). Dönüşüm (`convert`) aynı tam sayı formülüyle uygulanır.
- Her durum registeri ve her ölçüm için `ui...Ok : 1` okuma-başarı biti. Limit
  değerlendirmesi kartta yapılmaz (mevcut ilke).
- `_Static_assert` ile bayrak struct boyutu (GCC bit alanı yerleşimi simüle edilerek) ve 4B
  hizası kilitlenir.

## Doğrulama

- Host gcc round-trip: kullanıcı portu arka ucu ile sahte LTC2991/LMK04832 register modeli;
  bitlerin ve değerlerin beklenen şekilde dolduğu doğrulanır.
- Çapraz derleme: MicroBlaze BSP (xiic_l.h/xspi.h) `mb-gcc -Wall -Wextra -Werror` ve ZynqMP
  BSP (xiicps.h/xspips.h) `aarch64-none-elf-gcc`.
- Uçtan uca: MicroBlaze XSA (AXI UARTLite + IIC + Quad SPI) → generate → Vitis 2023.2 →
  ELF (cit/ dosyaları app'e dahil).
