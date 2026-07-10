# S2C-MSG + CİT + YATT v1 — Gerçek Kart Parite Kontrol Listesi

Bu liste, S2C-MSG binary geçişinin (metin satır protokolü tamamen kaldırıldı),
CİT altyapısının ve YATT v1'in **gerçek donanımda** doğrulanması içindir.
Geliştirme sırasında yalnız host round-trip testleri, loop-transport testleri
ve gerçek `gcc`/`aarch64` derleme testleri koşulabildi — **canlı TCP/UART/DCC
round-trip ve gerçek firmware trace davranışı bu liste ile İLK KEZ
doğrulanacak**.

Her satırı üç bağlantı tipinin **HER BİRİNDE** tekrarla: **UART (Seri)**,
**TCP/Ethernet**, **CoreSight DCC (JTAG)**. Bir satır bir transportta
NOK ise diğer ikisinde de tekrar dene — transport'a özgü mü, katalog/kodek
seviyesinde mi olduğunu ayırt etmek için.

## Bilinen v1 kısıtları (baştan oku)

- **`uiZaman` = 0**: CİT ölçüm zaman damgası (`SBoardCit.uiZaman`, ms-tick) v1'de
  kaynağı yok, her zaman 0 döner. Ölçüm zamanlaması istenirse sonraki faz.
- **CİT'te devre dışı ölçümde ham durum taşınmaz**: bir ölçüm CİT sayfasından
  devre dışı bırakılırsa (`enabled=false`) üretilen `SBoardCitOlcum.uiHam` = 0
  ve `uiIstatus` ham hata kodu taşımaz — yalnız "bu ölçüm çalışmadı" bilgisi var.
- **Bit-alanı yerleşimi GCC/ARM-EABI varsayımı**: `SBoardCitBayraklar` (bit
  başına 1 OK/NOK bayrağı) derleyicinin bit-field paketleme kuralına güvenir;
  bu proje `gcc`/aarch64-none-elf (ARM EABI) ile test edildi. Başka bir
  derleyici/ABI ile bit sırası FARKLI olabilir — YATT'taki bit tablosu ile
  gerçek derlenmiş binary'yi karşılaştır.
- **Gerçek firmware trace varyantları + canlı TCP round-trip ilk kez burada
  doğrulanıyor**: Task 3/5 raporlarında ⚠️ olarak devredilen konu bu listedir.
  UART/lwIP-socket/lwIP-raw/DCC dört transport üretecinin gerçek kartta
  chunk/segment sınırları arası parser durumu koruyup korumadığı (feed-forward)
  yalnız sahada kesin doğrulanır.
- **VERSION yanıtı arayüzde kontrat hash'i GÖSTERMEZ**: "Sürüm sorgula"
  sonucunda yalnız ASCII sürüm metni çözülür. Kontrat hash karşılaştırması
  (`message_catalog_crc32`) YATT sayfasındaki `kontrat CRC32 {hash}` rozeti
  ile manifest üzerinden yapılır — üretilen ajanın kullandığı katalogla
  backend'in katalogunun aynı olduğunu orada doğrula (bkz. madde 12).
- **ESKİ AJANLA UYUMSUZ**: karttaki önceki (metin protokolü) firmware bu
  sürümle KONUŞAMAZ. Karta yüklü eski ELF varsa Generate + Vitis workspace
  ile yeniden derleyip YÜKLEMEDEN hiçbir adım çalışmaz (bağlantı kurulur ama
  ilk komutta timeout/GECERSIZ_MESAJ alırsın — bu beklenen davranıştır, hata
  değildir).

---

## 1. Bağlan + VERSION sorgula

