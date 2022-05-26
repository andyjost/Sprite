#pragma once
#include <initializer_list>
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"

namespace cyrt
{
  Cursor subexpr(Node *, index_type);
  Cursor compress_fwd_chain(Cursor);
  Node ** compress_fwd_chain(Node **);
}
