/* Minimal Xilinx XIicPs stub for Spec2Code QC (syntax/type check only). */
#ifndef XIICPS_H
#define XIICPS_H
#include "xil_types.h"

typedef struct
{
    uint16_t DeviceId;
    uint32_t BaseAddress;
} XIicPs_Config;

typedef struct
{
    XIicPs_Config Config;
    uint32_t IsReady;
} XIicPs;

XIicPs_Config *XIicPs_LookupConfig(uint16_t DeviceId);
int XIicPs_CfgInitialize(XIicPs *InstancePtr, XIicPs_Config *ConfigPtr, uint32_t EffectiveAddr);
int XIicPs_SetSClk(XIicPs *InstancePtr, uint32_t FsclHz);
int XIicPs_MasterSendPolled(XIicPs *InstancePtr, uint8_t *MsgPtr, int ByteCount, uint16_t SlaveAddr);
int XIicPs_MasterRecvPolled(XIicPs *InstancePtr, uint8_t *MsgPtr, int ByteCount, uint16_t SlaveAddr);
int XIicPs_BusIsBusy(XIicPs *InstancePtr);

#endif /* XIICPS_H */
