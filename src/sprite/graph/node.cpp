#include <cassert>
#include "sprite/exceptions.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/raw.hpp"

namespace sprite
{
  Node * Node::create(
      InfoTable const * info, Arg * args, bool partial, Node * target
    )
  {
    if(!target)
      target = (Node *) node_alloc(info);
    assert(target);

    RawNodeMemory raw{target};
    *raw.info++ = info;

    auto argN = pack(raw, info->format, args);
    if(partial ? (argN - args) >= info->arity : (argN - args) != info->arity)
      throw TypeError("wrong number of arguments");

    return target;
  }

  Node * Node::rewrite(
      Node * node, InfoTable const * info, Arg * args, bool partial
    )
  {
    assert(node);
    return create(info, args, partial, node);
  }

  // std::string str(Node *);
  // std::string repr(Node *);
  // Node * copy(Node *);
  // Node * deepcopy(Node *);

  Cursor Node::getitem(Node * root, index_type i)
  {
    index_type path[] = {i, NOINDEX};
    return logical_subexpr(root, path);
  }

  // bool Node::eq(Node * lhs, Node * rhs)
  //   { return logically_equal(l, r); }

  // bool Node::ne(Node * lhs, Node * rhs)
  //   { return !logically_equal(lhs, rhs); }

  // This may not be needed.  It exists in Python so that Nodes can be placed
  // into a set.  It is not a true hash, though, just another way to express
  // the identity.
  //
  // hash_type hash(Node * node)
  // {
  //   union { Node * p; size_t i; } u{node};
  //   return u.i;
  // }

  Arg * Node::successors()
  {
    NodeU u{this};
    return &u.node1->arg;
  }

  Cursor Node::successor(index_type i)
  {
    return Cursor{
        this->successors()[i]
      , this->info->format[i]
      };
  }
}

