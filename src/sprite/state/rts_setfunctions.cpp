#include "sprite/state/rts.hpp"

namespace sprite
{
  Queue * RuntimeState::make_queue(sid_type sid)
  {
    Queue * q = Queue::create(sid);
    this->qtable[this->setfactory++] = q;
    return q;
  }

  void RuntimeState::push_queue(Queue * queue, TraceOpt /*trace*/)
  {
    assert(queue);
    this->qstack.push_back(queue);
  }
}
