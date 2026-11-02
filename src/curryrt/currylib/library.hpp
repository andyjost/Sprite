#pragma once
#include <string>
#include <functional>
#include "curryrt/fwd.hpp"

namespace curryrt
{
  bool is_handle(InfoTable const * info);
  void release_handle(Node * node);
  void gc_register_handle(Node * node);
  // The Python host supplies current standard streams; files stay in C++.
  using stream_hook = std::function<std::string(int, std::string const &,
                                               std::string const &, long long)>;
  void set_stream_hook(stream_hook hook);
  std::string standard_stream(int stream, std::string const & operation,
                              std::string const & text = "", long long value = 0);
  bool is_io_ref(InfoTable const * info);

  // Supplied by the Python runtime at startup, including relocated installs.
  void set_install_prefix(std::string const & prefix);
}