| Adım | Beklenen sonuç | Fark (eski protokole göre) |
|---|---|---|
| Test Bench sayfasında bağlantı tipini seç: **TCP**/**Seri**/**CoreSight** (BoardConnectionCard, sol panel). TCP için Host/Port; Seri için Seri port + Baud; CoreSight için Vitis kurulum yolu + Çekirdek (DCC). | **Bağlan**'a basınca birkaç saniye içinde rozet `bağlı` (yeşil) olur. CoreSight'ta ilk bağlantı xsdb açılışı nedeniyle ~10-30 sn sürebilir. | Bağlantı kurulumu değişmedi; yalnızca üstünden akan çerçeve formatı binary. |
| **CoreSight DCC RX-hazır maskesi doğrulaması** (CoreSight transportunda HATA ise): Telnet log ajan + CoreSight/DCC kombinasyonunda: Agent DCC çerçevesi alamıyorsa ya da timeout'lar sık görülüyorsa, SPEC2CODE_CORESIGHT_DCC_RX_MASK makrosu (üretilen koddaki varsayılan 1U<<30) kart BSP'sindeki XCoresightPs_DccGetStatus DCC registerinin gerçek ready-bit tanımıyla eşleşmediği anlamı taşır. Bağlantı kur, yalnız DCC'ye telnet log server çerçeveleri gönderin (komut göndermeden): PuTTY ile TCP 18.2.75.121:23'e bağlanın → S2C-LOG satırları akarsa, DCC RX maskesi doğru. Hiçbir satır gelmezse ya da timeout olursa, BSP'nin xil_io.h ve xcoresightps.h dosyalarındaki DCC status register belgelerine bakarak doğru bit konumunu bulup `project.spec`'te `coresight_dcc_rx_mask` override değerini ayarlayıp yeniden Generate et (Vitis rebuild + karta yükleme gerekli). | Yeni doğrulama adımı — Telnet/DCC kombinasyonunda v0.1.140 sonrası önemlidir. |
| **Sürüm sorgula** butonuna bas (ShieldCheck ikonlu, sol panelde). | Sonuç panelinde `ok` rozeti yeşil, `= {sürüm metni}` (örn. `v0.1.140`) çözülmüş değer olarak görünür. Request/Response kutuları artık `"VERSION (istek) sayac=N govde=NB"` gibi bir ÇERÇEVE ÖZETİ gösterir (eski `S2C|id=1|op=spec2code_version` satırı DEĞİL). | **Fark**: Request/Response artık ham komut satırı değil, binary çerçeve özeti + hex. Kontrat hash burada GÖSTERİLMEZ (bkz. kısıtlar). |
| Agent log seviyesini bağlantı kartından değiştir (dropdown: `1 — error`.. `5 — debug`). | Seçim anında `log_level` komutu gider; hata yoksa sessizce uygulanır (ayrı bir "başarılı" bildirimi yok — Akış ekranında sonraki trace satırlarının seviyesi değişerek doğrulanır, bkz. madde 8). | Aynı UI akışı; komutun teli artık binary. |

## 2. Register oku/yaz (Registers ekranı)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Registers ekranında bir cihaz seç (register_read/register_write op'u olan), **Snapshot** al. | Register haritası okunur, bit-bit ısı haritası çizilir; son 8 snapshot tarayıcıda saklanır. | Yok — bu ekranın veri kaynağı zaten `register_read` op'u, davranış aynı. |
| Bir `rw`/`wo` register'da kalem simgesiyle yeni hex değer gir, onayla. | Onay diyaloğu: *"{part} {register} ({offset}) registerına {değer} yazılacak. Kart üzerindeki cihaz state'i değişir. Devam edilsin mi?"* Onaylayınca `register_write` gider; `ok=1` ise ve register write-only DEĞİLSE otomatik `register_read` ile geri okunup satırda gösterilir (write-only ise yazılan değer olduğu gibi gösterilir, geri okunamaz). | Yok — akış aynı; yalnız komutlar artık binary çerçeve. |
| SPI parçalarında "Okuma koşulu" notunu kontrol et (LMK04832 gibi SDIO okuma önkoşulu olan cihazlarda). | Sol panelde donanım/konfigürasyon koşulu metni görünür. | Yok. |

