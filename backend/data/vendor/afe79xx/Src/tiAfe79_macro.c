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

/** @file tiAfe79_macro.c
 * 	@brief	This file has Macros related functions.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Deleted redundant function: doPrepareTune<br>
 * 		3. Added TX Tone Gen function<br>
 * 		4. Changed the C macros for all the spi wrapper and executeMacro function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 */

#include <stdint.h>

#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeCommonMacros.h"

#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"

#include "tiAfe79_macro.h"

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
    @brief Read Macro Result Register
    @details Read Macro Result Register
    @param afeInst AFE ID
    @param regNum Result register number.
    @param result Returns result register as a pointer.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readResultRegSpi)(AFE79_INST_TYPE afeInst, uint8_t regNum, uint32_t *result)
{

    uint8_t readValue;
    AFE79_ID_VALIDITY();
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, (AFE_MACRO_RESULT_START_REG_ADDR + i + (regNum * 4)) << (i << 3), 0, 7, &readValue));
        *result = *result + readValue;
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief TX Tone Generator
    @details This function sends a single tone to the TX.
    @param afeInst AFE ID
    @param chNo TX Channel Select.
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param configOption Tone Generation Command<br>
            0 → RESERVED<br>
            1 → The current mixer configuration will be saved and the mixers will be configured to give the new tone frequency. <br>
            2 → The mixers will be configured to give the new tone but the saved configuration will not be modified. <br>
            3 → RESERVED<br>
            4 → Restore saved configuration. This can be called to restore the last saved mixer configuration.
    @param freq0 RF tone Frequency<br>
                Should pass value in KHz in 1KHz ncoFreqMode and the frequency word value in FCW mode. The Mode is determined by the ncoFreqMode set in Latte while generating the bringup script.<br>
                In FCW mode, the value can be calculate using the equation: mixer =  (uint32_t) (2^32*mixerFrequency/Fdac).
    @param freq0Amp Tone Backoff in dB<br>
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(txCalibSiggen)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t configOption, uint32_t freq0, uint8_t freq0Amp)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= AFE79_NUM_TX_CHANNELS_BITWISE);
    uint8_t byteList[16];
    uint8_t numOfOperands = 0;
    uint8_t byteListFreq[4];
    byteList[numOfOperands] = chNo;
    numOfOperands++;
    byteList[numOfOperands] = 1 << configOption;
    numOfOperands++;
    byteList[numOfOperands] = 0;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(freq0 & 0xffffffff, 4, byteListFreq));
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListFreq[i];
        numOfOperands++;
    }
    byteList[numOfOperands] = freq0Amp;
    numOfOperands++;

    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = 0;
        numOfOperands++;
    }
    byteList[numOfOperands] = 0;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_CONFIG_SIGGEN_FOR_CAL));

    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Poll for Macro Acknowledgement
    @details Polls for Macro Acknowledgement
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed. It returns as failed even if the Macro_ACK doesn't become 1.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(waitForMacroAck)(AFE79_INST_TYPE afeInst)
{

    uint8_t count = 0;
    uint8_t readValue = 0;
    AFE79_ID_VALIDITY();
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    while (((readValue & 2) == 0) && (count <= 200))
    {
        count++;
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
        if (count > 200)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
            /*macro*/
            return TI_AFE_RET_EXEC_FAIL;
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
    /*macro*/

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Reconfigures the selected Chains.
    @details Reconfigures the selected Chains. This function is called in updateTxNco function and is not recommended to be called independently.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(doSystemTuneSelective)(AFE79_INST_TYPE afeInst, uint8_t rxChList, uint8_t fbChList, uint8_t txChList, uint8_t sectionEnable)
{
    /*  Does the System Configuration for selected Chains depending upon the Config Params set by other Macros. Section Enables can be used for Selective Tune.   */

    uint8_t byteList[4];
    uint8_t numOfOperands = 0;
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(rxChList <= AFE79_NUM_RX_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(fbChList <= AFE79_NUM_FB_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(txChList <= AFE79_NUM_TX_CHANNELS_BITWISE);
    byteList[numOfOperands] = (rxChList + (fbChList << 4));
    numOfOperands++;
    byteList[numOfOperands] = (txChList);
    numOfOperands++;
    byteList[numOfOperands] = ((0x3FFF ^ sectionEnable) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((0x3FFF ^ sectionEnable) >> 8);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_SYSTEM_TUNE_SELECTIVE)); // MacroConsts.MACRO_OPCODE_SYSTEM_TUNE);
    return TI_AFE_RET_EXEC_PASS;
}
/**
    @brief Write the Macro Operands.
    @details Write the Macro Operands.
    @param afeInst AFE ID
    @param operandList Byte-wise array of operands to be written.
    @param numOfOperands Size of operandList.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(writeOperandList)(AFE79_INST_TYPE afeInst, uint8_t *operandList, uint8_t numOfOperands)
{
    AFE79_ID_VALIDITY();

    uint8_t operandNo = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    for (operandNo = 0; operandNo < numOfOperands; operandNo++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_OPERAND_START_REG_ADDR + operandNo, operandList[operandNo] & 0xff, 0x0, 0x7));
        /*MACRO_OPERAND_REG0*/
    }
    if (operandNo % 4 != 0)
    {
        uint8_t i;
        for (i = 0; i < 4 - (operandNo % 4); i++)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_OPERAND_START_REG_ADDR + operandNo + i, 0, 0x0, 0x7));
        }
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Poll for Macro Ready
    @details Polls for Macro Ready
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed. It returns as failed even if the Macro_Ready doesn't become 1.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(waitForMacroReady)(AFE79_INST_TYPE afeInst)
{

    uint8_t count = 0;
    uint8_t readValue;
    /*  Wait for Macro Ready.   */
    AFE79_ID_VALIDITY();
    count = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    while (((readValue & 1) == 0) && (count <= 200))
    {
        count++;
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
        if (count > 200)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
            /*macro*/
            return TI_AFE_RET_EXEC_FAIL;
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
    /*macro*/
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Poll for Macro Done
    @details Polls for Macro Done
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed. It returns as failed even if the Macro_Done doesn't become 1.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(waitForMacroDone)(AFE79_INST_TYPE afeInst)
{

    uint8_t count = 0;
    uint8_t readValue;
    AFE79_ID_VALIDITY();
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    while (((readValue & 4) == 0) && (count <= 200))
    {
        count++;
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
        if (count > 200)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
            /*macro*/
            return TI_AFE_RET_EXEC_FAIL;
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &readValue));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
    /*macro*/

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks if there is a Macro Error
    @details Checks if there is a Macro Error and returns the error status as pointer.
    @param afeInst AFE ID
    @param macroErrorStatus Macro Error Status return as pointer.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkForMacroError)(AFE79_INST_TYPE afeInst, uint8_t *macroErrorStatus)
{

    uint8_t errorReadReg = 0;
    uint8_t errorExtendedCodeReg = 0;
    AFE79_ID_VALIDITY();
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, &errorReadReg));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_EXTENDED_ERROR_CODE_REG_ADDR, 0, 7, &errorExtendedCodeReg));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x000, 0x0, 0x7));
    *macroErrorStatus = AFE_MACRO_NO_ERROR;
    if ((((errorReadReg) >> 3) & 1) == 1)
    {
        afeLogErr("Macro Error Execution Failed with the error 0X%0X: ", errorExtendedCodeReg);
        if ((((errorReadReg) >> 4) & 0x1) == 1)
        {
            afeLogErr("%s", "MACRO_ERROR_IN_OPCODE");
            *macroErrorStatus |= AFE_MACRO_ERROR_IN_OPCODE;
        }
        if ((((errorReadReg) >> 5) & 0x1) == 1)
        {
            afeLogErr("%s", "MACRO_ERROR_OPCODE_NOT_ALLOWED");
            *macroErrorStatus |= AFE_MACRO_ERROR_OPCODE_NOT_ALLOWED;
        }
        if ((((errorReadReg) >> 6) & 0x1) == 1)
        {
            afeLogErr("%s", "MACRO_ERROR_IN_OPERAND");
            *macroErrorStatus |= AFE_MACRO_ERROR_IN_OPERAND;
        }
        if ((((errorReadReg) >> 7) & 0x1) == 1)
        {
            afeLogErr("%s", "MACRO_ERROR_IN_EXECUTION");
            *macroErrorStatus |= AFE_MACRO_ERROR_IN_EXECUTION;
        }
    }
    /*Returning only the macro Error*/
    *macroErrorStatus = ((errorReadReg >> 3) & 1);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Writes Opcode and triggers the Macro.
    @details Writes Opcode and triggers the Macro.
    @param afeInst AFE ID
    @param opcode Opcode of the Macro.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(triggerMacro)(AFE79_INST_TYPE afeInst, uint8_t opcode)
{

    AFE79_ID_VALIDITY();
    /*  Triggers the Macro by writing the Macro Opcode.   */
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    /*macro*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_OPCODE_REG_ADDR, (opcode)&0xff, 0x0, 0x7));
    /*MACRO_OPCODE*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Execute a Macro
    @details Executes the Macro by calling other sub functions.
    @param afeInst AFE ID
    @param byteList Byte-wise array of operands to be written.
    @param numOfOperands Size of operandList.
    @param opcode Opcode of the Macro.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(executeMacro)(AFE79_INST_TYPE afeInst, uint8_t *byteList, uint8_t numOfOperands, uint8_t opcode)
{
    /*  Execute a Macro.   */
    uint8_t macroErrorStatus = 0;

    AFE79_ID_VALIDITY();
    AFE_MACRO_READY_POLL_FAIL(AFE79FNP(waitForMacroReady)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(writeOperandList)(afeInst, byteList, numOfOperands));
    AFE79_FUNC_EXEC(AFE79FNP(triggerMacro)(afeInst, opcode));
    AFE_MACRO_DONE_POLL_FAIL(AFE79FNP(waitForMacroDone)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(checkForMacroError)(afeInst, &macroErrorStatus));
    AFE_MACRO_EXEC_ERROR(macroErrorStatus);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Enables MCU Memory Access for SPI.
    @details Enables MCU Memory Access for SPI. Note that this should be relinquished after the access is complete.
    @param afeInst AFE ID
    @param en 1 enable MCU memory access for SPI.<br>
            0 disable MCU memory access for SPI
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(enableMemAccess)(AFE79_INST_TYPE afeInst, uint8_t en)
{

    uint8_t byteList[1];
    uint8_t numOfOperands = 0;
    AFE79_ID_VALIDITY();

    if (en == 1)
    {
        byteList[numOfOperands] = 0;
        numOfOperands++;
    }
    else
    {
        byteList[numOfOperands] = 1;
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_SYSTEM_TUNE)); // MacroConsts.MACRO_OPCODE_SYSTEM_TUNE);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Reconfigures the TX NCO info to the MCU.
    @details Reconfigures the TX NCO info to the MCU. This function is called in updateTxNco function and is not recommended to be called independently.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateSystemTxChannelFreqConfig)(AFE79_INST_TYPE afeInst, uint8_t txChList, uint8_t listNCO, uint32_t txNCO, uint8_t immUpdt, uint8_t reload)
{
    /*  Update the Tx Channel Frequency Config Params for selected Chains/Bands/NCOs.   */

    uint8_t byteList[7];
    uint8_t byteListTxNco[4];
    uint8_t numOfOperands = 0;
    uint8_t updateNcoByte = 0;

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(txChList <= AFE79_NUM_TX_CHANNELS_BITWISE);
    byteList[numOfOperands] = (txChList);
    numOfOperands++;
    byteList[numOfOperands] = (listNCO);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(txNCO, 4, byteListTxNco));
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListTxNco[i];
        numOfOperands++;
    }
    updateNcoByte = immUpdt | (reload << 1);
    byteList[numOfOperands] = (updateNcoByte);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_SYSTEM_TX_CHANNEL_FREQUENCY_CONFIGURATION)); // MacroConsts.MACRO_OPCODE_UPDATE_SYSTEM_TX_CHANNEL_FREQUENCY_CONFIGURATION);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks for MCU Health.
    @details Checks for MCU Health and returns the status as a pointer.
    @param afeInst AFE ID
    @param healthOk Return Pointer of the status of the MCU. This value is 1 if the MCU is working properly and 0 if MCU is stuck.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkMcuHealth)(AFE79_INST_TYPE afeInst, uint8_t *healthOk)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(healthOk != NULL);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x10, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00F0, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00A0, 0x02, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0193, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x00, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, AFE_MACRO_PAGE_SEL_VAL, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE_MACRO_STATUS_REG_ADDR, 0, 7, healthOk));
    *healthOk &= 0x1;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x00, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}