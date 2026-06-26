/******************************************************************************
* Sample xparameters.h  —  MicroBlaze (7-series)  (Spec2Code demo fixture)
* All peripherals are soft AXI IP in the PL.
******************************************************************************/
#ifndef XPARAMETERS_H
#define XPARAMETERS_H

/* AXI IIC 0 (bus for LTC2991 + TCA9548A mux) */
#define XPAR_AXI_IIC_0_DEVICE_ID 0
#define XPAR_AXI_IIC_0_BASEADDR 0x40800000U
#define XPAR_AXI_IIC_0_HIGHADDR 0x4080FFFFU

/* AXI Quad SPI 0 (MT25Q128 flash lives here) */
#define XPAR_AXI_QUAD_SPI_0_DEVICE_ID 0
#define XPAR_AXI_QUAD_SPI_0_BASEADDR 0x44A00000U
#define XPAR_AXI_QUAD_SPI_0_HIGHADDR 0x44A0FFFFU

/* AXI GPIO 0 */
#define XPAR_AXI_GPIO_0_DEVICE_ID 0
#define XPAR_AXI_GPIO_0_BASEADDR 0x40000000U
#define XPAR_AXI_GPIO_0_HIGHADDR 0x4000FFFFU

/* AXI UARTLITE 0 */
#define XPAR_AXI_UARTLITE_0_DEVICE_ID 0
#define XPAR_AXI_UARTLITE_0_BASEADDR 0x40600000U
#define XPAR_AXI_UARTLITE_0_HIGHADDR 0x4060FFFFU

/* AXI DMA 0 */
#define XPAR_AXI_DMA_0_DEVICE_ID 0
#define XPAR_AXI_DMA_0_BASEADDR 0x41E00000U
#define XPAR_AXI_DMA_0_HIGHADDR 0x41E0FFFFU

/* MIG DDR controller memory region -> filtered (no DEVICE_ID) */
#define XPAR_MIG_7SERIES_0_BASEADDR 0x80000000U
#define XPAR_MIG_7SERIES_0_HIGHADDR 0xBFFFFFFFU

#endif /* XPARAMETERS_H */
