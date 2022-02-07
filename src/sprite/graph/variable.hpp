#pragma once
#include <list>
#include "sprite/fwd.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/walk.hpp"

namespace sprite
{
  struct Redex
  {
    Redex(Walk & search) : search(&search), ret(search.size()) {}
    explicit Redex(Variable const &);
    ~Redex() { this->search->resize(this->ret); }

    Walk * search;
    size_t ret;

    Node * root() const { return this->search->at(this->ret - 1)->node; }
    operator Node *() const { return this->root(); }
  };

  struct Variable
  {
    Variable(Redex const & parent, index_type pos)
      : redex(&parent)
      , pathdata(sprite::realpath(parent.root(), pos))
    {}

    Variable(Variable const & parent, index_type pos)
      : redex(parent.redex)
      , pathdata(sprite::realpath(parent.target(), pos))
    {}

    Redex const * redex;
    RealpathResult pathdata;

    Node * root() const { return this->redex->root(); }
    Cursor & target() const { return pathdata.target; }
    std::vector<index_type> const & realpath() { return pathdata.realpath; }
    std::vector<sid_type> const & guards() { return pathdata.guards; }
    Node * rvalue() const { return this->target()->node; }
  };

  inline Redex::Redex(Variable const & var)
    : search(var.redex->search)
  {
    this->search->extend(var.pathdata.realpath.data());
    this->ret = this->search->size();
  }
}
