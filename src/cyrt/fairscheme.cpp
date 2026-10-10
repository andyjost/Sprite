#include "cyrt/builtins.hpp"
#include "cyrt/checker.hpp"
#include "cyrt/exceptions.hpp"
#include "cyrt/graph/indexing.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"
#include <iostream>

#ifdef SPRITE_GC_WRITE_COUNTERS
  #include "cyrt/graph/gc/block.hpp"
  #define GC_COUNT_REDEX_WRITE(redex) gc_count_redex_write_fast(redex)
#else
  #define GC_COUNT_REDEX_WRITE(redex)
#endif


#ifdef SPRITE_TRACE_ENABLED
  #define TRACE_STEP_ENTER(cursor) \
      if(this->trace) { this->trace->enter_rewrite(this->Q(), cursor); }
  #define TRACE_STEP_EXIT(cursor) \
      if(this->trace) { this->trace->exit_rewrite(this->Q(), cursor); }
#else
  #define TRACE_STEP_ENTER(cursor)
  #define TRACE_STEP_EXIT(cursor)
#endif

namespace cyrt
{
  Expr RuntimeState::procD()
  {
    Queue * Q         = nullptr;
    Configuration * C = nullptr;
    tag_type tag      = NOTAG;

    // Tells the collector that an evaluation is on the C stack.  A collection
    // in a nested evaluation keeps every node allocated before this point.
    EvaluationScope evaluation_scope;

    // In time mode the ticker runs while the outermost procD of the state is
    // on the C stack (cyrt/ticker.hpp).  A nested procD (a set function)
    // runs inside that scope.
    TickerScope ticker_scope(
        this->rotation_steps == TIME_MODE && !this->in_recursive_call()
      , this->rotation_quantum_ns
      );

    #ifdef SPRITE_SCHEDULER_COUNTERS
    // The nodes a step allocates carry the serial number of the stepped
    // configuration; the enclosing one is restored when this scheduler
    // returns into its step.
    CreatorScope creator_scope;
    #endif

    // The stack guard measures from the outermost procD.  A set function
    // evaluates its queue in a nested procD, which keeps the base.
    if(!this->in_recursive_call())
      this->set_stack_base((char const *) __builtin_frame_address(0));

    while(this->ready())
    {
      Q = this->Q();
      C = Q->front();
      #ifdef SPRITE_SCHEDULER_COUNTERS
      g_creator_serial = C->serial;
      #endif
      tag = inspect::tag_of(C->root);
    redoD:
      switch(tag)
      {
        case T_UNBOXED : return this->release_value();
        case T_CONSTR  : if(this->constrain_equal(C, C->root))
                         {
                           *C->root = NodeU{C->root}.constr->value;
                           tag = inspect::tag_of(C->root);
                           goto redoD;
                         }
        case T_FAIL    : SCHEDULER_COUNT_END(C, END_FAILURE);
                         this->drop();
                         continue;
        case T_FREE    : tag = this->replace_freevar(C, C->root);
                         if(tag == T_FREE)
                           return this->release_value();
        case T_FWD     : compress_fwd_chain(C->root);
                         tag = inspect::tag_of(C->root);
                         goto redoD;
        case T_CHOICE  : if(this->choice_escapes(C, obj_id(C->root)))
                           return Expr{C->root};
                         else
                           this->fork(Q, C);
                         continue;
        case T_FUNC    : tag = this->procS(C);
                         goto redoD;
        // A collection runs in the outermost scheduler of the state, where
        // no step of the state is on the C stack: it marks the live heap
        // alone and reclaims every dead node, queue, and set.  A nested
        // scheduler hands E_GC outward, as it hands E_ROTATE; its queue
        // resumes when the enclosing configuration runs again.  A
        // collection changes nothing in the schedule: no queue rotates, and
        // the interrupted configuration continues.  Its forced flag makes
        // ready() accept it although the residuals it kept are still void
        // (see _make_ready).  So the stress mode of the collector, which
        // requests a collection at every step, follows the schedule of a
        // normal run; a rotation here turned a depth-first search into a
        // lockstep over all alternatives.
        case E_GC      : C->forced_rotate = true;
                         if(this->in_recursive_call())
                           return this->yield_control(E_GC);
                         run_gc();
                         continue;
        // E_ROTATE names the queue to rotate (see check_interrupts).  A
        // nested procD rotates its own queue as well, when that queue holds
        // more than one configuration, and hands the status outward.  So a
        // nested sibling gets its turn too.  E_UNWIND rotates or drops at
        // the outermost queue and rotates or goes outward at a nested one
        // (see unwind).
        //
        // A nested scheduler that yields leaves its front configuration in
        // the middle of a step, with any residual that step recorded (see
        // hnf_or_free).  The forced flag makes ready() accept the
        // configuration when the scheduler resumes, as in the E_GC case; a
        // queue of one configuration rotates nothing and would otherwise
        // find the residual void and suspend the set function.
        case E_ROTATE  : if(this->rotate_target && this->rotate_target != Q
                              && this->in_recursive_call())
                         {
                           C->forced_rotate = true;
                           if(Q->size() > 1)
                             this->rotate(Q, true);
                           return this->yield_control(E_ROTATE);
                         }
                         this->rotate_target = nullptr;
                         this->rotate(Q, true);
                         continue;
        case E_UNWIND  : if(this->unwind(Q, C))
                           continue;
                         C->forced_rotate = true;
                         return this->yield_control(E_UNWIND);
        // The step limit was reached (see step_limit).  A nested scheduler
        // hands the status out, as it hands E_UNWIND out; the outermost one
        // ends the evaluation.  The configuration is left as it is: the
        // evaluation never resumes.
        case E_TERMINATE: if(this->in_recursive_call())
                           return this->yield_control(E_TERMINATE);
                         throw StepLimitReached("the step limit was reached");
        // A boxed failure was demanded in this capsule (fail_capsule): the
        // nested scheduler hands the status to allValues_step, which makes
        // the set function a failure.  The queue is left as it is; nothing
        // runs it again.
        case E_SETFAIL : return this->yield_control(E_SETFAIL);
        // The nested evaluation read a binding of an enclosing
        // configuration (diverge): the scheduler hands the status out, up
        // to the allValues_step of that configuration, which clones the
        // capsule.  The front configuration stays in the middle of its
        // step, as after E_UNWIND.
        case E_DIVERGE : C->forced_rotate = true;
                         return this->yield_control(E_DIVERGE);
        case E_ERROR   : C->raise_error();
        case E_RESIDUAL: this->rotate(Q);
                         continue;
        case E_RESTART : tag = inspect::tag_of(C->root);
                         goto redoD;
        // A set guard at the root: the value of the set function is a
        // sub-term of its guarded argument (set1 id x).  The guard is a node
        // of the spine like a constructor.  procN descends into it, and a
        // choice found below it is pulled up through it, which puts the
        // choice into the escape set of the guard's set (Scan::copy_spine),
        // so the choice escapes the set function.  release_value drops the
        // guards of the current set from the value (make_value).
        case T_SETGRD  :
        default        : TRACE_STEP_ENTER(C->root)
                         tag = this->procN(C, C->root);
                         TRACE_STEP_EXIT(C->root)
                         if(tag == T_CTOR)
                           return this->release_value();
                         else
                         {
                           C->scan.reset();
                           goto redoD;
                         }
      }
    }
    // The queue is empty.  An alternative dropped at the stack limit reports
    // its error now, after the other alternatives produced their values.
    if(!this->in_recursive_call() && !this->deferred_error.empty())
    {
      std::string message;
      message.swap(this->deferred_error);
      throw EvaluationError(message);
    }
    return Expr{};
  }

