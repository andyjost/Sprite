#include "sprite/graph/indexing.hpp"
#include "sprite/state/scan.hpp"

namespace sprite
{
  void Scan::operator++()
  {
    while(true)
    {
      if(this->search.size() == this->callstack.back())
        return;
      switch(this->search.size())
      {
        case 1:  this->search.pop_back();
        case 0: return;
      }
      Level & parent = *(this->search.end() - 2);
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
      this->search.emplace_back(succ);
    }
    this->callstack.push_back(ret);
  }

  Node * Scan::copy_spine(
      Node * root, Node * end, Cursor * target, size_t start
    )
  {
    auto p = this->search.rbegin() + start;
    auto e = this->search.rend();
    assert(p<=e);
    for(; p!=e; ++p)
    {
      Node * tmp = copy_node(*p->cur);
      *tmp->successor(p->index) = end;
      if(target)
      {
        *target = tmp->successor(p->index);
        target = nullptr;
      }
      end = tmp;
      if(*p->cur == root)
        break;
    }
    return end;
  }
}
