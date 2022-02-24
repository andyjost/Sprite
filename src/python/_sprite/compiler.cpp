#include "pybind11/pybind11.h"
#include "sprite/compiler/synthesize.hpp"
#include "sprite/graph/infotable.hpp"
#include "sprite/builtins.hpp"

using namespace sprite;
namespace py = pybind11;

namespace
{
  InfoTable const * _sci_impl(
      py::object interp, py::object itype, py::object icons, py::object extern_
    )
  {
    return &Unit_Info;
  }
  void _st_impl() {}
  void _std_impl() {}
  void _gfis_impl() {}
}

namespace sprite { namespace python
{
  void register_compiler(py::module_ mod)
  {
    auto reference = py::return_value_policy::reference;
    mod.def("synthesize_constructor_info"  , &_sci_impl , reference);
    mod.def("synthesize_and_attach_typedef", &_std_impl , reference);
    mod.def("synthesize_type"              , &_st_impl , reference);
    mod.def("get_function_info_stub"       , &_gfis_impl, reference);
  }
}}
