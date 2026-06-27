# Spec2Code

Spec2Code, Xilinx/Vitis tabanlı gömülü projeler için yerel çalışan bir
donanımdan sürücüye kod üretim aracıdır. `xparameters.h` dosyasını okur,
harici I2C/SPI cihazları görsel şemaya eklemeni sağlar ve Vitis application
katmanına kopyalanabilecek `.c/.h` sürücüleri, testleri ve QC raporunu üretir.

Hedef kullanım: macOS üzerinde geliştirme, air-gap Windows 10 üzerinde çalıştırma
ve devam geliştirme.

## Neler Sağlar?

- **Vivado benzeri şema ekranı:** `xparameters.h` içinden controller'ları çıkarır,
  PS/PL bölgelerine yerleştirir ve harici cihazları görsel olarak bağlatır.
- **Descriptor tabanlı deterministik üretim:** Cihaz davranışı YAML descriptor'lardan
  gelir; template'ler aynı input için aynı çıktıyı üretir.
- **Generate öncesi wiring validation:** controller referansları, I2C adres
  çakışmaları, mux/channel hataları, SPI chip-select çakışmaları ve descriptor
  uyumsuzlukları generate başlamadan yakalanır.
- **QC loop:** clang-format, naming-linter/libclang, clang-tidy ve cppcheck ile
  kod formatı ve statik kontroller yapılır.
- **Project save/load:** UI'daki proje `project.spec.json` olarak indirilebilir ve
  daha sonra aynı dosyadan geri yüklenebilir.
- **Sabit kodlama standardı:** Generate ve QC her zaman `std/default.ruleset.json`
  ile çalışır; kullanıcıdan Word/JSON standard dosyası alınmaz.
- **Cihaz konfigürasyon profilleri:** `device.config` üzerinden karttaki kullanım
  şeklini toplar; LTC2991 için pair/mode seçimi init register array'ine çevrilir.
- **İndirilebilir çıktı ağacı:** Generate sonrası `drivers/`, `tests/`, raporlar ve
  varsa `reference_sources/` hiyerarşik gösterilir; tek dosya veya tüm çıktı zip
  olarak indirilebilir.
- **Vitis-ready export:** Ayrı Vitis paketi, `src/drivers`, `src/tests`,
  `src/spec2code_selftest_main.c`, `meta/project.spec.json` ve Türkçe entegrasyon
  README'si içerir.
- **Opsiyonel LLM:** OpenAI-compatible lokal endpoint kullanılabilir. Model adı
  kullanıcıdan tam olarak alınır; Kimi, Qwen veya başka bir model aynı alandan
  kullanılabilir. Timeout ve cevap uzunluğu limitleri açıktır.

## Temel Akış

```text
xparameters.h
  -> parser
  -> şema + harici cihaz bağlantıları
  -> project.spec.json
  -> descriptor + template tabanlı codegen
  -> import edilmiş referans kaynaklar
  -> QC
  -> drivers/tests/raporlar
  -> normal zip veya Vitis-ready zip
```

Dosya vermesen bile kod üretilebilmesinin sebebi budur: üretim, mevcut
`descriptors/*.yaml` dosyaları ve `orchestrator/templates/*.j2` template'leri ile
deterministik yapılır. Yani LTC2991, TCA9548A, MT25Q128, AD7414, DS1682 ve
LTC2945 gibi desteklenen cihazlar için hazır descriptor varsa dış kaynak dosyaya
ihtiyaç yoktur.

Senin verdiğin `.c/.h` dosyalar **Import** ekranında taranır ve parça ile
eşleştirilirse `catalog/imported.json` içine kaydedilir. Bu sürümde bu dosyalar
deterministik üretimi doğrudan değiştirmez; ilgili part projede kullanıldığında
çıktıya `reference_sources/<part>/` altında referans olarak kopyalanır. Böylece
Vitis paketinde hem Spec2Code üretimi hem de senin verdiğin orijinal kaynaklar
birlikte taşınır. Sonraki adım, bu kaynaklardan descriptor taslağı üretme akışını
daha otomatik hale getirmektir.

## Cihaz Konfigürasyonu

Bağlantı bilgisi `attach` altında, karttaki kullanım/mode bilgisi `config` altında
saklanır. LTC2991 eklediğinde sağ panelde **Configuration** bölümü görünür:

