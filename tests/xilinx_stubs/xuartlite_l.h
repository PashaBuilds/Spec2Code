/* Host stub: AXI UARTLite dusuk seviye API (xuartlite_l.h). Konsol girdisi test tarafindan
 * g_ucArrStubUartIn/g_uiStubUartInLen ile beslenir; cikti stdout'a gider. */
#ifndef XUARTLITE_L_H
#define XUARTLITE_L_H
#include "xil_types.h"
u32 XUartLite_IsReceiveEmpty(UINTPTR BaseAddress);
u8 XUartLite_RecvByte(UINTPTR BaseAddress);
void XUartLite_SendByte(UINTPTR BaseAddress, u8 Data);
#endif
