#pragma once
#include "cyrt/fwd.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/queue.hpp"
#include <cstdint>
#include <initializer_list>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#ifdef SPRITE_TRACE_ENABLED
#include "cyrt/trace.hpp"
#endif
#ifdef SPRITE_SCHEDULER_COUNTERS
#include "cyrt/state/counters.hpp"
#endif

namespace cyrt
{
  // The free-variable table: the node of a free variable by its id.  The
  // runtime looks a variable up by id when it has no node at hand: the
  // group of a variable (strict_constraints), a binding, a residual, and
  // the choice of a generator at the root of a configuration (fork) name a
  // variable by its id.  The table is weak: it is not a root of the
  // collector, which drops an entry whose node is unreachable, unless a
  // live configuration still names the id.  See gc/wdgc.cpp.
  using vtable_type  = std::unordered_map<xid_type, Node*>;

  // The state shared by the evaluations of one interpreter: the ids of the
  // choices and the free variables, and the free-variable table.  The ids
  // are unique per interpreter, so the table lives here and not in the
  // runtime state of one evaluation: a nested evaluation (a Python
  // callback) and a later evaluation of a value that holds a free variable
  // find the variables of an earlier one.  The collector sweeps the tables
  // of the registered states.
  struct InterpreterState
  {
    InterpreterState() { gc_register_istate(this); }
    ~InterpreterState() { gc_unregister_istate(this); }
    InterpreterState(InterpreterState const &) = delete;
    InterpreterState & operator=(InterpreterState const &) = delete;
    xid_type    xidfactory = 0;
    vtable_type vtable;
    // The free variables made outside an evaluation of this interpreter:
    // the markers of curry.free and the raw Free nodes of curry.raw_expr,
    // counted by the expression builder; the variables of a single rewrite
    // step (RuntimeState_single_step in the bindings); and the variables
    // copied into a value (make_value).  While it is zero, set_goal skips
    // the walk that registers the free variables a goal already holds, and
    // the generator step skips the walk of its item.  The Python backend
    // keeps the same counter.
    size_t      external_freevars = 0;
  };

  // The set of a set function: the choices that escape it.  The guards of
  // the arguments, the SetEval nodes, and the queues of the set function
  // point to it.  The collector frees it when none of them reaches it any
  // more; see gc/wdgc.cpp.
  struct Set
  {
    Set() { gc_register_set(this); }
    ~Set() { gc_unregister_set(this); }
    Set(Set const &) = delete;
    Set & operator=(Set const &) = delete;
    std::unordered_set<xid_type> escape_set;
    // The mark of the current collection.
    bool marked = false;
  };

  // Default number of bytes of C stack one evaluation may use.  Measured with
  // the -O2 build: one level of hnf -> procS -> step nesting costs 260-520
  // bytes for the Prelude's (+) and 520-1050 bytes for a user function with
  // two nested cases.  4 MiB therefore admits roughly 4000-16000 nested
  // evaluations and leaves half of the 8 MiB main-thread stack for Python,
  // pybind11, and the frames above the last check.
  static constexpr size_t DEFAULT_STACK_LIMIT = size_t(4) << 20;

  // The number of bytes of the thread's stack kept free of Curry evaluation.
  // It covers the frames above the last stack check, the value copy, and the
  // error path.  See RuntimeState::set_stack_base.
  static constexpr size_t STACK_MARGIN = size_t(1) << 20;

  // The rotation cadence (see check_interrupts and cyrt/ticker.hpp).  Zero
  // steps select time mode, whose quantum is in nanoseconds.  The defaults
  // are those of the interpreter flag ``rotation``: time:10ms, and
  // steps:65536 for its step mode.
  static constexpr size_t   TIME_MODE = 0;
  static constexpr size_t   DEFAULT_ROTATION_STEPS = 65536;
  static constexpr uint64_t DEFAULT_QUANTUM_NS = 10000000;

  using qstack_type  = std::vector<Queue*>;

  struct RuntimeState
  {
    RuntimeState(
        InterpreterState & istate, Node * goal, bool trace=false
      , SetFStrategy setfunction_strategy = SETF_LAZY
      , SetFFailures setfunction_failures = SETF_FAILURES_ENCAPSULATE
      , size_t stack_limit = DEFAULT_STACK_LIMIT
      , size_t rotation_steps = TIME_MODE
      , uint64_t rotation_quantum_ns = DEFAULT_QUANTUM_NS
      );
    ~RuntimeState();
    RuntimeState(RuntimeState const &) = delete;
    RuntimeState(RuntimeState &&) = delete;
    RuntimeState & operator=(RuntimeState const &) = delete;
    RuntimeState & operator=(RuntimeState &&) = delete;

