"""TI AFE7900 (AFE79xx C API v2.9) surucu uretimi + JESD204C IP baglanti (link) modulu.

Tasarim (2026-09-14, kullanici karari):
- TI'in C API'si (``backend/data/vendor/afe79xx``: Afe79xx/Include + Afe79xx/Src, TI Text File License)
  uretim ciktisinda ``drivers/vendor/afe79xx/`` altina aynen kopyalanir; QC (naming/clang-tidy/cppcheck)
  bu klasoru DENETLEMEZ (ucuncu parti kod, kendi standardi). Kullanici alani dosyasi
  ``tiAfe79_baseFunc.c`` (HAL) Spec2Code tarafindan uretilir ve kucuk bir kopru API'sine
  (``<mod>_hal.h``, camelCase) baglanir: SPI ham yaz/oku, ms bekleme, log, config sozcugu, SYSREF kancasi.
- Config: Latte'nin urettigi hex (satir basina bir ``unsigned int``, 8-9k satir) ``device.config.afe_config_words``
  olarak spec'e girer, ``<mod>_config.c`` icinde ``const unsigned int`` dizisine gomulur; TI API'nin
  ``afeDeviceBringupFromMem`` fonksiyonu bu diziyi ``hostMemRead`` kancasiyla sozcuk sozcuk ceker
  (sonda 0xFFFFFFFF = bitti).
- Surucu API'si Spec2Code kalibinda: ``<mod>DeviceInit(XSpi*)``, ``<mod>TemperatureRead(XSpi*, int*)`` ...
  Ajan/CIT/shell bu fonksiyonlari descriptor op adlarindan turetir (``afe7900.yaml`` operations).
- JESD204C IP (register_map=jesd204c) spec'te varsa ``drivers/ip/jesdlink.c/.h`` uretilir: cekirdek reset
  (1 = reset ver; 0 = kaldir ve reset/GT mesgul bitlerinin dusmesini timeout ile bekle, PG242) ve
  timeout'lu durum kontrolleri. Kodlama XSA'dan (``C_ENCODING``): 64B/66B'de SH lock + MB lock,
  8B/10B'de CGS + SYNC; iki akis ayni dosyada uretilmez (tek akis, #ifdef yok).
- Bring-up sirasi (kullanici kurali): FPGA cekirdek resetleri VERILIR -> AFE init (bringup from mem)
  -> FPGA resetleri KALDIRILIR (timeout'lu) -> AFE JESD blok resetleri + adcDacSync (SYSREF ile relink)
  -> FPGA RX link durumu (timeout) -> AFE DAC-JESD-RX link durumu -> alarm/sayac temizleme.

Adlandirma: "sdtm" on eki HICBIR yerde kullanilmaz.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Callable, Optional

from orchestrator import cmodel
from orchestrator.cmodel import CFunc, CUnit, Emit, _func_name, _handle_for, _is_axi_spi

_ROOT = Path(__file__).resolve().parents[1]
VENDOR_KEY = "afe79xx"
VENDOR_SRC_DIR = _ROOT / "backend" / "data" / "vendor" / "afe79xx"
VENDOR_OUT_REL = Path("drivers") / "vendor" / "afe79xx"
CONFIG_KEY = "afe_config_words"

# AFE79xx SPI cercevesi: 24 bit = R/W (bit23, 1 = okuma) + 15 bit adres + 8 bit veri (TI AFE79xx SPI
# protokolu; LMK04832 ile ayni kalip). SAHADA DOGRULANACAK (kullanici: sirkette gercek AFE7900 ile).
SPI_READ_BIT = 0x80

# JESD204C register offsetleri (PG242 v4.x; backend/ip_register_maps.jesd204c_document ile birebir).
JESD_REG_RESET = 0x020
JESD_REG_CTRL_SYSREF = 0x050
JESD_REG_STAT_RX_ERR_8B10B = 0x058
JESD_REG_STAT_STATUS = 0x060
JESD_REG_STAT_IRQ = 0x068
JESD_LANE_BLOCK = 0x080
JESD_LANE_BASE = 0x400
JESD_LANE_ERROR_CNT0 = 0x010


def is_afe79_descriptor(descriptor: dict) -> bool:
    return str((descriptor or {}).get("vendor_api", "")).lower() == VENDOR_KEY


def afe79_devices(spec: dict, get_descriptor: Callable[[str], dict]) -> list[dict]:
    out = []
    for device in spec.get("devices", []) or []:
        try:
            descriptor = get_descriptor(device.get("descriptor_ref") or device.get("part", ""))
        except Exception:  # noqa: BLE001 - tanimsiz parca baska katmanda raporlanir
            continue
        if is_afe79_descriptor(descriptor):
            out.append(device)
    return out


def parse_config_words(raw) -> list[int]:
    """Latte hex metni/listesi -> 32-bit sozcukler. Her ``0x........`` bir sozcuktur (bayt gruplama YOK)."""
    if raw is None:
        return []
    if isinstance(raw, list):
        words: list[int] = []
        for item in raw:
            if isinstance(item, int):
                words.append(item & 0xFFFFFFFF)
            elif isinstance(item, str):
                words.extend(parse_config_words(item))
        return words
    text = str(raw)
    tokens = re.findall(r"0[xX][0-9A-Fa-f]{1,8}", text)
    if tokens:
        return [int(t, 16) for t in tokens]
    return [int(t, 10) & 0xFFFFFFFF for t in re.findall(r"(?<![A-Za-z0-9_])\d+(?![A-Za-z0-9_])", text)]


def filtered_descriptor_loader(spec: dict, get_descriptor: Callable[[str], dict]) -> Callable[[str], dict]:
    """`requires_ip: <register_map>` isaretli op'lari spec'te o IP yoksa descriptor'dan dusurur.

    Boylece manifest, ajan dispatch'i, cmodel ve CIT ayni op listesini gorur (JESD204C IP'si olmayan
    bir projede AFE'nin jesd_link_bringup op'u hic uretilmez).
    """
    present = {str(ip.get("register_map", "")) for ip in spec.get("custom_ips", []) or []}
    cache: dict[int, dict] = {}

    def get(ref_or_part: str) -> dict:
        descriptor = get_descriptor(ref_or_part)
        if not is_afe79_descriptor(descriptor):
            return descriptor
        key = id(descriptor)
        if key not in cache:
            ops = [op for op in descriptor.get("operations", [])
                   if not op.get("requires_ip") or str(op.get("requires_ip")) in present]
            cache[key] = {**descriptor, "operations": ops}
        return cache[key]

    return get


def config_words(device: dict) -> list[int]:
    config = device.get("config") or {}
    if not isinstance(config, dict):
        return []
    return parse_config_words(config.get(CONFIG_KEY))


def jesd_ips(spec: dict) -> dict[str, dict]:
    """Spec'teki JESD204C IP'leri yonlerine gore: {"rx": {...}, "tx": {...}} (yoksa bos)."""
    out: dict[str, dict] = {}
    for ip in spec.get("custom_ips", []) or []:
        if str(ip.get("register_map", "")) != "jesd204c":
            continue
        params = ip.get("ip_parameters") or {}
        direction = str(params.get("direction", "rx")).lower()
        try:
            base = int(str(ip.get("base_address")), 0)
        except (TypeError, ValueError):
            continue
        out.setdefault(direction, {
            "id": ip.get("id", ""), "base": base,
            "link_layer": str(params.get("link_layer", "64b66b")).lower(),
            "lanes": int(params.get("lanes", 4) or 4),
            "subclass": int(params.get("subclass", 1) or 1),
        })
    return out


# --- surucu birimi (drivers/<mod>.c/.h) --------------------------------------------------------------

def device_unit(device: dict, controller: dict, descriptor: dict, module: Optional[str],
                sdt: bool, has_jesd: bool) -> CUnit:
    module = module or cmodel._module_of(device["part"])
    htype, hvar = _handle_for(controller)
    if htype not in {"XSpi", "XSpiPs"}:
        raise cmodel.CodegenError(
            f"device {device.get('id')}: AFE7900 SPI'si XSpi (AXI Quad SPI) ya da XSpiPs ister; "
            f"denetleyici surucusu {htype} desteklenmiyor")
    MOD = module.upper()
    pas = cmodel._pascal_suffix(module)
    attach = device.get("attach") or {}
    config = device.get("config") or {}
    log_level = int(config.get("log_level", 0) or 0)
    tdd_override = bool(config.get("tdd_override", True))
    instance = controller["instance"]
    sel_def = f"{MOD}_SPI_SELECT"
    hal_type = f"S{pas}Hal"

    defines = [
        (sel_def, f"{int(attach.get('spi_chip_select', 0))}U", "SPI slave select"),
        (f"{MOD}_LOG_LEVEL", f"{log_level}U", "TI AFE log seviyesi (0 ERROR .. 4 DEBUG)"),
        (f"{MOD}_TDD_OVERRIDE", "TRUE" if tdd_override else "FALSE",
         "bring-up sonrasi overrideTdd(rx=15, fb=0, tx=15, enable=1)"),
        (f"{MOD}_SPI_READ_BIT", f"0x{SPI_READ_BIT:02X}U", "SPI cerceve bayt0 bit7: 1 = okuma"),
        (f"{MOD}_JESD_RX_LINKS_UP", "0x000AU", "AFE DAC-JESD-RX: AB ve CD link'leri up (2 bit/link = 2)"),
        (f"{MOD}_PLL_LOCK_GOOD", "3U", "checkPllLockStatus: LOCK=1, LOCK_LOST=0"),
    ]
    public_types = [
        "typedef struct\n"
        "{\n"
        f"    {htype}* {hvar};\n"
        "    unsigned char ucSelect;\n"
        f"}} {hal_type}; /* TI API halConfig -> Spec2Code SPI baglami */",
    ]
    private_decls = [
        f"static {hal_type} S_s{pas}Hal = {{NULL, {sel_def}}};",
        f"static afe79InstDeviceInfo S_s{pas}Device;",
        f"static unsigned int S_ui{pas}Bound = FALSE;",
    ]
    funcs: list[CFunc] = []
    public: list[str] = []

    # --- HAL koprusu (vendor tiAfe79_baseFunc.c bunlari cagirir) ---
    e = Emit()
    e.ln(f"{hal_type}* spHal = ({hal_type}*)pvHal;")
    e.ln("unsigned char ucArrTx[3];")
    e.ln("int iStatus;")
    e.blank()
    e.open(f"if ((spHal == NULL) || (spHal->{hvar} == NULL))").ln("return XST_FAILURE;").close()
    e.ln(f"ucArrTx[0] = (unsigned char)((usAddress >> 8U) & 0x7FU);")
    e.ln("ucArrTx[1] = (unsigned char)(usAddress & 0xFFU);")
    e.ln("ucArrTx[2] = ucData;")
    _spi_select_hal(e, htype, hvar, "spHal", sel_def)
    cmodel._spi_transfer(e, htype, f"spHal->{hvar}", "ucArrTx", "NULL", "3U")
    e.ln("dbgTraceSpi((unsigned int)spHal->ucSelect, ucArrTx, NULL, 3U);")
    e.ln("return XST_SUCCESS;")
    funcs.append(CFunc(_func_name(module, "hal_spi_write"), "int",
                       ["void* pvHal", "unsigned short usAddress", "unsigned char ucData"], e.out(),
                       brief="TI HAL: 24-bit SPI yazma (R/W=0, 15-bit adres, 8-bit veri)."))
    public.append(_func_name(module, "hal_spi_write"))

    e = Emit()
    e.ln(f"{hal_type}* spHal = ({hal_type}*)pvHal;")
    e.ln("unsigned char ucArrTx[3];")
    e.ln("unsigned char ucArrRx[3];")
    e.ln("int iStatus;")
    e.blank()
    e.open(f"if ((spHal == NULL) || (spHal->{hvar} == NULL) || (ucpData == NULL))").ln("return XST_FAILURE;").close()
    e.ln(f"ucArrTx[0] = (unsigned char)({MOD}_SPI_READ_BIT | ((usAddress >> 8U) & 0x7FU));")
    e.ln("ucArrTx[1] = (unsigned char)(usAddress & 0xFFU);")
    e.ln("ucArrTx[2] = 0x00U;")
    e.ln("ucArrRx[0] = 0x00U;")
    e.ln("ucArrRx[1] = 0x00U;")
    e.ln("ucArrRx[2] = 0x00U;")
    _spi_select_hal(e, htype, hvar, "spHal", sel_def)
    cmodel._spi_transfer(e, htype, f"spHal->{hvar}", "ucArrTx", "ucArrRx", "3U")
    e.ln("dbgTraceSpi((unsigned int)spHal->ucSelect, ucArrTx, ucArrRx, 3U);")
    e.ln("*ucpData = ucArrRx[2];")
    e.ln("return XST_SUCCESS;")
    funcs.append(CFunc(_func_name(module, "hal_spi_read"), "int",
                       ["void* pvHal", "unsigned short usAddress", "unsigned char* ucpData"], e.out(),
                       brief="TI HAL: 24-bit SPI okuma (R/W=1); veri 3. baytta doner."))
    public.append(_func_name(module, "hal_spi_read"))

    e = Emit()
    e.ln("usleep((unsigned long)uiMs * 1000UL);")
    funcs.append(CFunc(_func_name(module, "hal_delay_ms"), "void", ["unsigned int uiMs"], e.out(),
                       brief="TI HAL: milisaniye bekleme (sleep.h usleep)."))
    public.append(_func_name(module, "hal_delay_ms"))

    e = Emit()
    e.ln("unsigned int uiDbgLevel;")
    e.blank()
    e.open("if (uiLevel > uiCurrentLevel)").ln("return;").close()
    e.ln("/* TI: 0 ERROR, 1 WARNING, 2 INFO, 3 SPILOG, 4 DEBUG -> dbg_printf seviyeleri. */")
    e.open("if (uiLevel == 0U)").ln("uiDbgLevel = DEBUG_LEVEL_ERROR;").close()
    e.open("else if (uiLevel == 1U)").ln("uiDbgLevel = DEBUG_LEVEL_WARNING;").close()
    e.open("else if (uiLevel == 2U)").ln("uiDbgLevel = DEBUG_LEVEL_INFO;").close()
    e.open("else").ln("uiDbgLevel = DEBUG_LEVEL_TRACE;").close()
    e.ln("dbg_printf(uiDbgLevel, \"AFE: %s\", cpText);")
    funcs.append(CFunc(_func_name(module, "hal_log"), "void",
                       ["unsigned int uiLevel", "unsigned int uiCurrentLevel", "const char* cpText"], e.out(),
                       brief="TI HAL: log satiri (seviye filtresi TI kurali: level <= current)."))
    public.append(_func_name(module, "hal_log"))

    e = Emit()
    e.open(f"if ((uipWord == NULL) || (uiIndex >= {MOD}_CONFIG_WORD_COUNT))").ln("return FALSE;").close()
    e.ln(f"*uipWord = G_uiArr{pas}ConfigWords[uiIndex];")
    e.ln("return TRUE;")
    funcs.append(CFunc(_func_name(module, "hal_config_word"), "unsigned int",
                       ["unsigned int uiIndex", "unsigned int* uipWord"], e.out(),
                       brief="TI HAL hostMemRead: Latte config sozcugu (dizi sonu -> FALSE)."))
    public.append(_func_name(module, "hal_config_word"))

    e = Emit()
    e.ln("(void)pvHal;")
    e.ln("/* Tek atimlik pin SYSREF kancasi: saat agaci (LMK) ya da PL GPIO surer; surekli SYSREF")
    e.ln(" * modunda TI islem beklemez. Karta ozel surus gerekiyorsa bu fonksiyon override edilir. */")
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"AFE: SYSREF darbe kancasi (bos)\");")
    funcs.append(CFunc(_func_name(module, "hal_sysref_pulse"), "void", ["void* pvHal"], e.out(),
                       brief="TI HAL giveSingleSysrefPulse kancasi (varsayilan: yalniz log)."))
    public.append(_func_name(module, "hal_sysref_pulse"))

    # --- baglam (static) ---
    e = Emit()
    e.ln("unsigned int uiIndex;")
    e.blank()
    e.ln(f"S_s{pas}Hal.{hvar} = {hvar};")
    e.ln(f"S_s{pas}Hal.ucSelect = (unsigned char){sel_def};")
    e.ln(f"S_s{pas}Device.afeId = 0U;")
    e.open("for (uiIndex = 0U; uiIndex < 4U; uiIndex++)")
    e.ln(f"S_s{pas}Device.rxChannelRemap[uiIndex] = (unsigned char)uiIndex;")
    e.ln(f"S_s{pas}Device.txChannelRemap[uiIndex] = (unsigned char)uiIndex;")
    e.close()
    e.ln(f"S_s{pas}Device.fbChannelRemap[0] = 0U;")
    e.ln(f"S_s{pas}Device.fbChannelRemap[1] = 1U;")
    e.ln(f"S_s{pas}Device.logLevel = {MOD}_LOG_LEVEL;")
    e.ln(f"S_s{pas}Device.halConfig = (void*)&S_s{pas}Hal;")
    e.ln(f"S_ui{pas}Bound = TRUE;")
    funcs.append(CFunc(_func_name(module, "bind"), "void", [f"{htype}* {hvar}"], e.out(), static=True))

    e = Emit()
    e.open(f"if ((S_ui{pas}Bound == FALSE) || (S_s{pas}Hal.{hvar} != {hvar}))")
    e.ln(f"{_func_name(module, 'bind')}({hvar});")
    e.close()
    e.ln(f"return &S_s{pas}Device;")
    funcs.append(CFunc(_func_name(module, "device"), "afe79InstDeviceInfo*", [f"{htype}* {hvar}"], e.out(),
                       static=True))

    e = Emit()
    e.ln("return (ucTiStatus == (unsigned char)TI_AFE_RET_EXEC_PASS) ? XST_SUCCESS : XST_FAILURE;")
    funcs.append(CFunc(_func_name(module, "status"), "int", ["unsigned char ucTiStatus"], e.out(), static=True))

    # --- device_init: SPI + bring-up from mem ---
    e = Emit()
    e.ln("int iStatus;")
    e.ln(f"{htype}_Config* spConfig;")
    e.ln("afe79InstDeviceInfo* spDevice;")
    e.blank()
    e.open(f"if ({hvar} == NULL)").ln("return XST_FAILURE;").close()
    cmodel._spi_emit_init(e, htype, hvar, instance, sdt)
    e.ln(f"{_func_name(module, 'bind')}({hvar});")
    e.ln(f"spDevice = &S_s{pas}Device;")
    e.open(f"if ({MOD}_CONFIG_WORD_COUNT == 0U)")
    e.ln("dbg_printf(DEBUG_LEVEL_ERROR, \"AFE: config sozcugu yok (Latte hex ice aktarilmamis)\");")
    e.ln("return XST_FAILURE;")
    e.close()
    e.ln(f"dbg_printf(DEBUG_LEVEL_INFO, \"AFE: bring-up basliyor (%u sozcuk)\", (unsigned int){MOD}_CONFIG_WORD_COUNT);")
    e.ln(f"iStatus = {_func_name(module, 'status')}(AFE79FNP(afeDeviceBringupFromMem)(spDevice, 0U, 0U));").check_status()
    e.open(f"if ({MOD}_TDD_OVERRIDE == TRUE)")
    e.ln(f"iStatus = {_func_name(module, 'status')}(AFE79FNP(overrideTdd)(spDevice, 15U, 0U, 15U, 1U));").check_status()
    e.close()
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"AFE: bring-up tamam\");")
    e.ln("return XST_SUCCESS;")
    funcs.append(CFunc(_func_name(module, "device_init"), "int", [f"{htype}* {hvar}"], e.out(),
                       brief="SPI denetleyicisini kurar, TI API baglamini baglar ve Latte config'iyle AFE bring-up yapar.",
                       doxy_params=[(hvar, "SPI denetleyici ornegi (AFE bu CS'te)")],
                       doxy_return="XST_SUCCESS / XST_FAILURE (TI API hatasi dbg_printf'e yazilir)"))
    public.append(_func_name(module, "device_init"))

    def _wrap(op: str, params: list[str], body: list[str], brief: str, ret: str = "int") -> None:
        funcs.append(CFunc(_func_name(module, op), ret, [f"{htype}* {hvar}", *params], body, brief=brief))
        public.append(_func_name(module, op))

    dev = f"{_func_name(module, 'device')}({hvar})"
    st = _func_name(module, "status")

    e = Emit()
    e.ln("short sTemperature = 0;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (ipTemperature == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(getDeviceTemp)({dev}, &sTemperature));").check_status()
    e.ln("*ipTemperature = (int)sTemperature;")
    e.ln("return XST_SUCCESS;")
    _wrap("temperature_read", ["int* ipTemperature"], e.out(), "Cihaz sicakligi (derece C, tam sayi).")

    e = Emit()
    e.ln("unsigned char ucLock = 0U;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (ucpPllLock == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(checkPllLockStatus)({dev}, &ucLock));").check_status()
    e.ln("*ucpPllLock = (unsigned char)ucLock;")
    e.ln("return XST_SUCCESS;")
    _wrap("pll_lock_read", ["unsigned char* ucpPllLock"], e.out(),
          "PLL kilit durumu: 3 = kilitli ve kilit kaybi yok (bit0 LOCK, bit1 = LOCK_LOST degil).")

    e = Emit()
    e.ln("unsigned short usOk = 0U;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (uspHealth == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(checkDeviceHealth)({dev}, &usOk));").check_status()
    e.ln("*uspHealth = (unsigned short)usOk;")
    e.ln("return XST_SUCCESS;")
    _wrap("health_read", ["unsigned short* uspHealth"], e.out(),
          "Cihaz sagligi: 0 = tamam; bit0 PLL, bit1 DAC JESD, bit2 ADC JESD, bit3 SPI, bit4 MCU, bit5 PAP.")

    e = Emit()
    e.ln("unsigned short usLink = 0U;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (uspLinkStatus == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(getJesdRxLinkStatus)({dev}, &usLink));").check_status()
    e.ln("*uspLinkStatus = (unsigned short)usLink;")
    e.ln("return XST_SUCCESS;")
    _wrap("jesd_rx_link_status_read", ["unsigned short* uspLinkStatus"], e.out(),
          "AFE DAC-JESD-RX link durumu (FPGA TX -> AFE): 2 bit/link, 2 = up; 0xA = AB ve CD up.")

    e = Emit()
    e.ln("unsigned char ucAlarms = 0U;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (ucpAlarms == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(getJesdRxAlarms)({dev}, &ucAlarms));").check_status()
    e.ln("*ucpAlarms = (unsigned char)ucAlarms;")
    e.ln("return XST_SUCCESS;")
    _wrap("jesd_rx_alarms_read", ["unsigned char* ucpAlarms"], e.out(), "AFE DAC-JESD-RX alarm bitleri (0 = temiz).")

    e = Emit()
    e.ln(f"return {st}(AFE79FNP(clearJesdRxAlarms)({dev}));")
    _wrap("jesd_rx_alarms_clear", [], e.out(), "AFE DAC-JESD-RX alarmlarini temizler.")

    e = Emit()
    e.ln(f"return {st}(AFE79FNP(sendSysref)({dev}, 0U, 1U));")
    _wrap("sysref_send", [], e.out(), "AFE'ye yeni pin SYSREF kabulu (spiSysref=0, PLL SPI erisimi alinir).")

    e = Emit()
    e.ln(f"return {st}(AFE79FNP(adcDacSync)({dev}, 1U));")
    _wrap("adc_dac_sync", [], e.out(),
          "Tum AFE JESD bloklarini resetler, pin SYSREF ile yeniden senkronlar ve DAC-JESD-RX linkini dogrular.")

    e = Emit()
    e.ln("int iStatus;")
    e.blank()
    e.ln(f"iStatus = {st}(AFE79FNP(jesdRxFullResetToggle)({dev}, 3U));").check_status()
    e.ln(f"return {st}(AFE79FNP(jesdTxFullResetToggle)({dev}, 3U));")
    _wrap("jesd_reset_toggle", [], e.out(), "AFE DAC-JESD (RX) ve ADC-JESD (TX) bloklarina tam reset darbesi (AB+CD).")

    e = Emit()
    e.ln("unsigned char ucLanes = 0U;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (ucpAllLanes == NULL)").ln("return XST_FAILURE;").close()
    e.ln(f"iStatus = {st}(AFE79FNP(pollSerdesLinkStatusAllLanes)({dev}, &ucLanes));").check_status()
    e.ln("*ucpAllLanes = (unsigned char)ucLanes;")
    e.ln("return XST_SUCCESS;")
    _wrap("serdes_link_status_read", ["unsigned char* ucpAllLanes"], e.out(), "SerDes RX lane kilit durumu (tum lane'ler).")

    if has_jesd:
        e = Emit()
        e.ln("unsigned short usStatus = 0U;")
        e.ln("unsigned short usAfeLink = 0U;")
        e.ln("unsigned char ucAlarms = 0U;")
        e.ln("unsigned char ucPll = 0U;")
        e.ln("int iStatus;")
        e.blank()
        e.open("if (uspStatus == NULL)").ln("return XST_FAILURE;").close()
        e.ln("*uspStatus = 0U;")
        e.ln("/* 1) FPGA cekirdek resetleri VERILIR (AFE init boyunca link hurda veri kovalamaz). */")
        e.ln("iStatus = jesdLinkCoreReset(JESDLINK_TX_BASE, 1U);").check_status()
        e.ln("iStatus = jesdLinkCoreReset(JESDLINK_RX_BASE, 1U);").check_status()
        e.ln("/* 2) AFE bring-up (Latte config: PLL, JESD, SerDes). */")
        e.ln(f"iStatus = {_func_name(module, 'device_init')}({hvar});").check_status()
        e.ln("/* 3) FPGA resetleri KALDIRILIR: reset/GT mesgul bitleri timeout icinde dusmeli (PG242). */")
        e.ln("iStatus = jesdLinkCoreReset(JESDLINK_TX_BASE, 0U);").check_status()
        e.ln("iStatus = jesdLinkCoreReset(JESDLINK_RX_BASE, 0U);").check_status()
        e.ln("/* 4) AFE JESD bloklari reset + SYSREF ile yeniden senkron (AFE, FPGA TX'ten gelen linki dogrular). */")
        e.ln(f"iStatus = {_func_name(module, 'jesd_reset_toggle')}({hvar});").check_status()
        e.ln(f"iStatus = {_func_name(module, 'adc_dac_sync')}({hvar});")
        e.open("if (iStatus != XST_SUCCESS)")
        e.ln("dbg_printf(DEBUG_LEVEL_ERROR, \"AFE: adcDacSync basarisiz (DAC-JESD-RX link kurulamadi)\");")
        e.close()
        e.ln("/* 5) FPGA RX'e GT'siz link reset: vericiler (AFE ADC-JESD-TX) calisirken alici yeniden senkron arar")
        e.ln(" *    (8B/10B: SYNC~ dusurulur -> CGS -> ILAS; 64B/66B: SH/EMB kilidi). GT resetlenmez. */")
        e.ln("iStatus = jesdLinkLinkReset(JESDLINK_RX_BASE);").check_status()
        e.ln("/* 6) FPGA RX link (AFE ADC -> FPGA): timeout'lu durum kontrolu. */")
        e.open("if (jesdLinkRxLinkWait(JESDLINK_LINK_TIMEOUT_MS) == XST_SUCCESS)").ln("usStatus |= 0x0001U;").close()
        e.open("if (jesdLinkTxCheck() == XST_SUCCESS)").ln("usStatus |= 0x0002U;").close()
        e.ln("/* 7) AFE tarafi: DAC-JESD-RX link (FPGA TX -> AFE), alarmlar, PLL. */")
        e.open(f"if (({_func_name(module, 'jesd_rx_link_status_read')}({hvar}, &usAfeLink) == XST_SUCCESS) && (usAfeLink == {MOD}_JESD_RX_LINKS_UP))")
        e.ln("usStatus |= 0x0004U;")
        e.close()
        e.open(f"if (({_func_name(module, 'jesd_rx_alarms_read')}({hvar}, &ucAlarms) == XST_SUCCESS) && (ucAlarms == 0U))")
        e.ln("usStatus |= 0x0008U;")
        e.close()
        e.open(f"if (({_func_name(module, 'pll_lock_read')}({hvar}, &ucPll) == XST_SUCCESS) && (ucPll == {MOD}_PLL_LOCK_GOOD))")
        e.ln("usStatus |= 0x0010U;")
        e.close()
        e.open("if ((usStatus & 0x001FU) == 0x001FU)").ln("usStatus |= 0x0080U;").close()
        e.ln("jesdLinkErrorCountersClear();")
        e.ln("*uspStatus = usStatus;")
        e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"JESD link bring-up durumu: 0x%04X (bit7 = hepsi tamam)\", (unsigned int)usStatus);")
        e.ln("return ((usStatus & 0x0080U) != 0U) ? XST_SUCCESS : XST_FAILURE;")
        _wrap("jesd_link_bringup", ["unsigned short* uspStatus"], e.out(),
              "FPGA JESD204C cekirdekleri + AFE7900 icin tam link bring-up dizisi; durum bitleri: "
              "0 FPGA RX up, 1 FPGA TX ok, 2 AFE DAC-JESD-RX up, 3 AFE alarm yok, 4 AFE PLL kilitli, 7 hepsi tamam.")

        e = Emit()
        e.ln("unsigned short usStatus = 0U;")
        e.ln("unsigned short usAfeLink = 0U;")
        e.ln("unsigned char ucAlarms = 0U;")
        e.ln("unsigned char ucPll = 0U;")
        e.blank()
        e.open("if (uspStatus == NULL)").ln("return XST_FAILURE;").close()
        e.open("if (jesdLinkRxLinkCheck() == XST_SUCCESS)").ln("usStatus |= 0x0001U;").close()
        e.open("if (jesdLinkTxCheck() == XST_SUCCESS)").ln("usStatus |= 0x0002U;").close()
        e.open(f"if (({_func_name(module, 'jesd_rx_link_status_read')}({hvar}, &usAfeLink) == XST_SUCCESS) && (usAfeLink == {MOD}_JESD_RX_LINKS_UP))")
        e.ln("usStatus |= 0x0004U;")
        e.close()
        e.open(f"if (({_func_name(module, 'jesd_rx_alarms_read')}({hvar}, &ucAlarms) == XST_SUCCESS) && (ucAlarms == 0U))")
        e.ln("usStatus |= 0x0008U;")
        e.close()
        e.open(f"if (({_func_name(module, 'pll_lock_read')}({hvar}, &ucPll) == XST_SUCCESS) && (ucPll == {MOD}_PLL_LOCK_GOOD))")
        e.ln("usStatus |= 0x0010U;")
        e.close()
        e.open("if ((usStatus & 0x001FU) == 0x001FU)").ln("usStatus |= 0x0080U;").close()
        e.ln("*uspStatus = usStatus;")
        e.ln("return XST_SUCCESS;")
        _wrap("jesd_link_status_read", ["unsigned short* uspStatus"], e.out(),
              "Anlik JESD link durumu (bring-up ile ayni bit yerlesimi; bekleme yapmaz).")

    driver_includes = [f"{module}.h", "dbg_printf.h", "xparameters.h", "xstatus.h", "sleep.h",
                       "tiAfe79_afeCommonMacros.h",
                       # tiAfe79_allInclude.h KULLANILMAZ: wrapper basliklari fonksiyon tablosu TANIMLAR
                       # (yalniz tiAfe79_init.c tek TU'da dahil eder; ikinci dahil -> multiple definition).
                       "tiAfe79_genLibFunc.h", "tiAfe79_init.h", "tiAfe79_controls.h", "tiAfe79_jesd.h",
                       "tiAfe79_serDes.h", f"{module}_config.h"]
    if has_jesd:
        driver_includes.append("jesdlink.h")
    return CUnit(
        module=module, part=device["part"],
        summary=str(descriptor.get("summary", "TI AFE7900 RF on uc (AFE79xx C API v2.9 uzerinden)")),
        transport="spi",
        header_includes=["xil_types.h", cmodel._spi_header_for(htype), "tiAfe79_afeGlobalConstants.h"],
        driver_includes=driver_includes, defines=defines, funcs=funcs, public_names=public,
        private_decls=private_decls, public_types=public_types)


def self_test_unit(unit: CUnit, controller: dict, runtime: str) -> cmodel.CTest:
    """tests/<mod>_test.c: DeviceInit + butun *Read fonksiyonlari (cikis parametresi tipine gore degisken)."""
    htype, hvar = _handle_for(controller)
    module = unit.module
    funcs_by_name = {f.name: f for f in unit.funcs}
    hal_prefix = _func_name(module, "hal")
    read_ops = [n for n in unit.public_names
                if n.endswith("Read") and n in funcs_by_name and not n.startswith(hal_prefix)]

    def out_type(name: str) -> str:
        params = funcs_by_name[name].params
        return params[1].split("*")[0].strip() if len(params) > 1 else ""

    types = {out_type(n) for n in read_ops}
    st = Emit()
    st.ln("int iStatus;")
    if "int" in types:
        st.ln("int iValue;")
    if "unsigned short" in types:
        st.ln("unsigned short usValue;")
    if "unsigned char" in types:
        st.ln("unsigned char ucValue;")
    st.blank()
    st.ln(f"iStatus = {_func_name(module, 'device_init')}({hvar});").check_status()
    for name in read_ops:
        ctype = out_type(name)
        label = name[len(module):]
        if ctype == "int":
            st.ln(f"iStatus = {name}({hvar}, &iValue);").check_status()
            st.ln(f'dbg_printf(DEBUG_LEVEL_INFO, "{unit.part} {label} = %d", iValue);')
        elif ctype == "unsigned short":
            st.ln(f"iStatus = {name}({hvar}, &usValue);").check_status()
            st.ln(f'dbg_printf(DEBUG_LEVEL_INFO, "{unit.part} {label} = 0x%04X", (unsigned int)usValue);')
        else:
            st.ln(f"iStatus = {name}({hvar}, &ucValue);").check_status()
            st.ln(f'dbg_printf(DEBUG_LEVEL_INFO, "{unit.part} {label} = 0x%02X", ucValue);')
    st.ln("return XST_SUCCESS;")
    func = CFunc(name=_func_name(module, "self_test"), ret="int", params=[f"{htype}* {hvar}"], body=st.out(),
                 brief=f"Non-destructive self-test for the {unit.part}: init + reads.",
                 doxy_params=[(hvar, "SPI denetleyici ornegi (gerekirse ilklendirilir).")],
                 doxy_return="XST_SUCCESS if all checks pass, else an XST_* error code.")
    return cmodel.CTest(runtime=runtime, module=module, includes=["dbg_printf.h", "xstatus.h", f"{module}.h"],
                        funcs=[func])


def _spi_select_hal(e: Emit, htype: str, hvar: str, hal: str, sel_def: str) -> None:
    if _is_axi_spi(htype):
        e.ln(f"iStatus = XSpi_SetSlaveSelect({hal}->{hvar}, (1U << {sel_def}));").check_status()
    else:
        e.ln(f"iStatus = XSpiPs_SetSlaveSelect({hal}->{hvar}, {sel_def});").check_status()


# --- destek dosyalari ---------------------------------------------------------------------------------

def write_support_files(spec: dict, out_dir: Path, get_descriptor: Callable[[str], dict],
                        write_output: Callable[[Path, str], Path], style: Callable[[str], str]) -> list[str]:
    """Vendor kopyasi + HAL koprusu + config dizisi (+ jesdlink). Yazilan yollar (str) doner."""
    devices = afe79_devices(spec, get_descriptor)
    if not devices:
        return []
    if len(devices) > 1:
        raise cmodel.CodegenError("S2C-CODEGEN-AFE-002: bu surumde tek AFE7900 desteklenir "
                                  f"(spec'te {len(devices)} adet)")
    device = devices[0]
    modules = cmodel.device_module_map(spec)
    module = modules.get(device.get("id", ""), cmodel._module_of(device.get("part", "AFE7900")))
    words = config_words(device)
    if not words:
        raise cmodel.CodegenError(
            f"S2C-CODEGEN-AFE-001: {device.get('id')} icin Latte config sozcukleri yok "
            f"(Schematic > cihaz > 'AFE config (Latte hex)' alanina yapistirin; spec: config.{CONFIG_KEY})")
    written: list[str] = []
    drivers_dir = out_dir / "drivers"

    # 1) TI kaynaklari (aynen)
    vendor_out = out_dir / VENDOR_OUT_REL
    for sub in ("Include", "Src"):
        src = VENDOR_SRC_DIR / sub
        if not src.is_dir():
            raise cmodel.CodegenError(f"S2C-CODEGEN-AFE-003: vendor kaynagi yok: {src}")
        (vendor_out / sub).mkdir(parents=True, exist_ok=True)
        for f in sorted(src.iterdir()):
            if f.suffix in (".c", ".h"):
                target = vendor_out / sub / f.name
                shutil.copy2(f, target)
                written.append(str(target))
    manifest = VENDOR_SRC_DIR / "MANIFEST_2.9.html"
    if manifest.is_file():
        target = vendor_out / manifest.name
        shutil.copy2(manifest, target)
        written.append(str(target))

    # 2) HAL koprusu: TI kullanici alani dosyasi (vendor klasorunde, QC disi)
    written.append(str(write_output(vendor_out / "Src" / "tiAfe79_baseFunc.c", _bridge_source(module))))

    # 3) config dizisi
    written.append(str(write_output(drivers_dir / f"{module}_config.h", style(_config_header(module, len(words))))))
    written.append(str(write_output(drivers_dir / f"{module}_config.c", style(_config_source(module, words)))))

    # 4) JESD204C IP baglanti modulu
    ips = jesd_ips(spec)
    if ips:
        written.append(str(write_output(drivers_dir / "ip" / "jesdlink.h", style(_jesdlink_header(ips)))))
        written.append(str(write_output(drivers_dir / "ip" / "jesdlink.c", style(_jesdlink_source(ips)))))
    return written


def _bridge_source(module: str) -> str:
    fn = lambda op: _func_name(module, op)  # noqa: E731
    return (
        "/*\n"
        " * tiAfe79_baseFunc.c - TI AFE79xx C API kullanici alani (HAL) - Spec2Code tarafindan uretildi.\n"
        " *\n"
        " * TI'in sablonundaki (Afe79xxUser/Src/tiAfe79_baseFunc.c) 'TBD: User domain' govdeleri Spec2Code\n"
        f" * surucusunun kopru API'sine ({module}.h) baglanir. Bu dosya vendor klasorunde durur; QC denetimi disidir.\n"
        " * Config sozcukleri (Latte hex) hostMemRead ile diziden okunur; dizi sonu 0xffffffff ile bildirilir.\n"
        " */\n"
        "#include <stdio.h>\n"
        "#include <stdint.h>\n"
        "#include <stdarg.h>\n"
        "\n"
        "#include \"tiAfe79_afeDeviceConstants.h\"\n"
        "#include \"tiAfe79_afeLibGlobals.h\"\n"
        "#include \"tiAfe79_afeGlobalConstants.h\"\n"
        "#include \"tiAfe79_baseFunc.h\"\n"
        "#include \"tiAfe79_basicFunctions.h\"\n"
        "#include \"tiAfe79_afeCommonMacros.h\"\n"
        f"#include \"{module}.h\"\n"
        "\n"
        "#define AFE_BRIDGE_LOG_MAX 256\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiRawWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t data)\n"
        "{\n"
        f"    return ({fn('hal_spi_write')}(afeInst->halConfig, addr, data) == 0) ? TI_AFE_RET_EXEC_PASS : TI_AFE_RET_EXEC_FAIL;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiRawRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *readVal)\n"
        "{\n"
        f"    return ({fn('hal_spi_read')}(afeInst->halConfig, addr, readVal) == 0) ? TI_AFE_RET_EXEC_PASS : TI_AFE_RET_EXEC_FAIL;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *data, uint16_t dataArraySize)\n"
        "{\n"
        "    uint16_t i;\n"
        "    for (i = 0; i < dataArraySize; i++)\n"
        "    {\n"
        "        AFE79_FUNC_EXEC(AFE79FNP(afeSpiRawWrite)(afeInst, addr + i, data[i]));\n"
        "    }\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t dataArraySize, uint8_t *data)\n"
        "{\n"
        "    uint16_t i;\n"
        "    for (i = 0; i < dataArraySize; i++)\n"
        "    {\n"
        "        AFE79_FUNC_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, addr + i, &data[i]));\n"
        "    }\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(giveSingleSysrefPulse)(AFE79_INST_TYPE afeInst)\n"
        "{\n"
        f"    {fn('hal_sysref_pulse')}(afeInst->halConfig);\n"
        "    AFE79FNP(afeWaitMs)(afeInst, 1);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(giveAfeAdcInput)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t toneNo)\n"
        "{\n"
        "    afeLogInfo(\"AFE%d: fabrika kalibrasyon girisi istendi (ch %d, ton 0x%02x) - kart kancasi yok\", AFE79_CURR_ID, chNo, toneNo);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(connectAfeTxToFb)(AFE79_INST_TYPE afeInst, uint8_t txChNo, uint8_t fbChNo, uint8_t bandNo)\n"
        "{\n"
        "    afeLogInfo(\"AFE%d: TX 0x%x -> FB 0x%x band %d baglantisi istendi - kart kancasi yok\", AFE79_CURR_ID, txChNo, fbChNo, bandNo);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeWait)(AFE79_INST_TYPE afeInst, uint32_t wait_s)\n"
        "{\n"
        "    (void)afeInst;\n"
        f"    {fn('hal_delay_ms')}(wait_s * 1000U);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeWaitMs)(AFE79_INST_TYPE afeInst, uint32_t wait_ms)\n"
        "{\n"
        "    (void)afeInst;\n"
        f"    {fn('hal_delay_ms')}(wait_ms);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(afeLogmsg)(AFE79_INST_TYPE afeInst, uint32_t level, const char *pcLogFmt, ...)\n"
        "{\n"
        "    char output[AFE_BRIDGE_LOG_MAX];\n"
        "    va_list arg;\n"
        "    if (level > AFE_CURRENT_LOG_LEVEL)\n"
        "    {\n"
        "        return TI_AFE_RET_EXEC_PASS;\n"
        "    }\n"
        "    va_start(arg, pcLogFmt);\n"
        "    (void)vsnprintf(output, sizeof(output), pcLogFmt, arg);\n"
        "    va_end(arg);\n"
        f"    {fn('hal_log')}(level, AFE_CURRENT_LOG_LEVEL, output);\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(updateSystemParamsPostDefault)(AFE79_INST_TYPE afeInst)\n"
        "{\n"
        "    afeLogDbg(\"%s\", \"Updating System Params\");\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(loadFactoryCalPackets)(AFE79_INST_TYPE afeInst)\n"
        "{\n"
        "    afeLogInfo(\"%s\", \"Loading Factory Calibration Packet\");\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
        "\n"
        "TI_AFE_API_COMP uint8_t AFE79FNP(hostMemRead)(AFE79_INST_TYPE afeInst, uint8_t memType, uint32_t addr, uint32_t numWordsToRead, uint32_t *buffPtr, uint32_t *numWordsActuallyRead)\n"
        "{\n"
        "    uint32_t i;\n"
        "    unsigned int word;\n"
        "    (void)afeInst;\n"
        "    (void)memType;\n"
        "    AFE79_PARAMS_VALID(numWordsToRead <= 1024);\n"
        "    *numWordsActuallyRead = 0;\n"
        "    for (i = 0; i < numWordsToRead; i++)\n"
        "    {\n"
        f"        if ({fn('hal_config_word')}((unsigned int)(addr + i), &word) == 0U)\n"
        "        {\n"
        "            break;\n"
        "        }\n"
        "        buffPtr[i] = (uint32_t)word;\n"
        "        (*numWordsActuallyRead)++;\n"
        "    }\n"
        "    if (*numWordsActuallyRead == 0)\n"
        "    {\n"
        "        *numWordsActuallyRead = 0xffffffff; /* dizi sonu: bring-up dizisi bitti */\n"
        "    }\n"
        "    return TI_AFE_RET_EXEC_PASS;\n"
        "}\n"
    )


def _config_header(module: str, count: int) -> str:
    MOD = module.upper()
    pas = cmodel._pascal_suffix(module)
    return (
        "/**\n"
        f" * @file {module}_config.h\n"
        " * @brief AFE7900 Latte config sozcukleri (afeDeviceBringupFromMem / hostMemRead kaynagi). Generated by Spec2Code.\n"
        " */\n"
        f"#ifndef {MOD}_CONFIG_H\n"
        f"#define {MOD}_CONFIG_H\n"
        "\n"
        f"#define {MOD}_CONFIG_WORD_COUNT {count}U /* Latte hex satir sayisi */\n"
        "\n"
        f"extern const unsigned int G_uiArr{pas}ConfigWords[{MOD}_CONFIG_WORD_COUNT];\n"
        "\n"
        f"#endif /* {MOD}_CONFIG_H */\n"
    )


def _config_source(module: str, words: list[int]) -> str:
    MOD = module.upper()
    pas = cmodel._pascal_suffix(module)
    rows = []
    for i in range(0, len(words), 8):
        rows.append("    " + ", ".join(f"0x{w:08X}U" for w in words[i:i + 8]) + ",")
    body = "\n".join(rows)
    return (
        "/**\n"
        f" * @file {module}_config.c\n"
        " * @brief AFE7900 Latte config sozcukleri: TI hex formati (opcode/veri sozcukleri), sirasi degistirilmez.\n"
        " *        Kaynak: Spec2Code spec devices[].config.afe_config_words (Latte cikisi). Generated by Spec2Code.\n"
        " */\n"
        f"#include \"{module}_config.h\"\n"
        "\n"
        f"const unsigned int G_uiArr{pas}ConfigWords[{MOD}_CONFIG_WORD_COUNT] = {{\n"
        f"{body}\n"
        "};\n"
    )


# --- jesdlink (drivers/ip/jesdlink.c/.h) --------------------------------------------------------------

def _jesdlink_header(ips: dict[str, dict]) -> str:
    rx = ips.get("rx")
    tx = ips.get("tx")
    ref = rx or tx
    is_64 = ref["link_layer"] == "64b66b"
    lanes = int(ref["lanes"])
    subclass = int(ref["subclass"])
    return (
        "/**\n"
        " * @file jesdlink.h\n"
        " * @brief JESD204C IP (PG242) baglanti yardimcilari: cekirdek reset (timeout'lu), link durumu, lane sayaclari.\n"
        f" *        Kodlama: {'64B/66B' if is_64 else '8B/10B'}, {lanes} lane, alt sinif {subclass}"
        f" (XSA C_ENCODING/C_LANES'ten; tek akis). Generated by Spec2Code.\n"
        " */\n"
        "#ifndef JESDLINK_H\n"
        "#define JESDLINK_H\n"
        "\n"
        f"#define JESDLINK_RX_BASE 0x{(rx['base'] if rx else 0):08X}U /* {rx['id'] if rx else 'RX cekirdegi yok'} */\n"
        f"#define JESDLINK_TX_BASE 0x{(tx['base'] if tx else 0):08X}U /* {tx['id'] if tx else 'TX cekirdegi yok'} */\n"
        f"#define JESDLINK_LANES {lanes}U\n"
        f"#define JESDLINK_SUBCLASS {subclass}U\n"
        f"#define JESDLINK_ENCODING_64B66B {'TRUE' if is_64 else 'FALSE'}\n"
        "#define JESDLINK_RESET_TIMEOUT_MS 200U /* reset kaldirma: CORE_RESET_STATE ve GT_RESET_BUSY dusmeli */\n"
        "#define JESDLINK_LINK_TIMEOUT_MS 1000U /* link kurulumu bekleme */\n"
        "#define JESDLINK_POLL_STEP_MS 1U\n"
        "\n"
        f"#define JESDLINK_REG_RESET 0x{JESD_REG_RESET:03X}U\n"
        f"#define JESDLINK_REG_CTRL_SYSREF 0x{JESD_REG_CTRL_SYSREF:03X}U\n"
        f"#define JESDLINK_REG_STAT_STATUS 0x{JESD_REG_STAT_STATUS:03X}U\n"
        f"#define JESDLINK_REG_STAT_IRQ 0x{JESD_REG_STAT_IRQ:03X}U\n"
        + (f"#define JESDLINK_REG_STAT_RX_ERR 0x{JESD_REG_STAT_RX_ERR_8B10B:03X}U /* 8B/10B lane basina 4 bit */\n"
           if not is_64 else
           f"#define JESDLINK_LANE_BASE 0x{JESD_LANE_BASE:03X}U\n"
           f"#define JESDLINK_LANE_BLOCK 0x{JESD_LANE_BLOCK:03X}U\n"
           f"#define JESDLINK_LANE_ERROR_CNT0 0x{JESD_LANE_ERROR_CNT0:03X}U /* CRC[31:16] MB[15:8] SH[7:0] */\n")
        + "\n"
        "#define JESDLINK_RESET_BIT 0x00000001U           /* RESET[0]: 1 yaz = reset baslat */\n"
        "#define JESDLINK_RESET_TYPE_LINK 0x00000002U     /* RESET_TYPE[1]: 1 = yalniz link reset */\n"
        "#define JESDLINK_RESET_CORE_STATE 0x00000020U    /* CORE_RESET_STATE[5]: 1 = reset'te */\n"
        "#define JESDLINK_RESET_GT_BUSY 0x00000080U       /* GT_RESET_BUSY[7] */\n"
        "#define JESDLINK_RESET_GT_POWERGOOD 0x00000040U  /* GT_POWERGOOD[6] */\n"
        "#define JESDLINK_STAT_SYSREF_CAPTURED 0x00000002U\n"
        "#define JESDLINK_STAT_SYSREF_ERROR 0x00000004U\n"
        "#define JESDLINK_STAT_RX_STARTED 0x00004000U\n"
        + ("#define JESDLINK_STAT_SH_LOCK 0x00000010U        /* SYNC_HEADER_LOCK_64B66B[4] */\n"
           "#define JESDLINK_STAT_MB_LOCK 0x00000020U        /* MB_LOCK_64B66B[5] */\n"
           if is_64 else
           "#define JESDLINK_STAT_SYNC 0x00001000U           /* SYNC_STATUS[12] */\n"
           "#define JESDLINK_STAT_CGS 0x00002000U            /* CGS_STATUS[13] */\n"
           "#define JESDLINK_STAT_ALIGN_ERROR 0x00008000U    /* ALIGN_ERROR_8B10B[15] */\n")
        + "\n"
        "/* --- public API --- */\n"
        "int jesdLinkCoreReset(unsigned int uiBase, unsigned int uiAssert);\n"
        "int jesdLinkLinkReset(unsigned int uiBase);\n"
        "int jesdLinkRxLinkCheck(void);\n"
        "int jesdLinkRxLinkWait(unsigned int uiTimeoutMs);\n"
        "int jesdLinkTxCheck(void);\n"
        "unsigned int jesdLinkStatusRead(unsigned int uiBase);\n"
        "int jesdLinkRxLaneErrorsRead(unsigned char ucLane, unsigned int* uipErrors);\n"
        "void jesdLinkErrorCountersClear(void);\n"
        "\n"
        "#endif /* JESDLINK_H */\n"
    )


def _jesdlink_source(ips: dict[str, dict]) -> str:
    rx = ips.get("rx")
    tx = ips.get("tx")
    ref = rx or tx
    is_64 = ref["link_layer"] == "64b66b"
    subclass = int(ref["subclass"])
    e = Emit()
    e.level = 0
    e.ln("/**")
    e.ln(" * @file jesdlink.c")
    e.ln(" * @brief JESD204C IP (PG242) baglanti yardimcilari. Generated by Spec2Code.")
    e.ln(" *")
    e.ln(" * Reset semantigi (kullanici kurali): uiAssert=1 -> RESET[0]'a 1 yazilir (tam reset, cekirdek GT reset")
    e.ln(" * bitene kadar reset'te kalir); uiAssert=0 -> CORE_RESET_STATE ve GT_RESET_BUSY bitlerinin dusmesi")
    e.ln(" * JESDLINK_RESET_TIMEOUT_MS icinde beklenir, dolarsa XST_FAILURE. Tum durum kontrolleri timeout'ludur.")
    e.ln(" */")
    e.ln('#include "jesdlink.h"')
    e.ln('#include "dbg_printf.h"')
    e.ln('#include "sleep.h"')
    e.ln('#include "xil_io.h"')
    e.ln('#include "xstatus.h"')
    e.ln("#include <stddef.h>")
    e.blank()
    e.ln("static unsigned int jesdLinkRead(unsigned int uiBase, unsigned int uiOffset)")
    e.ln("{")
    e.ln("    return (unsigned int)Xil_In32((UINTPTR)uiBase + (UINTPTR)uiOffset);")
    e.ln("}")
    e.blank()
    e.ln("static void jesdLinkWrite(unsigned int uiBase, unsigned int uiOffset, unsigned int uiValue)")
    e.ln("{")
    e.ln("    Xil_Out32((UINTPTR)uiBase + (UINTPTR)uiOffset, (u32)uiValue);")
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkCoreReset(unsigned int uiBase, unsigned int uiAssert)")
    e.ln("{")
    e.level = 1
    e.ln("unsigned int uiElapsedMs = 0U;")
    e.ln("unsigned int uiReset;")
    e.blank()
    e.open("if (uiBase == 0U)").ln("return XST_SUCCESS; /* bu yonde cekirdek yok */").close()
    e.open("if (uiAssert != 0U)")
    e.ln("jesdLinkWrite(uiBase, JESDLINK_REG_RESET, JESDLINK_RESET_BIT);")
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"JESD 0x%08X: reset verildi\", uiBase);")
    e.ln("return XST_SUCCESS;")
    e.close()
    e.open("while (uiElapsedMs < JESDLINK_RESET_TIMEOUT_MS)")
    e.ln("uiReset = jesdLinkRead(uiBase, JESDLINK_REG_RESET);")
    e.open("if ((uiReset & (JESDLINK_RESET_BIT | JESDLINK_RESET_CORE_STATE | JESDLINK_RESET_GT_BUSY)) == 0U)")
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"JESD 0x%08X: reset kalkti (%u ms, RESET=0x%08X)\", uiBase, uiElapsedMs, uiReset);")
    e.ln("return XST_SUCCESS;")
    e.close()
    e.ln("usleep(JESDLINK_POLL_STEP_MS * 1000U);")
    e.ln("uiElapsedMs += JESDLINK_POLL_STEP_MS;")
    e.close()
    e.ln("uiReset = jesdLinkRead(uiBase, JESDLINK_REG_RESET);")
    e.ln("dbg_printf(DEBUG_LEVEL_ERROR, \"JESD 0x%08X: reset %u ms icinde kalkmadi (RESET=0x%08X, GT_POWERGOOD=%u)\", uiBase,")
    e.ln("           JESDLINK_RESET_TIMEOUT_MS, uiReset, (uiReset & JESDLINK_RESET_GT_POWERGOOD) != 0U ? 1U : 0U);")
    e.ln("return XST_FAILURE;")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkLinkReset(unsigned int uiBase)")
    e.ln("{")
    e.level = 1
    e.open("if (uiBase == 0U)").ln("return XST_SUCCESS; /* bu yonde cekirdek yok */").close()
    e.ln("/* RESET_TYPE=1: yalniz link katmani (GT ve refclk yolu korunur); bit0 kendiliginden temizlenir. */")
    e.ln("jesdLinkWrite(uiBase, JESDLINK_REG_RESET, JESDLINK_RESET_TYPE_LINK | JESDLINK_RESET_BIT);")
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"JESD 0x%08X: link reset verildi (GT korunur)\", uiBase);")
    e.ln("return jesdLinkCoreReset(uiBase, 0U);")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("unsigned int jesdLinkStatusRead(unsigned int uiBase)")
    e.ln("{")
    e.ln("    return (uiBase == 0U) ? 0U : jesdLinkRead(uiBase, JESDLINK_REG_STAT_STATUS);")
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkRxLinkCheck(void)")
    e.ln("{")
    e.level = 1
    e.ln("unsigned int uiStatus;")
    e.blank()
    e.open("if (JESDLINK_RX_BASE == 0U)").ln("return XST_FAILURE;").close()
    e.ln("uiStatus = jesdLinkRead(JESDLINK_RX_BASE, JESDLINK_REG_STAT_STATUS);")
    e.open("if ((uiStatus & JESDLINK_STAT_SYSREF_ERROR) != 0U)").ln("return XST_FAILURE;").close()
    if subclass == 1:
        e.ln("/* Alt sinif 1: link ancak SYSREF yakalandiktan sonra deterministik. */")
        e.open("if ((uiStatus & JESDLINK_STAT_SYSREF_CAPTURED) == 0U)").ln("return XST_FAILURE;").close()
    if is_64:
        e.ln("/* 64B/66B: sync header kilidi + (genisletilmis) multiblok kilidi + veri basladi. */")
        e.open("if ((uiStatus & (JESDLINK_STAT_SH_LOCK | JESDLINK_STAT_MB_LOCK | JESDLINK_STAT_RX_STARTED)) != "
               "(JESDLINK_STAT_SH_LOCK | JESDLINK_STAT_MB_LOCK | JESDLINK_STAT_RX_STARTED))")
    else:
        e.ln("/* 8B/10B: SYNC~ kaldirildi + CGS (kod grubu senkronu) tamam + hizalama hatasi yok + veri basladi (ILAS gecildi). */")
        e.open("if (((uiStatus & JESDLINK_STAT_ALIGN_ERROR) != 0U) || "
               "((uiStatus & (JESDLINK_STAT_SYNC | JESDLINK_STAT_CGS | JESDLINK_STAT_RX_STARTED)) != "
               "(JESDLINK_STAT_SYNC | JESDLINK_STAT_CGS | JESDLINK_STAT_RX_STARTED)))")
    e.ln("return XST_FAILURE;")
    e.close()
    e.ln("return XST_SUCCESS;")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkRxLinkWait(unsigned int uiTimeoutMs)")
    e.ln("{")
    e.level = 1
    e.ln("unsigned int uiElapsedMs = 0U;")
    e.blank()
    e.open("while (uiElapsedMs < uiTimeoutMs)")
    e.open("if (jesdLinkRxLinkCheck() == XST_SUCCESS)")
    e.ln("dbg_printf(DEBUG_LEVEL_INFO, \"JESD RX: link kuruldu (%u ms, STAT=0x%08X)\", uiElapsedMs, jesdLinkStatusRead(JESDLINK_RX_BASE));")
    e.ln("return XST_SUCCESS;")
    e.close()
    e.ln("usleep(JESDLINK_POLL_STEP_MS * 1000U);")
    e.ln("uiElapsedMs += JESDLINK_POLL_STEP_MS;")
    e.close()
    e.ln("dbg_printf(DEBUG_LEVEL_ERROR, \"JESD RX: link %u ms icinde kurulmadi (STAT=0x%08X)\", uiTimeoutMs, jesdLinkStatusRead(JESDLINK_RX_BASE));")
    e.ln("return XST_FAILURE;")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkTxCheck(void)")
    e.ln("{")
    e.level = 1
    e.ln("unsigned int uiStatus;")
    e.ln("unsigned int uiReset;")
    e.blank()
    e.open("if (JESDLINK_TX_BASE == 0U)").ln("return XST_FAILURE;").close()
    e.ln("uiReset = jesdLinkRead(JESDLINK_TX_BASE, JESDLINK_REG_RESET);")
    e.open("if ((uiReset & (JESDLINK_RESET_CORE_STATE | JESDLINK_RESET_GT_BUSY)) != 0U)").ln("return XST_FAILURE;").close()
    e.ln("uiStatus = jesdLinkRead(JESDLINK_TX_BASE, JESDLINK_REG_STAT_STATUS);")
    e.open("if ((uiStatus & JESDLINK_STAT_SYSREF_ERROR) != 0U)").ln("return XST_FAILURE;").close()
    if subclass == 1:
        e.open("if ((uiStatus & JESDLINK_STAT_SYSREF_CAPTURED) == 0U)").ln("return XST_FAILURE;").close()
    e.ln("return XST_SUCCESS;")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("int jesdLinkRxLaneErrorsRead(unsigned char ucLane, unsigned int* uipErrors)")
    e.ln("{")
    e.level = 1
    e.open("if ((uipErrors == NULL) || (ucLane >= JESDLINK_LANES) || (JESDLINK_RX_BASE == 0U))").ln("return XST_FAILURE;").close()
    if is_64:
        e.ln("/* CRC[31:16] | MB hizalama[15:8] | SH hizalama[7:0] (L<n>_STAT_RX_ERROR_CNT0). */")
        e.ln("*uipErrors = jesdLinkRead(JESDLINK_RX_BASE, JESDLINK_LANE_BASE + ((unsigned int)ucLane * JESDLINK_LANE_BLOCK) + JESDLINK_LANE_ERROR_CNT0);")
    else:
        e.ln("/* STAT_RX_ERR: lane basina 4 bit (bit2 K, bit1 disparity, bit0 not-in-table); okuyunca temizlenir. */")
        e.ln("*uipErrors = (jesdLinkRead(JESDLINK_RX_BASE, JESDLINK_REG_STAT_RX_ERR) >> ((unsigned int)ucLane * 4U)) & 0xFU;")
    e.ln("return XST_SUCCESS;")
    e.level = 0
    e.ln("}")
    e.blank()
    e.ln("void jesdLinkErrorCountersClear(void)")
    e.ln("{")
    e.level = 1
    if is_64:
        e.ln("unsigned char ucLane;")
        e.ln("unsigned int uiDummy;")
        e.blank()
        e.ln("/* Sayaclar okuyunca temizlenir (PG242): her lane bir kez okunur. */")
        e.open("for (ucLane = 0U; ucLane < (unsigned char)JESDLINK_LANES; ucLane++)")
        e.ln("(void)jesdLinkRxLaneErrorsRead(ucLane, &uiDummy);")
        e.close()
    else:
        e.ln("unsigned int uiDummy;")
        e.blank()
        e.ln("/* STAT_RX_ERR okuyunca temizlenir (PG242). */")
        e.ln("(void)jesdLinkRxLaneErrorsRead(0U, &uiDummy);")
    e.ln("/* Kesme durum bitleri: 1 yazinca temizlenir. */")
    e.open("if (JESDLINK_RX_BASE != 0U)")
    e.ln("jesdLinkWrite(JESDLINK_RX_BASE, JESDLINK_REG_STAT_IRQ, jesdLinkRead(JESDLINK_RX_BASE, JESDLINK_REG_STAT_IRQ));")
    e.close()
    e.open("if (JESDLINK_TX_BASE != 0U)")
    e.ln("jesdLinkWrite(JESDLINK_TX_BASE, JESDLINK_REG_STAT_IRQ, jesdLinkRead(JESDLINK_TX_BASE, JESDLINK_REG_STAT_IRQ));")
    e.close()
    e.level = 0
    e.ln("}")
    return "\n".join(e.lines) + "\n"
