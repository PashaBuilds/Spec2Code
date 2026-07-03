# Minimal MicroBlaze design for Spec2Code platform validation:
# MB + 128KB local BRAM + MDM + AXI UARTLITE + AXI IIC + AXI Quad SPI.
# Exported without synthesis (same pattern as make_custom_ip_xsa.tcl).
set proj_dir D:/Projects/claude/Spec2Code/test/0_temp_dbg/vivado_mb
set xsa_out D:/Projects/claude/Spec2Code/test/0_dosyalar/microblaze_ax7a100.xsa
file delete -force $proj_dir

create_project -force mb_proj $proj_dir -part xc7a100tcsg324-1

puts "STEP: creating block design"
create_bd_design "design_1"
create_bd_cell -type ip -vlnv xilinx.com:ip:microblaze microblaze_0
apply_bd_automation -rule xilinx.com:bd_rule:microblaze -config { \
    local_mem {128KB} ecc {None} cache {None} debug_module {Debug Only} \
    axi_periph {Enabled} axi_intc {0} clk {New External Port (100 MHz)} } \
    [get_bd_cells microblaze_0]

create_bd_cell -type ip -vlnv xilinx.com:ip:axi_uartlite axi_uartlite_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_iic axi_iic_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_quad_spi axi_quad_spi_0

foreach slave {axi_uartlite_0/S_AXI axi_iic_0/S_AXI axi_quad_spi_0/AXI_LITE} {
    apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config [list \
        Clk_master {Auto} Clk_slave {Auto} Clk_xbar {Auto} \
        Master {/microblaze_0 (Periph)} Slave "/$slave" \
        ddr_seg {Auto} intc_ip {New AXI Interconnect} master_apm {0}] \
        [get_bd_intf_pins $slave]
}

# Quad SPI's ext_spi_clk needs a clock; reuse the net that feeds the SPI AXI
# clock (BSP-only design, timing is irrelevant without synthesis). Keep the
# net as an object reference on a single line - stringifying it (expr) or a
# continuation-split call makes connect_bd_net see a lone argument.
set spi_aclk_net [get_bd_nets -of_objects [get_bd_pins axi_quad_spi_0/s_axi_aclk]]
set spi_ext_clk_pin [get_bd_pins axi_quad_spi_0/ext_spi_clk]
puts "DIAG net='$spi_aclk_net' pin='$spi_ext_clk_pin'"
connect_bd_net -net $spi_aclk_net $spi_ext_clk_pin

make_bd_intf_pins_external [get_bd_intf_pins axi_uartlite_0/UART]
make_bd_intf_pins_external [get_bd_intf_pins axi_iic_0/IIC]
make_bd_intf_pins_external [get_bd_intf_pins axi_quad_spi_0/SPI_0]

assign_bd_address
validate_bd_design
save_bd_design

puts "STEP: generating targets and exporting XSA"
set_property synth_checkpoint_mode None [get_files design_1.bd]
generate_target all [get_files design_1.bd]
make_wrapper -files [get_files design_1.bd] -top -import
write_hw_platform -fixed -force $xsa_out
puts "XSA-DONE: $xsa_out"
exit
