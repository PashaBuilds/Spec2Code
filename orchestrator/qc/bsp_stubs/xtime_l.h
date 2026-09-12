/* Minimal xtime_l stub (PS islemci sayaci) for Spec2Code QC. */
#ifndef XTIME_L_H
#define XTIME_L_H
#include "xil_types.h"
typedef u64 XTime;
#define COUNTS_PER_SECOND 100000000U
void XTime_GetTime(XTime* Xtime_Global);
#endif /* XTIME_L_H */
