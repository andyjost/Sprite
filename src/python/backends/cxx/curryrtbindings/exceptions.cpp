#include "pybind11/pybind11.h"
#include "curryrt/checker.hpp"
#include "curryrt/exceptions.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace curryrt { namespace python
{
  void register_exceptions(pybind11::module_ mod)
  {
    auto exceptions = py::module_::import("curry.exceptions");
    mod.attr("EvaluationError") = exceptions.attr("EvaluationError");
    mod.attr("SuspensionError") = exceptions.attr("SuspensionError");
    py::register_exception_translator([](std::exception_ptr error)
    {
      try
      {
        if(error) std::rethrow_exception(error);
      }
      catch(EvaluationSuspended const &)
      {
        auto type = py::module_::import("curry.exceptions").attr("SuspensionError");
        PyErr_SetObject(type.ptr(), type().ptr());
      }
      catch(EvaluationError const & error)
      {
        auto make_error = py::module_::import("curry.exceptions").attr("evaluation_error");
        char const * kind = "evaluation";
        switch(error.kind)
        {
          case ErrorKind::io: kind = "io"; break;
          case ErrorKind::file_not_found: kind = "file_not_found"; break;
          case ErrorKind::nondet: kind = "nondet"; break;
          case ErrorKind::overflow: kind = "overflow"; break;
          case ErrorKind::division: kind = "division"; break;
          case ErrorKind::stack: kind = "stack"; break;
          default: break;
        }
        auto translated = make_error(error.what(), kind, error.filename);
        PyErr_SetObject(reinterpret_cast<PyObject *>(Py_TYPE(translated.ptr())), translated.ptr());
      }
      catch(InstantiationError const & error)
      {
        auto type = py::module_::import("curry.exceptions").attr("InstantiationError");
        PyErr_SetString(type.ptr(), error.what());
      }
      catch(DynloadError const & error)
      {
        auto type = py::module_::import("curry.exceptions").attr("LoadError");
        PyErr_SetString(type.ptr(), error.what());
      }
    });
    // The step limit of an evaluation was reached (RuntimeState::step_limit).
    // generate_values turns it into control.E_TERMINATE.
    py::register_exception<StepLimitReached>(
        mod, "StepLimitReached", exceptions.attr("CurryError")
      );
    // A run-time invariant of the Fair Scheme does not hold (the flag
    // ``checker``; curryrt/checker.hpp).  An AssertionError, as the report of
    // the checker of the former runtime is; its message names the
    // invariant, the event, the configuration and the identifiers.
    auto invariant_bases = py::make_tuple(
        py::reinterpret_borrow<py::object>(PyExc_AssertionError)
      , exceptions.attr("CurryError")
      );
    py::register_exception<InvariantViolation>(mod, "InvariantViolation", invariant_bases);
  }
}}
