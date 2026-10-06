#include <cassert>
#include "cyrt/builtins.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/state/rts.hpp"
#include <utility>

namespace cyrt
{
  bool RuntimeState::equate_fp(Configuration * C, xid_type i, xid_type j)
  {
    return this->update_fp(C, i, this->read_fp(C, j))
        && this->update_fp(C, j, this->read_fp(C, i));
  }

  static bool is_consistent(Fingerprint const & fp, xid_type id, ChoiceState expected)
  {
    ChoiceState lr = fp.test_no_check(id);
    return lr == UNDETERMINED || lr == expected;
  }

  void RuntimeState::fork(Queue * Q, Configuration * C)
  #ifdef SPRITE_TRACE_ENABLED
  {
    if(this->trace)
    {
      auto _ = this->trace->guard_fork(Q);
      this->_fork(Q, C);
    }
    else
      this->_fork(Q, C);
  }

  void RuntimeState::_fork(Queue * Q, Configuration * C)
  #endif
  {
    assert(Q == this->Q());
    ++this->forks_total;
    ChoiceNode * choice = NodeU{C->root}.choice;
    auto && process_one = [this,Q,C,choice](Node * alt, ChoiceState lr) -> void
    {
      auto copy = C->clone(alt);
      if(this->update_fp(copy.get(), choice->cid, lr))
      {
        xid_type gid = copy->grp_id(choice->cid);
        // A choice with the id of a free variable is the generator of that
        // variable.  The collector keeps a variable whose id a binding or a
        // group of the configuration names (see gc/wdgc.cpp); an entry it
        // dropped had neither, so the steps below would change nothing.
        Node * x = this->get_freevar(choice->cid);
        Node * y = x ? this->get_freevar(gid) : nullptr;
        assert(!x || y);
        if(x && y)
        {
          this->apply_binding(copy.get(), choice->cid);
          this->apply_binding(copy.get(), gid);
          if(!this->constrain_equal(copy.get(), x, y, STRICT_CONSTRAINT))
            return;
        }
        // The enclosing configurations prune the alternatives of a nested
        // fork (walk_qstack).  A choice that no enclosing configuration
        // decided is encapsulated: both alternatives stay.  A choice that
        // an enclosing configuration decided, or that is in an escape set,
        // escaped from this queue before it forks here (choice_escapes),
        // and the split bound the queue to one side (Queue::decisions): the
        // walk prunes the other alternative, to the side of the enclosing
        // configuration that runs this queue.  So the walk reads an
        // enclosing decision only for a choice whose escape split this
        // queue.
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
        Q->push_back(std::move(copy));
      }
    };
    process_one(choice->lhs, LEFT);
    process_one(choice->rhs, RIGHT);
    // The alternatives are in the queue.  The parent is destroyed.
    SCHEDULER_COUNT_END(C, END_FORK);
    Q->pop_front();
    #ifdef SPRITE_SCHEDULER_COUNTERS
    if(!this->in_recursive_call() && Q->size() > this->counters.queue_max)
      this->counters.queue_max = Q->size();
    #endif
  }

  Node * RuntimeState::pull_tab(Configuration * C, Node * source, Node * target)
  {
    assert(source != target);
    assert(target->info->tag == T_CHOICE);
    ChoiceNode * choice = NodeU{target}.choice;
    Node * lhs = C->scan.copy_spine(source, choice->lhs, choice->cid);
    Node * rhs = C->scan.copy_spine(source, choice->rhs, choice->cid);
    return make_node<ChoiceNode>(choice->cid, lhs, rhs);
  }

  Node * RuntimeState::pull_tab(Configuration * C, Variable * inductive)
  {
    assert(inductive->target->info->tag == T_CHOICE);
    Node * source = C->cursor().arg->node;
    C->scan.push(inductive);
    auto result = RuntimeState::pull_tab(C, source, inductive->target);
    C->scan.pop();
    return result;
  }

  ChoiceState RuntimeState::read_fp(Configuration * C, xid_type cid)
  {
    auto gid = C->grp_id(cid);
    auto lr = C->fingerprint.test(gid);
    if(lr == UNDETERMINED)
    {
      // walk_qstack: a nested configuration starts with an empty
      // fingerprint and reads the decisions of the enclosing configurations
      // for the choices it did not decide itself (see fork).
      for(auto p=this->qstack.rbegin()+1, e=this->qstack.rend(); p!=e; ++p)
      {
        lr = (*p)->front()->fingerprint.test(gid);
        if(lr != UNDETERMINED)
          break;
      }
    }
    return lr;
  }

  bool RuntimeState::update_fp(Configuration * C, xid_type cid, ChoiceState lr)
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
