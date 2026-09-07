/* Minimal Xilinx AXI UARTLite stub (xuartlite.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTLITE_H
#define XUARTLITE_H
#include "xil_types.h"
#include "xuartlite_l.h"

typedef struct
{
    u16 DeviceId;
    UINTPTR RegBaseAddr;
    u32 BaudRate;
    u8 UseParity;
    u8 ParityOdd;
    u8 DataBits;
} XUartLite_Config;

typedef struct
{
    UINTPTR RegBaseAddress;
    u32 IsReady;
} XUartLite;

XUartLite_Config* XUartLite_LookupConfig(u16 DeviceId);
int XUartLite_CfgInitialize(XUartLite* InstancePtr, XUartLite_Config* Config, UINTPTR EffectiveAddr);
int XUartLite_Initialize(XUartLite* InstancePtr, u16 DeviceId);
unsigned int XUartLite_Send(XUartLite* InstancePtr, u8* DataBufferPtr, unsigned int NumBytes);
unsigned int XUartLite_Recv(XUartLite* InstancePtr, u8* DataBufferPtr, unsigned int NumBytes);
void XUartLite_ResetFifos(XUartLite* InstancePtr);

#endif /* XUARTLITE_H */
