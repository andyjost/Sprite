#pragma once
#include "sprite/fwd.hpp"
#include <cstdint>

namespace sprite
{
  using unboxed_int_type = int64_t;
  using unboxed_float_type = double;
  using unboxed_char_type = signed char;

  struct Expr
  {
    enum Type { BOXED, INT, FLOAT, CHAR };
    Type type;
    union
    {
      Node               p;
      unboxed_int_type   i;
      unboxed_float_type f;
      unboxed_char_type  c;
    };
  };

  // Pack arguments according to the format string.  Returns the position of
  // the first argument not processed.
  void ** pack(void *, char const *, void **);

  // Compute the number of bytes needed to hold the given packing string, up to
  // the specified number of arguments.
  size_t packed_size(char const *, size_t limit=NOLIMIT);
}
