"""Register haritasi BILINEN Xilinx/AMD IP'leri: XSA'da gorulunce Register Map dokumani otomatik uretilir.

Bugun: **JESD204C v4.x** (PG242, AXI4-Lite register alani). Kullanici register haritasini elle
yazmaz; XSA ayristirici IP'yi taniyip `custom_ips[]` kaydina `register_map: "jesd204c"` ve IP
parametrelerini (lane sayisi, yon, hat kodlamasi, alt sinif) koyar, buradaki uretici da:

* Register Map ekrani icin dokuman (`/api/register-map/known-ip`): register adlari + bit alanlari
  ile canli okuma/yazma (mem_read/mem_write, bit alani cozumu istemcide);
* kod uretimi icin ayni dokuman -> `drivers/ip/<id>_regs.h/.c` + `<id>_shell.*` (shell `ip_<id>`).

Harita `backend/register_map.py` seması: her register 4 bayt, genislik bir sonraki offset'ten
cikarildigi icin bosluklar `reserved` dolgu register'lariyla kapatilir (`_with_reserved_fillers`).
Per-lane blok: 0x400 + 0x80 * lane (PG242 "per-lane registers"); yalniz L lane uretilir.
Kaynak: PG242 v4.x Register Space (docs.amd.com, 2026-09-12 okundu). Vivado 2023.2 hedeflenir.
"""

from __future__ import annotations

import re

KNOWN_IP_KEYS = ("jesd204c",)

#: VLNV/MODTYPE -> bilinen IP anahtari. VLNV `xilinx.com:ip:jesd204c:4.x` ya da modtype `jesd204c`.
_VLNV_RULES: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"^xilinx\.com:ip:jesd204c(:|$)"), "jesd204c"),
)
_MODTYPE_RULES: tuple[tuple[re.Pattern, str], ...] = (
    (re.compile(r"^jesd204c(_\d+)?$"), "jesd204c"),
)


def known_ip_key(vlnv: str, modtype: str) -> str | None:
    """XSA MODULE'unun VLNV'si ya da MODTYPE'i bilinen bir IP'ye uyuyorsa anahtari (`jesd204c`)."""
    vlnv_l = str(vlnv or "").strip().lower()
    for pattern, key in _VLNV_RULES:
        if pattern.search(vlnv_l):
            return key
    mod_l = str(modtype or "").strip().lower()
    for pattern, key in _MODTYPE_RULES:
        if pattern.search(mod_l):
            return key
    return None


# --- IP parametreleri -----------------------------------------------------------------------

#: Varsayilanlar (kullanici karari 2026-09-12): JESD204C 4 lane, alt sinif 1, 64B/66B; yon RX
#: (XSA'dan okunamazsa). Spec `custom_ips[].ip_parameters` ile ezilir.
JESD204C_DEFAULT_PARAMETERS: dict[str, object] = {
    "lanes": 4,
    "direction": "rx",
    "link_layer": "64b66b",
    "subclass": 1,
}

#: XSA PARAMETER adlarindan (buyuk harf, C_ oneki atilmis) normal parametrelere esleme.
#: IP'nin gercek parametre adlari surume gore degisebilir; bu yuzden ad ICINDE gecen
#: anahtar kelimelere bakilir (LANES, TRANSMIT/TX, SUBCLASS, 64B66B/LINK_LAYER/ENCODING).
def normalize_jesd204c_parameters(raw: dict | None) -> dict[str, object]:
    params = dict(JESD204C_DEFAULT_PARAMETERS)
    for name, value in (raw or {}).items():
        key = str(name).upper().removeprefix("C_")
        text = str(value).strip().lower()
        if key in ("LANES", "DIRECTION", "LINK_LAYER", "SUBCLASS"):
            _assign_normalized(params, key.lower(), text)
        elif "LANES" in key or key == "L":
            _assign_normalized(params, "lanes", text)
        elif "TRANSMIT" in key or key in ("TX", "IS_TX", "NODE_IS_TRANSMIT", "TRANSMITTER"):
            params["direction"] = "tx" if text in ("1", "true", "tx", "yes") else "rx"
        elif "SUBCLASS" in key:
            _assign_normalized(params, "subclass", text)
        elif "64B66B" in key or "LINK_LAYER" in key or "ENCODING" in key or "LINECODE" in key:
            _assign_normalized(params, "link_layer", text)
    return params


