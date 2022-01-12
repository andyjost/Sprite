#pragma once
#include "sprite/fwd.hpp"
#include "sprite/state/configuration.hpp"
#include <deque>

namespace sprite
{
  using queue_type = std::deque<Configuration*>;

  struct Queue : queue_type
  {
    Queue(sid_type sid=NOSID) : queue_type(), sid(sid) {}

    template<typename ... Args>
    static Queue * create(Args && ... args)
      { return new Queue(std::forward<Args>(args)...); }

    sid_type   sid;
  };
}
