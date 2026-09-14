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

/** @file tiAfe79_agc.c
 * 	@brief This file has AGC related functions.<br>
 * 		<b> Version 2.2:</b> <br>
 * 		1. Updated the agcStateControlMacro description<br>
 * 		2. Fixed macro opcode bug in agcDigDetRelativeNumCrossingConfig.<br>
 * 		<b> Version 2.1.1:</b> <br>
 * 		1. Added more functions. agcDigDetRelativeNumCrossingConfig, externalAgcConfig, internalAgcConfig, rfAnalogDetConfig, extLnaConfig, extLnaGainConfig<br>
 * 		2. Removed Automatically calling State Control Macro to giver user better flexibility.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Changed the C macro for executing the executeMacro function to AFE79_FUNC_EXEC.<br>
 * 		3. Changed the C macros for all the spi wrapper function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 */
#include <stdint.h>

#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_dsaAndNco.h"

#include "tiAfe79_afeParameters.h"
#include "tiAfe79_genLibFunc.h"
#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"
#include "tiAfe79_agc.h"
#include "tiAfe79_macro.h"

/* Detector Configuration and Common Controls */
/**
        @brief AGC State Control Macro
        @details Controls the state of the AGC
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param agcstate Bit wise parameter controlling the state of the AGC. Making a bit 1 does the corresponding operation. <br>
                Bit 0: Start Internal AGC with entire configuration redone<br>
                Bit 1: Freeze the Internal AGC loop<br>
                Bit 2: Unfreeze the Internal AGC loop (takes effect only if the loop is already in freeze)<br>
                Bit 3: Disable Internal AGC loop<br>
                Bit 4: ALC Block enable<br>
                Bit 5: ALC Block disable<br>
                Bit 6: External AGC enable<br>
                Bit 7: External AGC disable<br>
                Bit 8: Restart the Internal AGC. (Step1: Disable Internal AGC, Step2:Enable Internal AGC)<br>
                Bit 9: Restart ALC(Step1: Disable ALC, Step2:Enable ALC)<br>
                Bit 10: Restart external AGC(Step1: Disable external AGC, Step2:Enable external AGC)<br>
            All the bits should not be set together.For example, the enables and disables should not be set together. Invalid combinations include:<br>
            1. No other AGC related bit should be enabled when AGC enable is 1.<br>
            2. Enable and disable of the ALC should not be set at the same time.<br>
            3. Enable and disable of the AGC should not be set at the same time.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(agcStateControlConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t agcstate)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID((((agcstate & 1) == 1) && ((agcstate & 0x5ce) == 0)) || ((agcstate & 1) == 0)); // To ensure that no other AGC related bit is enabled when AGC enable is 1.
    AFE79_PARAMS_VALID((agcstate & 0b110) != 0b110);                                                   // To ensure that freeze and unfreeze of the AGC are not set at the same time.
    AFE79_PARAMS_VALID((agcstate & 0x30) != 0x30);                                                     // To ensure that enable and disable of the AlC are not set at the same time.
    AFE79_PARAMS_VALID((agcstate & 0xC0) != 0xC0);                                                     // To ensure that enable and disable of the external AGC are not set at the same time.
    uint8_t byteList[3];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (agcstate & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((agcstate >> 8) & 0xff);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_STATE_CONTROL)); // MacroConsts.MACRO_OPCODE_LIST.AGC_STATE_CONTROL);

    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief ADC Digital Detector Threshold configuration.
        @details Enables or disables the detectors. agcStateControlConfig function should be called with internal or external AGC enable appropriately after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param bigStepAttkEn 0 disables and 1 enables the corresponding detector.
        @param smallStepAttkEn 0 disables and 1 enables the corresponding detector.
        @param bigStepDecEn 0 disables and 1 enables the corresponding detector.
        @param smallStepDecEn 0 disables and 1 enables the corresponding detector.
        @param powerAttkEn 0 disables and 1 enables the corresponding detector.
        @param powerDecEn 0 disables and 1 enables the corresponding detector.
        @param bigStepAttkThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @param smallStepAttkThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @param bigStepDecThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @param smallStepDecThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @param powerAttkThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @param powerDecThresh: This -threshValue/4 is the threshold set. That is, to set the threshold of -2.25dbfs, this value should be 2.25*4=9. Supported range is 0-(AFE_DET_THRESHOLD_MAX_VAL*4).
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bigStepAttkEn, uint8_t smallStepAttkEn, uint8_t bigStepDecEn, uint8_t smallStepDecEn, uint8_t powerAttkEn, uint8_t powerDecEn,
                                                  uint8_t bigStepAttkThresh, uint8_t smallStepAttkThresh, uint8_t bigStepDecThresh, uint8_t smallStepDecThresh, uint8_t powerAttkThresh, uint8_t powerDecThresh)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(bigStepAttkThresh <= AFE_DET_THRESHOLD_MAX_VAL * 4);
    AFE79_PARAMS_VALID(smallStepAttkThresh <= AFE_DET_THRESHOLD_MAX_VAL * 4);
    AFE79_PARAMS_VALID(smallStepDecThresh <= AFE_DET_THRESHOLD_MAX_VAL * 4);
    AFE79_PARAMS_VALID(powerAttkThresh <= AFE_DET_THRESHOLD_MAX_VAL * 4);
    AFE79_PARAMS_VALID(powerDecThresh <= AFE_DET_THRESHOLD_MAX_VAL * 4);

    uint8_t byteList[8];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkEn) + (smallStepAttkEn << 1) + (bigStepDecEn << 2) + (smallStepDecEn << 3) + (powerAttkEn << 4) + (powerDecEn << 5));
    numOfOperands++;
    byteList[numOfOperands] = (bigStepAttkThresh);
    numOfOperands++;
    byteList[numOfOperands] = (smallStepAttkThresh);
    numOfOperands++;
    byteList[numOfOperands] = (bigStepDecThresh);
    numOfOperands++;
    byteList[numOfOperands] = (smallStepDecThresh);
    numOfOperands++;
    byteList[numOfOperands] = (powerAttkThresh);
    numOfOperands++;
    byteList[numOfOperands] = (powerDecThresh);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_DIG_DET_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.AGC_DIG_DET_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief ADC Digital Detector Window Length configuration
    @details Configures the Window Length (or time constant) of the detectors. agcStateControlConfig function should be called with internal or external AGC enable appropriately after this function call to update the configuration.
    @param afeInst AFE ID
    @param chNo Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param bigStepAttkWinLen Window length of big step attack and RF Analog (also called Customer RF) detectors. Window length is this value *10ns. Range is 0-AFE_AGC_MAX_WIN_LEN.
    @param miscStepAttkWinLen: Window length of all other attack detectors. Window length is this value *10ns. Range is 0-AFE_AGC_MAX_WIN_LEN.
    @param decayWinLen Window Length of all the decay detectors.Window length is this value *10ns. Range is 0-AFE_AGC_MAX_WIN_LEN.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetTimeConstantConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkWinLen, uint32_t miscStepAttkWinLen, uint32_t decayWinLen)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(bigStepAttkWinLen <= AFE_AGC_MAX_WIN_LEN);
    AFE79_PARAMS_VALID(miscStepAttkWinLen <= AFE_AGC_MAX_WIN_LEN);
    AFE79_PARAMS_VALID(decayWinLen <= AFE_AGC_MAX_WIN_LEN);
   
    uint8_t byteList[10];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo); /* AGC_DET_TIME_CONST_CONFIG*/
    numOfOperands++;
    byteList[numOfOperands] = (bigStepAttkWinLen & 0xff); /* check adc_intm_attack_win_len*/
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkWinLen >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkWinLen >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((miscStepAttkWinLen & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((miscStepAttkWinLen >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((miscStepAttkWinLen >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((decayWinLen & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((decayWinLen >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((decayWinLen >> 16) & 0xff);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_DET_TIME_CONST_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.AGC_DET_TIME_CONST_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief ADC Digital Detector Absolute NumHits configuration
        @details ADC Digital Detector Absolute NumHits configuration. This represents the exact number of crossings threshold and this may need to be adjusted whenever window length is reconfigured to ensure the NumHits threshold will be lower than the Window Length configuration.<br>
                Note that only this function or agcDigDetAbsoluteNumCrossingConfig should be used. Both shouldn't be called.<br>
                agcStateControlConfig function should be called with internal or external AGC enable appropriately after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param bigStepAttkNumHits Absolute Number of Threshold crossing hits threshold of big step attack detectors. Range is 0-AFE_AGC_MAX_ABS_NUM_HITS.
        @param smallStepAttkNumHits: Absolute Number of Threshold crossing hits threshold of Small step attack detectors. Range is 0-AFE_AGC_MAX_ABS_NUM_HITS.
        @param bigStepDecNumHits Absolute Number of Threshold crossing hits threshold of big step decay detectors. Range is 0-AFE_AGC_MAX_ABS_NUM_HITS.
        @param smallStepDecNumHits Absolute Number of Threshold crossing hits threshold of small step decay detectors. Range is 0-AFE_AGC_MAX_ABS_NUM_HITS.
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetAbsoluteNumCrossingConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkNumHits, uint32_t smallStepAttkNumHits, uint32_t bigStepDecNumHits, uint32_t smallStepDecNumHits)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(bigStepAttkNumHits <= AFE_AGC_MAX_ABS_NUM_HITS);
    AFE79_PARAMS_VALID(smallStepAttkNumHits <= AFE_AGC_MAX_ABS_NUM_HITS);
    AFE79_PARAMS_VALID(bigStepDecNumHits <= AFE_AGC_MAX_ABS_NUM_HITS);
    AFE79_PARAMS_VALID(smallStepDecNumHits <= AFE_AGC_MAX_ABS_NUM_HITS);
    uint8_t byteList[13];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (bigStepDecNumHits & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepDecNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepDecNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (smallStepDecNumHits & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepDecNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepDecNumHits >> 16) & 0xff);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_DIG_DET_ABSOLUTE_NUM_CROSSINGS_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.AGC_DIG_DET_ABSOLUTE_NUM_CROSSINGS_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief ADC Digital Detector Relative NumHits configuration
        @details ADC Digital Detector Relative NumHits configuration. This specifies the threshold relative to the window length of the corresponding detector. The advantage of this approach is, this will scale automatically when the window length is changed.<br>
                Note that only this function or agcDigDetAbsoluteNumCrossingConfig should be used. Both shouldn't be called.<br>
                agcStateControlConfig function should be called with internal or external AGC enable appropriately after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param bigStepAttkNumHits Relative Number of Threshold crossing hits threshold of big step attack detectors. The window counter threhold is (value*bigStepAttkWinLen/2^16). Range is 0-0xffff.
        @param smallStepAttkNumHits: Relative Number of Threshold crossing hits threshold of Small step attack detectors. The window counter threhold is (value*smallStepAttkNumHits/2^16).Range is 0-0xffff.
        @param bigStepDecNumHits Relative Number of Threshold crossing hits threshold of big step decay detectors. The window counter threhold is (value*bigStepDecNumHits/2^16). Range is 0-0xffff.
        @param smallStepDecNumHits Relative Number of Threshold crossing hits threshold of small step decay detectors. The window counter threhold is (value*smallStepDecNumHits/2^16). Range is 0-0xffff.
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(agcDigDetRelativeNumCrossingConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t bigStepAttkNumHits, uint32_t smallStepAttkNumHits, uint32_t bigStepDecNumHits, uint32_t smallStepDecNumHits)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[13];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepAttkNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits & 0xff));
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepAttkNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (bigStepDecNumHits & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepDecNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((bigStepDecNumHits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (smallStepDecNumHits & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepDecNumHits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((smallStepDecNumHits >> 16) & 0xff);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_DIG_DET_RELATIVE_NUM_CROSSINGS_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.AGC_DIG_DET_ABSOLUTE_NUM_CROSSINGS_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/* External AGC Related. */

/**
        @brief External AGC Configuration.
        @details Configures the External AGC.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param pin0sel Pin0/I_BIT0 configuration. Determines what detectors come out. <br>
            It can be configured to carry ORed combination of selected bits.<br>
            Setting a particular bit gets the detector on to the corresponding pin/LSB.<br>
                Bit 14: OVR Bit<br>
                Bit 13: Band 0 power detector<br>
                Bit 12: Band 0 peak detector<br>
                Bit 11: RF detector<br>
                Bit 10: Band 1 power detector<br>
                Bit 9: Band 1 peak detector<br>
                Bit 8: Reserved<br>
                Bit 7: Digital big step attack<br>
                Bit 6: Digital small step attack<br>
                Bit 5: Digital big step decay<br>
                Bit 4: Digital small step decay<br>
                Bit 3: Dig power attack<br>
                Bit 2: Dig power decay<br>
                Bit 1: Reserved (0)<br>
                Bit 0: Reserved (0)
        @param pin1sel Pin1/I_BIT1 configuration. Determines what detectors come out. Description same as pin1Sel.
        @param pin2sel Pin2/Q_BIT0 configuration. Determines what detectors come out. Description same as pin2Sel.
        @param pin3sel Pin3/Q_BIT1 configuration. Determines what detectors come out. Description same as pin30Sel.
        @param pulseExpansionCount Pulse Expansion Count. This value here is in steps of 10 ns. This pulseExpansionCount*10ns is the pulse width.Supported Range: 0-0xff
        @param pkDetPinLsbSel Determines whether to send detector data on LSB in External AGC mode.<br>
                0: send on Pin<br>
                1: send on Pin and LSB
        @param noLsbsToSend 0-Send only on Bits 0 of I and Q. 1- Send on both Bits 0 and 1.
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(externalAgcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t pin0sel, uint16_t pin1sel, uint16_t pin2sel, uint16_t pin3sel, uint8_t pkDetPinLsbSel, uint8_t pulseExpansionCount, uint8_t noLsbsToSend)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[12];
    uint8_t numOfOperands = 0;

    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (pin0sel & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((pin0sel >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (pin1sel & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((pin1sel >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (pin2sel & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((pin2sel >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (pin3sel & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((pin3sel >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = pkDetPinLsbSel;
    numOfOperands++;
    byteList[numOfOperands] = pulseExpansionCount;
    numOfOperands++;
    byteList[numOfOperands] = noLsbsToSend;
    numOfOperands++;

    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_EXT_AGC_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.MIN_MAX_DSA_ATTN_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/* Internal AGC Related. */

/**
        @brief Internal AGC Min-Max Attenuation Configuration.
        @details Configures the Minimum and Maximum DSA index between which the internal AGC operates. This is a dynamic Macro and AGC state macro needn't be called after this.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param minDsaAttn Minimum DSA index. (1LSB = 0.5dB)
        @param maxDsaAttn: Maximum DSA index. (1LSB = 0.5dB)
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(minMaxDsaAttnConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t minDsaAttn, uint8_t maxDsaAttn)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(minDsaAttn <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(maxDsaAttn <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(minDsaAttn <= maxDsaAttn);
    uint8_t byteList[3];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (minDsaAttn & 0xff); /* check min_attn*/
    numOfOperands++;
    byteList[numOfOperands] = (maxDsaAttn & 0xff); /* check max_attn*/
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_MIN_MAX_DSA_ATTN_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.MIN_MAX_DSA_ATTN_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief Internal AGC Gain-Step Configuration.
        @details Configures the Step size of the AGC (DSA index by which to change on detector triggering).<br>
                agcStateControlConfig function should be called with internal AGC enable after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param bigStepAttkStepSize Step Size of big step attack detector. (1LSB = 0.5dB)
        @param smallStepAttkStepSize Step Size of big step attack detector. (1LSB = 0.5dB)
        @param bigStepDecayStepSize Step Size of big step attack detector. (1LSB = 0.5dB)
        @param smallStepDecayStepSize Step Size of big step attack detector. (1LSB = 0.5dB)
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(agcGainStepSizeConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bigStepAttkStepSize, uint8_t smallStepAttkStepSize, uint8_t bigStepDecayStepSize, uint8_t smallStepDecayStepSize)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(bigStepAttkStepSize <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(smallStepAttkStepSize <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(bigStepDecayStepSize <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(smallStepDecayStepSize <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    uint8_t byteList[5];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (bigStepAttkStepSize & 0xff); /* big_step_attack_step_size*/
    numOfOperands++;
    byteList[numOfOperands] = (smallStepAttkStepSize & 0xff); /* small_step_attack_step_size*/
    numOfOperands++;
    byteList[numOfOperands] = (bigStepDecayStepSize & 0xff); /* big_step_decay_step_size*/
    numOfOperands++;
    byteList[numOfOperands] = (smallStepDecayStepSize & 0xff); /* small_step_decay_step_size*/
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_GAIN_STEP_SIZE_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.AGC_GAIN_STEP_SIZE_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief Internal AGC Configuration.
        @details Configures the internal AGC related settings.<br>
            agcStateControlConfig function should be called with internal AGC enable after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param tdd_freeze_agc Whether to reset or freeze the attack detectors during the OFF period of TDD. <br>0: Reset<br>1: Freeze
        @param blank_time_extcomp Blanking Time for all Detectors when external component (LNA or DVGA) gain change. This is interpreted as number of clocks of FadcRx/8. Supported range: 0-0xffff
        @param en_agcfreeze_pin Enable or Disable pin based AGC freeze.<br>0: Disable<br>1: Enable
        @param extCompControlEn External Component control to enable. <br>
                0x00: Neither of the controls are active<br>
                0x01: External LNA control is active<br>
                0x02: External DVGA control is active<br>
                Others: invalid
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(internalAgcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t tdd_freeze_agc, uint16_t blank_time_extcomp, uint8_t en_agcfreeze_pin, uint8_t extCompControlEn)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[6];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = tdd_freeze_agc;
    numOfOperands++;
    byteList[numOfOperands] = (blank_time_extcomp & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (blank_time_extcomp >> 8);
    numOfOperands++;
    byteList[numOfOperands] = en_agcfreeze_pin;
    numOfOperands++;
    byteList[numOfOperands] = extCompControlEn;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_INT_AGC_CONTROLLER_CONFIG));
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief Analog RF Detector Configuration.
        @details Analog RF Detector Configuration. agcStateControlConfig function should be called with internal or external AGC enable after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param rfdeten Use RF Analog detector for internal AGC. 0-Disable. 1-Enable
        @param rfDetMode Mode to use the RF Analog Detector Mode in AGC.<br>
            0: extAgc: Use RF Analog detector in External AGC.<br>
            1: bigStepAtk : Use RF Analog detector as very big step attack in internal AGC.<br>
            2: lnaBypass : Use RF Analog detector for external LNA bypass in internal AGC.<br>
        @param rfDetNumHitsMode Mode of input of the rfDetNumHitsMode. 0- Absolute. 1- Relative
        @param rfdetnumhits When rfDetNumHitsMode=0, this is the absolute Number of times signal crosses threshold above which attack is declared. This detector operates at FadcRx rate. Supported Range: <2^32.<br>
                    When rfDetNumHitsMode=1, this is the relative Number of times signal crosses threshold above which attack is declared. The actual threshold is floor(rfdetnumhits*bigStepAttkWinLen/2^32). Supported Range: <2^32.
        @param rfdetThreshold RF detect Threshold in dBm (for rfDetMode= 0 or 2) and in dbfs (for rfDetMode =1)
        @param rfdetstepsize Step Size of big step attack in dB. Valid only when rfDetMode=1
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(rfAnalogDetConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t rfdeten, uint8_t rfDetMode, uint8_t rfDetNumHitsMode, uint32_t rfdetnumhits, uint8_t rfdetThreshold, uint8_t rfdetstepsize)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[10];
    uint8_t numOfOperands = 0;

    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (rfdeten);
    numOfOperands++;
    byteList[numOfOperands] = (rfDetMode);
    numOfOperands++;
    byteList[numOfOperands] = (rfDetNumHitsMode);
    numOfOperands++;
    byteList[numOfOperands] = ((rfdetnumhits)&0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((rfdetnumhits >> 8) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((rfdetnumhits >> 16) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((rfdetnumhits >> 24) & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (rfdetThreshold & 0xff);
    numOfOperands++;
    if (rfDetMode == 1)
    {
        byteList[numOfOperands] = (rfdetstepsize & 0xff);
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_RF_ANALOG_CONFIG)); // MacroConsts.MACRO_OPCODE_LIST.MIN_MAX_DSA_ATTN_CONFIG);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief External LNA Configuration.
    @details Configures External LNA Configuration.<br>
            agcStateControlConfig function should be called with internal AGC enable after this function call to update the configuration.
    @param afeInst AFE ID
    @param chNo Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param singleDualBandMode Whether to use Single LNA control or dual LNA control in dual-band configuration.<br>
                0: Single LNA control, 1: Dual LNA control<br>
    @param lnaGainMargin LNA gain margin (this value is in dB scale where 1 LSB= 0.5 dB)<br>
            LNA reenable will happen when Current DSA Attenuation ≤ Maximum DSA Attenuation - LNA Gain - LNA Gain Margin in Single LNA Control Mode.<br>
            Not Applicable in Dual LNA Control
    @param enBandDet 0: Disable Band Detectors<br>
                    1: Enable band detectors<br>
                    Applicable only when Dual LNA control is enabled.
    @param tapOffPoint Band Detector Bandwidth Selection (Applicable only when dual LNA control and band detectors are enabled)<br>
                    0: Higher bandwidth<br>
                    1: Output bandwidth
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(extLnaConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t singleDualBandMode, uint8_t lnaGainMargin, uint8_t enBandDet, uint8_t tapOffPoint)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[5];
    uint8_t numOfOperands = 0;

    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = singleDualBandMode;
    numOfOperands++;
    byteList[numOfOperands] = lnaGainMargin;
    numOfOperands++;
    byteList[numOfOperands] = enBandDet;
    numOfOperands++;
    byteList[numOfOperands] = tapOffPoint;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_EXT_LNA_CONFIG));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief External LNA Fixed Gain Configuration.
    @details External LNA Fixed Gain Configuration.<br>
            agcStateControlConfig function should be called with internal AGC enable after this function call to update the configuration.
    @param afeInst AFE ID
    @param chNo Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param lnaGainB0 LNA Gain for Band 0 in dB. (1LSB=1/32dB). Supported Range 0-0x7ff.
    @param lnaPhaseB0 LNA Phase for Band 0 in degrees. (1LSB=360/1024 degrees). Supported Range 0-0x3ff.
    @param lnaGainB1 LNA Gain for Band 1 in dB. Valid only in dual band operation with dual LNA control enabled. (1LSB=1/32dB). Supported Range 0-0x7ff.
    @param lnaPhaseB1 LNA Phase for Band 1 in degrees. Valid only in dual band operation with dual LNA control enabled. (1LSB=360/1024 degrees). Supported Range 0-0x3ff.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(extLnaGainConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t lnaGainB0, uint16_t lnaPhaseB0, uint16_t lnaGainB1, uint16_t lnaPhaseB1)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(lnaGainB0 <= 0x7ff);
    AFE79_PARAMS_VALID(lnaPhaseB0 <= 0x3ff);
    AFE79_PARAMS_VALID(lnaGainB1 <= 0x7ff);
    AFE79_PARAMS_VALID(lnaPhaseB1 <= 0x3ff);
    uint8_t byteList[10];
    uint8_t numOfOperands = 0;

    byteList[numOfOperands] = chNo;
    numOfOperands++;
    byteList[numOfOperands] = 0;
    numOfOperands++;
    byteList[numOfOperands] = lnaGainB0 & 0xff;
    numOfOperands++;
    byteList[numOfOperands] = (lnaGainB0 >> 8) & 0x7f;
    numOfOperands++;
    byteList[numOfOperands] = lnaPhaseB0 & 0xff;
    numOfOperands++;
    byteList[numOfOperands] = (lnaPhaseB0 >> 8) & 0x3f;
    numOfOperands++;
    byteList[numOfOperands] = lnaGainB1 & 0xff;
    numOfOperands++;
    byteList[numOfOperands] = (lnaGainB1 >> 8) & 0x7f;
    numOfOperands++;
    byteList[numOfOperands] = lnaPhaseB1 & 0xff;
    numOfOperands++;
    byteList[numOfOperands] = (lnaPhaseB1 >> 8) & 0x3f;
    numOfOperands++;

    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_AGC_EXT_LNA_GAIN_CONFIG));
    return TI_AFE_RET_EXEC_PASS;
}

/* ALC Config Related. */

/**
        @brief ALC Configuration.
        @details Configures ALC. Note that this only informs the MCU of the mode. agcStateControlConfig function should be called with appropriate parameter after this to enable or disable it.
                agcStateControlConfig function should be called with ALC enable after this function call to update the configuration.
        @param afeInst AFE ID
        @param chNo Bit wise channel select<br>
                Bit0 for RXA<br>
                Bit1 for RXB<br>
                Bit2 for RXC<br>
                Bit3 for RXD
        @param alcMode ALC Mode<br>
            #0: Floatingpoint<br>
            #2: coarsefineI<br>
            #3: coarsefineIQ<br>
            #4: coarsefineALCpin<br>
            #5: inputALC
        @param totalGainRange Total gain range used by ALC for gain compensation. should be <AFE_ALC_TOTAL_GAIN_RANGE
        @param minAttnAlc Minimum Attenuation used by ALC for compensation when useMinAttnAgc = 0. should be <32. Value doesn;t matter when useMinAttnAgc=1
        @param useMinAttnAgc Configure the Min Attenuation Mode.<br>
            0: Use minAttnAlc for minimum attenuation for which compensation is required.<br>
            1: Enable ALC to use minimum attenuation from AGC for which compensation is required.
        @return Returns if the function execution passed or failed.
    */
TI_AFE_API_COMP uint8_t AFE79FNP(alcConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t alcMode, uint8_t totalGainRange, uint8_t minAttnAlc, uint8_t useMinAttnAgc)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(totalGainRange <= AFE_ALC_TOTAL_GAIN_RANGE);
    AFE79_PARAMS_VALID(minAttnAlc <= AFE_ALC_TOTAL_GAIN_RANGE);
    uint8_t byteList[4];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (totalGainRange & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = ((minAttnAlc & 0x3f) | (useMinAttnAgc << 7)); /* MinAttn*/
    numOfOperands++;
    byteList[numOfOperands] = (alcMode);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_ALC_CONFIGURATION)); // MacroConsts.MACRO_OPCODE_LIST.ALC_CONFIGURATION);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Floating Point Configuration.
    @details Configures Floating Point Mode related parameters. This needs to be called only when alcMode in alcConfig is set to floating point mode. Note that this only informs the MCU of the mode.<br>
                    agcStateControlConfig function should be called with ALC enable after this function call to update the configuration.
    @param afeInst AFE ID
    @param chNo Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param fltPtMode ALC Floating Point Mode. Sets whether to send MSB of mantissa always in Floating Point mode of ALC.<br>
            0: If exponent > 0, do not send MSB <br>
            1: Send MSB always

    @param fltPtFmt Floating Point Format. Number of Mantissa and Exponent bits to be used in floating point mode of ALC <br>
            0: 2 bit exponent , 13 bit mantissa and 1 bit sign
            1: 3 bit exponent, 12 bit mantissa and 1 bit sign
            2: 4 bit exponent, 11 bit mantissa and 1 bit sign
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(fltPtConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t fltPtMode, uint8_t fltPtFmt)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    uint8_t byteList[3];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (fltPtMode); /*FltPtMode*/
    numOfOperands++;
    byteList[numOfOperands] = (fltPtFmt); /*FltPtFmt*/
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FLOATING_POINT_CONFIG_ALC)); // MacroConsts.MACRO_OPCODE_LIST.FLOATING_POINT_CONFIG_ALC);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Coarse-Fine Mode Configuration.
    @details Configures Coarse-Fine Mode related parameters. This needs to be called only when alcMode in alcConfig is set to coarse-fine mode. Note that this only informs the MCU of the mode. <br>
                        agcStateControlConfig function should be called with ALC enable after this function call to update the configuration.
    @param afeInst AFE ID
    @param chNo Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param stepSize Choose the coarse step size. Appropriate value has to be chosen which can represent the complete attenuation range of operation.<br>
            0x00 → 0 dB<br>
            0x01 → 1 dB<br>
            0x02 → 2 dB<br>
            0x03 → 3 dB<br>
            0x04 → 4 dB<br>
            0x05 → 5 dB<br>
            0x06 → 6 dB<br>
            0x08 → 8 dB
    @param nBitIndex Choose the number of bits of coarse index. Supported Values are 0,2,3,4.
    @param indexInvert Coarse Index Invert. If this value is<br>
                        0: coarse index is transmitted as is.<br>
                        1: (15-coarse index) is transmitted
    @param indexSwapIQ Coarse Index Swap. If to swap coarse index on I and Q.<br>
                        0: LSB on I, MSB on Q<br>
                        1: MSB on I, LSB on Q
    @param sigBackOff This is the signal back-off, the offset attenuation applied. (in dB) This should be less than totalGainRange.
    @param gainChangeIndEn Applicable only when nBitIndex is 3. If this is set, in the bit-4 indicates if the DSA changed. Otherwise, 0 will be sent.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(coarseFineConfig)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t stepSize, uint8_t nBitIndex, uint8_t indexInvert, uint8_t indexSwapIQ, uint8_t sigBackOff, uint8_t gainChangeIndEn)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo <= (AFE79_NUM_RX_CHANNELS_BITWISE | (AFE79_NUM_FB_CHANNELS_BITWISE << AFE79_NUM_RX_CHANNELS)));
    AFE79_PARAMS_VALID(sigBackOff <= AFE_RX_DSA_MAX_ANA_DSA_DB);
    AFE79_PARAMS_VALID((nBitIndex <= 4) && (nBitIndex != 1));
    AFE79_PARAMS_VALID((stepSize <= 8) && (stepSize != 7));
    uint8_t byteList[7];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (chNo);
    numOfOperands++;
    byteList[numOfOperands] = (stepSize); /*CoarseStep*/
    numOfOperands++;
    byteList[numOfOperands] = (nBitIndex); /*NBitsCoarseIdx*/
    numOfOperands++;
    byteList[numOfOperands] = (indexInvert); /*CoarseIndexInvert*/
    numOfOperands++;
    byteList[numOfOperands] = (indexSwapIQ); /*CoarseIndexSwapIandQ*/
    numOfOperands++;
    byteList[numOfOperands] = (sigBackOff); /* SigBackOffdB*/
    numOfOperands++;
    byteList[numOfOperands] = (gainChangeIndEn); /* gainChangeIndEn*/
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_COARSE_FINE_MODE_ALC)); // MacroConsts.MACRO_OPCODE_LIST.COARSE_FINE_MODE_ALC);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Does the complete AGC-ALC configuration for all channels based on system parameters set.
    @details Does the complete AGC-ALC configuration for all channels based on system parameters set. RF Analog detecttor, dual LNA support is yet to be added to this. <br>
        setRxDsaMode should also set besides (preferably before calling this function but later is also okay) this function call to change the DSA control mux to required mode.
    @param afeInst AFE Instance of AFE79_INST_TYPE type
*/
TI_AFE_API_COMP uint8_t AFE79FNP(agcAlcConfiguration)(AFE79_INST_TYPE afeInst)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.chipVersion > 0x05);

    for (uint8_t topNo = 0; topNo < AFE79_NUM_RX_CHANNELS/2; topNo++)
    {   
        switch (AFE79_CURR_SYSPARAM.rxAgcParams[topNo*2].agcMode)
        {
            case 1:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 2));
                break;
            
            case 2:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 3));
                break;
            
            case 3:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 4));
                break;
            
            case 4:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 1));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << topNo, 0x0, 0x7)); /*dsa_page1*/
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xdc, 0 , 0x0, 0x0)); /*pin_agc_g6_en*/
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
                break;

            case 5:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 5));

                break;
            
            case 6:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 1));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << topNo, 0x0, 0x7)); /*dsa_page1*/
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xdc, 1, 0x0, 0x0)); /*pin_agc_g6_en*/
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
                break;
                
            default:
                AFE79_FUNC_EXEC(AFE79FNP(setRxDsaMode)(afeInst, topNo, 3));
        }
    }
    
    for(uint8_t Fb = 0; Fb < AFE79_NUM_FB_CHANNELS; Fb++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << Fb, 0x0, 0x7)); /*dsa_page1*/
        switch (AFE79_CURR_SYSPARAM.rxAgcParams[AFE79_NUM_RX_CHANNELS + Fb].agcMode)
        {
            case 1:
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x80, 0x2, 0x0, 0x2));/*gain_ctrl_fb*/
                break;
            
            case 2:
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x80, 0x3, 0x0, 0x2));
                break;

            default:
                AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x80, 0x3, 0x0, 0x2));
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x00, 0x0, 0x7));

    }
    
    uint8_t alc_mode, rxChSel = 0;

    for (uint8_t chNo = 0; chNo < AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
    {
        //Register Writes to Power Down or Power Up Channels
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x1 << chNo, 0x0, 0x7)); //Select Channel in 0x12
        if(AFE79_CURR_AGCPARAM_CH.agcMode == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x1, 0x0, 0x0)); //Power Down AGC
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x0, 0x0, 0x0)); //Normal Mode
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));

        AFE79_FUNC_EXEC(AFE79FNP(rfAnalogDetConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.rfdeten, AFE79_CURR_AGCPARAM_CH.custRfMode, AFE79_CURR_AGCPARAM_CH.rfdetNumhitsmode, AFE79_CURR_AGCPARAM_CH.rfdetnumhits, AFE79_CURR_AGCPARAM_CH.rfdetThreshold, AFE79_CURR_AGCPARAM_CH.rfdetstepsize));
  
        rxChSel = 1 << chNo;

        if (AFE79_CURR_AGCPARAM_CH.agcMode == 1)
        {
            AFE79_FUNC_EXEC(AFE79FNP(agcGainStepSizeConfig)(afeInst, rxChSel, 
                AFE79_CURR_AGCPARAM_CH.atksize[0],AFE79_CURR_AGCPARAM_CH.atksize[1], AFE79_CURR_AGCPARAM_CH.decaysize[0], AFE79_CURR_AGCPARAM_CH.decaysize[1]));

            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atken[0], AFE79_CURR_AGCPARAM_CH.atken[1], 
                AFE79_CURR_AGCPARAM_CH.decayen[0], AFE79_CURR_AGCPARAM_CH.decayen[1], AFE79_CURR_AGCPARAM_CH.atken[2], AFE79_CURR_AGCPARAM_CH.decayen[2],
                AFE79_CURR_AGCPARAM_CH.atkthreshold[0], AFE79_CURR_AGCPARAM_CH.atkthreshold[1], AFE79_CURR_AGCPARAM_CH.decaythreshold[0], AFE79_CURR_AGCPARAM_CH.decaythreshold[1], 
                AFE79_CURR_AGCPARAM_CH.atkthreshold[2], AFE79_CURR_AGCPARAM_CH.decaythreshold[2]));
            
            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetTimeConstantConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atkwinlength[0], AFE79_CURR_AGCPARAM_CH.atkwinlength[1], AFE79_CURR_AGCPARAM_CH.decaywinlength));
            
            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetAbsoluteNumCrossingConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atkNumHitsAbs[0], AFE79_CURR_AGCPARAM_CH.atkNumHitsAbs[1], 
                AFE79_CURR_AGCPARAM_CH.decayNumHitsAbs[0], AFE79_CURR_AGCPARAM_CH.decayNumHitsAbs[1]));
 
            AFE79_FUNC_EXEC(AFE79FNP(minMaxDsaAttnConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.minDsaAttn, AFE79_CURR_AGCPARAM_CH.maxDsaAttn));
            
            //Not sure if lnaEn Works, copied from below; This is very different from the Python Library
            if (AFE79_CURR_AGCPARAM_CH.lnaEn == 1)
            {
                //The following has some issues; have to fix
                /*
                AFE79_FUNC_EXEC(AFE79FNP(extLnaConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.singleDualBandMode, AFE79_CURR_AGCPARAM_CH.lnaGainMargin, AFE79_CURR_AGCPARAM_CH.enBandDet, AFE79_CURR_AGCPARAM_CH.tapOffPoint));

                for (uint8_t stageIndex = 0; stageIndex < AFE79_CURR_AGCPARAM_CH.maxLnaStage; stageIndex++)
                {
                    AFE79_FUNC_EXEC(AFE79FNP(extLnaGainConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.lnagain0[stageIndex], AFE79_CURR_AGCPARAM_CH.lnaphase0[stageIndex], AFE79_CURR_AGCPARAM_CH.lnagain1[stageIndex], AFE79_CURR_AGCPARAM_CH.lnaphase1[stageIndex]));
                }   
                */         
            }
            
            if (AFE79_CURR_AGCPARAM_CH.alcEn == 1)
            {
                alc_mode = AFE79_CURR_AGCPARAM_CH.alcMode;
                
                if (alc_mode == 0)
                {
                    AFE79_FUNC_EXEC(AFE79FNP(fltPtConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.fltPtMode, AFE79_CURR_AGCPARAM_CH.fltPtFmt));

                }

                else if (alc_mode >= 2 && alc_mode <= 4)
                {
                    AFE79_FUNC_EXEC(AFE79FNP(coarseFineConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.stepSize, AFE79_CURR_AGCPARAM_CH.nBitIndex, AFE79_CURR_AGCPARAM_CH.indexInvert, 
                        AFE79_CURR_AGCPARAM_CH.indexSwapIQ, AFE79_CURR_AGCPARAM_CH.sigBackOff, AFE79_CURR_AGCPARAM_CH.gainChangeIndEn));

                    if (alc_mode == 4)
                    {
                        ; //Have to add code to do this; CoarseIndexPinsAlcConfig function doesn't exist; The opcode also doesn't exist in DeviceConstants
                    }
                }
                                
                AFE79_FUNC_EXEC(AFE79FNP(alcConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.alcMode, AFE79_CURR_AGCPARAM_CH.totalGainRange, AFE79_CURR_AGCPARAM_CH.minAttnAlc, AFE79_CURR_AGCPARAM_CH.useMinAttnAgc));
            }
            AFE79_FUNC_EXEC(AFE79FNP(internalAgcConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.tdd_freeze_agc, AFE79_CURR_AGCPARAM_CH.blank_time_extcomp, AFE79_CURR_AGCPARAM_CH.en_agcfreeze_pin, AFE79_CURR_AGCPARAM_CH.lnaEn));
            
            if (AFE79_CURR_AGCPARAM_CH.alcEn == 1)
            {
                AFE79_FUNC_EXEC(AFE79FNP(agcStateControlConfig)(afeInst, rxChSel, 1 | (1 << 4) ));
            }
            else
            {
                AFE79_FUNC_EXEC(AFE79FNP(agcStateControlConfig)(afeInst, rxChSel, 1 | (1 << 5) ));
            }      
        }
        
        else if (AFE79_CURR_AGCPARAM_CH.agcMode >= 2 && AFE79_CURR_AGCPARAM_CH.agcMode <=5)
        {
            if (AFE79_CURR_AGCPARAM_CH.agcMode == 3 && chNo < 4 )//Don't do this for Fb
            {
                AFE79_FUNC_EXEC(AFE79FNP(setPinRxDsaSettings)(afeInst, chNo, AFE79_CURR_AGCPARAM_CH.dsaInit, AFE79_CURR_AGCPARAM_CH.dsaStep, AFE79_CURR_AGCPARAM_CH.maxInpPinDelay));//setPinDsaSettings(chNo >> 1); Not implemented
            }
            
            AFE79_FUNC_EXEC(AFE79FNP(agcGainStepSizeConfig)(afeInst, rxChSel, 
                AFE79_CURR_AGCPARAM_CH.atksize[0],AFE79_CURR_AGCPARAM_CH.atksize[1], AFE79_CURR_AGCPARAM_CH.decaysize[0], AFE79_CURR_AGCPARAM_CH.decaysize[1]));

            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atken[0], AFE79_CURR_AGCPARAM_CH.atken[1], 
                AFE79_CURR_AGCPARAM_CH.decayen[0], AFE79_CURR_AGCPARAM_CH.decayen[1], AFE79_CURR_AGCPARAM_CH.atken[2], AFE79_CURR_AGCPARAM_CH.decayen[2],
                AFE79_CURR_AGCPARAM_CH.atkthreshold[0], AFE79_CURR_AGCPARAM_CH.atkthreshold[1], AFE79_CURR_AGCPARAM_CH.decaythreshold[0], AFE79_CURR_AGCPARAM_CH.decaythreshold[1], 
                AFE79_CURR_AGCPARAM_CH.atkthreshold[2], AFE79_CURR_AGCPARAM_CH.decaythreshold[2]));
            
            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetTimeConstantConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atkwinlength[0], AFE79_CURR_AGCPARAM_CH.atkwinlength[1], AFE79_CURR_AGCPARAM_CH.decaywinlength));
            
            AFE79_FUNC_EXEC(AFE79FNP(agcDigDetAbsoluteNumCrossingConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.atkNumHitsAbs[0], AFE79_CURR_AGCPARAM_CH.atkNumHitsAbs[1], 
                AFE79_CURR_AGCPARAM_CH.decayNumHitsAbs[0], AFE79_CURR_AGCPARAM_CH.decayNumHitsAbs[1]));
 

            if (AFE79_CURR_AGCPARAM_CH.alcEn == 1)
            {
                alc_mode = AFE79_CURR_AGCPARAM_CH.alcMode;
                
                if (alc_mode == 0)
                {
                    AFE79_FUNC_EXEC(AFE79FNP(fltPtConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.fltPtMode, AFE79_CURR_AGCPARAM_CH.fltPtFmt));

                }

                else if (alc_mode >= 2 && alc_mode <= 4)
                {
                    AFE79_FUNC_EXEC(AFE79FNP(coarseFineConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.stepSize, AFE79_CURR_AGCPARAM_CH.nBitIndex, AFE79_CURR_AGCPARAM_CH.indexInvert, 
                        AFE79_CURR_AGCPARAM_CH.indexSwapIQ, AFE79_CURR_AGCPARAM_CH.sigBackOff, AFE79_CURR_AGCPARAM_CH.gainChangeIndEn));

                    if (alc_mode == 4)
                    {
                        ; //Have to add code to do this; CoarseIndexPinsAlcConfig function doesn't exist; The opcode also doesn't exist in DeviceConstants
                    }
                
                }
                AFE79_FUNC_EXEC(AFE79FNP(alcConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.alcMode, AFE79_CURR_AGCPARAM_CH.totalGainRange, AFE79_CURR_AGCPARAM_CH.minAttnAlc, AFE79_CURR_AGCPARAM_CH.useMinAttnAgc));

            }

            //The corresponding function is not present
            /*
            else if (AFE79_CURR_AGCPARAM_CH.phmEn == 1)
            {
                ;//Have to do this as well
            }
            */

            AFE79_FUNC_EXEC(AFE79FNP(externalAgcConfig)(afeInst, rxChSel, AFE79_CURR_AGCPARAM_CH.pin0sel, AFE79_CURR_AGCPARAM_CH.pin1sel, AFE79_CURR_AGCPARAM_CH.pin2sel, AFE79_CURR_AGCPARAM_CH.pin3sel, 
                AFE79_CURR_AGCPARAM_CH.pkDetPinLsbSel, AFE79_CURR_AGCPARAM_CH.pulseExpansionCount/10.0, AFE79_CURR_AGCPARAM_CH.pkDetOnPenultimateLsb));

            if (AFE79_CURR_AGCPARAM_CH.alcEn == 1)
            {
                AFE79_FUNC_EXEC(AFE79FNP(agcStateControlConfig)(afeInst, rxChSel, (1 << 6) + (1 << 4)));
            }
            else
            {
                AFE79_FUNC_EXEC(AFE79FNP(agcStateControlConfig)(afeInst, rxChSel, (1 << 6) + (1 << 5)));
            }  
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}


#endif
