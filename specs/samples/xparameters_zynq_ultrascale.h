/******************************************************************************
* Sample xparameters.h  —  Zynq UltraScale+ MPSoC  (Spec2Code demo fixture)
* Hand-crafted to resemble Vivado/Vitis BSP output. Exercises the parser:
*   - PS hardened peripherals (I2C/SPI/QSPI/GPIO/UART)  -> controllers (PS zone)
*   - one PL soft AXI GPIO                              -> controller (PL zone)
*   - DDR/OCM memory regions (no DEVICE_ID)             -> filtered out
*   - TTC / SCUGIC (have DEVICE_ID but non-attachable)  -> ignored
******************************************************************************/
#ifndef XPARAMETERS_H
#define XPARAMETERS_H

/* Definitions for peripheral PSU_I2C_0 (bus for LTC2991 + TCA9548A mux) */
#define XPAR_XIICPS_0_DEVICE_ID 0
#define XPAR_XIICPS_0_BASEADDR 0xFF020000U
#define XPAR_XIICPS_0_HIGHADDR 0xFF02FFFFU
#define XPAR_XIICPS_0_I2C_CLK_FREQ_HZ 99999001

/* Definitions for peripheral PSU_I2C_1 */
#define XPAR_XIICPS_1_DEVICE_ID 1
#define XPAR_XIICPS_1_BASEADDR 0xFF030000U
#define XPAR_XIICPS_1_HIGHADDR 0xFF03FFFFU

/* Definitions for peripheral PSU_QSPI_0 (MT25QU02G flash lives here) */
#define XPAR_XQSPIPS_0_DEVICE_ID 0
#define XPAR_XQSPIPS_0_BASEADDR 0xFF0F0000U
#define XPAR_XQSPIPS_0_HIGHADDR 0xFF0FFFFFU

/* Definitions for peripheral PSU_SPI_0 */
#define XPAR_XSPIPS_0_DEVICE_ID 0
#define XPAR_XSPIPS_0_BASEADDR 0xFF040000U
#define XPAR_XSPIPS_0_HIGHADDR 0xFF04FFFFU

/* Definitions for peripheral PSU_GPIO_0 */
#define XPAR_XGPIOPS_0_DEVICE_ID 0
#define XPAR_XGPIOPS_0_BASEADDR 0xFF0A0000U
#define XPAR_XGPIOPS_0_HIGHADDR 0xFF0AFFFFU

/* Definitions for peripheral PSU_UART_0 */
#define XPAR_XUARTPS_0_DEVICE_ID 0
#define XPAR_XUARTPS_0_BASEADDR 0xFF000000U
#define XPAR_XUARTPS_0_HIGHADDR 0xFF00FFFFU

/* Definitions for peripheral AXI_GPIO_0 (soft IP in PL) */
#define XPAR_AXI_GPIO_0_DEVICE_ID 2
#define XPAR_AXI_GPIO_0_BASEADDR 0xA0000000U
#define XPAR_AXI_GPIO_0_HIGHADDR 0xA000FFFFU

/* --- non-controller noise the parser must handle --- */

/* DDR memory region: has BASEADDR but NO DEVICE_ID -> filtered */
#define XPAR_PSU_DDR_0_BASEADDR 0x00000000U
#define XPAR_PSU_DDR_0_HIGHADDR 0x7FFFFFFFU

/* OCM memory region -> filtered */
#define XPAR_PSU_OCM_RAM_0_BASEADDR 0xFFFC0000U
#define XPAR_PSU_OCM_RAM_0_HIGHADDR 0xFFFFFFFFU

/* Triple-timer counter: has DEVICE_ID but is non-attachable -> ignored */
#define XPAR_XTTCPS_0_DEVICE_ID 0
#define XPAR_XTTCPS_0_BASEADDR 0xFF110000U

/* Interrupt controller -> ignored */
#define XPAR_SCUGIC_0_DEVICE_ID 0
#define XPAR_SCUGIC_0_BASEADDR 0xF9020000U

#endif /* XPARAMETERS_H */
