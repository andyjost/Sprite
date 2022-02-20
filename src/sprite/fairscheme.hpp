#pragma once
#include "sprite/state/rts.hpp"
#include "sprite/graph/cursor.hpp"

namespace sprite
{
  inline Expr eval_next(RuntimeState * rts) { return rts->procD(); }
}
