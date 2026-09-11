# Nexys A7-100T (xc7a100tcsg324-1) MicroBlaze + Ethernet referans tasarimi - Spec2Code PL
# Ethernet (lwIP TCP) test bench ajani dogrulamasi.
#
# MB (512KB LMB, Debug Only MDM) + AXI INTC + AXI Timer + AXI UARTLite (USB-UART 115200)
# + AXI IIC (ADT7420 0x4B) + AXI Quad SPI (S25FL128S, STARTUPE2) + AXI EthernetLite
# + MII-to-RMII (LAN8720A PHY, 50 MHz REFCLK FPGA'dan) - pinler Digilent Nexys-A7-100T-Master.xdc.
# Cikti: microblaze_nexys_a7_eth.xsa (bit'siz), microblaze_nexys_a7_eth_bit.xsa, .bit, .mmi.
#
# Kullanim: vivado -mode batch -source scripts/make_nexys_a7_eth_design.tcl
set root_dir   D:/Projects/claude/Spec2Code
set proj_dir   $root_dir/test/0_temp_dbg/vivado_nexys_a7_eth
set out_dir    $root_dir/test/0_dosyalar
set xsa_out    $out_dir/microblaze_nexys_a7_eth.xsa
set xsa_bit    $out_dir/microblaze_nexys_a7_eth_bit.xsa
set bit_out    $out_dir/microblaze_nexys_a7_eth.bit
set mmi_out    $out_dir/microblaze_nexys_a7_eth.mmi
set xdc_path   $proj_dir/nexys_a7_eth.xdc
file delete -force $proj_dir
file mkdir $proj_dir
create_project -force nexys_a7_eth $proj_dir -part xc7a100tcsg324-1
# RMII adaptoru (Xilinx mii_to_rmii 2023.x katalogunda yok): kendi RTL modulumuz.
add_files -norecurse $root_dir/scripts/hdl/rmii_adapter.v
update_compile_order -fileset sources_1

puts "STEP: block design"
create_bd_design "design_1"
create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0
# Clocking Wizard: 100 MHz sistem + 50 MHz Ethernet REFCLK (LAN8720A RMII).
apply_bd_automation -rule xilinx.com:bd_rule:microblaze -config { \
    local_mem {128KB} ecc {None} cache {None} debug_module {Debug Only} \
    axi_periph {Enabled} axi_intc {1} clk {New Clocking Wizard (100 MHz)} } \
    [get_bd_cells microblaze_0]

set clkwiz [get_bd_cells -filter {VLNV =~ "*:clk_wiz:*"}]
# Otomasyon diferansiyel giris (CLK_IN1_D) kurar; Nexys A7 tek uclu 100 MHz: tek uclu pine cevir,
# artik diff portu sil, "Clk" portunu olustur ve bagla. clk_wiz reset'i kullanilmaz (USE_RESET 0).
set_property -dict [list CONFIG.CLKOUT2_USED {true} CONFIG.CLKOUT2_REQUESTED_OUT_FREQ {50.000} \
    CONFIG.PRIM_SOURCE {Single_ended_clock_capable_pin} CONFIG.USE_RESET {false}] $clkwiz
foreach dp [get_bd_intf_ports -quiet -filter {VLNV =~ "*diff_clock*"}] { delete_bd_objs $dp }
create_bd_port -dir I -type clk -freq_hz 100000000 Clk
connect_bd_net [get_bd_ports Clk] [get_bd_pins $clkwiz/clk_in1]

# Reset: Nexys A7 CPU_RESETN AKTIF-DUSUK butondur (otomasyon `reset` portunu kurdu; polarite porttan).
set rst [get_bd_cells -filter {VLNV =~ "*:proc_sys_reset:*"}]
if {[get_bd_ports -quiet reset] eq ""} { make_bd_pins_external -name reset [get_bd_pins $rst/ext_reset_in] }
set_property CONFIG.POLARITY ACTIVE_LOW [get_bd_ports reset]
# clk_wiz'in giris portu otomasyonda "Clk" adiyla disari cikar; degilse adini sabitle.
foreach p [get_bd_ports -filter {DIR == I}] {
    if {[get_property TYPE $p] eq "clk" && [get_property NAME $p] ne "Clk"} { set_property NAME Clk $p }
}

