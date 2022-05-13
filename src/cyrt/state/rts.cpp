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

  void RuntimeState::set_error_msg(std::string const & msg)
  {
    assert(msg.size());
    assert(!this->_error_msg.size());
    this->_error_msg = msg;
  }

  std::string RuntimeState::pop_error_msg()
  {
    assert(this->_error_msg.size());
    std::string tmp;
    std::swap(tmp, this->_error_msg);
    return tmp;
  }
}
