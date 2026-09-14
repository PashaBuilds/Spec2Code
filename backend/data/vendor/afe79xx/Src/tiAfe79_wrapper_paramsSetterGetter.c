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

#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include "tiAfe79_afeGlobalConstants.h"

#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_paramsSetterGetter.h"

uint8_t AFE79FNP(wrap_set_chipId)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_chipId)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_chipVersion)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_X)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_X)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_FRef)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_FRef)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_FadcRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_FadcRx)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_FadcFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_FadcFb)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_Fdac)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint32_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_Fdac)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxEnable)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbEnable)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_txEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_txEnable)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_RRFMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_adcSelect0)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_adcSelect1)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_modeTdd)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_externalClockRx)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_externalClockTx)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_useSpiSysref)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_continuousSysref)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_sysrefTermination)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_spiMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_spiMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ncoFreqMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_halfRateModeRx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_halfRateModeFb)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_halfRateModeTx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_enableAdcAveragingMode)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_combineDucMode)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_enableTxFbLoopbackLowLatencyMode)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ddcFactorRx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t index1 = 0;
    uint8_t index2 = 0;
    uint32_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index1, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index2, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_rxNco)(afeInst, index0, index1, index2, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numBandsRx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numRxNCOB0)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numRxNCOB1)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t topNo = 0;
    uint8_t val = 0;

    memcpy(&topNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ncoRxMode)(afeInst, topNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_broadcastRxNcoSel)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ddcFactorFb)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t index1 = 0;
    uint32_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index1, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_fbNco)(afeInst, index0, index1, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chNo = 0;
    uint8_t val = 0;

    memcpy(&chNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numFbNCO)(afeInst, chNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ncoFbMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ducFactorTx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_txNco)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t index1 = 0;
    uint8_t index2 = 0;
    uint32_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index1, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index2, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_txNco)(afeInst, index0, index1, index2, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numBandsTx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numTxNCOB0)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_numTxNCOB1)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t bandNo = 0;
    uint8_t val = 0;

    memcpy(&bandNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_ncoTxMode)(afeInst, bandNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_broadcastTxNcoSel)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_enableDacInterleavedMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdLoopbackEn)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_syncLoopBack)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdABLvdsSync)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdCDLvdsSync)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_executeLinkUpSequenceSeparately)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_L)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_M)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_F)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_S)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_Hd)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdRx_Misc)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_L)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_M)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_F)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_S)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_Hd)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdFb_Misc)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t topNo = 0;
    uint8_t val = 0;

    memcpy(&topNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdSystemMode)(afeInst, topNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t topNo = 0;
    uint8_t val = 0;

    memcpy(&topNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdTxProtocol)(afeInst, topNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxJesdTxScr)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbJesdTxScr)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxJesdTxK)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbJesdTxK)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxJesdTxSyncMux)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbJesdTxSyncMux)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_setIlaParams)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdTxIlaM)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdTxIlaL)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdTxIlaLid)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesTxLanePolarity)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdTxLaneMux)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_adcDataMuxEn)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t converterNumber = 0;
    uint8_t val = 0;

    memcpy(&converterNumber, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxDataMux)(afeInst, converterNumber, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t converterNumber = 0;
    uint8_t val = 0;

    memcpy(&converterNumber, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbDataMux)(afeInst, converterNumber, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdSendZeroesInTddOff)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesTxPreCursor)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesTxPostCursor)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesTxMainCursor)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_L)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_M)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_F)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_S)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_Hd)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_LMFSHdTx_Misc)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxSyncMux)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t topNo = 0;
    uint8_t val = 0;

    memcpy(&topNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxProtocol)(afeInst, topNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesRxLanePolarity)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxLaneMux)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxRbd)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxScr)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxK)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t mapperNo = 0;
    uint8_t val = 0;

    memcpy(&mapperNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_jesdRxInitLmfcCounter)(afeInst, mapperNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_dacDataMuxEn)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t converterNumber = 0;
    uint8_t val = 0;

    memcpy(&converterNumber, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_txDataMux)(afeInst, converterNumber, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesManualCTLEEn)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t laneNo = 0;
    uint8_t val = 0;

    memcpy(&laneNo, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_serdesManualCTLE)(afeInst, laneNo, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_defaultRxDsa)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_defaultFbDsa)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_defaultTxDsa)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_enableRxDsaCalibration)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t startStop = 0;
    uint8_t val = 0;

    memcpy(&startStop, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_rxDsaGainRange)(afeInst, startStop, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_enableTxDsaCalibration)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t startStop = 0;
    uint8_t val = 0;

    memcpy(&startStop, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_txDsaGainRange)(afeInst, startStop, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_reliabilityDetectorDecayMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbDsaPerTxEn)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_fbDsaPerTx)(afeInst, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_txToFbMode)(afeInst, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t val = 0;

    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_spiInUseForPllAccess)(afeInst, val);

    return errorStatus;
}
#endif
