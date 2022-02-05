#pragma once
#include <initializer_list>
#include "sprite/graph/cursor.hpp"
#include "sprite/graph/memory.hpp"
#include <vector>

namespace sprite
{
  struct RealpathResult
  {
    mutable Cursor          target;
    std::vector<index_type> realpath;
    std::vector<sid_type>   guards;
  };

  Cursor compress_fwd_chain(Cursor);
  Node ** compress_fwd_chain(Node **);

  Cursor logical_subexpr(
      Node *, index_type const *, bool update_fwd_nodes=true
    );

  RealpathResult realpath(Node *, std::initializer_list<index_type>, bool update_fwd_nodes=true);
  RealpathResult realpath(Node *, index_type const *, bool update_fwd_nodes=true);
  RealpathResult realpath(Node *, index_type, bool update_fwd_nodes=true);

  Cursor subexpr(Node *, index_type const *);
  Cursor subexpr(Cursor, index_type);
}
