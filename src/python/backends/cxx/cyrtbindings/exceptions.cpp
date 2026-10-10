#include "pybind11/pybind11.h"
#include "cyrt/checker.hpp"
#include "cyrt/exceptions.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace cyrt { namespace python
{
  void register_exceptions(pybind11::module_ mod)
	{
		py::register_exception<EvaluationError>(mod, "EvaluationError");
		py::register_exception<EvaluationSuspended>(mod, "EvaluationSuspended");
		// The step limit of an evaluation was reached (RuntimeState::step_limit).
		// generate_values turns it into control.E_TERMINATE.
		py::register_exception<StepLimitReached>(mod, "StepLimitReached");
		// A run-time invariant of the Fair Scheme does not hold (the flag
		// ``checker``; cyrt/checker.hpp).  An AssertionError, as the report of
		// the checker of the Python backend is; its message names the
		// invariant, the event, the configuration and the identifiers.
		py::register_exception<InvariantViolation>(
		    mod, "InvariantViolation", PyExc_AssertionError
		  );
	}
}}
