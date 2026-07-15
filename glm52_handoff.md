# Spec2Code — GLM 5.2 FP-8 Geliştirme Handoff'u

> Bu doküman, **GLM 5.2 FP-8** modelinin, air-gap (internetsiz) bir Windows
> makinesinde Spec2Code kaynak koduna doğrudan **geliştirme** (yeni özellik,
> hata düzeltme, refactor, yeni cihaz descriptor'ı) yapması için yazıldı.
>
> Sen (GLM 5.2) burada bir **agentic coding assistant** olarak çalışıyorsun:
> dosya okuma/yazma ve kabuk (PowerShell/CMD) araçların var; **computer-use
> (ekran/fare) yok**; **internet yok**. Kod tabanı Türkçe yorumlu, hedef platform
> Windows 10, üretilen kod Xilinx/Vitis gömülü C.
>
> Bu doküman **kendi kendine yeter**: dış link takip etmen gerekmez. Türkçe
> yazıldı; komutlar, kod ve teknik imzalar İngilizce/orijinal bırakıldı.

---

## 0. Önce oku: 60 saniyelik özet

Spec2Code, `xparameters.h` + görsel şema girdisinden **deterministik** olarak
Xilinx gömülü C sürücüleri, test bench'leri ve QC raporu üreten, lokal çalışan
bir web uygulamasıdır (FastAPI backend + React frontend). Üretim, LLM'e değil
**YAML descriptor'lar + Jinja2 template'ler + Python codegen**'e dayanır; LLM
opsiyoneldir ve yalnızca yardımcıdır.

Senin işin genelde şu üçünden biri olacak:
1. **Codegen'i düzeltmek/genişletmek** — `orchestrator/codegen.py`, `cmodel.py`, `tics.py`.
2. **Yeni cihaz eklemek** — `descriptors/<part>.yaml` + `catalog/catalog.json`.
3. **Backend/QC/parser davranışını değiştirmek** — `backend/`, `orchestrator/qc/`.

**Bir değişikliğin "bitti" sayılması için tek ölçüt vardır:**

```text
1) python -m pytest        -> hepsi yeşil
2) python spec2code_cli.py build --spec specs/samples/radar_io_board.spec.json
   -> "QC GEÇTİ" (0 error-level ihlal)
```

Bu ikisi geçmeden hiçbir işi "tamam" deme. Ayrıntı aşağıda.

---

## 1. Altın kurallar (bunlardan sapma)

1. **Deterministik önce gelir.** Çıktı aynı girdi için her zaman aynı olmalı.
   `Date.now()`, rastgelelik, sıralamasız `set`/`dict` iterasyonu → yasak.
2. **Kodlama standardı kutsaldır.** `std/default.ruleset.json` tek kaynaktır.
   Üretilen C kodu bu standarda uymalı; QC bunu makine ile denetler (§6).
   Örn: `uint8_t` **asla** yazma → `unsigned char`. Pointer yıldızı tipe yapışır:
   `XIicPs* spIic`.
3. **Üretilen kod bir dosyada değil, `codegen.py` içinde string olarak durur.**
   Çıktı `.c` dosyasını elle düzeltme; **üreteci** düzelt, sonra yeniden üret (§7).
4. **Test beklentisi = sözleşme.** Bir davranışı değiştirdiysen ve test kırıldıysa,
   önce testin *neden* o değeri beklediğini anla. Testte "SAHA BULGUSU" / "KANITLANMIS
   KOK NEDEN" notu varsa, o test gerçek bir sahadaki hatayı kilitliyordur; körlemesine
   güncelleme — davranışın hâlâ doğru olduğundan emin ol.
5. **CRLF.** Üretilen `.c/.h/.md` her zaman `\r\n` satır sonuyla yazılır (Windows hedef).
6. **Türkçe cevap ver.** Kullanıcı Türkçe konuşur; commit mesajları ve kod yorumları da
   repo'daki mevcut Türkçe üsluba uyar.
7. **Kanıtsız "başarılı" deme.** Bir şeyin geçtiğini söylemeden önce ilgili komutu
   çalıştır ve çıktıyı gör. "Muhtemelen geçer" = geçmedi.
8. **İnternet yok.** `pip install <yeni-paket>` deneme; paket zaten offline cache'te
   yoksa (§4) o yolu kullanma. Yeni bağımlılık gerekiyorsa kullanıcıya söyle, tek
   başına ekleme.

---

## 2. 128K context bütçesi — hayatta kalma stratejisi

Bu repo ~40.000 satır. Context pencaren **128K token**. Tüm repoyu okuyamazsın ve
okumaya çalışırsan bütçeni bitirir, işin ortasında bağlamı kaybedersin. Kural:

**Asla "keşif için" büyük dosyayı baştan sona okuma. Önce haritala, sonra hedefli oku.**

Pratik protokol:

1. **Başlangıç bağlamı** = bu doküman + `README.md` başı + §5'teki repo haritası. Bu kadar.
2. **Bul, sonra oku.** İlgili yeri `grep`/`findstr` ile bul, dosyanın yalnızca o
   bölümünü (±40 satır) oku. Örnek:
   ```powershell
   findstr /S /N /I /C:"RegisterWidthBytes" orchestrator\*.py
   ```
   sonra sadece o satır aralığını aç.
3. **Büyük dosya uyarısı.** Bunları **asla** tümüyle context'e alma; hep grep+offset ile parçala:
   | Dosya | ~satır | Ne |
   |---|---|---|
   | `orchestrator/codegen.py` | ~5000 | Ana codegen (string emit) — en kritik, en büyük |
   | `orchestrator/cmodel.py` | ~1500 | C model / init sekansları |
   | `tests/test_testbench.py` | ~2500 | Test bench testleri |
   | `backend/vitis_workspace.py` | ~1400 | Vitis/XSCT akışı |
   | `changelog.md` | ~2000 | Sürüm geçmişi — referans, okuma |
4. **Bir seferde tek görev.** Görevi bitir, doğrula, sonra bir sonrakine geç.
   Yarım bırakılmış çok-görevli oturum context'i çöpe çevirir.
5. **Özetle, biriktir.** Bulgularını kısa notlar hâlinde tut ("codegen.py:2455
   width fonksiyonu burada"), ham dosya içeriğini context'te tutma.
6. **In-app LLM soru context'i ayrı meseledir.** Uygulamanın kendi bilgi-soru
   ekranı, catalog context'ini modele gönderir ve bu **220.000 karaktere** kadar
   çıkabilir (Qwen 256K sınıfı için tasarlı). GLM 5.2 128K ile o özelliği
   kullanan biri context aşımı görebilir; bu **senin** geliştirme bağlamından
   ayrıdır ama kullanıcı sana "soru ekranı model'i kesiyor" derse sebebi budur —
   çözüm soruyu daraltmak veya `max_response_chars`'ı düşürmektir.

---

## 3. İlk soru: Release'ten hangi dosyaları indirmeliyim?

Kullanıcı bu projeyi Windows'ta **lokal geliştirmek** istiyorsa (sadece
çalıştırmak değil), GitHub Releases'ten şunlar gerekir:

| Dosya | Zorunlu mu | Ne için |
|---|---|---|
| `spec2code-vX.Y.Z-source.zip` | **Evet** | Tam kaynak ağacı (git-tracked). Geliştirme bunun üzerinde yapılır. |
| `spec2code-vX.Y.Z-windows-x64.zip` | Opsiyonel | Sadece çalıştırmak/karşılaştırmak için hazır `.exe`. Geliştirme için gerekmez. |
| `changelog.md` (zip içinde) | — | Sürüm geçmişi. |
| `userguide.md` (zip içinde) | — | Kullanıcı kılavuzu. |
| `glm52_handoff.md` (bu dosya, zip içinde) | — | Bu handoff. |

`.exe` paketi geliştirme yapmaz; sadece server'ı başlatıp derlenmiş UI'yı sunar.
Geliştirme için **source zip** şarttır. Ayrıca offline geliştirme için (§4):

- **Offline bağımlılık cache'i** (`offline/` klasörü) — internet bağlı bir Windows
  makinesinde hazırlanır, air-gap makineye kopyalanır.
- **Kurulum installer'ları:** Python 3.12, Node.js 22 LTS, LLVM (clang-format/
  clang-tidy/libclang.dll), Cppcheck. Bunlar GitHub release'inde **değildir**;
  bağlı bir makineden IT süreciyle taşınır.

