#include "sprite/builtins.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/state/rts.hpp"

namespace sprite
{
  bool RuntimeState::equate_fp(Configuration * C, id_type i, id_type j)
  {
    return this->update_fp(C, i, this->read_fp(C, j))
        && this->update_fp(C, j, this->read_fp(C, i));
  }

  static bool is_consistent(Fingerprint const & fp, id_type id, ChoiceState expected)
  {
    ChoiceState lr = fp.test_no_check(id);
    return lr == UNDETERMINED || lr == expected;
  }

  void RuntimeState::fork(Queue * Q, Configuration * C)
  {
    assert(Q == this->Q());
    ChoiceNode * choice = NodeU{C->root->node}.choice;
    auto && process_one = [this,Q,C,choice](Node * alt, ChoiceState lr) -> void
    {
      auto copy = C->clone(alt);
      if(this->update_fp(copy.get(), choice->cid, lr))
      {
        id_type gid = copy->grp_id(choice->cid);
        if(this->vtable.count(choice->cid))
        {
          this->apply_binding(copy.get(), choice->cid);
          this->apply_binding(copy.get(), gid);
          if(!this->constrain_equal(
              copy.get(), this->get_freevar(choice->cid), this->get_freevar(gid)
            , STRICT_CONSTRAINT
            ))
            return;
        }
        // walk_qstack
        if(!is_consistent(copy->fingerprint, choice->cid, lr))
          return;
        if(!is_consistent(copy->fingerprint, gid, lr))
          return;
        for(auto p=this->qstack.rbegin()+1, e=this->qstack.rend(); p!=e; ++p)
        {
          if(!is_consistent((*p)->front()->fingerprint, choice->cid, lr))
            return;
          if(!is_consistent((*p)->front()->fingerprint, gid, lr))
            return;
        }
        Q->push_back(copy.release());
      }
    };
    process_one(choice->lhs, LEFT);
    process_one(choice->rhs, RIGHT);
    Q->pop_front();
  }

  Node * RuntimeState::pull_tab(Configuration * C, Node * source, Node * target)
  {
    auto & search = C->callstack.search;
    ChoiceNode * choice = NodeU{target}.choice;
    Node * lhs = search.copy_spine(source, choice->lhs);
    Node * rhs = search.copy_spine(source, choice->rhs);
    return make_node<ChoiceNode>(choice->cid, lhs, rhs);
  }

  Node * RuntimeState::pull_tab(Configuration * C, Variable * inductive)
  {
    Redex scope(*inductive);
    return RuntimeState::pull_tab(C, inductive->root(), inductive->target());
  }

  ChoiceState RuntimeState::read_fp(Configuration * C, id_type cid)
  {
    auto gid = C->grp_id(cid);
    auto lr = C->fingerprint.test(gid);
    if(lr == UNDETERMINED)
    {
      // walk_qstack:
      for(auto p=this->qstack.rbegin()+1, e=this->qstack.rend(); p!=e; ++p)
      {
        lr = (*p)->front()->fingerprint.test(gid);
        if(lr != UNDETERMINED)
          break;
      }
    }
    return lr;
  }

  bool RuntimeState::update_fp(Configuration * C, id_type cid, ChoiceState lr)
  {
    switch(lr)
    {
      case LEFT:
        switch(this->read_fp(C, cid))
        {
          case RIGHT:        return false;
          case UNDETERMINED: C->fingerprint.set_left(cid);
                             C->fingerprint.set_left(C->grp_id(cid));
          case LEFT:         return true;
          default: assert(0); __builtin_unreachable();
        }
      case RIGHT:
        switch(this->read_fp(C, cid))
        {
          case LEFT:         return false;
          case UNDETERMINED: C->fingerprint.set_right(cid);
                             C->fingerprint.set_right(C->grp_id(cid));
          case RIGHT:        return true;
          default: assert(0); __builtin_unreachable();
        }
      case UNDETERMINED: return true;
      default: assert(0); __builtin_unreachable();
    }
  }
}
