# Spec2Code Kodlama Standardı (üretilen C kodu)

Bu doküman, Spec2Code'un **ürettiği gömülü C kodunun** uyduğu kodlama standardını
insan-okur biçimde anlatır.

- **Tek makine-okunur kaynak:** [`std/default.ruleset.json`](../std/default.ruleset.json)
  (şema: [`schemas/ruleset.schema.json`](../schemas/ruleset.schema.json))
- **Denetleyici:** [`orchestrator/qc/naming_linter.py`](../orchestrator/qc/naming_linter.py)
  (libclang AST) + clang-format + clang-tidy + cppcheck
- **Kapı:** QC döngüsü ([`orchestrator/qc/loop.py`](../orchestrator/qc/loop.py))

Bu dosya ile ruleset çelişirse **ruleset kazanır**; burası onun okunabilir anlatımıdır.
Standart değişecekse önce `std/default.ruleset.json` (gerekiyorsa `naming_linter.py`)
güncellenir, sonra bu doküman.

---

## Kapsam — neye uygulanır, neye uygulanmaz

**Uygulanır:** Spec2Code'un ürettiği `.c` / `.h` dosyaları — sürücüler, test bench
ajanı, mesaj katmanı, CIT, trace. Yani `outputs/<proje>/` altına düşen her şey.

**UYGULANMAZ:** Uygulamanın kendi kaynak kodu. `backend/` ve `orchestrator/` altındaki
Python ile `frontend/` altındaki TypeScript bu kurallara **tabi değildir**; onlar kendi
dillerinin olağan üslubunu (PEP 8, TS/React konvansiyonları) izler. Hungarian önekler ve
`unsigned char` zorunluluğu yalnızca üretilen gömülü C içindir.

Üretilen kod tek tek dosyalarda değil, [`orchestrator/codegen.py`](../orchestrator/codegen.py)
ve [`orchestrator/cmodel.py`](../orchestrator/cmodel.py) içinde **string olarak** durur.
Bir ihlali düzeltmek için çıktı `.c` dosyasını elle düzenlemek işe yaramaz — bir sonraki
üretimde silinir. **Üreteci düzelt, sonra yeniden üret.**

---

## Biçimlendirme

| Kural | Değer |
|---|---|
| Süslü parantez | **Allman** — `{` her zaman yeni satırda |
| Girinti | 4 boşluk (tab yok) |
| Satır sonu | **CRLF** (`\r\n`) — hedef Windows/Vitis |
| Maksimum satır | 160 karakter (clang-format `ColumnLimit`; sığan ifadeler tek satırda kalır, gereksiz satır bölme yok) |
| Kontrol anahtar sözcüğü | sonrasında boşluk: `if (`, `for (`, `while (` |

```c
if (spIic == NULL)
{
    return XST_FAILURE;
}
```

Biçimlendirmeyi clang-format uygular; CRLF de bu adımda yazılır.

---

## İsimlendirme

### Fonksiyonlar

camelCase, regex `^[a-z][A-Za-z0-9]*$` — alt çizgi yok, büyük harfle başlamaz.

```c
int ltc2991DeviceInit(XIicPs* spIic);
int tca9548aChannelSelect(XIicPs* spIic, unsigned int uiChannel);
```

### Değişkenler — taban önekler

Değişken adı, tipini bildiren bir önek + camelCase gövdeden oluşur.

| Tip | Önek | Örnek |
|---|---|---|
| `unsigned char` | `uc` | `ucProbe` |
| `char` | `c` | `cDir` |
| `unsigned short` | `us` | `usValue` |
| `short` | `s` | `sDelta` |
| `unsigned int` | `ui` | `uiIndex` |
| `int` | `i` | `iStatus` |
| `unsigned long` | `ul` | `ulTicks` |
| `unsigned long long` | `ull` | `ullMask` |

### Önek bileşimi

Önekler şu sırayla birleşir: **`<storage>` + `<taban>` + `<pointer>` + `<dizi>`**

| Ek | Ne zaman | Örnek |
|---|---|---|
| `p` | pointer (skaler tabana eklenir) | `char*` → `cpVersion`, `unsigned int*` → `uipTuketilen` |
| `sp` | struct pointer (taban yerine geçer) | `XIicPs* spIic`, `SMesajParser* spParser` |
| `s` | struct değer | `SBoardCit sCit` |
| `Arr` | dizi | `unsigned char ucArrWide[2]` |
| `S_` | `static` değişken (en başa) | `static SBoardCit S_sCitSonKopya` |
| `G_` | global değişken (en başa) | `G_uiSayac` |

Birleşik örnekler — üretilen koddan:

