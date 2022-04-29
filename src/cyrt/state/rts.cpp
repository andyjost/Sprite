#include "cyrt/state/rts.hpp"

namespace cyrt
{
  RuntimeState::RuntimeState(InterpreterState & istate, Node * goal)
    : istate(istate)
  {
    this->push_queue(new Queue(), NOTRACE);
    this->set_goal(goal);
  }
}
