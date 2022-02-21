#include "sprite/graph/indexing.hpp"
#include "sprite/state/scan.hpp"

namespace sprite
{
  Scan::Scan(
      Cursor root
    , void * static_data
    , datadisposer_type dispose
    )
    : stack({Frame{root}})
    , static_data(static_data), dispose(dispose)
  {
    assert(root);
  }

  void Scan::reset()
  {
    if(this->stack.size() > 1)
      this->stack.resize(1);
  }

  void Scan::push_barrier() { this->barriers.push_back(this->size()); }
  void Scan::pop_barrier() { this->barriers.pop_back(); }

  Scan::operator bool() const
  {
    if(this->stack.empty())
      return false;
    else
      return this->barriers.empty() || this->stack.size() > this->barriers.back();
  }

  void Scan::operator++()
  {
    while(true)
    {
      if(!this->barriers.empty() && this->stack.size() == this->barriers.back())
        return;
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

  void Scan::push(void * data)
  {
    Frame & parent = stack.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->info->arity : 0;
    this->stack.emplace_back(data);
  }

  void Scan::extend(index_type pos)
  {
    Frame & parent = stack.back();
    parent.index = pos;
    parent.end = pos + 1;
    Cursor succ = parent.cur->successor(pos);
    this->stack.emplace_back(succ);
  }

  void Scan::extend(index_type const * path)
  {
    if(path)
      while(*path != NOINDEX)
        this->extend(*path++);
  }

  size_t Scan::extend(Variable const * inductive)
  {
    size_t ret = this->size();
    this->extend(inductive->realpath.data());
    return ret;
  }

  void Scan::pop()
  {
    if(this->dispose)
      this->dispose(this->static_data, this->stack.back().data);
    this->stack.pop_back();
  }

  Cursor Scan::cursor() const
  {
    assert(*this);
    return this->stack.back().cur;
  }

  void *& Scan::data() const
  {
    assert(*this);
    return this->stack.back().data;
  }

  Node * Scan::copy_spine(Node * root, Node * end, size_t start)
  {
    return this->copy_spine(root, end, nullptr, start);
  }

  Node * Scan::copy_spine(
      Node * root, Node * end, Cursor * target, size_t start
    )
  {
    auto p = this->stack.rbegin() + start;
    auto e = this->stack.rend();
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
