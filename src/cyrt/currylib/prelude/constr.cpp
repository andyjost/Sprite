#include <cassert>
#include "cyrt/cyrt.hpp"

using namespace cyrt;

namespace cyrt { inline namespace
{
  bool ub_equals(Cursor & lhs, Cursor & rhs)
  {
    assert(lhs.kind == rhs.kind);
    switch(lhs.kind)
    {
      case 'i': return (lhs.arg->ub_int == rhs.arg->ub_int);
      case 'f': return (lhs.arg->ub_float == rhs.arg->ub_float);
      case 'c': return (lhs.arg->ub_char == rhs.arg->ub_char);
      default: assert(0); __builtin_unreachable();
    }
  }

  void const * make_guides(ValueSet * vs, Cursor & cur)
  {
    assert(cur.kind == 'p');
    switch(typetag(*cur->info))
    {
      case F_INT_TYPE:
        vs->args = &NodeU{cur}.nodeN->data[0];
        vs->size = 1;
        vs->kind = 'i';
        return vs;
      case F_CHAR_TYPE:
        vs->args = &NodeU{cur}.nodeN->data[0];
        vs->size = 1;
        vs->kind = 'c';
        return vs;
      case F_FLOAT_TYPE:
        vs->args = &NodeU{cur}.nodeN->data[0];
        vs->size = 1;
        vs->kind = 'f';
        return vs;
      default:
        assert(cur->info->type);
        return cur->info->type;
    }
  }

  tag_type concurrentAnd_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    bool errs[2] = {false, false};
    index_type i = 0;
    tag_type tag;
    size_t stepnumber;
    while(true)
    {
      stepnumber = rts->stepcount;
      Variable _1 = _0[i];
      tag = rts->hnf(C, &_1, &Bool_Type);
      switch(tag)
      {
        case E_RESIDUAL: errs[i] = true;
                         if(errs[1-i] && rts->stepcount == stepnumber)
                           return E_RESIDUAL;
                         break;
        case T_TRUE    : _0->forward_to(_0->successor(1-i));
                         return T_FWD;
        case T_FALSE   : _0->forward_to(False);
                         return T_FWD;
        default        : return tag;
      }
      i ^= index_type(1);
    }
  }

  static xid_type vid(Variable const & var)
    { return inspect::xget_freevar_id(var.target); }

