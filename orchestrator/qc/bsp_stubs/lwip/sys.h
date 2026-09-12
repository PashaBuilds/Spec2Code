/* Minimal lwIP sys (OS abstraction) stub for Spec2Code QC (syntax/type check only). */
#ifndef LWIP_SYS_H
#define LWIP_SYS_H

typedef void (*lwip_thread_fn)(void* vpArg);

typedef struct
{
    int iUnused;
} sys_thread_t;

sys_thread_t sys_thread_new(const char* cpName, lwip_thread_fn fpThread, void* vpArg, int iStackSize, int iPriority);
#ifndef LWIP_U32_T_DEFINED
#define LWIP_U32_T_DEFINED
typedef unsigned int u32_t;
#endif
u32_t sys_now(void);

/* Kritik bolge makrolari (OS portunda kesme/mutex kilidi). */
typedef unsigned int sys_prot_t;
sys_prot_t sys_arch_protect(void);
void sys_arch_unprotect(sys_prot_t uiLevel);
#define SYS_ARCH_DECL_PROTECT(lev) sys_prot_t lev
#define SYS_ARCH_PROTECT(lev) (lev) = sys_arch_protect()
#define SYS_ARCH_UNPROTECT(lev) sys_arch_unprotect(lev)

#endif /* LWIP_SYS_H */
