#include "pybind11/pybind11.h"
#include "sprite/state/rts.hpp"

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  void register_rts(pybind11::module_ mod)
  {
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init())
      ;
  }
}}
