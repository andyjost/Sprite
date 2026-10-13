#pragma once
// A helper of the scheduler (fairscheme.cpp) that the checker shares
// (checker.cpp).  This header is outside the include closure of
// cyrt/cyrt.hpp: the generated code never sees it.
#include "cyrt/builtins.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/node.hpp"

namespace cyrt
{
  // Rule N.1 at a constructor cell: tells whether a successor of ``cell``,
  // read through forward cells, is a failure, and puts its index into
  // ``index``.  The successors are read once, in order, and nothing is
  // written.  A partial application is a value: its arguments are not
  // read, as the scan does not enter them.  A null slot (a cyclic let
  // under construction) is no failure.
  inline bool failed_successor(Node * cell, index_type & index)
  {
    InfoTable const * info = cell->info;
    if(is_partial(*info))
      return false;
    Arg const * data = cell->successors();
    char const * format = info->format;
    for(index_type i = 0; i < info->arity; ++i)
    {
      if(format[i] != 'p')
        continue;
      Node * succ = data[i].node;
      while(succ && succ->info->tag == T_FWD)
        succ = NodeU{succ}.fwd->target;
      if(succ && succ->info->tag == T_FAIL)
      {
        index = i;
        return true;
      }
    }
    return false;
  }
}
