#pragma once
#include <stdexcept>

namespace cyrt
{
  struct TypeError : std::invalid_argument
  {
    using std::invalid_argument::invalid_argument;
  };

  struct InstantiationError : std::logic_error
  {
    using std::logic_error::logic_error;
  };
}
