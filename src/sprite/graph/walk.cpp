#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  WalkState walk(Cursor root, index_type const * path)
    { return WalkState(root, path); }

  WalkState::WalkState(Cursor root, index_type const * realpath)
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
    this->data.pop_back();
  }

  void WalkState::push(sid_type sid)
  {
    Cursor cur = this->cursor();
    Frame frame;
    if(cur.kind == 'p')
    {
      index_type const n = cur->node->info->arity;
      frame.reserve(n);
      for(index_type i=0; i<n; ++i)
      {
        index_type const j = n - 1 - i;
        frame.emplace_back(Successor{cur->node->successor(j), j});
      }
    }
    this->realpath_.push_back(NOINDEX);
    this->spine.emplace_back();
    this->data.push_back(sid);
  }

  Cursor WalkState::cursor()
    { return this->spine.back(); }

  Cursor WalkState::parent()
  {
    size_t n = this->spine.size();
    return n < 2 ? Cursor() : this->spine[n-2];
  }
}