  tag_type RuntimeState::procN(Configuration * C, Cursor root)
  {
    size_t ret = 0;
    tag_type tag = 0;
    #ifdef SPRITE_TRACE_ENABLED
    PositionKey key;
    #endif
    for(auto * scan = &C->scan; *scan; ++(*scan))
    {
      tag = inspect::tag_of(scan->cursor());
    redoN:
      switch(tag)
      {
        case T_UNBOXED : continue;
        case T_SETGRD  : scan->extend(); ++(*scan); continue;
        case T_FAIL    : if(this->failure_escapes(C, nullptr))
                           return this->fail_capsule(C, nullptr);
                         return root->make_failure();
        case T_CONSTR  : *root = this->lift_constraint(C, root, scan->cursor());
                         return inspect::tag_of(root);
        case T_FREE    : tag = this->replace_freevar(C, root);
                         if(tag <= E_RESTART) goto redoN; else continue;
        case T_FWD     : compress_fwd_chain(scan->cursor());
                         tag = inspect::tag_of(scan->cursor());
                         goto redoN;
        case T_CHOICE  : *root = this->pull_tab(C, root, scan->cursor());
                         return T_CHOICE;
        case T_FUNC    : if(this->stack_exhausted()) return E_UNWIND;
                         ret = scan->size();
                         #ifdef SPRITE_TRACE_ENABLED
                         if(this->trace) { key = this->trace->enter_position(this->Q(), *scan); }
                         #endif
                         tag = this->procS(C);
                         #ifdef SPRITE_TRACE_ENABLED
                         if(this->trace) { this->trace->exit_position(this->Q(), key); }
                         #endif
                         scan->resize(ret);
                         goto redoN;
        case E_DIVERGE :
        case E_SETFAIL :
        case E_TERMINATE:
        case E_UNWIND  :
        case E_GC      :
        case E_ROTATE  :
        case E_ERROR   :
        case E_RESIDUAL:
        case E_RESTART : return tag;
        default        :
          if(!is_partial(*scan->cursor()->info))
            scan->extend();
      }
    }
    return T_CTOR;
  }

