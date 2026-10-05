#pragma once
#include <cassert>
#include <cstring>
#include "cyrt/builtins.hpp"
#include "cyrt/graph/copy.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/show.hpp"
#include <functional> // for std::hash
#include <sstream>
#include <type_traits>

namespace cyrt
{
  inline void _loadargs(Node ** slot) {}

  template<typename ... Args>
  void _loadargs(Node ** slot, Arg arg0, Args && ... args)
  {
    *slot++ = arg0.node;
    _loadargs(slot, std::forward<Args>(args)...);
  }

  template<typename ... Args>
  Node * Node::create(InfoTable const * info, Arg arg0, Args && ... args)
  {
    assert(sizeof...(args) + 1 == info->arity);
    Node * target;
    do
    {
      target = node_reserve(info->alloc_size);
      assert(target);
      RawNodeMemory mem{target};
      *mem.info++ = info;
      *mem.boxed++ = arg0.node;
      _loadargs(mem.boxed, std::forward<Args>(args)...);
    } while(!node_commit(target, info->alloc_size));
    return target;
  }

  // The arguments go into the slots after the missing count and the head,
  // in call order; the number of arguments picks the info table (see
  // PartApplicNode in builtins.hpp).
  template<typename ... Args>
  Node * Node::create_partial(InfoTable const * info, Args && ... args)
  {
    constexpr index_type nargs = sizeof...(args);
    unboxed_int_type const missing = int(info->arity) - int(nargs);
    assert(missing > 0);
    assert(!is_pinned(*info));
    return Node::create(
        partapplic_info(nargs), missing, info, std::forward<Args>(args)...
      );
  }

  inline void Node::forward_to(Node * target)
  {
		assert(target);
    static_assert(std::is_trivially_destructible<Node>::value, "");
    assert(this->info->tag != T_FWD);
    assert(!is_pinned(*this->info));
    assert(!gc_is_literal(this));
    size_t bytes = this->info->alloc_size;
    if(bytes == sizeof(FwdNode))
		  new(this) FwdNode{&Fwd_Info, target};
    else
    {
      assert(bytes >= sizeof(FwdSzNode));
		  new(this) FwdSzNode{&FwdSz_Info, target, bytes};
    }
	}

  inline void Node::forward_to(Variable const & var)
  {
    return this->forward_to(var.rvalue());
  }

  template<typename ... Args>
  void Node::forward_to(InfoTable const * info, Args && ... args)
  {
    Node * target = Node::create(info, std::forward<Args>(args)...);
    this->forward_to(target);
  }

  // Rewrites the node in place.  The info table and the successors of the
  // result replace those of the node, so the node needs no forward node, no
  // new block, and no second dispatch.  The result must fit the block of the
  // node: the generated code compares the sizes of the two info tables at
  // compile time (see backends/cxx/compiler.py), and the steps of the runtime
  // library compare the alloc_size fields.  A smaller result in a larger
  // block is fine: the collector keeps the size of the block in its own
  // entry, and a copy of the node takes the alloc_size of its info table.
  //
  // The arguments are read before the first slot is written, because an
  // argument may be a successor of the node (``f x y = g y x``).  A pinned
  // constructor is never written here: the collector takes a node with a
  // pinned info table for the static object and would never mark a heap copy
  // (see gc/wdgc.cpp).  Such a result keeps the forward node.  The node
  // written is a redex, never a literal node (one node serves every
  // occurrence of a small value; see builtins.hpp).
  template<typename ... Args>
  tag_type Node::rewrite(InfoTable const * info, Args && ... args)
  {
    static_assert(std::is_trivially_destructible<Node>::value, "");
    assert(sizeof...(args) == info->arity);
    assert(!is_pinned(*info));
    assert(info->alloc_size <= this->info->alloc_size);
    assert(!gc_is_literal(this));
    // The trailing element keeps the array non-empty for a nullary result.
    Arg const values[] = {Arg(std::forward<Args>(args))..., Arg()};
    size_t const old_bytes = this->info->alloc_size;
    RawNodeMemory mem{this};
    *mem.info++ = info;
    for(size_t i=0; i<sizeof...(args); ++i)
      *mem.boxed++ = values[i].node;
    // The slack of a larger block is dead space for the block heap, and a
    // pad object for the MPS back end (see gc_pad_slack).
    gc_pad_slack(this, old_bytes, info->alloc_size);
    return info->tag;
  }

