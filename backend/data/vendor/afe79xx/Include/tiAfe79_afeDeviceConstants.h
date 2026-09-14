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

#ifndef tiAfe79_AFE_DEVICE_CONSTANTS_H
#define tiAfe79_AFE_DEVICE_CONSTANTS_H

/* JESD-SERDES Related */
#define AFE79_NUM_RX_CHANNELS 4
#define AFE79_NUM_RX_CHANNELS_BITWISE 0xf
#define AFE79_NUM_BANDS_PER_RX 2

#define AFE79_NUM_TX_CHANNELS 4
#define AFE79_NUM_TX_CHANNELS_BITWISE 0xf
#define AFE79_NUM_BANDS_PER_TX 2

#define AFE79_NUM_FB_CHANNELS 2
#define AFE79_NUM_FB_CHANNELS_BITWISE 0x3
#define AFE79_NUM_BANDS_PER_FB 1

#define AFE79_NUM_JESD_INSTANCES 2
#define AFE79_NUM_DAC_JESD_LINKS 4
#define AFE79_NUM_CH_PER_JESD_INSTANCE 2
#define AFE79_NUM_SERDES_LANES 8

#define afe79jesdToSerdesLaneMapping \
    {                                \
        1, 0, 2, 3, 3, 2, 0, 1       \
    }

/*PAGE INFO*/
#define AFE_PAGE_START_ADDR 0x10
#define AFE_PAGE_END_ADDR 0x19

#define AFE79_PAGE_ADDR_DAC_JESD_RX 0x16
#define AFE79_PAGE_SELMASK_DAC_JESD_RX(pageSel) ((pageSel) << 2)

#define AFE79_LANE_NO_TO_PAGE_SEL(laneNo) (1 << (((laneNo) >> 2) & 1))

#define AFE79_PAGE_ADDR_SERDES_JESD 0x16
#define AFE79_PAGE_SELMASK_SERDES_JESD(pageSel) ((pageSel) << 5)

/*  MACRO ERROR STATUS TYPES   */
#define AFE_MACRO_NO_ERROR 0
#define AFE_MACRO_ERROR_IN_OPCODE 1
#define AFE_MACRO_ERROR_OPCODE_NOT_ALLOWED 2
#define AFE_MACRO_ERROR_IN_OPERAND 4
#define AFE_MACRO_ERROR_IN_EXECUTION 8

/*  MACRO STATUS ADDRESS INFO   */
#define AFE_MACRO_STATUS_REG_ADDR 0xF0
#define AFE_MACRO_OPCODE_REG_ADDR 0x193
#define AFE_MACRO_EXTENDED_ERROR_CODE_REG_ADDR 0xF2
#define AFE_MACRO_RESULT_START_REG_ADDR 0xF8
#define AFE_MACRO_OPERAND_START_REG_ADDR 0xA0
#define AFE_MACRO_PAGE_REG_ADDR 0x18
#define AFE_MACRO_PAGE_SEL_VAL 0x20

/*  MACRO OPCODES   */
#define AFE_MACRO_OPCODE_SYSTEM_TUNE 0x90
#define AFE_MACRO_OPCODE_PREPARE_FOR_TUNE 0x35
#define AFE_MACRO_OPCODE_SYSTEM_TUNE_SELECTIVE 0x36
#define AFE_MACRO_OPCODE_UPDATE_SYSTEM_TX_CHANNEL_FREQUENCY_CONFIGURATION 0x37
#define AFE_MACRO_OPCODE_UPDATE_TX_DIG_PARAM 0x50
#define AFE_MACRO_OPCODE_UPDATE_TX_GAIN 0x51
#define AFE_MACRO_OPCODE_UPDATE_SYSTEM_RX_CHANNEL_FREQUENCY_CONFIGURATION 0x38
#define AFE_MACRO_OPCODE_UPDATE_SYSTEM_FB_CHANNEL_FREQUENCY_CONFIGURATION 0x39
#define AFE_MACRO_OPCODE_APPLY_DSA_GAIN_PHASE_COMPENSATION 0x11
#define AFE_MACRO_OPCODE_UPDATE_SYSTEM_TX_CHANNEL_FREQUENCY_CONFIGURATION_ALL_BANDS 0x3E
#define AFE_MACRO_OPCODE_FACTORY_RX_DSA_GAIN_PHASE_CALIBRATION 0x41
#define AFE_MACRO_OPCODE_FACTORY_TX_DSA_GAIN_PHASE_CALIBRATION 0x42
#define AFE_MACRO_OPCODE_CONFIG_SIGGEN_FOR_CAL 0x48
#define AFE_MACRO_OPCODE_AGC_STATE_CONTROL 0x68
#define AFE_MACRO_OPCODE_AGC_DIG_DET_CONFIG 0x58
#define AFE_MACRO_OPCODE_AGC_DET_TIME_CONST_CONFIG 0x59
#define AFE_MACRO_OPCODE_AGC_DIG_DET_ABSOLUTE_NUM_CROSSINGS_CONFIG 0x5B
#define AFE_MACRO_OPCODE_AGC_DIG_DET_RELATIVE_NUM_CROSSINGS_CONFIG 0x5A
#define AFE_MACRO_OPCODE_EXT_AGC_CONFIG 0x5C
#define AFE_MACRO_OPCODE_INT_AGC_CONTROLLER_CONFIG 0x5E
#define AFE_MACRO_OPCODE_MIN_MAX_DSA_ATTN_CONFIG 0x5F
#define AFE_MACRO_OPCODE_AGC_EXT_LNA_CONFIG 0x61
#define AFE_MACRO_OPCODE_AGC_EXT_LNA_GAIN_CONFIG 0x66
#define AFE_MACRO_OPCODE_AGC_GAIN_STEP_SIZE_CONFIG 0x67
#define AFE_MACRO_OPCODE_AGC_RF_ANALOG_CONFIG 0x65
#define AFE_MACRO_OPCODE_ALC_CONFIGURATION 0x69
#define AFE_MACRO_OPCODE_FLOATING_POINT_CONFIG_ALC 0x6A
#define AFE_MACRO_OPCODE_COARSE_FINE_MODE_ALC 0x6B

/* DSA Related */
#define AFE_DET_THRESHOLD_MAX_VAL 40
#define AFE_ALC_TOTAL_GAIN_RANGE 50
#define AFE_RX_DSA_MAX_ANA_DSA_DB 25
#define AFE_TX_DSA_MAX_ANA_DSA_DB 34
#define AFE_FB_DSA_MAX_ANA_DSA_DB 25

#define AFE_RX_DSA_MAX_ANA_DSA_INDEX 50
#define AFE_RX_DSA_MAX_DIG_DSA_INDEX 47
#define AFE_TX_DSA_MAX_ANA_DSA_INDEX 29
#define AFE_FB_DSA_MAX_ANA_DSA_INDEX 50

#define AFE_TX_DSA_MAX_ANA_PLUS_DIG_DSA_DB 39

/* AGC Related */
#define AFE_AGC_MAX_WIN_LEN 4000000
#define AFE_AGC_MAX_ABS_NUM_HITS 0xffffff

/* JESD Related */
#define AFE79_REG_ADDR_DAC_JESD_LANE_ENA 0x64
/* SERDES Related */

static const uint16_t afe79afe79jesdToSerdesLaneMapping[8] = {1, 0, 2, 3, 3, 2, 0, 1};

#ifndef NULL
#define NULL (0)
#endif

#endif /* _BASICTYPES_H_ */
