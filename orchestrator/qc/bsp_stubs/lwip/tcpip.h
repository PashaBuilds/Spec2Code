/* Minimal lwIP tcpip (OS mode core thread) stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_TCPIP_H
#define LWIP_TCPIP_H

#include "lwip/err.h"

typedef void (*tcpip_init_done_fn)(void* vpArg);
typedef void (*tcpip_callback_fn)(void* vpArg);

void tcpip_init(tcpip_init_done_fn fpInitDone, void* vpArg);
err_t tcpip_callback(tcpip_callback_fn fpFunction, void* vpArg);

#endif /* LWIP_TCPIP_H */
