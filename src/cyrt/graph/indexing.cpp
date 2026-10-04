#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  Cursor compress_fwd_chain(Cursor cur)
  {
    if(cur.kind == 'p')
      *cur = *compress_fwd_chain(&cur.arg->node);
    return cur;
  }

  Node ** compress_fwd_chain(Node ** begin)
  {
    Node * end = *begin;
    while(end->info->tag == T_FWD)
      end = NodeU{end}.fwd->target;
    while(*begin != end)
    {
      NodeU u{*begin};
      Node ** next = &u.fwd->target;
      u.fwd->target = end;
      begin = next;
    }
    return begin;
  }

  Cursor subexpr(Node * root, index_type i)
    { return root->successor(i); }
}
