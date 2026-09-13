# Nexys A7-100T (xc7a100tcsg324-1) MicroBlaze referans tasarimi - Spec2Code kart dogrulamasi.
#
# MB (256KB LMB, MDM debug) + AXI UARTLite (USB-UART, 115200) + AXI IIC (kart ustu ADT7420,
# adres 0x4B) + AXI Quad SPI (konfigurasyon flash'i S25FL128S; SCK STARTUPE2 uzerinden,
# C_USE_STARTUP=1) - pin kisitlari Digilent Nexys-A7-100T-Master.xdc'den.
# Cikti: microblaze_nexys_a7.xsa (bit'siz), microblaze_nexys_a7_bit.xsa (bit'li), .bit, .mmi.
#
# Kullanim: vivado -mode batch -source scripts/make_nexys_a7_design.tcl [-tclargs mdm]
#   `mdm` verilirse MDM UART acilir (`debug_module {Debug & UART}`): Test Bench MDM
#   transportu (JTAG uzerinden, USB-UART kablosu gerekmez) icin. Ciktilar `_mdm` sonekli.
set mdm_uart  [expr {[lsearch -exact $argv "mdm"] >= 0}]
# `regmap`: Spec2Code Register Map Test IP'si (backend/data/spec2code_regmap_test.v, AXI4-Lite) BD'ye
# modul olarak eklenir -> bilinen IP haritasi (register_map=regmap_test) kartta dogrulanir.
set regmap_ip [expr {[lsearch -exact $argv "regmap"] >= 0}]
# `gpio`: AXI GPIO donanim testi - axi_gpio_0 (CH1: 16 LED cikis, CH2: 16 anahtar giris),
# axi_gpio_1 (CH1: 5 buton giris, CH2: 6 RGB LED cikis). Ajan gpio_read/gpio_write + Test Bench GPIO karti.
set gpio_ip   [expr {[lsearch -exact $argv "gpio"] >= 0}]
set suffix    [expr {$mdm_uart ? "_mdm" : ""}][expr {$regmap_ip ? "_regmap" : ""}][expr {$gpio_ip ? "_gpio" : ""}]
set root_dir   D:/Projects/claude/Spec2Code
set proj_dir   $root_dir/test/0_temp_dbg/vivado_nexys_a7$suffix
set out_dir    $root_dir/test/0_dosyalar
set xsa_out    $out_dir/microblaze_nexys_a7$suffix.xsa
set xsa_bit    $out_dir/microblaze_nexys_a7${suffix}_bit.xsa
set bit_out    $out_dir/microblaze_nexys_a7$suffix.bit
set mmi_out    $out_dir/microblaze_nexys_a7$suffix.mmi
set debug_mod  [expr {$mdm_uart ? "Debug & UART" : "Debug Only"}]
set xdc_path   $proj_dir/nexys_a7.xdc
file delete -force $proj_dir
file mkdir $proj_dir

create_project -force nexys_a7 $proj_dir -part xc7a100tcsg324-1
if {$regmap_ip} {
    add_files -norecurse $root_dir/backend/data/spec2code_regmap_test.v
    update_compile_order -fileset sources_1
}

puts "STEP: block design"
create_bd_design "design_1"
create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0
apply_bd_automation -rule xilinx.com:bd_rule:microblaze -config [list \
    local_mem {128KB} ecc {None} cache {None} debug_module $debug_mod \
    axi_periph {Enabled} axi_intc {0} clk {New External Port (100 MHz)} ] \
    [get_bd_cells microblaze_0]

# Reset: Nexys A7 CPU_RESETN AKTIF-DUSUK butondur.
set rst [get_bd_cells -filter {VLNV =~ "*:proc_sys_reset:*"}]
set_property CONFIG.C_EXT_RESET_HIGH 0 $rst
make_bd_pins_external -name reset [get_bd_pins $rst/ext_reset_in]

