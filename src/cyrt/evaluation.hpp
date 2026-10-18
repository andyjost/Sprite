#pragma once
#include <cstddef>
#include <thread>

namespace cyrt
{
  // Serialization of the shared heap is a stopgap for the concurrent runtime
  // of epic #28, not its design.  The allocator and collector currently own
  // one process-wide heap.  Bindings use this same lock, never a second one.
  // Ownership is recursive for callbacks; only the worker handoff may move
  // an existing ownership to another thread, while the caller is parked.
  bool heap_try_lock();
  void heap_lock(bool poll = true);
  void heap_unlock();
  void heap_handoff(std::thread::id);
  struct HeapStatus { size_t entries, waits, handoffs; };
  HeapStatus heap_status();

  struct HeapScope
  {
    explicit HeapScope(bool poll = true) { heap_lock(poll); }
    ~HeapScope() { heap_unlock(); }
    HeapScope(HeapScope const &) = delete;
    HeapScope & operator=(HeapScope const &) = delete;
  };

  // A host may install a signal/cancellation poll.  It runs at safepoints
  // and during timed waits, with no internal mutex held; a binding takes
  // its host lock inside the hook.  Pure C++ clients need no hook.
  using host_poll_type = void (*)();
  void set_host_poll(host_poll_type);
  using host_wait_type = void (*)(void (*)(void *), void *);
  void set_host_wait(host_wait_type);
  void host_poll();

  struct RuntimeState;
  struct Expr;
  bool on_evaluation_worker();
  size_t evaluation_worker_room(char const * base);
  Expr worker_evaluate(RuntimeState &);
}
