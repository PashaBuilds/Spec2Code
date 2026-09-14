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

#ifndef TIAFE79_WRAPPER_PARAMSSETTERGETTER_H
#define TIAFE79_WRAPPER_PARAMSSETTERGETTER_H

typedef uint8_t (*afe79SysParamWrapFunction)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);

uint8_t AFE79FNP(wrap_set_chipId)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                           // index : 0
uint8_t AFE79FNP(wrap_set_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 1
uint8_t AFE79FNP(wrap_set_X)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                                // index : 2
uint8_t AFE79FNP(wrap_set_FRef)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                             // index : 3
uint8_t AFE79FNP(wrap_set_FadcRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                           // index : 4
uint8_t AFE79FNP(wrap_set_FadcFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                           // index : 5
uint8_t AFE79FNP(wrap_set_Fdac)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                             // index : 6
uint8_t AFE79FNP(wrap_set_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                         // index : 7
uint8_t AFE79FNP(wrap_set_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                         // index : 8
uint8_t AFE79FNP(wrap_set_txEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                         // index : 9
uint8_t AFE79FNP(wrap_set_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                          // index : 10
uint8_t AFE79FNP(wrap_set_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 11
uint8_t AFE79FNP(wrap_set_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 12
uint8_t AFE79FNP(wrap_set_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                          // index : 13
uint8_t AFE79FNP(wrap_set_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                  // index : 14
uint8_t AFE79FNP(wrap_set_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                  // index : 15
uint8_t AFE79FNP(wrap_set_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 16
uint8_t AFE79FNP(wrap_set_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                 // index : 17
uint8_t AFE79FNP(wrap_set_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                // index : 18
uint8_t AFE79FNP(wrap_set_spiMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                          // index : 19
uint8_t AFE79FNP(wrap_set_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 20
uint8_t AFE79FNP(wrap_set_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 21
uint8_t AFE79FNP(wrap_set_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 22
uint8_t AFE79FNP(wrap_set_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 23
uint8_t AFE79FNP(wrap_set_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 24
uint8_t AFE79FNP(wrap_set_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 25
uint8_t AFE79FNP(wrap_set_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray); // index : 26
uint8_t AFE79FNP(wrap_set_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 27
uint8_t AFE79FNP(wrap_set_rxNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                            // index : 28
uint8_t AFE79FNP(wrap_set_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 29
uint8_t AFE79FNP(wrap_set_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 30
uint8_t AFE79FNP(wrap_set_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 31
uint8_t AFE79FNP(wrap_set_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 32
uint8_t AFE79FNP(wrap_set_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                // index : 33
uint8_t AFE79FNP(wrap_set_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 34
uint8_t AFE79FNP(wrap_set_fbNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                            // index : 35
uint8_t AFE79FNP(wrap_set_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                         // index : 36
uint8_t AFE79FNP(wrap_set_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 37
uint8_t AFE79FNP(wrap_set_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 38
uint8_t AFE79FNP(wrap_set_txNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                            // index : 39
uint8_t AFE79FNP(wrap_set_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 40
uint8_t AFE79FNP(wrap_set_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 41
uint8_t AFE79FNP(wrap_set_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 42
uint8_t AFE79FNP(wrap_set_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 43
uint8_t AFE79FNP(wrap_set_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                // index : 44
uint8_t AFE79FNP(wrap_set_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);         // index : 45
uint8_t AFE79FNP(wrap_set_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 46
uint8_t AFE79FNP(wrap_set_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 47
uint8_t AFE79FNP(wrap_set_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 48
uint8_t AFE79FNP(wrap_set_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 49
uint8_t AFE79FNP(wrap_set_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);  // index : 50
uint8_t AFE79FNP(wrap_set_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 51
uint8_t AFE79FNP(wrap_set_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 52
uint8_t AFE79FNP(wrap_set_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 53
uint8_t AFE79FNP(wrap_set_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 54
uint8_t AFE79FNP(wrap_set_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 55
uint8_t AFE79FNP(wrap_set_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 56
uint8_t AFE79FNP(wrap_set_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 57
uint8_t AFE79FNP(wrap_set_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 58
uint8_t AFE79FNP(wrap_set_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 59
uint8_t AFE79FNP(wrap_set_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 60
uint8_t AFE79FNP(wrap_set_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 61
uint8_t AFE79FNP(wrap_set_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 62
uint8_t AFE79FNP(wrap_set_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 63
uint8_t AFE79FNP(wrap_set_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 64
uint8_t AFE79FNP(wrap_set_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 65
uint8_t AFE79FNP(wrap_set_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 66
uint8_t AFE79FNP(wrap_set_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 67
uint8_t AFE79FNP(wrap_set_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 68
uint8_t AFE79FNP(wrap_set_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                  // index : 69
uint8_t AFE79FNP(wrap_set_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                  // index : 70
uint8_t AFE79FNP(wrap_set_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 71
uint8_t AFE79FNP(wrap_set_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 72
uint8_t AFE79FNP(wrap_set_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 73
uint8_t AFE79FNP(wrap_set_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 74
uint8_t AFE79FNP(wrap_set_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);             // index : 75
uint8_t AFE79FNP(wrap_set_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 76
uint8_t AFE79FNP(wrap_set_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 77
uint8_t AFE79FNP(wrap_set_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 78
uint8_t AFE79FNP(wrap_set_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 79
uint8_t AFE79FNP(wrap_set_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 80
uint8_t AFE79FNP(wrap_set_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                // index : 81
uint8_t AFE79FNP(wrap_set_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);               // index : 82
uint8_t AFE79FNP(wrap_set_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);               // index : 83
uint8_t AFE79FNP(wrap_set_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 84
uint8_t AFE79FNP(wrap_set_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 85
uint8_t AFE79FNP(wrap_set_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 86
uint8_t AFE79FNP(wrap_set_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 87
uint8_t AFE79FNP(wrap_set_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                      // index : 88
uint8_t AFE79FNP(wrap_set_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 89
uint8_t AFE79FNP(wrap_set_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 90
uint8_t AFE79FNP(wrap_set_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 91
uint8_t AFE79FNP(wrap_set_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);             // index : 92
uint8_t AFE79FNP(wrap_set_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                    // index : 93
uint8_t AFE79FNP(wrap_set_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 94
uint8_t AFE79FNP(wrap_set_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 95
uint8_t AFE79FNP(wrap_set_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                          // index : 96
uint8_t AFE79FNP(wrap_set_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);            // index : 97
uint8_t AFE79FNP(wrap_set_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 98
uint8_t AFE79FNP(wrap_set_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                        // index : 99
uint8_t AFE79FNP(wrap_set_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);               // index : 100
uint8_t AFE79FNP(wrap_set_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                 // index : 101
uint8_t AFE79FNP(wrap_set_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 102
uint8_t AFE79FNP(wrap_set_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 103
uint8_t AFE79FNP(wrap_set_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 104
uint8_t AFE79FNP(wrap_set_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 105
uint8_t AFE79FNP(wrap_set_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 106
uint8_t AFE79FNP(wrap_set_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);           // index : 107
uint8_t AFE79FNP(wrap_set_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                   // index : 108
uint8_t AFE79FNP(wrap_set_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);     // index : 109
uint8_t AFE79FNP(wrap_set_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                     // index : 110
uint8_t AFE79FNP(wrap_set_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 111
uint8_t AFE79FNP(wrap_set_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);                       // index : 112
uint8_t AFE79FNP(wrap_set_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray);             // index : 113

afe79SysParamWrapFunction AFE79FNP(wrapperFunctionTable)[114] = {AFE79FNP(wrap_set_chipId),
                                                                 AFE79FNP(wrap_set_chipVersion),
                                                                 AFE79FNP(wrap_set_X),
                                                                 AFE79FNP(wrap_set_FRef),
                                                                 AFE79FNP(wrap_set_FadcRx),
                                                                 AFE79FNP(wrap_set_FadcFb),
                                                                 AFE79FNP(wrap_set_Fdac),
                                                                 AFE79FNP(wrap_set_rxEnable),
                                                                 AFE79FNP(wrap_set_fbEnable),
                                                                 AFE79FNP(wrap_set_txEnable),
                                                                 AFE79FNP(wrap_set_RRFMode),
                                                                 AFE79FNP(wrap_set_adcSelect0),
                                                                 AFE79FNP(wrap_set_adcSelect1),
                                                                 AFE79FNP(wrap_set_modeTdd),
                                                                 AFE79FNP(wrap_set_externalClockRx),
                                                                 AFE79FNP(wrap_set_externalClockTx),
                                                                 AFE79FNP(wrap_set_useSpiSysref),
                                                                 AFE79FNP(wrap_set_continuousSysref),
                                                                 AFE79FNP(wrap_set_sysrefTermination),
                                                                 AFE79FNP(wrap_set_spiMode),
                                                                 AFE79FNP(wrap_set_ncoFreqMode),
                                                                 AFE79FNP(wrap_set_halfRateModeRx),
                                                                 AFE79FNP(wrap_set_halfRateModeFb),
                                                                 AFE79FNP(wrap_set_halfRateModeTx),
                                                                 AFE79FNP(wrap_set_enableAdcAveragingMode),
                                                                 AFE79FNP(wrap_set_combineDucMode),
                                                                 AFE79FNP(wrap_set_enableTxFbLoopbackLowLatencyMode),
                                                                 AFE79FNP(wrap_set_ddcFactorRx),
                                                                 AFE79FNP(wrap_set_rxNco),
                                                                 AFE79FNP(wrap_set_numBandsRx),
                                                                 AFE79FNP(wrap_set_numRxNCOB0),
                                                                 AFE79FNP(wrap_set_numRxNCOB1),
                                                                 AFE79FNP(wrap_set_ncoRxMode),
                                                                 AFE79FNP(wrap_set_broadcastRxNcoSel),
                                                                 AFE79FNP(wrap_set_ddcFactorFb),
                                                                 AFE79FNP(wrap_set_fbNco),
                                                                 AFE79FNP(wrap_set_numFbNCO),
                                                                 AFE79FNP(wrap_set_ncoFbMode),
                                                                 AFE79FNP(wrap_set_ducFactorTx),
                                                                 AFE79FNP(wrap_set_txNco),
                                                                 AFE79FNP(wrap_set_numBandsTx),
                                                                 AFE79FNP(wrap_set_numTxNCOB0),
                                                                 AFE79FNP(wrap_set_numTxNCOB1),
                                                                 AFE79FNP(wrap_set_ncoTxMode),
                                                                 AFE79FNP(wrap_set_broadcastTxNcoSel),
                                                                 AFE79FNP(wrap_set_enableDacInterleavedMode),
                                                                 AFE79FNP(wrap_set_jesdLoopbackEn),
                                                                 AFE79FNP(wrap_set_syncLoopBack),
                                                                 AFE79FNP(wrap_set_jesdABLvdsSync),
                                                                 AFE79FNP(wrap_set_jesdCDLvdsSync),
                                                                 AFE79FNP(wrap_set_executeLinkUpSequenceSeparately),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_L),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_M),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_F),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_S),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_Hd),
                                                                 AFE79FNP(wrap_set_LMFSHdRx_Misc),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_L),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_M),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_F),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_S),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_Hd),
                                                                 AFE79FNP(wrap_set_LMFSHdFb_Misc),
                                                                 AFE79FNP(wrap_set_jesdSystemMode),
                                                                 AFE79FNP(wrap_set_jesdTxProtocol),
                                                                 AFE79FNP(wrap_set_rxJesdTxScr),
                                                                 AFE79FNP(wrap_set_fbJesdTxScr),
                                                                 AFE79FNP(wrap_set_rxJesdTxK),
                                                                 AFE79FNP(wrap_set_fbJesdTxK),
                                                                 AFE79FNP(wrap_set_rxJesdTxSyncMux),
                                                                 AFE79FNP(wrap_set_fbJesdTxSyncMux),
                                                                 AFE79FNP(wrap_set_setIlaParams),
                                                                 AFE79FNP(wrap_set_jesdTxIlaM),
                                                                 AFE79FNP(wrap_set_jesdTxIlaL),
                                                                 AFE79FNP(wrap_set_jesdTxIlaLid),
                                                                 AFE79FNP(wrap_set_serdesTxLanePolarity),
                                                                 AFE79FNP(wrap_set_jesdTxLaneMux),
                                                                 AFE79FNP(wrap_set_adcDataMuxEn),
                                                                 AFE79FNP(wrap_set_rxDataMux),
                                                                 AFE79FNP(wrap_set_fbDataMux),
                                                                 AFE79FNP(wrap_set_jesdSendZeroesInTddOff),
                                                                 AFE79FNP(wrap_set_serdesTxPreCursor),
                                                                 AFE79FNP(wrap_set_serdesTxPostCursor),
                                                                 AFE79FNP(wrap_set_serdesTxMainCursor),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_L),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_M),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_F),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_S),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_Hd),
                                                                 AFE79FNP(wrap_set_LMFSHdTx_Misc),
                                                                 AFE79FNP(wrap_set_jesdRxSyncMux),
                                                                 AFE79FNP(wrap_set_jesdRxProtocol),
                                                                 AFE79FNP(wrap_set_serdesRxLanePolarity),
                                                                 AFE79FNP(wrap_set_jesdRxLaneMux),
                                                                 AFE79FNP(wrap_set_jesdRxRbd),
                                                                 AFE79FNP(wrap_set_jesdRxScr),
                                                                 AFE79FNP(wrap_set_jesdRxK),
                                                                 AFE79FNP(wrap_set_jesdRxInitLmfcCounter),
                                                                 AFE79FNP(wrap_set_dacDataMuxEn),
                                                                 AFE79FNP(wrap_set_txDataMux),
                                                                 AFE79FNP(wrap_set_serdesManualCTLEEn),
                                                                 AFE79FNP(wrap_set_serdesManualCTLE),
                                                                 AFE79FNP(wrap_set_defaultRxDsa),
                                                                 AFE79FNP(wrap_set_defaultFbDsa),
                                                                 AFE79FNP(wrap_set_defaultTxDsa),
                                                                 AFE79FNP(wrap_set_enableRxDsaCalibration),
                                                                 AFE79FNP(wrap_set_rxDsaGainRange),
                                                                 AFE79FNP(wrap_set_enableTxDsaCalibration),
                                                                 AFE79FNP(wrap_set_txDsaGainRange),
                                                                 AFE79FNP(wrap_set_reliabilityDetectorDecayMode),
                                                                 AFE79FNP(wrap_set_fbDsaPerTxEn),
                                                                 AFE79FNP(wrap_set_fbDsaPerTx),
                                                                 AFE79FNP(wrap_set_txToFbMode),
                                                                 AFE79FNP(wrap_set_spiInUseForPllAccess)};

#endif

#endif