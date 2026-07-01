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

Release paketini acinca uc dosya gorursun:

```text
Spec2Code.exe
changelog.md
userguide.md
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
- MicroBlaze 7-series

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

## 7. Catalog ve Knowledge

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

## 8. Bilgi Soru Merkezi

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

## 9. Generate Ekrani

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
reference_sources/
qc_report.json
README.md
.clang-format
```

Her `.c` dosyasinin karsilik gelen `.h` dosyasi olmalidir. Test ve Test Bench
agent dosyalari da bu kurala dahildir.

## 10. Code Viewer ve Download

Code viewer'da:

- Generated dosyalari hiyerarsik agacta gorursun.
- Tek dosya indirebilirsin.
- Tum generated output'u zip olarak indirebilirsin.
- Vitis-ready export zip indirebilirsin.
- QC bulgularini aktif dosya ozelinde gorebilirsin.
- Test bench manifest ve agent kaynaklarini `tests/` altinda gorebilirsin.

## 11. Test Bench

Test Bench sayfasi, generate sonucu uretilen su manifest dosyasindan beslenir:

```text
tests/spec2code_testbench_manifest.json
```

Generate sonucu ayrica hedef uygulamaya eklenebilecek agent kaynaklari uretir:

```text
tests/spec2code_testbench_protocol.c/.h
tests/<project>_testbench_ops.c/.h
```

Bu agent dosyalari kart tarafinda `spec2codeTestbenchDispatchLine()` fonksiyonunu
sunar. Windows UI dogrudan donanim bus'ina dokunmaz; TCP uzerinden karta baglanir
ve komut satirlarini bu baglanti uzerinden gonderir. Kart tarafindaki TCP server
kodu gelen her satiri `spec2codeTestbenchDispatchLine()` fonksiyonuna vermeli ve
olusan response satirini ayni TCP baglantisi uzerinden geri dondurmelidir.

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

Generated lwIP agent ayni zamanda schematic'te kullanilan `XIicPs`, `XSpiPs` ve
`XQspiPsu` controller handle'larini initialize eder. Test bench dispatch icindeki
weak hook'lar bu dosyada strong olarak override edilir; yani UI'dan gelen operasyon
dogrudan generated driver fonksiyonuna gider.

Komut formati:

```text
S2C|id=1|device=<id>|op=<operation>|reg=<name>|reg_addr=0x00|address=0x0|length=16|value=0x00|data=AABB
```

Test Bench sayfasinda:

- Host, port ve timeout girilir.
- **Baglan** ile kart tarafindaki TCP agent'a tek session acilir.
- Generate edilmis manifest icindeki entegre secilir.
- Entegre icin gercekten uretilmis operasyonlar listelenir.
- Register read/write icin register adi veya manuel register address verilebilir.
- Flash/EEPROM gibi adresli islemlerde address, length ve data hex alanlari kullanilir.
- Riskli islemler (`init`, `write`, `program`, `erase`) gonderilmeden once onay ister.
- **Gonder** ile komutlar mevcut TCP session uzerinden gider; her komutta yeni
  baglanti acilmaz.
- Baglanti koparsa UI bunu hata olarak gosterir ve tekrar **Baglan** gerekir.
- Response icindeki `ok`, `status`, `value`, `data` ve `message` alanlari okunabilir sekilde gosterilir.

LTC2991 icin test bench uzerinden tipik faydali operasyonlar:

- `voltage_read`: 8 kanal raw voltage code okur.
- `current_read`: current-shunt veya differential kullanilan pair'ler icin raw channel code okur.
- `temperature_read`: internal temperature raw code okur.
- `vcc_read`: VCC raw code okur.
- `register_read` / `register_write`: 8-bit register seviyesinde tek byte okuma/yazma yapar.

`current_read` dogrudan amper hesaplamasi yapmaz. LTC2991'de akim, shunt uzerindeki
differential raw code ve board tarafinda bilinen shunt milliohm degeriyle application
katmaninda hesaplanmalidir.

## 12. Vitis Workspace Uretimi

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
`self-heal gecti` rozeti gorunur. Basarisiz olursa Doctor panelindeki hata kodu
ve sayilar kok sebebi anlamak icin kalir.

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

## 13. Kodlama Standardi

Spec2Code sabit default coding standard kullanir. Kullanici Word, Markdown veya
ayri JSON standard dokumani vermez.

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

## 14. LLM Kullanimi

LLM varsayilan olarak kapali gelir. Acmak icin OpenAI-compatible endpoint,
tam model adi ve gerekirse API key girilir.

Desteklenen model ailesi uygulama tarafindan sinirlanmaz. Kimi, Qwen veya baska
bir OpenAI-compatible model kullanilabilir.

LLM generate akisi icinde yardimci roldedir:

- Cevap bos, cok uzun, eksik veya timeout olursa hata net gosterilir.
- LLM output dogrudan dosyaya yazilmaz.
- Aday dosya deterministic QC'den gecmeden kabul edilmez.
- Aday reddedilirse mevcut deterministic output korunur.

## 15. Air-gap Notlari

Air-gap Windows ortaminda executable paket en kolay yoldur. Tek gereken:

- `Spec2Code.exe`
- `changelog.md`
- `userguide.md`
- Opsiyonel LLVM/Cppcheck kurulumlari
- Opsiyonel Vitis kurulumu
- Opsiyonel lokal/internal LLM endpoint'i

Source uzerinden gelistirme yapacaksan GitHub Release icindeki source archive ve
offline dependency cache gerekir. Bu kullanici paketinin konusu degildir; source
developer akisi icin repo dokumanlarina bakilmalidir.

## 16. Desteklenen Entegreler

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

Desteklenen cihaz listesi Catalog ekraninda gorulur. Bir cihaz Catalog'da yoksa
deterministik descriptor/codegen destegi yoktur.

## 17. Sorun Giderme

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

- Kart tarafinda TCP server'in calistigindan emin ol.
- Host/port alanlari Windows makineden ulasilabilir olmalidir.
- Firewall veya air-gap ag kurallarini kontrol et.
- Kart server'i gelen satirlari `spec2codeTestbenchDispatchLine()` fonksiyonuna iletmeli ve response satirlarini ayni TCP baglantisindan geri yazmalidir.
- UI once **Baglan** demeden **Gonder** komutunu aktif etmez; baglanti durumu kopuksa yeniden baglan.

## 18. Release Dosyalari

Executable release zip'i sade tutulur:

```text
Spec2Code.exe
changelog.md
userguide.md
```

`changelog.md` en yeni surumden baslayarak tum gecmis release degisikliklerini
icerir. `userguide.md` bu dosyadir.