create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite axi_uartlite_0
set_property CONFIG.C_BAUDRATE 115200 [get_bd_cells axi_uartlite_0]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_iic axi_iic_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_quad_spi axi_quad_spi_0
set_property -dict [list CONFIG.C_USE_STARTUP {1} CONFIG.C_USE_STARTUP_INT {1} \
    CONFIG.C_SPI_MODE {0} CONFIG.C_NUM_SS_BITS {1} CONFIG.C_SCK_RATIO {4} \
    CONFIG.C_FIFO_DEPTH {16}] [get_bd_cells axi_quad_spi_0]
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_timer axi_timer_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_ethernetlite axi_ethernetlite_0
set_property -dict [list CONFIG.C_INCLUDE_MDIO {1} CONFIG.C_INCLUDE_INTERNAL_LOOPBACK {0}] [get_bd_cells axi_ethernetlite_0]
create_bd_cell -type module -reference rmii_adapter rmii_adapter_0

foreach slave {axi_uartlite_0/S_AXI axi_iic_0/S_AXI axi_quad_spi_0/AXI_LITE axi_timer_0/S_AXI axi_ethernetlite_0/S_AXI} {
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/microblaze_0 (Periph)} Slave "/$slave" \
        ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}] \
        [get_bd_intf_pins $slave]
}
set spi_aclk_net [get_bd_nets -of_objects [get_bd_pins axi_quad_spi_0/s_axi_aclk]]
connect_bd_net -net $spi_aclk_net [get_bd_pins axi_quad_spi_0/ext_spi_clk]

# Ethernet: EthernetLite MII <-> rmii_adapter <-> LAN8720A; REFCLK 50 MHz FPGA'dan PHY'ye.
connect_bd_net [get_bd_pins $clkwiz/clk_out2] [get_bd_pins rmii_adapter_0/ref_clk]
connect_bd_net [get_bd_pins $rst/peripheral_aresetn] [get_bd_pins rmii_adapter_0/rst_n]
foreach {mac pin} {phy_rx_clk mii_rx_clk phy_rx_data mii_rxd phy_dv mii_rx_dv phy_rx_er mii_rx_er                    phy_tx_clk mii_tx_clk phy_tx_data mii_txd phy_tx_en mii_tx_en phy_crs mii_crs phy_col mii_col} {
    connect_bd_net [get_bd_pins axi_ethernetlite_0/$mac] [get_bd_pins rmii_adapter_0/$pin]
}
foreach {port dir width pin} {eth_rxd I 2 rmii_rxd eth_crs_dv I 1 rmii_crs_dv eth_rx_er I 1 rmii_rx_er                               eth_txd O 2 rmii_txd eth_tx_en O 1 rmii_tx_en} {
    if {$width > 1} { create_bd_port -dir $dir -from [expr {$width - 1}] -to 0 $port } else { create_bd_port -dir $dir $port }
    connect_bd_net [get_bd_ports $port] [get_bd_pins rmii_adapter_0/$pin]
}
make_bd_intf_pins_external [get_bd_intf_pins axi_ethernetlite_0/MDIO]
create_bd_port -dir O -type clk eth_ref_clk
connect_bd_net [get_bd_pins $clkwiz/clk_out2] [get_bd_ports eth_ref_clk]
create_bd_port -dir O -from 0 -to 0 eth_rstn
connect_bd_net [get_bd_pins axi_ethernetlite_0/phy_rst_n] [get_bd_ports eth_rstn]

# Kesmeler: EthernetLite + Timer -> xlconcat -> AXI INTC (otomasyon concat'i kurdu).
set concat [get_bd_cells -filter {VLNV =~ "*:xlconcat:*"}]
set intc   [get_bd_cells -filter {VLNV =~ "*:axi_intc:*"}]
if {$concat eq ""} {
    create_bd_cell -type ip -vlnv xilinx.com:ip:xlconcat microblaze_0_xlconcat
    set concat [get_bd_cells microblaze_0_xlconcat]
    connect_bd_net [get_bd_pins $concat/dout] [get_bd_pins $intc/intr]
}
set_property CONFIG.NUM_PORTS 2 $concat
connect_bd_net [get_bd_pins axi_ethernetlite_0/ip2intc_irpt] [get_bd_pins $concat/In0]
connect_bd_net [get_bd_pins axi_timer_0/interrupt] [get_bd_pins $concat/In1]

make_bd_intf_pins_external [get_bd_intf_pins axi_uartlite_0/UART]
make_bd_intf_pins_external [get_bd_intf_pins axi_iic_0/IIC]
make_bd_intf_pins_external [get_bd_intf_pins axi_quad_spi_0/SPI_0]
set_property NAME UART     [get_bd_intf_ports UART_0]
set_property NAME IIC      [get_bd_intf_ports IIC_0]
set_property NAME SPI_0    [get_bd_intf_ports SPI_0_0]
set_property NAME eth_mdio [get_bd_intf_ports MDIO_0]

