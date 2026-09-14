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

/** @file tiAfe79_controls.c
 * 	@brief	This file has generic control related functions.<br>
 *      <b> Version 2.9:</b> <br>
 *      1. Added readSysrefMonitor function to readout of the SYSREF alignment detector.<br>
 *      2. Added getDeviceTemp to read device temp.<br>
 *      3. Added readPllCapCode to Pll Cap Code Read Out.<br>
 * 		<b> Version 2.7:</b> <br>
 * 		1. Added startMonitoring, stopMonitoring, computeGolden functions to monitor register upsets for AFE7950-SP device.<br>
 * 		<b> Version 2.2:</b> <br>
 * 		1. Fixed the bug in function getChipVersion.<br>
 * 		2. Updated description of checkPllLockStatus.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Removed redundant writes in functions.<br>
 * 		3. Changed the C macros for all the spi wrapper function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 * 		4. Checking if the sysref reached added to the sendSysref function. The function returns fail if the sysref fails to return.<br>
 * 		5. For all PLL Access, the selection between the SPIA and SPIB is changed to a system parameter to cut down the redundant need to pass it in all the functions, since in a typical use case, only one SPI (SPIA) is used for it.<br>
 * 		6. Added checkDeviceHealth function to return a overall status of the device.<br>
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
#include "tiAfe79_controls.h"
#include "tiAfe79_macro.h"
#include "tiAfe79_agc.h"
#include "tiAfe79_jesd.h"
#include "tiAfe79_pap.h"

#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Reads the Chip version of the AFE
    @details This function Reads the Chip version, logs it and also updates the same in the System Params (AFE79_CURR_SYSPARAM.chipVersion).
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getChipVersion)(AFE79_INST_TYPE afeInst)
{
    AFE79_ID_VALIDITY();
    uint8_t byteList[1];
    uint8_t numOfOperands = 0;
    uint8_t chipVersion, readValue;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x006, 0x0, 0x7, &readValue));
    if (readValue == 0x10)
    {
        AFE79_CURR_SYSPARAM.chipVersion = 0x10;
        afeLogInfo("%s", "Chip Version is 0x10");
    }
    else if (readValue == 0x11)
    {
        byteList[numOfOperands] = (2);
        numOfOperands++;
        AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, 0x1));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0, 7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00fc, 0x0, 0x7, &chipVersion));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0, 7));
        if (chipVersion == 0xe3)
        {
            AFE79_CURR_SYSPARAM.chipVersion = 0x12;
            afeLogInfo("%s", "Chip Version is 0x12");
        }
        else if (chipVersion == 0xf8)
        {
            AFE79_CURR_SYSPARAM.chipVersion = 0x13;
            afeLogInfo("%s", "Chip Version is 0x13");
        }
        else
        {
            afeLogErr("%s", "chip Version not recognised.");
        }
    }
    else if (readValue == 0x20)
    {
        AFE79_CURR_SYSPARAM.chipVersion = 0x20;
        afeLogInfo("%s", "Chip Version is 0x20");
    }
    else if (readValue == 0x30)
    {
        AFE79_CURR_SYSPARAM.chipVersion = 0x30;
        afeLogInfo("%s", "Chip Version is 0x30");
    }
    else if (readValue == 0x40)
    {
        AFE79_CURR_SYSPARAM.chipVersion = 0x40;
        afeLogInfo("%s", "Chip Version is 0x40");
    }
    else if (readValue == 0x41)
    {
        AFE79_CURR_SYSPARAM.chipVersion = 0x41;
        afeLogInfo("%s", "Chip Version is 0x41");
    }
    else
    {
        afeLogErr("%s", "chip Version not recognised.");
    }
    return TI_AFE_RET_EXEC_PASS;
}

#endif

/**
    @brief Override TDD Control Signals and set the SPI override value
    @details This function overrides SPI TDD Control Signals and set the SPI override value
    @param afeInst AFE ID
    @param rx Override Value of the RX chain.<br>
        This is Bit wise channel select<br>
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param fb Override Value of the FB chain.<br>
        This is Bit wise channel select<br>
            Bit0 for FBAB<br>
            Bit1 for FBCD
    @param tx Override Value of the TX chain.<br>
        This is Bit wise channel select<br>
            Bit0 for TXA<br>
            Bit1 for TXB<br>
            Bit2 for TXC<br>
            Bit3 for TXD
    @param enableOverride Enables the Override.<br>
            if enableOverride=0, it disables the TDD override<br>
            if enableOverride=1, it enables the TDD override && also sets the TDD values<br>
            if enableOverride=2, it only sets the TDD values
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(overrideTdd)(AFE79_INST_TYPE afeInst, uint8_t rx, uint8_t fb, uint8_t tx, uint8_t enableOverride)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(rx <= AFE79_NUM_RX_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(fb <= AFE79_NUM_FB_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(tx <= AFE79_NUM_TX_CHANNELS_BITWISE);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x80, 0x0, 0x7)); /*timing_controller*/

    if (enableOverride == 1 || enableOverride == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xec, (enableOverride) & 1, 0x0, 0x0)); /*Override Pins*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xf4, (enableOverride) & 1, 0x0, 0x0));

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xe4, (enableOverride) & 1, 0x0, 0x0));
    }

    if (enableOverride != 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xed, (rx) & 0xff, 0x0, 0x3));

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xf5, (fb) & 0xff, 0x0, 0x1));

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xe5, (tx) & 0xff, 0x0, 0x3));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS

/**
    @brief Override TDD Control Signals
    @details This function Set the override values for each of RX,FB,TX TDD pins.
    @param afeInst AFE ID
    @param rx Override enable Value of the RX chain. 1 sets the pin value in override state. 0 removes the override and gives control to pins.
    @param fb Override enable Value of the FB chain. 1 sets the pin value in override state. 0 removes the override and gives control to pins.
    @param tx Override enable Value of the TX chain. 1 sets the pin value in override state. 0 removes the override and gives control to pins.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(overrideTddPins)(AFE79_INST_TYPE afeInst, uint8_t rx, uint8_t fb, uint8_t tx)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(rx <= AFE79_NUM_RX_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(fb <= AFE79_NUM_FB_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(tx <= AFE79_NUM_TX_CHANNELS_BITWISE);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x80, 0x0, 0x7));       /*timing_controller*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xec, (rx) & 0x1, 0x0, 0x0)); /*use_reg_for_rxtdd*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xf4, (fb) & 0x1, 0x0, 0x0)); /*use_reg_for_fbtdd*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xe4, (tx) & 0x1, 0x0, 0x0)); /*use_reg_for_txtdd*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the Alarm Pin Status.
    @details This function reads the Alarm Pin Status and returns it as a pointer.
    @param afeInst AFE ID
    @param alarmNo Choose the Alarm Pin Number (0/1)
    @param status Pointer return Status of the alarm pin. 0 means there is no alarm and 1 means there is alarm.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readAlarmPinStatus)(AFE79_INST_TYPE afeInst, uint8_t alarmNo, uint8_t *status)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(status != NULL);
    AFE79_PARAMS_VALID(alarmNo < 2);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x10, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x01417 + alarmNo, 0x0, 0x0, status));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Override Alarm Pin output and set the SPI override value
    @details This function overrides Alarm Pin output and sets it to SPI override value
    @param afeInst AFE ID
    @param alarmNo Select the Alarm number, Alarm Pin Number 0/1.
    @param overrideSel 0-Don't override. 1-Override the pin output.
    @param overrideVal When overrideSel is 1, this is the value sent out onto pin (0/1).
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(overrideAlarmPin)(AFE79_INST_TYPE afeInst, uint8_t alarmNo, uint8_t overrideSel, uint8_t overrideVal)
{
    AFE79_ID_VALIDITY();

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x10, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10bd + (alarmNo * 4), (overrideSel << 1) + overrideVal, 0x0, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Override RX Reliability Pin output and set the SPI override value
    @details This function overrides the RX Reliability Pin output and sets it to SPI override value
    @param afeInst AFE ID
    @param chNo Select the RX channel number.<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param overrideSel 0-Don't override. 1-Override the pin output.
    @param overrideVal When overrideSel is 1, this is the value sent out onto pin (0/1).
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(overrideRelDetPin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t overrideSel, uint8_t overrideVal)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x10, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x10fd + (chNo * 8), (overrideSel << 1) + overrideVal, 0x0, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
/**
    @brief Programmable Delay in Low Latency Loopback Mode
    @details This function can change the low latency loopback mode latency.
    @param afeInst AFE ID
    @param chNo Select the TX channel number.<br>
            0 for FB1-TXA<br>
            1 for FB2-TXC
    @param progDelay Value ranges from 0 for minimum delay to 23 for maximum delay.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(lowLatencyModeProgDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t progDelay)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(progDelay < 24);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10 << (chNo * 2), 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0484, progDelay, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
/**
    @brief Sets the RX Channel Latency values
    @details Sets the value of programmable delay block to vary Rx chain Latency.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param delay Delay Value.<br>
            Delay value from 0 to 31.<br>
            Unit is (1/Fadc).

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateRxLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(delay < 32);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x1 << chNo, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0711, 0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0710, delay, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Sets the TX Channel Latency values
    @details Sets the value of programmable delay block to vary Tx chain Latency.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param delay Delay Value.<br>
            Delay value from 0 to 31.<br>
            Unit is (1/Fdac).

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateTxLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(delay < 32);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10 << chNo, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0334, 0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0335, delay, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Sets the FB Channel Latency values
    @details Sets the value of programmable delay block to vary Fb chain Latency.
    @param afeInst AFE ID
    @param chNo Select the Fb Channel<br>
            0 for FBA<br>
            1 for FBB<br>

    @param delay Delay Value.<br>
            Delay value from 0 to 31.<br>
            Unit is (1/Fdac).

    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(updateFbLatency)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t delay)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(delay < 32);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x10 << chNo, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0713, 0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0712, delay, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x0, 0x0, 0x7));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Override RX Peak Detector Pin output and set the SPI override value
    @details This function RX Peak Detector Pin output and sets it to SPI override value
    @param afeInst AFE ID
    @param chNo Select the RX channel number.<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param pinNo Pin Number to be overridden. Supported values are 0-3.
    @param overrideSel 0-Don't override. 1-Override the pin output.
    @param overrideVal When overrideSel is 1, this is the value sent out onto pin (0/1).
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(overrideDigPkDetPin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t pinNo, uint8_t overrideSel, uint8_t overrideVal)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(pinNo < 4);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x10, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x106d + (chNo * 0x10) + (pinNo * 4), (overrideSel << 1) + overrideVal, 0x0, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

#endif

/**
    @brief Check if the Sysref Reached
    @details This function Checks if the Sysref is detected by the AFE.
    @param afeInst AFE ID
    @param clearSysrefFlag Setting this to 1 clear the Sysref flag before reading.
    @param sysrefReceived Pointer return. Value of 1 means Sysref reached. 0 means Sysref reached. 0 means it didn't reach.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkSysref)(AFE79_INST_TYPE afeInst, uint8_t clearSysrefFlag, uint8_t *sysrefReceived)
{

    uint8_t readVal = 0;
    AFE79_ID_VALIDITY();

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x01, 0x0, 0x7));
    if (clearSysrefFlag)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0128, 0x08, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0128, 0x00, 0x0, 0x7));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x130, 0x0, 0x3, &readVal));
    *sysrefReceived = (readVal >> 3) & 1;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x00, 0x0, 0x7));

    if (clearSysrefFlag == 0)
    {
        if (*sysrefReceived)
            afeLogDbg("%s", "AFE Sysref Received.");
        else
            afeLogErr("%s", "AFE Sysref Not Received.");
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Give a new Sysref to the AFE
    @details This function is used to send a new sysref to the AFE. This enables the latch and performs the required operations for AFE to accept a new Sysref. <br>
            Note the following:<br>
            1. Contents of the giveSingleSysrefPulse function should be replaced by host function to give Pin Sysref to AFE. This is used only in case of a single shot sysref.<br>
            2. For Continuous Syref mode, external Pin Sysref should be enabled before this function is called. Note that even in this case, only one pulse edge will be captured by the AFE. In this mode, giveSingleSysrefPulse needn't do any operation. <br>
            3. AFE79_CURR_SYSPARAM.spiInUseForPllAccess should be set before the function call to the appropriate value for selecting SPIA/SPIB. In Normal use-case SPIA is used and hence can be left at the default.<br>
            4. The selection between the single shot and continuous sysref mode should be done in Latte during generation of the configuration log.
    @param afeInst AFE ID
    @param spiSysref If this is set to 0, external pin based Sysref is used. If this is set to 1, then the internal override of the Sysref pin will be used. Note that in this case, deterministic latency will not satisfied.
    @param getSpiAccess Setting this to 1 will take PLL SPI access. This should always be set 1.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(sendSysref)(AFE79_INST_TYPE afeInst, uint8_t spiSysref, uint8_t getSpiAccess)
{

    uint8_t sysrefReached = 0;
    AFE79_ID_VALIDITY();

    AFE79_FUNC_EXEC(AFE79FNP(checkSysref)(afeInst, 1, &sysrefReached));

    if (getSpiAccess == 1)
    {
        AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, AFE79_CURR_SYSPARAM.spiInUseForPllAccess));
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x80, 0x0, 0x7)); /*timing_controller*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85b, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85a, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x859, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x858, 0x0, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85b, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85a, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x859, 0x1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x858, 0x1, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85b, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x85a, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x859, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x858, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x1, 0x0, 0x7)); /*pll*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6a, 0x0, 0x1, 0x1));

    if (spiSysref == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6e, 0x1, 0x0, 0x0)); /*LCMGEN_USE_SPI_SYSREF*/
    }

    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6e, 0x0, 0x0, 0x0)); /*LCMGEN_USE_SPI_SYSREF*/
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6a, 0x0, 0x1, 0x1));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6a, 0x2, 0x1, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x58, 0x2, 0x1, 0x1));
    AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 10));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x58, 0x0, 0x1, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    if (spiSysref == 0)
    {
        /*		Need to Enable the Sysref toggle here in case of single shot sysref. Host function to be called here.	*/
        AFE79_FUNC_EXEC(AFE79FNP(giveSingleSysrefPulse)(afeInst));
        /* Sysref Enable Host function Call. */
    }
    else if (spiSysref == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x1, 0x0, 0x7)); /*pll*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6e, 0x0, 0x1, 0x1)); /*LCMGEN_SPI_SYSREF*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6e, 0x2, 0x1, 0x1)); /*LCMGEN_SPI_SYSREF*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x6e, 0x0, 0x1, 0x1)); /*LCMGEN_SPI_SYSREF*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    }

    if (getSpiAccess == 1)
    {
        AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, 0));
    }
    AFE79_FUNC_EXEC(AFE79FNP(checkSysref)(afeInst, 0, &sysrefReached));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the PLL Lock Status
    @details This function checks the PLL Lock Status and returns it as a pointer.
    @param afeInst AFE ID
    @param pllLockStatus Pointer Return of the lock statud of the PLL. 3 is ideal good state.<br>
            0: LOCK is low and LOCK_LOST is high. PLL is currently not locked but locked some time in the past since the status clear bit was last toggled. <br>
            1: LOCK is high and LOCK_LOST is high. PLL is currently locked but lost lock since the status clear bit was last toggled. (since clearPllStickyLockStatus was called)<br>
            2: LOCK is low and LOCK_LOST is low. PLL is currently not locked and never locked since the status clear bit was last toggled.<br>
            3: LOCK is high and LOCK_LOST is low. PLL is currently locked and didn't lose lock since the status clear bit was last toggled. (since clearPllStickyLockStatus was called).
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkPllLockStatus)(AFE79_INST_TYPE afeInst, uint8_t *pllLockStatus)
{

    AFE79_ID_VALIDITY();
    uint8_t ulRegValue = 0;
    *pllLockStatus = 0;
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, AFE79_CURR_SYSPARAM.spiInUseForPllAccess));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0066, 0x0, 0x7, &ulRegValue));
    if (((ulRegValue >> 4) & 1) == 0)
    {
        afeLogErr("%s", "PLL didn't lock");
    }
    else
    {
        *pllLockStatus |= 1;
        afeLogInfo("%s", "PLL locked.");
    }
    if (((ulRegValue >> 6) & 1) == 0)
    {
        *pllLockStatus |= 2;
        afeLogInfo("%s", "PLL LOCK_LOST_STICKY is low. That is, PLL didn't lose Lock. ");
    }
    else
    {
        afeLogInfo("%s", "PLL LOCK_LOST_STICKY is high. That is, PLL lost lock in between. ");
        // errorStatus |= 1;
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, 0));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Clears the PLL Lock Sticky Status
    @details This function clears the PLL Lock sticky Status.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(clearPllStickyLockStatus)(AFE79_INST_TYPE afeInst)
{

    AFE79_ID_VALIDITY();
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, AFE79_CURR_SYSPARAM.spiInUseForPllAccess));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0063, 0x40, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0063, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, 0));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Clears the SPI Alarm Status.
    @details This function clears the SPI Alarm Sticky Status. This is important when multiple SPIs are used and not critical when single SPI is being used.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(clearSpiAlarms)(AFE79_INST_TYPE afeInst)
{
    AFE79_ID_VALIDITY();

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x001b, 0xff, 0x0, 0x7)); /*alarms_clear=0x1ff*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x001d, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x001b, 0x00, 0x0, 0x7)); /*alarms_clear=0x0*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x001d, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the SPI Alarm Status.
    @details This function reads the Alarm Status and returns it as a pointer. It also prints the error description.
    @param afeInst AFE ID
    @param alarmStatus Pointer return status of the SPI alarm. 0 means there are no alarms and 1 means there is a alarm.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readSpiAlarms)(AFE79_INST_TYPE afeInst, uint8_t *alarmStatus)
{
    AFE79_ID_VALIDITY();

    uint16_t alarmVal = 0;
    uint8_t readValue_lsb, readValue_msb;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x01e, 0x0, 0x7, &readValue_lsb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x01f, 0x0, 0x0, &readValue_msb));
    alarmVal = readValue_lsb + (readValue_msb << 8);
    const char *spiAlarms[9];

    spiAlarms[0] = "Both SPI-A & B1 access Global page at the same time.";
    spiAlarms[1] = "Both SPI-A & B1 access same page at the same time.";
    spiAlarms[2] = "Both SPI-A & B2 access Global page at the same time.";
    spiAlarms[3] = "Both SPI-A & B2 access same page at the same time.";
    spiAlarms[4] = "Both SPI-B1 & B2 access Global page at the same time.";
    spiAlarms[5] = "Both SPI-B1 & B2 access same page at the same time.";
    spiAlarms[6] = "Invalid Address Accessed by SPI-A.";
    spiAlarms[7] = "Invalid Address Accessed by SPI-B1.";
    spiAlarms[8] = "Invalid Address Accessed by SPI-B2.";
    *alarmStatus = 0;
    uint8_t a;
    for (a = 0; a < 9; a++)
    {
        if (((alarmVal >> a) & 1) == 1)
        {
            afeLogErr("SPI Alarm seen: %s", spiAlarms[a]);
            *alarmStatus |= 1;
        }
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the TX power.
    @details This function reads the TX Power.
    @param afeInst AFE ID
    @param chNo Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param windowLen Determines the window length for number of samples. <br>
        2^(windowLen+5) samples at the interface rate will be used for power measurement. Range of this is 0-0xfff
    @param powerReadB0 Pointer Return of Band 0 Power Read
    @param powerReadB1 Pointer Return of Band 1 Power Read
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readTxPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t windowLen, double *powerReadB0, double *powerReadB1)
{
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(windowLen <= 0xfff);
    AFE79_PARAMS_VALID(powerReadB0 != NULL);
    AFE79_PARAMS_VALID(powerReadB1 != NULL);
    uint32_t powerRead = 0;

    uint8_t pap_blk_status, alarm_mask_status, single_status, combined_status, readValue_lsb, readValue_msb, readValue_mid;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, (1 << (chNo + 4)), 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0528, 0, 0, &pap_blk_status));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x052d, 0, 3, &alarm_mask_status));
    if (pap_blk_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x052d, 0xf, 0, 3));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0528, 0x01, 0, 0));
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0525, 0, 0, &single_status));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0524, 0, 0, &combined_status));
    if (combined_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0525, 0x01, 0, 0));
    }
    if (single_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0524, 0x01, 0, 0));
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0571, (windowLen >> 8) & 0xf, 0, 3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0570, windowLen & 0xff, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x056c, 0x01, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0521, (windowLen >> 8) & 0xf, 0, 3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0520, windowLen & 0xff, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x051c, 0x01, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x056d, 0x01, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x056d, 0x00, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x051d, 0x01, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x051d, 0x00, 0, 0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05a0, 0, 7, &readValue_lsb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05a1, 0, 7, &readValue_mid));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05a2, 0, 0, &readValue_msb));
    powerRead = readValue_lsb + (readValue_mid << 8) + (readValue_msb << 16);
    *powerReadB0 = 10 * log10(powerRead * 1.0 / 0x10000);
    afeLogInfo("Band 0 Power Read %lfdBFS", *powerReadB0);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05b0, 0, 7, &readValue_lsb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05b1, 0, 7, &readValue_mid));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x05b2, 0, 0, &readValue_msb));
    powerRead = readValue_lsb + (readValue_mid << 8) + (readValue_msb << 16);
    *powerReadB1 = 10 * log10(powerRead * 1.0 / 0x10000);
    afeLogInfo("Band 1 Power Read %lfdBFS", *powerReadB1);

    if (combined_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0525, 0x00, 0, 0));
    }
    if (single_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0524, 0x00, 0, 0));
    }
    if (pap_blk_status == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0528, 0x00, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x052d, alarm_mask_status, 0, 3));
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0, 0, 7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the RX power.
    @details This function reads the RX Power.<br>
            Note that this detector is near the ADC-DDC interface and needs the RX TDD to be ON.<br>
            For reading FB power needed in ADC shared case, it should be operated in RX Mode and correponding RX channel should be read.
    @param afeInst AFE ID
    @param chNo Select the RX Channel<br>
            0 for RXA<br>
            1 for RXB<br>
            2 for RXC<br>
            3 for RXD
    @param avg_pwrdb Pointer Return of RX Power Read
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getRxRmsPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, double *avg_pwrdb)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_RX_CHANNELS);
    AFE79_PARAMS_VALID(avg_pwrdb != NULL);
    uint16_t avg_pwr;
    uint8_t pwr_det_on_state = 0;
    uint8_t readValue, avg_pwr_lsb, avg_pwr_msb;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 1 << chNo, 0x0, 0x7)); /*rxdig*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x404, 0x5, 0x5, &readValue));
    if (readValue == 0x0)
    {
        pwr_det_on_state = 1;
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x404, 0x1 << 5, 0x5, 0x5));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0xb04, 1, 0x0, 0x0)); /*pwr_det_read_sel_agc*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5c4, 0x0, 0x0, 0x0));

    AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5c4, 0x1, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x5d1, 0x0, 0x7, &avg_pwr_msb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x5d0, 0x0, 0x7, &avg_pwr_lsb));
    avg_pwr = (avg_pwr_msb << 8) + avg_pwr_lsb;

    *avg_pwrdb = 10 * log10(avg_pwr / 65536.0);
    afeLogInfo("RX channel %d, Average Power read in dbfs %lf", chNo, avg_pwrdb);
    if (pwr_det_on_state == 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x404, 0x0 << 5, 0x5, 0x5));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Read the FB power.
    @details This function reads the FB Power.<br>
            Note that this detector is near the ADC-DDC interface and needs the RX TDD to be ON.<br>
            For reading FB power needed in ADC shared case, it should be operated in RX Mode and correponding RX channel should be read.
    @param afeInst AFE ID
    @param chNo Select the FB Channel<br>
            0 for FB1<br>
            1 for FB2<br>
    @param avg_pwrdb Pointer Return of FB Power Read
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getFbRmsPower)(AFE79_INST_TYPE afeInst, uint8_t chNo, double *avg_pwrdb)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chNo < AFE79_NUM_FB_CHANNELS);
    AFE79_PARAMS_VALID(avg_pwrdb != NULL);
    uint16_t avg_pwr;
    uint8_t readValue, avg_pwr_lsb, avg_pwr_msb;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x10 << chNo, 0x0, 0x7)); /*fbdig*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0773, 0x0, 0x0, &readValue));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1015, 0x04, 0x2, 0x2));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x00, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x00, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0408, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0416, 0x04, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0415, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0414, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x042d, 0x0e, 0x0, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x042c, 0x42, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0452, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0451, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0450, 0x08, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x00, 0x1, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x00, 0x1, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0409, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x041a, 0x04, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0419, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0418, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0431, 0x0b, 0x0, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0430, 0x53, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0456, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0455, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0454, 0x08, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x00, 0x4, 0x4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x00, 0x4, 0x4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x040c, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0424, 0x12, 0x0, 0x4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x043d, 0x40, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x043c, 0x4e, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x00, 0x2, 0x2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x00, 0x2, 0x2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x040a, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x041e, 0x04, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x041d, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x041c, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0435, 0x0e, 0x0, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0434, 0x42, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x045a, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0459, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0458, 0x08, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x00, 0x3, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x00, 0x3, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x040b, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0422, 0x04, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0421, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0420, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0439, 0x0b, 0x0, 0x3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0438, 0x53, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x045e, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x045d, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x045c, 0x08, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0400, 0x20, 0x5, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0404, 0x20, 0x5, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x040d, 0x02, 0x0, 0x5));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0425, 0x12, 0x0, 0x4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x043f, 0x40, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x043e, 0x4e, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0498, 0x00, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0498, 0x00, 0x1, 0x1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1015, 0x00, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0b04, 0x01, 0x0, 0x0));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5c4, 0x0, 0x0, 0x0));
    AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5c4, 0x1, 0x0, 0x0));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x5d1, 0x0, 0x7, &avg_pwr_msb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x5d0, 0x0, 0x7, &avg_pwr_lsb));
    avg_pwr = (avg_pwr_msb << 8) + avg_pwr_lsb;

    *avg_pwrdb = 10 * log10(avg_pwr / 65536.0);
    afeLogInfo("FB channel %d, Average Power read in dbfs %lf", chNo, avg_pwrdb);

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0773, readValue, 0x2, 0x2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x1015, 0x00, 0x2, 0x2));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Clear all the alarms
    @details Clears all the AFE alarms
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(clearAllAlarms)(AFE79_INST_TYPE afeInst)
{
    AFE79_ID_VALIDITY();

    AFE79_FUNC_EXEC(AFE79FNP(clearSpiAlarms)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(clearJesdRxAlarms)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(clearJesdRxAlarmsForPap)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(clearJesdTxAlarms)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(clearPllStickyLockStatus)(afeInst));
    AFE79_FUNC_EXEC(AFE79FNP(clearPapAlarms)(afeInst, 0xf));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Checks the Device Health
    @details This function Reads the complete device health and returns as a pointer.
    @param afeInst AFE ID
    @param allOk Pointer return of the device health status.<br>
        If there is no error, allOk will be 0.<br>
            If it is non-zero, below is the interpretation<br>
            Bit 0: PLL Not Okay<br>
            Bit 1: DAC JESD Not Okay<br>
            Bit 2: ADC JESD Not Okay<br>
            Bit 3: SPI Not Okay<br>
            Bit 4: MCU Not Okay<br>
            Bit 5: PAP Triggered
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkDeviceHealth)(AFE79_INST_TYPE afeInst, uint16_t *allOk)
{

    uint8_t linkError = 0;
    uint8_t pllStatus = 0;
    uint8_t spiAlarm = 0;
    uint8_t mcuHealth = 0;
    uint8_t papStatus = 0;
    uint16_t linkStatus = 0;

    *allOk = 0;

    /*	#### PLL Status	#### */
    AFE79_FUNC_EXEC(AFE79FNP(checkPllLockStatus)(afeInst, &pllStatus));
    if (pllStatus != 3)
    {
        *allOk |= 1 << 0;
        afeLogErr("%s", "PLL lost lock currently or in the past.");
    }
    else
    {
        afeLogInfo("%s", "PLL is locked now and did not lose lock in the past.");
    }

    /*	#### JESD Status	#### */
    AFE79_FUNC_EXEC(AFE79FNP(getJesdRxLinkStatus)(afeInst, &linkStatus));
    if (linkStatus != 10)
    {
        afeLogErr("%s", "AFE DAC-JESD-RX Link Down.");
        *allOk |= 1 << 1;
    }
    else
    {
        afeLogInfo("%s", "AFE DAC-JESD-RX Link is good.");
    }

    AFE79_FUNC_EXEC(AFE79FNP(getJesdRxAlarms)(afeInst, &linkError));
    if (linkError != 0)
    {
        afeLogErr("%s", "AFE DAC-JESD-RX has some errors triggered.");
        *allOk |= 1 << 1;
    }
    else
    {
        afeLogInfo("%s", "AFE DAC-JESD-RX has No Errors triggered.");
    }

    /* ADC JESD */
    AFE79_FUNC_EXEC(AFE79FNP(getJesdTxFifoErrors)(afeInst, 0, &linkError));
    if (linkError != 0)
    {
        afeLogErr("%s", "AFE ADC-JESD-TX AB has some errors triggered.");
        *allOk |= 1 << 2;
    }
    else
    {
        afeLogInfo("%s", "AFE ADC-JESD-TX AB has no Errors triggered.");
    }
    AFE79_FUNC_EXEC(AFE79FNP(getJesdTxFifoErrors)(afeInst, 1, &linkError));
    if (linkError != 0)
    {
        afeLogErr("%s", "AFE ADC-JESD-TX CD has some errors triggered.");
        *allOk |= 1 << 2;
    }
    else
    {
        afeLogInfo("%s", "AFE ADC-JESD-TX CD has no Errors triggered.");
    }

    /* SPI Alarms */
    AFE79_FUNC_EXEC(AFE79FNP(readSpiAlarms)(afeInst, &spiAlarm));
    if (spiAlarm != 0)
    {
        *allOk |= 1 << 3;
        afeLogErr("%s", "SPI Alarm triggered.");
    }
    else
    {
        afeLogInfo("%s", "SPI Alarm Not triggered.");
    }

    /* MCU Health */
    AFE79_FUNC_EXEC(AFE79FNP(checkMcuHealth)(afeInst, &mcuHealth));
    if (mcuHealth != 1)
    {
        *allOk |= 1 << 4;
        afeLogErr("%s", "MCU Not Running.");
    }
    else
    {
        afeLogInfo("%s", "MCU Okay.");
    }

    /* PAP Status */
    uint8_t chNo;
    for (chNo = 0; chNo < 4; chNo++)
    {
        AFE79_FUNC_EXEC(AFE79FNP(papAlarmStatus)(afeInst, chNo, &papStatus));
        if (papStatus == 1)
        {
            afeLogErr("PAP triggered for TX Channel Number: %d", chNo);
            *allOk |= 1 << 5;
        }
    }

    return TI_AFE_RET_EXEC_PASS;
}


