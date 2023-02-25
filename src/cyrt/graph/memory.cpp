#include <cassert>
#include <cstdlib>
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/state/rts.hpp"
#include <set>

namespace cyrt
{
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

  static std::set<RuntimeState *> g_rtslist;
  bool g_gc_collect = false;

  void gc_register_rts(RuntimeState * rts)
  {
    assert(rts);
    assert(g_rtslist.count(rts) == 0);
    g_rtslist.insert(rts);
  }

  void gc_unregister_rts(RuntimeState * rts)
  {
    assert(rts);
    g_rtslist.erase(rts);
    assert(g_rtslist.count(rts) == 0);
  }
}

// Select one of these.  It should define cyrt::node_reserve and
// cyrt::node_commit.
// #include "cyrt/graph/gc/mps.cpp"
// #include "cyrt/graph/gc/leaky.cpp"
#include "cyrt/graph/gc/wdgc.cpp"

