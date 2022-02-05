#pragma once
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  struct Variable
  {
    Variable(Walk & search) : search(&search), ret(search->size()) {}

    Variable(Variable * parent, index_type pos)
      : Variable(*parent, pos)
    {}

    Variable(Variable & parent, index_type pos)
      : search(parent.search)
      , ret(parent.search->size())
      , pathdata(sprite::realpath(this->root(), pos))
    {}

    Walk * search;
    size_t ret;
    RealpathResult pathdata;

    Node * root() { return search->at(this->ret - 1)->node; }
    Cursor & target() { return pathdata.target; }
    std::vector<index_type> & realpath() { return pathdata.realpath; }
    std::vector<sid_type> & guards() { return pathdata.guards; }

    Node * rvalue() { return this->target()->node; }
  };
}
