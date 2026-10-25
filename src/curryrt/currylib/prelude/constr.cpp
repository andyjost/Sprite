#include <cassert>
#include "curryrt/curryrt.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/inspect.hpp"

using namespace curryrt;

namespace curryrt { inline namespace
{
  bool ub_equals(Cursor & lhs, Cursor & rhs)
  {
    if(lhs.kind != rhs.kind)
      throw EvaluationError("ill-typed equality");
    switch(lhs.kind)
    {
      case 'i': return (lhs.arg->ub_int == rhs.arg->ub_int);
      case 'f': return (lhs.arg->ub_float == rhs.arg->ub_float);
      case 'c': return (lhs.arg->ub_char == rhs.arg->ub_char);
      default: assert(0); __builtin_unreachable();
    }
  }

  // The guides that narrow a free variable to the other side of a
  // constraint: the one value of a primitive, boxed or unboxed, or the type
  // of a constructor.
  void const * make_guides(ValueSet * vs, Cursor & cur)
  {
    if(cur.kind != 'p')
    {
      vs->args = cur.arg;
      vs->size = 1;
      vs->kind = cur.kind;
      return vs;
    }
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
    Residuals residuals;
    C->residuals.swap(residuals);
    while(true)
    {
      stepnumber = rts->stepcount;
      Variable _1 = _0[i];
      tag = rts->hnf(C, &_1, &Bool_Type);
      switch(tag)
      {
        case E_RESIDUAL: errs[i] = true;
                         if(errs[1-i] && rts->stepcount == stepnumber)
                         {
                           C->residuals.merge(residuals);
                           return E_RESIDUAL;
                         }
                         break;
        case T_TRUE    : C->residuals.swap(residuals);
                         {
                           Variable remaining = _0[1-i];
                           InfoTable const * info = remaining.target->info;
                           // These constraints already succeed only with
                           // True.  Keep their tail position: wrapping the
                           // recursive equality of a list in one guard per
                           // cell makes its reduction quadratic.
                           if(info == &constrEq_Info
                               || info == &nonstrictEq_Info
                               || info == &concurrentAnd_Info)
                           {
                             _0->forward_to(_0->successor(1-i));
                             return T_FWD;
                           }
                         }
                         // Both operands are constraints: the remaining
                         // operand must succeed with True as well.
                         _0->forward_to(Node::create(
                             &CyI7Prelude12BindingGuard
                           , _0->successor(1-i), True
                           ));
                         return T_FWD;
        case T_FALSE   : C->residuals.swap(residuals);
                         rts->record_failure(C, &_1);
                         _0->forward_to(Fail);
                         return T_FWD;
        default        : C->residuals.swap(residuals);
                         return tag;
      }
      i ^= index_type(1);
    }
  }

  // Recursively applies =:= or =:<= to ground terms.
  static Node * _equate_rec(Cursor _0, index_type arity, Variable & lhs, Variable & rhs)
  {
    switch(typetag(*lhs.target->info))
    {
      case F_INT_TYPE:
        return (NodeU{lhs.target}.int_->value == NodeU{rhs.target}.int_->value) ? True : Fail;
      case F_CHAR_TYPE:
        return (NodeU{lhs.target}.char_->value == NodeU{rhs.target}.char_->value) ? True : Fail;
      case F_FLOAT_TYPE:
        return (NodeU{lhs.target}.float_->value == NodeU{rhs.target}.float_->value) ? True : Fail;
      default:
      {
        Node * result = Node::create(_0->info, lhs[0], rhs[0]);
        for(index_type i=1; i<arity; ++i)
          result = Node::create(
              &concurrentAnd_Info
            , result
            , Node::create(_0->info, lhs[i], rhs[i])
            );
        return result;
      }
    }
  }

  static xid_type vid(Variable const & var)
    { return inspect::xget_freevar_id(var.target); }

  // The guides of the equality steps: a variable is bound in a
  // configuration when the fingerprint of the configuration decides its
  // group, or when a binding holds it; a generator that another
  // configuration created binds nothing here (Def 2.57 of the note on the
  // Fair Scheme).  An equality step binds such a variable by its constraint
  // cell or its non-strict binding, without a narrowing (Def 2.62, Def
  // 2.75; issue #129), so hnf_or_free reports it as free.  The marker is a
  // value set of kind 'v' and no values, which replace_freevar reads
  // (state/rts_freevars.cpp).  Every other demand of a variable with a
  // generator narrows it by that generator (rule S.x).
  static ValueSet const FREE_IN_CONFIGURATION{nullptr, 0, 'v'};

  // The marker of the strict equality (kind 'd'): a variable the
  // configuration decides is reported as it is too, instead of being
  // replaced by its generator.  The step reads both sides before it
  // expands a decided one (decision D25 of 2026-10-12).
  static ValueSet const FREE_OR_DECIDED{nullptr, 0, 'd'};

  // Whether the configuration decides the variable at ``var``: the
  // fingerprint decides its group and no binding holds it.  Such a
  // variable reads as its instance (replace_freevar writes its generator
  // under FREE_IN_CONFIGURATION).
  static bool decided(RuntimeState * rts, Configuration * C, Variable const & var)
  {
    xid_type const gid = C->grp_id(vid(var));
    return !rts->get_binding(C, gid) && rts->is_narrowed(C, gid);
  }

  // Writes the generator of the decided variable at ``var`` into its slot
  // (rule S.x; the pull-tab follows in hnf).
  static tag_type expand(RuntimeState * rts, Configuration * C, Variable * var)
    { return rts->hnf_or_free(C, var, &FREE_IN_CONFIGURATION); }

