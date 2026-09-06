# Spec2Code User Guide

Bu dosya release paketinin icine girer. Amaci, Spec2Code'u kullanan bir gomulu
yazilimcinin uygulamayi acip proje uretmesine, ciktiyi incelemesine ve gerekirse
Vitis workspace hazirlamasina yetecek pratik bilgiyi tek yerde vermektir.

## 1. Spec2Code Nedir?

Spec2Code, Xilinx/Vitis tabanli kartlarda kullanilan I2C, SPI ve QSPI bagli
entegreler icin deterministik C driver ve test dosyalari ureten lokal bir web
uygulamasidir.

Uygulama cloud uzerinde calismaz. `Spec2Code.exe` lokal bir FastAPI backend ve
React UI baslatir. Browser'da gordugun ekran kendi bilgisayarinda calisir.

Ana hedefler:

- `xparameters.h` icinden controller bilgisini okumak.
- Schematic ekraninda harici entegre baglantilarini kurmak.
- Desteklenen entegreler icin `.c/.h` driver ve test dosyalari uretmek.
- Generated kodu sabit coding standard ve QC kontrollerinden gecirmek.
- Gerekirse `.xsa` ile Vitis workspace olusturmak.
- Gercek karta baglanan test bench agent uzerinden register ve operasyon seviyesinde okuma/yazma denemeleri yapmak.

## 2. Windows'ta Calistirma

Release paketini acinca bu dosyalari gorursun:

```text
Spec2Code.exe
changelog.md
userguide.md
glm52_handoff.md
```

Calistirmak icin:

```powershell
.\Spec2Code.exe
```

Varsayilan adres:

```text
http://127.0.0.1:8077
```

Otomatik browser acilmazsa bu adresi manuel ac.

Port degistirmek icin:

```powershell
.\Spec2Code.exe --host 127.0.0.1 --port 8078
```

Browser acilmasin istersen:

```powershell
.\Spec2Code.exe --no-browser
```

## 3. Gerekli Yardimci Tool'lar

Uygulama acilmak icin LLVM veya Cppcheck'e mecbur degildir; ama gercek QC icin
bu tool'lar onerilir:

- LLVM: `clang-format`, `clang-tidy`, `libclang`
- Cppcheck

Tipik Windows kurulum path'leri otomatik aranir:

```text
C:\Program Files\LLVM\bin
C:\Program Files\Cppcheck
```

Farkli yerde kuruluysa environment variable verebilirsin:

```powershell
$env:SPEC2CODE_CLANG_FORMAT_PATH = "D:\Tools\LLVM\bin\clang-format.exe"
$env:SPEC2CODE_CLANG_TIDY_PATH = "D:\Tools\LLVM\bin\clang-tidy.exe"
$env:SPEC2CODE_CPPCHECK_PATH = "D:\Tools\Cppcheck\cppcheck.exe"
$env:SPEC2CODE_LIBCLANG_PATH = "D:\Tools\LLVM\bin\libclang.dll"
```

Tool algilama durumunu kontrol etmek icin:

```text
http://127.0.0.1:8077/api/health
```

## 4. Temel Kullanim Akisi

Spec2Code kullanimi genelde su sirayla ilerler:

1. **Setup** ekraninda platformu sec.
2. `xparameters.h` dosyasini yukle veya icerigini yapistir.
3. Parser tarafindan bulunan controller'lari kontrol et.
4. **Schematic** ekraninda entegreleri controller'lara bagla.
5. Gerekirse entegre configuration ayarlarini yap.
6. **Generate** ekraninda kod uret.
7. Code viewer'da dosya agacini, QC sonucunu ve Test Bench dosyalarini incele.
8. Istersen tek dosya, tum output zip veya Vitis-ready paket indir.
9. Istersen Vitis workspace paneliyle `.xsa` uzerinden workspace olustur.
10. Kart tarafinda TCP test agent hazirsa **Test Bench** sayfasindan canli okuma/yazma denemeleri yap.

## 5. Setup Ekrani

Setup ekraninda proje adi, platform, target core ve runtime secilir.

Desteklenen platformlar:

- Zynq-7000
- Zynq UltraScale+ MPSoC
- Versal ACAP
- MicroBlaze 7-series (Artix-7 / Kintex-7 / Spartan-7 PL)

### MicroBlaze 7-series notu (durust kapsam)

Uctan uca **masa ustunde** dogrulandi: urunun Vivado akisiyla uretilen gercek
`.xsa` -> XSA parser -> codegen + QC -> Vitis platform/BSP/app -> gercek
MicroBlaze ELF'i (`ELF 32-bit LSB executable, Xilinx MicroBlaze 32-bit RISC`).
Kapsam:

- **AXI IIC (`XIic`)** cihazlari, TCA9548A mux arkasindakiler dahil.
- **AXI Quad SPI (`XSpi`)** cihazlari (TICS register cihazlari dahil).
- **AXI GPIO (`XGpio`)** — hem cihaz transportu hem denetleyici op'lari
  (`gpio_read` / `gpio_write`).
- Test bench ajani: **MDM UART** (`testbench_transport: "mdm"`, xsdb
  `jtagterminal` koprusu) veya **AXI UARTLite** (fiziksel seri pin).
- `run_on_board`: bitstream ZORUNLU (soft cekirdek, PL programlanmadan JTAG'de
  hicbir islemci hedefi gorunmez).

