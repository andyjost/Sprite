#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/fwd.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  Node * RuntimeState::get_binding(Configuration * C, xid_type vid)
  {
    auto p = C->bindings->find(vid);
    return p == C->bindings->end() ? nullptr : p->second;
  }

  Node * RuntimeState::get_generator(Configuration * C, xid_type vid)
  {
    Node * x = this->get_freevar(vid);
    assert(x);
    if(!has_generator(x))
    {
      xid_type gid = C->grp_id(vid);
      Node * y = this->get_freevar(gid);
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
    Node * node = this->get_binding(C, gid);
    if(!node && this->is_narrowed(C, gid))
      node = this->get_generator(C, gid);
    if(!node && vid != gid)
      node = this->get_freevar(gid);
    if(node)
    {
      *root = C->scan.copy_spine(root, node);
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
      *slot = this->get_generator(C, slot);
      assert(slot->info->tag == T_CHOICE);
      return T_CHOICE;
    }
    else if(Node * binding = this->get_binding(C, slot))
    {
      C->scan.push(inductive);
      *C->root = C->scan.copy_spine(C->root, binding);
      C->scan.pop();
      return E_RESTART;
    }
    ValueSet const * values = (ValueSet const *) guides;
    if(values && values->kind != 't')
    {
      if(values->size)
      {
        *slot = this->make_value_bindings(slot, values);
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
    this->vtable[vid] = x;
    return x;
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
    NodeU{unbound}.free->genexpr = choice(vid, lhs, rhs);
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
      NodeU{freevar}.free->genexpr = genexpr;
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
      *inductive->target = genexpr;
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
      if(!C->has_binding(gid) && !this->is_narrowed(C, gid))
        return true;
    }
    return false;
  }
}

