# Çok-Kartlı (Multi-Board) Sistem Topolojisi — Tasarım

Tarih: 2026-08-04 · Durum: kullanıcı onaylı tasarım (spec)

## 1. Amaç

Gerçek projelerde sistem tek karttan ibaret değil: FPGA'in (PS/PL) bulunduğu bir
**ana kart** var; oradan I2C/SPI hatları fiziksel konnektörlerle **başka kartlara**
çıkıyor ve bu zincir kart kart devam edebiliyor. Bugün Spec2Code bu yapıyı
göremiyor — `devices` düz bir liste. Bu tasarım kartları birinci sınıf hale
getirir: şematikte kutu, üretimde klasör + kart fonksiyonları, CİT/Test Bench'te
grup, YATT'ta topoloji bölümü.

Kullanıcı kararları (bu tasarımın dayanağı):
- Kod üretimi: **dizin + kart başına toplu fonksiyonlar** (sembol öneki yok).
- Konnektörler **birinci sınıf ve isimli**.
- CİT/Test Bench **kart bazında gruplanır**.
- Kartlar arası hatta ara eleman olarak yalnız **I2C mux/switch** (ve o kartın
  kendi entegreleri) bulunur; repeater/seviye çevirici modellenmeyecek.
- **Tek denetleyici** ilkesi: FPGA ana kartta, tüm denetleyiciler oradadır.

## 2. Mimari karar: kart = fiziksel konum katmanı (Yaklaşım A)

Kart, elektriksel modele **dik (orthogonal) bir boyut**tur:

- Cihazın elektriksel bağlantısı bugünkü gibi kalır: `attach.controller_id`
  (+ `via_mux`). Bu alanlar DEĞİŞMEZ.
- Cihazın fiziksel yeri yeni `board_id` alanıyla belirtilir.
- Konnektör, bir hattın kartlar arası geçişini **belgeler** (elektriksel yol
  değiştirmez).

Reddedilen alternatif (B): her kartın kendi bus segmentini tanımlaması ve
konnektörlerin segmentleri birleştirmesi. Fiziksel olarak daha "doğru" ama
denetleyici zaten tek olduğundan fazladan dolaylılık ve büyük göç maliyeti
getirir; sahada doğrulanmış mevcut akışı riske atar.

## 3. Veri modeli (`project.spec`)

Yeni üst seviye diziler (ikisi de opsiyonel):

```json
"boards": [
  { "id": "main", "name": "Ana Kart", "role": "main",       "notes": "FPGA + PS" },
  { "id": "rf",   "name": "RF Kart",  "role": "peripheral", "notes": "" }
],
"connectors": [
  { "id": "j7_j1", "name": "J7 → J1", "from_board": "main", "to_board": "rf",
    "bus": { "controller_id": "ps_i2c_0",
             "via_mux": { "mux_id": "u10_tca9548a", "channel": 3 } },
    "notes": "10-pin FFC" }
]
```

- `boards[].id`: `^[a-z][a-z0-9_]*$`, benzersiz. `role`: `main` | `peripheral`.
  **Tam olarak bir** `main` kart olmalıdır.
- `boards[].name`: kullanıcının verdiği serbest metin (Türkçe karakter serbest).
- `devices[].board_id` ve `muxes[].board_id`: opsiyonel; verilmezse ana kart.
- Denetleyiciler: `board_id` ALMAZ — tanımı gereği ana karttadır (FPGA orada).
- `connectors[].bus.via_mux`: opsiyonel; hattın hangi mux kanalından geçtiğini
  belgeler.

**Geriye uyum:** `boards` yoksa tek örtük ana kart varsayılır
(`id: "main"`, `name`: proje adı), tüm cihazlar ona aittir.

## 4. Kod üretimi

### 4.1 Değişmezlik kuralı (en kritik)

`boards` **tanımlı değilse** üretilen çıktı bugünküyle **bayt-bayt aynıdır**.
Sahada doğrulanmış tek-kartlı akışlar (ZynqMP kullanıcı kartı dahil) hiç
etkilenmez. Kart katmanı yalnızca kullanıcı kart tanımladığında devreye girer.

### 4.2 Kart tanımlıyken düzen

```
drivers/ana_kart/ltc2991.c        (+ .h)
drivers/ana_kart/ana_kart.h/.c    → anaKartInit(), anaKartCitRun(), anaKartSelfTest()
drivers/rf_kart/lmk04832.c        (+ .h)
drivers/rf_kart/rf_kart.h/.c      → rfKartInit(), rfKartCitRun(), rfKartSelfTest()
tests/…                            (ajan/mesaj/CİT katmanı: SİSTEM geneli, tek firmware)
```

- Cihaz sürücü dosyaları kartına göre klasörlenir; **dosya içerikleri ve
  fonksiyon adları değişmez** (sembol öneki yok — kullanıcı kararı).
