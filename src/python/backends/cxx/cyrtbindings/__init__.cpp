#include "pybind11/pybind11.h"
#include "cyrt/evaluation.hpp"
#include "heap.hpp"

namespace cyrt { namespace python
{
  void register_constants(pybind11::module_);
  void register_dynload(pybind11::module_);
  void register_checker(pybind11::module_);
  void register_evaluator(pybind11::module_);
  void register_exceptions(pybind11::module_);
  void register_fingerprint(pybind11::module_);
  void register_graph(pybind11::module_);
  void register_icurry(pybind11::module_);
  void register_module(pybind11::module_);
  void register_tiered(pybind11::module_);
}}

namespace
{
  void python_wait(void (*wait)(void *), void * data)
  {
    // Native destructors can enter the heap without a bound-function
    // frame.  They obey the same lock order as an ordinary Python entry.
    if(PyGILState_Check())
    {
      pybind11::gil_scoped_release release;
      wait(data);
    }
    else wait(data);
  }

  void python_poll()
  {
    pybind11::gil_scoped_acquire gil;
    if(PyErr_CheckSignals() < 0)
      throw pybind11::error_already_set();
  }
}

PYBIND11_MODULE(_cyrtbindings, mod, pybind11::mod_gil_not_used())
{
  // Group native metadata operations and their Python publication without
  // acquiring a Python mutex before a heap wait. Never used for stepping.
  mod.def("_metadata_call", [](pybind11::function action) { return action(); },
      cyrt::python::heap_access());
  cyrt::set_host_poll(&python_poll);
  cyrt::set_host_wait(&python_wait);
  cyrt::python::register_checker(mod);
  cyrt::python::register_constants(mod);
  cyrt::python::register_dynload(mod);
  cyrt::python::register_evaluator(mod);
  cyrt::python::register_exceptions(mod);
  cyrt::python::register_fingerprint(mod);
  cyrt::python::register_graph(mod);
  cyrt::python::register_icurry(mod);
  cyrt::python::register_module(mod);
  cyrt::python::register_tiered(mod);
}
