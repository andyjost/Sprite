#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "sprite/cxx.hpp"
#include "sprite/graph/infotable.hpp"
#include "sprite/graph/node.hpp"

using namespace sprite;
namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace sprite { namespace python
{
  void register_cxx(pybind11::module_ mod)
  {
    py::class_<Module, std::shared_ptr<Module>>(mod, "Module")
      .def("create_infotable", &Module::create_infotable, reference)
      .def("create_type", &Module::create_type, reference)
      .def("get_infotable", &Module::get_infotable, reference)
      .def("get_type", &Module::get_type, reference)
      .def_readonly("name", &Module::name)
      .def_static("find_or_create", &Module::find_or_create)
      ;

    py::class_<Type>(mod, "Type")
      .def_property_readonly(
          "constructors"
        , [](Type const & self)
              { return std::vector(self.ctors, self.ctors+self.size); }
        )
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
  }
}}
