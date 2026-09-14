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

#include <stdint.h>
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_agcParamsSetterGetter.h"
#include "tiAfe79_basicFunctions.h"

/**
    @brief Set AFE Parameter enable
    @details Set AFE Parameter enable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_enable)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].enable = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enable
    @details Get AFE Parameter enable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_enable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].enable;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maEnable
    @details Set AFE Parameter maEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maEnable)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maEnable = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maEnable
    @details Get AFE Parameter maEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maEnable;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maNumSample
    @details Set AFE Parameter maNumSample
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maNumSample)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maNumSample = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maNumSample
    @details Get AFE Parameter maNumSample
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maNumSample)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maNumSample;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maWindowCntr
    @details Set AFE Parameter maWindowCntr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maWindowCntr = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maWindowCntr
    @details Get AFE Parameter maWindowCntr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maWindowCntr;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maWindowCntrTh
    @details Set AFE Parameter maWindowCntrTh
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maWindowCntrTh = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maWindowCntrTh
    @details Get AFE Parameter maWindowCntrTh
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maWindowCntrTh;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maThreshB0
    @details Set AFE Parameter maThreshB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maThreshB0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshB0 = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maThreshB0
    @details Get AFE Parameter maThreshB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maThreshB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshB0;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maThreshB1
    @details Set AFE Parameter maThreshB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maThreshB1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshB1 = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maThreshB1
    @details Get AFE Parameter maThreshB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maThreshB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshB1;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter maThreshComb
    @details Set AFE Parameter maThreshComb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_maThreshComb)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshComb = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter maThreshComb
    @details Get AFE Parameter maThreshComb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_maThreshComb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].maThreshComb;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfEnable
    @details Set AFE Parameter hpfEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfEnable)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfEnable = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfEnable
    @details Get AFE Parameter hpfEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfEnable;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfNumSample
    @details Set AFE Parameter hpfNumSample
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfNumSample)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfNumSample = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfNumSample
    @details Get AFE Parameter hpfNumSample
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfNumSample)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfNumSample;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfWindowCntr
    @details Set AFE Parameter hpfWindowCntr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfWindowCntr = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfWindowCntr
    @details Get AFE Parameter hpfWindowCntr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfWindowCntr)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfWindowCntr;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfWindowCntrTh
    @details Set AFE Parameter hpfWindowCntrTh
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfWindowCntrTh = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfWindowCntrTh
    @details Get AFE Parameter hpfWindowCntrTh
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfWindowCntrTh)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfWindowCntrTh;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfThreshB0
    @details Set AFE Parameter hpfThreshB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfThreshB0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshB0 = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfThreshB0
    @details Get AFE Parameter hpfThreshB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfThreshB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshB0;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfThreshB1
    @details Set AFE Parameter hpfThreshB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfThreshB1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshB1 = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfThreshB1
    @details Get AFE Parameter hpfThreshB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfThreshB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshB1;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter hpfThreshComb
    @details Set AFE Parameter hpfThreshComb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_hpfThreshComb)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshComb = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter hpfThreshComb
    @details Get AFE Parameter hpfThreshComb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_hpfThreshComb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].hpfThreshComb;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter multMode
    @details Set AFE Parameter multMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_multMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].multMode = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter multMode
    @details Get AFE Parameter multMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_multMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].multMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rampDownStartVal
    @details Set AFE Parameter rampDownStartVal
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_rampDownStartVal)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].rampDownStartVal = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rampDownStartVal
    @details Get AFE Parameter rampDownStartVal
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_rampDownStartVal)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].rampDownStartVal;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter waitCounter
    @details Set AFE Parameter waitCounter
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_waitCounter)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].waitCounter = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter waitCounter
    @details Get AFE Parameter waitCounter
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_waitCounter)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].waitCounter;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter gainStepSize
    @details Set AFE Parameter gainStepSize
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_gainStepSize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].gainStepSize = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter gainStepSize
    @details Get AFE Parameter gainStepSize
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_gainStepSize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].gainStepSize;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter attnStepSize
    @details Set AFE Parameter attnStepSize
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_attnStepSize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].attnStepSize = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter attnStepSize
    @details Get AFE Parameter attnStepSize
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_attnStepSize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].attnStepSize;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter amplUpdateCycles
    @details Set AFE Parameter amplUpdateCycles
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_amplUpdateCycles)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].amplUpdateCycles = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter amplUpdateCycles
    @details Get AFE Parameter amplUpdateCycles
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_amplUpdateCycles)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].amplUpdateCycles;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter triggerClearToRampUp
    @details Set AFE Parameter triggerClearToRampUp
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_triggerClearToRampUp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].triggerClearToRampUp = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter triggerClearToRampUp
    @details Get AFE Parameter triggerClearToRampUp
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_triggerClearToRampUp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].triggerClearToRampUp;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter triggerToRampDown
    @details Set AFE Parameter triggerToRampDown
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_triggerToRampDown)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].triggerToRampDown = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter triggerToRampDown
    @details Get AFE Parameter triggerToRampDown
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_triggerToRampDown)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].triggerToRampDown;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter detectInWaitState
    @details Set AFE Parameter detectInWaitState
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_detectInWaitState)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].detectInWaitState = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter detectInWaitState
    @details Get AFE Parameter detectInWaitState
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_detectInWaitState)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].detectInWaitState;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rampStickyMode
    @details Set AFE Parameter rampStickyMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_rampStickyMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].rampStickyMode = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rampStickyMode
    @details Get AFE Parameter rampStickyMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_rampStickyMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].rampStickyMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter alarmChannelMask
    @details Set AFE Parameter alarmChannelMask
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_alarmChannelMask)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmChannelMask = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter alarmChannelMask
    @details Get AFE Parameter alarmChannelMask
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_alarmChannelMask)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmChannelMask;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter alarmMask
    @details Set AFE Parameter alarmMask
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_alarmMask)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmMask = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter alarmMask
    @details Get AFE Parameter alarmMask
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_alarmMask)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmMask;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter alarmPinDynamicMode
    @details Set AFE Parameter alarmPinDynamicMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_alarmPinDynamicMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmPinDynamicMode = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter alarmPinDynamicMode
    @details Get AFE Parameter alarmPinDynamicMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_alarmPinDynamicMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmPinDynamicMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter alarmPulseGPIO
    @details Set AFE Parameter alarmPulseGPIO
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chSel Bit-Wise Channel select
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_pap_alarmPulseGPIO)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint32_t val)
{
    AFE79_ID_VALIDITY();
    chSel = AFE79FNP(afeTxChSelReMap)(afeInst, chSel);
    for (uint8_t chNo = 0; chNo < AFE79_NUM_TX_CHANNELS; chNo++)
    {
        if (((chSel >> chNo) & 1) == 1)
        {
            AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmPulseGPIO = val;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter alarmPulseGPIO
    @details Get AFE Parameter alarmPulseGPIO
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo Channel Number
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_pap_alarmPulseGPIO)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    chNo = AFE79FNP(afeTxChNoReMap)(afeInst, chNo);
    *val = AFE79_CURR_SYSPARAM.txPapParams[chNo].alarmPulseGPIO;
    return TI_AFE_RET_EXEC_PASS;
}

#endif
