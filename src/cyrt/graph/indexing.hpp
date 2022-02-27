#pragma once
#include <initializer_list>
#include "cyrt/graph/cursor.hpp"
#include "cyrt/graph/memory.hpp"
#include <vector>

namespace cyrt
{
  struct Variable
  {
    mutable Cursor          target;
    std::vector<index_type> realpath;
    std::vector<Set *>      guards;
  };

  Variable variable(Node *, index_type, bool update_fwd_nodes=true);

  // FIXME
  inline Node * rvalue(Variable const & var)
    { return var.target; }

  Cursor subexpr(Node *, index_type);

  Cursor compress_fwd_chain(Cursor);
  Node ** compress_fwd_chain(Node **);

}
