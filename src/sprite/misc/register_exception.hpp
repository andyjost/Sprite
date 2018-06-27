#pragma once
#include <boost/python.hpp>
#include <stdexcept>
#include <functional>

namespace sprite { namespace python
{
  void translate(std::exception const & e, PyObject * pyexc_type)
    { PyErr_SetString(pyexc_type, e.what()); }

  template<typename ExceptionType>
  void register_exception(PyObject * pyexc_type)
  {
    using std::placeholders::_1;
    auto handler = std::bind(&translate, _1, pyexc_type);
    boost::python::register_exception_translator<ExceptionType>(handler);
  }
}}

