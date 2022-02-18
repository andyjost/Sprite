#pragma once
// #include <initializer_list>
#include <iosfwd>
#include "sprite/fwd.hpp"
#include "sprite/graph/cursor.hpp"
#include <string>

namespace sprite
{
  struct Node
  {
    InfoTable const * info;

    // Create a complete node.
    static Node * create(InfoTable const *, Arg const * = nullptr);
    template<typename ... Args> static Node * create(InfoTable const *, Arg, Args && ...);

    // Create a partial application.
    template<typename ... Args>
    static Node * create_partial(InfoTable const *, Args && ...);

    // Materialize a completed partial application.
    static Node * from_partial(PartApplicNode const *, Node * finalarg = nullptr);

    // Create a flat expression (each successor is a fresh variable).
    static Node * create_flat(InfoTable const *, xid_type & xidfactory);


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
