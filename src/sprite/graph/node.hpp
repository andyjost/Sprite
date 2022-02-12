#pragma once
#include <initializer_list>
#include <iosfwd>
#include "sprite/fwd.hpp"
#include "sprite/graph/cursor.hpp"
#include <string>

namespace sprite
{
  struct Node
  {
    InfoTable const * info;

    static Node * create(InfoTable const *, Arg const * = nullptr, Node * target=nullptr);
    static Node * create(InfoTable const *, std::initializer_list<Arg>, Node * target=nullptr);
    static Node * create(InfoTable const *, xid_type & xidfactory);
    template<typename ... Args> static Node * create(InfoTable const *, Arg, Args && ...);
    static Node * from_partial(PartApplicNode const *, Node * arg = nullptr);
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

    index_type size() const;
    Arg * begin();
    Arg * end();
  };
}

#include "sprite/graph/node.hxx"
