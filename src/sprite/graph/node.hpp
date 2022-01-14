#pragma once
#include <iosfwd>
#include "sprite/fwd.hpp"
#include <string>

namespace sprite
{
  struct Node
  {
    InfoTable const * info;

    static Node * create(InfoTable const *, Arg * = nullptr, Node * target=nullptr);
    // Node * rewrite(InfoTable const *, Arg * = nullptr);
    void forward_to(Node * target);

    // Copy.
    Node * copy();
    Node * deepcopy();

    // Show.
    std::string repr();
    void repr(std::ostream &);
    std::string str();
    void str(std::ostream &);

    // Indexing.
    Cursor const successor(index_type);
    Arg * successors();
    Cursor operator[](index_type);
    Cursor operator[](index_type const *);
  };
}

#include "sprite/graph/node.hxx"