create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite axi_uartlite_0
set_property CONFIG.C_BAUDRATE 115200 [get_bd_cells axi_uartlite_0]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_iic axi_iic_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_quad_spi axi_quad_spi_0
# Standart SPI, tek slave, SCK STARTUPE2'den (konfigurasyon flash'inin CCLK pini),
# 100 MHz / 4 = 25 MHz (S25FL128S READ 0x03 icin <= 50 MHz).
set_property -dict [list CONFIG.C_USE_STARTUP {1} CONFIG.C_USE_STARTUP_INT {1} \
    CONFIG.C_SPI_MODE {0} CONFIG.C_NUM_SS_BITS {1} CONFIG.C_SCK_RATIO {4} \
    CONFIG.C_FIFO_DEPTH {16}] [get_bd_cells axi_quad_spi_0]

foreach slave {axi_uartlite_0/S_AXI axi_iic_0/S_AXI axi_quad_spi_0/AXI_LITE} {
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/microblaze_0 (Periph)} Slave "/$slave" \
        ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}] \
        [get_bd_intf_pins $slave]
}
if {$regmap_ip} {
    create_bd_cell -type module -reference spec2code_regmap_test regmap_test_0
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/microblaze_0 (Periph)} Slave {/regmap_test_0/s_axi} \
        ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}] \
        [get_bd_intf_pins regmap_test_0/s_axi]
}
if {$gpio_ip} {
    create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio axi_gpio_0
    set_property -dict [list CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO_WIDTH {16} CONFIG.C_ALL_OUTPUTS {1} \
        CONFIG.C_GPIO2_WIDTH {16} CONFIG.C_ALL_INPUTS_2 {1} CONFIG.C_DOUT_DEFAULT {0x00000000}] [get_bd_cells axi_gpio_0]
    create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio axi_gpio_1
    set_property -dict [list CONFIG.C_IS_DUAL {1} CONFIG.C_GPIO_WIDTH {5} CONFIG.C_ALL_INPUTS {1} \
        CONFIG.C_GPIO2_WIDTH {6} CONFIG.C_ALL_OUTPUTS_2 {1} CONFIG.C_DOUT_DEFAULT_2 {0x00000000}] [get_bd_cells axi_gpio_1]
    foreach slave {axi_gpio_0/S_AXI axi_gpio_1/S_AXI} {
        apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
            Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
            Master {/microblaze_0 (Periph)} Slave "/$slave" \
            ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}] \
            [get_bd_intf_pins $slave]
    }
    make_bd_intf_pins_external [get_bd_intf_pins axi_gpio_0/GPIO]
    make_bd_intf_pins_external [get_bd_intf_pins axi_gpio_0/GPIO2]
    make_bd_intf_pins_external [get_bd_intf_pins axi_gpio_1/GPIO]
    make_bd_intf_pins_external [get_bd_intf_pins axi_gpio_1/GPIO2]
    set_property NAME LED [get_bd_intf_ports GPIO_0]
    set_property NAME SW  [get_bd_intf_ports GPIO2_0]
    set_property NAME BTN [get_bd_intf_ports GPIO_1]
    set_property NAME RGB [get_bd_intf_ports GPIO2_1]
}
set spi_aclk_net [get_bd_nets -of_objects [get_bd_pins axi_quad_spi_0/s_axi_aclk]]
connect_bd_net -net $spi_aclk_net [get_bd_pins axi_quad_spi_0/ext_spi_clk]

make_bd_intf_pins_external [get_bd_intf_pins axi_uartlite_0/UART]
make_bd_intf_pins_external [get_bd_intf_pins axi_iic_0/IIC]
make_bd_intf_pins_external [get_bd_intf_pins axi_quad_spi_0/SPI_0]
# Dis arayuz adlari sabitlenir (otomatik ad UART_0 / IIC_0 / SPI_0_0 gelir; XDC bu
# adlari bekler: UART_rxd, IIC_scl_io, SPI_0_ss_io ...).
set_property NAME UART  [get_bd_intf_ports UART_0]
set_property NAME IIC   [get_bd_intf_ports IIC_0]
set_property NAME SPI_0 [get_bd_intf_ports SPI_0_0]

