#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/equality.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"

namespace cyrt
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

  Node * Node::create_partial(InfoTable const * info, Arg const * args, size_t numargs)
  {
    unboxed_int_type const missing = int(info->arity) - (int) numargs;
    assert(missing > 0);

    Node * arglist = nil();
    for(size_t i=0; i<numargs; ++i)
      arglist = cons(args[numargs-i-1].node, arglist);

    Node * partial = Node::create(
        &PartApplic_Info
      , missing
      , info
      , arglist
      );
    return partial;
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
    assert(is_partial(*partial->info));
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

  bool Node::operator==(Node & arg)
  {
    Node * a = this;
    Node * b = &arg;
    return logically_equal(a, b);
  }
}

