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
    id_type idfactory = 0;
    sid_type setfactory = 0;
  };

  using sftable_type = std::unordered_map<sid_type, SetFunctionEval*>;
  using vtable_type = std::unordered_map<id_type, Node*>;
  using qstack_type = std::vector<Queue*>;
  using qtable_type = std::unordered_map<qid_type, Queue*>;

  struct RuntimeState : boost::noncopyable
  {
    RuntimeState(InterpreterState & istate, Cursor goal);

    id_type &   idfactory;
    sid_type &   setfactory;
    size_t       stepcount   = 0;
    qstack_type  qstack;
    qtable_type  qtable;
    vtable_type  vtable;
    sftable_type sftable;

    qid_type qid() { return 0; } // FIXME
    sid_type const * sid() { return nullptr; } // FIXME

    Queue * Q() { return this->qstack.back(); }
    Configuration * C() { return this->Q()->front(); }
    Cursor & E() { return C()->root; }

    StepStatus S(Configuration *, Redex const &);
    StepStatus hnf(
        Configuration *, Variable * inductive, void const * guides=nullptr
      );

    // rts_bindings:
    bool add_binding(Configuration *, id_type, Node *);
    void update_binding(Configuration *, id_type);
    Node * make_value_bindings(Node * freevar, ValueSet const *);

    // rts_constraints:
    bool constrain_equal(Configuration *, Node * x, Node * y, ConstraintType);

    // rts_control:
    void append(Configuration *);
    void drop(TraceOpt=TRACE);
    Expr make_value();
    bool ready();
    Expr release_value();
    void set_goal(Cursor goal);

    // rts_fingerprint:
    bool equate_fp(Configuration *, id_type, id_type);
    void fork(Queue *);
    Node * pull_tab(Configuration *, Node * root);
    ChoiceState read_fp(Configuration *, id_type);
    bool update_fp(Configuration *, id_type, ChoiceState);

    // rts_freevars:
    Node * freshvar();
    Node * get_freevar(id_type vid);
    Node * get_binding(Configuration *, id_type vid);
    Node * get_binding(Configuration *, Node *);
    Node * get_generator(Configuration *, id_type vid);
    Node * get_generator(Configuration *, Node *);
    bool is_narrowed(Configuration *, id_type vid);
    bool is_narrowed(Configuration *, Node * vid);
    bool replace_freevar(Configuration *);
    StepStatus replace_freevar(Configuration *, Variable * inductive, void const *);
    void clone_generator(Node * bound, Node * unbound);
    StepStatus instantiate(
        Configuration *, Node * redex, Variable * inductive, void const * guides
      );

    // rts_setfunctions:
    Queue * make_queue(sid_type=NOSID);
    void push_queue(Queue *, TraceOpt=TRACE);
  };

  Node * has_generator(Node * freevar);
}

#include "sprite/state/rts.hxx"

