# S2C-MSG Binary Arayüzü + CİT Altyapısı + YATT v1 — Tasarım

Tarih: 2026-07-09 · Durum: kullanıcı onaylı tasarım (spec)
Kapsam etiketi: C1 (Board Contract/CİT) + mesaj ICD katmanı + YATT ilk hali

## 1. Amaç

Üç birbirine kilitli iş:

1. **S2C-MSG**: karta bağlanan üst birimle (bugün Spec2Code Test Bench, yarın ürün
   sistemi) konuşulan **binary mesaj arayüzü**. Mevcut metin-satırı ajan protokolü
   (`S2C|id=..|op=..` / `key=value|...`) **tamamen kaldırılır** (kullanıcı kararı:
   tam geçiş); seri (UART), TCP ve CoreSight DCC transportlarının üçü de aynı
   çerçeveyi taşır.
2. **CİT**: şematiğe bağlı BÜTÜN entegrelerden ham + işlenmiş değer ve limit
   bazlı OK/NOK bilgisini tek structure'da toplayan üretilmiş altyapı
   (`boardCitRun`) + arayüzde **CİT sayfası**.
3. **YATT v1**: tanımlı tüm mesajlardan otomatik türetilen Yazılım Arayüz
   Tasarım Tanımı dokümanı + arayüzde **Arayüz/YATT sayfası** ve dışa aktarma.

## 2. Mesaj çerçevesi

### 2.1 Başlık (12 byte, packed, little-endian)

Little-endian seçimi: Cortex-A/R ve MicroBlaze (AXI) doğal düzeni; YATT'ta
açıkça belirtilir.

```c
typedef struct
{
    unsigned int uiMesajKomut;  /* mesaja özgü unique ID                */
    unsigned int uiMesajBoyu;   /* gövde boyu (byte); 4'ün katı         */
    unsigned int uiMesajSayac;  /* yön başına monoton artan, +1         */
} SMesajBaslik;                 /* 12 byte; static_assert ile mühürlü   */
```

- `uiMesajSayac`: her yön (üst birim→kart, kart→üst birim) kendi sayacını tutar;
  1'den başlar, 2^32'de sarar. Alıcı taraf atlama görürse loglar (kayıp tespiti),
  mesajı yine işler.
- Gövde toplam boyu 4-byte hizalı; içeride 1/2 byte'lık anlamlı alanlar olabilir.

### 2.2 Yanıt şeması

- Yanıt ID = istek ID `| 0x80000000` (bit 31 = yanıt biti).
- Her yanıt gövdesi ortak önekle başlar:

```c
typedef struct
{
    unsigned int uiIstekSayac;  /* cevaplanan isteğin uiMesajSayac'ı   */
    unsigned int uiDurum;       /* 0 = OK; bkz. hata kodları           */
} SYanitOnek;                   /* 8 byte */
```

`uiIstekSayac` bugünkü id-eşleştirme davranışının binary karşılığıdır: timeout
sonrası GEÇ gelen yanıt, yeni komutun cevabı sanılmaz.

### 2.3 Hata kodları (`uiDurum`)

