#include <cassert>
#include <cstdlib>
#include "sprite/graph/raw.hpp"

namespace sprite
{
  char * node_alloc(InfoTable const * info)
  {
    assert(info);
    return (char *) std::malloc(info->alloc_size);
  }

  void node_free(char * px)
  {
    std::free(px);
  }

  Arg * pack(char * out, char const *format, Arg * args)
  {
    RawNodeMemory raw{out};
    for(; *format; ++format)
    {
      switch(*format)
      {
        case 'p':
          *raw.boxed++ = *(Node **)(args++);
          break;
        case 'i':
          *raw.ub_int++ = *(unboxed_int_type*)(args++);
          break;
        case 'f':
          *raw.ub_float++ = *(unboxed_float_type*)(args++);
          break;
        case 'c':
          *raw.ub_char++ = *(unboxed_char_type*)(args++);
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
        default: assert(0);
      }
    }
    return size;
  }
}
