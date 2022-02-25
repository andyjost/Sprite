#include "pybind11/pybind11.h"
#include "sprite/builtins.hpp"
#include "sprite/fingerprint.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/state/rts.hpp"
#include <iostream>

namespace sprite { namespace python
{
  void register_cxx(pybind11::module_);
  void register_fingerprint(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

using namespace sprite;
namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

PYBIND11_MODULE(__sprite, mod)
{
  sprite::python::register_cxx(mod);
  sprite::python::register_fingerprint(mod);
  sprite::python::register_scratch(mod); // temp

  py::class_<InterpreterState>(mod, "InterpreterState")
    .def(py::init())
    ;
}
