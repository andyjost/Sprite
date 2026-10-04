#include "cyrt/exceptions.hpp"
#include "cyrt/fingerprint.hpp"
#include "cyrt/state/rts.hpp"
#include <sstream>

namespace cyrt
{
  void RuntimeState::append(std::unique_ptr<Configuration> config)
  {
    this->Q()->push_back(std::move(config));
  }

  void RuntimeState::prepend(std::unique_ptr<Configuration> config)
  {
    this->Q()->push_front(std::move(config));
  }

  // Takes the front configuration out of the current queue and destroys
  // it.  Its nodes stay in the graph until the collector finds them
  // unreachable.
  void RuntimeState::drop(TraceOpt trace)
  {
    #ifdef SPRITE_TRACE_ENABLED
    if(trace && this->trace)
      this->trace->failed(this->Q());
    #endif
    this->Q()->pop_front();
  }

  Expr RuntimeState::make_value()
  {
    Cursor root = this->E();
    // A top-level IO action yields its payload, as in the Python backend.
    if(root.kind == 'p' && root->info == &IO_Info)
      root = root->successor(0);
    return copy_graph(root, SKIPFWD, this->S());
  }

  static bool _make_ready(RuntimeState * rts, Configuration * C)
  {
    if(C->forced_rotate)
    {
      C->forced_rotate = false;
      return true;
    }
    if(C->residuals.empty())
      return true;
    Residuals remaining;
    for(auto vid: C->residuals)
    {
      Node * var = rts->vtable[vid];
      if(rts->is_void(C, var))
        remaining.insert(vid);
    }
    if(remaining.size() < C->residuals.size())
    {
      C->residuals.swap(remaining);
      return true;
    }
    else
      return false;
  }

  bool RuntimeState::ready()
  {
    Queue * Q = this->Q();
    size_t const N = Q->size();
    if(!N)
      return false;
    Configuration * C = nullptr;
    for(size_t i=0; i<N; ++i)
    {
      // The front is about to be read and stepped: it must be private to
      // this queue.
      C = Q->unshare_front();
      if(_make_ready(this, C))
        return true;
      else
        this->rotate(Q);
    }
    throw EvaluationSuspended("");
  }

  Expr RuntimeState::release_value()
  {
    Expr value = this->make_value();
    #ifdef SPRITE_TRACE_ENABLED
    if(this->trace) this->trace->yield(value);
    #endif
    SCHEDULER_COUNT_END(this->C(), END_VALUE);
    this->drop(NOTRACE);
    return value;
  }

  void RuntimeState::rotate(Queue * Q, bool forced)
  {
    assert(Q);
    if(forced)
      Q->front()->forced_rotate = true;
    if(Q->size() > 1)
      Q->rotate();
  }

  // Handles E_UNWIND for C, the head of Q: the evaluation of C reached the
  // stack limit and unwound to procD.  Returns true when procD continues with
  // Q, and false when the unwind goes to the enclosing queue.
  //
  // A configuration that took no step since it last unwound is stuck: it
  // repeats the same descent and reaches the limit at the same point.  (A
  // step of a nested set-function evaluation counts for the enclosing
  // configuration.)  Re-scanning a configuration from its root repeats the
  // descent but loses no work, because the graph holds every result.
  //
  // In the outermost queue, a configuration that made progress runs again
  // after the others.  A stuck one is dropped, and its error waits until the
  // queue is empty (see procD), so the other alternatives still produce their
  // values.  In a nested queue, a configuration cannot be dropped without
  // losing a value of the set function.  It runs again after the others when
  // any step was taken since it last unwound.  That keeps a sibling that can
  // proceed running.  When no step was taken, the enclosing queue decides.
  bool RuntimeState::unwind(Queue * Q, Configuration * C)
  {
    if(this->in_recursive_call())
    {
      if(Q->size() > 1 && this->steps_total != C->unwind_total)
      {
        C->unwind_total = this->steps_total;
        this->rotate(Q, true);
        return true;
      }
      return false;
    }
    if(C->steps != C->unwind_steps)
    {
      C->unwind_steps = C->steps;
      this->rotate(Q, true);
      return true;
    }
    if(this->deferred_error.empty())
    {
      std::stringstream ss;
      ss << "stack limit of " << this->stack_room
         << " bytes exceeded (flag stack_limit)";
      this->deferred_error = ss.str();
    }
    SCHEDULER_COUNT_END(C, END_FAILURE);
    this->drop();
    return true;
  }

  // Sets the error for a choice inside a monadic action and returns E_ERROR.
  // The error value is the Prelude's NondetError, which catch hands to the
  // handler.  The Python backend raises NondetMonadError with the same text.
  tag_type RuntimeState::nondet_monad_error(Configuration * C)
  {
    Node * value = Node::create(
        ioerror_info(NONDET_ERROR), cstring(NONDET_MONAD_ERROR_TEXT)
      );
    C->set_error(value, NONDET_MONAD_ERROR_TEXT);
    return E_ERROR;
  }

  void RuntimeState::set_goal(Node * goal)
  {
    this->prepend(Configuration::create(goal));
  }
}
