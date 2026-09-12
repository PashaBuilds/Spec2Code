# Spec2Code Kullanim Kilavuzu

Bu dosya release paketinin icinde gelir. Amaci, Spec2Code'u kullanan bir gomulu
yazilimcinin uygulamayi acip proje kurmasina, kod uretmesine, ciktiyi kendi
firmware'ine tasimasina ve gercek kartta dogrulamasina yetecek bilgiyi tek yerde,
kisa ve dogru vermektir. Ayrintili protokol tablosu (YATT) ve kodlama standardi
kendi belgelerindedir; burada tekrar edilmez.

Icindekiler:

1. Spec2Code nedir
2. Calistirma
3. Yardimci araclar
4. Uctan uca akis
5. Ekranlar
6. Setup: platform, `xparameters.h`, Vivado ile XSA
7. Schematic: entegreler, kartlar, kimlikler
8. Generate: uretilen kod ve katmanlar
9. Kodu kendi projene tasima
10. Karta baglanma
11. Test Bench
12. CIT (Cihaz Ici Test)
13. Bring-up, Registers, Akis, Register Map, Arayuz/YATT
14. Vitis workspace ve Board'da calistirma
15. Kodlama standardi (ozet)
16. LLM kullanimi
17. Air-gap notlari
18. Desteklenen entegreler
19. Sorun giderme
20. Release dosyalari

---

## 1. Spec2Code nedir

Spec2Code, Xilinx/AMD (Zynq-7000, Zynq UltraScale+, Versal, MicroBlaze) kartlarda
I2C, SPI/QSPI ve GPIO ile bagli entegreler icin **deterministik** C surucu, CIT
(cihaz ici test) katmani, test bench ajani ve Vitis workspace ureten lokal bir web
uygulamasidir. Bulut yoktur: `Spec2Code.exe` bilgisayarinda bir backend ve
tarayici arayuzu baslatir.

Uretim akisi bastan sona "spec"e dayanir: Setup + Schematic ekranlarinda kurdugun
model bir JSON spec'e yazilir, kod bu spec'ten uretilir, ayni spec test bench
manifestini ve YATT'i besler. Elle duzenlenecek dosya yoktur; degistirmek icin
ekranda degistirip yeniden uretirsin.

---

## 2. Calistirma

Release paketi:

```text
Spec2Code.exe
changelog.md
userguide.md
glm52_handoff.md
```

```powershell
.\Spec2Code.exe                              # varsayilan http://127.0.0.1:8077, tarayici acilir
.\Spec2Code.exe --host 127.0.0.1 --port 8078 # port degistir
.\Spec2Code.exe --no-browser                 # tarayici acma
```

Kaynak koddan calistiriyorsan `python run_spec2code.py` ayni parametreleri alir.
Eski bir surum hala 8077'yi dinliyorsa uygulama bunu fark edip uyarir; eski sureci
kapatip tekrar baslat. Ust cubuktaki surum etiketi her zaman calisan surumu gosterir.

