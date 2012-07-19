#include "sprite/cmdline.hpp"
#include <boost/program_options.hpp>
#include <iostream>
#include <iomanip>
#include <limits>

namespace sprite
{
  CmdlineOptions parse_options(int argc, char * argv[])
  {
    namespace opt = boost::program_options;
    opt::options_description desc("Allowed options");
    desc.add_options()
        ("fast-normalize,f"
           , opt::value<int>()->implicit_value(1)->default_value(0)
           , "Replaces the fair normalization function (N) with "
             "the fast normalization function (FN).  This mode is "
             "unsound for programs involving choices or failures, "
             "but may be useful for comparative benchmarking.  Setting "
             "this implicitly sets the grain to infinity.  The option "
             "cannot be set together with tracing.")
        ("grain,g"
           , opt::value<size_t>()->default_value(10000)
           , "Specifies the granularity (number of steps until a forced "
             "context switch)")
        ("help,h", "Displays this help message")
        ("trace,t"
           , opt::value<int>()->implicit_value(1)->default_value(0)
           , "Enables tracing")
        ("verbosity,v"
           , opt::value<int>()->implicit_value(5)->default_value(0)
           , "Sets the verbosity level")
      ;
    opt::variables_map var;
    int const style = opt::command_line_style::unix_style;
    opt::store(opt::parse_command_line(argc, argv, desc, style), var);

    if (var.count("help"))
    {
      std::cout << desc << "\n";
      std::exit(EXIT_SUCCESS);
    }

    CmdlineOptions x;
    x.fastnormalize = var["fast-normalize"].as<int>();
    x.grain = var["grain"].as<size_t>();
    x.trace = var["trace"].as<int>() ? TRACE : NO_TRACE;
    x.verbosity = var["verbosity"].as<int>();

    if(x.fastnormalize)
    {
      if(x.trace)
      {
        std::cout
          << "--trace and --fast-normalize cannot be set simultaneously.  "
             "Ignoring --trace."
          << std::endl;
        x.trace = NO_TRACE;
      }

      std::cout
        << "Overriding --grain from " << x.grain
        << " to infinity because --fast-normalize was enabled." 
        << std::endl;
      x.grain = std::numeric_limits<size_t>::max();
    }

    if(x.trace && x.grain != 1)
    {
      std::cout
        << "Overriding --grain from " << x.grain
        << " to 1 because tracing was enabled."
        << std::endl;
      x.grain = 1;
    }

    if(x.verbosity > 0)
    {
      std::cout
        << "Parameters are:\n"
        << "  fast-normalize  = " << std::boolalpha << (bool) x.fastnormalize << "\n"
        << "  grain           = " << x.grain << "\n"
        << "  trace           = " << std::boolalpha << (bool) x.trace << "\n"
        << "  verbosity       = " << x.verbosity
        << std::endl;
    }
    return x;
  }
}
