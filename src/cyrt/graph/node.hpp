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

    // Create a partial application of the given head with the given
    // arguments (one allocation; see PartApplicNode in builtins.hpp).
    static Node * create_partial(InfoTable const *, Arg const *, size_t numargs);
    template<typename ... Args>
    static Node * create_partial(InfoTable const *, Args && ...);

    // A partial application with one more argument: a copy of the given one
    // under the table of its family for one more argument, with ``arg`` last
    // and one argument fewer missing.  apply and applyS allocate this node.
    static Node * extend_partial(PartApplicNode const *, Node * arg);

    // Materialize a completed partial application: the function node of its
    // head with its arguments, and ``finalarg`` last when given.
    static Node * from_partial(PartApplicNode const *, Node * finalarg = nullptr);

    // Create a flat expression (each successor is a fresh variable).
    static Node * create_flat(InfoTable const *, RuntimeState *);


    void forward_to(Node *);
    void forward_to(Variable const &);
    template<typename ... Args> void forward_to(InfoTable const *, Args && ...);

    // Rewrite this node in place to a node of the given info table, with the
    // given successors, and return the tag of the info table.  The result
    // must fit the block of this node; see node.hxx.
    template<typename ... Args>
    tag_type rewrite(InfoTable const *, Args && ...);

    // Rewrite this node in place to the function node a completed partial
    // application denotes.  The caller checks that it fits.
    tag_type rewrite_from_partial(
        PartApplicNode const *, Node * finalarg = nullptr
      );

    // The result of a step is an existing node: forward this node to it, or
    // copy it when it is a primitive value.  Returns the tag to return from
    // the step.  See node.hxx.
    tag_type forward_or_copy(Node *);
    tag_type forward_or_copy(Variable const &);

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
    std::string str(SubstFreevars, ShowMonitor * = nullptr);
    void str(std::ostream &, SubstFreevars=SUBST_FREEVARS, ShowMonitor * = nullptr);

    // Equality.
    std::size_t hash() const;
    bool operator==(Node &);
    bool operator!=(Node &);

    // Indexing.
    Cursor const successor(index_type);
    // The node in successor slot ``i``, for an argument that a step only
    // passes on: a forward node in the slot is skipped, a set guard stays.
    // See node.hxx.
    Node * successor_node(index_type);
    Arg * successors();
    Cursor operator[](index_type);

    index_type size() const;
    Arg * begin();
    Arg * end();
  };
}

#include "cyrt/graph/node.hxx"
