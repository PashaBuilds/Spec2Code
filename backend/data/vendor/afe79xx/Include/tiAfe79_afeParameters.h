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

#ifndef tiAfe79_AFEPARAMETERS_H
#define tiAfe79_AFEPARAMETERS_H

/** @struct afeSystemParamsStruct
 *  @brief This structure contains the System Parameters used in the intialization script of the AFE.<br>
 * 		Some of the system parameters, which are static for a use case, like sampling and interface rates, are captured in this structure, systemParams. This is to prevent passing these redundantly for related functions. For some variables this may act as a state variable to capture current state.<br>
 * 		An array of structures of size NUM_OF_AFE, one per each AFE, should be defined in /Afe79xxUser/Src/afeParameters.c similar to the sample provided.<br>
 * 		This can be generated for each AFE configuration by running AFE.saveCAfeParamsFile() in Latte after generating the initial configuration.<br>
 * 		<b> Version 2.1:</b> <br>
 * 		1. Added documentation.
 */

#include "tiAfe79_agcParams.h"
#include "tiAfe79_papParams.h"

typedef struct afe79SystemParamsStructDef
{
    /// Chip ID of the Device
    uint32_t chipId;
    /// Chip Version of the device
    uint8_t chipVersion;

    /// Multiplier Constant
    uint32_t X;

    // ###############################    TOP and Clocking Parameters      #################################################

    /// Input Reference Clock (KHz)
    uint32_t FRef;
    /// RX ADC Sampling clock. (KHz)
    uint32_t FadcRx;
    /// FB ADC Sampling clock. (KHz)
    uint32_t FadcFb;
    /// DAC Sampling clock. (KHz)
    uint32_t Fdac;

    /// RX Channel Enable for RX[A,B,C,D]
    uint8_t rxEnable[4]; //[chNo]
    /// FB Channel Enable for FB[AB,CD]
    uint8_t fbEnable[2]; //[chNo]
    /// TX Channel Enable for TX[A,B,C,D]
    uint8_t txEnable[4]; //[chNo]

    /** RRF Mode.
     * 0 - FDD Mode.<br>
     * 2 - FDD Mode Quad Band.<br>
     * 5 - TDD Mode.<br>
     * 10 - AB TDD/CD FDD.<br>
     * 11 - AB FDD/CD TDD.<br>
     */
    uint8_t RRFMode;

    /**
        This is the parameter to map ADC output port to the RRF channel<br>
        [FBAB, RXA, RXB]<br>
        Value meaning:<br>
        0-	Data from FB AB ADC is to be fed.<br>
        1-	Data from RX A ADC is to be fed.<br>
        2-	Data from RX B ADC is to be fed.<br>
    */
    uint8_t adcSelect0[3];

    /**
        This is the parameter to map ADC output port to the RRF channel<br>
        [FBCD, RXC, RXD]<br>
        Value meaning:<br>
        0-	Data from FB CD ADC is to be fed.<br>
        1-	Data from RX C ADC is to be fed.<br>
        2-	Data from RX D ADC is to be fed.<br>
    */
    uint8_t adcSelect1[3];

    /**
     * Mode to control TDD.<br>
     * 0- Common TDD for 4T/4R/2F<br>
     * 1- Separate Control for 2T/2R/1F<br>
     * 2- Separate Control for 1T/1R/1F<br>
     * */
    uint8_t modeTdd;

    /**
     * Use PLL clock or external clock for RX Sampling rate. <br>
     *    0 - PLL derived clock for RX.<br>
     *    1 - External Clock Mode for RX.<br>
     *    Note that in this case, the FRef should be equal to the FadcRx. Fdac and FadcFb will be derived use the FRef and PLL.<br>
     */
    uint8_t externalClockRx;

    /**
     * Use PLL clock or external clock for TX Sampling rate.<br>
     * False- PLL derived clock for TX.<br>
     * True - External Clock Mode for TX.<br>
     *
     * Note that in this case, the FRef should be equal to the Fdac. RX clock will be derived from this.<br>
     */
    uint8_t externalClockTx;

    /// When this is 0, the Pin based Sysref will be used by the AFE. When this is set to 1, AFE uses internal Sysref override in AFE and pin sysref is not used. This can be used in cases where there is no need for deterministic latency or phase consistency.<br>
    uint8_t useSpiSysref;

    /// 0-Single Shot Sysref. 1- Continuous Sysref.
    uint8_t continuousSysref;

    /// 0-100Ohm,1-150Ohm,2-300Ohm,3-inf
    uint8_t sysrefTermination;

    /// 0- 3wire SPI Mode. 1-4 wire SPI mode
    uint8_t spiMode;

    /// NCO Frequency Mode. 0-1KHz mode. 1-FCW mode
    uint8_t ncoFreqMode;

    /// Enabling Half Rate Mode for RX [AB,CD]. This will make the sampling rate half of FadcRx.
    uint8_t halfRateModeRx[2];
    /// Enabling Half Rate Mode for FB [AB,CD]. This will make the sampling rate half of FadcFb.
    uint8_t halfRateModeFb[2];
    /// Enabling Half Rate Mode for TX [AB,CD]. This will make the sampling rate half of Fdac.
    uint8_t halfRateModeTx[2];

    /// Enables Averaging Mode for RX [AB,CD]
    uint8_t enableAdcAveragingMode[2];
    /**
     * Combines 2TX channels. Used for enabling Tri-band or Quad-band modes.<br>
     * [TXAB,TXCD]<br>
     * 0- No combining<br>
     * 1- Combine and output on TXA/C<br>
     * */
    uint8_t combineDucMode[2];

    /** Enables Low latency loopback mode for [FBAB to TXA, FBCD to TXC].<br>
     * 0 - Loopback path disabled.<br>
     * 1 - Loopback path enabled.<br>
     */
    uint8_t enableTxFbLoopbackLowLatencyMode[2];

    // ###############################    RX Related Parameters     #################################################

    /// DDC decimation factor for RX [A,B,C,D]. FadcRx/ddcFactorRx for the channel will be output data rate.
    uint8_t ddcFactorRx[4];

    /// RX NCO Frequencies in KHz. rxNco[NCO Number][Channel Number][Band Number]
    uint32_t rxNco[2][4][2];

    /// Number of bands per channel for RX A, B, C, D. 0-Single Band. 1-Dual Band
    uint8_t numBandsRx[4];

    /// Number of active RX NCOs for RX [A,B,C,D] Band0
    uint8_t numRxNCOB0[4]; //[chNo]
    /// Number of active RX NCOs for RX [A,B,C,D] Band1
    uint8_t numRxNCOB1[4]; //[chNo]

    /**
     * NCO Switching mode for RX[AB,CD].<br>
     *       0-No NCO switching in both bands<br>
     *       1-1Pin/R  NCOSEL_0 for RxA Band0, NCOSEL_1 for RxB Band0, NCOSEL_2 for RxC Band0, NCOSEL_3 for RxD Band0. No control for Band 1.<br>
     *       2-1Pin/AB NCOSEL_0 for RxAB Band0, NCOSEL_1 for RxCD Band0. Same Pins control Band 1.
     *       3-2Pin/2R NCOSEL_0 for RxAB Band0, NCOSEL_2 for RxCD Band0. NCOSEL_1 for RxAB Band1, NCOSEL_3 for RxCD Band1.<br>
     *       4-2Pin/2R NCOSEL_1/0 for RxAB Band0, NCOSEL_3/2 for RxCD Band0. No control to Band 1<br>
     *       5-Common NCOSEL_1/0 for all channels Band 0. This is chosen if either entries are 5.<br>
     *       6-Common NCOSEL_3/2/1/0 for all channels Band 0. This is chosen if either entries are 6.<br>
     */
    uint8_t ncoRxMode[2]; //[topNo]
    /// If this is set, then same control goes to AB and CD. In this case, CD corresponding pins are not used
    uint8_t broadcastRxNcoSel;

    // ###############################    FB Related Parameters     #################################################

    /// DDC decimation factor for FB [AB, CD]. FadcFb/ddcFactorFb for the channel will be output data rate.
    uint8_t ddcFactorFb[2]; // DDC decimation factor for FB AB and FB CD;
    /// FB NCO Frequencies in KHz. fbNco[Channel Number][NCO Number]
    uint32_t fbNco[2][4];
    /// Number of active FB NCOs for FB [AB, CD].
    uint8_t numFbNCO[2]; //[chNo]
    /**
     *NCO Switching mode<br>
     *0-No NCO switching<br>
     *1-2 Pin/FB.(FB_NCOSEL_0 and FB_NCOSEL_1 for FBAB, FB_NCOSEL_2 and FB_NCOSEL_3 for FBCD)<br>
     *2-Common 4 Pin.(NCOSEL_0 and NCOSEL_1, NCOSEL_2 and NCOSEL_3 for FBAB/FBCD).<br>
     */
    uint8_t ncoFbMode;

    // ###############################    TX Related Parameters     #################################################

    /// DUC interpolation factor for TX [A,B, C, D]. Fdac/ducFactorTx for the channel will be output data rate.
    uint8_t ducFactorTx[4];

    /// TX NCO Frequencies in KHz. txNco[NCO Number][Channel Number][Band Number]
    uint32_t txNco[2][4][2];

    /// Number of bands per channel for TX A, B, C, D. 0-Single Band. 1-Dual Band
    uint8_t numBandsTx[4]; // Number of bands for TX AB and TX CD. SingleBand/DualBand
    /// Number of active TX NCOs for TX [A,B,C,D] Band0.
    uint8_t numTxNCOB0[4];
    /// Number of active TX NCOs for TX [A,B,C,D] Band1.
    uint8_t numTxNCOB1[4];
    /**
     * NCO Switching TX[AB, CD] <br>
     * First Element
     * 0- No NCO switching in both bands
     * 1- 1pin/2T Control to Band0 (NCOSEL_0 for AB and NCOSEL_1 for CD). Same Pin Controls Band 1 also.
     * 2: 2pin/2T Control to Band0 (NCOSEL_0/1 for AB and NCOSEL_2/3 for CD). Same Pin Controls Band 1 also.
     */
    uint8_t ncoTxMode[2]; //[bandNo]
    /// If this is set, then same control goes to AB and CD. In this case, CD corresponding pins are not used.
    uint8_t broadcastTxNcoSel;

    /// Operates DAC in interleaved mode when this is set to 1.
    uint8_t enableDacInterleavedMode;

    // ###############################    Common JESD Related Parameters     #################################################

    /// 0-	Normal Mode 1-	Enables the JESDTX to JESDRX internal loopback.
    uint8_t jesdLoopbackEn;

    /// 0-	Software JESD Sync 1-	Hardware JESD Sync loopback
    uint8_t syncLoopBack;

    /// Sync Mode for TX/RX AB 0-	CMOS Sync 1- LVDS Sync
    uint8_t jesdABLvdsSync;

    /// Sync Mode for TX/RX AB 0-	CMOS Sync 1- LVDS Sync
    uint8_t jesdCDLvdsSync;

    /// To determine if the linkup is as part of device intialization or executed as separate step. 0-Executed as part of main initialization sequence. 1-Executed separately.
    uint8_t executeLinkUpSequenceSeparately;

    // ###############################    ADC JESD TX Related Parameters     #################################################
    /// RX JESD Mode per mapper: Number of lanes(L).
    uint8_t LMFSHdRx_L[4]; //[mapperNo]
    /// RX JESD Mode per mapper: Number of converters(M).
    uint8_t LMFSHdRx_M[4]; //[mapperNo]
    /// RX JESD Mode per mapper: Number of octets per frame(F).
    uint8_t LMFSHdRx_F[4]; //[mapperNo]
    /// RX JESD Mode per mapper: Number of Samples Per Converter(S).
    uint8_t LMFSHdRx_S[4]; //[mapperNo]
    /// RX JESD Mode per mapper. High Density mode(Hd).
    uint8_t LMFSHdRx_Hd[4]; //[mapperNo]
    /// RX JESD Mode per mapper. Any Special Mode. Should be 0.
    uint8_t LMFSHdRx_Misc[4]; //[mapperNo]

    /// FB JESD Mode per mapper: Number of lanes(L).
    uint8_t LMFSHdFb_L[2]; //[mapperNo]
    /// FB JESD Mode per mapper: Number of converters(M).
    uint8_t LMFSHdFb_M[2]; //[mapperNo]
    /// FB JESD Mode per mapper: Number of octets per frame(F).
    uint8_t LMFSHdFb_F[2]; //[mapperNo]
    /// FB JESD Mode per mapper: Number of Samples Per Converter(S).
    uint8_t LMFSHdFb_S[2]; //[mapperNo]
    /// FB JESD Mode per mapper. High Density mode(Hd).
    uint8_t LMFSHdFb_Hd[2]; //[mapperNo]
    /// FB JESD Mode per mapper. Any Special Mode. Should be 0.
    uint8_t LMFSHdFb_Misc[2]; //[mapperNo]

    /**
     * ADC JESD System Mode<br>
     * SystemMode 0:	2R1F-FDD						; rx1-rx2-fb-fb<br>
     * SystemMode 1:	1R1F-FDD						; rx1-rx1-fb-fb<br>
     * SystemMode 2:	2R-FDD							; rx1-rx1-rx2-rx2<br>
     * SystemMode 3:	1R								; rx1-rx1-rx1-rx1<br>
     * SystemMode 4:	1F								; fb-fb-fb-fb<br>
     * SystemMode 5:	1R1F-TDD						; rx1/fb-rx1/fb-rx1/fb-rx1/fb<br>
     * */
    uint8_t jesdSystemMode[2]; //[topNo]
    /// JESD TX Protocol. JESD TX Protocol for ADC JESD instance [0, 1]. 0- 204B. <br> 2- 204C 64/66. <br> 3- 204B 64/80
    uint8_t jesdTxProtocol[2]; //[topNo]
    /// Scramber enable per RX Mapper.
    uint8_t rxJesdTxScr[4]; //[mapperNo]
    /// Scramber enable per FB Mapper.
    uint8_t fbJesdTxScr[2]; //[mapperNo]
    /// Number of multi frames (K) in JESD 204B or Number of multi-blocks(E) in JESD 204C per RX mapper.
    uint8_t rxJesdTxK[4]; //[mapperNo]
    /// Number of multi frames (K) in JESD 204B or Number of multi-blocks(E) in JESD 204C per FB mapper.
    uint8_t fbJesdTxK[2]; //[mapperNo]
    /// RX JESD TX Sync Mux
    uint8_t rxJesdTxSyncMux[4]; //[mapperNo]
    /// FB JESD TX Sync Mux
    uint8_t fbJesdTxSyncMux[2]; //[mapperNo]

    /// If set to 1, the ILA Params will be set to the defined values. Otherwise will be default values.
    uint8_t setIlaParams;
    /// Number of converters per RX/FB mapper.
    uint8_t jesdTxIlaM[6]; //[mapperNo]
    /// Number of converters per RX/FB mapper.
    uint8_t jesdTxIlaL[6]; //[mapperNo]
    /// Lane ID per ADC JESD TX lane.
    uint8_t jesdTxIlaLid[8]; //[laneNo]

    /// STX Lane polarity inversion per lane. 0 means no inversion. 1 means inversion
    uint8_t serdesTxLanePolarity[8]; //[laneNo]
    /// JESD TX Lane Mux
    uint8_t jesdTxLaneMux[8]; //[laneNo]

    /// 0-	Disable RX/FB DDC-JESD Data Mux 1-  Enable RX/FB DDC-JESD Data Mux
    uint8_t adcDataMuxEn;
    /** RX DDC-JESD Data Mux<br>
     *    Location Meaning:<br>
     *		[A_B0, A_B1, B_B0, B_B1, C_B0, C_B1, D_B0, D_B1]<br>
     *	Value meaning:<br>
     *		0-A_B0<br>
     *		1-A_B1<br>
     *		2-B_B0<br>
     *		3-B_B1<br>
     *		4-C_B0<br>
     *		5-C_B1<br>
     *		6-D_B0<br>
     *		7-D_B1<br>
     */
    uint8_t rxDataMux[8]; //[converterNumber]
    /** FB DDC-JESD Data Mux<br>
     * Location meaning : [FBAB, FBCD]<br>
     * Value meaning:<br>
     *  0-FBAB<br>
     *  1-FBCD<br>
     */
    uint8_t fbDataMux[2]; //[converterNumber]

    /// If set to 1, will send 0s in TDD off state. Else will send random data.
    uint8_t jesdSendZeroesInTddOff;
    /// Per lane pre-Cursor setting. Refer to Function setSerdesTxCursor description for meaning of the value.
    uint8_t serdesTxPreCursor[8];
    /// Per lane post-Cursor setting. Refer to Function setSerdesTxCursor description for meaning of the value.
    uint8_t serdesTxPostCursor[8];
    /// Per lane main-Cursor setting. Refer to Function setSerdesTxCursor description for meaning of the value.
    uint8_t serdesTxMainCursor[8];

    // ###############################    DAC JESD RX Related Parameters     #################################################
    /// TX JESD Mode per mapper: Number of lanes(L).
    uint8_t LMFSHdTx_L[4]; //[mapperNo]
    /// TX JESD Mode per mapper: Number of converters(M).
    uint8_t LMFSHdTx_M[4]; //[mapperNo]
    /// TX JESD Mode per mapper: Number of octets per frame(F).
    uint8_t LMFSHdTx_F[4]; //[mapperNo]
    /// TX JESD Mode per mapper: Number of Samples Per Converter(S).
    uint8_t LMFSHdTx_S[4]; //[mapperNo]
    /// TX JESD Mode per mapper. High Density mode(Hd).
    uint8_t LMFSHdTx_Hd[4]; //[mapperNo]
    /// TX JESD Mode per mapper. Any Special Mode. Should be 0.
    uint8_t LMFSHdTx_Misc[4]; //[mapperNo]

    /// JESD RX Sync Mux
    uint8_t jesdRxSyncMux[4]; //[mapperNo]

    /// JESD RX Protocol. JESD RX Protocol for ADC/DAC JESD instance [0, 1]. 0- 204B. <br> 2- 204C 64/66. <br> 3- 204B 64/80
    uint8_t jesdRxProtocol[2]; //[topNo]
    /// SRX Lane polarity inversion per lane. 0 means no inversion. 1 means inversion
    uint8_t serdesRxLanePolarity[8]; //[laneNo]
    /// JESD RX Lane Mux
    uint8_t jesdRxLaneMux[8]; //[laneNo]

    /// DAC JESD RX RBD Per Mapper
    uint8_t jesdRxRbd[4]; //[mapperNo]
    /// DAC JESD RX RBD Scrambler Enable
    uint8_t jesdRxScr[4]; //[mapperNo]
    /// Number of multi frames (K) in JESD 204B or Number of multi-blocks(E) in JESD 204C per TX mapper.
    uint8_t jesdRxK[4]; //[mapperNo]
    /// DAC JESD RX fcounter offset
    uint8_t jesdRxInitLmfcCounter[4]; //[mapperNo]

    /// 0-	Disable DAC JESD RX-DUC Data Mux 1-   Enable DAC JESD RX-DUC Data Mux
    uint8_t dacDataMuxEn;
    /** DAC JESD RX-DUC Data Mux
     * Location meaning : <br>
     *      [A_B0, A_B1, B_B0, B_B1, C_B0, C_B1, D_B0, D_B1] <br>
     * Value meaning:
     *      0-A_B0<br>
     *      1-A_B1<br>
     *      2-B_B0<br>
     *      3-B_B1<br>
     *      4-C_B0<br>
     *      5-C_B1<br>
     *      6-D_B0<br>
     *      7-D_B1<br>
     */
    uint8_t txDataMux[8]; //[converterNumber]

    /// SerDes RX-Manual CTLE Mode Enable. 0-Auto Adaptive CTLE. 1-Manual Force CTLE
    uint8_t serdesManualCTLEEn;
    /// SerDes RX-Manual CTLE Mode value per lane.
    uint8_t serdesManualCTLE[8]; //[laneNo]

    // ###############################    DSA-AGC Related Parameters     #################################################
    /// Default RX DSA. 1LSB=0.5dB.
    uint8_t defaultRxDsa[4];
    /// Default FB DSA. 1LSB=0.5dB.
    uint8_t defaultFbDsa[2];
    /// Default TX DSA.  1LSB=1dB.
    uint8_t defaultTxDsa[4];

    // ###############################    Calibration Related Parameters     #################################################
    /// Enable RX DSA Calibration.
    uint8_t enableRxDsaCalibration;
    /// [Start,Stop] of RX DSA range to calibrate. 1LSB=1dB.
    uint8_t rxDsaGainRange[2]; //[startStop]

    /// Enable TX DSA Calibration.
    uint8_t enableTxDsaCalibration;
    /// [Start,Stop] of TX DSA range to calibrate.
    uint8_t txDsaGainRange[2]; //[startStop]
    /// Mode for Reliability Detector release. 0- Time Based; 1- RF Analog Detector based; 2-Reliability Detector Based
    uint8_t reliabilityDetectorDecayMode; //[startStop]

    /// Enable mode to set independent FB DSA value per TX, selected based on pins. 1LSB=0.5dB.
    uint8_t fbDsaPerTxEn;

    /// Set the FB DSA value for each TX selection
    uint8_t fbDsaPerTx[4];

    /** Sets the Mux mode for the Pin based FB DSA control.<br>
        0 -Single Fb Mode FB AB. Only FBAB DSA should be controlled by pins.<br>
        1 -Single Fb Mode FB CD. Only FBCD DSA should be controlled by pins.<br>
        2- Dual Fb_Mode. LSB 2 pins Control to FBAB DSA and MSB 2 pins control FBCD DSA.<br>
    */
    uint8_t txToFbMode;

    /// SPI used to access PLL Pages. <br>1- SPIA.<br>2-SPIB
    uint8_t spiInUseForPllAccess;

    /// 6 AGC Parameters: 4 Rx and 2 for Fb
    afe79AgcSystemParamsStruct rxAgcParams[6];
    afe79PapSystemParamsStruct txPapParams[4];
} afe79SystemParamsStruct;

typedef struct afe79SystemStatusStructDef
{
    /// Lane rate of RX Mappers (KHz)
    uint32_t laneRateRx[4];

    /// Lane rate of FB Mappers (KHz)
    uint32_t laneRateFb[2];

    /// Lane rate of TX Mappers (KHz)
    uint32_t laneRateTx[4];

    /// Serdes TX Lane rate (KHz)
    uint32_t serdesTxLaneRate[8];

    /// Serdes RX Lane rate (KHz)
    uint32_t serdesRxLaneRate[8];

} afe79SystemStatusStruct;

#endif
