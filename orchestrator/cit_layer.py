"""CIT ust katmani (``outputs/<proje>/cit/``): surucu struct'larini ANLAMLANDIRAN katman.

Tasarim: docs/superpowers/specs/2026-09-06-driver-struct-api-design.md

Surucu (``drivers/<mod>.*``) Xilinx API'sini dogrudan cagirir ve ham veriyi kendi
struct'larinda verir (``S<Mod>Status`` bit bit, ``S<Mod>Voltage`` kanal dizisi, skaler
``int``/``unsigned short``). Bu katman o fonksiyonlari cagirir ve UST SEVIYE anlam ekler:
hangi olcumlerin okunacagi, limit (kapali aralik [min, max]; min == max gecerli), etkin,
OK/NOK bitleri, hata/NOK
sayaclari. Kullanici bu klasoru ``drivers/`` ile birlikte kendi yazilimina tasir.

Uretilen agac:
* ``cit/cit_ortak.h/.c``   - ``SCitLimit`` + ``citLimitDegerlendir`` + CIT_OK/NOK/HATA.
* ``cit/<mod>_cit.h/.c``   - ``S<Mod>CitLimit`` (spec varsayilani ``<MOD>_CIT_LIMIT_VARSAYILAN``),
                             ``S<Mod>Cit`` (bayraklar + ``S<Mod>Status`` + olcumler),
                             ``<mod>CitInit`` / ``<mod>CitRead``.
* ``cit/sistem_cit.h/.c``  - ``SSistemCitBus`` (denetleyici handle'lari), ``SSistemCitLimit``,
                             ``SSistemCit``; ``sistemCitBusVarsayilan/Init/Read``.

Kapsam: I2C register cihazlari ve SPI TICS-register cihazlari (durum registeri ya da
birimli olcum op'u olanlar). Sanal cihaz simulatorleri ``tests/sim/`` altindadir
(``orchestrator/cit_sim.py``); bu katman onlari bilmez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from hostplat import io as hio
from orchestrator import cmodel, tics

_IND = "    "

STATUS_OK = "CIT_OK"
STATUS_NOK = "CIT_NOK"
STATUS_FAIL = "CIT_HATA"


# --- kucuk yardimcilar ------------------------------------------------------------------

def _pascal(text: str) -> str:
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", str(text)) if p]
    out = "".join(p[:1].upper() + p[1:].lower() for p in parts)
    if out and not out[0].isalpha():
        out = "X" + out
    return out or "X"


def _hex(value: int, width: int = 8) -> str:
    digits = max(2, (width + 3) // 4)
    return f"0x{value:0{digits}X}U"


class _E:
    """Girintili C satir yayicisi."""

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

    def blank(self) -> "_E":
        self.lines.append("")
        return self

    def text(self) -> str:
        return "\n".join(self.lines)


@dataclass
class _Channel:
    label: str         # V1 / Temperature
    ok_bit: str        # uiV1Ok
    limit_field: str   # sV1
    index: int         # dizi indeksi (skalerde 0)
    olcum: dict        # manifest cit olcumu (name/min/max/severity/enabled)


@dataclass
class _Measure:
    name: str          # op adi
    func: str          # surucu fonksiyonu (ltc2991VoltageRead)
    is_array: bool
    ctype: str         # surucu cikti tipi: SLtc2991Voltage / int / unsigned short ...
    field: str         # S<Mod>Cit alani: sVoltage / iTemperature
    array_field: str   # usArrVoltage (dizi)
    op_ok: str         # uiVoltageReadOk
    unit: str
    channels: list[_Channel] = field(default_factory=list)


@dataclass
class _ChipPlan:
    device: dict
    descriptor: dict
    controller: dict
    module: str
    part: str
    transport: str     # i2c / spi
    htype: str = ""
    hvar: str = ""
    status_regs: list = field(default_factory=list)   # cmodel.StatusRegPlan
    measures: list[_Measure] = field(default_factory=list)
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

    @property
    def handle_param(self) -> str:
        return cmodel._handle_param(self.htype, self.hvar)

    @property
    def has_status(self) -> bool:
        return bool(self.status_regs)


def bitfield_bytes(widths: list[int]) -> int:
    """GCC ``unsigned int`` bit alani yerlesimi: 32-bit birim, sigmayan alan sonraki birime."""
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

_SCALAR_PREFIX = {"unsigned char": "uc", "unsigned int": "ui", "int": "i", "unsigned short": "us"}


def _scalar_noun(op_name: str) -> str:
    base = op_name[:-5] if op_name.endswith("_read") else op_name
    return _pascal(base)


def _measures(plan: _ChipPlan, olcumler: list[dict]) -> None:
    ops_by_name = {op["name"]: op for op in plan.descriptor.get("operations", [])}
    used: set[str] = set()
    by_op: dict[str, list[dict]] = {}
    for m in olcumler:
        if m.get("device") != plan.device.get("id"):
            continue
        by_op.setdefault(str(m.get("op", "")), []).append(m)
    for op_name, entries in by_op.items():
        op = ops_by_name.get(op_name)
        if op is None:
            continue
        returns = str(op.get("returns", ""))
        info = cmodel._array_return_info(plan.module, returns)
        func = cmodel._func_name(plan.module, op_name)
        if info:
            measure = _Measure(name=op_name, func=func, is_array=True, ctype=info["ctype"],
                               field=f"s{info['noun']}", array_field=info["field"],
                               op_ok=f"ui{_pascal(op_name)}Okundu", unit=str(entries[0].get("unit") or ""))
            for m in sorted(entries, key=lambda x: int(x.get("channel", 0))):
                label = str(m.get("channel_label") or f"{info['noun']}{int(m.get('channel', 0)) + 1}")
                measure.channels.append(_Channel(
                    label=label, ok_bit=f"ui{_pascal(label)}Ok", limit_field=f"s{_pascal(label)}",
                    index=int(m.get("channel", 0)), olcum=m))
        else:
            ctype, _p = cmodel._return_param(op_name, returns)
            noun = _scalar_noun(op_name)
            measure = _Measure(name=op_name, func=func, is_array=False, ctype=ctype,
                               field=f"{_SCALAR_PREFIX.get(ctype, 'us')}{noun}", array_field="",
                               op_ok=f"ui{_pascal(op_name)}Okundu", unit=str(entries[0].get("unit") or ""))
            measure.channels.append(_Channel(
                label=noun, ok_bit=f"ui{noun}Ok", limit_field=f"s{noun}", index=0, olcum=entries[0]))
        for ch in measure.channels:
            if ch.ok_bit in used or ch.limit_field in used:
                raise cmodel.CodegenError(
                    f"{plan.device.get('id')}: CIT alan adi cakismasi ({ch.ok_bit}) - op adlarini gozden gecirin")
            used.add(ch.ok_bit)
            used.add(ch.limit_field)
        plan.measures.append(measure)


def build_plans(spec: dict, get_descriptor: Callable[[str], dict],
                manifest_devices: list[dict], cit_olcumler: Optional[list[dict]] = None) -> list[_ChipPlan]:
    """Cihaz basina plan: surucu durum yapisi + manifest CIT olcumleri (kanal bazli)."""
    controllers = {c["id"]: c for c in spec.get("controllers", [])}
    muxes = {m["id"]: m for m in spec.get("muxes", [])}
    modules = cmodel.device_module_map(spec)
    olcumler = cit_olcumler or []
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
        htype, hvar = cmodel._handle_for(controller)
        if htype not in {"XIicPs", "XIic", "XSpiPs", "XSpi"}:
            continue
        plan = _ChipPlan(device=device, descriptor=descriptor, controller=controller,
                         module=modules.get(device["id"], cmodel._module_of(device["part"])),
                         part=str(device["part"]), transport=transport, htype=htype, hvar=hvar)
        attach = device["attach"]
        if transport == "i2c":
            plan.i2c_addr = int(str(attach["i2c_address"]), 0)
            via = attach.get("via_mux")
            if via and via.get("mux_id") in muxes:
                plan.mux_addr = int(str(muxes[via["mux_id"]]["i2c_address"]), 0)
                plan.mux_channel = int(via.get("channel", 0))
        else:
            plan.spi_select = int(attach.get("spi_chip_select", 0))
        regs = cmodel.status_register_plans(descriptor)
        plan.status_regs = regs if transport == "i2c" else [r for r in regs if r.width <= 8]
        _measures(plan, olcumler)
        if not plan.status_regs and not plan.measures:
            continue
        plans.append(plan)
    return plans


# --- cit_ortak --------------------------------------------------------------------------

def ortak_header() -> str:
    return """/**
 * @file cit_ortak.h
 * @brief CIT ust katmani ortak tipleri: olcum limiti ve degerlendirme, durum kodlari.
 *
 * Generated by Spec2Code. Do not edit by hand.
 */