def _assign_normalized(params: dict[str, object], key: str, text: str) -> None:
    if key == "lanes":
        try:
            lanes = int(text, 0)
        except ValueError:
            return
        if 1 <= lanes <= 8:
            params["lanes"] = lanes
    elif key == "direction":
        if text in ("rx", "tx"):
            params["direction"] = text
    elif key == "subclass":
        try:
            sub = int(text, 0)
        except ValueError:
            return
        if sub in (0, 1, 2):
            params["subclass"] = sub
    elif key == "link_layer":
        if text in ("64b66b", "1", "true", "yes"):
            params["link_layer"] = "64b66b"
        elif text in ("8b10b", "0", "false", "no"):
            params["link_layer"] = "8b10b"


# --- JESD204C v4.x register haritasi (PG242) ------------------------------------------------

def _reg(name: str, offset: int, description: str, fields: list[tuple[str, str, str]] | None = None,
         reset: int = 0) -> dict:
    return {
        "name": name, "offset": f"0x{offset:03X}", "reset": f"0x{reset:08X}", "reserved": False,
        "description": description,
        "fields": [{"name": f, "bits": b, "description": d} for f, b, d in (fields or [])],
    }


def _jesd204c_common_registers(direction: str, link_layer: str, lanes: int) -> list[dict]:
    is_tx = direction == "tx"
    is_64 = link_layer == "64b66b"
    regs: list[dict] = [
        _reg("IP_VERSION", 0x000, "[RO] Cekirdek surumu", [
            ("MAJOR", "31:24", "buyuk surum"), ("MINOR", "23:16", "kucuk surum"), ("REVISION", "15:8", "revizyon")]),
        _reg("IP_CONFIG", 0x004, "[RO] Cekirdek yapilandirmasi (sentez zamani)", [
            ("FEC_INCLUDED", "18", "FEC var"), ("LINECODE_64B66B", "17", "1=64B/66B, 0=8B/10B"),
            ("CORE_IS_TX", "16", "1=TX cekirdegi, 0=RX"), ("NUM_LANES", "3:0", "lane sayisi")]),
        _reg("RESET", 0x020, "[RW] Reset kontrol/durum: bit0 yaz=1 reset baslat; bit5 reset surerken 1", [
            ("GT_MST_RESET_BUSY", "31:24", "GT master reset mesgul (lane basina)"),
            ("GT_PMA_RESET_BUSY", "23:16", "GT PMA reset mesgul (lane basina)"),
            ("GT_RESET_BUSY", "7", "GT reset mesgul"), ("GT_POWERGOOD", "6", "GT guc iyi"),
            ("CORE_RESET_STATE", "5", "cekirdek reset durumu (1=reset'te)"),
            ("CORE_RESET_PIN", "4", "harici reset pini durumu"),
            ("RESET_TYPE", "1", "0=tam reset, 1=yalniz baglanti (link) reset"),
            ("RESET", "0", "1 yaz: reset baslat (kendiliginden temizlenir)")]),
    ]
    if is_tx and is_64:
        regs.append(_reg("CTRL_ENABLE", 0x024, "[RW] TX arayuz etkinlestirme", [
            ("ENABLE_DATA_IF", "1", "veri arayuzu etkin"), ("ENABLE_CMD_IF", "0", "komut arayuzu etkin")]))
    if is_tx and not is_64:
        regs.append(_reg("CTRL_TX_SYNC", 0x028, "[RW] TX SYNC zorlama (8B/10B)", [("FORCE_SYNC", "0", "SYNC'i zorla")]))
    if is_64:
        regs += [
            _reg("CTRL_MB_IN_EMB", 0x030, "[RW] Genisletilmis multiblok icindeki multiblok sayisi (E)", [
                ("MB_IN_EMB", "7:0", "1..255")], reset=1),
            _reg("CTRL_SUB_CLASS", 0x034, "[RW] Alt sinif", [("SUBCLASS", "1:0", "0/1/2")], reset=1),
            _reg("CTRL_META_MODE", 0x038, "[RW] Meta mod", [("META_MODE", "1:0", "0=CRC12, 2=CMD, 3=FEC")]),
        ]
    else:
        regs.append(_reg("CTRL_8B10B_CFG", 0x03C, "[RW] 8B/10B baglanti yapilandirmasi", [
            ("ILA_MULTIFRAMES", "31:24", "ILA multiframe sayisi"), ("LINK_ERROR_ENABLE", "19", "hat hata sayaci etkin"),
            ("ERROR_VIA_SYNC", "18", "hatayi SYNC ile bildir"), ("ILA_REQUIRED", "17", "ILA zorunlu"),
            ("SCRAMBLING", "16", "karistirma etkin"), ("FRAMES_PER_MF_K", "12:8", "K-1"),
            ("OCTETS_PER_FRAME_F", "7:0", "F-1")], reset=0x03000F01))
    regs.append(_reg("CTRL_LANE_ENA", 0x040, "[RW] Lane etkinlestirme (bit basina lane)", [
        ("LANE_ENABLE", "7:0", "lane 0..7")], reset=(1 << lanes) - 1))
    if not is_tx and is_64:
        regs.append(_reg("CTRL_RX_BUF_ADV", 0x044, "[RW] Alici tampon serbest birakma one alma (kelime)", [
            ("BUFFER_ADVANCE", "9:0", "0..31")]))
    regs.append(_reg("CTRL_TEST_MODE", 0x048, "[RW] Test modu", [
        ("GT_LOOPBACK", "30:28", "GT loopback secimi"), ("PRBS_MODE", "11:8", "PRBS modu"),
        ("TEST_MODE_8B10B", "2:0", "8B/10B test modu")]))
    if not is_tx and is_64:
        regs.append(_reg("CTRL_RX_MBLOCK_TH", 0x04C, "[RW] Multiblok kilit esigi", [("MB_LOCK_THRESHOLD", "2:0", "esik")]))
    regs.append(_reg("CTRL_SYSREF", 0x050, "[RW] SYSREF isleme", [
        ("SYSREF_DELAY", "23:16", "SYSREF gecikmesi (LEMC/LMFC)"), ("SYSREF_TOLERANCE", "10:8", "tolerans"),
        ("SYSREF_REQUIRED_RESYNC", "1", "yeniden senkronda SYSREF zorunlu"), ("SYSREF_ALWAYS", "0", "her SYSREF'te hizala")]))
    if not is_tx and is_64:
        regs.append(_reg("STAT_LOCK_DEBUG", 0x054, "[RO] Kilit ayiklama", [
            ("MB_ALIGNED", "23:16", "multiblok hizali (lane basina)"), ("SYNC_HEADER_ALIGNED", "7:0", "sync header hizali (lane basina)")]))
    if not is_tx and not is_64:
        regs += [
            _reg("STAT_RX_ERR", 0x058, "[RO, okuyunca temizlenir] Lane basina 8B/10B hatalari (4 bit: bit2 K, bit1 disparity, bit0 not-in-table)", [
                (f"LANE{i}_ERR", f"{4 * i + 3}:{4 * i}", f"lane {i}") for i in range(8)]),
            _reg("STAT_RX_DEBUG", 0x05C, "[RO] Lane basina durum (bit3 SOD, bit2 SOI, bit1 CGS, bit0 K28.5)", [
                (f"LANE{i}_STATUS", f"{4 * i + 3}:{4 * i}", f"lane {i}") for i in range(8)]),
        ]
    regs += [
        _reg("STAT_STATUS", 0x060, "[RO] Baglanti durumu", [
            ("ALIGN_ERROR_8B10B", "15", "hizalama hatasi (8B/10B)"), ("RX_STARTED", "14", "alici basladi"),
            ("CGS_STATUS", "13", "kod grubu senkron"), ("SYNC_STATUS", "12", "SYNC durumu"),
            ("BUFFER_OVERFLOW", "10", "tampon tasti"), ("MB_LOCK_64B66B", "5", "multiblok kilidi"),
            ("SYNC_HEADER_LOCK_64B66B", "4", "sync header kilidi"), ("SYSREF_ERROR", "2", "SYSREF hatasi"),
            ("SYSREF_CAPTURED", "1", "SYSREF yakalandi"), ("INTERRUPT_PENDING", "0", "kesme bekliyor")]),
        _reg("CTRL_IRQ", 0x064, "[RW] Kesme etkinlestirme", [
            ("RX_DATA_START_IE", "14", ""), ("RX_RESYNC_IE", "13", ""), ("SYNC_IE", "12", ""),
            ("OVERFLOW_IE", "10", ""), ("FEC_ERROR_IE", "9", ""), ("CRC_ERROR_IE", "8", ""),
            ("MB_ERROR_IE", "7", ""), ("BLOCK_SYNC_ERROR_IE", "6", ""), ("MB_LOCK_LOSS_IE", "5", ""),
            ("SYNC_HEADER_LOCK_LOSS_IE", "4", ""), ("SYSREF_ERROR_IE", "2", ""), ("SYSREF_RECEIVED_IE", "1", ""),
            ("GLOBAL_IE", "0", "genel kesme etkin")]),
        _reg("STAT_IRQ", 0x068, "[RO] Kesme durumu (CTRL_IRQ ile ayni bit yerlesimi)", [
            ("RX_DATA_START", "14", ""), ("RX_RESYNC", "13", ""), ("SYNC", "12", ""),
            ("OVERFLOW", "10", ""), ("FEC_ERROR", "9", ""), ("CRC_ERROR", "8", ""),
            ("MB_ERROR", "7", ""), ("BLOCK_SYNC_ERROR", "6", ""), ("MB_LOCK_LOSS", "5", ""),
            ("SYNC_HEADER_LOCK_LOSS", "4", ""), ("SYSREF_ERROR", "2", ""), ("SYSREF_RECEIVED", "1", "")]),
    ]
    if is_tx and is_64:
        regs += [
            _reg("CTRL_TX_ILA_CFG0", 0x070, "[RW] TX ILA: BID/DID", [("BID", "11:8", "bank ID"), ("DID", "7:0", "device ID")]),
            _reg("CTRL_TX_ILA_CFG1", 0x074, "[RW] TX ILA: CS/N'/N/M", [
                ("CS", "25:24", "kontrol biti/ornek"), ("N_PRIME", "20:16", "N'-1"), ("N", "12:8", "N-1"), ("M", "7:0", "M-1")]),
            _reg("CTRL_TX_ILA_CFG2", 0x078, "[RW] TX ILA: CF/HD/S", [("CF", "28:24", ""), ("HD", "16", "yuksek yogunluk"), ("S", "12:8", "S-1")]),
            _reg("CTRL_TX_ILA_CFG3", 0x07C, "[RW] TX ILA: faz ayari (alt sinif 2)", [("ADJDIR", "16", ""), ("PHADJ", "8", ""), ("ADJCNT", "3:0", "")]),
            _reg("CTRL_TX_ILA_CFG4", 0x080, "[RW] TX ILA: RES1/RES2", [("RES2", "15:8", ""), ("RES1", "7:0", "")]),
        ]
    return regs


