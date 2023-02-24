#include "cyrt/exceptions.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/state/rts.hpp"

namespace cyrt
{
  void RuntimeState::append(Configuration * config)
  {
    this->Q()->push_back(config);
  }

  void RuntimeState::prepend(Configuration * config)
  {
    this->Q()->push_front(config);
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

  static bool _make_ready(RuntimeState * rts, Configuration * C)
  {
    if(C->forced_rotate)
    {
      C->forced_rotate = false;
      return true;
    }
    if(C->residuals.empty())
      return true;
    Residuals remaining;
    for(auto vid: C->residuals)
    {
      Node * var = rts->vtable[vid];
      if(rts->is_void(C, var))
        remaining.insert(vid);
    }
    if(remaining.size() < C->residuals.size())
    {
      C->residuals.swap(remaining);
      return true;
    }
    else
      return false;
  }

  bool RuntimeState::ready()
  {
    Queue * Q = this->Q();
    size_t const N = Q->size();
    if(!N)
      return false;
    Configuration * C = nullptr;
    for(size_t i=0; i<N; ++i)
    {
      C = Q->front();
      if(_make_ready(this, C))
        return true;
      else
        this->rotate(Q);
    }
    throw EvaluationSuspended("");
  }

  Expr RuntimeState::release_value()
  {
    Expr value = this->make_value();
    #ifdef SPRITE_TRACE_ENABLED
    if(this->trace) this->trace->yield(value);
    #endif
    this->drop(NOTRACE);
    return value;
  }

  void RuntimeState::rotate(Queue * Q, bool forced)
  {
    assert(Q);
    if(forced)
      Q->front()->forced_rotate = true;
    if(Q->size() > 1)
    {
      Q->push_back(Q->front());
      Q->pop_front();
    }
  }

  void RuntimeState::set_goal(Node * goal)
  {
    auto config = Configuration::create(goal);
    this->prepend(config.get());
    config.release();
  }
}
