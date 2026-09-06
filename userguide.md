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
  karisik-mod CIT ve QSPI'dan acilis uctan uca dogrulanmistir.

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
| `cit_ortak.h/.c` | `SCitLimit {iMin, iMax, uiLimitVar, uiEtkin}`, `citLimitDegerlendir()` (TRUE/FALSE), `CIT_OK/NOK/HATA` |
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

1. `drivers/` (kart klasorleri dahil) ve `cit/` klasorlerini kaynak agacina ekle;
   include yoluna bu klasorleri koy. Baska hicbir Spec2Code dosyasi gerekmez.
2. Denetleyici orneklerini olustur, `i2cCihazlarInit(...)` ile tabloyu bagla (ya da
   cit/ kullaniyorsan `sistemCitBusVarsayilan()` bunu senin yerine yapar).
3. Her entegre icin `<mod>DeviceInit(i2cCihaz(...))` / SPI icin `<mod>DeviceInit(&sSpi)`.
4. Okumalar icin surucu fonksiyonlarini ya da `sistemCitRead()`'i cagir.
5. `dbg_printf.c`'yi derlemeye ekle; gurultu icin `dbgLevelSet(DEBUG_LEVEL_ERROR)`.

Test bench ajanini kendi projende kullanma; o yalniz Spec2Code ekranlari icindir.

---

## 10. Karta baglanma

Her ekranin ustundeki **Baglanti** karti ortaktir: bir kez baglanirsin, Test Bench,
Akis, Bring-up, CIT ve Registers ayni oturumu kullanir.

| Tip | Ne zaman | Alanlar |
|---|---|---|
| TCP | lwIP Ethernet ajani (ZynqMP PS Ethernet) | host, port (vars. 5000), timeout |
| Seri | UART ajani (PS UART / AXI UARTLite) | COM portu, baud (or. 115200) |
| CoreSight | ZynqMP DCC, JTAG (xsdb jtagterminal) | Vitis yolu, cekirdek |
| MDM | MicroBlaze Debug Module UART, JTAG | Vitis yolu |

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

**Karar karttadir.** Bir karoya tiklayip limit (min/max, kapali aralik) ya da etkin
durumunu degistirdiginde bagliysan bu degerler ANINDA karta yazilir (`CIT_LIMIT_SET`
mesaji -> `cit/` limit yapisi) ve her "CIT kostur"dan once yeniden gonderilir. Kart
`sistemCitRead()` ile okur, OK/NOK bitini kendisi hesaplar; ekran yalnizca kartin
bitini ve okuma durumunu gosterir. Yani ekranda gordugun sonuc, projene tasidigin
`cit/` + `drivers/` kodunun kendisinden gelir.

Akis: `CIT_RUN` -> ajan `boardCitRun()` -> `spec2codeTestbenchBoardInit()` -> I2C cihaz
tablosu baglanir -> `sistemCitRead()` -> `<mod>CitRead()` -> surucu okumalari -> sonuc
manifest sirasiyla `SBoardCit`'e (deger, okuma durumu, OK biti) -> host.
"Otomatik yenile" `CIT_READ` ile son kosuyu yeniden kosmadan okur.

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
  uret. Register genisligi offset'lerden cikarilir.
- **Arayuz/YATT**: S2C-MSG mesaj katalogu (ID, yon, govde sablonu, durum kodlari),
  manifest ile zenginlestirilmis; cok kartli projede Sistem Topolojisi; HTML/MD olarak
  paylasilabilir. Protokolun tek dogruluk kaynagi budur.

---

## 14. Vitis workspace ve Board'da calistirma

Generate bittikten sonra **Vitis workspace** paneli: Vitis dizini
(`C:\Xilinx\Vitis\2023.2`), `.xsa` dosya yolu, workspace ve temp/staging dizinleri,
platform/system/application adlari, islemci (`psu_cortexa53_0`, `microblaze_0`...).

Akis: XSCT bulunur -> `.xsa` ve uretilen kaynaklar staging'e kopyalanir (uretim
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
bir surucuyle geliyorsa `BSP default'u koru` sec.

**Vitis Doctor**: tamamen lokal; `S2C-VITIS-...` hata kodlari, custom IP/make.libs
sayilari, self-heal sonucu, beklenen ELF adi. Compile error mapper eksik header,
undefined reference, coklu tanim, `XPAR_*` uyusmazligi gibi hatalari one cikarir; ham
log gizlenmez.

**Board'da calistir (JTAG / xsdb)**: workspace'teki ELF'i (MicroBlaze'de zorunlu
bitstream ile birlikte) JTAG'dan yukleyip calistirir. Kalici acilis icin ELF'i
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
MT25Q128, MT25QU02G, S25FL128S (SPI/QSPI NOR flash), GPIO hat cihazlari.
Guncel liste Katalog ekranindadir; katalogda olmayan cihaz icin deterministik
uretim yoktur (Driver import sihirbaziyla kendi descriptor'ini ekleyebilirsin).

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
