# Kria KV260 (K26 SOM, xck26-sfvc784-2LV-c) + JESD204C v4.2 RX ve TX cekirdekleri, PL ici TX->RX loopback.
#
# Amac: JESD204C register haritasini ve link kurulum dizisini (SYSREF, SOEMB, block sync, STAT_STATUS)
# GT/PHY olmadan gercek kartta sinamak. TX cekirdeginin 64B/66B GT cikislari (txdata/txheader)
# dogrudan RX cekirdeginin GT girislerine baglanir; block_sync=1, reset_done=1, 8B/10B girisleri 0.
# SYSREF her iki cekirdege AXI GPIO (bit0) ile yazilimdan surulur (alt sinif 1 testi).
# Bitstream uretilir (JESD204 Hardware Evaluation lisansi gerekir: XILINXD_LICENSE_FILE).
#
# Kullanim: vivado -mode batch -source scripts/make_kv260_jesd204c_xsa.tcl [-tclargs nobit]
set root_dir D:/Projects/claude/Spec2Code
set proj_dir $root_dir/test/0_temp_dbg/vivado_kv260_jesd
set xsa_out  $root_dir/test/0_dosyalar/kv260_jesd204c.xsa
set with_bit 1
if {[llength $argv] > 0 && [lindex $argv 0] eq "nobit"} { set with_bit 0 }
file delete -force $proj_dir
create_project -force kv260_jesd $proj_dir -part xck26-sfvc784-2LV-c
set_property board_part xilinx.com:k26c:part0:1.4 [current_project]
set_property board_connections {som240_1_connector xilinx.com:kv260_carrier:som240_1_connector:1.3} [current_project]
create_bd_design "design_1"
puts "STEP: PS"
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} $ps
set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 {1} CONFIG.PSU__USE__M_AXI_GP1 {0} CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

puts "STEP: JESD204C RX/TX + GPIO"
set rx [create_bd_cell -type ip -vlnv xilinx.com:ip:jesd204c:4.2 jesd204c_rx]
set_property -dict [list CONFIG.C_LANES {4} CONFIG.C_NODE_IS_TRANSMIT {0} CONFIG.C_ENCODING {1}] $rx
set tx [create_bd_cell -type ip -vlnv xilinx.com:ip:jesd204c:4.2 jesd204c_tx]
set_property -dict [list CONFIG.C_LANES {4} CONFIG.C_NODE_IS_TRANSMIT {1} CONFIG.C_ENCODING {1}] $tx
set gpio [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio axi_gpio_sysref]
set_property -dict [list CONFIG.C_GPIO_WIDTH {1} CONFIG.C_ALL_OUTPUTS {1} CONFIG.C_DOUT_DEFAULT {0x00000000}] $gpio
foreach cell [list $rx $tx $gpio] {
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/zynq_ultra_ps_e_0/M_AXI_HPM0_FPD} Slave "[get_property NAME $cell]/[expr {$cell eq $gpio ? "S_AXI" : "s_axi"}]" \
        ddr_seg {Auto} intc_ip {New AXI SmartConnect} master_apm {0}] \
        [get_bd_intf_pins $cell/[expr {$cell eq $gpio ? "S_AXI" : "s_axi"}]]
}

