#pragma once
#include <iosfwd>
#include "sprite/graph/node.hpp"

namespace sprite
{
  enum ShowStyle { SHOW_STR, SHOW_REPR };
  void show(std::ostream &, Cursor, ShowStyle);
}
