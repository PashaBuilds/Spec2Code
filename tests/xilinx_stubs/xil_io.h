/* Host stub: xil_io.h - register erisimi sahte bellege gider (stdout'a da yazilir). */
#ifndef XIL_IO_H
#define XIL_IO_H
#include "xil_types.h"
void Xil_Out32(UINTPTR Addr, u32 Value);
u32 Xil_In32(UINTPTR Addr);
#endif
