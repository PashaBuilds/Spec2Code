# Nexys A7-100T (xc7a100tcsg324-1) MicroBlaze referans tasarimi - Spec2Code kart dogrulamasi.
#
# MB (256KB LMB, MDM debug) + AXI UARTLite (USB-UART, 115200) + AXI IIC (kart ustu ADT7420,
# adres 0x4B) + AXI Quad SPI (konfigurasyon flash'i S25FL128S; SCK STARTUPE2 uzerinden,
# C_USE_STARTUP=1) - pin kisitlari Digilent Nexys-A7-100T-Master.xdc'den.
# Cikti: microblaze_nexys_a7.xsa (bit'siz), microblaze_nexys_a7_bit.xsa (bit'li), .bit, .mmi.
#
# Kullanim: vivado -mode batch -source scripts/make_nexys_a7_design.tcl
set root_dir   D:/Projects/claude/Spec2Code
set proj_dir   $root_dir/test/0_temp_dbg/vivado_nexys_a7
set out_dir    $root_dir/test/0_dosyalar
set xsa_out    $out_dir/microblaze_nexys_a7.xsa
set xsa_bit    $out_dir/microblaze_nexys_a7_bit.xsa
set bit_out    $out_dir/microblaze_nexys_a7.bit
set mmi_out    $out_dir/microblaze_nexys_a7.mmi
set xdc_path   $proj_dir/nexys_a7.xdc
file delete -force $proj_dir
file mkdir $proj_dir

create_project -force nexys_a7 $proj_dir -part xc7a100tcsg324-1

puts "STEP: block design"
create_bd_design "design_1"
create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0
apply_bd_automation -rule xilinx.com:bd_rule:microblaze -config { \
    local_mem {128KB} ecc {None} cache {None} debug_module {Debug Only} \
    axi_periph {Enabled} axi_intc {0} clk {New External Port (100 MHz)} } \
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
