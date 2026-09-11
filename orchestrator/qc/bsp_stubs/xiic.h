/* Minimal Xilinx AXI IIC stub (xiic.h) for Spec2Code QC (syntax/type check only). */
#ifndef XIIC_H
#define XIIC_H
#include "xil_types.h"
#include "xiic_l.h"

typedef struct
{
    u16 DeviceId;
    UINTPTR BaseAddress;
    int Has10BitAddr;
    u8 GpOutWidth;
} XIic_Config;

typedef struct
{
    UINTPTR BaseAddress;
    u32 Has10BitAddr;
    u32 IsReady;
    u32 IsStarted;
} XIic;

#ifdef SDT
XIic_Config* XIic_LookupConfig(UINTPTR BaseAddress);
#else
XIic_Config* XIic_LookupConfig(u16 DeviceId);
#endif
int XIic_CfgInitialize(XIic* InstancePtr, XIic_Config* Config, UINTPTR EffectiveAddr);
int XIic_Start(XIic* InstancePtr);
int XIic_Stop(XIic* InstancePtr);

#endif /* XIIC_H */
