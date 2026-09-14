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

#ifndef tiAfe79_AFE_JESD_H
#define tiAfe79_AFE_JESD_H

#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(jesdRxClearSyncErrorCnt)(AFE79_INST_TYPE afeInst, uint8_t jesdNo);
TI_AFE_API_COMP uint8_t AFE79FNP(jesdRxGetSyncErrorCnt)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t *linkErrorCount);     // linkErrorCount:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(jesdTxGetSyncErrorCnt)(AFE79_INST_TYPE afeInst, uint8_t jesdLaneNo, uint8_t *linkErrorCount); // linkErrorCount:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(adcRampTestPattern)(AFE79_INST_TYPE afeInst, uint8_t topno, uint8_t chNo, uint8_t enable, uint8_t rampIncr);
TI_AFE_API_COMP uint8_t AFE79FNP(toggleSync)(AFE79_INST_TYPE afeInst, uint8_t overrideValue);
TI_AFE_API_COMP uint8_t AFE79FNP(setJesdTxSyncOverride)(AFE79_INST_TYPE afeInst, uint8_t syncNo, uint8_t overrideValue, uint8_t syncValue);
TI_AFE_API_COMP uint8_t AFE79FNP(setJesdRxSyncOverride)(AFE79_INST_TYPE afeInst, uint8_t syncNo, uint8_t overrideValue, uint8_t syncValue);
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdTxFifoErrors)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t *errors); // errors:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(jesdRxFullResetToggle)(AFE79_INST_TYPE afeInst, uint8_t jesdNo);
TI_AFE_API_COMP uint8_t AFE79FNP(jesdTxFullResetToggle)(AFE79_INST_TYPE afeInst, uint8_t jesdNo);
TI_AFE_API_COMP uint8_t AFE79FNP(adcDacSync)(AFE79_INST_TYPE afeInst, uint8_t pinSysref);
TI_AFE_API_COMP uint8_t AFE79FNP(jesdRxResetStateMachine)(AFE79_INST_TYPE afeInst, uint8_t linkNo);
TI_AFE_API_COMP uint8_t AFE79FNP(getSysrefCntOnReleaseOpp)(AFE79_INST_TYPE afeInst, uint8_t linkNo, uint8_t *readVal);          // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(checkIfRbdIsGood)(AFE79_INST_TYPE afeInst, uint8_t linkNo, uint8_t *rbdStatus);                // rbdStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxLaneErrors)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t maskValue);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxLaneFifoErrors)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t losMaskValue, uint8_t fifoMaskValue);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxMiscSerdesErrors)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t maskSerdesPllLock);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdTxFifoErrors)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t maskValue);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxLaneErrorsToPap)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t maskValue);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxLaneFifoErrorsToPap)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t losMaskValue, uint8_t fifoMaskValue);
TI_AFE_API_COMP uint8_t AFE79FNP(maskJesdRxMiscSerdesErrorsToPap)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t maskSerdesPllLock);
#endif

TI_AFE_API_COMP uint8_t AFE79FNP(dacJesdSendData)(AFE79_INST_TYPE afeInst, uint8_t topno);
TI_AFE_API_COMP uint8_t AFE79FNP(dacJesdConstantTestPatternValue)(AFE79_INST_TYPE afeInst, uint8_t topno, uint8_t enable, uint8_t chNo, uint8_t bandNo, uint16_t valueI, uint16_t valueQ);
TI_AFE_API_COMP uint8_t AFE79FNP(dacJesdSendRampTestPattern)(AFE79_INST_TYPE afeInst, uint8_t topno, uint8_t increment);
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxLaneErrors)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *error);           // error:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxLaneFifoErrors)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *error);        // error:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxMiscSerdesErrors)(AFE79_INST_TYPE afeInst, uint8_t jesdNo, uint8_t *errorValue); // errorValue:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxAlarms)(AFE79_INST_TYPE afeInst, uint8_t *error);                                // error:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxLinkStatus)(AFE79_INST_TYPE afeInst, uint16_t *linkStatus);                      // linkStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxLinkStatus204B)(AFE79_INST_TYPE afeInst, uint16_t *linkStatus);                  // linkStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getJesdRxLinkStatus204C)(AFE79_INST_TYPE afeInst, uint16_t *linkStatus);                  // linkStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(clearJesdTxAlarms)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(clearJesdRxAlarms)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(clearJesdRxAlarmsForPap)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(getAllLaneReady)(AFE79_INST_TYPE afeInst, uint8_t linkNo, uint16_t *rbdOffset);                // rbdOffset:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getGoodRbdRange)(AFE79_INST_TYPE afeInst, uint8_t linkNo, uint16_t *rbdMin, uint16_t *rbdMax); // rbdMin,rbdMax:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(setGoodRbd)(AFE79_INST_TYPE afeInst, uint8_t linkNo);
TI_AFE_API_COMP uint8_t AFE79FNP(setManualRbd)(AFE79_INST_TYPE afeInst, uint8_t linkNo, uint8_t value);

#endif
