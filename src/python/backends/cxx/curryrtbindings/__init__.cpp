#include "pybind11/pybind11.h"
#include "curryrt/evaluation.hpp"
#include "heap.hpp"

namespace curryrt { namespace python
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

PYBIND11_MODULE(_curryrtbindings, mod, pybind11::mod_gil_not_used())
{
  // Group native metadata operations and their Python publication without
  // acquiring a Python mutex before a heap wait. Never used for stepping.
  mod.def("_metadata_call", [](pybind11::function action) { return action(); },
      curryrt::python::heap_access());
  curryrt::set_host_poll(&python_poll);
  curryrt::set_host_wait(&python_wait);
  curryrt::python::register_checker(mod);
  curryrt::python::register_constants(mod);
  curryrt::python::register_dynload(mod);
  curryrt::python::register_evaluator(mod);
  curryrt::python::register_exceptions(mod);
  curryrt::python::register_fingerprint(mod);
  curryrt::python::register_graph(mod);
  curryrt::python::register_icurry(mod);
  curryrt::python::register_module(mod);
  curryrt::python::register_tiered(mod);
}
