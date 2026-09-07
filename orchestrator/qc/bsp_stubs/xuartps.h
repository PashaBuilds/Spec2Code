/* Minimal Xilinx PS UART stub (xuartps.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTPS_H
#define XUARTPS_H
#include "xil_types.h"
#include "xuartps_hw.h"

typedef struct
{
    u16 DeviceId;
    UINTPTR BaseAddress;
    u32 InputClockHz;
    s32 ModemPinsConnected;
} XUartPs_Config;

typedef struct
{
    XUartPs_Config Config;
    u32 InputClockHz;
    u32 IsReady;
    u32 BaudRate;
} XUartPs;

XUartPs_Config* XUartPs_LookupConfig(u16 DeviceId);
int XUartPs_CfgInitialize(XUartPs* InstancePtr, XUartPs_Config* Config, UINTPTR EffectiveAddr);
int XUartPs_SetBaudRate(XUartPs* InstancePtr, u32 BaudRate);
u32 XUartPs_Send(XUartPs* InstancePtr, u8* BufferPtr, u32 NumBytes);
u32 XUartPs_Recv(XUartPs* InstancePtr, u8* BufferPtr, u32 NumBytes);

#endif /* XUARTPS_H */
