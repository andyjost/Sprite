#pragma once
#include <algorithm>
#include "sprite/fwd.hpp"
#include "sprite/state/configuration.hpp"
#include <deque>

namespace sprite
{
  using queue_type = std::deque<Configuration*>;

  struct Queue : private queue_type
  {
    Queue(Set * set=nullptr) : queue_type(), set(set) {}
    Set * set;

    using queue_type::front;
    using queue_type::pop_front;
    using queue_type::empty;
    using queue_type::resize;
    using queue_type::begin;
    using queue_type::end;

    void push_back(Configuration * C)
		{
			if(C)
				this->queue_type::push_back(C);
		}

    void filter(xid_type cid, ChoiceState lr)
    {
      auto end = std::copy_if(
          this->begin(), this->end(), this->begin()
        , [cid,lr](Configuration * C)
          { return C->fingerprint.test2(cid, lr) == lr; }
        );
      this->resize(end - this->begin());
    }
  };
}
