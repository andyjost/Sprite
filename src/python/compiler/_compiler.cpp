#include <boost/python.hpp>
#include "sprite/llvm/module.hpp"

char const * greet() { return "hello"; }

BOOST_PYTHON_MODULE(_compiler)
{
  using namespace boost::python;
  def("greet", greet);
}


