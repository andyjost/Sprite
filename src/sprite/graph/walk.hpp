#pragma once
#include "sprite/graph/node.hpp"

namespace sprite
{
  struct WalkState
  {
    WalkState(Cursor root, index_type const * realpath);

    explicit operator bool() const { return !this->spine.empty(); }
    void operator++();

    void push(sid_type sid=NOSID);
    void pop();

    Cursor cursor();
    Cursor parent();
    index_type const * realpath() const { return realpath_.data(); }

  private:

    struct Successor { Cursor succ; index_type index; };
    using Frame = std::vector<Successor>;
    std::vector<Frame>      stack;
    std::vector<index_type> realpath_;
    std::vector<Cursor>     spine;
    std::vector<sid_type>   data;
  };

  WalkState walk(Cursor root, index_type const * path=nullptr);
}
