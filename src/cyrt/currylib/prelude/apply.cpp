#include "cyrt/cyrt.hpp"
#include "cyrt/currylib/prelude.hpp"
#include "cyrt/graph/walk.hpp"
#include "cyrt/inspect.hpp"

using namespace cyrt;

namespace cyrt { inline namespace
{
  static tag_type cond_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->forward_to(Fail);
                    return T_FWD;
      case T_TRUE : _0->forward_to(_0->successor(1));
                    return T_FWD;
      default: return tag;
    }
  }

  static tag_type apply_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    assert(partial->info->type == &PartApplic_Type);
    Node * arg = _0->successor(1);
    // A partial application reached through set guards (a function value
    // that is an argument of a set function, or that such an argument holds)
    // keeps its arguments boxed: each goes under the guards crossed on the
    // way to it (guard_successors).  The application itself is not boxed,
    // and neither is ``arg``, a successor of the redex.
    index_type const nargs = partial->nargs();
    if(partial->complete(arg))
    {
      // The function node is written into the redex when it fits: a function
      // of up to two arguments.  See Node::rewrite.
      if(partial->head_info->alloc_size <= _0->info->alloc_size)
      {
        tag_type const tag = _0->rewrite_from_partial(partial, arg);
        guard_successors(*_0, 0, nargs, _1.guards);
        return tag;
      }
      Node * replacement = Node::from_partial(partial, arg);
      guard_successors(replacement, 0, nargs, _1.guards);
      _0->forward_to(replacement);
      return T_FWD;
    }
    // One more argument: one node, with the arguments inline.  It never fits
    // the redex (three words and the arguments against a head and two).
    Node * extended = Node::extend_partial(partial, arg);
    guard_successors(extended, 2, 2 + nargs, _1.guards);
    _0->forward_to(extended);
    return T_FWD;
  }

  // Applies a function to an argument that ``action`` evaluates first.  The
  // argument is evaluated on behalf of the function applied.  So a choice in
  // the argument of a monadic function is an error, as in a monadic step
  // (see RuntimeState::hnf).  The Python backend applies the same rule.
  template<typename Action>
  static tag_type _applyspecial(
      RuntimeState * rts, Configuration * C, Action const & action
    )
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf(C, &_1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
    bool const monadic = partial->head_info
        && is_monadic(*partial->head_info);
    Variable _2 = _0[1];
    tag = action(rts, C, &_2, monadic);
    if(tag < T_UNBOXED)
      return tag;
    // hnf forwards the redex when the argument fails, is a constraint, or
    // holds a choice that it pull-tabs to the root.  The redex is then gone,
    // and so is the slot ``_2`` refers to.
    if(_0->info->tag == T_FWD)
      return T_FWD;
    // T_FREE: the action accepts a free variable (applynf_step).
    if(tag < T_CTOR && tag != T_FREE)
      return rts->hnf(C, &_2, nullptr, monadic);
    // The function and the argument keep the guards crossed on the way to
    // them (rvalue), so the box rule reaches the application (apply_step).
    Node * replacement = Node::create(
        &apply_Info, _1.rvalue(), _2.rvalue()
      );
    _0->forward_to(replacement);
    return T_FWD;
  }

  static tag_type applynf_step(RuntimeState * rts, Configuration * C)
  {
    auto && normalize = [](
        RuntimeState * rts, Configuration * C, Variable * var, bool monadic
      )
    {
    redo:
      // hnf first: it handles a choice, a failure, or a constraint at the
      // root of the argument.  procN pull-tabs a choice to the root of its
      // scan, which must not be the choice itself.
      tag_type tag = rts->hnf(C, var, nullptr, monadic);
      // A free variable is a normal form: ($!!) and normalForm give the
      // variable, as the Python backend and PAKCS do.  hnf recorded a
      // residual for it; take it back, as hnf_or_free does, and report the
      // variable.  ($##) suspends on it afterwards (applygnf_step).
      if(tag == E_RESIDUAL && inspect::isa_freevar(var->target))
      {
        C->remove_residual(obj_id(var->target));
        return T_FREE;
      }
      if(tag < T_CTOR)
        return tag;
      C->scan.push(var);
      tag = rts->procN(C, var->target);
      C->scan.pop();
      if(tag == E_RESTART)
        goto redo;
      return tag;
    };
    return _applyspecial(rts, C, normalize);
  }

  static tag_type applygnf_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    auto rv = applynf_step(rts, C);
    // The ground check applies when the normalization completed and the
    // redex became the application.  Any other outcome is handed on as it
    // is: the normalization was interrupted (E_GC, E_ROTATE, E_UNWIND),
    // suspended, or raised an error, or hnf forwarded the redex to a
    // failure, a lifted constraint, or a pull-tabbed choice.  The free
    // variables still in the expression may be bound when the evaluation
    // resumes (a constraint at the root binds them); a residual for them
    // here suspended the configuration for good.
    if(rv != T_FWD || _0->info->tag != T_FWD
        || NodeU{_0}.fwd->target->info != &apply_Info)
      return rv;
    Residuals unbound;
    auto node_visitor = visit_unique(_0);
    while(Node * node = node_visitor.next())
    {
      if(inspect::isa_freevar(node) && !has_generator(node))
        unbound.insert(obj_id(node));
    }
    if(!unbound.empty())
    {
      for(auto vid: unbound)
        C->add_residual(vid);
      return E_RESIDUAL;
    }
    else
      return rv;
  }

  static tag_type applyhnf_step(RuntimeState * rts, Configuration * C)
  {
    auto && headnormalize = [](
        RuntimeState * rts, Configuration * C, Variable * var, bool monadic
      )
      { return rts->hnf(C, var, nullptr, monadic); };
    return _applyspecial(rts, C, headnormalize);
  }

  static tag_type ensureNotFree_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf_or_free(C, &_1);
    if(tag < T_CTOR)
    {
      if(tag != T_FREE)
        return tag;
      if(rts->is_void(C, _1.target))
      {
        xid_type vid = obj_id(_1.target);
        C->add_residual(vid);
        return E_RESIDUAL;
      }
    }
    _0->forward_to(_1);
    return T_FWD;
  }
}}

extern "C"
{
  InfoTable const apply_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "apply"
    , /*format*/     "pp"
    , /*step*/       apply_step
    , /*type*/       nullptr
    };

  InfoTable const applygnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$##"
    , /*format*/     "pp"
    , /*step*/       applygnf_step
    , /*type*/       nullptr
    };

  InfoTable const applyhnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$!"
    , /*format*/     "pp"
    , /*step*/       applyhnf_step
    , /*type*/       nullptr
    };

  InfoTable const applynf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_OPERATOR | F_STATIC_OBJECT
    , /*name*/       "$!!"
    , /*format*/     "pp"
    , /*step*/       applynf_step
    , /*type*/       nullptr
    };

  InfoTable const cond_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "cond"
    , /*format*/     "pp"
    , /*step*/       cond_step
    , /*type*/       nullptr
    };

  InfoTable const ensureNotFree_Info {
      /*tag*/        T_FUNC
    , /*arity*/      1
    , /*alloc_size*/ sizeof(Node1)
    , /*flags*/      F_STATIC_OBJECT
    , /*name*/       "ensureNotFree"
    , /*format*/     "p"
    , /*step*/       ensureNotFree_step
    , /*type*/       nullptr
    };
}
