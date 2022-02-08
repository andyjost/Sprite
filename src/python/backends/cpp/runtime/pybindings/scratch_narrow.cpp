#include "sprite/builtins.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

using namespace sprite;

namespace sprite { inline namespace
{
  StepStatus not_step(RuntimeState * rts, Configuration * C, Redex const * _0);

  InfoTable const not_Info{
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "not"
    , /*format*/     "p"
    , /*step*/       &not_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus not_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _1(*_0, 0);
    StepStatus status = rts->hnf(C, &_1, &Bool_Type);
    switch(status)
    {
      case E_OK      : break;
      case E_RESIDUAL: assert(0); return status;
      case E_UNWIND  : return E_OK;
      case E_RESTART : assert(0); return status;
    }
    auto tag = inspect::tag_of(_1.target());
    switch(tag)
    {
      case T_FALSE: _0->root()->forward_to(true_());
                    return E_OK;
      case T_TRUE:  _0->root()->forward_to(false_());
                    return E_OK;
      default: __builtin_unreachable();
    }
  }

  StepStatus main1_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Node * goal = Node::create(&not_Info, {false_()});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main1_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main1"
    , /*format*/     ""
    , /*step*/       &main1_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus main2_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Node * goal = Node::create(&not_Info, {free(0)});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main2_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main2"
    , /*format*/     ""
    , /*step*/       &main2_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus main3_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // _B((not x, y), (x, y))
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, {x, y});
    Node * notx = Node::create(&not_Info, {x});
    Node * value = Node::create(&Pair_Info, {notx, y});
    Node * goal = Node::create(&StrictConstraint_Info, {value, pair});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main3_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main3"
    , /*format*/     ""
    , /*step*/       &main3_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus main4_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // (_B(not x, (x, y)), y)
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, {x, y});
    Node * notx = Node::create(&not_Info, {x});
    Node * binding = Node::create(&StrictConstraint_Info, {notx, pair});
    Node * goal = Node::create(&Pair_Info, {binding, y});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main4_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main4"
    , /*format*/     ""
    , /*step*/       &main4_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus main5_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // (not x, y)
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * notx = Node::create(&not_Info, {x});
    Node * goal = Node::create(&Pair_Info, {notx, y});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main5_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main5"
    , /*format*/     ""
    , /*step*/       &main5_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  StepStatus main6_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // (not _B(x, (x, y)), y)
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, {x, y});
    Node * binding = Node::create(&StrictConstraint_Info, {x, pair});
    Node * notb = Node::create(&not_Info, {binding});
    Node * goal = Node::create(&Pair_Info, {notb, y});
    _0->root()->forward_to(goal);
    return E_OK;
  }

  InfoTable const Main6_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main6"
    , /*format*/     ""
    , /*step*/       &main6_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };
}}

namespace sprite { namespace python
{
  Node * make_narrow_goal1() { return Node::create(&Main1_Info); }
  Node * make_narrow_goal2() { return Node::create(&Main2_Info); }
  Node * make_narrow_goal3() { return Node::create(&Main3_Info); }
  Node * make_narrow_goal4() { return Node::create(&Main4_Info); }
  Node * make_narrow_goal5() { return Node::create(&Main5_Info); }
  Node * make_narrow_goal6() { return Node::create(&Main6_Info); }
}}