Uygulama yazdigi her seyi (uretilen kod `outputs\`, kaydedilen spec'ler `specs\`,
yuklenen XSA'lar `uploads\`, import edilen katalog, `user_descriptors\`)
`Spec2Code.exe`'nin YANINDAKI klasorlere koyar; `SPEC2CODE_DATA_DIR` ortam
degiskeniyle baska bir kok secilebilir. (Eski surumler bunlari Windows'un gecici
`_MEIxxxx` klasorune yaziyordu; uygulama kapaninca siliniyordu.)

---

## 3. Yardimci araclar

Uygulama LLVM veya Cppcheck olmadan da acilir; ama gercek QC icin onerilir:

- LLVM: `clang-format`, `clang-tidy`, `libclang` (adlandirma denetimi libclang ister)
- Cppcheck
- Vitis (yalniz workspace/kart islemleri icin), Vivado (yalniz XSA/bitstream uretimi icin)

Tipik yollar (`C:\Program Files\LLVM\bin`, `C:\Program Files\Cppcheck`) otomatik
aranir. Farkli yerdeyse:

```powershell
$env:SPEC2CODE_CLANG_FORMAT_PATH = "D:\Tools\LLVM\bin\clang-format.exe"
$env:SPEC2CODE_CLANG_TIDY_PATH   = "D:\Tools\LLVM\bin\clang-tidy.exe"
$env:SPEC2CODE_CPPCHECK_PATH     = "D:\Tools\Cppcheck\cppcheck.exe"
$env:SPEC2CODE_LIBCLANG_PATH     = "D:\Tools\LLVM\bin\libclang.dll"
```

Algilama durumu: `http://127.0.0.1:8077/api/health`. Generate konsolu hangi
aracin bulunup hangisinin kosmadigini acikca yazar; "QC GECTI" yalniz kosan
araclar icin gecerlidir.

---

## 4. Uctan uca akis

1. **Setup**: proje adi, platform, cekirdek, runtime, test bench tasiyicisi.
2. `xparameters.h` yukle (ya da Vivado ile XSA/bitstream uret).
3. **Schematic**: entegreleri denetleyicilere bagla, config ve CIT limitlerini gir,
   gerekiyorsa kartlari ve konnektorleri tanimla, sanal cihazlari isaretle.
4. **Generate**: kod uret; QC sonucunu ve dosya agacini incele.
5. Ciktiyi indir ya da **Vitis workspace** paneliyle `.xsa` uzerinden workspace kur.
6. **Board'da calistir** (JTAG/xsdb) ya da flash'a kaz.
7. **Karta baglan** (TCP / seri / CoreSight / MDM) - tek baglanti butun ekranlar icin.
8. **Test Bench** ile tek op'lari, **CIT** ile butun olcumleri, **Bring-up** ile
   sirali acilis senaryosunu kos; **Registers** ve **Akis** ile derinlestir.
9. `drivers/` + `cit/` klasorlerini kendi firmware'ine tasi (bolum 9).

---

## 5. Ekranlar

Ust cubuktaki uc akis adimi: **Setup -> Schematic -> Generate**. Ikinci satirdaki
gorunumler:

| Gorunum | Ne icin |
|---|---|
| Bilgi | Katalog bilgisi uzerinden lokal LLM'e soru (opsiyonel) |
| Katalog | Desteklenen entegreler, register/komut haritalari, pin/waveform bilgisi |
| Test Bench | Karta tek tek op gonderme, register oku/yaz, flash dosya transferi, I2C tarama |
| Akis | Kart ile host arasindaki S2C-MSG cerceveleri ve ajan loglari canli |
| Bring-up | Mission Control: guc -> sensor -> saat agaci -> bellek -> RF sirali acilis, dogum sertifikasi |
| CIT | Cihaz ici test: her entegre kendi kutusunda, OK/NOK karari kartta |
| Registers | Register anlik goruntusu, reset degeriyle/onceki goruntuyle diff, isi haritasi |
| Register Map | Sayisal ekipten gelen register haritasi editoru; .h/.c, HTML, Excel |
| Arayuz/YATT | S2C-MSG mesaj katalogu ve govde sablonlari (tek dogruluk kaynagi); HTML/MD disa aktarim |
| Kilavuz | Bu kilavuzun uygulama ici surumu |

`Ctrl+K` komut paleti her ekrana ve sik aksiyonlara (Generate, Karta baglan) kisayoldur.

---

## 6. Setup

### Platform ve runtime

- Zynq-7000, Zynq UltraScale+ MPSoC, Versal ACAP, MicroBlaze 7-series (Artix/Kintex/Spartan-7 PL).
- Runtime: bare-metal ya da FreeRTOS (yalniz ajan main'i ve lwIP API modu degisir).
- **Test bench tasiyicisi**: `auto` (Ethernet varsa lwIP, yoksa UART), `eth`, `uart`,
  `coresight` (ZynqMP DCC, JTAG), `mdm` (MicroBlaze Debug Module UART, JTAG).
  JTAG tasiyicilari hicbir zaman otomatik secilmez.
- **BSP akisi** (`project.bsp_flow`): `classic` (varsayilan; Vitis <= 2023.2, xsct,
  `XPAR_*_DEVICE_ID` ile LookupConfig) ya da `sdt` (Vitis Unified >= 2024.1, System Device
  Tree: BSP `DEVICE_ID` uretmez, surucu ornegi `XPAR_*_BASEADDR` ile secilir, kod `-DSDT`
  ile derlenir). Uretilen C tek akisa gore cikar (iki akisi `#ifdef` ile tasiyan olu kod
  yok). `xparameters.h` yuklerken baslikta hic `DEVICE_ID` yoksa alan kendiliginden `sdt`
  olur. Vitis workspace uretimi spec akisi ile Vitis surumu uyusmazsa baslamadan hata verir.

### XSA yukleme: kopya mi, yol mu

"`.xsa / .hdf sec (kopyalar)`" dugmesi tarayici dosya secicisini acar; tarayici dosyanin
gercek yolunu vermedigi icin dosya sunucuya `uploads\xsa\<ad>` olarak KOPYALANIR ve
Vitis adimi bu kopyayi kullanir (ekranda sari notla gosterilir). Orijinal dosyayi
yerinde kullanmak istersen tam yolu (`D:\...\board.xsa`) alttaki alana yazip
"Semayi kur" de: bu durumda kopya olusmaz, Vitis dogrudan o yolu okur.

XSA uygulaninca ekran Schematic'e KENDILIGINDEN gecmez; yesil ozet satirindaki
"Schematic'e git" ile gecersin. **Sema korunur:** yeni XSA'da ayni kimlik ve tipte
denetleyicisi (`pl_i2c_0`, `ps_spi_0` ...) bulunan cihazlar, switch'ler ve konnektorler
yerinde kalir (limitler, isimler, config dahil); denetleyicisi kaybolanlar dusurulur ve
ozet satirinda adiyla listelenir. Kartlar her zaman korunur. Boylece PL bloklari ayni
kalip yalniz bitstream/PS ayari degisen XSA'larda semayi yeniden kurmak gerekmez.

### `xparameters.h`

Dosyayi yukle ya da icerigini yapistir; denetleyiciler (I2C, SPI/QSPI, GPIO, UART,
Ethernet) cikarilir. Ayni denetleyici farkli makro takma adlariyla geliyorsa
(`XPAR_PSU_I2C_0` / `XPAR_XIICPS_0`) tek denetleyici olarak birlestirilir.

### Vivado ile XSA uret (Setup icinde)

Kartin `.xsa` dosyasi yoksa Vivado kuruluysa Spec2Code onu uretebilir: PS
yapilandirma formu (MIO, DDR, saat) -> arka planda batch Vivado -> iki asama:
(1) sentezsiz `.xsa` dakikalar icinde hazir ve tek tusla Setup akisina baglanir,
(2) istenirse sentez + implementasyon ile `.bit` (ZynqMP) / `.pdi` (Versal).
MicroBlaze icin bitstream uretmek **XDC kisit dosyasi** ister (saat, reset ve disari
cikan her arayuz gercek pinlere baglanmali; Spec2Code pin uydurmaz).

### MicroBlaze notlari

- Firmware yalniz LMB (BRAM) icinde kosar. Tam test bench ajani + birkac surucu +
  BSP ~156 KB tuttugundan Spec2Code LMB'yi **256 KB** kurar (kucuk secersen link
  `S2C-VITIS-MEMORY-012` ile duser).
- Vitis'in varsayilan 1 KB yigini yetmez; workspace uretimi `lscript.ld`'yi
  yigin 16 KB / heap 8 KB olacak sekilde yamar.
- AXI IIC surucusu **dinamik mod** kullanir (`XIic_DynInit/DynSend/DynRecv`):
  standart modda tek baytlik STOP'lu yazim (register pointer, switch kontrol bayti)
  IP tarafindan dusuruluyordu (saha bulgusu, Nexys A7). Register okumasinda pointer
  `XIIC_REPEATED_START` ile gider.
- Referans tasarim: `scripts/make_nexys_a7_design.tcl` (Digilent Nexys A7-100T: MB
  256K LMB, AXI UARTLite 115200, AXI IIC, AXI Quad SPI STARTUPE2 uzerinden
  konfigurasyon flash'i). Bu kartta UART ajani, kart ustu ADT7420, S25FL128S flash,
  karisik-mod CIT ve QSPI'dan acilis uctan uca dogrulanmistir. `-tclargs mdm` ile
  ayni tasarim MDM UART acik uretilir; MDM transportu (JTAG, USB-UART kablosuz) bu
  tasarimla canli dogrulanmistir: baglanti ~7 sn, I2C/SPI op'lari, I2C tarama, CIT.
- **PL Ethernet (AXI EthernetLite) uzerinden lwIP TCP ajani**: XSA'da `axi_ethernetlite`
  (veya `axi_ethernet`) varsa `auto`/`eth` tasiyicisi MicroBlaze'de de lwIP RAW API ajanini
  uretir. Gerekenler: **AXI INTC + AXI Timer** (lwIP TCP zamanlayicilari 50 ms timer
  kesmesiyle isletilir, EMAC kesmesi INTC'ye bagli olmali), LMB **512 KB** (lwIP + ajan +
  BSP ~%84 BRAM). FreeRTOS + MicroBlaze + eth desteklenmez (`S2C-CODEGEN-...`, `uart` sec).
  Sabit adres: `18.2.75.121/24`, gw `18.2.75.1`, port 5000 (`spec2code_testbench_lwip.h`
  makrolari `#ifndef` korumali). Vitis workspace uretimi lwIP BSP'sini MicroBlaze'e gore
  boyutlandirir (mem 32 KB, pbuf 16, tcp_wnd/snd_buf 4096, tcp_seg 64) ve Xilinx lwip213'un
  iki hatasini yamar: `xadapter.c` cift `status` bildirimi (derleme hatasi) ve
  `xemacliteif.c` PHY reklam kaydinda eksik IEEE 802.3 secicisi (autoneg hic bitmiyor).
  Referans tasarim: `scripts/make_nexys_a7_eth_design.tcl` + `scripts/hdl/rmii_adapter.v`
  (LAN8720A RMII, 50 MHz REFCLK FPGA'dan; Xilinx `mii_to_rmii` IP'si 2023.x'te yok).

---

## 7. Schematic

### Entegre ekleme ve baglama

- Katalogdan I2C, SPI/QSPI veya GPIO cihazi ekle; denetleyiciye dogrudan ya da
  TCA9548A switch kanali uzerinden bagla.
- Attach bilgileri: I2C adresi, SPI chip-select, reset GPIO, IRQ.
- Config paneli: entegreye ozel init ayarlari (LTC2991 kanal ciftleri, LMK04832
  TICS Pro register listesi...), istenen op'lar, `self_test`, CIT olcum limitleri.
- **Kart verisi**: bazi donusumler kartta belirlenen bir degere ihtiyac duyar
  (LTC2945 akimi icin `sense_resistor_mohms`). Descriptor bunu ister; bos birakip
  op'u istersen Generate acik hata verir.
- **Disa aktar** (kanvasin sag ustu): **draw.io** (`<proje>-schematic.drawio`; kart basina
  bir sayfa: denetleyici -> mux -> cihaz katmanlari, kenar etiketi I2C adresi / SPI CS /
  mux kanali, karttan cikan konnektorler port kutusu; birden fazla kartta ayrica "Sistem"
  sayfasi) ve **Excel** (`<proje>-schematic.xlsx`; her sayfa bir kart: Cihazlar, Mux'lar,
  kartin kullandigi Denetleyiciler, Konnektorler bloklari). Kart tanimlanmadiysa tek
  sayfa/tek kart. Diyagram draw.io'da serbestce duzenlenebilir.
- **Sanal cihaz**: kutudaki "gercek / sanal" anahtari cihazi `simulate: true` yapar
  (eflatun kutu). Test bench ajani o cihazi yazilim simulatorunden cevaplar; ayni
  hattaki gercek cihazlar gercek kalir (bolum 8, simulasyon). Yalniz I2C register
  ve SPI TICS-register cihazlari sanal olabilir.

Generate oncesi validasyon: ayni hatta adres/CS cakismasi, var olmayan denetleyici,
descriptor ile uyumsuz transport, eksik kart verisi.

### Cihaz kimlikleri

Kimlik kurali `<kart>_<parca>[_<n>]`:

```text
sakk_adt7420        tek ADT7420
sakk_ltc2991_1      ayni kartta birden fazla LTC2991: ekleme sirasiyla _1, _2 ...
sakk_ltc2991_2
```

Kart oneki kart adinin snake_case halidir (kart tanimsiz projede `kart`). Kimlikler
her degisiklikte otomatik kurala cekilir (mux referanslari tasinir). Uretilen enum
(`I2C_CIHAZ_SAKK_LTC2991_1`) ve CIT varsayilan olcum adlari
(`SAKK_LTC2991_1_V1`, `SAKK_LTC2991_1_TEMPERATURE_READ`) bu kimlikten turer.

### Cok kartli sistemler

Sistem tek karttan ibaret degilse kartlari birinci sinif olarak modelle. Kart
tanimlamadigin surece hicbir sey degismez.

- **Kart ekle** (sag panel): ilk kart ana karttir, o ana kadar eklenen her sey ona
  tasinir; sonrakiler cevre kartidir. Denetleyiciler her zaman ana karttadir.
- Cihazi/mux'u kart kutusunun icine surukleyerek atarsin; elektriksel baglanti
  (`attach`) degismez, yalniz fiziksel konum degisir.
- **Konnektor**: iki kart arasi hat gecisini belgeler (ad, kaynak/hedef kart,
  denetleyici, varsa switch kanali, not). Elektriksel yolu degistirmez; cevre
  kartinda cihaz olup konnektor yoksa uyari alirsin.
- Ciktida surucu dosyalari kart klasorlerine ayrilir (`drivers/ana_kart/ltc2991.c`,
  `drivers/rf_kart/tmp101.c`); `cit/` ve `tests/` sistem genelidir. Vitis include
  yolu otomatik eklenir. CIT/Test Bench kutulari kart basliklari altinda gruplanir,
  YATT'a **Sistem Topolojisi** bolumu gelir.

Ornek: `specs/samples/multi_board_demo.spec.json`
(`python spec2code_cli.py build --spec specs/samples/multi_board_demo.spec.json`).

---

## 8. Generate: uretilen kod ve katmanlar

Generate konsolu codegen, referans kaynak kopyalama, (aciksa) LLM ve deterministik
QC turlarini gosterir; bitince Code viewer acilir.

```text
drivers/            surucular + i2c_cihazlar.* + dbg_printf.*        -> senin firmware'ine
cit/                CIT ust katmani (limit, OK/NOK)                  -> senin firmware'ine
tests/              test bench ajani, S2C-MSG, self-test'ler, manifest -> yalniz Spec2Code
tests/sim/          sanal cihaz simulatorleri (yalniz sanal cihaz varsa)
reference_sources/  ithal edilen referans kaynaklar (varsa)
qc_report.json, README.md, .clang-format
```

Her `.c` dosyasinin `.h` esi vardir. Kullaniciya giden `drivers/` ve `cit/`
dosyalarinda `spec2code` adli hicbir dosya ya da sembol yoktur ve test bench
basliklarina bagimlilik yoktur; oldugu gibi tasinirlar.

### 8.1 Surucu katmani (`drivers/`)

**I2C cihaz tablosu (`drivers/i2c_cihazlar.h/.c`)** - butun I2C cihazlari icin tek
dogruluk kaynagi:

```c
typedef enum { I2C_CIHAZ_SAKK_ADT7420 = 0, I2C_CIHAZ_SAKK_LTC2991_1, ..., I2C_CIHAZ_SAYISI } EI2cCihaz;

typedef struct
{
    XIic* spIic;                 /* denetleyici ornegi (i2cCihazlarInit ile atanir) */
    unsigned char ucAdres;       /* 7-bit I2C adresi                               */
    unsigned char ucSwitchAdres; /* TCA9548A adresi; 0 = switch yok                */
    unsigned char ucSwitchKanal; /* switch kanali 0..7                             */
    const SI2cInitYazim* spInit; /* cihaza ozel device_init yazimlari (NULL = yok) */
    unsigned char ucInitSayisi;
} SI2cCihaz;

void i2cCihazlarInit(XIic* spPlI2c0);   /* denetleyici basina bir parametre */
const SI2cCihaz* i2cCihaz(EI2cCihaz eCihaz);
```

Surucu fonksiyonlari ornek/adres yerine tablo satirini alir: `int ltc2991VoltageRead(const SI2cCihaz* spCihaz, SLtc2991Voltage* spVoltage)`.
Bus ornegi, adres, switch secimi ve init yazimlari satirdan gelir; ayni parcadan N
cihaz **tek surucu** paylasir, ayrim satirdan yapilir. SPI/GPIO cihazlarinda handle
Xilinx surucu ornegi isaretcisidir (`XSpi*`, `XSpiPs*`, `XGpio*`); kural: ornek en
alt seviyeye kadar iner, taban adres icerde (`spIic->BaseAddress`) cekilir.

**Struct API'si:**

- Durum registerleri: `S<Mod>Status` (bit alanlari + ham baytlar), `<mod>StatusRegistersRead(spCihaz, &sStatus)`.
- Dizi donuslu op (`voltages[8]`): `S<Mod>Voltage { unsigned short usArrVoltage[8]; }`, `<mod>VoltageRead(spCihaz, &sVoltage)` - mV tam sayi.
- Skaler op'lar `int*` / `unsigned short*` alir; birim donusumleri `static <mod><Olcum>Convert()` yardimcilarindadir.
- Donus degerleri: durum icin `XST_SUCCESS/XST_FAILURE`, dogru/yanlis icin `TRUE/FALSE`; ciplak 0/1 donen fonksiyon yoktur.

```c
static XIic S_sIic;
const SI2cCihaz* spLtc;
SLtc2991Status sDurum;
SLtc2991Voltage sVoltaj;

i2cCihazlarInit(&S_sIic);                            /* tablo -> denetleyici ornegi (bir kez) */
spLtc = i2cCihaz(I2C_CIHAZ_SAKK_LTC2991_1);
ltc2991DeviceInit(spLtc);                            /* ornek kurulur + cihaza ozel init yazimlari */
ltc2991StatusRegistersRead(spLtc, &sDurum);          /* sDurum.uiV1Ready, sDurum.uiBusy ... */
ltc2991VoltageRead(spLtc, &sVoltaj);                 /* sVoltaj.usArrVoltage[0..7] mV */
ltc2991VoltageRead(i2cCihaz(I2C_CIHAZ_SAKK_LTC2991_2), &sVoltaj); /* ikinci LTC2991: ayni surucu */
```

**Seviyeli debug print (`drivers/dbg_printf.h/.c`)** - uretilen kodun tek log kapisi:

| Sabit | Deger | Ne icin |
|---|---|---|
| `DEBUG_LEVEL_ALWAYS` | 0 | banner vb. kesin yazilacaklar |
| `DEBUG_LEVEL_ERROR` | 1 | hata durumlari (**varsayilan esik**) |
| `DEBUG_LEVEL_WARNING` | 2 | uyarilar |
| `DEBUG_LEVEL_MSG` | 3 | mesaj katmani TX/RX |
| `DEBUG_LEVEL_INFO` | 4 | debug bilgisi |
| `DEBUG_LEVEL_TRACE` | 5 | I2C/SPI gelen-giden baytlar |

Bir print ancak seviyesi esikten kucuk ya da esitse basilir.

```c
dbg_printf(DEBUG_LEVEL_ERROR, "LTC2991 init dustu: status=%d", iStatus);
dbgLevelSet(DEBUG_LEVEL_INFO);            /* calisma zamaninda esik */
dbgSinkSet(fp);                           /* ciktiyi yonlendir: void fp(unsigned int uiLevel, const char* cpBody) */
```

Sink kaydetmezsen `xil_printf` ile STDOUT UART'ina yazar. Suruculer her transferi
TRACE seviyesinde (`TRACE|bus=i2c|addr=0x48|reg=0x0A|dir=r|len=1|data=0C`), dusen
transferi ERROR seviyesinde (`TRACEERR|...|asama=p|status=-1`; asama `w` yazma,
`p` pointer, `r` okuma, `m` switch) basar. Tamponlar statiktir; kesme icinden cagirma.

### 8.2 CIT ust katmani (`cit/`)

| Dosya | Icerik |
|---|---|
| `cit_ortak.h/.c` | `SCitLimit {iMin, iMax, uiLimitVar}` (uiLimitVar = 0 -> limitsiz, okundu ise OK), `citLimitDegerlendir()` (TRUE/FALSE), `CIT_OK/NOK/HATA` |
| `<mod>_cit.h/.c` | `S<Mod>CitLimit` (olcum/kanal basina limit), `S<Mod>Cit` (bayraklar + `S<Mod>Status sDurum` + olcum struct'lari), `<mod>CitInit()`, `<mod>CitRead()` |
| `sistem_cit.h/.c` | `SSistemCitBus` (denetleyici ornekleri), `SSistemCitLimit` (cihaz basina varsayilan), `SSistemCit`; `sistemCitBusVarsayilan/Init/Read()` |

`<mod>CitRead` surucuyu cagirir; `sBayraklar` icinde op basina `ui<Op>Okundu`
(okuma basarili) ve olcum/kanal basina `ui<Ad>Ok` (okundu VE `iMin <= deger <= iMax`;
etkin degilse OK) bitleri dolar. Kapali aralik: `min == max` gecerlidir (or. 0..0).
Kritik/uyari ayrimi yoktur. Donus `CIT_OK` / `CIT_NOK` (etkin olcum limit disi) /
`CIT_HATA` (surucu okumasi dustu); sayac tutulmaz.

```c
static SSistemCitBus S_sBus;
static SSistemCitLimit S_sLimit = SISTEM_CIT_LIMIT_VARSAYILAN;   /* spec'ten cihaz basina */
static SSistemCit S_sCit;

sistemCitBusVarsayilan(&S_sBus);        /* surucu ornekleri + I2C cihaz tablosu baglanir */
sistemCitInit(&S_sBus);                 /* her entegrenin DeviceInit'i */
S_sLimit.sSakkLtc29911.sV1.iMin = 3135; /* istege bagli canli limit */
S_sLimit.sSakkLtc29911.sV1.iMax = 3465;
S_sLimit.sSakkLtc29911.sV1.uiLimitVar = 1U;
sistemCitRead(&S_sBus, &S_sLimit, &S_sCit);   /* S_sCit.sSakkLtc29911.sBayraklar.uiV1Ok ... */
```

`SISTEM_CIT_LIMIT_VARSAYILAN` alan adlariyla (designated initializer) uretilir; kendi
main'inde kopyalayip yalniz istedigin satiri degistirmen yeter:

```c
#define SISTEM_CIT_LIMIT_VARSAYILAN \
    { \
        .sSakkLtc29911 = { /* sakk_ltc2991_1 (LTC2991) */ \
            .sV1 = {.iMin = 3135, .iMax = 3465, .uiLimitVar = 1U}, /* SAKK_LTC2991_1_V1: [3135 .. 3465] mV */ \
            .sV2 = {.iMin = 0, .iMax = 0, .uiLimitVar = 0U},       /* SAKK_LTC2991_1_V2: limitsiz */ \
            .sTemperature = {.iMin = 1000, .iMax = 6000, .uiLimitVar = 1U}, /* 10.00..60.00 C */ \
        }, \
    }
```

Kapsam disi (CIT dosyasi uretilmez, README'de listelenir): GPIO hat cihazlari, komut
tabanli SPI flash, I2C EEPROM.

### 8.3 Test bench katmani (`tests/`)

Yalniz Spec2Code'un kullandigi dosyalar:

```text
spec2code_testbench_protocol.c/.h   istek/yanit veri yapilari
spec2code_mesaj.c/.h                S2C-MSG cerceve cozucu + dispatch koprusu
spec2code_testbench_log.c/.h        dbg_printf sink: satirlari S2C-LOG cercevesine sarar
<proje>_testbench_ops.c/.h          op dispatch (her cihaz kendi tablo satiriyla)
spec2code_cit.c/.h                  CIT kosusu (cit/ katmanini cagirir) - olcum varsa
spec2code_testbench_manifest.json   Test Bench / CIT / YATT'in okudugu manifest
<mod>_test.c/.h                     self-test (yalniz self_test istenen cihazlar)
spec2code_testbench_uart|lwip|coresight.* + _main.*   secilen tasiyici ve main()
sim/                                sanal cihazlar (asagida)
```

**Self-test**: `<mod>SelfTest(spCihaz)` = DeviceInit + butun okuma fonksiyonlari
(ilk hatada durur); Test Bench'te cihazin `self_test` op'u olarak kosulur.

**Simulasyon (`tests/sim/`)**: `spec2code_sim_xilinx.h` derleme bayragi `-include`
ile her ceviri birimine girer ve Xilinx veri-yolu fonksiyonlarini
(`XIic_DynSend/DynRecv`, `XIicPs_Master*Polled`, `XSpi_SetSlaveSelect/Transfer`,
`XSpiPs_*`) sarmalayicilara yonlendirir. Adres/CS kayitli bir sanal cihaza aitse
simulator cevap verir, degilse gercek Xilinx fonksiyonu cagrilir (karisik mod).
Surucu ve cit dosyalari sanal cihazi bilmez. `<mod>_sim.*` descriptor'dan uretilen
register modelidir; davranis bloklari (LTC2991 READY/deger uretimi, LTC2945 guc
carpimi, DS1682 gecen zaman sayaci, LMK04832 kilit bitleri) ve hata enjeksiyonu
(`SPEC2CODE_SIM_HATA_NACK`, `SPEC2CODE_SIM_HATA_HAZIR_YOK`) vardir.

---

## 9. Kodu kendi projene tasima

1. `drivers/` (kart klasorleri dahil), `cit/` ve istersen `shell/` klasorlerini kaynak
   agacina ekle; include yoluna bu klasorleri koy. Baska hicbir Spec2Code dosyasi gerekmez.
2. Denetleyici orneklerini olustur, `i2cCihazlarInit(...)` ile tabloyu bagla (ya da
   cit/ kullaniyorsan `sistemCitBusVarsayilan()` bunu senin yerine yapar).
3. Her entegre icin `<mod>DeviceInit(i2cCihaz(...))` / SPI icin `<mod>DeviceInit(&sSpi)`
   (cit/ ile: tek cagri `sistemCitInit(&sBus)`).
4. Okumalar icin surucu fonksiyonlarini ya da `sistemCitRead()`'i cagir.
5. `dbg_printf.c`'yi derlemeye ekle; gurultu icin `dbgLevelSet(DEBUG_LEVEL_ERROR)`.

### 9.1 Konsol shell'i (`shell/`)

Kendi main'inden konsol UART'i uzerinden komutla CIT kosturmak icin `shell/` katmani
uretilir (cit/ olan her projede). Cikti kokundeki `main.c` / `main.h` (shell/ icinde DEGIL; Vitis
`<app>_shell` projesinde `src/` altinda tek basina durur) kopyala-yapistir ana programdir (acilista proje adini
buyuk harf FIGlet Colossal banner olarak basar, ardindan `shell is initialized (type help)`):

```c
sistemCitBusVarsayilan(&S_sBus);
sistemCitInit(&S_sBus);                      /* ana dongu oncesi, bir kez */
shellInit(&S_sBus, &S_sLimit, &S_sCit);      /* yerlesik komutlar kaydolur */
shellCommandsRegister(shellUserCommandTable(), shellUserCommandCount()); /* senin komutlarin */
while (1)
{
    shellCheck();                            /* bloklamaz: bayt varsa isler */
}
```

XShell/PuTTY'de (BSP stdout/stdin UART'i, 115200) istem `> ` gelir. Komutlar:

| Komut | Ne yapar |
|---|---|
| `cit` | `sistemCitRead()`; cerceveli/renkli rapor `dbg_printf` INFO satirlaridir: gormek icin once `sdl info`; `cit: OK/NOK/ERROR (run #n)` sonuc satiri her seviyede |
| `i2c_search` | her I2C denetleyicisinde 0x08..0x77 tek-bayt yazma probu; ACK veren her adresi spec'teki cihaz kimligiyle listeler (`0x4B  ACK  ana_kart_adt7420 (ADT7420)`, switch arkasindakiler `switch 0x70 ch3` notuyla; spec'te olmayan adres `(not in spec)`), I2C switch adreslerini atlar |
| `i2c_read <addr> <reg> [n]` | secili I2C denetleyicisinde register isaretcisini yazip n bayt (1..16) okur: `i2c_read 0x48 0x01 2` -> `0x48 reg 0x01: 0A 1B`; NACK'te `NACK / bus error` |
| `i2c_write <addr> <byte...>` | ham bayt dizisi yazar, ilk bayt genelde register adresi: `i2c_write 0x48 0x06 0x10`; I2C switch kanali secmek icin `i2c_write 0x70 0x08` |
| `i2c_bus [id]` | birden fazla I2C denetleyicisi olan projede uretilir: i2c_read/i2c_write'in kullandigi denetleyiciyi listeler/secer (`*` isaretli) |
| `mem <addr> [value]` | 32-bit register oku / yaz (`Xil_In32` / `Xil_Out32`), yazinca geri okur: `mem 0x43C00000`, `mem 0x43C00004 0x12345678`; adres 4'e hizali olmali |
| `<custom_ip> dump` / `read <n>` / `write <n> <value>` | XSA'daki her custom IP icin OTOMATIK uretilir (komut adi = IP instance adi, or. `mem_pcie_intr_0`). `n` register numarasi (0'dan, her biri 4 bayt: adres = base + 4n); XSA adres araligiyla sinirlidir, disina cikan `out of range`. `dump` tum araligi 4'er bayt basar, `write` yazdiktan sonra geri okur |
| `sdl <level>` | set debug level: `error` `warning` `msg` `info` `trace` (ya da 0..5); argümansiz mevcut seviye |
| `help` | komut listesi (tablodan) |
| `mod <x> <y>` | GPIO loopback test IP'si (14 Samtec konnektor): `open` reg x <= desen (`reg0` 0x01010101 ... `reg7` 0x08080808), `close` 0, **`test`** = open + AXI INTC kesmesini bekle (1 s, gelmezse TIMEOUT) + reg8..reg21'deki 14 konnektor durumunu bit bit renkli bas (0 yesil OK, 1 kirmizi HATA, satir sonunda hata sayisi, altta genel OK/NOK) + close. Kesme isleyicisi yalniz `volatile` bayrak kurar. `shell_user_commands.c` basinda `SHELL_USER_MOD_BASEADDR` (XPAR_<IP>_BASEADDR) ve `SHELL_USER_MOD_INTR_ID` (XPAR_INTC_0_<IP>_<PORT>_VEC_ID) ayarlanir; tasarimda AXI INTC yoksa `test` bunu soyler |

**Custom IP komutlari:** Setup'ta XSA okunurken taninmayan REGISTER tipli PL IP'ler
(`user:user` VLNV'li kendi IP'lerin) spec'e `custom_ips` olarak yazilir: `id` (instance adi),
`base_address`, `high_address`, `register_count`. Register sayisi hwh'deki `C_<IF>_ADDR_WIDTH`
parametresinden gelir (AXI4-Lite sablonu: 4 bit -> 16 B -> 4 register); parametre yoksa
`HIGHADDR-BASEADDR+1 / 4` (64K pencere -> 16384 register, dump uzun surer). Setup ekraninda
"N custom IP" rozeti ve liste gorunur; register map dosyasi gerekmez, adres elle yazilmaz.
LMB BRAM gibi MEMORY tipli araliklar custom IP sayilmaz.

**Dosya rolleri:** `shell.c` cekirdektir ve KOMUT ICERMEZ (satir okuma, ok tusu gecmisi,
tokenize, tablo dagitimi, `shellBus()/shellLimit()/shellCit()` erisimcileri). Komutlarin
TAMAMI (`cit`, `i2c_search`, `sdl`, `help`, `mod`) `shell/shell_user_commands.c` icindeki tek
tabloda `S_sArrUserCommands[]` durur; `main.c` bu tabloyu bir kez kaydeder.

**Yeni komut eklemek** (`shell/shell_user_commands.c`): komutlar bu TABLODAN dagitilir,
if-zinciri yoktur. Her satir `SShellCommand {ad, isleyici, yardim}`; isleyici imzasi
`void f(unsigned int uiArgc, const char* cpArrArgv[])`, `cpArrArgv[0]` komut adi, sonrakiler
STRING arguman (sayi gerekiyorsa `atoi`/`strtol`). Iki adim:

```c
static void shellUserRele(unsigned int uiArgc, const char* cpArrArgv[])   /* 1. isleyici */
{
    int iKanal;
    if (uiArgc != 2U) { xil_printf("usage: rele <0..3>\r\n"); return; }
    iKanal = atoi(cpArrArgv[1]);
    ...
}

static const SShellCommand S_sArrUserCommands[] = {                        /* 2. tabloya satir */
    {"cit", shellUserCit, "read all devices, print the report"},
    {"i2c_search", shellUserI2cSearch, "scan I2C addresses 0x08..0x77"},
    {"sdl", shellUserSdl, "<level>  set debug level: error|warning|msg|info|trace (0..5)"},
    {"help", shellUserHelp, "list commands"},
    {"mod", shellUserMod, "<0..7> <open|close>  write custom IP register x"},
    {"rele", shellUserRele, "<0..3>  toggle relay"},                        /* konsol adi "rele" */
};
```

`help` yeni satiri kendiliginden listeler; `main.c` tabloyu bir kez kaydeder. `mod`
orneginde `SHELL_USER_MOD_BASEADDR` (dosyanin basinda, `xparameters.h`'teki
`XPAR_<IP>_BASEADDR`) 0 kaldigi surece yazim yapilmaz, uyari basilir.

Yukari/asagi ok tuslari son 8 komutta gezer (yukari: onceki, asagi: sonraki, sonda bos
satir); gelen satir duzenlenip Enter ile yeniden kosulabilir. `cit` komutu log esigine
dokunmaz: rapor `DEBUG_LEVEL_INFO` satirlaridir, `sdl info` (ya da `trace`) ile gorunur;
`sdl error`'da yalniz hata izleri (`TRACEERR`) ve `cit: ...` sonuc satiri gelir.
`shell_uart.c` platforma gore uretilir (XUartLite / XUartPs / XUartPsv, `STDIN_BASEADDRESS`).
Test bench ajani (tests/) ile birlikte derlenmez; UART ajani konsolu kullanirken shell
ayni hatta olamaz, MDM/CoreSight/TCP ajanlarinin yaninda konsolda calisabilir.

Vitis workspace kurulumu bu kodu ayrica DERLER: ayni platformda ikinci bir uygulama
(`<app>_shell`, kaynaklari `drivers/ + cit/ + shell/` + kokteki `main.c/main.h`) olusur ve
ELF'i Vitis sayfasinda "Shell ELF" satirinda gorunur. GUI bu ELF'i kullanmaz;
"Board'da calistir" her zaman ajani yukler. Shell ELF'ini XShell/PuTTY ile denemek icin
`xsdb`/Vitis'ten elle yukle ya da kaynaklari kendi projene tasi.

Test bench ajanini kendi projende kullanma; o yalniz Spec2Code ekranlari icindir.

---

## 10. Karta baglanma

Her ekranin ustundeki **Baglanti** karti ortaktir: bir kez baglanirsin, Test Bench,
Akis, Bring-up, CIT ve Registers ayni oturumu kullanir.

| Tip | Ne zaman | Alanlar |
|---|---|---|
| TCP | lwIP Ethernet ajani (ZynqMP PS Ethernet / MicroBlaze AXI EthernetLite) | host, port (vars. 5000), timeout, kaynak IP (opsiyonel: ayni alt ag birden fazla adaptordeyse kart tarafindaki adaptorun IP'si) |
| Seri | UART ajani (PS UART / AXI UARTLite) | COM portu, baud (or. 115200) |
| CoreSight | ZynqMP DCC, JTAG (xsdb jtagterminal) | Vitis yolu, cekirdek |
| MDM | MicroBlaze Debug Module UART, JTAG | Vitis yolu |

Kart loglari (`dbg_printf`, CIT raporu dahil) her zaman taşiyici hattindan Akis ekranina
gider. Taşiyici konsol UART'i DEGILSE (MDM, CoreSight, TCP) ayni satirlar BSP `stdout`
cihazina, yani USB-UART konsoluna (XShell/PuTTY, 115200) da basilir; UART ajaninda ise
hat zaten konsol oldugundan tekrar basilmaz. Raporu gormek icin kart esigini `info` yap.

MDM icin tasarimda MicroBlaze debug modulunun UART'i acik olmali (Vivado blok
otomasyonunda `debug_module {Debug & UART}`; XSA'da `XPAR_MDM_n` `XUartLite`
subtype `mdm` olarak gorunur). Spec'te `testbench_transport: "mdm"` secilince ajan bu
UART'a baglanir, host xsdb `jtagterminal` koprusunu MicroBlaze hedefiyle acar.

SmartLynq / uzak `hw_server` icin `connect -url` alani vardir. Ilk JTAG baglantisi
xsdb acilisi yuzunden 10-30 sn surebilir. Ayni COM portunu tutan eski oturum sunucu
tarafinda devralinir. Kartin debug esigi (0 always .. 5 trace, varsayilan error)
buradan canli degistirilir (`log_level` komutu).

Protokol: uc tasiyici da ayni 12 baytlik little-endian cerceveyi tasir
(`uiMesajKomut`, `uiMesajBoyu`, `uiMesajSayac`); mesajlar katalogludur ve tam tablo
Arayuz/YATT sayfasindadir. Kart yazilimi bu surumun uretimiyle yuklenmemisse ilk
komutta zaman asimi / GECERSIZ_MESAJ alirsin: Generate + Vitis ile yeniden derleyip
yukle.

---

## 11. Test Bench

Manifestteki entegreleri (kart basliklari altinda) listeler; her entegre icin gercekten
uretilmis op'lari sunar:

- `device_init`, okuma op'lari (`voltage_read`, `temperature_read`, ...), `self_test`.
- `register_read` / `register_write`: register adi ya da adres (genis registerler tek
  islemde).
- Flash/EEPROM: adres, uzunluk, veri hex; flash'ta **Dosya transferi** modu (256 baytlik
  parcalarla .bin okuma/yazma + geri okuma dogrulamasi).
- **Butun cihazlari ilklendir** (kart kart ilerler) ve **I2C tarama** (denetleyici ve
  switch kanali secilerek).
- Riskli op'lar (`init`, `write`, `program`, `erase`) onay ister.
- Yanit alanlari (`ok`, `status`, `value`, `data`, `message`) cozulmus gosterilir;
  ham istek/yanit cerceve ozeti + hex olarak durur.

LTC2991 ornegi: `voltage_read` 8 kanal mV, `temperature_read` 0.01 C, `vcc_read` mV,
`current_read` ham kanal kodu (sont uzerinden akim hesabi uygulama katmanindadir).

Karti ilk kez dogrularken `docs/s2cmsg_parite_listesi.md` kontrol listesini kullan.

---

## 12. CIT (Cihaz Ici Test)

CIT ekrani her entegreyi kendi kutusunda gosterir: baslik (parca, kimlik, adres/CS,
switch, SANAL rozeti), dizi donuslu op'lar icin kanal karolari (V1..V8 / I1..I8),
skaler olcumler icin satirlar. Ayni parcadan entegreler bir satirda yan yana durur.
LTC2991 `current_read` (ham diferansiyel kod, sont uygulama tarafinda) CIT'e GIRMEZ:
istense de akim karolari cikmaz; karta eklenirken varsayilan tiksiz gelir, `vcc_read`
ve diger olcumler tiklidir.

**Karar karttadir.** Bir karoya tiklayip limit (min/max, kapali aralik) ya da etkin
durumunu degistirdiginde bagliysan bu degerler ANINDA karta yazilir (`CIT_LIMIT_SET`
mesaji -> `cit/` limit yapisi) ve her "CIT kostur"dan once yeniden gonderilir. Kartta
tek alan vardir: `uiLimitVar` - limit varsa aralik denetlenir, yoksa (ya da ekranda
etkin degilse) olcum yalniz okunur ve OK sayilir; ayri bir "etkin" biti yoktur. Limitler
EKRANDA GORDUGUN birimde girilir (sicaklik °C, voltaj mV); ekran bunu kartin birimine
(santi-derece) cevirir, spec ve C varsayilanlari kart birimindedir. Kart
`sistemCitRead()` ile okur, OK/NOK bitini kendisi hesaplar; ekran yalnizca kartin
bitini ve okuma durumunu gosterir. Yani ekranda gordugun sonuc, projene tasidigin
`cit/` + `drivers/` kodunun kendisinden gelir.

Akis: `CIT_RUN` -> ajan `boardCitRun()` -> `spec2codeTestbenchBoardInit()` -> I2C cihaz
tablosu baglanir -> `sistemCitRead()` -> `<mod>CitRead()` -> surucu okumalari -> sonuc
manifest sirasiyla `SBoardCit`'e (deger, okuma durumu, OK biti) -> host.
`sistemCitRead()` her kosuda `DEBUG_LEVEL_INFO` seviyesinde cerceveli bir rapor basar:
72 sutunluk kutular, her entegre kendi kutusunda (baslik satirinda entegre sonucu), her
olcum satirinda ad / deger / birim / limit / OK-NOK, sonda genel SONUC. Olcum adi ekranda
verdigin addir (`VCC_3V3`); ad verilmemis kanal etiketiyle (`V2`) basilir. Ekranda yaptigin
limit/isim degisiklikleri spec'e (cihaz `config.cit.measurements`) yazilir; spec'i indirince
korunur ve bir sonraki uretimde `SISTEM_CIT_LIMIT_VARSAYILAN` ile rapor adlari boyle gelir. Satirlar ANSI
renklidir (OK yesil, NOK kirmizi, HATA sari): XShell/PuTTY dogrudan
renkli gosterir, Akis ekrani da ayni tonu uygular. Log esigini `info` yapinca gorunur.
"Otomatik yenile" `CIT_READ` ile son kosuyu yeniden kosmadan okur. **Rapor indir** son okunan
kosuyu tek dosya HTML rapor olarak verir (bring-up sertifikasi gibi): genel karar, ozet, dikkat
gerektiren olcumler, her entegre cerceveli kutuda deger / limit / OK-NOK renkli; yazdirilabilir,
paylasilabilir.

Not: cit/ okumalari ilklendirilmis entegre ister; once Test Bench'ten "butun
cihazlari ilklendir" ya da Bring-up kos.

---

## 13. Bring-up, Registers, Akis, Register Map, Arayuz/YATT

- **Bring-up (Mission Control)**: guc -> sensor -> saat agaci -> bellek -> RF sirasiyla
  cihazlari ilklendirir ve okur; her adim yesil/kirmizi, sonunda dogum sertifikasi.
- **Registers**: bir cihazin butun registerlerinin anlik goruntusu; karsilastirma
  tabani olarak reset degerleri (datasheet) ya da onceki goruntu; degisen bitler isi
  haritasinda. Yazma onay ister.
- **Akis**: karta giden/gelen cerceveler ve `S2C-LOG` satirlari canli; TRACE
  seviyesinde I2C/SPI baytlari komut kimligiyle eslestirilir. Telnet log sunucusu
  uretildiyse onun satirlari da burada.
- **Register Map**: sayisal ekipten gelen memory-mapped PL IP register haritasini
  duzenle; self-contained HTML editor, Excel ve `.h/.c` (struct/union, bit alanli)
  uret. Register genisligi offset'lerden cikarilir. Uretim ayrica `<map>_shell.h/.c`
  verir: shell tablosuna tek satir (`{"ip_<map>", shellUser<Map>, ...}`) ekleyince konsoldan
  `ip_<map> rd CONTROL.ENABLE`, `ip_<map> wr STATUS 0x10`, `ip_<map> dump` calisir; base adres
  haritadaki `<MAP>_BASE_ADDRESS`'ten gelir, elle adres yazilmaz.
- **Arayuz/YATT**: S2C-MSG mesaj katalogu (ID, yon, govde sablonu, durum kodlari),
  manifest ile zenginlestirilmis; cok kartli projede Sistem Topolojisi; HTML/MD olarak
  paylasilabilir. Protokolun tek dogruluk kaynagi budur.

---

## 14. Vitis workspace ve Board'da calistirma

Generate bittikten sonra **Vitis workspace** paneli: Vitis dizini
(`C:\Xilinx\Vitis\2023.2`), `.xsa` dosya yolu, workspace ve temp/staging dizinleri,
platform/system/application adlari, islemci (`psu_cortexa53_0`, `microblaze_0`...).

**Vitis Unified (>= 2024.1, or. 2025.2)**: xsct Tcl akisi yerine `vitis -s <python>`
betigi kosar (`spec2code_unified_workspace.py`, loglar `vitis_stdout.log`): platform
bileseni (XSA, os, cpu) -> lwIP gerekiyorsa `lwip220` + MicroBlaze bellek parametreleri ->
`platform.build()` -> lwip220 varsa libsrc yamasi (xadapter.c cift `status`, xemacliteif.c
IEEE 802.3 secicisi; lwip213'teki hatalar 2025.2'de de duruyor) + yeniden derleme ->
`empty_application` bileseni -> kaynak import + `USER_INCLUDE_DIRECTORIES` + MicroBlaze
lscript yigin/heap (16 KB / 8 KB) -> `app.build()`; ELF `<workspace>/<app>/build/<app>.elf`
(shell uygulamasi `<app>_shell` ayni sekilde). Bu akista spec `bsp_flow = sdt` olmali. Custom
PL IP surucu politikasi (make.libs yamasi) Unified'da uygulanmaz: SDT surucusu uyumluluk
dizgisiyle eslesir, eslesmeyen IP icin surucu uretilmez. MicroBlaze lwIP ajani SDT'de
`xiltimer` (50 ms tick) kullanir; EMAC kesmesini lwIP portu kurar, uygulamada XIntc yoktur.
Nexys A7 + Vitis 2025.2 ile uctan uca dogrulandi (UART ajani, shell, ADT7420, I2C tarama, CIT;
Ethernet ajani). Tam kosu (platform + iki uygulama) ~70 sn.

**Klasik akis (<= 2023.2)**: XSCT bulunur -> `.xsa` ve uretilen kaynaklar staging'e kopyalanir (uretim
ciktisi diskte eksikse acik hata: once Generate'i yeniden calistir) -> custom PL IP
adaylari `.hwh`'dan algilanir -> lwIP gerekiyorsa BSP kutuphanesi/API modu denenir ->
`spec2code_create_workspace.tcl` yazilir -> platform/system/application kurulur ->
`app build` -> uygulama adiyla eslesen `.elf` dogrulanir. **Kaynak guncelleme modu**
platform/BSP'ye dokunmadan yalniz kaynaklari yeniler ve uygulamayi derler
(CLI: `--vitis-update`). Sanal cihaz varsa `-include spec2code_sim_xilinx.h` bayragi ve
`tests/sim` include yolu otomatik eklenir.

Staging dizini:

```text
<temp>\<vitis_job>\hw\  src\  spec2code_create_workspace.tcl
                     spec2code_self_heal_workspace.tcl  spec2code_vitis_manifest.json
                     logs\xsct_stdout.log  logs\xsct_stderr.log  (+ self_heal loglari)
```

**Custom PL IP**: varsayilan politika `auto_none` - Xilinx/AMD disi (ya da standart
IP ailesine benzemeyen) PL modulleri icin BSP surucusu `none` denenir; source'suz
`make.libs` dosyalari yamalanir, gerekirse self-heal script'i `bsp regenerate` +
`app build` ile toparlar (`BSP patch N`, `self-heal gecti` rozetleri). Custom IP gercek
bir surucuyle geliyorsa `BSP default'u koru` sec. Ucuncu secenek **`Sec: IP basina koru /
none`**: XSA'daki custom IP adaylari listelenir; tikledigin IP'nin BSP surucusu korunur
(surucu kaynagi XSA'da olmali; adresi `xparameters.h`'a `XPAR_<INSTANCE>_..._BASEADDR` olarak
girer), tiksizler `none` yapilir. Secim tarayicida kalicidir; sonuc rozeti `custom IP sec: N
koru`. Shell'deki `<id> dump|read|write` komutlari bu politikadan bagimsizdir (adres XSA'dan
gelir, surucuye ihtiyac duymaz).

