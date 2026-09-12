"""BSP akisi: klasik Vitis (<= 2023.2, xsct, DEVICE_ID) ve Vitis Unified / SDT (>= 2024.1).

Vitis 2024.1+ "Unified" akisinda BSP System Device Tree (SDT) + Lopper ile uretilir:

* ``xparameters.h`` icinde ``XPAR_*_DEVICE_ID`` makrolari YOKTUR; surucu ornegi
  ``XPAR_*_BASEADDR`` ile secilir (``X<Drv>_LookupConfig(UINTPTR BaseAddress)``,
  ``XGpio_Initialize(&inst, BaseAddress)``, ``XIntc_Initialize(&inst, BaseAddress)``).
* Derleyici ``-DSDT`` tanimlar; Xilinx ornekleri ``#ifndef SDT`` ile iki akisi tasir.
* Kanonik ad ``XPAR_X<DRV>_<n>`` (or. ``XPAR_XIIC_0_BASEADDR``), etiket adi
  (``XPAR_AXI_IIC_0_BASEADDR``) de bulunur.

Spec'te ``project.bsp_flow`` = ``classic`` (varsayilan) | ``sdt``. Uretilen kod tek bir
akisa gore cikar (iki akisi ``#ifdef`` ile tasiyan olu kod istemiyoruz); akis butun
LookupConfig/Initialize argumanlarini bu modulden alir.
"""

from __future__ import annotations

BSP_FLOW_CLASSIC = "classic"
BSP_FLOW_SDT = "sdt"
BSP_FLOWS = (BSP_FLOW_CLASSIC, BSP_FLOW_SDT)

#: Vitis Unified (SDT tabanli BSP, `vitis -s` Python akisi) bu surumden itibaren.
UNIFIED_MIN_VERSION = (2024, 1)


def bsp_flow(spec: dict) -> str:
    """Spec'in BSP akisi (``classic`` | ``sdt``); bilinmeyen deger klasik sayilir."""
    value = str((spec.get("project") or {}).get("bsp_flow") or BSP_FLOW_CLASSIC).strip().lower()
    return value if value in BSP_FLOWS else BSP_FLOW_CLASSIC


def is_sdt(spec: dict) -> bool:
    return bsp_flow(spec) == BSP_FLOW_SDT


def lookup_arg(instance: str, sdt: bool) -> str:
    """``X<Drv>_LookupConfig`` / ``_Initialize`` icin ornek secici makro.

    Klasik: ``XPAR_AXI_IIC_0_DEVICE_ID``; SDT: ``XPAR_AXI_IIC_0_BASEADDR``.
    """
    return f"{instance}_BASEADDR" if sdt else f"{instance}_DEVICE_ID"


def lookup_suffix(sdt: bool) -> str:
    """Makro son eki (``DEVICE_ID`` | ``BASEADDR``) - uretilen `#define` adlarinda kullanilir."""
    return "BASEADDR" if sdt else "DEVICE_ID"


#: SDT xparameters.h'ta PS cevre birimleri YALNIZ kanonik surucu adiyla gelir (XPAR_XIICPS_0_BASEADDR;
#: etiket adi XPAR_PSU_I2C_0_BASEADDR YOKTUR - SAHA 2026-09-12, ZCU102 Vitis 2025.2). PL IP'lerde ise
#: hem etiket (XPAR_AXI_IIC_0) hem kanonik (XPAR_XIIC_0) vardir; etiket korunur. Kanonik indeks,
#: ayni surucuye sahip ETKIN orneklerin taban adres sirasindaki sirasidir (psu_ethernet_3 tek GEM ise XEMACPS_0).
PS_CANONICAL_DRIVER_PREFIX: dict[str, str] = {
    "XIicPs": "XIICPS", "XSpiPs": "XSPIPS", "XQspiPsu": "XQSPIPSU", "XQspiPs": "XQSPIPS",
    "XUartPs": "XUARTPS", "XUartPsv": "XUARTPSV", "XEmacPs": "XEMACPS", "XGpioPs": "XGPIOPS",
    "XCanPs": "XCANPS", "XSdPs": "XSDPS", "XTtcPs": "XTTCPS", "XWdtPs": "XWDTPS", "XScuGic": "XSCUGIC",
}


def _base_int(controller: dict) -> int:
    try:
        return int(str(controller.get("base_address") or "0"), 0)
    except ValueError:
        return 0


def sdt_controller_instances(spec: dict) -> dict[str, str]:
    """controller id -> SDT'de kullanilacak XPAR ornek adi (klasik akista degismez)."""
    controllers = list(spec.get("controllers") or [])
    if not is_sdt(spec):
        return {str(c.get("id")): str(c.get("instance") or "") for c in controllers}
    out: dict[str, str] = {}
    by_driver: dict[str, list[dict]] = {}
    for c in controllers:
        prefix = PS_CANONICAL_DRIVER_PREFIX.get(str(c.get("driver") or ""))
        if str(c.get("zone") or "") == "ps" and prefix:
            by_driver.setdefault(prefix, []).append(c)
        else:
            out[str(c.get("id"))] = str(c.get("instance") or "")
    for prefix, group in by_driver.items():
        for index, c in enumerate(sorted(group, key=_base_int)):
            out[str(c.get("id"))] = f"XPAR_{prefix}_{index}"
    return out


def with_sdt_instances(spec: dict) -> dict:
    """SDT akisinda spec kopyasi: PS denetleyicilerinin `instance` alani kanonik ada cekilir."""
    if not is_sdt(spec):
        return spec
    names = sdt_controller_instances(spec)
    return {**spec, "controllers": [{**c, "instance": names.get(str(c.get("id")), c.get("instance", ""))}
                                    for c in spec.get("controllers") or []]}


def parse_vitis_version(version: str) -> tuple[int, int] | None:
    """``2023.2`` / ``2025.2.1`` -> (2023, 2) / (2025, 2); cozulemezse None."""
    parts = str(version or "").strip().split(".")
    try:
        return int(parts[0]), int(parts[1])
    except (IndexError, ValueError):
        return None


def is_unified_vitis(version: str) -> bool:
    """Vitis 2024.1 ve sonrasi: Unified IDE, SDT BSP, Python (`vitis -s`) betik akisi."""
    parsed = parse_vitis_version(version)
    return parsed is not None and parsed >= UNIFIED_MIN_VERSION


def expected_bsp_flow_for_vitis(version: str) -> str:
    return BSP_FLOW_SDT if is_unified_vitis(version) else BSP_FLOW_CLASSIC
