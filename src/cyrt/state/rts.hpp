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

  using qstack_type  = std::vector<Queue*>;
  using vtable_type  = std::unordered_map<xid_type, Node*>;

  struct RuntimeState : boost::noncopyable
  {
    RuntimeState(
        InterpreterState & istate, Node * goal, bool trace=false
      , SetFStrategy setfunction_strategy = SETF_LAZY
      );
    ~RuntimeState();
    RuntimeState(RuntimeState const &) = delete;
    RuntimeState(RuntimeState &&) = delete;
    RuntimeState & operator=(RuntimeState const &) = delete;
    RuntimeState & operator=(RuntimeState &&) = delete;

    InterpreterState &     istate;
    size_t                 stepcount = 0;
    qstack_type            qstack;
    vtable_type            vtable;
    SetFStrategy           setfunction_strategy;
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
    tag_type hnf(
        Configuration *, Variable * inductive, void const * guides=nullptr
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