## 3. Birimli okumalar (Test Bench op'ları — LTC2991 mV, sıcaklık)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Test Bench'te LTC2991 cihazını seç, `voltage_read` op'unu seç, **Gönder**. | Sonuç panelinde yeşil `= {N} mV` rozeti (8 kanal ham voltage code'dan dönüştürülmüş; LSB 305.18 µV, 0–5000 mV aralığı, negatifler 0'a kırpılır). | Yok — dönüştürme mantığı değişmedi; yalnız komut/yanıt teli binary. |
| `temperature_read` op'unu seç, **Gönder**. | `= {N.NN} °C` (0.01°C çözünürlük, işaretli; örn. 2350 ham → 23.50 °C). | Yok. |
| `current_read` op'unu seç, **Gönder**. | Ham differential kod (işaret + 14 bit, two's complement) döner; panel notu Vsense_µV = kod × 19.075 formülünü hatırlatır — akım application katmanında shunt değeriyle hesaplanmalı, UI otomatik amper göstermez. | Yok. |
| `vcc_read` op'unu seç, **Gönder**. | `= {N} mV` (2500 mV + kod × 305.18 µV). | Yok. |

## 4. device_init

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| İlgili cihazda `device_init` op'unu seç (risk="risky" ise turuncu "state değiştirir" rozeti görünür). **Gönder**. | Risky ise onay diyaloğu: *"{op.label} kart üzerindeki cihaz state'ini değiştirebilir. Devam edilsin mi?"* Onaylayınca komut gider, `ok=1` beklenir; description'da post-init doğrulama okuması varsa (örn. "başarıda X geri okunur") panel notunda görünür. | Yok — akış aynı; tel binary. |
| Bring-up (Mission Control) sihirbazında "device_init adımlarını dahil et" açıkken tüm sırayı koştur. | Manifest bağımlılık sırasıyla (güç izleyiciler → sensörler → saat ağacı → bellekler → RF) her adım LED'i canlı yanar; hata bir adımı durdurmaz, sonunda board birth certificate HTML indirilir. | Yok — Bring-up akışı da aynı `testbenchCommand` API'sini kullanır, binary'ye şeffaf geçti. |

