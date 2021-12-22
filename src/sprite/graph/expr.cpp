#include <cassert>
#include "sprite/graph/expr.hpp"

namespace sprite
{
  union WriteHead
  {
    Node               * boxed;
    unboxed_int_type   * ub_int;
    unboxed_float_type * ub_float;
    unboxed_char_type  * ub_char;
    char               * pos;

    WriteHead(char * out) : pos(out) {}
  };

  void ** pack(char * out, char const *packing, void ** args)
  {
    WriteHead head = out;
    for(; *packing && *args; ++packing, ++args)
    {
      switch(*packing)
      {
        case 'p':
          *head.boxed = *(Node*)(*args);
          head.pos += sizeof(Node);
          break;
        case 'i':
          *head.ub_int = *(unboxed_int_type*)(*args);
          head.pos += sizeof(unboxed_int_type);
          break;
        case 'f':
          *head.ub_float = *(unboxed_float_type*)(*args);
          head.pos += sizeof(unboxed_float_type);
          break;
        case 'c':
          *head.ub_char = *(unboxed_char_type*)(*args);
          head.pos += sizeof(unboxed_char_type);
          break;
        default: assert(0);
      }
    }
    return args;
  }

  size_t packed_size(char const *packing, size_t limit)
  {
    size_t size=0;
    for(size_t i=0; *packing && i<limit; ++packing, ++i)
    {
      switch(*packing)
      {
        case 'p':
          size += sizeof(Node);
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
