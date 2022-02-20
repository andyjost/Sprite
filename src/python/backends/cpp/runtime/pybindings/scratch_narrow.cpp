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
  SStatus main1_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Node * goal = Node::create(&not_Info, false_());
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main2_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Node * goal = Node::create(&not_Info, free(0));
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main3_step(RuntimeState * rts, Configuration * C)
  {
    // _B((not x, y), (x, y))
    Cursor _0 = C->cursor();
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, x, y);
    Node * notx = Node::create(&not_Info, x);
    Node * value = Node::create(&Pair_Info, notx, y);
    Node * goal = Node::create(&StrictConstraint_Info, value, pair);
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main4_step(RuntimeState * rts, Configuration * C)
  {
    // (_B(not x, (x, y)), y)
    Cursor _0 = C->cursor();
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, x, y);
    Node * notx = Node::create(&not_Info, x);
    Node * binding = Node::create(&StrictConstraint_Info, notx, pair);
    Node * goal = Node::create(&Pair_Info, binding, y);
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main5_step(RuntimeState * rts, Configuration * C)
  {
    // (not x, y)
    Cursor _0 = C->cursor();
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * notx = Node::create(&not_Info, x);
    Node * goal = Node::create(&Pair_Info, notx, y);
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main6_step(RuntimeState * rts, Configuration * C)
  {
    // (not _B(x, (x, y)), y)
    Cursor _0 = C->cursor();
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * pair = Node::create(&Pair_Info, x, y);
    Node * binding = Node::create(&StrictConstraint_Info, x, pair);
    Node * notb = Node::create(&not_Info, binding);
    Node * goal = Node::create(&Pair_Info, notb, y);
    _0->node->forward_to(goal);
    return T_FWD;
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

  SStatus main7_step(RuntimeState * rts, Configuration * C)
  {
    // x=:=y &> (x, not y)
    Cursor _0 = C->cursor();
    Node * x = rts->freshvar();
    Node * y = rts->freshvar();
    Node * eq = Node::create(&constrEq_Info, x, y);
    Node * noty = Node::create(&not_Info, y);
    Node * pair = Node::create(&Pair_Info, x, noty);
    Node * goal = Node::create(&seq_Info, eq, pair);
    _0->node->forward_to(goal);
    return T_FWD;
  }

  InfoTable const Main7_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main7"
    , /*format*/     ""
    , /*step*/       &main7_step
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
  Node * make_narrow_goal7() { return Node::create(&Main7_Info); }
}}
