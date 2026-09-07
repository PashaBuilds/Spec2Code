/* Minimal lwIP timeouts stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_TIMEOUTS_H
#define LWIP_TIMEOUTS_H

typedef void (*sys_timeout_handler)(void* vpArg);

void sys_timeout(unsigned int uiMsecs, sys_timeout_handler fpHandler, void* vpArg);
void sys_untimeout(sys_timeout_handler fpHandler, void* vpArg);
void sys_check_timeouts(void);

#endif /* LWIP_TIMEOUTS_H */
