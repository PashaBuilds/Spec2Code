/* Host stub gerceklemeleri: gercek donanim YOK - veri-yolu cagrilari basarisiz doner
 * (sanal cihazlar spec2code_sim araya-girmesiyle cevaplanir). -include ile gelen
 * makrolar burada kaldirilir ki gercek adlar tanimlansin. */
#include "xil_types.h"
#include "xstatus.h"
#include "xiic_l.h"
#include "xspi.h"
#undef XIic_DynSend
#undef XIic_DynRecv
#undef XIic_Send
#undef XIic_Recv
#undef XSpi_SetSlaveSelect
#undef XSpi_Transfer
unsigned int g_uiStubGercekI2c = 0U; /* gercek hatta giden (sanal olmayan) I2C transfer sayisi */
unsigned int g_uiStubGercekSpi = 0U;
int XIic_DynInit(UINTPTR BaseAddress) { (void)BaseAddress; return XST_SUCCESS; }
u32 XIic_WaitBusFree(UINTPTR BaseAddress) { (void)BaseAddress; return 0U; }
unsigned XIic_DynSend(UINTPTR b, u16 a, u8* p, u8 n, u8 o) { (void)b; (void)a; (void)p; (void)n; (void)o; g_uiStubGercekI2c++; return 0U; }
unsigned XIic_DynRecv(UINTPTR b, u8 a, u8* p, u8 n) { (void)b; (void)a; (void)p; (void)n; g_uiStubGercekI2c++; return 0U; }
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
