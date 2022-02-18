#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"

namespace sprite
{
  Node * Node::create(InfoTable const * info, Arg const * args)
  {
    Node * target = (Node *) node_alloc(info->alloc_size);
    assert(target);
    RawNodeMemory mem{target};
    *mem.info++ = info;
    pack(mem, info->format, args);
    return target;
  }

  Node * Node::create_flat(InfoTable const * info, xid_type & xidfactory)
  {
    Node * node = (Node *) node_alloc(info->alloc_size);
    RawNodeMemory mem{node};
    *mem.info++ = info;
    for(size_t i=0; i<info->arity; ++i)
      *mem.boxed++ = free(xidfactory++);
    return node;
  }

  Node * Node::from_partial(PartApplicNode const * partial, Node * arg)
  {
    assert(partial->info->typetag == PARTIAL_TYPE);
    assert(partial->complete(arg));
    Node * out = (Node *) node_alloc(partial->head_info->alloc_size);
    RawNodeMemory mem(out);
    *mem.info++ = partial->head_info;
    Node ** slot = mem.boxed + partial->head_info->arity;
    Node * pos = partial->terms;
    if(arg)
      *(--slot) = arg;
    while(pos->info->tag == T_CONS)
    {
      *(--slot) = NodeU{pos}.cons->head;
      pos = NodeU{pos}.cons->tail;
    }
    assert(slot == mem.boxed);
    return out;
  }
}

