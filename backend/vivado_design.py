"""Vivado tasarım üretimi (Faz A): PS konfigürasyon formundan Tcl üretir,
Vivado'yu batch modda koşturur ve İKİ AŞAMADA teslim eder:

  1) pre-synthesis .xsa — PS-only tasarımda sentez GEREKMEZ; dakikalar değil
     ~1-2 dk. Hazır olur olmaz ``vivado.xsa_ready`` olayı yayınlanır ve
     kullanıcı Setup akışına geçebilir.
  2) istenirse synth + impl → .bit (ZynqMP) / .pdi (Versal) + bit'li sabit
     (fixed) XSA. Hazır olunca ``vivado.bit_ready`` yayınlanır.

Kapsam (Faz A): Zynq UltraScale+ (tam PS konfigürasyonu: çevre birimleri +
MIO + referans saat + DDR custom/none) ve Versal (UART/I2C, PMC/PS MIO; DDR
Faz A'da yok — ajan OCM'den koşar). Zynq-7000 bilinçli olarak kapsam dışı.

DÜRÜSTLÜK NOTU: Buradaki tüm PSU__*/CIPS parametre adları ve değer
biçimleri Vitis 2023.2 kurulumundaki resmi zcu102.xsa / vck190.xsa hardware
handoff'larından ve zynq_ultra_ps_e IP verisinden doğrulanarak alınmıştır
(ör. ``PSU__UART0__PERIPHERAL__IO = "MIO 18 .. 19"``,
``PS_UART0_PERIPHERAL {{ENABLE 1} {IO {PMC_MIO 42 .. 43}}}``). MIO seçimi
serbest metin değildir ama yasal aralık doğrulaması Vivado'ya bırakılır:
geçersiz bir MIO ataması 1. aşamada saniyeler içinde net Vivado hatasıyla
döner — el yapımı (uydurulmuş) bir pinmux tablosu taşımıyoruz.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
import subprocess
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

#: ZynqMP PS çevre birimi -> PSU parametre kökü (zcu102.xsa hwh'den doğrulandı).
_ZYNQMP_PERIPHERALS: dict[str, str] = {
    "uart0": "PSU__UART0",
    "uart1": "PSU__UART1",
    "i2c0": "PSU__I2C0",
    "i2c1": "PSU__I2C1",
    "spi0": "PSU__SPI0",
    "spi1": "PSU__SPI1",
    "qspi": "PSU__QSPI",
    "gem0": "PSU__ENET0",
    "gem1": "PSU__ENET1",
    "gem2": "PSU__ENET2",
    "gem3": "PSU__ENET3",
    "sd0": "PSU__SD0",
    "sd1": "PSU__SD1",
}

#: Versal CIPS anahtarı (vck190.xsa PS_PMC_CONFIG'ten doğrulandı). Faz A'da
#: yalnız UART/I2C: diğerlerinin anahtar yapısı farklı (ör. PMC_QSPI_*) ve
#: henüz gerçek bir tasarımla doğrulanmadı — uydurmuyoruz.
_VERSAL_PERIPHERALS: dict[str, str] = {
    "uart0": "PS_UART0_PERIPHERAL",
    "uart1": "PS_UART1_PERIPHERAL",
    "i2c0": "PS_I2C0_PERIPHERAL",
    "i2c1": "PS_I2C1_PERIPHERAL",
}

_MIO_RE = re.compile(r"^(?:MIO|PMC_MIO|PS_MIO)\s+\d+(?:\s*\.\.\s*\d+)?$")


#: QSPI mod seçenekleri (değerler zcu102.xsa'dan ve canlı probe'dan
#: doğrulandı): Single → IO 'MIO 0 .. 5'; Dual Parallel (2 yonga, toplam x8)
#: → IO 'MIO 0 .. 12'. FBCLK MIO 6'dadır ve isteğe bağlıdır.
_QSPI_MODES = {"Single": "MIO 0 .. 5", "Dual Parallel": "MIO 0 .. 12"}
_QSPI_DATA_MODES = ("x1", "x2", "x4")


@dataclass
class VivadoPeripheral:
    kind: str          # uart0 | i2c0 | ... (yukarıdaki tablolardan)
    mio: str = ""      # "MIO 18 .. 19" / "PMC_MIO 42 .. 43"; boş = IP varsayılanı
    # Yalnız qspi için (ZynqMP): mod/data/FBCLK — jenerik giriş.
    qspi_mode: str = ""       # "" = Single | "Dual Parallel"
    qspi_data_mode: str = ""  # "" = IP varsayılanı | x1 | x2 | x4 (yonga başına)
    qspi_fbclk: bool = False  # MIO 6 geri besleme saati


@dataclass
class VivadoDesignConfig:
    vivado_path: str            # örn. C:\Xilinx_2023_2\Vivado\2023.2
    platform: str               # zynq_ultrascale | versal
    part: str                   # örn. xczu9eg-ffvb1156-2-e
    temp_path: str              # staging/proje dizini (kullanıcı verir)
    design_name: str = "spec2code_hw"
    peripherals: list[VivadoPeripheral] = field(default_factory=list)
    ref_clk_mhz: str = ""       # boş = IP varsayılanı; ZynqMP: PSU__PSS_REF_CLK__FREQMHZ
    ddr_mode: str = "none"      # none (OCM-only) | model (havuzdan) | custom (yalnız ZynqMP)
    ddr_params: dict[str, str] = field(default_factory=dict)  # PSU__DDRC__* alt kümesi (custom)
    ddr_model: str = ""         # model modunda: zynqmp_ddr_parts.json id'si
    ddr_bus_width: str = ""     # model modunda: "16 Bit" | "32 Bit" | "64 Bit"
    ddr_speed_bin: str = ""     # model modunda boş = girdinin default_speed_bin'i
    add_regmap_test_ip: bool = False  # opsiyonel: Register Map Test IP (AXI4-Lite)
    make_bitstream: bool = False
    timeout_s: int = 3600


def validate_design(cfg: VivadoDesignConfig) -> list[str]:
    errors: list[str] = []
    if cfg.platform not in ("zynq_ultrascale", "versal"):
        errors.append(
            f"platform: yalnız zynq_ultrascale ve versal desteklenir (Faz A); Zynq-7000 kapsam dışı (şu an: {cfg.platform!r})")
    if not cfg.part.strip():
        errors.append("part: hedef parça numarası boş olamaz (örn. xczu9eg-ffvb1156-2-e)")
    if not cfg.vivado_path.strip():
        errors.append("vivado_path: Vivado kurulum dizini gerekli (örn. C:\\Xilinx_2023_2\\Vivado\\2023.2)")
    if not cfg.temp_path.strip():
        errors.append("temp_path: staging dizini gerekli")
    table = _ZYNQMP_PERIPHERALS if cfg.platform == "zynq_ultrascale" else _VERSAL_PERIPHERALS
    if not cfg.peripherals:
        errors.append("peripherals: en az bir PS çevre birimi seçilmeli (test edilecek arayüzler)")
    for per in cfg.peripherals:
        if per.kind not in table:
            supported = ", ".join(sorted(table))
            errors.append(f"peripherals.{per.kind}: bu platformda desteklenmiyor (desteklenen: {supported})")
        if per.mio and not _MIO_RE.match(per.mio.strip()):
            errors.append(
                f"peripherals.{per.kind}.mio: biçim 'MIO 18 .. 19' / 'PMC_MIO 42 .. 43' olmalı (şu an: {per.mio!r})")
        if per.kind == "qspi":
            if per.qspi_mode and per.qspi_mode not in _QSPI_MODES:
                errors.append(
                    f"peripherals.qspi.qspi_mode: {' | '.join(_QSPI_MODES)} olmalı (şu an: {per.qspi_mode!r})")
            if per.qspi_data_mode and per.qspi_data_mode not in _QSPI_DATA_MODES:
                errors.append(
                    f"peripherals.qspi.qspi_data_mode: {' | '.join(_QSPI_DATA_MODES)} olmalı (şu an: {per.qspi_data_mode!r})")
        elif per.qspi_mode or per.qspi_data_mode or per.qspi_fbclk:
            errors.append(f"peripherals.{per.kind}: qspi_* alanları yalnız qspi için geçerli")
    if cfg.ref_clk_mhz:
        try:
            float(cfg.ref_clk_mhz)
        except ValueError:
            errors.append(f"ref_clk_mhz: sayı olmalı (şu an: {cfg.ref_clk_mhz!r})")
    if cfg.ddr_mode not in ("none", "model", "custom"):
        errors.append(f"ddr_mode: none | model | custom (şu an: {cfg.ddr_mode!r})")
    if cfg.ddr_mode == "model":
        if cfg.platform != "zynq_ultrascale":
            errors.append("ddr_mode=model: DDR model havuzu şimdilik yalnız ZynqMP'de (Versal DDR NoC sonraki fazda)")
        else:
            entry = _ddr_part_by_id(cfg.ddr_model)
            if entry is None:
                known = ", ".join(e.get("id", "?") for e in zynqmp_ddr_parts()) or "(havuz boş)"
                errors.append(f"ddr_model: havuzda yok (şu an: {cfg.ddr_model!r}; mevcut: {known})")
            else:
                if cfg.ddr_bus_width and cfg.ddr_bus_width not in entry.get("bus_widths", []):
                    errors.append(
                        f"ddr_bus_width: {entry['label']} için {cfg.ddr_bus_width!r} desteklenmiyor "
                        f"(seçenekler: {', '.join(entry.get('bus_widths', []))})")
                if cfg.ddr_speed_bin and cfg.ddr_speed_bin not in entry.get("speed_bins", []):
                    errors.append(
                        f"ddr_speed_bin: {entry['label']} için {cfg.ddr_speed_bin!r} desteklenmiyor "
                        f"(seçenekler: {', '.join(entry.get('speed_bins', []))})")
    if cfg.add_regmap_test_ip and cfg.platform != "zynq_ultrascale":
        errors.append("add_regmap_test_ip: Register Map Test IP şimdilik yalnız ZynqMP'de (Versal M_AXI/NoC sonraki fazda)")
    if cfg.ddr_mode == "custom":
        if cfg.platform != "zynq_ultrascale":
            errors.append("ddr_mode=custom: Faz A'da DDR yalnız ZynqMP'de; Versal DDR (NoC) sonraki fazda — ajan OCM'den koşar")
        if not cfg.ddr_params:
            errors.append("ddr_params: custom DDR için en az bir PSU__DDRC__ parametresi gerekli")
        for key in cfg.ddr_params:
            if not key.startswith("PSU__DDRC__"):
                errors.append(f"ddr_params.{key}: yalnız PSU__DDRC__ parametreleri kabul edilir")
    return errors


def _tcl_path(path: Path) -> str:
    return "{" + _fs(path) + "}"


def _fs(path: Path) -> str:
    # Tcl cift tirnak icinde "\U" gibi bilinmeyen kacislar ters boluyu YER
    # (E2E bulgusu: marker'daki Windows yolu C:UsersQP... halinde geldi);
    # marker ve Tcl yollarinda daima forward slash.
    return str(path).replace("\\", "/")


def _tcl_brace(value: str) -> str:
    return "{" + value + "}"


def _marker(text: str) -> str:
    # Değişken içerebilir; pump S2C-VIVADO| öneki üzerinden ayrıştırır.
    return f'puts "S2C-VIVADO|{text}"\n'


#: MIO atama Tcl yardımcısı. SAHA KÖK NEDENİ (2026-07-06, Vivado 2023.2 ile
#: satır satır doğrulandı):
#:  - MIO boş bırakılınca birimler TOPLU (-dict) enable edilirse Vivado
#:    varsayılan MIO'ları BAĞIMSIZ hesaplayıp çakışıyor. Çözüm: TEK TEK
#:    enable — Vivado her yeni birimi boş MIO'ya yerleştirir (QSPI→0..5,
#:    SPI0→12..17, SPI1→6..11 çakışmasız).
#:  - AMA Vivado bir birime SABİT varsayılan verir ve çakışsa bile TAŞIMAZ:
#:    UART0 varsayılanı 'MIO 6 .. 7' zaten SPI1'in aldığı 6..11 ile çakışınca
#:    enable geri alındı. list_property_value bu IO parametreleri için boş
#:    döner, IO indeksle set edilemez — yani yasal seçenekleri Vivado'dan
#:    programatik alamıyoruz. Gerçek kartta bu birimin MIO'sunu zaten şema
#:    belirler. Bu yüzden: çakışmayan kombinasyonlar otomatik çalışır;
#:    çakışan birimde net, eyleme dönük hata verilir (uydurma pinmux yok).
#: Kullanıcı MIO verdiyse enable+IO birlikte, vermediyse yalnız enable.
_ZYNQMP_IO_HELPERS_TCL = """proc spec2codeAssignPeripheral {ps enable_param io_param requested label} {
    if {$requested ne ""} {
        if {[catch {set_property -dict [list CONFIG.$enable_param {1} CONFIG.$io_param $requested] $ps} spec2code_err]} {
            error "Spec2Code: $label icin verilen MIO '$requested' Vivado tarafindan reddedildi (baska bir cevre biriminin MIO'suyla cakisiyor ya da bu birim icin gecerli degil). MIO'lari gozden gecirin. Vivado: $spec2code_err"
        }
    } else {
        if {[catch {set_property CONFIG.$enable_param {1} $ps} spec2code_err]} {
            error "Spec2Code: $label otomatik yerlestirilemedi - varsayilan MIO'su onceden yerlestirilmis bir cevre biriminin MIO'suyla cakisiyor ve Vivado bu birimi otomatik tasimaz. COZUM: $label icin (ya da cakisan digeri icin) MIO'yu formda ELLE belirtin - gercek kartta bu deger zaten semadan okunur. Vivado: $spec2code_err"
        }
    }
    puts "S2C-VIVADO|io_assigned=$label|[get_property CONFIG.$io_param $ps]"
}
proc spec2codeAssignQspi {ps io mode data_mode fbclk} {
    # QSPI mod/IO/FBCLK tutarli TEK dict'te verilmeli (parametre adlari ve
    # 'Dual Parallel' degeri zcu102.xsa'dan dogrulandi).
    set cfg [list CONFIG.PSU__QSPI__PERIPHERAL__ENABLE {1} \
                  CONFIG.PSU__QSPI__PERIPHERAL__IO $io \
                  CONFIG.PSU__QSPI__PERIPHERAL__MODE $mode]
    if {$data_mode ne ""} { lappend cfg CONFIG.PSU__QSPI__PERIPHERAL__DATA_MODE $data_mode }
    if {$fbclk} {
        lappend cfg CONFIG.PSU__QSPI__GRP_FBCLK__ENABLE {1} CONFIG.PSU__QSPI__GRP_FBCLK__IO {MIO 6}
    } else {
        lappend cfg CONFIG.PSU__QSPI__GRP_FBCLK__ENABLE {0}
    }
    if {[catch {set_property -dict $cfg $ps} spec2code_err]} {
        error "Spec2Code: QSPI konfigurasyonu reddedildi (mod=$mode data=$data_mode io=$io fbclk=$fbclk). Vivado: $spec2code_err"
    }
    puts "S2C-VIVADO|io_assigned=qspi|$io ($mode[expr {$data_mode ne {} ? \" $data_mode\" : {}}][expr {$fbclk ? { +FBCLK} : {}}])"
}
"""

#: Otomatik yerleşimde işlem sırası: geniş/sabit bloklar önce (QSPI, GEM, SD),
#: küçük ve alternatifli olanlar sonra — Vivado'nun açgözlü yerleşiminde
#: kıtlığı önler.
_ZYNQMP_AUTO_PRIORITY = {"qspi": 0, "gem": 1, "sd": 2, "spi": 3, "uart": 4, "i2c": 5}


def _zynqmp_auto_rank(kind: str) -> int:
    for prefix, rank in _ZYNQMP_AUTO_PRIORITY.items():
        if kind.startswith(prefix):
            return rank
    return 9


def _zynqmp_ps_config_tcl(cfg: VivadoDesignConfig) -> str:
    # Önce IO içermeyen genel ayarlar tek dict'te (saat, DDR, AXI/PL kapama).
    pairs: list[str] = []
    if cfg.ref_clk_mhz:
        pairs.append(f"CONFIG.PSU__PSS_REF_CLK__FREQMHZ {_tcl_brace(cfg.ref_clk_mhz)}")
    if cfg.ddr_mode == "none":
        pairs.append("CONFIG.PSU__DDRC__ENABLE {0}")
    elif cfg.ddr_mode == "model":
        # Havuz girdisi: yalnız GEOMETRİ + veri yolu verilir (Xilinx
        # memparts.csv). HIZA BİLEREK DOKUNULMAZ: PCW'nin tutarlı varsayılanı
        # DDR4-1600'de kalır — tüm listelenen parçalar geriye uyumludur ve
        # ilk bring-up için yeterlidir. E2E bulgusu: SPEED_BIN/FREQMHZ'i
        # script'le değiştirmek PCW'de bin↔frekans↔CL tavuk-yumurtasına
        # takılıyor (2133P verildiğinde CL native 15'e çözülüyor ama işletim
        # frekansı 800'de kaldığından validator CL {11,12} isteyip TÜM set'i
        # geri alıyor; frekans+bin+PLL tam dict'te bile atomik reddedildi).
        # Hız yükseltme kart üzerinde doğrulanınca ayrı faz olarak ele alınır.
        # Zamanlamalar (CL/CWL/tRCD...) hiç yazılmaz — 1600 varsayılanında
        # PCW'nin kendi tutarlı değerleri geçerlidir.
        entry = _ddr_part_by_id(cfg.ddr_model) or {}
        bus_width = cfg.ddr_bus_width or "32 Bit"
        pairs.extend([
            "CONFIG.PSU__DDRC__ENABLE {1}",
            f"CONFIG.PSU__DDRC__MEMORY_TYPE {_tcl_brace(entry.get('memory_type', 'DDR 4'))}",
            f"CONFIG.PSU__DDRC__COMPONENTS {_tcl_brace(entry.get('components', 'Components'))}",
            f"CONFIG.PSU__DDRC__DEVICE_CAPACITY {_tcl_brace(entry.get('device_capacity', ''))}",
            f"CONFIG.PSU__DDRC__DRAM_WIDTH {_tcl_brace(entry.get('dram_width', ''))}",
            f"CONFIG.PSU__DDRC__ROW_ADDR_COUNT {_tcl_brace(entry.get('row_addr_count', ''))}",
            f"CONFIG.PSU__DDRC__COL_ADDR_COUNT {_tcl_brace(entry.get('col_addr_count', ''))}",
            f"CONFIG.PSU__DDRC__BANK_ADDR_COUNT {_tcl_brace(entry.get('bank_addr_count', ''))}",
            f"CONFIG.PSU__DDRC__BG_ADDR_COUNT {_tcl_brace(entry.get('bg_addr_count', ''))}",
            f"CONFIG.PSU__DDRC__BUS_WIDTH {_tcl_brace(bus_width)}",
            "CONFIG.PSU__DDRC__ECC {Disabled}",
        ])
    else:
        pairs.append("CONFIG.PSU__DDRC__ENABLE {1}")
        for key, value in cfg.ddr_params.items():
            pairs.append(f"CONFIG.{key} {_tcl_brace(str(value))}")
    # PS-only tasarım: kullanılmayan PL-yönlü AXI masterlar ve PL saati
    # kapatılır; aksi halde bağlantısız arabirimler validate'te eleştirel
    # uyarı üretir (adlar zcu102.xsa hwh'den doğrulandı).
    pairs.extend([
        "CONFIG.PSU__USE__M_AXI_GP0 {0}",
        "CONFIG.PSU__USE__M_AXI_GP1 {0}",
        "CONFIG.PSU__USE__M_AXI_GP2 {0}",
        "CONFIG.PSU__FPGA_PL0_ENABLE {0}",
        # TTC'ler HER ZAMAN açık (SAHA BULGUSU 2026-07-08): FreeRTOS BSP'si
        # tick için psu_ttc_0 ister; TTC'siz XSA'da workspace kurulumu
        # "FreeRTOS requires valid ticker timer" ile düşer. TTC'ler dahili
        # (PERIPHERAL__IO = NA, MIO harcamaz); dördü de zcu102 gibi açılır.
        "CONFIG.PSU__TTC0__PERIPHERAL__ENABLE {1}",
        "CONFIG.PSU__TTC1__PERIPHERAL__ENABLE {1}",
        "CONFIG.PSU__TTC2__PERIPHERAL__ENABLE {1}",
        "CONFIG.PSU__TTC3__PERIPHERAL__ENABLE {1}",
    ])
    lines = [f"set_property -dict [list {' '.join(pairs)}] $spec2code_ps\n"]

    # Kullanıcının MIO verdiği birimler ÖNCE enable edilir (kendi pinlerini
    # sabitler); kalanlar geniş-blok önceliğiyle TEK TEK enable edilip
    # yerleşimi Vivado'ya bırakılır (çakışmasız).
    manual = [per for per in cfg.peripherals if per.mio.strip()]
    auto = sorted(
        (per for per in cfg.peripherals if not per.mio.strip()),
        key=lambda per: (_zynqmp_auto_rank(per.kind), per.kind),
    )
    for per in manual + auto:
        root = _ZYNQMP_PERIPHERALS[per.kind]
        if per.kind == "qspi":
            # QSPI ozel: mod IO'yu belirler (Single=0..5, Dual Parallel=0..12,
            # zcu102'den dogrulandi); mod/data/FBCLK tek dict'te uygulanir.
            mode = per.qspi_mode or "Single"
            io = _tcl_brace(_QSPI_MODES[mode])
            data = _tcl_brace(per.qspi_data_mode) if per.qspi_data_mode else "{}"
            fbclk = "1" if per.qspi_fbclk else "0"
            lines.append(
                f"spec2codeAssignQspi $spec2code_ps {io} {_tcl_brace(mode)} {data} {fbclk}\n"
            )
            continue
        requested = _tcl_brace(per.mio.strip()) if per.mio.strip() else "{}"
        lines.append(
            f"spec2codeAssignPeripheral $spec2code_ps {root}__PERIPHERAL__ENABLE "
            f"{root}__PERIPHERAL__IO {requested} {per.kind}\n"
        )
        if per.kind.startswith("gem"):
            # RGMII MDIO ayrı MIO çiftidir; ana IO'dan sonra aynı düzenekle
            # çakışmasız atanır (zcu102 düzeninde 76..77).
            lines.append(
                f"spec2codeAssignPeripheral $spec2code_ps {root}__GRP_MDIO__ENABLE "
                f"{root}__GRP_MDIO__IO {{}} {per.kind}_mdio\n"
            )
    return "".join(lines)


def _versal_cips_config_tcl(cfg: VivadoDesignConfig) -> str:
    entries: list[str] = []
    for per in cfg.peripherals:
        key = _VERSAL_PERIPHERALS[per.kind]
        io = per.mio.strip() or ""
        if io:
            entries.append(f"{key} {{{{ENABLE 1}} {{IO {{{io}}}}}}}")
        else:
            entries.append(f"{key} {{{{ENABLE 1}}}}")
    if cfg.ref_clk_mhz:
        entries.append(f"PMC_REF_CLK_FREQMHZ {cfg.ref_clk_mhz}")
    # TTC'ler her zaman açık: FreeRTOS tick zamanlayıcısı ister (adlar
    # vck190 PS_PMC_CONFIG'ten doğrulandı; dahili, MIO harcamaz).
    for index in range(4):
        entries.append(f"PS_TTC{index}_PERIPHERAL_ENABLE 1")
    joined = " ".join(entries)
    return (
        "set_property -dict [list CONFIG.PS_PMC_CONFIG "
        f"{{{joined}}}"
        "] $spec2code_ps\n"
    )


def _regmap_test_ip_tcl(staging: Path, ps_inst: str) -> list[str]:
    """Register Map Test IP (AXI4-Lite) BD adımları — YALNIZ ZynqMP. PS'te bir
    master AXI (M_AXI_HPM0_FPD) + PL fabrik saati (pl_clk0) açar; custom RTL'i
    (spec2code_regmap_test.v, staging'e kopyalanır) BD'ye modül olarak koyar;
    apply_bd_automation ile AXI'yi bağlar (SmartConnect + proc_sys_reset + saat);
    adres atar ve atanan tabanı `regmap_ip_base=` işaretiyle bildirir."""
    rtl = staging / "spec2code_regmap_test.v"
    axi_cfg = (
        "{ Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} "
        f"Master {{/{ps_inst}/M_AXI_HPM0_FPD}} "
        "Slave {/regmap_test_0/s_axi} intc_ip {New AXI SmartConnect} master_apm {0} }"
    )
    return [
        _marker("stage=regmap_ip"),
        # PS'te bir master AXI (HPM0 FPD) + PL saati (pl_clk0, 100 MHz).
        "set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 {1} "
        "CONFIG.PSU__FPGA_PL0_ENABLE {1} "
        "CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $spec2code_ps\n",
        # Custom RTL'i projeye ekle, BD'ye modül referansı olarak koy.
        f"add_files -norecurse {_tcl_path(rtl)}\n",
        "update_compile_order -fileset sources_1\n",
        "create_bd_cell -type module -reference spec2code_regmap_test regmap_test_0\n",
        # AXI master -> slave otomasyonu (arayüz s_axi_* port adlarından çıkarılır).
        f"apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {axi_cfg} "
        "[get_bd_intf_pins regmap_test_0/s_axi]\n",
        "assign_bd_address\n",
        # Atanan taban adres XSA'nın hwh adres haritasından (BASEVALUE) okunur —
        # sürümden bağımsız ve xparameters.h ile birebir. Tcl adres sorgusu
        # sürüme göre kaygan olduğundan tercih edilmez.
    ]


def _regmap_ip_base_from_xsa(xsa_path: str, instance: str = "regmap_test_0") -> str:
    """XSA (zip) içindeki design hwh'sinden Register Map Test IP'nin atanmış taban
    adresini (MEMRANGE BASEVALUE) okur. Bu değer Vitis'in xparameters.h'da
    ``XPAR_<instance>_BASEADDR`` olarak yazdığı adresle birebir aynıdır."""
    try:
        import zipfile

        with zipfile.ZipFile(xsa_path) as archive:
            hwh_name = next(
                (n for n in archive.namelist()
                 if n.endswith(".hwh") and "smc" not in n.lower() and "smartconnect" not in n.lower()),
                None,
            )
            if hwh_name is None:
                return ""
            text = archive.read(hwh_name).decode("utf-8", "replace")
    except (OSError, KeyError):
        return ""
    inst = re.escape(instance)
    for pattern in (
        r'<MEMRANGE[^>]*INSTANCE="' + inst + r'"[^>]*BASEVALUE="(0x[0-9A-Fa-f]+)"',
        r'<MEMRANGE[^>]*BASEVALUE="(0x[0-9A-Fa-f]+)"[^>]*INSTANCE="' + inst + r'"',
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def design_tcl(cfg: VivadoDesignConfig, staging: Path) -> str:
    """Deterministic batch-Tcl: proje → BD → PS → validate → wrapper →
    aşama 1 XSA → (istenirse) synth/impl → bit/pdi → bit'li XSA."""
    proj_dir = staging / "vivado_proj"
    xsa_out = staging / f"{cfg.design_name}.xsa"
    xsa_bit_out = staging / f"{cfg.design_name}_bit.xsa"
    is_versal = cfg.platform == "versal"
    ps_vlnv = "xilinx.com:ip:versal_cips" if is_versal else "xilinx.com:ip:zynq_ultra_ps_e"
    ps_inst = "versal_cips_0" if is_versal else "zynq_ultra_ps_e_0"
    ps_config = _versal_cips_config_tcl(cfg) if is_versal else _zynqmp_ps_config_tcl(cfg)
    impl_step = "write_device_image" if is_versal else "write_bitstream"
    image_ext = "pdi" if is_versal else "bit"

    lines = [
        "# Spec2Code tarafindan uretildi - Vivado batch tasarim akisi.\n",
        "" if is_versal else _ZYNQMP_IO_HELPERS_TCL,
        _marker("stage=create_project"),
        f"create_project spec2code_design {_tcl_path(proj_dir)} -part {cfg.part.strip()} -force\n",
        _marker("stage=block_design"),
        "create_bd_design \"design_1\"\n",
        f"set spec2code_ps [create_bd_cell -type ip -vlnv {ps_vlnv} {ps_inst}]\n",
        _marker("stage=ps_config"),
        ps_config,
        *(_regmap_test_ip_tcl(staging, ps_inst) if cfg.add_regmap_test_ip else []),
        _marker("stage=validate"),
        "validate_bd_design\n",
        "save_bd_design\n",
        _marker("stage=wrapper"),
        "set spec2code_wrapper [make_wrapper -files [get_files design_1.bd] -top]\n",
        "add_files -norecurse $spec2code_wrapper\n",
        "set_property top design_1_wrapper [current_fileset]\n",
        "update_compile_order -fileset sources_1\n",
        _marker("stage=generate_targets"),
        # BD cikti urunleri (hwh dahil) uretilmeden write_hw_platform
        # "Block Diagram is not generated" hatasi verir (E2E'de dogrulandi).
        "generate_target all [get_files design_1.bd]\n",
        _marker("stage=xsa"),
        # Asama 1: sentezsiz XSA. PS-only tasarimda tam donanim tarifi icerir;
        # Vitis platform/BSP bu dosyadan kurulur. E2E'de dogrulanan iki Vivado
        # 2023.2 gereksinimi: (a) platform.name/board_id proje ozellikleri
        # zorunlu, (b) -fixed olmadan write_hw_platform UZATILABILIR platform
        # yazmaya kalkar ve PFM/hpfm metadata ister ("Unable to get hpfm
        # file") - klasik Export Hardware karsiligi fixed'dir.
        f"set_property platform.name {cfg.design_name} [current_project]\n",
        f"set_property platform.board_id {cfg.design_name} [current_project]\n",
        f"write_hw_platform -fixed -force -file {_tcl_path(xsa_out)}\n",
        _marker(f"xsa_ready={_fs(xsa_out)}"),
    ]
    if cfg.make_bitstream:
        impl_products = proj_dir / "spec2code_design.runs" / "impl_1"
        image_src = impl_products / f"design_1_wrapper.{image_ext}"
        image_out = staging / f"{cfg.design_name}.{image_ext}"
        lines.extend([
            _marker("stage=synth"),
            "launch_runs synth_1 -jobs 4\n",
            "wait_on_run synth_1\n",
            "if {[get_property PROGRESS [get_runs synth_1]] ne \"100%\"} {\n",
            "    error \"Spec2Code: synthesis tamamlanamadi - [get_property STATUS [get_runs synth_1]]\"\n",
            "}\n",
            _marker("stage=impl"),
            f"launch_runs impl_1 -to_step {impl_step} -jobs 4\n",
            "wait_on_run impl_1\n",
            "if {[get_property PROGRESS [get_runs impl_1]] ne \"100%\"} {\n",
            "    error \"Spec2Code: implementation tamamlanamadi - [get_property STATUS [get_runs impl_1]]\"\n",
            "}\n",
            f"file copy -force {_tcl_path(image_src)} {_tcl_path(image_out)}\n",
            _marker(f"bit_ready={_fs(image_out)}"),
            _marker("stage=xsa_bit"),
            f"write_hw_platform -fixed -include_bit -force -file {_tcl_path(xsa_bit_out)}\n",
            _marker(f"xsa_bit_ready={_fs(xsa_bit_out)}"),
        ])
    lines.extend([
        _marker("stage=done"),
        "exit\n",
    ])
    return "".join(lines)


def vivado_bat(vivado_path: str) -> Path:
    root = Path(vivado_path.strip().strip('"'))
    for candidate in (root / "bin" / "vivado.bat", root / "vivado.bat"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"vivado.bat bulunamadı: {root} (beklenen: <Vivado dizini>\\bin\\vivado.bat)")


@dataclass
class VivadoDesignJob:
    id: str
    config: VivadoDesignConfig
    status: str = "pending"            # pending | running | done | error
    events: list[dict] = field(default_factory=list)
    subscribers: set = field(default_factory=set)
    result: Optional[dict] = None
    error: Optional[str] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, event: dict) -> None:
        event = {**event, "_seq": len(self.events)}
        self.events.append(event)
        loop = self._loop
        if loop is None:
            return
        for queue in list(self.subscribers):
            loop.call_soon_threadsafe(queue.put_nowait, event)


