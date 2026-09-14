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

#ifndef tiAfe79_AFE_SERDES_H
#define tiAfe79_AFE_SERDES_H

#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(serdesTx1010Pattern)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(serdesTxSendData)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(SetSerdesTxCursor)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t mainCursorSetting, uint8_t preCursorSetting, uint8_t postCursorSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxPrbsError)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint32_t *errorRegValue); // errorRegValue:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(enableSerdesRxPrbsCheck)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t prbsMode, uint8_t enable);
TI_AFE_API_COMP uint8_t AFE79FNP(checkAdaptationStatus)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *status);            // status:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(resetSerDesDfeLane)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(reAdaptSerDesLane)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(resetSerDesDfeAllLanes)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(reAdaptSerDesAllLanes)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesEye)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *ber, uint16_t *extent); // ber:retArray[3135];extent:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxLaneEyeMarginValue_mV)(AFE79_INST_TYPE afeInst, uint8_t laneNo, float *eye_mV);   // eye_mV:retVal;
#endif

TI_AFE_API_COMP uint8_t AFE79FNP(clearSerdesRxPrbsErrorCounter)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(generateSerdesTxPrbsError)(AFE79_INST_TYPE afeInst, uint8_t laneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(sendSerdesTxPrbs)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t prbsMode, uint8_t enable);
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxLaneEyeMarginValue)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue); // regValue:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesLinkStatus)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue);       // regValue:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(pollSerdesLinkStatusAllLanes)(AFE79_INST_TYPE afeInst, uint8_t *allLaneStatus);          // allLaneStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readSerdesLaneCtle)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue);       // regValue:retVal;
#endif
