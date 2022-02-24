#include "pybind11/pybind11.h"
#include "sprite/fingerprint.hpp"

namespace sprite { namespace python
{
  void register_fingerprint(pybind11::module_);
  void register_runtime(pybind11::module_);
  void register_compiler(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

PYBIND11_MODULE(__sprite, mod)
{
  sprite::python::register_fingerprint(mod);
  sprite::python::register_runtime(mod);
  sprite::python::register_compiler(mod);
  sprite::python::register_scratch(mod); // temp
}
