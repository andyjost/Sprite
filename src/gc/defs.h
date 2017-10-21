#define PTRSZ (sizeof(void*))
#define MPSFWDBIT 1 // Used to fwd during GC.
#define CYFWDBIT 2 // Used to fwd normally.
#define FLAGMASK 0xffff000000000003
static_assert(sizeof(size_t) == sizeof(void*), "");
#define HASBIT(p,bit) ((((size_t)(p))&(bit)))
#define SETBIT(p,bit) ((typeof(p))(((size_t)(p))|(bit)))
#define CLEARBIT(p,bit) ((typeof(p))(((size_t)(p))&~(bit)))
#define CLEARFLAGS(p) CLEARBIT(p, FLAGMASK)
#define SKIPFWD(obj)                                \
    do                                              \
    {                                               \
      while(HASBIT(obj->info, FLAGMASK))            \
        obj = (heapobj_t *)(CLEARFLAGS(obj->info)); \
      assert(is_ordinary(obj));                     \
    } while(0)                                      \
  /**/
#define FIX(ref)                            \
    do                                      \
    {                                       \
      mps_addr_t addr = (ref);              \
      mps_res_t res = MPS_FIX12(ss, &addr); \
      if(res != MPS_RES_OK) return res;     \
      (ref) = (heapobj_t*)(addr);           \
    } while(0)                              \
  /**/
#define PAD1 (-5)
#define PAD (-4)


