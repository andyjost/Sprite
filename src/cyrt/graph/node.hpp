#pragma once
#include <iosfwd>
#include "cyrt/fwd.hpp"
#include "cyrt/graph/cursor.hpp"
#include <string>

namespace cyrt
{
  struct Node
  {
    InfoTable const * info;

    // Create a complete node.
    static Node * create(InfoTable const *, Arg const * = nullptr);
    template<typename ... Args> static Node * create(InfoTable const *, Arg, Args && ...);

    // Create a partial application.
    static Node * create_partial(InfoTable const *, Arg const *, size_t numargs);
    template<typename ... Args>
    static Node * create_partial(InfoTable const *, Args && ...);

    // Materialize a completed partial application.
    static Node * from_partial(PartApplicNode const *, Node * finalarg = nullptr);

    // Create a flat expression (each successor is a fresh variable).
    static Node * create_flat(InfoTable const *, xid_type & xidfactory);


    void forward_to(Node *);
    template<typename ... Args> void forward_to(InfoTable const *, Args && ...);


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
    std::string str(SubstFreevars);
    void str(std::ostream &, SubstFreevars=SUBST_FREEVARS);

    // Equality.
    std::size_t hash() const;
    bool operator==(Node &);
    bool operator!=(Node &);

    // Indexing.
    Cursor const successor(index_type);
    Arg * successors();
    Cursor operator[](index_type);

    index_type size() const;
    Arg * begin();
    Arg * end();
  };
}

#include "cyrt/graph/node.hxx"
