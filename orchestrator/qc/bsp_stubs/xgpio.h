/* Minimal Xilinx AXI GPIO stub (xgpio.h) for Spec2Code QC (syntax/type check only). */
#ifndef XGPIO_H
#define XGPIO_H
#include "xil_types.h"

typedef struct
{
    u16 DeviceId;
    UINTPTR BaseAddress;
    int InterruptPresent;
    int IsDual;
} XGpio_Config;

typedef struct
{
    UINTPTR BaseAddress;
    u32 IsReady;
    int InterruptPresent;
    int IsDual;
} XGpio;

XGpio_Config* XGpio_LookupConfig(u16 DeviceId);
int XGpio_CfgInitialize(XGpio* InstancePtr, XGpio_Config* Config, UINTPTR EffectiveAddr);
int XGpio_Initialize(XGpio* InstancePtr, u16 DeviceId);
void XGpio_SetDataDirection(XGpio* InstancePtr, unsigned Channel, u32 DirectionMask);
u32 XGpio_GetDataDirection(XGpio* InstancePtr, unsigned Channel);
u32 XGpio_DiscreteRead(XGpio* InstancePtr, unsigned Channel);
void XGpio_DiscreteWrite(XGpio* InstancePtr, unsigned Channel, u32 Data);

#endif /* XGPIO_H */
