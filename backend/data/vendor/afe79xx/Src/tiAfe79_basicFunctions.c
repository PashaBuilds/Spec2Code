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

/** @file tiAfe79_basicFunctions.c
 * 	@brief	This file has Basic SPI functions.<br>
 * 		<b> Version 2.2:</b> <br>
 * 		1. Updated the log comment in serdesRawWrite function.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 *      2. Changed the C macros for all the spi wrapper function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
 *      3. Added closeAllPages function.<br>
 */
#include <stdint.h>
#include <stdio.h>

#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_afeCommonMacros.h"

#include "tiAfe79_baseFunc.h"
#include "tiAfe79_basicFunctions.h"
#include "tiAfe79_afeParameters.h"

#define MASK_BYTE(lsb, msb) (uint8_t)(((1 << ((msb) - (lsb) + 1)) - 1) << (lsb))
#define MASK_SHORT(lsb, msb) (uint16_t)(((1 << ((msb) - (lsb) + 1)) - 1) << (lsb))
#define CFG_SPI_READ_POLL_MAX_COUNT 500
#define AFE_REQ_SPI_ACCESS_MAX_COUNT 100
static const uint16_t afe79jesdToSerdesLaneMappingLocal[8] = afe79jesdToSerdesLaneMapping;

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
        @brief This function sets the default values for elements of device info struct.
        @details This function sets the default values for elements of device info struct.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @return Returns remapped RX bit-wise channel select.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(setDefaultParams)(AFE79_INST_TYPE afeInst)
{
    for (uint8_t j = 0; j < 4; j++)
    {

        AFE79_CURR_RX_CH_REMAP[j] = j;
        AFE79_CURR_TX_CH_REMAP[j] = j;
    }
    AFE79_CURR_FB_CH_REMAP[0] = 0;
    AFE79_CURR_FB_CH_REMAP[1] = 1;
    AFE_CURRENT_LOG_LEVEL = AFE_LOG_LEVEL_SPILOG;
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief This function should be called after updating all the system Params.
        @details This function should be called after updating all the system Params. This is yet to be updated.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @return Returns remapped RX bit-wise channel select.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(initializeConfig)(AFE79_INST_TYPE afeInst)
{

    for (uint8_t i = 0; i < 4; i++)
    {
        AFE79_CURR_SYSSTATUS.laneRateRx[i] = 0;
        AFE79_CURR_SYSSTATUS.laneRateTx[i] = 0;
    }
    for (uint8_t i = 0; i < 2; i++)
    {
        AFE79_CURR_SYSSTATUS.laneRateFb[i] = 0;
    }

    for (uint8_t i = 0; i < 8; i++)
    {
        AFE79_CURR_SYSSTATUS.serdesTxLaneRate[i] = 0;
        AFE79_CURR_SYSSTATUS.serdesRxLaneRate[i] = 0;
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief RX Channel Select Remap
        @details Remaps the RX bit-wise channel select.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param rxChSel RX bit-wise channel select.
        @return Returns remapped RX bit-wise channel select.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t rxChSel)
{
#ifdef ENABLE_RX_CH_REMAP
    uint8_t rxChannelPreRemap = rxChSel;
    rxChSel = 0;
    for (uint8_t i = 0; i < AFE79_NUM_RX_CHANNELS; i++)
    {
        rxChSel |= ((rxChannelPreRemap >> i) & 1) << AFE79_CURR_RX_CH_REMAP[i];
    }
#endif
    return rxChSel;
}

/**
        @brief TX Channel Select Remap
        @details Remaps the TX bit-wise channel select.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param txChSel TX bit-wise channel select.
        @return Returns remapped TX bit-wise channel select.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeTxChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t txChSel)
{
#ifdef ENABLE_TX_CH_REMAP
    uint8_t txChannelPreRemap = txChSel;
    txChSel = 0;
    for (uint8_t i = 0; i < AFE79_NUM_TX_CHANNELS; i++)
    {
        txChSel |= ((txChannelPreRemap >> i) & 1) << AFE79_CURR_TX_CH_REMAP[i];
    }
#endif
    return txChSel;
}

/**
        @brief FB Channel Select Remap
        @details Remaps the FB bit-wise channel select.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param fbChSel FB bit-wise channel select.
        @return Returns remapped FB bit-wise channel select.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeFbChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t fbChSel)
{
#ifdef ENABLE_FB_CH_REMAP
    uint8_t fbChannelPreRemap = fbChSel;
    fbChSel = 0;
    for (uint8_t i = 0; i < AFE79_NUM_FB_CHANNELS; i++)
    {
        fbChSel |= ((fbChannelPreRemap >> i) & 1) << AFE79_CURR_FB_CH_REMAP[i];
    }
#endif
    return fbChSel;
}

/**
        @brief FB+RX Channel Select Remap
        @details Remaps the FB+RX bit-wise channel select.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param RxFbChSel FB+RX bit-wise channel select.
        @return Returns remapped FB+RX bit-wise channel select. (Bit 0:RxA, Bit 1:RxB, Bit 2:RxC, Bit3:RxD, Bit 4:FbAB, Bit 5:FbCD)
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxFbChSelReMap)(AFE79_INST_TYPE afeInst, uint8_t RxFbChSel)
{
#ifdef ENABLE_RX_FB_CH_REMAP
    uint8_t RxFbChannelPreRemap = RxFbChSel;
    RxFbChSel = 0;
    for (uint8_t i = 0; i < AFE79_NUM_RX_CHANNELS; i++)
    {
        RxFbChSel |= ((RxFbChannelPreRemap >> i) & 1) << AFE79_CURR_RX_CH_REMAP[i];
    }
    RxFbChannelPreRemap = RxFbChannelPreRemap >> AFE79_NUM_RX_CHANNELS;
    
    for (uint8_t i = 0; i <AFE79_NUM_FB_CHANNELS; i++)
    {
        RxFbChSel |= ((RxFbChannelPreRemap >> i) & 1) << (AFE79_CURR_FB_CH_REMAP[i] + AFE79_NUM_RX_CHANNELS);
    }
#endif
    return RxFbChSel;
}



/**
        @brief RX Channel Number Remap
        @details Remaps the RX channel index.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param rxChNo RX channel index.
        @return Returns remapped RX channel index.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeRxChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t rxChNo)
{
#ifdef ENABLE_RX_CH_REMAP
    rxChNo = AFE79_CURR_RX_CH_REMAP[rxChNo];
#endif
    return rxChNo;
}

/**
        @brief TX Channel Number Remap
        @details Remaps the TX channel index.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param txChNo TX channel index.
        @return Returns remapped TX channel index.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeTxChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t txChNo)
{
#ifdef ENABLE_TX_CH_REMAP
    txChNo = AFE79_CURR_TX_CH_REMAP[txChNo];
#endif
    return txChNo;
}

/**
        @brief FB Channel Number Remap
        @details Remaps the FB channel index.
        @param afeInst AFE Instance of AFE79_INST_TYPE type
        @param fbChNo FB channel index.
        @return Returns remapped FB channel index.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeFbChNoReMap)(AFE79_INST_TYPE afeInst, uint8_t fbChNo)
{
#ifdef ENABLE_FB_CH_REMAP
    fbChNo = AFE79_CURR_FB_CH_REMAP[fbChNo];
#endif
    return fbChNo;
}

/**
    @brief Remap the SerDes TX lane Number to pre-lane mux JESD TX lane number
    @details Remap the SerDes TX lane Number to pre-lane mux JESD TX lane number
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param serDesLaneNo SerDes TX Lane Number
    @return Returns remapped pre-lane mux JESD lane number
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesTxToJesdLane)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneNo)
{
    return AFE79_CURR_SYSPARAM.jesdTxLaneMux[serDesLaneNo];
}

/**
    @brief Remap the SerDes RX lane Number to post-lane mux JESD RX lane number
    @details Remap the SerDes RX lane Number to post-lane mux JESD RX lane number
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param serDesLaneNo SerDes RX Lane Number
    @return Returns remapped post-lane mux JESD RX lane number
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesRxToJesdLane)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneNo)
{
    int8_t jesdLaneNo = -1;
    for (uint8_t i = 0; i < AFE79_NUM_SERDES_LANES; i++)
    {
        if (AFE79_CURR_SYSPARAM.jesdRxLaneMux[i] == serDesLaneNo)
        {
            jesdLaneNo = i;
            break;
        }
    }
    return jesdLaneNo;
}

/**
    @brief Remap the SerDes RX lane Number to post-lane mux JESD RX lane number
    @details Remap the SerDes RX lane Number to post-lane mux JESD RX lane number
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param serDesLaneSel SerDes RX Lane Number
    @return Returns remapped post-lane mux JESD RX lane number
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSerdesRxToJesdLaneSel)(AFE79_INST_TYPE afeInst, uint8_t serDesLaneSel)
{

    uint8_t jesdLaneSel = 0;
    for (uint8_t jesdLaneNo = 0; jesdLaneNo < AFE79_NUM_SERDES_LANES; jesdLaneNo++)
    {
        if (((serDesLaneSel >> AFE79_CURR_SYSPARAM.jesdRxLaneMux[jesdLaneNo]) & 1) == 1)
        {
            jesdLaneSel |= (1 << jesdLaneNo);
        }
    }
    return jesdLaneSel;
}

/**
        @brief SerDes Read
        @details SerDes registers are 16-bit wide while SPI is 8-bit. This necessitates a translation between SPI and SerDes. This function reads SerDes registers and returns the read value as a pointer.
        @param afeInst AFE ID
        @param addr SerDes address
        @param readVal Pointer returning the read value
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesRawRead)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t *readVal)
{

    uint8_t ucValueHigh = 0;
    uint8_t ucValueLow = 0;
    uint16_t usAddr = (uint16_t)(((addr + 0x2000) & 0x3fff) << 1);

    AFE79_PARAMS_VALID(readVal != NULL)

    /* It is important to read each Byte twice, but only the second matters. */
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, (usAddr + 1), &ucValueHigh));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, (usAddr + 1), &ucValueHigh));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, usAddr, &ucValueLow));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, usAddr, &ucValueLow));

    *readVal = ((uint16_t)ucValueHigh << 8) | (uint16_t)ucValueLow;
    afeLogSpiLog("SerDes Raw READ: afeInst:%d: ADDR: 0X%X, Read Val: 0X%X", AFE79_CURR_ID, addr, *readVal);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief SerDes Write
        @details SerDes registers are 16-bit wide while SPI is 8-bit. This necessitates a translation between SPI and SerDes. This function writes SerDes registers.
        @param afeInst AFE ID
        @param addr SerDes address
        @param data Value to be written.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesRawWrite)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t data)
{

    afeLogSpiLog("SerDes Raw Write: afeInst:%d: ADDR: 0X%X, Write Val: 0X%X", AFE79_CURR_ID, addr, data);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawWrite)(afeInst, (((addr + 0x2000) << 1) + 1) & 0x7fff, (uint8_t)((data >> 8) & 0xFF)));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawWrite)(afeInst, ((addr + 0x2000) << 1) & 0x7fff, (uint8_t)(data & 0xff)));
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
        @brief SPI Write Wrapper
        @details Writes the value to the specified bits of the register.
        @param afeInst AFE ID
        @param addr SPI address
        @param data Value to be written.
        @param lsb lsb of the field.
        @param msb msb of the field.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t data, uint8_t lsb, uint8_t msb)
{

    uint8_t readValue = 0;
    uint8_t writeValue = 0;
    uint8_t mask = 0;
    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID((msb < 8) && (lsb <= msb));
    afeLogSpiLog("WRITE: afeInst: %d, addr: 0x%X, data: 0x%X, lsb: %d, msb: %d", AFE79_CURR_ID, addr, data, lsb, msb);
    if ((msb == 7) && (lsb == 0))
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiRawWrite)(afeInst, addr, data));
        return TI_AFE_RET_EXEC_PASS;
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, addr, &readValue));
    mask = MASK_BYTE(lsb, msb);
    writeValue = (readValue & (0xFF ^ mask)) | (data & mask);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawWrite)(afeInst, addr, writeValue));

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief AFE SPI Write driver function.
    @details AFE SPI Write driver function. The contents of this function should be replaced by host SPI driver function.
    @param afeInst AFE Instance of AFE79_INST_TYPE type
    @param addr Address to be written to.
    @param data Array of values to be written.
    @param dataArraySize Side of the data array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiBurstWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t *data, uint16_t dataArraySize)
{

    AFE79_PARAMS_VALID(data != NULL);
    AFE79_FUNC_EXEC(AFE79FNP(afeSpiBurstWrite)(afeInst, addr, data, dataArraySize));
    for (uint16_t i = 0; i < dataArraySize; i++)
    {
        afeLogSpiLog("WRITE: Address: 0x%X, data: 0x%X, lsb: %d, msb: %d", addr + i, data[i], 0, 7);
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief SPI Read Wrapper
        @details Reads the value to the specified bits of the register and returns as a pointer.
        @param afeInst AFE ID
        @param addr SPI address
        @param lsb lsb of the field.
        @param msb msb of the field.
        @param readVal pointer of the read value.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t *readVal)
{

    uint8_t readValue = 0;

    AFE79_PARAMS_VALID((msb < 8) && (lsb <= msb));
    AFE79_PARAMS_VALID(readVal != NULL)

    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, addr, &readValue));
    *readVal = (readValue & MASK_BYTE(lsb, msb)) >> lsb;
    afeLogSpiLog("READ: afeInst: %d, addr: 0x%X, Read Value: 0x%X, lsb: %d, msb: %d", AFE79_CURR_ID, addr, *readVal, lsb, msb);
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief SerDes Write Wrapper
        @details Writes the value to the specified bits of the SerDes register.
        @param afeInst AFE ID
        @param addr SerDes address
        @param data Value to be written.
        @param lsb lsb of the field.
        @param msb msb of the field.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint16_t data, uint8_t lsb, uint8_t msb)
{

    uint16_t readValue = 0;
    uint16_t writeValue = 0;
    uint16_t mask = 0;

    AFE79_PARAMS_VALID((msb < 16) && (lsb <= msb));
    afeLogSpiLog("SerDes WRITE: afeInst: %d, addr: 0x%X, data: 0x%X, lsb: %d, msb: %d", AFE79_CURR_ID, addr, data, lsb, msb);
    if ((msb == 15) && (lsb == 0))
    {
        AFE79_SPI_EXEC(AFE79FNP(serdesRawWrite)(afeInst, addr, data));
        return TI_AFE_RET_EXEC_PASS;
    }

    AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, addr, &readValue));
    mask = MASK_SHORT(lsb, msb);
    writeValue = (readValue & (0xFFFF ^ mask)) | (data & mask);
    AFE79_SPI_EXEC(AFE79FNP(serdesRawWrite)(afeInst, addr, writeValue));
    return TI_AFE_RET_EXEC_PASS;
}

