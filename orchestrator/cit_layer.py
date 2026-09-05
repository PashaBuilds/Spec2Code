"""CIT entegre katmani: portlanabilir HAL (I2C/SPI sarmalayici) + entegre CIT dosyalari.

Tasarim: docs/superpowers/specs/2026-09-05-cit-hal-layer-design.md

Uretilen agac (``outputs/<proje>/cit/``) mevcut ``drivers/`` ve ``tests/``
ciktilarina DOKUNMADAN eklenir; kullanici bu klasoru oldugu gibi kendi gomulu
yazilimina tasiyabilir:

* ``hal/spec2code_cit_port.h``  - platform secimi (``#ifndef`` korumali makrolar,
  ``-D`` ile ezilebilir) + katman durum kodlari.
* ``hal/spec2code_i2c_bus.*``   - ``SSpec2codeI2cBus``: XIicPs / XIic / kullanici portu.
* ``hal/spec2code_spi_bus.*``   - ``SSpec2codeSpiBus``: XSpiPs / XSpi / kullanici portu.
* ``<mod>_cit.*``               - entegre basina ``S<Mod>CitConfig`` (calisma zamaninda
  degistirilebilir adres/mux/timeout), ``S<Mod>Cit`` (durum register bitleri BIT BIT,
  olcumler bayt/kelime), ``<mod>CitInit`` ve ``<mod>CitRead``.
* ``spec2code_cit_sistem.*``    - ``SSistemCitBus`` + ``SSistemCit`` + ``sistemCitInit`` /
  ``sistemCitRead`` (butun entegreleri tek atimda gezer).

Kapsam: I2C register cihazlari ve SPI TICS-register cihazlari. GPIO hat cihazlari,
komut tabanli SPI flash ve I2C EEPROM icin CIT dosyasi uretilmez (README'de yazar).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from hostplat import io as hio
from orchestrator import cmodel, tics
from orchestrator.device_profiles import registry as device_profiles

_IND = "    "

#: Bir HAL yazma/okuma cagrisinda kopyalanan azami bayt (register erisimleri <= 4).
I2C_TX_MAX = 16
SPI_FRAME_MAX = 8

STATUS_OK = "SPEC2CODE_CIT_OK"
STATUS_FAIL = "SPEC2CODE_CIT_HATA"
STATUS_TIMEOUT = "SPEC2CODE_CIT_ZAMAN_ASIMI"
STATUS_PARAM = "SPEC2CODE_CIT_PARAMETRE"
STATUS_UNSUPPORTED = "SPEC2CODE_CIT_DESTEK_YOK"


# --- kucuk yardimcilar ------------------------------------------------------------------

def _pascal(text: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", str(text)) if p]
    out = "".join(p[:1].upper() + p[1:].lower() for p in parts)
    if out and not out[0].isalpha():
        out = "X" + out
    return out or "X"


def _camel(text: str) -> str:
    p = _pascal(text)
    return p[:1].lower() + p[1:]


def _bits_range(bits) -> Optional[tuple[int, int]]:
    """'7:4' -> (7, 4); '0' -> (0, 0); cozulemeyen -> None."""
    text = str(bits).strip()
    m = re.fullmatch(r"(\d+)\s*:\s*(\d+)", text)
    if m:
        hi, lo = int(m.group(1)), int(m.group(2))
        return (max(hi, lo), min(hi, lo))
    if re.fullmatch(r"\d+", text):
        return (int(text), int(text))
    return None


def _hex(value: int, width: int = 8) -> str:
    digits = max(2, (width + 3) // 4)
    return f"0x{value:0{digits}X}U"


class _E:
    """Girintili C satir yayicisi (cit katmani durum kodlariyla)."""

    def __init__(self, level: int = 1) -> None:
        self.lines: list[str] = []
        self.level = level

    def ln(self, text: str = "") -> "_E":
        self.lines.append((_IND * self.level + text) if text else "")
        return self

    def open(self, header: str) -> "_E":
        self.ln(header).ln("{")
        self.level += 1
        return self

    def close(self, suffix: str = "") -> "_E":
        self.level -= 1
        return self.ln("}" + suffix)

    def check(self, var: str = "iStatus") -> "_E":
        return self.open(f"if ({var} != {STATUS_OK})").ln(f"return {var};").close()

    def blank(self) -> "_E":
        self.lines.append("")
        return self

    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class _BitField:
    cname: str
    width: int
    comment: str


@dataclass
class _StatusReg:
    name: str          # descriptor register name
    offset: int
    width: int         # 8 / 16
    raw_field: str     # ucStatusHigh / usR74
    ok_bit: str        # uiStatusHighOk
    fields: list[tuple[str, int, int]]  # (cname, lo, width)


@dataclass
class _Measure:
    op: dict
    name: str          # op name
    ok_bit: str
    c_type: str        # unsigned short / int / ...
    field: str         # usArrVoltageRead / iTemperatureRead
    count: int         # >1 -> dizi
    unit: str
    convert: Optional[dict]
    func: str          # static helper name


@dataclass
class _ChipPlan:
    device: dict
    descriptor: dict
    controller: dict
    module: str
    part: str
    transport: str     # i2c / spi
    status_regs: list[_StatusReg] = field(default_factory=list)
    measures: list[_Measure] = field(default_factory=list)
    skipped_ops: list[str] = field(default_factory=list)
    mux_addr: int = 0
    mux_channel: int = 0
    i2c_addr: int = 0
    spi_select: int = 0

    @property
    def mod(self) -> str:
        return self.module.upper()

    @property
    def pascal(self) -> str:
        return _pascal(self.module)


def bitfield_bytes(widths: list[int]) -> int:
    """GCC ``unsigned int`` bit alani yerlesimi: 32-bit birim, sigmayan alan sonraki birime.

    Sifir alan -> 0 bayt (struct bos olamaz; cagiran en az bir bit garanti eder).
    """
    if not widths:
        return 0
    units = 1
    used = 0
    for w in widths:
        if used + w > 32:
            units += 1
            used = 0
        used += w
    return units * 4


# --- plan kurma -------------------------------------------------------------------------

def _post_init_reg(descriptor: dict) -> str:
    hint = (descriptor.get("test_hints") or {}).get("post_init_status") or {}
    return str(hint.get("reg", "") or "")


def _status_registers(plan: _ChipPlan, used_names: set[str]) -> list[_StatusReg]:
    post = _post_init_reg(plan.descriptor)
    regs: list[_StatusReg] = []
    for rg in plan.descriptor.get("registers", []):
        name = str(rg.get("name", ""))
        width = int(rg.get("width", 8) or 8)
        access = str(rg.get("access", "")).lower()
        if not name or width > 16 or not rg.get("fields"):
            continue
        if not (access == "ro" or name == post):
            continue
        fields: list[tuple[str, int, int]] = []
        for f in rg["fields"]:
            rng = _bits_range(f.get("bits"))
            fname = str(f.get("name", ""))
            if rng is None or not fname or rng[0] >= width:
                continue
            cname = "ui" + _pascal(fname)
            if cname in used_names:
                cname = "ui" + _pascal(name) + _pascal(fname)
            used_names.add(cname)
            fields.append((cname, rng[1], rng[0] - rng[1] + 1))
        if not fields:
            continue
        prefix = "uc" if width <= 8 else "us"
        # Register adi ile op adi cakisabilir (SHT21: USER_REGISTER_READ registeri +
        # user_register_read op'u) - ok biti ve ham alan adlari da rezerve edilir.
        used_names.add(f"ui{_pascal(name)}Ok")
        used_names.add(f"{prefix}{_pascal(name)}")
        regs.append(_StatusReg(
            name=name, offset=int(rg.get("offset", 0)), width=width,
            raw_field=f"{prefix}{_pascal(name)}", ok_bit=f"ui{_pascal(name)}Ok", fields=fields))
    return regs


def _value_type(returns: str) -> tuple[str, str, int]:
    """returns -> (C tipi, onek, adet). 'voltages[8]' -> ('unsigned short', 'us', 8)."""
    ret = returns.lower()
    count = 1
    m = re.search(r"\[(\d+)\]", ret)
    if m:
        count = int(m.group(1))
    if "uint8" in ret:
        return "unsigned char", "uc", count
    if "uint32" in ret:
        return "unsigned int", "ui", count
    if "int32" in ret:
        return "int", "i", count
    return "unsigned short", "us", count


_I2C_STEP_OPS = {"comment", "poll", "read_register", "read_registers", "read_channels"}
_SPI_STEP_OPS = {"comment", "read_register"}


def _measures(plan: _ChipPlan, manifest_ops: list[dict], used_names: set[str]) -> None:
    ops_by_name = {op["name"]: op for op in plan.descriptor.get("operations", [])}
    allowed = _I2C_STEP_OPS if plan.transport == "i2c" else _SPI_STEP_OPS
    for mop in manifest_ops:
        name = str(mop.get("name", ""))
        op = ops_by_name.get(name)
        if op is None or not mop.get("result_returns") or mop.get("risk") != "safe":
            continue
        if mop.get("requires_address") or mop.get("requires_data") or mop.get("requires_value") \
                or mop.get("requires_register"):
            continue
        steps = op.get("steps", [])
        if any(s.get("op") not in allowed for s in steps):
            plan.skipped_ops.append(name)
            continue
        # Hic okuma adimi olmayan bir op deger uretemez (yalniz comment/poll):
        # bos bir olcum alani ve -Wunused-variable yerine atlanir.
        if not any(s.get("op") in {"read_register", "read_registers", "read_channels"} for s in steps):
            plan.skipped_ops.append(name)
            continue
        if plan.transport == "spi" and "[" in str(op.get("returns", "")):
            plan.skipped_ops.append(name)
            continue
        if not cmodel._check_convert_config(plan.device, name, op):
            plan.skipped_ops.append(name)
            continue
        c_type, prefix, count = _value_type(str(op.get("returns", "")))
        pas = _pascal(name)
        fname = f"{prefix}Arr{pas}" if count > 1 else f"{prefix}{pas}"
        ok = f"ui{pas}Ok"
        if ok in used_names or fname in used_names:
            # Ayni adli durum registeri var: olcum alanlari "Olcum" sonekiyle ayrilir.
            pas = f"{pas}Olcum"
            fname = f"{prefix}Arr{pas}" if count > 1 else f"{prefix}{pas}"
            ok = f"ui{pas}Ok"
        used_names.add(ok)
        used_names.add(fname)
        plan.measures.append(_Measure(
            op=op, name=name, ok_bit=ok, c_type=c_type, field=fname, count=count,
            unit=str(mop.get("result_unit") or ""), convert=cmodel.resolve_convert(plan.device, op),
            func=f"{plan.module}Cit{pas}"))


def build_plans(spec: dict, get_descriptor: Callable[[str], dict],
                manifest_devices: list[dict]) -> list[_ChipPlan]:
    controllers = {c["id"]: c for c in spec.get("controllers", [])}
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    modules = cmodel.device_module_map(spec)
    manifest_by_id = {d.get("id", ""): d for d in manifest_devices}
    plans: list[_ChipPlan] = []
    for device in spec.get("devices", []):
        descriptor = get_descriptor(device.get("descriptor_ref") or device["part"])
        transport = str(descriptor.get("transport", {}).get("type", ""))
        if transport == "i2c" and descriptor.get("memory"):
            continue
        if transport == "spi" and not tics.has_tics_register_model(descriptor):
            continue
        if transport not in {"i2c", "spi"}:
            continue
        controller = controllers.get(device["attach"]["controller_id"])
        if controller is None:
            continue
        htype, _ = cmodel._handle_for(controller)
        if htype not in {"XIicPs", "XIic", "XSpiPs", "XSpi"}:
            continue
        plan = _ChipPlan(device=device, descriptor=descriptor, controller=controller,
                         module=modules.get(device["id"], cmodel._module_of(device["part"])),
                         part=str(device["part"]), transport=transport)
        attach = device["attach"]
        if transport == "i2c":
            plan.i2c_addr = int(str(attach["i2c_address"]), 0)
            via = attach.get("via_mux")
            if via and via.get("mux_id") in muxes:
                plan.mux_addr = int(str(muxes[via["mux_id"]]["i2c_address"]), 0)
                plan.mux_channel = int(via.get("channel", 0))
        else:
            plan.spi_select = int(attach.get("spi_chip_select", 0))
        used: set[str] = set()
        plan.status_regs = _status_registers(plan, used)
        _measures(plan, manifest_by_id.get(device["id"], {}).get("operations", []), used)
        if not plan.status_regs and not plan.measures:
            continue
        plans.append(plan)
    return plans


# --- port.h -----------------------------------------------------------------------------

def port_header(spec: dict) -> str:
    drivers = set()
    for c in spec.get("controllers", []):
        if c.get("type") in {"i2c", "spi"}:
            try:
                drivers.add(cmodel._handle_for(c)[0])
            except cmodel.CodegenError:
                continue
    flags = {
        "SPEC2CODE_CIT_PORT_XIICPS": int("XIicPs" in drivers),
        "SPEC2CODE_CIT_PORT_XIIC": int("XIic" in drivers),
        "SPEC2CODE_CIT_PORT_XSPIPS": int("XSpiPs" in drivers),
        "SPEC2CODE_CIT_PORT_XSPI": int("XSpi" in drivers),
        "SPEC2CODE_CIT_PORT_KULLANICI": 0,
    }
    e = _E(0)
    e.ln("/**")
    e.ln(" * @file spec2code_cit_port.h")
    e.ln(" * @brief CIT katmani platform secimi ve durum kodlari (TEK tasima noktasi).")
    e.ln(" *")
    e.ln(" * Baska bir platforma tasirken YALNIZ bu dosya degisir: ilgili arka uc makrosu 1,")
    e.ln(" * digerleri 0 yapilir. Xilinx disi bir MCU icin SPEC2CODE_CIT_PORT_KULLANICI=1")
    e.ln(" * secilir ve spec2code_i2c_bus.h / spec2code_spi_bus.h sonundaki iki port")
    e.ln(" * fonksiyonu kullanici tarafindan gerceklenir. Makrolar #ifndef korumali: derleyici")
    e.ln(" * satirindan -D ile ezilebilir (host testleri boyle kosar). Do not edit by hand.")
    e.ln(" */")
    e.ln("#ifndef SPEC2CODE_CIT_PORT_H")
    e.ln("#define SPEC2CODE_CIT_PORT_H")
    e.blank()
    e.ln("/* --- arka uc secimi (spec'teki denetleyicilerden turetildi) --- */")
    for name, value in flags.items():
        e.ln(f"#ifndef {name}")
        e.ln(f"#define {name} {value}")
        e.ln("#endif")
    e.blank()
    e.ln("/* Xilinx BSP basliklari (xparameters.h, xstatus.h) mevcut mu? Kullanici portunda 0. */")
    e.ln("#ifndef SPEC2CODE_CIT_PORT_XILINX")
    e.ln("#if SPEC2CODE_CIT_PORT_XIICPS || SPEC2CODE_CIT_PORT_XIIC || SPEC2CODE_CIT_PORT_XSPIPS || \\")
    e.ln("    SPEC2CODE_CIT_PORT_XSPI")
    e.ln("#define SPEC2CODE_CIT_PORT_XILINX 1")
    e.ln("#else")
    e.ln("#define SPEC2CODE_CIT_PORT_XILINX 0")
    e.ln("#endif")
    e.ln("#endif")
    e.blank()
    e.ln("/* --- katman durum kodlari (XST_SUCCESS/XST_FAILURE ile uyumlu: 0 / 1) --- */")
    e.ln(f"#define {STATUS_OK} 0")
    e.ln(f"#define {STATUS_FAIL} 1")
    e.ln(f"#define {STATUS_TIMEOUT} 2")
    e.ln(f"#define {STATUS_PARAM} 3")
    e.ln(f"#define {STATUS_UNSUPPORTED} 4")
    e.blank()
    e.ln("/* --- simulasyon: HAL'e sanal cihaz zinciri (karisik mod) derlenir mi? --- */")
    e.ln("#ifndef SPEC2CODE_CIT_SIM")
    e.ln("#define SPEC2CODE_CIT_SIM 1")
    e.ln("#endif")
    e.blank()
    e.ln("/* --- HAL tampon sinirlari --- */")
    e.ln(f"#define SPEC2CODE_I2C_TX_MAX {I2C_TX_MAX}U  /* tek yazmada azami bayt (register erisimleri <= 4) */")
    e.ln(f"#define SPEC2CODE_SPI_FRAME_MAX {SPI_FRAME_MAX}U /* tek SPI cercevesinde azami bayt */")
    e.blank()
    e.ln("#endif /* SPEC2CODE_CIT_PORT_H */")
    return e.text()


# --- I2C HAL ----------------------------------------------------------------------------

def i2c_bus_header() -> str:
    return """/**
 * @file spec2code_i2c_bus.h
 * @brief Portlanabilir I2C sarmalayici (CIT katmani alt seviyesi).
 *
 * Tek API, uc arka uc: Zynq/ZynqMP PS XIicPs (ornek tabanli), AXI IIC XIic
 * (taban adres tabanli, xiic_l.h polled API) ve kullanici portu (Xilinx disi MCU).
 * Arka uc secimi spec2code_cit_port.h icindedir. Her transfer bloklayicidir;
 * basarisiz transferler uiHataSayac'i artirir (saha teshisi icin).
 *
 * SIMULASYON / KARISIK MOD (SPEC2CODE_CIT_SIM): bus'a sanal cihazlar eklenir
 * (spec2codeI2cSimEkle). Bir transferde 7-bit adres sanal cihazla eslesirse cevabi
 * simulator verir, eslesmezse transfer GERCEK donanima gider - ayni bus uzerinde
 * takili olan entegre gercek, henuz takili olmayan entegre sanal cevap verir.
 * Donanimsiz kosum icin eSurucu = SPEC2CODE_I2C_SURUCU_SIM secilir (eslesmeyen
 * adres NACK sayilir).
 * Generated by Spec2Code. Do not edit by hand.
 */
