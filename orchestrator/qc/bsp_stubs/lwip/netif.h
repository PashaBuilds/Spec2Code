/* Minimal lwIP netif stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_NETIF_H
#define LWIP_NETIF_H

struct netif
{
    int iUnused;
};

void netif_set_default(struct netif* spNetif);
void netif_set_up(struct netif* spNetif);

#endif /* LWIP_NETIF_H */
