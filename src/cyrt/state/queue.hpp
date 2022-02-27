#pragma once
#include <algorithm>
#include "cyrt/fwd.hpp"
#include "cyrt/state/configuration.hpp"
#include <deque>

namespace cyrt
{
  using queue_type = std::deque<Configuration*>;

  struct Queue : private queue_type
  {
    Queue(Set * set=nullptr, Node * root=nullptr)
      : queue_type(), set(set)
    {
      if(root)
        this->push_back(new Configuration(root));
    }

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
  };
}
