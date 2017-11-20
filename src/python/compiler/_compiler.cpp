#include <boost/python.hpp>

char const * greet() { return "hello"; }

BOOST_PYTHON_MODULE(_compiler)
{
  using namespace boost::python;
  def("greet", greet);
}


