#include "pybind11/pybind11.h"
#include "sprite/compiler/synthesize.hpp"
#include "sprite/graph/infotable.hpp"
#include "sprite/builtins.hpp"

using namespace sprite;
namespace py = pybind11;

namespace
{
  InfoTable const * _gci_impl(
      py::object interp, py::object itype, py::object icons, py::object extern_
    )
  {
    return &Unit_Info;
  }
  void _gtd_impl() {}
  void _gfis_impl() {}
}

namespace sprite { namespace python
{
  void register_compiler(py::module_ mod)
  {
    auto reference = py::return_value_policy::reference;
    mod.def("synthesize_constructor_info"  , &_gci_impl , reference);
    mod.def("synthesize_and_attach_typedef", &_gtd_impl , reference);
    mod.def("get_function_info_stub"       , &_gfis_impl, reference);
  }
}}
