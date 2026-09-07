/* Minimal Xilinx Versal PS UART low-level stub (xuartpsv_hw.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTPSV_HW_H
#define XUARTPSV_HW_H
#include "xil_types.h"

u32 XUartPsv_IsReceiveData(UINTPTR BaseAddress);
u32 XUartPsv_IsTransmitFull(UINTPTR BaseAddress);
void XUartPsv_SendByte(UINTPTR BaseAddress, u8 Data);
u8 XUartPsv_RecvByte(UINTPTR BaseAddress);

#endif /* XUARTPSV_HW_H */