/**
    @brief Checks Async FIFO Status
    @details Checks Async FIFO Status
    @param afeInst AFE ID
    @param asyncFifoStatus Async FIFO Status as pointer return \verbatim
        A bit value of one means the corresponding Async FIFO pointer is not set correctly.
        Bit 0: RX1 ADC-DDC Async FIFO
        Bit 1: RX2 ADC-DDC Async FIFO
        Bit 2: RX3 ADC-DDC Async FIFO
        Bit 3: RX4 ADC-DDC Async FIFO
        Bit 4: RX1 DDC-JESD Async FIFO
        Bit 5: RX2 DDC-JESD Async FIFO
        Bit 6: RX3 DDC-JESD Async FIFO
        Bit 7: RX4 DDC-JESD Async FIFO
        Bit 8: FB1 ADC-DDC Async FIFO
        Bit 9: FB2 ADC-DDC Async FIFO
        Bit 10: FB1 DDC-JESD Async FIFO
        Bit 11: FB2 DDC-JESD Async FIFO
        Bit 12: TX1 DUC-DAC Async FIFO
        Bit 13: TX2 DUC-DAC Async FIFO
        Bit 14: TX3 DUC-DAC Async FIFO
        Bit 15: TX4 DUC-DAC Async FIFO
        Bit 16: TX1 JESD-DUC Async FIFO
        Bit 17: TX2 JESD-DUC Async FIFO
        Bit 18: TX3 JESD-DUC Async FIFO
        Bit 19: TX4 JESD-DUC Async FIFO
        Bit 20: ADC JESD TX - SerDes instance0 Async FIFO
        Bit 21: ADC JESD TX - SerDes instance1 Async FIFO
        Bit 22: SerDes RX - DAC JESD RX instance0 Async FIFO
        Bit 23: SerDes RX - DAC JESD RX instance1 Async FIFO
        \endverbatim
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(checkAsyncFifoStatus)(AFE79_INST_TYPE afeInst, uint64_t *asyncFifoStatus)
{
    AFE79_ID_VALIDITY();
    uint8_t writePtr=0, readPtr=0, rxChNo = 0, fbChNo = 0, txChNo = 0, iterCnt = 0, pointerDiff = 0, tempReadVal = 0, instanceNo =0;
    uint8_t iterCntMax = 10, laneEna=0;
    uint8_t fifoDepth, statusBitNo;
    uint8_t diffErrorThresh = 1;

    *asyncFifoStatus =0;

    // RX ADC-DDC Async FIFO
    fifoDepth=12;
    for (rxChNo = 0; rxChNo < AFE79_NUM_RX_CHANNELS; rxChNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 1<<rxChNo, 0x0, 0x7));
        if (AFE79_CURR_SYSPARAM.rxEnable[rxChNo]==0){
            continue;
        }
        statusBitNo = rxChNo;
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2477, 1, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 0, 0x0, 0x7));
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 1, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 0, 0x0, 0x7));

            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x247c, 0x0, 0x7, &readPtr));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x2480, 0x0, 0x7, &writePtr));
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) || (pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("RX ADC- DDC FIFO offset not set properly for rxChNo = %d", rxChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2477, 0, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0, 0x0, 0x7));
    }


    // RX DDC-JESD Async FIFO
    fifoDepth=16;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x10, 0x0, 0x7));
    for (rxChNo = 0; rxChNo < AFE79_NUM_RX_CHANNELS; rxChNo++){
        if (AFE79_CURR_SYSPARAM.rxEnable[rxChNo]==0){
            continue;
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0160, 1 << 7, 0x7, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, (rxChNo << 5) + 0, 0x0, 0x7));
            
        statusBitNo = 4 + rxChNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, (rxChNo << 5) + 1, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, (rxChNo << 5) + 0, 0x0, 0x7));

            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0162, 0x0, 0x7, &tempReadVal));
            readPtr =tempReadVal & 0xf;
            writePtr =tempReadVal >> 4;
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("RX DDC-JESD FIFO offset not set properly for rxChNo = %d", rxChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0160, 0, 0x7, 0x7));
        
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0, 0x0, 0x7));


    // FB ADC-DDC Async FIFO
    fifoDepth=12;
    for (fbChNo = 0; fbChNo < AFE79_NUM_FB_CHANNELS; fbChNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x10 << (fbChNo), 0x0, 0x7));
        if (AFE79_CURR_SYSPARAM.fbEnable[fbChNo]==0){
            continue;
        }
        statusBitNo = 8 + fbChNo;
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2477, 1, 0x0, 0x7));
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 0, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 1, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2475, 0, 0x0, 0x7));

            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x247c, 0x0, 0x7, &readPtr));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x2480, 0x0, 0x7, &writePtr));
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("FB ADC- DDC FIFO offset not set properly for fbChNo = %d", fbChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2477, 0, 0x0, 0x7));
        
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0, 0x0, 0x7));
    }

    // FB DDC-JESD Async FIFO
    fifoDepth=16;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x10, 0x0, 0x7));
    for (fbChNo = 0; fbChNo < AFE79_NUM_FB_CHANNELS; fbChNo++){
        if (AFE79_CURR_SYSPARAM.fbEnable[fbChNo]==0){
            continue;
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0160, 1, 0x7, 0x7));

        statusBitNo = 10 + fbChNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, ((4 + fbChNo) << 5) + 0, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, ((4 + fbChNo) << 5) + 1, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0161, ((4 + fbChNo) << 5) + 0, 0x0, 0x7));

            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0162, 0x0, 0x7, &tempReadVal));
            readPtr =tempReadVal & 0xf;
            writePtr =tempReadVal >> 4;
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("FB DDC-JESD FIFO offset not set properly for fbChNo = %d", fbChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0160, 0, 0x7, 0x7));

    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0, 0x0, 0x7));


    // TX DUC-DAC Async FIFO
    fifoDepth=12;
    for (txChNo = 0; txChNo < AFE79_NUM_TX_CHANNELS; txChNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10<<txChNo, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a38, 1, 0x0, 0x7));
        if (AFE79_CURR_SYSPARAM.txEnable[txChNo]==0){
            continue;
        }
        statusBitNo = 12 + txChNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a59, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a59, 1, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a59, 0, 0, 7));

            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0b0c, 0x0, 0x4, &readPtr));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0b00, 0x0, 0x4, &writePtr));
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("TX DUC- DAC FIFO offset not set properly for txChNo = %d", txChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a38, 0, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0, 0x0, 0x7));
    }

    // TX JESD-DUC Async FIFO
    fifoDepth=16;
    for (txChNo = 0; txChNo < AFE79_NUM_TX_CHANNELS; txChNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0x10<<(txChNo&2), 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a38, 1, 0x0, 0x7));
        if (AFE79_CURR_SYSPARAM.txEnable[txChNo]==0){
            continue;
        }
        statusBitNo = 16 + txChNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0acc, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0acc, 1, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0acc, 0, 0, 7));
            if ((txChNo & 1) == 0){
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0adc, 0x0, 0x5, &readPtr));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0ad4, 0x0, 0x5, &writePtr));
            }
            else{
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0adc, 0x0, 0x5, &readPtr));
                AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0ad4, 0x0, 0x5, &writePtr));
            }
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("TX JESD- DUC FIFO offset not set properly for txChNo = %d", txChNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0a38, 0, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0019, 0, 0x0, 0x7));
    }


    // ADC JESD TX-SerDes Async FIFO
    fifoDepth=16;
    for (instanceNo = 0; instanceNo < 2; instanceNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x1<<instanceNo, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x023, 0x0, 0x3, &laneEna));
        if (laneEna==0){
            continue;
        }
        statusBitNo = 20 + instanceNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0f3, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0f3, 1, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0f3, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0f6, 0x1, 0x4, &readPtr));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0f5, 0x0, 0x3, &writePtr));
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("ADC JESD TX- SerDes TX offset not set properly for JESD instanceNo = %d", instanceNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0, 0x0, 0x7));
    }

    
    // SerDes-DAC JESD RX Async FIFO
    fifoDepth=16;
    for (instanceNo = 0; instanceNo < 2; instanceNo++){
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0x4<<instanceNo, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x064, 0x0, 0x3, &laneEna));
        if (laneEna==0){
            continue;
        }
        statusBitNo = 22 + instanceNo;
        for (iterCnt = 0; iterCnt < iterCntMax; iterCnt++){
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0150, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0150, 1, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0150, 0, 0, 7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0151, 0x0, 0x7, &tempReadVal));
            writePtr = tempReadVal&0xff;
            readPtr = tempReadVal >> 4;
            pointerDiff = writePtr > readPtr ? ((writePtr - readPtr) % fifoDepth) : ((readPtr - writePtr) % fifoDepth);
            if ((pointerDiff <= diffErrorThresh) ||(pointerDiff >= (fifoDepth - diffErrorThresh))){
                *asyncFifoStatus |= (1<<statusBitNo);
                afeLogErr("SerDes RX - ADC JESD TX offset not set properly for JESD instanceNo = %d", instanceNo);
                break;
            }
        }
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0016, 0, 0x0, 0x7));
    }
    return TI_AFE_RET_EXEC_PASS;
}


/**
    @brief Readout of the SYSREF alignment detector
    @details Readout of the SYSREF alignment detector
    @param afeInst AFE ID
    @param sysrefMonitorReadout Readout value 6: SYSREF alignment has sufficient margin.
                                Other readout values: SYSREF is in window of timing uncertainty, Advance/delay SYSREF in steps of 10-15ps to enter valid window.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readSysrefMonitor)(AFE79_INST_TYPE afeInst, uint8_t *sysrefMonitorReadout)
{
    AFE79_ID_VALIDITY();

    uint8_t byteList[3];
    uint8_t numOfOperands = 0;
    uint8_t ulRegValue = 0;

    uint8_t temp0 = 0;
    uint8_t temp1 = 0;
    uint8_t temp2 = 0;
    uint8_t temp3 = 0;

    *sysrefMonitorReadout = 0;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x02, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CB, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CA, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C9, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C8, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));

    byteList[numOfOperands] = 0;
    numOfOperands++;
    byteList[numOfOperands] = 1;
    numOfOperands++;
    byteList[numOfOperands] = 20;
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, 0x71));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x02, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00CB, 0x0, 0x7, &temp3));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00CA, 0x0, 0x7, &temp2));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00C9, 0x0, 0x7, &temp1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00C8, 0x0, 0x7, &temp0));
    
    temp2 += 0x80;
    temp0 += 0x01;	
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CB, temp3, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CA, temp2, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C9, temp1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C8, temp0, 0x0, 0x7));
    
    temp0 += 0x04;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CB, temp3, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CA, temp2, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C9, temp1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C8, temp0, 0x0, 0x7));

    temp0 -= 0x04;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CB, temp3, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CA, temp2, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C9, temp1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C8, temp0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));

    AFE79_FUNC_EXEC(AFE79FNP(sendSysref)(afeInst, 0, 1));

    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, AFE79_CURR_SYSPARAM.spiInUseForPllAccess));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x007B, 0x0, 0x7, &ulRegValue));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x007A, 0x0, 0x7, &ulRegValue));
    *sysrefMonitorReadout = ((ulRegValue & 0x01) << 2);    // sm1
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0079, 0x0, 0x7, &ulRegValue));
    *sysrefMonitorReadout += ((ulRegValue >> 6) & 0x03);    // sm0

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0078, 0x0, 0x7, &ulRegValue));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));

    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, 0));

    temp2 -= 0x80;
    temp0 -= 0x01;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x02, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CB, temp3, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00CA, temp2, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C9, temp1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x00C8, temp0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0015, 0x00, 0x0, 0x7));

    if ((*sysrefMonitorReadout) == 0x6)
        {
            afeLogDbg("%s", "Sysref Clock is in Valid window");
        }
    else
        {
            afeLogErr("%s", "Sysref Clock is invalid window");
        }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Start Bit Monitoring.
    @details Starts Bit Monitoring
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(startMonitoring)(AFE79_INST_TYPE afeInst)
{
    uint8_t byteList[5]={1,0,0,0,1};
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, 5, 0xdc)); // MacroConsts.MACRO_OPCODE_LIST.FLOATING_POINT_CONFIG_ALC);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Stop Bit Monitoring.
    @details Stop Bit Monitoring
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(stopMonitoring)(AFE79_INST_TYPE afeInst)
{
    uint8_t byteList[5]={1,0,0,0,0};
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, 5, 0xdc)); // MacroConsts.MACRO_OPCODE_LIST.FLOATING_POINT_CONFIG_ALC);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Compute golden Parity Bit Monitoring.
    @details Compute golden Parity Bit Monitoring
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(computeGolden)(AFE79_INST_TYPE afeInst)
{
    uint8_t byteList[4]={2,0,0,0};
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, 4, 0xdc)); // MacroConsts.MACRO_OPCODE_LIST.FLOATING_POINT_CONFIG_ALC);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Temperature Sensor Read Out
    @details Temperature Sensor Read Out
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param tempValue Pointer Return. Temperature value read out in degrees C
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(getDeviceTemp)(AFE79_INST_TYPE afeInst, int16_t *tempValue)
{
    uint8_t errorStatus = 0;
    AFE79_ID_VALIDITY();
    uint8_t ulRegValue;
    uint16_t temp=0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x40, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0258, 0x0, 0x7, &ulRegValue));
    temp = ulRegValue;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0259, 0x0, 0x7, &ulRegValue));
    temp +=   (ulRegValue << 8);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, AFE_MACRO_PAGE_REG_ADDR, 0x000, 0x0, 0x7));
    if (temp >= 32768)
    {
        temp = temp - 65536;
    }
    *tempValue  =   temp;

    if (errorStatus)
        return TI_AFE_RET_EXEC_FAIL;
    else
        return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Pll Cap Code Read Out
    @details Pll Cap Code Read Out
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param pllCapCode Pointer return of Pll cap code.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readPllCapCode)(AFE79_INST_TYPE afeInst, uint8_t *pllCapCode)
{
    AFE79_ID_VALIDITY();
    uint8_t regValue;
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, AFE79_CURR_SYSPARAM.spiInUseForPllAccess));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x1, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x67, 0x0, 0x7, &regValue));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0x0, 0x7));
    AFE79_FUNC_EXEC(AFE79FNP(requestPllSpiAccess)(afeInst, 0));
    *pllCapCode =   regValue;

    return TI_AFE_RET_EXEC_PASS;
}