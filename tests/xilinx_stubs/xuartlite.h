/* Host stub: AXI UARTLite (xuartlite.h) - asgari tip/imza. */
#ifndef XUARTLITE_H
#define XUARTLITE_H
#include "xil_types.h"
#include "xuartlite_l.h"
typedef struct { u16 DeviceId; UINTPTR RegBaseAddr; u32 BaudRate; } XUartLite_Config;
typedef struct { UINTPTR RegBaseAddress; u32 IsReady; } XUartLite;
int XUartLite_Initialize(XUartLite* InstancePtr, u16 DeviceId);
unsigned int XUartLite_Send(XUartLite* InstancePtr, u8* DataBufferPtr, unsigned int NumBytes);
unsigned int XUartLite_Recv(XUartLite* InstancePtr, u8* DataBufferPtr, unsigned int NumBytes);
#endif
