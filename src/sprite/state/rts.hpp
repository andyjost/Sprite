#pragma once
#include "boost/utility.hpp"
#include <initializer_list>
#include "sprite/fwd.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/state/configuration.hpp"
#include "sprite/state/queue.hpp"
#include <unordered_map>
#include <vector>

namespace sprite
{
  enum TraceOpt : bool { TRACE = true, NOTRACE = false };

  struct InterpreterState : boost::noncopyable
  {
    xid_type xidfactory = 0;
    sid_type sidfactory = 0;
    qid_type qidfactory = 0;
  };

  using sftable_type = std::unordered_map<sid_type, SetFunctionEval*>;
  using vtable_type = std::unordered_map<xid_type, Node*>;
  using qstack_type = std::vector<Queue*>;
  using qtable_type = std::unordered_map<qid_type, Queue*>;

  struct RuntimeState : boost::noncopyable
  {
    RuntimeState(InterpreterState & istate, Cursor goal);

    InterpreterState & istate;
    size_t             stepcount   = 0;
    qstack_type        qstack;
    qtable_type        qtable;
    vtable_type        vtable;
    sftable_type       sftable;

    qid_type qid() { return this->qstack.back()->qid; }
    sid_type const * sid() { return nullptr; } // FIXME

    Queue * Q() { return this->qstack.back(); }
    Configuration * C() { return this->Q()->front(); }
    Cursor & E() { return C()->root; }

    step_status S(Configuration *, Redex const &);
    step_status hnf(
        Configuration *, Variable * inductive, void const * guides=nullptr
      );
    step_status hnf_or_free(
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
    void drop(TraceOpt=TRACE);
    Expr make_value();
    bool ready();
    Expr release_value();
    void set_goal(Cursor goal);

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
    Node * replace_freevar(Configuration *);
    step_status replace_freevar(Configuration *, Variable * inductive, void const *);
    void clone_generator(Node * bound, Node * unbound);
    step_status instantiate(
        Configuration *, Node * redex, Variable * inductive, void const * guides
      );

    // rts_setfunctions:
    Queue * make_queue(sid_type=NOSID);
    void push_queue(Queue *, TraceOpt=TRACE);
  };

  Node * has_generator(Node * freevar);
}

#include "sprite/state/rts.hxx"

