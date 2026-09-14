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

/** @file tiAfe79_dsaAndNco.c
 * 	@brief	This file has DSA and NCO related functions. <br>
 * 		<b> Version 2.6:</b> <br>
 * 		1. Fixed issues with updateRxNco, readRxNco and readTxNco CAFE functions in FCW mode.
 * 		<b> Version 2.2:</b> <br>
 * 		1.enWifiAccesMode placed in updateTxGainParam to enable the writes.<br>
 * 		2. A bug in udpateTxNco  which is visible in FCW mode only got resolved.<br>
 * 		3. A bug in readTxNco which is evident in FCW mode only got resolved.<br>
 * 		<b> Version 2.2:</b> <br>
 * 		1. Updated setTxDigGain and txDsaIdxGainSwap along with the description and parameter validity.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Removed redundant functions related to older device version.<br>
 * 		3. Fixed data types of parameters if function: updateTxGain<br>
 * 		4. Removed redundant writes in functions.<br>
 * 		5. Changed the function input definition of updateTxNco, updateRxNco and updateFbNco in FCW mode from KHz to FCW word. This is done to give finer control of frequency preventing rounding errors which is expected in FCW mode.<br>
 * 		6. Changed the C macros for all the spi wrapper and executeMacro function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 * 		7. Fixed bugs in readTxNco.<br>
 */

#include <stdint.h>
#include <math.h>

#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeCommonMacros.h"

#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"
#include "tiAfe79_afeParameters.h"
#include "tiAfe79_macro.h"

#include "tiAfe79_dsaAndNco.h"


