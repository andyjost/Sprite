#include "sprite/builtins.hpp"
#include "sprite/currylib/prelude.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

using namespace sprite;

namespace sprite { inline namespace
{
  SStatus main1_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // (not) True
    Node * not_ = Node::create_partial(&not_Info);
    Node * goal = Node::create(&apply_Info, not_, True);
    _0->root()->forward_to(goal);
    return T_FWD;
  }

  SStatus main2_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // (True:) []
    Node * cons_ = Node::create_partial(&Cons_Info, True);
    Node * goal = Node::create(&apply_Info, cons_, nil());
    _0->root()->forward_to(goal);
    return T_FWD;
  }

  SStatus main3_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // not $! (not True)
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applyhnf_Info, not_, rhs);
    _0->root()->forward_to(goal);
    return T_FWD;
  }

  SStatus main4_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // not $!! (not True)
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applynf_Info, not_, rhs);
    _0->root()->forward_to(goal);
    return T_FWD;
  }

  SStatus main5_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    // not $## (not True)
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applygnf_Info, not_, rhs);
    _0->root()->forward_to(goal);
    return T_FWD;
  }
}}

namespace sprite
{
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
}

namespace sprite { namespace python
{
  Node * make_partial_goal1() { return Node::create(&Main1_Info); }
  Node * make_partial_goal2() { return Node::create(&Main2_Info); }
  Node * make_partial_goal3() { return Node::create(&Main3_Info); }
  Node * make_partial_goal4() { return Node::create(&Main4_Info); }
  Node * make_partial_goal5() { return Node::create(&Main5_Info); }
}}
