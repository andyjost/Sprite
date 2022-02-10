#include "sprite/state/rts.hpp"

namespace sprite
{
  Queue * RuntimeState::make_queue(sid_type sid)
  {
    auto qid = this->istate.qidfactory++;
    Queue * q = Queue::create(qid, sid);
    this->qtable[qid] = q;
    return q;
  }

  void RuntimeState::push_queue(Queue * queue, TraceOpt /*trace*/)
  {
    assert(queue);
    this->qstack.push_back(queue);
  }
}
