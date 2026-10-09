#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/currylib/setfunctions.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/module.hpp"
#include "cyrt/state/rts.hpp"
#include <vector>

using namespace cyrt;

namespace cyrt { inline namespace
{
  // Puts the queue of a set function on the stack of queues for its nested
  // evaluation and takes it off on every exit, an exception included.  So an
  // error inside a set function leaves the stack as it was.
  struct QueueScope
  {
    QueueScope(RuntimeState * rts, Queue * queue) : rts(rts)
      { rts->push_queue(queue); }
    ~QueueScope() { this->rts->pop_queue(); }
    QueueScope(QueueScope const &) = delete;
    QueueScope & operator=(QueueScope const &) = delete;
    RuntimeState * rts;
  };

  tag_type allValues_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    ChoiceNode * choice = nullptr;
    SetEvalNode * seteval = NodeU{_1.target}.seteval;
    Expr value;
    {
      QueueScope scope(rts, seteval->queue);
      value = rts->procD();
    }
    if(rts->pending_control == E_SETFAIL)
    {
      // A boxed failure was demanded inside the capsule, under the flag
      // setfunction_failures (RuntimeState::fail_capsule): the set function
      // has no value.  The redex becomes a failure under the guards of the
      // enclosing sets the failure crossed, so an enclosing set function
      // whose argument it came from fails in turn when it demands it.
      rts->pending_control = NOTAG;
      Node * failure = Fail;
      for(Set * set: rts->capsule_failure_guards)
        failure = guard(set, failure);
      rts->capsule_failure_guards.clear();
      _0->forward_to(failure);
      return T_FWD;
    }
    if(rts->pending_control != NOTAG)
    {
      // The nested scheduler yields to an enclosing queue: the stack limit
      // was reached (E_UNWIND), an enclosing queue is due to rotate
      // (E_ROTATE), or a collection is due (E_GC).  The redex stays as it
      // is, and the set function resumes when this configuration runs
      // again.  See RuntimeState::yield_control.
      tag_type const status = rts->pending_control;
      rts->pending_control = NOTAG;
      return status;
    }
    if(!value)
    {
      _0->forward_to(nil());
      return T_FWD;
    }
    assert(value.kind == 'p');
    // A value of the set function: a constructor, a free variable, or a
    // term under the guard of an enclosing set function (the guards of this
    // set are dropped by make_value).  Only a choice escapes.
    if(value.arg.node->info->tag != T_CHOICE)
    {
      _0->forward_to(
          cons(
              value.arg.node
            , Node::create(&allValues_Info, _1.target)
            )
        );
      return T_FWD;
    }
    choice = NodeU{value.arg.node}.choice;
    assert(seteval->queue->front()->root == (Node *) choice);
    // The choice escapes the set function (rule SF.1), whatever this
    // configuration decided: nothing of the configuration that runs the
    // capsule goes into the capsule.  The queue splits on the choice: the
    // configurations that made it LEFT stay, those that made it RIGHT move
    // to a new queue, and one that has not made it is in both, which record
    // the choice (Queue::split).  The redex becomes the choice between the
    // two capsules, a node of the shared graph like any pull-tabbed choice:
    // a configuration that has not decided the choice forks on it, and one
    // that decided it prunes it.  So two configurations that share the
    // capsule, with different decisions, each get their side (issue #61).
    // The new queue belongs to its SetEval node; see queue.hpp.
    Queue * Qrhs = new Queue(seteval->set);
    seteval->queue->split(choice->cid, *Qrhs);
    Node * rhs_seteval = Node::create(seteval->info, seteval->set, Qrhs);
    gc_register_seteval(rhs_seteval);
    Node * lhs_view = Node::create(&allValues_Info, (Node *) seteval);
    Node * rhs_view = Node::create(&allValues_Info, rhs_seteval);
    Node * replacement = make_node<ChoiceNode>(
        choice->cid, lhs_view, rhs_view
      );
    _0->forward_to(replacement);
    // When this configuration owns the decision of the choice
    // (owns_decision: it made the choice, or its queue is bound to the
    // side), it takes its side at once, through a private copy of the
    // spine, as a binding goes into the expression (replace_freevar);
    // E_RESTART tells the enclosing steps that the root was replaced.  The
    // fork would prune the choice node to the same side, but it sends the
    // configuration to the back of its queue, and a search with many
    // alternatives then advances them in lockstep, with every capsule alive
    // at once.  When the choice is undecided here, or an enclosing
    // configuration alone decided it (read_fp walks the queue stack), the
    // choice node stays: in the second case this configuration may be in a
    // capsule that enclosing configurations with different decisions share,
    // so it takes no side; the node reaches its root and escapes in turn
    // (choice_escapes), up to the configuration that decided it.
    ChoiceState const lr = rts->read_fp(C, choice->cid);
    if(lr == UNDETERMINED || !rts->owns_decision(C, choice->cid))
      return T_FWD;
    *C->root = C->scan.copy_spine(
        C->root, lr == LEFT ? lhs_view : rhs_view
      );
    return E_RESTART;
  }

