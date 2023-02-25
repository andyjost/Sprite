// Integration of the MPS garbage collector.

extern "C"
{
  #include "mps.h"
  #include "mpsavm.h"
  #include "mpscamc.h"
}

#define ALIGNMENT sizeof(mps_word_t)

/* Align size upwards to the next multiple of the word size. */
#define ALIGN_WORD(size) \
  (((size) + ALIGNMENT - 1) & ~(ALIGNMENT - 1))

/* Align size upwards to the next multiple of the word size, and
 * additionally ensure that it's big enough to store a forwarding
 * pointer. Evaluates its argument twice. */
#define ALIGN_OBJ(size)                                \
  (ALIGN_WORD(size) >= ALIGN_WORD(sizeof(FwdSzNode))   \
   ? ALIGN_WORD(size)                                  \
   : ALIGN_WORD(sizeof(FwdSzNode)))

#define FIX(ref)                                                        \
    do {                                                                \
        mps_addr_t _addr = (ref); /* copy to local to avoid type pun */ \
        mps_res_t res = MPS_FIX12(ss, &_addr);                          \
        if (res != MPS_RES_OK) return res;                              \
        (ref) = (Node *) _addr;                                         \
    } while (0)

#define LENGTH(array)   (sizeof(array) / sizeof(array[0]))


namespace cyrt
{
  static mps_arena_t arena;

  // FIXME -- this cause frequent collection!!
  static mps_gen_param_s obj_gen_params[] = {
    { 150, 0.85 },
    { 170, 0.45 }
  };

