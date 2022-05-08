#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/walk.hpp"

namespace cyrt
{
  void Walk::operator++()
  {
    while(true)
    {
      switch(this->stack.size())
      {
        case 1: this->stack.pop_back();
        case 0: return;
      }
      Level & parent = *(this->stack.end() - 2);
      ++parent.index;
      if(parent.index >= parent.end)
        this->stack.pop_back();
      else
      {
        this->stack.back().cur = parent.cur->successor(parent.index);
        return;
      }
    }
  }

  std::vector<index_type> Walk2::path() const
  {
    std::vector<index_type> path;
    for(auto && level: this->stack)
    {
      if(level.index != NOINDEX)
        path.push_back(level.index);
    }
    return path;
  }

  bool Walk2::at_terminus(std::vector<index_type> const & path) const
  {
    auto p = path.begin();
    auto q = path.end();
    for(auto && frame: this->stack)
    {
      if(p<q)
      {
        if(*p++ != frame.index)
          return false;
      }
      else
      {
        if(frame.index < frame.end)
          return false;
      }
    }
    return true;
  }

  void Walk2::_dispose_back()
  {
    if(this->dispose)
    {
      auto && back = this->stack.back();
      this->dispose(this->static_data, back.data, this);
    }
  }

  void Walk2::operator++()
  {
    while(true)
    {
      switch(this->stack.size())
      {
        case 1: this->_dispose_back();
                this->stack.pop_back();
        case 0: return;
      }
      Level & parent = *(this->stack.end() - 2);
      ++parent.index;
      if(parent.index >= parent.end)
      {
        this->_dispose_back();
        this->stack.pop_back();
      }
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
