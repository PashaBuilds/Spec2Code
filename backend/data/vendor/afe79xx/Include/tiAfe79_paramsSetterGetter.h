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
#ifndef tiAfe79_AFE_PARAMS_GET_SET_
#define tiAfe79_AFE_PARAMS_GET_SET_

TI_AFE_API_COMP uint8_t AFE79FNP(set_chipId)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_chipId)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_X)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_X)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_FRef)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_FRef)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_FadcRx)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_FadcRx)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_FadcFb)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_FadcFb)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_Fdac)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_Fdac)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_spiMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_spiMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t bandNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t bandNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesRxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesRxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_afeId)(AFE79_INST_TYPE afeInst, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_afeId)(AFE79_INST_TYPE afeInst, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_txChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_txChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val); // val:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(set_logLevel)(AFE79_INST_TYPE afeInst, uint32_t val);
TI_AFE_API_COMP uint8_t AFE79FNP(get_logLevel)(AFE79_INST_TYPE afeInst, uint32_t *val); // val:retVal;
#endif
