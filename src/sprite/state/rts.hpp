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

    StepStatus S(Configuration *, Variable *);
    StepStatus hnf(
        Configuration *, Variable * inductive
      // , Node * root
      // , std::initializer_list<index_type> path
      // , Typedef const * = nullptr, void const * values = nullptr
      );

    // rts_control:
    void append(Configuration *);
    void drop(TraceOpt=TRACE);
    Expr make_value();
    bool ready();
    Expr release_value();
    void set_goal(Cursor goal);

    // rts_fingerprint:
    bool equate_fp(Configuration *, id_type, id_type);
    void forkD(Queue *);
    Node * pull_tab(Configuration *, Node * root);
    ChoiceState read_fp(Configuration *, id_type);
    bool update_fp(Configuration *, id_type, ChoiceState);

    // rts_setfunctions:
    Queue * make_queue(sid_type=NOSID);
    void push_queue(Queue *, TraceOpt=TRACE);
  };
}