---

## 4. Air-gap ortam kurulumu (offline)

Tam ayrıntı `docs/WINDOWS.md`'de. Özet akış:

**Bağlı bir Windows makinesinde** (source zip açılmış hâlde):
```powershell
.\scripts\windows\prepare-offline-deps.ps1 -OfflineRoot offline
```
Bu, `offline\wheels\` (pip wheel'leri) ve `offline\npm-cache\` (npm paketleri)
üretir. Bu `offline\` klasörünü + installer'ları air-gap makineye taşı.

**Air-gap makinede:**
```powershell
Expand-Archive .\spec2code-vX.Y.Z-source.zip -DestinationPath C:\Work
cd C:\Work\spec2code-vX.Y.Z
Copy-Item C:\Transfer\offline .\offline -Recurse

.\scripts\windows\setup-source.ps1 -OfflineRoot offline   # venv + offline pip + npm ci
.\scripts\windows\verify-source.ps1                       # selftest + frontend build
.\scripts\windows\run-source.ps1                          # http://127.0.0.1:8077
```

QC araçları (LLVM + Cppcheck) ayrı kurulur; app onlarsız da başlar ama **tam
deterministik doğrulama** onları ister. Kurulumdan sonra:
```text
http://127.0.0.1:8077/api/health   -> tools yollarının bulunduğunu doğrula
```

**Yeni Python paketi gerekiyorsa:** offline cache'te yoksa kuramaz­sın. Çekirdek
bağımlılıklar `requirements.txt`'te (fastapi, uvicorn, pydantic, jsonschema,
jinja2, watchdog, httpx, pyyaml, libclang, pyserial, python-multipart). RAG
bağımlılıkları (`requirements-rag.txt`: torch, faiss, sentence-transformers)
**çekirdek yol için gerekmez** — kurma. Yeni bir paket ihtiyacı doğarsa
kullanıcıya söyle; o, bağlı makinede wheel'ini indirip cache'e ekler.

---

## 5. Repo haritası

```text
Spec2Code/
├─ run_spec2code.py         # Giriş noktası: uvicorn + backend.main:app, port 8077
├─ spec2code_cli.py         # Headless boru hattı: build [--vitis ...]. UI'sız QC/Vitis.
├─ requirements.txt         # Çekirdek bağımlılıklar (RAG ayrı, kurma)
│
├─ backend/                 # FastAPI katmanı
│  ├─ main.py               # app + route montajı + /api/health
│  ├─ api/routes.py         # REST uçları (~770 satır)
│  ├─ jobs.py               # generate job orkestrasyonu (codegen+QC birleşimi)
│  ├─ ws/jobs.py            # websocket progress
│  ├─ vitis_workspace.py    # XSCT workspace build + self-heal (~1400 satır)
│  ├─ vitis_errors.py       # S2C-VITIS-... hata kodları
│  ├─ testbench.py          # test bench session manager (~940 satır)
│  ├─ s2cmsg.py cit.py yatt.py bringup.py  # S2C-MSG binary protokol, CIT, YATT, bring-up
│  ├─ register_map.py registers.py i2c_scan.py run_on_board.py telnet_log.py
│  ├─ parsers/              # xparameters.py, xsa.py (XSA/hwh okuma)
│  ├─ validators/wiring.py  # generate öncesi wiring doğrulama
│  └─ data/                 # zynqmp_mio_options.json, ddr parts, regmap HTML editor
│
├─ orchestrator/            # DETERMİNİSTİK ÜRETİM ÇEKİRDEĞİ
│  ├─ codegen.py            # ★ Ana codegen — string emit ile .c/.h üretir (~5000 satır)
│  ├─ cmodel.py             # C init sekansları, register R/W modeli (~1500 satır)
│  ├─ tics.py               # TICS Pro (LMK/LMX) SPI register modeli
│  ├─ selftest.py           # python -m orchestrator.selftest → uçtan uca QC
│  ├─ descriptor_check.py descriptor_example.py  # descriptor doğrulama/örnek
│  ├─ device_profiles/      # cihaza özel profiller (ör. ltc2991.py)
│  ├─ templates/*.j2        # Jinja2 (readme vb.)
│  ├─ qc/                   # ★ KALİTE KAPISI
│  │  ├─ loop.py            #   round döngüsü: format→lint→tidy→cppcheck, error gate
│  │  ├─ runners.py         #   clang-format/clang-tidy/cppcheck sarmalayıcıları
│  │  ├─ naming_linter.py   #   libclang AST ile Hungarian/isim denetimi
│  │  └─ bsp_stubs/*.h      #   Xilinx BSP stub başlıkları (clang tip denetimi için)
│  └─ llm/                  # opsiyonel OpenAI-uyumlu istemci (client.py, tasks.py)
│
├─ hostplat/tools.py        # clang/cppcheck/libclang bulma (tek platform-branch modülü)
├─ descriptors/*.yaml       # cihaz davranış tanımları (register map, transport, akışlar)
├─ catalog/catalog.json     # part → descriptor eşlemesi + knowledge pack
├─ std/default.ruleset.json # ★ KODLAMA STANDARDI (tek kaynak)
├─ schemas/*.json           # project.spec + ruleset JSON şemaları
├─ specs/samples/           # radar_io_board.spec.json + örnek xparameters.h'ler
├─ frontend/                # React + Vite + TS + Tailwind + @xyflow (şema)
│  └─ src/{App.tsx, features/*, lib/*, store/*, theme/*}
├─ tests/                   # 22 dosya, ~300+ test (pytest + unittest.subTest)
├─ scripts/                 # build_executable.py, package_release.py, windows/*.ps1
├─ docs/WINDOWS.md          # air-gap Windows kurulum/çalıştırma
└─ .github/workflows/       # auto-release.yml (main push→tag), release.yml (tag→asset)
```

---

## 6. Veri akışı ve mimari

```text
xparameters.h ──parser──► controller'lar (PS/PL)
                              │
     şema UI ─ harici I2C/SPI cihazları ekle ─► project.spec.json
                              │
                    wiring validation (adres çakışması, mux, CS)
                              │
       descriptor(YAML) + template(J2) + codegen.py ──► drivers/ tests/ raporlar
                              │
                     QC LOOP (clang-format, naming-linter, clang-tidy, cppcheck)
                              │
              zip / Vitis-ready zip  ──►  (ops.) XSCT workspace build → app.elf
```

**İki katman, karıştırma:**
- **Deterministik çekirdek** (`orchestrator/`, `descriptors/`, `std/`): girdi=çıktı
  garantisi. Asıl teslim edilen kod buradan çıkar. Testlerin çoğu bunu kilitler.
- **Opsiyonel LLM** (`orchestrator/llm/`): varsayılan KAPALI. Açıksa OpenAI-uyumlu
  bir endpoint'e (ör. lokal vLLM/SGLang ile servis edilen GLM 5.2 FP-8) gider.
  Çıktısı **doğrudan dosyaya yazılmaz**: geçici aday → markdown/boş/kısa reddi →
  mevcut C fonksiyonları silinmemiş mi kontrolü → deterministik QC → ancak error
  yoksa yazılır. Yani LLM asla kalite kapısını atlayamaz.

**GLM 5.2 FP-8'i in-app LLM olarak bağlamak** (kullanıcı isterse):
```powershell
$env:SPEC2CODE_LLM_BASE_URL = "http://127.0.0.1:8000/v1"   # lokal servis
$env:SPEC2CODE_LLM_MODEL     = "endpointte_gorunen_tam_model_adi"  # tahmin edilmez!
$env:SPEC2CODE_LLM_MAX_TOKENS = "4096"
$env:SPEC2CODE_LLM_TIMEOUT_S  = "120"
```
Model adı endpoint'in listelediği **birebir** ad olmalı; Spec2Code isim tahmin etmez.

---

## 7. Kodlama standardı (üretilen C kodu için)

Tek kaynak: `std/default.ruleset.json`. Denetleyici: `orchestrator/qc/naming_linter.py`
(libclang AST). Özet:

| Kural | Değer / örnek |
|---|---|
| Brace | Allman (`{` yeni satırda) |
| Girinti | 4 boşluk, satır ≤ 100, **CRLF** |
| Fonksiyon | camelCase `^[a-z][A-Za-z0-9]*$` → `tca9548aChannelSelect` |
| Değişken | Hungarian: `uc/c/us/s/ui/i/ul/ull` + camelCase (`uiIndex`, `iStatus`) |
| Pointer | skalere `p` (`char*`→`cp`, `unsigned int*`→`uip`); struct*→`sp` (`spIic`) |
| Dizi | `+Arr` (`ucArrWide[2]`); pointer dizisi `cpArr` (`const char* const cpArr...[]`) |
| Struct değişken | `s` (`SBoardCit sCit`) |
| Storage | `static`→`S_`, global→`G_` (en başa: `static ... S_cpArrCitCihaz[]`) |
| Typedef | struct/union→`S` (`SBoardCit`), enum→`E` (`EDurum`) |
| Yasak tip | `uint8_t/uint16_t/uint32_t/...` → primitive C (`unsigned char/short/int`) |
| Pointer yıldızı | tipe yapışık: `XIicPs* spIic` (✅), `XIicPs *spIic` (❌) |
| printf | satır sonu `\r\n` zorunlu (çıplak `\n` = error) |
| Doxygen | public fonksiyonlarda zorunlu |

Bunlar QC'de **error** seviyesindedir; ihlal build'i düşürür.

---

## 8. QC döngüsü — nasıl çalışır, hangi tuzak var

`orchestrator/qc/loop.py`:
1. **format** — clang-format (CRLF de burada yazılır).
2. **checks** — her `.c` için: naming_linter (libclang) + clang-tidy + cppcheck.
3. **gate** — yalnızca `severity == "error"` ihlaller kapıyı düşürür; `warning`
   teslime engel değildir. Rapor `outputs/<proje>/qc_report.json`.
4. **fix round** — LLM fixer verildiyse (opsiyonel) error'ları modele geri besler,
   `max_rounds`'a kadar tekrar. LLM yoksa tek round.

### ★ En önemli tuzak: araç eşitliği
QC, kurulu olmayan aracı **sessizce atlar** (graceful degradation). Yani
clang-tidy/cppcheck kurulu **olmayan** bir makinede (tipik Windows dev makinesi)
QC "GEÇTİ" der ama araçlar kurulu bir makinede (CI, macOS) **aynı kod FAIL** eder.

Bu gerçek bir sahada oldu (v0.1.147): Windows'ta görünmeyen 18 hata, araçların
kurulu olduğu makinede build'i kırdı. **Sonuç: bir codegen değişikliğini "QC geçti"
diye kapatmadan önce clang-tidy + cppcheck + libclang'in gerçekten kurulu ve
bulunmuş olduğunu doğrula:**
```powershell
# /api/health tools alanı 4'ünü de dolu göstermeli, VEYA:
clang-tidy --version ; cppcheck --version ; clang-format --version
```
Eğer araçlar yoksa, "QC geçti" ifaden **eksik** demektir; kullanıcıya araçların
kurulu olmadığını ve tam doğrulamanın CI/araçlı makinede yapılması gerektiğini söyle.

---

## 9. Çalıştırma ve doğrulama komutları

```powershell
# Uçtan uca deterministik selftest (UI/LLM yok) — en hızlı sağlık kontrolü
.\.venv\Scripts\python.exe -m orchestrator.selftest
#   Beklenen: "qc.passed: True"

# Tam test paketi
.\.venv\Scripts\python.exe -m pytest -q
#   Beklenen: "... passed, ... skipped ... subtests passed"

# Headless build (örnek proje) — QC kapısını gerçek CLI ile geçir
.\.venv\Scripts\python.exe spec2code_cli.py build --spec specs\samples\radar_io_board.spec.json
#   Beklenen son satır: "... dosya üretildi; QC GEÇTİ"

# Vitis'e kadar (yalnızca Vitis kurulu Windows'ta)
.\.venv\Scripts\python.exe spec2code_cli.py build --spec my.spec.json ^
    --vitis C:\Xilinx\Vitis\2023.2 --xsa board.xsa --workspace D:\ws --temp D:\tmp

# Uygulamayı çalıştır (UI)
.\.venv\Scripts\python.exe run_spec2code.py --port 8077
# Frontend HMR geliştirme
.\scripts\windows\run-dev.ps1     # http://localhost:5181

# Frontend tip + build (TS hataları burada çıkar)
cd frontend ; npm run build ; cd ..
```

CLI çıkış kodları: `0` başarı, `2` spec geçersiz, `3` codegen/QC hatası, `4` Vitis hatası.

**Definition of done (her değişiklik için):** `pytest` yeşil **ve** `spec2code_cli
build ... radar_io_board` → "QC GEÇTİ". Frontend'e dokunduysan ek olarak `npm run build`.

---

## 10. Değişiklik reçetesi (worked example)

Diyelim üretilen bir `.c` dosyasında QC hatası var:
`ltc2991.c:89 use of undeclared identifier 'XIL_COMPONENT_IS_READY'`.

**Yanlış yol:** `outputs/.../ltc2991.c`'yi elle düzeltmek. O dosya bir sonraki
generate'te silinip yeniden yazılır; kaybolur.

**Doğru yol:**
1. Üreteci veya stub'ı bul:
   ```powershell
   findstr /S /N /I /C:"XIL_COMPONENT_IS_READY" orchestrator\*.py orchestrator\qc\bsp_stubs\*.h
   ```
2. Kök nedeni ayır: kimlik `cmodel.py`'de emit ediliyor ama BSP stub'ında
   tanımlı değil → stub eksik. `orchestrator/qc/bsp_stubs/xil_types.h`'e ekle.
3. Yeniden üret + doğrula:
   ```powershell
   .\.venv\Scripts\python.exe spec2code_cli.py build --spec specs\samples\radar_io_board.spec.json
   .\.venv\Scripts\python.exe -m pytest -q
   ```
4. Test bir string beklentisiyle kırıldıysa (ör. `pcVersion` → `cpVersion`
   yeniden adlandırdın), testteki beklentiyi de güncelle **ama** önce davranışın
   doğru olduğundan emin ol.

**codegen.py'de string emit deseni:** üretilen kod, Python string'leri (çoğunlukla
`lines.extend([...])` veya bitişik string blokları) hâlinde tutulur. Bir C satırını
değiştirmek = o Python string'ini değiştirmek. Girinti C tarafında da anlamlıdır;
`"        if (...)"` gibi başındaki boşlukları koru.

---

## 11. Yeni cihaz ekleme (kısa reçete)

1. `descriptors/<part>.yaml` yaz — mevcut bir benzerini örnek al
   (`descriptors/ltc2991.yaml` I2C, `descriptors/lmk04832.yaml` SPI/TICS).
   Alanlar: `part`, `transport` (type/i2c-address/byte_order), `registers[]`
   (name/offset/width/access/reset), `operations`/`flows`, knowledge notları.
2. `catalog/catalog.json`'a part → descriptor eşlemesini + knowledge pack'i ekle.
3. `descriptor_check.py` ile şema/uyum doğrula:
   ```powershell
   .\.venv\Scripts\python.exe -m orchestrator.descriptor_check descriptors\<part>.yaml
   ```
4. Bir spec'e ekleyip build al; QC'nin geçtiğini gör.
5. Test ekle (`tests/test_user_descriptors.py` / `test_device_profiles.py` desenine bak).

`descriptors/_schema` altında descriptor şeması var; ona uy.

---

## 12. Sık tuzaklar (bunlara düşme)

- **`outputs/` düzenleme** → boşa emek; üreteci düzelt (§10).
- **CRLF unutma** → codegen zaten CRLF yazar; sen elle dosya yazarken Python'da
  `newline` ayarına dikkat, ama üretilen kod yolunda mevcut mekanizmayı kullan.
- **`uint32_t` yazma** → yasak; `unsigned int`.
- **Araçsız "QC geçti"** → §8; clang-tidy/cppcheck yoksa doğrulaman eksiktir.
- **Test string'ini codegen ile senkron tutmama** → codegen'de bir ismi/satırı
  değiştirdiysen `tests/` içinde o string'i arayıp güncelle:
  ```powershell
  findstr /S /N /I /C:"eskiIsim" tests\*.py
  ```
- **Sürüm/changelog atlama** → release öncesi `frontend/src/lib/version.ts` bump +
  `changelog.md` girdisi zorunlu; aksi halde `tests/test_release_docs.py` kırılır (§13).
- **Büyük dosyayı baştan okuma** → §2; context'i öldürür.
- **Ölü dal / sabit koşul** → cppcheck `knownConditionTrueFalse` verir. Bir dalı
  yalnızca gerçekten değişken olabilen koşullarda emit et (v0.1.147'de 2-bayt
  register dalı yalnızca 16-bit register'ı olan cihazlarda üretilecek şekilde
  koşullandı).

---

## 13. Git, sürüm ve release akışı

- **GitHub hesabı:** `PashaBuilds` (gh CLI aktif hesabı bu olmalı).
- **Commit mesajı:** Türkçe, kısa başlık + gövde. Repo mevcut üsluba bak
  (`git log --oneline -15`).
- **Sürüm bump:** `frontend/src/lib/version.ts` içindeki `"vX.Y.Z"` fallback'ini
  artır. Backend sürümü bundan türer (`orchestrator.codegen._app_version`).
- **Changelog:** `changelog.md` en üste `## vX.Y.Z - YYYY-MM-DD` girdisi ekle.
  `test_release_docs.py` hem güncel sürümü hem **tüm mevcut git tag'lerini**
  changelog'da arar; birini atlarsan test kırılır.
- **Release nasıl çıkar:** `main`'e push → `.github/workflows/auto-release.yml`
  `version.ts`'yi okur, o sürüm için tag yoksa `release.yml`'i tetikler.
  `release.yml` source zip/tar + macOS + Windows `.exe` asset'lerini üretip
  Release'e yükler. **Yani manuel tag gerekmez; sürüm bump'ı main'e girince
  release otomatik çıkar.**
- **Executable bundle içeriği** (`scripts/build_executable.py` → `_copy_release_docs`):
  `Spec2Code.exe`, `changelog.md`, `userguide.md`, `glm52_handoff.md`,
  `spec2code_version.txt`. Bundle'a dosya ekler/çıkarırsan
  `tests/test_release_docs.py` beklenen liste ile senkron olmalı.

---

## 14. GLM 5.2 için görev bataryası (kendini kanıtla)

Kullanıcı seni ölçmek isterse bu görevleri verir; ya da **sen kendi kendine**
koşup her adımda doğrulama komutunu çalıştırırsın. Her görev, tam bir
"değiştir → doğrula" döngüsüdür. Zorluk arttıkça context disiplinin (§2) ve
doğrulama disiplinin (§9) sınanır.

### Seviye 1 — Isınma (repo okuryazarlığı, ~5 dk)
> **Görev:** `spec2code_cli.py build` çıkış kodlarını (0/2/3/4) ve her birinin ne
> anlama geldiğini kaynaktan bul; `radar_io_board` örneğini build edip QC'nin
> geçtiğini göster.
>
> **Doğrulama:** `python spec2code_cli.py build --spec specs/samples/radar_io_board.spec.json`
> son satırı "QC GEÇTİ" olmalı; çıkış kodu 0.
>
> **Başarı ölçütü:** Doğru dosya/satır referansı + geçen build. Yanlış: repoyu
> baştan sona okuyup context'i tüketmek.

### Seviye 2 — Küçük, testli düzeltme (~15 dk)
> **Görev:** `std/default.ruleset.json`'daki Hungarian prefiks tablosunda
> `unsigned char`→`uc`. `naming_linter.py`'de pointer-dizi için beklenen prefiksin
> nasıl türetildiğini (`_expected_prefix`) bul ve `const char* const [] → cpArr`
> davranışını bir birim testiyle kanıtla (yeni test dosyası veya mevcut bir
> test'e case ekle).
>
> **Doğrulama:** `python -m pytest -q` yeşil; eklediğin test gerçekten
> `_expected_prefix(...)`'i çağırıp `cpArr` bekliyor.
>
> **Başarı ölçütü:** Yeni test var, geçiyor, mevcut testler kırılmadı.

### Seviye 3 — Codegen davranışı (~30 dk)
> **Görev:** Üretilen bir I2C sürücüsünde, `RegisterWidthBytes` fonksiyonunun
> **yalnızca** 16-bit (geniş) register'ı olan cihazlarda emit edildiğini doğrula
> (`orchestrator/codegen.py`, `_i2c_wide_registers`). Sadece 8-bit register'ı olan
> bir cihaz için bu fonksiyonun ve `ucWidthBytes==2U` dalının **üretilmediğini**
> bir testle kanıtla.
>
> **Doğrulama:** İlgili `tests/test_testbench.py` case'i + tam `pytest` yeşil +
> `radar_io_board` build "QC GEÇTİ".
>
> **Başarı ölçütü:** Ölü dal üretilmiyor; cppcheck `knownConditionTrueFalse` yok.

### Seviye 4 — Yeni cihaz descriptor'ı (~45 dk)
> **Görev:** Basit bir I2C sıcaklık sensörü için minimal descriptor ekle
> (`descriptors/` içindeki `tmp101.yaml`/`sht21.yaml` desenini örnek al),
> `catalog.json`'a bağla, bir spec'te kullanıp build al.
>
> **Doğrulama:** `python -m orchestrator.descriptor_check descriptors/<part>.yaml`
> temiz; build "QC GEÇTİ"; eklediğin descriptor testi yeşil.
>
> **Başarı ölçütü:** Deterministik (iki build byte-aynı), QC temiz, testli.

### Seviye 5 — Uçtan uca akıl yürütme (~60 dk)
> **Görev:** Kullanıcı "Windows'ta QC geçti ama CI kırıldı" diyor. Kök nedeni
> §8'deki araç-eşitliği tuzağı üzerinden açıkla; `qc_report.json`'daki
> `tool_status` ve `final_violations` alanlarından hangi kanıtın bakılacağını
> göster; bir örnek ihlali (ör. `naming.hungarian_prefix`) üreteçte düzelt.
>
> **Doğrulama:** Araçlı makinede (veya araçlar kuruluysa) build "QC GEÇTİ";
> pytest yeşil.
>
> **Başarı ölçütü:** Doğru teşhis + gerçek düzeltme + kanıtlı doğrulama.

**Puanlama rehberi (kullanıcı için):** Her seviyede *doğrulama komutunu gerçekten
çalıştırıp çıktısını raporladı mı?* Kanıtsız "yaptım" = başarısız. Context'i
haritalayarak mı ilerledi yoksa büyük dosyaları baştan okuyup mu tıkandı?
Türkçe ve repo üslubuna uygun mu çalıştı?

---

## 15. Vitis / XSCT hata ayıklama brief'i (air-gap)

Spec2Code'un Vitis workspace akışı hata verdiğinde, **source kodu paylaşmadan
önce** yalnızca log/Tcl/manifest ve dosya listeleri üzerinden kök nedeni ayır.
(Bu bölüm, eski `kimi_vitis_debug_guide.md`'nin özünü taşır.)

### 15.1 Çıktı formatın (kısa, kanıta dayalı)
```text
VERDICT:
- PASS/FAIL:
- Aktif blokaj:
- Recovered/geçmiş hata:

KANIT:
- Dosya / satır (birebir log parçası):
- Neden aktif ya da neden recovered:

KÖK SEBEP ADAYI:
- En olası neden + alternatifler:

ELF DURUMU:
- Beklenen ELF adı / bulunan ELF'ler / application ELF eşleşmesi:

SONRAKI 3 KONTROL:
1. 2. 3.
```

### 15.2 İlk aşamada bakılacak dosyalar
```text
<temp>/logs/xsct_stdout.log
<temp>/logs/xsct_stderr.log
<temp>/logs/xsct_self_heal_stdout.log
<temp>/logs/xsct_self_heal_stderr.log
<temp>/spec2code_create_workspace.tcl
<temp>/spec2code_self_heal_workspace.tcl
<temp>/spec2code_vitis_manifest.json
```

### 15.3 Analiz kuralları
- **Initial ≠ final.** `xsct_stderr.log` ilk denemedir; custom IP hatası orada
  görünse bile self-heal onu kapatmış olabilir. Asıl karar için
  `xsct_self_heal_stderr.log`'a bak; orada fatal imza yoksa ve application ELF
  varsa initial hata **recovered** sayılır.
- **returncode 0 ≠ başarı.** Log içinde şu **build-fatal imzaları** varsa build
  başarısızdır (XSCT 0 dönse bile):
  ```text
  cc1.exe: fatal error        cc1plus.exe: fatal error
  make: ***                   make[1]: ***                gmake: ***
  Failed to build             compilation terminated      collect2.exe: error
  ```
- **Application ELF zorunlu.** FSBL/PMU ELF tek başına yetmez. Beklenen
  `<app_name>.elf` yoksa: app build hiç çalışmamış / source import edilmemiş /
  app adı-klasör uyuşmuyor / link'e geçmemiş olabilir.
- **Custom PL IP `make.libs` hatası.** İmza:
  ```text
  cc1.exe: fatal error: *.c: Invalid argument
  make[1]: *** [.../psu_cortexa53_0/libsrc/<driver>/src/make.libs] Error 2
  Failed to build the bsp sources for domain ...
  ```
  Source'suz custom IP driver klasöründe literal `*.c` derlenmeye çalışılır.
  Patch kanıtı: log içinde `Spec2Code: source-less custom PL IP BSP driver disabled`.
- **lwIP/FreeRTOS.** FreeRTOS test bench TCP agent'ı `SOCKET_API` ister; `RAW_API`
  yanlıştır. Ama bunu yalnızca logda buna dair **hata** varsa aktif kök sebep yap;
  yalnızca uyarıysa missing-ELF/custom-IP fatal'ının önüne geçirme.
- **XSCT hiç çıktı üretmeden takılıyorsa** (`S2C-VITIS-HANG-010`): Vitis 2023.2
  `app create` sırasında `which sdscc` çağırır; bazı Windows'larda bu konsol
  process'i kernel seviyesinde donar. Kontrol:
  ```bat
  wmic process where "name='which.exe'" get ProcessId,ParentProcessId,CommandLine
  ```
  `which sdscc` + parent `eclipse.exe` ise bu senaryodasın; Spec2Code v0.1.79+
  watchdog ile process tree'yi sonlandırır. Kalıcı workaround: Vitis'teki
  `gnuwin\bin\which.exe`'i (yedekleyerek) konsol açmayan bir stub ile değiştir
  (`scripts/vitis_which_stub.c`). Antivirüs/EDR console-child engeli de aynı
  belirtiyi verir — kurumsal makinede önce güvenlik loglarını kontrol ettir.

### 15.4 Windows dosya/imza tarama komutları
```bat
dir /S /B "D:\path\to\workspace\*.elf"
dir /S /B "D:\path\to\temp\*.log"
findstr /S /N /I /C:"fatal error" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"make[1]: ***" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"set app_name" "D:\path\to\temp\*.tcl"
findstr /S /N /I /C:"importing generated sources" "D:\path\to\temp\*.log"
findstr /S /N /I /C:"spec2code_test_sw" "D:\path\to\workspace\*.log"
```

### 15.5 Source kodu ne zaman verilmeli?
Yalnızca şu kanıtlardan biri varsa: app build logunda **generated .c/.h**'de
compile error; `undefined reference`/missing `main`; belirli generated dosya
compile etmiyor; `xparameters.h` makro uyumsuzluğu compile logunda görünüyor.
O zaman **tüm repo değil**, sadece ilgili `.c/.h` + `xparameters.h` +
`spec2code_create_workspace.tcl` + ilgili log parçası verilir.

---

## 16. Hızlı referans kartı

```text
Sağlık:      python -m orchestrator.selftest            -> qc.passed: True
Testler:     python -m pytest -q                        -> hepsi yeşil
Build+QC:    python spec2code_cli.py build --spec specs\samples\radar_io_board.spec.json
UI:          python run_spec2code.py --port 8077        -> http://127.0.0.1:8077
Sağlık API:  http://127.0.0.1:8077/api/health           -> tools yolları dolu mu?
Frontend:    cd frontend & npm run build                -> TS hataları burada
Ara:         findstr /S /N /I /C:"desen" orchestrator\*.py
Standard:    std\default.ruleset.json  (denetim: orchestrator\qc\naming_linter.py)
QC raporu:   outputs\<proje>\qc_report.json  (final_violations, tool_status)
Sürüm:       frontend\src\lib\version.ts  + changelog.md  (release öncesi bump)
Release:     main'e push -> auto-release.yml tag'ler -> release.yml asset üretir
Hesap:       PashaBuilds
```

**Son söz:** Kanıt her zaman iddiadan önce gelir. Bir şeyi değiştirdin mi —
`pytest` + `radar_io_board build` koştur, çıktıyı gör, sonra "bitti" de. İnternet
yok, ekran yok; elindeki tek gerçek, çalıştırdığın komutun çıktısıdır.
