/*
* TEXAS INSTRUMENTS TEXT FILE LICENSE

* Copyright (c) 2022 - 2023 Texas Instruments Incorporated
*
* All rights reserved not granted herein.
* Limited License.
*
* Texas Instruments Incorporated grants a world-wide, royalty-free,
* non-exclusive license under copyrights and patents it now or hereafter
* owns or controls to make, have made, use, import, offer to sell and sell ("Utilize")
* this software subject to the terms herein.  With respect to the foregoing patent
* license, such license is granted  solely to the extent that any such patent is necessary
* to Utilize the software alone.  The patent license shall not apply to any combinations which
* include this software, other than combinations with devices manufactured by or for TI ("TI Devices").
* No hardware patent is licensed hereunder.
*
* Redistributions must preserve existing copyright notices and reproduce this license (including the
* above copyright notice and the disclaimer and (if applicable) source code license limitations below)
* in the documentation and/or other materials provided with the distribution
*
* Redistribution and use in binary form, without modification, are permitted provided that the following
* conditions are met:
*
*	* No reverse engineering, decompilation, or disassembly of this software is permitted with respect to any
*     software provided in binary form.
*	* any redistribution and use are licensed by TI for use only with TI Devices.
*	* Nothing shall obligate TI to provide you with source code for the software licensed and provided to you in object code.
*
* If software source code is provided to you, modification and redistribution of the source code are permitted
* provided that the following conditions are met:
*
*   * any redistribution and use of the source code, including any resulting derivative works, are licensed by
*     TI for use only with TI Devices.
*   * any redistribution and use of any object code compiled from the source code and any resulting derivative
*     works, are licensed by TI for use only with TI Devices.
*
* Neither the name of Texas Instruments Incorporated nor the names of its suppliers may be used to endorse or
* promote products derived from this software without specific prior written permission.
*
* DISCLAIMER.
*
* THIS SOFTWARE IS PROVIDED BY TI AND TI'S LICENSORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
* BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
* IN NO EVENT SHALL TI AND TI'S LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
* OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
* OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
* POSSIBILITY OF SUCH DAMAGE.
*/

#ifndef tiAfe79_AFE_CONTROLS_H
#define tiAfe79_AFE_CONTROLS_H
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"

#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(getChipVersion)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(overrideTddPins)(AFE79_INST_TYPE afeInst, uint8_t rx, uint8_t fb, uint8_t tx);
TI_AFE_API_COMP uint8_t AFE79FNP(readAlarmPinStatus)(AFE79_INST_TYPE afeInst, uint8_t alarmNo, uint8_t *status); // status:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(overrideAlarmPin)(AFE79_INST_TYPE afeInst, uint8_t alarmNo, uint8_t overrideSel, uint8_t overrideVal);
TI_AFE_API_COMP uint8_t AFE79FNP(overrideRelDetPin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t overrideSel, uint8_t overrideVal);
TI_AFE_API_COMP uint8_t AFE79FNP(overrideDigPkDetPin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t pinNo, uint8_t overrideSel, uint8_t overrideVal);
TI_AFE_API_COMP uint8_t AFE79FNP(lowLatencyModeProgDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t progDelay); 
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay);
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay);
#endif

TI_AFE_API_COMP uint8_t AFE79FNP(overrideTdd)(AFE79_INST_TYPE afeInst, uint8_t rx, uint8_t fb, uint8_t tx, uint8_t enableOverride);
TI_AFE_API_COMP uint8_t AFE79FNP(checkSysref)(AFE79_INST_TYPE afeInst, uint8_t clearSysrefFlag, uint8_t *sysrefReceived); // sysrefReceived:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(sendSysref)(AFE79_INST_TYPE afeInst, uint8_t spiSysref, uint8_t getSpiAccess);
TI_AFE_API_COMP uint8_t AFE79FNP(checkPllLockStatus)(AFE79_INST_TYPE afeInst, uint8_t *pllLockStatus); // pllLockStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(clearPllStickyLockStatus)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(clearSpiAlarms)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(readSpiAlarms)(AFE79_INST_TYPE afeInst, uint8_t *alarmStatus);                                                     // alarmStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readTxPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t windowLen, double *powerReadB0, double *powerReadB1); // powerReadB0:retVal;powerReadB1:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getRxRmsPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, double *avg_pwrdb);                                          // avg_pwrdb:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getFbRmsPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, double *avg_pwrdb);                                          // avg_pwrdb:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(clearAllAlarms)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(checkDeviceHealth)(AFE79_INST_TYPE afeInst, uint16_t *allOk); // allOk:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(startMonitoring)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(stopMonitoring)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(computeGolden)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(checkAsyncFifoStatus)(AFE79_INST_TYPE afeInst, uint64_t *asyncFifoStatus); // asyncFifoStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readSysrefMonitor)(AFE79_INST_TYPE afeInst, uint8_t *sysrefMonitorReadout); //sysrefMonitorReadout:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(afeSysrefMonitor)(AFE79_INST_TYPE afeInst, uint8_t enable, uint8_t *readVal); // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getDeviceTemp)(AFE79_INST_TYPE afeInst, int16_t *tempValue); // tempValue:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readPllCapCode)(AFE79_INST_TYPE afeInst, uint8_t *pllCapCode); //pllCapCode:retVal;
#endif
