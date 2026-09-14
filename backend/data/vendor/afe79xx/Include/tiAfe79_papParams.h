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
* THIS SOFTWARE IS PROVIDED BY TI AND TI’S LICENSORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING,
* BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
* IN NO EVENT SHALL TI AND TI’S LICENSORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
* CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
* OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
* OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
* POSSIBILITY OF SUCH DAMAGE.
*/
#ifndef DOXYGEN_SHOULD_SKIP_THIS

#ifndef tiAfe79_HAFE_PAP_PARAMS_H
#define tiAfe79_HAFE_PAP_PARAMS_H
/** @file tiAfe79_papParams.h
 * 	@brief This file has AFE PAP Related System Parameters definition.<br>
 */

#include <stdint.h>

/** @struct afe79PapSystemParamsStruct
 *  @brief This structure contains the AGC related System Parameters.<br>
 *
 */

typedef struct afe79PapSystemParamsStructDef
{
    /// Enable PAP
    uint8_t enable;

    /* ############################################################*/
    /* ############### Moving Average Detector Config ###############*/
    /* ############################################################*/
    /// 0: Disable Moving Average based PAP detector.<br>1:Enable Moving Average based PAP detector.
    uint8_t maEnable;
    /// Number of samples in a window. Supported values: 32, 64, 128 Samples.
    uint16_t maNumSample;
    /// Number of windows. Supported Range: 0 to 2**12-1
    uint16_t maWindowCntr;
    /// Window Counter Threshold. When the number of windows in a set of maWindowCntr windows have power above the power threshold. This should be lower than or equal to maWindowCntr. Supported Range: 0:2**12-1.
    uint16_t maWindowCntrTh;
    /// Percentage threshold with respect to full scale for Band 0 detector. Supported Range: 0-100.
    uint16_t maThreshB0;
    /// Percentage threshold with respect to full scale for Band 0 detector. Supported Range: 0-100. Valid only in dual band use case. In single band usecase, make this equal to maThreshB0.
    uint16_t maThreshB1;
    /// Percentage threshold with respect to full scale for combiner detector. Supported Range: 0-100.
    uint16_t maThreshComb;

    /* ############################################################*/
    /* ############### High Pass Filter Detector Config ###############*/
    /* ############################################################*/

    /// 0: Disable High Pass Filter based PAP detector.<br>1:Enable High Pass Filter based PAP detector.
    uint8_t hpfEnable;
    /// Number of samples in a window. Supported values: 4, 8, 16 Samples.
    uint16_t hpfNumSample;
    /// Number of windows. Supported Range: 0 to 2**12-1
    uint16_t hpfWindowCntr;
    /// Window Counter Threshold. When the number of windows in a set of hpfWindowCntr windows have filter trigger. This should be lower than hpfWindowCntr. Supported Range: 0:2**12-1.
    uint16_t hpfWindowCntrTh;
    /// Percentage threshold with respect to full scale for Band 0 detector. Supported Range: 0-100.
    uint16_t hpfThreshB0;
    /// Percentage threshold with respect to full scale for Band 0 detector. Supported Range: 0-100. Valid only in dual band use case. In single band usecase, make this equal to hpfThreshB0.
    uint16_t hpfThreshB1;
    /// Percentage threshold with respect to full scale for combiner detector. Supported Range: 0-100.
    uint16_t hpfThreshComb;

    /* ############################################################*/
    /* ############### PAP state machine Config ###############*/
    /* ############################################################*/

    /// Ramp Multiplication Mode 0 -  (1+Cosine)/2 profile; 1 -  Linear profile
    uint8_t multMode;
    /**
      * Starting Amplitude/Phase for Ramp down	<br>
         0 to 128 In <1.7u> format. <br>
         Value of 128 corresponds to unit amplitude for the linear profile<br>
         Value of 128 corresponds to pi radians for the cosine profile
     */
    uint8_t rampDownStartVal;
    /// Time delay in Wait State: Number of cycles the FSM should remain in the WAIT state. Indicates time in ns.
    uint16_t waitCounter;

    /// Amplitude Step in Ramp up: Difference between successive amplitude values during Ramp Up.<br> Can be from 1 to 127 in <0.7u> format.
    uint8_t gainStepSize;
    /// Amplitude Step in Ramp down: Difference between successive amplitude values during Ramp Down.<br> Can be from 1 to 127 in <0.7u> format.
    uint8_t attnStepSize;
    /**
      *  Time interval between amplitude step in Ramp up: Time duration to remain in a particular amplitude during ramp-up before going to the next amplitude.
         Indicates time in ns. Can take values from 1 clock cycle of Fdac/16 to 128 clock cycles of Fdac/16.
     */
    uint8_t amplUpdateCycles;
    /// Delay from PAP trigger going down to start of ramp up	Indicates time in ns.
    uint16_t triggerClearToRampUp;
    /// Delay from PAP trigger to ramp down start. Indicates time in ns.
    uint16_t triggerToRampDown;
    /**
      * Detect PAP trigger in wait state<br>
      * If set '1' and an alarm comes during FSM 'WAIT' state, FSM goes to 'ATTN' state.<br>
         If set to '0', alarm during FSM 'WAIT' state is ignored."
     */
    uint8_t detectInWaitState;
    /**
      * Disable auto transition from Wait to Gain<br>
      * 0: Enable auto-transition from WAIT to GAIN state.<br>
             1: Disable auto-transition from WAIT to GAIN state.
     */
    uint8_t rampStickyMode;

    /* ############################################################*/
    /* ############### PAP alarms Config ###############*/
    /* ############################################################*/

    /**
     * Bit wise alarms masking for other channels (bit-wise). Making the corresponding bit 0 will make the PAP state machine trigger on corresponding alarm. For each channel the bit-wise description is different.
     * Channel: Bit No 3-2-1-0
     * TxA - D-C-B-A,
     * TxB - D-C-A-B,
     * TxC - B-A-D-C,
     * TxD - B-A-C-D
     * For triggering each channel by its own PAP trigger, this value should be 0b1110 for all channels. For triggering each channel by PAP trigger of all channels, this value should be 0x0 for all channels.
     */
    uint8_t alarmChannelMask;
    /**
     * Bit wise alarms masking. Making the corresponding bit 0 will make the PAP state machine trigger on corresponding alarm.<br>
     * Bit 0 - pll_alarm<br>
     * Bit 1 - serdes_alarm<br>
     * Bit 2 - fifo_alarm<br>
     * Bit 3 - ovr_saturation_alarm<br>
     * Bit 4 - dual-band det alarm<br>
     * Bit 5 - combined band det alarm<br>
     * Bit 6 - spi trigger<br>
     */
    uint8_t alarmMask;

    /// Determines if the PAP Pin is sticky or non-sticky.  0:sticky, 1:dynamic
    uint8_t alarmPinDynamicMode;
    /// Pulse width of PAP alarm going to GPIO. Indicates time in ns.
    uint32_t alarmPulseGPIO;

} afe79PapSystemParamsStruct;

#endif

#endif