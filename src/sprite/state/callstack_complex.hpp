#pragma once
#include "sprite/graph/walk.hpp"
#include <utility>
#include <vector>

namespace sprite
{
  struct SFrame
  {
    stepfunc_type step; // compiler-generated step function
    size_t ret;         // return point (a depth in the search state).

    SFrame(stepfunc_type step, size_t ret)
      : step(step), ret(ret)
    {}

    size_t root_pos() const { return this->ret - 1; }
  };

  struct CallStack
  {
    CallStack(Cursor root) : search(root) {}

    Walk search;
    mutable std::vector<SFrame> stack;

    size_t stack_depth() const { return this->stack.size(); }
    size_t search_depth() const { return this->search.size(); }

    Cursor & root(size_t frameno=0) const
    {
      auto & f = this->frame(frameno);
      return this->search.at(f.root_pos());
    }

    size_t root_pos(size_t frameno=0) const
      { return this->frame(frameno).root_pos(); }

    Cursor & target(size_t frameno=0) const
    {
      if(!frameno)
        return this->search.cursor();
      else
        return this->root(frameno - 1);
    }

    SFrame & frame(size_t frameno=0) const
      { return *(this->stack.rbegin() + frameno); }

    void enter(stepfunc_type step)
    {
      size_t const ret = this->search_depth();
      this->stack.emplace_back(step, ret);
    }

    void exit()
    {
      this->search.resize(this->stack.back().ret);
      this->stack.pop_back();
    }

    void push() { this->enter(this->target().info()->step); }

    void reset(Cursor root)
    {
      this->search = Walk(root);
      this->stack.clear();
    }

    explicit operator bool() const { return !this->stack.empty(); }

    StepStatus runframe(RuntimeState * rts, Configuration * C)
    {
      assert(!this->stack.empty());
      auto & f = this->stack.back();
      return f.step(rts, C, this->search.at(f.root_pos()));
    }
  };
}
