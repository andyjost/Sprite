#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  Node * Node::create(
      InfoTable const * info, Arg const * args, Node * target
    )
  {
    if(!target)
      target = (Node *) node_alloc(info->alloc_size);
    assert(target);

    RawNodeMemory mem{target};
    *mem.info++ = info;
    pack(mem, info->format, args);
    return target;
  }

  Node * Node::create(InfoTable const * info, xid_type & xidfactory)
  {
    Node * node = (Node *) node_alloc(info->alloc_size);
    RawNodeMemory mem{node};
    *mem.info++ = info;
    for(size_t i=0; i<info->arity; ++i)
      *mem.boxed++ = free(xidfactory++);
    return node;
  }
}

