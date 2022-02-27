#pragma once
#include "cyrt/graph/cursor.hpp"
#include <set>

namespace cyrt
{
  enum SkipOpt : bool { SKIPFWD = true, NOSKIPFWD = false };

  Expr copy_node(Cursor);
  Node * copy_node(Node *);

  Expr copy_graph(
      Cursor
    , SkipOpt     skipfwd = NOSKIPFWD
    , Set *       skipgrd = nullptr
    , memo_type *         = nullptr
    );
}
