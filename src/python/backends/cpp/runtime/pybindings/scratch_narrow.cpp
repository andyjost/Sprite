#include "sprite/builtins.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

using namespace sprite;

namespace sprite { namespace python
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

  Node * make_narrow_goal1()
  {
    return Node::create(&Main1_Info);
  }

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

  Node * make_narrow_goal2()
  {
    return Node::create(&Main2_Info);
  }
}}
