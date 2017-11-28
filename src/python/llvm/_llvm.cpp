#include <boost/python.hpp>
#include "sprite/llvm/exceptions.hpp"
#include "python/llvm/_llvm.hpp"
#include <functional>

using namespace boost::python;
using namespace sprite::llvm;

namespace
{
  void translate(std::exception const & e, PyObject * pyexc_type)
    { PyErr_SetString(pyexc_type, e.what()); }

  template<typename ExceptionType>
  void register_exception(PyObject * pyexc_type)
  {
    using std::placeholders::_1;
    auto handler = std::bind(&translate, _1, pyexc_type);
    register_exception_translator<ExceptionType>(handler);
  }
}

BOOST_PYTHON_MODULE(_llvm)
{
  register_exception<type_error>(PyExc_TypeError);
  register_exception<value_error>(PyExc_ValueError);
  register_exception<scope_error>(PyExc_RuntimeError);
  sprite::python::register_module();
  sprite::python::register_type();
}