/**
        @brief SerDes Read Wrapper
        @details Reads the value to the specified bits of the SerDes register and returns as a pointer.
        @param afeInst AFE ID
        @param addr SerDes address
        @param lsb lsb of the field.
        @param msb msb of the field.
        @param readVal Pointer of the value to be written.
        @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint16_t *readVal)
{

    uint16_t readValue = 0;

    AFE79_PARAMS_VALID((msb < 16) && (lsb <= msb));
    AFE79_PARAMS_VALID(readVal != NULL)

    AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, addr, &readValue));

    *readVal = (readValue & MASK_SHORT(lsb, msb)) >> lsb;
    afeLogSpiLog("SerDes READ: afeInst: %d, addr: 0x%X, Read Value: 0x%X, lsb: %d, msb: %d", AFE79_CURR_ID, addr, *readVal, lsb, msb);

    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief SerDes Lane Write Wrapper
    @details Writes the value to the specified bits of the SerDes lane register of the corresponding lane by adding the appropriate offset.
    @param afeInst AFE ID
    @param addr SerDes lane base address
    @param laneNo SerDes lane Number. Values supported are: 0-7.
    @param data Value to be written.
    @param lsb lsb of the field.
    @param msb msb of the field.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesLaneWriteWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t laneNo, uint16_t data, uint8_t lsb, uint8_t msb)
{

    uint16_t readValue = 0;
    uint16_t writeValue = 0;
    uint16_t mask = 0;
    uint16_t usAddr = 0;

    AFE79_PARAMS_VALID((msb < 16) && (lsb <= msb));
    AFE79_PARAMS_VALID(laneNo < ARRAY_SIZE(afe79jesdToSerdesLaneMappingLocal));

    usAddr = addr + (0x100 * afe79jesdToSerdesLaneMappingLocal[laneNo]);
    if (msb == 15 && lsb == 0)
    {
        AFE79_SPI_EXEC(AFE79FNP(serdesRawWrite)(afeInst, usAddr, data));
        return TI_AFE_RET_EXEC_PASS;
    }

    AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, usAddr, &readValue));
    mask = MASK_SHORT(lsb, msb);
    writeValue = (readValue & (0xFFFF ^ mask)) | (data & mask);
    AFE79_SPI_EXEC(AFE79FNP(serdesRawWrite)(afeInst, usAddr, writeValue));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief SerDes Lane Read Wrapper
    @details Reads the value to the specified bits of the SerDes lane register of the corresponding lane by adding the appropriate offset. Returns the value as pointer.
    @param afeInst AFE ID
    @param addr SerDes lane base address
    @param laneNo SerDes lane number. 0-7 is the supported range.
    @param lsb lsb of the field.
    @param msb msb of the field.
    @param readVal Pointer of the value to be written.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(serdesLaneReadWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint32_t laneNo, uint8_t lsb, uint8_t msb, uint16_t *readVal)
{

    uint16_t readValue = 0;
    uint16_t usAddr = 0;

    AFE79_PARAMS_VALID((msb < 16) && (lsb <= msb));
    AFE79_PARAMS_VALID(laneNo < ARRAY_SIZE(afe79jesdToSerdesLaneMappingLocal));
    AFE79_PARAMS_VALID(readVal != NULL)

    usAddr = addr + (0x100 * afe79jesdToSerdesLaneMappingLocal[laneNo]);
    AFE79_SPI_EXEC(AFE79FNP(serdesRawRead)(afeInst, usAddr, &readValue));

    *readVal = (readValue & MASK_SHORT(lsb, msb)) >> lsb;
    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
    @brief AFE SPI Check Wrapper
    @details Reads and checks if the value of the field is as expected. Check Pass condition is (readValue&mask)==(data&mask) where mask = (((1 << ((msb) - (lsb) + 1)) - 1) << lsb);
    @param afeInst AFE ID
    @param addr SPI address
    @param data Expected Value.
    @param lsb lsb of the field.
    @param msb msb of the field.
    @param readCheckStatus Pointer return. Returns 0 if the check passes and if check fails.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiCheckWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t data, uint8_t *readCheckStatus)
{

    uint8_t readValue = 0;
    uint8_t mask = 0;
    AFE79_ID_VALIDITY();
    uint8_t libRunMode = 0;
    AFE79FNP(getAfeLibsRunMode)
    (&libRunMode);
    AFE79_PARAMS_VALID((msb < 8) && (lsb <= msb));
    AFE79_PARAMS_VALID(readCheckStatus != NULL)

    AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, addr, &readValue));

    mask = MASK_BYTE(lsb, msb);
    if (((readValue & mask) != (data & mask)) && (libRunMode != AFE_LIBS_SIMULATION_MODE))
    {
        *readCheckStatus = 1;
        afeLogInfo("addr[0x%04X], lsb[%d], msb[%d], data[0x%02X] not matching with expected value[0x%02X]", addr, lsb, msb, readValue, data);
    }
    else
        *readCheckStatus = 0;
    afeLogSpiLog("READ Check: afeInst: %d, addr: 0x%X, lsb: %d, msb: %d, Read Value: 0x%X, Expected Value:0x%X", AFE79_CURR_ID, addr, lsb, msb, readValue & mask, data & mask);
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief AFE SPI Poll Wrapper
    @details Polls and checks if the value of the field is as expected. Check Pass condition is (readValue&mask)==(data&mask) where mask = (((1 << ((msb) - (lsb) + 1)) - 1) << lsb);
    @param afeInst AFE ID
    @param addr SPI address
    @param expectedData Expected Value.
    @param lsb lsb of the field.
    @param msb msb of the field.
    @return Returns if the function execution passed or failed. It returns fail even when the read data didn't match the expected value.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiPollWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t expectedData, uint8_t lsb, uint8_t msb)
{

    uint32_t count = 0;
    uint8_t mask = 0;
    uint8_t readValue = 0;
    AFE79_ID_VALIDITY();
    uint8_t libRunMode = 0;
    AFE79FNP(getAfeLibsRunMode)
    (&libRunMode);
    AFE79_PARAMS_VALID((msb < 8) && (lsb <= msb));

    mask = MASK_BYTE(lsb, msb);
    afeLogSpiLog("Poll: afeInst: %d, addr: 0x%X, lsb: %d, msb: %d, Expected Value:0x%X", AFE79_CURR_ID, addr, lsb, msb, expectedData);

    for (count = 0; count < CFG_SPI_READ_POLL_MAX_COUNT; count++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiRawRead)(afeInst, addr, &readValue));
        if (((readValue & mask) == (expectedData & mask)) || (libRunMode == AFE_LIBS_SIMULATION_MODE))
            break;
        if (libRunMode != AFE_LIBS_SIMULATION_MODE)
        {
            AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 2));
        }
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 2));
    }

    if ((count >= CFG_SPI_READ_POLL_MAX_COUNT) && (libRunMode != AFE_LIBS_SIMULATION_MODE))
    {
        afeLogErr("POLL Fail: Address: 0x%X, lsb: %d, msb: %d, Expected Value: 0x%X, Read Value: 0x%X", addr, lsb, msb, expectedData, ((readValue >> lsb) & mask));
        return TI_AFE_RET_EXEC_FAIL;
    }
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief AFE SPI Poll Wrapper
    @details Polls and checks if the value of the field is as expected. Check Pass condition is (readValue&mask)==(data&mask) where mask = (((1 << ((msb) - (lsb) + 1)) - 1) << lsb); Function definition reordered from afeSpiPollWrapper to suit the log format.
    @param afeInst AFE ID
    @param addr SPI address
    @param expectedData Expected Value.
    @param lsb lsb of the field.
    @param msb msb of the field.
    @param pollStatus Pointer return. This will return 0 if the poll succeeds and 1 if poll fails,
    @return Returns if the function execution passed or failed. It returns fail even when the read data didn't match the expected value.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(afeSpiPollLogWrapper)(AFE79_INST_TYPE afeInst, uint16_t addr, uint8_t lsb, uint8_t msb, uint8_t expectedData, uint8_t *pollStatus)
{
    *pollStatus = AFE79FNP(afeSpiPollWrapper)(afeInst, addr, expectedData, lsb, msb);
    return TI_AFE_RET_EXEC_PASS;
}
#endif

typedef enum PLL_SPI_REG_TYPE
{
    PLL_SPI_REG_OFF = 0,
    PLL_SPI_REG_A,
    PLL_SPI_REG_B,

    PLL_SPI_REG_TYPE_SIZE
} PllSpiRegType_e;

/**
    @brief Requesting PLL Spi Access
    @details For access PLL registers, the access to the PLL page should be requested and we should proceed only after it is granted. After the access is complete, the SPI access should be. This function does these operations. This access is independent for SPIA and SPIB.
    @param afeInst AFE ID
    @param regType 0-Relinquish SPI access<br>
                1- Request Access for SPIA
                2- Request Access for SPIB
    @return Returns if the function execution passed or failed. It returns fail even when the request has not been granted.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(requestPllSpiAccess)(AFE79_INST_TYPE afeInst, uint8_t regType)
{
    uint32_t count = 0;
    uint8_t readVal = 0;
    uint8_t libRunMode = 0;
    AFE79FNP(getAfeLibsRunMode)
    (&libRunMode);
    AFE79_PARAMS_VALID(regType < PLL_SPI_REG_TYPE_SIZE);

    /*  "Requesting/releasing SPI Access to PLL Pages"  */
    if (regType == PLL_SPI_REG_A)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x40, 0, 7)); /*digtop*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x170, 0x1, 0, 0)); /*pll_reg_spi_req_a*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x540, 0x0, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0, 7));

        for (count = 0; count < AFE_REQ_SPI_ACCESS_MAX_COUNT; count++)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x40, 0, 7)); /*digtop*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x171, 0, 0, &readVal));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0, 7));
            if (readVal == 1)
                break;
            AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 1));
        }
        if (libRunMode != AFE_LIBS_SIMULATION_MODE){
            if (count >= AFE_REQ_SPI_ACCESS_MAX_COUNT)
            {
                afeLogErr("%s", "SPIA didn't get control of PLL pages.");
                return TI_AFE_RET_EXEC_FAIL;
            }
            else{
                afeLogInfo("%s", "SPIA has got control of PLL pages.");
            }

        }
    }
    else if (regType == PLL_SPI_REG_B)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x40, 0, 7)); /*digtop*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x170, 0x0, 0, 0)); /*pll_reg_spi_req_a*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x540, 0x1, 0, 0));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0, 7));

        for (count = 0; count > AFE_REQ_SPI_ACCESS_MAX_COUNT; count++)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x40, 0, 7)); /*digtop*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x541, 0, 0, &readVal));
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0, 7));
            if (readVal == 0)
                break;
            AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 20));
        }
        if (count >= AFE_REQ_SPI_ACCESS_MAX_COUNT)
        {
            afeLogErr("%s", "SPIB didn't get control of PLL pages.");
            return TI_AFE_RET_EXEC_FAIL;
        }
        afeLogInfo("%s", "SPIB has got control of PLL pages.");
    }
    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x40, 0, 7)); /*digtop*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x170, 0x0, 0, 0)); /*pll_reg_spi_req_a*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x540, 0x0, 0, 0));
        AFE79_FUNC_EXEC(AFE79FNP(afeWaitMs)(afeInst, 20));
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x15, 0x0, 0, 7));
        afeLogInfo("%s", "PLL Pages SPI control relinquished.");
    }

    return TI_AFE_RET_EXEC_PASS;
}

#ifndef DOXYGEN_SHOULD_SKIP_THIS
static const uint32_t ausAddr[] =
    {
        0,
        0x7fe0,
        0xffc0,
        0x17fa0,
        0x1ff80,
        0x27f60,
        0x2ff40,
        0x37f20,
        0x3ff00};

/**
    @brief Reads the MCU Memory
    @details This reads the MCU memory and returns the value as a pointer.
    @param afeInst AFE ID
    @param addr Memory Address.
    @param readVal Value read returned as a pointer.
    @param noBytes Number of bytes to be read. Supported values: 0<noBytes<=8
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(readTopMem)(AFE79_INST_TYPE afeInst, uint32_t addr, uint64_t *readVal, uint32_t noBytes)
{
    uint16_t addr_high = 0;
    uint16_t usAddr = 0;
    uint32_t count = 0;

    uint8_t readValue8 = 0;
    AFE79_PARAMS_VALID(addr < ausAddr[ARRAY_SIZE(ausAddr) - 1]);
    AFE79_PARAMS_VALID(readVal != NULL)
    AFE79_PARAMS_VALID(noBytes != 0 && noBytes <= 8);
    for (count = 1; count < ARRAY_SIZE(ausAddr); count++)
    {
        if (addr < ausAddr[count])
        {
            addr_high = count - 1;
            usAddr = (uint16_t)(addr - ausAddr[count - 1]) + 0x20;
            break;
        }
    }
    *readVal = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x20, 0, 7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x144, (addr_high << 2), 2, 4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x08, 0, 7));
    for (count = 0; count < noBytes; count++)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, (usAddr + count), 0, 7, &readValue8));
        *readVal = *readVal | (readValue8 << (8 * count));
    }
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x18, 0x00, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Close All Pages
    @details This function closes all the pages. Need to be called in case of a SPI/function to ensure no open page is present.
    @param afeInst AFE ID
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(closeAllPages)(AFE79_INST_TYPE afeInst)
{

    uint8_t addr = 0;
    for (addr = AFE_PAGE_START_ADDR; addr <= AFE_PAGE_END_ADDR; addr += 1)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, addr, 0x00, 0, 7));
    }
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Converts a value into byte wise array.
    @details Converts a value into byte wise array.
    @param val Value to be converted
    @param numBytes Number of Bytes to convert it to.
    @param splitByteList Pointer return of the resultant array.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(splitToByte)(uint64_t val, uint8_t numBytes, uint8_t *splitByteList)
{
    uint8_t iter = 0;
    /*  Split the given value into Byte format for forming Macro byteList.  */
    for (iter = 0; iter < numBytes; iter++)
    {
        splitByteList[iter] = (((val) & (0xFF << 8 * iter)) >> (8 * iter));
    }
    return TI_AFE_RET_EXEC_PASS;
}