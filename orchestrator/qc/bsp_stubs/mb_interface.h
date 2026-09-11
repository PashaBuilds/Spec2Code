/* Minimal mb_interface.h stub for QC static analysis (MicroBlaze). */
#ifndef MB_INTERFACE_H
#define MB_INTERFACE_H
#include "xil_types.h"
#ifndef XINTC_H
typedef void (*XInterruptHandler)(void* CallBackRef);
#endif
void microblaze_register_handler(XInterruptHandler Handler, void* DataPtr);
void microblaze_enable_interrupts(void);
void microblaze_disable_interrupts(void);
#endif /* MB_INTERFACE_H */