- `V1/V2`, `V3/V4`, `V5/V6`, `V7/V8` çiftleri için `Off`, `SE V`, `Diff V`,
  `Current`, `Temp` modu seçilir.
- `Current` seçilirse shunt değeri mΩ cinsinden zorunlu olur.
- Internal temperature ve VCC read enable seçenekleri aynı config içine yazılır.
- UI'daki init preview, generate sırasında C dosyasına `S_ltc2991_init_sequence`
  static array'i olarak girer.

Örnek `project.spec.json` parçası:

```json
"config": {
  "pairs": {
    "v1_v2": { "mode": "single_ended_voltage", "shunt_milliohm": null },
    "v3_v4": { "mode": "differential_voltage", "shunt_milliohm": null },
    "v5_v6": { "mode": "current_shunt", "shunt_milliohm": 10 },
    "v7_v8": { "mode": "disabled", "shunt_milliohm": null }
  },
  "internal_temperature": true,
  "vcc_read": false
}
```

Bu model generic altyapı + cihaz özel profile/editor şeklinde ilerler. Şu anda
özel profile LTC2991 için aktiftir; diğer cihazlar descriptor default'larıyla
çalışmaya devam eder.

## Kodlama Standardı Nasıl Çalışır?

Spec2Code sabit bir default kodlama standardı kullanır. `project.spec.json`
içinde eski sürümlerden kalan farklı bir `coding_standard_ref` görülse bile
generate/QC aşamasında şu ref'e normalize edilir:

```json
"coding_standard_ref": "std/default.ruleset.json"
```

Bu ruleset iki aşamada devreye girer:

1. **Codegen aşaması:** header yorumları, public API isimleri ve bazı template
   kararları ruleset referansına göre üretilir.
2. **QC aşaması:** `.clang-format` ruleset'ten türetilir; naming-linter,
   print terminator ve fonksiyon isimlendirme gibi makinece kontrol edilebilir
   kuralları JSON ruleset'ten okur.

Default standard özet olarak şunları içerir:

- `camelCase` identifier yaklaşımı ve Hungarian prefix kullanımı.
- Fonksiyon adları camelCase yazılır; örnek
  `int tca9548aChannelSelect(XIicPs* spIic, unsigned char ucChannel)`.
- Tip prefixleri: `unsigned char -> uc`, `char -> c`, `unsigned short -> us`,
  `short -> s`, `unsigned int -> ui`, `int -> i`, `unsigned long -> ul`,
  `unsigned long long -> ull`.
- Fixed-width typedef kullanılmaz: `uint8_t`, `uint16_t`, `uint32_t` yerine
  `unsigned char`, `unsigned short`, `unsigned int` gibi primitive C tipleri kullanılır.
- Structure typedef adları büyük `S` ile başlar; örnek `SOrnekStruct`.
- Structure değişkenleri küçük `s` prefix'iyle yazılır; örnek
  `SOrnekStruct sMyStruct; sMyStruct.uiVal = 0;`.
- Enum typedef adları büyük `E` ile başlar; örnek `EOrnekEnum`.
- Structure pointer değişkenleri `sp` prefix'iyle yazılır; diğer pointer'lar
  tip prefix'i + `p`. Pointer yıldızı tipe bitişik yazılır: `XIicPs* spIic`,
  `unsigned char* ucpValue`.
- Array'ler tip prefix'i + `Arr`; örnek `ucArr`.
- Global değişkenler `G_` + tip prefix'i, static değişkenler `S_` + tip prefix'i.
- `if`, `for`, `while` sonrasında bir boşluk ve Allman brace stili kullanılır.
- Bitfield üyelerinde Hungarian prefix kullanılmaz.

Setup ekranındaki **Sabit kodlama standardı** paneli bu kuralları bilgi amaçlı
gösterir. Kullanıcıdan kodlama standardı dokümanı alınmaz; LLM açıksa bile bu
standard sadece context olarak modele verilir ve deterministic QC yine bu ruleset
üzerinden çalışır.

## LLM Ayarları

LLM varsayılan olarak kapalıdır. Açarsan OpenAI-compatible endpoint ve endpoint'in
listelediği **tam model adını** vermen gerekir. Spec2Code model ismi tahmin etmez;
Kimi, Qwen veya başka bir model aynı alanla çalışır.

