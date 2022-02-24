#include "pybind11/pybind11.h"
#include "sprite/builtins.hpp"
#include "sprite/graph/equality.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/copy.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/state/rts.hpp"
#include <iostream>

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  // InfoTable dummy() { return Int_Info; }

  void register_runtime(py::module_ mod)
  {
    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init())
      ;

    py::class_<Type>(mod, "Type")
      ;

    py::class_<InfoTable>(mod, "InfoTable")
      // .def(py::init(&dummy))
      .def_readonly("name", &InfoTable::name)
      .def_readonly("arity", &InfoTable::arity)
      .def_readonly("tag", &InfoTable::tag)
      // .def_readonly("step", &InfoTable::step)
      // .def_readonly("format", &InfoTable::step)
      // .def_readonly("typecheck", &InfoTable::typecheck)
      .def_readonly("typedef", &InfoTable::type)
      .def_property_readonly("flags"
        , [](InfoTable const & self) { return self.typetag | self.flags << 1; }
        )
      ;

    py::class_<Node>(mod, "Node");
  }
}}
