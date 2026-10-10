#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/fwd.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/rts.hpp"
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <vector>

namespace cyrt
{
  // A lookup by id that found no node.  The collector keeps every variable a
  // live configuration can still ask for (see gc/wdgc.cpp), so this is an
  // error of the runtime, not of the program.
  static std::logic_error missing_freevar(xid_type vid)
  {
    return std::logic_error(
        "free variable " + std::to_string(vid)
        + " is not in the free-variable table"
      );
  }

  // The binding of variable ``vid`` for configuration C: its own, the one
  // its queue absorbed (Queue::absorbed), or the one of the nearest
  // enclosing level that has it, read through the queue stack as read_fp
  // reads the decisions (walk_qstack).  A nested configuration, the capsule
  // of a set function, starts with an empty binding map, and a variable of
  // its goal that the enclosing configuration bound keeps its binding there.
  // Without the walk the capsule took such a variable for unbound: it bound
  // the variable anew, to the other side of its comparison, or narrowed it,
  // and the enclosing configuration then met the generator of a variable it
  // had bound (issue #97).  The key in an enclosing map is the group id of
  // the variable in that configuration.  The writers (add_binding,
  // apply_binding, update_binding) use the map of the configuration alone.
  //
  // ``level`` tells where the binding was found: 0 for the state of C and
  // its queue, k for the k-th enclosing level (the configuration there or
  // the queue it is in).  A binding above is private to the configuration
  // there, and a capsule that reads it may be shared by configurations
  // with other bindings (issue #86): a reader that puts the binding into
  // the evaluation returns diverge, and the capsule is cloned for that
  // configuration before the read takes effect.  When the binding belongs
  // to the outermost configuration and that configuration is alone in its
  // queue, no other configuration reaches the capsule, and a later clone
  // of the configuration starts with the same binding: the queue of C
  // absorbs the binding in place, and the level is 0 (the shortcut of
  // private_state in currylib/setfunctions.cpp, for the same reason).
  Node * RuntimeState::get_binding(
      Configuration * C, xid_type vid, size_t * level
    )
  {
    auto p = C->bindings->find(vid);
    if(p != C->bindings->end())
    {
      if(level)
        *level = 0;
      return p->second;
    }
    size_t const n = this->qstack.size();
    size_t k = 0;
    for(auto q=this->qstack.rbegin(), e=this->qstack.rend(); q!=e; ++q, ++k)
    {
      Queue * Q = *q;
      Node * node = nullptr;
      xid_type key = vid;
      if(k)
      {
        Configuration * outer = Q->front();
        key = outer->grp_id(vid);
        BindingMap const & bindings = *outer->bindings;
        auto r = bindings.find(key);
        if(r != bindings.end())
          node = r->second;
      }
      if(!node)
      {
        auto a = Q->absorbed.find(key);
        if(a != Q->absorbed.end())
          node = a->second;
      }
      if(node)
      {
        if(k && k == n - 1 && Q->size() == 1)
        {
          this->qstack.back()->absorbed[vid] = node;
          k = 0;
        }
        if(level)
          *level = k;
        return node;
      }
    }
    return nullptr;
  }

  Node * RuntimeState::get_generator(Configuration * C, xid_type vid)
  {
    Node * x = this->get_freevar(vid);
    if(!x)
      throw missing_freevar(vid);
    if(!has_generator(x))
    {
      xid_type gid = C->grp_id(vid);
      Node * y = this->get_freevar(gid);
      if(!y)
        throw missing_freevar(gid);
      this->constrain_equal(C, x, y, STRICT_CONSTRAINT);
      assert(has_generator(x));
    }
    return NodeU{x}.free->genexpr;
  }

