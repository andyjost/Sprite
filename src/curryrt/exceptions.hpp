#pragma once
#include <stdexcept>
#include <string>

// The exception types cross the boundary between the runtime library and
// the Python extension, which pybind11 compiles with hidden visibility, and
// the objects of compiled modules.  A type with hidden visibility gets a
// type_info of its own in every image, and the C++ runtime of macOS
// compares type_info by address, so a catch in the extension would never
// match a throw of the library (the runtime of GCC compares by name, which
// is why Linux never showed it).  Default visibility lets the dynamic
// linker coalesce the type_info of the images into one.
#if defined(__GNUC__)
#define CURRYRT_EXCEPTION __attribute__((visibility("default")))
#else
#define CURRYRT_EXCEPTION
#endif

namespace curryrt
{
  struct CURRYRT_EXCEPTION TypeError : std::invalid_argument
  {
    using std::invalid_argument::invalid_argument;
  };

  struct CURRYRT_EXCEPTION InstantiationError : std::logic_error
  {
    using std::logic_error::logic_error;
  };

  struct CURRYRT_EXCEPTION DynloadError : std::runtime_error
  {
    using std::runtime_error::runtime_error;
  };

  enum class ErrorKind { evaluation, io, file_not_found, nondet, overflow, division, stack };

  struct CURRYRT_EXCEPTION EvaluationError : std::runtime_error
  {
    ErrorKind kind;
    std::string filename;
    EvaluationError(std::string const & message, ErrorKind kind=ErrorKind::evaluation,
                    std::string const & filename={})
      : std::runtime_error(message), kind(kind), filename(filename) {}
  };

  struct CURRYRT_EXCEPTION EvaluationSuspended : EvaluationError
  {
    using EvaluationError::EvaluationError;
  };

  // The step limit of an evaluation was reached (RuntimeState::step_limit).
  // The outermost scheduler throws it when the status E_TERMINATE reaches
  // it; the Python side turns it into the flow-control exception of the
  // generic evaluator (control.E_TERMINATE).  Not an EvaluationError: the
  // evaluation did not fail, it stopped.
  struct CURRYRT_EXCEPTION StepLimitReached : std::runtime_error
  {
    using std::runtime_error::runtime_error;
  };
}
