/* Minimal Xilinx XQspiPsu stub for Spec2Code QC (syntax/type check only). */
#ifndef XQSPIPSU_H
#define XQSPIPSU_H
#include "xil_types.h"

#define XQSPIPSU_MANUAL_START_OPTION 0x00000001U
#define XQSPIPSU_CLK_PRESCALE_8 0x03U
#define XQSPIPSU_SELECT_MODE_SPI 0U
#define XQSPIPSU_MSG_FLAG_TX 0x01U
#define XQSPIPSU_MSG_FLAG_RX 0x02U
#define XQSPIPSU_SELECT_FLASH_CS_LOWER 0U
#define XQSPIPSU_SELECT_FLASH_BUS_LOWER 0U

typedef struct
{
    uint16_t DeviceId;
    uint32_t BaseAddress;
} XQspiPsu_Config;

typedef struct
{
    XQspiPsu_Config Config;
    uint32_t IsReady;
} XQspiPsu;

typedef struct
{
    uint8_t *TxBfrPtr;
    uint8_t *RxBfrPtr;
    uint32_t ByteCount;
    uint32_t BusWidth;
    uint32_t Flags;
} XQspiPsu_Msg;

/* Classic (non-SDT) 2023.x BSP signature: lookup by device id. */
XQspiPsu_Config *XQspiPsu_LookupConfig(uint16_t DeviceId);
int XQspiPsu_CfgInitialize(XQspiPsu *InstancePtr, XQspiPsu_Config *ConfigPtr, uint32_t EffectiveAddr);
int XQspiPsu_SetOptions(XQspiPsu *InstancePtr, uint32_t Options);
int XQspiPsu_SetClkPrescaler(XQspiPsu *InstancePtr, uint8_t Prescaler);
void XQspiPsu_SelectFlash(XQspiPsu *InstancePtr, uint8_t FlashCS, uint8_t FlashBus);
int XQspiPsu_PolledTransfer(XQspiPsu *InstancePtr, XQspiPsu_Msg *Msg, uint32_t NumMsg);

#endif /* XQSPIPSU_H */