#ifndef SPEC2CODE_I2C_BUS_H
#define SPEC2CODE_I2C_BUS_H

#include "spec2code_cit_port.h"
#if SPEC2CODE_CIT_PORT_XIICPS
#include "xiicps.h"
#endif
#if SPEC2CODE_CIT_PORT_XIIC
#include "xiic_l.h"
#endif

typedef enum
{
    SPEC2CODE_I2C_SURUCU_YOK = 0,
    SPEC2CODE_I2C_SURUCU_XIICPS = 1,   /* PS I2C: uiDeviceId + uiSclkHz */
    SPEC2CODE_I2C_SURUCU_XIIC = 2,     /* AXI IIC: ulTabanAdres */
    SPEC2CODE_I2C_SURUCU_KULLANICI = 3, /* spec2codeI2cPortWrite/Read (kullanici gercekler) */
    SPEC2CODE_I2C_SURUCU_SIM = 4        /* donanim yok: yalniz sanal cihazlar cevap verir */
} ESpec2codeI2cSurucu;

#if SPEC2CODE_CIT_SIM
/**
 * @brief Bus'a takilan sanal I2C cihazi (zincir dugumu). Her simulator kendi struct'inin
 *        ILK alani olarak bunu tasir; pfYaz/pfOku o cihazin register modelini kosturur.
 *        Donus: 0 ACK, sifir disi NACK.
 */
typedef struct SSpec2codeI2cSimCihaz
{
    unsigned char ucAdres; /* 7-bit adres (eslestirme anahtari) */
    void* vpDurum;         /* cihaz modeli (sahibi simulator) */
    int (*pfYaz)(void* vpDurum, const unsigned char* ucpVeri, unsigned int uiBoy);
    int (*pfOku)(void* vpDurum, unsigned char* ucpVeri, unsigned int uiBoy);
    struct SSpec2codeI2cSimCihaz* spSonraki;
} SSpec2codeI2cSimCihaz;
#endif

/**
 * @brief Bir I2C denetleyicisinin calisma zamani tanimi. Alanlar spec'ten varsayilanla
 *        dolar (sistemCitBusVarsayilan) ama kullanici init'ten once degistirebilir.
 */
typedef struct
{
    ESpec2codeI2cSurucu eSurucu;
    unsigned int uiPortIndex;   /* kullanici portunda hangi bus (0,1,..)              */
    unsigned int uiDeviceId;    /* XPAR_<inst>_DEVICE_ID (XIicPs)                     */
    unsigned long ulTabanAdres; /* XPAR_<inst>_BASEADDR (XIic)                        */
    unsigned int uiSclkHz;      /* SCL (XIicPs'te uygulanir; AXI IIC'de IP sabiti)    */
    unsigned int uiHazir;       /* spec2codeI2cBusInit basarili -> 1                  */
    unsigned int uiHataSayac;   /* basarisiz transfer sayaci (init'te sifirlanir)     */
#if SPEC2CODE_CIT_SIM
    SSpec2codeI2cSimCihaz* spSimListe; /* sanal cihaz zinciri; NULL = simulasyon yok  */
    unsigned int uiSimSayac;           /* simulatore giden transfer sayisi (teshis)   */
#endif
#if SPEC2CODE_CIT_PORT_XIICPS
    XIicPs sIicPs; /* surucu ornegi (yalniz XIICPS arka ucunda) */
#endif
} SSpec2codeI2cBus;

/**
 * @brief Denetleyiciyi hazirlar (XIicPs: LookupConfig/CfgInitialize/SetSClk; XIic: hat bos
 *        mu; kullanici: yalniz bayrak). Zaten hazirsa yeniden ilklendirmez.
 * @param spBus Bus tanimi (eSurucu ve kimlik alanlari dolu olmali).
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cBusInit(SSpec2codeI2cBus* spBus);

/**
 * @brief Ham yazma: START adres(W) veri... STOP.
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucpVeri Yazilacak baytlar (en fazla SPEC2CODE_I2C_TX_MAX).
 * @param uiBoy Bayt sayisi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres, const unsigned char* ucpVeri,
                      unsigned int uiBoy);

/**
 * @brief Ham okuma: START adres(R) veri... STOP.
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucpVeri Okunan baytlarin yazilacagi tampon.
 * @param uiBoy Bayt sayisi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char* ucpVeri,
                     unsigned int uiBoy);

/**
 * @brief 8-bit register yaz (reg + deger tek transfer).
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucReg Register adresi.
 * @param ucDeger Yazilacak deger.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cRegisterWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                              unsigned char ucDeger);

/**
 * @brief 8-bit register oku (pointer yaz, 1 bayt oku).
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucReg Register adresi.
 * @param ucpDeger Okunan deger.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cRegisterRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                             unsigned char* ucpDeger);

/**
 * @brief GENIS (16-bit+) tek register: pointer bir kez yazilir, N bayt TEK islemde okunur
 *        (AD7414/TMP101 TEMPERATURE gibi; baytlar ayni adresin icindedir).
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucReg Register adresi.
 * @param ucpTampon Okunan baytlar (MSB once, cihazin verdigi sirayla).
 * @param uiBoy Bayt sayisi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cRegisterReadWide(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                                 unsigned char ucReg, unsigned char* ucpTampon,
                                 unsigned int uiBoy);

/**
 * @brief ARDISIK register adresleri: her bayt kendi adresinden tek tek okunur (DS1682,
 *        LTC2945 gibi; blok okuma sahada dusen cihazlar icin kanitli yol).
 * @param spBus Hazir bus.
 * @param ucAdres 7-bit I2C adresi.
 * @param ucReg Ilk register adresi.
 * @param ucpTampon Okunan baytlar.
 * @param uiBoy Register sayisi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cRegistersRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                              unsigned char* ucpTampon, unsigned int uiBoy);

/**
 * @brief TCA9548A tipi I2C switch'te TEK kanali acar (kontrol bayti = 1 << kanal).
 * @param spBus Hazir bus.
 * @param ucMuxAdres Switch'in 7-bit adresi.
 * @param ucKanal Kanal 0..7.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeI2cMuxSelect(SSpec2codeI2cBus* spBus, unsigned char ucMuxAdres,
                          unsigned char ucKanal);

#if SPEC2CODE_CIT_SIM
/**
 * @brief Sanal cihazi bus'a takar (ayni adreste eskisi varsa yenisi onu golgeler).
 * @param spBus Bus (init'ten once ya da sonra eklenebilir).
 * @param spCihaz Simulatorun zincir dugumu (ucAdres/pfYaz/pfOku dolu).
 * @return SPEC2CODE_CIT_OK ya da SPEC2CODE_CIT_PARAMETRE.
 */
int spec2codeI2cSimEkle(SSpec2codeI2cBus* spBus, SSpec2codeI2cSimCihaz* spCihaz);

/**
 * @brief Sanal cihazi bus'tan cikarir; o adres yeniden gercek donanima gider.
 * @param spBus Bus.
 * @param spCihaz Daha once eklenen dugum.
 * @return SPEC2CODE_CIT_OK ya da SPEC2CODE_CIT_PARAMETRE (bulunamadi).
 */
