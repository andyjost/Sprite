#pragma once
#include "sprite/graph/node.hpp"
#include <set>

namespace sprite
{

  Node * copynode(Node *);
  Node * copygraph(
      Node *
    , memo_type * = nullptr
    , bool skipfwd=false
    , sid_set_type * skipgrds = nullptr
    );
}
