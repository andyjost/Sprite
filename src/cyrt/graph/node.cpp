#include <cassert>
#include <cstring>
#include <vector>
#include "cyrt/builtins.hpp"
#include "cyrt/currylib/setfunctions.hpp"
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
    {
      do
      {
        target = node_reserve(info->alloc_size);
        assert(target);
        RawNodeMemory mem{target};
        *mem.info++ = info;
        pack(mem, info->format, args);
      } while(!node_commit(target, info->alloc_size));
      // The collector releases the iterator of a generator node that dies
      // unstepped (see gc/wdgc.cpp).  The bindings and the graph copier
      // make such nodes here; generator() in builtins.hpp registers its
      // own.
      if(info == &_biGenerator_Info)
        gc_register_generator(target);
      // The MPS back end finalizes a SetEval node to free its queue (see
      // gc_register_seteval); the graph copier and the bindings make such
      // nodes here.
      else if(info == &SetEval_Info)
        gc_register_seteval(target);
    }
    return target;
  }

  // Writes a partial application into a new block of ``info``, a table of a
  // partial family for ``numargs`` arguments: the missing count, the head,
  // and the arguments in call order.
  static Node * make_partial(
      InfoTable const * info, unboxed_int_type missing
    , InfoTable const * head_info, Node * const * args, size_t numargs
    )
  {
    assert(is_partial(*info));
    assert(info->arity == numargs + 2);
    Node * target;
    do
    {
      target = node_reserve(info->alloc_size);
      assert(target);
      RawNodeMemory mem{target};
      *mem.info++ = info;
      *mem.ub_int++ = missing;
      *mem.ub_ptr++ = (void *) head_info;
      for(size_t i=0; i<numargs; ++i)
        *mem.boxed++ = args[i];
    } while(!node_commit(target, info->alloc_size));
    return target;
  }

  Node * Node::create_partial(InfoTable const * info, Arg const * args, size_t numargs)
  {
    assert(!is_pinned(*info));
    unboxed_int_type const missing = int(info->arity) - (int) numargs;
    assert(missing > 0);
    static_assert(sizeof(Arg) == sizeof(Node *), "");
    return make_partial(
        partapplic_info((index_type) numargs), missing, info
      , (Node * const *) args, numargs
      );
  }

  Node * Node::extend_partial(PartApplicNode const * partial, Node * arg)
  {
    assert(is_partial(*partial->info));
    assert(!partial->is_encapsulated());
    assert(partial->missing >= 1);
    index_type const nargs = partial->nargs();
    InfoTable const * info = partial->info->type == &PartialS_Type
        ? partials_info(nargs + 1) : partapplic_info(nargs + 1);
    assert(info->type == partial->info->type);
    Node * target;
    do
    {
      target = node_reserve(info->alloc_size);
      assert(target);
      RawNodeMemory mem{target};
      *mem.info++ = info;
      *mem.ub_int++ = partial->missing - 1;
      *mem.ub_ptr++ = (void *) partial->head_info;
      std::memcpy(mem.boxed, partial->args(), nargs * sizeof(Node *));
      mem.boxed += nargs;
      *mem.boxed++ = arg;
    } while(!node_commit(target, info->alloc_size));
    return target;
  }

  // The node is written with null slots before the first variable is made,
  // and each variable goes into its slot as it is made.  A collector that
  // may run at an allocation (the MPS back end) then finds a complete node,
  // whose null slots it skips, and every variable made so far through the
  // node; the node itself is held by this frame of the C stack, which that
  // collector scans.  A pointer kept elsewhere (a vector on the heap) would
  // go stale when the collector moves its variable.
  Node * Node::create_flat(InfoTable const * info, RuntimeState * rts)
  {
    Node * node = get_pinned_object(info);
    if(!node)
    {
      do
      {
        node = node_reserve(info->alloc_size);
        RawNodeMemory mem{node};
        *mem.info++ = info;
        for(size_t i=0; i<info->arity; ++i)
          *mem.boxed++ = nullptr;
      } while(!node_commit(node, info->alloc_size));
      Arg * slots = node->successors();
      for(size_t i=0; i<info->arity; ++i)
        slots[i] = rts->freshvar();
    }
    return node;
  }

  // Writes the function node that a completed partial application denotes
  // into ``out``: the head of the partial application with its arguments,
  // and ``arg`` last.  ``out`` is a new block (from_partial) or the redex
  // (rewrite_from_partial); the partial application is another node, so the
  // reads do not overlap the writes.
  static void fill_from_partial(
      Node * out, PartApplicNode const * partial, Node * arg
    )
  {
    assert(is_partial(*partial->info));
    assert(partial->complete(arg));
    assert(!is_pinned(*partial->head_info));
    assert((Node const *) out != (Node const *) partial);
    index_type const nargs = partial->nargs();
    RawNodeMemory mem(out);
    *mem.info++ = partial->head_info;
    std::memcpy(mem.boxed, partial->args(), nargs * sizeof(Node *));
    mem.boxed += nargs;
    if(arg)
      *mem.boxed++ = arg;
    assert(nargs + (arg ? 1 : 0) == partial->head_info->arity);
  }

  Node * Node::from_partial(PartApplicNode const * partial, Node * arg)
  {
    Node * out;
    do
    {
      out = node_reserve(partial->head_info->alloc_size);
      fill_from_partial(out, partial, arg);
    } while(!node_commit(out, partial->head_info->alloc_size));
    return out;
  }

  tag_type Node::rewrite_from_partial(PartApplicNode const * partial, Node * arg)
  {
    assert(partial->head_info->alloc_size <= this->info->alloc_size);
    assert(!gc_is_literal(this));
    size_t const old_bytes = this->info->alloc_size;
    fill_from_partial(this, partial, arg);
    gc_pad_slack(this, old_bytes, partial->head_info->alloc_size);
    return partial->head_info->tag;
  }

  bool Node::operator==(Node & arg)
  {
    Node * a = this;
    Node * b = &arg;
    return logically_equal(a, b);
  }
}

