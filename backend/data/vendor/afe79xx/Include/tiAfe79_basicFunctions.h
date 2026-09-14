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

#ifndef tiAfe79_AFE_BASIC_FUNCTIONS_H
#define tiAfe79_AFE_BASIC_FUNCTIONS_H

#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(setDefaultParams)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(initializeConfig)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t rxChSel);
TI_AFE_API_COMP uint8_t AFE79FNP(afeFbChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t fbChSel);
TI_AFE_API_COMP uint8_t AFE79FNP(afeTxChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t txChSel);
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxFbChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t RxFbChSel);
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t rxChNo);
TI_AFE_API_COMP uint8_t AFE79FNP(afeFbChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t fbChNo);
TI_AFE_API_COMP uint8_t AFE79FNP(afeTxChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t txChNo);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesTxToJesdLane)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesRxToJesdLane)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneNo);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesRxToJesdLaneSel)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneSel);

TI_AFE_API_COMP uint8_t AFE79FNP(serdesRawRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t *readVal); // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(serdesRawWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t data);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiCheckWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t data, uint8_t *pbSame);         // pbSame:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiPollWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t expectedData, uint8_t lsb, uint8_t msb);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiPollLogWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t expectedData, uint8_t *pollStatus); // pollStatus:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(closeAllPages)(AFE79_INST_TYPE afeInst);
#endif

TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t data, uint8_t lsb, uint8_t msb);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *data, uint16_t dataArraySize); ////data:argArray[65536];
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t *readVal);  // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(serdesWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t data, uint8_t lsb, uint8_t msb);
TI_AFE_API_COMP uint8_t AFE79FNP(serdesReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint16_t *readVal); // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(serdesLaneWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t laneNo, uint16_t data, uint8_t lsb, uint8_t msb);
TI_AFE_API_COMP uint8_t AFE79FNP(serdesLaneReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint32_t laneNo, uint8_t lsb, uint8_t msb, uint16_t *readVal); // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(requestPllSpiAccess)(AFE79_INST_TYPE afeInst, uint8_t regType);
TI_AFE_API_COMP uint8_t AFE79FNP(readTopMem)(AFE79_INST_TYPE afeInst, uint32_t addr, uint64_t *readVal, uint32_t noBytes); // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(splitToByte)(uint64_t val, uint8_t numBytes, uint8_t *splitByteList); // splitByteList:retArray[32];

#endif
