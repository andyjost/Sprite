#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/fwd.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/state/configuration.hpp"
#include "sprite/state/rts.hpp"

namespace sprite
{
  Node * RuntimeState::get_binding(Configuration * C, id_type vid)
  {
    auto p = C->bindings->find(vid);
    return p == C->bindings->end() ? nullptr : p->second;
  }

  Node * RuntimeState::get_generator(Configuration * C, id_type vid)
  {
    Node * x = this->get_freevar(vid);
    if(!has_generator(x))
    {
      id_type gid = C->grp_id(vid);
      Node * y = this->get_freevar(gid);
      this->constrain_equal(C, x, y, STRICT_CONSTRAINT);
      assert(has_generator(x));
    }
    return NodeU{x}.free->genexpr;
  }

  bool RuntimeState::replace_freevar(Configuration * C)
  {
    assert(C->cursor().info()->tag == T_FREE);
    id_type vid = obj_id(C->cursor());
    id_type gid = C->grp_id(vid);
    Node * node = this->get_binding(C, gid);
    if(!node && this->is_narrowed(C, gid))
      node = this->get_generator(C, vid);
    if(!node && vid != gid)
      node = this->get_freevar(gid);
    if(node)
      // *C->root = node;
      *C->root = C->callstack.search.copy_spine(C->root, node);
    return node;
  }

  StepStatus RuntimeState::replace_freevar(
      Configuration * C, Cursor & inductive, Values const * values
    )
  {
    assert(inductive.info()->tag == T_FREE);
    if(has_generator(inductive))
    {
      *inductive = this->get_generator(C, inductive);
      return E_OK;
    }
    else if(Node * binding = this->get_binding(C, inductive))
    {
      *C->root = C->callstack.search.copy_spine(C->root, binding);
      return E_RESTART;
    }
    else if(values && values->is_builtin())
    {
      if(values->size)
      {
        *inductive = this->make_value_bindings(inductive, values);
        return E_OK;
      }
      else
        return E_RESIDUAL;
    }
    else
      return this->instantiate(C, C->cursor(), inductive, values);
  }
  
  Node * RuntimeState::freshvar()
  {
    id_type vid = this->idfactory++;
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
        id_type cid = rts->idfactory++;
        return choice(
            cid
          , _clone_generator_rec(rts, NodeU{node}.choice->lhs)
          , _clone_generator_rec(rts, NodeU{node}.choice->rhs)
          );
      }
      case T_FAIL  : return fail();
      case T_FREE  : return rts->freshvar();
      default      : assert(0); __builtin_unreachable();
    }
  }

  void RuntimeState::clone_generator(Node * bound, Node * unbound)
  {
    Node * genexpr = NodeU{bound}.free->genexpr;
    assert(genexpr->info == &Choice_Info);
    ChoiceNode * top_choice = NodeU{genexpr}.choice;
    Node * lhs = _clone_generator_rec(this, top_choice->lhs);
    Node * rhs = _clone_generator_rec(this, top_choice->rhs);
    id_type vid = obj_id(unbound);
    NodeU{unbound}.free->genexpr = choice(vid, lhs, rhs);
  }

  struct GeneratorMaker
  {
    GeneratorMaker(RuntimeState * rts) : rts(rts) {}
    RuntimeState * rts;

    Node * make(Values const * values, id_type vid) const
    {
      Node * genexpr = this->_rec(&values->args[0].info, values->size, vid);
      if(values->size == 1)
        genexpr = choice(vid, genexpr, fail());
      return genexpr;
    }

    Node * _rec(
        InfoTable const * const * ctors
      , size_t n
      , id_type vid = NOVID
      ) const
    {
      assert(n);
      if(n == 1)
        return Node::create(ctors[0], rts->idfactory);
      else
      {
        size_t mfloor = n/2;
        size_t mceil = n - mfloor;
        id_type cid = vid == NOVID ? rts->idfactory++ : vid;
        return choice(
            cid
          , this->_rec(ctors, mceil)
          , this->_rec(ctors + mceil, mfloor)
          );
      }
    }
  };

  Node * _make_generator(
      RuntimeState * rts, Node * redex, Node * inductive, Values const * values
    )
  {
    if(!has_generator(inductive))
    {
      GeneratorMaker maker(rts);
      Node * genexpr = maker.make(values, obj_id(inductive));
      NodeU{inductive}.free->genexpr = genexpr;
    }
    return NodeU{inductive}.free->genexpr;
  }

  StepStatus RuntimeState::instantiate(
      Configuration * C, Node * redex, Node * inductive
    , Values const * values
    )
  {
    assert(values && values->kind == 't');
    if(values->size == 0)
      return E_RESIDUAL;
    else
    {
      Node * genexpr = _make_generator(this, redex, inductive, values);
      Node * replacement = C->callstack.search.copy_spine(redex, genexpr);
      redex->forward_to(replacement);
      return E_OK;
    }
  }
}

