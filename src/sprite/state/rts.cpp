#include "sprite/state/rts.hpp"

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
    return copygraph(this->E(), SKIPFWD, this->sid());
  }

  void RuntimeState::set_goal(Cursor goal)
  {
    auto * config = Configuration::create(goal);
    this->append(config);
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
