#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  void Walk::operator++()
  {
    while(true)
    {
      switch(this->stack.size())
      {
        case 1: this->pop();
        case 0: return;
      }
      Frame & parent = *(this->stack.end() - 2);
      ++parent.index;
      if(parent.index >= parent.end)
        this->pop();
      else
      {
        this->stack.back().cur = parent.cur->successor(parent.index);
        return;
      }
    }
  }

  void Walk2::operator++()
  {
    while(true)
    {
      switch(this->stack.size())
      {
        case 1: this->pop();
        case 0: return;
      }
      Frame & parent = *(this->stack.end() - 2);
      ++parent.index;
      if(parent.index >= parent.end)
        this->pop();
      else
      {
        this->stack.back().cur = parent.cur->successor(parent.index);
        return;
      }
    }
  }

  Node * UniqueNodeVisitor::next()
  {
    while(!this->queue.empty())
    {
      Node * x = this->queue.front();
      this->queue.pop_front();
      if(this->seen.count(x) == 0)
      {
        this->seen.insert(x);
        for(index_type i=0; i<x->info->arity; ++i)
        {
          Cursor succ = x->successor(i);
          if(succ.kind == 'p')
            this->queue.push_back(succ);
        }
        return x;
      }
    }
    return nullptr;
  }
}
