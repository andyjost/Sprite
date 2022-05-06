#include "cyrt/state/rts.hpp"

namespace cyrt
{
  void RuntimeState::push_queue(Queue * queue, TraceOpt trace)
  {
    assert(queue);
    this->qstack.push_back(queue);
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace)
      this->trace->activate_queue(queue);
    #endif
  }

  void RuntimeState::pop_queue(TraceOpt trace)
  {
    this->qstack.pop_back();
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace && !this->qstack.empty())
      this->trace->activate_queue(this->Q());
    #endif
  }

  bool RuntimeState::choice_escapes(Configuration * C, xid_type cid)
  {
    Set * S = this->S();
    if((S && S->escape_set.count(cid)) || C->escape_all)
    {
      for(auto p=this->qstack.rbegin()+1, e=this->qstack.rend(); p!=e; ++p)
        if((*p)->front()->fingerprint.choice_is_made(cid))
          return false;
      return true;
    }
    return false;
  }
}
