#include "sprite/fingerprint.hpp"
#include "sprite/state/rts.hpp"
#include <memory>

namespace sprite
{
  RuntimeState::RuntimeState(InterpreterState & istate, Cursor goal)
    : idfactory(istate.idfactory), setfactory(istate.setfactory)
  {
    this->push_queue(this->make_queue(), NOTRACE);
    this->set_goal(goal);
  }

  void RuntimeState::append(Configuration * config)
  {
    this->Q().push_back(config);
  }

  void RuntimeState::drop(TraceOpt /*trace*/)
  {
    this->Q().pop_front();
  }

  Expr RuntimeState::make_value()
  {
    // if value is IO...
    return copy_graph(this->E(), SKIPFWD, this->sid());
  }

  void RuntimeState::set_goal(Cursor goal)
  {
    auto config = Configuration::create(goal);
    this->append(config.release());
  }

  bool RuntimeState::ready()
  {
    return !this->Q().empty();
  }

  Expr RuntimeState::release_value()
  {
    Expr value = this->make_value();
    this->drop(NOTRACE);
    return value;
  }

  void RuntimeState::forkD(Queue * Q)
  {
    assert(Q == &this->Q());
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

  void RuntimeState::forkN(Queue * Q)
  {
    assert(Q == &this->Q());
    Configuration * C = Q->front();
    auto && state = C->callstack.state;
    ChoiceNode * tgt = NodeU{state.cursor()->node}.choice;
    Node * lhs = state.copy_spine(tgt->lhs);
    Node * rhs = state.copy_spine(tgt->rhs);
    Node * repl = make_node<ChoiceNode>(tgt->cid, lhs, rhs);
    C->root->node->forward_to(repl);
    C->reset();
  }

  bool RuntimeState::update_fp(Configuration * C, cid_type cid, ChoiceState lr)
  {
    switch(lr)
    {
      case LEFT:
        switch(this->read_fp(cid, C))
        {
          case RIGHT:    return false;
          case UNDETERMINED: C->fingerprint.set_left(cid);
          case LEFT:     return true;
          default: assert(0); __builtin_unreachable();
        }
      case RIGHT:
        switch(this->read_fp(cid, C))
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

  ChoiceState RuntimeState::read_fp(cid_type cid, Configuration * C)
  {
    return C->fingerprint.test(cid);
  }


  // void RuntimeState::pull_tab(Configuration * C)
  // {
  // }

  // Set Functions
  Queue * RuntimeState::make_queue(sid_type sid)
  {
    Queue * q = Queue::create(sid);
    this->qtable[this->setfactory++] = q;
    return q;
  }

  void RuntimeState::push_queue(Queue * queue, TraceOpt /*trace*/)
  {
    assert(queue);
    this->qstack.push_back(queue);
  }
}
