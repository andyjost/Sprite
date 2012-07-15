#pragma once
#include "sprite/exec.hpp"

namespace sprite
{
  struct CmdlineOptions
  {
    size_t grain;
    TraceOption trace;
    int verbosity;
  };

  /// Parses the command line options.
  CmdlineOptions parse_options(int argc, char * argv[]);
}
