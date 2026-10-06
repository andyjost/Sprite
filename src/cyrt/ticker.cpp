#include <chrono>
#include <condition_variable>
#include <mutex>
#include <pthread.h>
#include <stdexcept>
#include <string>
#include <thread>
#include "cyrt/ticker.hpp"

// The ticker thread of time mode.  See ticker.hpp.
namespace cyrt
{
  std::atomic<unsigned char> g_tick{0};

  namespace
  {
    // The state shared with the thread.  ``active`` and ``started`` are
    // read by the evaluating thread without the mutex; the other fields are
    // written under the mutex.  The thread reads ``active`` under the mutex
    // before it parks, and the first evaluation takes the mutex before it
    // wakes the thread, so no wakeup is lost.
    struct State
    {
      std::mutex              mutex;
      std::condition_variable cv;
      std::atomic<size_t>     active{0};
      std::atomic<uint64_t>   quantum_ns{10000000};
      std::atomic<uint64_t>   ticks{0};
      std::atomic<bool>       started{false};
      bool                    parked = false;
    };

    // The state is made once and never destroyed.  A fork child replaces
    // the pointer (child_after_fork); the state of the parent, whose mutex
    // the parent's thread may hold at the fork, is never touched again.
    State *& state_ptr()
    {
      static State * instance = new State;
      return instance;
    }

    void ticker()
    {
      pthread_setname_np(pthread_self(), "cyrt-ticker");
      State & st = *state_ptr();
      std::unique_lock<std::mutex> lock(st.mutex);
      while(true)
      {
        if(st.active.load(std::memory_order_relaxed) == 0)
        {
          st.parked = true;
          st.cv.wait(
              lock
            , [&]{ return st.active.load(std::memory_order_relaxed) > 0; }
            );
          st.parked = false;
          continue;
        }
        // One quantum of sleep, with the mutex released.  Nothing notifies
        // the variable while the thread is not parked, so a return before
        // the deadline is spurious and the loop sleeps on.  The quantum is
        // above zero (ticker_enter), so every pass releases the mutex.
        auto const deadline = std::chrono::steady_clock::now()
            + std::chrono::nanoseconds(
                  st.quantum_ns.load(std::memory_order_relaxed)
                );
        while(std::chrono::steady_clock::now() < deadline)
          st.cv.wait_until(lock, deadline);
        // The tick is set while an evaluation runs.  A tick set just after
        // an evaluation ended is harmless: the next evaluation finds nothing
        // to rotate in its queue of one configuration.
        if(st.active.load(std::memory_order_relaxed) > 0)
        {
          g_tick.store(1, std::memory_order_relaxed);
          st.ticks.fetch_add(1, std::memory_order_relaxed);
        }
      }
    }

    // The child of a fork has no thread.  Fresh state with no thread and a
    // clear byte lets the first evaluation entered in the child start a
    // ticker of its own (ticker_enter starts the thread whenever the state
    // has none).  The count of the evaluations in flight carries over, so
    // the scope of an evaluation that spans the fork leaves a consistent
    // count.  The old state leaks: its mutex may be held by a thread that
    // does not exist here.  glibc makes malloc usable in the child before
    // the handlers of pthread_atfork run.
    void child_after_fork()
    {
      State * const old = state_ptr();
      State * const fresh = new State;
      fresh->active.store(
          old->active.load(std::memory_order_relaxed)
        , std::memory_order_relaxed
        );
      fresh->quantum_ns.store(
          old->quantum_ns.load(std::memory_order_relaxed)
        , std::memory_order_relaxed
        );
      state_ptr() = fresh;
      g_tick.store(0, std::memory_order_relaxed);
    }

    // Called under the mutex of ``st``.  Throws std::system_error when the
    // thread cannot start; ``started`` stays false then.
    void start_thread(State & st)
    {
      static bool atfork_registered = false;
      if(!atfork_registered)
      {
        pthread_atfork(nullptr, nullptr, &child_after_fork);
        atfork_registered = true;
      }
      std::thread(ticker).detach();
      st.started.store(true, std::memory_order_relaxed);
    }
  }

  void ticker_enter(uint64_t quantum_ns)
  {
    // A thread with no quantum would never release its mutex.
    if(quantum_ns == 0)
      throw std::invalid_argument(
          "the ticker of time mode needs a quantum above zero nanoseconds"
        );
    State & st = *state_ptr();
    st.quantum_ns.store(quantum_ns, std::memory_order_relaxed);
    // The thread starts when the state has none, whatever the count: the
    // state of a fork child carries the count of the evaluations in flight
    // at the fork, and none of them has a ticker.  Otherwise the first
    // evaluation wakes the parked thread.
    size_t const before = st.active.fetch_add(1, std::memory_order_acq_rel);
    if(before == 0 || !st.started.load(std::memory_order_relaxed))
    {
      std::lock_guard<std::mutex> lock(st.mutex);
      if(!st.started.load(std::memory_order_relaxed))
      {
        try
          { start_thread(st); }
        catch(std::exception const & e)
        {
          // No scope of this evaluation exists yet, so nothing else would
          // take the count back.  The next evaluation tries again.
          st.active.fetch_sub(1, std::memory_order_acq_rel);
          throw std::runtime_error(
              std::string("cannot start the ticker thread of time mode (")
            + e.what() + "); set the rotation to step mode, for example "
              "SPRITE_ROTATION=steps:65536"
            );
        }
      }
      else if(st.parked)
        st.cv.notify_one();
    }
  }

  void ticker_leave()
  {
    state_ptr()->active.fetch_sub(1, std::memory_order_acq_rel);
  }

  TickerStatus ticker_status()
  {
    State & st = *state_ptr();
    std::lock_guard<std::mutex> lock(st.mutex);
    TickerStatus status;
    status.started = st.started.load(std::memory_order_relaxed);
    status.parked = st.parked;
    status.active = st.active.load(std::memory_order_relaxed);
    status.ticks = st.ticks.load(std::memory_order_relaxed);
    status.quantum_ns = st.quantum_ns.load(std::memory_order_relaxed);
    return status;
  }
}