#ifndef CIT_ORTAK_H
#define CIT_ORTAK_H

#define CIT_OK 0   /* butun okumalar basarili, etkin olcumler limit icinde */
#define CIT_NOK 1  /* okumalar basarili, en az bir etkin olcum limit disi   */
#define CIT_HATA 2 /* en az bir surucu cagrisi dustu (bus/NACK/timeout)      */

/**
 * @brief Bir olcumun (ya da kanalin) degerlendirme politikasi. Spec varsayilani
 *        <MOD>_CIT_LIMIT_VARSAYILAN ile gelir; calisma zamaninda degistirilebilir.
 */
typedef struct
{
    int iMin;                    /* alt limit (kapali aralik; uiLimitVar == 1 ise gecerli) */
    int iMax;                    /* ust limit (iMin == iMax gecerli: tek kabul edilen deger)*/
    unsigned int uiLimitVar : 1; /* 0 = limitsiz (okundu ise OK)                           */
    unsigned int uiEtkin : 1;    /* 0 = olcum degerlendirilmez (OK sayilir)                 */
} SCitLimit;

/**
 * @brief Degeri limite gore degerlendirir: iMin <= iDeger <= iMax ise OK.
 * @return 1 = OK (etkin degil, limit yok ya da aralikta), 0 = NOK (aralik disi).
 */
