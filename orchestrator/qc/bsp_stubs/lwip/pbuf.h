/* Minimal lwIP pbuf stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_PBUF_H
#define LWIP_PBUF_H

struct pbuf
{
    struct pbuf* next;
    void* payload;
    unsigned short len;
    unsigned short tot_len;
};

unsigned char pbuf_free(struct pbuf* spPbuf);

#endif /* LWIP_PBUF_H */
