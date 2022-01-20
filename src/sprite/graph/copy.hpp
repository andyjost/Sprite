#pragma once
#include "sprite/graph/cursor.hpp"
#include <set>

namespace sprite
{
  enum SkipOpt : bool { SKIPFWD = true, NOSKIPFWD = false };

  Expr copy_node(Cursor);
  Node * copy_node(Node *);

  Expr copy_graph(
      Cursor
    , SkipOpt           skipfwd = NOSKIPFWD
    , sid_type const *  skipgrd = nullptr
    , memo_type *               = nullptr
    );
}
