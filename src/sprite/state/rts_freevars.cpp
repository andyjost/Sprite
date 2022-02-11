#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/fwd.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/state/configuration.hpp"
#include "sprite/state/rts.hpp"

namespace sprite
{
  Node * RuntimeState::get_binding(Configuration * C, xid_type vid)
  {
    auto p = C->bindings->find(vid);
    return p == C->bindings->end() ? nullptr : p->second;
  }

  Node * RuntimeState::get_generator(Configuration * C, xid_type vid)
  {
    Node * x = this->get_freevar(vid);
    if(!has_generator(x))
    {
      xid_type gid = C->grp_id(vid);
      Node * y = this->get_freevar(gid);
      this->constrain_equal(C, x, y, STRICT_CONSTRAINT);
      assert(has_generator(x));
    }
    return NodeU{x}.free->genexpr;
  }

  Node * RuntimeState::replace_freevar(Configuration * C)
  {
    assert(C->cursor().info()->tag == T_FREE);
    xid_type vid = obj_id(C->cursor());
    xid_type gid = C->grp_id(vid);
    Node * node = this->get_binding(C, gid);
    if(!node && this->is_narrowed(C, gid))
      node = this->get_generator(C, gid);
    if(!node && vid != gid)
      node = this->get_freevar(gid);
    return node ? C->search.copy_spine(C->root, node) : node;
  }

  SStatus RuntimeState::replace_freevar(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    Cursor & freevar = inductive->target();
    assert(freevar.info()->tag == T_FREE);
    if(has_generator(freevar))
    {
      *freevar = this->get_generator(C, freevar);
      assert(freevar.info()->tag == T_CHOICE);
      return T_CHOICE;
    }
    else if(Node * binding = this->get_binding(C, freevar))
    {
      *C->root = C->search.copy_spine(C->root, binding);
      return E_RESTART;
    }
    ValueSet const * values = (ValueSet const *) guides;
    if(values && values->kind != 't')
    {
      if(values->size)
      {
        *freevar = this->make_value_bindings(freevar, values);
        return freevar.info()->tag;
      }
      else
        return E_RESIDUAL;
    }
    else
    {
      Node * root = C->cursor();
      return this->instantiate(C, root, inductive, values);
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
      case T_FAIL  : return fail();
      case T_FREE  : return rts->freshvar();
      default      : assert(node->info->tag >= T_CTOR);
                     return Node::create(node->info, rts->istate.xidfactory);
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
    GeneratorMaker(xid_type & xidfactory) : xidfactory(xidfactory) {}
    xid_type & xidfactory;

    Node * make(ValueSet const * values, xid_type vid) const
    {
      Node * genexpr = this->_rec(&values->args[0].info, values->size, vid);
      if(values->size == 1)
        genexpr = choice(vid, genexpr, fail());
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
        return Node::create(ctors[0], xidfactory);
      else
      {
        size_t mfloor = n/2;
        size_t mceil = n - mfloor;
        xid_type cid = vid == NOXID ? xidfactory++ : vid;
        return choice(
            cid
          , this->_rec(ctors, mceil)
          , this->_rec(ctors + mceil, mfloor)
          );
      }
    }
  };

  Node * _make_generator(
      RuntimeState * rts, Node * freevar, ValueSet const * values
    )
  {
    if(!has_generator(freevar))
    {
      GeneratorMaker maker(rts->istate.xidfactory);
      Node * genexpr = maker.make(values, obj_id(freevar));
      NodeU{freevar}.free->genexpr = genexpr;
    }
    return NodeU{freevar}.free->genexpr;
  }

  SStatus RuntimeState::instantiate(
      Configuration * C, Node * root, Variable * inductive
    , void const * guides
    )
  {
    ValueSet const * values = (ValueSet const *) guides;
    if(!values || values->size == 0)
      return E_RESIDUAL;
    else
    {
      Redex tmp_frame(*inductive);
      Node * genexpr = _make_generator(this, inductive->target(), values);
      Cursor target;
      Node * replacement = C->search.copy_spine(root, genexpr, &target);
      inductive->target() = target;
      assert(inductive->target()->node = genexpr);
      root->forward_to(replacement);
      return T_FWD;
    }
  }
}

