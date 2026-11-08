#include "curryrt/curryrt.hpp"
#include "curryrt/checker.hpp"
#include "curryrt/currylib/prelude.hpp"
#include "curryrt/exceptions.hpp"
#include "curryrt/graph/walk.hpp"
#include "curryrt/inspect.hpp"

using namespace curryrt;

namespace curryrt { inline namespace
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
    if(_1.target->info->type != &PartApplic_Type)
      throw EvaluationError("ill-typed application: expected a partial application");
    PartApplicNode * partial = NodeU{_1.target}.partapplic;
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
  // (see RuntimeState::hnf).  The former runtime applies the same rule.
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
    if(_1.target->info->type != &PartApplic_Type)
      throw EvaluationError("ill-typed application: expected a partial application");
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
    // T_FREE: the action accepts a free variable (applyhnf_step and
    // applynf_step).
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

  static ValueSet const FREE_IN_CONFIGURATION{nullptr, 0, 'v'};

  // Do not inspect the function's captured arguments, or descend into a
  // free variable's shared generator: neither belongs to the demanded value.
  static bool wait_for_ground(RuntimeState * rts, Configuration * C, Cursor root)
  {
    GcClamp clamp;
    std::unordered_set<Node *> seen;
    bool ground = true;
    for(auto visitor = walk(root); visitor; ++visitor)
    {
      Cursor cur = visitor.cursor();
      if(cur.kind != 'p' || !seen.insert(cur).second)
        continue;
      if(inspect::isa_freevar(cur))
      {
        if(rts->is_free_in_configuration(C, cur))
        {
          C->add_residual(obj_id(cur), BOUND);
          ground = false;
        }
      }
      else
        visitor.extend();
    }
    return ground;
  }

  static tag_type applynormal_step(RuntimeState * rts, Configuration * C, bool ground)
  {
    auto normalize = [ground](
        RuntimeState * rts, Configuration * C, Variable * var, bool monadic
      ) -> tag_type
    {
      // Ground normalization must leave an undecided generator alone even
      // at the argument root. Ordinary ($!!) retains its hnf behavior.
      tag_type tag = rts->hnf(C, var,
          ground ? &FREE_IN_CONFIGURATION : nullptr, monadic);
      if(tag == E_RESIDUAL && inspect::isa_freevar(var->target))
      {
        C->remove_residual(obj_id(var->target));
        if(ground)
        {
          C->add_residual(obj_id(var->target), BOUND);
          return E_RESIDUAL;
        }
        return T_FREE;
      }
      if(tag < T_CTOR)
        return tag;
      // Keep pull-tabs and constraint lifts rooted at the argument.
      // Only failure belongs to the redex.
      Cursor redex = C->cursor();
      C->scan.push(var);
      tag = rts->procN(C, var->target);
      C->scan.pop();
      if(tag == T_FAIL)
      {
        if(rts->checker)
          rts->checker->normalization_failure(C, redex);
        return redex->make_failure();
      }
      // Interrupted normalization (including E_RESTART) retains the redex.
      // Check only a completed normal form, before _applyspecial forwards
      // it to apply. Each wake normalizes again, since a binding can bring
      // more free variables into the argument.
      if(tag >= T_CTOR && ground && !wait_for_ground(rts, C, var->target))
        return E_RESIDUAL;
      return tag;
    };
    return _applyspecial(rts, C, normalize);
  }

  static tag_type applynf_step(RuntimeState * rts, Configuration * C)
    { return applynormal_step(rts, C, false); }

  static tag_type applygnf_step(RuntimeState * rts, Configuration * C)
    { return applynormal_step(rts, C, true); }

  static tag_type applyhnf_step(RuntimeState * rts, Configuration * C)
  {
    auto && headnormalize = [](
        RuntimeState * rts, Configuration * C, Variable * var, bool monadic
      )
    {
      tag_type tag = rts->hnf(C, var, nullptr, monadic);
      // A free variable is a head normal form: ($!) applies the function to
      // the variable, as the former runtime and PAKCS do (id $! x gives x).
      // hnf recorded a residual for it; take it back, as hnf_or_free does,
      // and report the variable (issue #112).
      if(tag == E_RESIDUAL && inspect::isa_freevar(var->target))
      {
        C->remove_residual(obj_id(var->target));
        return T_FREE;
      }
      return tag;
    };
    return _applyspecial(rts, C, headnormalize);
  }

  static tag_type ensureNotFree_step(RuntimeState * rts, Configuration * C)
  {
    Cursor _0 = C->cursor();
    Variable _1 = _0[0];
    auto tag = rts->hnf_or_free(C, &_1, &FREE_IN_CONFIGURATION);
    if(tag < T_CTOR)
    {
      if(tag != T_FREE)
        return tag;
      C->add_residual(obj_id(_1.target), BOUND);
      return E_RESIDUAL;
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
