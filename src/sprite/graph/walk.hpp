#pragma once
#include "sprite/graph/node.hpp"

namespace sprite
{
  struct WalkState
  {
    WalkState(Node * root, index_type const * realpath);

    bool advance();
    void pop();
    void push(sid_type sid=NOSID);

    Arg & cursor();
    Node * parent() const;
    index_type const * realpath() const { return realpath_.data(); }

  private:

    struct Successor { Expr * succ; index_type index; };
    std::vector<std::vector<Successor>> stack;
    std::vector<index_type>             realpath_;
    std::vector<Expr *>                 spine;
    std::vector<sid_type>               data;
  };


  WalkState walk(Node * root, index_type const * path=nullptr);
}
