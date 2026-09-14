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

/** @file tiAfe79_serDes.c
 * 	@brief	This file has SerDes related functions.<br>
 *      <b> Version 2.9:</b><br>
 *      1. Added readSerdesLaneCtle to read the AFE Serde Lane CTLE value.<br>
 * 		<b> Version 2.5.0:</b><br>
 * 		1. Added getSerdesRxLaneEyeMarginValue_mV function
 * 		2.Updated em_read function which is used by getSerdes Eye.
 * 		<b> Version 2.2:</b> <br>
 * 		1. Fixed a bug in getSerDesEye function.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Updated function definition of: getSerdesEye.<br>
 * 		3. Changed the C macros for all the spi wrapper and executeMacro function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 * 		4. Added functions resetSerDesDfeLane, reAdaptSerDesLane, resetSerDesDfeAllLanes and reAdaptSerDesAllLanes.<br>
 */

#include <stdint.h>
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"
#include "tiAfe79_afeParameters.h"
#include "tiAfe79_serDes.h"

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
    @brief Send 1010 toggling pattern on AFE SerDes TX.
    @details Send 1010 toggling pattern on AFE SerDes TX.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to STX1-STX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesTx1010Pattern)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x0, 0xf, 0xf));                   /*TX_TEST_DATA_SOURCE*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x2000, 0xd, 0xd));                /*TX_TEST_EN*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x0, 0xe, 0xe));                   /*TX_PRBS_CLOCK_EN*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a1, laneNo, 0xaaaa, 0x0, 0xf));
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a2, laneNo, 0xaaaa, 0x0, 0xf));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Send JESD data on AFE SerDes TX.
    @details Send JESD data pattern on AFE SerDes TX.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to STX1-STX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesTxSendData)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x0, 0xd, 0xd));                   /*TX_TEST_EN*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x0, 0xe, 0xe));                   /*TX_PRBS_CLOCK_EN*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0x0, 0xf, 0xf));                   /*TX_TEST_DATA_SOURCE*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Set SerDes TX Cursor.
    @details Set SerDes TX Cursor. Below table shows the mapping between different settings and the equalization it provides.<br>
        Column (1):Pre-Cursor equalization acheived. (dB in relative to post cursor)	<br>
        Column (2):Main Cursor equalization acheived.(dB in relative to pre cursor)<br>
        Column (3):Post-Cursor equalization acheived.(dB in relative to pre cursor)<br>
        Column (4):Pre-Cursor Setting to be programmed.<br>
        Column (5):Main Setting to be programmed.<br>
        Column (6):Post-Cursor setting to be programmed.<br><br>
        (1)________(2)________(3)________(4)________(5)________(6)<br>
        0________25________0________0________0________0<br>
        0________23________0________0________1________0<br>
        0________21________0________0________2________0<br>
        0________19________0________0________3________0<br>
        0________17________0________0________4________0<br>
        0________15________0________0________5________0<br>
        0________13________0________0________6________0<br>
        0________11________0________0________7________0<br>
        0________24________0.72________0________0________1<br>
        0________20________0.87________0________2________1<br>
        0________16________1.09________0________4________1<br>
        0________12________1.45________0________6________1<br>
        0________23________1.51________0________0________2<br>
        0________21________1.66________0________1________2<br>
        0________15________2.33________0________4________2<br>
        0________22________2.38________0________0________3<br>
        0________13________2.69________0________5________2<br>
        0________21________3.35________0________0________4<br>
        0________19________3.71________0________1________4<br>
        0________14________3.78________0________4________3<br>
        0________17________4.17________0________2________2<br>
        0________20________4.44________0________0________5<br>
        0________15________4.75________0________3________2<br>
        0________16________5.62________0________2________5<br>
        0________19________5.68________0________0________6<br>
        0________17________6.41________0________1________6<br>
        0________18________7.13________0________0________7<br>
        0.72________24________0________1________0________0<br>
        0.87________20________0________1________2________0<br>
        0.87________22________1.66________1________0________2<br>
        1.09________16________0________1________4________0<br>
        1.09________20________3.71________1________0________4<br>
        1.45________12________0________1________2________0<br>
        1.45________14________2.69________1________4________2<br>
        1.45________16________4.75________1________2________4<br>
        1.45________18________6.41________1________0________6<br>
        1.51________23________0________2________0________0<br>
        1.66________21________0________2________1________0<br>
        1.66________22________0.87________2________0________1<br>
        2.33________15________0________2________4________0<br>
        2.33________19________4.17________2________0________4<br>
        2.38________22________0________3________0________0<br>
        2.69________18________5.62________2________0________5<br>
        2.69________13________0________2________5________0<br>
        2.69________14________1.45________2________4________1<br>
        2.69________17________4.75________2________1________4<br>
        3.35________21________0________4________0________0<br>
        3.71________19________0________4________1________0<br>
        3.71________20________1.09________4________0________1<br>
        3.78________18________4.75________3________0________4<br>
        3.78________14________0________3________4________0<br>
        4.17________17________0________4________2________0<br>
        4.17________19________2.33________4________0________2<br>
        4.44________20________0________5________0________0<br>
        4.75________15________0________4________3________0<br>
        4.75________16________1.45________4________2________1<br>
        4.75________18________3.78________4________0________3<br>
        4.75________17________2.69________4________1________2<br>
        5.62________16________0________5________2________0<br>
        5.62________18________2.69________5________0________2<br>
        5.68________19________0________6________0________0<br>
        6.41________18________1.45________6________0________1<br>
        6.41________17________0________6________1________0<br>
        7.13________18________0________7________0________0
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to STX1-STX8, the physical SerDes lanes.
    @param mainCursorSetting Main Cursor Setting.
    @param preCursorSetting Pre Cursor Setting.
    @param postCursorSetting Post Cursor Setting.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(SetSerdesTxCursor)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t mainCursorSetting, uint8_t preCursorSetting, uint8_t postCursorSetting)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    uint32_t cursorSetting;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    cursorSetting = (mainCursorSetting << 5) + (postCursorSetting << 11) + (preCursorSetting << 8);
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80f6, laneNo, cursorSetting, 0x5, 0xd));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the AFE SerDes RX PRBS error.
    @details Reads the AFE SerDes RX PRBS error and returns the error value as pointer.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param errorRegValue PRBS error register value. This value increments by 3 for each PRBS error.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxPrbsError)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint32_t *errorRegValue)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_PARAMS_VALID(errorRegValue != NULL);
    uint16_t readValue;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x804c, laneNo, 0, 0xf, &readValue));
    *errorRegValue = readValue << 16;
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x804d, laneNo, 0, 0xf, &readValue));
    *errorRegValue = *errorRegValue + readValue;
    *errorRegValue = *errorRegValue / 3;
    afeLogInfo("Number of Errors seen in lane %d are %d", laneNo, *errorRegValue);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Clear the AFE SerDes RX PRBS error counter.
    @details Clearss the AFE SerDes RX PRBS error counter.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(clearSerdesRxPrbsErrorCounter)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8042, laneNo, 0x20, 0x5, 0x5));
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8042, laneNo, 0x0, 0x5, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
    @brief Enables the AFE SerDes RX PRBS check.
    @details Enables the AFE SerDes RX PRBS check.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param prbsMode PRBS Mode Selection. 0 for PRBS9, 1 for PRBS15, 2 for PRBS23 and 3 for PRBS31.
    @param enable 1 will enable the PRBS check, 0 will disable the PRBS check.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(enableSerdesRxPrbsCheck)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t prbsMode, uint8_t enable)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    uint16_t readValue = 0, writeValue = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x8042, laneNo, 0, 0xf, &readValue));

    writeValue = (readValue & 0xffd1) | ((prbsMode & 3) << 2) | ((enable & 1) << 1) | (1 << 5);
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8042, laneNo, writeValue, 0, 0xf));
    writeValue = (readValue & 0xffd1) + ((prbsMode & 3) << 2) + ((enable & 1) << 1) + (0 << 5);
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8042, laneNo, writeValue, 0, 0xf));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Sends the AFE SerDes TX PRBS pattern.
    @details Sends the AFE SerDes TX PRBS pattern.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to STX1-STX8, the physical SerDes lanes.
    @param prbsMode PRBS Mode Selection. 0 for PRBS9, 1 for PRBS15, 2 for PRBS23 and 3 for PRBS31.
    @param enable 1 will enable the PRBS transmission, 0 will disable the PRBS pattern transmission.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(sendSerdesTxPrbs)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t prbsMode, uint8_t enable)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    uint16_t readValue = 0;
    uint32_t writeValue = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x80a0, laneNo, 0, 0xf, &readValue));
    writeValue = (readValue & 0x14ff) | ((prbsMode & 3) << 8) | ((enable & 1) << 11) | ((enable & 1) << 13) | ((enable & 1) << 14) | ((enable & 1) << 15);
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, writeValue, 0, 0xf));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Generates a single bit error in the AFE SerDes TX PRBS pattern.
    @details Generates a single bit error in the AFE SerDes TX PRBS pattern.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to STX1-STX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(generateSerdesTxPrbsError)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 1 << 10, 10, 10));
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x80a0, laneNo, 0 << 10, 10, 10));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Reads the AFE SerDes RX Eye margin value mV.
    @details Reads the AFE SerDes RX Eye margin value and returns the value as a pointer. This value*0.5 is the eye margin in mV post equalization.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param eye_mV Eye Margin value in mV.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxLaneEyeMarginValue_mV)(AFE79_INST_TYPE afeInst, uint8_t laneNo, float *eye_mV)
{

    uint16_t eye_reg, sel_val, dac_val;
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x802c, laneNo, 0, 11, &eye_reg));
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x801d, laneNo, 12, 12, &sel_val));
    if (sel_val == 1)
    {
        AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x801d, laneNo, 8, 11, &dac_val));
    }
    else
    {
        AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x8023, laneNo, 4, 7, &dac_val));
    }
    *eye_mV = ((float)eye_reg / 2048.0) * (200.0 + (50.0 * (float)dac_val));
    afeLogInfo("Eye height Value read out is on lane %d is %f", laneNo, *eye_mV);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the AFE SerDes RX CTLE adaptation status.
    @details This function checks if the AFE SerDes RX lane CTLE adaptation is complete.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param status Pointer return. Value will be 1 if the adaptation is done, else returns 0.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkAdaptationStatus)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint8_t *status)
{

    uint16_t adaptationStatus;
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesReadWrapper)(afeInst, 0x980f, 0, 3, &adaptationStatus));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7)); /*serdes_jesd*/
    uint8_t afe79jesdToSerdesLaneMappingLocal[8] = afe79jesdToSerdesLaneMapping;
    laneNo = afe79jesdToSerdesLaneMappingLocal[laneNo];
    if (((adaptationStatus >> laneNo) & 0x1) == 1)
    {
        afeLogDbg("%s", "CTLE Adaptation is done.");
        *status = 1;
    }
    else
    {
        afeLogErr("%s", "CTLE Adaptation is not done.");
        *status = 0;
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Resets the AFE SerDes RX DFE lane.
    @details Resets the AFE SerDes RX DFE lane.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(resetSerDesDfeLane)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    uint16_t readValue = 0;
    uint32_t writeValue = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x8000, laneNo, 0, 0xf, &readValue));
    writeValue = (readValue & 0x7fff);
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8000, laneNo, writeValue | 0x8000, 0, 0xf));
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneWriteWrapper)(afeInst, 0x8000, laneNo, writeValue, 0, 0xf));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Readapts the AFE SerDes RX lane.
    @details Readapts the AFE SerDes RX lane. This calls resetSerDesDfeLane within this function for the specific lane.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(reAdaptSerDesLane)(AFE79_INST_TYPE afeInst, uint8_t laneNo)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_FUNC_EXEC(AFE79FNP(resetSerDesDfeLane)(afeInst, laneNo));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Resets DFE of all the AFE SerDes RX lanes.
    @details Resets DFE of all the AFE SerDes RX lanes. This calls resetSerDesDfeLane within this function for all the lanes.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(resetSerDesDfeAllLanes)(AFE79_INST_TYPE afeInst)
{

    AFE79_ID_VALIDITY();
    uint8_t laneNo;
    for (laneNo = 0; laneNo < AFE79_NUM_SERDES_LANES; laneNo++)
    {
        AFE79_FUNC_EXEC(AFE79FNP(resetSerDesDfeLane)(afeInst, laneNo));
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Readapts all the AFE SerDes RX lanes.
    @details Readapts all the AFE SerDes RX lanes. This calls reAdaptSerDesLane within this function for all the lanes.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(reAdaptSerDesAllLanes)(AFE79_INST_TYPE afeInst)
{

    AFE79_ID_VALIDITY();
    AFE79_FUNC_EXEC(AFE79FNP(resetSerDesDfeAllLanes)(afeInst));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the status of the SerDes Eye Read.
    @details Checks the status of the SerDes Eye Read. This function is called getSerdesEye and shouldn't be called independently.
    @param afeInst AFE ID
    @param responseRet Pointer Return. Returns Status
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(parse_response)(AFE79_INST_TYPE afeInst, uint16_t *responseRet)
{

    uint16_t response = 0;
    uint8_t errorStatus = 0;

    while (1)
    {
        AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, 0x9815, &response));
        if (response >> 12 == 0)
        {
            break;
        }
    }
    uint8_t status = (response >> 8) & 0xf;
    uint8_t data = response & 0xff;
    if (status == 0x3)
    {
        if (data == 0x02)
        {
            afeLogErr("%s", "Invalid input");
            errorStatus |= 1;
        }
        else if (data == 0x03)
        {
            afeLogErr("%s", "Phy not ready");
            errorStatus |= 1;
        }
        else if (data == 0x05)
        {
            afeLogInfo("%s", "Eye monitor going on");
        }
        else if (data == 0x06)
        {
            afeLogErr("%s", "Eye monitor cancelled");
        }
        else if (data == 0x07)
        {
            afeLogErr("%s", "Eye monitor not started");
            errorStatus |= 1;
        }
        else
        {
            afeLogInfo("%d", data);
        }
    }
    *responseRet = response;
    if (errorStatus)
        return TI_AFE_RET_EXEC_FAIL;
    else
        return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Initiates the SerDes Eye Read.
    @details Initiates the SerDes Eye Read. This function is called getSerdesEye and shouldn't be called independently.
    @param afeInst AFE ID
    @param lane_num Lane Number.
    @param ber_exp BER accuracy.
    @param mode Should be always 1.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(em_start)(AFE79_INST_TYPE afeInst, uint8_t lane_num, uint8_t ber_exp, uint8_t mode)
{
    // uint8_t instanceNo = lane_num >> 2;

    uint16_t response = 0;
    // uint8_t afe79jesdToSerdesLaneMappingLocal[8] = afe79jesdToSerdesLaneMapping;
    // lane_num = afe79jesdToSerdesLaneMappingLocal[lane_num];
    uint16_t command = 0x1000 | (lane_num & 0x3) | ((ber_exp & 0xF) << 4);
    AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9816, mode));
    AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9815, command));
    AFE79_FUNC_EXEC(AFE79FNP(parse_response)(afeInst, &response));
    uint8_t status = (response >> 8) & 0xf;

    if (status == 0x0)
    {
        afeLogInfo("%s", "Eye monitor starts...");
    }

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the Progress of the SerDes Eye Read.
    @details Checks the Progress of the SerDes Eye Read. This function is called getSerdesEye and shouldn't be called independently.
    @param afeInst AFE ID
    @param progress Pointer return. Progress percentage.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(em_report_progress)(AFE79_INST_TYPE afeInst, uint8_t *progress)
{

    uint16_t command = 0x2000;
    uint16_t response = 0;
    AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9815, command));
    AFE79_FUNC_EXEC(AFE79FNP(parse_response)(afeInst, &response));
    uint8_t status = (response >> 8) & 0xf;
    uint8_t data = response & 0xff;
    if (status == 0x1)
    {
        *progress = data;
    }
    else
    {
        *progress = 0xff;
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Reads the SerDes Eye parameters.
    @details Reads the SerDes Eye parameters. This function is called getSerdesEye and shouldn't be called independently.
    @param afeInst AFE ID
    @param ber Pointer of array with 3135 elements.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(em_read)(AFE79_INST_TYPE afeInst, uint16_t *ber)
{

    uint16_t response = 0;
    int8_t m = 0;
    uint8_t status = 0;
    uint16_t marginValue;
    uint16_t phaseValue;
    uint16_t serdesReadVal;
    uint8_t i;
    int16_t margin;
    uint8_t pindex;
    int8_t phase;
    for (phase = -16; phase < 17; phase++)
    {
        pindex = phase + 16;
        for (margin = -47; margin < 48; margin += 16)
        {
            if (margin < 0)
            {
                marginValue = 65536 + margin;
            }
            else
            {
                marginValue = margin;
            }
            if (phase < 0)
            {
                phaseValue = 65536 + phase;
            }
            else
            {
                phaseValue = phase;
            }
            AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9816, marginValue & 0xffff));
            AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9815, (phaseValue & 0xFF) | 0x3000));
            AFE79_FUNC_EXEC(AFE79FNP(parse_response)(afeInst, &response));
            status = (response >> 8) & 0xf;
            uint16_t loop_counter = 0;
            while (status != 0x2)
            {
                if (status == 0x3)
                {
                    afeLogErr("%s", "Response asserted Failure!");
                    break;
                }
                loop_counter++;
                afeLogInfo("current Status read %x", status);
                afeLogInfo("%s", "waiting ..");
                if (loop_counter > 1000)
                {
                    afeLogErr("%s", "loop time out");
                    break;
                }
            }
            if (status == 0x2)
            {
                for (i = 0; i < 16; i++)
                {
                    m = margin + i;
                    if (m < 48)
                    {
                        AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, (0x9f00 + i), &serdesReadVal));
                        ber[(uint16_t)(47 + m) + (pindex * 95)] = serdesReadVal;
                    }
                }
            }
            else
            {
                for (i = 0; i < 16; i++)
                {
                    m = margin + i;
                    if (m < 48)
                    {
                        ber[(uint16_t)(47 + m) + (pindex * 95)] = 0;
                    }
                }
            }
            afeLogInfo("%d", ber[(uint16_t)(47 + m) + (pindex * 95)]);
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Stops the the SerDes Eye Read.
    @details Stops the the SerDes Eye Read. This function is called getSerdesEye and shouldn't be called independently.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(em_cancel)(AFE79_INST_TYPE afeInst)
{

    AFE79_FUNC_EXEC(AFE79FNP(serdesRawWrite)(afeInst, 0x9815, 0x4000));
    uint16_t response = 0;
    AFE79_FUNC_EXEC(AFE79FNP(parse_response)(afeInst, &response));

    afeLogInfo("%d", response);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Reads the SerDes Eye for a given lane.
    @details Reads the SerDes Eye for a given lane. The ber array and the extent returned by this function should be fed to the python script to plot the eye diagram.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param ber Pointer of array with 3135 elements.
    @param extent scaling factor of the ber needed by the function.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesEye)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *ber, uint16_t *extent)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_PARAMS_VALID(ber != NULL);
    AFE79_PARAMS_VALID(extent != NULL);
    // uint16_t extent;
    uint8_t afe79jesdToSerdesLaneMappingLocal[8] = afe79jesdToSerdesLaneMapping;
    uint8_t instanceNo = laneNo >> 2;
    laneNo = afe79jesdToSerdesLaneMappingLocal[laneNo];
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x20 << instanceNo, 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(em_start)(afeInst, laneNo, 7, 1)); /*lane0, ber_exp 10^7, mode 1*/
    uint8_t old_progress = 0;
    while (1)
    {
        uint8_t progress = 0;
        AFE79_FUNC_EXEC(AFE79FNP(em_report_progress)(afeInst, &progress));
        if (progress == 0xff)
        {
            break;
        }
        if (old_progress != progress)
        {
            afeLogInfo("%d", progress);
        }
        if (progress == 100)
        {
            break;
        }
        old_progress = progress;
    }
    AFE79_FUNC_EXEC(AFE79FNP(em_read)(afeInst, ber));

    AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, 0x9816, extent));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x00, 0x0, 0x7));
    afeLogInfo("Extent: %d", *extent);
    /*getSerdesEye*/
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Reads the AFE SerDes RX Eye margin value.
    @details Reads the AFE SerDes RX Eye margin value and returns the value as a pointer. This value*0.5 is the eye margin in mV post equalization.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param regValue Eye Margin value status.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesRxLaneEyeMarginValue)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x8030, laneNo, 0, 11, regValue));
    afeLogInfo("Eye Margin Value read out is on lane %d is %d", laneNo, *regValue);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

