# Kimi Vitis Debug Guide

Bu dokuman, Spec2Code ile uretilen Vitis workspace akisi hata verdiginde lokal
LLM'e ilk asamada verilecek debug brief'idir. Amac source kodu paylasmadan once
yalnizca log, Tcl ve workspace ciktisi uzerinden kok sebebi ayirmaktir.

## 1. Kimi'ye Verilecek Baslangic Promptu

Asagidaki metni Kimi'ye aynen ver:

```text
Sen airgap ortamda calisan bir Vitis/XSCT build debug yardimcisisin.
Sadece sana verdigim log, Tcl script, dosya listesi ve Spec2Code Doctor
ozetlerini kullan. Dis bilgi, tahmin veya datasheet bilgisi uydurma.

Onceliklerin:
1. Initial build hatasi ile final/recovery build hatasini ayir.
2. xsct_stderr.log icindeki eski hata self-heal ile kapanmis mi, yoksa
   xsct_self_heal_stderr.log icinde hala aktif mi kontrol et.
3. XSCT returncode 0 olsa bile log icinde build-fatal imzasi varsa bunu
   basarili sayma.
4. Beklenen application ELF uretilmis mi kontrol et.
5. Sonucu kisa, kanit satirlarina dayali ve aksiyon alinabilir sekilde yaz.

Kullanman gereken fatal imzalar:
- cc1.exe: fatal error
- cc1plus.exe: fatal error
- make: ***
- make[1]: ***
- gmake: ***
- Failed to build
- compilation terminated
- collect2.exe: error

Cikti formatin su olsun:

VERDICT:
- PASS/FAIL:
- Aktif blokaj:
- Recovered/gecmis hata:

KANIT:
- Dosya:
- Satir veya birebir log parcasi:
- Neden aktif veya neden recovered:

KOK SEBEP ADAYI:
- En olasi neden:
- Alternatif nedenler:

ELF DURUMU:
- Beklenen ELF adi:
- Bulunan ELF dosyalari:
- Application ELF eslesmesi var mi:

SONRAKI 3 KONTROL:
1.
2.
3.

SPEC2CODE ICIN ONERI:
- Uygulama tarafinda degistirilecek bir sey var mi?
- Yoksa kullanici tarafinda Vitis/BSP ayari mi gerekiyor?
```

## 2. Ilk Asamada Verilecek Dosyalar

Source kodu vermeden once su dosyalari ver:

```text
<temp_or_staging>/logs/xsct_stdout.log
<temp_or_staging>/logs/xsct_stderr.log
<temp_or_staging>/logs/xsct_self_heal_stdout.log
<temp_or_staging>/logs/xsct_self_heal_stderr.log
<temp_or_staging>/spec2code_create_workspace.tcl
<temp_or_staging>/spec2code_self_heal_workspace.tcl
```

Varsa bunlari da ekle:

```text
Vitis Doctor ekran goruntusu veya metin ozeti
Workspace dizini altindaki *.elf dosya listesi
Temp/Staging dizini altindaki *.elf dosya listesi
App, platform, system ve processor adlari
Spec2Code surumu
Vitis/XSCT surumu
Runtime: standalone veya freertos10_xilinx
lwIP API mode: RAW_API veya SOCKET_API
Custom IP policy: Auto: custom IP - none veya keep
```

Sirket icindeki path'ler veya IP isimleri gizli kabul ediliyorsa path'leri
sanitize edebilirsin. Ancak dosya adi, log satiri ve hata imzasi korunmali.

## 3. ZCU102 / Custom IP Yok / Application ELF Yok Senaryosu

Bu senaryo custom PL IP probleminden farklidir. Tipik durum:

```text
XSA: ZCU102 veya custom IP icermeyen temiz XSA
Custom IP adaylari: 0
XSA make.libs: 0
Workspace BSP make.libs: 0
FSBL/PMU gibi ELF dosyalari var
Beklenen application ELF yok: spec2code_test_sw.elf
XSCT stderr icinde belirgin compiler error yok
UI'da unclassified olarak normal gorunebilecek bir satir cikmis olabilir:
aarch64-none-elf-ar: creating ../../lib/libfreertos.a
```

Bu durumda Kimi custom IP tarafina odaklanmamali. Oncelik application project
olustu mu, generated source import edildi mi, app build gercekten calisti mi ve
application build logu nerede sorularidir.

