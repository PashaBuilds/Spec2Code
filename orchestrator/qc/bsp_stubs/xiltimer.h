/* Minimal xiltimer stub (Vitis Unified / SDT) for Spec2Code QC. */
#ifndef XILTIMER_H
#define XILTIMER_H
#include "xil_types.h"
typedef void (*XTimer_TickHandler)(void* CallBackRef, u32 StatusEvent);
void XTimer_SetInterval(unsigned long delay);
void XTimer_SetHandler(XTimer_TickHandler FuncPtr, void* CallBackRef, u8 Priority);
#endif /* XILTIMER_H */
