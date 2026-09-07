/* Minimal Xilinx AXI UARTLite low-level stub (xuartlite_l.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTLITE_L_H
#define XUARTLITE_L_H
#include "xil_types.h"

u32 XUartLite_IsReceiveEmpty(UINTPTR BaseAddress);
u32 XUartLite_IsTransmitFull(UINTPTR BaseAddress);
void XUartLite_SendByte(UINTPTR BaseAddress, u8 Data);
u8 XUartLite_RecvByte(UINTPTR BaseAddress);

#endif /* XUARTLITE_L_H */
