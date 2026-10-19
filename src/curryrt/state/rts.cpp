#include "curryrt/checker.hpp"
#include "curryrt/graph/memory.hpp"
#include "curryrt/state/rts.hpp"
#include "curryrt/trace.hpp"
#include <cstdint>
#include <pthread.h>
#include <stdexcept>
#include <sys/resource.h>

namespace curryrt
{
  // The lowest address of the stack of the calling thread, or nullptr when it
  // is unknown.  pthread_getattr_np knows the stack of every thread; for the
  // main thread, glibc derives the size from RLIMIT_STACK.  Without it, the
  // stack is taken to extend RLIMIT_STACK bytes below this frame.
  static char const * stack_floor_of_this_thread()
  {
    #if defined(__linux__)
    pthread_attr_t attr;
    if(pthread_getattr_np(pthread_self(), &attr) == 0)
    {
      void * addr = nullptr;
      size_t size = 0;
      int const rc = pthread_attr_getstack(&attr, &addr, &size);
      pthread_attr_destroy(&attr);
      if(rc == 0 && addr)
        return (char const *) addr;
    }
    #elif defined(__APPLE__)
    return static_cast<char const *>(pthread_get_stackaddr_np(pthread_self()))
        - pthread_get_stacksize_np(pthread_self());
    #endif
    struct rlimit limit;
    if(getrlimit(RLIMIT_STACK, &limit) == 0 && limit.rlim_cur != RLIM_INFINITY)
    {
      char probe;
      std::uintptr_t const here = (std::uintptr_t) &probe;
      if(here > limit.rlim_cur)
        return (char const *) (here - limit.rlim_cur);
    }
    return nullptr;
  }

  RuntimeState::RuntimeState(
      InterpreterState & istate, Node * goal, bool trace
    , size_t stack_limit
    , size_t rotation_steps, uint64_t rotation_quantum_ns, bool checker
    , size_t worker_stack
    )
    : istate(istate), rotation_steps(rotation_steps)
    , rotation_next(rotation_steps), rotation_quantum_ns(rotation_quantum_ns)
    , root_queue(new Queue())
    , stack_limit(stack_limit), worker_stack(worker_stack)
  {
    // Time mode needs a quantum: a ticker with none would never release its
    // mutex (curryrt/ticker.hpp).  The Python side guarantees one; this guards
    // the constructor itself.
    if(rotation_steps == TIME_MODE && rotation_quantum_ns == 0)
      throw std::invalid_argument(
          "the rotation in time mode needs a quantum above zero nanoseconds"
        );
    this->push_queue(this->root_queue.get(), NOTRACE);
    // The checker of the run-time invariants (the flag ``checker``).  See
    // curryrt/checker.hpp.
    if(checker)
      this->checker = new Checker(*this);
    this->set_goal(goal);
		#ifdef SPRITE_TRACE_ENABLED
		if(trace)
		  this->trace.reset(new Trace(*this));
    #endif
    #ifdef SPRITE_SCHEDULER_COUNTERS
    // The queue holds the goal; a run without a fork never grows it.
    this->counters.queue_max = this->root_queue->size();
    #endif
    gc_register_rts(this);
  }

  // The outermost queue and its configurations go with the state.  A queue
  // of a set function belongs to its SetEval node; the collector frees it.
  RuntimeState::~RuntimeState()
  {
    HeapScope heap(false);
    delete this->checker;
    gc_unregister_rts(this);
    this->root_queue.reset();
  }

  // Records the frame of the outermost procD and sets the stack room for this
  // entry: the configured limit, clamped to the stack below the frame less
  // STACK_MARGIN.  The clamp keeps the guard effective when the flag names a
  // limit larger than the stack; without it, the process would overflow the
  // stack and crash.  The floor is cached for the thread of the last entry.
  // Linux has an exact pthread probe, macOS its stack-address API, and
  // other POSIX hosts fall back to RLIMIT_STACK with the safety margin.
  // The worker knows its reservation and subtracts the frames already in
  // use, including those of a re-entrant callback.
  void RuntimeState::set_stack_base(char const * base)
  {
    this->stack_base = base;
    if(this->stack_limit == NOLIMIT && !on_evaluation_worker())
    {
      this->stack_room = NOLIMIT;
      return;
    }
    if(on_evaluation_worker())
    {
      this->stack_room = evaluation_worker_room(base);
      return;
    }
    auto const thread = std::this_thread::get_id();
    if(this->stack_thread != thread)
    {
      this->stack_floor = stack_floor_of_this_thread();
      this->stack_thread = thread;
    }
    size_t room = this->stack_limit;
    std::uintptr_t const top = (std::uintptr_t) base;
    std::uintptr_t const floor = (std::uintptr_t) this->stack_floor;
    if(floor && top > floor)
    {
      size_t const below = top - floor;
      size_t const usable = below > STACK_MARGIN ? below - STACK_MARGIN : 0;
      if(usable < room)
        room = usable;
    }
    this->stack_room = room;
  }
}
