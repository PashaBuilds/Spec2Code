/* Minimal FreeRTOS stub for Spec2Code QC (syntax/type check only). */
#ifndef FREERTOS_H
#define FREERTOS_H
#include "xil_types.h"
typedef uint32_t TickType_t;
#define pdMS_TO_TICKS(ms) ((TickType_t)(ms))
#endif /* FREERTOS_H */
