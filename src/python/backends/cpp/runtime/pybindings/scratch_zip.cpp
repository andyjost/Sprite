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
  StepStatus zip_step(RuntimeState * rts, Configuration * C, Redex * _0);
  StepStatus zip_step_CASE0(RuntimeState * rts, Configuration * C, Redex * _0);
  StepStatus list01_step(RuntimeState * rts, Configuration * C, Redex * _0);
  StepStatus mainzip_step(RuntimeState * rts, Configuration * C, Redex * _0);

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


  StepStatus zip_step(RuntimeState * rts, Configuration * C, Redex * _0)
  {
    // ZipNode * zip = (ZipNode *) _0->root();
    // StepStatus status = rts->hnf(C, root, {0});
    Variable _1(*_0, 0);
    StepStatus status = rts->hnf(C, &_1);
    switch(status)
    {
      case E_OK      : break;
      case E_RESIDUAL: assert(0); return status;
      case E_UNWIND  : assert(0); return status;
      case E_RESTART : assert(0); return status;
    }
    // auto tag = inspect::tag_of(zip->lhs);
    auto tag = inspect::tag_of(_1.target());
    switch(tag)
    {
      case T_CONS: _0->root()->info = &zip_Info_CASE0;
                   return E_OK;
      case T_NIL:  _0->root()->make_nil();
                   return E_OK;
      default: __builtin_unreachable();
    }
  }

  StepStatus zip_step_CASE0(RuntimeState * rts, Configuration * C, Redex * _0)
  {
    // ZipNode * zip = (ZipNode *) _0->root();
    // StepStatus status = rts->hnf(C, root, {1});
    Variable _2(*_0, 1);
    StepStatus status = rts->hnf(C, &_2);
    switch(status)
    {
      case E_OK      : break;
      case E_RESIDUAL: assert(0); return status;
      case E_UNWIND  : assert(0); return status;
      case E_RESTART : assert(0); return status;
    }
    // auto tag = inspect::tag_of(zip->rhs);
    auto tag = inspect::tag_of(_2.target());
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
        // ConsNode * lhs = NodeU{zip->lhs}.cons;
        // ConsNode * rhs = NodeU{zip->rhs}.cons;
        // Node * repl = cons(
        //      pair(lhs->head, rhs->head)
        //    , Node::create(&zip_Info, {lhs->tail, rhs->tail})
        //    );
        _0->root()->forward_to(repl);
        return E_OK;
      }
      case T_NIL:  _0->root()->make_nil();
                   return E_OK;
      default: __builtin_unreachable();
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

  StepStatus list01_step(RuntimeState * rts, Configuration * C, Redex * _0)
  {
    auto i0 = int_(0);
    auto i1 = int_(1);
    Node * goal = cons(i0, cons(i1, nil()));
    _0->root()->forward_to(goal);
    return E_OK;
  }

  StepStatus mainzip_step(RuntimeState * rts, Configuration * C, Redex * _0)
  {
    auto i2 = int_(2);
    auto i3 = int_(3);
    Node * lhs = Node::create(&list01_Info);
    Node * rhs = cons(i2, cons(i3, nil()));
    Node * goal = Node::create(&zip_Info, {lhs, rhs});
    _0->root()->forward_to(goal);
    return E_OK;
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