  tag_type RuntimeState::replace_freevar(Configuration * C, Cursor root)
  {
    assert(C->cursor()->info->tag == T_FREE);
    xid_type vid = obj_id(C->cursor());
    xid_type gid = C->grp_id(vid);
    size_t level = 0;
    char const * kind = "binding";
    Node * node = this->get_binding(C, gid, &level);
    if(node && level)
      return this->diverge(level, gid, node);
    if(!node && this->is_narrowed(C, gid))
    {
      node = this->get_generator(C, gid);
      kind = "generator";
    }
    if(!node && vid != gid)
    {
      node = this->get_freevar(gid);
      kind = "representative";
    }
    if(node)
    {
      Node * copy = C->scan.copy_spine(root, node);
      // The checker compares the copy with the spine it replaces, which
      // the slot still holds (cyrt/checker.hpp).
      if(this->checker)
        this->checker->copied(C, root, *root, copy, node, kind);
      *root = copy;
      return E_RESTART;
    }
    else
      return T_FREE;
  }

  tag_type RuntimeState::replace_freevar(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    Cursor & slot = inductive->target;
    assert(slot->info->tag == T_FREE);
    if(has_generator(slot))
    {
      // The slot write of an existing generator, rule S.x: the checker
      // reads the reducts of the configurations that reference the redex
      // before the write and compares them after (cyrt/checker.hpp).
      Node * genexpr = this->get_generator(C, slot);
      if(this->checker)
        this->checker->instantiate_begin(C, inductive, genexpr, "slot write");
      gc_count_slot_write(slot.arg);
      *slot = genexpr;
      if(this->checker)
        this->checker->instantiate_end(C, inductive, "slot write");
      assert(slot->info->tag == T_CHOICE);
      return T_CHOICE;
    }
    xid_type const gid = C->grp_id(obj_id(slot));
    size_t level = 0;
    if(Node * binding = this->get_binding(C, gid, &level))
    {
      if(level)
        return this->diverge(level, gid, binding);
      C->scan.push(inductive);
      Node * copy = C->scan.copy_spine(C->root, binding);
      if(this->checker)
        this->checker->copied(C, C->root, *C->root, copy, binding, "binding");
      *C->root = copy;
      C->scan.pop();
      return E_RESTART;
    }
    ValueSet const * values = (ValueSet const *) guides;
    if(values && values->kind != 't')
    {
      if(values->size)
      {
        Node * bindings = this->make_value_bindings(slot, values);
        if(this->checker)
          this->checker->value_bindings(slot, bindings);
        gc_count_slot_write(slot.arg);
        *slot = bindings;
        return slot->info->tag;
      }
      else
      {
        auto vid = obj_id(inductive->target);
        C->add_residual(vid);
        return E_RESIDUAL;
      }
    }
    else
    {
      return this->instantiate(C, C->cursor(), inductive, values);
    }
  }

  Node * RuntimeState::freshvar()
  {
    xid_type vid = this->istate.xidfactory++;
    Node * x = free(vid);
    this->istate.vtable.emplace(vid, x);
    if(this->checker)
      this->checker->variable(x);
    return x;
  }

