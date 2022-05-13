#include "pybind11/pybind11.h"

namespace cyrt { namespace python
{
  void register_constants(pybind11::module_);
  void register_dynload(pybind11::module_);
  void register_evaluator(pybind11::module_);
  void register_exceptions(pybind11::module_);
  void register_fingerprint(pybind11::module_);
  void register_graph(pybind11::module_);
  void register_module(pybind11::module_);
  void register_scratch(pybind11::module_); // temp
}}

PYBIND11_MODULE(_cyrtbindings, mod)
{
  cyrt::python::register_constants(mod);
  cyrt::python::register_dynload(mod);
  cyrt::python::register_evaluator(mod);
  cyrt::python::register_exceptions(mod); // temp
  cyrt::python::register_fingerprint(mod);
  cyrt::python::register_graph(mod);
  cyrt::python::register_module(mod);
  cyrt::python::register_scratch(mod); // temp
}
