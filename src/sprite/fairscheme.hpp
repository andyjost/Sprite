#pragma once
#include "sprite/state/rts.hpp"
#include "sprite/graph/cursor.hpp"

namespace sprite
{
  struct FairSchemeAlgo
  {
    FairSchemeAlgo(RuntimeState * rts)
      : rts(rts)
    {}

    RuntimeState * rts;

    Expr eval();
  };
}
