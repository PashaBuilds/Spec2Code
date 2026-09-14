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

#ifndef tiAfe79_AFE_AGC_PARAMS_SET_GET_H
#define tiAfe79_AFE_AGC_PARAMS_SET_GET_H

TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_chainen)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_chainen)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_agcMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_agcMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_tdd_freeze_agc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_tdd_freeze_agc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_blank_time_extcomp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_blank_time_extcomp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_en_agcfreeze_pin)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_en_agcfreeze_pin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_minDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_minDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_maxDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_maxDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atken)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atken)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atksize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atksize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkwinlength)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkwinlength)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkthreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkthreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayen)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayen)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaysize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaysize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaywinlength)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaywinlength)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaythreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaythreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdeten)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdeten)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_custRfMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_custRfMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetstepsize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetstepsize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetThreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetThreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetNumhitsmode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetNumhitsmode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetnumhits)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetnumhits)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_extLnaTempModel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_extLnaTempModel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_singleDualBandMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_singleDualBandMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_enBandDet)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_enBandDet)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_tapOffPoint)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_tapOffPoint)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnagain0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnagain0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaphase0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaphase0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnagain1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnagain1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaphase1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaphase1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaGainMargin)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaGainMargin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_startTemp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_startTemp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_stepTemp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_stepTemp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_NumStep)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_NumStep)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_temp_idxB0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_temp_idxB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_temp_idxB1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_temp_idxB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin0sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin0sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin1sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin1sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin2sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin2sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin3sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin3sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pkDetPinLsbSel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pkDetPinLsbSel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pulseExpansionCount)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pulseExpansionCount)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pkDetOnPenultimateLsb)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pkDetOnPenultimateLsb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_gpioRstEnable)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_gpioRstEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_dsaInit)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_dsaInit)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_dsaStep)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_dsaStep)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_maxInpPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_maxInpPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_alcEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_alcEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_alcMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_alcMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_totalGainRange)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_totalGainRange)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_minAttnAlc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_minAttnAlc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_useMinAttnAgc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_useMinAttnAgc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_fltPtMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_fltPtMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_fltPtFmt)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_fltPtFmt)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_stepSize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_stepSize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_nBitIndex)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_nBitIndex)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_indexInvert)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_indexInvert)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_indexSwapIQ)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_indexSwapIQ)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_sigBackOff)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_sigBackOff)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_gainChangeIndEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_gainChangeIndEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_outputDgcPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_outputDgcPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val); // val:retVal;
#endif
