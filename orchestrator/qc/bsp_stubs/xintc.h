/* Minimal xintc.h stub for QC static analysis (AXI INTC). */
#ifndef XINTC_H
#define XINTC_H
#include "xil_types.h"
#include "xstatus.h"
#define XIN_REAL_MODE 0U
typedef void (*XInterruptHandler)(void* CallBackRef);
typedef struct { u32 BaseAddress; u32 IsReady; } XIntc;
int XIntc_Initialize(XIntc* InstancePtr, u16 DeviceId);
int XIntc_Connect(XIntc* InstancePtr, u8 Id, XInterruptHandler Handler, void* CallBackRef);
int XIntc_Start(XIntc* InstancePtr, u8 Mode);
void XIntc_Enable(XIntc* InstancePtr, u8 Id);
void XIntc_InterruptHandler(XIntc* InstancePtr);
#endif /* XINTC_H */