// #define AFE_MAX_SERDES_STATUS_POLL_CNT 5000

static uint16_t AFE_MAX_SERDES_STATUS_POLL_CNT = 1000;
#ifndef DOXYGEN_SHOULD_SKIP_THIS
TI_AFE_API_COMP uint8_t AFE79FNP(setAfeSerDesPollMaxCnt)(uint16_t val)
{
    AFE_MAX_SERDES_STATUS_POLL_CNT = val;
    return TI_AFE_RET_EXEC_PASS;
}

TI_AFE_API_COMP uint8_t AFE79FNP(getAfeSerDesPollMaxCnt)(uint16_t *val)
{
    *val = AFE_MAX_SERDES_STATUS_POLL_CNT;
    return TI_AFE_RET_EXEC_PASS;
}
#endif
// #define AFE_MAX_SERDES_STATUS_POLL_CNT 1000

/**
    @brief Checks if SERDES receiver lane status.
    @details Checks if the SerDes lane CDR locked.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param regValue Pointer return. Link Status. 1:CDR locked. 0:CDR didn't lock.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getSerdesLinkStatus)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_SERDES_JESD, AFE79_PAGE_SELMASK_SERDES_JESD(AFE79_LANE_NO_TO_PAGE_SEL(laneNo)), 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x804e, laneNo, 15, 15, regValue));
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_SERDES_JESD, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
/**
    @brief Poll and check lane status of all SERDES receiver lanes.
    @details Poll and check lane status of all SERDES receiver lanes.
    @param afeInst AFE ID
    @param allLaneStatus Pointer return. Bit wise Link Status for each lane. If Bit is 1: Lane Adapted success. If bit is 0, lane recovery didn't happen. It returns 1 even for turned off lanes. This needs to be 0xff in good case.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(pollSerdesLinkStatusAllLanes)(AFE79_INST_TYPE afeInst, uint8_t *allLaneStatus)
{

    uint8_t laneEna = 0;
    uint16_t ctleStatus = 0, cdrStatus = 0, loopCount = 0;
    AFE79_ID_VALIDITY();
    uint8_t afe79jesdToSerdesLaneMappingLocal[8] = afe79jesdToSerdesLaneMapping;

    *allLaneStatus = 0;
    uint8_t serdesLaneEna[] = {0, 0, 0, 0, 0, 0, 0, 0};
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_DAC_JESD_RX, AFE79_PAGE_SELMASK_DAC_JESD_RX(1), 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE79_REG_ADDR_DAC_JESD_LANE_ENA, 0x0, 0x7, &laneEna));

    // For Checking which lanes are turned on from top 4 lanes.
    for (uint8_t jesdLaneNo = 0; jesdLaneNo < 4; jesdLaneNo++)
    {
        if (((laneEna >> jesdLaneNo) & 1) == 1)
        {
            serdesLaneEna[AFE79_CURR_SYSPARAM.jesdRxLaneMux[jesdLaneNo]] = 1;
        }
    }
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_DAC_JESD_RX, AFE79_PAGE_SELMASK_DAC_JESD_RX(2), 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, AFE79_REG_ADDR_DAC_JESD_LANE_ENA, 0x0, 0x7, &laneEna));
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_DAC_JESD_RX, 0, 0x0, 0x7));

    // For Checking which lanes are turned on from bottom 4 lanes.
    for (uint8_t jesdLaneNo = 0; jesdLaneNo < 4; jesdLaneNo++)
    {
        if (((laneEna >> jesdLaneNo) & 1) == 1)
        {
            serdesLaneEna[AFE79_CURR_SYSPARAM.jesdRxLaneMux[jesdLaneNo + 4]] = 1;
        }
    }

    for (uint8_t laneNo = 0; laneNo < AFE79_NUM_SERDES_LANES; laneNo++)
    {
        if (serdesLaneEna[laneNo] == 0)
        {
            *allLaneStatus |= (1 << laneNo);
        }
    }
    for (uint8_t laneNo = 0; laneNo < AFE79_NUM_SERDES_LANES; laneNo++)
    {
        if ((((*allLaneStatus) >> laneNo) & 1) == 1)
        {
            continue;
        }

        for (uint16_t pollTime = 0; pollTime < AFE_MAX_SERDES_STATUS_POLL_CNT; pollTime++)
        {
            AFE79_FUNC_EXEC(AFE79FNP(getSerdesLinkStatus)(afeInst, laneNo, &cdrStatus));
            if (AFE79_CURR_SYSPARAM.serdesManualCTLEEn == 0)
            {
                AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_SERDES_JESD, AFE79_PAGE_SELMASK_SERDES_JESD(1 << (laneNo >> 2)), 0x0, 0x7));                /*serdes_jesd*/
                AFE79_FUNC_EXEC(AFE79FNP(serdesReadWrapper)(afeInst, 0x980F, afe79jesdToSerdesLaneMappingLocal[laneNo], afe79jesdToSerdesLaneMappingLocal[laneNo], &ctleStatus)); /*TX_TEST_DATA_SOURCE*/
                AFE79_FUNC_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE79_PAGE_ADDR_SERDES_JESD, 0x0, 0x0, 0x7));
            }
            else
            {
                ctleStatus = 1;
            }
            if ((ctleStatus == 1) && (cdrStatus == 1))
            {
                *allLaneStatus |= (1 << laneNo);
                break;
            }
            AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
            if (loopCount > (AFE_MAX_SERDES_STATUS_POLL_CNT << 1))
            {
                break;
            }
            loopCount++;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Reads the AFE Serde Lane CTLE value.
    @details Reads the AFE Serde Lane CTLE value from CDR loop convergence of SRx lane and returns the value as a pointer.
    @param afeInst AFE ID
    @param laneNo Values 0-7, refer to SRX1-SRX8, the physical SerDes lanes.
    @param regValue Serde Lane CTLE value.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readSerdesLaneCtle)(AFE79_INST_TYPE afeInst, uint8_t laneNo, uint16_t *regValue)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(laneNo < AFE79_NUM_SERDES_LANES);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, (((1 << (laneNo >> 2))) << 5) & 0xff, 0x0, 0x7)); /*serdes_jesd*/
    AFE79_FUNC_EXEC(AFE79FNP(serdesLaneReadWrapper)(afeInst, 0x8023, laneNo, 0, 2, regValue));
    afeLogInfo("Ctle Value read out is on lane %d is %d", laneNo, *regValue);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