  tag_type RuntimeState::procS(Configuration * C)
  {
    TRACE_STEP_ENTER(C->cursor())
    #if defined(SPRITE_SCHEDULER_COUNTERS) || defined(SPRITE_GC_WRITE_COUNTERS)
    // The redex is rewritten in place, so its address names it after the
    // step as well.  A function node is never a pinned object.
    Node * const redex = C->cursor().arg->node;
    assert(!is_pinned(*redex->info));
    #endif
    // The checker records the redex before the step and checks the
    // completed step after it (cyrt/checker.hpp).
    if(this->checker)
      this->checker->step_begin(C);
    auto status = C->cursor()->info->step(this, C);
    if(this->checker)
      this->checker->step_end(C, status);
    // A step writes its result into its redex.  The counter of writes into
    // old nodes (gc/wdgc.cpp) runs on every return: an interrupted step may
    // have written too (writeFile advances its string in place before the
    // next hnf).
    GC_COUNT_REDEX_WRITE(redex);
    TRACE_STEP_EXIT(C->cursor())
    // Only a rewrite counts as a step.  A status below E_RESTART means the
    // step was interrupted (E_UNWIND, E_GC, E_ROTATE, E_TERMINATE), suspended
    // (E_RESIDUAL), or raised an error (E_ERROR), and the redex is as it was.
    // The Python backend applies the same rule (see S in fairscheme.py).
    //
    // A completed step is the safepoint of the scheduler: the periodic
    // rotation and a requested collection interrupt here (check_interrupts).
    // The step rewrote its redex, most often in place, so the status is the
    // tag of the result; the interrupt replaces it, and the caller finds the
    // result in the graph when the configuration runs again.  Before the
    // in-place rewrite every step left a forward node, and the check ran
    // when a consumer compressed it.  E_RESTART passes unchanged: it tells
    // every enclosing step that the root was replaced (replace_freevar), and
    // each of them counts it on the way out; the next step checks.
    if(status >= E_RESTART)
    {
      // The step limit (see step_limit): the evaluation ends after this
      // step, with the redex as the step wrote it.  The test reads the
      // count before the increment, from the value count_step loads, so
      // that it costs one compare per completed step; the limit is NOLIMIT
      // unless the stepper set one.
      bool const last = this->steps_total + 1 >= this->step_limit;
      this->count_step();
      SCHEDULER_COUNT_SHARED(redex, C);
      if(__builtin_expect(last, 0))
        return E_TERMINATE;
      if(status != E_RESTART)
        status = this->check_interrupts(status);
    }
    return status;
  }

