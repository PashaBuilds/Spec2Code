/* Minimal Xilinx BSP stub for Spec2Code QC. Real device IDs come from the user's BSP. */
#ifndef XPARAMETERS_H
#define XPARAMETERS_H
#define XPAR_XIICPS_0_DEVICE_ID 0
#define XPAR_XIICPS_1_DEVICE_ID 1
#define XPAR_XSPIPS_0_DEVICE_ID 0
#define XPAR_XQSPIPS_0_DEVICE_ID 0
#define XPAR_XQSPIPSU_0_DEVICE_ID 0
#define XPAR_XQSPIPSU_0_BASEADDR 0xFF0F0000U
#define XPAR_XGPIOPS_0_DEVICE_ID 0
#define XPAR_XEMACPS_0_DEVICE_ID 0
#define XPAR_XEMACPS_0_BASEADDR 0xFF0B0000U
#define XPAR_XEMACPS_1_DEVICE_ID 1
#define XPAR_XEMACPS_1_BASEADDR 0xFF0C0000U
#define XPAR_XEMACPS_2_DEVICE_ID 2
#define XPAR_XEMACPS_2_BASEADDR 0xFF0D0000U
#define XPAR_XEMACPS_3_DEVICE_ID 3
#define XPAR_XEMACPS_3_BASEADDR 0xFF0E0000U

/* Proje ozel ek: QC dongusu uretilen koddaki XPAR_<ornek>_{DEVICE_ID,BASEADDR,
 * HIGHADDR} adlarini toplar ve bu dosyayi gecici include klasorune yazar
 * (XSA'dan gelen XPAR_PSU_I2C_0, PS7_*, AXI_IIC_0, MDM_0 ... sonsuz adlandirma
 * semasi burada sabit listeyle tutulamaz). */
#if defined(__has_include)
#if __has_include("spec2code_qc_xparameters.h")
#include "spec2code_qc_xparameters.h"
#endif
#endif

#endif /* XPARAMETERS_H */
