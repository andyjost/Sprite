#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace
{
  using namespace cyrt;

  void link_function(
      InfoTable const & info, py::object materialize_cb, bool lazy
    )
  {
    // py::object stepfunction = materialize_cb();
    // assert(0);
  }
}

namespace cyrt { namespace python
{
  void register_graph(pybind11::module_ mod)
  {
    py::class_<InfoTable>(mod, "InfoTable")
      .def_readonly("arity"    , &InfoTable::arity)
      .def_readonly("flags"    , &InfoTable::flags)
      .def_readonly("format"   , &InfoTable::format)
      .def_readonly("name"     , &InfoTable::name)
      // .def_readonly("step"     , &InfoTable::step)
      .def_readonly("tag"      , &InfoTable::tag)
      // .def_readonly("typecheck", &InfoTable::typecheck)
      .def_readwrite("typedef" , &InfoTable::type)
      ;

    py::class_<Node>(mod, "Node");

    py::class_<Type>(mod, "Type")
      .def_property_readonly(
          "constructors"
        , [](Type const & self)
              { return std::vector(self.ctors, self.ctors+self.size); }
        )
      ;

    mod.def("link_function", &link_function);
  }
}}
