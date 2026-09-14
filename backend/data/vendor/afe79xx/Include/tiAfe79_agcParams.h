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

#ifndef tiAfe79_HAFE_AGC_PARAMS_H
#define tiAfe79_HAFE_AGC_PARAMS_H

/** @file tiAfe79_agcParams.h
 * 	@brief This file has AFE AGC Related System Parameters definition.<br>
 */

#include <stdint.h>

/** @struct afe79AgcSystemParamsStruct
 *  @brief This structure contains the AGC related System Parameters.<br>
 *
 */

typedef struct afe79AgcSystemParamsStructDef
{
    /// Chain Enable for the channel
    uint16_t chainen;

    /**  Mode of operation of the AGC per channel. <br>
     * 	0- disabled	<br>
     *    1- Internal AGC<br>
     *    2- External AGC SPI control<br>
     *    3- External AGC Fast DSA control<br>
     *    4- External AGC 8-Pin control 0.5dB step<br>
     *    5- External AGC 4-Pin control<br>
     *    6- External AGC 8-Pin control 1dB step<br>
     */
    uint8_t agcMode;

    /* ############################################################*/
    /* ############### Internal AGC Config ###############*/
    /* ############################################################*/

    /**
         * TDD Freeze Mode:<br>
            0 → Reset the AGC state during the OFF period of TDD<br>
            1 → Freeze the AGC state during the OFF period of TDD<br>
        */
    uint8_t tdd_freeze_agc;
    /**
     * Blanking Time when an External Component Gain Changes<br>
        The value is interpreted as the number of FADC/8 clocks for which the detectors are to be blanked.
    */
    uint16_t blank_time_extcomp;
    /**
     * Pin based AGC freeze enable<br>
        0x00 → Disable pin based AGC Freeze<br>
        0x01 → Enable pin based AGC Freeze
    */
    uint8_t en_agcfreeze_pin;

    /// Minimum DSA Attenuation(1LSB=0.5dB)
    uint8_t minDsaAttn;
    /// Maximum DSA Attenuation(1LSB=0.5dB)
    uint8_t maxDsaAttn;

    /* ############################################################*/
    /* ############### AGC Detector Params ###############*/
    /* ############################################################*/

    /* ############### Attack Detector Params ###############*/

    /**
     * Enable of Attack Detectors. Set 1 to enable. <br>[big step, small step, power det]
     */
    uint8_t atken[3];
    /**
     * Step Size for Attack detectors. 1LSB=0.5dB.<br
     * [Big Step Attack, Small Step and Power Attack]. Power Detector and Small Step Detector uses the same step size.
     * */
    uint8_t atksize[2];
    /**
     * Window Length (also referred to as Time Constant) for attack detectors. This is absolute time in range of 10ns to  40milliseconds in steps of 10ns. 1LSB=10ns.<br>
     * First index is for Big Step Attack Detectors.<br>
        Second index is common for small step attack,  fast attack using LNA RF Detector, and band detector based attack.
     */
    uint32_t atkwinlength[2];
    /**
     * Attack Level Thresholds. Range is 0 dBFS to -63.75 dBFS, in steps of -0.25dbfs. (-val/4) will be the programmed dbFs value.<br>
     * [Big Step, Small step, Power detector]
     */
    uint8_t atkthreshold[3];
    /**
     * Relative number of hits threshold for Attack Detector. In every time period, the attack detectors will trigger if the signal is above the programmed level threshold for more than this numHits threshold of samples. <br>
     * This value is as fraction of the atkwinlength. With 0 corresponding to 0% 2^16 corresponding to 100%. Range is 0-0xffff.<br>
     * This is valid only if the relative mode of Num Hits is programmed.<br>
     * [Big Step Attack, (Small Step and Power Attack)]. Power Detector and Small Step Detector uses the same value.
     */
    uint16_t atkNumHitsRel[2];
    /**
     * Absolute number of hits threshold for Attack Detector. In every time period, the attack detectors will trigger if the signal is above the programmed level threshold for more than this numHits threshold of samples. <br>
     * This value is Number of samples at FADC/8. Range is 0-0xffffff.<br>
     * This is valid only if the absolute mode of Num Hits is programmed.<br>
     * [Big Step Attack, Small Step and Power Attack]. Power Detector and Small Step Detector uses the same value.
     */
    uint32_t atkNumHitsAbs[2];

    /* ############### Decay Detector Params ###############*/

    /**
     * Enable of Decay Detectors. Set 1 to enable. <br>[big step, small step, power det]
     */
    uint8_t decayen[3];
    /**
     * Step Size for Decay detectors. 1LSB=0.5dB.<br
     * [Big Step Decay, (Small Step and Power Decay)]. Power Detector and Small Step Detector uses the same step size.
     * */
    uint8_t decaysize[2];

    /**
     * Window Length (also referred to as Time Constant) for decay detectors. This is absolute time in range of 10ns to  40milliseconds in steps of 10ns (value is 1 - 0x3d0900). 1LSB=10ns.<br>
     *  All detectors use the same Decay Window length.
     */
    uint32_t decaywinlength;
    /**
     * Decay Level Thresholds. Range is 0 dBFS to -63.75 dBFS, in steps of -0.25dbfs. If val is programmed value, (-val/4) will be the dbFs value. <br>
     * [Big Step, Small step, Power detector]
     */
    uint8_t decaythreshold[3];
    /**
     * Relative number of hits threshold for Decay Detector. In every time period, the decay detectors will trigger if the signal is above the programmed level threshold for less than this numHits threshold of samples. <br>
     * This value is as fraction of the decaywinlength. With 0 corresponding to 0% 2^16 corresponding to 100%. Range is 0-0xffff.<br>
     * This is valid only if the relative mode of Num Hits is programmed.<br>
     * [Big Step decay, (Small Step and Power decay)]. Power Detector and Small Step Detector uses the same value.
     */
    uint16_t decayNumHitsRel[2];
    /**
     * Absolute number of hits threshold for Decay Detector. In every time period, the decay detectors will trigger if the signal is above the programmed level threshold for less than this numHits threshold of samples. <br>
     * This value is Number of samples at FADC/8. Range is 0-0xffffff.<br>
     * This is valid only if the absolute mode of Num Hits is programmed.<br>
     * [Big Step decay, (Small Step and Power decay)]. Power Detector and Small Step Detector uses the same value.
     */
    uint32_t decayNumHitsAbs[2];

    /* ############### RF Analog Detector Detector Params ###############*/
    /// RF Analog detector Enable. 0-Disable. 1-Enable
    uint8_t rfdeten;
    /**
     * RF Analog Detector Mode<br>
        0x0 → customer AGC(External AGC mode)<br>
        0x1 → detector used as fixed step attack detector<br>
        0x2 → detector used to control LNA bypass<br>
        Others- Invalid
     */
    uint8_t custRfMode;

    /// Step Size for Attack when custRfMode is 1. 1LSB=0.5dB<br>
    uint8_t rfdetstepsize;

    /**
     * Detector Threshold in dBFs(When custRfMode=0x1: detector used as fixed step attack detector). 1LSB=1dB.<br>
     * Detector Threshold in dBm(When custRfMode=0x0 or custRfMode=0x2). 1LSB=1dB.
     */
    uint8_t rfdetThreshold;
    /// Absolute/Relative option for Time Crossings. 0 → Absolute; 1 → Relative
    uint8_t rfdetNumhitsmode;
    /**
     *  When rfdetNumhitsmode==0<br>
        This is number of samples at FADC for customer RF detector. Note that this should be less than the number of samples in a window in atkwinlength[1].<br>
        When rfdetNumhitsmode==1<br>
        This is fraction of samples crossing signal threshold in window length corresponding to atkwinlength[1]. This fraction is interpreted as a 32 bit precision value with the value 2^32 corresponding to 100%. Supported range is 0-2^32-1
     */
    uint32_t rfdetnumhits;

    /* ############################################################*/
    /* ############### LNA Control Configuration Params ###############*/
    /* ############################################################*/
    /// Enable LNA Control by AFE internal AGC. 0-Disable. 1-Enable
    uint8_t lnaEn;
    /// LNA Gain dependency on temperature. <br>0 → LNA gain phase does not depend on temperature. <br>1 → LNA gain phase depends on temperature
    uint8_t extLnaTempModel;

    /// 0 → Common LNA control for both bands; 1 → Independent LNA control for both bands
    uint8_t singleDualBandMode;
    /// 0 → Disable Band Detectors. 1 → Enable band detectors. Applicable only when Dual LNA control is enabled.
    uint8_t enBandDet;
    /// Band Detector Bandwidth Selection selection(Applicable only when Independent LNA control for both bands and band detectors are enabled). 0 → Higher bandwidth; 1 → Output bandwidth
    uint8_t tapOffPoint;

    /* ############### LNA Gain Configuration Params ###############*/

    /**
     * LNA Band0 Gain. This is also the gain when a single LNA is used. This is used only when extLnaTempModel=0.<br>
     * There are maximum of 3 stages supported. This is the gain for each of the 3 stages. [Stage 0, Stage 1, Stage 2]
     * 1LSB=1/32dB.
     * */
    uint16_t lnagain0;
    /**
     * LNA Band0 Phase. This is also the Phase when a single LNA is used. This is used only when extLnaTempModel=0.<br>
     * There are maximum of 3 stages supported. This is the Phase for each of the 3 stages. [Stage 0, Stage 1, Stage 2]
     * 1LSB=360/1024 degrees.
     * */
    uint16_t lnaphase0;
    /**
     * LNA Band1 Gain. This can be ignored when a single LNA is used. This is used only when extLnaTempModel=0.<br>
     * There are maximum of 3 stages supported. This is the gain for each of the 3 stages. [Stage 0, Stage 1, Stage 2]
     * 1LSB=1/32dB.
     * */
    uint16_t lnagain1;
    /**
     * LNA Band1 Phase. This can be ignored when a single LNA is used. This is used only when extLnaTempModel=0.<br>
     * There are maximum of 3 stages supported. This is the Phase for each of the 3 stages. [Stage 0, Stage 1, Stage 2]
     * 1LSB=360/1024 degrees.
     * */
    uint16_t lnaphase1;
    /** LNA gain margin ( this value is in dB scale where 1 LSB = 0.5 dB).<br>
        LNA re-enable will happen when Current DSA Attenuation <= Maximum DSA Attenuation(maxDsaAttn) - LNA Gain - LNA Gain Margin (lnaGainMargin) in Single LNA Control Mode.<br>
        Not Applicable in Dual LNA Control
    */
    uint16_t lnaGainMargin;

    // temp model
    /// LNA Gain Temperature Model, start temperature (Signed value in degree Celsius). <8.0,s> Format
    uint8_t startTemp;
    /// LNA Gain Temperature Model, step temperature (Signed value in degree Celsius). <8.0,s> Format
    uint8_t stepTemp;
    /// LNA Gain Temperature Model, number of steps. Number of steps(Value of N corresponds to N gain phase values for N different temperatures)
    uint8_t NumStep;
    /// External LNA temperature. (Signed value in degree Celsius). <8.0,s> Format
    uint8_t temp_idxB0;
    /// External LNA temperature. (Signed value in degree Celsius). <8.0,s> Format
    uint8_t temp_idxB1;

    /* ############################################################*/
    /* ############### External AGC Configuration ###############*/
    /* ############################################################*/
    /**
        This determines what detector outputs come out of Pin0 or BIT0 of I data. <br>
        It can be configured to carry ORed combination of selected bits.<br>
        Setting a particular bit gets the detector on to the corresponding pin/LSB.<br>

            Bit 15: Reserved. Set to 0.<br>
            Bit 14: Dig OVR<br>
            Bit 12 or Bit 13: Reliability Detector<br>
            Bit 11: Reserved. Set to 0.<br>
            Bit 10: Band 1 peak attack<br>
            Bit 9: Band 1 peak decay<br>
            Bit 8: Band 0 peak attack<br>
            Bit 7: Band 0 peak decay<br>
            Bit 6: LNARF detector<br>
            Bit 5: Power attack detector<br>
            Bit 4: Power decay detector<br>
            Bit 3: Big step attack<br>
            Bit 2: Small step attack<br>
            Bit 1: Big step decay<br>
            Bit 0: Small step decay<br>
    */
    uint16_t pin0sel;

    /**
        This determines what detector outputs come out of Pin1 or BIT0 of Q data. <br>
        It can be configured to carry ORed combination of selected bits.<br>
        Setting a particular bit gets the detector on to the corresponding pin/LSB.<br>

            Bit 15: Reserved. Set to 0.<br>
            Bit 14: Dig OVR<br>
            Bit 12 or Bit 13: Reliability Detector<br>
            Bit 11: Reserved. Set to 0.<br>
            Bit 10: Band 1 peak attack<br>
            Bit 9: Band 1 peak decay<br>
            Bit 8: Band 0 peak attack<br>
            Bit 7: Band 0 peak decay<br>
            Bit 6: LNARF detector<br>
            Bit 5: Power attack detector<br>
            Bit 4: Power decay detector<br>
            Bit 3: Big step attack<br>
            Bit 2: Small step attack<br>
            Bit 1: Big step decay<br>
            Bit 0: Small step decay<br>
    */
    uint16_t pin1sel;
    /**
        This determines what detector outputs come out of Pin2 or BIT1 of I data. <br>
        It can be configured to carry ORed combination of selected bits.<br>
        Setting a particular bit gets the detector on to the corresponding pin/LSB.<br>

            Bit 15: Reserved. Set to 0.<br>
            Bit 14: Dig OVR<br>
            Bit 12 or Bit 13: Reliability Detector<br>
            Bit 11: Reserved. Set to 0.<br>
            Bit 10: Band 1 peak attack<br>
            Bit 9: Band 1 peak decay<br>
            Bit 8: Band 0 peak attack<br>
            Bit 7: Band 0 peak decay<br>
            Bit 6: LNARF detector<br>
            Bit 5: Power attack detector<br>
            Bit 4: Power decay detector<br>
            Bit 3: Big step attack<br>
            Bit 2: Small step attack<br>
            Bit 1: Big step decay<br>
            Bit 0: Small step decay<br>
    */
    uint16_t pin2sel;
    /**
        This determines what detector outputs come out of Pin3 or BIT1 of Q data. <br>
        It can be configured to carry ORed combination of selected bits.<br>
        Setting a particular bit gets the detector on to the corresponding pin/LSB.<br>

            Bit 15: Reserved. Set to 0.<br>
            Bit 14: Dig OVR<br>
            Bit 12 or Bit 13: Reliability Detector<br>
            Bit 11: Reserved. Set to 0.<br>
            Bit 10: Band 1 peak attack<br>
            Bit 9: Band 1 peak decay<br>
            Bit 8: Band 0 peak attack<br>
            Bit 7: Band 0 peak decay<br>
            Bit 6: LNARF detector<br>
            Bit 5: Power attack detector<br>
            Bit 4: Power decay detector<br>
            Bit 3: Big step attack<br>
            Bit 2: Small step attack<br>
            Bit 1: Big step decay<br>
            Bit 0: Small step decay<br>
    */
    uint16_t pin3sel;
    /// Determines whether to send detector data on LSB in External AGC mode. For getting on pins, need to map the corresponding GPIO functions to the GPIO Balls. 0x00 → pins. 0x01 → LSBs and Pins
    uint8_t pkDetPinLsbSel;
    /// Pulse Expansion Count. This value here is in steps of 10 ns. This pulseExpansionCount*10ns is the pulse width.Supported Range: 0-0xff
    uint16_t pulseExpansionCount;
    /// 0-Send only on Bits 0 of I and Q. 1- Send on both Bits 0 and 1.
    uint8_t pkDetOnPenultimateLsb;
    /// Enable GPIO based reset to detectors. 0-Disable. 1-Enable
    uint8_t gpioRstEnable;

    /// For 4-Pin based DSA control Init.  ((pin_value * dsaStep) +dsaInit)*0.5dB
    uint8_t dsaInit;
    /// For 4-Pin based DSA control step.  ((pin_value * dsaStep) +dsaInit)*0.5dB
    uint8_t dsaStep;
    /// For 4-Pin based DSA control Maximum input Pin delay.
    uint8_t maxInpPinDelay;

    /* ############################################################*/
    /* ############### ALC Configuration ###############*/
    /* ############################################################*/
    /// Enable the ALC block.
    uint8_t alcEn;
    /**
     * ALC Mode<br>
        0: Floatingpoint<br>
        2: Coarse gain index on LSBs of only I / Q <br>
        3: Coarse gain index on LSBS of both I,Q<br>
        4: Coarse gain index sent on the ALC output pins<br>
        5: Coarse gain sent as input over the ALC input pins
    */
    uint8_t alcMode;

    // Total gain range used by ALC for gain compensation. 1LSB=1dB. Should be < AFE79_RX_DSA_MAX_ANA_DSA_DB
    uint8_t totalGainRange;
    // Minimum Attenuation used by ALC for compensation when useMinAttnAgc = 0. should be <32. Value doesn;t matter when useMinAttnAgc=1
    uint8_t minAttnAlc;
    /** Configure the Min Attenuation Mode.<br>
        0: Use minAttnAlc for minimum attenuation for which compensation is required.<br>
        1: Enable ALC to use minimum attenuation from AGC for which compensation is required.
    */
    uint8_t useMinAttnAgc;
    /**
     * ALC Floating Point Mode. Sets whether to send MSB of mantissa always in Floating Point mode of ALC.<br>
        0: If exponent > 0, do not send MSB <br>
        1: Send MSB always
    */
    uint8_t fltPtMode;
    /**
     * Floating Point Format. Number of Mantissa and Exponent bits to be used in floating point mode of ALC <br>
            0: 2 bit exponent , 13 bit mantissa and 1 bit sign<br>
            1: 3 bit exponent, 12 bit mantissa and 1 bit sign<br>
            2: 4 bit exponent, 11 bit mantissa and 1 bit sign
     */
    uint8_t fltPtFmt;

    // coarseFineConfig
    /**
     * Choose the coarse step size. Appropriate value has to be chosen which can represent the complete attenuation range of operation.<br>
            0x00 → 0 dB<br>
            0x01 → 1 dB<br>
            0x02 → 2 dB<br>
            0x03 → 3 dB<br>
            0x04 → 4 dB<br>
            0x05 → 5 dB<br>
            0x06 → 6 dB<br>
            0x08 → 8 dB
    */
    uint8_t stepSize;
    /// Choose the number of bits of coarse index. Supported Values are 0,2,3,4.
    uint8_t nBitIndex;
    /**
     * Coarse Index Invert. If this value is<br>
                        0: coarse index is transmitted as is.<br>
                        1: (15-coarse index) is transmitted
    */
    uint8_t indexInvert;
    /**
     * Coarse Index Swap. If to swap coarse index on I and Q.<br>
                        0: LSB on I, MSB on Q<br>
                        1: MSB on I, LSB on Q
     * */
    uint8_t indexSwapIQ;
    /// This is the signal back-off, the offset attenuation applied. (in dB) This should be less than totalGainRange.
    uint8_t sigBackOff;
    /// Applicable only when nBitIndex is 3. If this is set, in the bit-4 indicates if the DSA changed. Otherwise, 0 will be sent.
    uint8_t gainChangeIndEn;
    /** Coarse Index Pin Delay<br>
        In the case where coarse index is sent over the ALC pins, this field gives the amount of delay that needs to be applied on the gain data before being sent on the pins. The value programmed here will correspond to number of cycles of interface rate clock.<br>
        This can be used by the customer to match the ALC pin information with latency of the data through the JESD interface
    */
    uint16_t outputDgcPinDelay;

} afe79AgcSystemParamsStruct;

#endif
#endif
