#include "sprite/state/rts.hpp"

namespace sprite
{
  RuntimeState::RuntimeState(InterpreterState & istate, Cursor goal)
    : istate(istate)
  {
    this->push_queue(this->make_queue(), NOTRACE);
    this->set_goal(goal);
  }
}
