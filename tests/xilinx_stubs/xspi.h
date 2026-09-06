/* Host stub: AXI SPI (xspi.h) - gercek imzalarla. */
#ifndef XSPI_H
#define XSPI_H
#include "xil_types.h"
#define XSP_MASTER_OPTION 0x1U
#define XSP_MANUAL_SSELECT_OPTION 0x4U
typedef struct { u16 DeviceId; UINTPTR BaseAddress; } XSpi_Config;
typedef struct { u32 IsReady; UINTPTR BaseAddr; u32 SlaveSelectReg; } XSpi;
XSpi_Config* XSpi_LookupConfig(u16 DeviceId);
int XSpi_CfgInitialize(XSpi* InstancePtr, XSpi_Config* Config, UINTPTR EffectiveAddr);
int XSpi_SetOptions(XSpi* InstancePtr, u32 Options);
int XSpi_Start(XSpi* InstancePtr);
void XSpi_IntrGlobalDisable(XSpi* InstancePtr);
int XSpi_SetSlaveSelect(XSpi* InstancePtr, u32 SlaveMask);
int XSpi_Transfer(XSpi* InstancePtr, u8* SendBufPtr, u8* RecvBufPtr, unsigned int ByteCount);
#endif
