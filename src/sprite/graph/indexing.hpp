#pragma once
#include "sprite/graph/node.hpp"
#include "sprite/graph/raw.hpp"
#include <vector>

namespace sprite
{
  struct RealpathResult
  {
    Arg target;
    char kind;
    std::vector<index_type> realpath;
    std::vector<sid_type>   guards;
  };

  Node * compress_fwd_chain(Node *);

  Arg logical_subexpr(
      Node *, index_type const *, char * kind=nullptr, bool update_fwd_nodes=true
    );

  RealpathResult realpath(Node *, index_type const *, bool update_fwd_nodes=true);

  Arg subexpr(Node *, index_type const *, char * kind_out = nullptr);
  Arg subexpr(Node *, index_type, char * kind_out = nullptr);
}
