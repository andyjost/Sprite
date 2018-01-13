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
  register_exception<index_error>(PyExc_IndexError);
  register_exception<internal_error>(PyExc_SystemError);
  register_exception<key_error>(PyExc_KeyError);
  register_exception<scope_error>(PyExc_RuntimeError);
  register_exception<type_error>(PyExc_TypeError);
  register_exception<value_error>(PyExc_ValueError);
  sprite::python::register_globalvalues();
  sprite::python::register_type();
  sprite::python::register_value();
  sprite::python::register_module(); // depends on value
}
