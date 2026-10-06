#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>

// The ticker of the time mode of the rotation.
//
// The scheduler rotates its queue of configurations at a safepoint, after a
// completed rewrite step (RuntimeState::check_interrupts), so that a
// diverging alternative cannot starve the others.  Two modes pace the
// rotation.  In step mode the safepoint counts the steps and rotates every
// so many of them (65536 by default); the schedule depends on the program
// alone, so the exact steps and forks of a search reproduce between runs.
// In time mode, the default of the tools, a thread sets the byte g_tick
// every quantum (10 ms by default) with a relaxed store, and the safepoint
// polls the byte: a load and a branch per step, after the increment of the
// step count that both modes keep.  The latency of a waiting alternative
// is then bounded by the quantum whatever the cost of a step.  The
// completeness of the Fair Scheme holds for any finite quantum.
//
// The thread starts at the first evaluation in time mode and parks on a
// condition variable while no such evaluation is on the C stack (TickerScope
// counts them), so an idle host process has no wakeups.  It touches g_tick
// and its own state alone, never the runtime.  Its state is a leaked
// singleton: the destructor of a condition variable blocks until its
// waiters left, which would hang the exit of the process (see tiered.cpp).
// The detached thread ends with the process.
//
// A thread does not survive fork.  A child handler of pthread_atfork gives
// the child fresh state with no thread and a clear byte, and the count of
// the evaluations in flight at the fork.  The first evaluation entered in
// the child, nested in one of those or not, starts a ticker of its own,
// because the state has none.  An evaluation in flight at the fork runs in
// the child without a ticker until then.  A host that forks after an
// evaluation in time mode is multi-threaded, which Python's os.fork warns
// about; step mode starts no thread.
//
// The native workers of the performance program poll the same byte at their
// back-edges through ticker_due and return to the scheduler when it is set.
namespace cyrt
{
  // The byte the ticker sets every quantum.  Only the safepoint clears it.
  extern std::atomic<unsigned char> g_tick;

  // The hook of the safepoint and of the native workers: true when a quantum
  // passed since the last clear.
  inline bool ticker_due()
    { return g_tick.load(std::memory_order_relaxed) != 0; }

  inline void ticker_clear()
    { g_tick.store(0, std::memory_order_relaxed); }

  // Counts an evaluation in time mode on the C stack.  The first one starts
  // the thread or wakes it; the thread parks when the count is zero at a
  // tick.  ``quantum_ns`` is the quantum of this evaluation; the thread
  // takes the last one set.  A quantum of zero is a std::invalid_argument.
  // When the thread cannot start (std::thread throws, as under a limit on
  // the tasks of the user), ticker_enter leaves the count as it was and
  // throws a std::runtime_error that names the ticker and step mode; the
  // next evaluation tries again.
  void ticker_enter(uint64_t quantum_ns);
  void ticker_leave();

  struct TickerScope
  {
    TickerScope(bool on, uint64_t quantum_ns) : on(on)
      { if(on) ticker_enter(quantum_ns); }
    ~TickerScope() { if(on) ticker_leave(); }
    TickerScope(TickerScope const &) = delete;
    TickerScope & operator=(TickerScope const &) = delete;
    bool on;
  };

  // The state of the ticker, for the tests and the statistics.
  struct TickerStatus
  {
    bool     started = false;    // the thread exists in this process
    bool     parked = false;     // the thread waits for an evaluation
    size_t   active = 0;         // evaluations in time mode on the C stack
    uint64_t ticks = 0;          // ticks set since the start of the process
    uint64_t quantum_ns = 0;     // the quantum in use
  };
  TickerStatus ticker_status();
}
