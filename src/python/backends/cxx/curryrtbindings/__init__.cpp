#include "pybind11/pybind11.h"
#include "curryrt/evaluation.hpp"
#include "heap.hpp"
#include <atomic>
#include <csignal>
#include <exception>

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
  thread_local size_t lock_depth = 0;
  thread_local bool logs_pending = false;
  thread_local int drain_snapshot_signal = 0, drain_between_signal = 0;
  PyObject * drain_logs = nullptr; // retained with the host hooks
  bool python_lock_held()
  {
    return lock_depth != 0;
  }
  void leave_lock()
  {
    if(!--lock_depth && logs_pending)
      pybind11::reinterpret_borrow<pybind11::function>(drain_logs)();
  }

  void drain_signal(int & pending)
  {
    if(pending)
    { int sig = pending; pending = 0; std::raise(sig); }
    if(PyErr_CheckSignals() < 0) throw pybind11::error_already_set();
  }

  void drain_messages(pybind11::object local, pybind11::function write)
  {
    namespace py = pybind11;
    if(py::getattr(local, "draining", py::bool_(false)).cast<bool>()) return;
    py::list messages = py::getattr(local, "messages", py::list());
    py::list empty, suppressed;
    size_t next = 0, lost = 0;
    size_t const size = messages.size();
    std::exception_ptr failure;
    try
    {
      // No Python bytecode separates detachment, pending state and the
      // cleanup region. The snapshot stays owned here until it is accounted.
      local.attr("suppressed") = suppressed;
      local.attr("draining") = true;
      local.attr("messages") = empty;
      logs_pending = false;
      drain_signal(drain_snapshot_signal);
      while(next < size)
      {
        // A signal outside a logging attempt preserves the unattempted tail.
        if(next) drain_signal(drain_between_signal);
        try
        {
          // Record the attempt and enter the handler in one native step.
          py::tuple record = messages[next++];
          py::tuple args = record[3];
          record[0].attr("log")(record[1], record[2], *args);
        }
        catch(py::error_already_set const &)
        { if(!failure) failure = std::current_exception(); }
      }
    }
    catch(...) { failure = std::current_exception(); }
    try
    {
      if(next < size)
      {
        py::object tail = messages;
        if(next)
        {
          tail = py::reinterpret_steal<py::object>(
              PyList_GetSlice(messages.ptr(), next, size));
          if(!tail) throw py::error_already_set();
        }
        local.attr("messages") = tail;
        logs_pending = true;
      }
    }
    catch(...)
    {
      // Allocation failure must not turn an interrupted snapshot into an
      // unreported loss. Use the same handler-free count as recursive logs.
      lost = size - next;
      if(!failure) failure = std::current_exception();
    }
    // Restore state before reporting too; even an interrupted write cannot
    // leave this thread permanently suppressing diagnostics.
    local.attr("draining") = false;
    try
    {
      size_t const count = suppressed.size() + lost;
      if(count)
        write(2, py::bytes("Sprite logging: suppressed " + std::to_string(count)
            + " recursive records\n"));
    }
    catch(py::error_already_set const & error)
    {
      if(!failure || !error.matches(PyExc_OSError))
        failure = std::current_exception();
    }
    if(failure) std::rethrow_exception(failure);
    if(PyErr_CheckSignals() < 0) throw py::error_already_set();
  }

  // No Python bytecode between changing the mutex and its ownership record.
  // In particular __enter__ itself is native: a Python wrapper would reopen
  // the signal window before the caller's with statement installs cleanup.
  struct HostLock
  {
    pybind11::object mutex;
    pybind11::function acquire_mutex, release_mutex;
    std::atomic<unsigned long> owner{0};
    size_t count = 0;
    int acquire_signal = 0, release_signal = 0;
    explicit HostLock(bool recurse)
    {
      auto thread = pybind11::module_::import("_thread");
      mutex = thread.attr(recurse ? "RLock" : "allocate_lock")();
      acquire_mutex = mutex.attr("acquire");
      release_mutex = mutex.attr("release");
    }
    bool acquire(bool blocking, double timeout)
    {
      ++lock_depth; // Pending acquisition obeys the boundary too.
      bool acquired;
      try
      {
        // These retained methods are implemented in C by _thread, never in
        // Python. Keep the original mutex's fast path, timeouts and handoff
        // behavior; a wait may dispatch signals before it owns the mutex.
        acquired = acquire_mutex(blocking, timeout).cast<bool>();
      }
      catch(...) { leave_lock(); throw; }
      if(!acquired)
      { leave_lock(); return false; }
      if(acquire_signal)
      { int sig = acquire_signal; acquire_signal = 0; std::raise(sig); }
      owner.store(PyThread_get_thread_ident());
      ++count;
      // Dispatch a signal forced during the transition only after recording
      // ownership, and undo this acquisition if its handler refuses entry.
      try
      { if(PyErr_CheckSignals() < 0) throw pybind11::error_already_set(); }
      catch(...) { release(); throw; }
      return true;
    }
    void release()
    {
      if(owner.load() != PyThread_get_thread_ident())
        throw std::runtime_error("cannot release un-acquired lock");
      // Clear before unlocking so a free-threaded successor cannot race this
      // record update. The retained C builtin runs no Python bytecode here.
      if(!--count) owner.store(0);
      try { release_mutex(); }
      catch(...) { owner.store(PyThread_get_thread_ident()); ++count; throw; }
      if(release_signal)
      { int sig = release_signal; release_signal = 0; std::raise(sig); }
      leave_lock();
      if(PyErr_CheckSignals() < 0) throw pybind11::error_already_set();
    }
  };
  HostLock & lock_state(pybind11::object self)
  {
    return self.attr("_native_state").cast<HostLock &>();
  }
  struct Holding {};

  void register_host_locks(pybind11::module_ mod)
  {
    namespace py = pybind11;
    py::object locking = py::module_::import("curry.utility.locking");
    py::object drain = locking.attr("_drain");
    drain_logs = drain.release().ptr();
    py::class_<HostLock>(mod, "_HostLock")
      .def(py::init<bool>());
    py::class_<Holding>(mod, "_Holding")
      .def(py::init<>())
      .def("__enter__", [](Holding &)
        {
          ++lock_depth;
          try
          { if(PyErr_CheckSignals() < 0) throw py::error_already_set(); }
          catch(...) { leave_lock(); throw; }
        })
      .def("__exit__", [](Holding &, py::args) { leave_lock(); });
    mod.def("_locks_held", &python_lock_held);
    // Locks constructed during package bootstrap have never escaped to a
    // public caller. Upgrade them before enabling the runtime boundary.
    for(auto item: locking.attr("_bootstrap_locks"))
    {
      py::object lock = py::reinterpret_borrow<py::object>(item);
      lock.attr("_native_state") = mod.attr("_HostLock")(lock.attr("_recursive"));
    }
    locking.attr("_bootstrap_locks").attr("clear")();
    locking.attr("_native") = mod;
    locking.attr("holding") = mod.attr("_Holding");
    locking.attr("_held") = mod.attr("_locks_held");
    locking.attr("check_entry") = mod.attr("_check_reentrancy");
    mod.def("_set_logs_pending", [](bool pending) { logs_pending = pending; });
    locking.attr("_set_logs_pending") = mod.attr("_set_logs_pending");
    mod.def("_drain_logs", &drain_messages);
    mod.def("_signal_at_drain_transition", [](std::string const & step, int sig)
      {
        if(step == "snapshot") drain_snapshot_signal = sig;
        else if(step == "between") drain_between_signal = sig;
        else throw py::value_error("unknown drain transition");
      });
    logs_pending = py::len(py::getattr(locking.attr("_local"), "messages", py::list())) != 0;
    py::object cls = locking.attr("Lock");
    cls.attr("acquire") = py::cpp_function([](py::object self, bool blocking, double timeout)
      { return lock_state(self).acquire(blocking, timeout); }, py::is_method(cls),
      py::arg("blocking") = true, py::arg("timeout") = -1);
    cls.attr("release") = py::cpp_function([](py::object self)
      { lock_state(self).release(); }, py::is_method(cls));
    cls.attr("__enter__") = py::cpp_function([](py::object self)
      { lock_state(self).acquire(true, -1); return self; }, py::is_method(cls));
    cls.attr("__exit__") = py::cpp_function([](py::object self, py::args)
      { lock_state(self).release(); }, py::is_method(cls));
    cls.attr("locked") = py::cpp_function([](py::object self)
      { return lock_state(self).owner.load() != 0; }, py::is_method(cls));
    cls.attr("_signal_at_transition") = py::cpp_function(
      [](py::object self, std::string const & step, int sig)
      {
        auto & lock = lock_state(self);
        if(step == "acquire") lock.acquire_signal = sig;
        else if(step == "release") lock.release_signal = sig;
        else throw py::value_error("unknown lock transition");
      }, py::is_method(cls));
  }
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
  mod.def("_fork_prepare", &curryrt::fork_prepare);
  mod.def("_fork_check", &curryrt::fork_check);
  mod.def("_fork_poisoned", &curryrt::fork_poisoned);
  mod.def("_fork_work_begin", &curryrt::fork_work_begin);
  mod.def("_fork_work_end", &curryrt::fork_work_end);
  mod.def("_fork_abandon", [](pybind11::object value) {
    // Retain inherited executable owners without invoking LLVM destructors
    // or acquiring any of the vanished compiler thread's internal locks.
    (void) new pybind11::object(std::move(value));
  });
  mod.def("_check_reentrancy", &curryrt::check_reentrancy);
  register_host_locks(mod);
  curryrt::set_host_lock_held(&python_lock_held);
  // Group native metadata operations and their Python publication without
  // acquiring a Python mutex before a heap wait. Never used for stepping.
  mod.def("_metadata_call", [](pybind11::function action) { return action(); },
      curryrt::python::heap_access());
  mod.def("_heap_drain", []
    {
      pybind11::gil_scoped_release release;
      curryrt::HeapScope heap;
      curryrt::heap_drain();
    });
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
