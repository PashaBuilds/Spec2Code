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

#include <stdint.h>
#include "tiAfe79_afeGlobalConstants.h"
#include "tiAfe79_afeCommonMacros.h"
#include "tiAfe79_afeDeviceConstants.h"
#include "tiAfe79_afeLibGlobals.h"
#include "tiAfe79_agcParamsSetterGetter.h"
#include "tiAfe79_basicFunctions.h"

/**
	@brief Set AFE Parameter chainen
	@details Set AFE Parameter chainen
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_chainen)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].chainen=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter chainen
	@details Get AFE Parameter chainen
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_chainen)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].chainen;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter agcMode
	@details Set AFE Parameter agcMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_agcMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].agcMode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter agcMode
	@details Get AFE Parameter agcMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_agcMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].agcMode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter tdd_freeze_agc
	@details Set AFE Parameter tdd_freeze_agc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_tdd_freeze_agc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].tdd_freeze_agc=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter tdd_freeze_agc
	@details Get AFE Parameter tdd_freeze_agc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_tdd_freeze_agc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].tdd_freeze_agc;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter blank_time_extcomp
	@details Set AFE Parameter blank_time_extcomp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_blank_time_extcomp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].blank_time_extcomp=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter blank_time_extcomp
	@details Get AFE Parameter blank_time_extcomp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_blank_time_extcomp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].blank_time_extcomp;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter en_agcfreeze_pin
	@details Set AFE Parameter en_agcfreeze_pin
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_en_agcfreeze_pin)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].en_agcfreeze_pin=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter en_agcfreeze_pin
	@details Get AFE Parameter en_agcfreeze_pin
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_en_agcfreeze_pin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].en_agcfreeze_pin;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter minDsaAttn
	@details Set AFE Parameter minDsaAttn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_minDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].minDsaAttn=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter minDsaAttn
	@details Get AFE Parameter minDsaAttn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_minDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].minDsaAttn;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter maxDsaAttn
	@details Set AFE Parameter maxDsaAttn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_maxDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].maxDsaAttn=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter maxDsaAttn
	@details Get AFE Parameter maxDsaAttn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_maxDsaAttn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].maxDsaAttn;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atken
	@details Set AFE Parameter atken
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atken)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atken[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atken
	@details Get AFE Parameter atken
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atken)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atken[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atksize
	@details Set AFE Parameter atksize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atksize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atksize[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atksize
	@details Get AFE Parameter atksize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atksize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atksize[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atkwinlength
	@details Set AFE Parameter atkwinlength
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkwinlength)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkwinlength[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atkwinlength
	@details Get AFE Parameter atkwinlength
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkwinlength)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkwinlength[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atkthreshold
	@details Set AFE Parameter atkthreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkthreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkthreshold[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atkthreshold
	@details Get AFE Parameter atkthreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkthreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkthreshold[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atkNumHitsRel
	@details Set AFE Parameter atkNumHitsRel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint16_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkNumHitsRel[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atkNumHitsRel
	@details Get AFE Parameter atkNumHitsRel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkNumHitsRel[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter atkNumHitsAbs
	@details Set AFE Parameter atkNumHitsAbs
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_atkNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkNumHitsAbs[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter atkNumHitsAbs
	@details Get AFE Parameter atkNumHitsAbs
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_atkNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].atkNumHitsAbs[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decayen
	@details Set AFE Parameter decayen
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayen)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayen[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decayen
	@details Get AFE Parameter decayen
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayen)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayen[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decaysize
	@details Set AFE Parameter decaysize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaysize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaysize[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decaysize
	@details Get AFE Parameter decaysize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaysize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaysize[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decaywinlength
	@details Set AFE Parameter decaywinlength
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaywinlength)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint32_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaywinlength=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decaywinlength
	@details Get AFE Parameter decaywinlength
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaywinlength)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaywinlength;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decaythreshold
	@details Set AFE Parameter decaythreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decaythreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint8_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaythreshold[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decaythreshold
	@details Get AFE Parameter decaythreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decaythreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<3);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decaythreshold[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decayNumHitsRel
	@details Set AFE Parameter decayNumHitsRel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint16_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayNumHitsRel[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decayNumHitsRel
	@details Get AFE Parameter decayNumHitsRel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayNumHitsRel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayNumHitsRel[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter decayNumHitsAbs
	@details Set AFE Parameter decayNumHitsAbs
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param index0 index0 Index
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_decayNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t index0, uint32_t val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayNumHitsAbs[index0]=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter decayNumHitsAbs
	@details Get AFE Parameter decayNumHitsAbs
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param index0 index0 Index
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_decayNumHitsAbs)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t index0, uint32_t *val)
{
	AFE79_ID_VALIDITY();
	AFE79_PARAMS_VALID(index0<2);
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].decayNumHitsAbs[index0];
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter rfdeten
	@details Set AFE Parameter rfdeten
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdeten)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdeten=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter rfdeten
	@details Get AFE Parameter rfdeten
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdeten)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdeten;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter custRfMode
	@details Set AFE Parameter custRfMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_custRfMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].custRfMode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter custRfMode
	@details Get AFE Parameter custRfMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_custRfMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].custRfMode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter rfdetstepsize
	@details Set AFE Parameter rfdetstepsize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetstepsize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetstepsize=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter rfdetstepsize
	@details Get AFE Parameter rfdetstepsize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetstepsize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetstepsize;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter rfdetThreshold
	@details Set AFE Parameter rfdetThreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetThreshold)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetThreshold=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter rfdetThreshold
	@details Get AFE Parameter rfdetThreshold
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetThreshold)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetThreshold;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter rfdetNumhitsmode
	@details Set AFE Parameter rfdetNumhitsmode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetNumhitsmode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetNumhitsmode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter rfdetNumhitsmode
	@details Get AFE Parameter rfdetNumhitsmode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetNumhitsmode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetNumhitsmode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter rfdetnumhits
	@details Set AFE Parameter rfdetnumhits
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_rfdetnumhits)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint32_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetnumhits=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter rfdetnumhits
	@details Get AFE Parameter rfdetnumhits
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_rfdetnumhits)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint32_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].rfdetnumhits;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnaEn
	@details Set AFE Parameter lnaEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaEn=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnaEn
	@details Get AFE Parameter lnaEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaEn;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter extLnaTempModel
	@details Set AFE Parameter extLnaTempModel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_extLnaTempModel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].extLnaTempModel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter extLnaTempModel
	@details Get AFE Parameter extLnaTempModel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_extLnaTempModel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].extLnaTempModel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter singleDualBandMode
	@details Set AFE Parameter singleDualBandMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_singleDualBandMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].singleDualBandMode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter singleDualBandMode
	@details Get AFE Parameter singleDualBandMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_singleDualBandMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].singleDualBandMode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter enBandDet
	@details Set AFE Parameter enBandDet
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_enBandDet)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].enBandDet=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter enBandDet
	@details Get AFE Parameter enBandDet
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_enBandDet)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].enBandDet;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter tapOffPoint
	@details Set AFE Parameter tapOffPoint
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_tapOffPoint)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].tapOffPoint=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter tapOffPoint
	@details Get AFE Parameter tapOffPoint
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_tapOffPoint)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].tapOffPoint;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnagain0
	@details Set AFE Parameter lnagain0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnagain0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnagain0=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnagain0
	@details Get AFE Parameter lnagain0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnagain0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnagain0;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnaphase0
	@details Set AFE Parameter lnaphase0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaphase0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaphase0=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnaphase0
	@details Get AFE Parameter lnaphase0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaphase0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaphase0;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnagain1
	@details Set AFE Parameter lnagain1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnagain1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnagain1=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnagain1
	@details Get AFE Parameter lnagain1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnagain1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnagain1;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnaphase1
	@details Set AFE Parameter lnaphase1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaphase1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaphase1=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnaphase1
	@details Get AFE Parameter lnaphase1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaphase1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaphase1;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter lnaGainMargin
	@details Set AFE Parameter lnaGainMargin
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_lnaGainMargin)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaGainMargin=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter lnaGainMargin
	@details Get AFE Parameter lnaGainMargin
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_lnaGainMargin)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].lnaGainMargin;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter startTemp
	@details Set AFE Parameter startTemp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_startTemp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].startTemp=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter startTemp
	@details Get AFE Parameter startTemp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_startTemp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].startTemp;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter stepTemp
	@details Set AFE Parameter stepTemp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_stepTemp)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].stepTemp=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter stepTemp
	@details Get AFE Parameter stepTemp
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_stepTemp)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].stepTemp;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter NumStep
	@details Set AFE Parameter NumStep
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_NumStep)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].NumStep=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter NumStep
	@details Get AFE Parameter NumStep
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_NumStep)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].NumStep;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter temp_idxB0
	@details Set AFE Parameter temp_idxB0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_temp_idxB0)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].temp_idxB0=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter temp_idxB0
	@details Get AFE Parameter temp_idxB0
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_temp_idxB0)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].temp_idxB0;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter temp_idxB1
	@details Set AFE Parameter temp_idxB1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_temp_idxB1)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].temp_idxB1=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter temp_idxB1
	@details Get AFE Parameter temp_idxB1
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_temp_idxB1)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].temp_idxB1;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pin0sel
	@details Set AFE Parameter pin0sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin0sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin0sel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pin0sel
	@details Get AFE Parameter pin0sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin0sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin0sel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pin1sel
	@details Set AFE Parameter pin1sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin1sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin1sel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pin1sel
	@details Get AFE Parameter pin1sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin1sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin1sel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pin2sel
	@details Set AFE Parameter pin2sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin2sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin2sel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pin2sel
	@details Get AFE Parameter pin2sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin2sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin2sel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pin3sel
	@details Set AFE Parameter pin3sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pin3sel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin3sel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pin3sel
	@details Get AFE Parameter pin3sel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pin3sel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pin3sel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pkDetPinLsbSel
	@details Set AFE Parameter pkDetPinLsbSel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pkDetPinLsbSel)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pkDetPinLsbSel=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pkDetPinLsbSel
	@details Get AFE Parameter pkDetPinLsbSel
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pkDetPinLsbSel)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pkDetPinLsbSel;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pulseExpansionCount
	@details Set AFE Parameter pulseExpansionCount
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pulseExpansionCount)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pulseExpansionCount=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pulseExpansionCount
	@details Get AFE Parameter pulseExpansionCount
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pulseExpansionCount)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pulseExpansionCount;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter pkDetOnPenultimateLsb
	@details Set AFE Parameter pkDetOnPenultimateLsb
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_pkDetOnPenultimateLsb)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pkDetOnPenultimateLsb=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter pkDetOnPenultimateLsb
	@details Get AFE Parameter pkDetOnPenultimateLsb
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_pkDetOnPenultimateLsb)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].pkDetOnPenultimateLsb;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter gpioRstEnable
	@details Set AFE Parameter gpioRstEnable
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_gpioRstEnable)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].gpioRstEnable=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter gpioRstEnable
	@details Get AFE Parameter gpioRstEnable
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_gpioRstEnable)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].gpioRstEnable;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter dsaInit
	@details Set AFE Parameter dsaInit
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_dsaInit)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].dsaInit=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter dsaInit
	@details Get AFE Parameter dsaInit
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_dsaInit)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].dsaInit;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter dsaStep
	@details Set AFE Parameter dsaStep
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_dsaStep)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].dsaStep=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter dsaStep
	@details Get AFE Parameter dsaStep
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_dsaStep)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].dsaStep;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter maxInpPinDelay
	@details Set AFE Parameter maxInpPinDelay
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_maxInpPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].maxInpPinDelay=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter maxInpPinDelay
	@details Get AFE Parameter maxInpPinDelay
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_maxInpPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].maxInpPinDelay;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter alcEn
	@details Set AFE Parameter alcEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_alcEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].alcEn=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter alcEn
	@details Get AFE Parameter alcEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_alcEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].alcEn;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter alcMode
	@details Set AFE Parameter alcMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_alcMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].alcMode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter alcMode
	@details Get AFE Parameter alcMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_alcMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].alcMode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter totalGainRange
	@details Set AFE Parameter totalGainRange
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_totalGainRange)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].totalGainRange=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter totalGainRange
	@details Get AFE Parameter totalGainRange
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_totalGainRange)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].totalGainRange;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter minAttnAlc
	@details Set AFE Parameter minAttnAlc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_minAttnAlc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].minAttnAlc=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter minAttnAlc
	@details Get AFE Parameter minAttnAlc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_minAttnAlc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].minAttnAlc;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter useMinAttnAgc
	@details Set AFE Parameter useMinAttnAgc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_useMinAttnAgc)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].useMinAttnAgc=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter useMinAttnAgc
	@details Get AFE Parameter useMinAttnAgc
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_useMinAttnAgc)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].useMinAttnAgc;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter fltPtMode
	@details Set AFE Parameter fltPtMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_fltPtMode)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].fltPtMode=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter fltPtMode
	@details Get AFE Parameter fltPtMode
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_fltPtMode)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].fltPtMode;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter fltPtFmt
	@details Set AFE Parameter fltPtFmt
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_fltPtFmt)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].fltPtFmt=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter fltPtFmt
	@details Get AFE Parameter fltPtFmt
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_fltPtFmt)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].fltPtFmt;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter stepSize
	@details Set AFE Parameter stepSize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_stepSize)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].stepSize=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter stepSize
	@details Get AFE Parameter stepSize
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_stepSize)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].stepSize;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter nBitIndex
	@details Set AFE Parameter nBitIndex
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_nBitIndex)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].nBitIndex=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter nBitIndex
	@details Get AFE Parameter nBitIndex
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_nBitIndex)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].nBitIndex;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter indexInvert
	@details Set AFE Parameter indexInvert
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_indexInvert)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].indexInvert=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter indexInvert
	@details Get AFE Parameter indexInvert
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_indexInvert)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].indexInvert;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter indexSwapIQ
	@details Set AFE Parameter indexSwapIQ
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_indexSwapIQ)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].indexSwapIQ=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter indexSwapIQ
	@details Get AFE Parameter indexSwapIQ
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_indexSwapIQ)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].indexSwapIQ;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter sigBackOff
	@details Set AFE Parameter sigBackOff
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_sigBackOff)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].sigBackOff=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter sigBackOff
	@details Get AFE Parameter sigBackOff
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_sigBackOff)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].sigBackOff;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter gainChangeIndEn
	@details Set AFE Parameter gainChangeIndEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_gainChangeIndEn)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint8_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].gainChangeIndEn=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter gainChangeIndEn
	@details Get AFE Parameter gainChangeIndEn
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_gainChangeIndEn)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint8_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].gainChangeIndEn;
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Set AFE Parameter outputDgcPinDelay
	@details Set AFE Parameter outputDgcPinDelay
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chSel Bit-Wise Channel select
	@param val Value to be set
	@return Returns if the function execution passed or failed.
*/
TI_AFE_API_COMP uint8_t AFE79FNP(set_agc_outputDgcPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chSel, uint16_t val)
{
	AFE79_ID_VALIDITY();
	chSel = AFE79FNP(afeRxFbChSelReMap)(afeInst, chSel);
	for (uint8_t chNo=0; chNo<AFE79_NUM_RX_CHANNELS + AFE79_NUM_FB_CHANNELS; chNo++)
	{
		if (((chSel >> chNo) & 1) == 1)
		{
			AFE79_CURR_SYSPARAM.rxAgcParams[chNo].outputDgcPinDelay=val;
		}
	}
	return TI_AFE_RET_EXEC_PASS;
}

/**
	@brief Get AFE Parameter outputDgcPinDelay
	@details Get AFE Parameter outputDgcPinDelay
	@param afeInst AFE Instance of AFE79_INST_TYPE type
	@param chNo Channel Number
	@param val Value Pointer return
	@return Returns if the function execution passed or failed.*/
TI_AFE_API_COMP uint8_t AFE79FNP(get_agc_outputDgcPinDelay)(AFE79_INST_TYPE afeInst, uint8_t chNo, uint16_t *val)
{
	AFE79_ID_VALIDITY();
	chNo = AFE79FNP(afeRxChNoReMap)(afeInst, chNo);
	*val=AFE79_CURR_SYSPARAM.rxAgcParams[chNo].outputDgcPinDelay;
	return TI_AFE_RET_EXEC_PASS;
}

