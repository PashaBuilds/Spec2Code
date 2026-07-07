# Spec2Code Changelog

Bu dosya release paketlerinin icine girer ve gecmis tum release degisikliklerini
tek yerde tutar. En yeni surum her zaman en usttedir.

## v0.1.122 - 2026-07-07

- Vivado DDR: "Custom parametre" formu yerine MODEL HAVUZU (kullanici
  istegi). DDR modu artik uc secenek: DDR yok (OCM) | Model havuzundan
  sec (onerilen) | Gelismis (datasheet parametreleri). Havuzda:
  Micron MT40A512M16 (8Gb x16 - kullanicinin karti: LY-062E x2 =
  32-bit 2GB) ve MT40A256M16 (4Gb x16). Model + veri yolu (yonga
  sayisi) secilir; ozet satiri "2 x MT40A512M16 -> 2 GB, 32 Bit".
- Veri kaynagi durustlugu: adres geometrisi (row/col/bank/bg,
  kapasite, genislik) Xilinx'in resmi DDR4 katalogundan
  (mem_v1_4/memparts.csv); CL/tRCD gibi zamanlamalar HIC yazilmaz.
  HIZA DOKUNULMAZ: PCW'nin tutarli DDR4-1600 varsayilaninda kalinir -
  E2E bulgusu: SPEED_BIN/FREQMHZ'i script'le degistirmek PCW'de
  bin<->frekans<->CL tavuk-yumurtasina takilip atomik geri aliniyor
  (tam PLL dict'i bile). Tum listelenen parcalar 1600'e geriye uyumlu;
  hiz yukseltme kart dogrulaninca ayri faz. Yeni uc: GET
  /api/vivado/ddr-parts.
- E2E kaniti (gercek Vivado 2023.2, kullanicinin karti birebir):
  MT40A512M16 x2 (32-bit) + UART0/I2C0 -> DDR ACIK sentezsiz XSA
  uretildi; XSA icinden dogrulandi: 8192 MBits / x16 / 32 Bit /
  ROW 16 / COL 10 / BG 1 / ECC Disabled, PCW 1600 seti tutarli.

## v0.1.121 - 2026-07-07

- Vivado sayfasi: MIO konumlari artik ACILIR MENUDEN secilir (parca
  numarasi gibi). Her PS cevre birimi satirinda "otomatik (Vivado
  varsayilani)" + o birimin GECERLI MIO konumlari listelenir. Liste
  UYDURMA DEGIL: kurulu Vivado 2023.2'de kabul-testi taramasiyla
  uretildi (peripheral enable -> her MIO konumunu dene -> Vivado'nun
  kabul ettiklerini topla) ve part-bagimsiz oldugu icin (ZynqMP MIO
  duzeni sabit silikon) pakete gomulu gelir - aninda hazir.
  UART0 taramada 4'er blok verdi (MIO 2..3, 6..7, ...), I2C/SPI/GEM/SD
  cok esnek oldugundan liste uzun (hepsi Vivado-gecerli). QSPI iki
  moduyla (x1 MIO 0..5, x4 MIO 0..12). Yeni uc: GET /api/vivado/
  mio-options. Elle deger de korunur (eski kayit "(elle)" olarak).

## v0.1.120 - 2026-07-07

- Vivado MIO cakismasi (SAHA KOK NEDENI, Vivado 2023.2 ile satir satir
  dogrulandi): Coklu cevre birimi TOPLU (-dict) enable edilince Vivado
  varsayilan MIO'lari bagimsiz hesaplayip cakisiyordu (UART0 varsayilani
  'MIO 6..7' SPI1 ile cakisti, set_property topluca geri alindi -
  kullanicinin gordugu hata). Birimler artik TEK TEK enable edilir.
  Ayrica kesfedilen kisit: Vivado bir birime SABIT dusuk-MIO varsayilani
  verir ve cakissa bile OTOMATIK TASIMAZ (i2c1 varsayilani 'MIO 0..1'
  bile QSPI 0..5 ile cakisiyor); list_property_value bu IO'lar icin bos
  doner, indeksle set edilemez - yani yasal secenekler Vivado'dan
  programatik alinamaz (el yapimi pinmux tablosu tasimayiz).
- Dogru davranis: TEK birim bos MIO ile otomatik atanabilir; BIRDEN
  FAZLA birimde MIO'lar kartin semasindan girilmelidir (silikon
  gercegi). Bos birakilan birim cakisirsa uretim, HANGI birime MIO
  vermen gerektigini soyleyen net Turkce hatayla durur. UI: 2+ birim
  bos MIO ile secilince uretimden ONCE uyari; Kilavuz 2.5 guncellendi.
- E2E kanit (gercek Vivado 2023.2): 6 cevre birimli tam tasarim
  (QSPI + I2C0 + I2C1 + UART0 + GEM3 + SD1) hepsi acik MIO ile
  URETILDI, GEM3 MDIO 76..77'ye otomatik yerlesti, uretilen XSA parser
  tarafindan eth/i2c/i2c/qspi/sdio/uart olarak geri okundu.

## v0.1.119 - 2026-07-06

