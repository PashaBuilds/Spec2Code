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

/** @file tiAfe79_calibrations.c
 * 	@brief	This file has Factory calibration related functions.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added this file only in version 2.1.<br>
 * 		2. Added documentation and improved the parameter validity checks.<br>
 * 		3. Modified the RX DSA calibration function to add placeholder function for channel inputs.<br>
 * 		4. Added TX DSA calibration function.<br>
 */

#include <stdint.h>

#include <math.h>

#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeCommonMacros.h"

#include "tiAfe79_afeParameters.h"
#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"
#include "tiAfe79_controls.h"
#include "tiAfe79_calibrations.h"
#include "tiAfe79_macro.h"

/**
    @brief Perform ADC DSA Calibration
    @details This function Performs the RX DSA calibration. giveAfeAdcInput function in baseFunc.c file contents should be coded by the user as needed.
    However, in a single band case, if all the channels can be given input at the same time, this function needn't do any operation and all the channels should be given input before calling this function.
    @param afeInst AFE ID
    @param rxChainForCalib Bit Wise RX Channel Select.
            Bit0 for RXA<br>
            Bit1 for RXB<br>
            Bit2 for RXC<br>
            Bit3 for RXD
    @param fbChainForCalib Bit Wise FB Channel Select.
            Bit0 for FBAB<br>
            Bit1 for FBCD
    @param useTxForCalib When Set to 1, TX TDD will be kept on so that TX can be used for the calibration. The data should be still sent from the ASIC/FPGA through JESD.
    @param rxDsaBandCalibMode Sets the RX DSA Band Calibration Mode.<br>
        0 -One Band at a time<br>
        1 - both bands together
    @param readPacket Pointer returns Array of the Read packet. This should be stored in the host memory and be loaded post initialization in normal mode of operation.
    @param readPacketSize Pointer returns the size of the array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(doRxDsaCalib)(AFE79_INST_TYPE afeInst, uint8_t rxChainForCalib, uint8_t fbChainForCalib, uint8_t useTxForCalib, uint8_t rxDsaBandCalibMode, uint8_t *readPacket, uint16_t *readPacketSize)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(rxChainForCalib <= AFE79_NUM_RX_CHANNELS_BITWISE);
    AFE79_PARAMS_VALID(fbChainForCalib <= AFE79_NUM_FB_CHANNELS_BITWISE);

    uint8_t byteList[16];
    uint8_t numOfOperands = 0;
    uint8_t calibType = 1;
    uint8_t minAnaDsa = 0;
    uint8_t maxAnaDsa = AFE_RX_DSA_MAX_ANA_DSA_DB;
    uint16_t packetSize = 0;
    uint8_t tempVal = 0;

    

    if (useTxForCalib == 1)
    {
        AFE79_FUNC_EXEC(AFE79FNP(overrideTdd)(afeInst, 15, 0, 15, 1)); /*Overiding TDD Enables to remove dependency to pins.*/
    }
    else
    {
        AFE79_FUNC_EXEC(AFE79FNP(overrideTdd)(afeInst, 15, 0, 0, 1)); /*Overiding TDD Enables to remove dependency to pins.*/
    }
    /*
        Starting the DSA Calibration.
    */
    byteList[0] = 1;
    byteList[1] = calibType;
    numOfOperands = 2;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));
    AFE79_FUNC_EXEC(AFE79FNP(overrideTddPins)(afeInst, 1, 1, 1));
    
    /*
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x08, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x709e, 0x7a, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x709f, 0x28, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x00, 0x0, 0x7));
    */

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x17ba, 0x7a, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x17bb, 0x28, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x0, 0x0, 0x7));
    uint8_t chNo;
    for (chNo = 0; chNo < 4; chNo++)
    {
        if (((rxChainForCalib >> chNo) & 1) == 0)
        {
            continue;
        }
        /*Setting up the hardware for current channel.*/
        byteList[0] = 2;
        byteList[1] = calibType;
        byteList[2] = 0;
        byteList[3] = 0;
        byteList[4] = 1 << chNo;
        byteList[5] = 1 << (2*chNo);
        numOfOperands = 6;
        AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x01 << (chNo & 2), 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2333, 0x01, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2322, 0x01, 0x0, 0x7));
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2322, 0x00, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2333, 0x00, 0x0, 0x7));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x00, 0x0, 0x7));
        uint8_t bandNo;
        for (bandNo = 0; bandNo < 2; bandNo++)
        {
            if ((AFE79_CURR_SYSPARAM.numBandsRx[chNo] == 1 && rxDsaBandCalibMode == 1 && bandNo == 1) || (AFE79_CURR_SYSPARAM.numBandsRx[chNo] == 0 && bandNo == 1))
            {
                continue;
            }
            afeLogInfo("Calibrating RX%d, Band%d. Give input on 128 point bin.", chNo, bandNo);

            /*Giving the Channel Select Information for Macro*/
            AFE79_FUNC_EXEC(AFE79FNP(giveAfeAdcInput)(afeInst, chNo, bandNo));
            byteList[0] = 3;
            byteList[1] = calibType;
            byteList[2] = 0;
            byteList[3] = 0;
            byteList[4] = 1 << chNo;
            if (AFE79_CURR_SYSPARAM.numBandsRx[chNo] == 1 && rxDsaBandCalibMode == 1)
            {
                byteList[5] = 3 << (2*chNo);
            }
            else
            {
                byteList[5] = (1 << bandNo) << (2*chNo);
            }
            byteList[6] = 0;
            byteList[7] = 0;
            byteList[8] = 0x32;
            byteList[9] = 0;
            byteList[10] = 0;
            byteList[11] = 0; 
            byteList[12] = 0;
            byteList[13] = 0;
            byteList[14] = 0;
            byteList[15] = 0;
            numOfOperands = 16;
            AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));
        }
    }

    if (fbChainForCalib != 0)
    {
        if (useTxForCalib == 1)
        {
            AFE79_FUNC_EXEC(AFE79FNP(overrideTdd)(afeInst, 0, fbChainForCalib & 3, 15, 1)); /*Overiding TDD Enables to remove dependency to pins.*/
        }
        else
        {
            AFE79_FUNC_EXEC(AFE79FNP(overrideTdd)(afeInst, 0, fbChainForCalib & 3, 0, 1)); /*Overiding TDD Enables to remove dependency to pins.*/
        }
        uint8_t chNo;
        for (chNo = 0; chNo < 2; chNo++)
        {
            if (((fbChainForCalib >> chNo) & 1) == 0)
            {
                continue;
            }

            /*Setting up the hardware for current channel.*/
            byteList[0] = 2;
            byteList[1] = calibType;
            byteList[2] = 0;
            byteList[3] = 0;
            byteList[4] = 1 << (chNo + 4);
            byteList[5] = 1;
            numOfOperands = 6;
            AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x01 << chNo, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2333, 0x01, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2332, 0x01, 0x0, 0x7));
            AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2332, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2333, 0x00, 0x0, 0x7));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x00, 0x0, 0x7));
            afeLogInfo("Calibrating FB %d. Give input on 128 point bin.", chNo);
            AFE79_FUNC_EXEC(AFE79FNP(giveAfeAdcInput)(afeInst, chNo + AFE79_NUM_RX_CHANNELS, 0));
            /*Giving the Channel Select Information for Macro*/

            byteList[0] = 3;
            byteList[1] = calibType;
            byteList[2] = 0;
            byteList[3] = 0;
            byteList[4] = 1 << (chNo + 4);
            byteList[5] = 1;
            byteList[6] = 0;
            byteList[7] = 0;
            byteList[8] = 0x32;
            byteList[9] = 0;
            byteList[10] = 0;
            byteList[11] = 0;
            byteList[12] = 0;
            byteList[13] = 0;
            byteList[14] = 0;
            byteList[15] = 0;
            numOfOperands = 16;
            AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));
        }
    }

    byteList[0] = 4;
    byteList[1] = calibType;
    byteList[2] = 0;
    byteList[3] = 0;
    byteList[4] = 0;
    byteList[5] = 0xff;
    byteList[6] = 0;
    byteList[7] = minAnaDsa;
    byteList[8] = maxAnaDsa;
    byteList[9] = 0x3;
    byteList[10] = 0x0;
    byteList[11] = 0x0;
    numOfOperands = 12;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION));

    /*Read the packet Size*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x20, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00FC, 0x0, 0x7, &tempVal));
    packetSize = tempVal;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00FD, 0x0, 0x7, &tempVal));
    packetSize = packetSize + (tempVal << 8);

    /*Read the Packet. This packet should be saved.*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0144, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x01, 0x0, 0x7));
    *readPacketSize = packetSize;
    uint16_t i;
    for (i = 0; i < packetSize; i++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0020 + i, 0x0, 0x7, &tempVal));
        readPacket[i] = tempVal;
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x00, 0x0, 0x7));

    /*Apply the calibrated packet.*/
    byteList[0] = 1;
    numOfOperands = 1;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_APPLY_DSA_GAIN_PHASE_COMPENSATION));

    /*Toggling the DSA Change Pulses to apply the new packet.*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0013, 0xc0, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0320, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0370, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x02c8, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x02c8, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x02c8, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0013, 0x00, 0x0, 0x7));

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x30, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0d90, 0x01, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x2014, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0012, 0x00, 0x0, 0x7));
    /* Release TDD Pin Controls to Pins */
    AFE79_FUNC_EXEC(AFE79FNP(overrideTddPins)(afeInst, 0, 0, 0));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Perform DAC DSA Calibration
    @details This function Performs the TX DSA calibration. connectAfeTxToFb function in baseFunc.c file contents should be coded by the user as needed.
    However, in a single band case, if all the channels can be given input at the same time, this function needn't do any operation and all the channels should be given input before calling this function.
    @param afeInst AFE ID
    @param txChainForCalib Bit Wise TX Channel Select.<br>
            Bit0 for TXA<br>
            Bit1 for TXB<br>
            Bit2 for TXC<br>
            Bit3 for TXD
    @param txDsaCalibMode DSA Calibration Mode.<br>0 -Single Fb Mode FB AB ; 1 -Single Fb Mode FB CD ; 2- Dual Fb_Mode
    @param txDsaBandCalibMode Sets the TX DSA Band Calibration Mode.<br>
        0 -One Band at a time<br>
        1 - both bands together
    @param readPacket Pointer returns Array of the Read packet. This should be stored in the host memory and be loaded post initialization in normal mode of operation.
    @param readPacketSize Pointer returns the size of the array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(doTxDsaCalib)(AFE79_INST_TYPE afeInst, uint8_t txChainForCalib, uint8_t txDsaCalibMode, uint8_t txDsaBandCalibMode, uint8_t *readPacket, uint16_t *readPacketSize)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(txChainForCalib <= AFE79_NUM_TX_CHANNELS_BITWISE);

    uint8_t byteList[16];
    uint8_t numOfOperands = 0;
    uint8_t minAnaDsa = 0;
    uint8_t maxAnaDsa = AFE_TX_DSA_MAX_ANA_DSA_DB;
    uint16_t packetSize = 0;
    uint8_t tempVal = 0;
    uint8_t currentTxCalib = 0;
    uint8_t currentFbConnection = 0;
    uint8_t currentBandSel = 0;

    AFE79_FUNC_EXEC(AFE79FNP(overrideTdd)(afeInst, 0, 3, 15, 1)); /*Overiding TDD Enables to remove dependency to pins.*/
    //	Starting the DSA Calibration.
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 1));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x20, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0144, 0x04, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x08, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x70be, 0xff, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x70bf, 0x00, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x70be, 0x0c, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x70bf, 0x04, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x00, 0, 7));
    AFE79_FUNC_EXEC(AFE79FNP(enableMemAccess)(afeInst, 0));

    byteList[0] = 1;
    byteList[1] = 0;
    numOfOperands = 2;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_TX_DSA_GAIN_PHASE_CALIBRATION));
    AFE79_FUNC_EXEC(AFE79FNP(overrideTddPins)(afeInst, 1, 1, 1));
    uint8_t chNo;
    uint16_t i;
    uint8_t bandNo;

    for (chNo = 0; chNo < 4; chNo++)
    {
        if ((((txChainForCalib >> chNo) & 1) == 0) || ((txDsaCalibMode == 2) && (txChainForCalib >= AFE79_NUM_FB_CHANNELS)))
        {
            continue;
        }
        if (txDsaCalibMode == 0)
        {
            currentTxCalib = 1 << chNo;
            currentFbConnection = 1;
        }
        else if (txDsaCalibMode == 1)
        {
            currentTxCalib = 1 << chNo;
            currentFbConnection = 2;
        }
        else if (txDsaCalibMode == 2)
        {
            currentTxCalib = 5 << chNo;
            currentFbConnection = 3;
        }
        else
        {
            afeLogErr("%s", "Invalid txDsaCalibMode passed.");
            return TI_AFE_RET_EXEC_FAIL;
        }
        for (i = 0; i < AFE79_NUM_TX_CHANNELS; i++) // To Prevent coupling for other channels.
        {
            if (AFE79_CURR_SYSPARAM.ncoFreqMode == 1)
            {
                AFE79_FUNC_EXEC(AFE79FNP(txCalibSiggen)(afeInst, i, 1, ((uint32_t)ceil(((AFE79_CURR_SYSPARAM.txNco[0][chNo][0] / (double)AFE79_CURR_SYSPARAM.Fdac) * (0x100000000)))) & 0xffffffff, 100));
            }
            else
            {
                AFE79_FUNC_EXEC(AFE79FNP(txCalibSiggen)(afeInst, i, 1, (uint32_t)(1000 * AFE79_CURR_SYSPARAM.txNco[0][chNo][0]), 100));
            }
        }
        for (bandNo = 0; bandNo <= AFE79_CURR_SYSPARAM.numBandsTx[chNo]; bandNo++)
        {
            if ((txDsaBandCalibMode == 0) || (AFE79_CURR_SYSPARAM.numBandsTx[chNo] == 0))
                currentBandSel = 1 << bandNo;
            else if (AFE79_CURR_SYSPARAM.numBandsTx[chNo] == 1)
                currentBandSel = 3;
            afeLogInfo("Calibrating TX Enables %d, Band %d.", currentTxCalib, bandNo);
            AFE79_FUNC_EXEC(AFE79FNP(connectAfeTxToFb)(afeInst, currentTxCalib, currentFbConnection, currentBandSel));

            byteList[0] = 3;
            byteList[1] = 0;
            byteList[2] = currentTxCalib;

            if (txDsaCalibMode == 0)
            {
                byteList[3] = 0;
            }
            else if (txDsaCalibMode == 1)
            {
                byteList[3] = 0xf;
            }
            else if (txDsaCalibMode == 2)
            {
                byteList[3] = 0xC;
            }
            byteList[4] = currentBandSel + (currentBandSel << 2) + (currentBandSel << 4) + (currentBandSel << 6);
            byteList[5] = 0;
            byteList[6] = 1;
            byteList[7] = 0;
            byteList[8] = AFE_TX_DSA_MAX_ANA_DSA_DB;
            byteList[9] = 3;
            byteList[10] = 0;
            byteList[11] = 0;
            numOfOperands = 12;
            AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_TX_DSA_GAIN_PHASE_CALIBRATION));
        }
    }
    // Generate the Calibration Packet
    byteList[0] = 4;
    byteList[1] = 0;
    byteList[2] = 0;
    byteList[3] = 0;
    byteList[4] = 0;
    byteList[5] = 0;
    byteList[6] = 1;
    byteList[7] = minAnaDsa;
    byteList[8] = maxAnaDsa;
    byteList[9] = 0x3;
    byteList[10] = 0x0;
    byteList[11] = 0x0;
    numOfOperands = 12;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_FACTORY_TX_DSA_GAIN_PHASE_CALIBRATION));

    /*Read the packet Size*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x20, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00FC, 0x0, 0x7, &tempVal));
    packetSize = tempVal;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x00FD, 0x0, 0x7, &tempVal));
    packetSize = packetSize + (tempVal << 8);

    /*Read the Packet. This packet should be saved.*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0144, 0x00, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x01, 0x0, 0x7));
    *readPacketSize = packetSize;
    for (i = 0; i < packetSize; i++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x0020 + i, 0x0, 0x7, &tempVal));
        readPacket[i] = tempVal;
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0018, 0x00, 0x0, 0x7));
    /*Apply the calibrated packet.*/
    byteList[0] = 0;
    numOfOperands = 1;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_APPLY_DSA_GAIN_PHASE_COMPENSATION));

    /* Release TDD Pin Controls to Pins */
    AFE79_FUNC_EXEC(AFE79FNP(overrideTddPins)(afeInst, 0, 0, 0));
    return TI_AFE_RET_EXEC_PASS;
}
/**
    @brief Load the TX DSA Calibration Packet
    @details This function loads the TX DSA Calibration Packet
    @param afeInst AFE ID
    @param array Pointer of array of the packet which was stored in host after calibration.
    @param arraySize Value of the size of the array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(loadTxDsaPacket)(AFE79_INST_TYPE afeInst, uint8_t *array, uint16_t arraySize)
{
    /*
    Pass the packet read back during calibration to apply it for TX DSA.
    */

    AFE79_ID_VALIDITY();
    uint8_t byteList[1];
    uint8_t numOfOperands = 0;

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x20, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0144, 0x00, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x01, 0, 7));
    uint16_t i;
    for (i = 0; i < arraySize; i++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x020 + i, array[i], 0, 7));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x00, 0, 7));
    byteList[numOfOperands] = (0);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_APPLY_DSA_GAIN_PHASE_COMPENSATION));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Load the ADC DSA Calibration Packet
    @details This function loads the ADC DSA Calibration Packet
    @param afeInst AFE ID
    @param array Pointer of array of the packet which was stored in host after calibration.
    @param arraySize Value of the size of the array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(loadRxDsaPacket)(AFE79_INST_TYPE afeInst, uint8_t *array, uint16_t arraySize)
{
    /*
    Pass the packet read back during calibration to apply it for TX DSA.
    */

    uint8_t byteList[1];
    uint8_t numOfOperands = 0;

    AFE79_ID_VALIDITY();
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x20, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x0144, 0x00, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x01, 0, 7));
    uint16_t i;
    for (i = 0; i < arraySize; i++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x020 + i, array[i], 0, 7));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x018, 0x00, 0, 7));
    byteList[numOfOperands] = (1);
    numOfOperands++;
    AFE79_FUNC_EXEC(AFE79FNP(executeMacro)(afeInst, byteList, numOfOperands, AFE_MACRO_OPCODE_APPLY_DSA_GAIN_PHASE_COMPENSATION));
    return TI_AFE_RET_EXEC_PASS;
}
#endif
