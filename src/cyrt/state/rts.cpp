#include "cyrt/graph/memory.hpp"
#include "cyrt/state/rts.hpp"
#include "cyrt/trace.hpp"

namespace cyrt
{
  RuntimeState::RuntimeState(
      InterpreterState & istate, Node * goal, bool trace
    , SetFStrategy setfunction_strategy
    )
    : istate(istate), setfunction_strategy(setfunction_strategy)
  {
    this->push_queue(new Queue(), NOTRACE);
    this->set_goal(goal);
		#ifdef SPRITE_TRACE_ENABLED
		if(trace)
		  this->trace.reset(new Trace(*this));
    #endif
    gc::register_rts(this);
  }

  RuntimeState::~RuntimeState()
  {
    gc::unregister_rts(this);
  }
}