    InterpreterState &     istate;
    // ``stepcount`` counts the completed rewrite steps of the scheduler
    // (procS); it paces the periodic rotation in step mode
    // (check_interrupts) and shows the progress of the concurrent
    // conjunction in both modes.  ``steps_total`` counts the rewrite steps
    // taken (count_step), the steps outside the scheduler included.
    // ``forks_total`` counts the forks of a choice-rooted configuration
    // (fork).  Python reads both totals for the statistics of a run
    // (Interpreter.stats).
    size_t                 stepcount = 0;
    size_t                 steps_total = 0;
    size_t                 forks_total = 0;
    // The step limit of this evaluation, for the stepper of the test library
    // (Evaluator.set_global_step_limit; the Python side sets it from the
    // count at a reset).  NOLIMIT by default.  procS returns E_TERMINATE
    // after the completed step that brings ``steps_total`` to the limit,
    // every enclosing step hands the status out as it hands E_UNWIND out,
    // and the outermost procD throws StepLimitReached.  So the graph holds
    // the result of exactly that many steps, and no redex is half rewritten.
    // The step is not a safepoint: ``stepcount`` and the rotation do not
    // see it, so a run without a limit keeps its counters.
    size_t                 step_limit = NOLIMIT;
    // The rotation cadence of this evaluation (see check_interrupts).  In
    // step mode ``rotation_steps`` is the number of completed steps between
    // two rotation checks and ``rotation_next`` the value of ``stepcount``
    // at the next check.  In time mode ``rotation_steps`` is TIME_MODE, and
    // the ticker sets g_tick every ``rotation_quantum_ns`` nanoseconds
    // while the outermost procD of the state runs (cyrt/ticker.hpp).
    size_t                 rotation_steps;
    size_t                 rotation_next;
    uint64_t               rotation_quantum_ns;
    // The error of an alternative dropped at the stack limit.  procD raises
    // it when the outermost queue is empty.  See unwind.
    std::string            deferred_error;
    // The outermost queue.  It goes with the state, and so do the
    // configurations in it.  The other queues of ``qstack`` belong to the
    // SetEval nodes of the set functions under evaluation.
    std::unique_ptr<Queue> root_queue;
    qstack_type            qstack;
    SetFStrategy           setfunction_strategy;
    SetFFailures           setfunction_failures;
    // C-stack guard.  An evaluation may use ``stack_room`` bytes of C stack
    // below ``stack_base``, the frame of the outermost procD.  ``stack_room``
    // is ``stack_limit`` (from the flag) clamped to the stack of the thread
    // less STACK_MARGIN; ``stack_floor`` is the lowest address of that stack,
    // probed once per state.  NOLIMIT disables the guard.
    size_t                 stack_limit;
    size_t                 stack_room = NOLIMIT;
    char const *           stack_base = nullptr;
    char const *           stack_floor = nullptr;
    bool                   stack_probed = false;
    // Control handed between nested schedulers.  A nested procD that must
    // yield to an enclosing queue stores E_UNWIND, E_ROTATE, or E_GC here
    // and returns no value; allValues_step returns the status to the
    // enclosing evaluation.  ``rotate_target`` is the queue E_ROTATE is
    // meant for.
    tag_type               pending_control = NOTAG;
    Queue *                rotate_target = nullptr;
    // The sets of the enclosing guards a boxed failure crossed, from
    // fail_capsule to allValues_step, which puts their guards on the
    // failure the set function becomes.  See failure_escapes.
    std::vector<Set *>     capsule_failure_guards;
    // The divergence a nested evaluation met, from diverge to
    // allValues_step: the queue to clone for the configuration that runs
    // it, and the binding the clone absorbs, under the id the
    // configurations of that queue use.  See diverge.
    Queue *                diverge_queue = nullptr;
    xid_type               diverge_vid = NOXID;
    Node *                 diverge_binding = nullptr;
		#ifdef SPRITE_TRACE_ENABLED
    std::unique_ptr<Trace> trace;
    #endif
    #ifdef SPRITE_SCHEDULER_COUNTERS
    // The scheduler counters of an instrumented build (make COUNTERS=1).
    // The field is last, so the layout generated code reads is that of a
    // plain build.  See state/counters.hpp and the hooks in fairscheme.cpp,
    // rts_control.cpp, and rts_fingerprint.cpp.
    SchedulerCounters      counters;
    void count_end(Configuration *, ConfigurationEnd);
    void count_shared(Node * redex, Configuration *);
    #endif

    Queue * Q() { return this->qstack.back(); }
    Configuration * C() { return this->Q()->front(); }
    Cursor & E() { return C()->root; }
    Set * S() { return Q()->set; }