### 3.1 Kimi'ye Verilecek Hedefli Prompt

Asagidaki metni Kimi'ye aynen ver:

```text
Bu debug oturumu custom PL IP hatasi degil. XSA ZCU102 / custom IP yok gibi
gorunuyor. Spec2Code Doctor'da custom IP aday sayisi 0, XSA make.libs 0,
workspace make.libs 0. FSBL/PMU ELF dosyalari uretilmis, fakat beklenen
application ELF uretilmemis.

Beklenen application ELF:
spec2code_test_sw.elf

Gorunen onemli ipucu:
aarch64-none-elf-ar: creating ../../lib/libfreertos.a

Bu satiri tek basina hata kabul etme; FreeRTOS BSP library olusurken normal
bir archive creation satiri olabilir. Asil hata application build logunda,
application import/build adiminda veya app proje hedefinde olabilir.

Sadece sana verdigim log, Tcl script, manifest ve dosya listelerini kullan.
Dis bilgi uydurma. Source kod verilmediyse source kod hakkinda tahmin yapma.

Onceliklerin:
1. spec2code_create_workspace.tcl icinde app_name, platform_name, system_name,
   domain_name ve processor degerlerini cikar.
2. xsct_stdout.log ve xsct_stderr.log icinde su adimlarin gecip gecmedigini
   kanit satirlariyla kontrol et:
   - creating named platform/system/application from XSA
   - importing generated sources
   - building application
   - done
3. Workspace dosya listesinde app proje klasoru var mi kontrol et.
4. Workspace dosya listesinde app Debug/Release klasoru ve app build loglari
   var mi kontrol et.
5. Tum *.elf listesini incele; FSBL/PMU ELF ile application ELF'i ayir.
6. Application ELF yoksa bunun nedeni:
   - app build hic calismamis,
   - app build calismis ama hata logu ayrica workspace altinda kalmis,
   - sources import edilmemis,
   - app name/path beklenenden farkli,
   - app link asamasina gecmemis,
   seceneklerinden hangisine daha yakin?
7. aarch64-none-elf-ar libfreertos.a satirini sadece FreeRTOS BSP build
   kaniti olarak yorumla; baska fatal imza yoksa bunu root cause yapma.

Cikti formatin su olsun:

VERDICT:
- PASS/FAIL:
- Aktif blokaj:
- Custom IP ile ilgili mi: Evet/Hayir

KANIT:
- app_name:
- processor:
- runtime/os:
- XSCT adim kanitlari:
- Application proje klasoru kaniti:
- Application build log kaniti:
- ELF listesi kaniti:

ELF DURUMU:
- Beklenen ELF:
- Bulunan application disi ELF'ler:
- Application ELF eslesmesi var mi:

KOK SEBEP ADAYI:
- En olasi neden:
- Alternatif nedenler:
- Bunu destekleyen log/path kaniti:

KIMI'NIN ISTEDIGI EK DOSYALAR:
- Source kod istemeden once eksik olan log/path listesi:

SPEC2CODE ICIN ONERI:
- UI/backend hangi ek logu gostermeli?
- Missing application ELF durumunda hangi workspace klasorleri taranmali?
- Mapper hangi satiri yanlis unclassified hata gibi yorumlamis olabilir?
```

### 3.2 Bu Senaryoda Verilecek Dosyalar

Kimi'ye source koddan once su dosyalari ve komut ciktilari ver:

```text
<temp_or_staging>/spec2code_vitis_manifest.json
<temp_or_staging>/spec2code_create_workspace.tcl
<temp_or_staging>/logs/xsct_stdout.log
<temp_or_staging>/logs/xsct_stderr.log
Vitis Doctor ekran goruntusu veya metin ozeti
Workspace altindaki *.elf listesi
Workspace altindaki *.log listesi
Workspace altindaki app_name iceren path listesi
Temp/Staging altindaki *.elf listesi
Temp/Staging altindaki *.log listesi
```

Bu durumda `xsct_self_heal_*` dosyalari yoksa sorun degil; self-heal gerekmemis
olabilir. Varsa yine de ver, ama custom IP aday sayisi 0 ise Kimi bunu ana yol
haline getirmemeli.

