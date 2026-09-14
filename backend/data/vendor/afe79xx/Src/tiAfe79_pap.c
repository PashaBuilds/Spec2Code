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

/** @file tiAfe79_pap.c
 * 	@brief	This file has PAP related functions.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation and improved the parameter validity checks.<br>
 * 		2. Changed the C macros for all the spi wrapper and executeMacro function calls to AFE79_FUNC_EXEC from AFE79_SPI_EXEC.<br>
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

#include "tiAfe79_pap.h"

#ifndef DOXYGEN_SHOULD_SKIP_THIS
/**
    @brief Configure the Moving Average PAP Detector
    @details Configure the Moving Average PAP Detector. Note that all the System Parameters should be set as per the configuration before calling this.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD

    @param maEnable	 0: Disable Moving Average based PAP detector.<br>
                    1:Enable Moving Average based PAP detector.
    @param maNumSample Number of samples in a window. Supported values: 0-16; 1-32; 2-64; 3-128 Samples
    @param maWindowCntr Number of windows. Supported Range: 0 to 2**12-1
    @param maWindowCntrTh Window Counter Threshold. When the number of windows in a set of maWindowCntr windows have power above the power threshold. This should be lower than or equal to maWindowCntr. Supported Range: 0:2**12-1.
    @param maThreshB0 (128*val) is the power threshold for band 0 detector. Supported Range: 0-511
    @param maThreshB1 (128*val) is the power threshold for band 1 detector. Supported Range: 0-511. Valid only in dual band use case. In single band usecase, make this equal to maThreshB0.
    @param maThreshComb (128*val) is the power threshold for combined detector. Supported Range: 0-511. Valid only in dual band use case. In single band usecase, make this equal to maThreshB0.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(configurePapMaDet)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t maEnable, uint16_t maNumSample, uint16_t maWindowCntr,
                                                    uint16_t maWindowCntrTh, uint16_t maThreshB0, uint16_t maThreshB1, uint16_t maThreshComb)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(maThreshB0 <= 511);
    AFE79_PARAMS_VALID(maThreshB1 <= 511);
    AFE79_PARAMS_VALID(maThreshComb <= 511);
    AFE79_PARAMS_VALID(maWindowCntr <= 0xfff);
    AFE79_PARAMS_VALID(maWindowCntrTh <= maWindowCntr);
    AFE79_PARAMS_VALID((maNumSample < 4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chno + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
    if (maEnable == 1)
    { /* Moving Average Detector Porgramming*/
        if (AFE79_CURR_SYSPARAM.numBandsTx[chno] == 0)
        {
            maThreshB1 = maThreshB0;
        }

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x563, (maWindowCntr >> 8) & 0xff, 0x0, 0x3)); /*tx_ip_pap_moving_average_window_counter*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x562, maWindowCntr & 0xff, 0x0, 0x7));        /*tx_ip_pap_moving_average_window_counter*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x565, (maWindowCntrTh >> 8) & 0xff, 0x0, 0x3)); /*tx_ip_pap_moving_average_error_threshold*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x564, (maWindowCntrTh)&0xff, 0x0, 0x7));        /*tx_ip_pap_moving_average_error_threshold*/

        if ((AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) >= 2 && (AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) < 4)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x561, (maNumSample - 1) & 0xff, 0x0, 0x1)); /*tx_ip_pap_moving_average_samples*/
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x561, maNumSample & 0xff, 0x0, 0x1)); /*tx_ip_pap_moving_average_samples*/
        }

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5a5, (maThreshB0 >> 8) & 0xff, 0x0, 0x0)); /*tx_ip_pap_moving_average_accu_th_band0*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5a4, maThreshB0 & 0xff, 0x0, 0x7));        /*tx_ip_pap_moving_average_accu_th_band0*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5b5, (maThreshB1 >> 8) & 0xff, 0x0, 0x0)); /*tx_ip_pap_moving_average_accu_th_band1*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5b4, maThreshB1 & 0xff, 0x0, 0x7));        /*tx_ip_pap_moving_average_accu_th_band1*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x513, (maWindowCntr >> 8) & 0xff, 0x0, 0x3)); /*pap_moving_average_window_counter*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x512, maWindowCntr & 0xff, 0x0, 0x7));        /*pap_moving_average_window_counter*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x515, (maWindowCntrTh >> 8) & 0xff, 0x0, 0x3)); /*pap_moving_average_error_th			*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x514, (maWindowCntrTh)&0xff, 0x0, 0x7));        /*pap_moving_average_error_th			*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x511, (maNumSample & 0xff), 0x0, 0x1)); /*pap_moving_average_samples			*/

        if ((AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) >= 2)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x517, (maThreshComb >> 8) & 0xff, 0x0, 0x0)); /*pap_moving_average_accu_th*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x516, maThreshComb & 0xff, 0x0, 0x7));        /*pap_moving_average_accu_th*/
        }

        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x517, (maThreshB0 >> 8) & 0xff, 0x0, 0x0)); /*pap_moving_average_accu_th*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x516, maThreshB0 & 0xff, 0x0, 0x7));        /*pap_moving_average_accu_th*/
        }
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x560, (maEnable)&0xff, 0x0, 0x0)); /*tx_ip_pap_mode_moving_average_en*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x510, (maEnable)&0xff, 0x0, 0x0)); /*pap_mode_moving_average_en*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Configure the High Pass Filter PAP Detector
    @details Configure the High Pass Filter PAP Detector. Note that all the System Parameters should be set as per the configuration before calling this.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD

    @param hpfEnable	 0: Disable High Pass Filter based PAP detector.<br>
                    1:Enable High Pass Filter based PAP detector.
    @param hpfNumSample Number of samples in a window. Supported values: 1-32; 2-64; 3-128 Samples
    @param hpfWindowCntr Number of windows. Supported Range: 0 to 2**12-1
    @param hpfWindowCntrTh Window Counter Threshold. When the number of windows in a set of maWindowCntr windows have filter trigger. This should be lower than maWindowCntr. Supported Range: 0:2**12-1.
    @param hpfThreshB0 (128*val) is the filter threshold for band 0 detector. Supported Range: 0-511
    @param hpfThreshB1 (128*val) is the filter threshold for band 1 detector. Supported Range: 0-511. Valid only in dual band use case. In single band usecase, make this equal to maThreshB0.
    @param hpfThreshComb (128*val) is the filter threshold for combined detector. Supported Range: 0-511. Valid only in dual band use case. In single band usecase, make this equal to maThreshB0.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(configurePapHpfDet)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t hpfEnable, uint16_t hpfNumSample, uint16_t hpfWindowCntr,
                                                     uint16_t hpfWindowCntrTh, uint16_t hpfThreshB0, uint16_t hpfThreshB1, uint16_t hpfThreshComb)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(hpfThreshB0 <= 511);
    AFE79_PARAMS_VALID(hpfThreshB1 <= 511);
    AFE79_PARAMS_VALID(hpfThreshComb <= 511);
    AFE79_PARAMS_VALID(hpfWindowCntr <= 0xfff);
    AFE79_PARAMS_VALID(hpfWindowCntrTh <= hpfWindowCntr);
    AFE79_PARAMS_VALID((hpfNumSample > 0) && (hpfNumSample < 4));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chno + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
    if (hpfEnable == 1)
    {                                                                                                        /* High Pass Filter based detector*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x57d, (hpfWindowCntr >> 8) & 0xff, 0x0, 0x3)); /*tx_ip_pap_diff_window_counter		*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x57c, (hpfWindowCntr)&0xff, 0x0, 0x7));        /*tx_ip_pap_diff_window_counter		*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x57f, (hpfWindowCntrTh >> 8) & 0xff, 0x0, 0x3)); /*tx_ip_pap_diff_error_th			*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x57e, (hpfWindowCntrTh)&0xff, 0x0, 0x7));        /*tx_ip_pap_diff_error_th			*/

        if (((AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) >= 2) && (AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) < 4)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x56a, ((hpfNumSample - 1) & 0xff), 0x0, 0x1)); /*tx_ip_pap_diff_samples*/
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x56a, hpfNumSample & 0xff, 0x0, 0x1)); /*tx_ip_pap_diff_samples*/
        }

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5a7, (hpfThreshB0 >> 8) & 0xff, 0x0, 0x0)); /*tx_ip_pap_diff_accu_th_band0*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5a6, hpfThreshB0 & 0xff, 0x0, 0x7));        /*tx_ip_pap_diff_accu_th_band0*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5b7, (hpfThreshB1 >> 8) & 0xff, 0x0, 0x0)); /*tx_ip_pap_diff_accu_th_band1*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x5b6, hpfThreshB1 & 0xff, 0x0, 0x7));        /*tx_ip_pap_diff_accu_th_band1*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x575, (hpfWindowCntr >> 8) & 0xff, 0x0, 0x3)); /*pap_diff_window_counter		*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x574, (hpfWindowCntr)&0xff, 0x0, 0x7));        /*pap_diff_window_counter		*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x577, (hpfWindowCntrTh >> 8) & 0xff, 0x0, 0x3)); /*pap_diff_error_th*/
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x576, (hpfWindowCntrTh)&0xff, 0x0, 0x7));        /*pap_diff_error_th*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x51a, hpfNumSample & 0xff, 0x0, 0x1)); /*pap_diff_samples*/

        if ((AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) >= 2)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x579, (hpfThreshComb >> 8) & 0xff, 0x0, 0x0)); /*pap_diff_accu_th*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x578, hpfThreshComb & 0xff, 0x0, 0x7));        /*pap_diff_accu_th*/
        }
        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x579, (hpfThreshB0 >> 8) & 0xff, 0x0, 0x0)); /*pap_diff_accu_th*/
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x578, hpfThreshB0 & 0xff, 0x0, 0x7));        /*pap_diff_accu_th*/
        }
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x568, (hpfEnable)&0xff, 0x0, 0x0)); /*tx_ip_pap_mode_sr_en*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x518, (hpfEnable)&0xff, 0x0, 0x0)); /*pap_mode_sr_en*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Configure the PAP Block
    @details Configure the PAP Block. Note that all the System Parameters should be set as per the configuration before calling this.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param enable	1 to enable PAP. 0 To disable PAP
    @param multMode	Mode of Ramp up/down. 0:Cosine 1:Linear
    @param rampDownStartVal This is the starting value for the ramp down. Supported range: 0 to 127. <br>
                        For cosine mode, the start phase in radians is (128-rampDownStartVal)* pi /128.<br>
                        For linear mode, (rampDownStartVal/128) is the start value.
    @param attnStepSize This is the ramp step size while ramping down (actualSampleStep=attnStepSize*(last good sample)/1024). Supported Range is 0 to 127.
    @param gainStepSize This is the ramp step size while gaining up (actualSampleStep=GainStepSize*(last good sample)/1024). Supported Range is 0 to 127.
    @param detectInWaitState This determines if the PAP trigger should be acknowledged in the wait state.<br>
                            0:Do not detect in wait state<br>
                            1:detect in wait state
    @param triggerToRampDown Time from trigger occurance to ramp down time (ns). Supported Range: 0 to floor(65520000000.0/Fdac) where Fdac is in KHz.
    @param waitCounter	 Wait time counter (ns). Supported Range: 0 to floor(1048560000000.0/Fdac) where Fdac is in KHz.
    @param triggerClearToRampUp Time from end of wait state to Ramp up (ns).  Supported Range: 0 to floor(65520000000.0/Fdac) where Fdac is in KHz.
    @param amplUpdateCycles	 Time for each step during ramp up or down. (ns).  Supported Range: 0 to floor(2032000000.0/Fdac) where Fdac is in KHz.
    @param alarmPulseGPIO Pulse width of PAP alarm going to GPIO (ns). Supported Range: 0 to floor(1048560000000.0/Fdac) where Fdac is in KHz.
    @param alarmMask Bit wise alarms. Bit value 0 will make corresponding alarm to trigger PAP state machine.<br>
                        BitNo: Alarm<br>
                        0	:	 pll_alarm,<br>
                        1	:	 serdes_alarm,<br>
                        2	:	 fifo_alarm,<br>
                        3	:	 ovr_saturation_alarm,<br>
                        4	:	 dual band det alarm,<br>
                        5	:	 combined band det alarm,<br>
                        6	:	 spi trigger
    @param alarmChannelMask Mask other channels (bit-wise). <br>
                        For each channel the bit-wise description is different.<br>
                        Ch	:	BitNo	3-2-1-0<br>
                        TxA	:	D-C-B-A,<br>
                        TxB	:	D-C-A-B,<br>
                        TxC	:	B-A-D-C,<br>
                        TxD	:	B-A-C-D
    @param alarmPinDynamicMode Determines if the PAP Pin is sticky or non-sticky. 1:dynamic, 0:sticky
    @param rampStickyMode Determines if the Ramp up mode is sticky or non-sticky.<br>
                        0:Automatically come to ramp up mode after wait state.<br>
                        1: Wait for pap clear bit to be written
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(configurePap)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t enable, uint8_t multMode, uint8_t rampDownStartVal,
                                               uint8_t attnStepSize, uint8_t gainStepSize, uint8_t detectInWaitState, float triggerToRampDown,
                                               float waitCounter, float triggerClearToRampUp, float amplUpdateCycles, float alarmPulseGPIO,
                                               uint8_t alarmMask, uint8_t alarmChannelMask, uint8_t alarmPinDynamicMode, uint8_t rampStickyMode)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(rampDownStartVal <= 127);
    AFE79_PARAMS_VALID(attnStepSize <= 127);
    AFE79_PARAMS_VALID(gainStepSize <= 127);
    AFE79_PARAMS_VALID(triggerToRampDown <= (65520000000.0 / AFE79_CURR_SYSPARAM.Fdac));
    AFE79_PARAMS_VALID(triggerClearToRampUp <= (65520000000.0 / AFE79_CURR_SYSPARAM.Fdac));
    AFE79_PARAMS_VALID(waitCounter <= (1048560000000.0 / AFE79_CURR_SYSPARAM.Fdac));
    AFE79_PARAMS_VALID(amplUpdateCycles <= (2032000000.0 / AFE79_CURR_SYSPARAM.Fdac));
    AFE79_PARAMS_VALID(alarmPulseGPIO <= (1048560000000.0 / AFE79_CURR_SYSPARAM.Fdac));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chno + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
    if ((AFE79_CURR_SYSPARAM.FadcFb * AFE79_CURR_SYSPARAM.ducFactorTx[chno] / AFE79_CURR_SYSPARAM.Fdac) >= 2)
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x525, 0x1, 0x0, 0x0)); /*mem_pap_db_sb_en;	 Interface PAP enabled*/
        if (AFE79_CURR_SYSPARAM.numBandsTx[chno] == 0)
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x524, 0x0, 0x0, 0x0)); /*mem_pap_3g_band_en	;	 Comb PAP disabled i.e. B0+B1*/

            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x588, 0x1, 0x0, 0x0)); /*tx_ip_pap_en_pap_band1;	 1: for single band, 0: for dual band*/
        }

        else
        {
            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x524, 0x1, 0x0, 0x0)); /*mem_pap_3g_band_en	;	 Comb PAP enabled i.e. B0+B1*/

            AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x588, 0x0, 0x0, 0x0)); /*tx_ip_pap_en_pap_band1;	 1: for single band, 0: for dual band*/
        }
    }

    else
    {
        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x525, 0x0, 0x0, 0x0)); /*mem_pap_db_sb_en;	 Default Interface PAP can't be used*/

        AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x524, 0x1, 0x0, 0x0)); /*mem_pap_3g_band_en		;	 Comb PAP works as interface PAP*/
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x548, (multMode)&0xff, 0x0, 0x0)); /*sel_pap_ampl_mode*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x532, (128 - rampDownStartVal) & 0xff, 0x0, 0x7)); /*pap_attn_start_cos*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x534, (rampDownStartVal)&0xff, 0x0, 0x7)); /*pap_attn_start_lin*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x536, (attnStepSize)&0xff, 0x0, 0x6)); /*pap_attn_step_size	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x53c, (rampDownStartVal)&0xff, 0x0, 0x7)); /*pap_gain_start_cos*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x53e, (128 - rampDownStartVal) & 0xff, 0x0, 0x7)); /*pap_gain_start_lin*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x540, (gainStepSize)&0xff, 0x0, 0x6)); /*pap_gain_step_size	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x726, ((detectInWaitState) << 1) & 0xff, 0x1, 0x1));                                                             /*en_fsm_wait2attn*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x539, (((uint16_t)(ceil((triggerToRampDown * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0))) >> 8) & 0xff, 0x0, 0x3)); /*pap_dly1*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x538, ((uint16_t)(ceil((triggerToRampDown * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0))) & 0xff, 0x0, 0x7));        /*pap_dly1*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x545, ((uint16_t)(ceil((waitCounter * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0)) >> 8) & 0xff, 0x0, 0x7)); /*pap_wait_counter*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x544, ((uint16_t)(ceil((waitCounter * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0)) & 0xff), 0x0, 0x7));      /*pap_wait_counter*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x53b, ((uint16_t)(ceil((triggerClearToRampUp * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0)) >> 8) & 0xff, 0x0, 0x3)); /*pap_dly2*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x53a, ((uint16_t)(ceil((triggerClearToRampUp * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0)) & 0xff), 0x0, 0x7));      /*pap_dly2*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x531, ((uint16_t)(ceil((amplUpdateCycles * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0))) & 0xff, 0x0, 0x6)); /*pap_ampl_updt_cycles	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x597, ((uint16_t)(ceil((alarmPulseGPIO * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0)) >> 8) & 0xff, 0x0, 0x7)); /*pap_dyn_out_pulse_extsn*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x596, ((uint16_t)(ceil((alarmPulseGPIO * AFE79_CURR_SYSPARAM.Fdac) / 16000000.0))) & 0xff, 0x0, 0x7));      /*pap_dyn_out_pulse_extsn*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x542, 0xa, 0x0, 0x7)); /*pap_out_pulse_extsn*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54f, (((alarmMask & 1) + (0b11110) + ((alarmMask & 0x3e) << 4)) >> 8) & 0xff, 0x0, 0x2)); /*txa_pap_alarm_mask*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54e, ((alarmMask & 1) + (0b11110) + ((alarmMask & 0x3e) << 4)) & 0xff, 0x0, 0x7));        /*txa_pap_alarm_mask*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x52d, (alarmChannelMask)&0xff, 0x0, 0x6)); /*pap_alarm_mask*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x594, (alarmPinDynamicMode)&0xff, 0x0, 0x0)); /*tx_pap_dyn_gpio_alarm;	 1=dynamic, 0=sticky*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x726, (rampStickyMode)&0xff, 0x0, 0x0)); /*tx_pap_fsm_enable_wait_spi_clear*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x718, 0x1, 0x0, 0x0)); /*tx_ip_pap_tdd_fsm_alarm_rst*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x710, 0x2, 0x1, 0x1)); /*pap_en_sysref_mask	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x720, 0x1, 0x0, 0x0)); /*mem_en_sysref_mask*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x710, 0x1, 0x0, 0x0)); /*pap_en_pap_nco_blank*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x502, 0x1, 0x0, 0x1)); /*pap_mult_data_mode*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x528, (enable)&0xff, 0x0, 0x0)); /*pap_blk_en*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Clear the ramp sticky state
    @details In case where rampStickyMode is set, this function should be called to clear the PAP alarm and move to ramp up state.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(rampStickyClear)(AFE79_INST_TYPE afeInst, uint8_t chno)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chno + 4)) & 0xff, 0x0, 0x7)); /*txdig*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x708, 0x0, 0x0, 0x7));                     /*pap_blk_rst	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x708, 0x1, 0x0, 0x7)); /*pap_blk_rst	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x708, 0x0, 0x0, 0x7)); /*pap_blk_rst	*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Map the DAC JESD lane errors to the PAP block.
    @details This function chooses which lanes' errors should go to a particular TX PAP.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param laneMask This is 8-bit field with bit wise enable for lane errors.<br>
                    Bit0 is for lane0, Bit1 for lane1, Bit2 for lane 2 and so on.<br>
                    The errors from lanes with corresponding bits set to 1 will reach the PAP.<br>
                    The lane numbers are pre-lane mux (towards the AFE).<br>
                    For example, for TXA PAP to get errors from lanes 0 and 1, laneMask should be 0b00000011.<br>
                    Registers written are (tx<a/b/c/d>_lane_alarms_to_pap_en) in DAC JESD.s
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(configLaneErrorsForTxPap)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t laneMask)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x4, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12c + (chno >> 1), laneMask & 0xf, 0x0 + ((chno & 1) << 2), 0x3 + ((chno & 1) * 4)));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x8, 0x0, 0x7));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x12c + (chno >> 1), (laneMask >> 4) & 0xf, 0x0 + ((chno & 1) << 2), 0x3 + ((chno & 1) * 4)));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x16, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
#endif

/**
    @brief Reads the PAP alarm Status
    @details Reads the PAP alarm Status and returns it as a pointer. This is sticky status and clearPapAlarms needs to be called to clear the status.
    @param afeInst AFE ID
    @param chno Select the TX Channel<br>
            0 for TXA<br>
            1 for TXB<br>
            2 for TXC<br>
            3 for TXD
    @param alarmTriggered Pointer return of the status. If this value is 1, then there was a PAP trigger.
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(papAlarmStatus)(AFE79_INST_TYPE afeInst, uint8_t chno, uint8_t *alarmTriggered)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno < AFE79_NUM_TX_CHANNELS);
    AFE79_PARAMS_VALID(alarmTriggered != NULL);
    uint16_t errorRead = 0;
    uint8_t errorRead_lsb, errorRead_msb;
    *alarmTriggered = 0;
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (1 << (chno + 4)) & 0xff, 0x0, 0x7)); /*txdig*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x55c, 0x0, 0x7, &errorRead_lsb));
    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x55d, 0x0, 0x2, &errorRead_msb));
    errorRead = (errorRead_msb << 8) + errorRead_lsb; /*txa_pap_alarm_sts;*/
    if ((errorRead & 1) != 0)
    {
        afeLogErr("%s", "PLL Alarm Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead & 0x20) != 0)
    {
        afeLogErr("%s", "JESD-SerDes Alarm Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead & 0x40) != 0)
    {
        afeLogErr("%s", "Async FIFO Overflow Alarm Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead & 0x80) != 0)
    {
        afeLogErr("%s", "Saturation Overflow Alarm Triggered");
        *alarmTriggered = 1;
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x558, 0x0, 0x7, &errorRead_lsb)); /*pap_alarm_sts;	# refer dml for description*/
    if ((errorRead_lsb & 1) != 0)
    {
        afeLogErr("%s", "TXA PAP Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead_lsb & 0x2) != 0)
    {
        afeLogErr("%s", "TXB PAP Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead_lsb & 0x4) != 0)
    {
        afeLogErr("%s", "TXC PAP Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead_lsb & 0x8) != 0)
    {
        afeLogErr("%s", "TXD PAP Triggered");
        *alarmTriggered = 1;
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiReadWrapper)(afeInst, 0x584, 0x0, 0x7, &errorRead_lsb)); /*pap_alarm_sts;	# refer dml for description*/
    if ((errorRead_lsb & 1) != 0)
    {
        afeLogErr("%s", "Moving Average Mode Detector Triggered");
        *alarmTriggered = 1;
    }
    if ((errorRead_lsb & 0x2) != 0)
    {
        afeLogErr("%s", "HPF Mode Detector Triggered");
        *alarmTriggered = 1;
    }

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}

/**
    @brief Clears the PAP alarm Status
    @details Clears the PAP alarm sticky status which also goes to GPIO.
    @param afeInst AFE ID
    @param chno Value 1 = Clear, Value 0 = No Clear<br>
        bit [0] :TxA Alarm<br>
        bit [1]: TxB Alarm<br>
        bit [2]: TxC Alarm<br>
        bit [3]: TxD Alarm<br>
    @return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(clearPapAlarms)(AFE79_INST_TYPE afeInst, uint8_t chno)
{

    AFE79_ID_VALIDITY();
    AFE79_PARAMS_VALID(chno <= AFE79_NUM_TX_CHANNELS_BITWISE);
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, (chno << 4) & 0xff, 0x0, 0x7)); /*txdig*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x52c, 0x1f, 0x0, 0x4));              /*pap_alarm_clr*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x52c, 0x0, 0x0, 0x4)); /*pap_alarm_clr						*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54d, 0x7, 0x0, 0x2));  /*txa_pap_alarm_clr*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54c, 0xff, 0x0, 0x7)); /*txa_pap_alarm_clr*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54d, 0x0, 0x0, 0x2)); /*txa_pap_alarm_clr					*/
    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x54c, 0x0, 0x0, 0x7)); /*txa_pap_alarm_clr					*/

    AFE79_SPI_EXEC(AFE79FNP(afeSpiWriteWrapper)(afeInst, 0x19, 0x0, 0x0, 0x7));
    return TI_AFE_RET_EXEC_PASS;
}
