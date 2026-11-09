#pragma once
#include "curryrt/graph/node.hpp"

namespace curryrt
{
  bool equal(Cursor lhs, Cursor rhs, bool skipfwd);
  // Forward-transparent equality that also preserves node sharing.
  bool graph_equal(Cursor lhs, Cursor rhs);

  inline bool logically_equal(Cursor lhs, Cursor rhs)
    { return equal(lhs, rhs, true); }

  inline bool structurally_equal(Cursor lhs, Cursor rhs)
    { return equal(lhs, rhs, false); }
}
