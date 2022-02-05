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

  void RuntimeState::forkD(Queue * Q)
  {
    assert(Q == this->Q());
    Configuration * C = Q->front();
    ChoiceNode * choice = NodeU{C->root->node}.choice;

    auto copy = C->clone(choice->lhs);
    if(this->update_fp(copy.get(), choice->cid, LEFT))
      Q->push_back(copy.release());

    copy = C->clone(choice->rhs);
    if(this->update_fp(copy.get(), choice->cid, RIGHT))
      Q->push_back(copy.release());

    Q->pop_front();
  }

  Node * RuntimeState::pull_tab(Configuration * C, Node * root)
  {
    auto & search = C->callstack.search;
    ChoiceNode * target = NodeU{search.cursor()->node}.choice;
    Node * lhs = search.copy_spine(root, target->lhs);
    Node * rhs = search.copy_spine(root, target->rhs);
    Node * repl = make_node<ChoiceNode>(target->cid, lhs, rhs);
    return repl;
    // C->reset(&repl);
  }

  // void RuntimeState::pull_tabS(Configuration * C, Node * root)
  // {
  //   assert(root->info->tag == T_FUNC);
  //   auto & search = C->callstack.search;
  //   ChoiceNode * target = NodeU{search.cursor()->node}.choice;
  //   Node * lhs = search.copy_spine(root, target->lhs);
  //   Node * rhs = search.copy_spine(root, target->rhs);
  //   Node * replacement = choice(target->cid, lhs, rhs);
  //   root->forward_to(replacement);
  // }

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
          case RIGHT:    return false;
          case UNDETERMINED: C->fingerprint.set_left(cid);
          case LEFT:     return true;
          default: assert(0); __builtin_unreachable();
        }
      case RIGHT:
        switch(this->read_fp(C, cid))
        {
          case LEFT:     return false;
          case UNDETERMINED: C->fingerprint.set_right(cid);
          case RIGHT:    return true;
          default: assert(0); __builtin_unreachable();
        }
      case UNDETERMINED: return true;
      default: assert(0); __builtin_unreachable();
    }
  }
}
