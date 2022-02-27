#pragma once
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  bool equal(Cursor lhs, Cursor rhs, bool skipfwd);

  inline bool logically_equal(Cursor lhs, Cursor rhs)
    { return equal(lhs, rhs, true); }

  inline bool structurally_equal(Cursor lhs, Cursor rhs)
    { return equal(lhs, rhs, false); }
}