  tag_type constrEq_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable lhs = _0[0];
    Variable rhs = _0[1];
    // lhs:{0: ctor, 1: variable, 2: unboxed}
    //   + rhs:{0: ctor, 3: variable, 6: unboxed}
    // A variable is one that is free in the configuration or one that the
    // configuration decides; a bound one was replaced by its binding.  A
    // decided variable is expanded to its instance once the other side is
    // known: against a constructor or a value, or against a second decided
    // variable.  Against a variable that is free in the configuration the
    // step records the pair instead (decision D25 of 2026-10-12): the
    // constraint step unites the two classes, with the occurs check, and
    // the free variable reads the instance through the class.  The values
    // are those of the narrowing of the free variable against the
    // instance, with fewer forks, and a cyclic pair fails the step where
    // the narrowing ran without end.
    int code = 0;
    auto tagl = rts->hnf_or_free(C, &lhs, &FREE_OR_DECIDED);
    switch(tagl)
    {
      case T_UNBOXED: code += 2; break;
      case T_FREE   : code += 1; break;
      default       : if(tagl < T_CTOR) return tagl;
    }
    auto tagr = rts->hnf_or_free(C, &rhs, &FREE_OR_DECIDED);
    switch(tagr)
    {
      case T_UNBOXED: code += 6; break;
      case T_FREE   : code += 3; break;
      default       : if(tagr < T_CTOR) return tagr;
    }
    ValueSet vs;
    switch(code)
    {
      case 1: if(decided(rts, C, lhs))
                return expand(rts, C, &lhs);
              return rts->hnf(C, &lhs, make_guides(&vs, rhs.target));
      case 3: if(decided(rts, C, rhs))
                return expand(rts, C, &rhs);
              return rts->hnf(C, &rhs, make_guides(&vs, lhs.target));
      case 4: if(vid(lhs) == vid(rhs))
              {
                _0->forward_to(True);
                return T_FWD;
              }
              // Two decided variables: the left one is expanded first, and
              // the step runs again with its instance.
              if(decided(rts, C, lhs) && decided(rts, C, rhs))
                return expand(rts, C, &lhs);
              // Two free variables, or a free one and a decided one: the
              // pair.
              _0->forward_to(
                  Node::create(
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
    if(lhs.target->info->type != rhs.target->info->type
        || (tagl == tagr && lhs.target->info->arity != rhs.target->info->arity))
      throw EvaluationError("ill-typed equality");
    if(tagl != tagr)
      _0->forward_to(Fail);
    else
    {
      index_type arity = lhs.target->info->arity;
      if(!arity)
        _0->forward_to(True);
      else
      {
        Node * replacement = _equate_rec(_0, arity, lhs, rhs);
        _0->forward_to(replacement);
      }
    }
    return T_FWD;
  }

  // The step of =:<=.  The left side is the pattern, the right side the
  // actual argument.  A free variable on the left takes the right side as a
  // non-strict binding.  A free variable on the right is bound to the
  // constructor or the value on the left, as =:= binds it: the narrowing is
  // guided (make_guides), so a free Char, Int or Float gets the value.  An
  // unguided narrowing over the type (the former code) made a Char node with
  // no value for a primitive type, and the alternative died.
  tag_type nonstrictEq_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable lhs = _0[0];
    Variable rhs = _0[1];
    // lhs:{0: boxed, 2: unboxed} + rhs:{0: boxed, 1: unboxed}
    auto tagl = inspect::tag_of(lhs.target);
    auto tagr = inspect::tag_of(rhs.target);
    auto code = ((tagl == T_UNBOXED) ? 2 : 0) + ((tagr == T_UNBOXED) ? 1 : 0);
    ValueSet vs;
    if(code == 3)
    {
      _0->forward_to(ub_equals(lhs.target, rhs.target) ? True : Fail);
      return T_FWD;
    }
    if(code != 2)
    {
      tagl = rts->hnf_or_free(C, &lhs, &FREE_IN_CONFIGURATION);
      if(tagl == T_FREE)
      {
        if(code == 1)
          return rts->hnf(C, &lhs, make_guides(&vs, rhs.target));
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
    }
    if(code != 1)
    {
      tagr = rts->hnf_or_free(C, &rhs, &FREE_IN_CONFIGURATION);
      if(tagr == T_FREE)
        return rts->hnf(C, &rhs, make_guides(&vs, lhs.target));
      else if(tagr < T_CTOR)
        return tagr;
    }
    // One side is an unboxed value and the other a node: the two sides of a
    // constraint have one representation, so this does not occur.
    if(code)
      throw InstantiationError("=:<= cannot compare an unboxed value with a node");
    if(lhs.target->info->type != rhs.target->info->type
        || (tagl == tagr && lhs.target->info->arity != rhs.target->info->arity))
      throw EvaluationError("ill-typed equality");
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
        Node * replacement = _equate_rec(_0, arity, lhs, rhs);
        _0->forward_to(replacement);
      }
    }
    return T_FWD;
  }

  // The step of the &> of the runtime (CyI7Prelude12BindingGuard; see
  // prelude.hpp).
  tag_type BindingGuard_step(RuntimeState * rts, Configuration * C)
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

// namespace curryrt
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
    , /*name*/       "nonstrictEq"
    , /*format*/     "pp"
    , /*step*/       nonstrictEq_step
    , /*type*/       nullptr
    };

  InfoTable const CyI7Prelude12BindingGuard {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "&>"
    , /*format*/     "pp"
    , /*step*/       BindingGuard_step
    , /*type*/       nullptr
    };
}

