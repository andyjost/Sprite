#pragma once
#include "sprite/builtins.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/show.hpp"
#include <sstream>

namespace sprite
{
  inline Node * Node::rewrite(InfoTable const * info, Arg * args)
  {
    return create(info, args, this);
  }

  inline std::string Node::str()
  {
    std::stringstream ss;
    this->str(ss);
    return ss.str();
  }

  inline void Node::str(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_STR);
  }

  inline std::string Node::repr()
  {
    std::stringstream ss;
    this->repr(ss);
    return ss.str();
  }

  inline void Node::repr(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_REPR);
  }

  inline Node * Node::copy()
  {
    Node * self = this;
    return copy_node(self).arg.node;
  }

  inline Node * Node::deepcopy()
  {
    Node * self = this;
    return copy_graph(self).arg.node;
  }

  inline Arg * Node::successors()
    { return NodeU{this}.nodeN->data; }

  inline Cursor const Node::successor(index_type i)
  {
    return Cursor{
        this->successors()[i]
      , this->info->format[i]
      };
  }

  inline Cursor Node::operator[](index_type i)
  {
    index_type path[] = {i, NOINDEX};
    return (*this)[path];
  }

  inline Cursor Node::operator[](index_type const * path)
    { return logical_subexpr(this, path); }
}
