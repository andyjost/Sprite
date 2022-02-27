#include "pybind11/pybind11.h"

namespace cyrt { namespace python
{
  void register_cxx(pybind11::module_);
  void register_fingerprint(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

PYBIND11_MODULE(_cyrt, mod)
{
  cyrt::python::register_cxx(mod);
  cyrt::python::register_fingerprint(mod);
  cyrt::python::register_scratch(mod); // temp
}