unsigned int citLimitDegerlendir(const SCitLimit* spLimit, int iDeger);

#endif /* CIT_ORTAK_H */
"""


def ortak_source() -> str:
    return """/**
 * @file cit_ortak.c
 * @brief CIT ortak degerlendirme. Generated by Spec2Code.
 */
#include "cit_ortak.h"

unsigned int citLimitDegerlendir(const SCitLimit* spLimit, int iDeger)
{
    if ((spLimit == (const SCitLimit*)0) || (spLimit->uiEtkin == 0U) || (spLimit->uiLimitVar == 0U))
    {
        return 1U;
    }
    if ((iDeger < spLimit->iMin) || (iDeger > spLimit->iMax))
    {
        return 0U;
    }
    return 1U;
}
"""


# --- entegre CIT: baslik ----------------------------------------------------------------

def _limit_initializer(olcum: dict) -> str:
    mn, mx = olcum.get("min"), olcum.get("max")
    has = isinstance(mn, (int, float)) and isinstance(mx, (int, float))
    etkin = 1 if olcum.get("enabled", True) else 0
    return f"{{{int(mn) if has else 0}, {int(mx) if has else 0}, {1 if has else 0}U, {etkin}U}}"


def _flag_entries(plan: _ChipPlan) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    if plan.has_status:
        entries.append(("uiStatusRegistersOkundu", f"{plan.module}StatusRegistersRead basarili"))
    for m in plan.measures:
        entries.append((m.op_ok, f"{m.name} okundu"))
    for m in plan.measures:
        for ch in m.channels:
            entries.append((ch.ok_bit, f"{ch.olcum.get('name', ch.label)}: okundu VE limit icinde (etkin degilse 1)"))
    return entries


def chip_header(plan: _ChipPlan) -> str:
    mod, pas, module = plan.mod, plan.pascal, plan.module
    entries = _flag_entries(plan)
    flag_bytes = bitfield_bytes([1] * len(entries))
    e = _E(0)
    e.ln("/**")
    e.ln(f" * @file {module}_cit.h")
    e.ln(f" * @brief {plan.part} CIT (ust seviye): surucu struct'larini limitle anlamlandirir.")
    e.ln(" *")
    e.ln(f" *   {plan.descriptor.get('summary', '')}")
    e.ln(" *")
    e.ln(f" * Surucu ({module}.h) ham veriyi verir; bu katman HANGI olcumlerin okunacagini bilir,")
    e.ln(" * limit/etkin politikasini uygular ve OK/NOK bitlerini doldurur (aralik kapali: min <= deger <= max).")
    e.ln(" * Generated by Spec2Code. Do not edit by hand.")
    e.ln(" */")
    e.ln(f"#ifndef {mod}_CIT_H")
    e.ln(f"#define {mod}_CIT_H")
    e.blank()
    e.ln(f'#include "{module}.h"')
    e.ln('#include "cit_ortak.h"')
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} olcum limitleri (olcum/kanal basina). Varsayilan spec'ten.")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for m in plan.measures:
        for ch in m.channels:
            unit = f", {m.unit}" if m.unit else ""
            e.ln(f"    SCitLimit {ch.limit_field}; /* {ch.olcum.get('name', ch.label)} ({m.name}{unit}) */")
    if not plan.measures:
        e.ln("    unsigned int uiYok; /* olcum op'u yok; yalniz durum registerleri */")
    e.ln("}" + f" S{pas}CitLimit;")
    e.blank()
    inits = [_limit_initializer(ch.olcum) for m in plan.measures for ch in m.channels] or ["0U"]
    e.ln(f"#define {mod}_CIT_LIMIT_VARSAYILAN \\")
    for i, init in enumerate(inits):
        tail = "," if i < len(inits) - 1 else ""
        prefix = "    {" if i == 0 else "     "
        suffix = "}" if i == len(inits) - 1 else " \\"
        e.ln(f"{prefix}{init}{tail}{suffix}")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief BIT BIT bayraklar: op okuma-basari bitleri, sonra olcum/kanal OK bitleri")
    e.ln(" *        (okundu VE limit icinde; etkin olmayan olcum 1 sayilir).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for cname, comment in entries:
        e.ln(f"    unsigned int {cname} : 1; /* {comment} */")
    e.ln("}" + f" S{pas}CitBayraklar;")
    e.blank()
    e.ln(f"_Static_assert(sizeof(S{pas}CitBayraklar) == {flag_bytes}U, "
         f"\"S{pas}CitBayraklar {flag_bytes} bayt olmalidir\");")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} CIT sonucu: bayraklar + surucu durum yapisi + olcumler.")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    e.ln(f"    S{pas}CitBayraklar sBayraklar;")
    if plan.has_status:
        e.ln(f"    S{pas}Status sDurum; /* {module}StatusRegistersRead: durum registerleri bit bit */")
    for m in plan.measures:
        unit = f", birim {m.unit}" if m.unit else ""
        e.ln(f"    {m.ctype} {m.field}; /* {m.name}{unit} */")
    e.ln("    unsigned int uiHataSayac; /* dusen surucu cagrisi sayisi (0 = hepsi okundu) */")
    e.ln("    unsigned int uiNokSayac;  /* limit disi etkin olcum sayisi                  */")
    e.ln("}" + f" S{pas}Cit;")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} ilklendirme (surucu {module}DeviceInit).")
    e.ln(f" * @param {plan.hvar} Denetleyici handle'i.")
    e.ln(" * @return CIT_OK ya da CIT_HATA.")
    e.ln(" */")
    e.ln(f"int {module}CitInit({plan.handle_param});")
    e.blank()
    e.ln("/**")
    e.ln(f" * @brief {plan.part} CIT okumasi: surucu fonksiyonlarini cagirir, limitle degerlendirir.")
    e.ln(" *        Bir okuma dusse de digerlerine DEVAM eder.")
    e.ln(f" * @param {plan.hvar} Denetleyici handle'i.")
    e.ln(" * @param spLimit Limit politikasi (NULL -> <MOD>_CIT_LIMIT_VARSAYILAN).")
    e.ln(" * @param spCit Doldurulacak sonuc (once sifirlanir).")
    e.ln(" * @return CIT_OK / CIT_NOK (limit disi) / CIT_HATA (okuma dustu).")
    e.ln(" */")
    e.ln(f"int {module}CitRead({plan.handle_param}, const S{pas}CitLimit* spLimit, S{pas}Cit* spCit);")
    e.blank()
    e.ln(f"#endif /* {mod}_CIT_H */")
    return e.text()


# --- entegre CIT: kaynak ----------------------------------------------------------------

def chip_source(plan: _ChipPlan) -> str:
    mod, pas, module = plan.mod, plan.pascal, plan.module
    h = plan.hvar
    e = _E(0)
    e.ln("/**")
    e.ln(f" * @file {module}_cit.c")
    e.ln(f" * @brief {plan.part} CIT gerceklemesi: surucu -> limit -> OK/NOK. Generated by Spec2Code.")
    e.ln(" */")
    e.ln(f'#include "{module}_cit.h"')
    e.ln('#include "xstatus.h"')
    e.ln("#include <stddef.h>")
    e.ln("#include <string.h>")
    e.blank()
    e.ln(f"static const S{pas}CitLimit S_s{pas}CitLimitVarsayilan = {mod}_CIT_LIMIT_VARSAYILAN;")
    e.blank()
    e.ln("/* Olcumu degerlendirir; NOK ise sayaci artirir. Donus: OK biti (1/0). */")
    e.ln(f"static unsigned int {module}CitOlcum(const SCitLimit* spLimit, int iDeger, unsigned int* uipNok)")
    e.ln("{")
    e.ln("    unsigned int uiOk = citLimitDegerlendir(spLimit, iDeger);")
    e.blank()
    e.ln("    if (uiOk == 0U)")
    e.ln("    {")
    e.ln("        (*uipNok)++;")
    e.ln("    }")
    e.ln("    return uiOk;")
    e.ln("}")
    e.blank()
    e.ln(f"int {module}CitInit({plan.handle_param})")
    e.ln("{")
    if cmodel._func_name(module, "device_init") in [
            cmodel._func_name(module, op) for op in (plan.device.get("operations_requested") or ["device_init"])]:
        e.ln(f"    return ({module}DeviceInit({h}) == XST_SUCCESS) ? {STATUS_OK} : {STATUS_FAIL};")
    else:
        e.ln(f"    (void){h};")
        e.ln(f"    return {STATUS_OK}; /* spec'te device_init istenmemis */")
    e.ln("}")
    e.blank()
    e.ln(f"int {module}CitRead({plan.handle_param}, const S{pas}CitLimit* spLimit, S{pas}Cit* spCit)")
    e.ln("{")
    e.level = 1
    e.ln("int iStatus;")
    e.blank()
    e.open(f"if (spCit == NULL)").ln(f"return {STATUS_FAIL};").close()
    e.open("if (spLimit == NULL)").ln(f"spLimit = &S_s{pas}CitLimitVarsayilan;").close()
    e.ln("memset(spCit, 0, sizeof(*spCit));")
    if plan.has_status:
        e.ln(f"iStatus = {module}StatusRegistersRead({h}, &spCit->sDurum);")
        e.open("if (iStatus == XST_SUCCESS)").ln("spCit->sBayraklar.uiStatusRegistersOkundu = 1U;").close()
        e.open("else").ln("spCit->uiHataSayac++;").close()
    for m in plan.measures:
        e.ln(f"iStatus = {m.func}({h}, &spCit->{m.field});")
        e.open("if (iStatus == XST_SUCCESS)")
        e.ln(f"spCit->sBayraklar.{m.op_ok} = 1U;")
        for ch in m.channels:
            value = (f"(int)spCit->{m.field}.{m.array_field}[{ch.index}U]" if m.is_array
                     else f"(int)spCit->{m.field}")
            e.ln(f"spCit->sBayraklar.{ch.ok_bit} = {module}CitOlcum(&spLimit->{ch.limit_field}, {value}, &spCit->uiNokSayac);")
        e.close()
        e.open("else").ln("spCit->uiHataSayac++;").close()
    if not plan.measures:
        e.ln("(void)spLimit;")
    e.open("if (spCit->uiHataSayac != 0U)").ln(f"return {STATUS_FAIL};").close()
    e.ln(f"return (spCit->uiNokSayac != 0U) ? {STATUS_NOK} : {STATUS_OK};")
    e.level = 0
    e.ln("}")
    return e.text()


# --- sistem toplayici -------------------------------------------------------------------

def controller_field(controller: dict) -> str:
    """SSistemCitBus alan adi (denetleyici id -> sPlI2c0)."""
    return "s" + _pascal(str(controller.get("id", "bus")))


def device_field(device: dict) -> str:
    """SSistemCit / SSistemCitLimit alan adi (cihaz id -> sU2Ltc2991)."""
    return "s" + _pascal(str(device.get("id", "dev")))


def bus_controllers(plans: list[_ChipPlan]) -> list[dict]:
    """SSistemCitBus'taki denetleyiciler (ilk gorulme sirasiyla, tekil)."""
    seen: list[dict] = []
    ids = set()
    for plan in plans:
        cid = plan.controller.get("id")
        if cid not in ids:
            ids.add(cid)
            seen.append(plan.controller)
    return seen