  tag_type _applyS(RuntimeState * rts, Configuration * C, bool capture)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    assert(partial->info->type == &PartialS_Type);
    assert(partial->missing >= 1);
    Node * arg = _0->successor(1);
    if(!capture)
      arg = Node::create(&SetGuard_Info, nullptr, arg);
    Node * extended = Node::extend_partial(partial, arg);
    // The arguments the partial application holds keep the guards crossed on
    // the way to it (see set_step and apply_step).
    guard_successors(extended, 2, 2 + partial->nargs(), _1.guards);
    _0->forward_to(extended);
    return T_FWD;
  }

  tag_type applyS_step(RuntimeState * rts, Configuration * C)
    { return _applyS(rts, C, false); }

  tag_type captureS_step(RuntimeState * rts, Configuration * C)
    { return _applyS(rts, C, true); }

  // ($##>) f a = (f $>) $## a
  tag_type eagerApplyS_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Node * partial = Node::create_partial(
        &eagerApplyS_Info, _0->successor(0)
      );
    Node * replacement = Node::create(
        &applygnf_Info, partial, _0->successor(1)
      );
    _0->forward_to(replacement);
    return T_FWD;
  }

  // The number of nodes holds_private_state visits before it gives up.  The
  // Python backend has the same bound (currylib/setfunctions.py).
  static constexpr size_t PRIVATE_WALK_BUDGET = 64;

  // Tells whether configuration C holds private state for the expression at
  // ``root``: for a free variable of it, a binding or a narrowing (both read
  // through the queue stack: get_binding and read_fp), or a group with
  // another variable; for a choice of it, a decision.  That is the state
  // replace_freevar puts into the expression through a private copy of the
  // spine (rts_freevars.cpp), and the state a fork of the nested evaluation
  // reads through the queue stack (rts_fingerprint.cpp).  The walk follows
  // forward nodes and every pointer successor, so it crosses set guards,
  // partial applications, data, and the alternatives of an undecided
  // choice.  It does not enter the generator of a free variable: the
  // variable itself is the test, and nothing below its generator is decided
  // while the variable is not.  It stops after PRIVATE_WALK_BUDGET nodes
  // with the conservative answer: a long argument counts as private.  So
  // does a cyclic one.
  //
  // When the outermost queue holds one configuration, no other configuration
  // reads the shared graph, and a later clone of this one starts with the
  // same state, so the answer is false without a walk: a deterministic
  // program never pays the walk and never loses the sharing of an
  // application to the bound.  Inside a set function the state read through
  // the queue stack depends on the enclosing configuration that runs the
  // nested queue, so the walk runs there.
  bool holds_private_state(
      RuntimeState * rts, Configuration * C, Node * root
    )
  {
    if(!rts->in_recursive_call() && rts->Q()->size() == 1)
      return false;
    std::vector<Node *> stack;
    stack.push_back(root);
    size_t budget = PRIVATE_WALK_BUDGET;
    while(!stack.empty())
    {
      Node * node = stack.back();
      stack.pop_back();
      // A null successor exists between the creation of a recursive let and
      // its patch (INodeAssign).
      if(!node)
        continue;
      if(budget == 0)
        return true;
      --budget;
      InfoTable const * info = node->info;
      if(info->tag == T_FREE)
      {
        xid_type const vid = NodeU{node}.free->vid;
        xid_type const gid = C->grp_id(vid);
        if(vid != gid || rts->get_binding(C, gid) || rts->is_narrowed(C, gid))
          return true;
        continue;
      }
      if(info->tag == T_CHOICE
          && rts->read_fp(C, NodeU{node}.choice->cid) != UNDETERMINED)
        return true;
      Arg const * args = node->successors();
      for(index_type i=0; i<info->arity; ++i)
        if(info->format[i] == 'p')
          stack.push_back(args[i].node);
    }
    return false;
  }

  tag_type evalS_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    // The set and the queue register themselves with the collector, which
    // frees them when no node reaches them; see gc/wdgc.cpp.
    Set * new_set = new Set();
    Node * goal = partial->materialize();
    auto const arity = goal->info->arity;
    for(index_type i=0; i<arity; ++i)
    {
      Cursor cur = goal->successor(i);
      if(inspect::info_of(cur) == &SetGuard_Info && !inspect::get_set(cur))
        *cur = Node::create(
            &SetGuard_Info, new_set, inspect::get_setguard_value(cur)
          );
    }
    Queue * new_queue = new Queue(new_set, goal);
    Node * seteval = Node::create(&SetEval_Info, new_set, new_queue);
    gc_register_seteval(seteval);
    Node * allvalues = Node::create(&allValues_Info, seteval);
    Node * replacement = Node::create(&Values_Info, allvalues);
    // The nested evaluation reads the state of this configuration for the
    // free variables and the choices of its goal (the fingerprint, through
    // the queue stack), so its values depend on that state when this
    // configuration bound, narrowed, or grouped such a variable, or decided
    // such a choice.  A result that depends on the private state of a
    // configuration never goes into the shared graph, where another
    // configuration, with another binding of the variable or another side
    // of the choice, would read it (issue #61).  It goes into a private copy
    // of the spine, as the binding itself does (replace_freevar), and the
    // shared node stays an application for the other configurations.
    // E_RESTART tells the enclosing steps that the root was replaced.
    //
    // The copy is taken for the state the goal captures outside its
    // guards: a decided choice or a narrowed variable in an argument
    // applied with captureS (set f $< x), or in an encapsulated expression
    // (set0).  The escape would handle such a choice too (choice_escapes:
    // a choice an enclosing configuration decided escapes), at the cost of
    // a split and a restart per choice; the private capsule forks on it in
    // place.  A choice or a variable under a guard, an argument applied
    // with applyS or held by the function value (set_step boxes those),
    // needs no copy: its choice escapes the capsule (rule SF.1,
    // allValues_step) and the choice node is pruned by each configuration,
    // and a variable the capsule returns is resolved by each configuration
    // that reads the value.  The walk takes the copy in both cases, which
    // only loses the sharing of the capsule.
    if(holds_private_state(rts, C, (Node *) partial))
    {
      *C->root = C->scan.copy_spine(C->root, replacement);
      return E_RESTART;
    }
    _0->forward_to(replacement);
    return T_FWD;
  }

  tag_type exprS_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    // An encapsulated expression: no head, the expression as the one
    // argument.
    Node * replacement = Node::create(
        partials_info(1)
      , Arg(ENCAPSULATED_EXPR)
      , Arg((InfoTable const *) nullptr)
      , _0->successor(0)
      );
    _0->forward_to(replacement);
    return T_FWD;
  }

  tag_type set_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    assert(_1.target->info->type == &PartApplic_Type);
    PartApplicNode * partapplic = NodeU{_1.target}.partapplic;
    // The same contents under the table of the set functions: the formats
    // of the two families agree for one number of arguments.
    index_type const nargs = partapplic->nargs();
    Node * replacement = Node::create(
        partials_info(nargs), _1.target->successors()
      );
    // The arguments the function value holds are boxed as applyS boxes the
    // arguments applied: a partial application holds the arguments given so
    // far, and a lambda that closes over a variable of the enclosing context
    // holds it as an argument after lambda lifting.  Each goes under a guard
    // without a set, which evalS_step gives the new set, so its
    // non-determinism and its failure escape the capsule as an argument's
    // do (the entry rule of the dissertation boxes every argument of the
    // set function; issue #117).  captureS stays the explicit capture of an
    // argument.  A guard crossed on the way to the function value stays on
    // each argument below the new guard (guard_successors).
    guard_successors(replacement, 2, 2 + nargs, _1.guards);
    for(index_type i=0; i<nargs; ++i)
    {
      Node * boxed = Node::create(
          &SetGuard_Info, nullptr, replacement->successors()[2 + i].node
        );
      replacement->successors()[2 + i] = Arg(boxed);
    }
    _0->forward_to(replacement);
    return T_FWD;
  }

  Node * curry(InfoTable const * fapply, Node * head, Arg * tail, Arg * end)
  {
    while(tail < end)
      head = Node::create(fapply, head, *tail++);
    return head;
  }

  tag_type setN_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    index_type const n = _0->info->arity - 1;
    Node * setf = Node::create(
        n==0 ? &exprS_Info : &set_Info
      , _0->successor(0)
      );
    InfoTable const * fapply = rts->setfunction_strategy == SETF_EAGER
        ? &eagerApplyS_Info : &applyS_Info;
    Node * subexpr = curry(
        fapply, setf, _0->begin() + 1, _0->end()
      );
    Node * replacement = Node::create(&evalS_Info, subexpr);
    _0->forward_to(replacement);
    return T_FWD;
  }
}}

