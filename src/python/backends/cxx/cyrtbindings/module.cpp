#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace cyrt { namespace python
{
  void register_module(pybind11::module_ mod)
  {
    py::class_<Module, std::shared_ptr<Module>>(mod, "Module")
      .def("create_infotable", &Module::create_infotable, reference)
      .def("create_type", &Module::create_type, reference)
      .def("get_infotable", &Module::get_infotable, reference)
      .def("get_type", &Module::get_type, reference)
      .def("get_builtin_symbol", &Module::get_builtin_symbol, reference)
      .def("get_builtin_type", &Module::get_builtin_type, reference)
      .def_readonly("name", &Module::name)
      .def_static("find_or_create", &Module::find_or_create)
      .def_static("getall", &Module::getall)
      ;

    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init())
      ;
  }
}}
