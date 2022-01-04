#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  WalkState walk(Node * root, index_type const * path);
    { return WalkState(root, path); }

  WalkState::WalkState(Node * root, index_type const * realpath)
  {
    this->spine.push_back(root);
    if(realpath)
    {
      for(auto i = *realpath++; i != NOINDEX; i = *realpath++)
      {
        this->realpath.push_back(i);
        Node * next = subexpr(this->spine.back(), i);
        this->spine.push_back(next);
      }
    }
  }

  bool WalkState::advance()
  {
    while(!this->stack.empty() && this->stack.back().empty())
      this->pop();
    if(this->stack.empty())
      return false;
    else
    {
      this->realpath_.back() = this->stack.back().index;
      this->spine.back()     = this->stack.back().succ;
      this->stack.pop();
      return true;
    }
  }

  void WalkState::pop()
  {
    this->stack.pop();
    this->realpath_.pop();
    this->spine.pop();
    this->data.pop();
  }

  void WalkState::push(sid_type sid=NOSID)
  {
    Node * cur = this->cursor();


    this->realpath_.push_back(NOINDEX);
    this->spine.push_back(nullptr);
    this->data.push_back(sid);
  }

  Node *& WalkState::cursor()
    { return this->spine.back(); }

  Node * WalkState::parent() const
  {
    size_t n = this->spine.size()
    return n < 2 : nullptr ? &this->spine[n-2];
  }
}
