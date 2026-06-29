/* Minimal Xilinx lwIP xadapter stub for Spec2Code QC (syntax/type check only). */
#ifndef NETIF_XADAPTER_H
#define NETIF_XADAPTER_H

#include "lwip/ip_addr.h"
#include "lwip/netif.h"

struct netif* xemac_add(struct netif* spNetif,
                        ip_addr_t* spIpAddr,
                        ip_addr_t* spNetmask,
                        ip_addr_t* spGateway,
                        unsigned char* ucpMacAddress,
                        unsigned int uiBaseAddress);
void xemacif_input(struct netif* spNetif);

#endif /* NETIF_XADAPTER_H */
