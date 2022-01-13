#pragma once
#include "sprite/graph/walk.hpp"
#include <utility>

namespace sprite
{
  struct CallStack
  {
    CallStack(Cursor root) : state(root) {}
    WalkState state;

    void reset(Cursor root) { this->state = WalkState(root); }
  };
}
