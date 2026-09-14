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

#include <stdint.h>
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_agcParamsSetterGetter.h"
#include "tiAfe79_basicFunctions.h"

/**
    @brief Set AFE Parameter chipId
    @details Set AFE Parameter chipId
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_chipId)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.chipId = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter chipId
    @details Get AFE Parameter chipId
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_chipId)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.chipId;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter chipVersion
    @details Set AFE Parameter chipVersion
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.chipVersion = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter chipVersion
    @details Get AFE Parameter chipVersion
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_chipVersion)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.chipVersion;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter X
    @details Set AFE Parameter X
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_X)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.X = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter X
    @details Get AFE Parameter X
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_X)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.X;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter FRef
    @details Set AFE Parameter FRef
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_FRef)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.FRef = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter FRef
    @details Get AFE Parameter FRef
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_FRef)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.FRef;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter FadcRx
    @details Set AFE Parameter FadcRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_FadcRx)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.FadcRx = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter FadcRx
    @details Get AFE Parameter FadcRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_FadcRx)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.FadcRx;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter FadcFb
    @details Set AFE Parameter FadcFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_FadcFb)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.FadcFb = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter FadcFb
    @details Get AFE Parameter FadcFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_FadcFb)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.FadcFb;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter Fdac
    @details Set AFE Parameter Fdac
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_Fdac)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.Fdac = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter Fdac
    @details Get AFE Parameter Fdac
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_Fdac)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.Fdac;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxEnable
    @details Set AFE Parameter rxEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    AFE79_CURR_SYSPARAM.rxEnable[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxEnable
    @details Get AFE Parameter rxEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    *val = AFE79_CURR_SYSPARAM.rxEnable[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbEnable
    @details Set AFE Parameter fbEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    AFE79_CURR_SYSPARAM.fbEnable[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbEnable
    @details Get AFE Parameter fbEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    *val = AFE79_CURR_SYSPARAM.fbEnable[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txEnable
    @details Set AFE Parameter txEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    AFE79_CURR_SYSPARAM.txEnable[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txEnable
    @details Get AFE Parameter txEnable
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    *val = AFE79_CURR_SYSPARAM.txEnable[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter RRFMode
    @details Set AFE Parameter RRFMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.RRFMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter RRFMode
    @details Get AFE Parameter RRFMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_RRFMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.RRFMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter adcSelect0
    @details Set AFE Parameter adcSelect0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 3);
    AFE79_CURR_SYSPARAM.adcSelect0[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter adcSelect0
    @details Get AFE Parameter adcSelect0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcSelect0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 3);
    *val = AFE79_CURR_SYSPARAM.adcSelect0[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter adcSelect1
    @details Set AFE Parameter adcSelect1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 3);
    AFE79_CURR_SYSPARAM.adcSelect1[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter adcSelect1
    @details Get AFE Parameter adcSelect1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcSelect1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 3);
    *val = AFE79_CURR_SYSPARAM.adcSelect1[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter modeTdd
    @details Set AFE Parameter modeTdd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.modeTdd = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter modeTdd
    @details Get AFE Parameter modeTdd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_modeTdd)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.modeTdd;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter externalClockRx
    @details Set AFE Parameter externalClockRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.externalClockRx = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter externalClockRx
    @details Get AFE Parameter externalClockRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_externalClockRx)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.externalClockRx;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter externalClockTx
    @details Set AFE Parameter externalClockTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.externalClockTx = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter externalClockTx
    @details Get AFE Parameter externalClockTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_externalClockTx)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.externalClockTx;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter useSpiSysref
    @details Set AFE Parameter useSpiSysref
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.useSpiSysref = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter useSpiSysref
    @details Get AFE Parameter useSpiSysref
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_useSpiSysref)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.useSpiSysref;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter continuousSysref
    @details Set AFE Parameter continuousSysref
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.continuousSysref = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter continuousSysref
    @details Get AFE Parameter continuousSysref
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_continuousSysref)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.continuousSysref;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter sysrefTermination
    @details Set AFE Parameter sysrefTermination
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.sysrefTermination = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter sysrefTermination
    @details Get AFE Parameter sysrefTermination
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_sysrefTermination)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.sysrefTermination;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter spiMode
    @details Set AFE Parameter spiMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_spiMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.spiMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter spiMode
    @details Get AFE Parameter spiMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_spiMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.spiMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ncoFreqMode
    @details Set AFE Parameter ncoFreqMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.ncoFreqMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ncoFreqMode
    @details Get AFE Parameter ncoFreqMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoFreqMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.ncoFreqMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter halfRateModeRx
    @details Set AFE Parameter halfRateModeRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.halfRateModeRx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter halfRateModeRx
    @details Get AFE Parameter halfRateModeRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.halfRateModeRx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter halfRateModeFb
    @details Set AFE Parameter halfRateModeFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.halfRateModeFb[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter halfRateModeFb
    @details Get AFE Parameter halfRateModeFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.halfRateModeFb[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter halfRateModeTx
    @details Set AFE Parameter halfRateModeTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.halfRateModeTx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter halfRateModeTx
    @details Get AFE Parameter halfRateModeTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_halfRateModeTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.halfRateModeTx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter enableAdcAveragingMode
    @details Set AFE Parameter enableAdcAveragingMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.enableAdcAveragingMode[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enableAdcAveragingMode
    @details Get AFE Parameter enableAdcAveragingMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableAdcAveragingMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.enableAdcAveragingMode[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter combineDucMode
    @details Set AFE Parameter combineDucMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.combineDucMode[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter combineDucMode
    @details Get AFE Parameter combineDucMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_combineDucMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.combineDucMode[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter enableTxFbLoopbackLowLatencyMode
    @details Set AFE Parameter enableTxFbLoopbackLowLatencyMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.enableTxFbLoopbackLowLatencyMode[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enableTxFbLoopbackLowLatencyMode
    @details Get AFE Parameter enableTxFbLoopbackLowLatencyMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableTxFbLoopbackLowLatencyMode)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.enableTxFbLoopbackLowLatencyMode[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ddcFactorRx
    @details Set AFE Parameter ddcFactorRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.ddcFactorRx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ddcFactorRx
    @details Get AFE Parameter ddcFactorRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ddcFactorRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.ddcFactorRx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxNco
    @details Set AFE Parameter rxNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param index2 index2 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    AFE79_PARAMS_VALID(index2 < 2);
    AFE79_CURR_SYSPARAM.rxNco[index0][index1][index2] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxNco
    @details Get AFE Parameter rxNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param index2 index2 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    AFE79_PARAMS_VALID(index2 < 2);
    *val = AFE79_CURR_SYSPARAM.rxNco[index0][index1][index2];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numBandsRx
    @details Set AFE Parameter numBandsRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.numBandsRx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numBandsRx
    @details Get AFE Parameter numBandsRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numBandsRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.numBandsRx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numRxNCOB0
    @details Set AFE Parameter numRxNCOB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    AFE79_CURR_SYSPARAM.numRxNCOB0[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numRxNCOB0
    @details Get AFE Parameter numRxNCOB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numRxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    *val = AFE79_CURR_SYSPARAM.numRxNCOB0[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numRxNCOB1
    @details Set AFE Parameter numRxNCOB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    AFE79_CURR_SYSPARAM.numRxNCOB1[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numRxNCOB1
    @details Get AFE Parameter numRxNCOB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numRxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 4);
    *val = AFE79_CURR_SYSPARAM.numRxNCOB1[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ncoRxMode
    @details Set AFE Parameter ncoRxMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    AFE79_CURR_SYSPARAM.ncoRxMode[topNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ncoRxMode
    @details Get AFE Parameter ncoRxMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoRxMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    *val = AFE79_CURR_SYSPARAM.ncoRxMode[topNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter broadcastRxNcoSel
    @details Set AFE Parameter broadcastRxNcoSel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.broadcastRxNcoSel = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter broadcastRxNcoSel
    @details Get AFE Parameter broadcastRxNcoSel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_broadcastRxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.broadcastRxNcoSel;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ddcFactorFb
    @details Set AFE Parameter ddcFactorFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.ddcFactorFb[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ddcFactorFb
    @details Get AFE Parameter ddcFactorFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ddcFactorFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.ddcFactorFb[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbNco
    @details Set AFE Parameter fbNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    AFE79_CURR_SYSPARAM.fbNco[index0][index1] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbNco
    @details Get AFE Parameter fbNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    *val = AFE79_CURR_SYSPARAM.fbNco[index0][index1];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numFbNCO
    @details Set AFE Parameter numFbNCO
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    AFE79_CURR_SYSPARAM.numFbNCO[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numFbNCO
    @details Get AFE Parameter numFbNCO
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numFbNCO)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    *val = AFE79_CURR_SYSPARAM.numFbNCO[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ncoFbMode
    @details Set AFE Parameter ncoFbMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.ncoFbMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ncoFbMode
    @details Get AFE Parameter ncoFbMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoFbMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.ncoFbMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ducFactorTx
    @details Set AFE Parameter ducFactorTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.ducFactorTx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ducFactorTx
    @details Get AFE Parameter ducFactorTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ducFactorTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.ducFactorTx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txNco
    @details Set AFE Parameter txNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param index2 index2 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    AFE79_PARAMS_VALID(index2 < 2);
    AFE79_CURR_SYSPARAM.txNco[index0][index1][index2] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txNco
    @details Get AFE Parameter txNco
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param index1 index1 Index
    @param index2 index2 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txNco)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t index1, uint8_t index2, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_PARAMS_VALID(index1 < 4);
    AFE79_PARAMS_VALID(index2 < 2);
    *val = AFE79_CURR_SYSPARAM.txNco[index0][index1][index2];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numBandsTx
    @details Set AFE Parameter numBandsTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.numBandsTx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numBandsTx
    @details Get AFE Parameter numBandsTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numBandsTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.numBandsTx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numTxNCOB0
    @details Set AFE Parameter numTxNCOB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.numTxNCOB0[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numTxNCOB0
    @details Get AFE Parameter numTxNCOB0
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numTxNCOB0)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.numTxNCOB0[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter numTxNCOB1
    @details Set AFE Parameter numTxNCOB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.numTxNCOB1[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter numTxNCOB1
    @details Get AFE Parameter numTxNCOB1
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_numTxNCOB1)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.numTxNCOB1[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter ncoTxMode
    @details Set AFE Parameter ncoTxMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param bandNo bandNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t bandNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(bandNo < 2);
    AFE79_CURR_SYSPARAM.ncoTxMode[bandNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter ncoTxMode
    @details Get AFE Parameter ncoTxMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param bandNo bandNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_ncoTxMode)(AFE79_INST_TYPE afeInst, uint8_t bandNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(bandNo < 2);
    *val = AFE79_CURR_SYSPARAM.ncoTxMode[bandNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter broadcastTxNcoSel
    @details Set AFE Parameter broadcastTxNcoSel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.broadcastTxNcoSel = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter broadcastTxNcoSel
    @details Get AFE Parameter broadcastTxNcoSel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_broadcastTxNcoSel)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.broadcastTxNcoSel;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter enableDacInterleavedMode
    @details Set AFE Parameter enableDacInterleavedMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.enableDacInterleavedMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enableDacInterleavedMode
    @details Get AFE Parameter enableDacInterleavedMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableDacInterleavedMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.enableDacInterleavedMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdLoopbackEn
    @details Set AFE Parameter jesdLoopbackEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.jesdLoopbackEn = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdLoopbackEn
    @details Get AFE Parameter jesdLoopbackEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdLoopbackEn)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.jesdLoopbackEn;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter syncLoopBack
    @details Set AFE Parameter syncLoopBack
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.syncLoopBack = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter syncLoopBack
    @details Get AFE Parameter syncLoopBack
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_syncLoopBack)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.syncLoopBack;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdABLvdsSync
    @details Set AFE Parameter jesdABLvdsSync
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.jesdABLvdsSync = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdABLvdsSync
    @details Get AFE Parameter jesdABLvdsSync
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdABLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.jesdABLvdsSync;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdCDLvdsSync
    @details Set AFE Parameter jesdCDLvdsSync
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.jesdCDLvdsSync = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdCDLvdsSync
    @details Get AFE Parameter jesdCDLvdsSync
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdCDLvdsSync)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.jesdCDLvdsSync;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter executeLinkUpSequenceSeparately
    @details Set AFE Parameter executeLinkUpSequenceSeparately
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.executeLinkUpSequenceSeparately = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter executeLinkUpSequenceSeparately
    @details Get AFE Parameter executeLinkUpSequenceSeparately
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_executeLinkUpSequenceSeparately)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.executeLinkUpSequenceSeparately;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_L
    @details Set AFE Parameter LMFSHdRx_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_L[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_L
    @details Get AFE Parameter LMFSHdRx_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_L[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_M
    @details Set AFE Parameter LMFSHdRx_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_M[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_M
    @details Get AFE Parameter LMFSHdRx_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_M[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_F
    @details Set AFE Parameter LMFSHdRx_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_F[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_F
    @details Get AFE Parameter LMFSHdRx_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_F[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_S
    @details Set AFE Parameter LMFSHdRx_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_S[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_S
    @details Get AFE Parameter LMFSHdRx_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_S[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_Hd
    @details Set AFE Parameter LMFSHdRx_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_Hd[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_Hd
    @details Get AFE Parameter LMFSHdRx_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_Hd[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdRx_Misc
    @details Set AFE Parameter LMFSHdRx_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdRx_Misc[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdRx_Misc
    @details Get AFE Parameter LMFSHdRx_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdRx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdRx_Misc[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_L
    @details Set AFE Parameter LMFSHdFb_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_L[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_L
    @details Get AFE Parameter LMFSHdFb_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_L[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_M
    @details Set AFE Parameter LMFSHdFb_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_M[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_M
    @details Get AFE Parameter LMFSHdFb_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_M[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_F
    @details Set AFE Parameter LMFSHdFb_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_F[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_F
    @details Get AFE Parameter LMFSHdFb_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_F[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_S
    @details Set AFE Parameter LMFSHdFb_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_S[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_S
    @details Get AFE Parameter LMFSHdFb_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_S[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_Hd
    @details Set AFE Parameter LMFSHdFb_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_Hd[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_Hd
    @details Get AFE Parameter LMFSHdFb_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_Hd[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdFb_Misc
    @details Set AFE Parameter LMFSHdFb_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.LMFSHdFb_Misc[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdFb_Misc
    @details Get AFE Parameter LMFSHdFb_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdFb_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.LMFSHdFb_Misc[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdSystemMode
    @details Set AFE Parameter jesdSystemMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    AFE79_CURR_SYSPARAM.jesdSystemMode[topNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdSystemMode
    @details Get AFE Parameter jesdSystemMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdSystemMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    *val = AFE79_CURR_SYSPARAM.jesdSystemMode[topNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdTxProtocol
    @details Set AFE Parameter jesdTxProtocol
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    AFE79_CURR_SYSPARAM.jesdTxProtocol[topNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdTxProtocol
    @details Get AFE Parameter jesdTxProtocol
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    *val = AFE79_CURR_SYSPARAM.jesdTxProtocol[topNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxJesdTxScr
    @details Set AFE Parameter rxJesdTxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.rxJesdTxScr[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxJesdTxScr
    @details Get AFE Parameter rxJesdTxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.rxJesdTxScr[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbJesdTxScr
    @details Set AFE Parameter fbJesdTxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.fbJesdTxScr[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbJesdTxScr
    @details Get AFE Parameter fbJesdTxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.fbJesdTxScr[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxJesdTxK
    @details Set AFE Parameter rxJesdTxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.rxJesdTxK[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxJesdTxK
    @details Get AFE Parameter rxJesdTxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.rxJesdTxK[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbJesdTxK
    @details Set AFE Parameter fbJesdTxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.fbJesdTxK[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbJesdTxK
    @details Get AFE Parameter fbJesdTxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.fbJesdTxK[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxJesdTxSyncMux
    @details Set AFE Parameter rxJesdTxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.rxJesdTxSyncMux[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxJesdTxSyncMux
    @details Get AFE Parameter rxJesdTxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.rxJesdTxSyncMux[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbJesdTxSyncMux
    @details Set AFE Parameter fbJesdTxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    AFE79_CURR_SYSPARAM.fbJesdTxSyncMux[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbJesdTxSyncMux
    @details Get AFE Parameter fbJesdTxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbJesdTxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 2);
    *val = AFE79_CURR_SYSPARAM.fbJesdTxSyncMux[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter setIlaParams
    @details Set AFE Parameter setIlaParams
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.setIlaParams = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter setIlaParams
    @details Get AFE Parameter setIlaParams
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_setIlaParams)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.setIlaParams;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdTxIlaM
    @details Set AFE Parameter jesdTxIlaM
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 6);
    AFE79_CURR_SYSPARAM.jesdTxIlaM[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdTxIlaM
    @details Get AFE Parameter jesdTxIlaM
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaM)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 6);
    *val = AFE79_CURR_SYSPARAM.jesdTxIlaM[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdTxIlaL
    @details Set AFE Parameter jesdTxIlaL
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 6);
    AFE79_CURR_SYSPARAM.jesdTxIlaL[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdTxIlaL
    @details Get AFE Parameter jesdTxIlaL
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaL)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 6);
    *val = AFE79_CURR_SYSPARAM.jesdTxIlaL[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdTxIlaLid
    @details Set AFE Parameter jesdTxIlaLid
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.jesdTxIlaLid[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdTxIlaLid
    @details Get AFE Parameter jesdTxIlaLid
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxIlaLid)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.jesdTxIlaLid[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesTxLanePolarity
    @details Set AFE Parameter serdesTxLanePolarity
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.serdesTxLanePolarity[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesTxLanePolarity
    @details Get AFE Parameter serdesTxLanePolarity
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.serdesTxLanePolarity[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdTxLaneMux
    @details Set AFE Parameter jesdTxLaneMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.jesdTxLaneMux[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdTxLaneMux
    @details Get AFE Parameter jesdTxLaneMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdTxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.jesdTxLaneMux[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter adcDataMuxEn
    @details Set AFE Parameter adcDataMuxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.adcDataMuxEn = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter adcDataMuxEn
    @details Get AFE Parameter adcDataMuxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_adcDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.adcDataMuxEn;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxDataMux
    @details Set AFE Parameter rxDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 8);
    AFE79_CURR_SYSPARAM.rxDataMux[converterNumber] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxDataMux
    @details Get AFE Parameter rxDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 8);
    *val = AFE79_CURR_SYSPARAM.rxDataMux[converterNumber];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbDataMux
    @details Set AFE Parameter fbDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 2);
    AFE79_CURR_SYSPARAM.fbDataMux[converterNumber] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbDataMux
    @details Get AFE Parameter fbDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 2);
    *val = AFE79_CURR_SYSPARAM.fbDataMux[converterNumber];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdSendZeroesInTddOff
    @details Set AFE Parameter jesdSendZeroesInTddOff
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.jesdSendZeroesInTddOff = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdSendZeroesInTddOff
    @details Get AFE Parameter jesdSendZeroesInTddOff
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdSendZeroesInTddOff)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.jesdSendZeroesInTddOff;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesTxPreCursor
    @details Set AFE Parameter serdesTxPreCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    AFE79_CURR_SYSPARAM.serdesTxPreCursor[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesTxPreCursor
    @details Get AFE Parameter serdesTxPreCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxPreCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    *val = AFE79_CURR_SYSPARAM.serdesTxPreCursor[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesTxPostCursor
    @details Set AFE Parameter serdesTxPostCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    AFE79_CURR_SYSPARAM.serdesTxPostCursor[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesTxPostCursor
    @details Get AFE Parameter serdesTxPostCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxPostCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    *val = AFE79_CURR_SYSPARAM.serdesTxPostCursor[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesTxMainCursor
    @details Set AFE Parameter serdesTxMainCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    AFE79_CURR_SYSPARAM.serdesTxMainCursor[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesTxMainCursor
    @details Get AFE Parameter serdesTxMainCursor
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxMainCursor)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    *val = AFE79_CURR_SYSPARAM.serdesTxMainCursor[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_L
    @details Set AFE Parameter LMFSHdTx_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_L[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_L
    @details Get AFE Parameter LMFSHdTx_L
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_L)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_L[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_M
    @details Set AFE Parameter LMFSHdTx_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_M[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_M
    @details Get AFE Parameter LMFSHdTx_M
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_M)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_M[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_F
    @details Set AFE Parameter LMFSHdTx_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_F[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_F
    @details Get AFE Parameter LMFSHdTx_F
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_F)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_F[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_S
    @details Set AFE Parameter LMFSHdTx_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_S[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_S
    @details Get AFE Parameter LMFSHdTx_S
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_S)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_S[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_Hd
    @details Set AFE Parameter LMFSHdTx_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_Hd[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_Hd
    @details Get AFE Parameter LMFSHdTx_Hd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_Hd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_Hd[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter LMFSHdTx_Misc
    @details Set AFE Parameter LMFSHdTx_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.LMFSHdTx_Misc[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter LMFSHdTx_Misc
    @details Get AFE Parameter LMFSHdTx_Misc
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_LMFSHdTx_Misc)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.LMFSHdTx_Misc[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxSyncMux
    @details Set AFE Parameter jesdRxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.jesdRxSyncMux[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxSyncMux
    @details Get AFE Parameter jesdRxSyncMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxSyncMux)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.jesdRxSyncMux[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxProtocol
    @details Set AFE Parameter jesdRxProtocol
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    AFE79_CURR_SYSPARAM.jesdRxProtocol[topNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxProtocol
    @details Get AFE Parameter jesdRxProtocol
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param topNo topNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxProtocol)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < 2);
    *val = AFE79_CURR_SYSPARAM.jesdRxProtocol[topNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesRxLanePolarity
    @details Set AFE Parameter serdesRxLanePolarity
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.serdesRxLanePolarity[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesRxLanePolarity
    @details Get AFE Parameter serdesRxLanePolarity
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesRxLanePolarity)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.serdesRxLanePolarity[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxLaneMux
    @details Set AFE Parameter jesdRxLaneMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.jesdRxLaneMux[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxLaneMux
    @details Get AFE Parameter jesdRxLaneMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxLaneMux)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.jesdRxLaneMux[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxRbd
    @details Set AFE Parameter jesdRxRbd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.jesdRxRbd[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxRbd
    @details Get AFE Parameter jesdRxRbd
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxRbd)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.jesdRxRbd[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxScr
    @details Set AFE Parameter jesdRxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.jesdRxScr[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxScr
    @details Get AFE Parameter jesdRxScr
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxScr)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.jesdRxScr[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxK
    @details Set AFE Parameter jesdRxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.jesdRxK[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxK
    @details Get AFE Parameter jesdRxK
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxK)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.jesdRxK[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter jesdRxInitLmfcCounter
    @details Set AFE Parameter jesdRxInitLmfcCounter
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    AFE79_CURR_SYSPARAM.jesdRxInitLmfcCounter[mapperNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter jesdRxInitLmfcCounter
    @details Get AFE Parameter jesdRxInitLmfcCounter
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param mapperNo mapperNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_jesdRxInitLmfcCounter)(AFE79_INST_TYPE afeInst, uint8_t mapperNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(mapperNo < 4);
    *val = AFE79_CURR_SYSPARAM.jesdRxInitLmfcCounter[mapperNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter dacDataMuxEn
    @details Set AFE Parameter dacDataMuxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.dacDataMuxEn = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter dacDataMuxEn
    @details Get AFE Parameter dacDataMuxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_dacDataMuxEn)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.dacDataMuxEn;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txDataMux
    @details Set AFE Parameter txDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 8);
    AFE79_CURR_SYSPARAM.txDataMux[converterNumber] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txDataMux
    @details Get AFE Parameter txDataMux
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param converterNumber converterNumber Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txDataMux)(AFE79_INST_TYPE afeInst, uint8_t converterNumber, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(converterNumber < 8);
    *val = AFE79_CURR_SYSPARAM.txDataMux[converterNumber];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesManualCTLEEn
    @details Set AFE Parameter serdesManualCTLEEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.serdesManualCTLEEn = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesManualCTLEEn
    @details Get AFE Parameter serdesManualCTLEEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesManualCTLEEn)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.serdesManualCTLEEn;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesManualCTLE
    @details Set AFE Parameter serdesManualCTLE
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    AFE79_CURR_SYSPARAM.serdesManualCTLE[laneNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesManualCTLE
    @details Get AFE Parameter serdesManualCTLE
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param laneNo laneNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesManualCTLE)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < 8);
    *val = AFE79_CURR_SYSPARAM.serdesManualCTLE[laneNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter defaultRxDsa
    @details Set AFE Parameter defaultRxDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.defaultRxDsa[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter defaultRxDsa
    @details Get AFE Parameter defaultRxDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultRxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.defaultRxDsa[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter defaultFbDsa
    @details Set AFE Parameter defaultFbDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSPARAM.defaultFbDsa[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter defaultFbDsa
    @details Get AFE Parameter defaultFbDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultFbDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSPARAM.defaultFbDsa[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter defaultTxDsa
    @details Set AFE Parameter defaultTxDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.defaultTxDsa[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter defaultTxDsa
    @details Get AFE Parameter defaultTxDsa
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_defaultTxDsa)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.defaultTxDsa[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter enableRxDsaCalibration
    @details Set AFE Parameter enableRxDsaCalibration
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.enableRxDsaCalibration = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enableRxDsaCalibration
    @details Get AFE Parameter enableRxDsaCalibration
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableRxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.enableRxDsaCalibration;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxDsaGainRange
    @details Set AFE Parameter rxDsaGainRange
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param startStop startStop Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(startStop < 2);
    AFE79_CURR_SYSPARAM.rxDsaGainRange[startStop] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxDsaGainRange
    @details Get AFE Parameter rxDsaGainRange
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param startStop startStop Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(startStop < 2);
    *val = AFE79_CURR_SYSPARAM.rxDsaGainRange[startStop];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter enableTxDsaCalibration
    @details Set AFE Parameter enableTxDsaCalibration
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.enableTxDsaCalibration = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter enableTxDsaCalibration
    @details Get AFE Parameter enableTxDsaCalibration
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_enableTxDsaCalibration)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.enableTxDsaCalibration;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txDsaGainRange
    @details Set AFE Parameter txDsaGainRange
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param startStop startStop Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(startStop < 2);
    AFE79_CURR_SYSPARAM.txDsaGainRange[startStop] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txDsaGainRange
    @details Get AFE Parameter txDsaGainRange
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param startStop startStop Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txDsaGainRange)(AFE79_INST_TYPE afeInst, uint8_t startStop, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(startStop < 2);
    *val = AFE79_CURR_SYSPARAM.txDsaGainRange[startStop];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter reliabilityDetectorDecayMode
    @details Set AFE Parameter reliabilityDetectorDecayMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.reliabilityDetectorDecayMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter reliabilityDetectorDecayMode
    @details Get AFE Parameter reliabilityDetectorDecayMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_reliabilityDetectorDecayMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.reliabilityDetectorDecayMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbDsaPerTxEn
    @details Set AFE Parameter fbDsaPerTxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.fbDsaPerTxEn = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbDsaPerTxEn
    @details Get AFE Parameter fbDsaPerTxEn
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.fbDsaPerTxEn;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbDsaPerTx
    @details Set AFE Parameter fbDsaPerTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSPARAM.fbDsaPerTx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbDsaPerTx
    @details Get AFE Parameter fbDsaPerTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSPARAM.fbDsaPerTx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txToFbMode
    @details Set AFE Parameter txToFbMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.txToFbMode = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txToFbMode
    @details Get AFE Parameter txToFbMode
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txToFbMode)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.txToFbMode;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter spiInUseForPllAccess
    @details Set AFE Parameter spiInUseForPllAccess
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_SYSPARAM.spiInUseForPllAccess = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter spiInUseForPllAccess
    @details Get AFE Parameter spiInUseForPllAccess
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_spiInUseForPllAccess)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_SYSPARAM.spiInUseForPllAccess;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter laneRateRx
    @details Set AFE Parameter laneRateRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSSTATUS.laneRateRx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter laneRateRx
    @details Get AFE Parameter laneRateRx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateRx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSSTATUS.laneRateRx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter laneRateFb
    @details Set AFE Parameter laneRateFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    AFE79_CURR_SYSSTATUS.laneRateFb[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter laneRateFb
    @details Get AFE Parameter laneRateFb
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateFb)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 2);
    *val = AFE79_CURR_SYSSTATUS.laneRateFb[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter laneRateTx
    @details Set AFE Parameter laneRateTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_laneRateTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    AFE79_CURR_SYSSTATUS.laneRateTx[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter laneRateTx
    @details Get AFE Parameter laneRateTx
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_laneRateTx)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 4);
    *val = AFE79_CURR_SYSSTATUS.laneRateTx[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesTxLaneRate
    @details Set AFE Parameter serdesTxLaneRate
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesTxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    AFE79_CURR_SYSSTATUS.serdesTxLaneRate[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesTxLaneRate
    @details Get AFE Parameter serdesTxLaneRate
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesTxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    *val = AFE79_CURR_SYSSTATUS.serdesTxLaneRate[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter serdesRxLaneRate
    @details Set AFE Parameter serdesRxLaneRate
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_serdesRxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    AFE79_CURR_SYSSTATUS.serdesRxLaneRate[index0] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter serdesRxLaneRate
    @details Get AFE Parameter serdesRxLaneRate
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param index0 index0 Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_serdesRxLaneRate)(AFE79_INST_TYPE afeInst, uint8_t index0, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(index0 < 8);
    *val = AFE79_CURR_SYSSTATUS.serdesRxLaneRate[index0];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter afeId
    @details Set AFE Parameter afeId
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_afeId)(AFE79_INST_TYPE afeInst, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_CURR_ID = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter afeId
    @details Get AFE Parameter afeId
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_afeId)(AFE79_INST_TYPE afeInst, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE79_CURR_ID;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter rxChannelRemap
    @details Set AFE Parameter rxChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_rxChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 8);
    AFE79_CURR_RX_CH_REMAP[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter rxChannelRemap
    @details Get AFE Parameter rxChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_rxChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 8);
    *val = AFE79_CURR_RX_CH_REMAP[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter txChannelRemap
    @details Set AFE Parameter txChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_txChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 8);
    AFE79_CURR_TX_CH_REMAP[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter txChannelRemap
    @details Get AFE Parameter txChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_txChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 8);
    *val = AFE79_CURR_TX_CH_REMAP[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter fbChannelRemap
    @details Set AFE Parameter fbChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_fbChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    AFE79_CURR_FB_CH_REMAP[chNo] = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter fbChannelRemap
    @details Get AFE Parameter fbChannelRemap
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param chNo chNo Index
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_fbChannelRemap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < 2);
    *val = AFE79_CURR_FB_CH_REMAP[chNo];
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set AFE Parameter logLevel
    @details Set AFE Parameter logLevel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value to be set
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_logLevel)(AFE79_INST_TYPE afeInst, uint32_t val)
{
    AFE79_ID_VALIDITY();
    AFE_CURRENT_LOG_LEVEL = val;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get AFE Parameter logLevel
    @details Get AFE Parameter logLevel
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param val Value Pointer return
    @return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_logLevel)(AFE79_INST_TYPE afeInst, uint32_t *val)
{
    AFE79_ID_VALIDITY();
    *val = AFE_CURRENT_LOG_LEVEL;
    return TI_AFE_RET_EXEC_PASS;
}

