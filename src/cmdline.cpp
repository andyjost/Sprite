#include "sprite/cmdline.hpp"
#include <boost/program_options.hpp>

namespace sprite
{
  CmdlineOptions parse_options(int argc, char * argv[])
  {
    namespace opt = boost::program_options;
    opt::options_description desc("Allowed options");
    desc.add_options()
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
    x.trace = var["trace"].as<int>() ? TRACE : NO_TRACE;
    return x;
  }
}