def _jesd204c_lane_registers(lane: int, direction: str, link_layer: str) -> list[dict]:
    base = 0x400 + 0x80 * lane
    is_tx = direction == "tx"
    is_64 = link_layer == "64b66b"
    p = f"L{lane}_"
    regs: list[dict] = []
    if not is_tx:
        regs.append(_reg(p + "STAT_RX_BUF_LVL", base + 0x00, f"[RO] lane {lane} tampon doluluk (64-bit kelime / bayt)", [
            ("BUFFER_FILL_LEVEL", "9:0", "")]))
    else:
        regs.append(_reg(p + "CTRL_TX_ILA_LID", base + 0x04, f"[RW] lane {lane} ILA: L-1 ve lane ID", [
            ("NUM_LANES_MINUS1", "20:16", "L-1"), ("LANE_ID", "4:0", "LID")]))
    if not is_tx and is_64:
        regs += [
            _reg(p + "STAT_RX_ERROR_CNT0", base + 0x10, f"[RO] lane {lane} CRC / MB / SH hizalama hata sayaclari", [
                ("CRC_ERRORS", "31:16", ""), ("MB_ALIGN_ERRORS", "15:8", ""), ("SH_ALIGN_ERRORS", "7:0", "")]),
            _reg(p + "STAT_RX_ERROR_CNT1", base + 0x14, f"[RO] lane {lane} FEC hata sayaclari", [
                ("FEC_UNCORRECTED", "31:16", ""), ("FEC_CORRECTED", "15:0", "")]),
        ]
    if not is_tx and not is_64:
        regs += [
            _reg(p + "STAT_LINK_ERR_CNT", base + 0x20, f"[RO] lane {lane} hat hata sayaci", [("LINK_ERROR_COUNT", "31:0", "")]),
            _reg(p + "STAT_TEST_ERR_CNT", base + 0x24, f"[RO] lane {lane} test modu hata sayaci", [("TEST_ERROR_COUNT", "31:0", "")]),
            _reg(p + "STAT_TEST_ILA_CNT", base + 0x28, f"[RO] lane {lane} ILA dizi sayaci", [("ILA_COUNT", "31:0", "")]),
            _reg(p + "STAT_TEST_MF_CNT", base + 0x2C, f"[RO] lane {lane} multiframe sayaci", [("MF_COUNT", "31:0", "")]),
        ]
    if not is_tx:
        regs += [
            _reg(p + "RX_ILA_CFG0", base + 0x30, f"[RO] lane {lane} ILA: JESDV/SUBCLASS", [("JESDV", "10:8", ""), ("SUBCLASS", "2:0", "")]),
            _reg(p + "RX_ILA_CFG1", base + 0x34, f"[RO] lane {lane} ILA: F-1", [("F", "7:0", "")]),
            _reg(p + "RX_ILA_CFG2", base + 0x38, f"[RO] lane {lane} ILA: K-1", [("K", "4:0", "")]),
            _reg(p + "RX_ILA_CFG3", base + 0x3C, f"[RO] lane {lane} ILA: L/LID/BID/DID", [
                ("L", "28:24", ""), ("LID", "20:16", ""), ("BID", "11:8", ""), ("DID", "7:0", "")]),
            _reg(p + "RX_ILA_CFG4", base + 0x40, f"[RO] lane {lane} ILA: CS/N'/N/M", [
                ("CS", "25:24", ""), ("N_PRIME", "20:16", ""), ("N", "12:8", ""), ("M", "7:0", "")]),
            _reg(p + "RX_ILA_CFG5", base + 0x44, f"[RO] lane {lane} ILA: CF/HD/S/SCR", [
                ("CF", "28:24", ""), ("HD", "16", ""), ("S", "12:8", ""), ("SCR", "0", "")]),
            _reg(p + "RX_ILA_CFG6", base + 0x48, f"[RO] lane {lane} ILA: faz ayari", [("ADJDIR", "16", ""), ("PHADJ", "8", ""), ("ADJCNT", "3:0", "")]),
            _reg(p + "RX_ILA_CFG7", base + 0x4C, f"[RO] lane {lane} ILA: FCHK/RES", [("FCHK", "23:16", ""), ("RES2", "15:8", ""), ("RES1", "7:0", "")]),
        ]
    if is_tx:
        regs.append(_reg(p + "CTRL_TX_GT", base + 0x60, f"[RW] lane {lane} GT TX kontrol", [
            ("TXINHIBIT", "4", ""), ("TXELECIDLE", "3", ""), ("TXPD", "2:1", "guc kapatma"), ("TXPOLARITY", "0", "polarite")]))
    else:
        regs.append(_reg(p + "CTRL_RX_GT", base + 0x64, f"[RW] lane {lane} GT RX kontrol", [
            ("RXPD", "2:1", "guc kapatma"), ("RXPOLARITY", "0", "polarite")]))
    return regs


