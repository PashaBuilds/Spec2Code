
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

/** @file tiAfe79_genLibFunc.c
 * 	@brief	This file has Basic SPI functions.<br>
 *       <b> Version 1.0.0:</b> <br>
 *           1. Initial Version
 */
#include <stdint.h>
#include <stdio.h>

#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_genLibFunc.h"

/// Mode of execution of AFE. Simulation or Mission Mode.
static uint8_t AFE79_LIBS_RUN_MODE = AFE_LIBS_MISSION_MODE; // AFE_LIBS_SIMULATION_MODE

TI_AFE_API_COMP uint8_t AFE79FNP(setAfeLibsRunMode)(uint8_t mode)
{
    AFE79_LIBS_RUN_MODE = mode;
    return TI_AFE_RET_EXEC_PASS;
}

TI_AFE_API_COMP uint8_t AFE79FNP(getAfeLibsRunMode)(uint8_t *runMode)
{
    *runMode = AFE79_LIBS_RUN_MODE;
    return TI_AFE_RET_EXEC_PASS;
}

#ifdef USE_AFE79_LIB_FORMAT_2

/// Number of AFEs controlled by the host. This should be set by the user.
static uint8_t NUM_OF_AFE79 = 2;

TI_AFE_API_COMP uint8_t AFE79FNP(setNumAfe79)(uint8_t num)
{
    NUM_OF_AFE79 = num;
    return TI_AFE_RET_EXEC_PASS;
}

TI_AFE_API_COMP uint8_t AFE79FNP(getNumAfe79)(uint8_t *noOfAfe)
{
    *noOfAfe = NUM_OF_AFE79;
    return TI_AFE_RET_EXEC_PASS;
}
#endif
/**
    @brief Set the AFE Log Level.
    @details Sets the AFE Log Level. There are multiple levels of logging as below.<br>
            AFE_LOG_LEVEL_ERROR     0   :   Error conditions<br>
            AFE_LOG_LEVEL_WARNING   1   :   warning conditions<br>
            AFE_LOG_LEVEL_INFO      2   :   informational<br>
            AFE_LOG_LEVEL_SPILOG    3   :   SPI-level messages<br>
            AFE_LOG_LEVEL_DEBUG     4   :   debug-level messages<br>
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param level Log level.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setAfeLogLvl)(AFE79_INST_TYPE afeInst, uint32_t level)
{
    if (level > AFE_LOG_LEVEL_DEBUG)
        return TI_AFE_RET_EXEC_PASS;
    AFE_CURRENT_LOG_LEVEL = level;
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Get the AFE Log Level.
    @details Returns the AFE Log Level. There are multiple levels of logging as below.<br>
            AFE_LOG_LEVEL_ERROR     0   :   Error conditions<br>
            AFE_LOG_LEVEL_WARNING   1   :   warning conditions<br>
            AFE_LOG_LEVEL_INFO      2   :   informational<br>
            AFE_LOG_LEVEL_SPILOG    3   :   SPI-level messages<br>
            AFE_LOG_LEVEL_DEBUG     4   :   debug-level messages<br>
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param logLevel Pointer retur of Log level.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getAfeLogLvl)(AFE79_INST_TYPE afeInst, uint32_t *logLevel)
{
    *logLevel = AFE_CURRENT_LOG_LEVEL;
    return TI_AFE_RET_EXEC_PASS;
}

static uint16_t AFE79_LIB_VERSION = 0x0209;

/**
    @brief Get the Current Lib Version.
    @details Returns the AFE Library Verion as a pointer<br>
    @param libVersion Pointer retur of Library Version. Need to interpret it as libVersion[15:8].libVersion[7:0]. For example, if it is 0x0105, that means it is 1.5 version.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getLibVersion)(uint16_t *libVersion)
{
    *libVersion = AFE79_LIB_VERSION;
    return TI_AFE_RET_EXEC_PASS;
}