#: Aşama işaretleri -> kullanıcıya dost ilerleme. Sentez/impl süresi tasarıma
#: göre değiştiğinden yüzdeler kaba niyet göstergesidir.
_STAGE_PROGRESS = {
    "create_project": 10,
    "block_design": 20,
    "ps_config": 30,
    "regmap_ip": 35,
    "validate": 40,
    "wrapper": 45,
    "generate_targets": 50,
    "xsa": 60,
    "synth": 70,
    "impl": 85,
    "xsa_bit": 95,
    "done": 100,
}

_STAGE_LABELS = {
    "create_project": "Vivado projesi oluşturuluyor",
    "block_design": "Blok tasarım kuruluyor",
    "ps_config": "PS yapılandırılıyor",
    "regmap_ip": "Register Map Test IP ekleniyor (AXI4-Lite + adres atama)",
    "validate": "Tasarım doğrulanıyor (validate_bd_design)",
    "wrapper": "HDL wrapper üretiliyor",
    "generate_targets": "Blok tasarım çıktı ürünleri üretiliyor",
    "xsa": "Aşama 1: sentezsiz XSA yazılıyor",
    "synth": "Aşama 2: sentez koşuyor (süre tasarıma bağlı)",
    "impl": "Aşama 2: implementasyon + bit/pdi üretimi",
    "xsa_bit": "Bit'li sabit XSA yazılıyor",
    "done": "Vivado akışı tamamlandı",
}


class VivadoDesignJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, VivadoDesignJob] = {}
        self._counter = 0
        self._lock = threading.Lock()

    def get(self, job_id: str) -> Optional[VivadoDesignJob]:
        return self._jobs.get(job_id)

    async def start(self, config: VivadoDesignConfig) -> str:
        errors = validate_design(config)
        if errors:
            raise ValueError("; ".join(errors))
        vivado_bat(config.vivado_path)  # erken, net hata
        with self._lock:
            self._counter += 1
            job_id = f"vivado_{self._counter:04d}"
        job = VivadoDesignJob(id=job_id, config=config, _loop=asyncio.get_running_loop())
        self._jobs[job_id] = job
        asyncio.create_task(self._run(job))
        return job_id

    async def _run(self, job: VivadoDesignJob) -> None:
        job.status = "running"
        job.emit({
            "event": "vivado.start", "stage": "start", "progress": 5,
            "message": (
                "Vivado tasarım akışı başladı: aşama 1 sentezsiz XSA"
                + (", aşama 2 bit/pdi" if job.config.make_bitstream else " (bit istenmedi)")
            ),
        })
        try:
            await asyncio.to_thread(self._blocking, job)
            job.status = "done"
        except Exception as exc:  # noqa: BLE001 - Vivado/host hatası doğrudan raporlanır
            job.status = "error"
            job.error = str(exc)
            job.emit({
                "event": "vivado.error", "stage": "error", "progress": 100,
                "message": str(exc),
                "trace": traceback.format_exc().splitlines()[-5:],
            })
        finally:
            final_stage = "done" if job.status == "done" else "error"
            job.emit({"event": "vivado.end", "stage": final_stage, "progress": 100, "status": job.status})
            loop = job._loop
            if loop is not None:
                for queue in list(job.subscribers):
                    loop.call_soon_threadsafe(queue.put_nowait, None)

    def _blocking(self, job: VivadoDesignJob) -> None:
        cfg = job.config
        staging = Path(cfg.temp_path.strip().strip('"')) / f"s2c_{job.id}"
        # Vivado, Windows'ta 260 baytlik yol sinirini KENDISI uygular ve IP
        # dosyalarini derin klasorlere yazar (saha bulgusu: uzun staging'de
        # save_bd_design "Path length exceeds 260-Byte maximum" ile dustu).
        # Proje agacinin en derin dosyasi ~130 karakter ekliyor.
        if len(str(staging)) > 100:
            raise RuntimeError(
                f"Staging yolu çok uzun ({len(str(staging))} karakter): {staging}\n"
                "Vivado Windows'ta 260 karakter yol sınırı uygular ve proje "
                "ağacı derin klasörler açar. Kısa bir Temp dizini verin "
                "(örn. D:\\VivadoTemp).")
        staging.mkdir(parents=True, exist_ok=True)
        # Register Map Test IP RTL'i staging'e kopyala (Tcl oradan add_files eder).
        if cfg.add_regmap_test_ip:
            src_v = Path(__file__).with_name("data") / "spec2code_regmap_test.v"
            shutil.copy2(src_v, staging / "spec2code_regmap_test.v")
        tcl_path = staging / "spec2code_design.tcl"
        tcl_path.write_text(design_tcl(cfg, staging), encoding="utf-8")
        bat = vivado_bat(cfg.vivado_path)
        log_path = staging / "vivado_stdout.log"

        result: dict = {
            "successful": False,
            "staging": str(staging),
            "tcl": str(tcl_path),
            "xsa_path": "",
            "xsa_bit_path": "",
            "image_path": "",
            "platform": cfg.platform,
            "part": cfg.part,
        }
        job.result = result

        cmd = [str(bat), "-mode", "batch", "-nojournal",
               "-log", str(staging / "vivado.log"), "-source", str(tcl_path)]
        job.emit({"event": "vivado.log", "line": "$ " + " ".join(cmd)})
        proc = subprocess.Popen(
            cmd, cwd=str(staging),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        assert proc.stdout is not None
        with open(log_path, "w", encoding="utf-8", errors="replace", newline="") as handle:
            try:
                for line in iter(proc.stdout.readline, ""):
                    handle.write(line)
                    handle.flush()
                    text = line.rstrip("\r\n")
                    # Yalnız satır başında başlayan işaret gerçek puts
                    # çıktısıdır; Vivado'nun komut EKOSU (`# puts "S2C-..."`)
                    # işaret değildir ve olay akışına da girmez.
                    if text.startswith("S2C-VIVADO|"):
                        self._handle_marker(job, result, text[len("S2C-VIVADO|"):])
                        continue
                    if "S2C-VIVADO|" in text:
                        continue
                    # Vivado cok konusur: tum satirlar log dosyasinda; olay
                    # akisina hata/uyari ve onemli satirlar gider.
                    if re.match(r"^(ERROR|CRITICAL WARNING|WARNING: \[(?:BD|Common) )", text):
                        job.emit({"event": "vivado.log", "line": text})
                    elif text.startswith(("#", "****", "INFO: [Common 17-206]")):
                        pass
                    elif re.match(r"^(source |Command: |launch_runs |wait_on_run )", text):
                        job.emit({"event": "vivado.log", "line": text})
                exit_code = proc.wait(timeout=cfg.timeout_s)
            finally:
                if proc.poll() is None:
                    proc.kill()

        if exit_code != 0:
            tail = _log_tail(log_path)
            raise RuntimeError(
                f"Vivado {exit_code} koduyla çıktı. Son satırlar:\n{tail}\n"
                f"Tam log: {log_path}")
        if not result["xsa_path"]:
            raise RuntimeError(
                f"Vivado bitti ama XSA üretilmedi (xsa_ready işareti görülmedi). Log: {log_path}")
        if cfg.make_bitstream and not result["image_path"]:
            raise RuntimeError(
                f"Aşama 2 istendi ama bit/pdi üretilmedi. Log: {log_path}")
        # Register Map Test IP adresini XSA'dan (hwh BASEVALUE) oku — authoritative,
        # xparameters.h ile birebir. UI Register Map'e bu adresle içe aktarır.
        if cfg.add_regmap_test_ip and result["xsa_path"]:
            base = _regmap_ip_base_from_xsa(result["xsa_path"])
            if base:
                result["regmap_ip_base"] = base
                job.emit({"event": "vivado.regmap_ip", "stage": "xsa", "progress": 62,
                          "message": f"Register Map Test IP adresi (XSA): {base}",
                          "regmap_ip_base": base})
        result["successful"] = True

    def _handle_marker(self, job: VivadoDesignJob, result: dict, payload: str) -> None:
        if payload.startswith("stage="):
            stage = payload[len("stage="):]
            job.emit({
                "event": "vivado.stage", "stage": stage,
                "progress": _STAGE_PROGRESS.get(stage, 50),
                "message": _STAGE_LABELS.get(stage, stage),
            })
        elif payload.startswith("io_assigned="):
            rest = payload[len("io_assigned="):]
            label, _, value = rest.partition("|")
            result.setdefault("io_assignments", {})[label] = value
            job.emit({"event": "vivado.log", "line": f"MIO atandı: {label} -> {value}"})
        elif payload.startswith("regmap_ip_base="):
            base = payload[len("regmap_ip_base="):].strip()
            result["regmap_ip_base"] = base
            job.emit({"event": "vivado.regmap_ip", "stage": "regmap_ip", "progress": 38,
                      "message": f"Register Map Test IP adresi atandı: {base}", "regmap_ip_base": base})
        elif payload.startswith("xsa_ready="):
            path = payload[len("xsa_ready="):]
            result["xsa_path"] = path
            job.emit({
                "event": "vivado.xsa_ready", "stage": "xsa", "progress": 60,
                "message": "Sentezsiz XSA hazır — Setup'a bağlanabilir.",
                "xsa_path": path,
            })
        elif payload.startswith("bit_ready="):
            path = payload[len("bit_ready="):]
            result["image_path"] = path
            job.emit({
                "event": "vivado.bit_ready", "stage": "impl", "progress": 90,
                "message": "Programlama imajı hazır.", "image_path": path,
            })
        elif payload.startswith("xsa_bit_ready="):
            path = payload[len("xsa_bit_ready="):]
            result["xsa_bit_path"] = path
            job.emit({
                "event": "vivado.xsa_bit_ready", "stage": "xsa_bit", "progress": 95,
                "message": "Bit'li sabit XSA hazır.", "xsa_bit_path": path,
            })


def _log_tail(log_path: Path, lines: int = 12) -> str:
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(log okunamadı)"
    return "\n".join(content[-lines:])


#: ZynqMP MIO seçenek tablosu (backend/data/zynqmp_mio_options.json): her PS
#: çevre biriminin Vivado'nun kabul ettiği geçerli MIO konumları. UYDURMA
#: DEĞİL — kurulu Vivado 2023.2'de kabul-testi taramasıyla üretildi
#: (peripheral enable → her MIO konumunu dene → kabul edilenleri topla).
#: MIO düzeni ZynqMP ailesinde sabit silikon olduğundan part-bağımsızdır;
#: yine de nihai geçerlilik üretimde Vivado'ya aittir. QSPI özel modludur
#: (x1: MIO 0..5, x4: MIO 0..12) ve DATA_MODE'a bağlı olduğundan bu tabloda
#: iki bilinen değeriyle verilir.
_MIO_OPTIONS_PATH = Path(__file__).with_name("data") / "zynqmp_mio_options.json"
_QSPI_MIO_OPTIONS = {"width": 6, "default": "MIO 0 .. 5",
                     "options": ["MIO 0 .. 5", "MIO 0 .. 12"]}


def zynqmp_mio_options() -> dict:
    """Peripheral -> {width, default, options} (ZynqMP). Dosya yoksa boş."""
    try:
        raw = json.loads(_MIO_OPTIONS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    peripherals = dict(raw.get("peripherals", {}))
    peripherals.setdefault("qspi", _QSPI_MIO_OPTIONS)
    return peripherals


#: DDR model havuzu (backend/data/zynqmp_ddr_parts.json). UYDURMA DEĞİL:
#: adres geometrisi Xilinx'in resmi DDR4 kataloğundan (mem_v1_4 memparts.csv),
#: zamanlamalar ise HİÇ saklanmaz — SPEED_BIN verilince PCW kendisi hesaplar
#: (probe ile kanıtlandı: DDR4_2400R → CL16/CWL12/tRC45.32/tFAW30, x16'ya
#: göre doğru). Böylece CL/tRCD gibi değerler elle taşınmaz.
_DDR_PARTS_PATH = Path(__file__).with_name("data") / "zynqmp_ddr_parts.json"


def zynqmp_ddr_parts() -> list[dict]:
    try:
        raw = json.loads(_DDR_PARTS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return list(raw.get("parts", []))




def _ddr_part_by_id(part_id: str) -> dict | None:
    for entry in zynqmp_ddr_parts():
        if entry.get("id") == part_id:
            return entry
    return None


def _platform_of_family(family: str) -> str | None:
    """Vivado FAMILY -> Spec2Code platform. Aile adı Vivado'nun kendi
    sınıflandırmasıdır (zynquplus, zynquplusRFSOC, versalaicore,
    versalprime, ...) — önek tahmini yapılmaz."""
    lowered = family.lower()
    if "zynquplus" in lowered:
        return "zynq_ultrascale"
    if lowered.startswith("versal"):
        return "versal"
    return None


def group_parts(lines: list[str]) -> dict[str, dict[str, list[str]]]:
    """S2C-PART|<family>|<part> satırlarını platform -> cihaz -> tam parça
    listesi olarak gruplar (cihaz = parçanın ilk '-' öncesi, ör. xczu9eg)."""
    grouped: dict[str, dict[str, list[str]]] = {"zynq_ultrascale": {}, "versal": {}}
    for line in lines:
        if not line.startswith("S2C-PART|"):
            continue
        try:
            _tag, family, part = line.strip().split("|", 2)
        except ValueError:
            continue
        platform = _platform_of_family(family)
        if platform is None or not part:
            continue
        device = part.split("-", 1)[0]
        grouped[platform].setdefault(device, [])
        if part not in grouped[platform][device]:
            grouped[platform][device].append(part)
    for devices in grouped.values():
        for parts in devices.values():
            parts.sort()
    return grouped


def list_parts(vivado_path: str, cache_dir: Path, *, refresh: bool = False,
               cached_only: bool = False, timeout_s: int = 420) -> dict:
    """Kurulu Vivado'nun TAM parça listesi (get_parts) — tek gerçek kaynak.

    İlk çağrı Vivado'yu batch açar (~1 dk) ve sonucu önbelleğe yazar;
    sonraki çağrılar anında döner. Parçalar el ile YAZILMAZ: liste,
    kullanıcının kurulumunda gerçekten hedeflenebilen parçalardır.
    """
    bat = vivado_bat(vivado_path)
    cache_key = re.sub(r"[^A-Za-z0-9]+", "_", str(bat.parent.parent)).strip("_")
    cache_file = cache_dir / f"vivado_parts_{cache_key}.json"
    if not refresh and cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            if cached.get("platforms"):
                return {**cached, "cached": True}
        except (OSError, ValueError):
            pass
    if cached_only:
        # Önbellek yok: Vivado'yu ARKA PLANDA açmadan hızlı cevap — UI
        # "listeyi getir" düğmesini gösterir.
        return {"platforms": None, "cached": False, "total": 0}

    with tempfile.TemporaryDirectory(prefix="s2c_parts_") as tmp:
        tcl_path = Path(tmp) / "list_parts.tcl"
        tcl_path.write_text(
            "foreach spec2code_part [get_parts] {\n"
            "    puts \"S2C-PART|[get_property FAMILY $spec2code_part]|$spec2code_part\"\n"
            "}\n"
            "exit\n",
            encoding="utf-8",
        )
        proc = subprocess.run(
            [str(bat), "-mode", "batch", "-nojournal", "-nolog",
             "-source", str(tcl_path)],
            cwd=tmp, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout_s,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    if proc.returncode != 0:
        tail = "\n".join((proc.stdout or "").splitlines()[-8:])
        raise RuntimeError(f"Vivado get_parts başarısız (kod {proc.returncode}). Son satırlar:\n{tail}")
    platforms = group_parts((proc.stdout or "").splitlines())
    total = sum(len(parts) for devices in platforms.values() for parts in devices.values())
    if total == 0:
        raise RuntimeError("Vivado get_parts çıktısında ZynqMP/Versal parçası bulunamadı.")
    payload = {
        "platforms": platforms,
        "total": total,
        "generated_at": int(time.time()),
        "vivado_path": vivado_path,
    }
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload), encoding="utf-8")
    return {**payload, "cached": False}


vivado_manager = VivadoDesignJobManager()
