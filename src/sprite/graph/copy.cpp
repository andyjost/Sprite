#include <cstring>
#include "sprite/graph/copy.hpp"
#include "sprite/graph/raw.hpp"

namespace sprite
{
  Node * copynode(Node * node)
  {
    char * copy = node_alloc(node->info);
    std::memcpy(copy, node, node->info->alloc_size);
    return (Node *) copy;
  }

  namespace
  {
    Node * skip(Node * expr, bool skipfwd, sid_set_type * skipgrds)
    {
      NodeU u{expr};
      switch(expr->info->tag)
      {
        case T_FWD:
          if(skipfwd)
            return u.fwd->target;
          break;
        case T_SETGRD:
          if(skipgrds && skipgrds->count(u.setgrd->sid))
            return u.setgrd->value;
          break;
      }
      return nullptr;
    }
  }

  // Node * copygraph(
  //     Node * expr
  //   , memo_type * memo
  //   , bool skipfwd
  //   , sid_set_type * skipgrds
  //   )
  // {
  //   if(!memo)
  //   {
  //     memo_type memo_;
  //     return copygraph(expr, &memo_, skipfwd, skipgrds);
  //   }
  // }
}
