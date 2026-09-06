/* Host stub: AXI IIC dusuk seviye API (xiic_l.h) - gercek imzalarla. */
#ifndef XIIC_L_H
#define XIIC_L_H
#include "xil_types.h"
#define XIIC_STOP 0x00U
#define XIIC_REPEATED_START 0x01U
int XIic_DynInit(UINTPTR BaseAddress);
u32 XIic_WaitBusFree(UINTPTR BaseAddress);
unsigned XIic_DynSend(UINTPTR BaseAddress, u16 Address, u8* BufferPtr, u8 ByteCount, u8 Option);
unsigned XIic_DynRecv(UINTPTR BaseAddress, u8 Address, u8* BufferPtr, u8 ByteCount);
unsigned XIic_Send(UINTPTR BaseAddress, u8 Address, u8* BufferPtr, unsigned ByteCount, u8 Option);
unsigned XIic_Recv(UINTPTR BaseAddress, u8 Address, u8* BufferPtr, unsigned ByteCount, u8 Option);
#endif
