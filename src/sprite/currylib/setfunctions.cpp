#include "sprite/builtins.hpp"
#include "sprite/currylib/prelude.hpp"
#include "sprite/currylib/setfunctions.hpp"
#include "sprite/fairscheme.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/inspect.hpp"

namespace sprite { inline namespace
{
  tag_type allValues_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    ChoiceNode * choice = nullptr;
    SetEvalNode * seteval = NodeU{_1.target}.seteval;
    rts->push_queue(seteval->queue);
    auto value = eval_next(rts);
    assert(value.kind == 'p');
    rts->pop_queue();
    if(value.arg.node->info->tag >= T_CTOR)
    {
      _0->node->forward_to(
          cons(
              value.arg.node
            , Node::create(&allValues_Info, _1.target->node)
            )
        );
      return T_FWD;
    }
    assert(value.arg.node->info->tag == T_CHOICE);
    choice = NodeU{value.arg.node}.choice;
    Configuration * subC = seteval->queue->front();
    assert(subC->root->node == (Node *) choice);
    Queue * Qlhs = seteval->queue;
    Queue * Qrhs = new Queue(seteval->set);
    Node * rhs_seteval = Node::create(seteval->info, seteval->set, Qrhs);
    auto out = Qlhs->begin();
    for(auto p=Qlhs->begin(), e=Qlhs->end(); p!=e; ++p)
    {
      switch((*p)->fingerprint.test(choice->cid))
      {
        case LEFT:         *out++ = *p;
                           break;
        case RIGHT:        Qrhs->push_back(*p);
                           break;
        case UNDETERMINED: *out++ = *p;
                           Qrhs->push_back(*p);
                           break;
      }
    }
    Qlhs->resize(out - Qlhs->begin());
    Node * replacement = make_node<ChoiceNode>(
        choice->cid
      , Node::create(&allValues_Info, (Node *) seteval)
      , Node::create(&allValues_Info, rhs_seteval)
      );
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  tag_type _applyS(RuntimeState * rts, Configuration * C, bool capture)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    assert(partial->missing >= 1);
    Node * arg = _0->node->successor(1);
    if(!capture)
      arg = Node::create(&SetGuard_Info, nullptr, arg);
    Node * replacement = Node::create(
        &PartialS_Info
      , partial->missing - 1
      , partial->head_info
      , cons(partial->terms, arg)
      );
    _0->node->forward_to(replacement);
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
    Node * partial = Node::create(
        &PartApplic_Info
      , 1
      , &eagerApplyS_Info
      , cons(_0->node->successor(0), Nil)
      );
    Node * replacement = Node::create(
        &applygnf_Info, partial, _0->node->successor(1)
      );
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  tag_type evalS_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
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
    Node * allvalues = Node::create(&allValues_Info, seteval);
    Node * replacement = Node::create(&Values_Info, allvalues);
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  tag_type exprS_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Node * replacement = Node::create(
        &PartialS_Info
      , Arg(ENCAPSULATED_EXPR)
      , _0->node->successor(0)
      );
    _0->node->forward_to(replacement);
    return T_FWD;
  }

  tag_type set_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto status = rts->hnf(C, &_1);
    if(status != T_CTOR)
      return status;
    assert(_1.target.info() == &PartApplic_Info);
    _0->node->forward_to(_1.target);
    return T_FWD;
  }

  Node * curry(InfoTable const * fapply, Node * head, Arg * tail, Arg * end)
  {
    while(tail != end)
      head = Node::create(fapply, head, *tail++);
    return head;
  }

  tag_type setN_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    index_type const n = _0->node->info->arity - 1;
    Node * setf = Node::create(
        n==0 ? &exprS_Info : &set_Info
      , _0->node->successor(0)
      );
    InfoTable const * fapply = rts->setfunction_strategy == SETF_EAGER
        ? &eagerApplyS_Info : &applyS_Info;
    Node * subexpr = curry(
        fapply, setf, _0->node->begin(), _0->node->end()
      );
    Node * replacement = Node::create(&evalS_Info, subexpr);
    _0->node->forward_to(replacement);
    return T_FWD;
  }
}}

namespace sprite
{
  static InfoTable const * Values_Ctors[] = { &Values_Info };
  Type const Values_Type { Values_Ctors, 1 };

  InfoTable const Values_Info {
      /*tag*/        T_CTOR
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "Values"
    , /*format*/     "p"
    , /*step*/       nullptr
    , /*typecheck*/  nullptr
    , /*type*/       &Values_Type
    };

  InfoTable const allValues_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "allValues"
    , /*format*/     "p"
    , /*step*/       allValues_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applyS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "applyS"
    , /*format*/     "pp"
    , /*step*/       applyS_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const eagerApplyS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "$##>"
    , /*format*/     "pp"
    , /*step*/       eagerApplyS_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const captureS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "captureS"
    , /*format*/     "pp"
    , /*step*/       captureS_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const evalS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "evalS"
    , /*format*/     "p"
    , /*step*/       evalS_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const exprS_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "exprS"
    , /*format*/     "p"
    , /*step*/       exprS_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set"
    , /*format*/     "p"
    , /*step*/       set_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set0_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set0"
    , /*format*/     "p"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set1_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set1"
    , /*format*/     "pp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set2_Info {
      /*tag*/        T_FUNC
    , /*arity*/      3
    , /*alloc_size*/ sizeof(Node_<3>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set2"
    , /*format*/     "ppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set3_Info {
      /*tag*/        T_FUNC
    , /*arity*/      4
    , /*alloc_size*/ sizeof(Node_<4>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set3"
    , /*format*/     "pppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set4_Info {
      /*tag*/        T_FUNC
    , /*arity*/      5
    , /*alloc_size*/ sizeof(Node_<5>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set4"
    , /*format*/     "ppppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set5_Info {
      /*tag*/        T_FUNC
    , /*arity*/      6
    , /*alloc_size*/ sizeof(Node_<6>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set5"
    , /*format*/     "pppppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set6_Info {
      /*tag*/        T_FUNC
    , /*arity*/      7
    , /*alloc_size*/ sizeof(Node_<7>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set6"
    , /*format*/     "ppppppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const set7_Info {
      /*tag*/        T_FUNC
    , /*arity*/      8
    , /*alloc_size*/ sizeof(Node_<8>)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "set7"
    , /*format*/     "pppppppp"
    , /*step*/       setN_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };
}