int spec2codeI2cSimKaldir(SSpec2codeI2cBus* spBus, SSpec2codeI2cSimCihaz* spCihaz);

/**
 * @brief Adrese takili sanal cihazi dondurur (NULL: o adres gercek donanimda).
 * @param spBus Bus.
 * @param ucAdres 7-bit adres.
 * @return Dugum ya da NULL.
 */
SSpec2codeI2cSimCihaz* spec2codeI2cSimBul(SSpec2codeI2cBus* spBus, unsigned char ucAdres);
#endif

#if SPEC2CODE_CIT_PORT_KULLANICI
/* --- kullanici portu: Xilinx disi platformda bu iki fonksiyon KULLANICI tarafindan
 *     gerceklenir (spBus->uiPortIndex ile hangi fiziksel bus oldugu ayirt edilir).
 *     Donus: 0 basari, sifir disi hata. --- */
int spec2codeI2cPortWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                          const unsigned char* ucpVeri, unsigned int uiBoy);
int spec2codeI2cPortRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char* ucpVeri,
                         unsigned int uiBoy);
#endif

#endif /* SPEC2CODE_I2C_BUS_H */
"""


def i2c_bus_source() -> str:
    return """/**
 * @file spec2code_i2c_bus.c
 * @brief Portlanabilir I2C sarmalayici gerceklemesi. Generated by Spec2Code.
 *
 * Arka uc farklari (tek yerde):
 *  - XIicPs_MasterSendPolled/RecvPolled XST_* dondurur ve sonrasinda BusIsBusy
 *    beklenir; SCL hizi SetSClk ile kurulur.
 *  - XIic_DynSend/XIic_DynRecv (xiic_l.h, DINAMIK mod) TABAN ADRES alir ve
 *    AKTARILAN BAYT SAYISINI dondurur (mesgul hatta 0): kisa sayim tek hata
 *    isaretidir; kendileri transfer bitene kadar bloklar. Standart-mod XIic_Send
 *    tek baytlik STOP yaziminda bayti dusurdugu icin (SAHA: Nexys A7) dinamik mod
 *    secildi; XIic_DynInit BusInit'te kosar.
 *  - Kullanici portu: spec2codeI2cPortWrite/Read.
 */
#include "spec2code_i2c_bus.h"

#if SPEC2CODE_CIT_PORT_XILINX
#include "xstatus.h"
#endif

static int spec2codeI2cHata(SSpec2codeI2cBus* spBus, int iStatus)
{
    spBus->uiHataSayac++;
    return iStatus;
}

#if SPEC2CODE_CIT_SIM
int spec2codeI2cSimEkle(SSpec2codeI2cBus* spBus, SSpec2codeI2cSimCihaz* spCihaz)
{
    if ((spBus == (SSpec2codeI2cBus*)0) || (spCihaz == (SSpec2codeI2cSimCihaz*)0) ||
        (spCihaz->pfYaz == 0) || (spCihaz->pfOku == 0))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    /* Basa eklenir: ayni adresteki eski dugum golgelenir (once eklenen kazanmaz). */
    spCihaz->spSonraki = spBus->spSimListe;
    spBus->spSimListe = spCihaz;
    return SPEC2CODE_CIT_OK;
}

int spec2codeI2cSimKaldir(SSpec2codeI2cBus* spBus, SSpec2codeI2cSimCihaz* spCihaz)
{
    SSpec2codeI2cSimCihaz** sppGezgin;

    if ((spBus == (SSpec2codeI2cBus*)0) || (spCihaz == (SSpec2codeI2cSimCihaz*)0))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    sppGezgin = &spBus->spSimListe;
    while (*sppGezgin != (SSpec2codeI2cSimCihaz*)0)
    {
        if (*sppGezgin == spCihaz)
        {
            *sppGezgin = spCihaz->spSonraki;
            spCihaz->spSonraki = (SSpec2codeI2cSimCihaz*)0;
            return SPEC2CODE_CIT_OK;
        }
        sppGezgin = &(*sppGezgin)->spSonraki;
    }
    return SPEC2CODE_CIT_PARAMETRE;
}

SSpec2codeI2cSimCihaz* spec2codeI2cSimBul(SSpec2codeI2cBus* spBus, unsigned char ucAdres)
{
    SSpec2codeI2cSimCihaz* spGezgin;

    if (spBus == (SSpec2codeI2cBus*)0)
    {
        return (SSpec2codeI2cSimCihaz*)0;
    }
    spGezgin = spBus->spSimListe;
    while (spGezgin != (SSpec2codeI2cSimCihaz*)0)
    {
        if (spGezgin->ucAdres == ucAdres)
        {
            return spGezgin;
        }
        spGezgin = spGezgin->spSonraki;
    }
    return (SSpec2codeI2cSimCihaz*)0;
}
#endif

int spec2codeI2cBusInit(SSpec2codeI2cBus* spBus)
{
    if (spBus == (SSpec2codeI2cBus*)0)
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    spBus->uiHataSayac = 0U;
    if (spBus->uiHazir == 1U)
    {
        return SPEC2CODE_CIT_OK;
    }
    switch (spBus->eSurucu)
    {
#if SPEC2CODE_CIT_PORT_XIICPS
    case SPEC2CODE_I2C_SURUCU_XIICPS:
    {
        XIicPs_Config* spConfig;
        int iStatus;

        /* Zaten calisan (paylasilan) denetleyici yeniden CfgInitialize edilmez:
         * bazi suruculer XST_DEVICE_IS_STARTED dondurur, bazilari canli hat
         * ayarlarini sifirlar. */
        if (spBus->sIicPs.IsReady != XIL_COMPONENT_IS_READY)
        {
            spConfig = XIicPs_LookupConfig((u16)spBus->uiDeviceId);
            if (spConfig == NULL)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XIicPs_CfgInitialize(&spBus->sIicPs, spConfig, spConfig->BaseAddress);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XIicPs_SetSClk(&spBus->sIicPs, spBus->uiSclkHz);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
        }
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_XIIC
    case SPEC2CODE_I2C_SURUCU_XIIC:
    {
        /* AXI IIC polled API'de surucu ornegi yoktur; SCL IP'de sabittir. Hat gercekten
         * bosta mi diye bakilir: takili SDA/SCL burada YUKSEK SESLE duser. */
        if (spBus->ulTabanAdres == 0U)
        {
            return SPEC2CODE_CIT_PARAMETRE;
        }
        if (XIic_DynInit((UINTPTR)spBus->ulTabanAdres) != XST_SUCCESS)
        {
            return SPEC2CODE_CIT_HATA;
        }
        if (XIic_WaitBusFree((UINTPTR)spBus->ulTabanAdres) != XST_SUCCESS)
        {
            return SPEC2CODE_CIT_HATA;
        }
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_KULLANICI
    case SPEC2CODE_I2C_SURUCU_KULLANICI:
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
#endif
#if SPEC2CODE_CIT_SIM
    case SPEC2CODE_I2C_SURUCU_SIM:
        /* Donanim yok: yalniz sanal cihazlar cevap verir. */
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
#endif
    default:
        return SPEC2CODE_CIT_DESTEK_YOK;
    }
}

/* ucTut: 1 = transfer STOP yerine REPEATED_START ile biter (register pointer yazimi;
 * ardindan spec2codeI2cRead STOP'la bitirir). Yalniz AXI IIC'de anlamlidir: dinamik
 * modda STOP'lu pointer + DynRecv IP'de takilir (SAHA: Nexys A7). PS ve kullanici
 * portu STOP'lu yazim + ayri okuma yapar (PS'te sahada kanitli). */
static int spec2codeI2cWriteOpsiyon(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                                    const unsigned char* ucpVeri, unsigned int uiBoy,
                                    unsigned int uiTut)
{
    unsigned char ucArrTx[SPEC2CODE_I2C_TX_MAX];
    unsigned int uiIndex;

    (void)uiTut;
    if ((spBus == (SSpec2codeI2cBus*)0) || (ucpVeri == (const unsigned char*)0) ||
        (uiBoy == 0U) || (uiBoy > SPEC2CODE_I2C_TX_MAX))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    if (spBus->uiHazir != 1U)
    {
        return SPEC2CODE_CIT_HATA;
    }
#if SPEC2CODE_CIT_SIM
    {
        SSpec2codeI2cSimCihaz* spSim = spec2codeI2cSimBul(spBus, ucAdres);

        if (spSim != (SSpec2codeI2cSimCihaz*)0)
        {
            spBus->uiSimSayac++;
            if (spSim->pfYaz(spSim->vpDurum, ucpVeri, uiBoy) != 0)
            {
                return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
            }
            return SPEC2CODE_CIT_OK;
        }
        if (spBus->eSurucu == SPEC2CODE_I2C_SURUCU_SIM)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA); /* adres bosta: NACK */
        }
    }
#endif
    /* Surucu API'leri const olmayan tampon ister: yerel kopya. */
    for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
    {
        ucArrTx[uiIndex] = ucpVeri[uiIndex];
    }
    (void)ucArrTx; /* hicbir arka uc derlenmemisse (tam sanal) kullanilmaz */
    switch (spBus->eSurucu)
    {
#if SPEC2CODE_CIT_PORT_XIICPS
    case SPEC2CODE_I2C_SURUCU_XIICPS:
    {
        int iStatus;

        iStatus = XIicPs_MasterSendPolled(&spBus->sIicPs, ucArrTx, (s32)uiBoy, (u16)ucAdres);
        if (iStatus != XST_SUCCESS)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        while (XIicPs_BusIsBusy(&spBus->sIicPs) == TRUE)
        {
            /* wait */
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_XIIC
    case SPEC2CODE_I2C_SURUCU_XIIC:
    {
        unsigned int uiGiden;

        uiGiden = (unsigned int)XIic_DynSend((UINTPTR)spBus->ulTabanAdres, (unsigned short)ucAdres,
                                             ucArrTx, (unsigned char)uiBoy,
                                             (uiTut != 0U) ? XIIC_REPEATED_START : XIIC_STOP);
        if (uiGiden != uiBoy)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_KULLANICI
    case SPEC2CODE_I2C_SURUCU_KULLANICI:
        if (spec2codeI2cPortWrite(spBus, ucAdres, ucArrTx, uiBoy) != 0)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        return SPEC2CODE_CIT_OK;
#endif
    default:
        return SPEC2CODE_CIT_DESTEK_YOK;
    }
}

int spec2codeI2cWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres, const unsigned char* ucpVeri,
                      unsigned int uiBoy)
{
    return spec2codeI2cWriteOpsiyon(spBus, ucAdres, ucpVeri, uiBoy, 0U);
}

int spec2codeI2cRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char* ucpVeri,
                     unsigned int uiBoy)
{
    if ((spBus == (SSpec2codeI2cBus*)0) || (ucpVeri == (unsigned char*)0) || (uiBoy == 0U))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    if (spBus->uiHazir != 1U)
    {
        return SPEC2CODE_CIT_HATA;
    }
#if SPEC2CODE_CIT_SIM
    {
        SSpec2codeI2cSimCihaz* spSim = spec2codeI2cSimBul(spBus, ucAdres);

        if (spSim != (SSpec2codeI2cSimCihaz*)0)
        {
            spBus->uiSimSayac++;
            if (spSim->pfOku(spSim->vpDurum, ucpVeri, uiBoy) != 0)
            {
                return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
            }
            return SPEC2CODE_CIT_OK;
        }
        if (spBus->eSurucu == SPEC2CODE_I2C_SURUCU_SIM)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA); /* adres bosta: NACK */
        }
    }
