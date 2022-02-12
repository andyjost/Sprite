#include <cassert>
#include "sprite/builtins.hpp"
#include "sprite/currylib/prelude.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

namespace sprite { inline namespace
{
  bool ub_equals(Cursor & lhs, Cursor & rhs)
  {
    assert(lhs.kind == rhs.kind);
    switch(lhs.kind)
    {
      case 'i': return (lhs->ub_int == rhs->ub_int);
      case 'f': return (lhs->ub_float == rhs->ub_float);
      case 'c': return (lhs->ub_char == rhs->ub_char);
      default: assert(0); __builtin_unreachable();
    }
  }

  void const * make_guides(ValueSet * vs, Cursor & cur)
  {
    if(cur.kind == 'p')
      return nullptr;
    else
    {
      vs->args = cur.arg;
      vs->size = 1;
      vs->kind = cur.kind;
      return vs;
    }
  }

  SStatus concurrentAnd_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    bool errs[2] = {false, false};
    index_type i = 0;
    tag_type tag;
    size_t stepnumber;
    while(true)
    {
      stepnumber = rts->stepcount;
      Variable _1(_0, i);
      tag = rts->hnf(C, &_1, &Bool_Type);
      switch(tag)
      {
        case E_RESIDUAL: errs[i] = true;
                         if(errs[1-i] && rts->stepcount == stepnumber)
                           return E_RESIDUAL;
                         break;
        case T_TRUE    : _0->root()->forward_to(_0->root()->successor(1-i));
                         return T_FWD;
        case T_FALSE   : _0->root()->forward_to(false_());
                         return T_FWD;
        default        : return tag;
      }
      i ^= index_type(1);
    }
  }

  SStatus constrEq_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable lhs(_0, 0), rhs(_0, 1);
    auto tagl = rts->hnf_or_free(C, &lhs);
    auto tagr = rts->hnf_or_free(C, &rhs);
    auto code = ((tagl == T_UNBOXED) ? 2 : 0) + ((tagr == T_UNBOXED) ? 1 : 0);
    ValueSet vs;
    switch(code)
    {
      case 1:
      case 2: throw InstantiationError("=:= cannot bind to an unboxed value");
      case 3: _0->root()->forward_to(
                  ub_equals(lhs.target(), rhs.target()) ? true_() : fail()
                );
              return T_FWD;
    }
    code = ((tagl == T_FREE) ? 2 : 0) + ((tagr == T_FREE) ? 1 : 0);
    switch(code)
    {
      case 1: return rts->hnf(C, &lhs, make_guides(&vs, rhs.target()));
      case 2: return rts->hnf(C, &rhs, make_guides(&vs, lhs.target()));
      case 3: _0->root()->forward_to(
                  lhs.vid() == rhs.vid()
                      ? true_()
                      : Node::create(
                            &StrictConstraint_Info
                          , {true_(), pair(lhs.target(), rhs.target())}
                          )
                );
              return T_FWD;
    }
    if(tagl != tagr) // case 0
      _0->root()->forward_to(fail());
    else
    {
      index_type arity = lhs.target().info()->arity;
      if(!arity)
        _0->root()->forward_to(true_());
      else
      {
        Arg * lsuc = lhs.target()->node->successors();
        Arg * rsuc = rhs.target()->node->successors();
        Node * tmp = Node::create(_0->info(), {lsuc[0], rsuc[0]});
        for(index_type i=1; i<arity; ++i)
          tmp = Node::create(
              &concurrentAnd_Info
            , {tmp, Node::create(_0->info(), {lsuc[i], rsuc[i]})}
            );
        _0->root()->forward_to(tmp);
      }
    }
    return T_FWD;
  }

  SStatus nonstrictEq_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable lhs(_0, 0), rhs(_0, 1);
    auto tagl = inspect::tag_of(lhs.target());
    auto tagr = inspect::tag_of(rhs.target());
    auto code = ((tagl == T_UNBOXED) ? 2 : 0) + ((tagr == T_UNBOXED) ? 1 : 0);
    switch(code)
    {
      case 1:
      case 2: throw InstantiationError("=:<= cannot bind to an unboxed value");
      case 3: _0->root()->forward_to(
                  ub_equals(lhs.target(), rhs.target()) ? true_() : fail()
                );
              return T_FWD;
    }
    tagl = rts->hnf_or_free(C, &lhs);
    if(tagl == T_FREE)
    {
      _0->root()->forward_to(
            Node::create(
                &NonStrictConstraint_Info
              , {true_(), pair(lhs.target(), rhs.target())}
              )
        );
      return T_FWD;
    }
    else if(tagl < T_CTOR)
      return tagl;
    tagr = rts->hnf_or_free(C, &rhs);
    if(tagr == T_FREE)
      return rts->hnf(C, &rhs, lhs.target().info()->type);
    else if(tagr < T_CTOR)
      return tagr;
    if(tagl != tagr)
      _0->root()->forward_to(fail());
    else
    {
      assert(lhs.target().info() == rhs.target().info());
      index_type arity = lhs.target().info()->arity;
      if(!arity)
        _0->root()->forward_to(true_());
      else
      {
        Arg * lsuc = lhs.target()->node->successors();
        Arg * rsuc = rhs.target()->node->successors();
        Node * tmp = Node::create(_0->info(), {lsuc[0], rsuc[0]});
        for(index_type i=1; i<arity; ++i)
          tmp = Node::create(
              &concurrentAnd_Info
            , {tmp, Node::create(_0->info(), {lsuc[i], rsuc[i]})}
            );
        _0->root()->forward_to(tmp);
      }
    }
    return T_FWD;
  }

  SStatus seq_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _1(*_0, 0);
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->root()->forward_to(fail());
                    return T_FWD;
      case T_TRUE:  _0->root()->forward_to(_0->root()->successor(1));
                    return T_FWD;
      default: return tag;
    }
  }
}}

namespace sprite
{
  InfoTable const concurrentAnd_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "&"
    , /*format*/     "pp"
    , /*step*/       concurrentAnd_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const constrEq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "=:="
    , /*format*/     "pp"
    , /*step*/       constrEq_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const nonstrictEq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "=:<="
    , /*format*/     "pp"
    , /*step*/       nonstrictEq_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const seq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "&>"
    , /*format*/     "pp"
    , /*step*/       seq_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };
}