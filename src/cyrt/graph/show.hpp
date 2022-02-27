#pragma once
#include <iosfwd>
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  enum ShowStyle { SHOW_STR, SHOW_REPR };
  void show(std::ostream &, Cursor, ShowStyle);
}