extern "C"
{
  InfoTable const allValues_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "allValues"
    , /*format*/     "p"
    , /*step*/       allValues_step
    , /*type*/       nullptr
    };

  InfoTable const applyS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "applyS"
    , /*format*/     "pp"
    , /*step*/       applyS_step
    , /*type*/       nullptr
    };

  InfoTable const captureS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "captureS"
    , /*format*/     "pp"
    , /*step*/       captureS_step
    , /*type*/       nullptr
    };

  InfoTable const eagerApplyS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$##>"
    , /*format*/     "pp"
    , /*step*/       eagerApplyS_step
    , /*type*/       nullptr
    };

  InfoTable const evalS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "evalS"
    , /*format*/     "p"
    , /*step*/       evalS_step
    , /*type*/       nullptr
    };

  InfoTable const exprS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "exprS"
    , /*format*/     "p"
    , /*step*/       exprS_step
    , /*type*/       nullptr
    };

  // The set-function partial application without arguments.  The tables
  // for one or more arguments come from g_partials_infos.
  InfoTable const PartialS_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(PartApplicNode)
    , /*flags*/      F_PARTIAL_TYPE | F_STATIC_OBJECT
    , /*name*/       "PartialS"
    , /*format*/     "ix"
    , /*step*/       nullptr
    , /*type*/       &PartialS_Type
    };

  InfoTable const set0_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set0"
    , /*format*/     "p"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set1_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set1"
    , /*format*/     "pp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set2_Info {
      /*tag*/        T_FUNC
    , /*arity*/      3
    , /*alloc_size*/ sizeof(Node_<3>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set2"
    , /*format*/     "ppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set3_Info {
      /*tag*/        T_FUNC
    , /*arity*/      4
    , /*alloc_size*/ sizeof(Node_<4>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set3"
    , /*format*/     "pppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set4_Info {
      /*tag*/        T_FUNC
    , /*arity*/      5
    , /*alloc_size*/ sizeof(Node_<5>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set4"
    , /*format*/     "ppppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set5_Info {
      /*tag*/        T_FUNC
    , /*arity*/      6
    , /*alloc_size*/ sizeof(Node_<6>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set5"
    , /*format*/     "pppppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set6_Info {
      /*tag*/        T_FUNC
    , /*arity*/      7
    , /*alloc_size*/ sizeof(Node_<7>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set6"
    , /*format*/     "ppppppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const set7_Info {
      /*tag*/        T_FUNC
    , /*arity*/      8
    , /*alloc_size*/ sizeof(Node_<8>)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set7"
    , /*format*/     "pppppppp"
    , /*step*/       setN_step
    , /*type*/       nullptr
    };

  InfoTable const SetEval_Info{
      /*tag*/        T_CTOR
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "SetEval"
    , /*format*/     "xx"
    , /*step*/       nullptr
    , /*type*/       &SetEval_Type
    };

  InfoTable const set_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "set"
    , /*format*/     "p"
    , /*step*/       set_step
    , /*type*/       nullptr
    };

  InfoTable const Values_Info {
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "Values"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*type*/       &Values_Type
    };

  static InfoTable const * PartialS_Ctors[] = { &PartialS_Info };
  DataType const PartialS_Type { PartialS_Ctors, 1, 't', F_STATIC_OBJECT, "PartialS" };
}

namespace cyrt
{
  PartialInfoFamily g_partials_infos{{&PartialS_Info}, nullptr};
}

extern "C"
{

  static InfoTable const * SetEval_Ctors[] = { &SetEval_Info };
  DataType const SetEval_Type { SetEval_Ctors, 1, 't', F_STATIC_OBJECT, "SetEval" };

  static InfoTable const * Values_Ctors[] = { &Values_Info };
  DataType const Values_Type { Values_Ctors, 1, 't', F_STATIC_OBJECT, "Values" };
}

static int register_setfunction_builtins()
{
  TypeTable && builtin_setfunction_types{
      {"PartialS" , &PartialS_Type}
    , {"SetEval"  , &SetEval_Type}
    , {"_SetGuard", &SetGuard_Type}
    , {"Values"   , &Values_Type}
    };

  SymbolTable && builtin_setfunction_symbols{
      {"allValues"    , &allValues_Info}
    , {"applyS"       , &applyS_Info}
    , {"captureS"     , &captureS_Info}
    , {"eagerApplyS"  , &eagerApplyS_Info}
    , {"evalS"        , &evalS_Info}
    , {"exprS"        , &exprS_Info}
    , {"PartialS"     , &PartialS_Info}
    , {"set0"         , &set0_Info}
    , {"set1"         , &set1_Info}
    , {"set2"         , &set2_Info}
    , {"set3"         , &set3_Info}
    , {"set4"         , &set4_Info}
    , {"set5"         , &set5_Info}
    , {"set6"         , &set6_Info}
    , {"set7"         , &set7_Info}
    , {"SetEval"      , &SetEval_Info}
    , {"_SetGuardEval", &SetGuard_Info}
    , {"set"          , &set_Info}
    , {"Values"       , &Values_Info}
    };

  Module::register_builtin_module(
      "Control.SetFunctions"
    , std::move(builtin_setfunction_types)
    , std::move(builtin_setfunction_symbols)
    );
  return 0;
}

static int _ = register_setfunction_builtins();
