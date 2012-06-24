#pragma once
#include "sprite/exec.hpp"

namespace sprite
{
  struct CmdlineOptions
  {
    TraceOption trace;
  };

  /// Parses the command line options.
  CmdlineOptions parse_options(int argc, char * argv[]);
}
