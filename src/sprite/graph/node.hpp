#pragma once
#include <initializer_list>
#include <iosfwd>
#include "sprite/fwd.hpp"
#include <string>

namespace sprite
{
  struct Node
  {
    InfoTable const * info;

    static Node * create(InfoTable const *, Arg const * = nullptr, Node * target=nullptr);
    static Node * create(InfoTable const *, std::initializer_list<Arg>, Node * target=nullptr);
    static Node * create(InfoTable const *, id_type & idfactory);
    void forward_to(Node * target);
    tag_type make_failure();
    tag_type make_nil();
    tag_type make_unit();

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