#endif
    switch (spBus->eSurucu)
    {
#if SPEC2CODE_CIT_PORT_XIICPS
    case SPEC2CODE_I2C_SURUCU_XIICPS:
    {
        int iStatus;

        iStatus = XIicPs_MasterRecvPolled(&spBus->sIicPs, ucpVeri, (s32)uiBoy, (u16)ucAdres);
        if (iStatus != XST_SUCCESS)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        while (XIicPs_BusIsBusy(&spBus->sIicPs) == TRUE)
        {
            /* wait */
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_XIIC
    case SPEC2CODE_I2C_SURUCU_XIIC:
    {
        unsigned int uiGelen;

        uiGelen = (unsigned int)XIic_DynRecv((UINTPTR)spBus->ulTabanAdres, ucAdres, ucpVeri,
                                             (unsigned char)uiBoy);
        if (uiGelen != uiBoy)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_KULLANICI
    case SPEC2CODE_I2C_SURUCU_KULLANICI:
        if (spec2codeI2cPortRead(spBus, ucAdres, ucpVeri, uiBoy) != 0)
        {
            return spec2codeI2cHata(spBus, SPEC2CODE_CIT_HATA);
        }
        return SPEC2CODE_CIT_OK;
#endif
    default:
        return SPEC2CODE_CIT_DESTEK_YOK;
    }
}

int spec2codeI2cRegisterWrite(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                              unsigned char ucDeger)
{
    unsigned char ucArrTx[2];

    ucArrTx[0] = ucReg;
    ucArrTx[1] = ucDeger;
    return spec2codeI2cWrite(spBus, ucAdres, ucArrTx, 2U);
}

int spec2codeI2cRegisterRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                             unsigned char* ucpDeger)
{
    return spec2codeI2cRegisterReadWide(spBus, ucAdres, ucReg, ucpDeger, 1U);
}

int spec2codeI2cRegisterReadWide(SSpec2codeI2cBus* spBus, unsigned char ucAdres,
                                 unsigned char ucReg, unsigned char* ucpTampon,
                                 unsigned int uiBoy)
{
    int iStatus;

    /* Pointer yazimi: AXI IIC'de REPEATED_START ile hat tutulur ve DynRecv STOP'la
     * bitirir (STOP'lu pointer + DynRecv IP'de takilir - SAHA Nexys A7); PS ve
     * kullanici portunda STOP + ayri okuma (PS'te sahada kanitli). */
    iStatus = spec2codeI2cWriteOpsiyon(spBus, ucAdres, &ucReg, 1U, 1U);
    if (iStatus != SPEC2CODE_CIT_OK)
    {
        return iStatus;
    }
    return spec2codeI2cRead(spBus, ucAdres, ucpTampon, uiBoy);
}

int spec2codeI2cRegistersRead(SSpec2codeI2cBus* spBus, unsigned char ucAdres, unsigned char ucReg,
                              unsigned char* ucpTampon, unsigned int uiBoy)
{
    unsigned int uiIndex;
    int iStatus;

    if ((ucpTampon == (unsigned char*)0) || (uiBoy == 0U))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
    {
        iStatus = spec2codeI2cRegisterRead(spBus, ucAdres, (unsigned char)(ucReg + uiIndex),
                                           &ucpTampon[uiIndex]);
        if (iStatus != SPEC2CODE_CIT_OK)
        {
            return iStatus;
        }
    }
    return SPEC2CODE_CIT_OK;
}

int spec2codeI2cMuxSelect(SSpec2codeI2cBus* spBus, unsigned char ucMuxAdres,
                          unsigned char ucKanal)
{
    unsigned char ucMaske;

    if (ucKanal > 7U)
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    ucMaske = (unsigned char)(1U << ucKanal);
    return spec2codeI2cWrite(spBus, ucMuxAdres, &ucMaske, 1U);
}
"""


# --- SPI HAL ----------------------------------------------------------------------------

def spi_bus_header() -> str:
    return """/**
 * @file spec2code_spi_bus.h
 * @brief Portlanabilir SPI sarmalayici (CIT katmani alt seviyesi).
 *
 * Tek API, uc arka uc: PS XSpiPs, AXI Quad SPI XSpi (polled, kesmeler maskeli) ve
 * kullanici portu. Chip-select INDEKS olarak verilir; AXI XSpi'nin one-hot maskesine
 * cevrim sarmalayicinin icindedir. Generated by Spec2Code. Do not edit by hand.
 */
#ifndef SPEC2CODE_SPI_BUS_H
#define SPEC2CODE_SPI_BUS_H

#include "spec2code_cit_port.h"
#if SPEC2CODE_CIT_PORT_XSPIPS
#include "xspips.h"
#endif
#if SPEC2CODE_CIT_PORT_XSPI
#include "xspi.h"
#endif

typedef enum
{
    SPEC2CODE_SPI_SURUCU_YOK = 0,
    SPEC2CODE_SPI_SURUCU_XSPIPS = 1,   /* PS SPI: uiDeviceId */
    SPEC2CODE_SPI_SURUCU_XSPI = 2,     /* AXI Quad SPI: uiDeviceId */
    SPEC2CODE_SPI_SURUCU_KULLANICI = 3 /* spec2codeSpiPortTransfer (kullanici gercekler) */
} ESpec2codeSpiSurucu;

/**
 * @brief Bir SPI denetleyicisinin calisma zamani tanimi.
 */
typedef struct
{
    ESpec2codeSpiSurucu eSurucu;
    unsigned int uiPortIndex; /* kullanici portunda hangi bus                    */
    unsigned int uiDeviceId;  /* XPAR_<inst>_DEVICE_ID                           */
    unsigned int uiHazir;     /* spec2codeSpiBusInit basarili -> 1               */
    unsigned int uiHataSayac; /* basarisiz transfer sayaci (init'te sifirlanir)  */
#if SPEC2CODE_CIT_PORT_XSPIPS
    XSpiPs sSpiPs; /* surucu ornegi (yalniz XSPIPS arka ucunda) */
#endif
#if SPEC2CODE_CIT_PORT_XSPI
    XSpi sSpi; /* surucu ornegi (yalniz XSPI arka ucunda) */
#endif
} SSpec2codeSpiBus;

/**
 * @brief Denetleyiciyi master + manuel chip-select modunda hazirlar (resmi polled akis:
 *        LookupConfig -> CfgInitialize -> SetOptions -> Start -> kesmeleri kapat).
 * @param spBus Bus tanimi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeSpiBusInit(SSpec2codeSpiBus* spBus);

/**
 * @brief Bloklayici tam cift yonlu transfer (CS sec, gonder/al, CS birak).
 * @param spBus Hazir bus.
 * @param ucSelect Chip-select indeksi (0..).
 * @param ucpTx Gonderilecek baytlar (en fazla SPEC2CODE_SPI_FRAME_MAX).
 * @param ucpRx Alinan baytlar; ilgilenilmiyorsa NULL.
 * @param uiBoy Bayt sayisi.
 * @return SPEC2CODE_CIT_OK ya da hata kodu.
 */
int spec2codeSpiTransfer(SSpec2codeSpiBus* spBus, unsigned char ucSelect,
                         const unsigned char* ucpTx, unsigned char* ucpRx, unsigned int uiBoy);

#if SPEC2CODE_CIT_PORT_KULLANICI
/* --- kullanici portu: Xilinx disi platformda KULLANICI gercekler. Donus 0 basari. --- */
int spec2codeSpiPortTransfer(SSpec2codeSpiBus* spBus, unsigned char ucSelect,
                             const unsigned char* ucpTx, unsigned char* ucpRx,
                             unsigned int uiBoy);
#endif

#endif /* SPEC2CODE_SPI_BUS_H */
"""


def spi_bus_source() -> str:
    return """/**
 * @file spec2code_spi_bus.c
 * @brief Portlanabilir SPI sarmalayici gerceklemesi. Generated by Spec2Code.
 *
 *  - XSpiPs_SetSlaveSelect slave INDEKSI alir; AXI XSpi_SetSlaveSelect ONE-HOT
 *    AKTIF-YUKSEK MASKE alir (xspi.c: "a 32-bit mask with a 1 in the bit position
 *    of the slave being selected"). Uretilen API her yerde indeks konusur.
 *  - Her transfer polled; AXI arka ucunda kesmeler init'te kapatilir.
 */
#include "spec2code_spi_bus.h"

#if SPEC2CODE_CIT_PORT_XILINX
#include "xstatus.h"
#endif

int spec2codeSpiBusInit(SSpec2codeSpiBus* spBus)
{
    if (spBus == (SSpec2codeSpiBus*)0)
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    spBus->uiHataSayac = 0U;
    if (spBus->uiHazir == 1U)
    {
        return SPEC2CODE_CIT_OK;
    }
    switch (spBus->eSurucu)
    {
#if SPEC2CODE_CIT_PORT_XSPIPS
    case SPEC2CODE_SPI_SURUCU_XSPIPS:
    {
        XSpiPs_Config* spConfig;
        int iStatus;

        if (spBus->sSpiPs.IsReady != XIL_COMPONENT_IS_READY)
        {
            spConfig = XSpiPs_LookupConfig((u16)spBus->uiDeviceId);
            if (spConfig == NULL)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpiPs_CfgInitialize(&spBus->sSpiPs, spConfig, spConfig->BaseAddress);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpiPs_SetOptions(&spBus->sSpiPs,
                                        XSPIPS_MASTER_OPTION | XSPIPS_FORCE_SSELECT_OPTION);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpiPs_SetClkPrescaler(&spBus->sSpiPs, XSPIPS_CLK_PRESCALE_8);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
        }
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_XSPI
    case SPEC2CODE_SPI_SURUCU_XSPI:
    {
        XSpi_Config* spConfig;
        int iStatus;

        if (spBus->sSpi.IsReady != XIL_COMPONENT_IS_READY)
        {
            spConfig = XSpi_LookupConfig((u16)spBus->uiDeviceId);
            if (spConfig == NULL)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpi_CfgInitialize(&spBus->sSpi, spConfig, spConfig->BaseAddress);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpi_SetOptions(&spBus->sSpi, XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            iStatus = XSpi_Start(&spBus->sSpi);
            if (iStatus != XST_SUCCESS)
            {
                return SPEC2CODE_CIT_HATA;
            }
            /* Her transfer polled: kesmeler maskeli kalmali. */
            XSpi_IntrGlobalDisable(&spBus->sSpi);
        }
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_KULLANICI
    case SPEC2CODE_SPI_SURUCU_KULLANICI:
        spBus->uiHazir = 1U;
        return SPEC2CODE_CIT_OK;
#endif
    default:
        return SPEC2CODE_CIT_DESTEK_YOK;
    }
}

int spec2codeSpiTransfer(SSpec2codeSpiBus* spBus, unsigned char ucSelect,
                         const unsigned char* ucpTx, unsigned char* ucpRx, unsigned int uiBoy)
{
    unsigned char ucArrTx[SPEC2CODE_SPI_FRAME_MAX];
    unsigned int uiIndex;

    if ((spBus == (SSpec2codeSpiBus*)0) || (ucpTx == (const unsigned char*)0) || (uiBoy == 0U) ||
        (uiBoy > SPEC2CODE_SPI_FRAME_MAX))
    {
        return SPEC2CODE_CIT_PARAMETRE;
    }
    if (spBus->uiHazir != 1U)
    {
        return SPEC2CODE_CIT_HATA;
    }
    for (uiIndex = 0U; uiIndex < uiBoy; uiIndex++)
    {
        ucArrTx[uiIndex] = ucpTx[uiIndex];
    }
    (void)ucArrTx; /* hicbir arka uc derlenmemisse kullanilmaz */
    switch (spBus->eSurucu)
    {
#if SPEC2CODE_CIT_PORT_XSPIPS
    case SPEC2CODE_SPI_SURUCU_XSPIPS:
    {
        int iStatus;

        iStatus = XSpiPs_SetSlaveSelect(&spBus->sSpiPs, (u8)ucSelect);
        if (iStatus != XST_SUCCESS)
        {
            spBus->uiHataSayac++;
            return SPEC2CODE_CIT_HATA;
        }
        iStatus = XSpiPs_PolledTransfer(&spBus->sSpiPs, ucArrTx, ucpRx, uiBoy);
        if (iStatus != XST_SUCCESS)
        {
            spBus->uiHataSayac++;
            return SPEC2CODE_CIT_HATA;
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_XSPI
    case SPEC2CODE_SPI_SURUCU_XSPI:
    {
        int iStatus;

        iStatus = XSpi_SetSlaveSelect(&spBus->sSpi, (u32)(1U << ucSelect));
        if (iStatus != XST_SUCCESS)
        {
            spBus->uiHataSayac++;
            return SPEC2CODE_CIT_HATA;
        }
        iStatus = XSpi_Transfer(&spBus->sSpi, ucArrTx, ucpRx, uiBoy);
        if (iStatus != XST_SUCCESS)
        {
            spBus->uiHataSayac++;
            return SPEC2CODE_CIT_HATA;
        }
        return SPEC2CODE_CIT_OK;
    }
#endif
#if SPEC2CODE_CIT_PORT_KULLANICI
    case SPEC2CODE_SPI_SURUCU_KULLANICI:
        if (spec2codeSpiPortTransfer(spBus, ucSelect, ucArrTx, ucpRx, uiBoy) != 0)
        {
            spBus->uiHataSayac++;
            return SPEC2CODE_CIT_HATA;
        }
        return SPEC2CODE_CIT_OK;
#endif
    default:
        return SPEC2CODE_CIT_DESTEK_YOK;
    }
}
"""


# --- entegre CIT: baslik ----------------------------------------------------------------

def _bus_type(plan: _ChipPlan) -> str:
    return "SSpec2codeI2cBus" if plan.transport == "i2c" else "SSpec2codeSpiBus"


def _flag_entries(plan: _ChipPlan) -> list[_BitField]:
    """Bayrak struct'inin sirali bit alanlari: once OK bitleri, sonra register alanlari."""
    entries: list[_BitField] = []
    for reg in plan.status_regs:
        entries.append(_BitField(reg.ok_bit, 1, f"{reg.name} okundu"))
    for m in plan.measures:
        entries.append(_BitField(m.ok_bit, 1, f"{m.name} okundu"))
    for reg in plan.status_regs:
        for cname, lo, width in reg.fields:
            span = f"bit {lo}" if width == 1 else f"bit {lo + width - 1}:{lo}"
            entries.append(_BitField(cname, width, f"{reg.name} {span}"))
    return entries


def chip_header(plan: _ChipPlan) -> str:
    mod, pas = plan.mod, plan.pascal
    bus_t = _bus_type(plan)
    entries = _flag_entries(plan)
    flag_bytes = bitfield_bytes([b.width for b in entries])
    e = _E(0)
    e.ln("/**")
    e.ln(f" * @file {plan.module}_cit.h")
    e.ln(f" * @brief {plan.part} CIT: durum register bitleri + olcumler tek struct'ta.")
    e.ln(" *")
    e.ln(f" *   {plan.descriptor.get('summary', '')}")
    e.ln(" *")
    e.ln(f" * Katman: spec2code_{plan.transport}_bus.h (HAL) uzerinde calisir; Xilinx surucusune")
    e.ln(" * dogrudan bagimliligi yoktur. Adres/mux/timeout calisma zamaninda S...CitConfig ile")
    e.ln(" * verilir (varsayilan: spec). Kart yalniz OLCER; limit karari ust katmanda.")
    e.ln(" * Generated by Spec2Code. Do not edit by hand.")
    e.ln(" */")
    e.ln(f"#ifndef {mod}_CIT_H")
    e.ln(f"#define {mod}_CIT_H")
    e.blank()
    e.ln(f'#include "spec2code_{plan.transport}_bus.h"')
    e.blank()
    e.ln("/* --- spec'ten gelen varsayilanlar --- */")
    if plan.transport == "i2c":
        e.ln(f"#define {mod}_CIT_I2C_ADDR {_hex(plan.i2c_addr)}    /* {plan.part} I2C adresi */")
        e.ln(f"#define {mod}_CIT_MUX_ADDR {_hex(plan.mux_addr)}    /* I2C switch adresi; 0 = switch yok */")
        e.ln(f"#define {mod}_CIT_MUX_KANAL {plan.mux_channel}U      /* switch kanali */")
        e.ln(f"#define {mod}_CIT_POLL_TIMEOUT 1000U /* poll denemesi; her deneme bir register okumasi */")
        e.ln(f"#define {mod}_CIT_CONFIG_VARSAYILAN \\")
        e.ln("    {" + f"{mod}_CIT_I2C_ADDR, {mod}_CIT_MUX_ADDR, {mod}_CIT_MUX_KANAL, {mod}_CIT_POLL_TIMEOUT" + "}")
    else:
        model = tics.register_model(plan.descriptor)
        e.ln(f"#define {mod}_CIT_SPI_SELECT {plan.spi_select}U      /* chip-select indeksi */")
        e.ln(f"#define {mod}_CIT_SPI_FRAME_BYTES {int(model.get('frame_bits', 24) or 24) // 8}U /* register cercevesi */")
        e.ln(f"#define {mod}_CIT_CONFIG_VARSAYILAN \\")
        e.ln("    {" + f"{mod}_CIT_SPI_SELECT" + "}")
    e.blank()
    regs_used = {reg.name for reg in plan.status_regs}
    for m in plan.measures:
        for s in m.op.get("steps", []):
            if s.get("reg"):
                regs_used.add(str(s["reg"]))
    reg_by_name = {str(r.get("name")): r for r in plan.descriptor.get("registers", [])}
    e.ln("/* --- kullanilan register adresleri --- */")
    for name in sorted(regs_used, key=lambda n: int(reg_by_name.get(n, {}).get("offset", 0))):
        rg = reg_by_name.get(name)
        if rg is None:
            continue
        width = 8 if plan.transport == "i2c" else 16
        e.ln(f"#define {mod}_CIT_REG_{name} {_hex(int(rg.get('offset', 0)), width)}")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} calisma zamani ayarlari (farkli kart/adres icin degistirilebilir).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    if plan.transport == "i2c":
        e.ln("    unsigned char ucI2cAdres;   /* 7-bit cihaz adresi              */")
        e.ln("    unsigned char ucMuxAdres;   /* I2C switch adresi; 0 = yok      */")
        e.ln("    unsigned char ucMuxKanal;   /* switch kanali 0..7              */")
        e.ln("    unsigned int uiPollTimeout; /* hazir-biti bekleme deneme sayisi */")
    else:
        e.ln("    unsigned char ucSpiSelect; /* chip-select indeksi */")
    e.ln("}" + f" S{pas}CitConfig;")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief BIT BIT doldurulan bayraklar: once okuma-basari bitleri (register / olcum),")
    e.ln(" *        sonra durum registerlerinin alanlari (descriptor bit tanimlariyla birebir).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for b in entries:
        e.ln(f"    unsigned int {b.cname} : {b.width}; /* {b.comment} */")
    e.ln("}" + f" S{pas}CitBayraklar;")
    e.blank()
    e.ln(f"_Static_assert(sizeof(S{pas}CitBayraklar) == {flag_bytes}U, "
         f"\"S{pas}CitBayraklar {flag_bytes} bayt olmalidir\");")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} CIT sonucu: bayraklar + ham durum registerleri + olcumler.")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    e.ln(f"    S{pas}CitBayraklar sBayraklar;")
    for reg in plan.status_regs:
        ctype = "unsigned char" if reg.width <= 8 else "unsigned short"
        e.ln(f"    {ctype} {reg.raw_field}; /* ham {reg.name} ({_hex(reg.offset, 8 if plan.transport == 'i2c' else 16)}) */")
    for m in plan.measures:
        unit = f", birim {m.unit}" if m.unit else ""
        decl = f"{m.c_type} {m.field}[{m.count}]" if m.count > 1 else f"{m.c_type} {m.field}"
        e.ln(f"    {decl}; /* {m.name}: {m.op.get('returns', '')}{unit} */")
    e.ln("    unsigned int uiHataSayac; /* bu okumada basarisiz erisim sayisi (0 = hepsi OK) */")
    e.ln("}" + f" S{pas}Cit;")
    e.blank()
    e.ln(f"_Static_assert(sizeof(S{pas}Cit) % 4U == 0U, \"S{pas}Cit 4B hizali olmalidir\");")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} ilklendirme: spec'teki konfigurasyon register yazimlari HAL uzerinden.")
    e.ln(" * @param spBus Hazir (spec2code...BusInit gecmis) bus.")
    e.ln(" * @param spConfig Cihaz ayarlari (NULL -> derleme zamani varsayilan).")
    e.ln(" * @return SPEC2CODE_CIT_OK ya da ilk hata kodu.")
    e.ln(" */")
    e.ln(f"int {plan.module}CitInit({bus_t}* spBus, const S{pas}CitConfig* spConfig);")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} CIT okumasi: durum registerlerini bit bit, olcumleri bayt/kelime")
    e.ln(" *        olarak spCit'e doldurur. Bir okuma dusse de digerlerine DEVAM eder; her")
    e.ln(" *        parcanin kendi Ok biti vardir, uiHataSayac toplam dusen okumadir.")
    e.ln(" * @param spBus Hazir bus.")
    e.ln(" * @param spConfig Cihaz ayarlari (NULL -> derleme zamani varsayilan).")
    e.ln(" * @param spCit Doldurulacak sonuc (once sifirlanir).")
    e.ln(" * @return SPEC2CODE_CIT_OK (hepsi okundu) ya da SPEC2CODE_CIT_HATA.")
    e.ln(" */")
    e.ln(f"int {plan.module}CitRead({bus_t}* spBus, const S{pas}CitConfig* spConfig, S{pas}Cit* spCit);")
    e.blank()
    e.ln(f"#endif /* {mod}_CIT_H */")
    return e.text()


# --- entegre CIT: kaynak ----------------------------------------------------------------

def _i2c_init_writes(plan: _ChipPlan) -> list[dict]:
    regs = {rg["name"]: rg for rg in plan.descriptor.get("registers", [])}
    return [*device_profiles.i2c_init_writes(plan.device),
            *cmodel._generic_i2c_init_writes(plan.device, regs)]


def _emit_i2c_measure(plan: _ChipPlan, m: _Measure, e: _E) -> None:
    """Bir I2C olcum op'unun adimlarini HAL cagrilariyla yayar (surucu emitteriyle ayni anlam)."""
    mod = plan.mod
    regs = {rg["name"]: rg for rg in plan.descriptor.get("registers", [])}
    byte_order = plan.descriptor.get("transport", {}).get("byte_order", "big")
    op = m.op
    steps = op.get("steps", [])
    scalar = m.count == 1
    has_channels = any(s.get("op") == "read_channels" for s in steps)
    scalar_bytes = 0
    if scalar:
        for s in steps:
            if s.get("op") == "read_register":
                scalar_bytes += 1
            elif s.get("op") == "read_registers":
                scalar_bytes += int(s.get("length", 1))
        if scalar_bytes > 4:
            raise cmodel.CodegenError(f"{plan.device['id']} {m.name}: scalar reads are limited to 4 bytes")
    convert = m.convert
    addr = "spConfig->ucI2cAdres"

    e.ln("int iStatus;")
    if has_channels:
        e.ln("unsigned char ucIndex;").ln("unsigned char ucMsb;").ln("unsigned char ucLsb;")
    if scalar_bytes:
        e.ln("unsigned char ucArrBytes[4];")
    if convert:
        e.ln("unsigned int uiCode;" if convert.get("unsigned") else "int iCode;")
        if convert.get("format") == "pmbus_l11":
            e.ln("int iExp;").ln("long long llValue;")
    e.blank()
    read_seen = 0
    pieces: list[dict[str, int]] = []
    for s in steps:
        sop = s.get("op")
        if sop == "comment":
            e.ln(f"/* {s.get('note', '')} */")
        elif sop == "poll":
            rg = regs.get(s["reg"], {})
            bit = next((cmodel._first_bit(f["bits"]) for f in rg.get("fields", [])
                        if f["name"] == s.get("field")), 0)
            mask_expr = "(ucPoll & 0x1U)" if bit == 0 else f"((ucPoll >> {bit}) & 0x1U)"
            e.ln("{")
            e.level += 1
            e.ln("unsigned char ucPoll;")
            e.ln("unsigned int uiTimeout = spConfig->uiPollTimeout;")
            e.blank()
            e.open("do")
            e.ln(f"iStatus = spec2codeI2cRegisterRead(spBus, {addr}, {mod}_CIT_REG_{s['reg']}, &ucPoll);")
            e.check()
            e.open("if (uiTimeout == 0U)").ln(f"return {STATUS_TIMEOUT};").close()
            e.ln("uiTimeout--;")
            e.close(f" while ({mask_expr} != {int(s.get('until', 0))}U);")
            e.close()
        elif sop == "read_register":
            if scalar:
                target = f"ucArrBytes[{read_seen}U]"
                piece = {"index": read_seen}
                if "mask" in s:
                    piece["mask"] = int(s["mask"])
                if "shift" in s:
                    piece["shift"] = int(s["shift"])
                if "right_shift" in s:
                    piece["right_shift"] = int(s["right_shift"])
                pieces.append(piece)
            else:
                target = "ucMsb" if read_seen == 0 else "ucLsb"
            read_seen += 1
            e.ln(f"iStatus = spec2codeI2cRegisterRead(spBus, {addr}, {mod}_CIT_REG_{s['reg']}, &{target});")
            e.check()
        elif sop == "read_registers":
            length = int(s.get("length", 1))
            width = int(regs.get(s["reg"], {}).get("width", 8))
            func = "spec2codeI2cRegisterReadWide" if width > 8 else "spec2codeI2cRegistersRead"
            e.ln(f"iStatus = {func}(spBus, {addr}, {mod}_CIT_REG_{s['reg']}, &ucArrBytes[{read_seen}U], {length}U);")
            e.check()
            read_seen += length
        elif sop == "read_channels":
            base, count = f"{mod}_CIT_REG_{s['reg']}", int(s.get("count", 8))
            e.open(f"for (ucIndex = 0U; ucIndex < {count}U; ucIndex++)")
            e.ln(f"iStatus = spec2codeI2cRegisterRead(spBus, {addr}, (unsigned char)({base} + (ucIndex * 2U)), &ucMsb);")
            e.check()
            e.ln(f"iStatus = spec2codeI2cRegisterRead(spBus, {addr}, (unsigned char)({base} + (ucIndex * 2U) + 1U), &ucLsb);")
            e.check()
            if convert:
                _convert(e, convert, "((unsigned short)ucMsb << 8) | (unsigned short)ucLsb")
                cvar = "uiCode" if convert.get("unsigned") else "iCode"
                e.ln(f"{_ptr_name(m)}[ucIndex] = ({m.c_type}){cvar};")
            else:
                e.ln(f"{_ptr_name(m)}[ucIndex] = ({m.c_type})(((unsigned short)ucMsb << 8) | (unsigned short)ucLsb);")
            e.close()
    if scalar:
        expr = cmodel._scalar_assign_expr(read_seen, m.c_type, byte_order, pieces)
        if convert:
            _convert(e, convert, expr)
            cvar = "uiCode" if convert.get("unsigned") else "iCode"
            e.ln(f"*{_ptr_name(m)} = ({m.c_type}){cvar};")
        else:
            e.ln(f"*{_ptr_name(m)} = ({m.c_type})({expr});")
    e.ln(f"return {STATUS_OK};")


def _ptr_name(m: _Measure) -> str:
    prefix = {"unsigned char": "ucp", "unsigned int": "uip", "int": "ip"}.get(m.c_type, "usp")
    return f"{prefix}{_pascal(m.name)}"


def _convert(e: _E, convert: dict, raw_expr: str) -> None:
    """cmodel._emit_convert_lines'i yerel yayiciyla kosturur (ayni tam sayi formulu)."""
    tmp = cmodel.Emit()
    tmp.level = e.level
    cmodel._emit_convert_lines(tmp, convert, raw_expr)
    e.lines.extend(tmp.out())


def _emit_spi_measure(plan: _ChipPlan, m: _Measure, e: _E) -> None:
    mod = plan.mod
    byte_order = plan.descriptor.get("transport", {}).get("byte_order", "big")
    pieces: list[dict[str, int]] = []
    read_seen = 0
    e.ln("unsigned char ucArrBytes[4];")
    e.ln("unsigned int uiDeger;")
    e.ln("int iStatus;")
    e.blank()
    for s in m.op.get("steps", []):
        sop = s.get("op")
        if sop == "comment":
            e.ln(f"/* {s.get('note', '')} */")
        elif sop == "read_register":
            piece = {"index": read_seen}
            for key in ("mask", "right_shift", "shift"):
                if key in s:
                    piece[key] = int(s[key])
            pieces.append(piece)
            e.ln(f"iStatus = {plan.module}CitSpiRegOku(spBus, spConfig, {mod}_CIT_REG_{s['reg']}, &uiDeger);")
            e.check()
            e.ln(f"ucArrBytes[{read_seen}U] = (unsigned char)(uiDeger & 0xFFU);")
            read_seen += 1
    if read_seen > 4:
        raise cmodel.CodegenError(f"{plan.device['id']} {m.name}: scalar reads are limited to 4 bytes")
    expr = cmodel._scalar_assign_expr(read_seen, m.c_type, byte_order, pieces)
    e.ln(f"*{_ptr_name(m)} = ({m.c_type})({expr});")
    e.ln(f"return {STATUS_OK};")


def _spi_register_read_func(plan: _ChipPlan, e: _E) -> None:
    model = tics.register_model(plan.descriptor)
    frame_bits = int(model.get("frame_bits", 24) or 24)
    address_bits = int(model.get("address_bits", 15) or 15)
    address_shift = int(model.get("address_shift", 8) or 8)
    data_bits = int(model.get("data_bits", 8) or 8)
    rw_bit = int(model.get("rw_bit", frame_bits - 1) or (frame_bits - 1))
    write_value = int(model.get("write_value", 0) or 0)
    read_value = 0 if write_value else 1
    mod = plan.mod
    e.ln(f"/* Okuma cercevesi: R/W biti {rw_bit} = {read_value}, adres << {address_shift}, veri {data_bits} bit")
    e.ln(f" * (descriptor register_model). Cevap ayni cercevenin son {data_bits} bitinde. */")
    e.ln(f"static int {plan.module}CitSpiRegOku(SSpec2codeSpiBus* spBus, const S{plan.pascal}CitConfig* spConfig,")
    e.ln(f"                                 unsigned int uiReg, unsigned int* uipDeger)")
    e.ln("{")
    e.level += 1
    e.ln(f"unsigned char ucArrTx[{mod}_CIT_SPI_FRAME_BYTES];")
    e.ln(f"unsigned char ucArrRx[{mod}_CIT_SPI_FRAME_BYTES];")
    e.ln("unsigned int uiWord;")
    e.ln("unsigned int uiIndex;")
    e.ln("int iStatus;")
    e.blank()
    e.ln(f"uiWord = ((unsigned int){read_value}U << {rw_bit}U) | "
         f"((uiReg & {_hex((1 << address_bits) - 1, 16)}) << {address_shift}U);")
    e.open(f"for (uiIndex = 0U; uiIndex < {mod}_CIT_SPI_FRAME_BYTES; uiIndex++)")
    e.ln(f"ucArrTx[uiIndex] = (unsigned char)((uiWord >> (8U * ({mod}_CIT_SPI_FRAME_BYTES - 1U - uiIndex))) & 0xFFU);")
    e.ln("ucArrRx[uiIndex] = 0U;")
    e.close()
    e.ln(f"iStatus = spec2codeSpiTransfer(spBus, spConfig->ucSpiSelect, ucArrTx, ucArrRx, {mod}_CIT_SPI_FRAME_BYTES);")
    e.check()
    e.ln("uiWord = 0U;")
    e.open(f"for (uiIndex = 0U; uiIndex < {mod}_CIT_SPI_FRAME_BYTES; uiIndex++)")
    e.ln("uiWord = (uiWord << 8U) | (unsigned int)ucArrRx[uiIndex];")
    e.close()
    e.ln(f"*uipDeger = uiWord & {_hex((1 << data_bits) - 1, 16)};")
    e.ln(f"return {STATUS_OK};")
    e.close()
    e.blank()


def _spi_register_write_func(plan: _ChipPlan, e: _E) -> None:
    mod = plan.mod
    e.ln(f"static int {plan.module}CitSpiRegYaz(SSpec2codeSpiBus* spBus, const S{plan.pascal}CitConfig* spConfig,")
    e.ln("                                  unsigned int uiWord)")
    e.ln("{")
    e.level += 1
    e.ln(f"unsigned char ucArrTx[{mod}_CIT_SPI_FRAME_BYTES];")
    e.ln("unsigned int uiIndex;")
    e.blank()
    e.open(f"for (uiIndex = 0U; uiIndex < {mod}_CIT_SPI_FRAME_BYTES; uiIndex++)")
    e.ln(f"ucArrTx[uiIndex] = (unsigned char)((uiWord >> (8U * ({mod}_CIT_SPI_FRAME_BYTES - 1U - uiIndex))) & 0xFFU);")
    e.close()
    e.ln(f"return spec2codeSpiTransfer(spBus, spConfig->ucSpiSelect, ucArrTx, (unsigned char*)0, {mod}_CIT_SPI_FRAME_BYTES);")
    e.close()
    e.blank()


def chip_source(plan: _ChipPlan) -> str:
    mod, pas, module = plan.mod, plan.pascal, plan.module
    bus_t = _bus_type(plan)
    is_i2c = plan.transport == "i2c"
    e = _E(0)
    e.ln("/**")
    e.ln(f" * @file {module}_cit.c")
    e.ln(f" * @brief {plan.part} CIT gerceklemesi (HAL uzerinden; surucu bagimsiz).")
    e.ln(" *")
    e.ln(" * Generated by Spec2Code. Do not edit by hand.")
    e.ln(" */")
    e.ln(f'#include "{module}_cit.h"')
    e.blank()
    e.ln(f"static const S{pas}CitConfig S_s{pas}CitConfigVarsayilan = {mod}_CIT_CONFIG_VARSAYILAN;")
    e.blank()

    # --- init verisi ---
    init_writes: list[dict] = []
    spi_words: list = []
    spi_model: dict = {}
    rewrite_word = None
    rewrite_delay = 0
    if is_i2c:
        init_writes = _i2c_init_writes(plan)
        if init_writes:
            e.ln("typedef struct")
            e.ln("{")
            e.ln("    unsigned char ucReg;")
            e.ln("    unsigned char ucValue;")
            e.ln("}" + f" S{pas}CitInitWrite;")
            e.blank()
            e.ln(f"#define {mod}_CIT_INIT_SEQUENCE_COUNT {len(init_writes)}U")
            e.blank()
            e.ln(f"static const S{pas}CitInitWrite S_sArr{pas}CitInitSequence[{mod}_CIT_INIT_SEQUENCE_COUNT] = " + "{")
            reg_by_name = {rg["name"]: rg for rg in plan.descriptor.get("registers", [])}
            for w in init_writes:
                off = int(reg_by_name.get(w["reg"], {}).get("offset", 0))
                e.ln(f"    {{{_hex(off)}, {_hex(int(w['value']) & 0xFF)}}}, /* {w['reg']}: {w.get('note', '')} */")
            e.ln("};")
            e.blank()
    else:
        spi_model = tics.register_model(plan.descriptor)
        spi_words = tics.decode_words(tics.normalize_words(plan.device.get("config")), spi_model)
        rewrite_delay = int(spi_model.get("rewrite_last_address_after_ms", 0) or 0)
        rewrite_addr = spi_model.get("rewrite_last_address")
        if rewrite_delay > 0 and rewrite_addr is not None:
            for item in spi_words:
                if item.address == int(rewrite_addr):
                    rewrite_word = item
        if spi_words:
            e.ln(f"#define {mod}_CIT_INIT_SEQUENCE_COUNT {len(spi_words)}U")
            e.blank()
            e.ln(f"static const unsigned int S_uiArr{pas}CitInitSequence[{mod}_CIT_INIT_SEQUENCE_COUNT] = " + "{")
            for item in spi_words:
                e.ln(f"    {tics.c_word(item.word)}, /* adres 0x{item.address:X}, deger 0x{item.value:X} */")
            e.ln("};")
            e.blank()
        _spi_register_write_func(plan, e)
        _spi_register_read_func(plan, e)
        if rewrite_word is not None:
            e.ln(f"static void {module}CitBekleMs(unsigned int uiMs)")
            e.ln("{")
            e.level += 1
            e.ln("unsigned int uiIndex;")
            e.ln("volatile unsigned int uiDelay;")
            e.blank()
            e.open("for (uiIndex = 0U; uiIndex < uiMs; uiIndex++)")
            e.open("for (uiDelay = 0U; uiDelay < 100000U; uiDelay++)")
            e.close()
            e.close()
            e.close()
            e.blank()

    # --- mux yardimcisi (i2c) ---
    if is_i2c:
        e.ln(f"static int {module}CitMuxSec({bus_t}* spBus, const S{pas}CitConfig* spConfig)")
        e.ln("{")
        e.level += 1
        e.open("if (spConfig->ucMuxAdres == 0U)")
        e.ln(f"return {STATUS_OK};")
        e.close()
        e.ln("return spec2codeI2cMuxSelect(spBus, spConfig->ucMuxAdres, spConfig->ucMuxKanal);")
        e.close()
        e.blank()

    # --- durum register okuyucu ---
    if plan.status_regs:
        if is_i2c:
            e.ln(f"static int {module}CitDurumRegOku({bus_t}* spBus, const S{pas}CitConfig* spConfig,")
            e.ln("                             unsigned char ucReg, unsigned int uiWidth, unsigned int* uipDeger)")
            e.ln("{")
            e.level += 1
            e.ln("unsigned char ucArrBytes[2];")
            e.ln("int iStatus;")
            e.blank()
            e.open("if (uiWidth > 8U)")
            e.ln("iStatus = spec2codeI2cRegisterReadWide(spBus, spConfig->ucI2cAdres, ucReg, ucArrBytes, 2U);")
            e.check()
            e.ln("*uipDeger = ((unsigned int)ucArrBytes[0] << 8U) | (unsigned int)ucArrBytes[1];")
            e.close()
            e.open("else")
            e.ln("iStatus = spec2codeI2cRegisterRead(spBus, spConfig->ucI2cAdres, ucReg, &ucArrBytes[0]);")
            e.check()
            e.ln("*uipDeger = (unsigned int)ucArrBytes[0];")
            e.close()
            e.ln(f"return {STATUS_OK};")
            e.close()
            e.blank()

    # --- olcum yardimcilari ---
    for m in plan.measures:
        sig = f"{m.c_type}* {_ptr_name(m)}"
        e.ln(f"/* {m.name}: {m.op.get('description', '')} */")
        e.ln(f"static int {m.func}({bus_t}* spBus, const S{pas}CitConfig* spConfig, {sig})")
        e.ln("{")
        e.level += 1
        if is_i2c:
            _emit_i2c_measure(plan, m, e)
        else:
            _emit_spi_measure(plan, m, e)
        e.close()
        e.blank()

    # --- init ---
    e.ln(f"int {module}CitInit({bus_t}* spBus, const S{pas}CitConfig* spConfig)")
    e.ln("{")
    e.level += 1
    e.ln("int iStatus;")
    if init_writes or spi_words:
        e.ln("unsigned int uiIndex;")
    e.blank()
    e.open(f"if (spBus == ({bus_t}*)0)")
    e.ln(f"return {STATUS_PARAM};")
    e.close()
    e.open(f"if (spConfig == (const S{pas}CitConfig*)0)")
    e.ln(f"spConfig = &S_s{pas}CitConfigVarsayilan;")
    e.close()
    if is_i2c:
        e.ln(f"iStatus = {module}CitMuxSec(spBus, spConfig);")
        e.check()
        if init_writes:
            e.open(f"for (uiIndex = 0U; uiIndex < {mod}_CIT_INIT_SEQUENCE_COUNT; uiIndex++)")
            e.ln("iStatus = spec2codeI2cRegisterWrite(spBus, spConfig->ucI2cAdres,")
            e.ln(f"                                    S_sArr{pas}CitInitSequence[uiIndex].ucReg,")
            e.ln(f"                                    S_sArr{pas}CitInitSequence[uiIndex].ucValue);")
            e.check()
            e.close()
        else:
            e.ln("/* Bu cihaz icin spec'te konfigurasyon yazimi yok: switch secimi yeterli. */")
            e.ln(f"iStatus = {STATUS_OK};")
    else:
        if spi_words:
            e.open(f"for (uiIndex = 0U; uiIndex < {mod}_CIT_INIT_SEQUENCE_COUNT; uiIndex++)")
            e.ln(f"iStatus = {module}CitSpiRegYaz(spBus, spConfig, S_uiArr{pas}CitInitSequence[uiIndex]);")
            e.check()
            e.close()
        else:
            e.ln("/* Bu cihaz icin spec'te TICS Pro register dizisi yok. */")
            e.ln(f"iStatus = {STATUS_OK};")
        if rewrite_word is not None:
            e.ln(f"{module}CitBekleMs({rewrite_delay}U);")
            e.ln(f"iStatus = {module}CitSpiRegYaz(spBus, spConfig, {tics.c_word(rewrite_word.word)});")
            e.check()
    e.ln("return iStatus;")
    e.close()
    e.blank()

    # --- read ---
    e.ln(f"int {module}CitRead({bus_t}* spBus, const S{pas}CitConfig* spConfig, S{pas}Cit* spCit)")
    e.ln("{")
    e.level += 1
    e.ln("int iStatus;")
    if plan.status_regs:
        e.ln("unsigned int uiDeger;")
    e.blank()
    e.open(f"if (spCit == (S{pas}Cit*)0)")
    e.ln(f"return {STATUS_PARAM};")
    e.close()
    e.ln("/* Once sifirla: her Ok biti ve deger asagida yeniden yazilir. */")
    e.ln("{")
    e.level += 1
    e.ln("unsigned char* ucpBayt = (unsigned char*)spCit;")
    e.ln("unsigned int uiIndex;")
    e.blank()
    e.open(f"for (uiIndex = 0U; uiIndex < sizeof(S{pas}Cit); uiIndex++)")
    e.ln("ucpBayt[uiIndex] = 0U;")
    e.close()
    e.close()
    e.open(f"if (spBus == ({bus_t}*)0)")
    e.ln("spCit->uiHataSayac = 1U;")
    e.ln(f"return {STATUS_PARAM};")
    e.close()
    e.open(f"if (spConfig == (const S{pas}CitConfig*)0)")
    e.ln(f"spConfig = &S_s{pas}CitConfigVarsayilan;")
    e.close()
    if is_i2c:
        e.ln(f"iStatus = {module}CitMuxSec(spBus, spConfig);")
        e.open(f"if (iStatus != {STATUS_OK})")
        e.ln("/* Switch acilamadi: arkasindaki hicbir okuma anlamli degil. */")
        e.ln("spCit->uiHataSayac = 1U;")
        e.ln("return iStatus;")
        e.close()
    for reg in plan.status_regs:
        e.ln(f"/* {reg.name}: bit bit */")
        if is_i2c:
            e.ln(f"iStatus = {module}CitDurumRegOku(spBus, spConfig, {mod}_CIT_REG_{reg.name}, {reg.width}U, &uiDeger);")
        else:
            e.ln(f"iStatus = {module}CitSpiRegOku(spBus, spConfig, {mod}_CIT_REG_{reg.name}, &uiDeger);")
        e.open(f"if (iStatus == {STATUS_OK})")
        cast = "unsigned char" if reg.width <= 8 else "unsigned short"
        e.ln(f"spCit->{reg.raw_field} = ({cast})uiDeger;")
        e.ln(f"spCit->sBayraklar.{reg.ok_bit} = 1U;")
        for cname, lo, width in reg.fields:
            mask = (1 << width) - 1
            shifted = f"(uiDeger >> {lo}U)" if lo else "uiDeger"
            e.ln(f"spCit->sBayraklar.{cname} = {shifted} & {_hex(mask, 8)};")
        e.close()
        e.open("else")
        e.ln("spCit->uiHataSayac++;")
        e.close()
    for m in plan.measures:
        arg = f"spCit->{m.field}" if m.count > 1 else f"&spCit->{m.field}"
        e.ln(f"/* {m.name}: {'dizi' if m.count > 1 else 'deger'} */")
        e.ln(f"iStatus = {m.func}(spBus, spConfig, {arg});")
        e.open(f"if (iStatus == {STATUS_OK})")
        e.ln(f"spCit->sBayraklar.{m.ok_bit} = 1U;")
        e.close()
        e.open("else")
        e.ln("spCit->uiHataSayac++;")
        e.close()
    e.open("if (spCit->uiHataSayac != 0U)")
    e.ln(f"return {STATUS_FAIL};")
    e.close()
    e.ln(f"return {STATUS_OK};")
    e.close()
    return e.text()


# --- sistem toplayici ------------------------------------------------------------------

def _controller_field(controller: dict) -> str:
    return "s" + _pascal(str(controller.get("id", "bus")))


def _device_field(device: dict) -> str:
    return "s" + _pascal(str(device.get("id", "dev")))


def _bus_controllers(spec: dict, plans: list[_ChipPlan]) -> list[dict]:
    seen: list[dict] = []
    ids = set()
    for plan in plans:
        cid = plan.controller.get("id")
        if cid not in ids:
            ids.add(cid)
            seen.append(plan.controller)
    return seen


def sistem_header(spec: dict, plans: list[_ChipPlan], skipped: list[tuple[str, str]]) -> str:
    controllers = _bus_controllers(spec, plans)
    e = _E(0)
    e.ln("/**")
    e.ln(" * @file spec2code_cit_sistem.h")
    e.ln(" * @brief Sistem CIT toplayici: her entegrenin CIT struct'i tek yapida, tek cagriyla.")
    e.ln(" *")
    e.ln(" * Kullanim (kart yazilimi):")
    e.ln(" *   static SSistemCitBus S_sBus;")
    e.ln(" *   static SSistemCit S_sCit;")
    e.ln(" *   sistemCitBusVarsayilan(&S_sBus);   -- spec'ten surucu turu/kimlikler")
    e.ln(" *   sistemCitInit(&S_sBus);            -- bus'lar + entegre ilklendirmeleri")
    e.ln(" *   sistemCitRead(&S_sBus, &S_sCit);   -- periyodik: struct bit bit dolar")
    e.ln(" *")
    if skipped:
        e.ln(" * CIT dosyasi uretilmeyen cihazlar (kapsam disi transport):")
        for did, why in skipped:
            e.ln(f" *   - {did}: {why}")
        e.ln(" *")
    e.ln(" * Generated by Spec2Code. Do not edit by hand.")
    e.ln(" */")
    e.ln("#ifndef SPEC2CODE_CIT_SISTEM_H")
    e.ln("#define SPEC2CODE_CIT_SISTEM_H")
    e.blank()
    e.ln('#include "spec2code_cit_port.h"')
    if any(c.get("type") == "i2c" for c in controllers):
        e.ln('#include "spec2code_i2c_bus.h"')
    if any(c.get("type") == "spi" for c in controllers):
        e.ln('#include "spec2code_spi_bus.h"')
    for plan in plans:
        e.ln(f'#include "{plan.module}_cit.h"')
    e.blank()
    e.ln(f"#define SISTEM_CIT_CIHAZ_SAYISI {len(plans)}U")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Sistemdeki bus'lar (denetleyici basina bir sarmalayici; alan adi = denetleyici id).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for c in controllers:
        t = "SSpec2codeI2cBus" if c.get("type") == "i2c" else "SSpec2codeSpiBus"
        e.ln(f"    {t} {_controller_field(c)}; /* {c.get('id')} ({c.get('instance', '')}) */")
    e.ln("} SSistemCitBus;")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Butun entegrelerin CIT sonucu (alan adi = spec cihaz id'si).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    e.ln("    unsigned int uiSayac;     /* kac kez kosuldu                              */")
    e.ln("    unsigned int uiHataSayac; /* bu kosuda toplam basarisiz erisim (0 = temiz) */")
    for plan in plans:
        e.ln(f"    S{plan.pascal}Cit {_device_field(plan.device)}; /* {plan.device['id']} ({plan.part}) */")
    e.ln("} SSistemCit;")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Bus tanimlarini spec'ten gelen varsayilanlarla doldurur (surucu turu, device id,")
    e.ln(" *        taban adres, SCL). Xilinx disi portta surucu KULLANICI olarak isaretlenir.")
    e.ln(" * @param spBus Doldurulacak bus kumesi.")
    e.ln(" */")
    e.ln("void sistemCitBusVarsayilan(SSistemCitBus* spBus);")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Bus'lari ve entegreleri sirayla ilklendirir; biri dusse de DEVAM eder,")
    e.ln(" *        ILK hata kodunu dondurur (kismi ilklendirme sahada degerlidir).")
    e.ln(" * @param spBus Varsayilanla (ya da elle) doldurulmus bus kumesi.")
    e.ln(" * @return SPEC2CODE_CIT_OK ya da ilk hata.")
    e.ln(" */")
    e.ln("int sistemCitInit(SSistemCitBus* spBus);")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Butun entegrelerin CIT okumasini yapar; spCit tamamen yeniden doldurulur.")
    e.ln(" * @param spBus Hazir bus kumesi.")
    e.ln(" * @param spCit Sonuc.")
    e.ln(" * @return SPEC2CODE_CIT_OK (hicbir erisim dusmedi) ya da SPEC2CODE_CIT_HATA.")
    e.ln(" */")
    e.ln("int sistemCitRead(SSistemCitBus* spBus, SSistemCit* spCit);")
    e.blank()
    from orchestrator import cit_sim  # dongusel import: cit_sim, cit_layer'in yardimcilarini kullanir
    e.lines.extend(cit_sim.sistem_sim_header_section(spec, plans, _controller_field, _device_field))
    e.ln("#endif /* SPEC2CODE_CIT_SISTEM_H */")
    return e.text()


def sistem_source(spec: dict, plans: list[_ChipPlan]) -> str:
    controllers = _bus_controllers(spec, plans)
    e = _E(0)
    e.ln("/**")
    e.ln(" * @file spec2code_cit_sistem.c")
    e.ln(" * @brief Sistem CIT toplayici gerceklemesi. Generated by Spec2Code.")
    e.ln(" */")
    e.ln('#include "spec2code_cit_sistem.h"')
    e.blank()
    e.ln("#if SPEC2CODE_CIT_PORT_XILINX")
    e.ln('#include "xparameters.h"')
    e.ln("#endif")
    e.blank()
    for plan in plans:
        e.ln(f"static const S{plan.pascal}CitConfig S_s{_pascal(plan.device['id'])}Config = {plan.mod}_CIT_CONFIG_VARSAYILAN;")
    e.blank()
    e.ln("static unsigned int S_uiSistemCitSayac = 0U;")
    e.blank()
    e.ln("void sistemCitBusVarsayilan(SSistemCitBus* spBus)")
    e.ln("{")
    e.level += 1
    e.ln("unsigned char* ucpBayt = (unsigned char*)spBus;")
    e.ln("unsigned int uiIndex;")
    e.blank()
    e.open("if (spBus == (SSistemCitBus*)0)")
    e.ln("return;")
    e.close()
    e.open("for (uiIndex = 0U; uiIndex < sizeof(SSistemCitBus); uiIndex++)")
    e.ln("ucpBayt[uiIndex] = 0U;")
    e.close()
    for index, c in enumerate(controllers):
        fld = _controller_field(c)
        htype, _ = cmodel._handle_for(c)
        inst = str(c.get("instance", ""))
        e.ln(f"spBus->{fld}.uiPortIndex = {index}U;")
        if htype == "XIicPs":
            e.ln("#if SPEC2CODE_CIT_PORT_XIICPS")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_I2C_SURUCU_XIICPS;")
            e.ln(f"spBus->{fld}.uiDeviceId = {inst}_DEVICE_ID;")
            e.ln(f"spBus->{fld}.uiSclkHz = 100000U;")
            e.ln("#else")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_I2C_SURUCU_KULLANICI;")
            e.ln("#endif")
        elif htype == "XIic":
            e.ln("#if SPEC2CODE_CIT_PORT_XIIC")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_I2C_SURUCU_XIIC;")
            e.ln(f"spBus->{fld}.ulTabanAdres = (unsigned long){inst}_BASEADDR;")
            e.ln("#else")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_I2C_SURUCU_KULLANICI;")
            e.ln("#endif")
        elif htype == "XSpiPs":
            e.ln("#if SPEC2CODE_CIT_PORT_XSPIPS")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_SPI_SURUCU_XSPIPS;")
            e.ln(f"spBus->{fld}.uiDeviceId = {inst}_DEVICE_ID;")
            e.ln("#else")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_SPI_SURUCU_KULLANICI;")
            e.ln("#endif")
        else:
            e.ln("#if SPEC2CODE_CIT_PORT_XSPI")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_SPI_SURUCU_XSPI;")
            e.ln(f"spBus->{fld}.uiDeviceId = {inst}_DEVICE_ID;")
            e.ln("#else")
            e.ln(f"spBus->{fld}.eSurucu = SPEC2CODE_SPI_SURUCU_KULLANICI;")
            e.ln("#endif")
    e.close()
    e.blank()
    e.ln("int sistemCitInit(SSistemCitBus* spBus)")
    e.ln("{")
    e.level += 1
    e.ln("int iIlkHata = SPEC2CODE_CIT_OK;")
    e.ln("int iStatus;")
    e.blank()
    e.open("if (spBus == (SSistemCitBus*)0)")
    e.ln(f"return {STATUS_PARAM};")
    e.close()
    for c in controllers:
        fld = _controller_field(c)
        fn = "spec2codeI2cBusInit" if c.get("type") == "i2c" else "spec2codeSpiBusInit"
        e.ln(f"iStatus = {fn}(&spBus->{fld});")
        e.open(f"if ((iStatus != {STATUS_OK}) && (iIlkHata == {STATUS_OK}))")
        e.ln("iIlkHata = iStatus;")
        e.close()
    for plan in plans:
        fld = _controller_field(plan.controller)
        e.ln(f"iStatus = {plan.module}CitInit(&spBus->{fld}, &S_s{_pascal(plan.device['id'])}Config);")
        e.open(f"if ((iStatus != {STATUS_OK}) && (iIlkHata == {STATUS_OK}))")
        e.ln("iIlkHata = iStatus;")
        e.close()
    e.ln("return iIlkHata;")
    e.close()
    e.blank()
    e.ln("int sistemCitRead(SSistemCitBus* spBus, SSistemCit* spCit)")
    e.ln("{")
    e.level += 1
    e.open("if ((spBus == (SSistemCitBus*)0) || (spCit == (SSistemCit*)0))")
    e.ln(f"return {STATUS_PARAM};")
    e.close()
    e.ln("S_uiSistemCitSayac++;")
    e.ln("spCit->uiSayac = S_uiSistemCitSayac;")
    e.ln("spCit->uiHataSayac = 0U;")
    for plan in plans:
        fld = _controller_field(plan.controller)
        dev = _device_field(plan.device)
        e.ln(f"(void){plan.module}CitRead(&spBus->{fld}, &S_s{_pascal(plan.device['id'])}Config, &spCit->{dev});")
        e.ln(f"spCit->uiHataSayac += spCit->{dev}.uiHataSayac;")
    e.open("if (spCit->uiHataSayac != 0U)")
    e.ln(f"return {STATUS_FAIL};")
    e.close()
    e.ln(f"return {STATUS_OK};")
    e.close()
    from orchestrator import cit_sim
    sim_lines = cit_sim.sistem_sim_source_section(spec, plans, _controller_field, _device_field)
    if sim_lines:
        e.blank()
        e.lines.extend(sim_lines)
    return e.text()


# --- README bolumu ---------------------------------------------------------------------

def readme_section(plans: list[_ChipPlan], skipped: list[tuple[str, str]]) -> str:
    lines = [
        "",
        "## CIT entegre katmani (`cit/`)",
        "",
        "Kendi gomulu yazilimina oldugu gibi tasinabilen, hiyerarsik CIT katmani:",
        "",
        "| Katman | Dosya | Icerik |",
        "|---|---|---|",
        "| Port | `cit/hal/spec2code_cit_port.h` | platform secimi (`#ifndef` korumali), durum kodlari |",
        "| HAL | `cit/hal/spec2code_i2c_bus.h/.c` | `SSpec2codeI2cBus`: XIicPs / XIic / kullanici portu |",
        "| HAL | `cit/hal/spec2code_spi_bus.h/.c` | `SSpec2codeSpiBus`: XSpiPs / XSpi / kullanici portu |",
    ]
    for plan in plans:
        lines.append(f"| Entegre | `cit/{plan.module}_cit.h/.c` | `S{plan.pascal}CitConfig`, `S{plan.pascal}Cit`, "
                     f"`{plan.module}CitInit()`, `{plan.module}CitRead()` |")
    lines.append("| Sistem | `cit/spec2code_cit_sistem.h/.c` | `SSistemCitBus`, `SSistemCit`, `sistemCitInit()`, `sistemCitRead()` |")
    from orchestrator import cit_sim
    sims = cit_sim.sim_plans(plans)
    if sims:
        lines.append("| Simulasyon | `cit/hal/spec2code_i2c_sim.h/.c` | sanal switch (TCA9548A modeli), hata enjeksiyon kodlari |")
        for plan in sims:
            extra = " + davranis (READY bitleri, kod uretimi)" if cit_sim.has_behavior(plan) else ""
            lines.append(f"| Simulasyon | `cit/sim/{plan.module}_sim.h/.c` | `S{plan.pascal}Sim`: descriptor register modeli{extra}; "
                         f"`{plan.module}SimKur()`, `{plan.module}SimHataAyarla()` |")
        lines.append("| Simulasyon | `cit/spec2code_cit_sistem.h/.c` | `SSistemCitSim`, `sistemCitSimKur()`, `sistemCitSimEkle()` (karisik mod), `sistemCitSimSwitchEkle()` (tam sanal) |")
    lines.extend([
        "",
        "`S<Mod>Cit` icinde durum registerleri **bit bit** (descriptor alan tanimlariyla), olcumler",
        "**bayt/kelime** olarak durur; her register ve olcum icin `ui...Ok : 1` okuma-basari biti vardir.",
        "Adres / mux kanali / poll timeout `S<Mod>CitConfig` ile calisma zamaninda degistirilir",
        "(`<MOD>_CIT_CONFIG_VARSAYILAN` spec'ten gelir). Xilinx disi bir MCU'ya tasirken",
        "`spec2code_cit_port.h` icinde `SPEC2CODE_CIT_PORT_KULLANICI 1` yapip HAL basliklarinin",
        "sonundaki port fonksiyonlarini gerceklemek yeterlidir.",
        "",
        "**Karisik mod / simulasyon:** `sistemCitSimKur(&sSim); spec2codeI2cSimEkle(&sBus.s<Bus>,",
        "&sSim.s<Cihaz>.sCihaz);` ile takili olmayan entegre SANAL cevap verir, ayni bus'taki digerleri",
        "gercek donanima gider. Donanimsiz kosumda bus'in `eSurucu`'su `SPEC2CODE_I2C_SURUCU_SIM` yapilir",
        "ve `sistemCitSimSwitchEkle()` ile sanal switch'ler de takilir. `<mod>SimHataAyarla()` NACK ya da",
        "hazir-biti-yok senaryolarini enjekte eder. `SPEC2CODE_CIT_SIM 0` ile tamamen derleme disi kalir.",
    ])
    if skipped:
        lines.append("")
        lines.append("CIT dosyasi uretilmeyen cihazlar: " + ", ".join(f"`{d}` ({w})" for d, w in skipped) + ".")
    lines.append("")
    return "\n".join(lines)


# --- giris noktasi ---------------------------------------------------------------------

def skipped_devices(spec: dict, get_descriptor: Callable[[str], dict], plans: list[_ChipPlan]) -> list[tuple[str, str]]:
    covered = {p.device["id"] for p in plans}
    out: list[tuple[str, str]] = []
    for device in spec.get("devices", []):
        if device["id"] in covered:
            continue
        descriptor = get_descriptor(device.get("descriptor_ref") or device["part"])
        transport = str(descriptor.get("transport", {}).get("type", ""))
        if transport == "gpio":
            why = "GPIO hat cihazi"
        elif descriptor.get("memory"):
            why = "I2C EEPROM"
        elif transport == "spi" and not tics.has_tics_register_model(descriptor):
            why = "komut tabanli SPI flash"
        else:
            why = "okunabilir durum registeri / olcum op'u yok"
        out.append((str(device["id"]), why))
    return out


def write_cit_layer(spec: dict, out_dir: Path, get_descriptor: Callable[[str], dict],
                    manifest_devices: list[dict]) -> tuple[list[str], str]:
    """cit/ agacini yazar; (yazilan yollar, README bolumu) dondurur. Cihaz yoksa bos."""
    plans = build_plans(spec, get_descriptor, manifest_devices)
    if not plans:
        return [], ""
    cit_dir = out_dir / "cit"
    hal_dir = cit_dir / "hal"
    written: list[Path] = [
        hio.write_output(hal_dir / "spec2code_cit_port.h", port_header(spec)),
    ]
    controllers = _bus_controllers(spec, plans)
    if any(c.get("type") == "i2c" for c in controllers):
        written.append(hio.write_output(hal_dir / "spec2code_i2c_bus.h", i2c_bus_header()))
        written.append(hio.write_output(hal_dir / "spec2code_i2c_bus.c", i2c_bus_source()))
    if any(c.get("type") == "spi" for c in controllers):
        written.append(hio.write_output(hal_dir / "spec2code_spi_bus.h", spi_bus_header()))
        written.append(hio.write_output(hal_dir / "spec2code_spi_bus.c", spi_bus_source()))
    for plan in plans:
        written.append(hio.write_output(cit_dir / f"{plan.module}_cit.h", chip_header(plan)))
        written.append(hio.write_output(cit_dir / f"{plan.module}_cit.c", chip_source(plan)))
    # Simulasyon: sanal switch (HAL) + entegre basina register-modeli simulatoru (cit/sim/).
    from orchestrator import cit_sim
    sims = cit_sim.sim_plans(plans)
    if sims:
        written.append(hio.write_output(hal_dir / "spec2code_i2c_sim.h", cit_sim.i2c_sim_header()))
        written.append(hio.write_output(hal_dir / "spec2code_i2c_sim.c", cit_sim.i2c_sim_source()))
        for plan in sims:
            written.append(hio.write_output(cit_dir / "sim" / f"{plan.module}_sim.h", cit_sim.sim_header(plan)))
            written.append(hio.write_output(cit_dir / "sim" / f"{plan.module}_sim.c", cit_sim.sim_source(plan)))
    skipped = skipped_devices(spec, get_descriptor, plans)
    written.append(hio.write_output(cit_dir / "spec2code_cit_sistem.h", sistem_header(spec, plans, skipped)))
    written.append(hio.write_output(cit_dir / "spec2code_cit_sistem.c", sistem_source(spec, plans)))
    return [str(p) for p in written], readme_section(plans, skipped)
