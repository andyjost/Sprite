#include "pybind11/pybind11.h"

namespace sprite { namespace python
{
  void register_cxx(pybind11::module_);
  void register_fingerprint(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

PYBIND11_MODULE(__sprite, mod)
{
  sprite::python::register_cxx(mod);
  sprite::python::register_fingerprint(mod);
  sprite::python::register_scratch(mod); // temp
}
