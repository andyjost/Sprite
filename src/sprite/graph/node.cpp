#include <cstdlib>
#include "sprite/exceptions.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/expr.hpp"

namespace sprite { namespace node
{
  Node create(InfoTable const * info, void ** args, bool partial, Node target)
  {
    if(!target)
      target = malloc(info->alloc_size);
    assert(target);

    Node0 * out = (Node0 *)(target);
    out->info = info;
    out++;

    auto argN = pack(out, info->packing, args);
    if((argN - args) != info->arity && !partial)
      throw TypeError("todo");

    return target;
  }

  std::string str(Node);
  std::string repr(Node);
  Node copy(Node);
  Node deepcopy(Node);
  Expr getitem(Node, size_t);
  bool eq(Node, Node);
  bool ne(Node, Node);
  hash_type hash(Node);

}}
