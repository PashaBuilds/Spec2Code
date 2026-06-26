/* Minimal Xilinx XSpiPs stub for Spec2Code QC (syntax/type check only). */
#ifndef XSPIPS_H
#define XSPIPS_H
#include "xil_types.h"

#define XSPIPS_MASTER_OPTION 0x00000001U
#define XSPIPS_FORCE_SSELECT_OPTION 0x00000004U
#define XSPIPS_CLK_PRESCALE_8 0x03U

typedef struct
{
    uint16_t DeviceId;
    uint32_t BaseAddress;
} XSpiPs_Config;

typedef struct
{
    XSpiPs_Config Config;
    uint32_t IsReady;
} XSpiPs;

XSpiPs_Config *XSpiPs_LookupConfig(uint16_t DeviceId);
int XSpiPs_CfgInitialize(XSpiPs *InstancePtr, XSpiPs_Config *ConfigPtr, uint32_t EffectiveAddr);
int XSpiPs_SetOptions(XSpiPs *InstancePtr, uint32_t Options);
int XSpiPs_SetClkPrescaler(XSpiPs *InstancePtr, uint8_t Prescaler);
int XSpiPs_SetSlaveSelect(XSpiPs *InstancePtr, uint8_t SlaveSel);
int XSpiPs_PolledTransfer(XSpiPs *InstancePtr, uint8_t *SendBufPtr, uint8_t *RecvBufPtr, uint32_t ByteCount);

#endif /* XSPIPS_H */
