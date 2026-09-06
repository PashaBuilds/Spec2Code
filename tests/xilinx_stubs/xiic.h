/* Host stub: AXI IIC surucu ornegi (xiic.h) - gercek alan adlariyla. */
#ifndef XIIC_H
#define XIIC_H
#include "xil_types.h"
#include "xiic_l.h"
typedef struct { u16 DeviceId; UINTPTR BaseAddress; int Has10BitAddr; u8 GpOutWidth; } XIic_Config;
typedef struct { UINTPTR BaseAddress; u32 Has10BitAddr; u32 IsReady; u32 IsStarted; } XIic;
XIic_Config* XIic_LookupConfig(u16 DeviceId);
int XIic_CfgInitialize(XIic* InstancePtr, XIic_Config* Config, UINTPTR EffectiveAddr);
#endif
