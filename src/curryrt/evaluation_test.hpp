#pragma once
#include <cstddef>

namespace curryrt
{
  // Private test controls: pause a nonempty drain after detaching its list.
  void heap_test_pause_drain();
  void heap_test_resume_drain();
  void heap_test_resume_at_fork();
  bool heap_test_resumer_ready();
  bool heap_test_drain_paused();
  void heap_test_dispose();
  size_t heap_test_applied();
}
