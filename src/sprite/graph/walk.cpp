#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  Walk::Walk(
      Cursor root
    , void * static_data
    , datadisposer_type dispose
    )
    : stack({Frame{}, Frame{root}})
    , static_data(static_data), dispose(dispose)
  {
    assert(root);
  }

  Walk::operator bool() const
  {
    return this->stack.size() > 1;
  }

  void Walk::operator++()
  {
    while(*this)
    {
      Frame & frame = this->stack.back();
      ++frame.index;
      if(!frame)
        this->pop();
      else
      {
        this->stack.emplace_back(
            frame.cur->node->successor(frame.index)
          );
        return;
      }
    }
  }

  void Walk::push(void * data)
  {
    Frame & frame = stack.back();
    assert(frame.index == NOINDEX - 1);
    ++frame.index;
    frame.data = data;
  }

  void Walk::pop()
  {
    Frame & frame = this->stack.back();
    if(this->dispose && frame.index < NOINDEX)
      this->dispose(this->static_data, frame.data);
    this->stack.pop_back();
  }

  Cursor & Walk::root()
  {
    assert(*this);
    return this->stack.front().cur;
  }

  Cursor & Walk::cursor()
  {
    assert(*this);
    return this->stack.back().cur;
  }

  void *& Walk::data()
  {
    assert(*this);
    return (this->stack.end() - 2)->data;
  }

  Node * Walk::copy_spine(Node * end)
  {
    return nullptr;
  }
}
