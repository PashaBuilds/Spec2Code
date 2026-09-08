/* Host stub gerceklemeleri: gercek donanim YOK - veri-yolu cagrilari basarisiz doner
 * (sanal cihazlar spec2code_sim araya-girmesiyle cevaplanir). -include ile gelen
 * makrolar burada kaldirilir ki gercek adlar tanimlansin. */
#include "xil_types.h"
#include "xstatus.h"
#include "xiic.h"
#include "xspi.h"
#undef XIic_DynSend
#undef XIic_DynRecv
#undef XIic_Send
#undef XIic_Recv
#undef XSpi_SetSlaveSelect
#undef XSpi_Transfer
unsigned int g_uiStubGercekI2c = 0U; /* gercek hatta giden (sanal olmayan) I2C transfer sayisi */
unsigned int g_uiStubGercekSpi = 0U;
static XIic_Config S_sIicConfig = { 0U, 0x40800000UL, 0, 0U };
XIic_Config* XIic_LookupConfig(u16 DeviceId) { (void)DeviceId; return &S_sIicConfig; }
int XIic_CfgInitialize(XIic* i, XIic_Config* c, UINTPTR e) { i->BaseAddress = e; i->IsReady = XIL_COMPONENT_IS_READY; (void)c; return XST_SUCCESS; }
int XIic_DynInit(UINTPTR BaseAddress) { (void)BaseAddress; return XST_SUCCESS; }
u32 XIic_WaitBusFree(UINTPTR BaseAddress) { (void)BaseAddress; return 0U; }
unsigned int g_uiStubI2cAckAddress = 0xFFFFU; /* i2c_search probu: yalniz bu adres ACK (bayt sayisi 1) */
unsigned XIic_DynSend(UINTPTR b, u16 a, u8* p, u8 n, u8 o) { (void)b; (void)p; (void)o; g_uiStubGercekI2c++; return ((unsigned int)a == g_uiStubI2cAckAddress) ? (unsigned)n : 0U; }
unsigned XIic_DynRecv(UINTPTR b, u8 a, u8* p, u8 n) { u8 i; (void)b; g_uiStubGercekI2c++; if ((unsigned int)a != g_uiStubI2cAckAddress) { return 0U; } for (i = 0U; i < n; i++) { p[i] = (u8)(0xA0U + i); } return (unsigned)n; }
unsigned XIic_Send(UINTPTR b, u8 a, u8* p, unsigned n, u8 o) { (void)b; (void)a; (void)p; (void)n; (void)o; g_uiStubGercekI2c++; return 0U; }
unsigned XIic_Recv(UINTPTR b, u8 a, u8* p, unsigned n, u8 o) { (void)b; (void)a; (void)p; (void)n; (void)o; g_uiStubGercekI2c++; return 0U; }
static XSpi_Config S_sSpiConfig = { 0U, 0x44A00000UL };
XSpi_Config* XSpi_LookupConfig(u16 DeviceId) { (void)DeviceId; return &S_sSpiConfig; }
int XSpi_CfgInitialize(XSpi* i, XSpi_Config* c, UINTPTR e) { i->IsReady = XIL_COMPONENT_IS_READY; i->BaseAddr = e; (void)c; return XST_SUCCESS; }
int XSpi_SetOptions(XSpi* i, u32 o) { (void)i; (void)o; return XST_SUCCESS; }
int XSpi_Start(XSpi* i) { (void)i; return XST_SUCCESS; }
void XSpi_IntrGlobalDisable(XSpi* i) { (void)i; }
int XSpi_SetSlaveSelect(XSpi* i, u32 m) { i->SlaveSelectReg = m; return XST_SUCCESS; }
int XSpi_Transfer(XSpi* i, u8* t, u8* r, unsigned int n) { (void)i; (void)t; (void)r; (void)n; g_uiStubGercekSpi++; return XST_FAILURE; }

/* --- Konsol UART (xuartlite_l.h): test girdisi tampondan, cikti stdout'a ------------- */
#include "xuartlite_l.h"
#include <stdio.h>
const unsigned char* g_ucpStubUartIn = (const unsigned char*)0; /* test tarafinca atanir */
unsigned int g_uiStubUartInLen = 0U;
unsigned int g_uiStubUartInPos = 0U;
u32 XUartLite_IsReceiveEmpty(UINTPTR BaseAddress) { (void)BaseAddress; return (g_uiStubUartInPos < g_uiStubUartInLen) ? 0U : 1U; }
u8 XUartLite_RecvByte(UINTPTR BaseAddress) { (void)BaseAddress; return (g_uiStubUartInPos < g_uiStubUartInLen) ? g_ucpStubUartIn[g_uiStubUartInPos++] : 0U; }
void XUartLite_SendByte(UINTPTR BaseAddress, u8 Data) { (void)BaseAddress; (void)putchar((int)Data); }

/* --- xil_io.h: register erisimi (shell mod komutu testi) ------------------------------ */
#include "xil_io.h"
u32 g_uiStubLastOutAddr = 0U;
u32 g_uiStubLastOutValue = 0U;
void Xil_Out32(UINTPTR Addr, u32 Value) { g_uiStubLastOutAddr = (u32)Addr; g_uiStubLastOutValue = Value; printf("XIL_OUT32 0x%08X <= 0x%08X\n", (unsigned int)Addr, (unsigned int)Value); }
u32 Xil_In32(UINTPTR Addr) { (void)Addr; return 0U; }
