import tempfile
import unittest
from pathlib import Path

from backend.vivado_design import (
    VivadoDesignConfig,
    VivadoPeripheral,
    _local_mem_bytes,
    design_tcl,
    group_parts,
    validate_design,
    zynqmp_ddr_parts,
    zynqmp_mio_options,
)


def _zynqmp_cfg(**overrides) -> VivadoDesignConfig:
    base = dict(
        vivado_path=r"C:\Xilinx_2023_2\Vivado\2023.2",
        platform="zynq_ultrascale",
        part="xczu9eg-ffvb1156-2-e",
        temp_path=r"D:\tmp",
        peripherals=[
            VivadoPeripheral(kind="uart0", mio="MIO 18 .. 19"),
            VivadoPeripheral(kind="i2c0", mio="MIO 14 .. 15"),
        ],
        ref_clk_mhz="33.333",
        ddr_mode="none",
    )
    base.update(overrides)
    return VivadoDesignConfig(**base)


def _mb_cfg(**overrides) -> VivadoDesignConfig:
    """MicroBlaze varsayilani: kurulu Vivado 2023.2'de GERCEKTEN var olan bir
    Artix-7 parcasi (get_parts ile tarandi) ve cevre birimsiz MDM-only tasarim."""
    base = dict(
        vivado_path=r"C:\Xilinx_2023_2\Vivado\2023.2",
        platform="microblaze_7series",
        part="xc7a100tcsg324-1",
        temp_path=r"D:\tmp",
    )
    base.update(overrides)
    return VivadoDesignConfig(**base)


