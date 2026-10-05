#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  // The owner of the slot is not known here: the counter of writes into
  // old nodes gets the address (see gc_count_slot_write).
  Cursor compress_fwd_chain(Cursor cur)
  {
    if(cur.kind == 'p')
    {
      gc_count_slot_write(cur.arg);
      *cur = *compress_fwd_chain(&cur.arg->node);
    }
    return cur;
  }

  Node ** compress_fwd_chain(Node ** begin)
  {
    Node * end = *begin;
    while(end->info->tag == T_FWD)
      end = NodeU{end}.fwd->target;
    while(*begin != end)
    {
      gc_count_write(*begin);
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
