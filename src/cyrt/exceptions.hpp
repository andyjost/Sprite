#pragma once
#include <stdexcept>

namespace cyrt
{
  struct TypeError : std::invalid_argument
  {
    using std::invalid_argument::invalid_argument;
  };

  struct InstantiationError : std::logic_error
  {
    using std::logic_error::logic_error;
  };

  struct DynloadError : std::runtime_error
  {
    using std::runtime_error::runtime_error;
  };

  struct EvaluationError : std::runtime_error
  {
    using std::runtime_error::runtime_error;
  };

  struct EvaluationSuspended : EvaluationError
  {
    using EvaluationError::EvaluationError;
  };

  // The step limit of an evaluation was reached (RuntimeState::step_limit).
  // The outermost scheduler throws it when the status E_TERMINATE reaches
  // it; the Python side turns it into the flow-control exception of the
  // generic evaluator (control.E_TERMINATE).  Not an EvaluationError: the
  // evaluation did not fail, it stopped.
  struct StepLimitReached : std::runtime_error
  {
    using std::runtime_error::runtime_error;
  };
}