### 3.3 Windows Komutlari

Path'leri kendi workspace ve temp dizinine gore duzenle:

```bat
dir /S /B "D:\path\to\workspace\*.elf"
dir /S /B "D:\path\to\workspace\*.log"
dir /S /B "D:\path\to\workspace\*spec2code_test_sw*"
dir /S /B "D:\path\to\temp\*.elf"
dir /S /B "D:\path\to\temp\*.log"
dir /S /B "D:\path\to\temp\*.tcl"
```

Mevcut Spec2Code debug dizinleri `D:\Projects\claude\Spec2Code` altinda
kullaniliyorsa Kimi'ye su path'leri soyle:

```text
Spec2Code kok dizin:
D:\Projects\claude\Spec2Code

Temp/Staging dizini:
D:\Projects\claude\Spec2Code\0_temp

Workspace dizini:
D:\Projects\claude\Spec2Code\0_workspace
```

Bu path'lerle dogrudan calistirilacak komutlar:

```bat
dir /S /B "D:\Projects\claude\Spec2Code\0_workspace\*.elf"
dir /S /B "D:\Projects\claude\Spec2Code\0_workspace\*.log"
dir /S /B "D:\Projects\claude\Spec2Code\0_workspace\*spec2code_test_sw*"
dir /S /B "D:\Projects\claude\Spec2Code\0_temp\*.elf"
dir /S /B "D:\Projects\claude\Spec2Code\0_temp\*.log"
dir /S /B "D:\Projects\claude\Spec2Code\0_temp\*.tcl"
```

Application build ve import izlerini aramak icin:

```bat
findstr /S /N /I /C:"set app_name" "D:\path\to\temp\*.tcl"
findstr /S /N /I /C:"importing generated sources" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"building application" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"app build" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"Empty Application" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"named platform/system flow failed" "D:\path\to\temp\*.log"
```

Mevcut debug dizinleri icin:

```bat
findstr /S /N /I /C:"set app_name" "D:\Projects\claude\Spec2Code\0_temp\*.tcl"
findstr /S /N /I /C:"importing generated sources" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"building application" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"app build" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"platform build" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"BSP regenerate before app build" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"Empty Application" "D:\Projects\claude\Spec2Code\0_temp\*.log"
findstr /S /N /I /C:"named platform/system flow failed" "D:\Projects\claude\Spec2Code\0_temp\*.log"
```

Workspace altindaki gercek app build hatalarini aramak icin:

```bat
findstr /S /N /I /C:"error:" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"fatal error" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"undefined reference" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"No rule to make target" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"Nothing to be done" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"main" "D:\path\to\workspace\*.log"
findstr /S /N /I /C:"spec2code_test_sw" "D:\path\to\workspace\*.log"
```

Mevcut debug dizinleri icin:

```bat
findstr /S /N /I /C:"error:" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"fatal error" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"undefined reference" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"No rule to make target" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"Nothing to be done" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"main" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
findstr /S /N /I /C:"spec2code_test_sw" "D:\Projects\claude\Spec2Code\0_workspace\*.log"
```

Bu komutlar hata bulmazsa Kimi su noktayi acik yazmali:

```text
Verilen loglarda application build'in neden ELF uretmedigi kanitlanamiyor.
Workspace icindeki app project metadata, build loglari veya Vitis GUI project
tree bilgisi gerekiyor. Source kod istemek icin henuz yeterli kanit yok.
```

### 3.4 Bu Senaryoda Source Kodu Ne Zaman Verilmeli?

Source kod sadece su kanitlardan biri varsa verilmeli:

```text
Workspace app build logunda generated .c/.h dosyasina ait compile error var.
Link logunda undefined reference veya missing main var.
Application source import edilmis ama belirli source dosyasi compile etmiyor.
xparameters.h macro uyumsuzlugu application compile logunda gorunuyor.
```

Bu kanit yoksa once app build loglari, project path'leri ve generated source'un
Vitis app projesine import edilip edilmedigi bulunmali.

## 4. Windows'ta Hizli Dosya Listesi Cikarma

Bu komutlar Windows ortaminda lokal olarak calistirilip ciktisi Kimi'ye
verilebilir. Path'leri kendi workspace/temp dizinine gore duzenle.

