#pragma once
#include <cstddef>

namespace curryrt
{
  // Private test controls: pause a nonempty drain after detaching its list.
  bool heap_test_completion(bool retire);
  bool heap_test_child_fence();
  void heap_test_pause_drain();
  void heap_test_resume_drain();
  void heap_test_resume_at_fork();
  bool heap_test_resumer_ready();
  bool heap_test_drain_paused();
  void heap_test_dispose();
  size_t heap_test_applied();
  // Hold readiness back while the caller polls during worker startup.
  void worker_test_pause_startup();
  void worker_test_resume_startup();
  bool worker_test_startup_paused();
}
