#include "pybind11/pybind11.h"
#include "sprite/runtime/graph/node.hpp"

using namespace sprite;
namespace py = pybind11;

namespace sprite { namespace python
{
  void register_graph(py::module_ mod)
  {
    mod.def("hello", &runtime::hello);
  }
}}