```bat
dir /S /B "D:\path\to\workspace\*.elf"
dir /S /B "D:\path\to\temp\*.elf"
dir /S /B "D:\path\to\temp\*.log"
dir /S /B "D:\path\to\temp\*.tcl"
```

Fatal imza aramak icin:

```bat
findstr /S /N /I /C:"fatal error" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"make[1]: ***" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"make: ***" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"Failed to build" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"compilation terminated" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"mem_pcie_intr" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"set app_name" "D:\path\to\temp\*.tcl"
```

## 5. Analiz Kurallari

### 5.1 Initial hata ve final hata ayrimi

`xsct_stderr.log` ilk denemeyi gosterir. Burada custom IP hatasi gorunebilir.
Bu tek basina aktif blokaj demek degildir.

Eger self-heal denendiyse asil karar icin once sunlara bak:

```text
xsct_self_heal_stdout.log
xsct_self_heal_stderr.log
```

Recovery loglarinda fatal imza yoksa ve application ELF bulunuyorsa initial
custom IP hatasi recovered kabul edilebilir.

Recovery loglarinda fatal imza varsa, initial hata recovered sayilmaz.

### 5.2 Returncode 0 tek basina basari degildir

Vitis/XSCT bazi durumlarda ic build hatalarina ragmen process seviyesinde `0`
donebilir. Bu nedenle log icinde su imzalar varsa build basarisiz sayilmalidir:

```text
cc1.exe: fatal error
cc1plus.exe: fatal error
make: ***
make[1]: ***
Failed to build
compilation terminated
collect2.exe: error
```

### 5.3 Custom PL IP make.libs hatasi

Tipik imza:

```text
cc1.exe: fatal error: *.c: Invalid argument
make[1]: *** [Makefile:46: psu_cortexa53_0/libsrc/<driver>/src/make.libs] Error 2
Failed to build the bsp sources for domain ...
```

Bu genelde source dosyasi olmayan custom PL IP driver klasorunde `make.libs`
icindeki literal `*.c` derlenmeye calistigi anlamina gelir.

Kimi su sorulari cevaplamali:

```text
Hata sadece xsct_stderr.log icinde mi?
Yoksa xsct_self_heal_stderr.log icinde de var mi?
Hangi driver adi geciyor?
make.libs path'i application BSP, FSBL BSP veya PMU/PMUFW BSP altinda mi?
Spec2Code patch'i gercekten bu path'e uygulanmis mi?
```

Patch kaniti olarak su metin aranabilir:

```text
Spec2Code: source-less custom PL IP BSP driver disabled
```

### 5.4 Missing ELF hatasi

Spec2Code icin workspace basarili sayilmak zorunda olan artifact application
ELF'tir. FSBL veya PMU ELF'i tek basina yeterli degildir.

Kontrol:

```text
Beklenen app adi: <app_name>
Beklenen ELF: <app_name>.elf
Workspace altinda bulunan tum *.elf dosyalari
Temp/Staging altinda bulunan tum *.elf dosyalari
```

Eger toplam ELF var ama application ELF yoksa:

```text
FSBL/PMU build gecmis olabilir, application build gecmemis olabilir.
Application proje adi UI'daki app_name ile Vitis'in olusturdugu klasor arasinda
uyusmuyor olabilir.
Application source import edilmemis olabilir.
Application build hedefi calismamis olabilir.
```

### 5.5 lwIP ve FreeRTOS kontrolu

FreeRTOS kullaniliyorsa Test Bench TCP agent icin lwIP API mode `SOCKET_API`
olmali. `RAW_API` FreeRTOS socket kullanan agent icin yanlis secimdir.

Kimi sadece logda bu konuya dair hata varsa bunu aktif kok sebep yapsin.
Sadece uyari olarak gorunuyorsa missing ELF veya custom IP fatal yerine
gecirmesin.

## 6. Kimi'nin Vermesi Gereken Sonuc

Kimi uzun genel aciklama yazmamali. Beklenen cevap boyle olmali:

