#pragma once
#include "pybind11/pybind11.h"
#include "curryrt/evaluation.hpp"

namespace curryrt { namespace python
{
  // A binding borrows the runtime's heap lock.  Never wait for it holding
  // the GIL: the owner may be about to call a Python generator or trap.
  struct HeapAccessScope
  {
    explicit HeapAccessScope(bool poll = true)
    {
      if(!heap_try_lock())
      {
        pybind11::gil_scoped_release release;
        heap_lock(poll);
      }
    }
    ~HeapAccessScope() { heap_unlock(); }
  };
  template<class T> struct HeapDeleter
  {
    void operator()(T * p) const
    {
      HeapAccessScope lock(false);
      delete p;
    }
  };
  template<class T> using HeapOwned = std::unique_ptr<T, HeapDeleter<T>>;
  struct heap_access {};
}}

namespace pybind11 { namespace detail
{
  template<> struct process_attribute<curryrt::python::heap_access>
    : process_attribute_default<curryrt::python::heap_access>
  {
    static void precall(function_call &)
    {
      // A call_guard ends before return-value conversion.  The loader's
      // lifetime frame instead covers conversions, overload retries and
      // exceptional exits too: a returned node is rooted before unlocking.
      auto scope = std::make_unique<curryrt::python::HeapAccessScope>();
      capsule patient(scope.get(), [](void * p)
        { delete static_cast<curryrt::python::HeapAccessScope *>(p); });
      scope.release();
      loader_life_support::add_patient(patient);
    }
  };
}}
