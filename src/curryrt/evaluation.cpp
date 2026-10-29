#include "curryrt/evaluation.hpp"
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
    void before_fork() { gate_ptr()->mutex.lock(); }
    void parent_after_fork() { gate_ptr()->mutex.unlock(); }
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
    std::atomic<host_poll_type> poll_hook{nullptr};
    std::atomic<host_wait_type> wait_hook{nullptr};
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
  void host_poll() { if(auto hook = poll_hook.load()) hook(); }

  bool heap_try_lock()
  {
    auto & g = gate();
    std::lock_guard<std::mutex> lock(g.mutex);
    auto const self = std::this_thread::get_id();
    if(g.depth && g.owner != self) { ++g.counts.waits; return false; }
    if(!g.depth) ++g.counts.entries;
    g.owner = self;
    ++g.depth;
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
    }
  }

  void heap_lock(bool poll)
  {
    if(heap_try_lock()) return;
    if(auto wait = wait_hook.load()) wait(&wait_for_heap, &poll);
    else wait_for_heap(&poll);
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
