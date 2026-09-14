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

#include "tiAfe79_papParamsSetterGetter.h"

uint8_t AFE79FNP(wrap_set_pap_enable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_enable)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_maEnable)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maNumSample)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maNumSample)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maWindowCntr)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maWindowCntrTh)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maThreshB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maThreshB0)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maThreshB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maThreshB1)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_maThreshComb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_maThreshComb)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfEnable)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_hpfEnable)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfNumSample)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfNumSample)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfWindowCntr)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfWindowCntrTh)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfThreshB0)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfThreshB0)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfThreshB1)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfThreshB1)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_hpfThreshComb)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_hpfThreshComb)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_multMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_multMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_rampDownStartVal)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_rampDownStartVal)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_waitCounter)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_waitCounter)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_gainStepSize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_gainStepSize)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_attnStepSize)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_attnStepSize)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_amplUpdateCycles)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_amplUpdateCycles)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_triggerClearToRampUp)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_triggerClearToRampUp)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_triggerToRampDown)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint16_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint16_t));
    errorStatus = AFE79FNP(set_pap_triggerToRampDown)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_detectInWaitState)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_detectInWaitState)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_rampStickyMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_rampStickyMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_alarmChannelMask)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_alarmChannelMask)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_alarmMask)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_alarmMask)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_alarmPinDynamicMode)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint8_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint8_t));
    errorStatus = AFE79FNP(set_pap_alarmPinDynamicMode)(afeInst, chSel, val);

    return errorStatus;
}

uint8_t AFE79FNP(wrap_set_pap_alarmPulseGPIO)(AFE79_INST_TYPE afeInst, uint8_t *dimArray, uint8_t *valByteArray)
{

    uint8_t errorStatus = 0;
    AFE79_PARAMS_VALID(dimArray != NULL);
    AFE79_PARAMS_VALID(valByteArray != NULL);

    uint8_t chSel = 0;
    uint32_t val = 0;

    memcpy(&chSel, dimArray, sizeof(uint8_t));
    memcpy(&val, valByteArray, sizeof(uint32_t));
    errorStatus = AFE79FNP(set_pap_alarmPulseGPIO)(afeInst, chSel, val);

    return errorStatus;
}
#endif
