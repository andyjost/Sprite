#include "cyrt/graph/equality.hpp"
#include "cyrt/inspect.hpp"
#include <unordered_map>
#include <unordered_set>

namespace
{
  using namespace cyrt;

  struct GraphEquality
  {
    bool skipfwd;
    std::unordered_map<void *, std::unordered_set<void *>> memo;

    GraphEquality(bool skipfwd) : skipfwd(skipfwd) {}

    bool apply(Cursor lhs, Cursor rhs)
    {
      auto p = memo.find(lhs.id());
      if(p != memo.end() && p->second.find(rhs.id()) != p->second.end())
        return true;
      if(lhs.kind != rhs.kind)
        return false;
      switch(lhs.kind)
      {
        case 'i':
          return lhs.arg->ub_int == rhs.arg->ub_int;
        case 'f':
          return lhs.arg->ub_float == rhs.arg->ub_float;
        case 'c':
          return lhs.arg->ub_char == rhs.arg->ub_char;
      }
      assert(lhs.kind == 'p');
      auto && bucket = p==memo.end() ? memo[lhs.id()] : p->second;
      bucket.insert(rhs.id());
      if(lhs->info != rhs->info)
        return false;
      for(index_type i=0; i<lhs->info->arity; ++i)
      {
        Cursor l = lhs->successor(i);
        Cursor r = rhs->successor(i);
        if(skipfwd)
        {
          l = inspect::fwd_chain_target(l);
          r = inspect::fwd_chain_target(r);
        }
        if(!this->apply(l, r))
          return false;
      }
      return true;
    }
  };
}

namespace cyrt
{
  bool equal(Cursor lhs, Cursor rhs, bool skipfwd)
  {
    auto && equality = GraphEquality(skipfwd);
    return equality.apply(lhs, rhs);
  }
}
