#include "sprite/cmdline.hpp"
#include <boost/program_options.hpp>
#include <iostream>

namespace sprite
{
  CmdlineOptions parse_options(int argc, char * argv[])
  {
    namespace opt = boost::program_options;
    opt::options_description desc("Allowed options");
    desc.add_options()
        ("grain,g"
           , opt::value<size_t>()->default_value(10000)
           , "Specifies the granularity (number of steps between context "
             "switches)")
        ("help,h", "Displays this help message")
        ("trace,t"
           , opt::value<int>()->implicit_value(1)->default_value(0)
           , "Enables tracing")
      ;
    opt::variables_map var;
    int const style = opt::command_line_style::unix_style;
    opt::store(opt::parse_command_line(argc, argv, desc, style), var);


    if (var.count("help"))
    {
      std::cout << desc << "\n";
      std::exit(EXIT_FAILURE);
    }

    CmdlineOptions x;
    x.grain = var["grain"].as<size_t>();
    x.trace = var["trace"].as<int>() ? TRACE : NO_TRACE;

    if(x.trace && x.grain != 1)
    {
      std::cout
        << "Overriding --grain from " << x.grain
        << " to 1 because tracing was enabled"
        << std::endl;
      x.grain = 1;
    }
    return x;
  }
}
