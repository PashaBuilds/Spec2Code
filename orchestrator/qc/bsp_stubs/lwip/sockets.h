/* Minimal lwIP BSD socket API stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_SOCKETS_H
#define LWIP_SOCKETS_H

#include <stddef.h>

#define AF_INET 2
#define SOCK_STREAM 1
#define IPPROTO_TCP 6
#define SOL_SOCKET 0xFFF
#define SO_REUSEADDR 0x0004
#define SO_KEEPALIVE 0x0008
#define INADDR_ANY 0U
#define MSG_DONTWAIT 0x08

typedef unsigned int socklen_t;
typedef unsigned char sa_family_t;
typedef unsigned short in_port_t;
typedef unsigned int in_addr_t;

struct in_addr
{
    in_addr_t s_addr;
};

struct sockaddr_in
{
    unsigned char sin_len;
    sa_family_t sin_family;
    in_port_t sin_port;
    struct in_addr sin_addr;
    char sin_zero[8];
};

struct sockaddr
{
    unsigned char sa_len;
    sa_family_t sa_family;
    char sa_data[14];
};

unsigned short lwip_htons(unsigned short usValue);
unsigned int lwip_htonl(unsigned int uiValue);
#define htons(x) lwip_htons(x)
#define htonl(x) lwip_htonl(x)
#define ntohs(x) lwip_htons(x)
#define ntohl(x) lwip_htonl(x)

int lwip_socket(int iDomain, int iType, int iProtocol);
int lwip_bind(int iSocket, const struct sockaddr* spName, socklen_t uiNameLength);
int lwip_listen(int iSocket, int iBacklog);
int lwip_accept(int iSocket, struct sockaddr* spAddress, socklen_t* upAddressLength);
int lwip_recv(int iSocket, void* vpBuffer, size_t uiLength, int iFlags);
int lwip_send(int iSocket, const void* vpData, size_t uiSize, int iFlags);
int lwip_close(int iSocket);
int lwip_setsockopt(int iSocket, int iLevel, int iOptionName, const void* vpOptionValue, socklen_t uiOptionLength);

#define socket(a, b, c) lwip_socket(a, b, c)
#define bind(a, b, c) lwip_bind(a, b, c)
#define listen(a, b) lwip_listen(a, b)
#define accept(a, b, c) lwip_accept(a, b, c)
#define recv(a, b, c, d) lwip_recv(a, b, c, d)
#define send(a, b, c, d) lwip_send(a, b, c, d)
#define closesocket(s) lwip_close(s)
#define setsockopt(a, b, c, d, e) lwip_setsockopt(a, b, c, d, e)

#endif /* LWIP_SOCKETS_H */