class VivadoDesignTclTests(unittest.TestCase):
    # Parametre adlari resmi zcu102.xsa/vck190.xsa hardware handoff'larindan
    # dogrulanmistir; bu testler uretilen Tcl'in o dogrulanmis bicimden
    # sapmasini engeller.

    def test_zynqmp_ps_only_two_stage_tcl(self) -> None:
        tcl = design_tcl(_zynqmp_cfg(), Path(r"D:\tmp\s2c"))
        self.assertIn("create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e", tcl)
        # MIO atamasi birimleri TEK TEK enable eden yardimciyla yapilir
        # (toplu -dict cakismasini onler); kullanicinin verdigi MIO aynen gecer.
        self.assertIn("proc spec2codeAssignPeripheral", tcl)
        self.assertNotIn("list_property_value", tcl)
        self.assertIn(
            "spec2codeAssignPeripheral $spec2code_ps PSU__UART0__PERIPHERAL__ENABLE "
            "PSU__UART0__PERIPHERAL__IO {MIO 18 .. 19} uart0", tcl)
        self.assertIn(
            "spec2codeAssignPeripheral $spec2code_ps PSU__I2C0__PERIPHERAL__ENABLE "
            "PSU__I2C0__PERIPHERAL__IO {MIO 14 .. 15} i2c0", tcl)
        self.assertIn("CONFIG.PSU__PSS_REF_CLK__FREQMHZ {33.333}", tcl)
        # OCM-only: DDR denetleyicisi kapali.
        self.assertIn("CONFIG.PSU__DDRC__ENABLE {0}", tcl)
        # PS-only: baglantisiz PL-yonlu arabirimler kapali (validate temiz).
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 {0}", tcl)
        self.assertIn("CONFIG.PSU__FPGA_PL0_ENABLE {0}", tcl)
        # SAHA BULGUSU (2026-07-08): FreeRTOS BSP'si psu_ttc_0 tick ister;
        # TTC'siz XSA'da workspace "FreeRTOS requires valid ticker timer"
        # ile dusuyordu. TTC0-3 her zaman acik (dahili, MIO harcamaz).
        for i in range(4):
            self.assertIn(f"CONFIG.PSU__TTC{i}__PERIPHERAL__ENABLE {{1}}", tcl)
        # Asama 1 sentezsiz XSA + isaret; bit istenmedi -> synth yok.
        # -fixed sart: fixed olmayan export PFM metadata ister (E2E bulgusu).
        self.assertIn("write_hw_platform -fixed -force -file", tcl)
        self.assertIn("generate_target all [get_files design_1.bd]", tcl)
        self.assertIn("set_property platform.name", tcl)
        self.assertIn("S2C-VIVADO|xsa_ready=", tcl)
        self.assertNotIn("launch_runs synth_1", tcl)

    def test_regmap_test_ip_injects_axi_ip_and_address(self) -> None:
        tcl = design_tcl(_zynqmp_cfg(add_regmap_test_ip=True), Path(r"D:\tmp\s2c"))
        # PS master AXI + PL saati acilir.
        self.assertIn("CONFIG.PSU__USE__M_AXI_GP0 {1}", tcl)
        self.assertIn("CONFIG.PSU__FPGA_PL0_ENABLE {1}", tcl)
        # Custom RTL BD'ye modul olarak konur, otomasyonla baglanir, adres atanir.
        self.assertIn("spec2code_regmap_test.v", tcl)
        self.assertIn("create_bd_cell -type module -reference spec2code_regmap_test regmap_test_0", tcl)
        self.assertIn("apply_bd_automation -rule xilinx.com:bd_rule:axi4", tcl)
        self.assertIn("M_AXI_HPM0_FPD", tcl)
        self.assertIn("assign_bd_address", tcl)

    def test_regmap_ip_base_extracted_from_xsa_hwh(self) -> None:
        # Atanan taban adres XSA'nın hwh MEMRANGE BASEVALUE'sinden okunur (gerçek
        # zcu102 E2E'sinde 0xA0000000 doğrulandı). Sürüm-bağımsız + xparameters
        # ile birebir.
        import io
        import zipfile
        from backend.vivado_design import _regmap_ip_base_from_xsa
        hwh = (
            '<EDKSYSTEM><MEMRANGE ADDRESSBLOCK="reg0" BASENAME="C_BASEADDR" '
            'BASEVALUE="0xA0000000" HIGHNAME="C_HIGHADDR" HIGHVALUE="0xA0000FFF" '
            'INSTANCE="regmap_test_0" MASTERBUSINTERFACE="M_AXI_HPM0_FPD" '
            'SLAVEBUSINTERFACE="s_axi"/></EDKSYSTEM>'
        )
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("design_1.hwh", hwh)
        with tempfile.NamedTemporaryFile(suffix=".xsa", delete=False) as tf:
            tf.write(buf.getvalue())
            xsa = tf.name
        self.assertEqual(_regmap_ip_base_from_xsa(xsa), "0xA0000000")

    def test_regmap_test_ip_absent_by_default(self) -> None:
        tcl = design_tcl(_zynqmp_cfg(), Path(r"D:\tmp\s2c"))
        self.assertNotIn("spec2code_regmap_test", tcl)
        self.assertNotIn("apply_bd_automation", tcl)

    def test_regmap_test_ip_rejected_on_versal(self) -> None:
        from backend.vivado_design import validate_design
        cfg = VivadoDesignConfig(
            vivado_path="C:/Xilinx", platform="versal", part="xcvc1902-vsva2197-2MP-e-S",
            temp_path="D:/tmp", peripherals=[VivadoPeripheral(kind="uart0")], add_regmap_test_ip=True)
        errs = validate_design(cfg)
        self.assertTrue(any("add_regmap_test_ip" in e for e in errs))

    def test_zynqmp_bitstream_stage_appends_synth_impl_and_fixed_xsa(self) -> None:
        tcl = design_tcl(_zynqmp_cfg(make_bitstream=True), Path(r"D:\tmp\s2c"))
        self.assertIn("launch_runs synth_1", tcl)
        self.assertIn("launch_runs impl_1 -to_step write_bitstream", tcl)
        self.assertIn("S2C-VIVADO|bit_ready=", tcl)
        self.assertIn("write_hw_platform -fixed -include_bit -force -file", tcl)
        # Asama 1 XSA, asama 2'den ONCE yazilir (erken teslim).
        self.assertLess(tcl.index("S2C-VIVADO|xsa_ready="), tcl.index("launch_runs synth_1"))

    def test_zynqmp_custom_ddr_params_pass_through(self) -> None:
        cfg = _zynqmp_cfg(ddr_mode="custom", ddr_params={
            "PSU__DDRC__MEMORY_TYPE": "DDR 4",
            "PSU__DDRC__SPEED_BIN": "DDR4_2133P",
            "PSU__DDRC__BUS_WIDTH": "32 Bit",
        })
        tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
        self.assertIn("CONFIG.PSU__DDRC__ENABLE {1}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__MEMORY_TYPE {DDR 4}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__BUS_WIDTH {32 Bit}", tcl)

    def test_versal_cips_config_and_pdi_step(self) -> None:
        cfg = VivadoDesignConfig(
            vivado_path=r"C:\X", platform="versal", part="xcvc1902-vsva2197-2MP-e-S",
            temp_path=r"D:\tmp",
            peripherals=[
                VivadoPeripheral(kind="uart0", mio="PMC_MIO 42 .. 43"),
                VivadoPeripheral(kind="i2c1", mio="PMC_MIO 44 .. 45"),
            ],
            ref_clk_mhz="33.3333", make_bitstream=True,
        )
        tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
        self.assertIn("xilinx.com:ip:versal_cips", tcl)
        # vck190.xsa'daki dogrulanmis ic ice dict bicimi.
        self.assertIn("PS_UART0_PERIPHERAL {{ENABLE 1} {IO {PMC_MIO 42 .. 43}}}", tcl)
        self.assertIn("PS_I2C1_PERIPHERAL {{ENABLE 1} {IO {PMC_MIO 44 .. 45}}}", tcl)
        self.assertIn("PMC_REF_CLK_FREQMHZ 33.3333", tcl)
        # FreeRTOS tick icin TTC'ler Versal'da da acik.
        self.assertIn("PS_TTC0_PERIPHERAL_ENABLE 1", tcl)
        self.assertIn("PS_TTC3_PERIPHERAL_ENABLE 1", tcl)
        # Versal'da imaj .pdi'dir ve write_device_image adimiyla uretilir.
        self.assertIn("launch_runs impl_1 -to_step write_device_image", tcl)
        self.assertIn(".pdi", tcl)
        self.assertNotIn("write_bitstream", tcl)

    def test_validate_rejects_bad_input_with_turkish_errors(self) -> None:
        cfg = _zynqmp_cfg(platform="zynq_7000")
        errors = validate_design(cfg)
        self.assertTrue(any("Zynq-7000 kapsam dışı" in e for e in errors))

        cfg = _zynqmp_cfg(peripherals=[VivadoPeripheral(kind="uart0", mio="MIO18-19")])
        errors = validate_design(cfg)
        self.assertTrue(any("biçim 'MIO 18 .. 19'" in e for e in errors))

        cfg = _zynqmp_cfg(peripherals=[VivadoPeripheral(kind="can0")])
        errors = validate_design(cfg)
        self.assertTrue(any("desteklenmiyor" in e for e in errors))

        # Versal'da custom DDR Faz A'da yok - durust hata.
        cfg = VivadoDesignConfig(
            vivado_path="x", platform="versal", part="p", temp_path="t",
            peripherals=[VivadoPeripheral(kind="uart0")],
            ddr_mode="custom", ddr_params={"PSU__DDRC__CL": "15"},
        )
        errors = validate_design(cfg)
        self.assertTrue(any("Versal DDR" in e for e in errors))

        cfg = _zynqmp_cfg(ddr_mode="custom", ddr_params={"HATALI__KEY": "1"})
        errors = validate_design(cfg)
        self.assertTrue(any("PSU__DDRC__" in e for e in errors))

    def test_zynqmp_auto_mio_conflict_free_assignment(self) -> None:
        # SAHA KOK NEDENI (2026-07-06): MIO bos birakilinca Vivado "uygun
        # bos yeri" SECMEZ - IP'nin sabit varsayilanlari cakisti (UART0
        # 'MIO 6 .. 7' SPI1 araligina dustu) ve set_property topluca geri
        # alindi. Beklenen: bos MIO'lar Vivado'nun yasal secenek listesinden
        # (list_property_value) cakismadan otomatik atanir; kullanici MIO'su
        # verilenler ONCE hak iddia eder; otomatikler genis-blok onceligiyle
        # (qspi -> gem/sd -> spi -> uart -> i2c) islenir.
        cfg = _zynqmp_cfg(peripherals=[
            VivadoPeripheral(kind="uart0"),
            VivadoPeripheral(kind="i2c1"),
            VivadoPeripheral(kind="spi0"),
            VivadoPeripheral(kind="spi1"),
            VivadoPeripheral(kind="qspi"),
            VivadoPeripheral(kind="i2c0", mio="MIO 14 .. 15"),
        ])
        tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
        # Elle verilen i2c0 en once; otomatiklerde qspi, spi'lerden ve
        # uart/i2c'den once gelir.
        order = [line for line in tcl.splitlines() if line.startswith("spec2codeAssign")]
        labels = ["qspi" if line.startswith("spec2codeAssignQspi") else line.rsplit(" ", 1)[-1]
                  for line in order]
        self.assertEqual(labels[0], "i2c0")
        self.assertLess(labels.index("qspi"), labels.index("spi0"))
        self.assertLess(labels.index("spi1"), labels.index("uart0"))
        self.assertLess(labels.index("uart0"), labels.index("i2c1"))
        # Bos MIO'lar {} olarak gecer (tek tek enable), toplu ENABLE dict'i yok.
        self.assertIn("PSU__SPI1__PERIPHERAL__IO {} spi1", tcl)
        self.assertNotIn("CONFIG.PSU__SPI1__PERIPHERAL__ENABLE {1} CONFIG", tcl)
        # Cakisma durumunda eyleme donuk hata: hangi birim, ne yapmali.
        self.assertIn("otomatik yerlestirilemedi", tcl)
        self.assertIn("MIO'yu formda ELLE belirtin", tcl)

    def test_qspi_mode_data_fbclk_are_generic_and_verified_values(self) -> None:
        # SAHA (2026-07-08, kullanicinin kart plani): QSPI dual parallel
        # 2x4=x8, FBCLK (MIO 6) KULLANILMIYOR. Parametre adlari/degerleri
        # zcu102.xsa'dan dogrulandi (MODE 'Dual Parallel', DATA_MODE x4,
        # GRP_FBCLK MIO 6). Mod IO'yu belirler: Single=0..5, DP=0..12.
        cfg = _zynqmp_cfg(peripherals=[
            VivadoPeripheral(kind="qspi", qspi_mode="Dual Parallel",
                             qspi_data_mode="x4", qspi_fbclk=False),
            VivadoPeripheral(kind="uart1", mio="MIO 60 .. 61"),
        ])
        self.assertEqual(validate_design(cfg), [])
        tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
        self.assertIn("proc spec2codeAssignQspi", tcl)
        self.assertIn("spec2codeAssignQspi $spec2code_ps {MIO 0 .. 12} {Dual Parallel} {x4} 0", tcl)
        self.assertIn("PSU__QSPI__PERIPHERAL__MODE", tcl)
        self.assertIn("PSU__QSPI__GRP_FBCLK__ENABLE", tcl)

        # Single mod IO 0..5'e gider; FBCLK istenirse MIO 6 dict'e girer.
        cfg2 = _zynqmp_cfg(peripherals=[VivadoPeripheral(kind="qspi", qspi_fbclk=True)])
        tcl2 = design_tcl(cfg2, Path(r"D:\tmp\s2c"))
        self.assertIn("spec2codeAssignQspi $spec2code_ps {MIO 0 .. 5} {Single} {} 1", tcl2)

        # Hatali degerler ve qspi-disi kullanim durust hata verir.
        bad = _zynqmp_cfg(peripherals=[VivadoPeripheral(kind="qspi", qspi_mode="Octal")])
        self.assertTrue(any("qspi_mode" in e for e in validate_design(bad)))
        bad = _zynqmp_cfg(peripherals=[VivadoPeripheral(kind="uart0", qspi_fbclk=True)])
        self.assertTrue(any("yalnız qspi" in e for e in validate_design(bad)))

    def test_group_parts_uses_vivado_family_not_prefix_guess(self) -> None:
        # Siniflama Vivado'nun FAMILY alanindan yapilir: xcvu (Virtex
        # UltraScale+) versal DEGILDIR ve listeye girmez; zynquplusRFSOC
        # ZynqMP sayilir. Cihaz gruplama parcanin '-' oncesidir.
        lines = [
            "S2C-PART|zynquplus|xczu9eg-ffvb1156-2-e",
            "S2C-PART|zynquplus|xczu9eg-ffvb1156-1-e",
            "S2C-PART|zynquplusRFSOC|xczu28dr-ffvg1517-2-e",
            "S2C-PART|versalaicore|xcvc1902-vsva2197-2MP-e-S",
            "S2C-PART|virtexuplus|xcvu9p-flga2104-2-e",
            "S2C-PART|artix7|xc7a35t-cpg236-1",
            "gurultu satiri",
        ]
        grouped = group_parts(lines)
        self.assertEqual(sorted(grouped["zynq_ultrascale"]), ["xczu28dr", "xczu9eg"])
        self.assertEqual(grouped["zynq_ultrascale"]["xczu9eg"],
                         ["xczu9eg-ffvb1156-1-e", "xczu9eg-ffvb1156-2-e"])
        self.assertEqual(list(grouped["versal"]), ["xcvc1902"])
        self.assertNotIn("xcvu9p", str(grouped))

    def test_ddr_model_pool_sets_geometry_but_never_timings(self) -> None:
        # DDR model havuzu ilkesi: geometri (Xilinx memparts.csv) + hiz sinifi
        # verilir; CL/CWL/tRCD gibi zamanlamalar Tcl'e YAZILMAZ - PCW bin'e
        # gore kendisi hesaplar (probe kaniti: 2400R -> CL16/CWL12/tFAW30).
        # Kullanicinin karti: MT40A512M16LY-062E x2 = 32-bit.
        parts = zynqmp_ddr_parts()
        self.assertTrue(any(p["id"] == "mt40a512m16" for p in parts), "kullanicinin yongasi havuzda yok")
        self.assertTrue(any(p["id"] == "mt40a256m16" for p in parts))

        cfg = _zynqmp_cfg(ddr_mode="model", ddr_model="mt40a512m16", ddr_bus_width="32 Bit")
        self.assertEqual(validate_design(cfg), [])
        tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
        self.assertIn("CONFIG.PSU__DDRC__ENABLE {1}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__DEVICE_CAPACITY {8192 MBits}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__DRAM_WIDTH {16 Bits}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__ROW_ADDR_COUNT {16}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__BG_ADDR_COUNT {1}", tcl)
        self.assertIn("CONFIG.PSU__DDRC__BUS_WIDTH {32 Bit}", tcl)
        # HIZA DOKUNULMAZ (E2E bulgusu: bin/frekans degisimi PCW'de
        # bin<->frekans<->CL tavuk-yumurtasina takilip atomik geri aliniyor;
        # PCW'nin tutarli 1600 varsayilani kalir, parcalar geriye uyumlu).
        for forbidden in ("PSU__DDRC__SPEED_BIN", "PSU__CRF_APB__DDR_CTRL__FREQMHZ",
                          "PSU__DDRC__CL", "PSU__DDRC__CWL", "PSU__DDRC__T_RCD", "PSU__DDRC__T_FAW"):
            self.assertNotIn(forbidden, tcl, f"{forbidden} yazilmamali")

        # Hatali model/genislik durust hata verir.
        bad = _zynqmp_cfg(ddr_mode="model", ddr_model="olmayan_yonga")
        self.assertTrue(any("havuzda yok" in e for e in validate_design(bad)))
        bad = _zynqmp_cfg(ddr_mode="model", ddr_model="mt40a512m16", ddr_bus_width="128 Bit")
        self.assertTrue(any("desteklenmiyor" in e for e in validate_design(bad)))

    def test_zynqmp_mio_options_table_is_present_and_vivado_sourced(self) -> None:
        # MIO dropdown tablosu (backend/data/zynqmp_mio_options.json): Vivado
        # kabul-testi taramasindan uretildi, part-bagimsiz. UI bu tablodan
        # beslenir. Temel birimlerin gecerli konumlari bulunmali; UART0
        # taramada temiz cikti (4'er blok), QSPI iki bilinen moduyla eklenir.
        opts = zynqmp_mio_options()
        for kind in ("uart0", "i2c0", "i2c1", "spi0", "gem3", "sd1", "qspi"):
            self.assertIn(kind, opts, f"{kind} MIO tablosunda yok")
            self.assertTrue(opts[kind]["options"], f"{kind} icin secenek listesi bos")
        # UART0 taramasi 4'er blok verdi (2..3, 6..7, 10..11 ...).
        self.assertIn("MIO 2 .. 3", opts["uart0"]["options"])
        self.assertIn("MIO 18 .. 19", opts["uart0"]["options"])
        # QSPI iki bilinen moduyla (x1 dar, x4 genis).
        self.assertEqual(opts["qspi"]["options"], ["MIO 0 .. 5", "MIO 0 .. 12"])
        # Tum secenekler "MIO a .. b" bicimindedir (bozuk kayit yok).
        for kind, spec in opts.items():
            for opt in spec["options"]:
                self.assertRegex(opt, r"^MIO \d+ \.\. \d+$", f"{kind}: bozuk MIO '{opt}'")

    def test_validate_accepts_good_zynqmp_and_versal(self) -> None:
        self.assertEqual(validate_design(_zynqmp_cfg()), [])
        cfg = VivadoDesignConfig(
            vivado_path="x", platform="versal", part="xcvc1902",
            temp_path="t", peripherals=[VivadoPeripheral(kind="uart0", mio="PMC_MIO 42 .. 43")],
        )
        self.assertEqual(validate_design(cfg), [])


