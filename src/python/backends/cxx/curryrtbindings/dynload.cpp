#include "heap.hpp"
#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "curryrt/dynload.hpp"
#include <memory>
#include <string>

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;
static auto constexpr reference_internal = py::return_value_policy::reference_internal;

namespace curryrt { namespace python
{
  void register_dynload(pybind11::module_ mod)
  {
    py::class_<ModuleBOM>(mod, "ModuleBOM")
		  .def_readonly("fullname" , &ModuleBOM::fullname, curryrt::python::heap_access{})
		  .def_readonly("filename" , &ModuleBOM::filename, curryrt::python::heap_access{})
		  .def_readonly("imports"  , &ModuleBOM::imports, curryrt::python::heap_access{})
		  .def_readonly("metadata" , &ModuleBOM::metadata, curryrt::python::heap_access{})
		  .def_readonly("aliases"  , &ModuleBOM::aliases, curryrt::python::heap_access{})
		  .def_readonly("types"    , &ModuleBOM::types, curryrt::python::heap_access{})
		  .def_readonly("functions", &ModuleBOM::functions, curryrt::python::heap_access{})
			;

    // The registry entry shared by every library loaded under one module name.
    py::class_<SharedCurryModuleInfo>(mod, "SharedCurryModuleInfo")
      .def_readonly("fullname"  , &SharedCurryModuleInfo::fullname, curryrt::python::heap_access{})
      .def_readonly("sofilename", &SharedCurryModuleInfo::sofilename, curryrt::python::heap_access{})
      ;

    py::class_<SharedCurryModule, std::shared_ptr<SharedCurryModule>>(mod, "SharedCurryModule")
      .def(py::init<std::string const &>(), curryrt::python::heap_access{})
			.def_property_readonly("bom", &SharedCurryModule::bom, reference_internal, curryrt::python::heap_access{})
			.def_property_readonly("info", &SharedCurryModule::info, reference_internal, curryrt::python::heap_access{})
			.def("sofilename", &SharedCurryModule::sofilename, reference, curryrt::python::heap_access{})
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
          "of a loaded name is never opened.", curryrt::python::heap_access{})
      ;
  }
}}
