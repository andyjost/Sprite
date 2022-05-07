#include "cyrt/fingerprint.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  void RuntimeState::append(Configuration * config)
  {
    this->Q()->push_back(config);
  }

  void RuntimeState::drop(TraceOpt trace)
  {
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace)
      this->trace->failed(this->Q());
    #endif
    this->Q()->pop_front();
  }

  Expr RuntimeState::make_value()
  {
    // if value is IO...
    return copy_graph(this->E(), SKIPFWD, this->S());
  }

  bool RuntimeState::ready()
  {
    return !this->Q()->empty();
  }

  Expr RuntimeState::release_value()
  {
    Expr value = this->make_value();
    #ifdef SPRITE_TRACE_ENABLED
    this->trace->yield(value);
    #endif
    this->drop(NOTRACE);
    return value;
  }

  void RuntimeState::set_goal(Node * goal)
  {
    auto config = Configuration::create(goal);
    this->append(config.get());
    config.release();
  }
}