- Kart başına bir modül üretilir:
  - `<kart>Init(void)` — o kartın tüm cihazlarını sırayla ilklendirir
    (mux kanal seçimi bugünkü disiplinle yapılır). Bir cihaz hata verse de devam
    eder; ilk hatayı döndürür (kısmi ilklendirme değerlidir).
  - `<kart>CitRun(SBoardCit* spCit)` — yalnız o kartın ölçümlerini
    sistem-geneli `SBoardCit` içindeki kendi slotlarına doldurur.
  - `<kart>SelfTest(void)` — o kartın `self_test` hint'i olan cihazlarını koşar.

### 4.3 Kart adı → C tanımlayıcı

"RF Kart" → `rfKart`. Türkçe karakterler katlanır (ı→i, İ→I, ş→s, ğ→g, ü→u,
ö→o, ç→c), alfanümerik olmayanlar ayraç sayılır, camelCase üretilir. İki kart
aynı tanımlayıcıya düşerse **açık `CodegenError`** (sessiz çakışma yok).
Klasör adı: `snake_case` (`rf_kart`).

### 4.4 CİT sözleşmesi

Sistem-geneli `boardCitRun()` / `SBoardCit` ve **bit sırası DEĞİŞMEZ** — YATT'ta
belgeli sözleşme korunur. Kart bilgisi manifest üzerinden taşınır
(`cit.olcumler[i].board_id`), gruplama tüketici tarafında yapılır. Kart bazlı
`<kart>CitRun` aynı struct'ın yalnız kendi slotlarını doldurur.

> Adlandırma notu: mevcut `boardCit*` adlarındaki "board" **sistem** anlamındadır
> (fiziksel kart değil). Sözleşme kırılmasın diye korunur; YATT'ta bu ayrım
> açıkça yazılır.

## 5. Şematik (UI)

- Kart = yeniden boyutlanabilir **kutu** (React Flow parent/group node). Başlıkta
  kullanıcının verdiği ad; ana kartta ayırt edici rozet.
- Entegre/mux kutunun içine sürüklenince `board_id` atanır; dışına alınınca ana
  karta düşer.
- Konnektörler kartlar arası **etiketli çizgi**: "J7 → J1 · I2C0 · mux ch3".
- "Kart ekle" / yeniden adlandır / sil. Dolu kart silinmek istenirse: içindeki
  cihazlar ana karta taşınır (onay sorulur).
- Mevcut bus/kanal çizim mantığı korunur; kartlar üstüne bir katman olarak gelir.

## 6. CİT / Test Bench

- CİT sayfası: kart başlıkları altında gruplanmış ölçümler + kart başına özet
  rozeti ("RF Kart: 4/4 OK", "PSU Kart: 1 kritik NOK"). Üst şeritteki sistem
  toplamları korunur.
- Test Bench: entegre listesi kart başlıkları altında gruplanır. "Bütün cihazları
  ilklendir" kartlı üretimde kart kart ilerler ve özet kart bazında gösterilir.

## 7. YATT / manifest

- Manifest yeni bölümler taşır: `boards[]`, `connectors[]`; `devices[]` ve
  `cit.olcumler[]` girdilerine `board_id` eklenir.
- YATT'a **Sistem Topolojisi** bölümü: kart tablosu (ad/rol/not) + konnektör
  tablosu (ad, kartlar, hat, mux kanalı, not). Doküman böylece "bu sistem şu
  kartlardan oluşur ve şöyle bağlanır" der.

## 8. Doğrulama (wiring validator)

- `board_id` var olan bir kartı göstermeli; tam olarak bir `main` kart olmalı.
- Konnektörün `from_board`/`to_board`'ı var olmalı, aynı kart olmamalı,
  `bus.controller_id` var olmalı, `via_mux` verildiyse mux ve kanal geçerli olmalı.
- **Uyarı (hata değil)**: ana kart dışındaki bir kartta cihaz var ama o hattı
  belgeleyen konnektör yok → "bu kartın bağlantısı belgelenmemiş".
- Kart tanımlayıcı çakışması → hata (bkz. §4.3).

## 9. Kapsam dışı (bu spec'te YOK)

- Repeater/buffer/seviye çevirici/izolatör modellemesi (kullanıcı: gerekmiyor).
- Kart başına ayrı firmware/derleme birimi (tek FPGA, tek firmware).
- Kartlar arası elektriksel segment modeli (Yaklaşım B).
- Kart başına ayrı XSA/donanım tanımı.

## 10. Karar kaydı

| Karar | Seçim | Gerekçe |
|---|---|---|
| Kart semantiği | Fiziksel konum katmanı (A) | Mevcut elektriksel modeli ve saha akışını bozmaz |
| Kod granülerliği | Dizin + kart fonksiyonları | Kullanıcı kararı; sembol öneki gereksiz uzatma |
| Tek kart çıktısı | Bayt-bayt değişmez | Saha-doğrulanmış akışın korunması |
| CİT bit sırası | Değişmez, gruplama manifestten | YATT sözleşmesi kırılmasın |
| Konnektör | Birinci sınıf, isimli | Kullanıcı kararı; saha kablo takibi + doküman |
| Denetleyici konumu | Her zaman ana kart | Tek FPGA ilkesi |