  tag_type RuntimeState::hnf(
      Configuration * C, Variable * inductive, void const * guides
    , bool monadic
    )
  {
    Cursor _0 = C->cursor();
    // The checker tests the inductive position against the definitional
    // tree of the operation (B2; cyrt/checker.hpp).
    if(this->checker)
      this->checker->hnf(C, inductive);
    // A choice at the inductive position of a monadic step is an error: an
    // I/O action cannot fork.  The Python backend raises NondetMonadError
    // there.  The flag covers a strict application of a monadic function,
    // whose argument is evaluated by ($!) on behalf of that function.
    monadic = monadic || is_monadic(*_0->info);
    tag_type tag = inspect::tag_of(inductive->target);
    while(true)
    {
      switch(tag)
      {
        // The step at the inductive position rewrote it to a guarded
        // expression: a function returned its guarded argument (set1 id x).
        // Cross the guard as the indexer does (Variable::skip): its set
        // joins the guards of the variable, and the guarded expression
        // becomes the target.  rvalue puts the guard back, and a choice
        // found below it joins the escape set (update_escape_sets).
        case T_SETGRD:
        {
          SetGrdNode * guard = NodeU{inductive->target}.setgrd;
          inductive->guards.push_back(guard->set);
          inductive->realpath.push_back(1);
          inductive->target = Cursor(guard->value);
          tag = inspect::tag_of(inductive->target);
          continue;
        }
        case T_FAIL  : if(this->failure_escapes(C, inductive))
                         return this->fail_capsule(C, inductive);
                       _0->forward_to(Fail);
                       return T_FWD;
        case T_CONSTR: _0->forward_to(this->lift_constraint(C, inductive));
                       return T_FWD;
        case T_FREE  : tag = this->replace_freevar(C, inductive, guides);
                       continue;
        case T_FWD   : compress_fwd_chain(inductive->target);
                       tag = inspect::tag_of(inductive->target);
                       continue;
        case T_CHOICE: if(monadic)
                         return this->nondet_monad_error(C);
                       inductive->update_escape_sets(); // move this into pull_tab?
                       _0->forward_to(this->pull_tab(C, inductive));
                       return T_FWD;
        // A step that rewrites the redex in place to another function node
        // (a tail call) is followed by the step of that node under the same
        // scan frame.
        case T_FUNC  : if(this->stack_exhausted()) return E_UNWIND;
                       C->scan.push(inductive);
                       do
                         tag = this->procS(C);
                       while(tag == T_FUNC);
                       C->scan.pop();
                       continue;
        default      : return tag;
      }
    }
  }

  // Head-normalizes the expression at ``inductive`` and reports a free
  // variable there as T_FREE instead of E_RESIDUAL.  The caller handles the
  // variable itself (it binds it, or builds a constraint), so the residual
  // that hnf recorded for it (see instantiate) is taken back: the variable
  // and its group (add_residual records both).  Left in place, it made the
  // configuration "not ready" when the step was interrupted (E_GC,
  // E_ROTATE, E_UNWIND) before the caller acted on the variable, and a
  // nested scheduler then reported a false suspension.
  tag_type RuntimeState::hnf_or_free(
      Configuration * C, Variable * inductive, void const * guides
    )
  {
    tag_type tag = this->hnf(C, inductive, guides);
    if(tag == E_RESIDUAL && inspect::isa_freevar(inductive->target))
    {
      C->remove_residual(obj_id(inductive->target));
      return T_FREE;
    }
    else
      return tag;
  }
}

