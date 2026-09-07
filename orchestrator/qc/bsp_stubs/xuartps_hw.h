/* Minimal Xilinx PS UART low-level stub (xuartps_hw.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTPS_HW_H
#define XUARTPS_HW_H
#include "xil_types.h"

u32 XUartPs_IsReceiveData(UINTPTR BaseAddress);
u32 XUartPs_IsTransmitFull(UINTPTR BaseAddress);
void XUartPs_SendByte(UINTPTR BaseAddress, u8 Data);
u8 XUartPs_RecvByte(UINTPTR BaseAddress);

#endif /* XUARTPS_HW_H */
