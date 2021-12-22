#pragma once
#include <stdexcept>

namespace sprite
{
  struct TypeError : std::invalid_argument
  {
    using std::invalid_argument::invalid_argument;
  };
}
