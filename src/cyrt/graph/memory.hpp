#pragma once
#include "cyrt/fwd.hpp"

namespace cyrt
{
  char * node_alloc(size_t bytes);
  void node_free(char *);

  namespace gc
  {
    extern size_t g_alloc_this_gen;
    void register_rts(RuntimeState *);
    void unregister_rts(RuntimeState *);
    void run_gc();
  }

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
