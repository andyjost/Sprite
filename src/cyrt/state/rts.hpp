#pragma once
#include "boost/utility.hpp"
#include "cyrt/fwd.hpp"
#include "cyrt/state/configuration.hpp"
#include "cyrt/state/queue.hpp"
#include <initializer_list>
#include <memory>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#ifdef SPRITE_TRACE_ENABLED
#include "cyrt/trace.hpp"
#endif

namespace cyrt
{
  struct InterpreterState : boost::noncopyable
  {
    xid_type xidfactory = 0;
  };

  struct Set
  {
    std::unordered_set<xid_type> escape_set;
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

  using qstack_type  = std::vector<Queue*>;
  using vtable_type  = std::unordered_map<xid_type, Node*>;

  struct RuntimeState : boost::noncopyable
  {
    RuntimeState(
        InterpreterState & istate, Node * goal, bool trace=false
      , SetFStrategy setfunction_strategy = SETF_LAZY
      , size_t stack_limit = DEFAULT_STACK_LIMIT
      );
    ~RuntimeState();
    RuntimeState(RuntimeState const &) = delete;
    RuntimeState(RuntimeState &&) = delete;
    RuntimeState & operator=(RuntimeState const &) = delete;
    RuntimeState & operator=(RuntimeState &&) = delete;

    InterpreterState &     istate;
    // ``stepcount`` counts the forward nodes compressed (about one per
    // rewrite step) and paces the periodic rotation (check_interrupts) and
    // the concurrent conjunction.  ``steps_total`` counts the rewrite steps
    // taken (count_step).
    size_t                 stepcount = 0;
    size_t                 steps_total = 0;
    // The error of an alternative dropped at the stack limit.  procD raises
    // it when the outermost queue is empty.  See unwind.
    std::string            deferred_error;
    qstack_type            qstack;
    vtable_type            vtable;
    SetFStrategy           setfunction_strategy;
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
    // yield to an enclosing queue stores E_UNWIND or E_ROTATE here and returns
    // no value; allValues_step returns the status to the enclosing
    // evaluation.  ``rotate_target`` is the queue E_ROTATE is meant for.
    tag_type               pending_control = NOTAG;
    Queue *                rotate_target = nullptr;
		#ifdef SPRITE_TRACE_ENABLED
    std::unique_ptr<Trace> trace;
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
    void append(Configuration *);
    void prepend(Configuration *);
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
    Node * get_freevar(xid_type vid);
    Node * get_binding(Configuration *, xid_type vid);
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
    void filter_queue(Queue *, xid_type, ChoiceState);
    bool in_recursive_call() const;
  private:
    #ifdef SPRITE_TRACE_ENABLED
    void _fork(Queue *, Configuration *);
    #endif
  };

  Node * has_generator(Node * freevar);
}

#include "cyrt/state/rts.hxx"