puts "STEP: loopback"
set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
# GT veri yolu: TX -> RX (64B/66B: data + 2-bit header)
for {set i 0} {$i < 4} {incr i} {
    connect_bd_net [get_bd_pins $tx/gt${i}_txdata]   [get_bd_pins $rx/gt${i}_rxdata]
    connect_bd_net [get_bd_pins $tx/gt${i}_txheader] [get_bd_pins $rx/gt${i}_rxheader]
}
# SYSREF: GPIO bit0 -> her iki cekirdek
connect_bd_net [get_bd_pins $gpio/gpio_io_o] [get_bd_pins $tx/tx_sysref]
connect_bd_net [get_bd_pins $gpio/gpio_io_o] [get_bd_pins $rx/rx_sysref]
# Cekirdek saatleri: pl_clk0 (hat hizi onemsiz, PHY yok)
connect_bd_net $pl_clk [get_bd_pins $tx/tx_core_clk]
connect_bd_net $pl_clk [get_bd_pins $rx/rx_core_clk]
# Cekirdek reset (aktif yuksek): PS reset bloguna bagli
set psr [get_bd_cells -filter {VLNV =~ xilinx.com:ip:proc_sys_reset:*}]
set psr [lindex $psr 0]
connect_bd_net [get_bd_pins $psr/peripheral_reset] [get_bd_pins $tx/tx_core_reset]
connect_bd_net [get_bd_pins $psr/peripheral_reset] [get_bd_pins $rx/rx_core_reset]
# Sabit 1'ler: GT reset done, RX block sync (gearbox yok, veri zaten hizali), rx_cmd_tready
set one [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant xlconstant_one]
set_property -dict [list CONFIG.CONST_WIDTH 1 CONFIG.CONST_VAL 1] $one
foreach pin [list $tx/tx_reset_done $rx/rx_reset_done $rx/rx_cmd_tready \
                  $rx/gt0_rxblock_sync $rx/gt1_rxblock_sync $rx/gt2_rxblock_sync $rx/gt3_rxblock_sync] {
    connect_bd_net [get_bd_pins $one/dout] [get_bd_pins $pin]
}
# TX kullanici verisi: sabit desen (256 bit); alici tarafta rx_tdata dogrulanabilir (ILA yok, register testi yeterli)
set pat [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant xlconstant_txpat]
set_property -dict [list CONFIG.CONST_WIDTH 256 CONFIG.CONST_VAL {0xA5A5A5A55A5A5A5A0F0F0F0FF0F0F0F0123456789ABCDEF0CAFEBABEDEADBEEF}] $pat
connect_bd_net [get_bd_pins $pat/dout] [get_bd_pins $tx/tx_tdata]
# Kalan girisler sabit 0 (8B/10B durum girisleri, misalign, cmd akisi)
set const_idx 0
foreach cell [list $rx $tx] {
    foreach pin [get_bd_pins -of_objects $cell -filter {DIR == I}] {
        if {[get_bd_nets -quiet -of_objects $pin] ne ""} { continue }
        if {[get_property TYPE $pin] eq "clk"} { connect_bd_net $pl_clk $pin; continue }
        set left [get_property LEFT $pin]
        set width [expr {$left eq "" ? 1 : $left + 1}]
        set c [create_bd_cell -type ip -vlnv xilinx.com:ip:xlconstant xlconstant_$const_idx]
        set_property -dict [list CONFIG.CONST_WIDTH $width CONFIG.CONST_VAL {0}] $c
        connect_bd_net [get_bd_pins $c/dout] $pin
        incr const_idx
    }
}
assign_bd_address
validate_bd_design
save_bd_design
foreach seg [get_bd_addr_segs -of_objects [get_bd_addr_spaces zynq_ultra_ps_e_0/Data]] {
    puts "SEG [get_property NAME $seg] [get_property OFFSET $seg] [get_property RANGE $seg]"
}
puts "STEP: wrapper"
set wrapper [make_wrapper -files [get_files design_1.bd] -top]
add_files -norecurse $wrapper
set_property top design_1_wrapper [current_fileset]
update_compile_order -fileset sources_1
generate_target all [get_files design_1.bd]
if {$with_bit} {
    puts "STEP: synth + impl + bitstream"
    launch_runs impl_1 -to_step write_bitstream -jobs 8
    wait_on_run impl_1
    if {[get_property PROGRESS [get_runs impl_1]] ne "100%"} { error "impl_1 tamamlanmadi: [get_property STATUS [get_runs impl_1]]" }
    puts "BIT: [get_property DIRECTORY [get_runs impl_1]]/design_1_wrapper.bit"
    write_hw_platform -fixed -include_bit -force $xsa_out
} else {
    write_hw_platform -fixed -force $xsa_out
}
puts "XSA-DONE: $xsa_out"
exit
