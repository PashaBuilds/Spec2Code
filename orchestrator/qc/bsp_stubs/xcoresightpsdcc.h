/* Spec2Code QC stub: coresightps_dcc surucusu (ZynqMP/Versal DCC bayt kanali). Yalniz tip denetimi. */
#ifndef XCORESIGHTPSDCC_H
#define XCORESIGHTPSDCC_H

#include "xil_types.h"

void XCoresightPs_DccSendByte(u32 BaseAddress, u8 Data);
u8 XCoresightPs_DccRecvByte(u32 BaseAddress);

#endif /* XCORESIGHTPSDCC_H */