  // A reference result: the step returns a node that exists already.  The
  // redex is forwarded to it, unless the target is a primitive value (an
  // Int, Char, or Float node).  Such a node is never rewritten, so a copy of
  // it is as good as the node, and the copy saves the forward node, its
  // compression, and the second dispatch.  Every primitive node has the
  // smallest size, so it fits every redex.  A pinned constructor is not a
  // primitive and keeps the forward node (see rewrite).
  inline tag_type Node::forward_or_copy(Node * target)
  {
    assert(target);
    InfoTable const * info = target->info;
    if(is_primitive(*info))
    {
      // One size for the three kinds, so the copy is two words, not a call.
      static_assert(sizeof(IntNode) == sizeof(FloatNode), "");
      static_assert(sizeof(IntNode) == sizeof(CharNode), "");
      assert(info->alloc_size == sizeof(IntNode));
      assert(sizeof(IntNode) <= this->info->alloc_size);
      assert(!gc_is_literal(this));
      size_t const old_bytes = this->info->alloc_size;
      std::memcpy(this, target, sizeof(IntNode));
      gc_pad_slack(this, old_bytes, sizeof(IntNode));
      return info->tag;
    }
    this->forward_to(target);
    return T_FWD;
  }

  inline tag_type Node::forward_or_copy(Variable const & var)
  {
    return this->forward_or_copy(var.rvalue());
  }

  inline tag_type Node::make_failure()
  {
    if(this->info != &Fail_Info)
    {
      this->forward_to(Fail);
      return T_FWD;
    }
    return T_FAIL;
  }

  inline tag_type Node::make_nil()
  {
    if(this->info != &Nil_Info)
    {
      this->forward_to(Nil);
      return T_FWD;
    }
    return T_NIL;
  }

  inline tag_type Node::make_unit()
  {
    if(this->info != &Unit_Info)
    {
      this->forward_to(Unit);
      return T_FWD;
    }
    return T_UNIT;
  }

  inline std::string Node::str()
  {
    return this->str(SUBST_FREEVARS);
  }

  inline std::string Node::str(SubstFreevars subst_freevars, ShowMonitor * monitor)
  {
    std::stringstream ss;
    this->str(ss, subst_freevars, monitor);
    return ss.str();
  }

  inline void Node::str(std::ostream & os, SubstFreevars subst_freevars, ShowMonitor * monitor)
  {
    Node * self = this;
    auto style = subst_freevars ? SHOW_STR_SUBST_FREEVARS : SHOW_STR;
    show(os, self, style, monitor);
  }

  inline std::string Node::repr()
  {
    std::stringstream ss;
    this->repr(ss);
    return ss.str();
  }

  inline void Node::repr(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_REPR);
  }

  inline Node * Node::copy()
  {
    Node * self = this;
    return copy_node(self);
  }

  inline Node * Node::deepcopy()
  {
    Node * self = this;
    return copy_graph(self).arg.node;
  }

  inline Arg * Node::successors()
    { return NodeU{this}.nodeN->data; }

  inline Cursor const Node::successor(index_type i)
  {
    return Cursor{
        this->successors()[i]
      , this->info->format[i]
      };
  }

  inline Cursor Node::operator[](index_type i)
  {
    Variable v(this, i);
    return v.target;
  }

  // The node in successor slot ``i``, for an argument that a step only
  // passes on to another call.  Such an argument needs no Variable: no path,
  // because nothing head-normalizes it from this step, and no guard list,
  // because the slot holds the whole guarded value.  A forward node in the
  // slot is skipped, and the slot is shortened to the end of its chain, as
  // the indexer does (Variable::skip).  A set guard in the slot stays: it is
  // part of the argument (the rvalue of a Variable builds it again).  So the
  // result denotes what a Variable of the slot denotes.  The slot must hold a
  // node (format 'p'), as every slot of a function node of generated code
  // does; it is null between the creation of a recursive let and its patch
  // (INodeAssign).
  //
  // The redex of a step is a function node, never a guard, so the generated
  // code reads a direct successor of the redex this way.  A successor of a
  // Variable may lie under the guards the Variable crossed; that read goes
  // through Variable::successor_node (indexing.hxx), which knows them.
  inline Node * Node::successor_node(index_type i)
  {
    assert(i < this->info->arity);
    assert(this->info->format[i] == 'p');
    Node *& slot = this->successors()[i].node;
    Node * node = slot;
    if(node && node->info->tag == T_FWD)
    {
      Node * end = NodeU{node}.fwd->target;
      if(end->info->tag == T_FWD)
        end = *compress_fwd_chain(&slot);
      slot = end;
      node = end;
    }
    return node;
  }

  inline index_type Node::size() const { return this->info->arity; }
  inline Arg * Node::begin() { return successors(); }
  inline Arg * Node::end() { return begin() + size(); }
  inline std::size_t Node::hash() const { return std::hash<Node const *>()(this); }
  inline bool Node::operator!=(Node & arg) { return !(*this == arg); }
}

// The indexer of Variable needs the node layouts and Node::successor.
#include "cyrt/graph/indexing.hxx"