def _bus_field_type(htype: str) -> str:
    return "unsigned long" if htype in cmodel.BASE_ADDRESS_HANDLE_DRIVERS else f"{htype}*"


def sistem_header(plans: list[_ChipPlan], skipped: list[tuple[str, str]]) -> str:
    controllers = bus_controllers(plans)
    e = _E(0)
    e.ln("/**")
    e.ln(" * @file sistem_cit.h")
    e.ln(" * @brief Sistem CIT toplayici: her entegrenin CIT struct'i tek yapida, tek cagriyla.")
    e.ln(" *")
    e.ln(" * Kullanim (kart yazilimi):")
    e.ln(" *   static SSistemCitBus S_sBus;")
    e.ln(" *   static const SSistemCitLimit S_sLimit = SISTEM_CIT_LIMIT_VARSAYILAN;")
    e.ln(" *   static SSistemCit S_sCit;")
    e.ln(" *   sistemCitBusVarsayilan(&S_sBus);        -- spec'ten denetleyici handle'lari")
    e.ln(" *   sistemCitInit(&S_sBus);                 -- entegre ilklendirmeleri (surucu DeviceInit)")
    e.ln(" *   sistemCitRead(&S_sBus, &S_sLimit, &S_sCit); -- periyodik: struct bit bit dolar")
    e.ln(" *")
    if skipped:
        e.ln(" * CIT dosyasi uretilmeyen cihazlar (kapsam disi):")
        for did, why in skipped:
            e.ln(f" *   - {did}: {why}")
        e.ln(" *")
    e.ln(" * Generated by Spec2Code. Do not edit by hand.")
    e.ln(" */")
    e.ln("#ifndef SISTEM_CIT_H")
    e.ln("#define SISTEM_CIT_H")
    e.blank()
    for plan in plans:
        e.ln(f'#include "{plan.module}_cit.h"')
    e.blank()
    e.ln(f"#define SISTEM_CIT_CIHAZ_SAYISI {len(plans)}U")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Sistemdeki denetleyici handle'lari (alan adi = denetleyici id).")
    e.ln(" *        AXI IIC taban adres, digerleri surucu ornegi isaretcisi.")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for c in controllers:
        htype, _ = cmodel._handle_for(c)
        e.ln(f"    {_bus_field_type(htype)} {controller_field(c)}; /* {c.get('id')} ({c.get('instance', '')}) */")
    e.ln("} SSistemCitBus;")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Butun entegrelerin limit politikasi (alan adi = spec cihaz id'si).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    for plan in plans:
        e.ln(f"    S{plan.pascal}CitLimit {device_field(plan.device)}; /* {plan.device['id']} ({plan.part}) */")
    e.ln("} SSistemCitLimit;")
    e.blank()
    e.ln("#define SISTEM_CIT_LIMIT_VARSAYILAN \\")
    for i, plan in enumerate(plans):
        tail = "," if i < len(plans) - 1 else ""
        prefix = "    {" if i == 0 else "     "
        suffix = "}" if i == len(plans) - 1 else " \\"
        e.ln(f"{prefix}{plan.mod}_CIT_LIMIT_VARSAYILAN{tail}{suffix}")
    e.blank()
    e.ln("/**")
    e.ln(" * @brief Butun entegrelerin CIT sonucu (alan adi = spec cihaz id'si).")
    e.ln(" */")
    e.ln("typedef struct")
    e.ln("{")
    e.ln("    unsigned int uiSayac;     /* kac kez kosuldu                          */")
    e.ln("    unsigned int uiHataSayac; /* bu kosuda toplam dusen surucu cagrisi    */")
    e.ln("    unsigned int uiNokSayac;  /* bu kosuda toplam limit disi etkin olcum  */")
    for plan in plans:
        e.ln(f"    S{plan.pascal}Cit {device_field(plan.device)}; /* {plan.device['id']} ({plan.part}) */")
    e.ln("} SSistemCit;")
    e.blank()
    e.ln("void sistemCitBusVarsayilan(SSistemCitBus* spBus);")
    e.ln("int sistemCitInit(SSistemCitBus* spBus);")
    e.ln("int sistemCitRead(SSistemCitBus* spBus, const SSistemCitLimit* spLimit, SSistemCit* spCit);")
    e.blank()
    e.ln("#endif /* SISTEM_CIT_H */")
    return e.text()


def sistem_source(plans: list[_ChipPlan]) -> str:
    controllers = bus_controllers(plans)
    e = _E(0)
    e.ln("/**")
    e.ln(" * @file sistem_cit.c")
    e.ln(" * @brief Sistem CIT toplayici gerceklemesi. Generated by Spec2Code.")
    e.ln(" */")
    e.ln('#include "sistem_cit.h"')
    e.ln('#include "xparameters.h"')
    e.ln("#include <stddef.h>")
    e.blank()
    e.ln("static const SSistemCitLimit S_sSistemCitLimitVarsayilan = SISTEM_CIT_LIMIT_VARSAYILAN;")
    for c in controllers:
        htype, _ = cmodel._handle_for(c)
        if htype not in cmodel.BASE_ADDRESS_HANDLE_DRIVERS:
            e.ln(f"static {htype} S_{controller_field(c)}Instance; /* {c.get('id')} */")
    e.blank()
    e.ln("void sistemCitBusVarsayilan(SSistemCitBus* spBus)")
    e.ln("{")
    e.ln("    if (spBus == NULL)")
    e.ln("    {")
    e.ln("        return;")
    e.ln("    }")
    for c in controllers:
        htype, _ = cmodel._handle_for(c)
        fld = controller_field(c)
        if htype in cmodel.BASE_ADDRESS_HANDLE_DRIVERS:
            e.ln(f"    spBus->{fld} = (unsigned long){c.get('instance', 'XPAR_UNKNOWN')}_BASEADDR;")
        else:
            e.ln(f"    spBus->{fld} = &S_{fld}Instance;")
    e.ln("}")
    e.blank()
    e.ln("int sistemCitInit(SSistemCitBus* spBus)")
    e.ln("{")
    e.ln(f"    int iIlkHata = {STATUS_OK};")
    e.ln("    int iStatus;")
    e.blank()
    e.ln("    if (spBus == NULL)")
    e.ln("    {")
    e.ln(f"        return {STATUS_FAIL};")
    e.ln("    }")
    for plan in plans:
        e.ln(f"    iStatus = {plan.module}CitInit(spBus->{controller_field(plan.controller)});")
        e.ln(f"    if ((iStatus != {STATUS_OK}) && (iIlkHata == {STATUS_OK}))")
        e.ln("    {")
        e.ln("        iIlkHata = iStatus;")
        e.ln("    }")
    e.ln("    return iIlkHata;")
    e.ln("}")
    e.blank()
    e.ln("int sistemCitRead(SSistemCitBus* spBus, const SSistemCitLimit* spLimit, SSistemCit* spCit)")
    e.ln("{")
    e.ln("    unsigned int uiSayac;")
    e.blank()
    e.ln("    if ((spBus == NULL) || (spCit == NULL))")
    e.ln("    {")
    e.ln(f"        return {STATUS_FAIL};")
    e.ln("    }")
    e.ln("    if (spLimit == NULL)")
    e.ln("    {")
    e.ln("        spLimit = &S_sSistemCitLimitVarsayilan;")
    e.ln("    }")
    e.ln("    uiSayac = spCit->uiSayac + 1U;")
    e.ln("    spCit->uiHataSayac = 0U;")
    e.ln("    spCit->uiNokSayac = 0U;")
    for plan in plans:
        dev = device_field(plan.device)
        e.ln(f"    (void){plan.module}CitRead(spBus->{controller_field(plan.controller)}, &spLimit->{dev}, &spCit->{dev});")
        e.ln(f"    spCit->uiHataSayac += spCit->{dev}.uiHataSayac;")
        e.ln(f"    spCit->uiNokSayac += spCit->{dev}.uiNokSayac;")
    e.ln("    spCit->uiSayac = uiSayac;")
    e.ln("    if (spCit->uiHataSayac != 0U)")
    e.ln("    {")
    e.ln(f"        return {STATUS_FAIL};")
    e.ln("    }")
    e.ln(f"    return (spCit->uiNokSayac != 0U) ? {STATUS_NOK} : {STATUS_OK};")
    e.ln("}")
    return e.text()


# --- README + yazma ---------------------------------------------------------------------

def readme_section(plans: list[_ChipPlan], skipped: list[tuple[str, str]]) -> str:
    lines = [
        "",
        "## CIT ust katmani (`cit/`)",
        "",
        "`drivers/` ham veriyi surucu struct'lariyla verir (`S<Mod>Status` bit bit, `S<Mod>Voltage`",
        "kanal dizisi, skaler `int`/`unsigned short`); `cit/` bunlari ANLAMLANDIRIR: hangi olcumler",
        "okunur, limit/etkin politikasi (kapali aralik, min == max gecerli), OK/NOK bitleri. Ikisini birlikte kendi yazilimina tasi.",
        "",
        "| Dosya | Icerik |",
        "|---|---|",
        "| `cit/cit_ortak.h/.c` | `SCitLimit`, `citLimitDegerlendir()`, `CIT_OK/NOK/HATA` |",
    ]
    for plan in plans:
        lines.append(f"| `cit/{plan.module}_cit.h/.c` | `S{plan.pascal}CitLimit` (`{plan.mod}_CIT_LIMIT_VARSAYILAN` spec'ten), "
                     f"`S{plan.pascal}Cit`, `{plan.module}CitInit()`, `{plan.module}CitRead()` |")
    lines.append("| `cit/sistem_cit.h/.c` | `SSistemCitBus`, `SSistemCitLimit`, `SSistemCit`, `sistemCitBusVarsayilan/Init/Read()` |")
    lines.extend([
        "",
        "`<mod>CitRead(handle, &sLimit, &sCit)` surucu fonksiyonlarini cagirir, `sCit.sDurum` (surucu",
        "durum bitleri), olcum struct'lari ve `sBayraklar` (op okundu bitleri + olcum/kanal OK bitleri)",
        "dolar; `uiHataSayac` dusen cagri, `uiNokSayac` limit disi olcum sayisidir.",
    ])
    if skipped:
        lines.append("")
        lines.append("CIT dosyasi uretilmeyen cihazlar: " + ", ".join(f"`{d}` ({w})" for d, w in skipped) + ".")
    lines.append("")
    return "\n".join(lines)


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
                    manifest_devices: list[dict], cit_olcumler: list[dict]) -> tuple[list[str], str]:
    """cit/ agacini yazar; (yazilan yollar, README bolumu) dondurur. Cihaz yoksa bos."""
    plans = build_plans(spec, get_descriptor, manifest_devices, cit_olcumler)
    if not plans:
        return [], ""
    cit_dir = out_dir / "cit"
    written: list[Path] = [
        hio.write_output(cit_dir / "cit_ortak.h", ortak_header()),
        hio.write_output(cit_dir / "cit_ortak.c", ortak_source()),
    ]
    for plan in plans:
        written.append(hio.write_output(cit_dir / f"{plan.module}_cit.h", chip_header(plan)))
        written.append(hio.write_output(cit_dir / f"{plan.module}_cit.c", chip_source(plan)))
    skipped = skipped_devices(spec, get_descriptor, plans)
    written.append(hio.write_output(cit_dir / "sistem_cit.h", sistem_header(plans, skipped)))
    written.append(hio.write_output(cit_dir / "sistem_cit.c", sistem_source(plans)))
    return [str(p) for p in written], readme_section(plans, skipped)
