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
deterministik yapılır. Yani LTC2991, TCA9548A, MT25Q128 gibi desteklenen cihazlar
için hazır descriptor varsa dış kaynak dosyaya ihtiyaç yoktur.

Senin verdiğin `.c/.h` dosyalar **Import** ekranında taranır ve parça ile
eşleştirilirse `catalog/imported.json` içine kaydedilir. Bu sürümde bu dosyalar
deterministik üretimi doğrudan değiştirmez; ilgili part projede kullanıldığında
çıktıya `reference_sources/<part>/` altında referans olarak kopyalanır. Böylece
Vitis paketinde hem Spec2Code üretimi hem de senin verdiğin orijinal kaynaklar
birlikte taşınır. Sonraki adım, bu kaynaklardan descriptor taslağı üretme akışını
daha otomatik hale getirmektir.

## Kodlama Standardı Nasıl Çalışır?

Kodlama standardı `project.spec.json` içindeki `coding_standard_ref` alanıyla
seçilir. Varsayılan:

```json
"coding_standard_ref": "std/default.ruleset.json"
```

Bu ruleset iki aşamada devreye girer:

1. **Codegen aşaması:** header yorumları, public API isimleri ve bazı template
   kararları ruleset referansına göre üretilir.
2. **QC aşaması:** `.clang-format` ruleset'ten türetilir; naming-linter,
   print terminator ve fonksiyon isimlendirme gibi makinece kontrol edilebilir
   kuralları JSON ruleset'ten okur.

Makinece uygulanacak kurallar için JSON gerekir. Word veya Markdown dosyası iyi
bir insan dokümanıdır ama QC'nin otomatik karar vermesi için nihayetinde JSON
ruleset'e çevrilmesi gerekir.

Word standardın varsa:

```bash
.venv/bin/python -m std.extract_ruleset path/to/standard.docx > std/my.ruleset.json
```

Sonra UI'daki **Coding standard** alanına şunu yaz:

```text
std/my.ruleset.json
```

Markdown kullanmak; açıklama, örnek, gerekçe ve insan review'u için iyidir.
Ama “bit field'lar şöyle yazılır”, “fonksiyon isimleri şu regex'e uyar”,
“print içinde satır sonu `\r\n` olmalı” gibi otomatik kontrol edilecek kurallar
JSON ruleset'e girmelidir. En sağlıklı model:

- `docs/coding-standard.md`: İnsan tarafından okunacak açıklama ve örnekler.
- `std/my.ruleset.json`: Spec2Code/QC tarafından uygulanacak makine kuralları.

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
hata mesajıyla görünür. Model cevabı `max_tokens` nedeniyle kesilirse veya cevap `max_response_chars`
limitini aşarsa çıktı kullanılmaz; hata açıkça raporlanır ve deterministic QC
akışı sonucu teslim etmeye devam eder.

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
