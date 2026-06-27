/* Minimal Xilinx BSP stub for Spec2Code QC (syntax/type check only — NOT the real BSP). */
#ifndef XIL_TYPES_H
#define XIL_TYPES_H
#include <stdint.h>
#include <stddef.h>
#ifndef TRUE
#define TRUE 1
#endif
#ifndef FALSE
#define FALSE 0
#endif
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int32_t s32;
typedef uintptr_t UINTPTR;
#endif /* XIL_TYPES_H */
