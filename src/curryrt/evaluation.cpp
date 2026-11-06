#include "curryrt/evaluation.hpp"
#include "curryrt/evaluation_test.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/state/rts.hpp"
#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <condition_variable>
#include <exception>
#include <mutex>
#include "curryrt/platform.hpp"
#include <sstream>
#include <stdexcept>
#include <system_error>
#ifndef _WIN32
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace curryrt
{
  namespace
  {
    constexpr size_t MIN_WORKER_STACK = size_t(64) << 20;
    constexpr auto POLL_INTERVAL = std::chrono::milliseconds(10);
    struct Gate
    {
      std::mutex mutex;
      std::condition_variable cv;
      std::thread::id owner;
      size_t depth = 0;
      HeapStatus counts{0, 0, 0};
    };
    Gate *& gate_ptr() { static auto * p = new Gate; return p; }
    void drain_pending(bool complete) noexcept;
    void before_fork();
    void parent_after_fork();
    void child_after_fork();
    Gate & gate()
    {
      static bool const registered = []
      {
        (void) gate_ptr();
        platform::at_fork(before_fork, parent_after_fork, child_after_fork);
        return true;
      }();
      (void) registered;
      return *gate_ptr();
    }
    struct Pending
    {
      std::mutex mutex;
      PendingHeapAction * head = nullptr;
      size_t count = 0;
      std::atomic<uint64_t> generation{1};
    };
    // Retained for finalizers that run after library static destruction.
    Pending & pending() { static auto * p = new Pending; return *p; }
    // A drain owns this fence through its last apply/delete. Prepare takes
    // it before either short-lived mutex: apply may recursively take the heap.
    // Acquisition drains only try it; completion drains wait without either
    // bookkeeping mutex. Actions are native-only and never acquire the GIL; prepare
    // must not enter Python's host wait after Python has prepared its fork.
    std::recursive_mutex *& drain_fence_ptr()
    { static auto * p = new std::recursive_mutex; return p; }
    std::atomic<host_wait_type> wait_hook{nullptr};
    std::atomic<bool> test_pause{false}, test_paused{false};
    std::atomic<bool> test_preparing{false}, test_resumer_ready{false};
    std::atomic<size_t> test_applied{0};
    void before_fork()
    {
      auto * fence = drain_fence_ptr();
      if(!fence->try_lock())
      {
        test_preparing = true;
        fence->lock();
      }
      gate_ptr()->mutex.lock();
      pending().mutex.lock();
      test_preparing = true;
    }
    void parent_after_fork()
    {
      pending().mutex.unlock();
      gate_ptr()->mutex.unlock();
      drain_fence_ptr()->unlock();
    }
    thread_local bool draining = false;
    std::atomic<host_poll_type> poll_hook{nullptr};
    std::atomic<host_lock_held_type> lock_held_hook{nullptr};
    thread_local size_t boundary_depth = 0;
    struct BoundaryScope
    {
      BoundaryScope() { ++boundary_depth; }
      ~BoundaryScope() { --boundary_depth; }
    };
    thread_local bool is_worker = false;
    thread_local size_t reserved_room = 0;
    thread_local char const * worker_base = nullptr;

    struct Worker
    {
      std::mutex mutex;
      std::condition_variable cv;
      platform::Thread thread;
      std::thread::id id;
      RuntimeState * job = nullptr;
      Expr value;
      std::exception_ptr error;
      bool ready = false;
      bool done = false;
      bool stop = false;
      size_t requested = 0;
      size_t reserved = 0;
      std::string attempts;
    };
    Worker * retained_worker = nullptr; // guarded by the heap lock

    void child_after_fork()
    {
      // As with the ticker, the parent's parked thread does not survive
      // fork.  Keep recursion belonging to the surviving thread and leak
      // the old synchronization objects, which may have vanished waiters.
      // Other prepare callers may have been waiting on the old fence.
      // Retain it, just like the old gate, rather than destroying waiters.
      drain_fence_ptr()->unlock();
      drain_fence_ptr() = new std::recursive_mutex;
      // The surviving drain owns the replacement until its guard exits.
      if(draining) drain_fence_ptr()->lock();
      pending().mutex.unlock();
      Gate * old = gate_ptr();
      Gate * fresh = new Gate;
      if(old->owner == std::this_thread::get_id())
      {
        fresh->owner = old->owner;
        fresh->depth = old->depth;
      }
      fresh->counts = old->counts;
      gate_ptr() = fresh;
      retained_worker = nullptr;
      is_worker = false;
    }

    void * worker_main(void * arg)
    {
      auto & w = *static_cast<Worker *>(arg);
      is_worker = true;
      char base;
      worker_base = &base;
      std::unique_lock<std::mutex> lock(w.mutex);
      w.id = std::this_thread::get_id();
      w.ready = true;
      w.cv.notify_all();
      for(;;)
      {
        w.cv.wait(lock, [&]{ return w.job != nullptr || w.stop; });
        if(w.stop) return nullptr;
        RuntimeState & rts = *w.job;
        reserved_room = std::min(rts.worker_stack, w.reserved) - STACK_MARGIN;
        lock.unlock();
        try { w.value = rts.procD(); }
        catch(...) { w.error = std::current_exception(); }
        lock.lock();
        w.job = nullptr;
        w.done = true;
        w.cv.notify_all();
      }
    }

    Worker & get_worker(size_t requested)
    {
      if(requested < MIN_WORKER_STACK)
        throw EvaluationError("cannot reserve worker stack (flag worker_stack); "
            "attempted sizes in bytes: " + std::to_string(requested)
            + "; minimum reservation is " + std::to_string(MIN_WORKER_STACK),
            ErrorKind::stack);
      if(retained_worker && retained_worker->requested == requested)
        return *retained_worker;
      if(retained_worker)
      {
        {
          std::lock_guard<std::mutex> lock(retained_worker->mutex);
          retained_worker->stop = true;
          retained_worker->cv.notify_all();
        }
        platform::join(retained_worker->thread);
        delete retained_worker;
        retained_worker = nullptr;
      }
      std::ostringstream attempts;
      std::string refusal;
      for(size_t size = requested; ; size /= 2)
      {
        if(size != requested) attempts << ", ";
        attempts << size;
        std::unique_ptr<Worker> w;
        bool started = false;
        try
        {
          w = std::make_unique<Worker>();
          w->requested = requested;
          // C++17's std::thread has no stack-size constructor: the platform
          // layer reserves the stack (pthread_attr_setstacksize on POSIX,
          // the reservation flag of _beginthreadex on Windows).
          std::string thread_error;
          int rc = EINVAL;
          if(size >= MIN_WORKER_STACK)
            rc = platform::start(w->thread, size, worker_main, w.get(), &thread_error) ? 0 : EAGAIN;
          started = rc == 0;
          if(rc == 0)
          {
            w->reserved = size;
            w->attempts = attempts.str();
            std::unique_lock<std::mutex> lock(w->mutex);
            std::exception_ptr interrupted;
            while(!w->ready)
            {
              w->cv.wait_for(lock, POLL_INTERVAL);
              lock.unlock();
              if(!interrupted)
                try { host_poll(); }
                catch(...) { interrupted = std::current_exception(); }
              lock.lock();
            }
            if(interrupted) std::rethrow_exception(interrupted);
            retained_worker = w.release();
            return *retained_worker;
          }
          refusal = thread_error.empty() ? "thread error " + std::to_string(rc) : thread_error;
        }
        catch(std::bad_alloc const &)
        { refusal = "std::bad_alloc"; }
        catch(std::system_error const & error)
        { refusal = std::string("std::system_error: ") + error.what(); }
        catch(...)
        {
          if(started)
          {
            {
              std::lock_guard<std::mutex> lock(w->mutex);
              w->stop = true;
              w->cv.notify_all();
            }
            platform::join(w->thread);
          }
          throw;
        }
        // A failure during creation or the ready handoff refuses this
        // reservation too.  Retire a started worker before trying less.
        if(started)
        {
          {
            std::lock_guard<std::mutex> lock(w->mutex);
            w->stop = true;
            w->cv.notify_all();
          }
          platform::join(w->thread);
        }
        if(size <= MIN_WORKER_STACK) break;
        if(size / 2 < MIN_WORKER_STACK) size = MIN_WORKER_STACK * 2;
      }
      throw EvaluationError("cannot reserve worker stack (flag worker_stack); "
          "attempted sizes in bytes: " + attempts.str()
          + "; refused by " + refusal, ErrorKind::stack);
    }
  }

  void set_host_wait(host_wait_type hook) { wait_hook.store(hook); }
  void set_host_poll(host_poll_type hook) { poll_hook.store(hook); }
  void set_host_lock_held(host_lock_held_type hook) { lock_held_hook.store(hook); }
  void check_reentrancy()
  {
    auto held = lock_held_hook.load();
    if(boundary_depth || (held && held()))
      throw ReentrancyError("cannot reenter Sprite while this thread holds a Sprite lock "
                            "or waits for its evaluation worker");
  }
  void host_poll()
  {
    BoundaryScope boundary;
    if(auto hook = poll_hook.load()) hook();
  }

  bool heap_try_lock()
  {
    auto & g = gate();
    std::unique_lock<std::mutex> lock(g.mutex);
    auto const self = std::this_thread::get_id();
    if(g.depth && g.owner != self) { ++g.counts.waits; return false; }
    if(!g.depth) ++g.counts.entries;
    g.owner = self;
    ++g.depth;
    lock.unlock();
    drain_pending(false);
    return true;
  }

  namespace
  {
    void wait_for_heap(void * data)
    {
      bool const poll = *static_cast<bool *>(data);
      auto & g = gate();
      std::unique_lock<std::mutex> lock(g.mutex);
      auto const self = std::this_thread::get_id();
      while(g.depth && g.owner != self)
      {
        g.cv.wait_for(lock, POLL_INTERVAL);
        lock.unlock();
        if(poll) host_poll();
        lock.lock();
      }
      if(!g.depth) ++g.counts.entries;
      g.owner = self;
      ++g.depth;
      lock.unlock();
      drain_pending(false);
    }
  }

  void heap_lock(bool poll)
  {
    if(heap_try_lock()) return;
    check_reentrancy();
    if(auto wait = wait_hook.load()) wait(&wait_for_heap, &poll);
    else wait_for_heap(&poll);
  }

  uint64_t heap_generation() { return pending().generation.load(); }

  size_t heap_pending_count()
  {
    auto & p = pending();
    std::lock_guard<std::mutex> lock(p.mutex);
    return p.count;
  }

  namespace
  {
    // The observer is instantiated only by the completion test. Ordinary
    // calls use an empty lambda, with no test flag load or branch.
    template<class BeforeWait>
    void drain_pending(bool complete, BeforeWait before_wait) noexcept
    {
      if(draining) return;
      if(complete)
      {
        before_wait();
        drain_fence_ptr()->lock();
      }
      else if(!drain_fence_ptr()->try_lock()) return;
      draining = true;
      struct Guard
      {
        ~Guard()
        {
          draining = false;
          // A fork inside apply replaces the fence on this surviving thread.
          drain_fence_ptr()->unlock();
        }
      } guard;
      auto & p = pending();
      for(;;)
      {
        PendingHeapAction * actions;
        {
          std::lock_guard<std::mutex> lock(p.mutex);
          actions = p.head;
          p.head = nullptr;
          p.count = 0;
        }
        if(!actions) break;
        if(test_pause.load())
        {
          test_paused = true;
          while(test_pause.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
          test_paused = false;
        }
        while(actions)
        {
          auto * action = actions;
          actions = action->next;
          action->apply(action->generation == heap_generation());
          delete action;
        }
      }
    }

    void drain_pending(bool complete) noexcept
    { drain_pending(complete, [] {}); }

    template<class BeforeWait>
    void retire_generation(BeforeWait before_wait) noexcept
    {
      drain_pending(true, before_wait);
      ++pending().generation;
    }
  }

  void heap_drain() noexcept { drain_pending(true); }

  bool heap_test_completion(bool retire)
  {
    HeapScope heap(false);
    std::atomic<bool> held{false}, waiting{false};
    bool timed_out = false;
    std::thread blocker([&]
    {
      drain_fence_ptr()->lock();
      held = true;
      auto end = std::chrono::steady_clock::now() + std::chrono::seconds(10);
      while(!waiting)
      {
        if(std::chrono::steady_clock::now() >= end)
        {
          timed_out = true;
          break;
        }
        std::this_thread::yield();
      }
      drain_fence_ptr()->unlock();
    });
    while(!held) std::this_thread::yield();
    std::atomic<bool> current{false};
    struct Action : PendingHeapAction
    {
      std::atomic<bool> & current;
      explicit Action(std::atomic<bool> & c) : current(c) {}
      void apply(bool value) noexcept override { current = value; }
    };
    std::thread enqueue([&] { heap_dispose(new Action(current)); });
    enqueue.join();
    // The holder cannot release before this exact completion path reaches
    // its blocking lock. A try-only drain never acknowledges the wait.
    auto before_wait = [&] { waiting = true; };
    if(retire) retire_generation(before_wait);
    else drain_pending(true, before_wait);
    bool complete = heap_pending_count() == 0 && current;
    blocker.join();
    heap_drain();
    return !timed_out && waiting && complete && current;
  }

  bool heap_test_child_fence()
  {
#ifndef _WIN32
    HeapScope heap(false);
    bool covered = false;
    pid_t child = -1;
    struct Action : PendingHeapAction
    {
      bool & covered;
      pid_t & child;
      Action(bool & c, pid_t & p) : covered(c), child(p) {}
      void apply(bool) noexcept override
      {
        child = fork();
        if(child != 0) return;
        // Only native code runs in this child; no Python reattachment.
        alarm(10);
        std::thread probe([&]
        {
          covered = !drain_fence_ptr()->try_lock();
          if(!covered) drain_fence_ptr()->unlock();
        });
        probe.join();
      }
    };
    std::thread enqueue([&] { heap_dispose(new Action(covered, child)); });
    enqueue.join();
    heap_drain();
    if(child == 0)
    {
      bool released = false;
      std::thread probe([&]
      {
        released = drain_fence_ptr()->try_lock();
        if(released) drain_fence_ptr()->unlock();
      });
      probe.join();
      _exit(covered && released ? 0 : 1);
    }
    if(child < 0) return false;
    int status;
    pid_t result;
    do { result = waitpid(child, &status, 0); } while(result < 0 && errno == EINTR);
    return result == child && WIFEXITED(status) && WEXITSTATUS(status) == 0;
#else
    return false;
#endif
  }

  void heap_test_pause_drain()
  {
    test_applied = 0;
    test_preparing = false;
    test_resumer_ready = false;
    test_pause = true;
  }
  void heap_test_resume_drain() { test_pause = false; }
  void heap_test_resume_at_fork()
  {
    test_resumer_ready = true;
    auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(10);
    while(!test_preparing.load())
    {
      if(std::chrono::steady_clock::now() > deadline)
        throw std::runtime_error("fork prepare handshake timed out");
      std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
    heap_test_resume_drain();
  }
  bool heap_test_resumer_ready() { return test_resumer_ready.load(); }
  bool heap_test_drain_paused() { return test_paused.load(); }
  size_t heap_test_applied() { return test_applied.load(); }
  void heap_test_dispose()
  {
    struct Action : PendingHeapAction
    {
      void apply(bool) noexcept override
      {
        // Match the recursive acquisition in state/module removals.
        HeapScope heap(false);
        ++test_applied;
      }
    };
    heap_dispose(new Action);
  }

  void heap_dispose(PendingHeapAction * action) noexcept
  {
    if(heap_try_lock())
    {
      action->apply(action->generation == heap_generation());
      delete action;
      heap_unlock();
      return;
    }
    // No heap acquisition is attempted with this mutex held. The action
    // owns its storage; a state is still registered until apply deletes it.
    auto & p = pending();
    std::lock_guard<std::mutex> lock(p.mutex);
    action->next = p.head;
    p.head = action;
    ++p.count;
  }

  void heap_retire_generation() noexcept
  {
    retire_generation([] {});
  }

  void heap_unlock()
  {
    auto & g = gate();
    std::lock_guard<std::mutex> lock(g.mutex);
    assert(g.depth && g.owner == std::this_thread::get_id());
    if(--g.depth == 0)
    {
      g.owner = {};
      g.cv.notify_all();
    }
  }

  void heap_handoff(std::thread::id owner)
  {
    auto & g = gate();
    std::lock_guard<std::mutex> lock(g.mutex);
    assert(g.depth);
    ++g.counts.handoffs;
    g.owner = owner;
  }

  HeapStatus heap_status()
  {
    auto & g = gate();
    std::lock_guard<std::mutex> lock(g.mutex);
    return g.counts;
  }

  bool on_evaluation_worker() { return is_worker; }
  size_t evaluation_worker_room(char const * base)
  {
    auto const used = std::uintptr_t(worker_base) > std::uintptr_t(base)
        ? std::uintptr_t(worker_base) - std::uintptr_t(base) : 0;
    return used < reserved_room ? reserved_room - used : 0;
  }

  Expr worker_evaluate(RuntimeState & rts)
  {
    BoundaryScope boundary;
    Worker & w = get_worker(rts.worker_stack);
    auto const caller = std::this_thread::get_id();
    std::unique_lock<std::mutex> lock(w.mutex);
    rts.worker_attempts = w.attempts;
    w.error = nullptr;
    w.done = false;
    w.job = &rts;
    heap_handoff(w.id);
    w.cv.notify_all();
    std::exception_ptr interrupted;
    while(!w.done)
    {
      w.cv.wait_for(lock, POLL_INTERVAL);
      lock.unlock();
      if(!interrupted)
        try { host_poll(); }
        catch(...) { interrupted = std::current_exception(); rts.cancelled = true; }
      lock.lock();
    }
    heap_handoff(caller);
    rts.cancelled = false;
    auto error = std::move(w.error);
    if(interrupted) std::rethrow_exception(interrupted);
    if(error) std::rethrow_exception(error);
    return w.value;
  }
}