def _with_reserved_fillers(regs: list[dict]) -> list[dict]:
    """Register genisligi bir sonraki offset'ten cikarildigindan (register_map.py) bosluklari
    `reserved` dolgu register'lariyla kapatir; boylece her gercek register 4 bayt kalir."""
    ordered = sorted(regs, key=lambda r: int(r["offset"], 0))
    out: list[dict] = []
    for i, reg in enumerate(ordered):
        out.append(reg)
        offset = int(reg["offset"], 0)
        if i + 1 < len(ordered):
            nxt = int(ordered[i + 1]["offset"], 0)
            if nxt - offset > 4:
                out.append({"name": f"RESERVED_{offset + 4:03X}", "offset": f"0x{offset + 4:03X}", "reset": "0x00000000",
                            "reserved": True, "description": "ayrilmis (dolgu)", "fields": []})
        else:
            # Son register'in genisligi alanlarindan cikarilir (bit 2'ye kadar alan -> 1 bayt olurdu);
            # arkasina 4 baytlik dolgu koyunca son gercek register de 4 bayt kalir.
            out.append({"name": f"RESERVED_{offset + 4:03X}", "offset": f"0x{offset + 4:03X}", "reset": "0x00000000",
                        "reserved": True, "description": "ayrilmis (son register 4 bayt kalsin)", "fields": []})
    return out


