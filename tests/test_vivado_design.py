import tempfile
import unittest
from pathlib import Path

from backend.vivado_design import (
    VivadoDesignConfig,
    VivadoPeripheral,
    design_tcl,
    group_parts,
    validate_design,
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
        # Asama 1 sentezsiz XSA + isaret; bit istenmedi -> synth yok.
        # -fixed sart: fixed olmayan export PFM metadata ister (E2E bulgusu).
        self.assertIn("write_hw_platform -fixed -force -file", tcl)
        self.assertIn("generate_target all [get_files design_1.bd]", tcl)
        self.assertIn("set_property platform.name", tcl)
        self.assertIn("S2C-VIVADO|xsa_ready=", tcl)
        self.assertNotIn("launch_runs synth_1", tcl)

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
        order = [line for line in tcl.splitlines() if line.startswith("spec2codeAssignPeripheral")]
        labels = [line.rsplit(" ", 1)[-1] for line in order]
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

    def test_validate_accepts_good_zynqmp_and_versal(self) -> None:
        self.assertEqual(validate_design(_zynqmp_cfg()), [])
        cfg = VivadoDesignConfig(
            vivado_path="x", platform="versal", part="xcvc1902",
            temp_path="t", peripherals=[VivadoPeripheral(kind="uart0", mio="PMC_MIO 42 .. 43")],
        )
        self.assertEqual(validate_design(cfg), [])


if __name__ == "__main__":
    unittest.main()
