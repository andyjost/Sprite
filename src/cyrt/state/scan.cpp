#include "cyrt/graph/indexing.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/state/scan.hpp"

namespace cyrt
{
  void Scan::operator++()
  {
    while(true)
    {
      if(this->search.size() == this->callstack.back())
        return;
      switch(this->search.size())
      {
        case 1: this->search.pop_back();
        case 0: return;
      }
      Level & parent = this->search[this->search.size() - 2];
      ++parent.index;
      if(parent.index >= parent.end)
        this->search.pop_back();
      else
      {
        this->search.back().cur = parent.cur->successor(parent.index);
        return;
      }
    }
  }

  void Scan::push(Variable const * inductive)
  {
    size_t ret = this->search.size();
    for(auto pos: inductive->realpath)
    {
      Level & parent = this->search.back();
      parent.index = pos;
      parent.end = pos + 1;
      Cursor succ = parent.cur->successor(pos);
      this->search.push_back(Level(succ));
    }
    this->callstack.push_back(ret);
  }

  Node * Scan::copy_spine(
      Node * root, Node * end, xid_type cid, Cursor * target, size_t start
    )
  {
    // From the level ``start`` below the deepest one up to the root.
    size_t const n = this->search.size();
    assert(start <= n);
    for(size_t i = n - start; i-- > 0;)
    {
      Level & level = this->search[i];
      if(cid != NOXID && level.cur.kind == 'p' && level.cur->info->tag == T_SETGRD)
        NodeU{level.cur}.setgrd->set->escape_set.insert(cid);
      Node * tmp = copy_node(*level.cur);
      *tmp->successor(level.index) = end;
      if(target)
      {
        *target = tmp->successor(level.index);
        target = nullptr;
      }
      end = tmp;
      if(*level.cur == root)
        break;
    }
    return end;
  }
}
