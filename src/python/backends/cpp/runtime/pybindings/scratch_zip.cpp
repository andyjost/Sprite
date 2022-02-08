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
  step_status zip_step(RuntimeState * rts, Configuration * C, Redex const * _0);
  step_status zip_step_CASE0(RuntimeState * rts, Configuration * C, Redex const * _0);
  step_status list01_step(RuntimeState * rts, Configuration * C, Redex const * _0);
  step_status mainzip_step(RuntimeState * rts, Configuration * C, Redex const * _0);

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


  step_status zip_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _1(*_0, 0);
    auto tag = rts->hnf(C, &_1);
    switch(tag)
    {
      case T_CONS: _0->root()->info = &zip_Info_CASE0;
                   return T_FUNC;
      case T_NIL : _0->root()->make_nil();
                   return T_NIL;
      default    : return tag;
    }
  }

  step_status zip_step_CASE0(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _2(*_0, 1);
    auto tag = rts->hnf(C, &_2);
    switch(tag)
    {
      case T_CONS:
      {
        Variable _1 (*_0, 0);
        Variable _10(_1, 0);
        Variable _11(_1, 1);
        Variable _20(_2, 0);
        Variable _21(_2, 1);
        Node * repl = cons(
            pair(_10.rvalue(), _20.rvalue())
          , Node::create(&zip_Info, {_11.rvalue(), _21.rvalue()})
          );
        _0->root()->forward_to(repl);
        return T_CONS;
      }
      case T_NIL: _0->root()->make_nil();
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

  step_status list01_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    auto i0 = int_(0);
    auto i1 = int_(1);
    Node * goal = cons(i0, cons(i1, nil()));
    _0->root()->forward_to(goal);
    return T_FWD;
  }

  step_status mainzip_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    auto i2 = int_(2);
    auto i3 = int_(3);
    Node * lhs = Node::create(&list01_Info);
    Node * rhs = cons(i2, cons(i3, nil()));
    Node * goal = Node::create(&zip_Info, {lhs, rhs});
    _0->root()->forward_to(goal);
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
