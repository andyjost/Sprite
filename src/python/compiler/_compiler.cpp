#include <boost/python.hpp>
#include "sprite/llvm/module.hpp"

using namespace boost::python;

BOOST_PYTHON_MODULE(_compiler)
{
  class_<sprite::llvm::module>(
      "module", init<std::string const &>()
    )
    .def(self == other<sprite::llvm::module>())
    ;

}


