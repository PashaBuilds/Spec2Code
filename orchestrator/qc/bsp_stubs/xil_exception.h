/* Minimal xil_exception.h stub for QC static analysis. */
#ifndef XIL_EXCEPTION_H
#define XIL_EXCEPTION_H
#include "xil_types.h"
#define XIL_EXCEPTION_ID_INT 16U
typedef void (*Xil_ExceptionHandler)(void* Data);
void Xil_ExceptionInit(void);
void Xil_ExceptionRegisterHandler(u32 Id, Xil_ExceptionHandler Handler, void* Data);
void Xil_ExceptionEnable(void);
#endif /* XIL_EXCEPTION_H */
