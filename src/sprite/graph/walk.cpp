#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  Walk::Walk(
      Cursor root
    , void * static_data
    , datadisposer_type dispose
    )
    : stack({Frame{root}})
    , static_data(static_data), dispose(dispose)
  {
    assert(root);
  }

  Walk::operator bool() const
  {
    return !this->stack.empty();
  }

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
        this->stack.back().cur = parent.cur->node->successor(parent.index);
        return;
      }
    }
  }

  void Walk::push(void * data)
  {
    Frame & parent = stack.back();
    parent.index = NOINDEX;
    parent.end = parent.cur.kind == 'p' ? parent.cur->node->info->arity : 0;
    this->stack.emplace_back(data);
    // this->stack.back().data = data;
  }

  void Walk::extend(index_type pos)
  {
    Frame & parent = stack.back();
    parent.index = pos;
    parent.end = pos + 1;
    Cursor succ = parent.cur->node->successor(pos);
    this->stack.emplace_back(succ);
    // this->stack.back().cur = succ;
    // this->stack.back().data = data;
  }

  void Walk::pop()
  {
    if(this->dispose)
      this->dispose(this->static_data, this->stack.back().data);
    this->stack.pop_back();
  }

  Cursor & Walk::root() const
  {
    assert(*this);
    return this->stack.front().cur;
  }

  Cursor & Walk::cursor() const
  {
    assert(*this);
    return this->stack.back().cur;
  }

  void *& Walk::data() const
  {
    assert(*this);
    return this->stack.back().data;
  }

  Node * Walk::copy_spine(Node * root, Node * end)
  {
    auto p = this->stack.rbegin() + 1;
    auto e = this->stack.rend();
    assert(p<=e);
    for(; p!=e; ++p)
    {
      Node * tmp = copy_node(p->cur->node);
      *tmp->successor(p->index) = Arg(end);
      end = tmp;
      if(p->cur->node == root)
        break;
    }
    return end;
  }
}
