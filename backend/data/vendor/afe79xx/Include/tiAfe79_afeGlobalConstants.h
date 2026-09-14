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

#ifndef tiAfe79_AFE_GLOBAL_CONSTANTS_H_
#define tiAfe79_AFE_GLOBAL_CONSTANTS_H_
/** @file tiAfe79_afeGlobalConstants.h
 * 	@brief	This file contains AFE Device Info structure definition.<br>
 *       <b> Version 1.1.0:</b> <br>
 *           1. Added Define to access AGC and PAP.
 */
#include <stdint.h>

#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeParameters.h"

typedef struct afe79InstDeviceInfoDef
{
    uint8_t afeId;
    /// This structure contains the parameters derived from the afeSystemParams.
    afe79SystemStatusStruct afeSystemStatus;

    /// This structure contains the System Parameters used in the intialization script of the AFE.
    afe79SystemParamsStruct afeSystemParams;
    /** This captures the mapping between the AFE RX channel number to the system channel number.
     * In the array, the index of the array is the System channel number and value there is the corresponding AFE channel number.
     * That is, if the system channel number 0 maps to AFE channel number 4, the first element of the array should be 4.
     * */
    uint8_t rxChannelRemap[4]; //[chNo]
    /** This captures the mapping between the AFE TX channel number to the system channel number.
     * In the array, the index of the array is the System channel number and value there is the corresponding AFE channel number.
     * That is, if the system channel number 0 maps to AFE channel number 4, the first element of the array should be 4.
     * */
    uint8_t txChannelRemap[4]; //[chNo]
    /** This captures the mapping between the AFE FB channel number to the system channel number.
     * In the array, the index of the array is the System channel number and value there is the corresponding AFE channel number.
     * That is, if the system channel number 0 maps to AFE channel number 4, the first element of the array should be 4.
     * */
    uint8_t fbChannelRemap[2]; //[chNo]

    uint32_t logLevel;

    void *halConfig;
} afe79InstDeviceInfo;

#ifndef USE_AFE79_LIB_FORMAT_2
#define AFE79_CURR_INST_STRUCT afeInst
#define AFE79_INST_TYPE afe79InstDeviceInfo *

#define AFE79_CURR_ID AFE79_CURR_INST_STRUCT->afeId
#define AFE79_CURR_SYSPARAM AFE79_CURR_INST_STRUCT->afeSystemParams
#define AFE79_CURR_SYSSTATUS AFE79_CURR_INST_STRUCT->afeSystemStatus

#define AFE_CURRENT_LOG_LEVEL AFE79_CURR_INST_STRUCT->logLevel

/// Way to access the RX Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_RX_CHANNELS.
#define AFE79_CURR_RX_CH_REMAP AFE79_CURR_INST_STRUCT->rxChannelRemap
/// Way to access the TX Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_TX_CHANNELS.
#define AFE79_CURR_TX_CH_REMAP AFE79_CURR_INST_STRUCT->txChannelRemap
/// Way to access the FB Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_TX_CHANNELS.
#define AFE79_CURR_FB_CH_REMAP AFE79_CURR_INST_STRUCT->fbChannelRemap

#endif
#ifdef USE_AFE79_LIB_FORMAT_2
/// Pointer for the array of AFE afe79InstDeviceInfo.
extern afe79InstDeviceInfo *tiAfe79DeviceInfo_t;
#define AFE79_CURR_INST_STRUCT tiAfe79DeviceInfo_t[afeInst]
#define AFE79_INST_TYPE uint8_t

#define AFE79_CURR_ID AFE79_CURR_INST_STRUCT.afeId
#define AFE79_CURR_SYSPARAM AFE79_CURR_INST_STRUCT.afeSystemParams
#define AFE79_CURR_SYSSTATUS AFE79_CURR_INST_STRUCT.afeSystemStatus

#define AFE_CURRENT_LOG_LEVEL AFE79_CURR_INST_STRUCT.logLevel

/// Way to access the RX Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_RX_CHANNELS.
#define AFE79_CURR_RX_CH_REMAP AFE79_CURR_INST_STRUCT.rxChannelRemap
/// Way to access the TX Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_TX_CHANNELS.
#define AFE79_CURR_TX_CH_REMAP AFE79_CURR_INST_STRUCT.txChannelRemap
/// Way to access the FB Channel Remap for the current AFE. This should be an array of uint8_t of size AFE79_NUM_TX_CHANNELS.
#define AFE79_CURR_FB_CH_REMAP AFE79_CURR_INST_STRUCT.fbChannelRemap
#endif

#define AFE79_CURR_AGCPARAM_CH AFE79_CURR_SYSPARAM.rxAgcParams[chNo]
#define AFE79_CURR_PAPPARAM_CH AFE79_CURR_SYSPARAM.txPapParams[chNo]
#ifndef TI_AFE79xx_FUNC_NAME_PREFIX
/// This can be used to prefix the function names to able to differentiate across multiple devices controlled by the AFE.
// #define TI_AFE79xx_FUNC_NAME_PREFIX(funcName) (funcName)
#define TI_AFE79xx_FUNC_NAME_PREFIX(funcName) (ti_afe79_##funcName)
#endif

/// This can be used to prefix the function names to able to differentiate across multiple devices controlled by the AFE.
#define AFE79FNP TI_AFE79xx_FUNC_NAME_PREFIX

#endif
