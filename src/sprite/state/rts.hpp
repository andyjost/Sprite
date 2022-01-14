#pragma once
#include "sprite/fwd.hpp"
#include "sprite/state/configuration.hpp"
#include "sprite/state/queue.hpp"
#include <unordered_map>
#include <vector>
#include "boost/utility.hpp"

namespace sprite
{
  enum TraceOpt : bool { TRACE = true, NOTRACE = false };

  struct InterpreterState : boost::noncopyable
  {
    cid_type idfactory = 0;
    sid_type setfactory = 0;
  };

  using sftable_type = std::unordered_map<sid_type, SetFunctionEval*>;
  using vtable_type = std::unordered_map<vid_type, Node*>;
  using qstack_type = std::vector<Queue*>;
  using qtable_type = std::unordered_map<qid_type, Queue*>;

  struct RuntimeState : boost::noncopyable
  {
    RuntimeState(InterpreterState & istate, Cursor goal);

    cid_type &   idfactory;
    sid_type &   setfactory;
    size_t       stepcount   = 0;
    qstack_type  qstack;
    qtable_type  qtable;
    vtable_type  vtable;
    sftable_type sftable;

    qid_type qid() { return 0; } // FIXME
    sid_type const * sid() { return nullptr; } // FIXME

    Queue & Q() { return *this->qtable[this->qid()]; }
    Configuration * C() { return this->Q().front(); }
    Cursor & E() { return C()->root; }

    bool ready();
    Expr make_value();
    Expr release_value();
    void append(Configuration *);
    void drop(TraceOpt=TRACE);
    void push_queue(Queue *, TraceOpt=TRACE);
    Queue * make_queue(sid_type=NOSID);
    void set_goal(Cursor goal);
    // void pull_tab(Configuration *);
    void forkD(Queue *);
    void forkN(Queue *);
    bool update_fp(Configuration *, cid_type, ChoiceState);
    ChoiceState read_fp(cid_type, Configuration *);
  };
}

