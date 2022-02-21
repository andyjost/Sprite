#include "sprite/builtins.hpp"
#include "sprite/graph/memory.hpp"
#include "sprite/graph/node.hpp"
#include "sprite/graph/walk.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

using namespace sprite;

namespace sprite { namespace python
{
  tag_type zip_step(RuntimeState * rts, Configuration * C);
  tag_type zip_step_CASE0(RuntimeState * rts, Configuration * C);
  tag_type list01_step(RuntimeState * rts, Configuration * C);
  tag_type mainzip_step(RuntimeState * rts, Configuration * C);

  InfoTable const zip_Info{
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "zip"
    , /*format*/     "pp"
    , /*step*/       &zip_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };


  InfoTable const zip_Info_CASE0{
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "zip_CASE0"
    , /*format*/     "pp"
    , /*step*/       &zip_step_CASE0
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  struct ZipNode : Head
  {
    Node * lhs;
    Node * rhs;
    static constexpr InfoTable const * static_info = &zip_Info;
  };


  tag_type zip_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = variable(_0, 0);
    auto tag = rts->hnf(C, &_1);
    switch(tag)
    {
      case T_CONS: _0->node->info = &zip_Info_CASE0;
                   return T_FUNC;
      case T_NIL : _0->node->make_nil();
                   return T_NIL;
      default    : return tag;
    }
  }

  tag_type zip_step_CASE0(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _2 = variable(_0, 1);
    auto tag = rts->hnf(C, &_2);
    switch(tag)
    {
      case T_CONS:
      {
        Variable _1  = variable(_0, 0);
        Variable _10 = variable(_1.target, 0);
        Variable _11 = variable(_1.target, 1);
        Variable _20 = variable(_2.target, 0);
        Variable _21 = variable(_2.target, 1);
        Node * repl = cons(
            pair(rvalue(_10), rvalue(_20))
          , Node::create(&zip_Info, rvalue(_11), rvalue(_21))
          );
        _0->node->forward_to(repl);
        return T_CONS;
      }
      case T_NIL: _0->node->make_nil();
                  return T_NIL;
      default   : return tag;
    }
  }

  InfoTable const list01_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "list01"
    , /*format*/     ""
    , /*step*/       &list01_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  tag_type list01_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto i0 = int_(0);
    auto i1 = int_(1);
    Node * goal = cons(i0, cons(i1, nil()));
    _0->node->forward_to(goal);
    return T_FWD;
  }

  tag_type mainzip_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto i2 = int_(2);
    auto i3 = int_(3);
    Node * lhs = Node::create(&list01_Info);
    Node * rhs = cons(i2, cons(i3, nil()));
    Node * goal = Node::create(&zip_Info, lhs, rhs);
    _0->node->forward_to(goal);
    return T_FWD;
  }

  InfoTable const MainZip_Info{
      /*tag*/        T_FUNC
    , /*arity*/      0
    , /*alloc_size*/ sizeof(Node1)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "main"
    , /*format*/     ""
    , /*step*/       &mainzip_step
    , /*typecheck*/  nullptr
    , /*typedef*/    nullptr
    };

  struct MainZipNode : Node1
  {
    static constexpr InfoTable const * static_info = &MainZip_Info;
  };

  Node * make_zip_goal()
  {
    return make_node<MainZipNode>();
  }
}}
