#pragma once
#include <cassert>
#include "sprite/fwd.hpp"
#include "sprite/graph/infotable.hpp"

// Nodes are implemented as void * because their size depends on the Curry
// type, which is only known at runtime.  The interface is implementing as
// freestanding functions in this file.

namespace sprite { namespace node
{
  struct Node0
  {
    InfoTable const * info;
  };

  using hash_type = std::size_t;
  using path_type = arity_type*;

  static bool constexpr PARTIAL = true;
  Node create(InfoTable const *, void **, bool partial=false, Node target=nullptr);
  Node rewrite(Node, InfoTable const *, void **, bool partial=false);

  std::string str(Node);
  std::string repr(Node);
  Node copy(Node);
  Node deepcopy(Node);
  Expr getitem(Node, size_t);
  bool eq(Node, Node);
  bool ne(Node, Node);
  hash_type hash(Node);
}}


// Implementation
namespace sprite { namespace node
{
  inline Node rewrite(Node node, InfoTable const * info, void ** args, bool partial)
  {
    assert(node);
    return create(info, args, partial, node);
  }
}}
