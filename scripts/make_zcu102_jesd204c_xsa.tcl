# ZCU102 (xczu9eg) + JESD204C v4.2 RX ve TX cekirdekleri - Spec2Code bilinen IP haritasi dogrulamasi.
#
# Amac: gercek hwh PARAMETER adlariyla (C_LANES, C_NODE_IS_TRANSMIT, C_ENCODING ...) XSA uretmek;
# XSA ayristirici -> custom_ips[].register_map=jesd204c -> drivers/ip + shell ip_<id> + Register Map.
# GT/PHY tarafi bagli DEGILDIR (link kurulmaz): GT arayuz cikislari bos, girisler sabit 0, saatler PS pl_clk0.
# Bitstream uretilmez (lisans/GT gerekmez); write_hw_platform bit'siz XSA verir.
#
# Kullanim: vivado -mode batch -source scripts/make_zcu102_jesd204c_xsa.tcl
set root_dir D:/Projects/claude/Spec2Code
set proj_dir $root_dir/test/0_temp_dbg/vivado_zcu102_jesd
set xsa_out  $root_dir/test/0_dosyalar/zcu102_jesd204c.xsa
file delete -force $proj_dir
create_project -force zcu102_jesd $proj_dir -part xczu9eg-ffvb1156-2-e
set_property board_part xilinx.com:zcu102:part0:3.4 [current_project]
create_bd_design "design_1"
puts "STEP: PS"
set ps [create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e zynq_ultra_ps_e_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} $ps
set_property -dict [list CONFIG.PSU__USE__M_AXI_GP0 {1} CONFIG.PSU__USE__M_AXI_GP1 {0} CONFIG.PSU__USE__M_AXI_GP2 {0} \
    CONFIG.PSU__FPGA_PL0_ENABLE {1} CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100}] $ps

puts "STEP: JESD204C RX/TX"
# RX: 4 lane, 64B/66B (C_ENCODING 1), alt sinif register'dan (CTRL_SUB_CLASS); TX: 4 lane.
set rx [create_bd_cell -type ip -vlnv xilinx.com:ip:jesd204c:4.2 jesd204c_rx]
set_property -dict [list CONFIG.C_LANES {4} CONFIG.C_NODE_IS_TRANSMIT {0} CONFIG.C_ENCODING {1}] $rx
set tx [create_bd_cell -type ip -vlnv xilinx.com:ip:jesd204c:4.2 jesd204c_tx]
set_property -dict [list CONFIG.C_LANES {4} CONFIG.C_NODE_IS_TRANSMIT {1} CONFIG.C_ENCODING {1}] $tx
foreach cell [list $rx $tx] {
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/zynq_ultra_ps_e_0/M_AXI_HPM0_FPD} Slave "[get_property NAME $cell]/s_axi" \
        ddr_seg {Auto} intc_ip {New AXI SmartConnect} master_apm {0}] \
        [get_bd_intf_pins $cell/s_axi]
}
# Kalan girisler: saatler pl_clk0'a, diger her giris sabit 0 (GT/PHY yok, link kurulmayacak).
set pl_clk [get_bd_pins zynq_ultra_ps_e_0/pl_clk0]
set const_idx 0
foreach cell [list $rx $tx] {
    foreach pin [get_bd_pins -of_objects $cell -filter {DIR == I}] {
        if {[get_bd_nets -quiet -of_objects $pin] ne ""} { continue }
        if {[get_property TYPE $pin] eq "clk"} {
            connect_bd_net $pl_clk $pin
            continue
        }
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
puts "STEP: wrapper + XSA"
set wrapper [make_wrapper -files [get_files design_1.bd] -top]
add_files -norecurse $wrapper
set_property top design_1_wrapper [current_fileset]
update_compile_order -fileset sources_1
generate_target all [get_files design_1.bd]
write_hw_platform -fixed -force $xsa_out
puts "XSA-DONE: $xsa_out"
exit
