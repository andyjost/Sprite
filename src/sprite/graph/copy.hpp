#pragma once
#include "sprite/graph/cursor.hpp"
#include <set>

namespace sprite
{
  enum SkipOpt : bool { SKIPFWD = true, NOSKIPFWD = false };

  Expr copynode(Cursor);

  Expr copygraph(
      Cursor
    , SkipOpt           skipfwd = NOSKIPFWD
    , sid_type const *  skipgrd = nullptr
    , memo_type *               = nullptr
    );
}