```c
unsigned int uiIndex;                                  /* ui                */
int iStatus;                                           /* i                 */
XIicPs* spIic;                                         /* sp  (struct*)     */
const char* cpVersion;                                 /* c + p             */
unsigned int* uipTuketilen;                            /* ui + p            */
unsigned char ucArrWide[2];                            /* uc + Arr          */
static const char S_cArrDigits[] = "0123456789ABCDEF"; /* S_ + c + Arr      */
static const char* const S_cpArrCitCihaz[2];           /* S_ + c + p + Arr  */
static SBoardCit S_sCitSonKopya;                       /* S_ + s            */
```

"Struct sayılan" tipler: adı `S` ile başlayanlar (`SBoardCit`), `X` ile başlayanlar
(Xilinx sürücü tipleri: `XIicPs`, `XSpiPs`) ve `struct ...` yazımı. `void*`
isimleri kural dışıdır (denetlenmez).

### Tip tanımları (typedef)

| Tür | Önek | Örnek |
|---|---|---|
| `struct` | `S` | `typedef struct { ... } SBoardCit;` |
| `union` | `S` | `typedef union { ... } SCerceve;` |
| `enum` | `E` | `typedef enum { ... } EDurum;` |

---

## Yasak tipler

`stdint.h` sabit-genişlik tipleri üretilen kodda **kullanılmaz**; düz C tipleri kullanılır.

```c
uint8_t  ucValue;        /* ❌ hata */
unsigned char ucValue;   /* ✅      */
```

Yasak liste: `uint8_t`, `int8_t`, `uint16_t`, `int16_t`, `uint32_t`, `int32_t`,
`uint64_t`, `int64_t`.

Xilinx BSP'nin kendi tipleri (`u8`, `u32`, `UINTPTR`) BSP başlıklarından gelir ve
bu yasağın dışındadır; ama üretilen kod kendi değişkenlerinde primitive tipleri tercih eder.

---

## Pointer yıldızı

Yıldız **tipe yapışır**, isme değil:

```c
XIicPs* spIic;    /* ✅ */
XIicPs *spIic;    /* ❌ hata: "pointer '*' must attach to the type" */
```

---

## printf satır sonu

Tüm `printf`/`xil_printf` çağrılarında satır sonu `\r\n` olmalıdır; çıplak `\n` hatadır.

```c
xil_printf("S2C-CORESIGHT-AGENT-READY\r\n");   /* ✅ */
xil_printf("hazir\n");                          /* ❌ hata */
```

---

## Doxygen

Public fonksiyonlarda Doxygen bloğu zorunludur.

```c
/**
 * @brief LTC2991 cihazini ilklendirir.
 * @param spIic Initialized I2C controller handle.
 * @return XST_SUCCESS on success, else an XST_* error code.
 */
int ltc2991DeviceInit(XIicPs* spIic);
```

---

## Denetim nasıl işler

QC döngüsü ([`orchestrator/qc/loop.py`](../orchestrator/qc/loop.py)) üretilen her
`.c` dosyası için sırayla:

1. **format** — clang-format (CRLF bu adımda yazılır).
2. **checks** — naming_linter (libclang AST) + clang-tidy + cppcheck.
3. **gate** — yalnızca `severity == "error"` olan ihlaller kapıyı düşürür;
   `warning` teslimi engellemez.
4. **fix round** — LLM fixer verilmişse error'lar modele geri beslenir ve tekrar denenir.

Rapor: `outputs/<proje>/qc_report.json` (`passed`, `final_violations`, `tool_status`).

**Error seviyesindeki (build düşüren) ihlaller:** fonksiyon adı deseni, Hungarian/storage
önekleri, camelCase, yasak tip kullanımı, pointer yıldızı yerleşimi, printf satır sonu.

### ★ Araç eşitliği tuzağı

QC, **kurulu olmayan aracı sessizce atlar**. Yani clang-tidy / cppcheck / libclang
kurulu olmayan bir makinede QC "GEÇTİ" der; aynı kod, araçların kurulu olduğu bir
makinede (CI) **FAIL** eder.

Bu sahada gerçekten yaşandı (v0.1.147): Windows'ta görünmeyen 18 ihlal, araçlı makinede
build'i kırdı. libclang bulunamazsa naming-linter yalnızca `warning` seviyesinde
`naming.libclang_missing` üretir ve **AST denetimlerinin tamamını atlar** — yani isim
kuralları hiç denetlenmemiş olur.

Bir codegen değişikliğini "QC geçti" diye kapatmadan önce dört aracın da bulunduğunu
doğrula:

```bash
clang-format --version && clang-tidy --version && cppcheck --version
```

veya uygulama çalışırken `/api/health` çıktısındaki `tools` alanının dördünü de dolu
gösterdiğini kontrol et. (libclang için `libclang` pip paketi yeterlidir; v0.1.149'dan
beri paketin kendi native kütüphanesi de otomatik bulunur.)

### Yerel doğrulama

```bash
python spec2code_cli.py build --spec specs/samples/radar_io_board.spec.json
```

Son satır `QC GEÇTİ` olmalı. Ayrıntı için `outputs/radar_io_board/qc_report.json`.
