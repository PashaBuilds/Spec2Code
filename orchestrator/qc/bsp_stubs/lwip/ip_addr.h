/* Minimal lwIP IP address stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_IP_ADDR_H
#define LWIP_IP_ADDR_H

typedef struct
{
    unsigned int uiAddr;
} ip_addr_t;

#define IP4_ADDR(spIpAddr, ucA, ucB, ucC, ucD) \
    do \
    { \
        (spIpAddr)->uiAddr = (((unsigned int)(ucA) & 0xFFU) << 24U) | \
                             (((unsigned int)(ucB) & 0xFFU) << 16U) | \
                             (((unsigned int)(ucC) & 0xFFU) << 8U) | \
                             ((unsigned int)(ucD) & 0xFFU); \
    } while (0)

#define IP_ADDR_ANY ((const ip_addr_t*)0)

#endif /* LWIP_IP_ADDR_H */
