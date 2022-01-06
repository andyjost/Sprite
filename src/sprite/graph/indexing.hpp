#pragma once
#include "sprite/graph/node.hpp"
#include "sprite/graph/raw.hpp"
#include <vector>

namespace sprite
{
  struct RealpathResult
  {
    Cursor                  target;
    std::vector<index_type> realpath;
    std::vector<sid_type>   guards;
  };

  Cursor compress_fwd_chain(Cursor);
  Node ** compress_fwd_chain(Node **);

  Cursor logical_subexpr(
      Node *, index_type const *, bool update_fwd_nodes=true
    );

  RealpathResult realpath(Node *, index_type const *, bool update_fwd_nodes=true);

  Cursor subexpr(Node *, index_type const *);
  Cursor subexpr(Cursor, index_type);
}
