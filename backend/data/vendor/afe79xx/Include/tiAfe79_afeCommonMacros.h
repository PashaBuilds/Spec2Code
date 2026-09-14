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

#ifndef tiAfe79_AFE_COMMON_MACROS_H_
#define tiAfe79_AFE_COMMON_MACROS_H_
/** @file tiAfe79_afeCommonMacros.h
 * 	@brief	This file contains C Macros for different kinds of operations in the AFE function.<br>
 *      <b> Version 2.6:</b> <br>
 *      1. Corrected the PASS/FAIL return status of Functions.
 *      <b> Version 2.1:</b> <br>
 *      1. Added Documentation.
 *      2. Modified the Macro Execution errors for better handling.
 */

#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_baseFunc.h"
#include "tiAfe79_genLibFunc.h"

#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

/// This C Macro has the operation on what to do when the input parameters to AFE function are invalid. It is not recommended to change its contents.
#define AFE79_PARAMS_VALID(args)                                         \
    if (!(args))                                                         \
    {                                                                    \
        afeLogErr("Parameter did not satisfy the condition: %s", #args); \
        return TI_AFE_RET_EXEC_FAIL;                                     \
    }

/// This C Macro has the operation on what to do when the AFE ID(afeInst) is invalid. It is not recommended to change its contents.
#define AFE79_ID_VALIDITY()                         \
    uint8_t noOfAfe;                                \
    AFE79FNP(getNumAfe79)                           \
    (&noOfAfe);                                     \
    if (AFE79_CURR_ID >= noOfAfe)                   \
    {                                               \
        afeLogErr("%s", "device ID out of bounds"); \
        return TI_AFE_RET_EXEC_FAIL;                \
    }

#ifndef USE_AFE79_LIB_FORMAT_2
#undef AFE79_ID_VALIDITY
#define AFE79_ID_VALIDITY()
#endif

/** This C Macro has the operation on what to do when an SPI driver function fails.<br>
 *  There are two recommended recovery ways for this<br>
 *  Option 1. Resolve the SPI issue, reperform the last SPI operation and continue with the execution.<br>
 *  Option 2. Resolve the SPI issue, close all the open pages using the function closeAllPages(afeInst). Call the failed function again.*/
#define AFE79_SPI_EXEC(args)                                         \
    if (TI_AFE_RET_EXEC_PASS != (args))                              \
    {                                                                \
        afeLogErr("Execution of function(SPI) failed: %s", #args);   \
        return TI_AFE_RET_EXEC_FAIL;                                 \
    }                                                                \
    else                                                             \
    {                                                                \
        afeLogDbg("Executed function(SPI) successfully: %s", #args); \
    }

/** This C Macro handles what to do when a sub-function call fails. <br>
 * If on fail, TI_AFE_RET_EXEC_FAIL is returned, then the function execution is stopped and returns TI_AFE_RET_EXEC_FAIL. <br>
 * If only the command "errorStatus |= 1;" is executed, then the main function execution will continue and the main called function will return TI_AFE_RET_EXEC_FAIL.*/
#define AFE79_FUNC_EXEC(args)                                        \
    if (TI_AFE_RET_EXEC_PASS != (args))                              \
    {                                                                \
        afeLogErr("AFE Function Execution failed: %s", #args);       \
        return TI_AFE_RET_EXEC_FAIL;                                 \
    }                                                                \
    else                                                             \
    {                                                                \
        afeLogDbg("AFE Function Executed successfully: %s ", #args); \
    }

/// This C Macro has the operation on what to do when the AFE MCU MACRO(not C Macro) Ready poll fails. It is not recommended to change its contents.
#define AFE_MACRO_READY_POLL_FAIL(args)                              \
    if (TI_AFE_RET_EXEC_PASS != (args))                              \
    {                                                                \
        afeLogErr("AFE MACRO READY POLL FAILED: %s", #args);         \
        return TI_AFE_RET_EXEC_FAIL;                                 \
    }                                                                \
    else                                                             \
    {                                                                \
        afeLogDbg("AFE MACRO READY Successfully Passed: %s", #args); \
    }

/// This C Macro has the operation on what to do when the AFE MCU MACRO(not C Macro) Done poll fails. It is not recommended to change its contents.
#define AFE_MACRO_DONE_POLL_FAIL(args)                              \
    if (TI_AFE_RET_EXEC_PASS != (args))                             \
    {                                                               \
        afeLogErr("AFE MACRO DONE POLL FAILED: %s", #args);         \
        return TI_AFE_RET_EXEC_FAIL;                                \
    }                                                               \
    else                                                            \
    {                                                               \
        afeLogDbg("AFE MACRO DONE Successfully Passed: %s", #args); \
    }

/** This C Macro has the operation on what to do when the AFE MCU MACRO(not C Macro) execution fails.<br>
 * * If on fail, TI_AFE_RET_EXEC_FAIL is returned, then the function execution is stopped and returns TI_AFE_RET_EXEC_FAIL. <br>
 * If only the command "errorStatus |= 1;" is executed, then the main function execution will continue and the main called function will return TI_AFE_RET_EXEC_FAIL.*/
#define AFE_MACRO_EXEC_ERROR(args)                                                                               \
    if (AFE_MACRO_NO_ERROR != (args))                                                                            \
    {                                                                                                            \
        if (((AFE_MACRO_ERROR_IN_OPCODE & (args)) != 0) || ((AFE_MACRO_ERROR_OPCODE_NOT_ALLOWED & (args)) != 0)) \
        {                                                                                                        \
            afeLogErr("AFE MACRO 0x%X: ERROR in OPCODE Received", opcode);                                       \
        }                                                                                                        \
        else if ((AFE_MACRO_ERROR_IN_OPERAND & (args)) != 0)                                                     \
        {                                                                                                        \
            afeLogErr("AFE MACRO 0x%X: ERROR in Operand Received", opcode);                                      \
        }                                                                                                        \
        else if ((AFE_MACRO_ERROR_IN_EXECUTION & (args)) != 0)                                                   \
        {                                                                                                        \
            afeLogErr("AFE MACRO 0x%X: ERROR in Execution.", opcode);                                            \
        }                                                                                                        \
        return TI_AFE_RET_EXEC_FAIL;                                                                             \
    }                                                                                                            \
    else                                                                                                         \
    {                                                                                                            \
        afeLogDbg("AFE MACRO 0x%X: Executed without Error.", opcode);                                            \
    }

#endif
