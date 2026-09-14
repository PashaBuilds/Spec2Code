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
#ifndef DOXYGEN_SHOULD_SKIP_THIS

#ifndef TIAFE79_WRAPPER_PAPPARAMSSETTERGETTER_H
#define TIAFE79_WRAPPER_PAPPARAMSSETTERGETTER_H

typedef uint8_t (*afe79PapSysParamWrapFunction)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);

// tiAfe79_papParamsSetterGetter.h

uint8_t AFE79FNP(wrap_set_pap_enable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);               // index : 0
uint8_t AFE79FNP(wrap_set_pap_maEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);             // index : 1
uint8_t AFE79FNP(wrap_set_pap_maNumSample)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);          // index : 2
uint8_t AFE79FNP(wrap_set_pap_maWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 3
uint8_t AFE79FNP(wrap_set_pap_maWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);       // index : 4
uint8_t AFE79FNP(wrap_set_pap_maThreshB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 5
uint8_t AFE79FNP(wrap_set_pap_maThreshB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 6
uint8_t AFE79FNP(wrap_set_pap_maThreshComb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 7
uint8_t AFE79FNP(wrap_set_pap_hpfEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);            // index : 8
uint8_t AFE79FNP(wrap_set_pap_hpfNumSample)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 9
uint8_t AFE79FNP(wrap_set_pap_hpfWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);        // index : 10
uint8_t AFE79FNP(wrap_set_pap_hpfWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);      // index : 11
uint8_t AFE79FNP(wrap_set_pap_hpfThreshB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);          // index : 12
uint8_t AFE79FNP(wrap_set_pap_hpfThreshB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);          // index : 13
uint8_t AFE79FNP(wrap_set_pap_hpfThreshComb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);        // index : 14
uint8_t AFE79FNP(wrap_set_pap_multMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);             // index : 15
uint8_t AFE79FNP(wrap_set_pap_rampDownStartVal)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);     // index : 16
uint8_t AFE79FNP(wrap_set_pap_waitCounter)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);          // index : 17
uint8_t AFE79FNP(wrap_set_pap_gainStepSize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 18
uint8_t AFE79FNP(wrap_set_pap_attnStepSize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 19
uint8_t AFE79FNP(wrap_set_pap_amplUpdateCycles)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);     // index : 20
uint8_t AFE79FNP(wrap_set_pap_triggerClearToRampUp)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray); // index : 21
uint8_t AFE79FNP(wrap_set_pap_triggerToRampDown)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);    // index : 22
uint8_t AFE79FNP(wrap_set_pap_detectInWaitState)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);    // index : 23
uint8_t AFE79FNP(wrap_set_pap_rampStickyMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);       // index : 24
uint8_t AFE79FNP(wrap_set_pap_alarmChannelMask)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);     // index : 25
uint8_t AFE79FNP(wrap_set_pap_alarmMask)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);            // index : 26
uint8_t AFE79FNP(wrap_set_pap_alarmPinDynamicMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);  // index : 27
uint8_t AFE79FNP(wrap_set_pap_alarmPulseGPIO)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);       // index : 28

afe79PapSysParamWrapFunction AFE79FNP(papWrapperFunctionTable)[29] = {AFE79FNP(wrap_set_pap_enable),
                                                                      AFE79FNP(wrap_set_pap_maEnable),
                                                                      AFE79FNP(wrap_set_pap_maNumSample),
                                                                      AFE79FNP(wrap_set_pap_maWindowCntr),
                                                                      AFE79FNP(wrap_set_pap_maWindowCntrTh),
                                                                      AFE79FNP(wrap_set_pap_maThreshB0),
                                                                      AFE79FNP(wrap_set_pap_maThreshB1),
                                                                      AFE79FNP(wrap_set_pap_maThreshComb),
                                                                      AFE79FNP(wrap_set_pap_hpfEnable),
                                                                      AFE79FNP(wrap_set_pap_hpfNumSample),
                                                                      AFE79FNP(wrap_set_pap_hpfWindowCntr),
                                                                      AFE79FNP(wrap_set_pap_hpfWindowCntrTh),
                                                                      AFE79FNP(wrap_set_pap_hpfThreshB0),
                                                                      AFE79FNP(wrap_set_pap_hpfThreshB1),
                                                                      AFE79FNP(wrap_set_pap_hpfThreshComb),
                                                                      AFE79FNP(wrap_set_pap_multMode),
                                                                      AFE79FNP(wrap_set_pap_rampDownStartVal),
                                                                      AFE79FNP(wrap_set_pap_waitCounter),
                                                                      AFE79FNP(wrap_set_pap_gainStepSize),
                                                                      AFE79FNP(wrap_set_pap_attnStepSize),
                                                                      AFE79FNP(wrap_set_pap_amplUpdateCycles),
                                                                      AFE79FNP(wrap_set_pap_triggerClearToRampUp),
                                                                      AFE79FNP(wrap_set_pap_triggerToRampDown),
                                                                      AFE79FNP(wrap_set_pap_detectInWaitState),
                                                                      AFE79FNP(wrap_set_pap_rampStickyMode),
                                                                      AFE79FNP(wrap_set_pap_alarmChannelMask),
                                                                      AFE79FNP(wrap_set_pap_alarmMask),
                                                                      AFE79FNP(wrap_set_pap_alarmPinDynamicMode),
                                                                      AFE79FNP(wrap_set_pap_alarmPulseGPIO)};
#endif

#endif