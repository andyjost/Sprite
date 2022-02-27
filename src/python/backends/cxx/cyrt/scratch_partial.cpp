#include "cyrt/builtins.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/graph/memory.hpp"
#include "cyrt/graph/node.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"
#include "cyrt/state/rts.hpp"

using namespace cyrt;

namespace cyrt { inline namespace
{
  tag_type main1_step(RuntimeState * rts, Configuration * C)
  {
    // (not) True
    Cursor _0 = C->cursor();
    Node * not_ = Node::create_partial(&not_Info);
    Node * goal = Node::create(&apply_Info, not_, True);
    _0->forward_to(goal);
    return T_FWD;
  }

  tag_type main2_step(RuntimeState * rts, Configuration * C)
  {
    // (True:) []
    Cursor _0 = C->cursor();
    Node * cons_ = Node::create_partial(&Cons_Info, True);
    Node * goal = Node::create(&apply_Info, cons_, nil());
    _0->forward_to(goal);
    return T_FWD;
  }

  tag_type main3_step(RuntimeState * rts, Configuration * C)
  {
    // not $! (not True)
    Cursor _0 = C->cursor();
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applyhnf_Info, not_, rhs);
    _0->forward_to(goal);
    return T_FWD;
  }

  tag_type main4_step(RuntimeState * rts, Configuration * C)
  {
    // not $!! (not True)
    Cursor _0 = C->cursor();
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applynf_Info, not_, rhs);
    _0->forward_to(goal);
    return T_FWD;
  }

  tag_type main5_step(RuntimeState * rts, Configuration * C)
  {
    // not $## (not True)
    Cursor _0 = C->cursor();
    Node * not_ = Node::create_partial(&not_Info);
    Node * rhs = Node::create(&not_Info, True);
    Node * goal = Node::create(&applygnf_Info, not_, rhs);
    _0->forward_to(goal);
    return T_FWD;
  }
}}

namespace cyrt
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

namespace cyrt { namespace python
{
  Node * make_partial_goal1() { return Node::create(&Main1_Info); }
  Node * make_partial_goal2() { return Node::create(&Main2_Info); }
  Node * make_partial_goal3() { return Node::create(&Main3_Info); }
  Node * make_partial_goal4() { return Node::create(&Main4_Info); }
  Node * make_partial_goal5() { return Node::create(&Main5_Info); }
}}