  tag_type constrEq_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable lhs = _0[0];
    Variable rhs = _0[1];
    // lhs:{0: ctor, 1: free, 2: unboxed} + rhs:{0: ctor, 3: free, 6: unboxed}
    int code = 0;
    auto tagl = rts->hnf_or_free(C, &lhs);
    switch(tagl)
    {
      case T_UNBOXED: code += 2; break;
      case T_FREE   : code += 1; break;
      default       : if(tagl < T_CTOR) return tagl;
    }
    auto tagr = rts->hnf_or_free(C, &rhs);
    switch(tagr)
    {
      case T_UNBOXED: code += 6; break;
      case T_FREE   : code += 3; break;
      default       : if(tagr < T_CTOR) return tagr;
    }
    ValueSet vs;
    switch(code)
    {
      case 1: return rts->hnf(C, &lhs, make_guides(&vs, rhs.target));
      case 3: return rts->hnf(C, &rhs, make_guides(&vs, lhs.target));
      case 4: _0->forward_to(
                  vid(lhs) == vid(rhs)
                      ? True
                      : Node::create(
                            &StrictConstraint_Info
                          , True, pair(lhs.target, rhs.target)
                          )
                );
              return T_FWD;
      case 2:
      case 5:
      case 6:
      case 7: throw InstantiationError("=:= cannot bind to an unboxed value");
      case 8: _0->forward_to(
                  ub_equals(lhs.target, rhs.target) ? True : Fail
                );
              return T_FWD;
      default: break;
    }
    assert(tagl >= T_CTOR && tagr >= T_CTOR);
    if(tagl != tagr)
      _0->forward_to(Fail);
    else
    {
      index_type arity = lhs.target->info->arity;
      if(!arity)
        _0->forward_to(True);
      else
      {
        Node * result = nullptr;
        switch(typetag(*lhs.target->info))
        {
          case F_INT_TYPE:
            result = (NodeU{lhs.target}.int_->value == NodeU{rhs.target}.int_->value) ? True : False;
            break;
          case F_CHAR_TYPE:
            result = (NodeU{lhs.target}.char_->value == NodeU{rhs.target}.char_->value) ? True : False;
            break;
          case F_FLOAT_TYPE:
            result = (NodeU{lhs.target}.float_->value == NodeU{rhs.target}.float_->value) ? True : False;
            break;
          default:
          {
            Arg * lsuc = lhs.target->successors();
            Arg * rsuc = rhs.target->successors();
            result = Node::create(_0->info, lsuc[0], rsuc[0]);
            for(index_type i=1; i<arity; ++i)
              result = Node::create(
                  &concurrentAnd_Info
                , result
                , Node::create(_0->info, lsuc[i], rsuc[i])
                );
          }
        }
        _0->forward_to(result);
      }
    }
    return T_FWD;
  }

  tag_type nonstrictEq_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable lhs = _0[0];
    Variable rhs = _0[1];
    auto tagl = inspect::tag_of(lhs.target);
    auto tagr = inspect::tag_of(rhs.target);
    auto code = ((tagl == T_UNBOXED) ? 2 : 0) + ((tagr == T_UNBOXED) ? 1 : 0);
    switch(code)
    {
      case 1:
      case 2: throw InstantiationError("=:<= cannot bind to an unboxed value");
      case 3: _0->forward_to(
                  ub_equals(lhs.target, rhs.target) ? True : Fail
                );
              return T_FWD;
    }
    tagl = rts->hnf_or_free(C, &lhs);
    if(tagl == T_FREE)
    {
      _0->forward_to(
            Node::create(
                &NonStrictConstraint_Info
              , True, pair(lhs.target, rhs.target)
              )
        );
      return T_FWD;
    }
    else if(tagl < T_CTOR)
      return tagl;
    tagr = rts->hnf_or_free(C, &rhs);
    if(tagr == T_FREE)
      return rts->hnf(C, &rhs, lhs.target->info->type);
    else if(tagr < T_CTOR)
      return tagr;
    if(tagl != tagr)
      _0->forward_to(Fail);
    else
    {
      assert(lhs.target->info == rhs.target->info);
      index_type arity = lhs.target->info->arity;
      if(!arity)
        _0->forward_to(True);
      else
      {
        Arg * lsuc = lhs.target->successors();
        Arg * rsuc = rhs.target->successors();
        Node * tmp = Node::create(_0->info, lsuc[0], rsuc[0]);
        for(index_type i=1; i<arity; ++i)
          tmp = Node::create(
              &concurrentAnd_Info
            , tmp
            , Node::create(_0->info, lsuc[i], rsuc[i])
            );
        _0->forward_to(tmp);
      }
    }
    return T_FWD;
  }

  tag_type seq_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->forward_to(Fail);
                    return T_FWD;
      case T_TRUE:  _0->forward_to(_0->successor(1));
                    return T_FWD;
      default: return tag;
    }
  }
}}

// namespace cyrt
extern "C"
{
  InfoTable const concurrentAnd_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "&"
    , /*format*/     "pp"
    , /*step*/       concurrentAnd_step
    , /*type*/       nullptr
    };

  InfoTable const constrEq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "constrEq"
    , /*format*/     "pp"
    , /*step*/       constrEq_step
    , /*type*/       nullptr
    };

  InfoTable const nonstrictEq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "nonStrictEq"
    , /*format*/     "pp"
    , /*step*/       nonstrictEq_step
    , /*type*/       nullptr
    };

  InfoTable const seq_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "&>"
    , /*format*/     "pp"
    , /*step*/       seq_step
    , /*type*/       nullptr
    };
}

