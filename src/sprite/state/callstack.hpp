#pragma once
#include "sprite/graph/walk.hpp"
#include <utility>
#include <vector>

namespace sprite
{
  struct CallStack
  {
    CallStack(Cursor root) : search(root) {}

    Walk search;

    // size_t search_depth() const { return this->search.size(); }

    void reset(Cursor root)
    {
      this->search = Walk(root);
    }
  };
}