**Iki uygulama**: kurulum `<app>` (test bench ajani, GUI ile konusur; Board'da calistir
bunu yukler) ve `<app>_shell` (drivers + cit + shell, projene tasinacak kod; ELF'i manuel
alinir) uygulamalarini ayni platformda derler. Iki proje de HER DURUMDA olusturulur: once iki
app projesi kurulup kaynaklar import edilir, sonra derlemeler ayri ayri kosar. Ajan derlemesi
duserse (or. yazilim BRAM'e sigmadi, link hatasi) shell yine derlenir, is "basarisiz" doner
ama Vitis sayfasindaki "Shell ELF" satiri dolar ve ELF'i alabilirsin. Shell derlemesi ajani
etkilemez: ELF cikmazsa `S2C-VITIS-SHELL-014` uyarisi verilir, is basarili sayilir. "Kaynaklari guncelle" ikisini de
gunceller (eski workspace'te shell uygulamasi yoksa olusturur).

**Vitis Doctor**: tamamen lokal; `S2C-VITIS-...` hata kodlari, custom IP/make.libs
sayilari, self-heal sonucu, beklenen ELF adi. Compile error mapper eksik header,
undefined reference, coklu tanim, `XPAR_*` uyusmazligi gibi hatalari one cikarir; ham
log gizlenmez.

**Board'da calistir (JTAG / xsdb)**: workspace'teki ELF'i (MicroBlaze'de zorunlu
bitstream ile birlikte) JTAG'dan yukleyip calistirir. ELF'in gomulu surumu ve derleme
zamani ilerleme mesajinda gorunur; uygulama surumuyle uyusmuyorsa uyari verir (workspace
yeniden derlenmemis demektir). Vitis build'i "gecti" ama ELF build'den eskiyse is
`stale_elf` hatasiyla durur - bayat ELF karta yuklenmez. Kalici acilis icin ELF'i
`updatemem` ile BRAM'e gomulu bitstream'e yazip konfigurasyon flash'ina kazirsin
(Nexys A7 akisi changelog'da belgelidir).

En sik hatalar: yanlis Vitis/XSA yolu, XSA'daki islemci adinin farkli olmasi,
BSP/toolchain eksigi, lwIP kutuphanesinin BSP'de acilamamasi, custom IP surucusu.
Once UI'daki son ilerleme mesajina, sonra `xsct_stderr.log`'a bak.

---

## 15. Kodlama standardi (ozet)

Tam referans: `docs/kodlama_standardi.md`. Uretilen kod `clang-format` + `clang-tidy`
+ adlandirma denetcisinden gecer; standart sabittir, kullanici belge vermez.

- Fonksiyonlar camelCase: `tca9548aChannelSelect`. Allman parantez. Satir en fazla 160 sutun.
- Primitive tipler (`unsigned char`, `unsigned int`); `uint8_t` gibi sabit genislikli
  typedef'ler yasak.
- Hungarian onekler: `uc c us s ui i ul ull`, struct `S<Ad>` / degisken `s`, struct
  pointer `sp`, diger pointer tip oneki + `p`, dizi tip oneki + `Arr`, global `G_`,
  static `S_`, enum `E<Ad>`. Bit alani uyelerinde onek yok.
- Pointer yildizi tipe bitisik: `XIicPs* spIic`.
- Donus degerleri: `XST_*` (durum), `TRUE/FALSE` (dogru/yanlis), adlandirilmis makro;
  ciplak 0/1 yok. Sayi donenler (bayt sayisi, boy) serbest.
- Doxygen fonksiyon bloklari varsayilan kapali (dosya basligi kalir).

---

## 16. LLM kullanimi

Varsayilan kapali. OpenAI-uyumlu bir endpoint, model adi ve gerekirse API key
girilir (GLM, Qwen, Kimi...). Generate icinde yardimci roldedir: aday dosya
deterministik QC'den gecmeden kabul edilmez, reddedilirse mevcut cikti korunur;
bos/uzun/timeout cevaplar net hata olarak gosterilir. Bilgi soru merkezi yalniz
katalogdaki dogrulanmis context'i kullanir; context disi register/bit adlari
reddedilir.

---

## 17. Air-gap notlari

Executable paket icin gereken: `Spec2Code.exe` + bu belgeler; opsiyonel LLVM/Cppcheck,
Vitis/Vivado, lokal LLM endpoint'i. Vitis Doctor ve loglar disari hicbir sey
gondermez. Kaynak koddan gelistirme icin release'teki source archive ve offline
bagimlilik onbellegi gerekir (`glm52_handoff.md`).

---

## 18. Desteklenen entegreler

TCA9548A (I2C switch), LTC2991, LTC2945, ADT7420, AD7414, TMP101, SHT21, DS1682,
24LC32A (I2C EEPROM), LMK04832, LMX2820, LMX1204, LMX1205, ADAR1000, LTM4681,
MT25Q128, MT25QL128, MT25QU02G, S25FL128S (SPI/QSPI NOR flash), GPIO hat cihazlari.
Guncel liste Katalog ekranindadir; katalogda olmayan cihaz icin deterministik
uretim yoktur (yeni entegre destegi descriptor eklenerek surume girer).

---

## 19. Sorun giderme

**Tarayici eski surumu gosteriyor** - eski backend calisiyor olabilir; butun
Spec2Code sureclerini kapatip yeniden baslat, `Ctrl+F5` ile yenile, ust cubuktaki
surumu kontrol et.

**Generate tamamlanmiyor** - konsoldaki son hata satiri; LLM aciksa zaman asimi /
context disi cevap; `/api/health` ile arac yollari.

**Vitis workspace olusmuyor** - Vitis/XSA/temp yollari, islemci adi,
`logs\xsct_stderr.log`, compile error listesi; "Generate ciktisi diskte eksik"
uyarisinda once Generate'i yeniden calistir (ayni proje adiyla baska bir uretim
klasoru ezmis olabilir).

**Workspace "takiliyor", application projesinde yalniz lscript/README var
(`S2C-VITIS-HANG-010`, `which sdscc`)** - Spec2Code surumunden bagimsiz bir makine
sorunudur: Vitis 2023.2 `app create` sirasinda `which sdscc` cocuk sureci bazi
Windows makinelerinde (antivirus/EDR, konsol host) donar, XSCT sonsuza dek bekler;
Spec2Code watchdog'u sureci keser ve Doctor bu kodu basar. Kalici cozum: Vitis
kapaliyken yonetici PowerShell'de
`scripts\windows\vitis_which_stub\apply.ps1 -VitisRoot C:\Xilinx\Vitis\2023.2`
(orijinal `which.exe` `.s2cbackup` olarak yedeklenir, konsol acmayan stub yerine
konur; `restore.ps1` geri alir; klasor release'in `spec2code-vX.Y.Z-source.zip` kaynak
paketindedir). Onceki yarim workspace'i silip yeniden olustur.

**Her dosyada `qc.format_failed` / "invalid boolean" (`.clang-format`)** - eski bir
clang-format (10 oncesi) config'i reddediyor. v0.1.186'dan itibaren uygulama config'i
yerel aracla dogrular ve eski surum icin uyumlu config'e duser; hala goruyorsan LLVM'i
guncelle ya da `SPEC2CODE_CLANG_FORMAT_PATH` ile yeni bir clang-format goster.

**"Workspace kilitli" / `Invalid Workspace` (`S2C-VITIS-PREFLIGHT-013`)** - Vitis IDE ayni
workspace'i acik tutuyor (Eclipse bir workspace'i tek ornekte acar, `.metadata\.lock`).
IDE'de File > Switch Workspace ile baska bir workspace'e gec ya da IDE'yi kapat; ya da
Spec2Code'a farkli bir workspace dizini ver. Spec2Code bunu XSCT'yi baslatmadan yakalar.

