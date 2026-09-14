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
#ifndef tiAfe79_AFE_AGC_H
#define tiAfe79_AFE_AGC_H

TI_AFE_API_COMP uint8_t AFE79FNP(agcStateControlConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t agcstate);
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bigStepAttkEn, uint8_t smallStepAttkEn, uint8_t bigStepDecEn, uint8_t smallStepDecEn, uint8_t powerAttkEn, uint8_t powerDecEn, uint8_t bigStepAttkThresh, uint8_t smallStepAttkThresh, uint8_t bigStepDecThresh, uint8_t smallStepDecThresh, uint8_t powerAttkThresh, uint8_t powerDecThresh);
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetTimeConstantConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkWinLen, uint32_t miscStepAttkWinLen, uint32_t decayWinLen);
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetAbsoluteNumCrossingConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkNumHits, uint32_t smallStepAttkNumHits, uint32_t bigStepDecNumHits, uint32_t smallStepDecNumHits);
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetRelativeNumCrossingConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkNumHits, uint32_t smallStepAttkNumHits, uint32_t bigStepDecNumHits, uint32_t smallStepDecNumHits);
TI_AFE_API_COMP uint8_t AFE79FNP(externalAgcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t pin0sel, uint16_t pin1sel, uint16_t pin2sel, uint16_t pin3sel, uint8_t pkDetPinLsbSel, uint8_t pulseExpansionCount, uint8_t noLsbsToSend);
TI_AFE_API_COMP uint8_t AFE79FNP(minMaxDsaAttnConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t minDsaAttn, uint8_t maxDsaAttn);
TI_AFE_API_COMP uint8_t AFE79FNP(agcGainStepSizeConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bigStepAttkStepSize, uint8_t smallStepAttkStepSize, uint8_t bigStepDecayStepSize, uint8_t smallStepDecayStepSize);
TI_AFE_API_COMP uint8_t AFE79FNP(internalAgcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t tdd_freeze_agc, uint16_t blank_time_extcomp, uint8_t en_agcfreeze_pin, uint8_t extCompControlEn);
TI_AFE_API_COMP uint8_t AFE79FNP(rfAnalogDetConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t rfdeten, uint8_t rfDetMode, uint8_t rfDetNumHitsMode, uint32_t rfdetnumhits, uint8_t rfdetThreshold, uint8_t rfdetstepsize);
TI_AFE_API_COMP uint8_t AFE79FNP(extLnaConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t singleDualBandMode, uint8_t lnaGainMargin, uint8_t enBandDet, uint8_t tapOffPoint);
TI_AFE_API_COMP uint8_t AFE79FNP(extLnaGainConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t lnaGainB0, uint16_t lnaPhaseB0, uint16_t lnaGainB1, uint16_t lnaPhaseB1);
TI_AFE_API_COMP uint8_t AFE79FNP(alcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t alcMode, uint8_t totalGainRange, uint8_t minAttnAlc, uint8_t useMinAttnAgc);
TI_AFE_API_COMP uint8_t AFE79FNP(fltPtConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t fltPtMode, uint8_t fltPtFmt);
TI_AFE_API_COMP uint8_t AFE79FNP(coarseFineConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t stepSize, uint8_t nBitIndex, uint8_t indexInvert, uint8_t indexSwapIQ, uint8_t sigBackOff, uint8_t gainChangeIndEn);
TI_AFE_API_COMP uint8_t AFE79FNP(agcAlcConfiguration)(AFE79_INST_TYPE afeInst);
#endif

#endif
