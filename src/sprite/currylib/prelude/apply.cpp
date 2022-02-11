#include <cassert>
#include <functional>
#include "sprite/builtins.hpp"
#include "sprite/currylib/prelude.hpp"
#include "sprite/exceptions.hpp"
#include "sprite/graph/variable.hpp"
#include "sprite/inspect.hpp"
#include "sprite/state/rts.hpp"

namespace sprite { inline namespace
{
  SStatus cond_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _1(_0, 0);
    auto tag = rts->hnf(C, _1, &Bool_Type);
    switch(tag)
    {
      case T_FALSE: _0->root.forward_to(fail());
                    return T_FWD;
      case T_TRUE : _0->root.forward_to(_0->root()->sucessor(1));
                    return T_FWD;
      default: return tag;
    }
  }

  SStatus apply_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    Variable _1(_0, 0);
    auto tag = rts->hnf(C, _1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1->target()}.partapplic;
    Node * arg = _0->root().successors(1);
    Node * replacement = partial->complete(arg)
        ? Node::from_partial(partial, arg)
        : Node::create(
              &PartApplic_Info, partial->missing - 1, partial->func_info
            , cons(arg, partial->terms)
            );
    _0->root().forward_to(replacement);
    return T_FWD;
  }

  template<typename Action>
  static SStatus _applyspecial(
      RuntimeState * rts, Configuration * C, Redex const * _0
    , Action const & action
    )
  {
    Variable _1(_0, 0);
    auto tag = rts->hnf(C, _1);
    if(tag != T_CTOR)
      return tag;
    PartApplicNode * partial = NodeU{_1->target()}.partapplic;
    Node * arg = _0->root().successors(1);
    // TODO: catch nondeterminism in IO
    Variable _2(_0, 1);
    Node * xformed = action(rts, C, &_2);
    Node * replacement = Node::create(
        &apply_Info, _0->root->successor(0), xformed
      );
    _0->root().forward_to(replacement);
    return T_FWD;
  }

  SStatus applygnf_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    auto rv = applynf_step(rts, C, _0);
    std::unordered_set<xid_type> unbound;
    for(Node * node: iterexpr(_0->root()))
    {
      if(inspect::isa_freevar(node) && !has_generator(node))
        unbound.insert(obj_id(node));
    }
    if(!unbound.empty())
      // FIXME: return unbound set
      return E_RESIDUAL;
    else
      return rv;
  }

  SStatus applyhnf_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    return _applyspecial(rts, C, _0, std::bind(&RuntimeState::hnf));
  }

  SStatus applynf_step(RuntimeState * rts, Configuration * C, Redex const * _0)
  {
    auto && normalize = [](RuntimeState * rts, Configuration * C, Variable * var)
      -> Node *
    {
      tag_type tag;
      NStatus status = rts->procN(C, tag);
      if(status != N_YIELD)
        return tag;
      return var->target();
    };
    return _applyspecial(rts, C, _0, normalize);
  }
}

namespace sprite
{
  InfoTable const apply_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "$"
    , /*format*/     "pp"
    , /*step*/       apply_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applygnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "$##"
    , /*format*/     "pp"
    , /*step*/       applygnf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applyhnf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "$!"
    , /*format*/     "pp"
    , /*step*/       applyhnf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const applynf_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "$!!"
    , /*format*/     "pp"
    , /*step*/       applynf_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };

  InfoTable const cond_Info {
      /*tag*/        T_FUNC
    , /*arity*/      2
    , /*alloc_size*/ sizeof(Node2)
    , /*typetag*/    NO_FLAGS
    , /*flags*/      NO_FLAGS
    , /*name*/       "cond"
    , /*format*/     "pp"
    , /*step*/       cond_step
    , /*typecheck*/  nullptr
    , /*type*/       nullptr
    };
}
