#include "pybind11/pybind11.h"
#include "pybind11/stl.h"
#include "cyrt/cxx.hpp"
#include "cyrt/graph/infotable.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/state/rts.hpp"

using namespace cyrt;
namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace cyrt { namespace python
{
  void register_cxx(pybind11::module_ mod)
  {
    py::class_<InfoTable>(mod, "InfoTable")
      .def_property_readonly("step", [](InfoTable const &){})
      .def_property_readonly("typecheck", [](InfoTable const &){})
      .def_readonly("arity", &InfoTable::arity)
      .def_readonly("format", &InfoTable::format)
      .def_readonly("name", &InfoTable::name)
      .def_readonly("tag", &InfoTable::tag)
      .def_readwrite("typedef", &InfoTable::type)
      .def_property_readonly("flags"
        , [](InfoTable const & self)
            { return self.typetag | (self.flags << 8 * sizeof(flag_type)); }
        )
      ;

    py::class_<InterpreterState>(mod, "InterpreterState")
      .def(py::init())
      ;

    py::class_<Module, std::shared_ptr<Module>>(mod, "Module")
      .def_static("find_or_create", &Module::find_or_create)
      .def_static("getall", &Module::getall)
      .def("create_infotable", &Module::create_infotable, reference)
      .def("create_type", &Module::create_type, reference)
      .def("get_infotable", &Module::get_infotable, reference)
      .def("get_type", &Module::get_type, reference)
      .def_readonly("name", &Module::name)
      ;

    py::class_<Node>(mod, "Node");

    py::class_<Type>(mod, "Type")
      .def_property_readonly(
          "constructors"
        , [](Type const & self)
              { return std::vector(self.ctors, self.ctors+self.size); }
        )
      ;

    mod.attr("T_UNBOXED") = (int) T_UNBOXED;
    mod.attr("T_SETGRD")  = (int) T_SETGRD;
    mod.attr("T_FAIL")    = (int) T_FAIL;
    mod.attr("T_CONSTR")  = (int) T_CONSTR;
    mod.attr("T_FREE")    = (int) T_FREE;
    mod.attr("T_FWD")     = (int) T_FWD;
    mod.attr("T_CHOICE")  = (int) T_CHOICE;
    mod.attr("T_FUNC")    = (int) T_FUNC;
    mod.attr("T_CTOR")    = (int) T_CTOR;

    mod.attr("NO_FLAGS")      = (int) NO_FLAGS;
    mod.attr("INT_TYPE")      = (int) INT_TYPE;
    mod.attr("CHAR_TYPE")     = (int) CHAR_TYPE;
    mod.attr("FLOAT_TYPE")    = (int) FLOAT_TYPE;
    mod.attr("BOOL_TYPE")     = (int) BOOL_TYPE;
    mod.attr("LIST_TYPE")     = (int) LIST_TYPE;
    mod.attr("TUPLE_TYPE")    = (int) TUPLE_TYPE;
    mod.attr("IO_TYPE")       = (int) IO_TYPE;
    mod.attr("PARTIAL_TYPE")  = (int) PARTIAL_TYPE;
    mod.attr("OPERATOR")      = (int) OPERATOR;
    mod.attr("MONADIC")       = (int) MONADIC;
    mod.attr("STATIC_OBJECT") = (int) STATIC_OBJECT;

    py::enum_<ConstraintType>(mod, "ConstraintType")
        .value("STRICT_CONSTRAINT"   , STRICT_CONSTRAINT)
        .value("NONSTRICT_CONSTRAINT", NONSTRICT_CONSTRAINT)
        .value("VALUE_BINDING"       , VALUE_BINDING)
        .export_values()
        ;
  }
}}