assign_bd_address
# LMB 512K: lwIP + ajan + BSP (Artix-100T BRAM'inin ~%84'u).
set_property range 512K [get_bd_addr_segs {microblaze_0/Data/SEG_dlmb_bram_if_cntlr_Mem}]
set_property range 512K [get_bd_addr_segs {microblaze_0/Instruction/SEG_ilmb_bram_if_cntlr_Mem}]
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
## Nexys A7-100T - Spec2Code MicroBlaze + Ethernet referans tasarimi (Digilent master XDC'den)
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
## SMSC LAN8720A Ethernet PHY (RMII)
set_property -dict { PACKAGE_PIN C9  IOSTANDARD LVCMOS33 } [get_ports eth_mdio_mdc]
set_property -dict { PACKAGE_PIN A9  IOSTANDARD LVCMOS33 } [get_ports eth_mdio_mdio_io]
set_property -dict { PACKAGE_PIN B3  IOSTANDARD LVCMOS33 } [get_ports {eth_rstn[0]}]
set_property -dict { PACKAGE_PIN D9  IOSTANDARD LVCMOS33 } [get_ports eth_crs_dv]
set_property -dict { PACKAGE_PIN C10 IOSTANDARD LVCMOS33 } [get_ports eth_rx_er]
set_property -dict { PACKAGE_PIN C11 IOSTANDARD LVCMOS33 } [get_ports {eth_rxd[0]}]
set_property -dict { PACKAGE_PIN D10 IOSTANDARD LVCMOS33 } [get_ports {eth_rxd[1]}]
set_property -dict { PACKAGE_PIN B9  IOSTANDARD LVCMOS33 } [get_ports eth_tx_en]
set_property -dict { PACKAGE_PIN A10 IOSTANDARD LVCMOS33 } [get_ports {eth_txd[0]}]
set_property -dict { PACKAGE_PIN A8  IOSTANDARD LVCMOS33 } [get_ports {eth_txd[1]}]
set_property -dict { PACKAGE_PIN D5  IOSTANDARD LVCMOS33 } [get_ports eth_ref_clk]
## MII 25 MHz saati: rmii_adapter icindeki ref_clk/2 bolucusu (BUFG)
## Vivado register hucre adina _reg ekler: clk25_reg -> clk25_reg_reg (aksi halde 'No valid object', 25 MHz alani kisitsiz kalir).
create_generated_clock -name mii_clk25 -source [get_pins -hier -filter {NAME =~ *rmii_adapter_0*clk25_reg_reg/C}] -divide_by 2 [get_pins -hier -filter {NAME =~ *rmii_adapter_0*clk25_reg_reg/Q}]
## RMII giris/cikislari ref_clk'e gore (PHY REFCLK ayni kaynak): kaba I/O kisitlari
set_input_delay -clock [get_clocks -of_objects [get_pins -hier -filter {NAME =~ *clk_wiz*/clk_out2}]] -max 12.0 [get_ports {eth_rxd[*] eth_crs_dv eth_rx_er}]
set_input_delay -clock [get_clocks -of_objects [get_pins -hier -filter {NAME =~ *clk_wiz*/clk_out2}]] -min 2.0 [get_ports {eth_rxd[*] eth_crs_dv eth_rx_er}]
## TX cikislari ref_clk DUSEN kenarinda surulur (rmii_adapter): PHY yukselen kenarda ornekler.
set_output_delay -clock [get_clocks -of_objects [get_pins -hier -filter {NAME =~ *clk_wiz*/clk_out2}]] -max 4.0 [get_ports {eth_txd[*] eth_tx_en}]
set_output_delay -clock [get_clocks -of_objects [get_pins -hier -filter {NAME =~ *clk_wiz*/clk_out2}]] -min -1.0 [get_ports {eth_txd[*] eth_tx_en}]
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
set bit $proj_dir/nexys_a7_eth.runs/impl_1/design_1_wrapper.bit
file copy -force $bit $bit_out
file copy -force $proj_dir/nexys_a7_eth.runs/impl_1/design_1_wrapper.mmi $mmi_out
write_hw_platform -fixed -include_bit -force $xsa_bit
puts "BIT-DONE: $bit_out"
puts "XSA-BIT-DONE: $xsa_bit"
exit