  static mps_res_t obj_scan(mps_ss_t ss, mps_addr_t base, mps_addr_t limit)
  {
    MPS_SCAN_BEGIN(ss)
    {
      while (base < limit)
      {
        Node * obj = (Node *) base;
        switch(obj->info->tag)
        {
          case T_FWD:
            if(obj->info == &FwdSz_Info)
              base = (char *)base + ALIGN_OBJ(NodeU{obj}.fwdsz->bytes);
            else
              base = (char *)base + ALIGN_OBJ(sizeof(FwdNode));
            break;
          case T_PAD:
            if(obj->info == &PadSz_Info)
              base = (char *)base + ALIGN_OBJ(NodeU{obj}.padsz->bytes);
            else
              base = (char *)base + ALIGN_OBJ(sizeof(PadNode));
            break;
          default:
          {
            auto data = obj->begin();
            for(index_type i=0, e=obj->size(); i<e; ++i)
            {
              if(obj->info->format[i] == 'p')
              {
                FIX(data[i].node);
              }
            }
          }
        }
      }
    } MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static mps_addr_t obj_skip(mps_addr_t base)
  {
    Node * obj = (Node *) base;
    switch(obj->info->tag)
    {
      case T_FWD:
        if(obj->info == &FwdSz_Info)
          base = (char *)base + ALIGN_OBJ(NodeU{obj}.fwdsz->bytes);
        else
          base = (char *)base + ALIGN_OBJ(sizeof(FwdNode));
        break;
      case T_PAD:
        if(obj->info == &PadSz_Info)
          base = (char *)base + ALIGN_OBJ(NodeU{obj}.padsz->bytes);
        else
          base = (char *)base + ALIGN_OBJ(sizeof(PadNode));
        break;
      default:
        base = (char *)base + ALIGN_OBJ(obj->info->alloc_size);
    }
    return base;
  }

  static void obj_fwd(mps_addr_t old, mps_addr_t new_)
  {
    Node * obj = (Node *) old;
    mps_addr_t limit = obj_skip(old);
    size_t size = (char *)limit - (char *)old;
    assert(size >= ALIGN_WORD(sizeof(FwdNode)));
    if (size == ALIGN_WORD(sizeof(FwdNode)))
    {
      obj->info = &Fwd_Info;
      NodeU{obj}.fwd->target = (Node *) new_;
    }
    else
    {
      obj->info = &FwdSz_Info;
      NodeU{obj}.fwdsz->target = (Node *) new_;
      NodeU{obj}.fwdsz->bytes = size;
    }
  }

  static mps_addr_t obj_isfwd(mps_addr_t addr)
  {
    Node * obj = (Node *) addr;
    switch(obj->info->tag)
    {
      case T_FWD:
        return NodeU{obj}.fwd->target;
    }
    return nullptr;
  }

  static void obj_pad(mps_addr_t addr, size_t size)
  {
    Node * obj = (Node *) addr;
    assert(size >= ALIGN_OBJ(sizeof(PadNode)));
    if (size == ALIGN_OBJ(sizeof(PadNode)))
    {
      obj->info = &Pad_Info;
    }
    else
    {
      obj->info = &PadSz_Info;
      NodeU{obj}.padsz->bytes = size;
    }
  }

  static mps_res_t roots_scan(mps_ss_t ss, void *p, size_t s)
  {
    MPS_SCAN_BEGIN(ss)
    {
      for(auto * rts: g_rtslist)
      {
        for(auto * Q: rts->qstack)
        {
          for(auto * C: *Q)
          {
            FIX(C->root_storage);
            for(auto & pair: *C->bindings)
              FIX(pair.second);
          }
        }
      }
    }
    MPS_SCAN_END(ss);
    return MPS_RES_OK;
  }

  static struct MemoryManager
  {
    mps_fmt_t obj_fmt;
    mps_chain_t obj_chain;
    mps_pool_t obj_pool;
    mps_root_t sprite_roots;
    mps_thr_t thread;
    mps_root_t stack_root;
    mps_ap_t obj_ap;

    MemoryManager()
    {
      mps_res_t res;
      MPS_ARGS_BEGIN(args)
      {
        MPS_ARGS_ADD(args, MPS_KEY_ARENA_SIZE, 32 * 1024 * 1024);
        res = mps_arena_create_k(&arena, mps_arena_class_vm(), args);
      } MPS_ARGS_END(args);
      if(res != MPS_RES_OK)
        throw std::runtime_error("couldn't create arena");

      MPS_ARGS_BEGIN(args)
      {
        MPS_ARGS_ADD(args, MPS_KEY_FMT_ALIGN, ALIGNMENT);
        MPS_ARGS_ADD(args, MPS_KEY_FMT_SCAN, obj_scan);
        MPS_ARGS_ADD(args, MPS_KEY_FMT_SKIP, obj_skip);
        MPS_ARGS_ADD(args, MPS_KEY_FMT_FWD, obj_fwd);
        MPS_ARGS_ADD(args, MPS_KEY_FMT_ISFWD, obj_isfwd);
        MPS_ARGS_ADD(args, MPS_KEY_FMT_PAD, obj_pad);
        res = mps_fmt_create_k(&obj_fmt, arena, args);
      } MPS_ARGS_END(args);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't create obj format");

      res = mps_chain_create(&obj_chain,
                             arena,
                             LENGTH(obj_gen_params),
                             obj_gen_params);
      if (res != MPS_RES_OK)
        throw std::runtime_error("Couldn't create obj chain");


      MPS_ARGS_BEGIN(args)
      {
        MPS_ARGS_ADD(args, MPS_KEY_FORMAT, obj_fmt);
        res = mps_pool_create_k(&obj_pool, arena, mps_class_amc(), args);
      } MPS_ARGS_END(args);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't create obj pool");

      res = mps_root_create(&sprite_roots, arena, mps_rank_exact(), 0,
                            roots_scan, NULL, 0);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't register Sprite roots");

      res = mps_thread_reg(&thread, arena);
      if (res != MPS_RES_OK) 
        throw std::runtime_error("couldn't register thread");
      
      // FIXME -- This frame does not stay on the stack.  How to get a safe cold end?
      void *marker = &marker;
      // union XXX
      // {
      //   size_t i;
      //   void * p;
      // } xxx{0x800000000000};
      // void *marker = xxx.p;
      // std::cout << "COOL END = " << marker << std::endl;
      res = mps_root_create_thread(&stack_root, arena, thread, marker);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't create stack root");


      res = mps_ap_create_k(&obj_ap, obj_pool, mps_args_none);
      if (res != MPS_RES_OK) 
        throw std::runtime_error("couldn't create obj allocation point");
    }

    ~MemoryManager()
    {
      mps_arena_park(arena);
      mps_ap_destroy(obj_ap);
      mps_root_destroy(stack_root);
      mps_thread_dereg(thread);
      mps_root_destroy(sprite_roots);
      mps_pool_destroy(obj_pool);
      mps_chain_destroy(obj_chain);
      mps_fmt_destroy(obj_fmt);
      mps_arena_destroy(arena);
    }
  } g_mps;

  void run_gc() {}

  Node * node_reserve(size_t bytes)
  {
    mps_addr_t addr;
    bytes = ALIGN_OBJ(bytes);
    mps_res_t res = mps_reserve(&addr, g_mps.obj_ap, bytes);
    if (res != MPS_RES_OK)
      throw std::runtime_error("out of memory in node_reserve");
    return (Node *) addr;
  }

  bool node_commit(void * addr, size_t bytes)
  {
    bytes = ALIGN_OBJ(bytes);
    return mps_commit(g_mps.obj_ap, addr, bytes);
  }
}