**"Spec/XSA uyumsuz" (`S2C-VITIS-PREFLIGHT-011/012`)** - workspace olusturma XSCT'yi hic
baslatmadan durdu. 011: spec platformu (orn. Zynq UltraScale+) ile XSA'nin islemcisi
(orn. MicroBlaze) farkli - Setup'ta dogru XSA'yi yukleyip spec'i ondan turet. 012:
MicroBlaze + FreeRTOS icin tasarimda AXI Interrupt Controller ve AXI Timer yok
(BSP DRC: "CPU has no connection to Interrupt controller") - runtime'i bare_metal yap ya
da Vivado tasarimina axi_intc + axi_timer ekleyip XSA'yi yeniden uret.

**Spec'teki denetleyici XSA'da yok** (`fatal error: xspips.h: No such file`) - spec
xparameters.h'ten cikarilmis ama XSA'da o PS cevre birimi (orn. PS SPI) kapali. Setup'ta
XSA'yi yeniden yukleyip denetleyici listesini XSA'dan al ya da o denetleyiciye bagli
cihazi kaldir.

**Karta baglanamiyor** - TCP: ajan (lwIP) kosuyor mu, host/port/firewall. Seri: COM
portu ve baud. CoreSight/MDM: Vitis yolu ve JTAG kablosu; ilk baglanti 10-30 sn.
Ilk komutta zaman asimi / GECERSIZ_MESAJ: karttaki yazilim eski, yeniden derleyip yukle.

**"CIT yanit govdesi boyu uyusmuyor" / init'te cihaz bulunamiyor** - karttaki ajan
ile ekrandaki manifest farkli uretimlerden: karti mevcut spec'ten yeniden derleyip
yukle (cihaz eklediysen ajan da degismelidir).

**Sanal cihaz NACK veriyor** - sanal cihaz da `device_init` ister; once "butun
cihazlari ilklendir".

---

## 20. Release dosyalari

```text
Spec2Code.exe      uygulama
changelog.md       en yeni surumden baslayan tum degisiklik gecmisi
userguide.md       bu kilavuz
glm52_handoff.md   air-gap'te kaynak kod uzerinde calisacak lokal model icin gelistirme handoff'u
```
