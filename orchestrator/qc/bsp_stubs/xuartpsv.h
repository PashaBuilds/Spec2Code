/* Minimal Xilinx Versal PS UART stub (xuartpsv.h) for Spec2Code QC (syntax/type check only). */
#ifndef XUARTPSV_H
#define XUARTPSV_H
#include "xil_types.h"
#include "xuartpsv_hw.h"

typedef struct
{
    u16 DeviceId;
    UINTPTR BaseAddress;
    u32 InputClockHz;
    s32 ModemPinsConnected;
} XUartPsv_Config;

typedef struct
{
    XUartPsv_Config Config;
    u32 InputClockHz;
    u32 IsReady;
    u32 BaudRate;
} XUartPsv;

XUartPsv_Config* XUartPsv_LookupConfig(u16 DeviceId);
int XUartPsv_CfgInitialize(XUartPsv* InstancePtr, XUartPsv_Config* Config, UINTPTR EffectiveAddr);
int XUartPsv_SetBaudRate(XUartPsv* InstancePtr, u32 BaudRate);
u32 XUartPsv_Send(XUartPsv* InstancePtr, u8* BufferPtr, u32 NumBytes);
u32 XUartPsv_Recv(XUartPsv* InstancePtr, u8* BufferPtr, u32 NumBytes);

#endif /* XUARTPSV_H */
