#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/fwd.hpp"
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

  bool RuntimeState::replace_freevar(Configuration * C, Cursor & cur)
  {
    assert(cur.info()->tag == T_FREE);
    id_type vid = obj_id(cur->node);
    id_type gid = C->grp_id(vid);
    Node * node = this->get_binding(C, gid);
    if(!node && this->is_narrowed(C, gid))
      node = this->get_generator(C, vid);
    if(node)
      *C->root = node;
    return node;
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
}

