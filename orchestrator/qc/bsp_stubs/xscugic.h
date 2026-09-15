/* Minimal xscugic.h stub for QC static analysis (ZynqMP GIC, classic BSP). */
#ifndef XSCUGIC_H
#define XSCUGIC_H
#include "xil_types.h"
#include "xstatus.h"
#ifndef XPAR_SCUGIC_SINGLE_DEVICE_ID
#define XPAR_SCUGIC_SINGLE_DEVICE_ID 0U
#endif
typedef void (*Xil_InterruptHandler)(void* CallBackRef);
typedef struct { u32 IsReady; UINTPTR CpuBaseAddress; } XScuGic;
int XScuGic_DeviceInitialize(u32 DeviceId);
void XScuGic_DeviceInterruptHandler(void* DeviceId);
void XScuGic_RegisterHandler(u32 BaseAddress, int InterruptId, Xil_InterruptHandler Handler, void* CallBackRef);
void XScuGic_EnableIntr(u32 DistBaseAddress, u32 Int_Id);
void XScuGic_DisableIntr(u32 DistBaseAddress, u32 Int_Id);
#endif /* XSCUGIC_H */
