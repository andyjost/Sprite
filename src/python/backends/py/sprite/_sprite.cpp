#include "pybind11/pybind11.h"
#include "sprite/fingerprint.hpp"

namespace sprite { namespace python
{
  void register_fingerprint(pybind11::object);
}}

PYBIND11_MODULE(_sprite, module)
{
  sprite::python::register_fingerprint(module);
}