- Vivado sayfasi: DDR "Custom" secilip hicbir alan doldurulmadan
  "Tasarimi uret" denince ham dogrulama hatasi yerine formda anlasilir
  uyari cikar (API'ye gitmeden): datasheet degerlerini gir ya da ilk
  bring-up icin "DDR yok (OCM)" moduna al.

## v0.1.118 - 2026-07-06

- Vivado Tasarimi: hedef parca artik ACILIR MENUDEN secilir - platforma
  gore Cihaz -> Paket/hiz iki kademeli secim (Vivado'nun kendi part
  secicisi gibi). Liste el ile YAZILMADI: kurulu Vivado'nun get_parts
  ciktisindan bir kez cekilir (~1 dk, "Parca listesini Vivado'dan
  getir" dugmesi) ve onbellege yazilir - sonraki acilislar aninda.
  Siniflama Vivado'nun FAMILY alanindan yapilir (onek tahmini yok;
  ornegin xcvu Virtex UltraScale+ oldugu icin listeye girmez). Bu
  kurulumda: 61 ZynqMP cihazi / 1000 parca, 39 Versal cihazi / 1342
  parca. "elle gir" kacis yolu duruyor.
- Bilinmeyen /api yollari artik durust 404 doner ("backend bu ucu
  tanimiyor - uygulamayi yeniden baslatin/guncelleyin"). Eskiden SPA
  statik sunucusuna dusup POST'ta sasirtici "405 Method Not Allowed"
  uretiyordu (saha bulgusu: eski backend sureci + yeni frontend ucu).
- Vivado sayfasi ust sekmelerden SETUP ICINE tasindi: "Donanim
  tasarimi" kartinin altinda "XSA uret (opsiyonel)" bolumu - "Vivado
  sayfasini ac" ile Setup sayfasi TAM EKRAN Vivado sayfasina donusur,
  "Setup'a don" ile geri gelinir (kosan is kesilmez, panel yeniden
  baglanir). Esneklik: uretilen son XSA ana Setup'ta tek tusluk
  "Vivado'da uretilen XSA'yi kullan" kisayolu olarak gorunur; yol elle
  de secilebilir. Ctrl+K komutu da Setup icindeki sayfaya goturur.

## v0.1.117 - 2026-07-06

- YENI: Vivado Tasarimi sekmesi (Faz A) - elde .xsa yokken Spec2Code
  onu uretir. Gercek kartin PS arayuzleri (UART/I2C/SPI/QSPI/GEM/SD)
  formdan secilir, MIO'lar girilir; arka planda Vivado batch kosar.
  IKI ASAMALI teslim: (1) sentezsiz .xsa ~1-2 dk'da hazir, "Setup'a
  bagla" ile sematik akisina tek tusla girer; (2) istege bagli sentez +
  implementasyon ile .bit (ZynqMP) / .pdi (Versal) + bit'li sabit XSA.
  Canli log/asama akisi (WebSocket), sekme degisiminde ise yeniden
  baglanma, Kilavuz 2.5 bolumu.
- Kapsam ve durustluk: ZynqMP tam (DDR dahil), Versal Faz A'da UART/I2C
  + DDR'siz (NoC/DDRMC sonraki faz), Zynq-7000 bilincli kapsam disi.
  PSU__*/CIPS parametre adlari resmi zcu102/vck190 tasarimlarindan
  dogrulandi; MIO yasallik denetimi Vivado'ya birakilir (uydurma pinmux
  tablosu yok). DDR: "DDR yok (OCM)" ilk bring-up onerisi + Custom
  datasheet formu (19 alan). Vivado'nun 260 karakterlik Windows yol
  siniri icin kisa Temp zorunlulugu onden denetlenir.
- E2E kanitlari (gercek Vivado 2023.2): ZynqMP xczu9eg PS-only ->
  sentezsiz XSA -> Spec2Code parser'i geri okudu (I2C0/I2C1/UART0 tam
  konfigure edilen MIO'larla); Versal xcvc1902 -> XSA -> parse
  (XIicPs + XUartPsv); ZynqMP xczu2cg -> synth+impl -> GERCEK .bit +
  bit'li XSA. 174 unittest yesil (6 yeni Tcl/validasyon testi).

## v0.1.116 - 2026-07-06

- Setup: donanim girisi TEK dosya - Vivado .xsa (2019.2+) veya eski SDK
  akisinin .hdf'i (ikisi de zip icinde .hwh tasir, ayni parser okur).
  xparameters.h yukleme/yapistirma destegi arayuzden kaldirildi.
- Vitis sekmesi: ayri "XSA dosyasi" girisi kaldirildi - Setup'ta verilen
  dosya otomatik kullanilir (salt okunur gosterilir; degistirmek icin
  Setup'ta yeni .xsa yuklenir). Setup'ta dosya yoksa net uyari.
- Durust kapi: Vitis workspace kurulumu .xsa gerektirir (XSCT platform
  create XSA icin belgelidir); .hdf ile kuruluma hem arayuz hem API
  (422) acik Turkce hatayla izin vermez - .hdf yalniz sematik ve kod
  uretimi icindir.
- Dogrulama: sentetik .hdf ve gercek vck190.xsa canli API uzerinden
  parse edildi; .hdf yukleme adi uzantisini korur; 168 test yesil.

## v0.1.115 - 2026-07-06

- Sematik kanal kablolari RENK KODLU: her kanalin kablosu ve "ch N"
  etiketi ayni renktedir, farkli kanallar farkli renk alir (8 kanallik
  sabit palet: ch0 kehribar, ch1 gok mavisi, ch2 zumrut, ch3 pembe,
  ch4 eflatun, ch5 mercan, ch6 limon, ch7 turkuaz). Kanal cikis
  noktalari (handle) da ayni renge boyanir.
- "ch N" etiketi tek yerde: I2C switch cikisinin hemen dibinde kucuk
  renkli cip olarak durur; kablolar uzerindeki tekrarli etiketler
  kaldirildi (saha istegi). Kanal takibi renkle yapilir - ayni kanali
  paylasan entegrelerin kablolari ayni renkte ortak baradan dallanir.

## v0.1.114 - 2026-07-06

- DS1682 SAHA KOK NEDENI COZULDU: elapsed_read / alarm_read / event_read
  (ve LTC2945 power_read) ajanda BUS'A HIC CIKMADAN status=1 donuyordu.
  Sebep: bu op'larin descriptor'daki donus tipi "uint32" ve testbench op
  eslemesinde uint32 dali yoktu - op'lar surucu fonksiyonu hic
  cagrilmadan "operation signature not mapped" yakalayicisina dusuyordu
  (bu yuzden seviye 5'te bile tek I2C izi/TRACEERR gorunmuyordu; karar
  verdiren ayni-oturum logu: 13:10, v0.1.113 dogrulanmis ajan).
  Duzeltme: uint32 op'lar artik surucuyu cagirir, ham deger value + 4
  big-endian bayt olarak doner. Yakalayiciya dusen op bundan boyle
  ERROR seviyesinde adiyla loglanir (genel "failed" mesaji ipucunu
  ezmisti). Regresyon: katalogdaki HER descriptor'in *_read op'unun
  testbench'e baglandigini dogrulayan yapisal test eklendi. Kartta
  calismasi icin YENI release ile generate + ELF yukleme gerekir.
- Veri Akisi konsolu: S2C-LOG satirlari log seviyesine gore renklenir
  (E kirmizi, W sari, I parlak, D soluk, M en soluk ayna satiri; S2C|
  yanit satirlari bus renginde). Not: ajanin seviye olcegi 1=error..
  5=debug'dir - ayri bir "trace" seviyesi yok; DS1682'de debug baytlari
  gorunmemesinin sebebi yukaridaki kok nedendi (op bus'a inmiyordu).
- Sematik kanal kablolari: her kanal kendi DIKEY SERIDINDE yurur (ozel
  ChannelWireEdge kenari). v0.1.112 kanal cikislarini ayirmisti ama
  smoothstep tum kablolari ayni orta noktada bukup tek dikey hatta
  bindiriyordu (saha fotografi: ch2/3/3/4/4/5 ayni hat uzerinde).
  Seritler cihaz kolonunun solundaki bos koridora demirlenir (orta
  kolondaki dugumlerin icinden gecmez), ayni kanali paylasan kablolar
  ayni seridi kullanip ortak bara gibi gorunur, "ch N" etiketleri kendi
  seridinin ustunde durur. Gercek Chrome goruntusuyle dogrulandi.
- Demo sema (?demo) saha kartina benzetildi: mux arkasi ch2 SHT21,
  ch3 LTC2991+LTC2945, ch4 iki LTC2991, ch5 DS1682 - kanal ayrisma ve
  paylasilan-kanal gorunumu demo uzerinde dogrudan gozlenebilir.

## v0.1.113 - 2026-07-06

- Registers ekrani: register listesi TUM entegrelerde adrese gore
  kucukten buyuge siralanir. Katalog birlestirmesi yeni registerlari
  descriptor dosyasinin sonuna ekledigi icin LMK04832'de liste karisik
  gorunuyordu (RESET'ten sonra PLL2_N_CAL_0..RB_PLL_STATUS, ardindan
  0x002'ye donus) - siralama manifest uretiminde tek noktadan yapilir,
  snapshot/diff ayni duzeni izler. Yeniden Generate gerektirir
  (firmware degil, yalniz manifest).

## v0.1.112 - 2026-07-06

- Sematik: I2C switch'in kanal kablolari artik ust uste binmez. Mux
  dugumu KULLANILAN her kanal icin ayri bir cikis noktasi cizer (sag
  kenarda dikey dagitilmis); farkli kanallarin kablolari dugumden
  farkli yuksekliklerden cikar, yalniz AYNI kanali paylasan entegrelerin
  kablolari ayni noktadan cikip ortak hat olusturur (saha UX bulgusu).

## v0.1.111 - 2026-07-06

- DESCRIPTOR SIHIRBAZI (Import ekrani): formdan descriptor YAML'i uretir
  - v1 kapsami I2C register cihazlari. Ilke: hata siniflarini imkansiz
  kilmak - register/alan referanslari elle yazilmaz, tablodan SECILIR
  (poll alani secili registerin bit alanlarindan beslenir). Icerik:
  kimlik/transport formu, register tablo editoru + bit alanlari,
  operasyon kurucu (adim turu secimli), convert formu + CANLI formul
  onizlemesi (ornek ham deger gir -> donusmus degeri aninda gor,
  uretilen C ile ayni tam sayi matematigi), test_hints. Sagda canli
  YAML onizleme + uretilecek C imzalari (yaklasik) + Dogrula (kaydetsiz
  yapisal kontrol - yeni POST /api/user-descriptors/validate ucu) +
  Kaydet (user_descriptors) + YAML indir + "Ornekle doldur". Bos
  zorunlu alanlar yer tutucuyla maskelenmez - dogrulayici yakalar.
- Release workflow artefaktlarina retention-days: 1 - varsayilan 90 gun
  saklama artefakt depolama kotasini doldurup release'leri kirmisti
  (312 artefakt / ~1.2 GB temizlendi).

## v0.1.110 - 2026-07-06

- KULLANICI DESCRIPTOR'LARI: katalogda olmayan (veya sirket ici) bir
  entegre artik uygulamaya YAML descriptor olarak eklenebilir. Import
  ekranindaki "Descriptor ice aktar" bolumu dosyayi sema dogrulamasindan
  gecirir (alan alan Turkce hatalar; hatali dosya kaydedilmez) ve
  exe'nin yanindaki user_descriptors/ klasorune koyar - dosya dogrudan
  klasore de birakilabilir. Kaydedilen parca sematik parca secicide
  "user" statusuyle gorunur; Generate, Test Bench, Registers, Seri Hat
  ve uretilen surucu yerlesik entegrelerle birebir ayni zincirden
  uretilir. Ayni adli yerlesik parca varsa KULLANICI dosyasi onceliklidir
  (yerlesik bir haritayi duzeltmek icin de kullanilabilir). Bilinmeyen
  parcalarda Seri Hat dalga formu manifest'teki transport tipine duser.
- Kilavuz'a 15.0 "Ozel entegre - descriptor yazim rehberi" bolumu:
  adim adim kimlik/transport -> registers -> operasyonlar (adim tablosu)
  -> convert formulu -> test_hints, TICS/flash/EEPROM arketipleri ve
  dogrulama duzeni.
- Import ekraninda "Ornek sablonu indir / goruntule": aciklamali MYMON16
  ornegi tek dogruluk kaynagindan servis edilir ve testler AYNI icerigi
  dogrulayicidan + tam uretimden gecirir - indirilen sablon her zaman
  bilinen-iyi bir baslangictir. Surucu kaynak (.c/.h) ice aktarma
  ikincillestirildi: kapali "gelismis" basligi altinda ve durust
  etiketle ("uretimin yerine gecmez; cikti paketine referans olarak
  eklenir") - birincil yol descriptor akisidir.

## v0.1.109 - 2026-07-05

- SAHA (kok neden KANITLANDI): paketli uygulama ajani "dev" suruguyle
  damgaliyordu - taze generate + guncel ELF'te bile. Neden: PyInstaller
  --add-data'nin hedefi DIZINDIR; hedefe dosya adi yazildigi icin surum
  dosyasi exe icine spec2code_version.txt\spec2code_version.txt diye
  IC ICE gomuluyordu ve okuyucu o yolda dizin bulup "dev" yedegine
  dusuyordu. TUM onceki paketli surumler etkilendi. Yerelde v0.1.108
  exe'si ayni betikle paketlenip API'den generate edilerek birebir
  yeniden uretildi (AGENT_VERSION: dev + _MEI icinde ic ice dizin),
  duzeltme sonrasi ayni sondaj AGENT_VERSION: v0.1.109 verdi.
  Duzeltme: --add-data hedefi "." (paket koku).
- Ayrica surum cozumleme zinciri katmanlandi (tek nokta kalmasin):
  spec2code_version.txt exe'nin YANINDA da paketlenir; BOM'lu metadata
  tolere edilir (utf-8-sig); changelog yedegi exe dizini dahil tum
  koklerde aranir; uygulama aciliste cozdugu surumu basar ("Spec2Code
  backend version: vX"). NOT: karttaki "dev" ancak yeni uygulamayla
  yeniden Generate + kaynaklari guncelle + build + ELF yukleyince
  degisir.

## v0.1.108 - 2026-07-05

- Genis (16-bit) registerlar Registers ekraninda: manifest'teki genislik
  filtresi AD7414 TEMPERATURE, TMP101 TEMPERATURE/TLOW/THIGH ve LTM4681
  word komutlarini ekrandan dusuruyordu - kaldirildi. Generic
  register_read/write ajan tarafinda genislik-farkindali oldu: 16-bit
  register tek islemde 2 bayt okunur/yazilir (SMBus read/write-word ile
  ayni tel bicimi), value birlesimi descriptor byte_order'a gore
  (AD7414/TMP101 big, PMBus little). Yeni firmware gerektirir.
- REGRESYON KORUMASI: read_registers'in iki anlami genislige gore
  ayristirildi - 8-bit ardisik registerlar (DS1682 ETC, LTC2945) tek
  bayt okumalarla toplanir; TEK genis register (AD7414/TMP101
  TEMPERATURE) pointer + 2 bayt TEK islemde okunur (tek-bayt yontemi
  orada ikinci bayti yanlis registerdan okurdu).

- SAHA (DS1682 cozuldu): elapsed/alarm okumasi fail olurken register
  snapshot'in 21/21 basarili olmasi kok nedeni gosterdi - snapshot
  register basina TEK baytlik okuma yapar (kanitli calisan yol),
  elapsed_read ise tek pointer + 4 baytlik BLOK recv kullaniyordu ve
  bu kartta blok recv aninda dusuyor. read_registers artik ardisik
  register adreslerini tek-bayt okumalarla toplar; kosan sayac icin
  datasheet yontemi uygulanir (iki gecis karsilastirilir, uyusmazsa
  ucuncu gecis gecerlidir). Yeni firmware gerektirir.
- I2C hatalari artik SESSIZ degil: her basarisiz transfer
  spec2codeBusTraceI2cError kancasiyla adres/register/asama (p=pointer,
  r=recv, w=yazma, m=mux kanal secimi) raporlar; test bench guclu
  implementasyonu ERROR seviyesinde loglar - VARSAYILAN log seviyesinde
  bile "TRACEERR|...|addr=0x6B|reg=0x05|asama=r|status=1" satiri
  gorunur. Surucusu bagimsiz projelerde kanca zayif no-op'tur.
- Flash binary okuma ozeti artik ilk 16 + SON 16 bayti gosterir:
  chunk'lar arasi adres ilerleyisinin hizli saglamasi (yinelenen blok
  suphesi ilk bakista dogrulanir/curutulur).

- Registers ekrani katalogla birebir: descriptor register haritalari
  katalogdaki (datasheet-dogrulanmis) tam haritayla esitlendi -
  LMK04832 10 -> 125, LMX2820 7 -> 123, LMX1205 9 -> 44, LMX1204
  6 -> 35 register (alan/bit tanimlari ve aciklamalariyla). Diger
  entegreler zaten birebirdi (ADAR1000 78, LTC2945 50, LTC2991 30,
  DS1682 24, ...). Mevcut girdiler aynen korundu; ekler manifest,
  Registers ekrani, register_read/write ve uretilen C register
  tablolarina tek kaynaktan yansir.

## v0.1.107 - 2026-07-05

- SAHA: flash'tan 256 bayt okumak timeout'a dusuyordu (128 calisirken).
  Kok neden: ajan cevap satiri tamponu 512 karakterdi; 256 baytlik data
  (512 hex) + prefix + mesaj ~750 karakterdir. Satir kirpilip \n'siz
  gonderiliyor, host satiri tamamlayamayip timeout'a dusuyor ve kirpik
  govde bir SONRAKI cevapla yapisiyordu (sahada id=47+id=48 tek satir).
  Duzeltme: LINE_MAX 1024 (tum ajanlar; istek tarafi 256B page_program
  payload'i icin de gerekliydi) + tasma bekcisi: satira sigmayan cevap
  kirpik gonderilmek yerine data'siz "response line overflow" hatasina
  cevrilir. NOT: yeni firmware gerektirir.
- Test Bench flash sayfasina "Binary dosya aktarimi" karti: adres +
  uzunluk ver, chunk chunk okunur ve .bin olarak iner (ozet: sure, hiz,
  ilk 16 bayt); .bin dosyasi + hedef adres ver, sayfa hizali
  page_program komutlariyla yazilir (NOR uyarisi: alan onceden silinmis
  olmali - onay istenir) ve istenirse geri okunup bayt bayt dogrulanir
  (ilk uyusmayan adres raporlanir). Ilerleme cubugu + kalan sure +
  iptal. Sinirlar: komut basina 256 bayt (protokol data alani), tek
  aktarim <= 1 MiB (zaman pratikligi - DCC uzerinde buyuk aktarim
  yavastir, TCP/UART onerilir); teoride flash'in tamami chunk'larla
  okunabilir.

- SAHA: "build edildi ama karttaki ELF eski kalmis" tuzagina karsi uc
  gorunurluk katmani. (1) I2C taramasi artik once ajan surumunu sorgular
  ve sonucta "ajan vX" cipi gosterir; v0.1.105 oncesi ELF'te (okuma
  problu, sahada hepsi-ACK artefakti ureten surumler) kirmizi uyari
  cikar. (2) Hepsi-ACK bekcisi: 0x08-0x77'nin ~tamami cevap veriyorsa
  harita "fiziksel olarak olagan disi" uyarisiyla doner (eski firmware
  veya SDA'si takili hat). (3) Vitis sonucundaki Application ELF
  satirlari uretim zamanini gosterir - karta yuklenen ELF bundan
  eskiyse eski firmware kosuyordur.
- Test Bench entegre sayfasina baglanti zinciri rozeti: denetleyici ->
  switch+kanal (veya "switch yok (dogrudan hat)") -> I2C adresi / SPI
  CS. Model/kart uyusmazliklari (or. cihaz fiziksel olarak switch
  arkasindayken modelde dogrudan hatta gorunmesi) tek bakista yakalanir.
- Ajan tarama dongusu log seviye 5'te ACK basina "i2c tarama ACK: 0x.."
  satiri basar (tarama ici adim adim teshis).

## v0.1.106 - 2026-07-05

- SAHA: QSPI flash data_read ajani KILITLIYORDU (address=0x0 length=4:
  "op basla" son log, cevap yok, sonraki tum komutlar cevapsiz - agent
  tek is parcaciginda calisir). Kok neden: command_read TEK mesajda
  TX|RX kombine gonderiyordu; toplam 1+4+4=9 bayt >= 8 oldugundan
  transfer DMA okuma yoluna girer ve XQspiPsu_SetupRxDma 4'e bolunmeyen
  uzunlukta Msg->ByteCount'u kirpar (9->8) - ayni ByteCount'u TX
  kurulumu 9 olarak kullanmisti; tek ortak alan iki yonu birden temsil
  edemez ve polled dongu sonsuz bekler. id_read'in calismasi toplam 4
  baytin surucu tarafindan IO moduna dusurulmesindendir (<8 bayt
  kurali). Duzeltme resmi surucu akisiyla hizalar: cmd+addr TX-only
  mesaj + veri RX-only mesaj (CS iki giris boyunca asserted kalir) ve
  RX tamponu DMA cache-invalidate icin 64 bayt hizali. TICS register
  okumalari (3 baytlik kombine frame) surucunun <8 bayt IO-mod
  kuralinda kaldigindan etkilenmez ve degistirilmedi.
  NOT: duzeltme yeni firmware gerektirir (kaynaklari guncelle + build
  sonrasi ELF'i karta yukle).

## v0.1.105 - 2026-07-05

- SAHA: I2C hat taramasi probu okumadan YAZMAYA cevrildi (1 bayt 0x00).
  Gercek kartta XIicPs_MasterRecvPolled adres NACK'inde de basari
  dondurup 0x08-0x77 arasi HER adresi "cevap verdi" gosteriyordu; send
  yolu NACK'i guvenilir raporlar (EEPROM ack-poll ayni ilke). 0x00 cogu
  cihazda yalniz register pointer'ini sifirlar. Kanal taranirken aktif
  switch'in kendi adresi ajana atlatilir (0x00 yazilsaydi secili kanal
  kapanirdi) - ajan op'una address=<atlanacak adres> parametresi eklendi.
  NOT: duzeltme yeni firmware gerektirir (kaynaklari guncelle + build).
- I2C Hat Taramasi ayri sayfa oldu: Test Bench sol menusunde entegrelerin
  ustunde "Hat Tarama" basligi altinda "I2C" girisi; tarama karti yalniz
  bu sayfada gorunur, entegre sayfalarindan kaldirildi.
- SAHA: Surum sorgusu cevabi artik dogru cozulur. Cevap secili cihaz
  operasyonunun metasiyla decode ediliyordu ("0 °C" gibi yanlis rozet);
  sonucu ureten operasyon ayrica izlenir. Ajan surumu ASCII olarak data
  alaninda da doner (eski firmware'de mesajdan ayiklanir) ve yesil
  rozette "= v0.1.105" olarak gosterilir.
- Seri Hat dalga formlarinda gercek bit degerleri: bayt degeri biliniyorsa
  hucrede 0/1 ustte, bit rolu (A6..A0/W, D7..D0, b7..b0) altta yazar.
  SLA satiri gercek hat baytini ve 7-bit adresi verir: "SLA+W = 0x90
  (adres 0x48)" - kablo planinda kartin manifest adresi, canli izde
  TRACE satirindaki gercek adres kullanilir. Katalog (Bilgi) sembolik
  kalir. Kilavuz 8.0 guncellendi.
- Vitis sekmesi metinleri kurulum moduna uyarlandi: "Kaynaklari guncelle
  + build" modunda ilerleme basligi artik "Workspace olusturuluyor"
  yerine "Kaynaklar guncelleniyor + build aliniyor" der (bitiste
  "Kaynaklar guncellendi, build hazir", basarisizlikta "Guncelleme +
  build tamamlanmadi"); backend olay mesajlari (baslangic/bitis) de
  moda gore yazilir. Update modunda workspace olusturulmaz - metinler
  bunu yansitir.

## v0.1.104 - 2026-07-05

Saha oturumunun ikinci dalgasi: I2C hat taramasi, canli bit izleme,
kanal kanal Seri Hat ve kritik coklu-cihaz duzeltmesi.

- I2C HAT TARAMASI (Test Bench): yeni "Hatti tara" karti hattaki tum
  adresleri 1-baytlik okumayla yoklar (0x08-0x77) ve I2C switch
  (TCA9548A) varsa arkasindaki HER KANALI sirasiyla secip ayrica
  tarayarak tam haritayi cikarir. Once tum switch'ler kapatilip
  dogrudan hat taranir (switch arkasi adresler sizmaz); kanal icerigi
  dogrudan-hat adreslerinden ve switch'in kendisinden arindirilir.
  Sonuc pozisyon pozisyon tablo: "Dogrudan hat" satiri (switch'ler
  "0x70 - switch u1_tca9548a" rozetiyle isaretli) + her switch icin
  kanal kanal adres cipleri ve adetler. Cihaz kimligi CIKARILMAZ -
  yalniz adres/pozisyon. Ajan iki global op kazandi: i2c_scan (mevcut
  hatti yoklar, ACK adresleri data'da) ve i2c_mux_set (switch kontrol
  bayti); orkestrasyon backend'te (/api/testbench/i2c-scan), topoloji
  manifest'in yeni i2c_scan bolumunden gelir.
- SERI HAT CANLI BIT IZLEME: surucu en alt seviye bus fonksiyonlarina
  zayif iz kancalari eklendi (drivers/spec2code_bus_trace.h - standalone
  kullanimda no-op, sifir maliyet); test ajaninin guclu implementasyonu
  (tests/spec2code_testbench_trace.c) her GERCEK transferi komut id'siyle
  "S2C-LOG|D|TRACE|..." satiri olarak yayinlar (yalniz log seviyesi 5 /
  debug iken). Kapsam: I2C register oku/yaz/blok-oku, SPI TICS 24-bit
  frame, flash komutlari (send/read/write) ve testbench generic register
  yollari. Seri Hat bu izleri id'ye baglar ve diyagramlari GERCEK
  runtime TX/RX baytlariyla cizer: LTC2991 voltage_read'de V1_MSB'den
  V8_LSB'ye HER KANAL SIRASIYLA ayri diyagram olur, poll iterasyonlari
  "xk" olarak katlanir (gercekten yasanan tekrarlar; uydurma yok). Iz
  yokken (seviye<5 veya eski firmware) operasyonun kablo plani "kablo
  plani" rozetiyle gosterilmeye devam eder. TCP oturumu artik yanit
  eslestirmede S2C-LOG/TRACE satirlarini yanit sanmaz.
- Seri Hat kablo plani diyagramlari: manifest operasyonlarina bus
  seviyesindeki "wire" plani islenir (poll/register adimlari, kanal
  taramasi, flash komut frame'leri, TICS init dizisi) ve iz yokken HER
  kart katalogdaki bus zaman diyagramiyla cizilir - gercek register
  adlari/adresleri, init'te gercek yazilan degerler; donusturulmus
  sonuclarda RX hucreleri MSB/LSB etiketiyle kalir (uydurma bayt yok).
- KRITIK DUZELTME (saha, 2026-07-05): ayni parcadan birden cok cihaz
  (or. 3 x LTC2991) tek surucu modulunu ve tek I2C adres sabitini
  paylasiyordu - hangi cihaz secilirse secilsin hep ayni fiziksel cip
  okunuyordu. Artik her ornek kendi modulunu alir (ltc2991, ltc2991b,
  ltc2991c...): ayri .c/.h, ayri adres/mux sabitleri, dispatch her
  cihazi kendi fonksiyonlarina baglar. Ilk ornek geriye donuk uyumlu
  adlari korur. (Regresyon testi + cift-modul gercek BSP derlemesi.)
- Ajan dispatch'ine op baslangic DEBUG logu eklendi ("op basla: cihaz
  op") - log seviyesi 5'te asili kalan/uzun suren surucu cagrilari
  Akis'tan tespit edilebilir.

## v0.1.103 - 2026-07-05

Gercek ZynqMP karti saha bulgulari (2026-07-05 seri logu) duzeltmeleri:

- TIMEOUT ARTIK OTURUMU GERCEKTEN KESER: onceden bir komut timeout'a
  ugradiginda ajanin GEC gelen yaniti (a) seri/CoreSight yolunda bir
  sonraki komutun cevabi sanilabiliyor, (b) TCP yolunda hic id kontrolu
  olmadan aynen donuyordu; TCP'de timeout ustune oturum da kapaniyordu.
  Simdi her transportta yanit komut id'siyle eslestirilir (yalniz id=0 =
  ajan parse hatasi fallback kalir), id eslesmeyen gec yanitlar dusurulur
  (Akis'ta gorunmeye devam eder), TCP'de timeout oturumu acik birakir ve
  bekleyen bayat satirlar bir sonraki gonderim oncesi ayiklanir.
  Regresyon testleri: TCP bayat+timeout senaryosu, seri bayat-yanit.
- device_init yanitlarinin data alani artik bos degil: descriptor'daki
  post_init_status registeri init basarisindan sonra generic yoldan geri
  okunur; value + data alanlarina konur ve manifest aciklamasina islenir
  ("Basarida X geri okunur"). Kapsam: LTC2991 STATUS_HIGH, LTC2945
  CONTROL, AD7414/TMP101/DS1682 CONFIGURATION, SHT21 USER_REGISTER,
  LTM4681 STATUS_BYTE, LMK04832 RB_PLL_STATUS, LMX2820 R74, LMX1204 R0,
  LMX1205 R32 (rb_VER_ID), ADAR1000 CHIP_TYPE. Generic okuma yolu
  olmayan flash/EEPROM/mux durust sekilde kapsam disi (flash icin JEDEC
  id_read zaten var).
- LTC2945'e milliamper okuma: yeni current_read operasyonu I_mA =
  kod x 25 uV / R_mohm donusumunu yapar; sont direnci KART verisi
  oldugundan device.config.sense_resistor_mohms (miliohm) zorunludur -
  config yokken op listeden durust sekilde duser, acikca istenirse
  anlasilir hata verir. VIN zaten mV (voltage_read). Altyapi: convert
  bloguna scale_den_config (device.config'ten payda) destegi.
- DS1682 gecen sure okumasi zaten saniye cinsindendir (0.25 s tik / 4);
  Test Bench etiketleri netlestirildi: "Gecen sure oku (saniye)" /
  "Alarm esigi oku (saniye)". LTC2945 etiketleri de birimli yazildi
  (uV/mV/mA).
- YENI EKRAN: "Seri Hat" (Akis'in yani) - her S2C komut/yanit cifti id
  ile eslestirilip kart olarak gosterilir: zaman, cihaz, operasyon,
  sure (ms), ok/hata ve COZULMUS deger; register_read/register_write
  transferleri katalogdaki bus zaman diyagramiyla gercek baytlar
  uzerinden cizilir, ham S2C satirlari kart altinda katlanabilir durur.
- Donusturulmus sonuclar artik ondalik + birimle gosterilir: Test Bench
  sonuc karti ve Seri Hat kartlari value alanini manifest'teki yeni
  result_returns/result_unit metaverisiyle cozer - 0xF23 -> "= 38.75 C",
  mV/mA/mW/uV/s ve %RH birimleri, kanal dizileri (voltages[8]) mV
  listesi olarak. Birimsiz (bilincli raw) operasyonlarda hex gosterim
  degismez.
- Vitis paneli kosan ise YENIDEN BAGLANIR: workspace kurulumu surerken
  baska adima/ekrana gecip donunce panel bos buton durumuna dusuyordu
  (is backend'de suruyordu ama UI yansitmiyordu). vitis_job_id artik
  kalici; panel acilista son isi sorgular - is kosuyorsa ilerleme cubugu
  ve log akisi geri gelir (backend soketi tamponlanmis olaylari replay
  eder), bittiyse sonuc/hata gosterilir; is backend'de yoksa kayit
  sessizce temizlenir. Sayfa yenileme de ayni yoldan kurtarilir.

- LTC2991 okumalari kartta ~46.4 s surup status=1 ile dusuyordu. Kok
  neden iki katmanli: (1) init profili repeated-acquisition actigi icin
  (PWM_T_INTERNAL_CONTROL=0x10) cip surekli donusumde ve STATUS_HIGH.BUSY
  hic 0 olmuyor - "BUSY==0 bekle" poll'u hicbir zaman tutmuyordu; (2)
  poll butcesi 100000 ITERASYONDU ve her iterasyon tam bir I2C okumasi
  (~0.46 ms @100 kHz) oldugundan tukenmesi ~46 s aliyordu (UI 5 s
  timeout'unu asar). Duzeltme: poll'lar olcume ozgu READY (data-valid)
  bitlerini bekler (voltage/current -> STATUS_LOW.V1_READY,
  temperature -> STATUS_HIGH.T_INTERNAL_READY, vcc -> VCC_READY) ve
  poll butcesi 1000 denemeye indirildi (~0.5 s tavan; EEPROM ACK poll
  butcesi de ayni sekilde). Regresyon testleri eklendi.
- device_init operasyonlari testbench'in bastan baslattigi paylasilan
  denetleyicide XIicPs/XSpiPs/XQspiPsu_CfgInitialize'i yeniden
  cagiriyordu: sahada mt25qu02g device_init status=5
  (XST_DEVICE_IS_STARTED) dondu; I2C'de de canli SCLK ayarini
  bozabiliyordu. Tum device_init'ler artik IsReady bayragini kontrol
  edip baslatilmis denetleyicide controller-init blogunu atlar
  (standalone kullanimda davranis ayni kalir).
- Test Bench sonuc kartina gonderim zamani (HH:MM:SS.mmm) ve toplam
  gidis-donus suresi (ms) eklendi; "message" alani etiketli ve belirgin
  gosterilir (surum sorgusunun cevabi message'ta tasinir - data alani
  bos olmasi normaldir). NOT: Akis ekraninda ms'li zaman damgalari
  zaten vardir (ekranda sol sutun, indirilen logda satir basi);
  agent'in "Spec2Code dev" bildirmesi eski bir uretimden kalan ELF'tir,
  yeni Generate + update-mode build surumu getirir. Agent log seviyesi
  bagli iken baglanti kartindaki "Agent log seviyesi" secicisinden
  degistirilir (1 error ... 5 debug).

## v0.1.102 - 2026-07-05

- Generate sag kolonu 3 sekmeye ayrildi: "Uretilen kod", "Vitis"
  (workspace kurulumu/guncelleme) ve "Board" (JTAG ile karta yukleme) -
  onceki birlesik "Vitis & Board" sekmesi bolundu. Backend degismedi;
  iki sekme tek panel ornegini paylasir (workspace canli log soketi,
  sonuc ve Board kartinin "workspace hazir" durumu sekme gecislerinde
  kaybolmaz). Board sekmesi basliginda hangi workspace'in yuklenecegi
  (yol + hazir/bekleniyor rozeti) gosterilir; yol ve isimler Vitis
  sekmesindeki formdan gelir. Kilavuz (1.0/4.0/6.0) guncellendi.

## v0.1.101 - 2026-07-05

- YENI ENTEGRE: LMX1205 (TI 0.3-12.8 GHz JESD buffer/multiplier/divider,
  4 clock + 4 SYSREF + LOGICLK) - resmi SNAS850 datasheet'inden (Aralik
  2024, ADVANCE INFORMATION statusu notlara islendi) dogrulanarak eklendi.
  SPI: 24-bit frame (R/W + 7-bit adres + 16-bit veri), mode 0, max 20 MHz
  (LMX1204'un 10 kati). Readback MUXOUT'ta OTOMATIK: pin okuma sirasinda
  kendiliginden aktiflesir, sonra tri-state olur - LMX1204'teki
  MUXOUT_SEL/R86 adimlari yok; READBACK_CTRL (R1, reset 1) yazilan
  degerleri dondurur, multiplier modunda paylasimli bus icin LD_DIS=1
  kosulu "Okuma kosulu" olarak gosterilir. Bring-up sirasi (6.3.7): RESET
  1->0 toggle -> programlama -> zorunlu son yazim DEV_IOPT_CTRL=0x6 (R55);
  descriptor/kilavuz/bilgi ekranina islendi. multiplier_lock_detect
  operasyonu (R37 bit 0) eklendi. Bilgi ekrani: 44 satirlik Table 7-1
  register haritasi + 20 register icin SNAS850 7.1.x bitfield aktarimi +
  VQFN-40 pin haritasi + sicaklik formulu (T = 0.65 x kod - 351 C).
  Katalog, sematik, TICS Pro editoru, test bench etiketleri ve
  dokumantasyon guncellendi. Dogrulama: 139 test + gercek Versal BSP'ye
  karsi -Wall -Wextra -Werror sifir uyari derleme.

## v0.1.100 - 2026-07-04

Tek dosya girisi: .xsa'dan uctan uca akis - xparameters.h artik opsiyonel.

- Registers ekranina YAZMA: tablo artik manifest'ten her zaman cizilir
  (snapshot beklemez; Erisim sutunu eklendi), rw/wo satirlardaki kalemle
  hex deger girilir, onay sonrasi yazilir ve ayni register geri okunarak
  satir yerinde dogrulanir (wo registerlarda son yazilan deger gosterilir;
  ro satirlar kilitli). Snapshot wo registerlari atlar. Yazimlar Test
  Bench'teki gibi onay ister ve islem zaman cizelgesine islenir.
- SPI TICS parcalarina generic register R/W (LMK04832, LMX2820, LMX1204,
  ADAR1000): ajan 24-bit frame'i register modelinden paketler (yazma
  device_init ile ayni word formati; 15-bit adres cozucu, 8/16-bit veri).
  Okuma (readback) resmi datasheet'lerden dogrulanarak acildi ve
  donanim/konfigurasyon kosulu manifest'e "KOSUL:" olarak islenip UI'da
  "Okuma kosulu" kutusunda gosterilir:
  - LMK04832 (SNAS688C 8.5/8.6): adanmis SDO yok - veri 3-wire'da
    SDIO'da, 4-wire'da "SPI readback" secilen MUX pininde (or. RESET_MUX
    reg 0x14A[5:3]=6). Onceki "SPI_3WIRE_DIS=1 4-wire readback acar"
    yorumu duzeltildi: o bit yalniz SDIO cikisini kapatir.
  - LMX2820 (SNAS783C 7.3.6/6.6): MUXOUT (pin 23) adanmis readback
    cikisi, konfigurasyon gerekmez (bu parcada MUXOUT_LD_SEL yok; lock
    detect ayri LD pini). rb_* durum registerlari (R74/R76) haritaya
    eklendi.
  - LMX1204 (SNAS800B 5.7/Fig. 5-1): once MUXOUT_SEL=1 (R23/0x17 bit 6,
    reset 0=Lock Detect) yazilmali; R23 haritaya eklendi. Not: okunan
    deger dahili cihaz durumu olabilir.
  - ADAR1000 (Rev. B): 4-wire icin SDOACTIVE=1 (INTERFACE_CONFIG_A
    0x000 <- 0x18); 3-wire'da veri SDIO'da.
  16-bit LMX registerlari artik manifest'e girer (genislik filtresi
  transport'a duyarli: I2C 8-bit, SPI native data_bits). Demo semasina
  LMK04832 (XSpiPs) eklendi. Dogrulama: 139 test + tum katalog gercek
  BSP'ye karsi -Wall -Wextra -Werror sifir uyari (XSpiPs basliklari
  resmi Vitis surucu kaynagindan).
- YENI EKRAN: "Kilavuz" - uygulamaya gomulu Turkce kullanim kilavuzu
  (frontend/src/features/docs/DocsPanel.tsx). Saha el kitabi/datasheet
  estetigi: numarali 14 bolum (genel bakis, .xsa girisi, sematik,
  generate+QC, Vitis workspace, Board'da calistir, baglanti/transportlar,
  Test Bench + Akis, Bring-up, Registers, Headless CLI, platform destek
  matrisi, sorun giderme, kisayollar), SVG boru hatti ve transport
  diyagramlari (bus renkleriyle), ipucu/uyari kutulari, tablolar ve kod
  bloklari. Sol tarafta yapiskan icindekiler: baslik+anahtar kelime
  aramasi ve scrollspy (icindekilerden tiklayinca hedef kilitlenir,
  elle kaydirinca izleyici devralir; dipte son bolum aydinlanir).
  Komut paletine "Kullanim kilavuzu" girdisi eklendi.
- XSA parser (backend/parsers/xsa.py): XSA icindeki .hwh hardware
  handoff'u okunur. Islemci modullerinden platform otomatik algilanir
  (psu/ps7/psv cortex, microblaze). Board-level hwh'lerde PS tek blok
  oldugundan (zynq_ultra_ps_e / processing_system7) etkin cevre
  birimleri PSU__X__PERIPHERAL__ENABLE / PCW_X_PERIPHERAL_ENABLE
  parametrelerinden acilir ve mimari-sabit adreslerle listelenir;
  Versal CIPS'in psv_* modulleri dogrudan okunur. Instance adlari
  kanonik XPAR_* makro oneklerine birebir esledigi icin uretilen kod
  xparameters akisiyla ayni kalir. Bellek-esli tanninmayan IP'ler
  (custom PL IP adaylari) unmatched olarak raporlanir.
- API: POST /api/xsa/parse {path} (backend lokal oldugundan dogrudan
  yol) ve POST /api/xsa/upload (multipart; uploads/xsa altina kaydeder).
  Yanit xparameters/parse ile ayni sekil + platform + islemciler +
  xsa_path.
- UI (Setup): "Donanim tasarimi" karti iki modlu - varsayilan ".xsa
  (tek dosya)": dosya sec veya tam yol yapistir -> platform + hedef
  cekirdek otomatik secilir, sematik kurulur, XSA yolu Vitis workspace
  adimina otomatik tasinir (spec2code.xsaPath). xparameters.h sekmesi
  eskisi gibi durur.
- Dogrulama: 136/136 test (sentetik hwh + gercek vck190/zc702/zcu102
  parse'lari); tarayicida vck190.xsa yolundan tek adimda Versal ACAP +
  tam sematik kuruldu; sirket-sekilli custom-IP XSA'sinda 8 PS
  denetleyici + mem_pcie_intr unmatched dogrulandi. python-multipart
  bagimliligi eklendi.
- Generate sag kolonu duzeni: kod alani (dosya agaci + editor + QC
  bulgulari + diff) artik yalnizca "Uretilen kod" sekmesinde; "Vitis &
  Board" sekmesi sade (yalniz workspace + Board'da calistir kartlari).
- UART "Konsol" ekrani kaldirildi: protokol TX/RX'i "Akis" ekrani
  zaten gosteriyor, ham seri terminal ihtiyaci harici programla
  karsilaniyor. Komut paleti girdisi ve sekme kaldirildi; backend
  console API'lari yerinde (Akis ve dis araclar kullanabilir).
- YENI ENTEGRE: LTM4681 (quad 31.25A uModule, PMBus/I2C) - resmi Rev.A
  datasheet'ten dogrulanarak eklendi. Cift die mimarisi: bir modul =
  iki PMBus slave (Ch0/1 @ 0x4F, Ch2/3 @ 0x4E; ayri SDA/SCL ciftleri) -
  her die icin bir Spec2Code cihazi eklenir; die basina 2 PAGE (kanal
  secimi PAGE registerina register_write ile). Operasyonlar birimli:
  vout_read mV (Linear16, exp -12 sabit), voltage_read/current_read/
  power_read mV/mA/mW ve temperature_read santi-C (PMBus Linear11 -
  cmodel'e dinamik-uslu `pmbus_l11` donusumu eklendi, 64-bit ara deger).
  id_read MFR_SPECIAL_ID (0x500n beklenir; datasheet'teki 0x414n
  celiskisi nota islendi), status_read STATUS_WORD. Bayt registerlar
  (PAGE/OPERATION/STATUS_*/MFR_COMMON...) Registers ekraninda R/W;
  word komutlari genel 1-bayt register yolundan filtrelenir (manifest
  yalniz width=8 registerlari listeler). Katalog + etiketler + sematik
  descriptor listesi guncellendi. NOT: LTM4671 analog-only cikti
  (36 sayfada I2C/PMBus yok) - istek uzerine kapsam disi birakildi.
  Self-test uretecine PMBus word/int-out dallari (Id/Status/Current/
  Power) eklendi. Dogrulama: 138 test + gercek Versal BSP'ye karsi
  -Wall -Wextra -Werror sifir uyari.
- Birimli okumalar tum katalogda: AD7414 -> santi-C (10-bit D15..D6,
  0.25 C/LSB), TMP101 -> santi-C (12-bit D15..D4, 0.0625 C/LSB), SHT21
  -> santi-C ve santi-%RH (datasheet formulleri: T=-46.85+175.72*S/2^16,
  RH=-6+125*S/2^16; status bitleri maskelenir), LTC2945 sense -> uV
  (LSB 25 uV), VIN -> mV (LSB 25 mV), ADIN -> uV (LSB 0.5 mV; power
  bilincli raw: Rsense uygulama verisi), DS1682 elapsed/alarm -> saniye
  (0.25 s tik). convert altyapisina `rshift` (hizalama) ve `unsigned`
  (32-bit sayac, tasmasiz) eklendi. Tum donusumlu parcalar + ajan gercek
  Versal BSP'sine karsi -Wall -Wextra -Werror sifir uyari derlendi;
  137 test yesil. (uint32/int32 substring eslesme hatasi da duzeltildi.)
- LTC2991 okumalari artik muhendislik birimlerinde (2991f Table 10):
  voltage_read mV dondurur (LSB 305.18 uV; isaret/DV ayiklanir, negatif
  0'a kirpilir), vcc_read mV (2500 mV + kod x 305.18 uV),
  temperature_read isaretli santi-santigrat (0.01 C; 13-bit two's
  complement, LSB 0.0625 C) - donus tipi int32'ye gecti (dispatch 4
  byte big-endian tasir). current_read bilincli olarak raw kaldi:
  Vsense_uV = kod x 19.075, akim = Vsense/Rshunt hesabi pair'e ozgu
  shunt degeriyle uygulama tarafinda (aciklamalara islendi). Altyapi:
  descriptor'lara genel `convert` blogu (mask/signed_bits/scale/offset/
  clamp, tamsayi aritmetigi) - diger sensorlere de uygulanabilir.
  Dogrulama: yeni regresyon testi (donusum katsayilari + int32 dispatch
  + manifest), 137 test yesil; uretilen kod gercek zc702 BSP'sine karsi
  -Wall -Wextra -Werror sifir uyari derlendi.
- ?demo tohumu kanonik surucu adlarina gecirildi (XIicPs/XQspiPsu/...)
  - demo semasi artik gercek codegen'i uctan uca kosabiliyor (32 dosya,
  QC yesil); ayrica surucu kapisinin UI'da net hata gosterdigi teyit
  edildi.

## v0.1.99 - 2026-07-03

Kapsamli arayuz yenilemesi (3 faz): tek kart baglantisi, kalicilik,
header/palet/sekme duzeni.

- FAZ 1 - TEK KART BAGLANTISI: Test Bench, Konsol (UART), Bring-up,
  Registers ve telemetri artik TEK ortak session'i paylasir
  (BoardConnectionCard + baglanti profili store'u). Bir kez baglanmak
  yeter; seri port / CoreSight koprusu ikinci kez acilamadigi icin
  yasanan cakismalar bitti. Bring-up ve Registers boylece CORESIGHT
  destegi kazandi (onceden sessizce TCP'ye dusuyorlardi). Konsol ekrani
  CoreSight baglantisinda da calisir; TCP'de "konsol kanali yok" der.
  Agent log seviyesi secici ortak kartta. Header'da canli "kart
  bagli/kopuk" rozeti; komut paletine "Karta baglan / Baglantiyi kes"
  aksiyonlari eklendi.
- FAZ 2 - KALICILIK DUZELTMESI: proje, sema (zone/controller/mux/
  cihazlar) ve secimler artik tarayicida kalicidir (zustand persist) -
  sayfa yenilenince emek kaybolmaz; manifest cache'inin proje adiyla
  bulunamamasi sorunu da boylece cozuldu. Board hedef profili
  birlestirildi: SmartLynq adresi tek kanonik anahtarda (Run on Board
  ile ortak, eski anahtardan migrasyon), Vitis yolu tek kaynakta,
  CoreSight cekirdegi bos birakilirsa Setup'taki hedef cekirdekten
  otomatik turetilir (a53_1 secildiyse artik yanlis cekirdege
  baglanilmaz).
- FAZ 3 - DUZEN/CILA: header ikiye ayrildi - ust satir kimlik/adimlar/
  telemetri/Generate, alt satir goruntu sekmeleri (dar ekranda sarar,
  tasmaz) + baglanti rozeti. Ctrl+K paleti artik kesfedilebilir (header
  butonu). Generate ekraninin sag kolonu sekmelendi: "Uretilen kod" /
  "Vitis & Board". Kopya yardimcilar tek yerde (lib/console: zaman
  damgasi/ANSI temizleme/log indirme/session id; lib/board: islemci
  turetme) - TransactionTimeline'daki ms/saniye zaman tabani
  karisikligi giderildi. TR/EN karisik metinlerde ilk normalizasyon
  (SidePanel, XparametersUpload, GenerateConsole kabugu, ProjectSetup
  diyakritikleri).
- Dogrulama: frontend tsc + vite build temiz; backend testleri
  etkilenmedi (degisiklikler frontend'de).

## v0.1.98 - 2026-07-03

UX: ekranlar arasi durum korunumu (keep-alive), telemetri basliga
tasindi, Build & Run secimlerinin kalicilastirilmasi.

- KEEP-ALIVE EKRANLAR: Test Bench, UART konsolu, Veri Akisi, Bring-up,
  Registers, Bilgi, Katalog ve Import ekranlari ilk ziyaretten sonra
  sokulmez, yalnizca gizlenir. Sekme degistirip donunce baglanti, form
  alanlari, konsol/akis gecmisi ve secimler aynen kalir - Test Bench
  baglantisi Veri Akisi'na gidip donunce artik kopmaz (onceden ekran
  degisince bilesen sokuluyor ve cikista session kapatiliyordu).
- TELEMETRI BASLIKTA: "Canli telemetri" anahtari schematic ekranindan
  uygulama basligina tasindi - artik hangi ekranda olursaniz olun
  calismaya devam eder (degerler yine sematikteki cihaz node'larinda
  akar). Hata mesaji basligin altinda balon olarak gorunur.
- BUILD & RUN KALICILIK: elle secilen bitstream dosyasi yolu, PL
  bitstream secimi (auto/yes/no) ve JTAG baglanti tipi (USB/SmartLynq)
  artik tarayicida hatirlanir (SmartLynq adresi zaten hatirlaniyordu).
- Dogrulama: frontend tsc + vite build temiz; backend testleri
  etkilenmedi.

## v0.1.97 - 2026-07-03

Seviyeli calisma-zamani log altyapisi (agent tarafi) + host stabilite:
yanit zaman asimi artik baglantiyi dusurmuyor.

- LOG CEKIRDEGI: her generate ciktisina spec2code_testbench_log.h/.c
  girer. Seviyeler artan detayla: error(1) < warning(2) < message(3,
  gelen/giden S2C satirlari) < info(4) < debug(5). Bir print ancak
  seviyesi ayarli esikten KUCUK/ESITSE basilir; varsayilan warning.
  Cikti "S2C-LOG|E/W/M/I/D|..." satirlari - host yanit sanmaz, konsol
  ve Veri Akisi ekranlarinda gorunur. Sink agent transportuna baglanir:
  CoreSight'ta DCC'den, UART'ta seri hattan akar (lwIP'te stdout).
- RUNTIME SEVIYE DEGISIMI: global op `S2C|id=1|op=log_level|value=1..5`
  esigi degistirir, value'suz sorgu gecerli seviyeyi dondurur. Test
  Bench baglanti kutusunda "Agent log seviyesi" secici eklendi.
  Manifest'e `log` blogu (seviye haritasi + varsayilan) yazilir.
- ENSTRUMANTASYON: dispatch RX/TX satirlari (message), op basladi
  (info) + parametreler (debug), op sonucu ok=info / hata=error
  (status ve mesajla), parse hatasi (error), I2C register okuma/yazma
  adim adim (debug) ve bus hatalari status koduyla (error), board init
  controller bazli (debug/error) + tamamlaninca info ("device_init
  otomatik KOSULMAZ" hatirlatmasiyla), agent dongusu baslangici (info).
- HOST STABILITE: Test Bench'te komut zaman asimi artik oturumu
  "kopuk" isaretlemiyor; gercek durum backend'den sorulup ona gore
  gosteriliyor (uzun operasyonlar baglantiyi kaybettirmez, yeniden
  baglanma gerekmez). Onceki turda eklenen yanit-id eslestirmesiyle
  gec gelen yanitlar da sonraki komuta yapismaz.
- Dogrulama: 31/31 testbench testi - gcc round-trip artik log
  cekirdegini de derleyip esik davranisini (default'ta debug sessiz,
  error basilir; seviye 5'te debug acilir) ve uiHasValue'yu uctan uca
  dogruluyor; codegen testi enstrumantasyon noktalarini ve manifest log
  blogunu kontrol ediyor. Frontend tsc + vite build temiz.

## v0.1.96 - 2026-07-03

Kaynak guncelleme modu: mevcut Vitis workspace'inde yalnizca generated
kaynaklari degistirip app build alan hizli akis - yazilim-only
degisikliklerde (cihaz konfigurasyonu, yeni entegre, operasyon/register
guncellemesi) workspace'i sifirdan kurmadan ELF uretimi.

- BACKEND: VitisWorkspaceConfig.mode = "full" | "update". Update modunda
  XSA gerekmez; platform/BSP'ye dokunulmaz. Akis: app'in src/ altindaki
  Spec2Code staged konumlari (drivers/, tests/, reference_sources/,
  spec2code_selftest_main.*) temizlenir - onceki transport'un agent
  main'i gibi bayat dosyalar cift main() hatasi uretmesin - kullanicinin
  kendi ekledigi dosyalara dokunulmaz; yeni kaynaklar importsources ile
  alinir, include path'ler idempotent eklenir, yalnizca app build kosar
  (hatada bir kez clean+retry), ELF dogrulanir. Uygulama projesi
  workspace'te yoksa acik hata: once "Sifirdan kur".
- DURUSTLUK: yeni kaynaklar lwIP agent'i gerektiriyorsa uyari verilir ve
  build duserse "BSP'yi etkileyen degisiklik - sifirdan kurun" ipucu
  eklenir (lwIP BSP kutuphanesi update modunda eklenemez).
- UI (Vitis workspace karti): "Kurulum modu" secici - "Sifirdan kur"
  (mevcut davranis) / "Kaynaklari guncelle + build". Update modunda XSA
  alani gizlenir, buton adi degisir; secim hatirlanir.
- CLI: `--vitis-update` bayragi - `spec2code_cli.py build --spec ...
  --vitis ... --workspace ... --temp ... --vitis-update` XSA'siz
  kaynak guncelleme + build kosar.
- Dogrulama: 42/42 vitis workspace testi - update modu bayat agent
  dosyasini temizleyip kullanici dosyasini koruyor, script'te platform/
  domain create yok, XSA'siz ELF uretiyor; app projesi yoksa acik hata.
  Frontend tsc + vite build temiz.

## v0.1.95 - 2026-07-03

KRITIK DUZELTME: uretilen agent'in istek parser'i her komutu "request
parse failed" ile reddediyordu. Ayrica telemetri artik acik session'i
paylasiyor (CoreSight dahil) ve yanitlar komut id'siyle eslestiriliyor.

- PARSER (kok neden, sahada bulundu): spec2codeTestbenchRequestParse
  istek satirini yerel tampona TextCopy ile kopyaliyordu; bu yardimci
  ilk '|' ayracinda durdugu icin tampona yalnizca "S2C" kaliyor ve HER
  istek id=0 + "request parse failed" donuyordu. Tum transportlari
  (TCP/UART/CoreSight) etkileyen bu hata bugune kadar gorulmedi cunku
  onceki uctan uca kosumlar sahte (host-tarafi) agent'la yapilmisti.
  Yeni LineCopy yardimcisi ayraclari koruyarak yalnizca satir sonunda
  durur. Regresyon icin uretilen parser gercek bir C derleyicisiyle
  derlenip ayni isteklerle uctan uca test ediliyor (gcc varsa kosar).
- YANIT ID ESLESTIRME: seri/CoreSight send() artik yaniti komutun
  id'siyle eslestirir; paylasimli kanaldaki (konsol UART'i, ikinci
  jtagterminal istemcisi) yabanci yanitlar isteğe yapistirilmaz.
  Eslesen yanit gelmezse eldeki son yanit fallback olarak dondurulur
  (id=0 parse hatasi mesajlari kaybolmaz).
- TELEMETRI: "Canli telemetri" once acik bir testbench session'i
  varsa onu paylasir (seri port ve CoreSight koprusu ikinci kez
  acilamaz); yoksa kayitli transporta gore kendi baglantisini kurar -
  artik CoreSight ayarlarini da bilir (eskiden yalniz TCP/seri deneyip
  "connection refused" veriyordu). Odunc alinan session telemetri
  kapatilirken kapatilmaz.
- WINDOWS TEMIZLIK: xsdb koprusu CREATE_NO_WINDOW ile baslar ve
  kapatilirken surec agaci taskkill /T ile sonlandirilir (yetim
  jtagterminal/tclsh pencereleri kalmasin).
- Dogrulama: 30/30 testbench testi (gcc round-trip, id eslestirme,
  fallback dahil); frontend tsc + vite build temiz.

## v0.1.94 - 2026-07-03

CoreSight saha duzeltmeleri: paketli exe'de "invalid URL, protocol
'socket' not known" baglanti hatasi ve seri konsolda acilis banner'inin
gorunmemesi.

- KOPRU ARTIK PYSERIAL'SIZ: CoreSight oturumu jtagterminal'in TCP
  portuna pyserial'in socket:// URL isleyicisi yerine yerlesik bir
  soket akisiyla baglanir. PyInstaller pyserial'in dinamik URL
  isleyicisini paketlemedigi icin release exe'sinde baglanti
  "invalid URL, protocol 'socket' not known" ile dusuyordu - kok neden
  ortadan kalkti. Ayrica exe'ye serial.urlhandler.protocol_socket/loop
  hidden-import'lari eklendi (UART konsolunda elle socket:// URL
  kullananlar icin).
- SERI KONSOLDA ACILIS BANNER'I: CoreSight agent'inin main'i banner'i
  yalnizca DCC'ye basiyordu; seri konsol bos kaliyordu. Banner artik
  iki kanala da basilir - xil_printf ile stdout'a (UART) ve DCC'ye.
  BSP stdin/stdout ayarina dokunulmaz: printler UART'tan akmaya devam
  eder, yalnizca S2C protokolu CoreSight uzerindedir (UART banner'i
  bunu acikca soyler).
- Dogrulama: 27/27 testbench testi - coresight koprusu testi artik
  pyserial'siz gercek yoldan kosuyor; codegen testi banner'in iki
  kanala da basildigini dogruluyor.

## v0.1.93 - 2026-07-03

CoreSight (JTAG DCC) test bench transportu, Veri Akisi ekrani ve seri
konsol canlilik iyilestirmeleri.

- CORESIGHT TRANSPORTU (hedef taraf): `project.testbench_transport`
  secenegine "coresight" eklendi. ZynqMP'de psu_coresight_0 uzerinden
  ayni S2C satir protokolunu konusan polled DCC agent'i uretilir
  (tests/spec2code_testbench_coresight*.c/h, standalone BSP
  coresightps_dcc surucusu: XCoresightPs_DccSendByte/RecvByte).
  Ethernet PHY'si veya bos UART pini gerektirmez - yalnizca JTAG.
  Dürüst kapi: ZynqMP disinda acik CodegenError. auto asla coresight
  secmez (debug kablosu gerektirir). Manifest'e `coresight` blogu yazilir.
- CORESIGHT TRANSPORTU (host taraf): Test Bench baglanti paneline
  ucuncu secenek olarak CoreSight eklendi (Vitis yolu + opsiyonel
  SmartLynq/hw_server adresi + cekirdek). Backend xsdb'yi
  `jtagterminal -socket` ile calistirip DCC'yi lokal TCP portuna
  koprular; oturumun geri kalani mevcut seri altyapisini kullanir -
  UART konsolu, komutlar ve bring-up ayni sekilde calisir. SmartLynq
  uzerinden de dogrudan kullanilabilir (connect -url).
- VERI AKISI EKRANI (yeni "Akis" gorunumu + Ctrl+K): host ile agent
  arasindaki her satir yon (TX/RX) ve zaman damgasiyla canli izlenir -
  TCP, seri ve CoreSight session'larinin tumu icin. Session secici,
  duraklat/temizle/indir, TX/RX sayaclari, seri/CoreSight'ta ham satir
  gonderimi. API: POST /api/testbench/traffic, GET /api/testbench/sessions.
- SERI KANAL CANLILIK: uretilen agent'lar acilista surum/proje banner'i
  basar ("Spec2Code test bench vX | proje: ... | transport: ...").
  Enter'a (bos satir) "> " istemi doner - cakilma/takilma konsoldan
  anlasilir. CR tek basina da satir sonu sayilir (PuTTY Enter'i yalniz
  CR gonderir); CRLF cift istem uretmez. UART konsolu ve Veri Akisi
  ekranindan bos Enter gonderilebilir.
- Dogrulama: 124 testte 122 gecti (kalan 2'si ortamdaki libclang
  eksikligi, degisiklikten bagimsiz); yeni birim testleri: coresight
  codegen + platform kapisi, sahte jtagterminal soketiyle uctan uca
  coresight oturumu (banner + "> " istemi + trafik), TCP/seri trafik
  halkasi. Frontend tsc + vite build temiz.

## v0.1.92 - 2026-07-03

Elle bitstream secimi: XSA her zaman .bit icermez; Build & Run on Board
artik platformdan otomatik bulmanin yaninda elle secilen bir .bit
dosyasiyla da PL programlayabilir.

- Backend: `RunOnBoardConfig.bitstream_path` alani eklendi (bos =
  platform klasorunden otomatik bul, mevcut davranis). Dolu ise verilen
  .bit dogrudan kullanilir; dosya yoksa kosum acik hata ile durur.
  "Zorunlu yukle" + platformda bit yok hatasi artik elle secim ipucunu
  da verir. Olay akisi bit'in elle mi otomatik mi geldigini raporlar.
- UI (Board'da calistir karti): "Bitstream dosyasi (opsiyonel)" alani -
  yalnizca PL bitstream "Yukleme" degilken ve Versal disinda gorunur
  (Versal'da PL, PDI icindedir).
- Dogrulama: 22/22 run-on-board testi (elle secim, otomatik bulmayi
  ezme, eksik dosya hatasi dahil); frontend tsc + vite build temiz.

## v0.1.91 - 2026-07-03

SmartLynq / uzak hw_server destegi: Build & Run on Board artik lokal USB
JTAG kablosunun yaninda Ethernet uzerinden SmartLynq/SmartLynq+ (veya baska
bir uzak hw_server) ile de board'a yukleme yapabilir.

- Backend: `RunOnBoardConfig.hw_server_url` alani eklendi (bos = lokal USB
  JTAG). Adres `TCP:<host>:<port>` bicimine normalize edilir - kullanici
  `192.168.0.10`, `192.168.0.10:3121`, `TCP:...` veya `tcp://...`
  girebilir; port verilmezse hw_server varsayilani 3121 kullanilir. xsdb
  betigi bu durumda `connect` yerine `connect -url TCP:<host>:<port>`
  uretir; gecersiz adres API'de 400 ile reddedilir.
- Hata ipuclari baglanti tipine gore ozellesti: uzak baglantida
  "connection refused/timed out" SmartLynq IP/port kontrolune, "no
  targets" kablonun kartin JTAG konnektorune takili olmasina isaret eder.
  Is sonucu (`result.hw_server_url`) ve olay akisi kullanilan baglantiyi
  raporlar.
- UI (Board'da calistir karti): "JTAG baglantisi" secici (USB kablo lokal /
  SmartLynq Ethernet) ve SmartLynq adres alani eklendi; adres tarayicida
  hatirlanir (localStorage). SmartLynq seciliyken adres girilmeden kosum
  baslamaz; kart metni ve buton ikonu baglanti tipine uyar.
- Dogrulama: 19/19 run-on-board testi (URL normalizasyonu, xsdb betiginde
  `connect -url`, uzak baglanti hata ipucu ve is sonucu dahil); frontend
  tsc + vite build temiz.

## v0.1.90 - 2026-07-03

Platform genislemesi: Versal + MicroBlaze + Zynq-7000 dogrulamasi ve
durust platform kapilari. Tum dogrulamalar bu makinede, Vitis 2023.2
kurulumuyla gelen built-in fixed platformlar (vck190/zc702) ve Vivado
ile uretilen MicroBlaze tasarimi uzerinden uctan uca yapildi.

- VERSAL (VCK190 ile uctan uca dogrulandi): parser XUARTPSV'yi artik
  XUartPs'e yanlis eslemiyor; PSV_* kanonik adlari eklendi. UART test
  bench ajani surucu-parametrik oldu - Versal'da XUartPsv (xuartpsv.h)
  ile uretiliyor. vck190.xsa'dan psv_cortexa72_0 workspace kuruldu,
  versal_test_sw.elf uretildi; 8 uretilen kaynak gercek VCK190 BSP'sine
  karsi -Wall -Wextra -Werror sifir uyari derlendi. Build&Run on Board
  Versal'da PDI akisini kullanir (device program -> A72 -> dow -> con).
- MICROBLAZE (Vivado'da uretilen tasarimla dogrulandi):
  scripts/make_microblaze_xsa.tcl MB + BRAM + AXI UARTLITE/IIC/QSPI
  tasarimini sentezsiz XSA olarak uretir. UART ajanina XUartLite
  varyanti eklendi (tek cagrili init, donanimda sabit baud). XSA'dan
  microblaze_0 workspace kuruldu, mb_test_sw.elf uretildi (mb-objdump:
  elf32-microblazeel) - XUartLite ajani mb-gcc ile gercek BSP'de
  derlendi.
- ZYNQ-7000 (zc702 ile uctan uca dogrulandi): a9_N -> ps7_cortexa9_N
  islemci eslemesi (backend + frontend); Build&Run 7000'de ps7_init +
  ps7_post_config akisini kullanir; I2C cihazlari + XUartPs ajani zc702
  BSP'siyle dogrulandi.
- DURUST KAPILAR: cmodel, destek disi suruculere (AXI XIic/XSpi,
  XQspiPs, XOspiPsv) bagli cihazlarda derlenemeyecek kod uretmek yerine
  acik CodegenError verir. Setup ekraninda platforma gore dogrulanmis/
  sinirli destek notu gosterilir. XCANFD/XOSPIPSV parser'da taninir.
- Ayrica: custom IP make.libs watcher'i BSP regen sirasinda kaybolan
  dizinlere dayanikli (Windows rglob yarisi).

## v0.1.89 - 2026-07-02

Faz 5: Headless CLI, Ctrl+K komut paleti ve islem zaman cizelgesi.

- Headless CLI (`spec2code_cli.py`): UI'siz tam boru hatti -
  `python spec2code_cli.py build --spec my.spec.json` spec'i dogrular,
  kodu uretir, QC kosar; `--vitis/--xsa/--workspace/--temp` verilirse
  ayni kosuda Vitis workspace kurup ELF dogrular. Cikis kodlari: 0 ok,
  2 spec gecersiz, 3 codegen/QC, 4 Vitis. `--json` makine-okur ozet
  basar; CI/gece kosulari icin uygundur.
- Ctrl+K (Cmd+K) komut paleti: ekranlar arasi gecis ve "Generate
  calistir" aksiyonu; ok tuslari + Enter, bulanik arama, bakir temali.
- Islem zaman cizelgesi (Test Bench alti): host'tan gonderilen her S2C
  komutu (Test Bench, canli telemetri, register snapshot) son-60-sn
  seridinde isaretlenir ve son 10 islem sure/durumla listelenir.
- Duzeltme: Vitis staging'de selftest main artik UART agent main'i
  varken de bastirilir (cift main() link hatasi onlendi) - onceden
  yalnizca lwIP main'e bakiliyordu.
- Dogrulama: 99/99 test (CLI build gercek codegen+QC kosuyor); palet ve
  zaman cizelgesi gercek backend + sahte agent ile tarayicida dogrulandi.

## v0.1.88 - 2026-07-02

Faz 4: Register snapshot & diff isi haritasi + sematikte canli telemetri.

- Register snapshot: `POST /api/registers/snapshot` canli session uzerinden
  cihazin tum register haritasini okur (register basina bir S2C
  register_read). Yeni "Registers" ekrani: cihaz sec, snapshot al,
  bit-bit isi haritasi - okunan/beklenen farkli bitler kirmizi yanar,
  bit uzerine gelince descriptor'daki alan adi/aciklamasi gorunur
  (datasheet bilgi paketi). Karsilastirma tabani: datasheet reset
  degerleri veya onceki snapshot'lar (cihaz basina son 8 snapshot
  tarayicida saklanir). Kopan baglantida kalan registerlar "atlandi".
- Canli telemetri overlay: Schematic ekranindaki "Canli telemetri"
  anahtari kayitli test bench baglanti ayarlariyla kendi session'ini
  acar ve her cihazi 3 sn'de bir en uygun guvenli operasyonla yoklar
  (sicaklik > lock > vcc/voltaj > id). Son okuma, cihaz cip node'unun
  altinda fosfor yesili canli deger cipi olarak akar.
- Dogrulama: 95/95 test; gercek backend + sahte agent ile tarayicida
  uctan uca (4/4 register okundu, 0xA8 farki bit 7/5/3 kirmizi; telemetri
  ciplerinde 0x19C8 / JEDEC 20BB22 canli akti).

## v0.1.87 - 2026-07-02

Faz 3: Bring-up sihirbazi (Mission Control) ve board birth certificate.

- Bring-up plani test bench manifest'inden bagimlilik sirasiyla kurulur:
  guc/izleme -> sensorler -> saat agaci -> bellekler -> RF -> diger
  (backend/bringup.py `build_plan`). Cihaz basina once opsiyonel
  `device_init`, sonra guvenli okuma operasyonlari (id/status/lock
  oncelikli); elle adres/veri isteyen operasyonlar gozetimsiz plana
  alinmaz. Hata bir adimi durdurmaz - sertifika tam resmi ister; yalnizca
  baglanti koptugunda kalan adimlar "atlandi" olarak isaretlenir.
- Yurutme mevcut TCP/seri test bench session'i uzerinden adim adim S2C
  komutlariyla yapilir; canli akis ws://.../ws/bringup/{id}. API:
  `POST /api/bringup/start`, `GET /api/bringup/{id}/result`,
  `GET /api/bringup/{id}/certificate`.
- Mission Control ekrani (Bring-up butonu): TCP/seri baglanti, tek tusla
  kosum, kategori bazli "stage light" panolari (bekliyor/calisiyor/gecti/
  hata LED'leri), adim degerleri (orn. JEDEC ID, lock bitleri) satirda
  gosterilir; sonunda gecti/kaldi ozeti.
- Board birth certificate: tek dosyalik, yazdirilabilir HTML raporu -
  proje, tarih, agent surumu/transport, kategori gruplu adim tablosu,
  GECTI/KOSULLU damgasi. Indirme başligiyla servis edilir.
- Dogrulama: 93/93 test (plan kurucu + sahte seri oturumla kosum +
  sertifika iceriği); ayrica gercek backend + sahte TCP agent ile
  tarayicida uctan uca kosuldu (8/8 adim yesil, sertifika indirilebilir;
  seri yol socket:// pyserial URL'i ile ayni ajanla dogrulandi).

## v0.1.86 - 2026-07-02

Faz 2: UART test bench transportu, JTAG ile board'a yukleme (Build & Run)
ve UART konsolu.

- UART test bench agent'i (hedef taraf): `project.testbench_transport`
  secenegi eklendi (`auto` | `eth` | `uart`; varsayilan auto = ETH varsa
  lwIP TCP, yoksa PS UART). UART secildiginde ayni S2C satir protokolunu
  XUartPs uzerinden konusan polled agent uretilir
  (tests/spec2code_testbench_uart*.c/h): resmi xuartps polled ornegi
  kalibi, kesme/scheduler gerektirmez, bare-metal ve FreeRTOS BSP'de ayni
  calisir. "S2C|" ile baslamayan satirlar yok sayilir - agent konsol
  UART'ini xil_printf ciktisiyla paylasabilir. Gercek ZynqMP BSP'sine
  karsi -Wall -Wextra -Werror ile sifir uyari dogrulandi. Manifest'e
  `transport_agent` ve `uart` alanlari eklendi.
- Host tarafi seri (COM) istemcisi: pyserial tabanli kalici seri session
  (backend/testbench.py `_TestbenchSerialSession`); okuyucu thread gelen
  her satiri zaman damgali konsol ring'ine yazar, "S2C|...|ok=..."
  yanitlarini komut kuyruguna ayirir - konsol gurultusu komutlari bozmaz.
  Yeni API'ler: `GET /api/testbench/serial/ports` (COM listesi),
  `POST /api/testbench/console/read` ve `/write`. Test Bench ekranina
  TCP/Seri transport secici eklendi. `loop://` gibi pyserial URL'leri
  donanimsiz duman testi icin destekleniyor.
- Build & Run on Board: `POST /api/vitis/run-on-board` xsdb ile klasik
  ZynqMP JTAG akisini kosar (sistem reset -> psu_init -> bitstream
  [varsa] -> ELF indir -> calistir; Vitis "Run on hardware" sirasi).
  Canli log ws://.../ws/runboard/{id} uzerinden akar; "no targets" gibi
  yaygin hatalara Turkce ipucu eslenir. Vitis workspace panelinin altina
  "Board'da calistir" karti eklendi (PL bitstream: auto/zorla/yukleme).
- UART konsolu ekrani: COM port + baud secimiyle baglan, karttan gelen
  her satir zaman damgasiyla akar (S2C satirlari turuncu, hata satirlari
  kirmizi vurgulanir), satir gonderme, temizle/log indir/oto-kaydir.
- pyserial bagimliligi requirements.txt'e eklendi. Spec semasi
  `project.testbench_transport` alanini taniyor. Test suite 79 -> 90
  (UART codegen, seri session, run-on-board fake-xsdb testleri).

## v0.1.85 - 2026-07-02

Gorsel yenileme Faz 1: PCB tasarim dili ve sematik glow-up.

- Yeni tasarim paleti: grafit substrat + bakir (copper) vurgu rengi, fosfor
  yesili saglik LED'i, amber uyari. Tum tema token'lari
  `frontend/src/theme/tokens.css`'te yeniden duzenlendi.
- Kanonik bus renk dili: her transport tek renk tasir (I2C amber, SPI cyan,
  QSPI mor, ETH yesil, UART turuncu, CAN pembe, SDIO/GPIO notr) ve uygulama
  genelinde tek kaynaktan gelir (`src/lib/busColors.ts`). Sematikteki
  kablolar, node rozetleri ve baglanti noktalari (handle) ayni rengi
  paylasir.
- Sematik cizim dili: cihaz ve mux node'lari artik entegre paketi gibi
  cizilir - cip govdesi, kenar pin pad'leri, pin-1 noktasi, silkscreen
  tipografisi (JetBrains Mono, genis harf araligi). Descriptor durumu
  parlayan LED ile gosterilir. Kablolar dik acili (smoothstep) PCB izi
  olarak yonlendirilir; secili kablo "yuruyen karinca" animasyonu ve ayni
  renkte glow alir. Secili node bakir cerceve + halo ile vurgulanir.
- Detay seviyesi (LOD): zoom 0.55 altina inince node'lar ikincil detaylari
  gizleyip yalnizca parca adini buyuk gosterir; uzaktan bakista kart
  okunabilir kalir.
- MiniMap eklendi (cip renkleriyle stillendirilmis, pan/zoom destekli).
- Fontlar artik pakete gomulu: Inter (variable) ve JetBrains Mono woff2
  olarak `frontend/public/fonts/` altinda, OFL lisanslariyla birlikte.
  Google Fonts CDN linkleri kaldirildi - hava bosluklu (air-gapped)
  makinelerde tipografi artik ayni gorunur.
- Gelistirici onizlemesi: `?demo` URL parametresi backend'siz temsili bir
  sema yukler (2xI2C + mux fan-out + QSPI flash + GEM); gorsel regresyon
  kontrolu icin.

## v0.1.84 - 2026-07-02

Kalite denetimi surumu: 14 destekli entegrenin tamami icin uretilen kod
gercek ZynqMP BSP'sine karsi derlenerek (aarch64-none-elf-gcc, -Wall
-Wextra, iki controller varyanti) dogrulandi; lwIP test katmani resmi
Xilinx orneklerine gore duzeltildi; descriptor register haritalari resmi
datasheet'lerle teyit edildi.

- LTC2991 device_init duzeltildi (datasheet 2991f Table 2/7, s.14): yazma
  sirasi artik CONTROL_V1V4 -> CONTROL_V5V8 -> PWM_T_INTERNAL_CONTROL
  (0x10, Repeated Acquisition) -> STATUS_HIGH. Onceden 0x01 enable/trigger
  ILK yaziliyordu ve tekrar modu hic acilmadigi icin poll-oku operasyonlari
  ilk donusumden sonra BAYAT veri donduruyordu. UI init onizlemesi de ayni
  sirayi gosterir. 0x08 bit haritasi duzeltildi: b4 REPEATED_ACQUISITION
  (eski yanlis ad PWM_MODE), b3 T_INTERNAL_FILTER_ENABLE, b2
  T_INTERNAL_KELVIN (eskiden b3 sanilan).
- FreeRTOS + lwIP test bench agent'i resmi
  `freertos_lwip_echo_server` yapisina gecirildi: main ->
  sys_thread_new + vTaskStartScheduler; lwip_init bir thread icinde
  (Xilinx portu OS modunda tcpip_init'i da calistirir - init.c'de
  dogrulandi); xemac_add + xemacif_input_thread network thread'inde; agent
  SOCKET API (lwip_socket/bind/listen/accept + lwip_recv/lwip_send) ile
  ayri thread'de. Onceki uretim FreeRTOS'ta scheduler'i hic baslatmayan
  RAW API + polling kaliba sahipti ve SOCKET_API BSP'siyle calisamazdi.
  bare_metal/standalone uretimi resmi `lwip_echo_server` RAW kalibinda
  degismeden kaldi. Iki flavor da gercek BSP'ye karsi sifir uyariyla
  derlendi; FreeRTOS flavor'i Vitis'te uctan uca ELF'e goturuldu.
- XQspiPsu_LookupConfig cagrilari klasik (non-SDT) 2023.x BSP imzasina
  cevrildi: `(UINTPTR)XPAR_..._BASEADDR` yerine `XPAR_..._DEVICE_ID`.
  Eski cagri u16'ya kirpilip yalnizca QSPI-0'da sans eseri calisiyordu;
  QC bsp stub'i da ayni yanlis imzayi tasidigi icin hatayi gizliyordu
  (stub duzeltildi).
- Kullanilmayan statik yardimcilar artik uretilmiyor: istenen operasyon
  seti bir low-level helper'i (ornegin `<part>RegisterWrite`,
  `ltc2991RegistersRead`) cagirmiyorsa dosyaya yazilmaz; -Wall'da
  -Wunused-function gurultusu sifirlandi.
- Datasheet teyitleri (resmi kaynaklar; ADI/TI/Micron/Microchip/Sensirion):
  TCA9548A, TMP101, LMX1204, LTC2945, 24LC32A, SHT21 birebir dogru cikti.
  Duzeltilenler: LMK04832 0x000 reset 0x10->0x00 (SNAS688C Table 6);
  LMX2820 R0 reset 0x251C->0x4070 (SNAU251A 1.1; repo'nun kendi knowledge
  paketi zaten 0x4070 diyordu); ADAR1000 DEV_CONFIG reset 0x00->0x10
  (Rev. A Table 23); AD7414 config bit adlari FLTR_ENABLE/ALERT_DISABLE
  olarak duzeltildi (Table VII ters mantik); DS1682 ETC/EVENT registerlari
  WDF kilidine kadar yazilabilir (ro->rw); MT25Q FAST_READ komutlarina
  8 dummy cycle notu eklendi (uretilen operasyonlar zaten 0-dummy READ
  kullanir); SHT21 raw frame aciklamalarina status-bit maskesi ve donusum
  formulleri eklendi.
- Olu kod temizligi: hicbir yerden referans almayan
  `hostplat.io.detect_line_ending` ve `cmodel._doxy` kaldirildi.

## v0.1.83 - 2026-07-02

- Application ELF uretilmis, exit code 0 ve compiler/make/linker hatasi yoksa
  workspace artik basarili sayilir. Onceden Tcl akisinin yakalayip kurtardigi
  hsi probe'lari bile (ornegin BSP'de olmayan bir instance icin `bsp
  setdriver` denemesinin stderr'e bastigi `ERROR: [Hsi 55-1464] Hardware
  instance ... not found in the design`) `^ERROR:` imzasina takilip ELF'e
  ragmen job'u `S2C-VITIS-XSA-PLATFORM-005` ile basarisiz gosteriyordu. Bu
  satirlar artik Vitis Doctor'da `recovered` olarak raporlanir; gercek
  hatalar (nonzero exit, compiler/make/linker fatal, ELF yoklugu) davranisi
  degismedi.
- `bsp setdriver -driver none` denemeleri artik `bsp getdrivers` listesinde
  olan instance'larla sinirli; BSP'de karsiligi olmayan adaylar (PHY/stream
  IP'leri, smartconnect ic dugumleri) icin hsi ERROR spami olusmaz.
- Custom aday listesi gurultusu azaltildi: `jesd204*`, `sc_node` ve `xdma`
  standart Xilinx ailesi olarak tanınir. XSA'ya gomulu driver'i olan IP'ler
  bu listeden bagimsiz olarak aday kalmaya devam eder.

## v0.1.82 - 2026-07-02

- Custom PL IP korumasi iki bosluga karsi genisletildi (airgap sahadaki
  `[Hsi 55-1562] Source directory ... drivers\<ip>_v1_0/src does not exist`
  ciktisiyla dogrulandi):
  1. XSA'ya gomulu driver'da `src/` klasoru hic yoksa (yalniz `data/` ile
     paketlenmis sirket IP'leri) staged XSA'ya artik no-op `src/Makefile` ve
     `src/make.libs` EKLENIR; hsi hatasi kaybolur ve BSP kopyalari no-op
     derlenir. Onceden neutralize yalnizca var olan dosyalari degistirdigi
     icin bu durumda hic devreye girmiyordu.
  2. Neutralize ve aday tespiti artik hwh VLNV sezgilerinden bagimsiz olarak
     "XSA icinde gomulu non-Xilinx driver" sinyalini kullanir. Boylece
     `axi_mem_space` gibi `axi_*` onekiyle standart Xilinx ailesine benzeyen
     ve/veya `xilinx.com:ip:` VLNV ile paketlenmis sirket IP'leri de yakalanir;
     gomulu tum non-Xilinx driver'lar auto_none altinda etkisizlestirilir.
- Bu senaryo lokalde, driver'i yalniz `data/` iceren (src'siz) gercek bir
  custom-IP XSA'siyla uctan uca dogrulandi: `Hsi 55-1562` yok, `*.c Invalid
  argument` yok, application ELF uretildi.

## v0.1.81 - 2026-07-02

- Secilen port (varsayilan 8077) doluysa uygulama artik `[WinError 10048]`
  bind hatasiyla kapanmak yerine sonraki bos portu secip acilir. Tipik neden
  arka planda acik kalmis eski bir Spec2Code instance'idir; konsola hangi
  porta gecildigi ve eski instance'in nasil kapatilacagi
  (`netstat -ano | findstr :8077` + `taskkill /PID <pid> /F`) yazilir.
  Taryici da dogru (yeni) portta acilir.

## v0.1.80 - 2026-07-02

- Custom PL IP kesfi gercek Vivado `.hwh` formatiyla duzeltildi. Gercek
  dosyalarda modul turu `IPTYPE`/`MODCLASS` attribute'unda, `MODTYPE` ise IP
  adinda tasinir; eski dedektor `MODTYPE == "PERIPHERAL"` bekledigi icin
  gercek bir exported XSA'da hicbir custom IP adayi bulamiyordu ve tum custom
  IP korumasi yalnizca build-log tabanli self-heal'e kaliyordu. Iki format da
  desteklenir; regresyon testi gercek format ile eklendi.
- `auto_none` policy'de staged XSA icindeki custom PL IP driver'inin build
  recetesi (`drivers/<ip>_vX_Y/src/Makefile` ve varsa `make.libs`) XSCT
  calismadan once no-op ile degistirilir. `bsp setdriver none` yalnizca
  application domain BSP'sini kapsiyor; FSBL ve PMUFW BSP'leri gomulu driver'i
  her uretimde yeniden derliyor ve source'suz driver deterministik olarak
  `cc1.exe: fatal error: *.c: Invalid argument` + `cannot find -lxilffs` /
  `-lxilfpga` zinciriyle platformu kiriyordu (workspace watcher patch'i bu
  yarisi bazen kaybediyordu). Driver klasorunu tamamen silmek hsi'yi kirdigi
  icin (`Repository Directory ... doesn't exist`) recete no-op'lanir; repo
  yapisi bozulmaz, tum BSP kopyalari no-op derlenir. Kullanicinin orijinal
  `.xsa` dosyasina dokunulmaz; etkisizlestirilen driver klasorleri is
  sonucunda raporlanir. Bu senaryo lokalde Vivado ile uretilen gercek bir
  custom-IP XSA'si (kaynaksiz driver) ile uctan uca dogrulandi.
- Vitis workspace testlerindeki sahte `xsct` scriptleri tek Python
  implementasyonuna tasindi ve Windows'ta `.bat` sarmalayici ile calisiyor;
  onceden POSIX shell scriptleri oldugu icin bu testler Windows'ta hic
  kosamiyordu. Tum suite artik Windows'ta da yesil (70 test).

## v0.1.79 - 2026-07-02

- Test bench codegen artik yalnizca tasarimda gercekten kullanilan controller
  tiplerinin BSP header'larini include eder. Onceden `*_testbench_ops.h` her
  zaman `xiicps.h`, `xspips.h` ve `xqspipsu.h` include ediyordu; PS SPI kapali
  bir XSA'da (ornegin ZCU102 + I2C + QSPI senaryosu) BSP'de `xspips.h`
  uretilmedigi icin application build `fatal error: xspips.h: No such file or
  directory` ile dusuyor ve application ELF hic uretilemiyordu. Getter
  prototipleri, weak getter'lar ve lwIP agent getter tanimlari da ayni sekilde
  kosullu uretilir.
- Vitis XSCT calistirmasi artik stdout/stderr'i log dosyalarina canli olarak
  yazar; timeout veya kill durumunda bile kismi loglar `logs/` altinda kalir.
  XSCT stdin'i kapali (NUL) baglanir.
- XSCT hicbir cikti uretmeden takilirsa Spec2Code watchdog once bilinen stuck
  probe child'lari (Vitis 2023.2 `app create` sirasindaki `which sdscc`)
  sonlandirmayi dener, duzelmezse process tree'yi kill edip `S2C-VITIS-HANG-010`
  hata koduyla aksiyon alinabilir bir mesaj gosterir. Onceden bu durum sonsuz
  bekleme + log kaybi demekti.
- Timeout durumunda process tree (`cmd -> xsct -> eclipse`) artik komple kill
  edilir; yetim kalan Vitis cmdline service'in sonraki denemeleri kilitlemesi
  engellenir.
- Generated Tcl script'lerine `fconfigure stdout -buffering line` eklendi;
  progress marker'lari log'a gecikmeden yazilir ve stall tespiti guvenilir
  calisir.
- Platform senkronizasyonu Vitis 2023.2 ile uyumlu hale getirildi: `platform
  build` bu surumde `Wrong sub-command` hatasi veriyordu; artik once `platform
  generate` denenir, desteklenmiyorsa `platform build`'e dusulur.
- `app create` sessizce basarisiz olursa (tipik neden: onceki basarisiz
  denemeden kalinti iceren workspace dizini) akis artik `importsources`/`app
  build`e devam etmez; `app list` dogrulamasi yapilir ve
  `S2C-VITIS-WORKSPACE-011` koduyla acik bir hata verilir. `The project given
  does not exist in workspace` hatasi da ayni koda maplenir; onerilen cozum bos
  bir workspace dizinidir.
- `scripts/vitis_which_stub.c` eklendi: `which sdscc` hang'i goruen makineler
  icin konsol acmayan `which` stub'inin kaynagi ve build komutu (bkz.
  `kimi_vitis_debug_guide.md` bolum 7).
- Application projesine `importsources` sonrasi staged header klasorleri
  (`drivers/`, `tests/`, varsa digerleri) `app config -add include-path` ile
  eklenir. CDT app build varsayilan olarak yalnizca BSP include path'ini
  verdigi icin `tests/ltc2991_test.c` gibi dosyalar `drivers/ltc2991.h`'i
  bulamiyor ve application build ELF uretmeden dusuyordu; bu, ZCU102
  senaryosunda missing application ELF'in ana nedenlerinden biriydi.
- `app build` bazen platform bagimliliklarini derleyip application make
  adimini sessizce atlayabiliyor (exit 0, log'da hata yok, ELF yok). Script
  artik build sonrasi beklenen ELF'i dogrular; yoksa `Debug` klasorunde
  make'i dogrudan calistirir, o da ELF uretmezse acik hata verir.
- Backend yeniden basladiginda Vitis job sayaci sifirlandigi icin yeni job
  eski `vitis_0001` staging klasorunu ezebiliyordu; staging dizini artik
  mevcutsa `vitis_0001_2` gibi benzersiz bir klasore yazilir (eski loglar
  debug kaniti olarak korunur).
- XSCT fatal-log dedektoru artik case-sensitive ve satir bazli calisir.
  Onceden `Error: Library "lwip220", not available` (beklenen lwIP fallback
  cizgisi) ve `xil_exception.o` gibi BSP obje listeleri `^ERROR:`/`exception`
  desenlerine takilip her basarili ZynqMP build'ini bile `failed` olarak
  isaretliyordu. Gercek `ERROR: [...]`, Tcl `invalid command name` /
  `while executing` ve compiler/make imzalari fatal olmaya devam eder.

## v0.1.78 - 2026-07-01

- Vitis workspace Tcl akisi `importsources` sonrasi application build'e gecmeden
  once `bsp regenerate` ve `platform build` ile platform/domain senkronizasyonu
  dener. Bu, Vitis 2023.2 + FreeRTOS/lwIP akisinda app build'in sessizce erken
  atlanmasi riskini azaltir.
- XSCT hata ile donse bile application ELF bulunamazsa `S2C-VITIS-ELF-009`
  artik aktif issue listesine eklenir; FSBL/PMU ELF uretimi workspace hazir gibi
  yorumlanmaz.
- `aarch64-none-elf-ar: creating ../../lib/libfreertos.a` gibi normal FreeRTOS
  BSP archive satirlari tek basina root cause gibi gosterilmez.
- `kimi_vitis_debug_guide.md` icine mevcut Windows debug dizinleri icin hazir
  komutlar eklendi: `D:\Projects\claude\Spec2Code\0_temp` ve
  `D:\Projects\claude\Spec2Code\0_workspace`.

## v0.1.77 - 2026-07-01

- `kimi_vitis_debug_guide.md` icine ZCU102/custom IP yok/application ELF yok
  senaryosu icin hedefli debug bolumu eklendi.
- Kimi'ye dogrudan verilecek prompt, gerekli `dir`/`findstr` komutlari ve
  `aarch64-none-elf-ar: creating ../../lib/libfreertos.a` satirinin nasil
  yorumlanacagi dokumante edildi.
- Source kod istemeden once application project, source import, app build logu ve
  ELF listesi uzerinden debug edilmesi gereken kanit akisi netlestirildi.

## v0.1.76 - 2026-07-01

- Release paketlerine `kimi_vitis_debug_guide.md` eklendi.
- Bu dokuman lokal Kimi/Qwen gibi airgap LLM'lere source koddan once verilecek
  Vitis debug brief'ini, gerekli log/Tcl dosyalarini, fatal imza listesini ve
  beklenen analiz cikti formatini tanimlar.
- Executable release zip'leri artik `Spec2Code`, `changelog.md`, `userguide.md`
  ve `kimi_vitis_debug_guide.md` icerir.

## v0.1.75 - 2026-07-01

- Vitis self-heal basari kontrolu sertlestirildi: XSCT `exit 0` donse bile log icinde `cc1.exe fatal error`, `make: ***`, `Failed to build`, `compilation terminated` veya linker fatal imzasi varsa build basarisiz sayilir.
- Recovery stderr logunda `mem_pcie_intr_v1_0/src/make.libs` gibi custom IP build hatasi kalirsa artik `self-heal gecti` olarak isaretlenmez.
- Recovery build basarisizsa hata mesaji artik ilk deneme logu yerine aktif recovery stderr log path'ini isaret eder.

## v0.1.74 - 2026-07-01

- Vitis Doctor aktif hata kodlari ile self-heal tarafindan kapanmis hata kodlarini ayirdi.
- Custom IP `make.libs` hatasi recovery build ile kapanmissa artik kirmizi aktif hata gibi degil, `kapandi S2C-VITIS-CUSTOM-IP-MAKELIBS-001` olarak gosterilir.
- Application ELF yoksa aktif hata listesinde yalnizca `S2C-VITIS-ELF-009` kalir; boylece `xsct_stderr.log` icindeki ilk deneme hatalari ile son blokaj birbirine karismaz.

## v0.1.73 - 2026-07-01

- Vitis workspace akisi artik XSCT/app build basarili donse bile application ELF dosyasini ayrica dogrular.
- Application adiyla eslesen `.elf` bulunamazsa workspace `hazir` sayilmaz ve `S2C-VITIS-ELF-009` hata kodu gosterilir.
- Vitis Doctor ve workspace sonucunda bulunan ELF sayisi, application ELF sayisi, beklenen ELF adi ve bulunan ELF path ornekleri gosterilir.
- lwIP test bench main'i yoksa Vitis staging icindeki `spec2code_selftest_main.c` artik default `main()` entry point uretir.
- Bu degisiklik `BSP patch` basarili gorunmesine ragmen `Debug` altinda ELF bulunamayan durumlari acik ve aksiyon alinabilir hale getirir.

## v0.1.72 - 2026-07-01

- Vitis Doctor artik build log icindeki `psu_cortexa53_0/libsrc/<driver>/src/make.libs` hedeflerini ayrica cikarir ve UI'da `Log make.libs hedefleri` olarak gosterir.
- Custom IP self-heal, Vitis log'u `make.libs` hedefi gosterdigi halde workspace/temp taramasinda fiziksel dosya bulamazsa ilgili processor BSP koku altinda sentetik no-op `make.libs` olusturup recovery build'i dener.
- Bu fallback, `Workspace BSP make.libs=0` gorunurken log'da `mem_pcie_intr_v1_0/src/make.libs` hatasi bulunan airgap Windows senaryosunu daha dogru handle eder.
- Self-heal sonucunda normal patchlenen ve sentetik olusturulan `make.libs` path'leri UI'da ayrilastirildi.

## v0.1.71 - 2026-06-30

- Vitis workspace paneline lokal `Vitis Doctor` tanisi eklendi; custom IP adaylari, XSA/workspace `make.libs` sayilari, riskli source'suz driver durumu, hata kodlari ve self-heal sonucu UI icinde gosterilir.
- Airgap kullanimi icin Doctor bilgisi otomatik disari aktarilmaz; kullanici sadece `S2C-VITIS-...` hata kodlarini veya soyut sayilari paylasarak debug surecini ilerletebilir.
- Custom IP BSP `*.c Invalid argument` hatasi gorulurse Spec2Code workspace/temp altini tekrar patchleyip mevcut workspace uzerinden recovery Tcl ile `bsp regenerate` ve `app build` denemesi yapar.
- Release paketi yine yalnizca `Spec2Code.exe`, `changelog.md` ve `userguide.md` icerir.

## v0.1.70 - 2026-06-30

- Vitis custom IP kesfi genisletildi: `xilinx.com:ip:<custom_ad>:...` seklinde gorunen ama standart Xilinx IP ailesine benzemeyen PL peripheral'lar da `Auto: custom IP - none` kapsamına alinir.
- `axi_gpio`, `clk_wiz`, `xlconcat`, `smartconnect`, `proc_sys_reset` gibi standart Xilinx IP aileleri otomatik none politikasindan korunur.
- Custom IP BSP watcher daha hizli calisir ve artik kullanicinin verdigi `Temp/Staging` kok dizinini de izler; Vitis'in ara klasoru farkli yerde acmasi durumunda `make.libs` patch sansi artar.

## v0.1.69 - 2026-06-30

- Vitis workspace akisi staged `.xsa` icindeki source'suz custom IP driver `make.libs` dosyalarini Vitis platform/FSBL/PMU BSP uretimi baslamadan once patchler.
- Runtime watcher'a ek olarak XSA pre-patch sonucu manifest/result icine yazilir; UI'da `XSA:` ve `BSP:` kaynakli patch path'leri ayri gosterilir.
- Vitis panelindeki `BSP patch` rozeti artik patch sayisi `0` olsa bile gorunur; bu sayede watcher/pre-patch katmaninin hic dosya yakalayip yakalamadigi net okunur.

## v0.1.68 - 2026-06-30

- Vitis workspace akisi, XSCT calisirken host tarafinda paralel bir custom IP BSP watcher baslatir.
- Watcher workspace altindaki application, FSBL ve PMU/PMUFW dahil tum BSP `libsrc/*/src/make.libs` dosyalarini izler; source'suz custom IP `*.c` makefile'lari olusur olusmaz no-op hale getirir.
- `.hwh` custom IP eslesmesi hic yapilamasa bile source'suz ve `*.c` wildcard'li non-Xilinx BSP driver klasorleri patchlenir.
- Vitis workspace UI/result artik kac adet custom IP BSP `make.libs` dosyasinin patchlendigini ve ilgili path'leri gosterir.

## v0.1.67 - 2026-06-30

- Vitis workspace custom IP BSP bypass'i `app build` oncesiyle sinirli kalmayacak sekilde `bsp regenerate` oncesinde de calistirilir.
- `.hwh` custom IP eslesmesi yetersiz kalsa bile, `libsrc/*/src/make.libs` icinde `*.c` literal'i bulunan ve ayni `src` klasorunde gercek `.c` dosyasi olmayan source'suz BSP driver klasorleri otomatik no-op hale getirilir.
- FreeRTOS/lwIP BSP regenerate adimi custom IP makefile patch'i tazelendikten sonra calisir; bu, Vitis 2023.2'de gorulen `cc1.exe: fatal error: *.c: Invalid argument` hatasini daha erken asamada engeller.

## v0.1.66 - 2026-06-30

- Vitis workspace akisi, `Auto: custom IP - none` seciliyken source'suz custom PL IP BSP driver klasorlerini build oncesi ikinci emniyet katmani ile bypass eder.
- `libsrc/<custom_ip>*/src/make.libs` dosyalari build'i kiran `*.c` literal derleme hatasina dusmeyecek no-op hedeflerle guncellenir; orijinal dosya `.spec2code_backup` olarak korunur.
- `app build` ilk denemede custom IP BSP makefile nedeniyle hata verirse script bypass'i tazeleyip build'i bir kez daha dener.
- `mem_pcie_intr_0` gibi instance adlari `mem_pcie_intr_v1_0` benzeri BSP driver klasorleriyle eslestirilecek sekilde normalize edilir.

## v0.1.65 - 2026-06-30

- Windows executable icinde Generate sirasinda `frontend/src/lib/version.ts` source dosyasi aranmasindan kaynaklanan paketli exe hatasi giderildi.
- Test Bench agent version bilgisi artik paketlenmis `spec2code_version.txt` metadata dosyasindan, environment degiskenlerinden veya gelistirme ortaminda source fallback'lerinden okunur.
- PyInstaller build akisi release version metadata dosyasini exe icine ekler.

## v0.1.64 - 2026-06-30

- Vitis Workspace akisi temp/staging dizinini kullanicidan zorunlu input olarak alacak sekilde guncellendi.
- XSA kopyasi, generated kaynaklar, Tcl script, manifest ve XSCT loglari artik workspace altina varsayilan yazilmaz; kullanicinin verdigi temp dizini altindaki job klasorune yazilir.
- Vitis Workspace sonucuna `temp_path` ve `staging_path` alanlari eklendi.

## v0.1.63 - 2026-06-30

- Vitis Workspace paneli platform, system ve application proje adlarini kullanicidan alacak sekilde genisletildi.
- Vitis dizini, XSA dosyasi ve workspace dizini alanlari uzun Windows path'leri icin alt alta yerlestirildi.
- XSA girdisi artik dogrudan `.xsa` dosyasi olarak dogrulanir ve XSCT script'i orijinal path yerine staging altindaki XSA kopyasini kullanir.
- XSCT script'i once adlandirilmis platform/system/application akisini dener; uyumsuz Vitis varyantlarinda legacy `app create -hw` akisi fallback olarak korunur.

## v0.1.62 - 2026-06-30

- Vitis workspace custom PL IP tespiti `xilinx.com:user:*` gibi user-packaged IP'leri de kapsayacak sekilde genisletildi.
- Custom PL IP driver `none` policy artik lwIP BSP regenerate adimindan once uygulanir.
- `libsrc/<driver>/src/make.libs` ve `fatal error: *.c: Invalid argument` Vitis loglari custom IP BSP driver hatasi olarak aciklanir.

## v0.1.61 - 2026-06-30

- Test Bench TCP session uzerinden `spec2code_version` global komutu eklendi.
- Kart uzerinde calisan generated agent, `Spec2Code v...` cevabi dondurerek TCP/lwIP/dispatch hattinin saglikli oldugunu dogrular.
- Test Bench arayuzune baglanti sonrasi `Surum sorgula` butonu eklendi.
- Generate edilen Test Bench manifest artik `agent_version` bilgisini tasir.

## v0.1.60 - 2026-06-30

- LMK04832 Test Bench operasyonlarina PLL1/PLL2 lock detect ve lock loss sorgulari eklendi.
- LMK04832 `0x183` readback status register alanlari 0/1 normalize edilerek TCP Test Bench sonucunda tek byte olarak dondurulur.
- SPI/TICS register tabanli descriptor'larda `read_register` operasyonlari icin register read helper uretimi eklendi.
- Descriptor semasi cok parcali operasyon adlarini ve readback bit alanlari icin `right_shift` ifadesini destekler.

## v0.1.59 - 2026-06-30

- Vitis workspace akisi XSA icindeki non-Xilinx/AMD custom PL IP'leri `.hwh` uzerinden algilar.
- Varsayilan custom PL IP driver policy `auto_none` oldu; aday IP'ler icin BSP driver `none` denenir ve build korumasi saglanir.
- Sirket custom IP'sinin gercek driver'i kullanilacaksa Vitis workspace panelinden `BSP default'u koru` secilebilir.
- Vitis manifest/result artik custom IP driver policy ve aday IP listesini tasir; UI rozetlerinde ozet bilgi gorunur.

## v0.1.58 - 2026-06-30

- Vitis workspace akisi lwIP test bench gerektiginde BSP `api_mode` ayarini runtime'a gore otomatik secer.
- FreeRTOS runtime icin lwIP `SOCKET_API`, standalone runtime icin `RAW_API` denenir.
- Vitis manifest/result ve UI rozeti artik kullanilan lwIP API mode bilgisini gosterir.
- README, Windows dokumani ve userguide lwIP runtime/API mode ayrimini aciklayacak sekilde guncellendi.

## v0.1.57 - 2026-06-30

- Vitis/XSCT workspace script'indeki `[Spec2Code]` log prefix'i Tcl tarafinda komut gibi yorumlanmayacak sekilde escape edildi.
- XSCT return code `0` donse bile stderr/stdout icinde Tcl/Vitis fatal hata sinyali varsa workspace job artik hata kabul edilir.
- Vitis workspace UI'i hata durumunda yesil "Workspace hazir" karti gostermeyip stderr/stdout log tail bilgisini kirmizi tani kartinda gosterir.
- `invalid command name "Spec2Code"` hatasi icin Vitis error mapper ve regresyon testleri eklendi.

## v0.1.56 - 2026-06-30

- Test Bench TCP akisi kalici session modeline gecirildi; kullanici once karta baglanir, sonraki komutlar ayni socket uzerinden gonderilir.
- Backend'e Test Bench connect/disconnect/status session API'leri ve thread-safe socket manager eklendi.
- Test Bench arayuzunde baglanti durumu, Baglan/Kes kontrolleri ve baglanti yokken komut gondermeyi engelleyen akisi eklendi.
- Persistent TCP davranisi unit test ile sabitlendi.

## v0.1.55 - 2026-06-29

- Boardless debug/simulasyon artefactleri kaldirildi; canli debug akisi TCP Test Bench uzerinden sade tutuldu.
- Generate artik emekli boardless transfer dosyalarini uretmez ve backend bu dosyalar icin ayri event yaymaz.
- Code Viewer, Design Review, generated README ve userguide icindeki eski boardless debug referanslari temizlendi.

## v0.1.54 - 2026-06-29

- Aynı part'tan birden fazla entegre bulunan şematiklerde Test Bench register resolver fonksiyonlarının tekrar üretilmesi düzeltildi.
- `my_io_board_testbench_ops.c` içinde `ltc2991TestbenchRegisterResolve` benzeri helper'lar artık module başına tek kez yazılır.
- Aynı driver header include satırlarının tekrar edilmesi önlendi.

## v0.1.53 - 2026-06-29

- Test Bench sayfasinin generate sonucunu yalnizca aktif frontend state'inden okuma problemi duzeltildi.
- Test Bench artik aktif generate dosyalarinda manifest yoksa son basarili generate manifest'ini tarayici hafizasindan kontrollu sekilde yukler.
- Generate devam ederken eski manifest'in yanlislikla aktif gorunmemesi icin bekleme mesaji ve daha net hazir degil aciklamasi eklendi.

## v0.1.52 - 2026-06-29

- Zynq UltraScale+ PS Ethernet icin lwIP tabanli hedef kart TCP test bench agent dosyalari eklendi.
- Generated agent, `XIicPs`, `XSpiPs` ve `XQspiPsu` controller handle'larini kart uzerinde initialize edip test bench dispatch hook'larini override eder.
- Vitis workspace akisi lwIP agent algiladiginda BSP lwIP library secimini best-effort olarak dener ve manifest'e `requires_lwip` bilgisini yazar.
- Design Review ve Vitis panelinde lwIP test bench dosyalari/gereksinimi gorunur hale getirildi.
- lwIP/xadapter minimal QC stublari ve parser/codegen/Vitis unit testleri eklendi.

## v0.1.51 - 2026-06-29

- Generate sonucu hedef kart üzerinde çalıştırılabilecek test bench agent dosyaları üretilecek şekilde genişletildi.
- Test Bench sayfası eklendi; generated manifest üzerinden entegre/operasyon seçip lokal TCP ile karta komut gönderme altyapısı kuruldu.
- LTC2991 için raw current/differential read operasyonu eklendi; voltage, VCC, temperature ve current raw okumaları test bench üzerinden yüzeye çıkarıldı.
- Test bench dispatch artık yalnızca gerçekten generate edilen `operations_requested` fonksiyonlarına referans verir.
- Vitis compile error mapper eklendi; missing include, undefined reference, eksik `XPAR_*`, unknown type gibi hatalar UI'da öneriyle gösterilir.
- Test bench TCP bridge ve Vitis mapper için unit test kapsamı eklendi.

## v0.1.50 - 2026-06-29

- Executable release paketleri sadeleştirildi: paket içinde yalnızca çalıştırılabilir dosya, `changelog.md` ve `userguide.md` bulunur.
- `changelog.md` release geçmişinin tamamını tutacak kalıcı dosya olarak eklendi.
- `userguide.md` kullanıcı seviyesinde kurulum, kullanım, generate, Vitis workspace, LLM ve sorun giderme akışlarını kapsayacak şekilde eklendi.
- Release dokümanlarının yeni sürümle güncel kalması için test kapsamı eklendi.

## v0.1.49 - 2026-06-29

- Generate sonrası tek tuş Vitis workspace üretim paneli eklendi.
- Windows ortamında Vitis dizini, `.xsa` dosyası ve workspace path'i verilerek XSCT tabanlı platform/application build akışı eklendi.
- Vitis sürüm algılama, staging klasörü, Tcl script, manifest ve XSCT log dosyaları üretildi.
- Vitis self-test runner için `.c` dosyasına karşılık `.h` dosyası da eklendi.
- Vitis workspace akışı progress bar ve job log ile görünür hale getirildi.

## v0.1.48 - 2026-06-29

- TMP101, SHT21 ve 24LC32A entegreleri için descriptor, catalog knowledge ve driver üretim desteği eklendi.
- Knowledge context limiti Qwen 256K kullanımına uygun olacak şekilde yükseltildi.

## v0.1.47 - 2026-06-29

- Bilgi soru merkezi için LLM progress aşamaları eklendi.
- LLM cevapları insan tarafından daha rahat okunacak başlık, liste ve token formatına dönüştürüldü.
- Cevapların doğrulanmış catalog context dışına çıkmadığını kontrol eden görünür mekanizma iyileştirildi.

## v0.1.46 - 2026-06-29

- ADAR1000 entegresi için kapsamlı destek eklendi.
- ADAR1000 register, bit field, driver view ve bus transaction bilgileri catalog tarafına işlendi.

## v0.1.45 - 2026-06-29

- SPI chip select waveform görünümü gerçek transaction diyagramına daha yakın hale getirildi.
- Chip select high/low geçişleri tek sinyal satırında daha okunabilir gösterildi.

## v0.1.44 - 2026-06-28

- Bus waveform hizalaması iyileştirildi.
- Clock, SPI ve I2C sinyal satırlarının görsel hizası netleştirildi.

## v0.1.43 - 2026-06-28

- Bus waveform sinyal satırları sadeleştirildi.
- SPI chip select, SCK, MOSI ve MISO satırlarının okunabilirliği artırıldı.

## v0.1.42 - 2026-06-28

- SPI waveform satır etiketleri kendi sinyal satırlarına hizalandı.
- SCK, MOSI ve MISO takibi daha anlaşılır hale getirildi.

## v0.1.41 - 2026-06-28

- I2C SDA hattında master ve slave tarafının data sürdüğü anlar ayrı renklerle gösterildi.
- I2C transaction okuma/yazma görselleştirmesi netleştirildi.

## v0.1.40 - 2026-06-28

- Catalog register detayına bus waveform view eklendi.
- Driver view karşılığı olarak I2C/SPI transaction akışları görsel hale getirildi.

## v0.1.39 - 2026-06-28

- Bilgi soru merkezi Catalog içinden çıkarılıp ayrı sayfa haline getirildi.
- LMK04832, LMX2820 ve LMX1204 için TI clock cihaz desteği eklendi.
- TI clock register catalog kapsamı genişletildi.
- TI clock bit field detayları eklendi.
- Catalog register knowledge kapsamı genel olarak genişletildi.
- Register map search eklendi ve arama register/bit field isimleriyle sınırlandı.
- Global, doğrulanmış knowledge context üzerinden LLM soru-cevap akışı eklendi.
- Register açıklamaları ve driver detayları daha doğrudan hale getirildi.

## v0.1.36 - 2026-06-28

- Her test `.c` dosyası için karşılık gelen `.h` dosyası üretimi garanti altına alındı.
- Test source içindeki public prototip ve dışarıdan gereken tanımlar header tarafına taşındı.

## v0.1.35 - 2026-06-28

- Generate sonucu içinde mock harness dosyalarının her zaman bulunması garanti edildi.
- Mock bus ve mock plan dosyalarının output listesine girmesi düzeltildi.

## v0.1.34 - 2026-06-28

- Uygulama versiyonu üstte sabit gösterilecek şekilde eklendi.
- Generate sonucunda mock harness dosyalarının görünürlüğü iyileştirildi.

## v0.1.33 - 2026-06-28

- Design review paneli eklendi.
- Init tooling ve init sequence düzenleme akışları geliştirildi.
- Generate sonrası beklenen mock/test dosya uyarıları iyileştirildi.

## v0.1.32 - 2026-06-27

- Register transaction preview eklendi.
- Register read/write akışlarında TX/RX byte boyutları ve driver view ilişkisi gösterildi.

## v0.1.31 - 2026-06-27

- Register bit field değer açıklamaları tamamlandı.
- Tek bitli ve çok bitli alanlarda anlamlı value açıklamaları eklendi.

## v0.1.30 - 2026-06-27

- Register bit field explorer eklendi.
- Register'a tıklayınca ilgili bit field seviyesindeki bilgiler görünür hale getirildi.

## v0.1.29 - 2026-06-27

- Pin map notları tek noktada gösterilecek şekilde sadeleştirildi.
- Tekrar eden sol/sağ bilgi alanları azaltıldı.

## v0.1.28 - 2026-06-27

- Catalog sayfasına protokol filtresi eklendi.
- I2C ve SPI cihazları ayrı ayrı veya birlikte filtrelenebilir hale geldi.

## v0.1.27 - 2026-06-27

- Pin map'ler interaktif hale getirildi.
- Pin detayları yalnızca seçilen pine tıklanınca gösterilecek şekilde sadeleştirildi.

## v0.1.26 - 2026-06-27

- Pin map görselleri küçültüldü ve okunabilirlik iyileştirildi.
- LTC2991 pin bilgi yerleşimi düzeltildi.
- Pin/register bilgilerinin doğruluğu için ek kontroller yapıldı.

## v0.1.25 - 2026-06-27

- Catalog pin map altyapısı bütün desteklenen entegreleri kapsayacak şekilde genelleştirildi.
- Catalog layout'u sol liste ve sağ detay ekranı yapısına taşındı.

## v0.1.24 - 2026-06-27

- Schematic arka planındaki devre dokusu daha geniş alana yayıldı.
- Sol koyu çalışma alanı görsel olarak daha bütünlüklü hale getirildi.

## v0.1.23 - 2026-06-27

- Device knowledge metinleri Türkçe cümle yapısına taşındı.
- English teknik terimler yalnızca anlaşılırlık için bırakıldı.

## v0.1.22 - 2026-06-27

- Uygulama metinlerinde Türkçe karakter ve encoding kaynaklı sorunlar giderildi.
- Metinler daha stabil ASCII/Türkçe uyumlu hale getirildi.

## v0.1.21 - 2026-06-27

- Device knowledge yalnızca Catalog sayfasında gösterilecek şekilde taşındı.
- Schematic ekranı bağlantı ve konfigürasyon odağında sadeleştirildi.

## v0.1.20 - 2026-06-27

- LTC2991 pin map ve schematic summary eklendi.
- LTC2991 pair/mode bilgileri node üzerinde kompakt özetlenebilir hale geldi.

## v0.1.19 - 2026-06-27

- Statik device knowledge pack altyapısı eklendi.
- Desteklenen entegreler için datasheet'ten süzülmüş özet bilgiler Catalog tarafında gösterilmeye başlandı.

## v0.1.18 - 2026-06-27

- Schematic bağlantı etiketlerinin kontrastı artırıldı.
- I2C/SPI_CS gibi edge label'lar daha okunabilir hale getirildi.

## v0.1.17 - 2026-06-27

- ADXL345 ve BME280 catalog/descriptors desteği kaldırıldı.
- Kullanılmayacak entegreler UI ve üretim altyapısından çıkarıldı.

## v0.1.16 - 2026-06-27

- Generated C standardında camelCase fonksiyon isimleri zorunlu hale getirildi.
- Fixed-width `uint*_t` yerine primitive C tipleri kullanılacak şekilde üretim düzeltildi.
- Pointer yıldızı tipe bitişik yazılacak şekilde template'ler iyileştirildi.

## v0.1.15 - 2026-06-27

- Struct typedef ve struct değişken prefix kuralları netleştirildi.
- `SOrnekStruct sMyStruct;` biçimi kodlama standardına işlendi.

## v0.1.14 - 2026-06-27

- Arayüze daha sakin ve restrained visual asset layer eklendi.
- Schematic ve setup ekranları görsel olarak zenginleştirildi.

## v0.1.13 - 2026-06-27

- Schematic layout parent/controller pozisyonuna göre sıralanacak şekilde düzeltildi.
- Çapraz bağlantı çakışmaları azaltıldı.

## v0.1.12 - 2026-06-27

- QSPI PSU desteği eklendi.
- Generated identifier standardı sıkılaştırıldı.

## v0.1.11 - 2026-06-27

- Kodlama standardı sabit default ruleset'e bağlandı.
- Kullanıcıdan ayrı coding-standard dokümanı alma altyapısı kaldırıldı.

## v0.1.10 - 2026-06-27

- `xparameters.h` içindeki aynı controller'ın alias olarak iki kez görünmesi düzeltildi.
- Örneğin `XPAR_PSU_I2C_0` ve `XPAR_XIICPS_0` aynı controller olarak dedupe edildi.

## v0.1.9 - 2026-06-27

- LTC2991 device configuration profile eklendi.
- Pair mode, single-ended/differential/current/temp seçimleri init sequence'e bağlandı.

## v0.1.8 - 2026-06-26

- AD7414, DS1682 ve LTC2945 desteği eklendi.
- Bu cihazlar descriptor ve codegen akışına alındı.

## v0.1.7 - 2026-06-26

- Coding standard studio altyapısı eklendi.
- Sonraki sürümlerde bu altyapı sabit default standard lehine sadeleştirildi.

## v0.1.6 - 2026-06-26

- LLM tarafından üretilen aday çıktıların doğrudan uygulanması engellendi.
- Aday dosyalar deterministic QC kapısından geçmeden gerçek dosyaya yazılmaz hale getirildi.

## v0.1.5 - 2026-06-26

- LLM configuration daha dayanıklı hale getirildi.
- Model adı, endpoint, timeout ve cevap limitleri kullanıcı tarafından esnek girilebilir oldu.

## v0.1.4 - 2026-06-26

- Generate öncesi project preflight validation eklendi.
- Vitis-ready export paketi eklendi.

## v0.1.3 - 2026-06-26

- Generated file tree ve dosya indirme altyapısı eklendi.
- Tek dosya ve tüm output zip download akışları eklendi.

## v0.1.2 - 2026-06-26

- Windows ortamında result file decoding hatası giderildi.
- Vendor dosyalarındaki farklı encoding durumları daha toleranslı okundu.

## v0.1.1 - 2026-06-26

- Windows source development workflow dokümante edildi.
- Air-gap Windows geliştirme adımları eklendi.

## v0.1.0 - 2026-06-26

- Release packaging altyapısı eklendi.
- Windows kullanım dokümantasyonu eklendi.
- İlk public release paketi üretildi.
