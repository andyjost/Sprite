#pragma once
#include "cyrt/fwd.hpp"

namespace cyrt
{
  Node * node_reserve(size_t bytes);
  bool node_commit(void *, size_t bytes);

  extern bool g_gc_collect;
  void gc_register_rts(RuntimeState *);
  void gc_unregister_rts(RuntimeState *);
  void run_gc();

  union RawNodeMemory
  {
    InfoTable const   ** info;
    Node              ** boxed;
    unboxed_int_type   * ub_int;
    unboxed_float_type * ub_float;
    unboxed_char_type  * ub_char;
    void              ** ub_ptr;
    char               * pos;

    RawNodeMemory(Node * mem) : pos((char *) mem) {}
    RawNodeMemory(char * mem) : pos(mem) {}
    operator char*() const { return pos; }
  };

  // Pack arguments according to the format string.  Returns the position of
  // the first argument not processed.
  Arg const * pack(char * out, char const * format, Arg const * args);

  // Compute the number of bytes needed to hold the given format string, up to
  // the specified number of arguments.
  size_t packed_size(char const * format, size_t limit=NOLIMIT);
}
