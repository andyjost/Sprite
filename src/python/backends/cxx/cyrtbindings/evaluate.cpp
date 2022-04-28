#include "pybind11/pybind11.h"
#include <cassert>
#include "pybind11/stl.h"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"
#include <iostream>

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace cyrt { namespace python
{
  namespace
  {
    py::object Evaluator_next(Evaluator & evaluator)
    {
      Expr result = evaluator.next();
      switch(result.kind)
      {
        case 'p': return py::cast(result.arg.node);
        case 'i': return py::cast(result.arg.ub_int);
        case 'f': return py::cast(result.arg.ub_float);
        case 'c': return py::cast(result.arg.ub_char);
        case 'x': assert(false); // FIXME
        case 'u': return py::none();
      }
    }
  }


  void register_evaluator(pybind11::module_ mod)
  {
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init<>())
      ;

    py::class_<Evaluator>(mod, "Evaluator")
      .def(py::init<InterpreterState &, Node *>())
      .def("next", &Evaluator_next)
      ;
  }
}}
