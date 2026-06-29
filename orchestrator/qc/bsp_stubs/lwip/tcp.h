/* Minimal lwIP TCP raw API stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_TCP_H
#define LWIP_TCP_H

#include "lwip/err.h"
#include "lwip/ip_addr.h"
#include "lwip/pbuf.h"

#define TCP_WRITE_FLAG_COPY 0x01U

struct tcp_pcb
{
    int iUnused;
};

struct tcp_pcb* tcp_new(void);
err_t tcp_bind(struct tcp_pcb* spPcb, const ip_addr_t* spIpAddr, unsigned short usPort);
struct tcp_pcb* tcp_listen(struct tcp_pcb* spPcb);
void tcp_accept(struct tcp_pcb* spPcb,
                err_t (*fpAccept)(void* vpArg, struct tcp_pcb* spNewPcb, err_t enErr));
void tcp_arg(struct tcp_pcb* spPcb, void* vpArg);
void tcp_recv(struct tcp_pcb* spPcb,
              err_t (*fpRecv)(void* vpArg, struct tcp_pcb* spPcb, struct pbuf* spPbuf, err_t enErr));
void tcp_err(struct tcp_pcb* spPcb, void (*fpErr)(void* vpArg, err_t enErr));
err_t tcp_write(struct tcp_pcb* spPcb, const void* vpData, unsigned short usLength, unsigned char ucFlags);
err_t tcp_output(struct tcp_pcb* spPcb);
void tcp_recved(struct tcp_pcb* spPcb, unsigned short usLength);
err_t tcp_close(struct tcp_pcb* spPcb);
void tcp_abort(struct tcp_pcb* spPcb);

#endif /* LWIP_TCP_H */
