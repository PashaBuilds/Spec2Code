/* Minimal xintc.h stub for QC static analysis (AXI INTC). */
#ifndef XINTC_H
#define XINTC_H
#include "xil_types.h"
#include "xstatus.h"
#define XIN_REAL_MODE 0U
#ifndef MB_INTERFACE_H
typedef void (*XInterruptHandler)(void* CallBackRef);
#endif
typedef struct { u32 BaseAddress; u32 IsReady; } XIntc;
int XIntc_Initialize(XIntc* InstancePtr, u16 DeviceId);
int XIntc_Connect(XIntc* InstancePtr, u8 Id, XInterruptHandler Handler, void* CallBackRef);
int XIntc_Start(XIntc* InstancePtr, u8 Mode);
void XIntc_Enable(XIntc* InstancePtr, u8 Id);
void XIntc_InterruptHandler(XIntc* InstancePtr);
void XIntc_RegisterHandler(UINTPTR BaseAddress, int InterruptId, XInterruptHandler Handler, void* CallBackRef);
void XIntc_MasterEnable(UINTPTR BaseAddress);
void XIntc_AckIntr(UINTPTR BaseAddress, u32 Mask);
#endif /* XINTC_H */
