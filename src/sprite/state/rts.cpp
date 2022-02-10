#include "sprite/state/rts.hpp"

namespace sprite
{
  RuntimeState::RuntimeState(InterpreterState & istate, Cursor goal)
    : istate(istate)
  {
    this->push_queue(new Queue(), NOTRACE);
    this->set_goal(goal);
  }
}
