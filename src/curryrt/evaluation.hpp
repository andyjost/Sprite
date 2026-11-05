#pragma once
#include <cstddef>
#include <cstdint>
#include <thread>

namespace curryrt
{
  // Process forks are usable only when Sprite has no work in flight.
  void fork_check();
  bool fork_poisoned() noexcept;
  void fork_prepare();
  long long fork_work_begin();
  void fork_work_end(long long owner) noexcept;
  struct ForkWork
  {
    long long owner;
    ForkWork() : owner(fork_work_begin()) {}
    ~ForkWork() { fork_work_end(owner); }
    ForkWork(ForkWork const &) = delete;
    ForkWork & operator=(ForkWork const &) = delete;
  };

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

  // Allocate an action while its owner is constructed, before finalization.
  // dispose transfers ownership, and never waits for the heap. apply runs
  // under the heap, without the pending-list mutex. A stale action must not
  // dereference any address borrowed from the old heap.
  uint64_t heap_generation();
  struct PendingHeapAction
  {
    PendingHeapAction() : generation(heap_generation()) {}
    virtual ~PendingHeapAction() = default;
    virtual void apply(bool current) noexcept = 0;
    uint64_t generation;
    PendingHeapAction * next = nullptr;
  };
  void heap_dispose(PendingHeapAction *) noexcept;
  size_t heap_pending_count();
  void heap_drain() noexcept; // caller owns the heap
  // Call after draining and before releasing a heap that is being replaced.
  // Interpreter reset retains the process-wide node heap and does not call it.
  void heap_retire_generation() noexcept;

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