    Expr procD();
    tag_type procN(Configuration *, Cursor root);
    tag_type procS(Configuration *);
    // Head-normalizes the expression at ``inductive``, a position below the
    // current redex.  A choice there is pull-tabbed to the redex, unless the
    // redex is a monadic step or ``monadic`` is set.  Then the step reports
    // the non-determinism error instead.  See nondet_monad_error.
    tag_type hnf(
        Configuration *, Variable * inductive, void const * guides=nullptr
      , bool monadic=false
      );
    tag_type hnf_or_free(
        Configuration *, Variable * inductive, void const * guides=nullptr
      );

    // rts_bindings:
    bool add_binding(Configuration *, xid_type, Node *);
    void apply_binding(Configuration *, xid_type);
    void update_binding(Configuration *, xid_type);
    Node * make_value_bindings(Node * freevar, ValueSet const *);

    // rts_constraints:
    bool constrain_equal(Configuration *, Cursor constraint);
    bool constrain_equal(Configuration *, Node * x, Node * y, ConstraintType);
    static Node * lift_constraint(Configuration *, Variable * inductive);
    static Node * lift_constraint(Configuration *, Node * source, Node * target);

    // rts_control:
    void append(std::unique_ptr<Configuration>);
    void prepend(std::unique_ptr<Configuration>);
    void drop(TraceOpt=TRACE);
    Expr make_value();
    bool ready();
    Expr release_value();
    void rotate(Queue *, bool forced=false);
    void set_goal(Node * goal);
    tag_type check_interrupts(tag_type);
    void count_step();
    tag_type nondet_monad_error(Configuration *);
    void set_stack_base(char const *);
    bool stack_exhausted() const;
    bool unwind(Queue *, Configuration *);
    Expr yield_control(tag_type);

    // rts_fingerprint:
    bool equate_fp(Configuration *, xid_type, xid_type);
    void fork(Queue *, Configuration *);
    static Node * pull_tab(Configuration *, Variable * inductive);
    static Node * pull_tab(Configuration *, Node * source, Node * target);
    ChoiceState read_fp(Configuration *, xid_type);
    bool update_fp(Configuration *, xid_type, ChoiceState);

    // rts_freevars:
    Node * freshvar();
    void register_freevars(Node * root);
    // The node of a free variable by its id, or nullptr: the table has no
    // entry for a variable the collector dropped, or for a node built
    // outside the runtime (Node.create from Python).  See InterpreterState.
    Node * get_freevar(xid_type vid);
    // The binding of a variable: the configuration's own, the one its queue
    // absorbed, or that of the nearest enclosing level, read through the
    // queue stack as read_fp reads the decisions; nullptr when none has
    // one.  ``level`` receives where it was found: 0 for the state of the
    // configuration and its queue, k for the k-th enclosing level.  A
    // binding found above is private state of the configuration there;
    // a reader that puts it into the evaluation returns diverge (see
    // rts_setfunctions.cpp).
    Node * get_binding(Configuration *, xid_type vid, size_t * level=nullptr);
    Node * get_binding(Configuration *, Node *);
    Node * get_generator(Configuration *, xid_type vid);
    Node * get_generator(Configuration *, Node *);
    bool is_narrowed(Configuration *, xid_type vid);
    bool is_narrowed(Configuration *, Node * vid);
    tag_type replace_freevar(Configuration *, Cursor root);
    tag_type replace_freevar(
        Configuration *, Variable * inductive, void const *
      );
    void clone_generator(Node * bound, Node * unbound);
    tag_type instantiate(
        Configuration *, Cursor redex, Variable * inductive
      , void const * guides
      );
    bool is_void(Configuration *, Node * freevar);

    // rts_setfunctions:
    void push_queue(Queue *, TraceOpt=TRACE);
    void pop_queue(TraceOpt=TRACE);
    bool choice_escapes(Configuration *, xid_type);
    bool owns_decision(Configuration *, xid_type);
    bool failure_escapes(Configuration *, Variable const * inductive);
    tag_type fail_capsule(Configuration *, Variable const * inductive);
    tag_type diverge(size_t level, xid_type vid, Node * binding);
    bool in_recursive_call() const;
  private:
    #ifdef SPRITE_TRACE_ENABLED
    void _fork(Queue *, Configuration *);
    #endif
  };

  Node * has_generator(Node * freevar);
}

// The hooks of the scheduler counters.  They vanish in a plain build.
#ifdef SPRITE_SCHEDULER_COUNTERS
  #define SCHEDULER_COUNT_END(C, end) this->count_end(C, end)
  #define SCHEDULER_COUNT_SHARED(redex, C) this->count_shared(redex, C)
#else
  #define SCHEDULER_COUNT_END(C, end)
  #define SCHEDULER_COUNT_SHARED(redex, C)
#endif

#include "cyrt/state/rts.hxx"

