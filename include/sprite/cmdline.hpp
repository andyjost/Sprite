#pragma once
#include "sprite/exec.hpp"

namespace sprite
{
  /**
   * @brief The bundle of command line options.
   *
   * See cmdline.cpp for detailed documentation.
   */
  struct CmdlineOptions
  {
    size_t grain;
    TraceOption trace;
    int verbosity;
    int fastnormalize;  
  };

  /// Parses the command line options.
  CmdlineOptions parse_options(int argc, char * argv[]);
}
