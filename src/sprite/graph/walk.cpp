#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  Search::Search(
      Cursor root
    , void * static_data
    , datadisposer_type dispose
    )
    : stack({Frame{root}})
    , static_data(static_data), dispose(dispose)
  {
    assert(root);
  }

  void Search::reset()
  {
    if(this->stack.size() > 1)
      this->stack.resize(1);
  }

  Search::operator bool() const
  {
    return !this->stack.empty();
  }

  void Search::operator++()
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
        this->stack.back().cur = parent.cur->node->successor(parent.index);
        return;
      }
    }
  }

  void Search::push(void * data)
  {
    Frame & parent = stack.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->node->info->arity : 0;
    this->stack.emplace_back(data);
  }

  void Search::extend(index_type pos)
  {
    Frame & parent = stack.back();
    parent.index = pos;
    parent.end = pos + 1;
    Cursor succ = parent.cur->node->successor(pos);
    this->stack.emplace_back(succ);
  }

  void Search::extend(index_type const * path)
  {
    if(path)
      while(*path != NOINDEX)
        this->extend(*path++);
  }

  void Search::pop()
  {
    if(this->dispose)
      this->dispose(this->static_data, this->stack.back().data);
    this->stack.pop_back();
  }

  Cursor Search::root() const
  {
    assert(*this);
    return this->stack.front().cur;
  }

  Cursor Search::cursor() const
  {
    assert(*this);
    return this->stack.back().cur;
  }

  void *& Search::data() const
  {
    assert(*this);
    return this->stack.back().data;
  }

  Node * Search::copy_spine(Node * root, Node * end, size_t start)
  {
    return this->copy_spine(root, end, nullptr, start);
  }

  Node * Search::copy_spine(
      Node * root, Node * end, Cursor * target, size_t start
    )
  {
    auto p = this->stack.rbegin() + start;
    auto e = this->stack.rend();
    assert(p<=e);
    for(; p!=e; ++p)
    {
      Node * tmp = copy_node(p->cur->node);
      *tmp->successor(p->index) = Arg(end);
      if(target)
      {
        *target = tmp->successor(p->index);
        target = nullptr;
      }
      end = tmp;
      if(p->cur->node == root)
        break;
    }
    return end;
  }

  Node * NodeIterator::next()
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
            this->queue.push_back(succ->node);
        }
        return x;
      }
    }
    return nullptr;
  }
}