/**
    @brief Set the RX Digital DSA
    @details Sets the RX Digital DSA.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param bandNo Select the RX Band. 0-Band0, 1-Band1<br>
    @param dsaSetting (dsaSetting*0.5-3)dB is the applied DSA gain (if positive) and attenuation (if negative). Range for dsaSetting is 0 to 47.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDigGain)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bandNo, uint8_t dsaSetting)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(dsaSetting <= AFE_RX_DSA_MAX_DIG_DSA_INDEX);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 1 << chNo, 0x0, 0x7)); /*rxdig*/
    if (bandNo == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x188, dsaSetting & 0xff, 0x0, 0x5)); /*diggain_rx_b0_gain_idx*/
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x288, dsaSetting & 0xff, 0x0, 0x5)); /*diggain_rx_b1_gain_idx*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0013, (0x40 << (chNo >> 1)), 0x0, 0x7));
    if ((chNo & 1) == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x00, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x01, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x00, 0x0, 0x7));
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x00, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x01, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x00, 0x0, 0x7));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0013, 0x00, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Set the RX DSA Mode
    @details Sets the RX DSA Control Mode.
    @param afeInst AFE ID
    @param topNo Select the RX Channel<br>
            0 for RXAB<br>
            1 for RXCD
    @param mode DSA Control Mode Setting.<br>
        1-8-Pin Based DSA Control<br>
        2-Internal AGC<br>
        3-SPI AGC<br>
        4-4-Pin Based DSA Control
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDsaMode)(AFE79_INST_TYPE afeInst, uint8_t topNo, uint8_t mode)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topNo < (AFE79_NUM_RX_CHANNELS / 2));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << topNo, 0x0, 0x7)); /*dsa_page1*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xd0, (mode) & 0xff, 0x0, 0x2)); /*gain_ctrl*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Configure Settings related to the 4-pin based DSA control mode.
    @details Configure Settings related to the 4-pin based DSA control mode. Effective DSA attenuation is ((pin_value * dsaStep) +dsaInit)*0.5dB.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param dsaInit Offset of the DSA.
    @param dsaStep DSA Step Value.
    @param maxDelay This is the delay after the change of pin change to latch the values. This is to account for the latency variation between pins.<br>
            This should be the maximum latency variation between the earliest pin and the last pin.
            <br>This is the common control for 2RX. The unit is in cycles of FadcRx/8 clock. Supported values: 0<=maxDelay<=255.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setPinRxDsaSettings)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaInit, uint8_t dsaStep, uint8_t maxDelay)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(dsaInit < AFE_RX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(dsaStep < AFE_RX_DSA_MAX_ANA_DSA_INDEX);   
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << (chNo >> 1), 0x0, 0x7)); /*dsa_page1*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xe1, (AFE79_CURR_AGCPARAM_CH.maxDsaAttn) & 0xff, 0x0, 0x5)); /*fdsa_max_attn*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xe0, (maxDelay) & 0xff, 0x0, 0x2));   /*fdsa_pin_uncert_cyc*/

    if (chNo % 2 == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12c, (dsaStep) & 0xff, 0x0, 0x6)); /*fdsa_offset_val_A*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12d, (dsaInit) & 0xff, 0x0, 0x5)); /*fdsa_init_val_A*/
    }

    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x17c, (dsaStep) & 0xff, 0x0, 0x6)); /*fdsa_offset_val_B*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x17d, (dsaInit) & 0xff, 0x0, 0x5)); /*fdsa_init_val_B*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#endif

/**
    @brief Set the TX Digital DSA
    @details Sets the TX Digital DSA.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param bandNo Select the TX Band. 0-Band0, 1-Band1<br>
    @param dig_gain dig_gain is integer value ranging from +24 to -167, that maps to +3dBfs to -20.875dBfs gain. (negative values refers to attenuation)<br>
                    The needed attenuation*8 is the dig_gain value to be passed.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setTxDigGain)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t bandNo, int16_t dig_gain)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(dig_gain <= 24);
    AFE79_PARAMS_VALID(dig_gain >= -167);
    uint8_t dig_gain_val;
    dig_gain_val = 24 - dig_gain;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x10 << (chNo >> 1), 0x0, 0x7)); /*dsa_page0*/
    if (chNo % 2 == 0)
    {
        if (bandNo == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xd0, (dig_gain_val) & 0xff, 0x0, 0x7)); /*txa_dsa_dig0_gain*/
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xd8, (dig_gain_val) & 0xff, 0x0, 0x7)); /*txa_dsa_dig1_gain*/
        }
    }
    else
    {
        if (bandNo == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xd4, (dig_gain_val) & 0xff, 0x0, 0x7)); /*txb_dsa_dig0_gain*/
        }

        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xdc, (dig_gain_val) & 0xff, 0x0, 0x7)); /*txb_dsa_dig1_gain*/
        }
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Set the TX DSA Gain Swap Attenuation
    @details Set the TX DSA Gain Swap Attenuation. There are 2 Gain Swap settings possible which can be chosen using the pin.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param anaAttn0	Analog Attenuation for Swap Attenuation 0, from 0 to 29. (1dB steps)
    @param anaAttn1	Analog Attenuation for Swap Attenuation 1, from 0 to 29. (1dB steps)
    @param digB0Gain0	Digital Attenuation*8 for Swap Attenuation 0 for band 0<br>
                Is integer value ranging from +24 to -167, that maps to +3dBfs to -20.875dBfs gain (negative values refers to attenuation)<br>
                The needed attenuation*8 is the dig_gain value to be passed
    @param digB0Gain1	Digital Attenuation*8 for Swap Attenuation 1 for band 0<br>
                Is integer value ranging from +24 to -167, that maps to +3dBfs to -20.875dBfs gain (negative values refers to attenuation)<br>
                The needed attenuation*8 is the dig_gain value to be passed
    @param digB1Gain0	Digital Attenuation*8 for Swap Attenuation 0 for band 1<br>
                Is integer value ranging from +24 to -167, that maps to +3dBfs to -20.875dBfs gain (negative values refers to attenuation)<br>
                The needed attenuation*8 is the dig_gain value to be passed
    @param digB1Gain1	Digital Attenuation*8 for Swap Attenuation 1 for band 1<br>
                Is integer value ranging from +24 to -167, that maps to +3dBfs to -20.875dBfs gain (negative values refers to attenuation)<br>
                The needed attenuation*8 is the dig_gain value to be passed
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(txDsaIdxGainSwap)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t anaAttn0, uint8_t anaAttn1, int8_t digB0Gain0, int8_t digB0Gain1, int8_t digB1Gain0, int8_t digB1Gain1)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(anaAttn0 <= AFE_TX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(anaAttn1 <= AFE_TX_DSA_MAX_ANA_DSA_INDEX);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << (chNo >> 1), 0x0, 0x7)); /*dsa_page1*/
    if (chNo % 2 == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1c4, (anaAttn0) & 0xff, 0x0, 0x5)); /*txa_dsa_index_swap0		*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1d0, (anaAttn1) & 0xff, 0x0, 0x5)); /*txa_dsa_index_swap1		*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1c8, (24 - digB0Gain0) & 0xff, 0x0, 0x7)); /*txa_dsa_dig0_gain_swap0	*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1d4, (24 - digB0Gain1) & 0xff, 0x0, 0x7)); /*txa_dsa_dig0_gain_swap1	*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1cc, (24 - digB1Gain0) & 0xff, 0x0, 0x7)); /*txa_dsa_dig1_gain_swap0	*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1d8, (24 - digB1Gain1) & 0xff, 0x0, 0x7)); /*txa_dsa_dig1_gain_swap1	*/
    }

    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x214, (anaAttn0) & 0xff, 0x0, 0x5)); /*txb_dsa_index_swap0		*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x220, (anaAttn1) & 0xff, 0x0, 0x5)); /*txb_dsa_index_swap1*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x218, (24 - digB0Gain0) & 0xff, 0x0, 0x7)); /*txb_dsa_dig0_gain_swap0*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x224, (24 - digB0Gain1) & 0xff, 0x0, 0x7)); /*txb_dsa_dig0_gain_swap1*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x21c, (24 - digB1Gain0) & 0xff, 0x0, 0x7)); /*txb_dsa_dig1_gain_swap0*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x228, (24 - digB1Gain1) & 0xff, 0x0, 0x7)); /*txb_dsa_dig1_gain_swap1*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the TX DSA Update Mode
    @details This function sets the Params of applying TX DSA through Macro.
    @param afeInst AFE ID
    @param mode Mode of TX DSA Update<br>
                0-oneshot	(Immediately update)<br>
                1-smoothening (Enable smooth transition of DSA)<br>
                2-TDD mode (Set DSA on TX TDD off state)
    @param transitTime	This value/8 us is the time taken for each step in smoothening mode.
    @param maxAnaDsa	This is the maximum analog DSA (in dB) beyond which the digital gain/attenuation will be applied. Maximum value of this is 29
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxGainParam)(AFE79_INST_TYPE afeInst, uint8_t mode, uint8_t transitTime, uint8_t maxAnaDsa)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(maxAnaDsa <= AFE_TX_DSA_MAX_ANA_DSA_INDEX);
    uint8_t byteList[2];
    uint8_t numOfOperands = 0;
    byteList[numOfOperands] = (mode);
    numOfOperands++;
    byteList[numOfOperands] = (transitTime);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_TX_DIG_PARAM)); // MacroConsts.MACRO_OPCODE_UPDATE_TX_DIG_PARAM);
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, 0x8, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x8, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x03ac, maxAnaDsa, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x03ad, maxAnaDsa, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x0, 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 0));
    return TI_AFE_RET_EXEC_PASS;
}

#endif

/**
    @brief Set the TX DSA.
    @details This function sets the TX DSA (analog+digital) through Macro.<br>
            When the value is less or equal to than the maxAnaDsa setting in updateTxGainParam function, the integer part of the value will be applied to analog and fractional part will be applied to digital.<br>
            When the value is more than the maxAnaDsa setting in updateTxGainParam function, maxAnaDsa will be applied to the analog and rest will be applied in digital.<br>
            For single band case, set same value as band0 to band1 and apply gain validity accordingly.
    @param afeInst AFE ID
    @param txChainSel Selects if the DSA attenuation needs to be applied to AB or CD channels.<br>
                0-AB<br>
                1-CD
    @param gainValidity	Selects where all to set the DSA. This is a bit wise field.<br>
                bit 0- TXA/C Band0<br>
                bit 1- TXA/C Band1<br>
                bit 2- TXB/D Band0<br>
                bit 3- TXB/D Band1
    @param tx0B0Dsa TXA/C Band 0 DSA setting *8. For getting attenuation of 2.25dB, this value should be 18. Supported Range is 0-320.
    @param tx0B1Dsa TXA/C Band 1 DSA setting *8. For getting attenuation of 2.25dB, this value should be 18. Supported Range is 0-320.
    @param tx1B0Dsa TXB/D Band 0 DSA setting *8. For getting attenuation of 2.25dB, this value should be 18. Supported Range is 0-320.
    @param tx1B1Dsa TXB/D Band 1 DSA setting *8. For getting attenuation of 2.25dB, this value should be 18. Supported Range is 0-320.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxGain)(AFE79_INST_TYPE afeInst, uint8_t txChainSel, uint8_t gainValidity, uint16_t tx0B0Dsa, uint16_t tx0B1Dsa, uint16_t tx1B0Dsa, uint16_t tx1B1Dsa)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(txChainSel < (AFE79_NUM_TX_CHANNELS >> 1));
    AFE79_PARAMS_VALID(tx0B0Dsa <= (AFE_TX_DSA_MAX_ANA_PLUS_DIG_DSA_DB * 8));
    AFE79_PARAMS_VALID(tx0B1Dsa <= (AFE_TX_DSA_MAX_ANA_PLUS_DIG_DSA_DB * 8));
    AFE79_PARAMS_VALID(tx1B0Dsa <= (AFE_TX_DSA_MAX_ANA_PLUS_DIG_DSA_DB * 8));
    AFE79_PARAMS_VALID(tx1B1Dsa <= (AFE_TX_DSA_MAX_ANA_PLUS_DIG_DSA_DB * 8));
    AFE79_PARAMS_VALID(gainValidity <= 0xf);

    uint8_t byteList[10];
    uint8_t numOfOperands = 0;

    byteList[numOfOperands] = (txChainSel);
    numOfOperands++;
    byteList[numOfOperands] = (gainValidity);
    numOfOperands++;

    byteList[numOfOperands] = (tx0B0Dsa & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (tx0B0Dsa >> 8);
    numOfOperands++;
    byteList[numOfOperands] = (tx0B1Dsa & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (tx0B1Dsa >> 8);
    numOfOperands++;
    byteList[numOfOperands] = (tx1B0Dsa & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (tx1B0Dsa >> 8);
    numOfOperands++;
    byteList[numOfOperands] = (tx1B1Dsa & 0xff);
    numOfOperands++;
    byteList[numOfOperands] = (tx1B1Dsa >> 8);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_TX_GAIN)); // MacroConsts.MACRO_OPCODE_UPDATE_TX_GAIN
    return TI_AFE_RET_EXEC_PASS;
}


/**
    @brief Sets the TX NCO values in Multi NCO mode
    @details Sets the value of one of the 16 NCOs for mentioned channel in Multi NCO mode.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param mixer Mixer Frequency.<br>
            Should pass frequency word value.<br>
            The value can be calculate using the equation: mixer =  (uint32_t) (2^32*mixerFrequency/Fdac).
    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0353 + 4 * nco, (mixer >> 24) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0352 + 4 * nco, (mixer >> 16) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0351 + 4 * nco, (mixer >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0350 + 4 * nco, mixer & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, 0x00, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Sets the RX NCO values in Multi NCO mode
    @details Sets the value of one of the 16 NCOs for mentioned channel in Multi NCO mode.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param mixer Mixer Frequency.<br>
            Should pass frequency word value.<br>
            The value can be calculate using the equation: mixer =  (uint32_t) (2^32*mixerFrequency/Fadc).
    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x1 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a3 + 4 * nco, (mixer >> 24) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a2 + 4 * nco, (mixer >> 16) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a1 + 4 * nco, (mixer >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a0 + 4 * nco, mixer & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x00, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Sets the FB NCO values in Multi NCO mode
    @details Sets the value of one of the 16 NCOs for mentioned channel in Multi NCO mode.
    @param afeInst AFE ID
    @param chNo Select the FB Channel<br>
            0 for FBA<br>
            1 for FBB<br>
    @param mixer Mixer Frequency.<br>
            Should pass frequency word value.<br>
            The value can be calculate using the equation: mixer =  (uint32_t) (2^32*mixerFrequency/Fadc).
    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNcoMultiNcoMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x10 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a3 + 4 * nco, (mixer >> 24) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a2 + 4 * nco, (mixer >> 16) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a1 + 4 * nco, (mixer >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00a0 + 4 * nco, mixer & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0180, 0x00, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Changes the TX NCO Phase values in Infinite NCO mode
    @details Changes the phase value of one of the 16 NCOs for mentioned channel in Infinite NCO mode. Make sure that sysParams.txChainDirectCtrl is set to 1 before using this function.
    @param afeInst AFE ID

    @param phaseNo Value from 0 to 2^16-1. The phase offset is phaseNum*(360/2^16) degrees.<br>

    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15

    @param chNo TX Channel Number
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0391 + 2 * nco, (phaseNo >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0390 + 2 * nco, phaseNo & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Changes the RX NCO Phase values.
    @details Changes the phase value of one of the 16 NCOs for mentioned channel in Infinite NCO mode.
    @param afeInst AFE ID

    @param phaseNo Value from 0 to 2^16-1. The phase offset is phaseNum*(360/2^16) degrees.<br>

    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15

    @param chNo RX Channel Number
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x01 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00e1 + 2 * nco, (phaseNo >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00e0 + 2 * nco, phaseNo & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Changes the FB NCO Phase values.
    @details Changes the phase value of one of the 16 NCOs for mentioned channel in Infinite NCO mode.
    @param afeInst AFE ID

    @param phaseNo Value from 0 to 2^16-1. The phase offset is phaseNum*(360/2^16) degrees.<br>

    @param nco NCO Number. 0-NCO0, 1-NCO1, 2-NCO2, 3-NCO3, 4-NCO4, 5-NCO5, 6-NCO6, 7-NCO7, 8-NCO8, 9-NCO9, 10-NCO10<br>
                        11-NCO11, 12-NCO12, 13-NCO13, 14-NCO14, 15-NCO15

    @param chNo FB Channel Number
            0 for FBA<br>
            1 for FBB

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNcoPhase)(AFE79_INST_TYPE afeInst, uint8_t nco, uint16_t phaseNo, uint8_t chNo)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(nco < 16);
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(AFE79_CURR_SYSPARAM.ncoFreqMode == 1);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x10 << chNo, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00e1 + 2 * nco, (phaseNo >> 8) & 0xff, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00e0 + 2 * nco, phaseNo & 0xff, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}


#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Set the TX NCO for Dual band.
    @details This function updates the TX NCO and should be used only single band of operation.<br>
                For all the mixer frequency values, should pass value in KHz in 1KHz ncoFreqMode and the frequency word value in FCW mode. The Mode is determined by the ncoFreqMode set in Latte while generating the bringup script.<br>
                In FCW mode, the value can be calculate using the equation: mixer =  (2^32*mixerFrequency/Fdac).<br>
                In case second NCO is not used, set the band1 parameters to same value as band0.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @param band0Nco0 Band0, NCO0 Mixer frequency.
    @param band1Nco0 Band1, NCO0 Mixer frequency.
    @param band0Nco1 Band0, NCO1 Mixer frequency.
    @param band1Nco1 Band1, NCO1 Mixer frequency.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNcoDb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t nco, uint32_t band0Nco0, uint32_t band1Nco0, uint32_t band0Nco1, uint32_t band1Nco1)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(nco < 2);

    uint32_t averageMixerFreq;
    uint32_t Fdac = AFE79_CURR_SYSPARAM.Fdac;
    uint8_t byteList[18];

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x80, 0x0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x81d, 0x07, 0x0, 2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x81c, 0xae, 0x0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x00, 0x0, 7));

    uint8_t numOfOperands = 0;
    uint8_t byteListTxNCO[4];
    AFE79_CURR_SYSPARAM.txNco[0][chNo][0] = band0Nco0;
    AFE79_CURR_SYSPARAM.txNco[0][chNo][1] = band1Nco0;
    AFE79_CURR_SYSPARAM.txNco[1][chNo][0] = band0Nco1;
    AFE79_CURR_SYSPARAM.txNco[1][chNo][1] = band1Nco1;
    averageMixerFreq = (band0Nco0 >> 2) + (band1Nco0 >> 2) + (band0Nco1 >> 2) + (band1Nco1 >> 2); // Average Mixer frequency
    band0Nco0 = band0Nco0 % Fdac;
    band1Nco0 = band1Nco0 % Fdac;
    band0Nco1 = band0Nco1 % Fdac;
    band1Nco1 = band1Nco1 % Fdac;
    byteList[numOfOperands] = chNo;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(band0Nco0 & 0xffffffff, 4, byteListTxNCO));
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListTxNCO[i];
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(band1Nco0 & 0xffffffff, 4, byteListTxNCO));
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListTxNCO[i];
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(band0Nco1 & 0xffffffff, 4, byteListTxNCO));
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListTxNCO[i];
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(band1Nco1 & 0xffffffff, 4, byteListTxNCO));
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListTxNCO[i];
        numOfOperands++;
    }

    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_SYSTEM_TX_CHANNEL_FREQUENCY_CONFIGURATION_ALL_BANDS));
    chNo = 1 << chNo;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, chNo << 4, 0x0, 7)); /*txdig*/
    if (nco == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x0, 0x0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x1, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x0, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x0, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x0, 0x0, 0x0));
    }
    else if (nco == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x0, 0x0, 0x0));
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x0, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x1, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x0, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x80, 0x0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x81d, 0x07, 0x0, 2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x81c, 0xff, 0x0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x00, 0x0, 7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, chNo, 0x0, 0x7)); /*txdh*/
    if (AFE79_CURR_SYSPARAM.chipVersion <= 0x13)
    {
        if (averageMixerFreq <= 500000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x10, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x1F, 0x0, 0x7));
        }
        else if (averageMixerFreq < 2300000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0xf0, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x00, 0x0, 0x7));
        }
        else if (averageMixerFreq < 6000000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x00, 0x0, 0x7));
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x3f, 0x0, 0x7));
        }
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the RX NCO Select.
    @details This function sets the override to the RX NCO select. This is useful only when more than 1 NCO is used.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param BandId NCO number. 0-NCO0, 1-NCO1.
    @param ovr 1 will override the pin. 0 will give control to the pin.
    @param NCOId NCO number which is to be selected. Supported range is 0 to numRxNco set in the initial configuration.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(rxNCOSel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t BandId, uint8_t ovr, uint8_t NCOId)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(BandId < AFE79_NUM_BANDS_PER_RX);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, (1 << chNo) & 0xff, 0x0, 0x7)); /*rxdig*/
    if (BandId == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2219, (ovr) & 0xff, 0x0, 0x0));   /*b0_nco_switch_ovr_en*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x221a, (NCOId) & 0xff, 0x0, 0x3)); /*b0_nco_switch_ovr_val*/
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x221d, (ovr) & 0xff, 0x0, 0x0));   /*b1_nco_switch_ovr_en*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x221e, (NCOId) & 0xff, 0x0, 0x0)); /*b1_nco_switch_ovr_val*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the FB NCO Select.
    @details This function sets the override to the FB NCO select. This is useful only when more than 1 NCO is used.
    @param afeInst AFE ID
    @param topno Select the FB Channel<br>
            0 for FBAB<br>
            1 for FBCD
    @param ovr 1 will override the pin. 0 will give control to the pin.
    @param NCOId NCO number which is to be selected. Supported range is 0 to numFbNco set in the initial configuration.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(fbNCOSel)(AFE79_INST_TYPE afeInst, uint8_t topno, uint8_t ovr, uint8_t NCOId)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(topno < AFE79_NUM_FB_CHANNELS);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, (((1 << (topno))) << 4) & 0xff, 0x0, 0x7)); /*fbdig*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2219, (ovr) & 0xff, 0x0, 0x0));                 /*nco_switch_ovr_en*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x221a, (NCOId) & 0xff, 0x0, 0x3));               /*nco_switch_ovr_val*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the FB Analog DSA for pin select mode.
    @details AFE has a feature to select the FB DSA value from a set of pre-programmed values using pins. This function sets the FB Analog DSA index. AFE79_CURR_SYSPARAM.txToFbMode should be set as needed in the initialization.
    @param afeInst AFE ID
    @param pinNo Select the pin value for which to program the DSA. The range of this is 0-3.
    @param dsaSetting Analog dsaSetting is FB DSA for the corresponding pin value. dsaSetting*0.5 is the attenuation in dB applied when the pin value is pinNo.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setFbDsaPerTx)(AFE79_INST_TYPE afeInst, uint8_t pinNo, uint8_t dsaSetting)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(pinNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(dsaSetting <= AFE_FB_DSA_MAX_ANA_DSA_INDEX);
    AFE79_PARAMS_VALID(pinNo <= 3);
    if (AFE79_CURR_SYSPARAM.txToFbMode == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x10, 0, 7)); /*dsa_page0*/
        if (pinNo == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x078, dsaSetting, 0, 7)); /*spi_agc_dsa_fb_0*/
        }
        else if (pinNo == 1)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x07c, dsaSetting, 0, 7)); /*spi_agc_dsa_fb_1*/
        }
        else if (pinNo == 2)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x080, dsaSetting, 0, 7)); /*spi_agc_dsa_fb_2*/
        }
        else if (pinNo == 3)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x084, dsaSetting, 0, 7)); /*spi_agc_dsa_fb_3*/
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x00, 0, 7));
    }
    else if (AFE79_CURR_SYSPARAM.txToFbMode == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x20, 0, 7));
        if (pinNo == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x078, dsaSetting, 0, 7));
        }
        else if (pinNo == 1)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x07c, dsaSetting, 0, 7));
        }
        else if (pinNo == 2)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x080, dsaSetting, 0, 7));
        }
        else if (pinNo == 3)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x084, dsaSetting, 0, 7));
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x00, 0, 7));
    }
    else
    {
        if (pinNo == 0 || pinNo == 1)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x10, 0, 7));
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x20, 0, 7));
        }
        if (pinNo == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x078, dsaSetting, 0, 7));
        }
        else if (pinNo == 1)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x07c, dsaSetting, 0, 7));
        }
        else if (pinNo == 2)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x080, dsaSetting, 0, 7));
        }
        else if (pinNo == 3)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x084, dsaSetting, 0, 7));
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x00, 0, 7));
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Enable the pin select based Mode for FB DSA.
    @details AFE has a feature to select the FB DSA value from a set of pre-programmed values using pins. This function sets the FB Analog DSA index.
    @param afeInst AFE ID
    @param en en as 1 will enable the feature to set FB DSA per TX based on the GPIO
    @param txToFbMode Selects the mode.<br>
                0 - Only FBAB used.<br>
                1 - Only FBCD used.<br>
                2 - Both FBAB and FBCD used..
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(fbDsaPerTxEn)(AFE79_INST_TYPE afeInst, uint8_t en, uint8_t txToFbMode)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(en < 2);
    AFE79_PARAMS_VALID(txToFbMode < 3);

    AFE79_CURR_SYSPARAM.txToFbMode = txToFbMode;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x015, 0x80, 0, 7)); /*timing_controller*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c0, (txToFbMode >> 1) & 1, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c1, txToFbMode & 1, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c2, 0, 0, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c3, 1, 0, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c4, 2, 0, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0c5, 3, 0, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x015, 0x00, 0, 7)); /*timing_controller*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x10, 0, 7)); /*dsa_page0*/
    if ((txToFbMode == 0) || (txToFbMode == 2))
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x079, 1, 0, 7)); /*enable_fbmuxsel_for_fbdsa*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x20, 0, 7)); /*dsa_page0*/
    if ((txToFbMode == 1) || (txToFbMode == 2))
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x079, 1, 0, 7)); /*enable_fbmuxsel_for_fbdsa*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x013, 0x00, 0, 7));
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Set the TX Analog DSA
    @details Sets the TX Analog DSA.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param dsaSetting Analog DSA Index. Attenuation applied is dsaSetting*1dB
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setTxDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(dsaSetting <= AFE_TX_DSA_MAX_ANA_DSA_INDEX);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x10 << (chNo >> 1), 0x0, 0x7)); /*dsa_page0*/
    if (chNo % 2 == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xc8, (dsaSetting) & 0xff, 0x0, 0x5)); /*txa_dsa_index*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xc8, (dsaSetting) & 0xff, 0x0, 0x5)); /*Writing Twice is needed for consistency.*/
    }

    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xcc, (dsaSetting) & 0xff, 0x0, 0x5)); /*txb_dsa_index*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xcc, (dsaSetting) & 0xff, 0x0, 0x5)); /*Writing Twice is needed for consistency.*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the FB Analog DSA
    @details Sets the FB Analog DSA.
    @param afeInst AFE ID
    @param chNo Select the FB Channel<br>
            0 for FBAB<br>
            1 for FBCD
    @param dsaSetting Analog DSA Index. Attenuation applied is dsaSetting*0.5dB
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setFbDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(dsaSetting <= AFE_FB_DSA_MAX_ANA_DSA_INDEX);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x10 << chNo, 0x0, 0x7));      /*dsa_page0*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6c, dsaSetting & 0xff, 0x0, 0x5)); /*spi_agc_dsa_fb*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the RX Analog DSA
    @details Sets the RX Analog DSA.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param dsaSetting Analog DSA Index. Attenuation applied is dsaSetting*0.5dB
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setRxDsa)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t dsaSetting)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(dsaSetting <= AFE_RX_DSA_MAX_ANA_DSA_INDEX);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x40 << (chNo >> 1), 0x0, 0x7)); /*dsa_page1*/
    if (chNo % 2 == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x124, dsaSetting & 0xff, 0x0, 0x5)); /*spi_agc_dsa_A*/
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x174, dsaSetting & 0xff, 0x0, 0x5)); /*spi_agc_dsa_B*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the TX NCO for single band.
    @details This function updates the TX NCO and should be used only single band of operation.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param mixer Mixer frequency.<br>
                Should pass value in KHz in 1KHz ncoFreqMode and the frequency word value in FCW mode. The Mode is determined by the ncoFreqMode set in Latte while generating the bringup script.<br>
                In FCW mode, the value can be calculate using the equation: mixer =  (uint32_t) (2^32*mixerFrequency/Fdac).
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(nco < 2);
    uint64_t mixerVal;
    uint64_t ncoFreq;
    uint32_t Fdac = AFE79_CURR_SYSPARAM.Fdac;
    uint8_t newNyquistNo;
    uint8_t bringupNyquistNo = ((AFE79_CURR_SYSPARAM.txNco[0][chNo][0] * 2) / Fdac);

    if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1) /*FCW mode*/
    {
        ncoFreq = ((uint64_t)mixer * (uint64_t)Fdac) / (0x100000000);
        newNyquistNo = mixer >> 31;
    }
    else
    {
        ncoFreq = mixer;
        newNyquistNo = ((mixer * 2) / Fdac);
    }
    if (newNyquistNo != bringupNyquistNo){ // Checking if the nyquist frequency
        afeLogErr("%s", "The new Nyquist frequency and the frequency set in bringup should be same");
        AFE79_PARAMS_VALID(newNyquistNo == bringupNyquistNo);
    }

    if (nco == 0)
    {
        AFE79_CURR_SYSPARAM.txNco[0][chNo][0] = ncoFreq;
    }
    else if (nco == 1)
    {
        AFE79_CURR_SYSPARAM.txNco[1][chNo][0] = ncoFreq;
    }
    mixerVal = mixer;

    AFE79_FUNC_EXEC(AFE79FNP(updateSystemTxChannelFreqConfig)(afeInst, chNo, nco, (mixerVal), 1, 1));
    chNo = 1 << chNo;
    AFE79_FUNC_EXEC(AFE79FNP(doSystemTuneSelective)(afeInst, 0, 0, chNo, 0x20));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, chNo << 4, 0x0, 7)); /*txdig*/
    if (nco == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x0, 0x0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x1, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x130, 0x0, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x0, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x230, 0x0, 0x0, 0x0));
    }

    else if (nco == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x131, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x0, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x1, 0x0, 0x0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x231, 0x0, 0x0, 0x0));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x0, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x1, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x773, 0x0, 0x0, 0x0)); /*config_fmixer_update_pulse*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, chNo, 0x0, 0x7)); /*txdh*/
    if ((AFE79_CURR_SYSPARAM.chipVersion <= 0x13) || (AFE79_CURR_SYSPARAM.chipVersion == 0x30) || (AFE79_CURR_SYSPARAM.chipVersion == 0x31))
    {
        if (mixer <= 500000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x10, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x1f, 0x0, 0x7));
        }
        else if (mixer < 2300000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0xf0, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x00, 0x0, 0x7));
        }
        else if (mixer < 6000000)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x00, 0x0, 0x7));
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x107, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x105, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x104, 0x40, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10a, 0x01, 0x0, 0x3));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x109, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x108, 0x3f, 0x0, 0x7));
        }
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x13, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the RX NCO.
    @details This function updates the RX NCO.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param mixer Mixer frequency.<br>
                Should pass value in KHz in 1KHz ncoFreqMode and the frequency word value in FCW mode. The Mode is determined by the ncoFreqMode set in Latte while generating the bringup script.<br>
                In FCW mode, the value can be calculate using the equation: mixer =  (uint32_t) (2^32*(mixerFrequency%FadcRx)/FadcRx).
    @param band Band number. 0-band0, 1-band1.
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t band, uint8_t nco)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(band < AFE79_NUM_BANDS_PER_RX);
    uint32_t mixerVal = 3000;
    uint32_t Fadc = AFE79_CURR_SYSPARAM.FadcRx;
    uint64_t ncoFreq;
    uint8_t byteList[7];
    uint8_t numOfOperands = 0;
    uint8_t byteListRxNCO[4];
    uint8_t newNyquistNo;
    uint8_t bringupNyquistNo = ((AFE79_CURR_SYSPARAM.rxNco[0][chNo][0] * 2) / Fadc);

    if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1) /*FCW mode*/
    {
        ncoFreq = ((uint64_t)mixer * (uint64_t)Fadc) / (0x100000000);
        ncoFreq += Fadc * (bringupNyquistNo >> 1);
        newNyquistNo = (mixer >> 31);
        if (newNyquistNo != (bringupNyquistNo & 1)){ // Checking if the nyquist frequency
            afeLogErr("%s", "The new Nyquist frequency and the frequency set in bringup should be same");
            AFE79_PARAMS_VALID(newNyquistNo == (bringupNyquistNo & 1));
        }
    }
    else
    {
        ncoFreq = mixer;
        mixer = mixer % Fadc;
        newNyquistNo = ((ncoFreq * 2) / Fadc);
        if (newNyquistNo != bringupNyquistNo){ // Checking if the nyquist frequency
            afeLogErr("%s", "The new Nyquist frequency and the frequency set in bringup should be same");
            AFE79_PARAMS_VALID(newNyquistNo == bringupNyquistNo);
        }
    }
    if (nco == 0)
    {
        AFE79_CURR_SYSPARAM.rxNco[0][chNo][band] = ncoFreq;
    }
    else if (nco == 1)
    {
        AFE79_CURR_SYSPARAM.rxNco[1][chNo][band] = ncoFreq;
    }

    mixerVal = (mixer & 0xffffffff);
    if (AFE79_CURR_SYSPARAM.chipVersion <= 0x12)
    {
        byteList[numOfOperands] = (1 << chNo);
        numOfOperands++;
        byteList[numOfOperands] = (1 << (nco + (band << 1)));
        numOfOperands++;
    }
    else
    {
        byteList[numOfOperands] = (chNo);
        numOfOperands++;
        byteList[numOfOperands] = (nco + (band << 1));
        numOfOperands++;
    }
    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(mixerVal, 4, byteListRxNCO));
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListRxNCO[i];
        numOfOperands++;
    }
    byteList[numOfOperands] = (3);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_SYSTEM_RX_CHANNEL_FREQUENCY_CONFIGURATION)); // MacroConsts.MACRO_OPCODE_UPDATE_SYSTEM_RX_CHANNEL_FREQUENCY_CONFIGURATION);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set the FB NCO.
    @details This function updates the FB NCO.
    @param afeInst AFE ID
    @param chNo Select the FB Channel<br>
            0 for FBAB<br>
            1 for FBCD
    @param mixer Mixer frequency.<br>
                Should pass value in KHz in 1KHz ncoFreqMode and the frequency word value in FCW mode. The Mode is determined by the ncoFreqMode set in Latte while generating the bringup script.<br>
                In FCW mode, the value can be calculate using the equation: mixer =  (uint32_t) (2^32*(mixerFrequency%FadcRx)/FadcRx).<br>
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t mixer, uint8_t nco)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    uint32_t mixerVal = 3000;
    uint32_t Fadc = AFE79_CURR_SYSPARAM.FadcFb;
    uint64_t ncoFreq;
    uint8_t byteList[7];
    uint8_t byteListFbNCO[4];
    uint8_t numOfOperands = 0;
    uint8_t newNyquistNo;
    uint8_t bringupNyquistNo = ((AFE79_CURR_SYSPARAM.fbNco[chNo][0] * 2) / Fadc);

    if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1) /*FCW mode*/
    {
        ncoFreq = ((uint64_t)mixer * (uint64_t)Fadc) / (0x100000000);
        ncoFreq += Fadc * (bringupNyquistNo >> 1);
        newNyquistNo = (mixer >> 31);
        if (newNyquistNo != (bringupNyquistNo & 1)){ // Checking if the nyquist frequency
            afeLogErr("%s", "The new Nyquist frequency and the frequency set in bringup should be same");
            AFE79_PARAMS_VALID(newNyquistNo == (bringupNyquistNo & 1));
        }

    }
    else
    {
        ncoFreq = mixer;
        mixer = mixer % Fadc;
        newNyquistNo = ((ncoFreq * 2) / Fadc);
        if (newNyquistNo != bringupNyquistNo){ // Checking if the nyquist frequency
            afeLogErr("%s", "The new Nyquist frequency and the frequency set in bringup should be same");
            AFE79_PARAMS_VALID(newNyquistNo == bringupNyquistNo);
        }
    }
    if (nco == 0)
    {
        AFE79_CURR_SYSPARAM.fbNco[0][chNo] = ncoFreq;
    }
    if (nco == 1)
    {
        AFE79_CURR_SYSPARAM.fbNco[1][chNo] = ncoFreq;
    }
    if (nco == 2)
    {
        AFE79_CURR_SYSPARAM.fbNco[2][chNo] = ncoFreq;
    }
    if (nco == 3)
    {
        AFE79_CURR_SYSPARAM.fbNco[3][chNo] = ncoFreq;
    }

    mixerVal = (mixer & 0xffffffff);
    if (AFE79_CURR_SYSPARAM.chipVersion <= 0x12)
    {
        byteList[numOfOperands] = (1 << chNo);
        numOfOperands++;
        byteList[numOfOperands] = (1 << nco);
        numOfOperands++;
    }
    else
    {
        byteList[numOfOperands] = (chNo);
        numOfOperands++;
        byteList[numOfOperands] = (nco);
        numOfOperands++;
    }

    AFE79_FUNC_EXEC(AFE79FNP(splitToByte)(mixerVal, 4, byteListFbNCO));
    uint8_t i;
    for (i = 0; i < 4; i++)
    {
        byteList[numOfOperands] = byteListFbNCO[i];
        numOfOperands++;
    }
    byteList[numOfOperands] = (3);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_UPDATE_SYSTEM_FB_CHANNEL_FREQUENCY_CONFIGURATION)); // MacroConsts.MACRO_OPCODE_UPDATE_SYSTEM_FB_CHANNEL_FREQUENCY_CONFIGURATION);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the RX NCO.
    @details This function reads the RX NCO and returns it as a pointer. AFE79_CURR_SYSPARAM.ncoFreqMode should be matched with the value set in the initial configuration.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param band Band number. 0-band0, 1-band1.
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @param ncoFreq Pointer Return. Returns the value of the NCO frequency read in KHz in case of 1KHz raster mode.<br>
            In case of FCW mode, the return value is FCW.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readRxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t band, uint8_t nco, uint32_t *ncoFreq)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(band < AFE79_NUM_BANDS_PER_RX);
    AFE79_PARAMS_VALID(ncoFreq != NULL);
    uint16_t addr = 0;
    uint32_t fcwVal = 0;
    uint8_t fcwVal_lsb, fcwVal_midlow, fcwVal_midhigh, fcwVal_msb;
    uint8_t bringupNyquistNo = ((AFE79_CURR_SYSPARAM.rxNco[0][chNo][0] * 2) / AFE79_CURR_SYSPARAM.FadcRx);
    float ncoFreqKhz;
    
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 1));
    if (AFE79_CURR_SYSPARAM.chipVersion <= 0x12)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, 0x04, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0x0, 0x7));
        addr = 0x61c4 + 4 * (chNo * 4 + band * 2 + nco);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr, 0, 7, &fcwVal_lsb));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 1, 0, 7, &fcwVal_midlow));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 2, 0, 7, &fcwVal_midhigh));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 3, 0, 7, &fcwVal_msb));
        fcwVal = fcwVal_lsb + (fcwVal_midlow << 8) + (fcwVal_midhigh << 16) + (fcwVal_msb << 24);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0x0, 0x7));
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, 0x08, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0x0, 0x7));
        addr = 0x220 + 4 * (chNo * 4 + band * 2 + nco);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr, 0, 7, &fcwVal_lsb));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 1, 0, 7, &fcwVal_midlow));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 2, 0, 7, &fcwVal_midhigh));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 3, 0, 7, &fcwVal_msb));
        fcwVal = fcwVal_lsb + (fcwVal_midlow << 8) + (fcwVal_midhigh << 16) + (fcwVal_msb << 24);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0x0, 0x7));
    }
    if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1)
    {
        *ncoFreq = fcwVal;
        ncoFreqKhz = (float)((uint64_t)fcwVal * (uint64_t)AFE79_CURR_SYSPARAM.FadcRx) / (float)(pow(2, 32));
        ncoFreqKhz += (AFE79_CURR_SYSPARAM.FadcRx * (bringupNyquistNo >> 1));
        afeLogInfo("RX NCO frequency for Channel: %d, Band: %d and NCO Number: %d is %f KHz", chNo, band, nco, ncoFreqKhz);
    }
    else
    {
        *ncoFreq = fcwVal + (AFE79_CURR_SYSPARAM.FadcRx * (bringupNyquistNo >> 1));
        afeLogInfo("RX NCO frequency for Channel: %d, Band: %d and NCO Number: %d is %ld KHz", chNo, band, nco, *ncoFreq);
    }
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 0));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the FB NCO.
    @details This function reads the FB NCO.
    @param afeInst AFE ID
    @param chNo Select the FB Channel<br>
            0 for FBAB<br>
            1 for FBCD
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @param ncoFreq Pointer Return. Returns the value of the NCO frequency read in KHz in case of 1KHz raster mode.<br>
            In case of FCW mode, the return value is FCW.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readFbNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t nco, uint32_t *ncoFreq)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(ncoFreq != NULL);
    uint16_t addr = 0;
    uint32_t fcwVal = 0;
    uint8_t fcwVal_lsb, fcwVal_midlow, fcwVal_midhigh, fcwVal_msb;
    uint8_t bringupNyquistNo = ((AFE79_CURR_SYSPARAM.fbNco[chNo][0] * 2) / AFE79_CURR_SYSPARAM.FadcFb);
    float ncoFreqKhz;
    
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 1));
    if (AFE79_CURR_SYSPARAM.chipVersion <= 0x12)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, 0x04, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0x0, 0x7));
        addr = 0x6204 + 4 * (chNo * 4 + nco);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr, 0, 7, &fcwVal_lsb));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 1, 0, 7, &fcwVal_midlow));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 2, 0, 7, &fcwVal_midhigh));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 3, 0, 7, &fcwVal_msb));
        fcwVal = fcwVal_lsb + (fcwVal_midlow << 8) + (fcwVal_midhigh << 16) + (fcwVal_msb << 24);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0x0, 0x7));
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, 0x08, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0x0, 0x7));
        addr = 0x260 + 4 * (chNo * 4 + nco);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr, 0, 7, &fcwVal_lsb));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 1, 0, 7, &fcwVal_midlow));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 2, 0, 7, &fcwVal_midhigh));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, addr + 3, 0, 7, &fcwVal_msb));
        fcwVal = fcwVal_lsb + (fcwVal_midlow << 8) + (fcwVal_midhigh << 16) + (fcwVal_msb << 24);
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0x0, 0x7));
    }

    if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1)
    {
        *ncoFreq = fcwVal;
        ncoFreqKhz = (AFE79_CURR_SYSPARAM.FadcFb * (bringupNyquistNo >> 1)) + (float)((uint64_t)fcwVal * (uint64_t)AFE79_CURR_SYSPARAM.FadcFb) / (float)(pow(2, 32));
        ncoFreqKhz += (AFE79_CURR_SYSPARAM.FadcFb * (bringupNyquistNo >> 1));
        afeLogInfo("FB NCO frequency for Channel:%d and NCO Number:%d is %f KHz ", chNo, nco, ncoFreqKhz);
    }
    else
    {
        *ncoFreq = fcwVal + (AFE79_CURR_SYSPARAM.FadcFb * (bringupNyquistNo >> 1));
        afeLogInfo("FB NCO frequency for Channel:%d and NCO Number:%d is %ld KHz ", chNo, nco, *ncoFreq);
    }
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 0));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the TX NCO.
    @details This function reads the RX NCO and returns it as a pointer. AFE79_CURR_SYSPARAM.ncoFreqMode should be matched with the value set in the initial configuration.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param band Band number. 0-band0, 1-band1.
    @param nco NCO number. 0-NCO0, 1-NCO1.
    @param val Pointer Return. Returns the value of the NCO frequency read in KHz in case of 1KHz raster mode.<br>
            In case of FCW mode, the return value is FCW.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readTxNco)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t band, uint8_t nco, int64_t *val)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(band < AFE79_NUM_BANDS_PER_TX);
    AFE79_PARAMS_VALID(nco < 2);
    AFE79_PARAMS_VALID(val != NULL);

    /* The below function reads various internal variables and calculates the TX NCO programmed.*/

    float I2 = 0;        /* Interpolation2 (back Stage) interpolation factor	*/
    float i1Fout = 0;    /* Interpolation1 (front stage) output sampling rate (equals DAC rate divided by Interpolation 2 factor).	*/
    uint64_t M1Mode = 0; /* Front (stage 1) mixer mode: 0 --> bypassed; 1/2/3/4 --> impact how overall frequency is calculated */
    uint64_t M2Mode = 0; /* Back (stage 2) mixer mode, needs to be accounted for in calculation of frequencies. */
    uint8_t scm_val, sfm_val, lutIndex, lutIndexFw;
    uint8_t m2fcw_lsb, m2fcw_midlow, m2fcw_midhigh, m2fcw_msb;
    int64_t m1fcw = 0;
    int64_t m2fcw = 0;
    uint8_t readValuetemp = 0;
    uint8_t fcwMode;
    uint64_t readValue64;
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 1));
    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 4 + chNo, &readValue64, 1));
    if ((readValue64 & 1) == 0)
    {
        I2 = (float)(readValue64 >> 1); // readValue64/2.0
    }
    else
    {
        I2 = (float)(readValue64 >> 1) + (float)0.5; // readValue64/2.0
    }

    i1Fout = (float)(AFE79_CURR_SYSPARAM.Fdac / I2);

    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 8 + chNo, &M1Mode, 1));
    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 12 + chNo, &M2Mode, 1));

    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0x10281, &readValue64, 1));
    fcwMode = readValue64 & 0xff;

    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 732 + chNo, &readValue64, 1));
    scm_val = readValue64 & 0xff;
    AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 736 + chNo, &readValue64, 1));
    sfm_val = readValue64 & 0xff;

    if (AFE79_CURR_SYSPARAM.numBandsTx[chNo] == 0)
    {
        lutIndex = nco;
        lutIndexFw = nco;
    }
    else
    {
        lutIndex = 3 * nco;
        lutIndexFw = 3 * nco;
    }

    if (fcwMode == 1)
    { /*# FCW Mode*/
        if (M1Mode == 0)
        {
            m1fcw = 0;
        }

        else if (M1Mode % 2 == 1)
        {
            AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 208 + (band << 6) + (chNo << 4) + (nco << 3), &readValue64, 4));
            m1fcw = readValue64 & 0xffffffff;
        }

        else if (M1Mode % 2 == 0)
        {
            AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 336 + (32 * chNo) + (lutIndex << 3), &readValue64, 4));
            if (band == 1)
            {
                m1fcw = 0x100000000 - (readValue64 & 0xffffffff);
            }
            else
            {
                m1fcw = readValue64 & 0xffffffff;
            }
        }

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chNo + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
        if (M2Mode == 1)
        {
            if ((lutIndex == 0) || (scm_val == 1))
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x304, 0x0, 0x3, &readValuetemp));
                m2fcw = (readValuetemp << 28);
            }
            else if (lutIndex == 1)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x305, 0x0, 0x3, &readValuetemp));
                m2fcw = (readValuetemp << 28);
            }
            else if (lutIndex == 2)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x306, 0x0, 0x3, &readValuetemp));
                m2fcw = (readValuetemp << 28);
            }
            else if (lutIndex == 3)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x307, 0x0, 0x3, &readValuetemp));
                m2fcw = (readValuetemp << 28);
            }
        }
        else
        {
            if ((lutIndex == 0) || (sfm_val == 1))
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x353, 0x0, 0x7, &m2fcw_msb));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x352, 0x0, 0x7, &m2fcw_midhigh));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x351, 0x0, 0x7, &m2fcw_midlow));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x350, 0x0, 0x7, &m2fcw_lsb));
                m2fcw = (m2fcw_msb << 24) + (m2fcw_midhigh << 16) + (m2fcw_midlow << 8) + m2fcw_lsb;
            }
            else if (lutIndex == 1)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x357, 0x0, 0x7, &m2fcw_msb));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x356, 0x0, 0x7, &m2fcw_midhigh));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x355, 0x0, 0x7, &m2fcw_midlow));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x354, 0x0, 0x7, &m2fcw_lsb));
                m2fcw = (m2fcw_msb << 24) + (m2fcw_midhigh << 16) + (m2fcw_midlow << 8) + m2fcw_lsb;
            }
            else if (lutIndex == 2)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35b, 0x0, 0x7, &m2fcw_msb));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35a, 0x0, 0x7, &m2fcw_midhigh));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x359, 0x0, 0x7, &m2fcw_midlow));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x358, 0x0, 0x7, &m2fcw_lsb));
                m2fcw = (m2fcw_msb << 24) + (m2fcw_midhigh << 16) + (m2fcw_midlow << 8) + m2fcw_lsb;
            }
            else if (lutIndex == 3)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35f, 0x0, 0x7, &m2fcw_msb));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35e, 0x0, 0x7, &m2fcw_midhigh));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35d, 0x0, 0x7, &m2fcw_midlow));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x35c, 0x0, 0x7, &m2fcw_lsb));
                m2fcw = (m2fcw_msb << 24) + (m2fcw_midhigh << 16) + (m2fcw_midlow << 8) + m2fcw_lsb;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));

        if (m1fcw > 0x80000000)
        {
            m1fcw = (m1fcw - 0x100000000);
        }

        *val = (int64_t)ceil(m1fcw / I2) + m2fcw;
        if (*val < 0){            
            *val = ((int64_t)1<<32) + *val;
        }
        afeLogInfo("TX NCO Frequency Read: %f KHz", (float)((uint64_t)*val * (uint64_t)AFE79_CURR_SYSPARAM.Fdac) / (float)(pow(2, 32)));
    }

    else
    { /*# 1KHz Mode*/
        if (M1Mode == 0)
        {
            m1fcw = 0;
        }
        else if (M1Mode % 2 == 1)
        {
            AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 16 + (band << 5) + (chNo << 3) + (nco << 2), &readValue64, 4));
            m1fcw = readValue64;
        }
        else if (M1Mode % 2 == 0)
        {
            AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 80 + (16 * chNo) + (lutIndexFw << 2), &readValue64, 4));
            if (band == 0)
            {
                m1fcw = (readValue64 & 0xffffffff);
            }
            else
            {
                m1fcw = (int64_t)i1Fout - (int64_t)(readValue64 & 0xffffffff);
            }
        }

        if (m1fcw > (i1Fout / 2))
        {
            m1fcw = m1fcw - i1Fout;
        }

        if (M2Mode == 1)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chNo + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
            if ((lutIndex == 0) || (scm_val == 1))
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x304, 0x0, 0x3, &readValuetemp));
                m2fcw = (int64_t)(readValuetemp * AFE79_CURR_SYSPARAM.Fdac) >> 4;
            }
            else if (lutIndex == 1)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x305, 0x0, 0x3, &readValuetemp));
                m2fcw = (int64_t)(readValuetemp * AFE79_CURR_SYSPARAM.Fdac) >> 4;
            }
            else if (lutIndex == 2)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x306, 0x0, 0x3, &readValuetemp));
                m2fcw = (int64_t)(readValuetemp * AFE79_CURR_SYSPARAM.Fdac) >> 4;
            }
            else if (lutIndex == 3)
            {
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x307, 0x0, 0x3, &readValuetemp));
                m2fcw = (int64_t)(readValuetemp * AFE79_CURR_SYSPARAM.Fdac) >> 4;
            }
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
        }
        else
        {
            if (sfm_val == 1)
            {
                AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 144 + (16 * chNo), &readValue64, 4));
                m2fcw = readValue64 & 0xffffffff;
            }
            else
            {
                AFE79_FUNC_EXEC(AFE79FNP(readTopMem)(afeInst, 0xfbd4 + 144 + (16 * chNo) + (lutIndexFw << 2), &readValue64, 4));
                m2fcw = readValue64 & 0xffffffff;
            }
        }
        *val = m1fcw + m2fcw;
        afeLogInfo("TX NCO Frequency Read: %lld KHz", *val);
    }

    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 0));

    return TI_AFE_RET_EXEC_PASS;
}
