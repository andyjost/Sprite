#pragma once
#include "sprite/fwd.hpp"
#include "sprite/state/configuration.hpp"
#include <deque>

namespace sprite
{
  using queue_type = std::deque<Configuration*>;

  struct Queue : private queue_type
  {
    Queue(qid_type qid, sid_type sid)
      : queue_type(), qid(qid), sid(sid)
    {}

    template<typename ... Args>
    static Queue * create(Args && ... args)
      { return new Queue(std::forward<Args>(args)...); }

    qid_type qid;
    sid_type sid;

    using queue_type::front;
    using queue_type::pop_front;
    using queue_type::empty;

    void push_back(Configuration * C)
		{
			if(C)
				this->queue_type::push_back(C);
		}
  };
}
