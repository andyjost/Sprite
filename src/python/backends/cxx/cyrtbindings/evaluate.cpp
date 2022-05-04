#include "pybind11/pybind11.h"
#include <cassert>
#include "pybind11/stl.h"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"
#include <iostream>

namespace py = pybind11;

namespace cyrt { namespace python
{
  py::object Expr_get(Expr const & expr)
  {
    switch(expr.kind)
    {
      case 'p': return py::cast(expr.arg.node);
      case 'i': return py::cast(expr.arg.ub_int);
      case 'f': return py::cast(expr.arg.ub_float);
      case 'c': return py::cast(expr.arg.ub_char);
      case 'x': assert(false);
      case 'u':
      default : return py::none();
    }
  }

  void register_evaluator(pybind11::module_ mod)
  {
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init<>())
      ;

    py::class_<Expr>(mod, "Expr")
      .def("get", &Expr_get)
      .def("__nonzero__", &Expr::operator bool)
      .def("__bool__", &Expr::operator bool)
      ;

    py::class_<RuntimeState>(mod, "RuntimeStateBase")
      .def(py::init<InterpreterState &, Node *>())
      .def("next", &RuntimeState::procD)
      ;
  }
}}