```text
VERDICT:
- FAIL
- Aktif blokaj: xsct_self_heal_stderr.log icinde mem_pcie_intr_v1_0 make.libs
  build hatasi devam ediyor.
- Recovered/gecmis hata: Yok. Initial hata recovery logunda da tekrar ediyor.

KANIT:
- xsct_self_heal_stderr.log: cc1.exe: fatal error: *.c: Invalid argument
- xsct_self_heal_stderr.log: make[1]: *** [.../mem_pcie_intr_v1_0/src/make.libs] Error 2
- xsct_self_heal_stderr.log: Failed to build the bsp sources ...

KOK SEBEP ADAYI:
- Source'suz custom PL IP driver make.libs hala patchlenmemis veya Vitis
  recovery sirasinda patch'ten sonra ayni make.libs'i yeniden uretmis.

ELF DURUMU:
- Beklenen ELF: spec2code_test_sw.elf
- Bulunan ELF: fsbl.elf, pmufw.elf gibi application disi ELF'ler
- Application ELF eslesmesi: Yok

SONRAKI 3 KONTROL:
1. Recovery logunda gecen tam make.libs path'inde patch metni var mi bak.
2. Bu make.libs FSBL/PMU BSP altindaysa patch kapsaminda mi kontrol et.
3. App build logunda application source import/build adimi calismis mi kontrol et.

SPEC2CODE ICIN ONERI:
- Recovery build oncesi ve sonrasinda logda gecen make.libs hedeflerini
  tekrar patchle; build-fatal imzasi varsa self-heal basarili sayma.
```

## 7. XSCT Hicbir Cikti Uretmeden Takiliyorsa (S2C-VITIS-HANG-010)

Belirti: `xsct_stdout.log` icinde son satir
`[Spec2Code] creating named platform/system/application from XSA` (veya
`Starting vitis.bat` / sysconfig uyarilari) ve dakikalarca yeni satir yok.
Workspace altinda app projesi `src/lscript.ld` disinda bos, FSBL/PMU compile
baslamamis.

Kok sebep: Vitis 2023.2 `app create` sirasinda SDSoC eklentisi
`which sdscc` komutunu calistirir ve ciktisini bekler. Bazi Windows
makinelerinde Vitis cmdline service (eclipse.exe) altindan spawn edilen bu
konsol process'i console initialisation asamasinda kernel seviyesinde donar;
process Task Manager'dan bile oldurulemez ve `app create` sonsuza dek doner.

Kontrol:

```bat
tasklist /FI "IMAGENAME eq which.exe"
wmic process where "name='which.exe'" get ProcessId,ParentProcessId,CommandLine
```

`CommandLine = which sdscc` ve parent `eclipse.exe` ise bu senaryodasin.

Spec2Code v0.1.79+ bu durumda watchdog ile process tree'yi sonlandirir ve
`S2C-VITIS-HANG-010` kodunu gosterir; loglar `logs/` altinda kalir.

Makine tarafindaki kalici workaround (Vitis kurulumunda kucuk bir degisiklik
gerektirir, yedegi alinarak yapilmali):

```text
1. C:\<VitisKurulumu>\Vitis\2023.2\gnuwin\bin\which.exe dosyasini
   which.exe.backup olarak yedekle.
2. Yerine konsol acmayan (GUI-subsystem) bir which stub'i koy. Stub,
   SearchPath ile arguman olarak verilen exe'yi PATH'te arar; bulursa yolu
   yazip 0, bulamazsa 1 ile cikar. sdscc 2023.2'de zaten yoktur; normal
   makinelerde bu komut aninda exit 1 doner ve akis devam eder.
3. Geri almak icin yedegi geri kopyala.
```

Antivirus/EDR console-child engellemesi de ayni belirtiyi verebilir; kurumsal
makinede once guvenlik yazilimi loglarini kontrol ettir.

## 8. Source Kodu Ne Zaman Verilmeli?

Ilk asamada source kod verilmemeli. Source kod ancak su durumlardan biri varsa
verilmeli:

```text
Loglar uygulama tarafindaki generated C/H kaynaklarinda compile hatasi gosteriyor.
Undefined reference, missing include, unknown type veya XPAR macro uyumsuzlugu var.
Application source import edilmis ama belirli bir generated dosyada hata var.
Kimi, kanit satirlariyla source incelemesi gerektigini acikca soyluyor.
```

Bu durumda sadece ilgili generated `.c/.h`, `xparameters.h`, `spec2code_create_workspace.tcl`
ve ilgili compile log parcasi verilmeli. Tum repo kaynak kodu son secenek olmalidir.
