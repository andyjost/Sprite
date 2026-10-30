// The platform layer: the few services of the operating system that the
// runtime uses, with a POSIX and a Windows implementation (platform.cpp).
// Threads with a chosen stack size, the name of a thread, the handlers of
// fork, the stack of the calling thread, aligned allocation, and the
// loading of shared objects.  Everything else in the runtime is portable
// C++17.  The port to Windows (the portability memo, step 4) runs the
// interpreter: the background compile of the tiered mode stays POSIX and
// reports itself unavailable elsewhere.
#pragma once

#include <cstddef>
#include <string>

namespace curryrt { namespace platform {

  // A thread of the operating system.  ``start`` runs ``main(arg)`` on a new
  // thread whose stack reserves ``stack_size`` bytes (0: the default of the
  // platform); it returns false and sets ``error`` when the thread cannot be
  // made.  ``join`` waits for the thread and releases it.
  struct Thread
  {
    void * handle = nullptr;   // pthread_t, boxed, or a HANDLE
    bool started = false;
  };
  bool start(Thread & thread, size_t stack_size, void * (*main)(void *), void * arg, std::string * error);
  void join(Thread & thread);

  // The name of the calling thread, for debuggers and profilers; best effort.
  void set_current_thread_name(char const * name);

  // The handlers of fork(2); Windows has no fork and the call does nothing.
  void at_fork(void (*prepare)(), void (*parent)(), void (*child)());

  // The lowest address of the stack of the calling thread, or nullptr when
  // the platform cannot say.
  char const * stack_floor_of_this_thread();

  // Aligned allocation and its release; the pair belongs together.
  void * aligned_allocate(size_t alignment, size_t size);
  void aligned_release(void * memory);

  // Shared objects.  ``load`` maps the object at ``path`` with its symbols
  // visible to objects loaded later (RTLD_GLOBAL on POSIX; the one namespace
  // of Windows); nullptr and ``error`` on failure.  ``loaded`` answers
  // whether the object at ``path`` is mapped already, without loading it.
  // ``symbol`` looks a name up in a loaded object.  ``unload`` releases a
  // handle; false and ``error`` on failure.
  void * load(std::string const & path, std::string * error);
  bool loaded(std::string const & path);
  void * symbol(void * handle, char const * name);
  bool unload(void * handle, std::string * error);

  // The path of the shared object that holds ``address``, or the empty
  // string when the platform cannot say (the runtime library finds itself
  // this way).
  std::string path_of_object_holding(void const * address);

  // The identity of this process, for the names of temporary files.
  long long process_id();
}}
