/* Minimal xtmrctr_l.h stub for QC static analysis (AXI Timer low-level API). */
#ifndef XTMRCTR_L_H
#define XTMRCTR_L_H
#include "xil_types.h"
#define XTC_CSR_ENABLE_TMR_MASK 0x00000080U
#define XTC_CSR_ENABLE_INT_MASK 0x00000040U
#define XTC_CSR_AUTO_RELOAD_MASK 0x00000010U
#define XTC_CSR_DOWN_COUNT_MASK 0x00000002U
#define XTC_CSR_INT_OCCURED_MASK 0x00000100U
#define XTC_CSR_LOAD_MASK 0x00000020U
void XTmrCtr_SetLoadReg(UINTPTR BaseAddress, u8 TmrCtrNumber, u32 RegisterValue);
void XTmrCtr_SetControlStatusReg(UINTPTR BaseAddress, u8 TmrCtrNumber, u32 RegisterValue);
#endif /* XTMRCTR_L_H */