**Yerel bellek (LMB) siniri — onemli:** MicroBlaze firmware'i yalniz LMB (BRAM)
icinde kosar. Olcum (gercek `mb-gcc` link'i): tam test bench ajani + 3 cihaz
surucusu + BSP ~**156 KB**. Vivado blok otomasyonunun tavani 128 KB'dir, bu
yuzden Spec2Code 256KB/512KB'i LMB adres segmentini buyuterek kurar ve geri
okuyup dogrular. Vivado Tasarimi ekraninda MicroBlaze varsayilani **256KB**'dir;
kucuk secersen link `S2C-VITIS-MEMORY-012` (yerel bellek tasmasi) ile duser.

**Gercek kart (2026-09-05, Digilent Nexys A7-100T):** `scripts/make_nexys_a7_design.tcl`
ile uretilen bitstream (MB 256K LMB + AXI UARTLite 115200 + AXI IIC + AXI Quad SPI
STARTUPE2 uzerinden konfigurasyon flash'ina) kartta kosuldu: UART ajani, kart ustu
ADT7420 (ID 0xCB, sicaklik), I2C tarama, S25FL128S flash sil/yaz/oku (0xF00000) ve
karisik-mod CIT (ADT7420 gercek + LTC2991 sanal) uctan uca dogrulandi. Kartta bulunan
saha bug'i: AXI IIC standart modda tek baytlik STOP yazimi bayti dusuruyor - uretilen
kod artik DINAMIK mod (`XIic_DynInit/DynSend/DynRecv`) kullanir ve register
okumalarinda pointer'i `XIIC_REPEATED_START` ile gonderir (STOP'lu pointer + DynRecv
IP'de takilir). Nexys A7 pinleri: saat E3, CPU_RESETN C12 (aktif-dusuk), UART C4/D4,
I2C C14/C15, QSPI CS L13 / DQ0 K17 / DQ1 K18 (SCK STARTUPE2). Kesme yolu (`axi_intc`)
ve DDR/MIG yoktur.

`xparameters.h` yuklediginde uygulama controller'lari cikartir. Ayni controller
farkli macro alias'lariyla geldiyse tek controller olarak dedupe edilir.

Ornek:

```text
XPAR_PSU_I2C_0
XPAR_XIICPS_0
```

Bu iki macro ayni donanim controller'ini isaret ediyorsa UI'da tek I2C controller
olarak gorunmelidir.

## 6. Schematic Ekrani

Schematic ekraninda controller, mux ve entegre baglantilari kurulur.

Yapabileceklerin:

- I2C cihaz eklemek.
- SPI/QSPI cihaz eklemek.
- TCA9548A gibi I2C mux eklemek.
- Cihazi mux channel uzerinden veya dogrudan controller'a baglamak.
- I2C address, SPI chip select, reset GPIO ve IRQ gibi attach bilgilerini girmek.
- Desteklenen cihazlarda configuration panelinden init ayarlarini yapmak.

Baglanti validasyonu generate oncesinde yapilir. Ornegin:

- Ayni I2C bus uzerinde address cakismasi.
- Ayni SPI controller uzerinde chip select cakismasi.
- Var olmayan controller referansi.
- Descriptor ile uyumsuz transport tipi.

## 7. Cok-kartli Sistemler

Gercek projelerde sistem tek karttan ibaret degildir: FPGA'in bulundugu bir ana
kart vardir, I2C/SPI hatlari fiziksel konnektorlerle baska kartlara cikar.
Spec2Code kartlari birinci sinif olarak modeller: sematikte kutu, uretimde klasor
ve kart fonksiyonlari, CIT/Test Bench'te grup, YATT'ta topoloji bolumu.

Onemli kural: kart tanimlamadigin surece hicbir sey degismez. Kart tanimsiz bir
projede uretilen cikti bugunku duzeniyle bayt-bayt aynidir. Kart katmani yalnizca
sen kart tanimlayinca devreye girer.

### Kart olusturma

Schematic ekraninin sag panelindeki **Kartlar** kutusunda "Kart ekle" dugmesi
vardir.

- Ilk eklenen kart **ana karttir** ve o ana kadar eklenmis butun controller, mux
  ve entegreler ona tasinir. Sonraki kartlar cevre karti olur.
- Tam olarak bir ana kart olmalidir. Controller'lar her zaman ana karttadir (tek
  FPGA ilkesi), onlar icin kart secilemez.
- Kart kimligi ilk verilen addan turer (`RF Kart` -> `rf_kart`). Adi sonradan
  degistirmek kimligi degistirmez, cunku cihazlar ve konnektorler o kimlige
  referans verir. Uretilen klasor ve C fonksiyon adlari ise her zaman GUNCEL
  addan turer.
- Kart kutulari sematikte yeniden boyutlandirilabilir; ana kartta "ana" rozeti
  gorunur.
- Bir karti silersen icindeki cihazlar ana karta duser ve o karta degen
  konnektorler silinir. Silme onaylidir.

### Cihaz atama

Entegre veya mux'u fare ile hedef kart kutusunun icine surukle; birakildiginda
`board_id` o karta ayarlanir. Kutularin disina birakilan cihaz ana karta doner.

Cihazin elektriksel baglantisi (`attach.controller_id` ve `via_mux`) bundan
ETKILENMEZ. Kart, elektriksel modele dik bir konum katmanidir: yalnizca cihazin
fiziksel olarak hangi PCB uzerinde oldugunu soyler.

### Konnektor tanimlama

Kart kutusuna tiklayip sag paneldeki **Konnektorler** bolumunden ekle:

- **Ad**: serbest metin, ornegin `J7 -> J1`.
- **Kaynak kart / Hedef kart**: iki uc farkli kart olmalidir.
- **Hat (denetleyici)**: hattin ciktigi controller.
- **Switch (ops.) + Kanal**: hat bir I2C mux kanalindan geciyorsa.
- **Not**: saha bilgisi, ornegin `10-pin FFC`.

Konnektor hattin kartlar arasi gecisini BELGELER, elektriksel yolu degistirmez.
Sematikte kesikli ok olarak cizilir; etiketi `ad - hat - mux ch N` seklindedir.

Ana kart disindaki bir kartta cihaz varsa ama o baglantiyi belgeleyen konnektor
yoksa validasyon uyari verir (hata degil): "... kartinda cihaz var ama
baglantisini belgeleyen konnektor yok".

### Uretilen ciktida ne degisir?

Kart tanimliyken surucu dosyalari kart klasorlerine ayrilir:

```text
drivers/ana_kart/ltc2991.c    (+ .h)
drivers/ana_kart/tca9548a.c   (+ .h)
drivers/rf_kart/tmp101.c      (+ .h)
drivers/rf_kart/sht21.c       (+ .h)
cit/, tests/                           (degismez: CIT katmani ve ajan SISTEM genelidir)
```

Klasor adi kart ADINDAN turetilir:

- Turkce harfler ASCII karsiligina katlanir (`i I s S g G u U o O c C`).
- Alfanumerik olmayan her karakter ayrac sayilir; klasor adi `snake_case` olur
  (`"RF Kart"` -> `rf_kart`).
- Iki kart ayni ada duserse uretim sessizce devam etmez, acik hata ile durur.

Cihaz surucu dosyalarinin ICERIGI ve fonksiyon adlari degismez; sembol onekleme
yoktur, yalniz klasor degisir. Kart basina ayri bir C modulu URETILMEZ (v0.1.178:
hic cagrilmayan `<kart>Init/CitRun/SelfTest` kaldirildi); kart bilgisi manifest
uzerinden tasinir, CIT ve Test Bench ekranlari kutulari kart basliklari altinda
gruplar. Sistem geneli `boardCitRun()` ve `SBoardCit` bit sirasi kart sayisindan
bagimsizdir - `boardCit*` adlarindaki "board" SISTEM anlamindadir, fiziksel kart degil.

`drivers/<kart>/` klasorleri Vitis workspace uretiminde application include
yoluna otomatik eklenir; bu yuzden nitelenmemis `#include "tmp101.h"` calismaya
devam eder.

### CIT, Test Bench ve YATT

- **CIT** ekrani (Bring-up sekmesinin yanindadir) her entegreyi KENDI kutusunda
  gosterir: baslik (parca, cihaz id, adres/CS, mux, SANAL rozeti, ozet), dizi
  donuslu op'lar icin kanal karolari (LTC2991 V1..V8 / I1..I8), skaler olcumler
  icin deger satirlari. Kart tanimliysa kutular kart basliklari altinda gruplanir;
  ustteki sistem toplamlari korunur. Kanal karosuna tiklayinca o kanalin
  isim/limit/onem duzenleme seridi acilir; kalem = duzenle, guc = ac/kapa.
- **Dizi donuslu olcumler (voltages[8] gibi):** CIT'te her kanal AYRI bir olcum
  slotudur (manifest `cit.olcumler[].channel`, `channel_label` = "V1".."V8";
  varsayilan isim `<PART>_V<k>_<i>`). Kart op'u BIR kez okur, kanallari yanittan
  ayristirir. `config.cit.measurements[]` girdisinde `channel` verilirse yalniz o
  kanala, verilmezse (isim haric) butun kanallara uygulanir.
- **Test Bench** entegre listesini kart basliklari altinda gruplar; "butun
  cihazlari ilklendir" kart kart ilerler ve ozet kart bazinda gosterilir.
- **YATT** dokumanina **Sistem Topolojisi** bolumu eklenir: kart tablosu
  (ad, rol, not, cihaz sayisi) ve konnektor tablosu (ad, kartlar, hat, mux
  kanali, not).
- Test bench manifesti `boards[]` ve `connectors[]` bolumlerini, ayrica her cihaz
  ve her CIT olcumu icin `board_id` alanini tasir.

### Ornek proje

`specs/samples/multi_board_demo.spec.json` calisan iki kartli bir ornektir: ana
kartta ZynqMP PS I2C controller, TCA9548A switch ve LTC2991; RF kartta TMP101 ve
SHT21 (ikisi de switch kanal 3'un arkasinda). Aradaki gecisi `J7 -> J1`
konnektoru belgeler. Headless uretmek icin:

```powershell
python spec2code_cli.py build --spec specs/samples/multi_board_demo.spec.json
```

## 8. Catalog ve Knowledge

Catalog ekrani desteklenen entegreleri listeler. Arama ve protokol filtreleri ile
I2C/SPI cihazlari daraltabilirsin.

Knowledge bolumunde su bilgiler bulunur:

- Register veya command map.
- Bit field seviyesi anlamlar.
- Deger aciklamalari.
- Pin map.
- Tipik kullanim receteleri.
- Driver view.
- Bus transaction waveform.

Bu bilgiler runtime'da LLM'e yazdirilmaz. Repo icindeki dogrulanmis statik bilgi
paketlerinden gelir. LLM soru merkezi de cevap verirken bu dogrulanmis context'i
kullanir.

## 9. Bilgi Soru Merkezi

Bilgi soru merkezi, catalog knowledge uzerinden lokal OpenAI-compatible modele
soru sormak icindir.

Ornek sorular:

```text
LMK04832 PLL2 lock nereden okunur?
Flash sector erase icin hangi byte'lar gider?
LTC2991 differential ayari hangi register'lari etkiler?
```

Model sadece verilen knowledge context'i kullanmalidir. Backend cevap icindeki
register, opcode ve bit field gibi token'lari context ile karsilastirir. Context
disi bilgi varsa hata verir.

Qwen 3.5 397B gibi 256K context destekli modeller icin context limiti yuksek
tutulmustur. Daha kucuk modellerde soru daha dar sorulmalidir.

## 10. Generate Ekrani

Generate basladiginda pipeline console su asamalari gosterir:

- Codegen.
- Imported reference source kopyalama.
- LLM destekli QC fixer varsa LLM adimlari.
- Deterministik QC round'lari.
- Result summary.

Generate bittiginde Code viewer'da dosya agaci acilir.

Output klasor yapisi tipik olarak:

```text
drivers/
tests/
cit/
tests/sim/   (yalniz sanal cihaz isaretliyken)
reference_sources/
qc_report.json
README.md
.clang-format
```

Her `.c` dosyasinin karsilik gelen `.h` dosyasi olmalidir. Test ve Test Bench
agent dosyalari da bu kurala dahildir.

### Katmanlar: surucu struct API'si, CIT ust katmani, simulasyon

Uretilen kod uc katmandir; bagimlilik tek yonlu (yukaridan asagiya):

| Katman | Klasor | Kime gider | Icerik |
|---|---|---|---|
| Test bench | `tests/` (+ `tests/sim/`) | yalniz Spec2Code | ajan, S2C-MSG, `<mod>_test.*` self-test'ler (Test Bench `self_test` op'u), `spec2code_cit.*` (CIT kosusu: `cit/` katmanini cagirir, host raporu), sanal cihazlar |
| CIT ust katmani | `cit/` | senin firmware'ine | surucu struct'larini ANLAMLANDIRIR: kapali aralik limiti (min <= deger <= max, min = max gecerli), etkin, OK/NOK |
| Surucu | `drivers/` | senin firmware'ine | Xilinx API'sini DOGRUDAN cagirir, ham veriyi kendi struct'larinda verir |

Kullaniciya giden `drivers/` ve `cit/` dosyalarinda `spec2code` adli hicbir dosya/sembol
yoktur. Suruculer `drivers/dbg_printf.h/.c` ile loglar: `dbg_printf(DEBUG_LEVEL_x, fmt, ...)`,
esik `dbgLevelSet()` ile calisma zamaninda (varsayilan ERROR; yalniz esikten kucuk/esit
seviyeler basilir); bus baytlari `dbgTraceI2c/Spi` ile TRACE seviyesinde. Kendi projende
cikti `xil_printf`e gider, test bench ise `dbgSinkSet` ile satirlari S2C-LOG cercevesine sarar.

**Surucu (`drivers/<mod>.h`):**

- Durum registerleri (fields tanimli, width <= 16, `access: ro` ya da `post_init_status`):
  `S<Mod>Status` bit alanlari + ham baytlar; `<mod>StatusRegistersRead(handle, &sStatus)`.
- Dizi donuslu op (`returns: voltages[8]`): `S<Mod>Voltage { unsigned short usArrVoltage[8]; }`,
  `<mod>VoltageRead(handle, &sVoltage)`. Skaler op'lar `int*` / `unsigned short*` alir.
- Handle HER ZAMAN Xilinx surucu ornegi isaretcisidir (`XIic*`, `XIicPs*`, `XSpi*`, `XSpiPs*`);
  kural: ornek en alt seviyeye kadar iner. AXI IIC'de polled cagrilar (`xiic_l.h`) taban adresi
  ornekten (`spIic->BaseAddress`) alir; ornek ilk `DeviceInit`'te `XIic_LookupConfig/CfgInitialize`
  ile kurulur.

```c
SLtc2991Status sDurum;
SLtc2991Voltage sVoltaj;
static XIic S_sIic;                                /* AXI IIC ornegi (xiic.h) */
ltc2991DeviceInit(&S_sIic);                       /* ornek kurulur + dinamik mod */
ltc2991StatusRegistersRead(&S_sIic, &sDurum);     /* sDurum.uiV1Ready, sDurum.uiBusy ... */
ltc2991VoltageRead(&S_sIic, &sVoltaj);            /* sVoltaj.usArrVoltage[0..7] mV */
```

**CIT ust katmani (`cit/`):**

| Dosya | Icerik |
|---|---|
| `cit/cit_ortak.h/.c` | `SCitLimit {iMin, iMax, uiLimitVar, uiEtkin}`, `citLimitDegerlendir()`, `CIT_OK/NOK/HATA` |
| `cit/<mod>_cit.h/.c` | `S<Mod>CitLimit` (olcum/kanal basina limit; `<MOD>_CIT_LIMIT_VARSAYILAN` spec `config.cit.measurements`'tan), `S<Mod>Cit` (bayraklar + `S<Mod>Status sDurum` + olcum struct'lari + `uiHataSayac/uiNokSayac`), `<mod>CitInit()`, `<mod>CitRead()` |
| `cit/sistem_cit.h/.c` | `SSistemCitBus` (denetleyici handle'lari), `SSistemCitLimit`, `SSistemCit`; `sistemCitBusVarsayilan/Init/Read()` |

`<mod>CitRead` surucu fonksiyonlarini cagirir; `sBayraklar` icinde op basina `ui<Op>Okundu`
(okuma basarili) ve olcum/kanal basina `ui<Ad>Ok` (okundu VE min <= deger <= max; etkin degilse 1)
bitleri dolar. Kritik/uyari ayrimi yoktur: aralik disi = NOK. Limitler calisma zamaninda degistirilebilir; NULL verilirse spec varsayilani.

```c
static SSistemCitBus S_sBus;
static SSistemCitLimit S_sLimit = SISTEM_CIT_LIMIT_VARSAYILAN;
static SSistemCit S_sCit;

sistemCitBusVarsayilan(&S_sBus);                 /* XPAR taban adresleri / surucu ornekleri */
sistemCitInit(&S_sBus);                          /* her entegrenin DeviceInit'i (ilk hata doner) */
S_sLimit.sU2Ltc2991.sV1.iMin = 3135;             /* isteğe bagli: canli limit */
S_sLimit.sU2Ltc2991.sV1.iMax = 3465;
S_sLimit.sU2Ltc2991.sV1.uiLimitVar = 1U;
sistemCitRead(&S_sBus, &S_sLimit, &S_sCit);      /* S_sCit.sU2Ltc2991.sBayraklar.uiV1Ok ... */
```

Kapsam disi (CIT dosyasi uretilmez, README'de listelenir): GPIO hat cihazlari, komut
tabanli SPI flash, I2C EEPROM.

**"CIT kostur" akisi (CIT ekrani / Test Bench):** host `CIT_RUN` gonderir; ajan
`tests/spec2code_cit.c` `boardCitRun()` -> `spec2codeTestbenchBoardInit()` (denetleyiciler)
-> `SSistemCitBus` ajanin handle getter'larindan doldurulur -> `cit/sistem_cit.c`
`sistemCitRead()` -> `cit/<mod>_cit.c` `<mod>CitRead()` -> `drivers/<mod>.c` okuma
fonksiyonlari. Sonuc manifest sirasiyla `SBoardCit`'e kopyalanir (deger + okuma-basarili
biti); limit/OK-NOK karari host'ta canli yapilir. Ekranda gordugun CIT sonucu, projene
tasiyacagin `cit/` ve `drivers/` kodunun KENDISINDEN gelir. Anlik okumalar ("sicaklik oku"
gibi tek op'lar) ise ajan dispatch'inden dogrudan surucu fonksiyonunu cagirir.

**Self-test (`tests/<mod>_test.c`):** yalniz `tests_requested: ["self_test"]` olan cihazlar
icin uretilir; `<mod>SelfTest(handle)` = DeviceInit + butun okuma fonksiyonlari (ilk hatada
durur), loglar `dbg_printf(DEBUG_LEVEL_INFO, ...)` ile. Test Bench'te cihazin `self_test`
op'u olarak kosulur; ayri bir harness/FreeRTOS gorevi ya da `spec2code_selftest_main.c`
runner'i ajanli projede uretilmez (yalniz ajansiz projede `main()` runner'i sahnelenir).

### Seviyeli debug print: `dbg_printf`

Uretilen kodun tek log kapisi `drivers/dbg_printf.h/.c`'dir; kullaniciya giden katmanda
oldugundan adinda `spec2code` yoktur ve kendi projene suruculerle birlikte tasinir.

**Seviyeler** (`dbg_printf.h`):

| Sabit | Deger | Ne icin |
|---|---|---|
| `DEBUG_LEVEL_ALWAYS` | 0 | banner vb. kesin yazilacaklar |
| `DEBUG_LEVEL_ERROR` | 1 | hata durumlari (**varsayilan esik**) |
| `DEBUG_LEVEL_WARNING` | 2 | hataya sebep olabilecek uyarilar |
| `DEBUG_LEVEL_MSG` | 3 | mesaj gonderim/alim katmani (S2C-MSG RX/TX) |
| `DEBUG_LEVEL_INFO` | 4 | debug'a faydali ekstra bilgi |
| `DEBUG_LEVEL_TRACE` | 5 | I2C/SPI gelen-giden baytlar (en alt katman) |

**Kural:** bir print ancak seviyesi o an ayarli esikten KUCUK ya da ESITSE basilir. Esik
WARNING (2) ise ALWAYS, ERROR ve WARNING basilir; MSG/INFO/TRACE bastirilir.

**API:**

```c
#include "dbg_printf.h"

dbg_printf(DEBUG_LEVEL_ALWAYS, "kart yazilimi v%u basladi", uiSurum);   /* her zaman */
dbg_printf(DEBUG_LEVEL_ERROR, "LTC2991 init dustu: status=%d", iStatus);
dbg_printf(DEBUG_LEVEL_INFO, "yazilacak veri: %d", iVeri);              /* esik >= 4 ise */

dbgLevelSet(DEBUG_LEVEL_INFO);          /* calisma zamaninda esik; 0..5'e kirpar, yeniyi dondurur */
unsigned int uiEsik = dbgLevelGet();    /* gecerli esik */
const char* cpAd = dbgLevelName(uiEsik);/* "error", "info" ... */
```

- Cikti: kayitli bir sink yoksa `xil_printf` (satir sonu `
` eklenir). Cikti hedefini
  degistirmek icin `dbgSinkSet(fp)` ile `void fp(unsigned int uiLevel, const char* cpBody)`
  imzali bir fonksiyon kaydet (govde satir sonsuz gelir).
- Format govdesi en fazla 159 karakterdir (`DBG_BODY_MAX`); uzun mesajlar kesilir.
- Tamponlar statiktir (tek baglam, bare-metal): kesme icinden cagirma.
- Bus izleri: suruculer her transferi `dbgTraceI2c(adres, reg, 'r'|'w', veri, boy)` ve
  `dbgTraceSpi(cs, tx, rx, boy)` ile TRACE seviyesinde basar
  (`TRACE|bus=i2c|addr=0x48|reg=0x0A|dir=r|len=1|data=0C`); dusen transfer
  `dbg_printf(DEBUG_LEVEL_ERROR, "TRACEERR|bus=i2c|addr=..|reg=..|asama=p|status=-1")`
  uretir (asama: `w` yazma, `p` pointer, `r` okuma, `m` mux). Esik TRACE'in altindayken
  hex formatlama hic yapilmaz (maliyet sifira yakin).

**Test bench'te:** ajan `spec2codeLogSinkSet()` ile bir sink kaydeder; her satir
`S2C-LOG|<A/E/W/M/I/T>|govde` cercevesine sarilip UART/DCC'den host'a gider. TRACE ve
TRACEERR govdelerine komut id'si eklenir (`TRACE|id=7|bus=...`) ki Akis ekrani izi ilgili
istekle eslestirsin. Esik baglanti kartindaki secici ya da `log_level` komutuyla (deger 0..5)
canli degistirilir; kart varsayilan olarak ERROR ile acilir.

**Kendi projende:** `drivers/dbg_printf.c`'yi derlemeye ekle; sink kaydetmezsen
`xil_printf` uzerinden STDOUT UART'ina yazar. Uretimde gurultuyu kesmek icin
`dbgLevelSet(DEBUG_LEVEL_ERROR)` (varsayilan) yeterlidir; sorun kovalarken
`DEBUG_LEVEL_TRACE` bus baytlarini gosterir.

### Simulasyon ve karisik mod (`tests/sim/`)

Sanal cihazlar YALNIZ test bench derlemesine girer; surucu ve cit dosyalari sanal cihazi
bilmez. Mekanizma: `tests/sim/spec2code_sim_xilinx.h` derleme bayragi `-include` ile her
ceviri birimine girer ve Xilinx veri-yolu fonksiyonlarini (`XIic_DynSend/DynRecv`,
`XIicPs_Master*Polled`, `XSpi_SetSlaveSelect/Transfer`, `XSpiPs_*`) `spec2codeSim*`
sarmalayicilarina yonlendirir. Sarmalayici adres/CS'i kayitli sanal cihaz zincirinde bulursa
simulatoru kosturur, bulamazsa GERCEK Xilinx fonksiyonunu cagirir (karisik mod). Vitis
uretimi bayragi ve include yolunu kendisi ekler.

- `tests/sim/spec2code_sim.h/.c`: cihaz kaydi (`spec2codeSimI2cEkle/Kaldir`,
  `spec2codeSimSpiEkle/Kaldir`), sanal TCA9548A switch, sarmalayicilar.
- `tests/sim/<mod>_sim.h/.c`: descriptor'dan uretilen register modeli + davranis bloklari;
  `<mod>SimKur()`, `<mod>SimHataAyarla()`, `<mod>SimRegisterYaz()`.
- Ajan (`<proje>_testbench_ops.c`): `simulate` isaretli cihazlari ilk dispatch'te kaydeder
  (`spec2codeSimHazirla`); dispatch dogrudan GERCEK surucuyu cagirir, sarmalayici yoktur.
  Bir mux'un arkasindaki HER cihaz sanalsa sanal switch de kaydedilir.

**Sematikte sanal cihaz isareti:** entegre kutusundaki "gercek / sanal" piline tikla. Spec'e
`simulate: true` yazilir, kutu eflatun olur ve test bench ajani o cihazin butun op'larini
simulatorden cevaplar; ayni hattaki gercek cihazlar gercek kalir. Yalniz I2C register ve
SPI TICS-register cihazlari isaretlenebilir.

**Hata enjeksiyonu:** `ltc2991SimHataAyarla(&sim, SPEC2CODE_SIM_HATA_NACK)` cihazi hattan
kaldirir (her erisim duser); `SPEC2CODE_SIM_HATA_HAZIR_YOK` READY bitlerini hic kurmaz
(poll zaman asimi).

Davranisli simulatorler (statik register modelinin ustune):

| Entegre | Davranis | Senaryo API'si |
|---|---|---|
| LTC2991 | READY bitleri (repeated / tek-atis tetik, LSB okununca temizlenir), 2991f kod uretimi, STATUS_HIGH ro bit korumasi | `ltc2991SimKanalAyarla(mV)`, `SicaklikAyarla(santi-C)`, `VccAyarla(mV)` |
| LTC2945 | SHUTDOWN degilse her okumada SENSE/VIN/ADIN 12-bit kodlari + 24-bit guc carpimi, MAX/MIN izleme, ADC_BUSY, FAULT_CLEAR | `ltc2945SimAkimAyarla(mA, Rsense mohm)`, `SenseAyarla(uV)`, `VinAyarla(mV)`, `AdinAyarla(uV)` |
| DS1682 | Her I2C okuma isleminde ETC ilerler (vars. 4 tik = 1 s), EVENT sayaci + CONFIGURATION[0] (bit 16), ETC >= ALARM -> ALARM_FLAG, RESET_COMMAND 0x55 + RESET_ENABLE sifirlar | `ds1682SimEtcAyarla(s)`, `OlayAyarla(n)`, `OlayEkle(n)`, `TikAdimiAyarla(tik)` |
| LMK04832 | `register_model` cercevesi cozulur; RB_PLL_STATUS DLD/LOST bitleri | `lmk04832SimKilitAyarla(&sim, pll1, pll2)` |

Host tarafinda `tests/xilinx_stubs/` (xil_types/xstatus/xiic_l/xspi stub'lari) ile
`drivers + cit + tests/sim` gcc'de derlenip kosulur (`tests/test_cit_layer.py`).

**Kart verisi (`sense_resistor_mohms` gibi):** bazi donusumler kartta belirlenen bir
degere ihtiyac duyar (LTC2945 `current_read` icin sont direnci). Descriptor bunu
`convert.scale_den_config` ile ister; codegen degeri `device.config` icinde arar ve op
acikca istenmisse deger yoksa `device.config.<anahtar> gerekli` hatasiyla durur.
Schematic'te cihazi secince config editoru bu alanlari **Kart verisi** basligiyla
gosterir; istenen op icin bos birakilan alan kirmizi uyarilir.

## 11. Code Viewer ve Download

Code viewer'da:

- Generated dosyalari hiyerarsik agacta gorursun.
- Tek dosya indirebilirsin.
- Tum generated output'u zip olarak indirebilirsin.
- Vitis-ready export zip indirebilirsin.
- QC bulgularini aktif dosya ozelinde gorebilirsin.
- Test bench manifest ve agent kaynaklarini `tests/` altinda gorebilirsin.

## 12. Test Bench

Test Bench sayfasi, generate sonucu uretilen su manifest dosyasindan beslenir:

```text
tests/spec2code_testbench_manifest.json
```

Generate sonucu ayrica hedef uygulamaya eklenebilecek **S2C-MSG binary mesaj
katmani** kaynaklarini uretir:

```text
tests/spec2code_mesaj.c/.h                 (kodek: parser + dispatch koprusu)
tests/spec2code_testbench_protocol.c/.h
tests/spec2code_testbench_log.c/.h
tests/spec2code_testbench_trace.c/.h
tests/<project>_testbench_ops.c/.h
```

Platforma gore ayrica UART, lwIP (TCP) veya CoreSight DCC tasiyici uretilir
(asagida). Metin satir protokolu (eski `S2C|id=..|op=..`) TAMAMEN KALKMISTIR;
uc tasiyicinin ucu de ayni **12 baytli little-endian binary cerceveyi** tasir:

```c
typedef struct
{
    unsigned int uiMesajKomut;  /* mesaja ozgu ID           */
    unsigned int uiMesajBoyu;   /* govde boyu (byte), 4 katı */
    unsigned int uiMesajSayac;  /* yon basina artan sayac    */
} SMesajBaslik;
```

Her mesaj kataloglanmistir (`backend/data/message_catalog.json`); tam ID/govde
tablosu ve hata kodlari uygulamadaki **Arayuz/YATT** sayfasindan (self-contained
HTML/MD olarak da) indirilebilir — bu userguide kod uretecinin sozlesmesini
tekrar etmez, tek dogruluk kaynagi YATT sayfasidir.

Bu agent dosyalari kart tarafinda `spec2codeMesajBesle()` / `spec2codeMesajIsle()`
fonksiyonlarini sunar (eski `spec2codeTestbenchDispatchLine()` SILINDI). Windows
UI dogrudan donanim bus'ina dokunmaz; secilen tasiyici (TCP, seri UART veya
CoreSight DCC) uzerinden karta baglanir ve binary cerceveleri bu baglanti
uzerinden gonderir. Kart tarafi gelen her bayt/chunk/segment'i parser'a
besleyip (`spec2codeMesajBesle`) tamamlanan cerceveyi isler (`spec2codeMesajIsle`)
ve yanit cercevesini ayni baglanti uzerinden geri dondurur.

Platform `zynq_ultrascale` ise ve `xparameters.h` icinden PS Ethernet controller'i
(`XEmacPs`) yakalandiysa Spec2Code ek olarak hazir lwIP TCP agent uretir:

```text
tests/spec2code_testbench_lwip.c/.h
tests/spec2code_testbench_lwip_main.c/.h
```

Bu dosyalar Zynq UltraScale+ PS Ethernet uzerinden lwIP TCP server acar. Vitis
workspace uretiminde standalone runtime icin BSP `RAW_API`, FreeRTOS runtime icin
BSP `SOCKET_API` mode secimi denenir. Varsayilan port `5000`, varsayilan IP
`192.168.1.10` olarak gelir. Bunlari
Vitis compile define veya generated header uzerinden su makrolarla degistirebilirsin:

```text
SPEC2CODE_TESTBENCH_TCP_DEFAULT_PORT
SPEC2CODE_TESTBENCH_IP_ADDR0..3
SPEC2CODE_TESTBENCH_NETMASK_ADDR0..3
SPEC2CODE_TESTBENCH_GATEWAY_ADDR0..3
SPEC2CODE_TESTBENCH_MAC0..5
```

PS UART veya CoreSight DCC uzerinden baglanmak istersen (Ethernet yoksa/JTAG
disinda erisim yoksa) generate ayrica su dosyalari uretir:

```text
tests/spec2code_testbench_uart.c/.h + _main.c/.h
tests/spec2code_testbench_coresight.c/.h + _main.c/.h
```

Generated lwIP/UART agent ayni zamanda schematic'te kullanilan `XIicPs`, `XSpiPs`
ve `XQspiPsu` controller handle'larini initialize eder. Test bench dispatch
icindeki weak hook'lar bu dosyada strong olarak override edilir; yani UI'dan
gelen operasyon dogrudan generated driver fonksiyonuna gider.

Test Bench sayfasinda:

- Baglanti tipi secilir: **TCP**, **Seri** (UART/COM portu + baud) veya
  **CoreSight** (Vitis kurulum yolu + JTAG cekirdek); host/port yalniz TCP'de,
  timeout hepsinde girilir.
- **Baglan** ile kart tarafindaki agent'a tek session acilir; bu session Test
  Bench, UART konsolu, Bring-up, Registers ve telemetri ekranlari arasinda
  ORTAKTIR (bir kez baglanmak yeter).
- Generate edilmis manifest icindeki entegre secilir.
- Entegre icin gercekten uretilmis operasyonlar listelenir.
- Register read/write icin register adi veya manuel register address verilebilir.
- Flash/EEPROM gibi adresli islemlerde address, length ve data hex alanlari
  kullanilir; flash cihazlarinda ayrica "Dosya transferi" modu 256 baytlik
  komutlara bolunmus toplu okuma (.bin indirme) ve sayfa hizali yazma (.bin'den
  page_program + istege bagli geri-okuma dogrulamasi) sunar.
- Riskli islemler (`init`, `write`, `program`, `erase`) gonderilmeden once onay ister.
- **Gonder** ile komutlar mevcut session uzerinden gider; her komutta yeni
  baglanti acilmaz.
- Baglanti koparsa UI bunu hata olarak gosterir ve tekrar **Baglan** gerekir.
- Response icindeki `ok`, `status`, `value`, `data` ve `message` alanlari
  (binary cerceveden cozulmus) okunabilir sekilde gosterilir; ham istek/yanit
  kutulari artik cerceve ozeti + hex gosterir (eski ham `S2C|...` metin satiri
  DEGIL).
- Agent debug esigi (`dbg_printf`: 0 always, 1 error [varsayilan], 2 warning, 3 msg,
  4 info, 5 trace) baglanti kartindan canli degistirilir (`log_level` komutu); yalniz
  esikten kucuk ya da esit seviyeli printler basilir. TRACE seviyesi I2C/SPI baytlarini
  Akis ekranina tasir.

LTC2991 icin test bench uzerinden tipik faydali operasyonlar:

- `voltage_read`: 8 kanal, milivolt cinsinden donusturulmus deger (LSB 305.18 µV).
- `current_read`: current-shunt veya differential kullanilan pair'ler icin raw channel code okur.
- `temperature_read`: internal temperature, 0.01 °C cozunurlukte donusturulmus deger.
- `vcc_read`: VCC, milivolt cinsinden donusturulmus deger.
- `register_read` / `register_write`: 8-bit register seviyesinde tek byte okuma/yazma yapar.

`current_read` dogrudan amper hesaplamasi yapmaz. LTC2991'de akim, shunt uzerindeki
differential raw code ve board tarafinda bilinen shunt milliohm degeriyle application
katmaninda hesaplanmalidir.

Karti test etmeden once tum akislarin gercek donanimda dogrulanmasi icin
`docs/s2cmsg_parite_listesi.md` kontrol listesini kullan (uc tasiyicinin
ucunde de tekrarlanmasi gereken adimlar + bilinen v1 kisitlari orada).

## 13. Vitis Workspace Uretimi

Generate tamamlandiktan sonra **Vitis workspace** paneli gorunur.

Girilmesi gereken bilgiler:

- Vitis dizini: ornek `C:\Xilinx\Vitis\2024.2`
- `.xsa` dosyasi: klasor degil, dogrudan dosyanin tam yolu; ornek `D:\Board\export\system.xsa`
- Workspace dizini: ornek `D:\VitisWorkspaces\spec2code`
- Temp/Staging dizini: ornek `D:\VitisTemp\spec2code`
- Platform proje adi: ornek `my_io_board_platform`
- System proje adi: ornek `my_io_board_system`
- Application proje adi: ornek `my_io_board_app`
- Processor: ornek `psu_cortexa53_0`

Backend Vitis dizininden `xsct.bat` veya `xsct` bulur. Sonra:

1. Vitis/XSCT surumunu algilar.
2. `.xsa` dosyasini ve generated kaynaklari kullanicinin verdigi temp/staging dizinine kopyalar.
3. XSA icindeki non-Xilinx/AMD custom PL IP adaylarini `.hwh` uzerinden algilar.
4. lwIP test bench dosyasi varsa BSP icin lwIP library ve API mode secimini dener.
5. Custom PL IP driver policy `auto_none` ise aday IP'lerin BSP driver'ini `none`
   yapmayi dener; gerekirse source'suz custom IP `make.libs` dosyalarini no-op
   hale getirerek BSP build'in `*.c` literal hatasina dusmesini engeller.
6. `spec2code_create_workspace.tcl` dosyasini yazar.
7. XSCT ile once adlandirilmis platform/system/application akisini dener.
8. `app build` calistirir.
9. Workspace ve staging dizinlerinde application adiyla eslesen `.elf` dosyasini
   dogrular.

Temp/Staging dizini altinda olusan yardimci klasor:

```text
<temp-staging-dizini>\<vitis_job>\
  hw\
  src\
  spec2code_create_workspace.tcl
  spec2code_self_heal_workspace.tcl
  spec2code_vitis_manifest.json
  logs\xsct_stdout.log
  logs\xsct_stderr.log
  logs\xsct_self_heal_stdout.log
  logs\xsct_self_heal_stderr.log
```

Hata olursa once UI'daki son progress mesajina, sonra `xsct_stderr.log` dosyasina
bak. En sik hatalar:

- Yanlis Vitis dizini.
- Yanlis `.xsa` path'i.
- XSA icinde beklenen processor instance adinin farkli olmasi.
- Vitis surumunde template adinin farkli davranmasi.
- BSP/toolchain eksigi.
- lwIP agent uretilmis ama Vitis BSP icinde lwIP library/API mode enable edilememis olmasi.
- PL tarafinda driver'i olmayan custom IP'nin BSP tarafinda driver ile build edilmeye calisilmasi.

lwIP agent uretilirse Vitis panelinde `lwIP RAW_API` veya `lwIP SOCKET_API` rozeti
gorunur ve staging manifest icinde `requires_lwip: true` ile `lwip_api_mode`
yazar. Tcl script `lwip220`, `lwip213`, `lwip211` ve `lwip202` library adlarini
sirayla dener. Standalone icin `RAW_API`, FreeRTOS icin `SOCKET_API` secmeye
calisir. Kullanilan Vitis surumunde bu isimler veya `api_mode` parametresi
farkliysa BSP/domain ayarlarindan lwIP library'yi ve API mode'u manuel kontrol
etmek gerekebilir.

Custom PL IP driver policy varsayilan olarak `auto_none` gelir. Bu modda XSA
icindeki `.hwh` dosyasi okunur; `VLNV` vendor'i `xilinx.com` veya `amd.com`
olmayan `PERIPHERAL` moduller custom PL IP adayi sayilir. Ayrica
`xilinx.com:ip:<custom_ad>` gibi gorunen ama `axi_gpio`, `clk_wiz`, `xlconcat`,
`smartconnect` gibi standart Xilinx IP ailelerine benzemeyen PL peripheral'lar da
custom-like adayi sayilir. Tcl script bu instance'lar icin
`bsp setdriver -ip <instance> -driver none` varyantlarini dener.
Vitis buna ragmen `libsrc/<custom_ip>*/src/make.libs` altinda source'suz driver
build etmeye calisirsa Spec2Code bunu uc katmanda yakalamaya calisir: staged
`.xsa` icindeki driver `make.libs` dosyalarini Vitis gormeden once patchler, Tcl
script `bsp regenerate`/`app build` oncesi workspace'i tarar ve XSCT calisirken
host watcher application, FSBL ve PMU/PMUFW BSP `libsrc` klasorlerini izler.
Vitis build log'u `psu_cortexa53_0/libsrc/<driver>/src/make.libs` gibi bir hedef
gosteriyor ama taramada fiziksel dosya bulunmuyorsa self-heal ayni processor BSP
koku altinda sentetik no-op `make.libs` olusturup recovery build'i dener.
Orijinal var olan `make.libs` dosyalari `.spec2code_backup` olarak saklanir. Bu,
driver dosyasi olmayan custom IP'lerin BSP build'i bozmasini engellemek icin
tasarlanmistir. Vitis panelindeki `BSP patch N` rozeti toplam patch sayisini
gosterir; Doctor icindeki `Log make.libs hedefleri` ise log'da gorulen hedefleri
ayrica listeler. `BSP patch 0`, hic patch uygulanmadigi veya hedefin ancak
self-heal sirasinda sentetik olusturulabildigi anlamina gelebilir. Eger custom IP
gercek ve kullanilacak bir sirket driver'i ile geliyorsa Vitis panelinde
`BSP default'u koru` secilmelidir.

### Vitis Doctor ve Lokal Self-Heal

Vitis workspace panelindeki **Vitis Doctor** bolumu tamamen lokal calisir ve
otomatik olarak disari dosya, log veya zip aktarmaz. Airgap kullaniminda buradaki
soyut bilgiler debug surecini hizlandirmak icin tasarlanmistir:

- `S2C-VITIS-...` hata kodlari.
- Self-heal ile kapanmis hata kodlari; bunlar aktif blokaj degil, onceki denemede
  gorulup recovery build ile asilmis durumlardir.
- Custom IP aday sayisi.
- XSA icinde kac `make.libs` bulundugu.
- Workspace/FSBL/PMU/application BSP tarafinda kac riskli `make.libs` goruldugu.
- `BSP patch N` sayisi.
- Self-heal denenip denenmedigi ve sonucu.
- Application ELF sayisi ve beklenen ELF adi.

Bu bilgilerden yalnizca hata kodunu veya sayisal ozeti paylasmak genelde yeterli
olur; sirket icindeki path, IP adi veya log dosyasini disari cikarmak gerekmez.

Custom IP BSP kaynakli `*.c Invalid argument` hatasi gorulurse Spec2Code ilk
build sonrasinda workspace/temp altini tekrar tarar. Patchlenecek source'suz
`make.libs` bulunursa mevcut workspace'i bozmadan
`spec2code_self_heal_workspace.tcl` calistirilir. Bu recovery script
platform/application projesini bastan kurmaz; mevcut workspace uzerinde
driver-none, `bsp regenerate` ve `app build` dener. Log'da `make.libs` hedefi
olup dosya taramada yoksa self-heal sentetik no-op `make.libs` olusturabilir; bu
path `Sentetik make.libs` olarak gorunur. Self-heal basarili olursa panelde
`self-heal gecti` rozeti gorunur. Bu rozet icin recovery XSCT donus kodunun
basarili olmasi yetmez; recovery logunda `cc1.exe fatal error`, `make: ***`,
`Failed to build` veya benzer build-fatal imzalari kalmamali. Basarisiz olursa
Doctor panelindeki hata kodu ve sayilar kok sebebi anlamak icin kalir.

XSCT/app build hata vermese bile application adiyla eslesen `.elf` dosyasi
bulunamazsa workspace `hazir` sayilmaz. Bu durumda `S2C-VITIS-ELF-009` hata kodu
gosterilir ve Doctor panelinde beklenen ELF adi ile bulunan diger `.elf`
ornekleri listelenir. Bu ozellikle `BSP patch` basarili gorunup `Debug` altinda
application ELF bulunamayan durumlari ayirt etmek icindir.

Vitis compile error mapper, uzun build log icindeki bazi yaygin hatalari UI'da
ayri liste olarak gosterir:

- Missing include/header.
- Undefined reference.
- Multiple definition.
- Eksik veya uyumsuz `XPAR_*` macro.
- Unknown type veya implicit function declaration.
- Yanlis processor/XSA/platform secimi.

Mapper raw log'u gizlemez; yalnizca ilk aksiyon alinacak ipucunu one cikarir.

## 14. Kodlama Standardi

Spec2Code sabit default coding standard kullanir. Kullanici Word, Markdown veya
ayri JSON standard dokumani vermez.

Kurallarin tamami, onek bilesim tablosu ve ornekleri icin ayrintili referans:
`docs/kodlama_standardi.md`.

Ozet kurallar:

- Fonksiyon isimleri camelCase: `tca9548aChannelSelect`.
- Primitive C tipleri kullanilir: `unsigned char`, `unsigned int`.
- `uint8_t`, `uint16_t`, `uint32_t` gibi fixed-width typedef kullanilmaz.
- Hungarian prefix kullanilir:
  - `unsigned char -> uc`
  - `char -> c`
  - `unsigned short -> us`
  - `short -> s`
  - `unsigned int -> ui`
  - `int -> i`
  - `unsigned long -> ul`
  - `unsigned long long -> ull`
- Struct typedef adi buyuk `S` ile baslar: `SOrnekStruct`.
- Struct degiskeni kucuk `s` prefix'i alir: `SOrnekStruct sMyStruct;`.
- Struct pointer `sp` prefix'i alir.
- Diger pointer'lar tip prefix'i + `p` kullanir.
- Pointer yildizi tipe bitisik yazilir: `XIicPs* spIic`.
- Array'ler tip prefix'i + `Arr` kullanir.
- Global degiskenler `G_`, static degiskenler `S_` ile baslar.
- Allman brace stili kullanilir.
- Bitfield uyelerinde Hungarian prefix kullanilmaz.

## 15. LLM Kullanimi

LLM varsayilan olarak kapali gelir. Acmak icin OpenAI-compatible endpoint,
tam model adi ve gerekirse API key girilir.

Desteklenen model ailesi uygulama tarafindan sinirlanmaz. GLM, Qwen, Kimi veya
baska bir OpenAI-compatible model kullanilabilir.

LLM generate akisi icinde yardimci roldedir:

- Cevap bos, cok uzun, eksik veya timeout olursa hata net gosterilir.
- LLM output dogrudan dosyaya yazilmaz.
- Aday dosya deterministic QC'den gecmeden kabul edilmez.
- Aday reddedilirse mevcut deterministic output korunur.

## 16. Air-gap Notlari

Air-gap Windows ortaminda executable paket en kolay yoldur. Tek gereken:

- `Spec2Code.exe`
- `changelog.md`
- `userguide.md`
- `glm52_handoff.md`
- Opsiyonel LLVM/Cppcheck kurulumlari
- Opsiyonel Vitis kurulumu
- Opsiyonel lokal/internal LLM endpoint'i

Source uzerinden gelistirme yapacaksan GitHub Release icindeki source archive ve
offline dependency cache gerekir. Bu kullanici paketinin konusu degildir; source
developer akisi icin repo dokumanlarina bakilmalidir.

## 17. Desteklenen Entegreler

Bu surumde desteklenen baslica entegreler:

- TCA9548A
- LTC2991
- MT25Q128
- MT25QU02G
- AD7414
- TMP101
- SHT21
- 24LC32A
- DS1682
- LTC2945
- ADAR1000
- LMK04832
- LMX2820
- LMX1204
- LMX1205
- LTM4681
- ADT7420 (I2C sicaklik sensoru; Digilent Nexys A7 kart ustu, 0x4B)
- S25FL128S (SPI NOR flash, 3-bayt adres; Nexys A7 konfigurasyon flash'i)

Desteklenen cihaz listesi Catalog ekraninda gorulur. Bir cihaz Catalog'da yoksa
deterministik descriptor/codegen destegi yoktur.

## 18. Sorun Giderme

**Browser aciliyor ama eski surum gibi davranıyor**

- Eski backend hala calisiyor olabilir.
- Tum eski Spec2Code sureclerini kapat.
- Yeni exe'yi tekrar calistir.
- Uygulamanin ust kismindaki versiyonu kontrol et.

**Generate tamamlanmiyor**

- Generate console'daki son hata satirini oku.
- LLM aciksa timeout, bos cevap veya context disi cevap olabilir.
- QC tool path'lerini `/api/health` ile kontrol et.

**Windows'ta UnicodeDecodeError benzeri hata**

- Yeni surumu kullandigindan emin ol.
- Vendor dosyalari farkli encoding ile geldiyse parser toleransli okur; hata
  devam ederse problemli dosyayi ayri incelemek gerekir.

**Vitis workspace olusmuyor**

- Vitis path'ini kontrol et.
- `.xsa` path'ini kontrol et.
- Temp/Staging path'inin yazilabilir oldugunu kontrol et.
- Processor adinin XSA icindeki gercek processor instance adi oldugundan emin ol.
- UI'da gorunen `staging_path` altindaki `logs\xsct_stderr.log` dosyasini oku.
- UI'da Vitis compile hata eslestirme listesi ciktiysa kategori ve oneriyi takip et.

**Test Bench karta baglanmiyor**

- TCP: kart tarafinda agent'in (lwIP TCP server) calistigindan, host/port
  alanlarinin Windows makineden ulasilabilir oldugundan ve firewall/air-gap ag
  kurallarinin engellemedigi emin ol. Seri: dogru COM portu/baud secildiginden
  emin ol. CoreSight: Vitis kurulum yolunun/JTAG baglantisinin dogru oldugundan
  emin ol (ilk baglanti xsdb acilisi nedeniyle 10-30 sn surebilir).
- Kart tarafi gelen bayt/chunk/segment'leri `spec2codeMesajBesle()` fonksiyonuna
  besleyip tamamlanan cerceveyi `spec2codeMesajIsle()` ile islemeli ve yanit
  cercevesini ayni baglanti uzerinden geri yazmalidir (eski
  `spec2codeTestbenchDispatchLine()` artik yok — karttaki firmware bu arktan
  ONCEKI bir surumse ilk komutta timeout/GECERSIZ_MESAJ alinir; Generate +
  Vitis workspace ile yeniden derleyip YUKLEMEK gerekir).
- UI once **Baglan** demeden **Gonder** komutunu aktif etmez; baglanti durumu kopuksa yeniden baglan.

## 19. Release Dosyalari

Executable release zip'i sade tutulur:

```text
Spec2Code.exe
changelog.md
userguide.md
glm52_handoff.md
```

`changelog.md` en yeni surumden baslayarak tum gecmis release degisikliklerini
icerir. `userguide.md` bu dosyadir. `glm52_handoff.md`, airgap Windows'ta kaynak
kod uzerinde gelistirme yapacak lokal GLM 5.2 FP-8 modeli icin kapsamli gelistirme
handoff'udur: repo haritasi, mimari, kodlama standardi, QC dongusu, calistirma/test
komutlari, gorev bataryasi ve Vitis/XSCT debug brief'i icerir.
