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

#ifndef tiAfe79_AFE_BASE_FUNCTIONS_H
#define tiAfe79_AFE_BASE_FUNCTIONS_H

TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiRawWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t data);
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiRawRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *readVal);                         // readVal:retVal;
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *data, uint16_t dataArraySize); // data:argArray[65536];
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t dataArraySize, uint8_t *data);  // data:retArray[65536];
TI_AFE_API_COMP uint8_t AFE79FNP(afeWait)(AFE79_INST_TYPE afeInst, uint32_t wait_s);
TI_AFE_API_COMP uint8_t AFE79FNP(afeWaitMs)(AFE79_INST_TYPE afeInst, uint32_t wait_ms);
TI_AFE_API_COMP uint8_t AFE79FNP(afeLogmsg)(AFE79_INST_TYPE afeInst, uint32_t level, const char *pcLogFmt, ...);
TI_AFE_API_COMP uint8_t AFE79FNP(giveSingleSysrefPulse)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(giveAfeAdcInput)(AFE79_INST_TYPE afeInst, uint8_t rxChNo, uint8_t bandNo);
TI_AFE_API_COMP uint8_t AFE79FNP(connectAfeTxToFb)(AFE79_INST_TYPE afeInst, uint8_t txChNo, uint8_t fbChNo, uint8_t bandNo);

TI_AFE_API_COMP uint8_t AFE79FNP(updateSystemParamsPostDefault)(AFE79_INST_TYPE afeInst);
TI_AFE_API_COMP uint8_t AFE79FNP(loadFactoryCalPackets)(AFE79_INST_TYPE afeInst);

TI_AFE_API_COMP uint8_t AFE79FNP(hostMemRead)(AFE79_INST_TYPE afeInst, uint8_t memType, uint32_t addr, uint32_t numWordsToRead, uint32_t *buffPtr, uint32_t *numWordsActuallyRead); // buffPtr:retArray[1024];numWordsActuallyRead:retVal;

#endif

    