class MicroBlazeDesignTclTests(unittest.TestCase):
    """MicroBlaze (7 serisi PL) uretimi.

    Buradaki her literal Vivado 2023.2 kurulumundan DOGRULANMISTIR:
    otomasyon secenek sozlugu ``data/rsb/design_assist/block/microblaze/bd.tcl``
    (``dbg_all [list None "Debug Only" "Debug & UART" "Extended Debug"]``),
    geri kalani ise canli batch probe'lariyla.
    """

    def test_microblaze_tcl_enables_the_mdm_uart(self) -> None:
        tcl = design_tcl(_mb_cfg(), Path(r"D:\tmp\s2c"))
        self.assertIn("create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0", tcl)
        self.assertIn("apply_bd_automation -rule xilinx.com:bd_rule:microblaze", tcl)
        # MDM UART'i acan TEK literal. Yazimi Vivado'nun kendi otomasyon
        # sozlugunden gelir; "Debug Only" MDM'i UART'siz kurar ve Faz 3'un
        # MDM transportu calismaz.
        self.assertIn("debug_module {Debug & UART}", tcl)
        self.assertNotIn("debug_module {Debug Only}", tcl)
        self.assertIn("local_mem {128KB}", tcl)
        self.assertIn("axi_periph {Enabled}", tcl)
        self.assertIn("axi_intc {0}", tcl)
        self.assertIn("clk {New External Port (100 MHz)}", tcl)
        # PS makinesi MicroBlaze'e SIZMAZ.
        for ps_token in ("zynq_ultra_ps_e", "versal_cips", "PSU__", "PS_PMC_CONFIG", "psu_init"):
            self.assertNotIn(ps_token, tcl, f"PS artefakti MicroBlaze Tcl'ine sizdi: {ps_token}")

    def test_microblaze_tcl_verifies_the_automation_instead_of_trusting_it(self) -> None:
        # SAHA BULGUSU (canli probe): gecersiz bir config degerinde
        # apply_bd_automation Tcl HATASI ATMAZ - "Invalid configuration value"
        # basip sessizce hicbir sey yapar ve batch 0 ile cikar. Uretilen Tcl bu
        # yuzden MDM'i ve UART bayragini ACIKCA dogrulamak ZORUNDA.
        tcl = design_tcl(_mb_cfg(), Path(r"D:\tmp\s2c"))
        self.assertIn("proc spec2codeMbVerifyAutomation", tcl)
        self.assertIn('get_bd_cells -quiet -filter {VLNV =~ "*:mdm:*"}', tcl)
        self.assertIn("CONFIG.C_USE_UART", tcl)
        # Dogrulama otomasyondan SONRA, cevre birimlerinden ONCE cagrilir.
        self.assertLess(tcl.index("apply_bd_automation -rule xilinx.com:bd_rule:microblaze"),
                        tcl.index("\nspec2codeMbVerifyAutomation\n"))

    def test_microblaze_clock_frequency_is_written_to_the_port(self) -> None:
        # Otomasyon string'i daima dogrulanmis (100 MHz) variantidir; istenen
        # frekans porta ACIKCA yazilir (probe: set_property FREQ_HZ tutuyor).
        tcl = design_tcl(_mb_cfg(mb_clk_mhz="50"), Path(r"D:\tmp\s2c"))
        self.assertIn("clk {New External Port (100 MHz)}", tcl)
        self.assertIn("set_property CONFIG.FREQ_HZ 50000000 [get_bd_ports Clk]", tcl)

    def test_microblaze_peripherals_use_vivado_instance_names_and_real_ports(self) -> None:
        tcl = design_tcl(
            _mb_cfg(mb_axi_iic=2, mb_axi_spi=1, mb_axi_uartlite=1, mb_axi_gpio=1),
            Path(r"D:\tmp\s2c"))
        # Ornek adlari xparameters.h'taki XPAR_AXI_IIC_0_* adlarina donusur -
        # Faz 1-3 zinciri tam olarak bunlari bekler.
        for inst, vlnv in (
            ("axi_iic_0", "xilinx.com:ip:axi_iic"),
            ("axi_iic_1", "xilinx.com:ip:axi_iic"),
            ("axi_quad_spi_0", "xilinx.com:ip:axi_quad_spi"),
            ("axi_uartlite_0", "xilinx.com:ip:axi_uartlite"),
            ("axi_gpio_0", "xilinx.com:ip:axi_gpio"),
        ):
            self.assertIn(f"create_bd_cell -type ip -vlnv {vlnv} {inst}\n", tcl)
        # Quad SPI'nin AXI slave'i FARKLI adlanir (AXI_LITE), digerleri S_AXI.
        self.assertIn("[get_bd_intf_pins axi_quad_spi_0/AXI_LITE]", tcl)
        self.assertIn("[get_bd_intf_pins axi_iic_0/S_AXI]", tcl)
        # Interconnect ACIKCA yeniden kullanilir (her birime yeni bir tane degil).
        self.assertIn("intc_ip {/microblaze_0_axi_periph}", tcl)
        self.assertNotIn("New AXI Interconnect", tcl)
        # ext_spi_clk ayri bir saat girisidir; baglanmazsa validate duser.
        self.assertIn("spec2codeMbTieSpiClock axi_quad_spi_0\n", tcl)
        # Her cevre biriminin dis arayuzu gercek bir port olur.
        for intf in ("axi_iic_0/IIC", "axi_quad_spi_0/SPI_0",
                     "axi_uartlite_0/UART", "axi_gpio_0/GPIO"):
            self.assertIn(f"make_bd_intf_pins_external [get_bd_intf_pins {intf}]", tcl)
        # Akis sirasi: hucre -> AXI otomasyonu -> disari cikarma -> adres -> XSA.
        order = [tcl.index("create_bd_cell -type ip -vlnv xilinx.com:ip:axi_iic axi_iic_0"),
                 tcl.index("apply_bd_automation -rule xilinx.com:bd_rule:axi4"),
                 tcl.index("make_bd_intf_pins_external"),
                 tcl.index("\nassign_bd_address\n"),
                 tcl.index("\nvalidate_bd_design\n"),
                 tcl.index("make_wrapper"),
                 tcl.index("generate_target all"),
                 tcl.index("write_hw_platform -fixed -force")]
        self.assertEqual(order, sorted(order))
        self.assertIn("xsa_ready=", tcl)

    def test_microblaze_without_peripherals_is_still_a_valid_mdm_only_design(self) -> None:
        tcl = design_tcl(_mb_cfg(), Path(r"D:\tmp\s2c"))
        self.assertNotIn("bd_rule:axi4", tcl)
        self.assertNotIn("make_bd_intf_pins_external", tcl)
        # MDM UART tek basina da anlamlidir: ajan MDM uzerinden konusur.
        self.assertIn("debug_module {Debug & UART}", tcl)
        self.assertIn("write_hw_platform -fixed -force", tcl)

    def test_microblaze_external_reset_port_is_explicit(self) -> None:
        # Otomasyon proc_sys_reset/ext_reset_in'i BAGLANMADAN birakiyor; Vivado
        # onu 0'a bagliyor ve CRITICAL WARNING BD 41-759 veriyor. Portu acikca
        # disari cikariyoruz (polarite C_EXT_RESET_HIGH'dan raporlanir).
        tcl = design_tcl(_mb_cfg(), Path(r"D:\tmp\s2c"))
        self.assertIn("proc spec2codeMbExternalReset", tcl)
        self.assertIn("make_bd_pins_external -name reset", tcl)
        self.assertIn("C_EXT_RESET_HIGH", tcl)
        # Kullanicinin XDC'sinin kisitlamasi gereken portlar bildirilir.
        self.assertIn("proc spec2codeMbReportPorts", tcl)

    def test_microblaze_bitstream_requires_user_xdc(self) -> None:
        # DURUSTLUK KAPISI: MicroBlaze PL'de yasar; saat/reset/arayuz pinleri
        # yalniz kartin semasindadir. Pin atamasi UYDURULMAZ.
        errors = validate_design(_mb_cfg(make_bitstream=True))
        self.assertTrue(any("XDC" in e for e in errors), errors)
        self.assertTrue(any("UYDURMAZ" in e for e in errors), errors)
        # XSA-only (sentezsiz) SIFIR kisitla calisir.
        self.assertEqual(validate_design(_mb_cfg()), [])
        tcl = design_tcl(_mb_cfg(), Path(r"D:\tmp\s2c"))
        self.assertNotIn("launch_runs", tcl)
        self.assertNotIn("constrs_1", tcl)

    def test_microblaze_bitstream_with_xdc_adds_constraints_and_synth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            xdc = Path(tmp) / "board.xdc"
            xdc.write_text("set_property PACKAGE_PIN E3 [get_ports Clk]\n", encoding="utf-8")
            cfg = _mb_cfg(make_bitstream=True, constraints_path=str(xdc), mb_axi_iic=1)
            self.assertEqual(validate_design(cfg), [])
            tcl = design_tcl(cfg, Path(r"D:\tmp\s2c"))
            self.assertIn(f"add_files -fileset constrs_1 -norecurse {{{str(xdc).replace(chr(92), '/')}}}", tcl)
            order = [tcl.index("constrs_1"), tcl.index("launch_runs synth_1"),
                     tcl.index("launch_runs impl_1"), tcl.index("bit_ready="),
                     tcl.index("write_hw_platform -fixed -include_bit")]
            self.assertEqual(order, sorted(order))
            # 7 serisi: .bit (Versal .pdi degil).
            self.assertIn("write_bitstream", tcl)
            self.assertNotIn("write_device_image", tcl)

    def test_microblaze_validation_rejects_ps_fields_and_bad_values(self) -> None:
        errors = validate_design(_mb_cfg(peripherals=[VivadoPeripheral(kind="uart0")]))
        self.assertTrue(any("PS çevre birimi" in e for e in errors), errors)
        errors = validate_design(_mb_cfg(ddr_mode="model", ddr_model="x"))
        self.assertTrue(any("DDR" in e for e in errors), errors)
        errors = validate_design(_mb_cfg(mb_local_mem="1MB"))
        self.assertTrue(any("mb_local_mem" in e for e in errors), errors)
        errors = validate_design(_mb_cfg(mb_axi_iic=5))
        self.assertTrue(any("0..2" in e for e in errors), errors)
        errors = validate_design(_mb_cfg(mb_clk_mhz="hizli"))
        self.assertTrue(any("mb_clk_mhz" in e for e in errors), errors)
        errors = validate_design(_mb_cfg(constraints_path=r"D:\yok\boyle\bir.xdc"))
        self.assertTrue(any("bulunamadı" in e for e in errors), errors)
        # XDC su an yalniz MicroBlaze akisinda kullaniliyor - sessizce yok sayilmaz.
        errors = validate_design(_zynqmp_cfg(constraints_path="x.xdc"))
        self.assertTrue(any("microblaze_7series" in e for e in errors), errors)

    def test_local_mem_above_the_automation_ceiling_resizes_the_lmb_segments(self) -> None:
        """128KB ustu LMB: otomasyon TAVANDAN kurulur, sonra segment buyutulur.

        SAHA BULGUSU (Faz 5, gercek mb-gcc link'i): tam ajan + 3 cihaz surucusu
        + BSP 128KB'ye sigmiyor (`.text` 24840 bayt tasti). Vivado otomasyonunun
        sozlugu 128KB'de bitiyor, o yuzden buyugu adres segmenti uzerinden.
        CANLI PROBE: `set_property range 256K` -> hwh MEMRANGE HIGHVALUE
        0x0001FFFF -> 0x0003FFFF, blk_mem_gen derinligi 32768 -> 65536.
        """
        tcl = design_tcl(_mb_cfg(mb_local_mem="256KB"), Path(r"D:\tmp\s2c"))
        # Otomasyona GECERLI bir deger gider (256KB otomasyon sozlugunde YOK).
        self.assertIn("local_mem {128KB}", tcl)
        self.assertNotIn("local_mem {256KB}", tcl)
        # ... ve hemen ardindan segment buyutulur. Vivado adres birimi K'dir,
        # geri okuma ise hex BAYT sayisidir -> beklenen bayt da gecirilir.
        self.assertIn("\nspec2codeMbResizeLocalMemory {256K} 262144\n", tcl)
        self.assertNotIn("spec2codeMbResizeLocalMemory {256KB}", tcl)
        # Sira: otomasyon -> dogrulama -> buyutme.
        self.assertLess(tcl.index("apply_bd_automation -rule xilinx.com:bd_rule:microblaze"),
                        tcl.index("\nspec2codeMbResizeLocalMemory {256K}"))
        # Buyutme yazip GERI OKUR (sessiz no-op'a guvenilmez doktrini) ve
        # karsilastirmayi SAYISAL yapar (canli kosuda '256K' ne '0x00040000').
        self.assertIn("proc spec2codeMbResizeLocalMemory", tcl)
        self.assertIn("get_property range $spec2code_seg", tcl)
        self.assertIn("$spec2code_got_bytes != $wanted_bytes", tcl)
        self.assertIn("S2C-VIVADO|local_mem=", tcl)

    def test_local_mem_byte_conversion(self) -> None:
        self.assertEqual(_local_mem_bytes("128KB"), 131072)
        self.assertEqual(_local_mem_bytes("256KB"), 262144)
        self.assertEqual(_local_mem_bytes("512KB"), 524288)
        tcl = design_tcl(_mb_cfg(mb_local_mem="512KB"), Path(r"D:\tmp\s2c"))
        self.assertIn("\nspec2codeMbResizeLocalMemory {512K} 524288\n", tcl)

    def test_local_mem_at_or_below_the_ceiling_does_not_resize(self) -> None:
        for size in ("64KB", "128KB"):
            with self.subTest(size=size):
                tcl = design_tcl(_mb_cfg(mb_local_mem=size), Path(r"D:\tmp\s2c"))
                self.assertIn("local_mem {" + size + "}", tcl)
                # Proc TANIMI her zaman var; CAGRI (satir basi) olmamali.
                self.assertNotIn("\nspec2codeMbResizeLocalMemory {", tcl)

    def test_oversize_local_mem_values_are_accepted_by_validation(self) -> None:
        for size in ("256KB", "512KB"):
            with self.subTest(size=size):
                self.assertEqual(validate_design(_mb_cfg(mb_local_mem=size)), [])

    def test_group_parts_maps_7series_families_to_microblaze(self) -> None:
        # Aile adlari kurulu Vivado 2023.2'nin get_parts FAMILY degerleridir.
        grouped = group_parts([
            "S2C-PART|artix7|xc7a100tcsg324-1",
            "S2C-PART|artix7|xc7a100tcsg324-2",
            "S2C-PART|kintex7|xc7k325tffg900-2",
            "S2C-PART|spartan7|xc7s50csga324-1",
            "S2C-PART|zynquplus|xczu9eg-ffvb1156-2-e",
        ])
        self.assertEqual(sorted(grouped["microblaze_7series"]),
                         ["xc7a100tcsg324", "xc7k325tffg900", "xc7s50csga324"])
        self.assertEqual(grouped["microblaze_7series"]["xc7a100tcsg324"],
                         ["xc7a100tcsg324-1", "xc7a100tcsg324-2"])
        # Zynq-7000 BILINCLI olarak disarida (ayri platform).
        self.assertNotIn("microblaze_7series", str(group_parts(["S2C-PART|zynq|xc7z020clg484-1"])["versal"]))
        self.assertEqual(group_parts(["S2C-PART|zynq|xc7z020clg484-1"])["microblaze_7series"], {})


if __name__ == "__main__":
    unittest.main()
