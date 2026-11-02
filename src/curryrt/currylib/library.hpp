#pragma once
#include <string>
#include "curryrt/fwd.hpp"

namespace curryrt
{
  bool is_io_ref(InfoTable const * info);

  // Supplied by the Python runtime at startup, including relocated installs.
  void set_install_prefix(std::string const & prefix);
}