def jesd204c_document(*, name: str, base_address: str, parameters: dict | None = None) -> dict:
    """JESD204C cekirdegi icin Register Map dokumani (tek map; adi = custom IP kimligi)."""
    params = normalize_jesd204c_parameters(parameters)
    lanes = int(params["lanes"])
    direction = str(params["direction"])
    link_layer = str(params["link_layer"])
    regs = _jesd204c_common_registers(direction, link_layer, lanes)
    for lane in range(lanes):
        regs += _jesd204c_lane_registers(lane, direction, link_layer)
    return {
        "version": 1,
        "maps": [{
            "name": name,
            "base_address": base_address,
            "description": (f"AMD JESD204C v4.x (PG242) {direction.upper()} cekirdegi, {lanes} lane, {link_layer.upper()}, "
                            f"alt sinif {params['subclass']} - Spec2Code bilinen IP haritasi (XSA'dan otomatik)."),
            "registers": _with_reserved_fillers(regs),
        }],
    }


def known_ip_document(key: str, *, name: str, base_address: str, parameters: dict | None = None) -> dict:
    if key == "jesd204c":
        return jesd204c_document(name=name, base_address=base_address, parameters=parameters)
    raise KeyError(f"bilinmeyen IP register haritasi: {key}")


def known_ip_parameters(key: str, raw: dict | None) -> dict[str, object]:
    if key == "jesd204c":
        return normalize_jesd204c_parameters(raw)
    raise KeyError(f"bilinmeyen IP register haritasi: {key}")
