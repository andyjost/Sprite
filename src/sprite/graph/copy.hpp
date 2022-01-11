#pragma once
#include "sprite/graph/cursor.hpp"
#include <set>

namespace sprite
{
  Arg copynode(Cursor);

  Arg copygraph(
      Cursor
    , memo_type * = nullptr
    , bool skipfwd=false
    , sid_set_type * skipgrds = nullptr
    );
}
