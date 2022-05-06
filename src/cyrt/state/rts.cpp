#include "cyrt/state/rts.hpp"
#include "cyrt/trace.hpp"

namespace cyrt
{
  RuntimeState::RuntimeState(InterpreterState & istate, Node * goal, bool trace)
    : istate(istate)
  {
    this->push_queue(new Queue(), NOTRACE);
    this->set_goal(goal);
		#ifdef SPRITE_TRACE_ENABLED
		if(trace)
		  this->trace.reset(new Trace(*this));
    #endif
  }
}
