# Spec2Code Changelog

Bu dosya release paketlerinin icine girer ve gecmis tum release degisikliklerini
tek yerde tutar. En yeni surum her zaman en usttedir.

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