  // Registers every free variable reachable from ``root`` in the variable
  // table.  A goal built outside this evaluation can hold variables that no
  // table of this state knows: a curry.free marker shared with an earlier
  // goal, whose node the step of Prelude.unknown forwarded to a free
  // variable; the result of the single step of a compiled expression; a raw
  // Free node of curry.raw_expr; a value of an earlier evaluation.  The item
  // of a generator node is built during the evaluation, so its step walks
  // the item as well (currylib/prelude/string.cpp).  The walk is iterative
  // with a visited set, because a goal can be cyclic.  It follows forward
  // nodes and descends through every pointer successor: data, partial
  // applications, set guards, constraints, choices, and the generators of
  // free variables.  The format string of an info table names the pointer
  // successors.
  void RuntimeState::register_freevars(Node * root)
  {
    std::vector<Node *> stack;
    std::unordered_set<Node *> seen;
    stack.push_back(root);
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      if(!node || !seen.insert(node).second)
        continue;
      InfoTable const * info = node->info;
      if(info->tag == T_FREE)
        this->istate.vtable[NodeU{node}.free->vid] = node;
      Arg const * args = node->successors();
      for(index_type i=0; i<info->arity; ++i)
        if(info->format[i] == 'p')
          stack.push_back(args[i].node);
    }
  }

  Node * _clone_generator_rec(RuntimeState * rts, Node * node)
  {
    switch(node->info->tag)
    {
      case T_CHOICE:
      {
        xid_type cid = rts->istate.xidfactory++;
        return choice(
            cid
          , _clone_generator_rec(rts, NodeU{node}.choice->lhs)
          , _clone_generator_rec(rts, NodeU{node}.choice->rhs)
          );
      }
      case T_FAIL  : return Fail;
      case T_FREE  : return rts->freshvar();
      default      : assert(node->info->tag >= T_CTOR);
                     return Node::create_flat(node->info, rts);
    }
  }

  void RuntimeState::clone_generator(Node * bound, Node * unbound)
  {
    Node * genexpr = NodeU{bound}.free->genexpr;
    assert(genexpr->info == &Choice_Info);
    ChoiceNode * top_choice = NodeU{genexpr}.choice;
    Node * lhs = _clone_generator_rec(this, top_choice->lhs);
    Node * rhs = _clone_generator_rec(this, top_choice->rhs);
    xid_type vid = obj_id(unbound);
    Node * cloned = choice(vid, lhs, rhs);
    gc_count_write(unbound);
    NodeU{unbound}.free->genexpr = cloned;
    if(this->checker)
      this->checker->generator(unbound, cloned);
  }

  struct GeneratorMaker
  {
    GeneratorMaker(RuntimeState * rts) : rts(rts) {}
    RuntimeState * rts;

    Node * make(ValueSet const * values, xid_type vid) const
    {
      Node * genexpr = this->_rec(&values->args[0].xinfo, values->size, vid);
      if(values->size == 1)
        genexpr = choice(vid, genexpr, Fail);
      return genexpr;
    }

    Node * _rec(
        InfoTable const * const * ctors
      , size_t n
      , xid_type vid = NOXID
      ) const
    {
      assert(n);
      if(n == 1)
        return Node::create_flat(ctors[0], this->rts);
      else
      {
        size_t mfloor = n/2;
        size_t mceil = n - mfloor;
        xid_type cid = vid == NOXID ? this->rts->istate.xidfactory++ : vid;
        Node * lhs = this->_rec(ctors, mceil);
        Node * rhs = this->_rec(ctors + mceil, mfloor);
        return choice(cid, lhs, rhs);
      }
    }
  };

  Node * _make_generator(
      RuntimeState * rts, Node * freevar, ValueSet const * values
    )
  {
    if(!has_generator(freevar))
    {
      GeneratorMaker maker(rts);
      Node * genexpr = maker.make(values, obj_id(freevar));
      gc_count_write(freevar);
      NodeU{freevar}.free->genexpr = genexpr;
      if(rts->checker)
        rts->checker->generator(freevar, genexpr);
    }
    return NodeU{freevar}.free->genexpr;
  }

  tag_type RuntimeState::instantiate(
      Configuration * C, Cursor root, Variable * inductive
    , void const * guides
    )
  {
    ValueSet const * values = (ValueSet const *) guides;
    if(!values || values->size == 0)
    {
      auto const vid = obj_id(inductive->target);
      C->add_residual(vid);
      return E_RESIDUAL;
    }
    else
    {
      Node * genexpr = _make_generator(this, inductive->target, values);
      // The slot write of rule S.x (see replace_freevar).
      if(this->checker)
        this->checker->instantiate_begin(C, inductive, genexpr, "instantiation");
      gc_count_slot_write(inductive->target.arg);
      *inductive->target = genexpr;
      if(this->checker)
        this->checker->instantiate_end(C, inductive, "instantiation");
      assert(genexpr->info->tag == T_CHOICE);
      return T_CHOICE;
    }
  }

  bool RuntimeState::is_void(Configuration * C, Node * freevar)
  {
    assert(freevar);
    assert(freevar->info->tag == T_FREE);
    if(!has_generator(freevar))
    {
      xid_type vid = obj_id(freevar);
      xid_type gid = C->grp_id(vid);
      if(!this->get_binding(C, gid) && !this->is_narrowed(C, gid))
        return true;
    }
    return false;
  }
}

