#pragma once
#include <cassert>
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
    Node * target = (Node *) node_alloc(info->alloc_size);
    assert(target);
    RawNodeMemory mem{target};
    *mem.info++ = info;
    *mem.boxed++ = arg0.node;
    _loadargs(mem.boxed, std::forward<Args>(args)...);
    return target;
  }

  inline Node * _args2list_rev(Arg arg) { return arg.node; }

  template<typename ... Args>
  inline Node * _args2list_rev(Arg arg0, Arg arg1, Args && ... args)
    { return _args2list_rev(cons(arg1.node, arg0.node), std::forward<Args>(args)...); }

  template<typename ... Args>
  Node * Node::create_partial(InfoTable const * info, Args && ... args)
  {
    unboxed_int_type const missing = int(info->arity) - int(sizeof...(args));
    assert(missing > 0);
    Node * partial = Node::create(
        &PartApplic_Info
      , missing
      , info
      , _args2list_rev(Nil, std::forward<Args>(args)...)
      );
    return partial;
  }

  inline void Node::forward_to(Node * target)
  {
		assert(target);
    static_assert(std::is_trivially_destructible<Node>::value, "");
		new(this) FwdNode{&Fwd_Info, target};
	}

  template<typename ... Args>
  void Node::forward_to(InfoTable const * info, Args && ... args)
  {
    Node * target = Node::create(info, std::forward<Args>(args)...);
    this->forward_to(target);
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

  inline index_type Node::size() const { return this->info->arity; }
  inline Arg * Node::begin() { return successors(); }
  inline Arg * Node::end() { return begin() + size(); }
  inline std::size_t Node::hash() const { return std::hash<Node const *>()(this); }
  inline bool Node::operator!=(Node & arg) { return !(*this == arg); }
}
