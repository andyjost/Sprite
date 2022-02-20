#pragma once
#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/indexing.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/show.hpp"
#include <sstream>

namespace sprite
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
    Node * target = (Node *) node_alloc(info->alloc_size);
    assert(target);
    RawNodeMemory mem{target};
    *mem.info++ = info;
    *mem.boxed++ = arg0.node;
    _loadargs(mem.boxed, std::forward<Args>(args)...);
    return target;
  }

  inline Node * _args2list() { return Nil; }

  template<typename ... Args>
  inline Node * _args2list(Arg arg0, Args && ... args)
    { return cons(arg0.node, _args2list(std::forward<Args>(args)...)); }

  template<typename ... Args>
  Node * Node::create_partial(InfoTable const * info, Args && ... args)
  {
    unboxed_int_type const missing = int(info->arity) - int(sizeof...(args));
    assert(missing > 0);
    Node * partial = Node::create(
        &PartApplic_Info
      , missing
      , info
      , _args2list(std::forward<Args>(args)...)
      );
    return partial;
  }

  inline void Node::forward_to(Node * target)
  {
		assert(target);
		new(this) FwdNode{&Fwd_Info, target};
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
    std::stringstream ss;
    this->str(ss);
    return ss.str();
  }

  inline void Node::str(std::ostream & os)
  {
    Node * self = this;
    show(os, self, SHOW_STR);
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
    return variable(this, i).target;
  }

  inline index_type Node::size() const { return this->info->arity; }
  inline Arg * Node::begin() { return successors(); }
  inline Arg * Node::end() { return begin() + size(); }
}