| Kod | Ad | Anlam |
|----:|----|-------|
| 0 | OK | başarılı |
| 1 | GENEL_HATA | sınıflanmamış hata |
| 2 | GECERSIZ_MESAJ | bilinmeyen ID / boy uyumsuz / hizasız |
| 3 | GECERSIZ_PARAMETRE | gövde alanı aralık dışı |
| 4 | CIHAZ_YOK | uiCihazIndeks manifest dışı |
| 5 | BUS_HATASI | I2C NACK / SPI hata (trace'te detay) |
| 6 | ZAMAN_ASIMI | cihaz/bus zaman aşımı |
| 7 | DESTEKLENMIYOR | bu kartta/op'ta yok |

### 2.4 Akış (çok parçalı) yanıtlar

Flash okuma, hat taraması gibi büyük/parçalı sonuçlar: tek istek → aynı yanıt
ID'siyle N parça. Parça gövdesi: `SYanitOnek` + `uiParcaNo` (1..N) +
`uiToplamParca` + `uiVeriBoyu` + veri (4B'a pad). Varsayılan parça veri boyu
**256 byte** (mevcut saha-doğrulanmış blok boyu; DCC'de de güvenli).

### 2.5 Kendiliğinden (unsolicited) mesajlar

Trace/log ve canlı bus-trace olayları karttan kendiliğinden gelir; kendi
ID'leri vardır (sistem grubunda), yanıt biti taşımaz, `uiIstekSayac` önekleri
yoktur. UI Akış/Seri Hat ekranları bunları çözerek bugünkü görünümleri korur.

### 2.6 Senkron/dayanıklılık (resync)

Başlıkta magic/CRC YOK (kullanıcının format tanımına sadakat). Dayanıklılık:

- Tüm komut ID'lerinin üst 2 byte'ı sabit **0x5343** ("SC"); yanıtlarda bit 31
  ile 0xD343 olur. Ayrıştırıcı senkron kaybında bayt akışında 0x43 0x53 / 0x43
  0xD3 dizisini (LE yazımda) arar.
- `uiMesajBoyu` üst sınırı 4096; aşan değer = senkron kaybı → resync.
- CRC ve zenginleştirilmiş bütünlük YATT detaylandırma fazına ertelendi
  (kullanıcıyla mutabık).

### 2.7 Cihaz adresleme

Mesaj ID'si **op türünü** tanımlar; hedef cihaz gövdedeki `uiCihazIndeks` ile
seçilir (üretim manifestindeki `devices[]` sırası). YATT'a indeks→(part, id)
cihaz tablosu otomatik girer. Böylece ID kataloğu şematikten bağımsız ve
kararlı kalır.

## 3. Mesaj ID planı ve katalog

### 3.1 Gruplar

| Aralık | Grup |
|--------|------|
| 0x53430100–01FF | Sistem: PING, VERSION, TRACE_LEVEL_SET; 0x53430180+ unsolicited TRACE_EVENT, BUS_TRACE_EVENT |
| 0x53430200–02FF | Generic: REGISTER_READ, REGISTER_WRITE, REGISTERS_READ (geniş), MEM_READ, MEM_WRITE, I2C_SCAN |
| 0x53430300–03FF | CİT: CIT_RUN, CIT_READ |
| 0x53430400–04FF | Cihaz op'ları: DEVICE_INIT, VOLTAGE_READ, TEMPERATURE_READ, CURRENT_READ, VCC_READ, STATUS_READ, CONFIG_READ, ELAPSED_READ, ALARM_READ, EVENT_READ, SENSE_READ, ADIN_READ, VOUT_READ, POWER_READ, HUMIDITY_READ, USER_REGISTER_READ, ID_READ, DATA_READ, BYTE_WRITE, PAGE_WRITE, PAGE_PROGRAM, SECTOR_ERASE, PLL1_LOCK_DETECT, PLL1_LOCK_LOSS, PLL2_LOCK_DETECT, PLL2_LOCK_LOSS, MULTIPLIER_LOCK_DETECT, ... (bugünkü UI'daki her manuel işlem) |

### 3.2 Tek doğruluk kaynağı

`backend/data/message_catalog.json`: her mesaj için ID, ad, yön, gövde alanları
(ad/tip/offset/boy/birim/açıklama). Codegen (ajan C), backend (pack/unpack),
UI (görselleştirme) ve YATT üretimi HEPSİ bu dosyadan beslenir.

**Kalıcılık kuralı:** atanmış ID asla değişmez; yeni op grubunun sonuna eklenir.
Testle korunur (ID tablosu snapshot testi).

### 3.3 VERSION mesajı

Yanıt gövdesi: protokol sürümü (4B) + uygulama sürümü (char[16]) + **kontrat
hash'i** (4B; message_catalog + CİT tanımının CRC32'si). Üst birim uyumsuz
hash'te uyarır ("kartta farklı kontrat sürümü") — sessiz veri bozulması
imkânsızlaşır.

## 4. CİT altyapısı

### 4.1 Limit modeli (Board Contract v1)

- Birimli her ölçüm op'u (mV, °C, mA, mW, µV...) CİT adayıdır ve **varsayılan
  dahildir**.
- Satır başına kullanıcı girdisi: **isim** (`VCC_3V3_RF`; C tanımlayıcısına
  türetilir), **min**, **max**, **önem** (critical/warning). Hepsi opsiyonel;
  isim girilmezse `<part>_<op>_<indeks>` türetilir.
- OK biti = okuma başarılı **VE** (limit girilmişse değer [min,max] içinde).
  Limitsiz satırda OK = okuma başarısı.
- Persist: şematik modelinde cihaz başına `config.cit` alanı (measurements[]:
  {op, name, min, max, severity, enabled}).

### 4.2 Üretilen C (kod standardına birebir)

```c
typedef struct
{
    unsigned int uiVcc3v3RfOk : 1;   /* kullanıcı isimleri */
    unsigned int uiLoLockOk   : 1;
    /* ... ölçüm başına 1 bit ... */
} SBoardCitBayraklar;

typedef struct
{
    int          iDeger;     /* işlenmiş değer (op'un birimi; YATT'ta) */
    unsigned int uiHam;      /* ham register/kod değeri                */
    unsigned int uiDurum;    /* 0 OK; hata kodu (bkz. 2.3)             */
} SBoardCitOlcum;

typedef struct
{
    unsigned int       uiSayac;      /* her koşuda +1        */
    unsigned int       uiZaman;     /* ms tick               */
    SBoardCitBayraklar sBayraklar;
    SBoardCitOlcum     arrOlcum[BOARD_CIT_OLCUM_SAYISI];
} SBoardCit;   /* packed + _Static_assert(offsetof...) mühürleri */
```

- `boardCitRun(SBoardCit* spCit)`: tüm entegreleri **tek atımda**, mux
  disipliniyle gezer; her ölçümü doldurur, bayrakları set eder. Bus hatasında
  ölçüm `uiDurum` alır, OK=0, koşu devam eder (kısmi CİT her zaman döner).
- Limitler v1'de **derlemeye gömülü** (üretilen sabit tablo). NVM'e taşıma
  sonraki faz.

### 4.3 CİT mesajları

- `CIT_RUN` (0x53430301): gövdesiz istek → yanıt: SYanitOnek + SBoardCit.
- `CIT_READ` (0x53430302): son koşulmuş SBoardCit'i (yeniden koşmadan) döner.

### 4.4 CİT sayfası (UI)

- Üst şerit: kritik NOK sayısı, uyarı NOK sayısı, son koşu zamanı, CİT sayacı.
- Tablo: ölçüm adı · cihaz (part+id) · ham · işlenmiş+birim · min/max · önem ·
  OK/NOK rozeti (kritik NOK kırmızı, uyarı NOK amber).
- Eylemler: "CİT koştur" (CIT_RUN), periyodik otomatik yenile aç/kapa
  (masada CBIT önizlemesi), limit/isim/önem düzenleme aynı tabloda (persist).
- Limitler değişince yeniden üretim gerektiği açıkça rozetlenir
  ("kontrat değişti — kodu yeniden üret").

## 5. YATT v1 + Arayüz sayfası

- Kaynak: message_catalog + CİT structure tanımı + cihaz tablosu. Offset
  tabloları üretilen packed struct'larla aynı kaynaktan türetilir; kod-doküman
  kayması yapısal olarak imkânsız.
- **Arayüz/YATT sayfası**: mesaj tablosu (ID, ad, yön, gövde boyu); satır
  genişlet → alan tablosu (offset/tip/boy/birim/açıklama); başlık formatı ve
  hata kodları bölümleri.
- **Dışa aktar**: self-contained HTML (register map export kalıbı) + Markdown.
  Word şablonu ve içerik detaylandırması sonraki faz (kullanıcı: "ileride
  detaylandıracağız").

## 6. Tam geçiş etkisi

- **Ajan C (codegen)**: `spec2codeTestbenchDispatchLine` yerine binary
  `spec2codeTestbenchDispatchMessage`; UART/TCP/DCC alım yolları bayt-akışı
  çerçeve ayrıştırıcısına bağlanır (DCC 32-bit word taşır — 4B hizalı formata
  doğal uyum). Trace çıktıları TRACE_EVENT mesajı olur.
- **Backend**: `format_command`/`parse_response` → Python `struct` tabanlı
  pack/unpack (message_catalog'dan üretilen kodek); Akış/Seri Hat ekranları
  çerçeveleri hex + çözülmüş gösterir.
- **UI**: mevcut ekranlar aynı API çağrılarıyla kalır; + 2 yeni sayfa (CİT,
  Arayüz/YATT) + nav/palette kaydı.
- **Testler**: pack/unpack round-trip; hizalama static_assert'leri (gerçek
  aarch64 -Werror derleme); ID kararlılık snapshot testi; loop transport E2E
  (istek→ajan-simülasyonu→yanıt); akış parçalama testi (flash 256B blokları);
  resync testi (araya çöp bayt sok → toparlama).
- **Gerçek kart doğrulaması kullanıcıda**; parite kontrol listesi teslim
  edilir: register R/W, birimli okumalar, device_init, flash indir/yükle,
  hat tarama, trace seviyeleri, CİT koşusu — üç transportta.

## 7. Karar kaydı

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Protokol kaderi | TAM GEÇİŞ (metin kalkar) | kullanıcı onayı; en temiz ICD, YATT gerçeği yansıtır |
| Endian | little-endian | hedef işlemcilerin doğal düzeni |
| Yanıt kimliği | istek ID \| 0x80000000 | ID uzayı tek tabloda kalır |
| Cihaz seçimi | gövdede uiCihazIndeks | ID kataloğu şematikten bağımsız/kararlı |
| Limitler | v1'de derlemeye gömülü | kullanıcı onayı; NVM sonraki faz |
| CRC/magic | v1'de yok; resync deseni | kullanıcının 12B başlık tanımına sadakat |
| YATT formatı | self-contained HTML + MD | air-gapped; Word sonraki faz |
