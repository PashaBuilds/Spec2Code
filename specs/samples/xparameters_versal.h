/******************************************************************************
* Sample xparameters.h  —  Versal ACAP  (Spec2Code demo fixture)
******************************************************************************/
#ifndef XPARAMETERS_H
#define XPARAMETERS_H

/* PMC/LPD I2C 0 (bus for LTC2991 + TCA9548A mux) */
#define XPAR_XIICPS_0_DEVICE_ID 0
#define XPAR_XIICPS_0_BASEADDR 0xFF020000U
#define XPAR_XIICPS_0_HIGHADDR 0xFF02FFFFU

/* OSPI/QSPI 0 (MT25QU02G flash lives here) */
#define XPAR_XQSPIPS_0_DEVICE_ID 0
#define XPAR_XQSPIPS_0_BASEADDR 0xF1030000U
#define XPAR_XQSPIPS_0_HIGHADDR 0xF103FFFFU

/* LPD SPI 0 */
#define XPAR_XSPIPS_0_DEVICE_ID 0
#define XPAR_XSPIPS_0_BASEADDR 0xFF040000U
#define XPAR_XSPIPS_0_HIGHADDR 0xFF04FFFFU

/* LPD GPIO 0 */
#define XPAR_XGPIOPS_0_DEVICE_ID 0
#define XPAR_XGPIOPS_0_BASEADDR 0xFF0B0000U
#define XPAR_XGPIOPS_0_HIGHADDR 0xFF0BFFFFU

/* PMC UART 0 */
#define XPAR_XUARTPS_0_DEVICE_ID 0
#define XPAR_XUARTPS_0_BASEADDR 0xFF000000U
#define XPAR_XUARTPS_0_HIGHADDR 0xFF00FFFFU

/* AXI IIC 0 (soft IP in PL, e.g. for a second sensor bus) */
#define XPAR_AXI_IIC_0_DEVICE_ID 1
#define XPAR_AXI_IIC_0_BASEADDR 0xA0010000U
#define XPAR_AXI_IIC_0_HIGHADDR 0xA001FFFFU

/* DDR memory region -> filtered (no DEVICE_ID) */
#define XPAR_PSV_DDR_0_BASEADDR 0x00000000U
#define XPAR_PSV_DDR_0_HIGHADDR 0x7FFFFFFFU

#endif /* XPARAMETERS_H */
