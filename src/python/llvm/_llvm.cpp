#include <boost/python.hpp>
#include "python/llvm/_llvm.hpp"

BOOST_PYTHON_MODULE(_llvm)
{
  sprite::python::register_module();
  sprite::python::register_type();
}
