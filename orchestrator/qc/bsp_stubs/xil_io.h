/* Minimal xil_io.h stub for QC static analysis (clang-tidy/cppcheck).
 * Mirrors the real Xilinx standalone BSP signatures so generated agent code
 * that uses the Xil_In / Xil_Out accessors (mem_read/mem_write) parses cleanly.
 * Not used at build time on target - there the real BSP header is picked up. */
#ifndef XIL_IO_H
#define XIL_IO_H

#include "xil_types.h"

u8 Xil_In8(UINTPTR Addr);
u16 Xil_In16(UINTPTR Addr);
u32 Xil_In32(UINTPTR Addr);
void Xil_Out8(UINTPTR Addr, u8 Value);
void Xil_Out16(UINTPTR Addr, u16 Value);
void Xil_Out32(UINTPTR Addr, u32 Value);

#endif /* XIL_IO_H */
