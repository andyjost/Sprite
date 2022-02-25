#include "pybind11/pybind11.h"
#include "sprite/builtins.hpp"
#include "sprite/compiler.hpp"
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
  void register_fingerprint(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

using namespace sprite;
namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace
{
  static ModuleHandle M;
  ModuleHandle * get_module_handle(py::object moduleobj)
  {
    return &M;
  }
}

PYBIND11_MODULE(__sprite, mod)
{
  sprite::python::register_fingerprint(mod);
  sprite::python::register_scratch(mod); // temp

  py::class_<InterpreterState>(mod, "InterpreterState")
    .def(py::init())
    ;

  py::class_<Type>(mod, "Type")
    ;

  py::class_<InfoTable>(mod, "InfoTable")
    // .def_static("create", &InfoTable_create, reference)
    .def_readonly("name", &InfoTable::name)
    .def_readonly("arity", &InfoTable::arity)
    .def_readonly("tag", &InfoTable::tag)
    .def_property_readonly("step", [](InfoTable const &){})
    .def_readonly("format", &InfoTable::format)
    .def_property_readonly("typecheck", [](InfoTable const &){})
    .def_readwrite("_typedef", &InfoTable::type)
    .def_property_readonly("flags"
      , [](InfoTable const & self) { return self.typetag | self.flags << 1; }
      )
    ;

  py::class_<Node>(mod, "Node");
  py::class_<ModuleHandle>(mod, "ModuleHandle");

  mod.def("get_module_handle", &get_module_handle, reference);
  mod.def("create_info", create_info, py::return_value_policy::reference);
}
