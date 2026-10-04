#pragma once
#include "cyrt/graph/cursor.hpp"
#include <set>

namespace cyrt
{
  enum SkipOpt : bool { SKIPFWD = true, NOSKIPFWD = false };

  Expr copy_node(Cursor);
  Node * copy_node(Node *);

  // ``freevars``, when given, takes up the number of free variables copied.
  Expr copy_graph(
      Cursor
    , SkipOpt     skipfwd  = NOSKIPFWD
    , Set *       skipgrd  = nullptr
    , memo_type *          = nullptr
    , size_t *    freevars = nullptr
    );
}