UI'da veya `project.spec.json` içinde kullanılan alanlar:

```json
"llm": {
  "enabled": true,
  "base_url": "http://127.0.0.1:11434/v1",
  "model": "endpointte_gorunen_tam_model_adi",
  "api_key": "",
  "timeout_s": 120,
  "max_tokens": 4096,
  "max_response_chars": 120000,
  "retries": 0
}
```

Ortam değişkenleri de kullanılabilir:

```bash
export SPEC2CODE_LLM_BASE_URL="http://127.0.0.1:11434/v1"
export SPEC2CODE_LLM_MODEL="endpointte_gorunen_tam_model_adi"
export SPEC2CODE_LLM_API_KEY=""
export SPEC2CODE_LLM_TIMEOUT_S="120"
export SPEC2CODE_LLM_MAX_TOKENS="4096"
export SPEC2CODE_LLM_MAX_RESPONSE_CHARS="120000"
export SPEC2CODE_LLM_RETRIES="0"
```

Model cevap vermezse timeout hatası generate console'da `LLM` satırında görev adı ve
hata mesajıyla görünür. Model cevabı `max_tokens` nedeniyle kesilirse veya cevap
`max_response_chars` limitini aşarsa çıktı kullanılmaz; hata açıkça raporlanır.

LLM'in ürettiği cevap doğrudan dosyaya yazılmaz. Önce geçici bir aday dosyaya alınır ve şu
kapılardan geçer:

- Markdown/prose, boş cevap, kontrol karakteri ve şüpheli kısa çıktı reddedilir.
- Mevcut C fonksiyonlarının kaldırılmadığı kontrol edilir.
- Aday dosya kurulu deterministik araçlarla kontrol edilir: `clang-format`, naming linter,
  `clang-tidy` ve `cppcheck`.
- Sadece hata seviyesinde ihlal yoksa gerçek dosyanın yerine yazılır.
- Aday reddedilirse mevcut dosya korunur; olay generate console'da `LLM QC` satırıyla görünür.

Sonrasında normal QC round'u yine tüm proje üzerinde çalışır. Yani LLM sadece yardımcıdır;
teslim edilecek çıktı deterministik kalite kapısından geçmeden kabul edilmez.

## Windows'ta Çalıştırma

GitHub Releases içinden Windows paketini indir:

```text
spec2code-vX.Y.Z-windows-x64.zip
```

Zip'i aç, içindeki `Spec2Code.exe` dosyasını çalıştır. Uygulama lokal web
arayüzünü açar. `windows-x64`, Intel ve AMD 64-bit Windows makinelerde çalışır.

Windows'ta geliştirmeye devam etmek için source zip'i indir:

```text
spec2code-vX.Y.Z-source.zip
```

Detaylı Windows setup ve air-gap akışı için:

```text
docs/WINDOWS.md
```

## macOS Geliştirme

```bash
brew install llvm cppcheck

python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

.venv/bin/python run_spec2code.py --port 8077
```

Tarayıcıda:

```text
http://127.0.0.1:8077
```

## Doğrulama

```bash
.venv/bin/python -m orchestrator.selftest
cd frontend && npm run build
```

Beklenen selftest sonucu:

```text
qc.passed: True
```

## Release

Release'ler `v*` tag'leriyle otomatik üretilir.

```bash
git tag -a v0.1.4 -m "Spec2Code v0.1.4"
git push origin main --tags
```

GitHub Actions şu asset'leri üretir:

- `spec2code-vX.Y.Z-source.zip`
- `spec2code-vX.Y.Z-source.tar.gz`
- `spec2code-vX.Y.Z-macos-*.zip`
- `spec2code-vX.Y.Z-windows-x64.zip`

## Repo Haritası

```text
backend/         FastAPI, parser, job manager, validation, download endpointleri
frontend/src/    React UI, schematic, setup, generate console, code viewer
orchestrator/    C model, Jinja templates, codegen, QC loop
descriptors/     Cihaz davranış descriptor'ları
std/             Makinece okunabilir coding-standard ruleset'leri
schemas/         project.spec JSON schema
hostplat/        Windows/macOS/Linux izolasyonu
scripts/         release ve Windows yardımcı scriptleri
docs/            Windows, handoff ve execution plan dokümanları
```
