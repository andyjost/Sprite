#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/equality.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  static inline Node * get_pinned_object(InfoTable const * info)
  {
    return is_pinned(*info) ? (Node *) info->step : nullptr;
  }

  Node * Node::create(InfoTable const * info, Arg const * args)
  {
    Node * target = get_pinned_object(info);
    if(!target)
      do
      {
        target = node_reserve(info->alloc_size);
        assert(target);
        RawNodeMemory mem{target};
        *mem.info++ = info;
        pack(mem, info->format, args);
      } while(!node_commit(target, info->alloc_size));
    return target;
  }

  Node * Node::create_partial(InfoTable const * info, Arg const * args, size_t numargs)
  {
    assert(!is_pinned(*info));
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

  Node * Node::create_flat(InfoTable const * info, RuntimeState * rts)
  {
    Node * node = get_pinned_object(info);
    if(!node)
      do
      {
        node = node_reserve(info->alloc_size);
        RawNodeMemory mem{node};
        *mem.info++ = info;
        for(size_t i=0; i<info->arity; ++i)
          *mem.boxed++ = rts->freshvar();
      } while(!node_commit(node, info->alloc_size));
    return node;
  }

  Node * Node::from_partial(PartApplicNode const * partial, Node * arg)
  {
    assert(is_partial(*partial->info));
    assert(partial->complete(arg));
    assert(!is_pinned(*partial->head_info));
    Node * out;
    do
    {
      out = node_reserve(partial->head_info->alloc_size);
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
    } while(!node_commit(out, partial->head_info->alloc_size));
    return out;
  }

  bool Node::operator==(Node & arg)
  {
    Node * a = this;
    Node * b = &arg;
    return logically_equal(a, b);
  }
}