assign_bd_address
if {$regmap_ip} {
    # Otomatik atama IP'yi LMB ile cakisan 0x00020000'e koyar; AXI cevre birimi bolgesine tasi.
    set_property offset 0x44A10000 [get_bd_addr_segs {microblaze_0/Data/SEG_regmap_test_0_reg0}]
}
# LMB 256K (blok otomasyonu tavani 128KB; segment range buyutulur)
set_property range 256K [get_bd_addr_segs {microblaze_0/Data/SEG_dlmb_bram_if_cntlr_Mem}]
set_property range 256K [get_bd_addr_segs {microblaze_0/Instruction/SEG_ilmb_bram_if_cntlr_Mem}]
validate_bd_design
save_bd_design
foreach p [get_bd_ports] { puts "PORT [get_property NAME $p] [get_property DIR $p]" }
foreach p [get_bd_intf_ports] { puts "INTF [get_property NAME $p]" }

puts "STEP: wrapper + XSA (bit'siz)"
set wrapper [make_wrapper -files [get_files design_1.bd] -top]
add_files -norecurse $wrapper
set_property top design_1_wrapper [current_fileset]
update_compile_order -fileset sources_1
generate_target all [get_files design_1.bd]
write_hw_platform -fixed -force $xsa_out
puts "XSA-DONE: $xsa_out"

