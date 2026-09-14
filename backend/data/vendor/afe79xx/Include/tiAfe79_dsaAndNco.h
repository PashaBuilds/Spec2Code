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

#ifndef tiAfe79_AFE_DSAANDNCO_H
#define tiAfe79_AFE_DSAANDNCO_H

#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDsaMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t mode);
TI_AFE_API_COMP uint8_t AFE79FNP(setPinRxDsaSettings)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaInit, uint8_t dsaStep, uint8_t maxDelay);
TI_AFE_API_COMP uint8_t AFE79FNP(txDsaIdxGainSwap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t anaAttn0, uint8_t anaAttn1, int8_t digB0Gain0, int8_t digB0Gain1, int8_t digB1Gain0, int8_t digB1Gain1);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxGainParam)(AFE79_INST_TYPE afeInst, uint8_t mode, uint8_t transitTime, uint8_t maxAnaDsa);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoDb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t nco, uint32_t band0Nco0, uint32_t band1Nco0, uint32_t band0Nco1, uint32_t band1Nco1);
TI_AFE_API_COMP uint8_t AFE79FNP(rxNCOSel)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t BandId, uint8_t ovr, uint8_t NCOId);
TI_AFE_API_COMP uint8_t AFE79FNP(fbNCOSel)(AFE79_INST_TYPE afeInst, uint8_t topno, uint8_t ovr, uint8_t NCOId);
TI_AFE_API_COMP uint8_t AFE79FNP(setFbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t pinNo, uint8_t dsaSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t en, uint8_t txToFbMode);
#endif
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDigGain)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bandNo, uint8_t dsaSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(setTxDigGain)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bandNo, int16_t dig_gain);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxGain)(AFE79_INST_TYPE afeInst, uint8_t txChainSel, uint8_t gainValidity, uint16_t tx0B0Dsa, uint16_t tx0B1Dsa, uint16_t tx1B0Dsa, uint16_t tx1B1Dsa);
TI_AFE_API_COMP uint8_t AFE79FNP(setTxDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(setFbDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t band, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(readRxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t band, uint8_t nco, uint32_t *ncoFreq); // ncoFreq:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readFbNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t nco, uint32_t *ncoFreq);               // ncoFreq:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(readTxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t band, uint8_t nco, int64_t *val);      // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo);
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco);
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo);
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo);
#endif
