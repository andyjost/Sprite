#include "sprite/state/rts.hpp"

namespace sprite
{
  void RuntimeState::push_queue(Queue * queue, TraceOpt /*trace*/)
  {
    assert(queue);
    this->qstack.push_back(queue);
  }

  void RuntimeState::pop_queue(TraceOpt /*trace*/)
  {
    this->qstack.pop_back();
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