puts "STEP: XDC"
set fh [open $xdc_path w]
puts $fh {
## Nexys A7-100T - Spec2Code MicroBlaze referans tasarimi (Digilent master XDC'den)
set_property -dict { PACKAGE_PIN E3 IOSTANDARD LVCMOS33 } [get_ports Clk]
create_clock -add -name sys_clk_pin -period 10.000 -waveform {0 5} [get_ports Clk]
set_property -dict { PACKAGE_PIN C12 IOSTANDARD LVCMOS33 } [get_ports reset]
## USB-UART (FTDI): C4 = FPGA RX (UART_TXD_IN), D4 = FPGA TX (UART_RXD_OUT)
set_property -dict { PACKAGE_PIN C4 IOSTANDARD LVCMOS33 } [get_ports UART_rxd]
set_property -dict { PACKAGE_PIN D4 IOSTANDARD LVCMOS33 } [get_ports UART_txd]
## ADT7420 sicaklik sensoru I2C
set_property -dict { PACKAGE_PIN C14 IOSTANDARD LVCMOS33 } [get_ports IIC_scl_io]
set_property -dict { PACKAGE_PIN C15 IOSTANDARD LVCMOS33 } [get_ports IIC_sda_io]
## S25FL128S QSPI flash (SCK STARTUPE2 uzerinden; burada pin yok)
set_property -dict { PACKAGE_PIN L13 IOSTANDARD LVCMOS33 } [get_ports SPI_0_ss_io]
set_property -dict { PACKAGE_PIN K17 IOSTANDARD LVCMOS33 } [get_ports SPI_0_io0_io]
set_property -dict { PACKAGE_PIN K18 IOSTANDARD LVCMOS33 } [get_ports SPI_0_io1_io]
## AXI GPIO (gpio varyanti): LED[15:0], SW[15:0] (SW8/SW9 LVCMOS18), BTN[4:0] = C,U,L,R,D, RGB[5:0] = 16R,16G,16B,17R,17G,17B
set_property -dict { PACKAGE_PIN H17 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[0]}]
set_property -dict { PACKAGE_PIN K15 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[1]}]
set_property -dict { PACKAGE_PIN J13 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[2]}]
set_property -dict { PACKAGE_PIN N14 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[3]}]
set_property -dict { PACKAGE_PIN R18 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[4]}]
set_property -dict { PACKAGE_PIN V17 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[5]}]
set_property -dict { PACKAGE_PIN U17 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[6]}]
set_property -dict { PACKAGE_PIN U16 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[7]}]
set_property -dict { PACKAGE_PIN V16 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[8]}]
set_property -dict { PACKAGE_PIN T15 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[9]}]
set_property -dict { PACKAGE_PIN U14 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[10]}]
set_property -dict { PACKAGE_PIN T16 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[11]}]
set_property -dict { PACKAGE_PIN V15 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[12]}]
set_property -dict { PACKAGE_PIN V14 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[13]}]
set_property -dict { PACKAGE_PIN V12 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[14]}]
set_property -dict { PACKAGE_PIN V11 IOSTANDARD LVCMOS33 } [get_ports {LED_tri_o[15]}]
set_property -dict { PACKAGE_PIN J15 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[0]}]
set_property -dict { PACKAGE_PIN L16 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[1]}]
set_property -dict { PACKAGE_PIN M13 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[2]}]
set_property -dict { PACKAGE_PIN R15 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[3]}]
set_property -dict { PACKAGE_PIN R17 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[4]}]
set_property -dict { PACKAGE_PIN T18 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[5]}]
set_property -dict { PACKAGE_PIN U18 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[6]}]
set_property -dict { PACKAGE_PIN R13 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[7]}]
set_property -dict { PACKAGE_PIN T8  IOSTANDARD LVCMOS18 } [get_ports {SW_tri_i[8]}]
set_property -dict { PACKAGE_PIN U8  IOSTANDARD LVCMOS18 } [get_ports {SW_tri_i[9]}]
set_property -dict { PACKAGE_PIN R16 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[10]}]
set_property -dict { PACKAGE_PIN T13 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[11]}]
set_property -dict { PACKAGE_PIN H6  IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[12]}]
set_property -dict { PACKAGE_PIN U12 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[13]}]
set_property -dict { PACKAGE_PIN U11 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[14]}]
set_property -dict { PACKAGE_PIN V10 IOSTANDARD LVCMOS33 } [get_ports {SW_tri_i[15]}]
set_property -dict { PACKAGE_PIN N17 IOSTANDARD LVCMOS33 } [get_ports {BTN_tri_i[0]}]
set_property -dict { PACKAGE_PIN M18 IOSTANDARD LVCMOS33 } [get_ports {BTN_tri_i[1]}]
set_property -dict { PACKAGE_PIN P17 IOSTANDARD LVCMOS33 } [get_ports {BTN_tri_i[2]}]
set_property -dict { PACKAGE_PIN M17 IOSTANDARD LVCMOS33 } [get_ports {BTN_tri_i[3]}]
set_property -dict { PACKAGE_PIN P18 IOSTANDARD LVCMOS33 } [get_ports {BTN_tri_i[4]}]
set_property -dict { PACKAGE_PIN N15 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[0]}]
set_property -dict { PACKAGE_PIN M16 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[1]}]
set_property -dict { PACKAGE_PIN R12 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[2]}]
set_property -dict { PACKAGE_PIN N16 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[3]}]
set_property -dict { PACKAGE_PIN R11 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[4]}]
set_property -dict { PACKAGE_PIN G14 IOSTANDARD LVCMOS33 } [get_ports {RGB_tri_o[5]}]
## Konfigurasyon: QSPI'dan acilis icin
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property BITSTREAM.CONFIG.CONFIGRATE 33 [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
}
close $fh
add_files -fileset constrs_1 -norecurse $xdc_path

puts "STEP: synth/impl/bitstream"
launch_runs synth_1 -jobs 8
wait_on_run synth_1
if {[get_property PROGRESS [get_runs synth_1]] ne "100%"} { error "synth failed: [get_property STATUS [get_runs synth_1]]" }
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} { error "impl failed: [get_property STATUS [get_runs impl_1]]" }
set bit $proj_dir/nexys_a7.runs/impl_1/design_1_wrapper.bit
file copy -force $bit $bit_out
file copy -force $proj_dir/nexys_a7.runs/impl_1/design_1_wrapper.mmi $mmi_out
write_hw_platform -fixed -include_bit -force $xsa_bit
puts "BIT-DONE: $bit_out"
puts "XSA-BIT-DONE: $xsa_bit"
exit
