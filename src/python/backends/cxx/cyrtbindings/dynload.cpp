#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/dynload.hpp"
#include <memory>
#include <string>

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;
static auto constexpr reference_internal = py::return_value_policy::reference_internal;

namespace cyrt { namespace python
{
  void register_dynload(pybind11::module_ mod)
  {
    py::class_<ModuleBOM>(mod, "ModuleBOM")
		  .def_readonly("fullname" , &ModuleBOM::fullname)
		  .def_readonly("filename" , &ModuleBOM::filename)
		  .def_readonly("imports"  , &ModuleBOM::imports)
		  .def_readonly("metadata" , &ModuleBOM::metadata)
		  .def_readonly("aliases"  , &ModuleBOM::aliases)
		  .def_readonly("types"    , &ModuleBOM::types)
		  .def_readonly("functions", &ModuleBOM::functions)
			;

    py::class_<SharedCurryModule, std::shared_ptr<SharedCurryModule>>(mod, "SharedCurryModule")
      .def(py::init<std::string const &>())
			.def_property_readonly("bom", &SharedCurryModule::bom, reference_internal)
			.def("sofilename", &SharedCurryModule::sofilename, reference)
      ;
  }
}}
