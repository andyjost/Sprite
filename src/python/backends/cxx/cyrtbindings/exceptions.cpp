#include "pybind11/pybind11.h"
#include "cyrt/exceptions.hpp"

namespace py = pybind11;
static auto constexpr reference = py::return_value_policy::reference;

namespace cyrt { namespace python
{
  void register_exceptions(pybind11::module_ mod)
	{
		py::register_exception<EvaluationError>(mod, "EvaluationError");
		py::register_exception<EvaluationSuspended>(mod, "EvaluationSuspended");
	}
}}
