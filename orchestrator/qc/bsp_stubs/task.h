/* Minimal FreeRTOS task stub for Spec2Code QC (syntax/type check only). */
#ifndef TASK_H
#define TASK_H
#include "FreeRTOS.h"

typedef void* TaskHandle_t;

void vTaskDelay(TickType_t xTicksToDelay);
void vTaskDelete(TaskHandle_t xTaskToDelete);
void vTaskStartScheduler(void);

#endif /* TASK_H */
