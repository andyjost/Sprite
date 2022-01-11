#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  Node * Node::create(
      InfoTable const * info, Arg * args, Node * target
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
}

