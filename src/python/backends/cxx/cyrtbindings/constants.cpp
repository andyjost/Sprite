#include "pybind11/pybind11.h"
#include "cyrt/fwd.hpp"
#include "cyrt/graph/infotable.hpp"

namespace py = pybind11;

namespace cyrt { namespace python
{
  void register_constants(pybind11::module_ mod)
  {
    mod.attr("T_UNBOXED") = (int) T_UNBOXED;
    mod.attr("T_SETGRD")  = (int) T_SETGRD;
    mod.attr("T_FAIL")    = (int) T_FAIL;
    mod.attr("T_CONSTR")  = (int) T_CONSTR;
    mod.attr("T_FREE")    = (int) T_FREE;
    mod.attr("T_FWD")     = (int) T_FWD;
    mod.attr("T_CHOICE")  = (int) T_CHOICE;
    mod.attr("T_FUNC")    = (int) T_FUNC;
    mod.attr("T_CTOR")    = (int) T_CTOR;

    mod.attr("NO_FLAGS")        = (int) NO_FLAGS;
    mod.attr("F_INT_TYPE")      = (int) F_INT_TYPE;
    mod.attr("F_CHAR_TYPE")     = (int) F_CHAR_TYPE;
    mod.attr("F_FLOAT_TYPE")    = (int) F_FLOAT_TYPE;
    mod.attr("F_BOOL_TYPE")     = (int) F_BOOL_TYPE;
    mod.attr("F_LIST_TYPE")     = (int) F_LIST_TYPE;
    mod.attr("F_TUPLE_TYPE")    = (int) F_TUPLE_TYPE;
    mod.attr("F_IO_TYPE")       = (int) F_IO_TYPE;
    mod.attr("F_PARTIAL_TYPE")  = (int) F_PARTIAL_TYPE;
    mod.attr("F_CSTRING_TYPE")  = (int) F_CSTRING_TYPE;
    mod.attr("F_MONADIC")       = (int) F_MONADIC;
    mod.attr("F_OPERATOR")      = (int) F_OPERATOR;
    mod.attr("F_STATIC_OBJECT") = (int) F_STATIC_OBJECT;
    mod.attr("F_PINNED")        = (int) F_PINNED;

    py::enum_<ConstraintType>(mod, "ConstraintType")
        .value("STRICT_CONSTRAINT"   , STRICT_CONSTRAINT)
        .value("NONSTRICT_CONSTRAINT", NONSTRICT_CONSTRAINT)
        .value("VALUE_BINDING"       , VALUE_BINDING)
        .export_values()
        ;

    py::enum_<SetFStrategy>(mod, "SetFStrategy")
        .value("SETF_EAGER"   , SETF_EAGER)
        .value("SETF_LAZY"    , SETF_LAZY)
        .export_values()
        ;
  }
}}
