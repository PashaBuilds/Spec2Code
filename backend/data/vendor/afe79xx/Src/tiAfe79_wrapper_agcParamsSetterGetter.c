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
#include "tiAfe79_afeLibGlobals.h"

#include "tiAfe79_agcParamsSetterGetter.h"

uint8_t AFE79FNP(wrap_set_agc_chainen)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_chainen)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_agcMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_agcMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_tdd_freeze_agc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_tdd_freeze_agc)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_blank_time_extcomp)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_blank_time_extcomp)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_en_agcfreeze_pin)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_en_agcfreeze_pin)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_minDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_minDsaAttn)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_maxDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_maxDsaAttn)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atken)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_atken)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atksize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_atksize)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atkwinlength)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_agc_atkwinlength)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atkthreshold)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_atkthreshold)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atkNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_atkNumHitsRel)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_atkNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_agc_atkNumHitsAbs)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decayen)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_decayen)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decaysize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_decaysize)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decaywinlength)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_agc_decaywinlength)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decaythreshold)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_decaythreshold)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decayNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_decayNumHitsRel)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_decayNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t index0 = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    dimArray += sizeof(uint8_t);

    memcpy(&index0, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_agc_decayNumHitsAbs)(afeInst, chSel, index0, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_rfdeten)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_rfdeten)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_custRfMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_custRfMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_rfdetstepsize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_rfdetstepsize)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_rfdetThreshold)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_rfdetThreshold)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_rfdetNumhitsmode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_rfdetNumhitsmode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_rfdetnumhits)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_agc_rfdetnumhits)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnaEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_lnaEn)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_extLnaTempModel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_extLnaTempModel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_singleDualBandMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_singleDualBandMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_enBandDet)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_enBandDet)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_tapOffPoint)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_tapOffPoint)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnagain0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_lnagain0)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnaphase0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_lnaphase0)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnagain1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_lnagain1)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnaphase1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_lnaphase1)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_lnaGainMargin)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_lnaGainMargin)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_startTemp)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_startTemp)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_stepTemp)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_stepTemp)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_NumStep)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_NumStep)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_temp_idxB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_temp_idxB0)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_temp_idxB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_temp_idxB1)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pin0sel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_pin0sel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pin1sel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_pin1sel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pin2sel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_pin2sel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pin3sel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_pin3sel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pkDetPinLsbSel)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_pkDetPinLsbSel)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pulseExpansionCount)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_pulseExpansionCount)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_pkDetOnPenultimateLsb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_pkDetOnPenultimateLsb)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_gpioRstEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_gpioRstEnable)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_dsaInit)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_dsaInit)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_dsaStep)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_dsaStep)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_maxInpPinDelay)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_maxInpPinDelay)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_alcEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_alcEn)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_alcMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_alcMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_totalGainRange)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_totalGainRange)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_minAttnAlc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_minAttnAlc)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_useMinAttnAgc)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_useMinAttnAgc)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_fltPtMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_fltPtMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_fltPtFmt)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_fltPtFmt)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_stepSize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_stepSize)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_nBitIndex)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_nBitIndex)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_indexInvert)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_indexInvert)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_indexSwapIQ)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_indexSwapIQ)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_sigBackOff)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_sigBackOff)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_gainChangeIndEn)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_agc_gainChangeIndEn)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_agc_outputDgcPinDelay)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_agc_outputDgcPinDelay)(afeInst, chSel, val);

    return errorStatus;
}

#endif
