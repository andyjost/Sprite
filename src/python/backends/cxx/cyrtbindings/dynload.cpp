#include "heap.hpp"
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
		  .def_readonly("fullname" , &ModuleBOM::fullname, cyrt::python::heap_access{})
		  .def_readonly("filename" , &ModuleBOM::filename, cyrt::python::heap_access{})
		  .def_readonly("imports"  , &ModuleBOM::imports, cyrt::python::heap_access{})
		  .def_readonly("metadata" , &ModuleBOM::metadata, cyrt::python::heap_access{})
		  .def_readonly("aliases"  , &ModuleBOM::aliases, cyrt::python::heap_access{})
		  .def_readonly("types"    , &ModuleBOM::types, cyrt::python::heap_access{})
		  .def_readonly("functions", &ModuleBOM::functions, cyrt::python::heap_access{})
			;

    // The registry entry shared by every library loaded under one module name.
    py::class_<SharedCurryModuleInfo>(mod, "SharedCurryModuleInfo")
      .def_readonly("fullname"  , &SharedCurryModuleInfo::fullname, cyrt::python::heap_access{})
      .def_readonly("sofilename", &SharedCurryModuleInfo::sofilename, cyrt::python::heap_access{})
      ;

    py::class_<SharedCurryModule, std::shared_ptr<SharedCurryModule>>(mod, "SharedCurryModule")
      .def(py::init<std::string const &>(), cyrt::python::heap_access{})
			.def_property_readonly("bom", &SharedCurryModule::bom, reference_internal, cyrt::python::heap_access{})
			.def_property_readonly("info", &SharedCurryModule::info, reference_internal, cyrt::python::heap_access{})
			.def("sofilename", &SharedCurryModule::sofilename, reference, cyrt::python::heap_access{})
      .def_static("find_sofilename"
        , [](char const * fullname) -> py::object {
            // A copy: the registry owns the entry weakly, and a reference
            // would outlive the library.
            auto * info = SharedCurryModule::find(fullname);
            if(!info)
              return py::none();
            return py::str(info->sofilename);
          }
        , py::arg("fullname")
        , "The file of the library loaded under a module name, or None.  "
          "The loader asks before it opens an object, so a second library "
          "of a loaded name is never opened.", cyrt::python::heap_access{})
      ;
  }
}}
