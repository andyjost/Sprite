#include <cassert>
#include <cstdlib>
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/state/rts.hpp"
#include <set>

extern "C"
{
  #include "mps.h"
  #include "mpsavm.h"
  #include "mpscamc.h"
}

// DEBUG
#include <iostream>

namespace cyrt
{
  char * node_alloc(size_t bytes)
  {
    gc::g_alloc_this_gen += bytes;
    return (char *) std::malloc(bytes);
  }

  void node_free(char * px)
    { std::free(px); }

  Arg const * pack(char * out, char const *format, Arg const * args)
  {
    RawNodeMemory mem{out};
    for(; *format; ++format)
    {
      switch(*format)
      {
        case 'p':
          *mem.boxed++ = *(Node **)(args++);
          break;
        case 'i':
          *mem.ub_int++ = *(unboxed_int_type*)(args++);
          break;
        case 'f':
          *mem.ub_float++ = *(unboxed_float_type*)(args++);
          break;
        case 'c':
          *mem.ub_char++ = *(unboxed_char_type*)(args++);
          break;
        case 'x':
          *mem.ub_ptr++ = *(unboxed_ptr_type*)(args++);
          break;
        default: assert(0);
      }
    }
    return args;
  }

  size_t packed_size(char const *format, size_t limit)
  {
    size_t size=0;
    for(size_t i=0; *format && i<limit; ++format, ++i)
    {
      switch(*format)
      {
        case 'p':
          size += sizeof(Node *);
          break;
        case 'i':
          size += sizeof(unboxed_int_type);
          break;
        case 'f':
          size += sizeof(unboxed_float_type);
          break;
        case 'c':
          size += sizeof(unboxed_char_type);
          break;
        case 'x':
          size += sizeof(unboxed_ptr_type);
          break;
        default: assert(0);
      }
    }
    return size;
  }
}

namespace cyrt { namespace gc
{
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

  static mps_arena_t arena;

  static std::set<RuntimeState *> g_rtslist;
  size_t g_alloc_this_gen = 0;

  void register_rts(RuntimeState * rts)
  {
    assert(rts);
    assert(g_rtslist.count(rts) == 0);
    g_rtslist.insert(rts);
  }

  void unregister_rts(RuntimeState * rts)
  {
    assert(rts);
    g_rtslist.erase(rts);
    assert(g_rtslist.count(rts) == 0);
  }

  void run_gc()
  {
    g_alloc_this_gen = 0;
  }

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
    mps_pool_t obj_pool;
    mps_root_t globals_root;

    MemoryManager()
    {
      return;
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

      MPS_ARGS_BEGIN(args)
      {
        MPS_ARGS_ADD(args, MPS_KEY_FORMAT, obj_fmt);
        res = mps_pool_create_k(&obj_pool, arena, mps_class_amc(), args);
      } MPS_ARGS_END(args);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't create obj pool");

      res = mps_root_create(&globals_root, arena, mps_rank_exact(), 0,
                            roots_scan, NULL, 0);
      if (res != MPS_RES_OK)
        throw std::runtime_error("couldn't register globals root");
    }
  } _memory;
}}