## 5. Flash: JEDEC ID + 256B okuma + binary indirme döngüsü + page_program + sector_erase

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Flash cihazında JEDEC/ID okuma op'unu (örn. `id_read`) tekil operasyon panelinden seç, **Gönder**. | Sonuç panelinde data bytes olarak JEDEC ID baytları görünür (`fixed_read_length` rozetiyle beklenen bayt sayısı). | Yok. |
| **Dosya transferi** moduna geç (yalnız `data_read`/`page_program` op'u olan cihazlarda görünür buton). Başlangıç adresi + Uzunluk (bayt) gir (örn. 256), **Oku ve .bin indir**. | 256 baytlık TEK `data_read` komutu gider, `.bin` dosyası (`{device}_{adres}_{uzunluk}B.bin`) indirilir; özet satırında ilk/son 16 bayt hex gösterilir. | **Fark**: eskiden `data=AABB` gibi hex alan tek satırlık metin komuttaydı; şimdi `data_read` yanıtı binary çerçevenin veri alanından (256B parça boyutu — CİT/flash tasarımındaki "varsayılan parça 256 byte" ile birebir) çözülüyor. |
| Aynı ekranda daha büyük bir uzunluk gir (örn. 4096, birden fazla 256B chunk). **Oku ve .bin indir**. | Arka arkaya N adet 256B `data_read` komutu döngüyle gider (ilerleme çubuğu %); indirilen `.bin` adres sırasına göre birleşik. 1 MiB üst sınırı zaman pratikliğidir (DCC'de ~4096 komut/MiB), protokol sınırı değildir. | Yok — chunk döngüsü mantığı korunmuş, yalnız her chunk artık binary çerçeve. |
| `.bin` dosyası seç, Hedef adres gir, **Dosyayı flash'a yaz** (yazım sonrası geri okuyup doğrula işaretliyken). | Onay diyaloğu: *"{dosya} ({N} bayt) → {part} {başlangıç}..{bitiş} yazılacak. DİKKAT: NOR flash programlama yalnız 1→0 çevirir; hedef alan önceden SİLİNMİŞ (0xFF) olmalıdır..."* Onaylayınca 256B sayfa-hizalı `page_program` komutları döngüyle gider; ardından `data_read` ile geri okunup byte-byte doğrulanır; başarıda "N bayt yazıldı ve geri okumayla birebir doğrulandı" özeti. | Yok — akış aynı; her komut artık binary çerçeve; page_program body alanları katalogdan gelir. |
| Aynı cihazda önce **hedef sektörü sil** (tekil operasyon panelinden `sector_erase`, address = sektör içi bir adres), sonra üstteki page_program adımını TEKRARLA. | `sector_erase` `ok=1` döner (geri dönüşsüz uyarı notu panelde görünür); ardından program+doğrulama adımı temiz geçer (silinmemiş alanda yazarsan doğrulama düşer — bu senaryoyu da bir kez dene: sil MEDEN yaz → "doğrulama düştü: {adres} adresinde X beklendi Y okundu (alan silinmemiş olabilir)" hatasını gör). | Yok — sector_erase her zaman ayrı komut olarak vardı; tel binary. |

## 6. I2C hat taraması (mux dahil)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Test Bench sol menüde **Hat Tarama** (I2C) sayfasına geç, Denetleyici seç, **Hattı tara**. | Tarama sırasında buton "Taranıyor..." gösterir; bitince Doğrudan hat + (varsa) her switch'in her kanalı ayrı satır olarak tam harita tablo döner (`Pozisyon` / `Cevap veren adresler` / `Adet`). Şematikle eşleşen adresler yeşil, şematikte olmayan adresler turuncu, şematikte beklenip cevap vermeyen cihazlar kesikli kırmızı işaretlenir. | Yok — tarama probu (1-baytlık 0x00 yazma) davranışı aynı; her adres yoklaması artık `i2c_scan`/`i2c_mux_set` binary komutlarıyla gidiyor (`I2C_MUX_SET` yeni katalog girdisi — bu arkın eklediği tek yeni op). |
| Ajan rozetini kontrol et (`ajan {sürüm}`). | Eğer `probe_is_write=false` görürsen (eski ELF hâlâ karttaysa) kırmızı uyarı çıkar: "yazma-problu tarama v0.1.105+ firmware gerektirir... Kaynakları güncelle + ÜRETİLEN yeni ELF'i yükle." | Bu uyarı S2C-MSG'den bağımsız, eski bir saha bulgusu — yine de yeni ELF'i yükledikten sonra kontrol et. |
| `suspect_all_ack` uyarısını tetikleyecek bir durum varsa (SDA hattı LOW'a takılıysa) gözlemle. | "0x08–0x77 aralığının neredeyse tamamı cevap verdi..." turuncu uyarı. | Yok. |

## 7. Trace seviyeleri (log_level değişimi + Akış'ta TRACE metinleri + Seri Hat dalga formu)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Bağlantı kartından Agent log seviyesini `2 — warning` (varsayılan) bırak, birkaç komut gönder, **Akış** (Veri Akışı/TrafficPanel) sayfasını aç. | TX/RX satırları görünür (`entry.ozet` üstte, `entry.hex` altta mono/soluk); `S2C-LOG|` metinleri normal warning/error seviyesinde nadir. | **Fark**: eski satır-protokolde ham `S2C|...` / `S2C-LOG|...` metinleri direkt görünürdü; şimdi normal komut/yanıt çiftleri ÇERÇEVE ÖZETİ olarak (`"{AD} (istek|yanit) sayac=N govde=NB"`), TRACE/log satırları ise TRACE_EVENT çerçevesi içinde AYNEN korunmuş metin olarak akar — biçim aynı görünür ama taşıyıcı artık binary çerçeve. |
| Log seviyesini `5 — debug`'a çevir. | Bundan sonraki komutlarda çok daha fazla `S2C-LOG|...|TRACE|...` satırı Akış'ta görünür (bus-seviyesi transfer izleri dahil). | Yok — davranış aynı; TRACE_EVENT/BUS_TRACE_EVENT ayrımı yeni ama metin AYNEN korunuyor. |
| **Seri Hat** sayfasına geç, log seviyesi 5 (debug) İKEN bir `register_read`/`register_write` komutu gönder. | Komut kartında "canlı iz" rozeti (yeşil) görünür; alt kısımda gerçek TX/RX baytlarından kanal kanal (I2C/SPI) çizilmiş bit-seviyeli dalga formu (`BusWaveform`) render olur — poll tekrarları `×k` olarak katlanır. | **Fark (kritik)**: log seviyesi 5 OLMADAN bu dalga formu çizilmez, yalnız istek/yanıt özeti + ham hex görünür — bu davranış Task 3'te bilinçli olarak sadeleştirildi (eski satır-protokolün `S2C|...reg=...|data=...` alanlarını client-side ayrıştırıp senkron olarak diyagram kuran eski mekanizma binary protokolde YOK; dalga formu artık yalnız gerçek TRACE metninden gelir). Karta yüklenen firmware'in TRACE_EVENT'leri gerçekten bu şekilde ürettiğini burada ilk kez doğrula. |
| Log seviyesini `1 — error`'a çevir, aynı komutu tekrar gönder. | Seri Hat kartında artık TRACE yok, yalnız istek/yanıt özeti + hex görünür (dalga formu render OLMAZ). | Beklenen davranış — kısıt değil. |

## 8. mem_read/mem_write (register map canlı izleme, 0xA0000000 test IP)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Register Map sayfasında **Canlı İzleme** sekmesine geç; base adresi `0xA0000000` olan haritayı seç (ya da "Test IP haritasını yükle" ile Vivado'nun ürettiği Register Map Test IP haritasını yükle — gerçek base adres `localStorage["spec2code.regmap.testIpBase"]`'ten gelir, Vivado atadıysa). | Bağlantı durumu satırı (`Bağlı`/`Bağlı değil`) + Bağlan/Kes; **Hepsini oku** ile tüm rezerve-olmayan register'lar sırayla `mem_read` ile okunur, tablo `Değer` sütununda dolar. | Yok — bu ekranın komutları zaten `mem_read`/`mem_write` op adlarını kullanıyordu; tel artık binary. |
| Bir register satırında **oku** butonuna bas (scalar ya da bit alanı). | Tek register `Xil_In32(base+offset)` eşdeğeri okunur; `Etkinlik günlüğü`nde `rd 0x{adres} → {değer}` satırı eklenir. | Yok. |
| Bir bit-alanına ya da ham değere yeni değer yaz (**yaz** linki). | Onay YOK (register_write'tan farklı olarak mem_write burada direkt gider) — `mem_write` komutu gider, `Etkinlik günlüğü`nde `wr 0x{adres} = 0x{değer} → {değer}` satırı görünür. | Yok. |

## 9. CİT koştur + CİT oku + limit ihlali senaryosu

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| CİT sayfasını aç (yalnız üretimde birimli okuma op'u seçili bir cihaz varsa görünür), bağlan, **CİT koştur**. | `CIT_RUN` gider; üst şeritte `kritik NOK N`, `uyarı NOK N`, `OK N` rozetleri + "son koşu {saat} · sayaç {N}" güncellenir. Tablo: her ölçüm için Ad/Cihaz/Ham/Değer+birim/Min-Max/Önem/Durum (OK yeşil, kritik NOK kırmızı, uyarı NOK amber). | Yeni özellik — bu arkta eklendi, eski protokolde karşılığı yok. |
| **Son CİT'i oku** butonuna bas (yeniden koşturmadan). | `CIT_READ` gider, aynı `SBoardCit` anlık görüntüsü (koşturmadan) döner — sayaç/son koşu zamanı DEĞİŞMEZ (yeniden koşulmadığı için). | — |
| oto-yenile aç. | 5 saniyede bir otomatik `CIT_READ` (koşturma değil, yalnız okuma) tetiklenir. | — |
| Bir ölçümün limitini (min/max) daralt (örn. gerçek değeri dışarıda bırakacak şekilde), **kaydet**. | Satırda `değişti` rozeti + üst şeritte `kontrat değişti — kodu yeniden üret` uyarı rozeti belirir (store'daki override ile üretilmiş koddaki limit farklı olduğu için). | Beklenen davranış — bu, CİT limitlerinin DERLEMEYE GÖMÜLÜ olmasının doğal sonucu (bkz. kısıtlar); yeniden Generate + Vitis build + karta yükleme yapılmadan yeni limit KART TARAFINDA etkili olmaz. |
| Generate'i tekrar çalıştır, yeni ELF'i karta yükle, **CİT koştur**. | Daraltılmış limit artık üretilmiş kodda gömülü; ilgili ölçüm gerçek değeri limit dışına düşürüyorsa `NOK` rozeti (kritik ise kırmızı, uyarı ise amber) görünür ve üst şeritteki `kritik NOK`/`uyarı NOK` sayaçları artar. Limiti eski haline getirip tekrar üret/yükleyince NOK kaybolur. | Uçtan uca kanıt: limit → kod → NOK zinciri BURADA ilk kez gerçek kartta doğrulanıyor. |

## 10. YATT export (manifest'li)

| Adım | Beklenen sonuç | Fark |
|---|---|---|
| Bir proje Generate edilmişken Arayüz/YATT sayfasını aç. | Üst şeritte `kontrat CRC32 {hash}` rozeti + `{N} mesaj` rozeti + `manifest zenginleştirmesi hazır` (yeşil) rozeti (cihaz/CİT tabloları export'a dahil edilecek anlamında). Aşağıda başlık formatı (12 bayt LE) tablosu + hata kodları tablosu + mesaj tablosu (ID/ad/yön/gövde boyu, satır genişletince alan tablosu). | Yeni sayfa — bu arkta eklendi. |
| **YATT indir (HTML)** butonuna bas. | Self-contained tek dosya `yatt.html` iner; harici bağımlılık olmadan (air-gap'te) tarayıcıda açılabilir; içinde manifest cihaz/CİT tabloları dahil. | — |
| **YATT indir (MD)** butonuna bas. | `yatt.md` iner, aynı içerik Markdown formatında. | — |
| Generate ÇALIŞTIRILMADAN (manifest yokken) aynı sayfayı aç. | `manifest yok — katalog-yalın` (nötr) rozeti görünür; export yine çalışır ama yalnız katalog (cihaz/CİT tabloları OLMADAN). | — |
| Backend'in ürettiği `message_catalog_crc32` (manifest içinde) ile YATT sayfasındaki `kontrat CRC32` rozetinin AYNI değeri gösterdiğini doğrula. | İki değer birebir eşleşmeli — bu, üretilen ajanın (`spec2code_mesaj.c`) kullandığı katalog ile backend'in `s2cmsg.py` katalogunun senkron olduğunun kanıtı. | Bu arkın kontrat-hash mekanizması budur (VERSION yanıtında DEĞİL, manifest+YATT'ta). |

---

## Genel notlar

- Her transportta en az bir kez **madde 1'den 9'a kadar TAM sırayla** koş
  (device_init → flash → i2c → trace → mem_read/write → CİT); tek tek izole
  test değil, art arda gerçek kullanım senaryosunu simüle eder (parser
  durumunun feed-forward ile chunk/segment sınırları arası korunduğunu en iyi
  bu şekilde yoklarsın).
- Herhangi bir adımda beklenmedik `GECERSIZ_MESAJ`/`ZAMAN_ASIMI` görürsen:
  önce karttaki ELF'in bu arkla üretilmiş GÜNCEL kod olduğunu doğrula (eski
  ajanla uyumsuzluk en olası sebep), sonra transport'a özgü mü (yalnız
  UART'ta mı, hepsinde mi) olduğunu diğer iki transportla karşılaştırarak ayır.
- Bulgularını (geçti/kaldı + hata mesajı + transport) bu dosyanın bir
  kopyasına işleyip proje ekibine ilet; "Bilinen v1 kısıtları" bölümündeki
  maddeler haricindeki her NOK bir gerçek bulgudur.
