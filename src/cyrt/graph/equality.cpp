#include "cyrt/graph/equality.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/inspect.hpp"
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace
{
  using namespace cyrt;

  struct GraphEquality
  {
    bool skipfwd;
    // The memo is keyed by the addresses of the nodes: no node may move
    // while the comparison runs.
    GcClamp gc_clamp;
    std::unordered_map<void *, std::unordered_set<void *>> memo;

    using pending_type = std::vector<std::pair<Cursor, Cursor>>;

    GraphEquality(bool skipfwd) : skipfwd(skipfwd) {}

    // Compares two graphs.  The traversal keeps its own stack, so a deep
    // graph such as a long list cannot overflow the C stack.
    bool apply(Cursor lhs, Cursor rhs)
    {
      pending_type pending{{lhs, rhs}};
      while(!pending.empty())
      {
        auto [l, r] = pending.back();
        pending.pop_back();
        if(!this->visit(l, r, pending))
          return false;
      }
      return true;
    }

    // Compares one pair of nodes.  Equal compound nodes push their successor
    // pairs onto ``pending``; the leftmost pair goes on top.
    bool visit(Cursor lhs, Cursor rhs, pending_type & pending)
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
        // An unboxed pointer: the head of a partial application, or the set
        // of a set guard.
        case 'x':
          return lhs.arg->blob == rhs.arg->blob;
      }
      assert(lhs.kind == 'p');
      auto && bucket = p==memo.end() ? memo[lhs.id()] : p->second;
      bucket.insert(rhs.id());
      if(lhs->info != rhs->info)
        return false;
      for(index_type i=lhs->info->arity; i-->0;)
      {
        Cursor l = lhs->successor(i);
        Cursor r = rhs->successor(i);
        if(skipfwd)
        {
          l = inspect::fwd_chain_target(l);
          r = inspect::fwd_chain_target(r);
        }
        pending.emplace_back(l, r);
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
