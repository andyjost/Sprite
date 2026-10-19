#pragma once
#include <initializer_list>
#include "curryrt/graph/cursor.hpp"
#include "curryrt/graph/memory.hpp"

namespace curryrt
{
  Cursor subexpr(Node *, index_type);
  Cursor compress_fwd_chain(Cursor);
  Node ** compress_fwd_chain(Node **);
}
