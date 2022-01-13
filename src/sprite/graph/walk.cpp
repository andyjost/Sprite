#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  WalkState::WalkState(
      Cursor root
    , index_type const * realpath
    , void * static_data
    , datadisposer_type dispose
    , void * data
    )
    : static_data(static_data), dispose(dispose)
  {
    if(root)
    {
      this->spine.push_back(root);
      if(realpath)
      {
        for(auto i = *realpath++; i != NOINDEX; i = *realpath++)
        {
          this->realpath_.push_back(i);
          Cursor && next = subexpr(this->spine.back(), i);
          this->spine.push_back(next);
        }
      }
      this->data_.push_back(data);
    }
  }

  void WalkState::operator++()
  {
    while(!this->stack.empty() && this->stack.back().empty())
      this->pop();
    if(this->stack.empty())
      this->spine.clear();
    else
    {
      auto && frame = this->stack.back();
      this->realpath_.back() = frame.back().index;
      this->spine.back()     = frame.back().succ;
      frame.pop_back();
    }
  }

  void WalkState::pop()
  {
    this->stack.pop_back();
    this->realpath_.pop_back();
    this->spine.pop_back();
    if(this->dispose)
      this->dispose(this->static_data, this->data_.back());
    this->data_.pop_back();
  }

  void WalkState::push(void * data)
  {
    Cursor cur = this->cursor();
    Frame frame;
    assert(cur.kind == 'p');
    index_type const n = cur->node->info->arity;
    frame.reserve(n);
    for(index_type i=0; i<n; ++i)
    {
      index_type const j = n - 1 - i;
      frame.emplace_back(Successor{cur->node->successor(j), j});
    }
    this->stack.emplace_back(std::move(frame));
    this->realpath_.push_back(NOINDEX);
    this->spine.emplace_back();
    this->data_.push_back(data);
  }

  Cursor & WalkState::root()
  {
    assert(!this->spine.empty());
    return this->spine.front();
  }

  Cursor & WalkState::cursor()
  {
    assert(!this->spine.empty());
    return this->spine.back();
  }

  Cursor & WalkState::parent()
  {
    size_t n = this->spine.size();
    assert(n >= 2);
    return this->spine[n-2];
  }
}
